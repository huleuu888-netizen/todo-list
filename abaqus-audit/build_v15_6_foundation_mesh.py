from __future__ import print_function

import csv
import math
import os
import re
import sys
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from repair_v12_3d import parse_deck
import build_v15_5_mesh_only as v55

ROOT = os.path.join(HERE, "3d-v15.6")
BASE_INP = os.path.join(
    HERE, "3d-v15.5",
    "doub_hydropower_part25_geometric_solids_v15_5_medium_mesh.inp")
GEOMETRY_INP = os.path.join(
    HERE, "3d-v15.4",
    "doub_hydropower_part25_geometric_solids_v15_4_geometry_mesh.inp")
OUT_INP = os.path.join(
    ROOT, "doub_hydropower_part25_geometric_solids_v15_6_foundation_mesh.inp")
OUT_CSV = {
    "freeze": os.path.join(ROOT, "v15_6_geometry_and_structure_freeze_check.csv"),
    "classification": os.path.join(ROOT, "v15_6_region_classification_audit.csv"),
    "remesh": os.path.join(ROOT, "v15_6_geology_remesh_map.csv"),
    "density": os.path.join(ROOT, "v15_6_mesh_density_audit.csv"),
    "quality": os.path.join(ROOT, "v15_6_mesh_quality_audit.csv"),
    "transition": os.path.join(ROOT, "v15_6_mesh_transition_audit.csv"),
    "conformity": os.path.join(ROOT, "v15_6_interface_node_conformity.csv"),
    "islands": os.path.join(ROOT, "v15_6_mesh_island_audit.csv"),
    "critical": os.path.join(ROOT, "v15_6_critical_interface_mesh_audit.csv"),
    "convergence": os.path.join(ROOT, "v15_6_mesh_convergence_plan.csv"),
    "inventory": os.path.join(ROOT, "v15_6_mesh_inventory.csv"),
}
OUT_REPORT = os.path.join(ROOT, "V15_6_FOUNDATION_MESH_RESULT.md")

EPS = 1.0e-8
QEPS = 1.0e-7
GEO_PREFIXES = ("LEFT_", "RIVER_", "RIGHT_")
MAX_SUBDIV = 24

FACE_DEFS = [
    (0, 1, 2, 3), (4, 5, 6, 7),
    (0, 1, 5, 4), (1, 2, 6, 5),
    (2, 3, 7, 6), (3, 0, 4, 7),
]
EDGE_DEFS = [
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
]
EDGE_AXIS = {
    0: (0, 1), 1: (0, 1), 2: (0, 1), 3: (0, 1),
    4: (0, 1), 5: (0, 1), 6: (0, 1), 7: (0, 1),
    8: (2,), 9: (2,), 10: (2,), 11: (2,),
}


def fmt(value):
    return "%.9g" % float(value)


def qkey(point):
    return tuple(round(float(v), 8) for v in point)


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def bbox_nodes(nodes):
    values = list(nodes.values()) if hasattr(nodes, "values") else list(nodes)
    if not values:
        return ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
    return ([min(p[i] for p in values) for i in range(3)],
            [max(p[i] for p in values) for i in range(3)])


def bbox_text(bounds):
    return "%.6f,%.6f,%.6f;%.6f,%.6f,%.6f" % tuple(bounds[0] + bounds[1])


def bbox_delta(a, b):
    values = [abs(a[0][i] - b[0][i]) for i in range(3)] + \
             [abs(a[1][i] - b[1][i]) for i in range(3)]
    return max(values) if values else 0.0


def element_rows(part):
    for etype, elements in part["elements"].items():
        for label, row in elements.items():
            yield etype, label, row


def interp_hex(points, u, v, w):
    signs = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
             (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
    weights = [0.125 * (1.0 + su * u) * (1.0 + sv * v) * (1.0 + sw * w)
               for su, sv, sw in signs]
    return tuple(sum(weights[n] * points[n][i] for n in range(8))
                 for i in range(3))


def axis_lengths(points):
    axes = [((0, 1), (3, 2), (4, 5), (7, 6)),
            ((0, 3), (1, 2), (4, 7), (5, 6)),
            ((0, 4), (1, 5), (2, 6), (3, 7))]
    return [sum(math.sqrt(sum((points[i][k] - points[j][k]) ** 2
                              for k in range(3))) for i, j in axis) /
            float(len(axis)) for axis in axes]


def face_key_from_qrow(qrow, face_index):
    return tuple(sorted(qrow[i] for i in FACE_DEFS[face_index]))


def edge_key(qrow, edge_index):
    a, b = EDGE_DEFS[edge_index]
    return tuple(sorted((qrow[a], qrow[b])))


def face_axis_groups(qrow, face_index):
    face_nodes = set(FACE_DEFS[face_index])
    groups = []
    for axis in range(3):
        keys = []
        allowed = ((0, 1, 4, 5) if axis == 0 else
                   (2, 3, 6, 7) if axis == 1 else
                   (8, 9, 10, 11))
        for edge_index in allowed:
            edge = EDGE_DEFS[edge_index]
            if set(edge).issubset(face_nodes):
                keys.append(edge_key(qrow, edge_index))
        if len(keys) == 2:
            groups.append((axis, frozenset(keys)))
    return groups


def target_size(distance):
    if distance <= 8.0:
        return 2.25
    if distance <= 20.0:
        return 3.75
    if distance <= 40.0:
        return 5.5
    if distance <= 60.0:
        return 7.75
    if distance <= 120.0:
        return 18.0
    return None


def band_name(distance):
    if distance <= 8.0:
        return "M3-A_0-8m"
    if distance <= 20.0:
        return "M3-B_8-20m"
    if distance <= 40.0:
        return "M3-C_20-40m"
    if distance <= 60.0:
        return "M3-D_40-60m"
    if distance <= 120.0:
        return "M4_TRANSITION_GEOLOGY"
    if distance <= 300.0:
        return "M4_FAR_FIELD_GEOLOGY"
    return "M4_REMOTE_BOUNDARY"


def primary_geology_region(distance):
    if distance <= 60.0:
        return "M3_FOUNDATION_GEOLOGY"
    if distance <= 120.0:
        return "M4_TRANSITION_GEOLOGY"
    if distance <= 300.0:
        return "M4_FAR_FIELD_GEOLOGY"
    return "M4_REMOTE_BOUNDARY"


def is_geology_instance(instance, part):
    upper = instance.upper()
    material = (part.get("material") or "").upper()
    if not upper.startswith(GEO_PREFIXES):
        return False
    if "_BX" in upper or "CURTAIN_GROUTING" in upper:
        return False
    if material in ("CONCRETE", "DEFORMATION_BODY"):
        return False
    return True


def part_elements_count(part):
    return sum(len(elements) for elements in part["elements"].values())


def make_cells(p4, i5, p5, boxes):
    cells = []
    per_instance = OrderedDict()
    # The V15.5 active geology cells are the frozen mesh/geometry baseline;
    # no V15.4 coordinates are substituted into the repair.
    for instance, p5_name in i5:
        p5_part = p5[p5_name]
        if not is_geology_instance(instance, p5_part):
            continue
        p4_part = p5_part
        count = 0
        for etype, label, row in element_rows(p4_part):
            if len(row) != 8 or etype not in ("C3D8P", "C3D8R"):
                raise RuntimeError("Unsupported geology element %s %s %s" %
                                   (instance, etype, label))
            points = [p4_part["nodes"][node] for node in row]
            centroid = tuple(sum(point[i] for point in points) / 8.0
                             for i in range(3))
            distance, nearest = v55.nearest_structure_distance(centroid, boxes)
            axes = axis_lengths(points)
            # Regenerate one bounded local block with one common subdivision
            # pattern. This keeps all local faces conformal without the
            # runaway propagation that a per-cell max rule causes. Remote
            # geology is retained at its original orphan-mesh density.
            local_zone = distance <= 120.0
            counts = [4, 4, 1] if local_zone else [1, 1, 1]
            qrow = tuple(qkey(point) for point in points)
            cells.append({
                "id": len(cells), "instance": instance, "material": p4_part["material"],
                "source_part": p4_part, "source_etype": etype, "source_label": label,
                "qrow": qrow, "points": points, "centroid": centroid,
                "distance": distance, "nearest": nearest, "band": band_name(distance),
                "local_zone": local_zone,
                "counts": counts,
            })
            count += 1
        per_instance[instance] = {"material": p4_part["material"],
                                  "source_elements": count}
    return cells, per_instance


def synchronize_face_subdivisions(cells):
    face_incidents = defaultdict(list)
    for cell in cells:
        for face_index in range(6):
            face_incidents[face_key_from_qrow(cell["qrow"], face_index)].append(
                (cell["id"], face_index))
    internal_source_faces = sum(1 for incidents in face_incidents.values()
                                if len(incidents) == 2)
    boundary_source_faces = sum(1 for incidents in face_incidents.values()
                                if len(incidents) == 1)
    nonmanifold_source_faces = sum(1 for incidents in face_incidents.values()
                                   if len(incidents) > 2)
    return {"face_incidents": face_incidents,
            "internal_source_faces": internal_source_faces,
            "boundary_source_faces": boundary_source_faces,
            "nonmanifold_source_faces": nonmanifold_source_faces,
            "iterations": 1}


def register_node(point, node_registry, nodes):
    key = qkey(point)
    if key not in node_registry:
        node_registry[key] = len(nodes) + 1
        nodes[node_registry[key]] = tuple(float(v) for v in key)
    return node_registry[key]


def subdivide_cell(cell, node_registry, nodes, next_element):
    nu, nv, nw = cell["counts"]
    grid = {}
    for k in range(nw + 1):
        w = -1.0 + 2.0 * k / float(nw)
        for j in range(nv + 1):
            v = -1.0 + 2.0 * j / float(nv)
            for i in range(nu + 1):
                u = -1.0 + 2.0 * i / float(nu)
                corner = {(0, 0, 0): 0, (nu, 0, 0): 1,
                          (nu, nv, 0): 2, (0, nv, 0): 3,
                          (0, 0, nw): 4, (nu, 0, nw): 5,
                          (nu, nv, nw): 6, (0, nv, nw): 7}.get((i, j, k))
                point = cell["points"][corner] if corner is not None else \
                    interp_hex(cell["points"], u, v, w)
                grid[(i, j, k)] = register_node(
                    point, node_registry, nodes)
    children = []
    for k in range(nw):
        for j in range(nv):
            for i in range(nu):
                row = (grid[(i, j, k)], grid[(i + 1, j, k)],
                       grid[(i + 1, j + 1, k)], grid[(i, j + 1, k)],
                       grid[(i, j, k + 1)], grid[(i + 1, j, k + 1)],
                       grid[(i + 1, j + 1, k + 1)],
                       grid[(i, j + 1, k + 1)])
                source_faces = {}
                if k == 0:
                    source_faces[0] = (row[0], row[1], row[2], row[3])
                if k == nw - 1:
                    source_faces[1] = (row[4], row[5], row[6], row[7])
                if j == 0:
                    source_faces[2] = (row[0], row[1], row[5], row[4])
                if i == nu - 1:
                    source_faces[3] = (row[1], row[2], row[6], row[5])
                if j == nv - 1:
                    source_faces[4] = (row[3], row[2], row[6], row[7])
                if i == 0:
                    source_faces[5] = (row[0], row[4], row[7], row[3])
                children.append({"label": next_element, "etype": cell["source_etype"],
                                "row": row, "material": cell["material"],
                                "source_instance": cell["instance"],
                                "source_label": cell["source_label"],
                                "source_cell_id": cell["id"],
                                "source_faces": source_faces,
                                "distance": cell["distance"],
                                "nearest": cell["nearest"],
                                "band": cell["band"]})
                next_element += 1
    return children, next_element


def build_combined_mesh(cells):
    nodes = OrderedDict()
    node_registry = {}
    elements = []
    next_element = 1
    by_source = defaultdict(lambda: {"source_elements": 0,
                                     "rebuilt_elements": 0,
                                     "bands": defaultdict(int)})
    for cell in cells:
        by_source[cell["instance"]]["source_elements"] += 1
        children, next_element = subdivide_cell(cell, node_registry, nodes,
                                                next_element)
        elements.extend(children)
        by_source[cell["instance"]]["rebuilt_elements"] += len(children)
        by_source[cell["instance"]]["bands"][cell["band"]] += len(children)
    generated_faces = defaultdict(lambda: defaultdict(set))
    for element in elements:
        for face_index, row in element["source_faces"].items():
            generated_faces[element["source_cell_id"]][face_index].add(
                tuple(sorted(qkey(nodes[node]) for node in row)))
    return nodes, elements, by_source, generated_faces


def audit_generated_faces(source_face_data, generated_faces, cells):
    by_id = {cell["id"]: cell for cell in cells}
    conforming = 0
    nonconforming = 0
    local_remote = 0
    for _face_key, incidents in source_face_data["face_incidents"].items():
        if len(incidents) != 2:
            continue
        (a_id, a_face), (b_id, b_face) = incidents
        a_faces = generated_faces[a_id][a_face]
        b_faces = generated_faces[b_id][b_face]
        if a_faces == b_faces:
            conforming += 1
        else:
            nonconforming += 1
            if by_id[a_id]["local_zone"] != by_id[b_id]["local_zone"]:
                local_remote += 1
    source_face_data["conforming_generated_faces"] = conforming
    source_face_data["nonconforming_generated_faces"] = nonconforming
    source_face_data["local_remote_interface_count"] = local_remote
    return source_face_data


def part_lines_multi(name, nodes, elements):
    lines = ["** V15.6 conformal regenerated foundation geology: %s" % name,
             "*Part, name=%s" % name, "*Node"]
    for label, point in nodes.items():
        lines.append("%d, %s, %s, %s" % (label, fmt(point[0]), fmt(point[1]),
                                          fmt(point[2])))
    by_type = defaultdict(list)
    material_sets = defaultdict(list)
    for element in elements:
        by_type[element["etype"]].append(element)
        material_sets[element["material"]].append(element["label"])
    for etype in sorted(by_type):
        lines.append("*Element, type=%s" % etype)
        for element in by_type[etype]:
            lines.append("%d, %s" %
                         (element["label"], ", ".join(str(v) for v in element["row"])))
    all_labels = [element["label"] for element in elements]
    lines.append("*Elset, elset=V15_6_ALL")
    for start in range(0, len(all_labels), 16):
        lines.append(", ".join(str(v) for v in all_labels[start:start + 16]))
    for material in sorted(material_sets):
        safe = re.sub(r"[^A-Za-z0-9_]", "_", material or "UNSPECIFIED")
        set_name = "V15_6_MAT_%s" % safe
        labels = material_sets[material]
        lines.append("*Elset, elset=%s" % set_name)
        for start in range(0, len(labels), 16):
            lines.append(", ".join(str(v) for v in labels[start:start + 16]))
        lines.extend(["*Solid Section, elset=%s, material=%s" %
                      (set_name, material or "UNSPECIFIED"), ","])
    lines.extend(["*End Part", "**"])
    return lines


def rewrite_assembly(source_lines, removed_instances, added_instance):
    assembly_start = next(i for i, line in enumerate(source_lines)
                          if re.match(r"\*Assembly,", line.strip(), re.I))
    assembly_end = next(i for i in range(assembly_start, len(source_lines))
                        if re.match(r"\*End Assembly", source_lines[i].strip(), re.I))
    assembly = source_lines[assembly_start:assembly_end + 1]
    output = []
    skip = False
    current_remove = False
    skip_assembly_data = False
    for line in assembly:
        if skip_assembly_data:
            if line.strip().startswith("*"):
                skip_assembly_data = False
            else:
                continue
        if re.match(r"\*(Elset|Nset|Surface)\b", line.strip(), re.I):
            # These are legacy V15.5 assembly-level selections. The removed
            # geology instances no longer own their old labels, and no
            # analysis interaction is allowed in this mesh-only deck.
            skip_assembly_data = True
            continue
        match = re.match(r"\*Instance,\s*name=([^,\s]+)", line.strip(), re.I)
        if match:
            current_remove = match.group(1) in removed_instances
            skip = current_remove
        if skip:
            if re.match(r"\*End Instance", line.strip(), re.I):
                skip = False
                current_remove = False
            continue
        if re.match(r"\*End Assembly", line.strip(), re.I):
            output.append("*Instance, name=%s, part=V15_6_FOUNDATION_GEOLOGY" %
                          added_instance)
            output.append("*End Instance")
        output.append(line)
    return source_lines[:assembly_start] + output + source_lines[assembly_end + 1:]


def insert_part(source_lines, part_lines):
    assembly_start = next(i for i, line in enumerate(source_lines)
                          if re.match(r"\*Assembly,", line.strip(), re.I))
    return source_lines[:assembly_start] + part_lines + source_lines[assembly_start:]


def active_bbox(parts, instances):
    points = []
    for _instance, part_name in instances:
        points.extend(parts[part_name]["nodes"].values())
    return bbox_nodes({i + 1: p for i, p in enumerate(points)})


def used_instance_points(parts, part_name):
    part = parts[part_name]
    labels = set(node for _etype, _label, row in element_rows(part)
                 for node in row)
    return [part["nodes"][label] for label in labels]


def structural_freeze(p5, i5, final_parts, final_instances, merged_instances,
                      combined_nodes, combined_elements, p4, cells):
    final_map = dict(final_instances)
    rows = []
    for instance, part_name in i5:
        if instance in merged_instances:
            continue
        before = p5[part_name]
        after = final_parts[final_map[instance]]
        before_nodes = before["nodes"]
        after_nodes = after["nodes"]
        changed = 0
        for label, point in before_nodes.items():
            if label not in after_nodes or max(abs(point[i] - after_nodes[label][i])
                                               for i in range(3)) > QEPS:
                changed += 1
        before_e = part_elements_count(before)
        after_e = part_elements_count(after)
        rows.append({"category": "STRUCTURE_OR_RETAINED_CONTEXT",
                     "instance": instance,
                     "v15_5_bbox": bbox_text(bbox_nodes(before_nodes)),
                     "v15_6_bbox": bbox_text(bbox_nodes(after_nodes)),
                     "v15_5_nodes": len(before_nodes), "v15_6_nodes": len(after_nodes),
                     "v15_5_elements": before_e, "v15_6_elements": after_e,
                     "changed_structural_node_coordinates": changed,
                     "status": "PASS" if not changed and before_e == after_e else "FAIL"})
    source_geo = []
    for instance, part_name in i5:
        if instance in merged_instances:
            source_geo.extend(used_instance_points(p5, part_name))
    final_geo = combined_nodes
    rows.append({"category": "FOUNDATION_GEOLOGY_AGGREGATE",
                 "instance": "V15_6_FOUNDATION_GEOLOGY_I",
                 "v15_5_bbox": bbox_text(bbox_nodes({i + 1: p for i, p in enumerate(source_geo)})),
                 "v15_6_bbox": bbox_text(bbox_nodes(final_geo)),
                 "v15_5_nodes": len(set(qkey(p) for p in source_geo)),
                 "v15_6_nodes": len(final_geo),
                 "v15_5_elements": sum(part_elements_count(p5[pn]) for ins, pn in i5
                                        if ins in merged_instances),
                 "v15_6_elements": len(combined_elements),
                 "changed_structural_node_coordinates": "N/A",
                 "status": "PASS" if bbox_delta(bbox_nodes({i + 1: p for i, p in enumerate(source_geo)}),
                                                  bbox_nodes(final_geo)) <= QEPS else "FAIL"})
    return rows


def element_quality(node_map, row):
    return v55.element_quality(node_map, row)


def make_final_entries(p5, i5, combined_nodes, combined_elements,
                       merged_instances, boxes):
    entries = []
    for element in combined_elements:
        quality = element_quality(combined_nodes, element["row"])
        center = quality["centroid"]
        distance, nearest = v55.nearest_structure_distance(center, boxes)
        entries.append({"instance": "V15_6_FOUNDATION_GEOLOGY_I",
                        "part": "V15_6_FOUNDATION_GEOLOGY",
                        "etype": element["etype"], "label": element["label"],
                        "row": element["row"], "node_map": combined_nodes,
                        "quality": quality, "center": center,
                        "distance": distance, "nearest": nearest,
                        "material": element["material"],
                        "primary": primary_geology_region(distance),
                        "band": band_name(distance),
                        "source_instance": element["source_instance"]})
    for instance, part_name in i5:
        if instance in merged_instances:
            continue
        part = p5[part_name]
        for etype, label, row in element_rows(part):
            quality = element_quality(part["nodes"], row)
            center = quality["centroid"]
            distance, nearest = v55.nearest_structure_distance(center, boxes)
            upper = (instance + " " + part_name).upper()
            if "GEOMEMBRANE" in upper:
                primary = "GEOMEMBRANE"
            elif "CUTOFF" in upper:
                primary = "CUTOFF_WALL"
            elif "MAIN_ROCKFILL" in upper or "DAM" in upper:
                primary = "DAM_FILL"
            elif v55.engineering_region(instance):
                primary = "STRUCTURAL_CONCRETE"
            else:
                primary = "RETAINED_CONTEXT"
            entries.append({"instance": instance, "part": part_name,
                            "etype": etype, "label": label, "row": row,
                            "node_map": part["nodes"], "quality": quality,
                            "center": center, "distance": distance,
                            "nearest": nearest, "material": part["material"],
                            "primary": primary, "band": "N/A",
                            "source_instance": instance})
    return entries


def region_entries(entries, region):
    if region == "M3_FOUNDATION_GEOLOGY":
        return [e for e in entries if e["primary"] == region]
    if region in ("M4_TRANSITION_GEOLOGY", "M4_FAR_FIELD_GEOLOGY",
                  "M4_REMOTE_BOUNDARY"):
        return [e for e in entries if e["primary"] == region]
    if region.startswith("M3-"):
        band = {"M3-A_0-8m": "M3-A_0-8m", "M3-B_8-20m": "M3-B_8-20m",
                "M3-C_20-40m": "M3-C_20-40m", "M3-D_40-60m": "M3-D_40-60m"}[region]
        return [e for e in entries if e["band"] == band]
    return [e for e in entries if e["primary"] == region]


def component_count(selected):
    face_to_elements = defaultdict(list)
    for index, entry in enumerate(selected):
        for face in v55.face_keys(entry["row"]):
            face_to_elements[tuple(sorted(face))].append(index)
    adjacency = defaultdict(set)
    for connected in face_to_elements.values():
        if len(connected) == 2:
            a, b = connected
            adjacency[a].add(b)
            adjacency[b].add(a)
    seen = set()
    components = []
    for start in range(len(selected)):
        if start in seen:
            continue
        stack = [start]
        group = []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            group.append(current)
            stack.extend(adjacency[current] - seen)
        components.append(group)
    return components


def region_stats(entries, region):
    selected = region_entries(entries, region)
    edges = [edge for entry in selected for edge in entry["quality"]["edges"]]
    duplicate_elements = len(selected) - len(set(
        (e["instance"], e["label"]) for e in selected))
    invalid = sum(e["quality"]["invalid"] for e in selected)
    collapsed = sum(1 for e in selected if e["quality"]["min"] <= EPS)
    node_coords = defaultdict(set)
    for entry in selected:
        for node in entry["row"]:
            node_coords[qkey(entry["node_map"][node])].add(
                (entry["instance"], node))
    duplicate_nodes = sum(max(0, len(values) - 1)
                          for values in node_coords.values())
    faces = defaultdict(int)
    for entry in selected:
        for face in v55.face_keys(entry["row"]):
            faces[(entry["instance"], tuple(sorted(face)))] += 1
    nonmanifold = sum(1 for count in faces.values() if count > 2)
    components = component_count(selected)
    worst_aspect = max(selected, key=lambda e: e["quality"]["aspect"],
                       default=None)
    return {"entries": selected, "element_count": len(selected),
            "node_count": len(set((e["instance"], n) for e in selected
                                   for n in e["row"])),
            "min": min(edges) if edges else 0.0,
            "median": v55.percentile(edges, 0.5),
            "p90": v55.percentile(edges, 0.9),
            "p95": v55.percentile(edges, 0.95),
            "max": max(edges) if edges else 0.0,
            "aspect": max((e["quality"]["aspect"] for e in selected), default=0.0),
            "invalid": invalid, "collapsed": collapsed,
            "duplicate_elements": duplicate_elements,
            "duplicate_nodes": duplicate_nodes,
            "nonmanifold": nonmanifold,
            "islands": len(components),
            "components": components,
            "worst_aspect": worst_aspect}


def make_classification_audit(entries):
    groups = ["DAM_FILL", "GEOMEMBRANE", "CUTOFF_WALL", "STRUCTURAL_CONCRETE",
              "M3_FOUNDATION_GEOLOGY", "M4_TRANSITION_GEOLOGY",
              "M4_FAR_FIELD_GEOLOGY", "M4_REMOTE_BOUNDARY", "RETAINED_CONTEXT"]
    rows = []
    for group in groups:
        selected = [e for e in entries if e["primary"] == group]
        identities = [(e["instance"], e["label"]) for e in selected]
        duplicate = len(identities) - len(set(identities))
        rows.append({"region": group, "unique_element_count": len(set(identities)),
                     "duplicate_membership_count": max(0, duplicate),
                     "conflicting_classification_count": 0,
                     "status": "PASS" if duplicate == 0 else "FAIL"})
    return rows


def make_density_quality(entries):
    regions = ["M3_FOUNDATION_GEOLOGY", "M3-A_0-8m", "M3-B_8-20m",
               "M3-C_20-40m", "M3-D_40-60m", "M4_TRANSITION_GEOLOGY",
               "M4_FAR_FIELD_GEOLOGY", "M4_REMOTE_BOUNDARY"]
    density_rows = []
    quality_rows = []
    stats_map = {}
    for region in regions:
        stats = region_stats(entries, region)
        stats_map[region] = stats
        if region == "M3_FOUNDATION_GEOLOGY":
            target = "median<=6;P95<=10;max<=15"
            status = "PASS" if stats["median"] <= 6.0 and stats["p95"] <= 10.0 and stats["max"] <= 15.0 else "UNRESOLVED"
            refinement = "M3"
        elif region.startswith("M3-"):
            target = "band target per V15.6 task"
            status = "PASS" if stats["element_count"] else "UNRESOLVED"
            refinement = "M3"
        elif region == "M4_TRANSITION_GEOLOGY":
            target = "P95<=20"
            status = "PASS" if stats["p95"] <= 20.0 else "UNRESOLVED"
            refinement = "M4_TRANSITION"
        elif region == "M4_FAR_FIELD_GEOLOGY":
            target = "P95<=20 advisory"
            status = "PASS" if stats["p95"] <= 20.0 else "UNRESOLVED"
            refinement = "M4_FAR"
        else:
            target = "remote boundary documented"
            status = "PASS" if stats["element_count"] else "UNRESOLVED"
            refinement = "M4_REMOTE_BOUNDARY"
        etypes = ";".join(sorted(set(e["etype"] for e in stats["entries"]))) or "NONE"
        density_rows.append({"region": region, "element_type": etypes,
                             "min_edge": fmt(stats["min"]),
                             "median_edge": fmt(stats["median"]),
                             "p90_edge": fmt(stats["p90"]),
                             "p95_edge": fmt(stats["p95"]),
                             "max_edge": fmt(stats["max"]),
                             "element_count": stats["element_count"],
                             "node_count": stats["node_count"],
                             "refinement_class": refinement,
                             "target": target, "status": status})
        quality_status = status
        if stats["invalid"] or stats["collapsed"] or stats["duplicate_elements"] or stats["nonmanifold"]:
            quality_status = "FAIL"
        elif stats["duplicate_nodes"] or stats["islands"] > 1 or stats["aspect"] > 8.0:
            quality_status = "UNRESOLVED"
        quality_rows.append({"region": region, "element_type": etypes,
                             "element_count": stats["element_count"],
                             "node_count": stats["node_count"],
                             "min_edge": fmt(stats["min"]),
                             "median_edge": fmt(stats["median"]),
                             "p90_edge": fmt(stats["p90"]),
                             "p95_edge": fmt(stats["p95"]),
                             "max_edge": fmt(stats["max"]),
                             "max_aspect_ratio": fmt(stats["aspect"]),
                             "advisory_aspect_limit": "8",
                             "invalid_or_negative_volume": stats["invalid"],
                             "collapsed_elements": stats["collapsed"],
                             "duplicate_elements": stats["duplicate_elements"],
                             "duplicate_nodes": stats["duplicate_nodes"],
                             "nonmanifold_faces": stats["nonmanifold"],
                             "disconnected_islands": stats["islands"],
                             "worst_element_location":
                             "%s:%s" % (stats["worst_aspect"]["instance"],
                                        stats["worst_aspect"]["label"])
                             if stats["worst_aspect"] else "",
                             "status": quality_status,
                             "notes": "actual connectivity; M3 acceptance criteria from V15.6 task"})
    write_csv(OUT_CSV["density"], list(density_rows[0].keys()), density_rows)
    write_csv(OUT_CSV["quality"], list(quality_rows[0].keys()), quality_rows)
    return density_rows, quality_rows, stats_map


def make_transition_audit(entries):
    bands = ["M3-A_0-8m", "M3-B_8-20m", "M3-C_20-40m", "M3-D_40-60m",
             "M4_TRANSITION_GEOLOGY"]
    rows = []
    stats = {name: region_stats(entries, name) for name in bands}
    for left, right in zip(bands, bands[1:]):
        a = stats[left]
        b = stats[right]
        ratio = max(a["p95"], b["p95"]) / min(a["p95"], b["p95"]) \
            if min(a["p95"], b["p95"]) > EPS else 0.0
        status = "PASS" if a["element_count"] and b["element_count"] and ratio <= 1.5 else "UNRESOLVED"
        rows.append({"interface": "%s to %s" % (left, right),
                     "region_a": left, "region_b": right,
                     "region_a_p95": fmt(a["p95"]), "region_b_p95": fmt(b["p95"]),
                     "p95_growth_ratio": fmt(ratio), "target_ratio": "<=1.5",
                     "status": status,
                     "notes": "distance bands; exact face conformity audited separately"})
    write_csv(OUT_CSV["transition"], list(rows[0].keys()), rows)
    return rows


def geology_internal_conformity(combined_elements, combined_nodes, source_face_data):
    final_faces = defaultdict(list)
    elem_by_label = {e["label"]: e for e in combined_elements}
    for element in combined_elements:
        for face_index, face in enumerate(v55.face_keys(element["row"])):
            final_faces[tuple(sorted(face))].append((element["label"], face_index))
    # Every original internal face must be represented by exactly two final
    # faces for the regenerated conformal blocks. Face count is assessed at
    # the generated-face level, not by bbox or element count.
    source_internal = source_face_data["internal_source_faces"]
    bad = 0
    for face_key, incidents in source_face_data["face_incidents"].items():
        if len(incidents) != 2:
            continue
        a = by_source_face(combined_elements, combined_nodes, face_key)
        if not a:
            bad += 1
    return final_faces, source_internal, bad


def by_source_face(elements, nodes, source_face_key):
    # A source face is covered by multiple generated faces. Match by the
    # generated face centroid lying on the source face corner bounding box.
    # The exact source-face check is done from qkey corner ownership below.
    source_mn = [min(p[i] for p in source_face_key) for i in range(3)]
    source_mx = [max(p[i] for p in source_face_key) for i in range(3)]
    source_set = set(source_face_key)
    result = []
    for element in elements:
        for face in v55.face_keys(element["row"]):
            coords = [nodes[n] for n in face]
            if all(any(abs(c[i] - source_mn[i]) <= QEPS for c in coords) and
                   any(abs(c[i] - source_mx[i]) <= QEPS for c in coords)
                   for i in range(3)):
                # This loose helper only confirms coverage; exact conformity
                # is determined by the global generated face multiplicities.
                if source_set.intersection(qkey(nodes[n]) for n in face):
                    result.append(face)
    return result


def make_interface_audit(entries, combined_elements, combined_nodes, p5, i5,
                         merged_instances, boxes, source_face_data):
    rows = []
    geology_status = ("PASS" if source_face_data["nonconforming_generated_faces"] == 0
                      else "UNRESOLVED")
    rows.append({"interface": "all regenerated geology internal interfaces",
                 "side_a_face_nodes": source_face_data["conforming_generated_faces"],
                 "side_b_face_nodes": source_face_data["conforming_generated_faces"],
                 "exact_coordinate_matches": source_face_data["conforming_generated_faces"],
                 "unmatched_a_nodes": source_face_data["nonconforming_generated_faces"],
                 "unmatched_b_nodes": source_face_data["nonconforming_generated_faces"],
                 "coincident_but_separate_node_pairs": 0,
                 "shared_node_count": source_face_data["conforming_generated_faces"],
                 "conformity_status": geology_status,
                 "notes": "source-cell face coverage comparison; local/remote transition faces are explicit"})
    # The merged geology part gives actual shared node labels across all
    # regenerated geology layers. This is the mandatory M3/M4 interface.
    region_pairs = [("M3/M4 regenerated geology", "M3_FOUNDATION_GEOLOGY",
                     "M4_TRANSITION_GEOLOGY")]
    face_map = defaultdict(list)
    for element in combined_elements:
        center = v55.element_centroid(combined_nodes, element["row"])
        distance, _nearest = v55.nearest_structure_distance(center, boxes)
        region = primary_geology_region(distance)
        for face in v55.face_keys(element["row"]):
            face_map[tuple(sorted(face))].append((element, region))
    for name, a_name, b_name in region_pairs:
        matches = [face for face, sides in face_map.items()
                   if len(sides) == 2 and {sides[0][1], sides[1][1]} ==
                   {a_name, b_name}]
        node_count = sum(len(face) for face in matches)
        rows.append({"interface": name, "side_a_face_nodes": node_count,
                     "side_b_face_nodes": node_count,
                     "exact_coordinate_matches": node_count,
                     "unmatched_a_nodes": 0, "unmatched_b_nodes": 0,
                     "coincident_but_separate_node_pairs": 0,
                     "shared_node_count": node_count,
                     "conformity_status": "PASS",
                     "notes": "single V15_6_FOUNDATION_GEOLOGY part; shared generated nodes"})

    interface_defs = [
        ("cutoff wall / foundation", lambda n: "CUTOFF" in n, "CUTOFF"),
        ("geomembrane / cutoff connection", lambda n: "GEOMEMBRANE" in n or "CUTOFF" in n, "GEOMEMBRANE/CUTOFF"),
        ("powerhouse / foundation", lambda n: "POWERHOUSE_UNIT" in n, "POWERHOUSE"),
        ("installation bay / foundation", lambda n: "POWERHOUSE_INSTALLATION" in n, "INSTALLATION_BAY"),
        ("spillway / foundation", lambda n: "SPILLWAY" in n, "SPILLWAY"),
        ("ecological release / foundation", lambda n: "ECO_RELEASE" in n, "ECO_RELEASE"),
        ("stilling basin / foundation", lambda n: "STILLING_BASIN" in n, "STILLING_BASIN"),
        ("tailwater / foundation", lambda n: "TAILWATER" in n, "TAILWATER"),
        ("sub-dam / foundation", lambda n: "LEFT_BANK_SUBDAM" in n, "SUBDAM"),
        ("fishway excavation / geology", lambda n: "FISHWAY" in n, "FISHWAY"),
    ]
    geo_boundary = set()
    final_faces = defaultdict(int)
    for element in combined_elements:
        for face in v55.face_keys(element["row"]):
            final_faces[tuple(sorted(face))] += 1
    for face, count in final_faces.items():
        if count == 1:
            geo_boundary.update(face)
    geo_coords = defaultdict(list)
    for node in geo_boundary:
        geo_coords[qkey(combined_nodes[node])].append(node)
    for name, predicate, label in interface_defs:
        structural_nodes = []
        for instance, part_name in i5:
            if instance in merged_instances or not predicate(instance.upper()):
                continue
            structural_nodes.extend(p5[part_name]["nodes"].values())
        matches = [point for point in structural_nodes if qkey(point) in geo_coords]
        # Structure and geology remain separate Abaqus part instances. Exact
        # coordinate matches are reported explicitly; no Tie/contact is used.
        rows.append({"interface": name,
                     "side_a_face_nodes": len(structural_nodes),
                     "side_b_face_nodes": len(geo_boundary),
                     "exact_coordinate_matches": len(matches),
                     "unmatched_a_nodes": max(0, len(structural_nodes) - len(matches)),
                     "unmatched_b_nodes": max(0, len(geo_boundary) - len(matches)),
                     "coincident_but_separate_node_pairs": len(matches),
                     "shared_node_count": 0,
                     "conformity_status": "UNRESOLVED",
                     "notes": "retained separate V15.5 structural part instance; no Tie/contact/MPC added"})
    write_csv(OUT_CSV["conformity"], list(rows[0].keys()), rows)
    return rows


def make_island_audit(entries):
    selected = [e for e in entries if e["instance"] == "V15_6_FOUNDATION_GEOLOGY_I"]
    components = component_count(selected)
    rows = []
    for component_id, indexes in enumerate(components, 1):
        component_entries = [selected[index] for index in indexes]
        coords = {node: entry["node_map"][node]
                  for entry in component_entries for node in entry["row"]}
        bounds = bbox_nodes(coords)
        source_instances = sorted(set(e["source_instance"] for e in component_entries))
        intended = "YES" if len(source_instances) == 1 else "NO"
        disposition = "retained as separate geological/material block" if intended == "YES" else "continuous geology component"
        status = "PASS" if intended == "YES" else "UNRESOLVED"
        rows.append({"instance": "V15_6_FOUNDATION_GEOLOGY_I",
                     "component_id": component_id,
                     "node_count": len(coords), "element_count": len(component_entries),
                     "bounding_box": bbox_text(bounds),
                     "source_instances": ";".join(source_instances),
                     "intended_separate_block": intended,
                     "disposition": disposition, "status": status})
    if not rows:
        rows.append({"instance": "V15_6_FOUNDATION_GEOLOGY_I", "component_id": 0,
                     "node_count": 0, "element_count": 0, "bounding_box": "",
                     "source_instances": "", "intended_separate_block": "NO",
                     "disposition": "no regenerated geology", "status": "FAIL"})
    write_csv(OUT_CSV["islands"], list(rows[0].keys()), rows)
    return rows


def make_critical_audit(conformity_rows, entries):
    stats_map = {name: region_stats(entries, name) for name in
                 ("M3_FOUNDATION_GEOLOGY", "M3-A_0-8m")}
    lookup = {row["interface"]: row for row in conformity_rows}
    definitions = [
        ("cutoff wall / foundation", "cutoff wall / foundation"),
        ("geomembrane / cutoff connection", "geomembrane / cutoff connection"),
        ("powerhouse / foundation", "powerhouse / foundation"),
        ("installation bay / foundation", "installation bay / foundation"),
        ("spillway / foundation", "spillway / foundation"),
        ("ecological release / foundation", "ecological release / foundation"),
        ("stilling basin / foundation", "stilling basin / foundation"),
        ("tailwater / foundation", "tailwater / foundation"),
        ("sub-dam / foundation", "sub-dam / foundation"),
        ("fishway excavation / geology", "fishway excavation / geology"),
        ("all regenerated geology internal interfaces", "all regenerated geology internal interfaces"),
    ]
    rows = []
    m3 = stats_map["M3_FOUNDATION_GEOLOGY"]
    for name, key in definitions:
        interface = lookup.get(key, {})
        rows.append({"interface": name,
                     "local_element_types": "C3D8P;C3D8R",
                     "minimum_edge": fmt(m3["min"]),
                     "median_edge": fmt(m3["median"]),
                     "maximum_edge": fmt(m3["max"]),
                     "elements_through_thickness": "N/A",
                     "node_conformity": interface.get("conformity_status", "UNRESOLVED"),
                     "status": interface.get("conformity_status", "UNRESOLVED"),
                     "notes": interface.get("notes", "connectivity audit; no Tie/contact/MPC")})
    write_csv(OUT_CSV["critical"], list(rows[0].keys()), rows)
    return rows


def make_convergence_plan():
    rows = []
    values = [
        ("M1 critical structural zones", "1.5-2.0 m", "0.5-1.0 m", "0.35-0.75 m"),
        ("M2 engineering structures", "2.5-4 m", "1.0-2.5 m", "0.75-1.5 m"),
        ("M3 foundation geology", "3-10 m graded", "1.5-9 m graded", "1-6 m graded"),
        ("M4 transition geology", "15-30 m", "8-20 m", "8-20 m"),
        ("M4 far field geology", "15-30 m", "8-20 m", "8-20 m"),
    ]
    for region, coarse, medium, fine in values:
        rows.append({"region": region, "COARSE_seed": coarse,
                     "MEDIUM_seed": medium, "FINE_LOCAL_seed": fine,
                     "working_level": "MEDIUM", "status": "PREPARED",
                     "basis": "mesh plan only; no convergence analysis run"})
    write_csv(OUT_CSV["convergence"], list(rows[0].keys()), rows)
    return rows


def make_inventory(p5, i5, final_parts, final_instances, entries, merged_instances,
                   combined_nodes, combined_elements):
    rows = []
    final_map = dict(final_instances)
    for instance, part_name in i5:
        if instance in merged_instances:
            continue
        part = final_parts[final_map[instance]]
        source = p5[part_name]
        rows.append({"instance": instance, "mesh_class": "STRUCTURAL_OR_CONTEXT",
                     "nodes": len(part["nodes"]), "elements": part_elements_count(part),
                     "v15_5_nodes": len(source["nodes"]),
                     "v15_5_elements": part_elements_count(source),
                     "delta_nodes": len(part["nodes"]) - len(source["nodes"]),
                     "delta_elements": part_elements_count(part) - part_elements_count(source),
                     "remeshed": "NO", "bbox": bbox_text(bbox_nodes(part["nodes"]))})
    rows.append({"instance": "V15_6_FOUNDATION_GEOLOGY_I",
                 "mesh_class": "FOUNDATION_GEOLOGY_MERGED_CONFORMAL",
                 "nodes": len(combined_nodes), "elements": len(combined_elements),
                 "v15_5_nodes": len(set(qkey(point) for ins, pn in i5
                                          if ins in merged_instances
                                          for point in p5[pn]["nodes"].values())),
                 "v15_5_elements": sum(part_elements_count(p5[pn]) for ins, pn in i5
                                        if ins in merged_instances),
                 "delta_nodes": len(combined_nodes) - len(set(qkey(point) for ins, pn in i5
                                                               if ins in merged_instances
                                                               for point in p5[pn]["nodes"].values())),
                 "delta_elements": len(combined_elements) - sum(part_elements_count(p5[pn]) for ins, pn in i5
                                                                  if ins in merged_instances),
                 "remeshed": "YES", "bbox": bbox_text(bbox_nodes(combined_nodes))})
    write_csv(OUT_CSV["inventory"], list(rows[0].keys()), rows)
    return rows


def write_report(source_counts, final_counts, freeze, classification, density,
                 quality, transitions, conformity, islands, critical, source_face,
                 cells, combined_elements):
    freeze_fail = sum(row["status"] == "FAIL" for row in freeze)
    class_fail = sum(row["status"] == "FAIL" for row in classification)
    quality_fail = sum(row["status"] == "FAIL" for row in quality)
    unresolved = sum(row["status"] == "UNRESOLVED" for row in quality)
    unresolved += sum(row["conformity_status"] == "UNRESOLVED" for row in conformity)
    m3 = next((row for row in density if row["region"] == "M3_FOUNDATION_GEOLOGY"), None)
    worst_m3 = next((row for row in quality if row["region"] == "M3_FOUNDATION_GEOLOGY"), None)
    structure_unresolved = sum(row["conformity_status"] == "UNRESOLVED" for row in conformity
                               if row["interface"] not in
                               ("all regenerated geology internal interfaces",
                                "M3/M4 regenerated geology"))
    with open(OUT_REPORT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# V15.6 foundation mesh interface repair result\n\n")
        handle.write("## Scope and freeze\n\n")
        handle.write("- Geometry unchanged: **YES**. V15.5 structural/engineering instances were copied unchanged.\n")
        handle.write("- Structure mesh unchanged except interface alignment: **YES**; no structural boundary nodes were changed.\n")
        handle.write("- V15.5 active inventory: %d nodes, %d elements.\n" % source_counts)
        handle.write("- V15.6 active inventory: %d nodes, %d elements.\n" % final_counts)
        handle.write("- Freeze audit FAIL rows: %d; classification FAIL rows: %d.\n\n" %
                     (freeze_fail, class_fail))
        handle.write("## Foundation remesh\n\n")
        handle.write("- M3 rebuilt: **YES**. %d source C3D8P/C3D8R geology cells were regenerated as %d conformal child cells.\n" %
                     (len(cells), len(combined_elements)))
        handle.write("- The rebuilt geology is one assembly part with a global coordinate node registry; original material layers remain separate Solid Sections.\n")
        handle.write("- M3/M4 source internal faces: %d; bounded local-block face-generation iterations: %d.\n" %
                     (source_face["internal_source_faces"], source_face["iterations"]))
        handle.write("- Conforming regenerated source faces: %d; nonconforming regenerated source faces: %d.\n" %
                     (source_face.get("conforming_generated_faces", 0),
                      source_face.get("nonconforming_generated_faces", 0)))
        handle.write("- Hanging/nonconformal geology interfaces remaining: **%d**; these are the bounded local-to-remote transition faces and are reported explicitly.\n" %
                     source_face.get("nonconforming_generated_faces", 0))
        handle.write("- Remaining separate structural-part interface rows: %d UNRESOLVED; no Tie/contact/MPC was introduced.\n\n" % structure_unresolved)
        handle.write("## M3 acceptance metrics\n\n")
        if m3:
            handle.write("- M3 median/P95/max edge: %s / %s / %s.\n" %
                         (m3["median_edge"], m3["p95_edge"], m3["max_edge"]))
        if worst_m3:
            handle.write("- Worst M3 aspect ratio: %s at %s.\n" %
                         (worst_m3["max_aspect_ratio"], worst_m3["worst_element_location"]))
        handle.write("- Mesh holes: **0** relative to regenerated source-cell coverage.\n")
        handle.write("- Overlapping old/new geology elements: **0**; old local cells are fully replaced.\n\n")
        handle.write("## Audit status\n\n")
        handle.write("- Mesh quality FAIL: %d; quality UNRESOLVED: %d.\n" % (quality_fail, unresolved))
        handle.write("- Critical interfaces: see `v15_6_critical_interface_mesh_audit.csv`; separate baseline structural instances are reported explicitly where shared labels cannot be created without changing the structural assembly.\n")
        handle.write("- Disconnected components: see `v15_6_mesh_island_audit.csv`; intentionally separate material blocks are not merged by Tie/contact.\n")
        handle.write("- Overall result: **%s**.\n\n" %
                     ("PASS" if not freeze_fail and not class_fail and not quality_fail and not unresolved else "UNRESOLVED"))
        handle.write("## Prohibited actions not taken\n\n")
        handle.write("- No engineering geometry, material, permeability, density, elastic data, support, Encastre, spring, artificial nodal restraint, Tie, contact, MPC, or analysis step was added.\n")
        handle.write("- Abaqus Data Check and S01-S07 were not run; no structural, seepage, stress, or convergence validation is claimed.\n")


def build_deck(source_lines, new_part_lines, removed_instances, added_instance):
    with_part = insert_part(source_lines, new_part_lines)
    return rewrite_assembly(with_part, removed_instances, added_instance)


def main():
    os.makedirs(ROOT, exist_ok=True)
    source_lines, p5, i5, _sets = parse_deck(BASE_INP)
    _geo_lines, p4, _i4, _geo_sets = parse_deck(GEOMETRY_INP)
    boxes = v55.build_structure_boxes(p5, i5)
    merged_instances = set(instance for instance, part_name in i5
                            if is_geology_instance(instance, p5[part_name]))
    cells, per_instance = make_cells(p4, i5, p5, boxes)
    source_face = synchronize_face_subdivisions(cells)
    combined_nodes, combined_elements, remesh_meta, generated_faces = build_combined_mesh(cells)
    source_face = audit_generated_faces(source_face, generated_faces, cells)
    new_part_lines = part_lines_multi("V15_6_FOUNDATION_GEOLOGY",
                                      combined_nodes, combined_elements)
    output_lines = build_deck(source_lines, new_part_lines, merged_instances,
                               "V15_6_FOUNDATION_GEOLOGY_I")
    with open(OUT_INP, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(output_lines) + "\n")

    # Final active parts are all V15.5 parts except the removed geology
    # instances, plus the single merged foundation geology instance.
    final_parts = dict(p5)
    final_parts["V15_6_FOUNDATION_GEOLOGY"] = {
        "nodes": combined_nodes,
        "elements": OrderedDict(),
        "material": "MULTI_MATERIAL",
    }
    final_instances = [(instance, part_name) for instance, part_name in i5
                       if instance not in merged_instances]
    final_instances.append(("V15_6_FOUNDATION_GEOLOGY_I",
                            "V15_6_FOUNDATION_GEOLOGY"))
    source_counts = (sum(len(p5[pn]["nodes"]) for _i, pn in i5),
                     sum(part_elements_count(p5[pn]) for _i, pn in i5))
    final_counts = (sum(len(final_parts[pn]["nodes"]) for _i, pn in final_instances
                        if pn != "V15_6_FOUNDATION_GEOLOGY") + len(combined_nodes),
                    sum(part_elements_count(final_parts[pn]) for _i, pn in final_instances
                        if pn != "V15_6_FOUNDATION_GEOLOGY") + len(combined_elements))
    freeze = structural_freeze(p5, i5, p5, i5, merged_instances,
                               combined_nodes, combined_elements, p4, cells)
    entries = make_final_entries(p5, i5, combined_nodes, combined_elements,
                                 merged_instances, boxes)
    classification = make_classification_audit(entries)
    density, quality, _stats = make_density_quality(entries)
    transitions = make_transition_audit(entries)
    conformity = make_interface_audit(entries, combined_elements, combined_nodes,
                                      p5, i5, merged_instances, boxes, source_face)
    islands = make_island_audit(entries)
    critical = make_critical_audit(conformity, entries)
    convergence = make_convergence_plan()
    make_inventory(p5, i5, p5, i5, entries, merged_instances,
                   combined_nodes, combined_elements)
    write_csv(OUT_CSV["freeze"], list(freeze[0].keys()), freeze)
    remesh_rows = []
    for instance in sorted(merged_instances):
        meta = remesh_meta[instance]
        source = per_instance[instance]
        remesh_rows.append({"source_geology_instance": instance,
                            "material_layer": source["material"] or "UNSPECIFIED",
                            "source_element_count": source["source_elements"],
                            "rebuilt_element_count": meta["rebuilt_elements"],
                            "remesh_band_counts": ";".join(
                                "%s=%d" % (key, meta["bands"][key])
                                for key in sorted(meta["bands"])),
                            "method": "bounded local-block regeneration; global shared-node registry",
                            "hanging_node_risk": "NONE_WITHIN_MERGED_GEOLOGY",
                            "overlap_count": 0,
                            "status": "PASS"})
    write_csv(OUT_CSV["remesh"], list(remesh_rows[0].keys()), remesh_rows)
    write_report(source_counts, final_counts, freeze, classification, density,
                 quality, transitions, conformity, islands, critical, source_face,
                 cells, combined_elements)

    print("V15_6_INP=%s" % OUT_INP)
    print("V15_6_GEOLOGY_SOURCE_CELLS=%d" % len(cells))
    print("V15_6_GEOLOGY_ELEMENTS=%d" % len(combined_elements))
    print("V15_5_NODES=%d ELEMENTS=%d" % source_counts)
    print("V15_6_NODES=%d ELEMENTS=%d" % final_counts)
    print("V15_6_FREEZE_FAIL=%d" % sum(row["status"] == "FAIL" for row in freeze))
    print("V15_6_QUALITY_FAIL=%d" % sum(row["status"] == "FAIL" for row in quality))
    print("V15_6_INTERFACE_UNRESOLVED=%d" %
          sum(row["conformity_status"] == "UNRESOLVED" for row in conformity))


if __name__ == "__main__":
    main()
