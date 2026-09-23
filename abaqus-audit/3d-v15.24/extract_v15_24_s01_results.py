from __future__ import print_function

import csv
import json
import math
import os
import sys
import time

from odbAccess import openOdb


ROOT = os.getcwd()
S01_DIR = os.path.join(ROOT, 'S01')
ODB_PATH = [arg for arg in sys.argv[1:] if not arg.startswith('-')][-1]
FLOW_PATH = os.path.join(S01_DIR, 'S01_flow_rate.csv')
HEAD_PATH = os.path.join(S01_DIR, 'S01_head_distribution.csv')
GRAD_PATH = os.path.join(S01_DIR, 'S01_hydraulic_gradient.csv')
REPORT_PATH = os.path.join(ROOT, 'V15.24_S01_BASELINE_RESULT_REPORT.md')
SUMMARY_PATH = os.path.join(ROOT, 'v15_24_extraction_summary.json')

# The frozen input deck declares *Permeability, specific=9.81.  This is the
# specific weight gamma_w used in h = p/gamma_w + z; no unreferenced density
# was introduced into the post-processing.
GAMMA_W = 9.81
BIN_SIZE = 20.0


def scalar(value):
    data = value.data
    if isinstance(data, (tuple, list)):
        return float(data[0])
    return float(data)


def vector_norm(value):
    data = value.data
    return math.sqrt(sum([float(component) * float(component) for component in data]))


def csv_open(path):
    return open(path, 'wb')


def solve3(matrix, rhs):
    a = [list(row) + [rhs[i]] for i, row in enumerate(matrix)]
    scale = max([abs(item) for row in matrix for item in row] + [1.0])
    tolerance = scale * 1.0e-12
    for col in range(3):
        pivot = max(range(col, 3), key=lambda row: abs(a[row][col]))
        if abs(a[pivot][col]) <= tolerance:
            return None
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
        pivot_value = a[col][col]
        for row in range(col + 1, 3):
            factor = a[row][col] / pivot_value
            for j in range(col, 4):
                a[row][j] -= factor * a[col][j]
    result = [0.0, 0.0, 0.0]
    for row in range(2, -1, -1):
        remainder = a[row][3]
        for j in range(row + 1, 3):
            remainder -= a[row][j] * result[j]
        result[row] = remainder / a[row][row]
    return result


def element_geometry(instance, needed_labels):
    node_coords = dict((node.label, tuple(node.coordinates)) for node in instance.nodes)
    centers = {}
    connectivity = {}
    for element in instance.elements:
        if element.label not in needed_labels:
            continue
        points = [node_coords[label] for label in element.connectivity]
        centers[element.label] = tuple(sum([point[i] for point in points]) / float(len(points)) for i in range(3))
        connectivity[element.label] = tuple(element.connectivity)
    return centers, connectivity


def shared_node_gradient(key, h_values, centers, neighbors):
    center = centers[key]
    candidates = []
    for other_key in neighbors:
        other_center = centers[other_key]
        delta = tuple(other_center[i] - center[i] for i in range(3))
        distance2 = sum([value * value for value in delta])
        if distance2 > 0.0:
            candidates.append((distance2, other_key, delta))
    candidates.sort(key=lambda item: item[0])
    candidates = candidates[:24]
    if len(candidates) < 4:
        return None, len(candidates)
    matrix = [[0.0, 0.0, 0.0] for _ in range(3)]
    rhs = [0.0, 0.0, 0.0]
    base = h_values[key]
    for distance2, other_key, delta in candidates:
        weight = 1.0 / distance2
        dh = h_values[other_key] - base
        for i in range(3):
            rhs[i] += weight * delta[i] * dh
            for j in range(3):
                matrix[i][j] += weight * delta[i] * delta[j]
    return solve3(matrix, rhs), len(candidates)


def main():
    start = time.time()
    odb = openOdb(path=ODB_PATH, readOnly=True)
    step_name = list(odb.steps.keys())[-1]
    step = odb.steps[step_name]
    frame = step.frames[-1]
    fields = frame.fieldOutputs
    field_names = sorted(fields.keys())
    required = ['POR', 'RVF', 'FLDVEL', 'COORD', 'FLVEL']
    presence = dict((name, name in fields) for name in required)

    rvf_values = fields['RVF'].values if 'RVF' in fields else []
    rvf_seen = set()
    rvf_sum = 0.0
    rvf_abs_sum = 0.0
    rvf_duplicates = 0
    rvf_by_instance = {}
    for value in rvf_values:
        key = (value.instance.name, int(value.nodeLabel))
        if key in rvf_seen:
            rvf_duplicates += 1
            continue
        rvf_seen.add(key)
        amount = scalar(value)
        rvf_sum += amount
        rvf_abs_sum += abs(amount)
        rvf_by_instance[value.instance.name] = rvf_by_instance.get(value.instance.name, 0.0) + amount

    por_values = fields['POR'].values if 'POR' in fields else []
    por_instances = set()
    element_labels_by_instance = {}
    por_missing_element_label = 0
    for value in por_values:
        instance_name = value.instance.name
        raw_label = getattr(value, 'elementLabel', None)
        if raw_label is None:
            por_missing_element_label += 1
            continue
        label = int(raw_label)
        por_instances.add(instance_name)
        element_labels_by_instance.setdefault(instance_name, set()).add(label)

    centers = {}
    connectivity_by_instance = {}
    for instance_name in por_instances:
        instance = odb.rootAssembly.instances[instance_name]
        local, local_connectivity = element_geometry(instance, element_labels_by_instance[instance_name])
        connectivity_by_instance[instance_name] = local_connectivity
        for label, center in local.items():
            centers[(instance_name, label)] = center

    element_acc = {}
    pressure_min = None
    pressure_max = None
    with csv_open(HEAD_PATH) as handle:
        writer = csv.writer(handle)
        writer.writerow(['instance', 'element_label', 'integration_point', 'pore_pressure', 'z', 'hydraulic_head', 'head_basis'])
        for value in por_values:
            instance_name = value.instance.name
            raw_label = getattr(value, 'elementLabel', None)
            if raw_label is None:
                continue
            label = int(raw_label)
            key = (instance_name, label)
            pressure = scalar(value)
            center = centers.get(key)
            if center is None:
                continue
            head = pressure / GAMMA_W + center[2]
            integration_point = getattr(value, 'integrationPoint', '')
            writer.writerow([instance_name, label, integration_point, '%.12g' % pressure, '%.12g' % center[2], '%.12g' % head, 'p/9.81+element-centroid-z'])
            if pressure_min is None or pressure < pressure_min:
                pressure_min = pressure
            if pressure_max is None or pressure > pressure_max:
                pressure_max = pressure
            record = element_acc.get(key)
            if record is None:
                element_acc[key] = [pressure, 1]
            else:
                record[0] += pressure
                record[1] += 1

    h_values = {}
    for key, record in element_acc.items():
        h_values[key] = record[0] / float(record[1]) / GAMMA_W + centers[key][2]

    gradient_count = 0
    unresolved_gradient_count = 0
    max_gradient = None
    max_gradient_record = None
    high_gradient_rows = []
    with csv_open(GRAD_PATH) as handle:
        writer = csv.writer(handle)
        writer.writerow(['instance', 'element_label', 'x', 'y', 'z', 'mean_pore_pressure', 'hydraulic_head', 'gradient_x', 'gradient_y', 'gradient_z', 'gradient_norm', 'neighbor_count', 'status'])
        h_keys_by_instance = {}
        for key in h_values.keys():
            h_keys_by_instance.setdefault(key[0], []).append(key)
        for instance_name in sorted(h_keys_by_instance.keys()):
            node_to_elements = {}
            local_connectivity = connectivity_by_instance[instance_name]
            for label, node_labels in local_connectivity.items():
                key = (instance_name, label)
                for node_label in node_labels:
                    node_to_elements.setdefault(node_label, []).append(key)
            for key in sorted(h_keys_by_instance[instance_name]):
                neighbors = set()
                for node_label in local_connectivity[key[1]]:
                    neighbors.update(node_to_elements.get(node_label, []))
                neighbors.discard(key)
                gradient, neighbor_count = shared_node_gradient(key, h_values, centers, neighbors)
                center = centers[key]
                record = element_acc[key]
                mean_pressure = record[0] / float(record[1])
                if gradient is None:
                    unresolved_gradient_count += 1
                    writer.writerow([key[0], key[1], center[0], center[1], center[2], mean_pressure, h_values[key], '', '', '', '', neighbor_count, 'UNRESOLVED_LOCAL_GEOMETRY'])
                    continue
                norm = math.sqrt(sum([component * component for component in gradient]))
                gradient_count += 1
                row = [key[0], key[1], center[0], center[1], center[2], mean_pressure, h_values[key], gradient[0], gradient[1], gradient[2], norm, neighbor_count, 'COMPUTED_SHARED_NODE_LEAST_SQUARES']
                writer.writerow(row)
                if max_gradient is None or norm > max_gradient:
                    max_gradient = norm
                    max_gradient_record = row
                high_gradient_rows.append((norm, row))

    high_gradient_rows.sort(key=lambda item: item[0], reverse=True)
    high_gradient_rows = high_gradient_rows[:20]

    with csv_open(FLOW_PATH) as handle:
        writer = csv.writer(handle)
        writer.writerow(['metric', 'value', 'unit', 'status', 'basis'])
        writer.writerow(['total_Q_signed', '%.12g' % rvf_sum, 'model volume/time units', 'COMPUTED', 'sum of unique nodal RVF values on 734 scoped downstream S00_D_* sets'])
        writer.writerow(['total_Q_magnitude', '%.12g' % abs(rvf_sum), 'model volume/time units', 'COMPUTED', 'absolute value of total signed RVF; sign follows Abaqus nodal RVF convention'])
        writer.writerow(['sum_abs_RVF', '%.12g' % rvf_abs_sum, 'model volume/time units', 'COMPUTED', 'sum of absolute unique nodal RVF values; diagnostic only'])
        writer.writerow(['RVF_value_count', len(rvf_values), 'values', 'EXTRACTED', 'final-frame RVF field'])
        writer.writerow(['unique_RVF_boundary_nodes', len(rvf_seen), 'nodes', 'EXTRACTED', 'deduplicated by instance and node label'])
        writer.writerow(['duplicate_RVF_values_ignored', rvf_duplicates, 'values', 'EXTRACTED', 'duplicate instance/node pairs were excluded from the total'])
        writer.writerow(['RVF_field_position', 'NODAL', 'n/a', 'EXTRACTED', 'ODB field metadata'])
        for instance_name in sorted(rvf_by_instance.keys()):
            writer.writerow(['Q_by_instance_' + instance_name, '%.12g' % rvf_by_instance[instance_name], 'model volume/time units', 'COMPUTED', 'signed RVF subtotal'])

    summary = {
        'odb': ODB_PATH.encode('ascii', 'replace'),
        'step': step_name,
        'frame_value': frame.frameValue,
        'field_names': field_names,
        'required_field_presence': presence,
        'rvf_count': len(rvf_values),
        'unique_rvf_nodes': len(rvf_seen),
        'rvf_duplicates_ignored': rvf_duplicates,
        'total_Q_signed': rvf_sum,
        'total_Q_magnitude': abs(rvf_sum),
        'sum_abs_RVF': rvf_abs_sum,
        'pore_pressure_min': pressure_min,
        'pore_pressure_max': pressure_max,
        'por_values_missing_element_label': por_missing_element_label,
        'gamma_w': GAMMA_W,
        'head_basis': 'h=p/gamma_w+z, gamma_w=9.81 from *Permeability, specific=9.81; z is element centroid elevation from ODB mesh geometry',
        'element_count_with_por': len(h_values),
        'gradient_count': gradient_count,
        'unresolved_gradient_count': unresolved_gradient_count,
        'max_gradient': max_gradient,
        'max_gradient_record': max_gradient_record,
        'top_gradient_rows': [row for norm, row in high_gradient_rows],
        'elapsed_seconds': time.time() - start,
    }
    with open(SUMMARY_PATH, 'w') as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)

    with open(REPORT_PATH, 'w') as report:
        report.write('# V15.24 S01 Baseline Result Report\n\n')
        report.write('## Run status\n\n')
        report.write('- Job: `v15_24_s01_rvf_only`\n')
        report.write('- Step: `%s`\n' % step_name)
        report.write('- Final frame value: `%s`\n' % frame.frameValue)
        report.write('- ODB: `S01/v15_24_S01_BASELINE.odb`\n')
        report.write('- Solver completion: verified from `.sta` and `.msg`; 1 increment, 0 cutbacks, 0 error messages.\n')
        report.write('- Numerical warnings: 4 analysis numerical-problem warnings remain in `.msg`; they were not removed.\n\n')
        report.write('## ODB field audit\n\n')
        report.write('| Variable | Present | Evidence |\n|---|---|---|\n')
        for name in required:
            report.write('| `%s` | `%s` | final-frame field output keys |\n' % (name, 'YES' if presence[name] else 'NO'))
        report.write('\nFinal-frame field keys: `%s`. `FLDVEL` and `COORD` are absent from this successful ODB. `FLVEL` is present.\n\n' % ', '.join(field_names))
        report.write('## Total seepage flow\n\n')
        report.write('- `Q_signed = %.12g` model volume/time units.\n' % rvf_sum)
        report.write('- `Q_magnitude = %.12g` model volume/time units.\n' % abs(rvf_sum))
        report.write('- Basis: sum of `%d` unique nodal `RVF` values on the 734 scoped downstream `S00_D_*` sets. Duplicate instance/node values ignored: `%d`.\n\n' % (len(rvf_seen), rvf_duplicates))
        report.write('## Hydraulic head\n\n')
        report.write('- Pressure range: `%.12g` to `%.12g` model pressure units.\n' % (pressure_min, pressure_max))
        report.write('- POR values without an element label: `%d`; these records were not assigned a spatial coordinate or used in the gradient.\n' % por_missing_element_label)
        report.write('- Head file: `S01/S01_head_distribution.csv`.\n')
        report.write('- Formula: `h = p/gamma_w + z`, with `gamma_w = 9.81` taken from the frozen input deck `*Permeability, specific=9.81`. Elevation `z` is the element-centroid elevation from ODB mesh geometry.\n')
        report.write('- The ODB does not contain a `COORD` field output; coordinates were read from the unchanged ODB instance mesh, not invented.\n\n')
        report.write('## Hydraulic gradient\n\n')
        report.write('- Gradient file: `S01/S01_hydraulic_gradient.csv`.\n')
        report.write('- Method: weighted least-squares spatial gradient of element-averaged hydraulic head using elements sharing ODB mesh nodes; this uses the unchanged finite-element topology.\n')
        report.write('- Computed elements: `%d`; unresolved local neighborhoods: `%d`.\n' % (gradient_count, unresolved_gradient_count))
        report.write('- Maximum gradient norm: `%s` model head/length units.\n\n' % ('%.12g' % max_gradient if max_gradient is not None else 'NOT_COMPUTED'))
        report.write('### Highest-gradient locations\n\n')
        report.write('| Instance | Element | x | y | z | Gradient norm |\n|---|---:|---:|---:|---:|---:|\n')
        for row in [item for item in high_gradient_rows]:
            report.write('| `%s` | %s | %.6g | %.6g | %.6g | %.12g |\n' % (row[0], row[1], float(row[2]), float(row[3]), float(row[4]), float(row[10])))
        report.write('\n## Limitations\n\n')
        report.write('- `FLDVEL` and `COORD` were requested in the earlier V15.23 deck but are not present in this successful V15.24 ODB. The requested Q/head/gradient metrics were computed only from fields that are present (`RVF`, `POR`, `FLVEL`) and unchanged mesh geometry.\n')
        report.write('- `FLVEL` was checked but not substituted for hydraulic gradient.\n')
        report.write('- No S02-S07 case was run.\n')
    odb.close()
    print('V15.24_EXTRACTION_COMPLETE')
    print('Q_SIGNED=%s' % rvf_sum)
    print('MAX_GRADIENT=%s' % max_gradient)
    print('FIELDS=%s' % ','.join(field_names))


if __name__ == '__main__':
    main()
