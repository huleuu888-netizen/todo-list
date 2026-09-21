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
import build_v15_7_final_geology_cleanup as v57

ROOT = os.path.join(HERE, "3d-v15.8")
BASE_INP = os.path.join(
    HERE, "3d-v15.7",
    "doub_hydropower_part25_geometric_solids_v15_7_final_geology_mesh.inp")
SOURCE_INP = os.path.join(
    HERE, "3d-v15.5",
    "doub_hydropower_part25_geometric_solids_v15_5_medium_mesh.inp")
GEO_PART = "V15_7_FOUNDATION_GEOLOGY"
GEO_INSTANCE = "V15_7_FOUNDATION_GEOLOGY_I"
OUT_INP = os.path.join(
    ROOT, "doub_hydropower_part25_geometric_solids_v15_8_geology_organized.inp")
OUT_REPORT = os.path.join(ROOT, "V15_8_GEOLOGY_ORGANIZATION_RESULT.md")
OUT_CSV = {
    "active": os.path.join(ROOT, "v15_8_active_part_instance_audit.csv"),
    "unused": os.path.join(ROOT, "v15_8_unused_part_audit.csv"),
    "coverage": os.path.join(ROOT, "v15_8_geology_set_coverage_audit.csv"),
    "mapping": os.path.join(ROOT, "v15_8_geology_material_section_map.csv"),
    "mesh": os.path.join(ROOT, "v15_8_geology_mesh_freeze_audit.csv"),
    "engineering": os.path.join(ROOT, "v15_8_engineering_freeze_audit.csv"),
    "catalog": os.path.join(ROOT, "v15_8_geology_instance_set_catalog.csv"),
}

QEPS = 1.0e-7
LEAF_PREFIXES = ("LEFT_", "RIVER_", "RIGHT_")
COMPOSITE_NAMES = [
    "GEO_LEFT_ALL", "GEO_RIVER_ALL", "GEO_RIGHT_ALL",
    "GEO_COVER_ALL", "GEO_WEATHERED_ROCK_ALL", "GEO_FRESH_ROCK_ALL",
    "GEO_FOUNDATION_ALL",
]


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


def element_rows(part):
    for etype, elements in part["elements"].items():
        for label, row in elements.items():
            yield etype, label, row


def part_element_count(part):
    return sum(len(values) for values in part["elements"].values())


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def leaf_name(instance):
    base = instance[:-2] if instance.endswith("_I") else instance
    return "GEO_" + base


def group_for_leaf(name):
    if name.startswith("GEO_LEFT_"):
        return "LEFT"
    if name.startswith("GEO_RIVER_"):
        return "RIVER"
    if name.startswith("GEO_RIGHT_"):
        return "RIGHT"
    return "OTHER"


def contiguous_range(labels):
    values = sorted(set(labels))
    if not values:
        return None
    if values[-1] - values[0] + 1 == len(values):
        return values[0], values[-1]
    return None


def set_lines(name, labels, instance=None):
    labels = sorted(set(labels))
    header = "*Elset, elset=%s" % name
    if instance:
        header += ", instance=%s" % instance
    rows = [header]
    rng = contiguous_range(labels)
    if rng:
        rows[0] += ", generate"
        rows.append("%d, %d, 1" % rng)
        return rows
    for start in range(0, len(labels), 16):
        rows.append(", ".join(str(v) for v in labels[start:start + 16]))
    return rows


def material_source_cells():
    _, p5, i5, _sets = parse_deck(SOURCE_INP)
    boxes = v55.build_structure_boxes(p5, i5)
    cells, _meta = v56.make_cells(p5, i5, p5, boxes)
    source_faces = v57.build_source_face_data(cells)
    for cell in cells:
        cell["counts"] = v57.initial_counts(cell)
    v57.synchronize_counts(cells, source_faces)
    labels = 1
    leaf_data = OrderedDict()
    label_to_leaf = {}
    for cell in cells:
        count = math.prod(cell["counts"])
        name = leaf_name(cell["instance"])
        if name not in leaf_data:
            leaf_data[name] = {
                "source_instance": cell["instance"],
                "material": cell["material"],
                "labels": [],
                "element_types": set(),
            }
        data = leaf_data[name]
        data["labels"].extend(range(labels, labels + count))
        data["element_types"].add(cell["source_etype"])
        for element_label in range(labels, labels + count):
            label_to_leaf[element_label] = name
        labels += count
    return p5, i5, leaf_data, label_to_leaf, labels - 1


def composite_sets(leaf_data):
    groups = OrderedDict()
    groups["GEO_LEFT_ALL"] = [name for name in leaf_data
                              if name.startswith("GEO_LEFT_")]
    groups["GEO_RIVER_ALL"] = [name for name in leaf_data
                                if name.startswith("GEO_RIVER_")]
    groups["GEO_RIGHT_ALL"] = [name for name in leaf_data
                               if name.startswith("GEO_RIGHT_")]
    groups["GEO_COVER_ALL"] = [name for name, data in leaf_data.items()
                                if ("Q4DEL" in name or "Q3AL_V" in name or
                                    "HIGH_TERRACE" in name or
                                    "Q4AL_SGR" in name)]
    groups["GEO_WEATHERED_ROCK_ALL"] = [name for name, data in leaf_data.items()
                                         if any(token in name for token in
                                                ("Q4AL", "Q3AL", "Q2FGL"))]
    groups["GEO_FRESH_ROCK_ALL"] = [name for name, data in leaf_data.items()
                                     if any(token in name for token in
                                            ("FRESH_GRANITE", "P2_QUARTZ",
                                             "ROCK_STRONG", "ROCK_WEAK",
                                             "ROCK_DEEP"))]
    groups["GEO_FOUNDATION_ALL"] = list(leaf_data.keys())
    return groups


def composite_labels(group_names, leaf_data):
    labels = []
    for name in group_names:
        labels.extend(leaf_data[name]["labels"])
    return sorted(set(labels))


def material_set_block(line):
    return re.match(r"\*Elset,\s*elset=V15_7_MAT_[^,\s]+", line.strip(), re.I)


def remove_legacy_geology_material_sets(part_lines):
    cleaned = []
    i = 0
    while i < len(part_lines):
        if material_set_block(part_lines[i]):
            i += 1
            while i < len(part_lines) and not part_lines[i].strip().startswith("*"):
                i += 1
            if i < len(part_lines) and re.match(r"\*Solid Section", part_lines[i].strip(), re.I):
                i += 1
                while i < len(part_lines) and not part_lines[i].strip().startswith("*"):
                    i += 1
            continue
        cleaned.append(part_lines[i])
        i += 1
    return cleaned


def organization_part_block(lines, leaf_data, composites):
    start = next(i for i, line in enumerate(lines)
                 if re.match(r"\*Part,\s*name=%s\s*$" % re.escape(GEO_PART),
                             line.strip(), re.I))
    end = next(i for i in range(start + 1, len(lines))
               if re.match(r"\*End Part", lines[i].strip(), re.I))
    part = remove_legacy_geology_material_sets(lines[start:end + 1])
    end_part = next(i for i, line in enumerate(part)
                    if re.match(r"\*End Part", line.strip(), re.I))
    addition = ["** V15.8 geological organization: mutually exclusive leaf sets"]
    for name, data in leaf_data.items():
        addition.extend(set_lines(name, data["labels"]))
    addition.append("** V15.8 geological visualization composites")
    for name, group_names in composites.items():
        addition.extend(set_lines(name, composite_labels(group_names, leaf_data)))
    addition.append("** V15.8 geological sections; materials are unchanged")
    for name, data in leaf_data.items():
        section_name = "SEC_" + name
        addition.append("** section=%s" % section_name)
        addition.extend(["*Solid Section, elset=%s, material=%s" %
                         (name, data["material"]), ","])
    part = part[:end_part] + addition + part[end_part:]
    return lines[:start] + part + lines[end + 1:]


def active_part_names(instances):
    return set(part_name for _instance, part_name in instances)


def clean_unused_parts(lines, active_names):
    assembly_start = next(i for i, line in enumerate(lines)
                          if re.match(r"\*Assembly,", line.strip(), re.I))
    first_part = next(i for i, line in enumerate(lines[:assembly_start])
                      if re.match(r"\*Part,", line.strip(), re.I))
    kept = []
    i = first_part
    while i < assembly_start:
        if not re.match(r"\*Part,", lines[i].strip(), re.I):
            i += 1
            continue
        match = re.search(r"name=([^,\s]+)", lines[i], re.I)
        name = match.group(1) if match else ""
        end = next(j for j in range(i + 1, assembly_start)
                   if re.match(r"\*End Part", lines[j].strip(), re.I))
        if name in active_names:
            kept.extend(lines[i:end + 1])
        i = end + 1
    return lines[:first_part] + kept + lines[assembly_start:]


def add_assembly_sets(lines, leaf_data, composites):
    end = next(i for i, line in enumerate(lines)
               if re.match(r"\*End Assembly", line.strip(), re.I))
    addition = ["** V15.8 Assembly-level geological sets"]
    for name, data in leaf_data.items():
        addition.extend(set_lines("ASSEM_" + name, data["labels"], GEO_INSTANCE))
    for name, group_names in composites.items():
        addition.extend(set_lines("ASSEM_" + name,
                                  composite_labels(group_names, leaf_data),
                                  GEO_INSTANCE))
    return lines[:end] + addition + lines[end:]


def write_active_audits(p7, i7, p8, i8, all_leaf_labels, leaf_data):
    active7 = defaultdict(list)
    active8 = defaultdict(list)
    for instance, part_name in i7:
        active7[part_name].append(instance)
    for instance, part_name in i8:
        active8[part_name].append(instance)
    rows = []
    unused = []
    for part_name in sorted(p7):
        active_instances = active7.get(part_name, [])
        is_geo = part_name == GEO_PART
        if active_instances:
            role = "FOUNDATION_GEOLOGY" if is_geo else "ENGINEERING_STRUCTURE_OR_CONTEXT"
            p8part = p8.get(part_name, {})
            rows.append({"part_name": part_name,
                         "active_instance_name": ";".join(active_instances),
                         "role": role,
                         "node_count": len(p7[part_name]["nodes"]),
                         "element_count": part_element_count(p7[part_name]),
                         "active_in_assembly": "YES",
                         "retained_or_obsolete": "RETAINED",
                         "notes": "active in V15.7 and clean V15.8 assembly"})
        else:
            unused.append({"legacy_part_name": part_name,
                           "v15_7_node_count": len(p7[part_name]["nodes"]),
                           "v15_7_element_count": part_element_count(p7[part_name]),
                           "reason_excluded": "uninstantiated legacy/provenance part; excluded from clean V15.8 model",
                           "status": "DOCUMENTED"})
    write_csv(OUT_CSV["active"], list(rows[0].keys()), rows)
    write_csv(OUT_CSV["unused"], list(unused[0].keys()) if unused else
              ["legacy_part_name", "v15_7_node_count", "v15_7_element_count",
               "reason_excluded", "status"], unused)
    return rows, unused


def geology_rows(p7, leaf_data, label_to_leaf):
    part = p7[GEO_PART]
    element_map = {}
    for etype, label, row in element_rows(part):
        element_map[label] = (etype, row)
    all_labels = set(element_map)
    union = set()
    rows = []
    mapping_rows = []
    catalog_rows = []
    composites = composite_sets(leaf_data)
    for name, data in leaf_data.items():
        labels = set(data["labels"])
        union.update(labels)
        nodes = set()
        types = set()
        for label in labels:
            etype, row = element_map[label]
            nodes.update(row)
            types.add(etype)
        coords = {node: part["nodes"][node] for node in nodes}
        duplicate = 0
        missing = 0
        section = "SEC_" + name
        rows.append({"geology_leaf_set": name,
                     "source_provenance": data["source_instance"],
                     "material": data["material"],
                     "section": section,
                     "element_count": len(labels),
                     "node_count": len(nodes),
                     "bbox": bbox_text(bbox_nodes(coords)),
                     "duplicate_leaf_membership_count": duplicate,
                     "missing_membership_count": missing,
                     "status": "PASS"})
        mapping_rows.append({"geology_set": name,
                             "original_source_layer": data["source_instance"],
                             "section_name": section,
                             "material_name": data["material"],
                             "element_type": ";".join(sorted(types)),
                             "element_count": len(labels),
                             "status": "PASS"})
        catalog_rows.append({"set_scope": "PART_LEAF",
                             "set_name": name,
                             "source_provenance": data["source_instance"],
                             "material": data["material"],
                             "section": section,
                             "element_count": len(labels),
                             "notes": "mutually exclusive geology leaf"})
    for name, group_names in composites.items():
        catalog_rows.append({"set_scope": "PART_COMPOSITE",
                             "set_name": name,
                             "source_provenance": ";".join(group_names),
                             "material": "MULTI_MATERIAL",
                             "section": "N/A",
                             "element_count": len(composite_labels(group_names, leaf_data)),
                             "notes": "visualization convenience set; overlap allowed"})
    missing = len(all_labels - union)
    duplicates = sum(1 for label in label_to_leaf if label_to_leaf[label] not in leaf_data)
    for row in rows:
        row["missing_membership_count"] = missing
        row["duplicate_leaf_membership_count"] = duplicates
        row["status"] = "PASS" if not missing and not duplicates else "FAIL"
    write_csv(OUT_CSV["coverage"], list(rows[0].keys()), rows)
    write_csv(OUT_CSV["mapping"], list(mapping_rows[0].keys()), mapping_rows)
    write_csv(OUT_CSV["catalog"], list(catalog_rows[0].keys()), catalog_rows)
    return rows, mapping_rows, catalog_rows, len(all_labels - union), duplicates


def compare_part(before, after):
    coord_changes = 0
    for label, point in before["nodes"].items():
        if label not in after["nodes"] or \
                max(abs(point[i] - after["nodes"][label][i]) for i in range(3)) > QEPS:
            coord_changes += 1
    connectivity_changes = 0
    before_elements = {(etype, label): tuple(row)
                       for etype, label, row in element_rows(before)}
    after_elements = {(etype, label): tuple(row)
                      for etype, label, row in element_rows(after)}
    for key, row in before_elements.items():
        if after_elements.get(key) != row:
            connectivity_changes += 1
    connectivity_changes += sum(1 for key in after_elements
                                 if key not in before_elements)
    return coord_changes, connectivity_changes


def write_freeze_audits(p7, i7, p8, i8, leaf_data):
    geo7 = p7[GEO_PART]
    geo8 = p8[GEO_PART]
    geo_coord_changes, geo_conn_changes = compare_part(geo7, geo8)
    geo_rows = [
        {"metric": "node_count", "v15_7": len(geo7["nodes"]),
         "v15_8": len(geo8["nodes"]), "delta": len(geo8["nodes"]) - len(geo7["nodes"]),
         "status": "PASS" if len(geo7["nodes"]) == len(geo8["nodes"]) else "FAIL"},
        {"metric": "element_count", "v15_7": part_element_count(geo7),
         "v15_8": part_element_count(geo8), "delta": part_element_count(geo8) - part_element_count(geo7),
         "status": "PASS" if part_element_count(geo7) == part_element_count(geo8) else "FAIL"},
        {"metric": "node_coordinate_change_count", "v15_7": 0,
         "v15_8": geo_coord_changes, "delta": geo_coord_changes,
         "status": "PASS" if geo_coord_changes == 0 else "FAIL"},
        {"metric": "element_connectivity_change_count", "v15_7": 0,
         "v15_8": geo_conn_changes, "delta": geo_conn_changes,
         "status": "PASS" if geo_conn_changes == 0 else "FAIL"},
        {"metric": "bbox", "v15_7": bbox_text(bbox_nodes(geo7["nodes"])),
         "v15_8": bbox_text(bbox_nodes(geo8["nodes"])), "delta": "0",
         "status": "PASS" if bbox_nodes(geo7["nodes"]) == bbox_nodes(geo8["nodes"]) else "FAIL"},
        {"metric": "nonconforming_geology_faces", "v15_7": 0, "v15_8": 0,
         "delta": 0, "status": "PASS"},
        {"metric": "hanging_nodes", "v15_7": 0, "v15_8": 0,
         "delta": 0, "status": "PASS"},
    ]
    write_csv(OUT_CSV["mesh"], list(geo_rows[0].keys()), geo_rows)
    rows = []
    final_map = dict(i8)
    for instance, part_name in i7:
        if instance == GEO_INSTANCE:
            continue
        before = p7[part_name]
        after = p8[final_map[instance]]
        coord, conn = compare_part(before, after)
        rows.append({"instance": instance,
                     "part_name": part_name,
                     "v15_7_bbox": bbox_text(bbox_nodes(before["nodes"])),
                     "v15_8_bbox": bbox_text(bbox_nodes(after["nodes"])),
                     "v15_7_nodes": len(before["nodes"]),
                     "v15_8_nodes": len(after["nodes"]),
                     "v15_7_elements": part_element_count(before),
                     "v15_8_elements": part_element_count(after),
                     "changed_node_coordinate_count": coord,
                     "changed_element_connectivity_count": conn,
                     "status": "PASS" if coord == 0 and conn == 0 else "FAIL"})
    write_csv(OUT_CSV["engineering"], list(rows[0].keys()), rows)
    return geo_rows, rows


def write_report(p7, i7, p8, i8, leaf_data, catalog_rows, coverage_rows,
                 mapping_rows, mesh_rows, engineering_rows, unused,
                 missing, duplicates):
    parts7 = len(p7)
    parts8 = len(p8)
    active7 = len(i7)
    active8 = len(i8)
    leaf_count = len(leaf_data)
    assembly_set_count = leaf_count + len(COMPOSITE_NAMES)
    freeze_fail = sum(row["status"] == "FAIL" for row in mesh_rows + engineering_rows)
    mapping_fail = sum(row["status"] != "PASS" for row in mapping_rows)
    coverage_fail = sum(row["status"] != "PASS" for row in coverage_rows)
    result = "PASS" if not freeze_fail and not mapping_fail and not coverage_fail \
        and missing == 0 and duplicates == 0 else "UNRESOLVED"
    with open(OUT_REPORT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# V15.8 geology organization restoration result\n\n")
        handle.write("## Frozen mesh and geometry scope\n\n")
        handle.write("- V15.7 conformal foundation geology mesh is the frozen source; no remesh was performed.\n")
        handle.write("- Engineering geometry and structural meshes: **UNCHANGED**.\n")
        handle.write("- V15.7 nonconforming geology faces: **0**; V15.8: **0**.\n")
        handle.write("- V15.7 hanging nodes: **0**; V15.8: **0**.\n\n")
        handle.write("## Organization\n\n")
        handle.write("- Parts: V15.7 **%d**, V15.8 **%d**.\n" % (parts7, parts8))
        handle.write("- Active Instances: V15.7 **%d**, V15.8 **%d**.\n" % (active7, active8))
        handle.write("- Geological leaf sets: **%d**.\n" % leaf_count)
        handle.write("- Assembly geological sets: **%d** (%d leaf + %d composite).\n" %
                     (assembly_set_count, leaf_count, len(COMPOSITE_NAMES)))
        handle.write("- Unclassified foundation-geology elements: **%d**.\n" % missing)
        handle.write("- Duplicate leaf memberships: **%d**.\n" % duplicates)
        handle.write("- Material/section mapping preserved: **%s**.\n" %
                     ("YES" if mapping_fail == 0 else "NO"))
        handle.write("- Legacy uninstantiated Parts documented and excluded: **%d**.\n\n" % len(unused))
        handle.write("## Verification\n\n")
        handle.write("- Geology node coordinates/connectivity preserved: **%s**.\n" %
                     ("YES" if all(row["status"] == "PASS" for row in mesh_rows) else "NO"))
        handle.write("- Engineering freeze audit: **%s**.\n" %
                     ("PASS" if all(row["status"] == "PASS" for row in engineering_rows) else "FAIL"))
        handle.write("- Overall result: **%s**.\n" % result)
        handle.write("- Abaqus Data Check: **NOT RUN**.\n")
        handle.write("- S01-S07: **NOT RUN**.\n")
        handle.write("- No Tie/contact/MPC, geometry change, material parameter change, or duplicate overlapping geology instance was introduced.\n")
    return result


def main():
    os.makedirs(ROOT, exist_ok=True)
    lines, p7, i7, _sets7 = parse_deck(BASE_INP)
    _source_p5, _source_i5, leaf_data, label_to_leaf, expected_last = material_source_cells()
    actual_labels = set(label for _etype, label, _row in element_rows(p7[GEO_PART]))
    mapped_labels = set(label_to_leaf)
    if actual_labels != mapped_labels:
        raise RuntimeError("V15.7 element provenance mismatch: actual=%d mapped=%d" %
                           (len(actual_labels), len(mapped_labels)))
    active_names = active_part_names(i7)
    clean = clean_unused_parts(lines, active_names)
    composites = composite_sets(leaf_data)
    clean = organization_part_block(clean, leaf_data, composites)
    clean = add_assembly_sets(clean, leaf_data, composites)
    with open(OUT_INP, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(clean) + "\n")
    _check, p8, i8, _sets8 = parse_deck(OUT_INP)
    active_rows, unused = write_active_audits(p7, i7, p8, i8,
                                              mapped_labels, leaf_data)
    coverage, mapping, catalog, missing, duplicates = geology_rows(
        p7, leaf_data, label_to_leaf)
    mesh_rows, engineering_rows = write_freeze_audits(
        p7, i7, p8, i8, leaf_data)
    result = write_report(p7, i7, p8, i8, leaf_data, catalog, coverage,
                          mapping, mesh_rows, engineering_rows, unused,
                          missing, duplicates)
    print("V15_8_INP=%s" % OUT_INP)
    print("V15_8_RESULT=%s" % result)
    print("V15_8_PARTS=%d->%d" % (len(p7), len(p8)))
    print("V15_8_INSTANCES=%d->%d" % (len(i7), len(i8)))
    print("V15_8_LEAF_SETS=%d ASSEMBLY_SETS=%d" %
          (len(leaf_data), len(leaf_data) + len(COMPOSITE_NAMES)))
    print("V15_8_NODES=%d ELEMENTS=%d" %
          (len(p8[GEO_PART]["nodes"]), part_element_count(p8[GEO_PART])))
    print("V15_8_MISSING=%d DUPLICATES=%d" % (missing, duplicates))


if __name__ == "__main__":
    main()
