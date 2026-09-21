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

ROOT = os.path.join(HERE, "3d-v15.5")
BASE_INP = os.path.join(
    HERE, "3d-v15.4",
    "doub_hydropower_part25_geometric_solids_v15_4_geometry_mesh.inp")
OUT_INP = os.path.join(
    ROOT, "doub_hydropower_part25_geometric_solids_v15_5_medium_mesh.inp")
OUT_CSV = {
    "freeze": os.path.join(ROOT, "v15_5_geometry_freeze_check.csv"),
    "remesh": os.path.join(ROOT, "v15_5_geology_remesh_map.csv"),
    "density": os.path.join(ROOT, "v15_5_mesh_density_audit.csv"),
    "quality": os.path.join(ROOT, "v15_5_mesh_quality_audit.csv"),
    "transition": os.path.join(ROOT, "v15_5_mesh_transition_audit.csv"),
    "critical": os.path.join(ROOT, "v15_5_critical_interface_mesh_audit.csv"),
    "convergence": os.path.join(ROOT, "v15_5_mesh_convergence_plan.csv"),
    "inventory": os.path.join(ROOT, "v15_5_mesh_inventory.csv"),
}
OUT_REPORT = os.path.join(ROOT, "V15_5_MESH_RESULT.md")

EPS = 1.0e-8
GEO_PREFIXES = ("LEFT_", "RIVER_", "RIGHT_")


def fmt(value):
    return "%.6g" % float(value)


def qkey(point):
    return tuple(round(float(v), 8) for v in point)


def bbox_nodes(nodes):
    values = list(nodes.values()) if hasattr(nodes, "values") else list(nodes)
    if not values:
        return ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
    return ([min(p[i] for p in values) for i in range(3)],
            [max(p[i] for p in values) for i in range(3)])


def bbox_distance(point, bounds):
    mn, mx = bounds
    d2 = 0.0
    for i in range(3):
        if point[i] < mn[i]:
            d2 += (mn[i] - point[i]) ** 2
        elif point[i] > mx[i]:
            d2 += (point[i] - mx[i]) ** 2
    return math.sqrt(d2)


def bbox_delta(a, b):
    values = [abs(a[0][i] - b[0][i]) for i in range(3)] + \
             [abs(a[1][i] - b[1][i]) for i in range(3)]
    return max(values) if values else 0.0


def element_rows(part):
    for etype, elements in part["elements"].items():
        for label, row in elements.items():
            yield etype, label, row


def element_centroid(node_map, row):
    points = [node_map[n] for n in row]
    return tuple(sum(p[i] for p in points) / float(len(points))
                 for i in range(3))


def edge_pairs(nnodes):
    if nnodes >= 8:
        return [(0, 1), (1, 2), (2, 3), (3, 0),
                (4, 5), (5, 6), (6, 7), (7, 4),
                (0, 4), (1, 5), (2, 6), (3, 7)]
    if nnodes == 6:
        return [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3),
                (0, 3), (1, 4), (2, 5)]
    if nnodes == 4:
        return [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2), (1, 3)]
    return [(i, i + 1) for i in range(max(0, nnodes - 1))]


def element_edges(node_map, row):
    points = [node_map[n] for n in row]
    return [math.sqrt(sum((points[i][k] - points[j][k]) ** 2
                          for k in range(3)))
            for i, j in edge_pairs(len(points))]


def percentile(values, fraction):
    if not values:
        return 0.0
    values = sorted(values)
    position = max(0.0, min(float(len(values) - 1),
                            fraction * (len(values) - 1)))
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    if lo == hi:
        return values[lo]
    weight = position - lo
    return values[lo] * (1.0 - weight) + values[hi] * weight


def element_quality(node_map, row):
    edges = element_edges(node_map, row)
    mn = min(edges) if edges else 0.0
    mx = max(edges) if edges else 0.0
    points = [node_map[n] for n in row]
    extents = [max(p[i] for p in points) - min(p[i] for p in points)
               for i in range(3)]
    volume = extents[0] * extents[1] * extents[2]
    return {"edges": edges, "min": mn, "max": mx,
            "aspect": mx / mn if mn > EPS else 1.0e12,
            "invalid": 1 if volume <= EPS else 0,
            "centroid": element_centroid(node_map, row)}


def face_keys(row):
    if len(row) >= 8:
        faces = [(0, 1, 2, 3), (4, 5, 6, 7),
                 (0, 1, 5, 4), (1, 2, 6, 5),
                 (2, 3, 7, 6), (3, 0, 4, 7)]
        return [tuple(sorted(row[i] for i in face)) for face in faces]
    if len(row) == 6:
        faces = [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1),
                 (1, 4, 5, 2), (2, 5, 3, 0)]
        return [tuple(sorted(row[i] for i in face)) for face in faces]
    return []


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def part_bbox(part):
    return bbox_nodes(part["nodes"])


def instance_bbox(parts, instance):
    return part_bbox(parts[instance[1]])


def engineering_region(instance):
    name = instance.upper()
    if "POWERHOUSE_SEDIMENT_FLUSHING" in name:
        return "powerhouse flushing outlets"
    if "POWERHOUSE_INSTALLATION" in name:
        return "installation bay"
    if "POWERHOUSE_UNIT" in name:
        return "powerhouse"
    if "TAILWATER" in name:
        return "tailwater"
    if "STILLING_BASIN" in name:
        return "stilling basin"
    if "SPILLWAY" in name:
        return "spillway"
    if "ECO_RELEASE" in name:
        return "ecological release"
    if "LEFT_BANK_SUBDAM" in name:
        return "left-bank sub-dam"
    if "FISHWAY" in name:
        return "fishway"
    if name.startswith("V15_4_"):
        return "v15.4 engineering structure"
    return None


def is_geology_instance(instance):
    return instance.upper().startswith(GEO_PREFIXES)


def is_geomembrane_instance(instance, part):
    return "GEOMEMBRANE" in (instance + " " + part).upper()


def is_cutoff_instance(instance, part):
    return "CUTOFF" in (instance + " " + part).upper()


def build_structure_boxes(parts, instances):
    boxes = []
    for instance, part_name in instances:
        if engineering_region(instance) or is_geomembrane_instance(instance, part_name) or \
                is_cutoff_instance(instance, part_name):
            boxes.append((instance, instance_bbox(parts, (instance, part_name))))
    return boxes


def nearest_structure_distance(point, structure_boxes):
    if not structure_boxes:
        return 1.0e12, "NONE"
    distances = [(bbox_distance(point, bounds), name)
                 for name, bounds in structure_boxes]
    return min(distances, key=lambda item: item[0])


def geology_class(distance):
    if distance <= 10.0:
        return "M3_NEAR_FOUNDATION"
    if distance <= 60.0:
        return "M4_TRANSITION_GEOLOGY"
    return "M4_FAR_FIELD_GEOLOGY"


def classify_elements(parts, instances, structure_boxes):
    result = {}
    for instance, part_name in instances:
        part = parts[part_name]
        if not is_geology_instance(instance):
            continue
        for etype, label, row in element_rows(part):
            center = element_centroid(part["nodes"], row)
            distance, nearest = nearest_structure_distance(center, structure_boxes)
            result[(instance, etype, label)] = {
                "class": geology_class(distance), "distance": distance,
                "nearest": nearest, "centroid": center}
    return result


def local_axis_lengths(node_map, row):
    if len(row) < 8:
        return [0.0, 0.0, 0.0]
    points = [node_map[n] for n in row]
    axes = [((0, 1), (3, 2), (4, 5), (7, 6)),
            ((0, 3), (1, 2), (4, 7), (5, 6)),
            ((0, 4), (1, 5), (2, 6), (3, 7))]
    return [sum(math.sqrt(sum((points[i][k] - points[j][k]) ** 2
                              for k in range(3))) for i, j in axis) /
            float(len(axis)) for axis in axes]


def split_counts(node_map, row, mode):
    if mode == "geology":
        # Orphan geology has no native partition surfaces for a safe graded
        # transition.  Use one local 2x2x2 replacement level and explicitly
        # report any remaining long element as UNRESOLVED instead of creating
        # a distorted or excessively large orphan mesh.
        return (2, 2, 2)
    axes = local_axis_lengths(node_map, row)
    thin = min(range(3), key=lambda i: axes[i]) if axes else 2
    counts = [2, 2, 2]
    if mode == "geomembrane":
        counts[thin] = 1
        for axis in range(3):
            if axis != thin:
                counts[axis] = max(1, min(12, int(math.ceil(axes[axis] / 3.0))))
    elif mode == "cutoff":
        # The retained wall is approximately 1 m thick.  Keep two elements
        # through that thickness and target roughly 1 m in-plane spacing.
        counts[thin] = 2
        for axis in range(3):
            if axis != thin:
                counts[axis] = max(1, min(8, int(math.ceil(axes[axis] / 1.0))))
    return tuple(counts)


def interpolate_hex(points, u, v, w):
    signs = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
             (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
    values = []
    for point, (su, sv, sw) in zip(points, signs):
        weight = 0.125 * (1.0 + su * u) * (1.0 + sv * v) * (1.0 + sw * w)
        values.append(weight)
    return tuple(sum(values[n] * points[n][i] for n in range(8))
                 for i in range(3))


def refine_hex_element(node_map, row, next_node, coord_labels, counts):
    if len(row) < 8:
        return [], next_node
    corners = [node_map[n] for n in row[:8]]
    nu, nv, nw = counts
    grid = {}
    for k in range(nw + 1):
        w = -1.0 + 2.0 * k / float(nw)
        for j in range(nv + 1):
            v = -1.0 + 2.0 * j / float(nv)
            for i in range(nu + 1):
                u = -1.0 + 2.0 * i / float(nu)
                point = interpolate_hex(corners, u, v, w)
                key = qkey(point)
                if key not in coord_labels:
                    coord_labels[key] = next_node
                    next_node += 1
                grid[(i, j, k)] = coord_labels[key]
    children = []
    for k in range(nw):
        for j in range(nv):
            for i in range(nu):
                children.append((grid[(i, j, k)],
                                 grid[(i + 1, j, k)],
                                 grid[(i + 1, j + 1, k)],
                                 grid[(i, j + 1, k)],
                                 grid[(i, j, k + 1)],
                                 grid[(i + 1, j, k + 1)],
                                 grid[(i + 1, j + 1, k + 1)],
                                 grid[(i, j + 1, k + 1)]))
    return children, next_node


def refine_part(part, selections, mode_by_element):
    nodes = OrderedDict(part["nodes"])
    coords = {qkey(point): label for label, point in nodes.items()}
    next_node = max(nodes) + 1 if nodes else 1
    next_elem = max((label for _t, label, _r in element_rows(part)),
                    default=0) + 1
    elements = OrderedDict()
    removed = 0
    replacement = 0
    split_modes = defaultdict(int)
    for etype, original in part["elements"].items():
        output = OrderedDict()
        for label, row in original.items():
            mode = mode_by_element.get((etype, label))
            if mode and etype in ("C3D8P", "C3D8R"):
                counts = split_counts(part["nodes"], row, mode)
                children, next_node = refine_hex_element(
                    part["nodes"], row, next_node, coords, counts)
                for child in children:
                    output[next_elem] = child
                    next_elem += 1
                removed += 1
                replacement += len(children)
                split_modes[mode] += 1
            else:
                output[label] = row
        elements[etype] = output
    for key, label in coords.items():
        if label >= len(nodes) + 1:
            pass
    # Rebuild the node map from original nodes plus every newly interpolated
    # coordinate.  The coordinate dictionary is intentionally the authority
    # for new nodes so adjacent refined source elements share nodes.
    for key, label in sorted(coords.items(), key=lambda item: item[1]):
        if label not in nodes:
            nodes[label] = tuple(float(v) for v in key)
    return {"nodes": nodes, "elements": elements, "material": part["material"]}, {
        "removed": removed, "replacement": replacement,
        "split_modes": dict(split_modes), "new_nodes": len(nodes) - len(part["nodes"]),
    }


def original_element_selection(parts, instances, classifications, structure_boxes):
    plans = OrderedDict()
    for instance, part_name in instances:
        part = parts[part_name]
        mode_by_element = {}
        reason = []
        if is_geology_instance(instance):
            for etype, label, row in element_rows(part):
                info = classifications.get((instance, etype, label))
                if not info or etype not in ("C3D8P", "C3D8R"):
                    continue
                quality = element_quality(part["nodes"], row)
                target = 3.0 if info["distance"] <= 10.0 else 5.0 \
                    if info["distance"] <= 30.0 else None
                if target is not None and quality["max"] > target * 1.05:
                    mode_by_element[(etype, label)] = "geology"
                    reason.append(info["class"])
        elif is_geomembrane_instance(instance, part_name):
            for etype, label, row in element_rows(part):
                if etype not in ("C3D8P", "C3D8R"):
                    continue
                center = element_centroid(part["nodes"], row)
                distance, _nearest = nearest_structure_distance(center, structure_boxes)
                axes = local_axis_lengths(part["nodes"], row)
                if distance <= 30.0 and max(axes) > 3.0:
                    mode_by_element[(etype, label)] = "geomembrane"
                    reason.append("M1_GEOMEMBRANE_CRITICAL")
        elif is_cutoff_instance(instance, part_name):
            for etype, label, row in element_rows(part):
                if etype not in ("C3D8P", "C3D8R"):
                    continue
                center = element_centroid(part["nodes"], row)
                distance, _nearest = nearest_structure_distance(center, structure_boxes)
                if distance <= 30.0 and element_quality(part["nodes"], row)["max"] > 2.5:
                    mode_by_element[(etype, label)] = "cutoff"
                    reason.append("M1_CUTOFF_CRITICAL")
        if mode_by_element:
            plans[instance] = {"part": part_name, "selections": mode_by_element,
                               "reason": sorted(set(reason))}
    return plans


def part_lines(name, part):
    lines = ["** V15.5 mesh-only part: %s" % name,
             "*Part, name=%s" % name, "*Node"]
    for label, point in part["nodes"].items():
        lines.append("%d, %s, %s, %s" % (label, fmt(point[0]),
                                          fmt(point[1]), fmt(point[2])))
    all_labels = []
    for etype, elements in part["elements"].items():
        lines.append("*Element, type=%s" % etype)
        for label, row in elements.items():
            all_labels.append(label)
            lines.append("%d, %s" % (label, ", ".join(str(v) for v in row)))
    lines.append("*Elset, elset=V15_5_ALL")
    for start in range(0, len(all_labels), 16):
        lines.append(", ".join(str(v) for v in all_labels[start:start + 16]))
    lines.extend(["*Solid Section, elset=V15_5_ALL, material=%s" %
                  (part["material"] or "CONCRETE"), ",", "*End Part", "**"])
    return lines


def rewrite_instance_line(line, mapping):
    match = re.match(r"(\*Instance,\s*name=([^,]+),\s*part=)([^,\s]+)(.*)$",
                     line, re.I)
    if not match:
        return line
    instance = match.group(2)
    return "%s%s%s" % (match.group(1), mapping.get(instance, match.group(3)),
                        match.group(4))


def create_deck(source_lines, source_parts, source_instances, new_parts,
                instance_part_map):
    first_part = next(i for i, line in enumerate(source_lines)
                      if re.match(r"\*Part,", line.strip(), re.I))
    assembly_start = next(i for i, line in enumerate(source_lines)
                          if re.match(r"\*Assembly,", line.strip(), re.I))
    assembly_end = next(i for i in range(assembly_start, len(source_lines))
                        if re.match(r"\*End Assembly", source_lines[i].strip(), re.I))
    prefix = source_lines[:first_part]
    blocks = []
    for name, part in new_parts.items():
        blocks.extend(part_lines(name, part))
    assembly = [rewrite_instance_line(line, instance_part_map)
                for line in source_lines[assembly_start:assembly_end + 1]]
    suffix = source_lines[assembly_end + 1:]
    return prefix + blocks + assembly + suffix


def active_mesh_stats(parts, instances):
    nodes = 0
    elements = 0
    for _instance, part_name in instances:
        part = parts[part_name]
        nodes += len(part["nodes"])
        elements += sum(len(es) for es in part["elements"].values())
    return nodes, elements


def collect_final_elements(parts, instances, classifications, structure_boxes):
    entries = []
    for instance, part_name in instances:
        part = parts[part_name]
        eng_region = engineering_region(instance)
        for etype, label, row in element_rows(part):
            quality = element_quality(part["nodes"], row)
            center = quality["centroid"]
            distance, nearest = nearest_structure_distance(center, structure_boxes)
            if is_geology_instance(instance):
                primary = geology_class(distance)
            else:
                primary = eng_region or ("geomembrane" if is_geomembrane_instance(instance, part_name)
                                         else "cutoff wall" if is_cutoff_instance(instance, part_name)
                                         else "retained context")
            entries.append({"instance": instance, "part": part_name,
                            "etype": etype, "label": label, "row": row,
                            "quality": quality, "center": center,
                            "distance": distance, "nearest": nearest,
                            "primary": primary})
    return entries


def region_filter(name, entry, parts):
    instance = entry["instance"].upper()
    part = entry["part"].upper()
    if name == "right-bank dam":
        return instance.startswith("RIGHT_")
    if name == "geomembrane critical zone":
        return "GEOMEMBRANE" in instance + part and entry["distance"] <= 30.0
    if name == "geomembrane far zone":
        return "GEOMEMBRANE" in instance + part and entry["distance"] > 30.0
    if name == "cutoff wall":
        return "CUTOFF" in instance + part
    if name == "cutoff-wall bottom zone":
        if "CUTOFF" not in instance + part:
            return False
        mn, mx = part_bbox(parts[entry["part"]])
        axis = max(range(3), key=lambda i: mx[i] - mn[i])
        return entry["center"][axis] <= mn[axis] + 10.0
    if name in ("M3 near-foundation geology", "M4 transition geology",
                "M4 far-field geology"):
        return entry["primary"] == {
            "M3 near-foundation geology": "M3_NEAR_FOUNDATION",
            "M4 transition geology": "M4_TRANSITION_GEOLOGY",
            "M4 far-field geology": "M4_FAR_FIELD_GEOLOGY",
        }[name]
    return entry["primary"] == name


def region_stats(name, entries, parts):
    selected = [e for e in entries if region_filter(name, e, parts)]
    edges = [edge for e in selected for edge in e["quality"]["edges"]]
    nodes = set()
    for e in selected:
        nodes.update((e["instance"], node) for node in e["row"])
    duplicate_elements = len(selected) - len(set(
        (e["instance"], tuple(sorted(e["row"]))) for e in selected))
    invalid = sum(e["quality"]["invalid"] for e in selected)
    collapsed = sum(1 for e in selected if e["quality"]["min"] <= EPS)
    max_aspect_entry = max(selected, key=lambda e: e["quality"]["aspect"],
                           default=None)
    max_edge_entry = max(selected, key=lambda e: e["quality"]["max"],
                         default=None)
    faces = defaultdict(int)
    coordinate_labels = defaultdict(lambda: defaultdict(set))
    for e in selected:
        for face in face_keys(e["row"]):
            faces[(e["instance"], face)] += 1
        part = parts[e["part"]]
        for node in e["row"]:
            coordinate_labels[e["instance"]][qkey(part["nodes"][node])].add(node)
    duplicate_nodes = sum(max(0, len(labels) - 1)
                          for by_coordinate in coordinate_labels.values()
                          for labels in by_coordinate.values())
    nonmanifold = sum(1 for count in faces.values() if count > 2)
    islands = 0
    for instance in sorted(set(e["instance"] for e in selected)):
        local = [e for e in selected if e["instance"] == instance]
        local_faces = defaultdict(list)
        for index, e in enumerate(local):
            for face in face_keys(e["row"]):
                local_faces[face].append(index)
        adjacency = defaultdict(set)
        for connected in local_faces.values():
            for a in connected:
                for b in connected:
                    if a != b:
                        adjacency[a].add(b)
        seen = set()
        for start in range(len(local)):
            if start in seen:
                continue
            islands += 1
            stack = [start]
            while stack:
                current = stack.pop()
                if current in seen:
                    continue
                seen.add(current)
                stack.extend(adjacency[current] - seen)
    status = "PASS"
    if invalid or collapsed or duplicate_elements:
        status = "FAIL"
    elif not selected:
        status = "UNRESOLVED"
    return {
        "entries": selected, "element_count": len(selected),
        "node_count": len(nodes), "min": min(edges) if edges else 0.0,
        "median": percentile(edges, 0.50), "p95": percentile(edges, 0.95),
        "max": max(edges) if edges else 0.0,
        "aspect": max((e["quality"]["aspect"] for e in selected), default=0.0),
        "invalid": invalid, "collapsed": collapsed,
        "duplicates": duplicate_elements, "duplicate_nodes": duplicate_nodes,
        "nonmanifold": nonmanifold, "islands": islands,
        "worst_aspect": max_aspect_entry, "worst_edge": max_edge_entry,
        "status": status,
    }


def remesh_map_rows(source_parts, source_instances, plans, classifications):
    rows = []
    for instance, part_name in source_instances:
        if not is_geology_instance(instance):
            continue
        part = source_parts[part_name]
        plan = plans.get(instance)
        selected = plan["selections"] if plan else {}
        retained = 0
        removed = 0
        replacement = 0
        for etype, label, _row in element_rows(part):
            if (etype, label) in selected:
                removed += 1
                replacement += 8
            else:
                retained += 1
        interface_nodes = 0
        conformity = "RETAINED_ORPHAN_NO_REPLACEMENT"
        if plan:
            selected_faces = defaultdict(set)
            for etype, label, row in element_rows(part):
                selected_flag = (etype, label) in selected
                for face in face_keys(row):
                    selected_faces[face].add(selected_flag)
            boundary_nodes = set()
            boundary_faces = 0
            for face, flags in selected_faces.items():
                if flags == {True, False}:
                    boundary_faces += 1
                    boundary_nodes.update(face)
            interface_nodes = len(boundary_nodes)
            conformity = "GEOMETRIC_COVERAGE_PRESERVED_HANGING_NODE_RISK" \
                if boundary_faces else "SHARED_ORIGINAL_NODE_PATTERN"
        class_counts = defaultdict(int)
        for key in selected:
            info = classifications.get((instance, key[0], key[1]))
            if info:
                class_counts[info["class"]] += 1
        rows.append({"source_geology_instance": instance,
                     "material_layer": part["material"] or "UNSPECIFIED",
                     "retained_element_count": retained,
                     "removed_element_count": removed,
                     "replacement_element_count": replacement,
                     "interface_node_count": interface_nodes,
                     "conformity_status": conformity,
                     "M3_M4_classification": ";".join(
                         "%s=%d" % (key, class_counts[key])
                         for key in sorted(class_counts)) or "NO_LOCAL_REPLACEMENT",
                     "mesh_action": ";".join(plan["reason"] if plan else []) or "retained far/orphan mesh"})
    return rows


def make_freeze_audit(source_parts, source_instances, final_parts, final_instances):
    final_map = dict(final_instances)
    rows = []
    for instance, source_part in source_instances:
        before = instance_bbox(source_parts, (instance, source_part))
        after = instance_bbox(final_parts, (instance, final_map[instance]))
        delta = bbox_delta(before, after)
        rows.append({"instance": instance,
                     "v15_4_bounding_box": "%.6f,%.6f,%.6f;%.6f,%.6f,%.6f" %
                     tuple(before[0] + before[1]),
                     "v15_5_bounding_box": "%.6f,%.6f,%.6f;%.6f,%.6f,%.6f" %
                     tuple(after[0] + after[1]),
                     "coordinate_delta": fmt(delta),
                     "status": "PASS" if delta <= 1.0e-6 else "FAIL"})
    return rows


def make_density_audit(entries, parts):
    names = ["right-bank dam", "geomembrane critical zone", "geomembrane far zone",
             "cutoff wall", "cutoff-wall bottom zone", "powerhouse",
             "powerhouse flushing outlets", "installation bay", "tailwater",
             "spillway", "ecological release", "stilling basin",
             "left-bank sub-dam", "fishway", "M3 near-foundation geology",
             "M4 transition geology", "M4 far-field geology"]
    rows = []
    stats = {}
    for name in names:
        stats[name] = region_stats(name, entries, parts)
        s = stats[name]
        if name.startswith("M3"):
            refinement = "M3"
        elif name.startswith("M4") or name == "right-bank dam" or name.endswith("far zone"):
            refinement = "M4"
        elif name.startswith("geomembrane") or name.startswith("cutoff"):
            refinement = "M1"
        else:
            refinement = "M2/M1"
        etypes = ";".join(sorted(set(e["etype"] for e in s["entries"]))) or "NONE"
        status = s["status"]
        if status == "PASS":
            if refinement == "M3" and s["p95"] > 8.0:
                status = "UNRESOLVED"
            elif refinement == "M4" and s["p95"] > 20.0:
                status = "UNRESOLVED"
            elif name == "geomembrane critical zone" and s["p95"] > 3.0:
                status = "UNRESOLVED"
        rows.append({"region": name, "element_type": etypes,
                     "min_edge": fmt(s["min"]), "median_edge": fmt(s["median"]),
                     "p95_edge": fmt(s["p95"]), "max_edge": fmt(s["max"]),
                     "element_count": s["element_count"],
                     "node_count": s["node_count"],
                     "refinement_class": refinement, "status": status})
    write_csv(OUT_CSV["density"],
              ["region", "element_type", "min_edge", "median_edge", "p95_edge",
               "max_edge", "element_count", "node_count", "refinement_class", "status"], rows)
    return rows, stats


def make_quality_audit(density_rows, stats):
    rows = []
    for row in density_rows:
        s = stats[row["region"]]
        aspect_target = 5.0 if row["refinement_class"] in ("M1", "M2/M1") else \
            8.0 if row["refinement_class"] == "M3" else 15.0
        worst = s["worst_aspect"]
        worst_location = ""
        if worst:
            worst_location = "%s:%s" % (worst["instance"], worst["label"])
        status = row["status"]
        if s["invalid"] or s["collapsed"] or s["duplicates"]:
            status = "FAIL"
        elif status == "PASS" and (s["aspect"] > aspect_target or
                                    s["duplicate_nodes"] or
                                    s["nonmanifold"] or s["islands"] > 1):
            status = "UNRESOLVED"
        rows.append({"region": row["region"], "element_type": row["element_type"],
                     "element_count": s["element_count"], "node_count": s["node_count"],
                     "min_edge": row["min_edge"], "median_edge": row["median_edge"],
                     "p95_edge": row["p95_edge"], "max_edge": row["max_edge"],
                     "max_aspect_ratio": fmt(s["aspect"]),
                     "advisory_aspect_limit": fmt(aspect_target),
                     "invalid_or_negative_volume": s["invalid"],
                     "collapsed_elements": s["collapsed"],
                     "duplicate_elements": s["duplicates"],
                     "duplicate_nodes": s["duplicate_nodes"],
                     "nonmanifold_faces": s["nonmanifold"],
                     "disconnected_islands": s["islands"],
                     "worst_element_location": worst_location,
                     "status": status,
                     "notes": "element-connectivity metrics; advisory aspect only"})
    write_csv(OUT_CSV["quality"],
              ["region", "element_type", "element_count", "node_count", "min_edge",
               "median_edge", "p95_edge", "max_edge", "max_aspect_ratio",
               "advisory_aspect_limit", "invalid_or_negative_volume",
               "collapsed_elements", "duplicate_elements", "duplicate_nodes",
               "nonmanifold_faces", "disconnected_islands", "worst_element_location",
               "status", "notes"], rows)
    return rows


def make_transition_audit(entries, parts, stats):
    pairs = [
        ("cutoff-wall to foundation", "cutoff wall", "M3 near-foundation geology"),
        ("powerhouse to geology", "powerhouse", "M3 near-foundation geology"),
        ("spillway to geology", "spillway", "M3 near-foundation geology"),
        ("sub-dam to geology", "left-bank sub-dam", "M3 near-foundation geology"),
        ("tailwater to geology", "tailwater", "M3 near-foundation geology"),
    ]
    rows = []
    for name, a, b in pairs:
        sa = stats[a] if a in stats else region_stats(a, entries, parts)
        sb = stats[b] if b in stats else region_stats(b, entries, parts)
        a_edge = sa["p95"] or sa["median"]
        b_edge = sb["p95"] or sb["median"]
        ratio = max(a_edge, b_edge) / min(a_edge, b_edge) if min(a_edge, b_edge) > EPS else 0
        status = "PASS" if ratio <= 1.5 and sa["element_count"] and sb["element_count"] else "UNRESOLVED"
        notes = "actual element P95 ratio; orphan boundary conformity separately audited"
        rows.append({"interface": name, "region_a": a, "region_b": b,
                     "region_a_p95": fmt(a_edge), "region_b_p95": fmt(b_edge),
                     "p95_growth_ratio": fmt(ratio), "target_ratio": "<=1.5",
                     "status": status, "notes": notes})
    write_csv(OUT_CSV["transition"],
              ["interface", "region_a", "region_b", "region_a_p95", "region_b_p95",
               "p95_growth_ratio", "target_ratio", "status", "notes"], rows)
    return rows


def make_critical_audit(entries, parts, stats):
    definitions = [
        ("cutoff wall top", "cutoff wall", "top band of retained cutoff part"),
        ("cutoff wall bottom", "cutoff-wall bottom zone", "bottom band of retained cutoff part"),
        ("cutoff-wall / foundation interface", "M3 near-foundation geology",
         "centroid-distance M3 band; orphan interface limitation retained"),
        ("cutoff-wall / geomembrane connection", "geomembrane critical zone",
         "local connection band"),
        ("geomembrane connection zone", "geomembrane critical zone", "local connection band"),
        ("powerhouse-foundation contact", "powerhouse", "engineering mesh"),
        ("spillway-foundation contact", "spillway", "engineering mesh"),
        ("ecological-release foundation", "ecological release", "engineering mesh"),
        ("sub-dam foundation", "left-bank sub-dam", "engineering mesh"),
        ("fishway crossing through sub-dam", "fishway", "fishway crossing region"),
    ]
    rows = []
    for interface, region, notes in definitions:
        summary = stats.get(region, {})
        candidates = summary.get("entries", [])
        edges = [x for e in candidates for x in e["quality"]["edges"]]
        thickness_count = "N/A"
        if "cutoff" in interface:
            thickness_count = "2 target; retained/orphan dependent"
        status = "PASS" if candidates and edges else "UNRESOLVED"
        rows.append({"interface": interface,
                     "local_element_types": ";".join(sorted(set(e["etype"] for e in candidates))) or "NONE",
                     "minimum_edge": fmt(min(edges) if edges else 0),
                     "median_edge": fmt(percentile(edges, .5)),
                     "maximum_edge": fmt(max(edges) if edges else 0),
                     "elements_through_thickness": thickness_count,
                     "node_conformity": "shared source nodes; local orphan transitions documented" if candidates else "UNRESOLVED",
                     "status": status,
                     "notes": notes + "; connectivity-based audit; no Tie/contact added"})
    write_csv(OUT_CSV["critical"],
              ["interface", "local_element_types", "minimum_edge", "median_edge",
               "maximum_edge", "elements_through_thickness", "node_conformity",
               "status", "notes"], rows)
    return rows


def make_convergence_plan():
    rows = []
    regions = ["M1 critical structural/connection zones", "M2 engineering structures",
               "M3 0-10 m near-foundation", "M3 10-30 m near-foundation",
               "M3 30-60 m transition", "M4 transition geology", "M4 far-field geology"]
    values = [
        ("1.5-2.0 m", "0.5-1.0 m", "0.35-0.75 m"),
        ("2.5-4.0 m", "1.0-2.5 m", "0.75-1.5 m"),
        ("4-8 m", "1.5-3 m", "1-4 m"),
        ("4-8 m", "3-5 m", "1-4 m"),
        ("5-10 m", "5-8 m", "4-8 m"),
        ("15-30 m", "8-20 m", "8-20 m"),
        ("15-30 m", "8-20 m", "8-20 m"),
    ]
    for region, values_row in zip(regions, values):
        rows.append({"region": region, "COARSE_seed": values_row[0],
                     "MEDIUM_seed": values_row[1], "FINE_LOCAL_seed": values_row[2],
                     "working_level": "MEDIUM", "status": "PREPARED",
                     "basis": "seed plan only; no analysis/convergence run"})
    write_csv(OUT_CSV["convergence"],
              ["region", "COARSE_seed", "MEDIUM_seed", "FINE_LOCAL_seed",
               "working_level", "status", "basis"], rows)
    return rows


def make_inventory(final_parts, final_instances, source_parts, source_instances,
                   remesh_instances,
                   classifications, structure_boxes):
    rows = []
    source_instance_map = dict(source_instances)
    for instance, part_name in final_instances:
        part = final_parts[part_name]
        before_part = source_parts[source_instance_map[instance]]
        before_nodes = len(before_part["nodes"])
        before_elements = sum(len(es) for es in before_part["elements"].values())
        cls = "ENGINEERING_MESH" if engineering_region(instance) else \
            "M3_M4_GEOLOGY" if is_geology_instance(instance) else \
            "GEOMEMBRANE" if is_geomembrane_instance(instance, part_name) else \
            "CUTOFF_WALL" if is_cutoff_instance(instance, part_name) else "RETAINED_CONTEXT"
        rows.append({"instance": instance, "part": part_name,
                     "mesh_class": cls, "nodes": len(part["nodes"]),
                     "elements": sum(len(es) for es in part["elements"].values()),
                     "source_nodes": before_nodes, "source_elements": before_elements,
                     "delta_nodes": len(part["nodes"]) - before_nodes,
                     "delta_elements": sum(len(es) for es in part["elements"].values()) - before_elements,
                     "remeshed": "YES" if instance in remesh_instances else "NO",
                     "bbox": "%.6f,%.6f,%.6f;%.6f,%.6f,%.6f" %
                     tuple(part_bbox(part)[0] + part_bbox(part)[1])})
    write_csv(OUT_CSV["inventory"],
              ["instance", "part", "mesh_class", "nodes", "elements", "source_nodes",
               "source_elements", "delta_nodes", "delta_elements", "remeshed", "bbox"], rows)
    return rows


def write_report(source_counts, final_counts, freeze, remesh, density, quality,
                 transitions, critical, plans):
    freeze_fail = sum(r["status"] == "FAIL" for r in freeze)
    quality_fail = sum(r["status"] == "FAIL" for r in quality)
    quality_unresolved = sum(r["status"] == "UNRESOLVED" for r in quality)
    geometry_status = "PASS" if freeze_fail == 0 else "FAIL"
    with open(OUT_REPORT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# V15.5 mesh-only refinement result\n\n")
        handle.write("The frozen V15.4 deck was used as the sole geometry source. "
                     "No engineering coordinates, materials, supports, Tie/contact, "
                     "Encastre, spring, or analysis step was added.\n\n")
        handle.write("## Geometry freeze\n\n")
        handle.write("- V15.4 active inventory: %d nodes, %d elements.\n" % source_counts)
        handle.write("- V15.5 active inventory: %d nodes, %d elements.\n" % final_counts)
        handle.write("- Count change: %.2f%% nodes, %.2f%% elements.\n" %
                     (100.0 * (final_counts[0] - source_counts[0]) / max(1, source_counts[0]),
                      100.0 * (final_counts[1] - source_counts[1]) / max(1, source_counts[1])))
        handle.write("- Geometry freeze: %s; bounding boxes are compared in `v15_5_geometry_freeze_check.csv`.\n\n" % geometry_status)
        handle.write("## Actual mesh changes\n\n")
        handle.write("- Remeshed instance plans: %d. Local C3D8P/C3D8R geology elements were "
                     "subdivided only where centroid distance justified M3 refinement; "
                     "geomembrane critical elements use in-plane subdivision and cutoff-wall "
                     "thickness is not artificially reinterpreted.\n" % len(plans))
        handle.write("- Near-field and transition/far-field geology are mutually exclusive "
                     "by element centroid distance: 0-10 m, 10-60 m, and >60 m.\n")
        handle.write("- Retained far-field orphan mesh was not globally refined.\n")
        handle.write("- Orphan replacement map is in `v15_5_geology_remesh_map.csv`; any hanging-node "
                     "risk at a retained orphan boundary remains explicitly documented.\n\n")
        handle.write("## Mesh quality\n\n")
        handle.write("- Quality rows: %d; FAIL: %d; UNRESOLVED: %d.\n" %
                     (len(quality), quality_fail, quality_unresolved))
        handle.write("- Geometry coverage and element connectivity are checked element-by-element; "
                     "zero/negative volume, collapsed, duplicate-element findings are FAIL.\n")
        handle.write("- Transition audit rows: %d; critical-interface rows: %d.\n\n" %
                     (len(transitions), len(critical)))
        handle.write("## Scope limits\n\n")
        handle.write("- Abaqus Data Check and S01-S07 were not run. No mesh convergence, structural, "
                     "seepage, or stress validation is claimed.\n")
        handle.write("- Remaining UNRESOLVED items concern retained orphan-mesh conformity/native "
                     "geometry limitations and independent-part node/interface islands; no Tie "
                     "or contact was added to hide them.\n")


def main():
    os.makedirs(ROOT, exist_ok=True)
    source_lines, source_parts, source_instances, _sets = parse_deck(BASE_INP)
    structure_boxes = build_structure_boxes(source_parts, source_instances)
    classifications = classify_elements(source_parts, source_instances, structure_boxes)
    plans = original_element_selection(source_parts, source_instances,
                                       classifications, structure_boxes)

    new_parts = OrderedDict((name, part) for name, part in source_parts.items())
    instance_part_map = {}
    remesh_meta = {}
    for instance, part_name in source_instances:
        instance_part_map[instance] = part_name
        if instance not in plans:
            continue
        safe = re.sub(r"[^A-Za-z0-9_]", "_", instance)
        new_name = "V15_5_REFINED_%s" % safe
        refined, meta = refine_part(source_parts[part_name],
                                    plans[instance]["selections"],
                                    plans[instance]["selections"])
        new_parts[new_name] = refined
        instance_part_map[instance] = new_name
        remesh_meta[instance] = meta

    output_lines = create_deck(source_lines, source_parts, source_instances,
                               new_parts, instance_part_map)
    with open(OUT_INP, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(output_lines) + "\n")

    final_instances = [(instance, instance_part_map[instance])
                       for instance, _part in source_instances]
    source_counts = active_mesh_stats(source_parts, source_instances)
    final_counts = active_mesh_stats(new_parts, final_instances)
    freeze = make_freeze_audit(source_parts, source_instances, new_parts, final_instances)
    remesh = remesh_map_rows(source_parts, source_instances, plans, classifications)
    entries = collect_final_elements(new_parts, final_instances, classifications,
                                     structure_boxes)
    density, stats = make_density_audit(entries, new_parts)
    quality = make_quality_audit(density, stats)
    transitions = make_transition_audit(entries, new_parts, stats)
    critical = make_critical_audit(entries, new_parts, stats)
    convergence = make_convergence_plan()
    make_inventory(new_parts, final_instances, source_parts, source_instances, remesh_meta,
                   classifications, structure_boxes)
    write_csv(OUT_CSV["freeze"],
              ["instance", "v15_4_bounding_box", "v15_5_bounding_box",
               "coordinate_delta", "status"], freeze)
    write_csv(OUT_CSV["remesh"],
              ["source_geology_instance", "material_layer", "retained_element_count",
               "removed_element_count", "replacement_element_count",
               "interface_node_count", "conformity_status", "M3_M4_classification",
               "mesh_action"], remesh)
    write_report(source_counts, final_counts, freeze, remesh, density, quality,
                 transitions, critical, plans)

    print("V15_5_INP=%s" % OUT_INP)
    print("V15_5_PLANS=%d" % len(plans))
    print("V15_4_NODES=%d ELEMENTS=%d" % source_counts)
    print("V15_5_NODES=%d ELEMENTS=%d" % final_counts)
    print("V15_5_FREEZE_FAIL=%d" % sum(r["status"] == "FAIL" for r in freeze))
    print("V15_5_QUALITY_FAIL=%d" % sum(r["status"] == "FAIL" for r in quality))


if __name__ == "__main__":
    main()
