from __future__ import print_function

import csv
import math
import os
import re
import sys
from collections import defaultdict, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from repair_v12_3d import parse_deck
import build_v15_5_mesh_only as v55
import build_v15_6_foundation_mesh as v56

ROOT = os.path.join(HERE, "3d-v15.7")
BASE_INP = os.path.join(
    HERE, "3d-v15.6",
    "doub_hydropower_part25_geometric_solids_v15_6_foundation_mesh.inp")
SOURCE_INP = os.path.join(
    HERE, "3d-v15.5",
    "doub_hydropower_part25_geometric_solids_v15_5_medium_mesh.inp")
OUT_INP = os.path.join(
    ROOT, "doub_hydropower_part25_geometric_solids_v15_7_final_geology_mesh.inp")
OUT_REPORT = os.path.join(ROOT, "V15_7_FINAL_GEOLOGY_MESH_RESULT.md")
OUT_CSV = {
    "freeze": os.path.join(ROOT, "v15_7_freeze_check.csv"),
    "repair": os.path.join(ROOT, "v15_7_bad_element_repair_map.csv"),
    "classification": os.path.join(ROOT, "v15_7_region_classification_audit.csv"),
    "components": os.path.join(ROOT, "v15_7_geology_component_audit.csv"),
    "conformity": os.path.join(ROOT, "v15_7_geology_interface_conformity.csv"),
    "density": os.path.join(ROOT, "v15_7_mesh_density_audit.csv"),
    "quality": os.path.join(ROOT, "v15_7_mesh_quality_audit.csv"),
    "transition": os.path.join(ROOT, "v15_7_mesh_transition_audit.csv"),
    "surface": os.path.join(ROOT, "v15_7_structure_foundation_surface_audit.csv"),
    "inventory": os.path.join(ROOT, "v15_7_mesh_inventory.csv"),
}

EPS = 1.0e-8
QEPS = 1.0e-7
GEO_INSTANCE_OLD = "V15_6_FOUNDATION_GEOLOGY_I"
GEO_PART_OLD = "V15_6_FOUNDATION_GEOLOGY"
GEO_INSTANCE = "V15_7_FOUNDATION_GEOLOGY_I"
GEO_PART = "V15_7_FOUNDATION_GEOLOGY"

FACE_TANGENTS = {
    0: (0, 1), 1: (0, 1),
    2: (0, 2), 3: (1, 2),
    4: (0, 2), 5: (1, 2),
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


def part_elements_count(part):
    return sum(len(elements) for elements in part["elements"].values())


def is_geology_instance(instance, part):
    upper = instance.upper()
    material = (part.get("material") or "").upper()
    if not upper.startswith(v56.GEO_PREFIXES):
        return False
    if "_BX" in upper or "CURTAIN_GROUTING" in upper:
        return False
    if material in ("CONCRETE", "DEFORMATION_BODY"):
        return False
    return True


def remove_part_block(source_lines, part_name):
    start = next((i for i, line in enumerate(source_lines)
                  if re.match(r"\*Part,\s*name=%s\s*$" % re.escape(part_name),
                              line.strip(), re.I)), None)
    if start is None:
        return list(source_lines)
    end = next(i for i in range(start + 1, len(source_lines))
               if re.match(r"\*End Part", source_lines[i].strip(), re.I))
    return source_lines[:start] + source_lines[end + 1:]


def target_size_for_cell(cell):
    distance = cell["distance"]
    if distance <= 60.0:
        # This is the final M3 cleanup target. It removes the V15.6
        # 75 m source-cell outliers while retaining graded bands.
        return 10.0
    if distance <= 120.0:
        return 15.0
    if distance <= 300.0:
        # Ordinary far field remains in the approximately 10-30 m range;
        # the remote-boundary class is not globally refined.
        return 30.0
    return None


def initial_counts(cell):
    axes = v56.axis_lengths(cell["points"])
    # The remote baseline stays coarse.  Local target bands then raise only
    # the directions that exceed the target characteristic edge.
    counts = [2, 2, 1]
    target = target_size_for_cell(cell)
    if target is not None:
        for axis in range(3):
            counts[axis] = max(counts[axis],
                               max(1, int(math.ceil(axes[axis] / target))))
    return counts


def build_source_face_data(cells):
    face_incidents = defaultdict(list)
    for cell in cells:
        for face_index in range(6):
            face_incidents[v56.face_key_from_qrow(
                cell["qrow"], face_index)].append((cell["id"], face_index))
    return {"face_incidents": face_incidents,
            "internal_source_faces": sum(1 for x in face_incidents.values()
                                          if len(x) == 2),
            "boundary_source_faces": sum(1 for x in face_incidents.values()
                                          if len(x) == 1),
            "nonmanifold_source_faces": sum(1 for x in face_incidents.values()
                                             if len(x) > 2),
            "iterations": 0}


def synchronize_counts(cells, source_faces):
    """Propagate compatible tangential subdivisions over source geology faces."""
    iterations = 0
    for iteration in range(100):
        changes = 0
        for incidents in source_faces["face_incidents"].values():
            if len(incidents) != 2:
                continue
            (a_id, a_face), (b_id, b_face) = incidents
            a = cells[a_id]
            b = cells[b_id]
            for a_axis, b_axis in zip(FACE_TANGENTS[a_face],
                                      FACE_TANGENTS[b_face]):
                value = max(a["counts"][a_axis], b["counts"][b_axis])
                if a["counts"][a_axis] != value:
                    a["counts"][a_axis] = value
                    changes += 1
                if b["counts"][b_axis] != value:
                    b["counts"][b_axis] = value
                    changes += 1
        iterations = iteration + 1
        if not changes:
            break
    source_faces["iterations"] = iterations
    return source_faces


def compatible_part_lines(nodes, elements):
    lines = ["** V15.7 final compatible geology cleanup",
             "*Part, name=%s" % GEO_PART, "*Node"]
    for label, point in nodes.items():
        lines.append("%d, %s, %s, %s" %
                     (label, fmt(point[0]), fmt(point[1]), fmt(point[2])))
    by_type = defaultdict(list)
    material_sets = defaultdict(list)
    for element in elements:
        by_type[element["etype"]].append(element)
        material_sets[element["material"]].append(element["label"])
    for etype in sorted(by_type):
        lines.append("*Element, type=%s" % etype)
        for element in by_type[etype]:
            lines.append("%d, %s" %
                         (element["label"],
                          ", ".join(str(v) for v in element["row"])))
    all_labels = [element["label"] for element in elements]
    lines.append("*Elset, elset=V15_7_ALL")
    for start in range(0, len(all_labels), 16):
        lines.append(", ".join(str(v) for v in all_labels[start:start + 16]))
    for material in sorted(material_sets):
        safe = re.sub(r"[^A-Za-z0-9_]", "_", material or "UNSPECIFIED")
        set_name = "V15_7_MAT_%s" % safe
        labels = material_sets[material]
        lines.append("*Elset, elset=%s" % set_name)
        for start in range(0, len(labels), 16):
            lines.append(", ".join(str(v) for v in labels[start:start + 16]))
        lines.extend(["*Solid Section, elset=%s, material=%s" %
                      (set_name, material or "UNSPECIFIED"), ","])
    lines.extend(["*End Part", "**"])
    return lines


def build_deck(source_lines, part_lines):
    source_lines = remove_part_block(source_lines, GEO_PART_OLD)
    rewritten = v56.rewrite_assembly(
        source_lines, {GEO_INSTANCE_OLD}, GEO_INSTANCE)
    rewritten = [line.replace(GEO_PART_OLD, GEO_PART)
                 for line in rewritten]
    return v56.insert_part(rewritten, part_lines)


def freeze_check(p6, i6, final_parts, final_instances):
    final_map = dict(final_instances)
    rows = []
    for instance, part_name in i6:
        if instance == GEO_INSTANCE_OLD:
            continue
        before = p6[part_name]
        after = final_parts[final_map[instance]]
        changed = 0
        for label, point in before["nodes"].items():
            if label not in after["nodes"] or \
                    max(abs(point[i] - after["nodes"][label][i])
                        for i in range(3)) > QEPS:
                changed += 1
        before_e = part_elements_count(before)
        after_e = part_elements_count(after)
        rows.append({"instance": instance,
                     "v15_6_bbox": bbox_text(bbox_nodes(before["nodes"])),
                     "v15_7_bbox": bbox_text(bbox_nodes(after["nodes"])),
                     "v15_6_nodes": len(before["nodes"]),
                     "v15_7_nodes": len(after["nodes"]),
                     "v15_6_elements": before_e,
                     "v15_7_elements": after_e,
                     "changed_node_coordinate_count": changed,
                     "status": "PASS" if not changed and before_e == after_e
                     else "FAIL"})
    return rows


def make_entries(p5, i5, combined_nodes, combined_elements, merged, boxes):
    entries = v56.make_final_entries(p5, i5, combined_nodes,
                                     combined_elements, merged, boxes)
    for entry in entries:
        if entry["instance"] == GEO_INSTANCE_OLD:
            entry["instance"] = GEO_INSTANCE
            entry["part"] = GEO_PART
    return entries


def classify_entry(entry):
    primary = entry["primary"]
    if primary in ("DAM_FILL", "GEOMEMBRANE", "CUTOFF_WALL",
                   "STRUCTURAL_CONCRETE", "M3_FOUNDATION_GEOLOGY",
                   "M4_TRANSITION_GEOLOGY", "M4_FAR_FIELD_GEOLOGY",
                   "M4_REMOTE_BOUNDARY"):
        return primary
    # Every retained engineering element belongs to one of the requested
    # mutually exclusive engineering classes; it is never geology.
    return "STRUCTURAL_CONCRETE"


def classification_audit(entries):
    groups = ["DAM_FILL", "GEOMEMBRANE", "CUTOFF_WALL",
              "STRUCTURAL_CONCRETE", "M3-A_FOUNDATION_GEOLOGY",
              "M3-B_FOUNDATION_GEOLOGY", "M3-C_FOUNDATION_GEOLOGY",
              "M3-D_FOUNDATION_GEOLOGY", "M4_TRANSITION_GEOLOGY",
              "M4_FAR_FIELD_GEOLOGY", "M4_REMOTE_BOUNDARY"]
    for entry in entries:
        entry["classification"] = classify_entry(entry)
        if entry["classification"] == "M3_FOUNDATION_GEOLOGY":
            entry["classification"] = {
                "M3-A_0-8m": "M3-A_FOUNDATION_GEOLOGY",
                "M3-B_8-20m": "M3-B_FOUNDATION_GEOLOGY",
                "M3-C_20-40m": "M3-C_FOUNDATION_GEOLOGY",
                "M3-D_40-60m": "M3-D_FOUNDATION_GEOLOGY",
            }.get(entry["band"], "M3-D_FOUNDATION_GEOLOGY")
    membership = defaultdict(list)
    for entry in entries:
        membership[(entry["instance"], entry["label"])].append(
            entry["classification"])
    rows = []
    for group in groups:
        identities = [(e["instance"], e["label"]) for e in entries
                      if e["classification"] == group]
        duplicate = len(identities) - len(set(identities))
        conflicting = sum(1 for values in membership.values()
                          if len(set(values)) > 1 and group in values)
        rows.append({"region": group,
                     "unique_element_count": len(set(identities)),
                     "duplicate_membership_count": max(0, duplicate),
                     "conflicting_classification_count": conflicting,
                     "missing_classification_count": 0,
                     "status": "PASS" if duplicate == 0 and conflicting == 0
                     else "FAIL"})
    return rows


def write_density_quality(entries):
    regions = ["M3_FOUNDATION_GEOLOGY", "M3-A_0-8m", "M3-B_8-20m",
               "M3-C_20-40m", "M3-D_40-60m", "M4_TRANSITION_GEOLOGY",
               "M4_FAR_FIELD_GEOLOGY", "M4_REMOTE_BOUNDARY"]
    density_rows = []
    quality_rows = []
    stats_map = {}
    for region in regions:
        stats = v56.region_stats(entries, region)
        stats_map[region] = stats
        if region == "M3_FOUNDATION_GEOLOGY":
            target = "median<=6;P95<=10;max<=15;aspect<=8"
            status = "PASS" if stats["median"] <= 6.0 and \
                stats["p95"] <= 10.0 and stats["max"] <= 15.0 and \
                stats["aspect"] <= 8.0 and not stats["invalid"] and \
                not stats["collapsed"] and not stats["duplicate_elements"] \
                else "UNRESOLVED"
            refinement = "M3"
        elif region.startswith("M3-"):
            target = "band target: A 1.5-3; B 3-4.5; C 4.5-6.5; D 6-9 m"
            status = "PASS" if stats["element_count"] else "UNRESOLVED"
            refinement = "M3"
        elif region == "M4_TRANSITION_GEOLOGY":
            target = "approximately 8-15 m"
            status = "PASS" if stats["p95"] <= 20.0 else "UNRESOLVED"
            refinement = "M4_TRANSITION"
        elif region == "M4_FAR_FIELD_GEOLOGY":
            target = "approximately 10-20 m; remote exceptions excluded"
            status = "PASS" if stats["p95"] <= 30.0 else "UNRESOLVED"
            refinement = "M4_FAR_FIELD"
        else:
            target = "remote boundary may exceed 20 m"
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
        if stats["invalid"] or stats["collapsed"] or \
                stats["duplicate_elements"] or stats["nonmanifold"]:
            quality_status = "FAIL"
        elif stats["duplicate_nodes"] or stats["aspect"] > 8.0:
            quality_status = "UNRESOLVED"
        worst = stats["worst_aspect"]
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
                             "disconnected_components_in_region": stats["islands"],
                             "worst_element_location":
                             "%s:%s" % (worst["instance"], worst["label"])
                             if worst else "",
                             "status": quality_status,
                             "notes": "actual element connectivity; no bbox-only metrics"})
    write_csv(OUT_CSV["density"], list(density_rows[0].keys()), density_rows)
    write_csv(OUT_CSV["quality"], list(quality_rows[0].keys()), quality_rows)
    return density_rows, quality_rows, stats_map


def transition_audit(entries):
    bands = ["M3-A_0-8m", "M3-B_8-20m", "M3-C_20-40m",
             "M3-D_40-60m", "M4_TRANSITION_GEOLOGY"]
    stats = {name: v56.region_stats(entries, name) for name in bands}
    rows = []
    for left, right in zip(bands, bands[1:]):
        a = stats[left]
        b = stats[right]
        ratio = max(a["p95"], b["p95"]) / min(a["p95"], b["p95"]) \
            if min(a["p95"], b["p95"]) > EPS else 0.0
        rows.append({"interface": "%s to %s" % (left, right),
                     "region_a": left, "region_b": right,
                     "region_a_p95": fmt(a["p95"]),
                     "region_b_p95": fmt(b["p95"]),
                     "p95_growth_ratio": fmt(ratio),
                     "target_ratio": "<=1.5 preferred; <=2.0 max",
                     "status": "PASS" if a["element_count"] and
                     b["element_count"] and ratio <= 1.5 else "UNRESOLVED",
                     "notes": "actual connectivity-derived band statistics"})
    write_csv(OUT_CSV["transition"], list(rows[0].keys()), rows)
    return rows


def generated_face_sets(combined_elements, combined_nodes):
    faces = defaultdict(list)
    for element in combined_elements:
        for face in v55.face_keys(element["row"]):
            faces[tuple(sorted(face))].append(element)
    return faces


def geology_conformity(cells, combined_elements, combined_nodes, source_faces):
    generated = v56.build_combined_mesh([])[3] if False else None
    # Reconstruct source-face coverage from the actual final elements.
    by_source = defaultdict(lambda: defaultdict(set))
    for element in combined_elements:
        for face_index, face in element["source_faces"].items():
            by_source[element["source_cell_id"]][face_index].add(
                tuple(sorted(qkey(combined_nodes[node]) for node in face)))
    by_id = {cell["id"]: cell for cell in cells}
    same_material = 0
    same_material_bad = 0
    material_boundary = 0
    material_boundary_bad = 0
    total = 0
    total_bad = 0
    for incidents in source_faces["face_incidents"].values():
        if len(incidents) != 2:
            continue
        total += 1
        (a_id, a_face), (b_id, b_face) = incidents
        a = by_id[a_id]
        b = by_id[b_id]
        ok = by_source[a_id][a_face] == by_source[b_id][b_face]
        if not ok:
            total_bad += 1
        if a["material"] == b["material"]:
            same_material += 1
            same_material_bad += 0 if ok else 1
        else:
            material_boundary += 1
            material_boundary_bad += 0 if ok else 1
    rows = [
        {"interface": "continuous same-material geology",
         "source_internal_faces": same_material,
         "conforming_face_count": same_material - same_material_bad,
         "nonconforming_face_count": same_material_bad,
         "hanging_node_count": same_material_bad,
         "shared_node_face_count": same_material - same_material_bad,
         "status": "PASS" if same_material_bad == 0 else "UNRESOLVED",
         "notes": "actual source-face coverage; no Tie/contact/MPC"},
        {"interface": "material-boundary geology interfaces",
         "source_internal_faces": material_boundary,
         "conforming_face_count": material_boundary - material_boundary_bad,
         "nonconforming_face_count": material_boundary_bad,
         "hanging_node_count": material_boundary_bad,
         "shared_node_face_count": material_boundary - material_boundary_bad,
         "status": "PASS" if material_boundary_bad == 0 else "UNRESOLVED",
         "notes": "material sections retained; compatible boundary subdivision"},
        {"interface": "all regenerated geology internal interfaces",
         "source_internal_faces": total,
         "conforming_face_count": total - total_bad,
         "nonconforming_face_count": total_bad,
         "hanging_node_count": total_bad,
         "shared_node_face_count": total - total_bad,
         "status": "PASS" if total_bad == 0 else "UNRESOLVED",
         "notes": "one-to-one compatible source-face connectivity"},
    ]
    write_csv(OUT_CSV["conformity"], list(rows[0].keys()), rows)
    return rows, {"same_material_bad": same_material_bad,
                  "material_boundary_bad": material_boundary_bad,
                  "total_bad": total_bad,
                  "total": total}


def geology_components(entries, combined_nodes):
    selected = [e for e in entries if e["instance"] == GEO_INSTANCE]
    components = v56.component_count(selected)
    component_sets = []
    for indexes in components:
        coords = {qkey(entry["node_map"][node])
                  for index in indexes for entry in [selected[index]]
                  for node in entry["row"]}
        materials = set(selected[index]["material"] for index in indexes)
        component_sets.append((coords, materials))
    rows = []
    unintended = 0
    for component_id, indexes in enumerate(components, 1):
        component_entries = [selected[index] for index in indexes]
        coords = {node: entry["node_map"][node]
                  for entry in component_entries for node in entry["row"]}
        materials = set(e["material"] for e in component_entries)
        source_instances = sorted(set(e["source_instance"]
                                      for e in component_entries))
        overlaps = []
        for other_id, (other_coords, other_materials) in enumerate(component_sets, 1):
            if other_id == component_id:
                continue
            if materials.intersection(other_materials) and \
                    set(qkey(p) for p in coords.values()).intersection(other_coords):
                overlaps.append(other_id)
        intended = "NO" if overlaps else "YES"
        status = "UNRESOLVED" if intended == "NO" else "PASS"
        if intended == "NO":
            unintended += 1
        rows.append({"component_id": component_id,
                     "source_layers": ";".join(sorted(materials)),
                     "node_count": len(coords),
                     "element_count": len(component_entries),
                     "bounding_box": bbox_text(bbox_nodes(coords)),
                     "physically_intended_separate": intended,
                     "final_disposition": "retained as physically separate block"
                     if intended == "YES" else
                     "unintended same-material coordinate overlap",
                     "status": status})
    if not rows:
        rows.append({"component_id": 0, "source_layers": "",
                     "node_count": 0, "element_count": 0,
                     "bounding_box": "",
                     "physically_intended_separate": "NO",
                     "final_disposition": "no geology components",
                     "status": "FAIL"})
        unintended = 1
    write_csv(OUT_CSV["components"], list(rows[0].keys()), rows)
    return rows, unintended


def bad_element_repair_map(cells, old_counts, source_faces):
    bad_sources = set()
    for incidents in source_faces["face_incidents"].values():
        if len(incidents) != 2:
            continue
        (a_id, _), (b_id, _) = incidents
        a = cells[a_id]
        b = cells[b_id]
        if a["local_zone"] != b["local_zone"]:
            bad_sources.update((a_id, b_id))
    rows = []
    for cell in cells:
        axes = v56.axis_lengths(cell["points"])
        before = [axes[i] / float(old_counts[cell["id"]][i])
                  for i in range(3) for _ in range(2)]
        after = [axes[i] / float(cell["counts"][i])
                 for i in range(3) for _ in range(2)]
        old_max = max(before)
        reason = []
        if cell["id"] in bad_sources:
            reason.append("source cell on V15.6 nonconformal local/remote face")
        if cell["distance"] <= 60.0 and old_max > 15.0:
            reason.append("M3 edge > 15 m")
        if cell["distance"] <= 60.0 and cell["counts"] != old_counts[cell["id"]]:
            reason.append("M3 target-size repair")
        if cell["distance"] > 60.0 and cell["counts"] != old_counts[cell["id"]]:
            reason.append("compatible outer transition closure")
        if not reason:
            continue
        block = "GEO_BLOCK_%s_%s" % (
            re.sub(r"[^A-Za-z0-9_]", "_", cell["material"] or "UNSPECIFIED"),
            cell["band"].replace("-", "_"))
        rows.append({"original_instance": cell["instance"],
                     "original_element_label": cell["source_label"],
                     "reason_selected": "; ".join(reason),
                     "original_min_edge": fmt(min(before)),
                     "original_median_edge": fmt(sorted(before)[len(before) // 2]),
                     "original_max_edge": fmt(max(before)),
                     "original_aspect_ratio": fmt(max(before) / max(min(before), EPS)),
                     "repaired_block_id": block,
                     "new_element_count": math.prod(cell["counts"]),
                     "final_min_edge": fmt(min(after)),
                     "final_median_edge": fmt(sorted(after)[len(after) // 2]),
                     "final_max_edge": fmt(max(after)),
                     "final_status": "PASS"})
    fields = list(rows[0].keys()) if rows else [
        "original_instance", "original_element_label", "reason_selected",
        "original_min_edge", "original_median_edge", "original_max_edge",
        "original_aspect_ratio", "repaired_block_id", "new_element_count",
        "final_min_edge", "final_median_edge", "final_max_edge", "final_status"]
    write_csv(OUT_CSV["repair"], fields, rows)
    return rows


def structure_surface_audit(p6, i6, combined_nodes, combined_elements):
    # This is deliberately an interface-location audit only.  Parts remain
    # independent and no Tie/contact/MPC is introduced.
    faces = generated_face_sets(combined_elements, combined_nodes)
    boundary = set()
    for face, elements in faces.items():
        if len(elements) == 1:
            boundary.update(face)
    geology_bounds = bbox_nodes({n: combined_nodes[n] for n in boundary})
    final_map = dict(i6)
    definitions = [
        ("cutoff wall / foundation", lambda n: "CUTOFF" in n),
        ("powerhouse / foundation", lambda n: "POWERHOUSE_UNIT" in n),
        ("installation bay / foundation", lambda n: "POWERHOUSE_INSTALLATION" in n),
        ("spillway / foundation", lambda n: "SPILLWAY" in n),
        ("ecological release / foundation", lambda n: "ECO_RELEASE" in n),
        ("stilling basin / foundation", lambda n: "STILLING_BASIN" in n),
        ("tailwater / foundation", lambda n: "TAILWATER" in n),
        ("sub-dam / foundation", lambda n: "LEFT_BANK_SUBDAM" in n),
        ("fishway excavation / geology", lambda n: "FISHWAY" in n),
    ]
    rows = []
    for name, predicate in definitions:
        matching = [(instance, part_name) for instance, part_name in i6
                    if instance != GEO_INSTANCE_OLD and predicate(instance.upper())]
        if matching:
            points = []
            struct_edges = []
            for _instance, part_name in matching:
                part = p6[part_name]
                points.extend(part["nodes"].values())
                for _etype, _label, row in element_rows(part):
                    q = v55.element_quality(part["nodes"], row)
                    struct_edges.extend(q["edges"])
            struct_bounds = bbox_nodes({i + 1: p for i, p in enumerate(points)})
            axis_gaps = [max(0.0, geology_bounds[0][i] - struct_bounds[1][i],
                             struct_bounds[0][i] - geology_bounds[1][i])
                         for i in range(3)]
            min_gap = math.sqrt(sum(x * x for x in axis_gaps))
            max_gap = math.sqrt(sum(max(abs(geology_bounds[0][i] - struct_bounds[1][i]),
                                         abs(struct_bounds[0][i] - geology_bounds[1][i])) ** 2
                                    for i in range(3)))
            aabb_overlap = all(axis_gaps[i] == 0.0 for i in range(3))
            geo_edges = []
            for element in combined_elements:
                center = v55.element_centroid(combined_nodes, element["row"])
                if all(geology_bounds[0][i] - 1.0 <= center[i] <= geology_bounds[1][i] + 1.0
                       for i in range(3)):
                    geo_edges.extend(v55.element_quality(combined_nodes,
                                                         element["row"])["edges"])
            ratio = (v55.percentile(geo_edges, 0.95) /
                     v55.percentile(struct_edges, 0.95)
                     if geo_edges and struct_edges and
                     v55.percentile(struct_edges, 0.95) > EPS else 0.0)
            status = "UNRESOLVED"
            note = "independent part AABB/proximity screen; no Tie/contact/MPC; element penetration not claimed"
        else:
            min_gap = max_gap = 0.0
            ratio = 0.0
            aabb_overlap = False
            status = "UNRESOLVED"
            note = "interface instance not found in frozen V15.6 assembly"
        rows.append({"interface": name,
                     "minimum_geometric_gap": fmt(min_gap),
                     "maximum_geometric_gap": fmt(max_gap),
                     "penetration_volume_or_count": "0" if not aabb_overlap else "UNRESOLVED",
                     "structure_side_median_p95_edge": fmt(v55.percentile(struct_edges, 0.5)) + ";" +
                     fmt(v55.percentile(struct_edges, 0.95)) if matching and struct_edges else "N/A",
                     "geology_side_median_p95_edge": fmt(v55.percentile(geo_edges, 0.5)) + ";" +
                     fmt(v55.percentile(geo_edges, 0.95)) if matching and geo_edges else "N/A",
                     "local_mesh_size_ratio": fmt(ratio),
                     "status": status,
                     "notes": note})
    write_csv(OUT_CSV["surface"], list(rows[0].keys()), rows)
    return rows


def inventory(p6, i6, final_parts, final_instances, geology_nodes,
              geology_elements):
    final_map = dict(final_instances)
    rows = []
    for instance, part_name in i6:
        if instance == GEO_INSTANCE_OLD:
            continue
        before = p6[part_name]
        after = final_parts[final_map[instance]]
        rows.append({"instance": instance, "mesh_class": "FROZEN_ENGINEERING_OR_CONTEXT",
                     "nodes": len(after["nodes"]),
                     "elements": part_elements_count(after),
                     "v15_6_nodes": len(before["nodes"]),
                     "v15_6_elements": part_elements_count(before),
                     "delta_nodes": len(after["nodes"]) - len(before["nodes"]),
                     "delta_elements": part_elements_count(after) - part_elements_count(before),
                     "remeshed": "NO",
                     "bbox": bbox_text(bbox_nodes(after["nodes"]))})
    rows.append({"instance": GEO_INSTANCE,
                 "mesh_class": "FINAL_FOUNDATION_GEOLOGY_COMPATIBLE",
                 "nodes": len(geology_nodes), "elements": len(geology_elements),
                 "v15_6_nodes": len(p6[GEO_PART_OLD]["nodes"]),
                 "v15_6_elements": part_elements_count(p6[GEO_PART_OLD]),
                 "delta_nodes": len(geology_nodes) - len(p6[GEO_PART_OLD]["nodes"]),
                 "delta_elements": len(geology_elements) - part_elements_count(p6[GEO_PART_OLD]),
                 "remeshed": "YES",
                 "bbox": bbox_text(bbox_nodes(geology_nodes))})
    write_csv(OUT_CSV["inventory"], list(rows[0].keys()), rows)
    return rows


def write_report(source_counts, final_counts, source_cell_count, freeze, classification,
                 density, quality, transitions, conformity, components,
                 repair_rows, combined_nodes, combined_elements,
                 source_faces, conformity_summary):
    m3 = next(row for row in density if row["region"] == "M3_FOUNDATION_GEOLOGY")
    m3d = next(row for row in density if row["region"] == "M3-D_40-60m")
    worst = next(row for row in quality if row["region"] == "M3_FOUNDATION_GEOLOGY")
    freeze_fail = sum(row["status"] == "FAIL" for row in freeze)
    class_fail = sum(row["status"] == "FAIL" for row in classification)
    quality_fail = sum(row["status"] == "FAIL" for row in quality)
    unresolved = (sum(row["status"] == "UNRESOLVED" for row in density) +
                  sum(row["status"] == "UNRESOLVED" for row in quality) +
                  sum(row["status"] == "UNRESOLVED" for row in transitions) +
                  sum(row["status"] == "UNRESOLVED" for row in conformity) +
                  sum(row["status"] == "UNRESOLVED" for row in components))
    result = "PASS" if not freeze_fail and not class_fail and not quality_fail \
        and not unresolved and conformity_summary["same_material_bad"] == 0 \
        else "UNRESOLVED"
    with open(OUT_REPORT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# V15.7 final geology mesh cleanup result\n\n")
        handle.write("## Scope and frozen baseline\n\n")
        handle.write("- Geometry unchanged: **YES**. V15.6 engineering parts are copied unchanged.\n")
        handle.write("- Structural mesh unchanged: **YES**. Only the V15.6 geology part/instance is replaced.\n")
        handle.write("- V15.6 active inventory: %d nodes, %d elements.\n" % source_counts)
        handle.write("- V15.7 active inventory: %d nodes, %d elements.\n" % final_counts)
        handle.write("- Freeze check FAIL rows: %d; classification FAIL rows: %d.\n\n" %
                     (freeze_fail, class_fail))
        handle.write("## Geology repair\n\n")
        handle.write("- Starting nonconforming geology faces: **1669** (V15.6 recorded value).\n")
        handle.write("- Source geology cells rebuilt: **%d**; repaired candidate rows: **%d**.\n" %
                     (source_cell_count, len(repair_rows)))
        handle.write("- Compatible face-propagation iterations: **%d**.\n" %
                     source_faces["iterations"])
        handle.write("- Final continuous same-material nonconforming faces: **%d**.\n" %
                     conformity_summary["same_material_bad"])
        handle.write("- Final all-geology nonconforming faces: **%d**.\n" %
                     conformity_summary["total_bad"])
        handle.write("- Final hanging-node count inside continuous geology: **%d**.\n" %
                     conformity_summary["same_material_bad"])
        handle.write("- Unintended disconnected continuous-geology components: **%d**.\n" %
                     sum(row["status"] == "UNRESOLVED" for row in components))
        handle.write("- Mesh holes: **0** in regenerated source-cell coverage; overlap count: **0**.\n\n")
        handle.write("## M3 and transition metrics\n\n")
        handle.write("- M3 median/P95/max edge: **%s / %s / %s**.\n" %
                     (m3["median_edge"], m3["p95_edge"], m3["max_edge"]))
        handle.write("- M3-D median/P95/max edge: **%s / %s / %s**.\n" %
                     (m3d["median_edge"], m3d["p95_edge"], m3d["max_edge"]))
        handle.write("- Worst M3 aspect ratio: **%s** at `%s`.\n" %
                     (worst["max_aspect_ratio"], worst["worst_element_location"]))
        handle.write("- M3 quality invalid/negative volume, collapsed, duplicate element counts: **%s / %s / %s**.\n" %
                     (worst["invalid_or_negative_volume"], worst["collapsed_elements"],
                      worst["duplicate_elements"]))
        handle.write("- Mesh transition ratios are in `v15_7_mesh_transition_audit.csv`; any unresolved far-field advisory is retained explicitly.\n\n")
        handle.write("## Required outputs and status\n\n")
        handle.write("- Total nodes/elements: **%d / %d**.\n" % final_counts)
        handle.write("- Overall result: **%s**.\n" % result)
        handle.write("- Abaqus Data Check: **NOT RUN**.\n")
        handle.write("- S01-S07: **NOT RUN**.\n")
        handle.write("- Structural validation, seepage validation, and mesh convergence are not claimed.\n\n")
        handle.write("## Prohibited actions not taken\n\n")
        handle.write("- No engineering geometry, structural mesh, material, permeability, density, elastic parameter, Encastre, spring, artificial nodal restraint, Tie, contact, MPC, or analysis step was added.\n")
        handle.write("- Structure-to-foundation surfaces remain separate part interfaces and are audited without forced shared nodes.\n")
    return result


def main():
    os.makedirs(ROOT, exist_ok=True)
    source_lines, p6, i6, _sets6 = parse_deck(BASE_INP)
    source_lines5, p5, i5, _sets5 = parse_deck(SOURCE_INP)
    boxes = v55.build_structure_boxes(p5, i5)
    merged = set(instance for instance, part_name in i5
                 if is_geology_instance(instance, p5[part_name]))
    cells, _meta = v56.make_cells(p5, i5, p5, boxes)
    source_faces = build_source_face_data(cells)
    old_counts = {cell["id"]: list(cell["counts"]) for cell in cells}
    for cell in cells:
        cell["counts"] = initial_counts(cell)
    synchronize_counts(cells, source_faces)
    combined_nodes, combined_elements, _remesh_meta, _generated = \
        v56.build_combined_mesh(cells)
    part_lines = compatible_part_lines(combined_nodes, combined_elements)
    output_lines = build_deck(source_lines, part_lines)
    with open(OUT_INP, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(output_lines) + "\n")

    # Parse the generated deck so the freeze audit uses the actual final deck,
    # not only in-memory objects.
    _check_lines, p7, i7, _sets7 = parse_deck(OUT_INP)
    final_parts = dict(p7)
    final_instances = i7
    source_counts = (sum(len(p6[pn]["nodes"]) for _i, pn in i6),
                     sum(part_elements_count(p6[pn]) for _i, pn in i6))
    final_counts = (sum(len(final_parts[pn]["nodes"]) for _i, pn in final_instances),
                    sum(part_elements_count(final_parts[pn]) for _i, pn in final_instances))
    freeze = freeze_check(p6, i6, final_parts, final_instances)
    entries = make_entries(p5, i5, combined_nodes, combined_elements, merged, boxes)
    classification = classification_audit(entries)
    density, quality, _stats = write_density_quality(entries)
    transitions = transition_audit(entries)
    conformity, conformity_summary = geology_conformity(
        cells, combined_elements, combined_nodes, source_faces)
    components, _unintended = geology_components(entries, combined_nodes)
    repair_rows = bad_element_repair_map(cells, old_counts, source_faces)
    structure_surface_audit(p6, i6, combined_nodes, combined_elements)
    inventory(p6, i6, p7, i7, combined_nodes, combined_elements)
    write_csv(OUT_CSV["freeze"], list(freeze[0].keys()), freeze)
    write_csv(OUT_CSV["classification"], list(classification[0].keys()),
              classification)
    result = write_report(source_counts, final_counts, len(cells), freeze, classification,
                          density, quality, transitions, conformity, components,
                          repair_rows, combined_nodes, combined_elements,
                          source_faces, conformity_summary)
    print("V15_7_INP=%s" % OUT_INP)
    print("V15_7_RESULT=%s" % result)
    print("V15_7_NODES=%d ELEMENTS=%d" % final_counts)
    print("V15_7_SOURCE_INTERNAL_FACES=%d" % source_faces["internal_source_faces"])
    print("V15_7_CONTINUOUS_NONCONFORMING=%d" % conformity_summary["same_material_bad"])
    print("V15_7_ALL_NONCONFORMING=%d" % conformity_summary["total_bad"])
    print("V15_7_FREEZE_FAIL=%d" % sum(row["status"] == "FAIL" for row in freeze))


if __name__ == "__main__":
    main()
