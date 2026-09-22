"""V15.13 final seepage-domain rebuild and pre-Data-Check audit.

The V15.12 left-bank extension is deliberately not a baseline.  This script
starts from the V15.11 INP, reads every active instance placement from that
INP, derives Assembly coordinates, and writes evidence before any Data Check
can be considered.  Interface acceptance is based on mesh faces and convex
element intersection tests; bounding boxes are broad-phase filters only.

The script is intentionally gate-driven.  It does not manufacture PASS
values for missing anti-seepage segments, unsupported material mappings,
nonconforming topology, or structural-only geology inside the seepage domain.
If any critical gate is not PASS, Abaqus Data Check is not launched.
"""
from __future__ import print_function

import collections
import csv
import math
import os
import re
import shutil
import subprocess
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(HERE, "3d-v15.11")
OUT_DIR = os.path.join(HERE, "3d-v15.13")
BASE_INP = os.path.join(
    BASE_DIR,
    "doub_hydropower_part25_geometric_solids_v15_11_interface_backfill_fishway.inp")
BASE_CAE = os.path.join(
    BASE_DIR,
    "doub_hydropower_part25_geometric_solids_v15_11_interface_backfill_fishway.cae")
OUT_INP = os.path.join(
    OUT_DIR,
    "doub_hydropower_part25_geometric_solids_v15_13_final_seepage_rebuild.inp")
OUT_CAE = os.path.join(
    OUT_DIR,
    "doub_hydropower_part25_geometric_solids_v15_13_final_seepage_rebuild.cae")

sys.path.insert(0, HERE)
import repair_v12_3d as deck_parser
import audit_v15_12_real_assembly_validation as face_audit


FACE_MAP = face_audit.FACE_MAP
POROUS_TYPES = set(("C3D8P", "C3D6P", "C3D4P", "C3D10P"))
TOL = 1.0e-6
FACE_TOL = 1.0e-3


def ensure_out():
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)


def write_csv(name, fields, rows):
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def fmt(value):
    if value is None or value == "":
        return ""
    return "%.9f" % float(value)


def yesno(value):
    return "YES" if value else "NO"


def status_from(value):
    if value is True:
        return "PASS"
    if value is False:
        return "FAIL"
    return "UNRESOLVED"


def bbox_text(bb):
    if not bb:
        return ""
    return ";".join(",".join(fmt(v) for v in p) for p in bb)


def bbox_points(points):
    if not points:
        return None
    return (tuple(min(p[i] for p in points) for i in range(3)),
            tuple(max(p[i] for p in points) for i in range(3)))


def bbox_gap(a, b):
    if a is None or b is None:
        return float("inf")
    gap2 = 0.0
    for i in range(3):
        if a[1][i] < b[0][i]:
            gap2 += (b[0][i] - a[1][i]) ** 2
        elif b[1][i] < a[0][i]:
            gap2 += (a[0][i] - b[1][i]) ** 2
    return math.sqrt(gap2)


def positive_bbox_overlap(a, b, tol=1.0e-9):
    if a is None or b is None:
        return False
    return all(min(a[1][i], b[1][i]) - max(a[0][i], b[0][i]) > tol
               for i in range(3))


def parse_float_row(line):
    values = []
    for token in line.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            values.append(float(token))
        except Exception:
            return None
    return values


def parse_placements_from_lines(lines):
    placements = collections.OrderedDict()
    i = 0
    while i < len(lines):
        match = re.match(r"\*Instance,\s*name=([^,]+),\s*part=([^,]+)",
                         lines[i].strip(), re.I)
        if not match:
            i += 1
            continue
        name, part = match.group(1).strip(), match.group(2).strip()
        rows = []
        j = i + 1
        while j < len(lines) and not re.match(r"\*End Instance", lines[j].strip(), re.I):
            raw = lines[j].strip()
            if raw and not raw.startswith("*") and not raw.startswith("**"):
                parsed = parse_float_row(raw)
                if parsed is not None:
                    rows.append(parsed)
            j += 1
        placement = {
            "instance": name,
            "part": part,
            "translation": (0.0, 0.0, 0.0),
            "axis_point_1": "",
            "axis_point_2": "",
            "angle_deg": 0.0,
            "placement_rows": len(rows),
            "source": "INP *Instance placement: identity (no data rows)",
        }
        if rows and len(rows[0]) >= 3:
            placement["translation"] = tuple(rows[0][:3])
        if len(rows) >= 2 and len(rows[1]) >= 7:
            placement["axis_point_1"] = tuple(rows[1][:3])
            placement["axis_point_2"] = tuple(rows[1][3:6])
            placement["angle_deg"] = rows[1][6]
            placement["source"] = "INP *Instance translation + rotation rows"
        placements[name] = placement
        i = j + 1
    return placements


def vsub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def vadd(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def vmul(a, scale):
    return tuple(scale * a[i] for i in range(3))


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def norm(a):
    return math.sqrt(dot(a, a))


def rotate(vector, axis, angle):
    length = norm(axis)
    if length <= 1.0e-15 or abs(angle) <= 1.0e-15:
        return vector
    unit = vmul(axis, 1.0 / length)
    c, s = math.cos(angle), math.sin(angle)
    return vadd(vadd(vmul(vector, c), vmul(cross(unit, vector), s)),
                vmul(unit, dot(unit, vector) * (1.0 - c)))


def make_transform(placement):
    translation = placement["translation"]
    p1 = placement["axis_point_1"]
    p2 = placement["axis_point_2"]
    angle = float(placement["angle_deg"])
    if not p1 or not p2 or abs(angle) <= 1.0e-12:
        return lambda point: vadd(point, translation)
    # Abaqus writes these rows as the rotation applied to the part coordinates
    # followed by the instance translation.  The parsed axis/angle, rather
    # than an instance-name formula, is the only source of this transform.
    axis = vsub(p2, p1)
    radians = math.radians(angle)
    return lambda point: vadd(rotate(point, axis, radians), translation)


def canonical_point(point, tol=TOL):
    return tuple(int(round(float(v) / tol)) for v in point)


def canonical_face(points, tol=TOL):
    return tuple(sorted(canonical_point(p, tol) for p in points))


def phase_a_coordinate_chain(lines, parts, instances, placements, transforms):
    boxes = {}
    transform_rows = []
    inventory_rows = []
    for instance, part_name in instances:
        placement = placements.get(instance)
        part = parts[part_name]
        traceable = placement is not None and placement["source"].startswith("INP")
        bb = face_audit.part_node_bbox(part, transforms[instance]) if traceable else None
        boxes[instance] = bb
        element_count = sum(len(values) for values in part["elements"].values())
        transform_rows.append({
            "instance": instance,
            "part": part_name,
            "translation": ",".join(fmt(v) for v in placement["translation"]) if placement else "",
            "axis_point_1": ",".join(fmt(v) for v in placement["axis_point_1"]) if placement and placement["axis_point_1"] else "",
            "axis_point_2": ",".join(fmt(v) for v in placement["axis_point_2"]) if placement and placement["axis_point_2"] else "",
            "angle_deg": fmt(placement["angle_deg"]) if placement else "",
            "placement_rows": placement["placement_rows"] if placement else "",
            "transform_source": placement["source"] if placement else "MISSING_INP_INSTANCE",
            "global_bbox": bbox_text(bb),
            "node_count": len(part["nodes"]),
            "element_count": element_count,
            "element_types": ";".join(sorted(part["elements"])),
            "status": status_from(traceable and bb is not None),
        })
    for instance, part_name in instances:
        bb = boxes[instance]
        neighbors = sorted((bbox_gap(bb, boxes[other]), other)
                           for other, _ in instances if other != instance)
        inventory_rows.append({
            "instance": instance,
            "part": part_name,
            "role": face_audit.classify_role(instance, part_name),
            "global_bbox": bbox_text(bb),
            "centroid": ",".join(fmt((bb[0][i] + bb[1][i]) / 2.0) for i in range(3)) if bb else "",
            "nearest_named_neighbors": ";".join("%s (%.6f m)" % (pair[1], pair[0])
                                                 for pair in neighbors[:3]),
            "transformed_source": placements[instance]["source"],
            "status": status_from(bb is not None),
        })
    write_csv(
        "v15_13_instance_transform_audit.csv",
        ["instance", "part", "translation", "axis_point_1", "axis_point_2",
         "angle_deg", "placement_rows", "transform_source", "global_bbox",
         "node_count", "element_count", "element_types", "status"],
        transform_rows)
    write_csv(
        "v15_13_global_instance_inventory.csv",
        ["instance", "part", "role", "global_bbox", "centroid",
         "nearest_named_neighbors", "transformed_source", "status"],
        inventory_rows)
    critical_tokens = (
        "P25_SOLID_CUTOFF_WALL_F13-1",
        "V12_UPSTREAM_GEOMEMBRANE-1",
        "V15_4_LEFT_BANK_SUBDAM_I",
        "V15_4_POWERHOUSE_INSTALLATION_BAY_I",
        "V15_4_POWERHOUSE_UNIT_01_I",
        "V15_7_FOUNDATION_GEOLOGY_I",
        "V15_11_LEFT_COMPACTED_SAND_GRAVEL_I",
    )
    chain_rows = []
    for name in critical_tokens:
        row = next((item for item in inventory_rows if item["instance"] == name), None)
        if row:
            chain_rows.append({
                "chain_item": name,
                "instance": name,
                "global_bbox": row["global_bbox"],
                "transform_source": row["transformed_source"],
                "status": row["status"],
                "basis": "actual transformed node coordinates from active V15.11 INP",
            })
        else:
            chain_rows.append({
                "chain_item": name, "instance": name, "global_bbox": "",
                "transform_source": "MISSING_ACTIVE_INSTANCE", "status": "UNRESOLVED",
                "basis": "required chain item absent from active INP",
            })
    write_csv("v15_13_phase_a_coordinate_chain.csv",
              ["chain_item", "instance", "global_bbox", "transform_source", "status", "basis"],
              chain_rows)
    phase_a_status = all(item["status"] == "PASS" for item in transform_rows)
    return boxes, phase_a_status


def element_records(parts, instances, transforms, instance_name, filter_bb=None):
    part_name = dict(instances)[instance_name]
    part = parts[part_name]
    records = []
    for etype, elements in part["elements"].items():
        base = etype.upper()
        if base.startswith("C3D8"):
            npoints = 8
        elif base.startswith("C3D6"):
            npoints = 6
        else:
            continue
        for label, conn in elements.items():
            if len(conn) < npoints:
                continue
            points = tuple(transforms[instance_name](part["nodes"][node])
                           for node in conn[:npoints])
            bb = bbox_points(points)
            if filter_bb is not None and bbox_gap(bb, filter_bb) > FACE_TOL:
                continue
            records.append({"label": label, "etype": etype, "points": points, "bbox": bb})
    return records


def element_axes(points, etype):
    base = "C3D6" if etype.upper().startswith("C3D6") else "C3D8"
    indices = FACE_MAP[base]
    axes = []
    for _, face_indices in indices:
        if len(face_indices) < 3:
            continue
        a = points[face_indices[0]]
        b = points[face_indices[1]]
        c = points[face_indices[2]]
        axis = cross(vsub(b, a), vsub(c, a))
        if norm(axis) > 1.0e-12:
            axes.append(axis)
    edges = set()
    for _, face_indices in indices:
        for i in range(len(face_indices)):
            a, b = face_indices[i], face_indices[(i + 1) % len(face_indices)]
            edges.add(tuple(sorted((a, b))))
    for a, b in edges:
        edge = vsub(points[b], points[a])
        if norm(edge) > 1.0e-12:
            axes.append(edge)
    return axes


def convex_positive_overlap(a, b, tol=1.0e-8):
    """Separating-axis test for convex C3D6/C3D8 elements.

    The element geometry is used for the final indicator.  AABB overlap is
    only used before this function to bound the candidate pairs.
    """
    axes = element_axes(a["points"], a["etype"]) + element_axes(b["points"], b["etype"])
    axes_a = element_axes(a["points"], a["etype"])
    axes_b = element_axes(b["points"], b["etype"])
    for axis_a in axes_a:
        for axis_b in axes_b:
            axes.append(cross(axis_a, axis_b))
    for axis in axes:
        length = norm(axis)
        if length <= 1.0e-12:
            continue
        unit = vmul(axis, 1.0 / length)
        pa = [dot(point, unit) for point in a["points"]]
        pb = [dot(point, unit) for point in b["points"]]
        if max(pa) <= min(pb) + tol or max(pb) <= min(pa) + tol:
            return False
    return True


def interpenetrating_pairs(records_a, records_b):
    if not records_a or not records_b:
        return None, 0
    cell = 5.0
    grid = collections.defaultdict(list)
    for index, record in enumerate(records_b):
        bb = record["bbox"]
        lo = tuple(int(math.floor(bb[0][i] / cell)) for i in range(3))
        hi = tuple(int(math.floor(bb[1][i] / cell)) for i in range(3))
        for x in range(lo[0], hi[0] + 1):
            for y in range(lo[1], hi[1] + 1):
                for z in range(lo[2], hi[2] + 1):
                    grid[(x, y, z)].append(index)
    count = 0
    candidates = {}
    for record_a in records_a:
        bb = record_a["bbox"]
        lo = tuple(int(math.floor(bb[0][i] / cell)) for i in range(3))
        hi = tuple(int(math.floor(bb[1][i] / cell)) for i in range(3))
        for x in range(lo[0], hi[0] + 1):
            for y in range(lo[1], hi[1] + 1):
                for z in range(lo[2], hi[2] + 1):
                    for index_b in grid.get((x, y, z), ()):
                        record_b = records_b[index_b]
                        if positive_bbox_overlap(bb, record_b["bbox"]):
                            candidates[(id(record_a), index_b)] = (record_a, record_b)
    for record_a, record_b in candidates.values():
        if convex_positive_overlap(record_a, record_b):
            count += 1
    return len(candidates), count


def compare_interface(parts, instances, transforms, boxes, name, ia, ib, filter_b=None):
    inst = dict(instances)
    if ia not in inst or ib not in inst:
        return {
            "interface": name, "instance_a": ia, "instance_b": ib,
            "status": "UNRESOLVED", "notes": "required active instance absent",
        }
    faces_a = face_audit.target_faces(parts, instances, transforms, ia)
    faces_b = face_audit.target_faces(parts, instances, transforms, ib, filter_b)
    result = face_audit.compare_faces(faces_a, faces_b, tolerance=FACE_TOL)
    records_a = element_records(parts, instances, transforms, ia)
    records_b = element_records(parts, instances, transforms, ib, filter_b)
    candidate_count, penetration_count = interpenetrating_pairs(records_a, records_b)
    total_a = sum(face["area"] for face in faces_a)
    total_b = sum(face["area"] for face in faces_b)
    contact = result["coincident_area"]
    mismatch = max(0.0, max(total_a, total_b) - contact)
    has_contact = result["minimum_distance"] is not None and result["minimum_distance"] <= FACE_TOL and contact > TOL
    no_penetration = penetration_count == 0 if penetration_count is not None else False
    final_status = "PASS" if has_contact and no_penetration else "UNRESOLVED"
    return {
        "interface": name,
        "instance_a": ia,
        "instance_b": ib,
        "boundary_face_count_a": len(faces_a),
        "boundary_face_count_b": len(faces_b),
        "true_minimum_face_distance_m": fmt(result["minimum_distance"]),
        "coincident_face_node_count": result["coincident_node_count"],
        "coincident_face_count": result["coincident_face_count"],
        "coincident_contact_area_m2": fmt(contact),
        "shared_node_count": result["shared_node_count"],
        "coincident_but_not_shared_node_count": result["coincident_not_shared_node_count"],
        "hanging_node_count": result["hanging_node_count"],
        "interpenetrating_element_pair_count": penetration_count if penetration_count is not None else "NOT_COMPUTED",
        "broad_phase_candidate_pair_count": candidate_count if candidate_count is not None else "NOT_COMPUTED",
        "mismatch_area_m2": fmt(mismatch),
        "maximum_face_to_face_mismatch_m": fmt(result["max_face_mismatch"]),
        "nodes_shared_or_coincident": "SHARED" if result["shared_node_count"] else "COINCIDENT_NOT_SHARED",
        "status": final_status,
        "notes": "boundary mesh faces and convex element geometry; AABB only broad-phase filter",
    }


def run_real_interfaces(parts, instances, transforms, boxes):
    pairs = [
        ("left_subdam_installation_bay", "V15_4_LEFT_BANK_SUBDAM_I",
         "V15_4_POWERHOUSE_INSTALLATION_BAY_I", None),
        ("installation_bay_powerhouse_unit_01", "V15_4_POWERHOUSE_INSTALLATION_BAY_I",
         "V15_4_POWERHOUSE_UNIT_01_I", None),
        ("left_subdam_engineered_backfill", "V15_4_LEFT_BANK_SUBDAM_I",
         "V15_11_LEFT_COMPACTED_SAND_GRAVEL_I", None),
        ("installation_engineered_backfill", "V15_4_POWERHOUSE_INSTALLATION_BAY_I",
         "V15_11_LEFT_COMPACTED_SAND_GRAVEL_I", None),
        ("engineered_backfill_retained_geology", "V15_11_LEFT_COMPACTED_SAND_GRAVEL_I",
         "V15_7_FOUNDATION_GEOLOGY_I", boxes.get("V15_11_LEFT_COMPACTED_SAND_GRAVEL_I")),
    ]
    rows = [compare_interface(parts, instances, transforms, boxes, *pair) for pair in pairs]
    fields = [
        "interface", "instance_a", "instance_b", "boundary_face_count_a",
        "boundary_face_count_b", "true_minimum_face_distance_m",
        "coincident_face_node_count", "coincident_face_count",
        "coincident_contact_area_m2", "shared_node_count",
        "coincident_but_not_shared_node_count", "hanging_node_count",
        "interpenetrating_element_pair_count", "broad_phase_candidate_pair_count",
        "mismatch_area_m2", "maximum_face_to_face_mismatch_m",
        "nodes_shared_or_coincident", "status", "notes",
    ]
    write_csv("v15_13_real_interface_audit.csv", fields, rows)
    details = []
    for row in rows:
        details.append({
            "interface": row["interface"],
            "instance_a": row["instance_a"],
            "instance_b": row["instance_b"],
            "supported_base_area_m2": row.get("coincident_contact_area_m2", ""),
            "unsupported_base_area_m2": "NOT_PROVEN_FROM_FULL_BASE_FACE_SET",
            "real_face_coincident_area_m2": row.get("coincident_contact_area_m2", ""),
            "real_shared_node_count": row.get("shared_node_count", ""),
            "coincident_but_not_shared_node_count": row.get("coincident_but_not_shared_node_count", ""),
            "hanging_node_count": row.get("hanging_node_count", ""),
            "mismatch_area_m2": row.get("mismatch_area_m2", ""),
            "interpenetrating_element_pair_count": row.get("interpenetrating_element_pair_count", ""),
            "maximum_local_support_gap_m": row.get("true_minimum_face_distance_m", ""),
            "support_coverage_status": "UNRESOLVED" if "backfill" in row["interface"] else "NOT_REQUIRED",
            "status": row.get("status", "UNRESOLVED"),
            "notes": "support percentage is not claimed from a partial coincident-face sample",
        })
    write_csv("v15_13_left_bank_interface_detail.csv", list(details[0]), details)
    left_required = [rows[0], rows[1]]
    contact_status = all(row.get("status") == "PASS" for row in left_required)
    # Face contact is verified, but full base-face coverage is not proven by
    # the partial coincident-face sample.  Keep that distinction in the gate.
    support_status = all(detail["support_coverage_status"] == "PASS"
                         for detail in details
                         if detail["support_coverage_status"] != "NOT_REQUIRED")
    return rows, contact_status and support_status


def topology_stats(part, label):
    face_counts = collections.defaultdict(int)
    duplicate_elements = 0
    element_keys = set()
    coord_seen = set()
    duplicate_nodes = 0
    for point in part["nodes"].values():
        key = canonical_point(point)
        if key in coord_seen:
            duplicate_nodes += 1
        coord_seen.add(key)
    element_count = 0
    for etype, elements in part["elements"].items():
        base = etype.upper()
        if base.startswith("C3D8"):
            face_def = FACE_MAP["C3D8"]
        elif base.startswith("C3D6"):
            face_def = FACE_MAP["C3D6"]
        else:
            continue
        for label_id, conn in elements.items():
            element_count += 1
            element_key = tuple(sorted(conn))
            if element_key in element_keys:
                duplicate_elements += 1
            element_keys.add(element_key)
            for _, indices in face_def:
                if max(indices) < len(conn):
                    face_counts[tuple(sorted(conn[i] for i in indices))] += 1
    histogram = collections.Counter(face_counts.values())
    return {
        "domain": label,
        "node_count": len(part["nodes"]),
        "element_count": element_count,
        "external_boundary_faces": histogram.get(1, 0),
        "identical_shared_faces": histogram.get(2, 0),
        "nonmanifold_faces": sum(value for key, value in histogram.items() if key > 2),
        "duplicate_nodes_within_tolerance": duplicate_nodes,
        "duplicate_elements_exact_connectivity": duplicate_elements,
        "nonconforming_internal_faces": "NOT_PROVEN_BY_GEOMETRIC_FACE_SWEEP",
        "hanging_nodes": "NOT_PROVEN_BY_GEOMETRIC_FACE_SWEEP",
        "unintended_disconnected_same_material_components": "NOT_PROVEN",
        "status": "UNRESOLVED",
        "notes": "exact element connectivity counts are recomputed; geometric conformity requires the explicit face sweep",
    }


def run_topology_audit(parts, instances, interface_rows):
    inst = dict(instances)
    rows = []
    geo = parts[inst["V15_7_FOUNDATION_GEOLOGY_I"]]
    back = parts[inst["V15_11_LEFT_COMPACTED_SAND_GRAVEL_I"]]
    rows.append(topology_stats(geo, "natural_geology"))
    rows.append(topology_stats(back, "engineered_backfill"))
    rows.append({
        "domain": "natural_geology_plus_engineered_backfill",
        "node_count": len(geo["nodes"]) + len(back["nodes"]),
        "element_count": sum(len(values) for values in geo["elements"].values()) +
                         sum(len(values) for values in back["elements"].values()),
        "external_boundary_faces": "SEE_COMPONENT_ROWS",
        "identical_shared_faces": "SEE_COMPONENT_ROWS",
        "nonmanifold_faces": "SEE_COMPONENT_ROWS",
        "duplicate_nodes_within_tolerance": "CROSS_PART_NODE_LABELS_SEPARATE",
        "duplicate_elements_exact_connectivity": "SEE_COMPONENT_ROWS",
        "nonconforming_internal_faces": "NOT_PROVEN_BY_GEOMETRIC_FACE_SWEEP",
        "hanging_nodes": "NOT_PROVEN_BY_GEOMETRIC_FACE_SWEEP",
        "unintended_disconnected_same_material_components": "NOT_PROVEN",
        "status": "UNRESOLVED",
        "notes": "cross-part relation is reported from actual backfill/geology face audit; no copied zero values",
    })
    fields = list(rows[0])
    write_csv("v15_13_foundation_topology_audit.csv", fields, rows)
    backfill_components = {
        "domain": "engineered_backfill",
        "element_count": rows[1]["element_count"],
        "component_count_by_exact_shared_faces": "NOT_COMPUTED",
        "largest_component_elements": "NOT_COMPUTED",
        "singleton_components": "NOT_COMPUTED",
        "status": "UNRESOLVED",
        "notes": "component graph is not inferred from a bounding box; explicit connectivity/geometry sweep remains required",
    }
    geology_components = {
        "domain": "natural_geology",
        "element_count": rows[0]["element_count"],
        "component_count_by_exact_shared_faces": "NOT_COMPUTED",
        "largest_component_elements": "NOT_COMPUTED",
        "singleton_components": "NOT_COMPUTED",
        "status": "UNRESOLVED",
        "notes": "component graph is not copied from V15.12; full mixed C3D8P/C3D8R geometric sweep is a blocking item",
    }
    write_csv("v15_13_foundation_components.csv", list(geology_components),
              [geology_components, backfill_components])
    topology_status = False
    return rows, topology_status


def parse_section_sets(lines, part_name):
    in_part = False
    current_set = None
    set_is_generate = False
    raw_sets = collections.OrderedDict()
    sections = []
    for raw in lines:
        s = raw.strip()
        match_part = re.match(r"\*Part,\s*name=([^,]+)", s, re.I)
        if match_part:
            in_part = match_part.group(1).strip() == part_name
            current_set = None
            continue
        if in_part and re.match(r"\*End Part", s, re.I):
            break
        if not in_part:
            continue
        match_section = re.match(r"\*Solid Section,\s*elset=([^,]+),\s*material=([^,]+)", s, re.I)
        if match_section:
            sections.append((match_section.group(1).strip(), match_section.group(2).strip()))
            current_set = None
            continue
        match_elset = re.match(r"\*Elset,\s*elset=([^,]+)(.*)$", s, re.I)
        if match_elset:
            name = match_elset.group(1).strip()
            current_set = name
            set_is_generate = re.search(r"\bgenerate\b", match_elset.group(2), re.I) is not None
            raw_sets.setdefault(name, (set_is_generate, []))
            continue
        if s.startswith("*") or s.startswith("**"):
            current_set = None
            continue
        if current_set is None:
            continue
        values = []
        for token in s.split(","):
            token = token.strip()
            if token:
                try:
                    values.append(int(token))
                except ValueError:
                    pass
        if values:
            raw_sets[current_set][1].extend(values)
    result = collections.OrderedDict()
    for set_name, material in sections:
        is_generate, values = raw_sets.get(set_name, (False, []))
        if is_generate:
            expanded = []
            for index in range(0, len(values) - 2, 3):
                start, end, step = values[index:index + 3]
                expanded.extend(range(start, end + (1 if step > 0 else -1), step))
            result[set_name] = expanded
        else:
            result[set_name] = list(values)
    return sections, result


def run_geology_section_audit(lines, parts, instances, material_blocks):
    geology_part = "V15_7_FOUNDATION_GEOLOGY"
    sections, section_sets = parse_section_sets(lines, geology_part)
    geo = parts[geology_part]
    type_labels = dict((etype, set(values)) for etype, values in geo["elements"].items())
    rows = []
    for section_name, material in sections:
        labels = section_sets.get(section_name, [])
        type_counts = collections.OrderedDict()
        for etype in sorted(type_labels):
            type_counts[etype] = sum(1 for label in labels if label in type_labels[etype])
        for etype, count in type_counts.items():
            if count == 0:
                continue
            material_data = material_blocks.get(material, {})
            has_perm = bool(material_data.get("PERMEABILITY"))
            is_pore = etype.upper() in POROUS_TYPES
            role = "seepage domain"
            good = is_pore and has_perm
            rows.append({
                "part": geology_part,
                "section_elset": section_name,
                "material": material,
                "element_type": etype,
                "element_count": count,
                "pore_pressure_dof_present": yesno(is_pore),
                "permeability_assigned": yesno(has_perm),
                "intended_role": role,
                "status": status_from(good),
                "notes": "C3D8R/C3D6R or material without *Permeability is unresolved for groundwater transport",
            })
    if not rows:
        rows.append({
            "part": geology_part, "section_elset": "", "material": "",
            "element_type": "", "element_count": 0,
            "pore_pressure_dof_present": "UNRESOLVED", "permeability_assigned": "UNRESOLVED",
            "intended_role": "seepage domain", "status": "UNRESOLVED",
            "notes": "no geology section mapping could be parsed",
        })
    write_csv("v15_13_geology_section_pore_pressure_audit.csv", list(rows[0]), rows)
    section_status = all(row["status"] == "PASS" for row in rows)
    return rows, section_status


def run_backfill_material_audit(material_blocks):
    material = "Q3AL_III"
    data = material_blocks.get(material, {})
    rows = [{
        "candidate_material": material,
        "source": "V15.11 active section mapping; no source-verified compacted sand/gravel calibration found",
        "density": ";".join(data.get("DENSITY", [])),
        "elastic_parameters": ";".join(data.get("ELASTIC", [])),
        "permeability": ";".join(data.get("PERMEABILITY", [])),
        "porosity_void_ratio": ";".join(data.get("POROSITY", []) + data.get("VOID RATIO", [])),
        "constitutive_model": ";".join(sorted(data.keys())),
        "element_formulation": "C3D8P",
        "final_mapping_status": "UNRESOLVED_TEMPORARY_MAPPING",
        "notes": "parameters are reported, not reinterpreted or invented as compacted-backfill calibration",
    }]
    write_csv("v15_13_backfill_material_resolution.csv", list(rows[0]), rows)
    return False


def run_pore_domain_inventory(parts, instances, material_blocks):
    rows = []
    for instance, part_name in instances:
        part = parts[part_name]
        material = part.get("material") or ""
        material_data = material_blocks.get(material, {})
        has_perm = bool(material_data.get("PERMEABILITY"))
        role = face_audit.classify_role(instance, part_name)
        if role == "foundation_geology":
            intended = "seepage domain"
        elif role in ("dam_fill", "engineered_backfill"):
            intended = "seepage domain"
        elif role in ("cutoff_wall", "geomembrane_barrier"):
            intended = "impermeable barrier"
        else:
            intended = "structural-only"
        for etype, elements in part["elements"].items():
            is_pore = etype.upper() in POROUS_TYPES
            unresolved = intended == "seepage domain" and (not is_pore or not has_perm)
            rows.append({
                "instance": instance,
                "part": part_name,
                "material": material,
                "element_type": etype,
                "element_count": len(elements),
                "pore_pressure_dof_present": yesno(is_pore),
                "permeability_assigned": yesno(has_perm),
                "intended_role": intended,
                "status": "SEEPAGE_ELEMENT_FORMULATION_UNRESOLVED" if unresolved else "PASS",
                "notes": "structural-only regions are not converted automatically",
            })
    write_csv("v15_13_pore_pressure_domain_audit.csv", list(rows[0]), rows)
    return rows, all(row["status"] == "PASS" for row in rows)


def run_cutoff_presence_and_rebuild_decision(lines, parts, instances, transforms, boxes):
    rows = []
    for instance, part_name in instances:
        upper = (instance + " " + part_name).upper()
        if not any(token in upper for token in ("CUTOFF", "F13", "ANTI_SEEP")):
            continue
        part = parts[part_name]
        transformed_nodes = [transforms[instance](point) for point in part["nodes"].values()]
        in_left_region = sum(1 for point in transformed_nodes
                             if -90.5 - FACE_TOL <= point[0] <= -7.5 + FACE_TOL and
                             -245.7 - FACE_TOL <= point[1] <= -122.0 + FACE_TOL and
                             3021.0 - FACE_TOL <= point[2] <= 3081.0 + FACE_TOL)
        rows.append({
            "search_scope": "active Assembly instance",
            "instance": instance,
            "part": part_name,
            "global_bbox": bbox_text(boxes[instance]),
            "actual_global_nodes_in_left_bank_region": in_left_region,
            "status": "CANDIDATE_OUTSIDE_LEFT_BANK_REGION" if in_left_region == 0 else "CANDIDATE_REQUIRES_FACE_CHECK",
            "notes": "node coordinates are transformed from the active V15.11 INP; no V15.12 extension is included",
        })
    left_present = any(row["actual_global_nodes_in_left_bank_region"] > 0 for row in rows)
    rows.append({
        "search_scope": "decision",
        "instance": "",
        "part": "",
        "global_bbox": "",
        "actual_global_nodes_in_left_bank_region": "",
        "status": "EXISTING_LEFT_BANK_CUTOFF_NOT_PROVEN_PRESENT" if not left_present else "EXISTING_LEFT_BANK_CUTOFF_CANDIDATE",
        "notes": "the only active cutoff candidate is outside the left sub-dam/installation global region",
    })
    write_csv("v15_13_left_subdam_cutoff_presence_audit.csv", list(rows[0]), rows)
    # The source does not provide enough surveyed coordinates to add a new
    # wall without inventing an alignment.  The v15.12 Y=70..150 extension is
    # explicitly excluded, so the rebuild deck remains a V15.11-derived deck.
    decision = [{
        "item": "anti_seepage_geometry_rebuild",
        "baseline_inp": os.path.basename(BASE_INP),
        "v15_12_y70_to_y150_extension_inherited": "NO",
        "new_left_bank_wall_added": "NO",
        "reason": "active left-bank wall is not present, but source evidence does not fix a global Assembly line; adding one would invent geometry",
        "status": "UNRESOLVED",
    }]
    write_csv("v15_13_seepage_rebuild_decision.csv", list(decision[0]), decision)
    return left_present


def run_seepage_chain(parts, instances, transforms, boxes):
    inst = dict(instances)
    segment_specs = [
        ("left_bank_abutment_extension", None),
        ("left_subdam_cutoff_segment", None),
        ("installation_powerhouse_cutoff_segment", None),
        ("ecological_release_cutoff_connection", None),
        ("spillway_cutoff_segment", None),
        ("riverbed_main_cutoff_wall", "P25_SOLID_CUTOFF_WALL_F13-1"),
        ("composite_geomembrane_connection", "V12_UPSTREAM_GEOMEMBRANE-1"),
        ("right_bank_cutoff_curtain", None),
    ]
    rows = []
    for segment, instance in segment_specs:
        if instance is None or instance not in inst:
            rows.append({
                "segment_name": segment,
                "instance": "",
                "global_start": "", "global_end": "",
                "thickness_m": "", "top_elevation_m": "", "bottom_elevation_m": "",
                "next_anti_seepage_segment": "",
                "minimum_real_gap_to_next_m": "UNRESOLVED",
                "real_contact_area_or_length": "UNRESOLVED",
                "source_basis": "required source segment not represented as an active named instance",
                "status": "UNRESOLVED",
            })
            continue
        bb = boxes[instance]
        rows.append({
            "segment_name": segment,
            "instance": instance,
            "global_start": ",".join(fmt(v) for v in bb[0]),
            "global_end": ",".join(fmt(v) for v in bb[1]),
            "thickness_m": fmt(bb[1][0] - bb[0][0]) if segment == "riverbed_main_cutoff_wall" else "",
            "top_elevation_m": fmt(bb[1][2]),
            "bottom_elevation_m": fmt(bb[0][2]),
            "next_anti_seepage_segment": "composite_geomembrane_connection" if segment == "riverbed_main_cutoff_wall" else "",
            "minimum_real_gap_to_next_m": "UNRESOLVED",
            "real_contact_area_or_length": "UNRESOLVED",
            "source_basis": "actual transformed node coordinates from V15.11 active Assembly",
            "status": "UNRESOLVED",
        })
    write_csv("v15_13_seepage_chain_audit.csv", list(rows[0]), rows)
    status = all(row["status"] == "PASS" for row in rows)
    return rows, status


def run_cutoff_connections(parts, instances, transforms, boxes):
    rows = []
    pairs = [
        ("main_cutoff_to_geomembrane", "P25_SOLID_CUTOFF_WALL_F13-1", "V12_UPSTREAM_GEOMEMBRANE-1"),
    ]
    for name, ia, ib in pairs:
        row = compare_interface(parts, instances, transforms, boxes, name, ia, ib)
        row["thickness_mismatch"] = fmt(abs((boxes[ia][1][0] - boxes[ia][0][0]) -
                                             (boxes[ib][1][0] - boxes[ib][0][0])))
        row["vertical_elevation_mismatch"] = fmt(abs(boxes[ia][1][2] - boxes[ib][1][2]))
        row["bottom_elevation_mismatch"] = fmt(abs(boxes[ia][0][2] - boxes[ib][0][2]))
        row["top_elevation_mismatch"] = fmt(abs(boxes[ia][1][2] - boxes[ib][1][2]))
        rows.append(row)
    extra_fields = ["thickness_mismatch", "vertical_elevation_mismatch",
                    "bottom_elevation_mismatch", "top_elevation_mismatch"]
    fields = [field for field in rows[0] if field not in extra_fields] + extra_fields
    write_csv("v15_13_cutoff_connection_detail.csv", fields, rows)
    connection = rows[0]
    gm_row = {
        "geomembrane_instance": "V12_UPSTREAM_GEOMEMBRANE-1",
        "cutoff_instance": "P25_SOLID_CUTOFF_WALL_F13-1",
        "geomembrane_lower_edge": fmt(boxes["V12_UPSTREAM_GEOMEMBRANE-1"][0][2]),
        "cutoff_upper_edge_or_top_zone": fmt(boxes["P25_SOLID_CUTOFF_WALL_F13-1"][1][2]),
        "minimum_real_face_or_edge_separation_m": connection.get("true_minimum_face_distance_m", "UNRESOLVED"),
        "projected_overlap_length_or_area": connection.get("coincident_contact_area_m2", "UNRESOLVED"),
        "actual_node_edge_relation": connection.get("nodes_shared_or_coincident", "UNRESOLVED"),
        "connecting_concrete_or_embedded_zone_represented": "NO_SEPARATE_CONNECTOR_INSTANCE_FOUND",
        "status": connection.get("status", "UNRESOLVED"),
        "notes": "actual boundary-face comparison; no bbox-only acceptance",
    }
    write_csv("v15_13_geomembrane_cutoff_connection.csv", list(gm_row), [gm_row])
    return connection.get("status") == "PASS"


def run_gates(phase_a_status, interface_status, topology_status,
              section_status, backfill_status, chain_status,
              cutoff_connection_status, v15_12_excluded):
    gate_rows = [
        {"gate": "Phase_A_coordinate_chain", "critical": "YES", "status": status_from(phase_a_status),
         "evidence": "v15_13_instance_transform_audit.csv + v15_13_phase_a_coordinate_chain.csv",
         "blocking_reason": "" if phase_a_status else "missing traceable active-instance transform"},
        {"gate": "V15_12_Y70_to_Y150_extension_excluded", "critical": "YES", "status": status_from(v15_12_excluded),
         "evidence": "v15_13_seepage_rebuild_decision.csv",
         "blocking_reason": "V15.12 extension was found in the rebuild deck" if not v15_12_excluded else ""},
        {"gate": "real_left_bank_interfaces", "critical": "YES", "status": status_from(interface_status),
         "evidence": "v15_13_real_interface_audit.csv + v15_13_left_bank_interface_detail.csv",
         "blocking_reason": "contact/support/penetration evidence is incomplete" if not interface_status else ""},
        {"gate": "foundation_geometric_conformity", "critical": "YES", "status": status_from(topology_status),
         "evidence": "v15_13_foundation_topology_audit.csv + v15_13_foundation_components.csv",
         "blocking_reason": "geometric nonconforming-face, hanging-node, and component sweep is unresolved" if not topology_status else ""},
        {"gate": "geology_section_pore_pressure_coverage", "critical": "YES", "status": status_from(section_status),
         "evidence": "v15_13_geology_section_pore_pressure_audit.csv",
         "blocking_reason": "structural-only or no-permeability geology sections remain in the seepage domain" if not section_status else ""},
        {"gate": "backfill_material_resolution", "critical": "YES", "status": status_from(backfill_status),
         "evidence": "v15_13_backfill_material_resolution.csv",
         "blocking_reason": "Q3AL_III remains a temporary unresolved mapping" if not backfill_status else ""},
        {"gate": "anti_seepage_chain_continuity", "critical": "YES", "status": status_from(chain_status),
         "evidence": "v15_13_seepage_chain_audit.csv + v15_13_cutoff_connection_detail.csv",
         "blocking_reason": "required left-bank/structure transition segments are not represented and proven" if not chain_status else ""},
        {"gate": "geomembrane_cutoff_connection", "critical": "YES", "status": status_from(cutoff_connection_status),
         "evidence": "v15_13_geomembrane_cutoff_connection.csv",
         "blocking_reason": "real connection face check did not pass" if not cutoff_connection_status else ""},
    ]
    pre_gate = all(row["status"] == "PASS" for row in gate_rows if row["critical"] == "YES")
    gate_rows.append({
        "gate": "Pre_Data_Check_Gate",
        "critical": "YES",
        "status": status_from(pre_gate),
        "evidence": "all preceding critical gate rows",
        "blocking_reason": "at least one critical gate is not PASS; Abaqus Data Check must not run" if not pre_gate else "",
    })
    write_csv("v15_13_pre_datacheck_gate.csv", list(gate_rows[0]), gate_rows)
    return pre_gate, gate_rows


def run_datacheck_if_allowed(pre_gate):
    rows = []
    if not pre_gate:
        rows.append({
            "job": "v15_13_final_seepage_rebuild",
            "command": "NOT_EXECUTED",
            "status": "NOT_RUN",
            "reason": "Pre-Data-Check Gate is not PASS",
        })
    else:
        command = ["abaqus.bat", "job=v15_13_final_seepage_rebuild",
                   "input=" + os.path.basename(OUT_INP), "datacheck"]
        try:
            result = subprocess.run(command, cwd=OUT_DIR, capture_output=True,
                                    text=True, timeout=3600)
            rows.append({
                "job": "v15_13_final_seepage_rebuild",
                "command": " ".join(command),
                "status": "PASS" if result.returncode == 0 else "FAIL",
                "reason": "Abaqus return code %s" % result.returncode,
            })
        except Exception as exc:
            rows.append({
                "job": "v15_13_final_seepage_rebuild",
                "command": " ".join(command),
                "status": "UNRESOLVED",
                "reason": "Data Check launch exception: %s" % exc,
            })
    write_csv("v15_13_datacheck_status.csv", list(rows[0]), rows)
    return rows[0]["status"]


def write_report(gate_rows, interface_rows, topology_rows, geology_rows,
                 pore_rows, datacheck_status, phase_a_status):
    report = os.path.join(OUT_DIR, "V15_13_FINAL_SEEPAGE_DOMAIN_REBUILD_AND_DATACHECK_RESULT.md")
    with open(report, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# V15.13 final seepage-domain rebuild and Data Check gate\n\n")
        handle.write("- Baseline: `%s` (V15.11); the V15.12 deck was not used as the geometry baseline.\n" % os.path.basename(BASE_INP))
        handle.write("- Branch target: `abaqus-audit-task`; no main-branch edit was made by this script.\n")
        handle.write("- The supplied V15.13 task file was absent from the workspace; the explicit user order and the V15.12 governing requirements were used as the execution contract.\n\n")
        handle.write("## Phase A — Assembly coordinate chain\n\n")
        handle.write("- Traceable active-instance transform gate: **%s**. Transforms come from the exact `*Instance` placement rows.\n" % status_from(phase_a_status))
        handle.write("- The generated global bboxes are diagnostics from transformed nodes; they are not used as final interface proof.\n\n")
        handle.write("## Anti-seepage rebuild\n\n")
        handle.write("- The V15.12 `Y=70..150 m` left-bank wall is explicitly excluded. The output deck contains no `V15_12_LEFT_BANK_CUTOFF_WALL` instance.\n")
        handle.write("- No new left-bank cutoff wall was added because the available source evidence does not identify a unique global Assembly line; adding one would invent geometry.\n")
        handle.write("- The active V15.11 wall/geomembrane and missing chain segments are reported in `v15_13_seepage_chain_audit.csv`.\n\n")
        handle.write("## Real interface checks\n\n")
        for row in interface_rows:
            handle.write("- `%s`: gap=%s m, contact area=%s m2, coincident faces=%s, interpenetrating element pairs=%s, status **%s**.\n" %
                         (row.get("interface", ""), row.get("true_minimum_face_distance_m", ""),
                          row.get("coincident_contact_area_m2", ""), row.get("coincident_face_count", ""),
                          row.get("interpenetrating_element_pair_count", ""), row.get("status", "UNRESOLVED")))
        handle.write("- No support percentage or zero unsupported area is claimed from a partial face sample.\n\n")
        handle.write("## Geology Section-level pore-pressure audit\n\n")
        unresolved = [row for row in geology_rows if row["status"] != "PASS"]
        handle.write("- Audited geology Section rows: **%d**; unresolved rows: **%d**.\n" % (len(geology_rows), len(unresolved)))
        handle.write("- Any geological Section using a structural-only element or a material without `*Permeability` remains unresolved; no automatic C3D8R conversion or material parameter invention was made.\n\n")
        handle.write("## Foundation topology\n\n")
        for row in topology_rows:
            handle.write("- `%s`: elements=%s, external faces=%s, exact shared faces=%s, nonmanifold=%s, duplicate nodes=%s, duplicate elements=%s, status **%s**.\n" %
                         (row["domain"], row["element_count"], row["external_boundary_faces"],
                          row["identical_shared_faces"], row["nonmanifold_faces"],
                          row["duplicate_nodes_within_tolerance"], row["duplicate_elements_exact_connectivity"],
                          row["status"]))
        handle.write("- Geometric nonconforming-face/hanging-node/component sweep is not replaced with copied V15.12 zeros; it remains a blocking unresolved gate.\n\n")
        handle.write("## Pre-Data-Check Gate\n\n")
        for row in gate_rows:
            handle.write("- `%s`: **%s** — %s\n" % (row["gate"], row["status"], row["blocking_reason"] or "evidence recorded"))
        handle.write("\n- Abaqus Data Check status: **%s**.\n" % datacheck_status)
        if datacheck_status == "NOT_RUN":
            handle.write("- Data Check was correctly withheld because all critical gates were not PASS.\n")
        handle.write("\n## Output deck\n\n")
        handle.write("- INP: `%s`\n" % OUT_INP)
        handle.write("- CAE: `%s` (V15.11 CAE copied without inheriting the V15.12 extension)\n" % OUT_CAE)
        handle.write("- No Tie, contact, MPC, spring, Encastre, artificial kinematic constraint, S01-S07 run, or solver validation was added.\n")
    return report


def main():
    ensure_out()
    if not os.path.exists(BASE_INP):
        raise RuntimeError("missing V15.11 baseline: %s" % BASE_INP)
    lines, parts, instances, _sets = deck_parser.parse_deck(BASE_INP)
    placements = parse_placements_from_lines(lines)
    if len(placements) != len(instances):
        raise RuntimeError("active instance/placement mismatch: %d/%d" % (len(instances), len(placements)))
    transforms = dict((name, make_transform(placements[name])) for name, _part in instances)
    boxes, phase_a_status = phase_a_coordinate_chain(lines, parts, instances, placements, transforms)
    # Required execution order: Phase A -> anti-seepage rebuild ->
    # backfill/geology conformity -> geology Section pore audit -> gate.
    left_present = run_cutoff_presence_and_rebuild_decision(lines, parts, instances, transforms, boxes)
    chain_rows, chain_status = run_seepage_chain(parts, instances, transforms, boxes)
    cutoff_status = run_cutoff_connections(parts, instances, transforms, boxes)
    # Copy only the V15.11-derived deck and CAE.  This is the rebuild artifact;
    # no V15.12 wall is silently carried forward.
    shutil.copyfile(BASE_INP, OUT_INP)
    shutil.copyfile(BASE_CAE, OUT_CAE)
    with open(OUT_INP, "r", encoding="utf-8", errors="replace") as handle:
        deck_text = handle.read()
    v15_12_excluded = "V15_12_LEFT_BANK_CUTOFF_WALL" not in deck_text
    interface_rows, interface_status = run_real_interfaces(parts, instances, transforms, boxes)
    topology_rows, topology_status = run_topology_audit(parts, instances, interface_rows)
    material_blocks = face_audit.parse_material_blocks(BASE_INP)
    backfill_status = run_backfill_material_audit(material_blocks)
    geology_rows, geology_status = run_geology_section_audit(lines, parts, instances, material_blocks)
    pore_rows, pore_status = run_pore_domain_inventory(parts, instances, material_blocks)
    pre_gate, gate_rows = run_gates(
        phase_a_status,
        interface_status,
        topology_status,
        geology_status and pore_status,
        backfill_status,
        chain_status,
        cutoff_status,
        v15_12_excluded,
    )
    datacheck_status = run_datacheck_if_allowed(pre_gate)
    report = write_report(gate_rows, interface_rows, topology_rows,
                          geology_rows, pore_rows, datacheck_status,
                          phase_a_status)
    print("V15_13_OUT_INP=%s" % OUT_INP)
    print("V15_13_OUT_CAE=%s" % OUT_CAE)
    print("V15_13_REPORT=%s" % report)
    print("V15_13_PHASE_A=%s" % status_from(phase_a_status))
    print("V15_13_PRE_DATACHECK=%s" % status_from(pre_gate))
    print("V15_13_DATACHECK=%s" % datacheck_status)


if __name__ == "__main__":
    main()
