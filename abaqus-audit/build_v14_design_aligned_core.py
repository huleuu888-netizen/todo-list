"""Build the V14 design-alignment deck from the immutable V13 keyword deck.

The available design evidence supports changing hydraulic case definitions and
separating the seismic case. It does not prove a 3-D coordinate correction, so
this builder intentionally makes no geometry-node edits.
"""
from __future__ import print_function

import argparse
import csv
import os
import re
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from repair_v12_3d import parse_deck, global_coord, WATER_UNIT_WEIGHT


SOURCE_DEFAULT = os.path.join(
    HERE, "3d-v13",
    "doub_hydropower_part25_geometric_solids_v13_rigidbody_geostatic_fixed.inp")
OUTPUT_DEFAULT = os.path.join(
    HERE, "3d-v14",
    "doub_hydropower_part25_geometric_solids_v14_design_aligned.inp")

TARGETS = {
    "S03_NORMAL_RESERVOIR_3076M":
        ("S03_NORMAL_RESERVOIR", 3076.00, 3053.50, "normal reservoir"),
    "S04_DESIGN_FLOOD_3580CMS":
        ("S04_DESIGN_FLOOD", 3076.00, 3060.26,
         "design-flood stability pair; source text has an inconsistent alternate upstream narrative"),
    "S05_CHECK_FLOOD_AND_SEISMIC":
        ("S05_CHECK_FLOOD", 3077.35, 3061.38, "check flood only; seismic load removed"),
    "S06_DRAWDOWN_TO_3074M":
        ("S06_DRAWDOWN_DEADWATER", 3074.00, 3053.50, "drawdown/dead-water"),
}
SEISMIC_STEP = ("S07_NORMAL_RESERVOIR_SEISMIC_0P206G", 3076.00, 3053.50,
                "normal reservoir pair with horizontal equivalent gravity 0.206 g")


def step_name(line):
    match = re.search(r"\*Step,\s*name=([^,]+)", line.strip(), re.I)
    return match.group(1).strip() if match else None


def collect_downstream_sets(lines, parts, instances):
    instance_to_part = dict(instances)
    sets = {}
    current = None
    for line in lines:
        text = line.strip()
        if text.lower().startswith("*nset, nset=v12_"):
            fields = [value.strip() for value in text.split(",")]
            name = fields[1].split("=", 1)[1]
            instance = fields[2].split("=", 1)[1]
            if name.startswith("V12_U_") or name.startswith("V12_D_"):
                sets[name] = {"instance": instance, "labels": []}
                current = name
            else:
                current = None
            continue
        if current and text.startswith("*"):
            current = None
        elif current and text and not text.startswith("**"):
            for token in text.split(","):
                try:
                    sets[current]["labels"].append(int(token.strip()))
                except ValueError:
                    pass
    for name, record in sets.items():
        instance = record["instance"]
        part = instance_to_part[instance]
        if not record["labels"]:
            raise RuntimeError("empty hydraulic set %s" % name)
        points = [global_coord(instance, part, parts[part]["nodes"][label])
                  for label in record["labels"]]
        zs = [point[2] for point in points]
        record["part"] = part
        record["points"] = points
        record["z"] = sum(zs) / len(zs)
    return sets


def replace_hydraulic_line(line, step, hydraulic_sets):
    fields = [value.strip() for value in line.strip().split(",")]
    if len(fields) < 4 or fields[0] not in hydraulic_sets:
        return line
    try:
        dof1 = int(fields[1]); dof2 = int(fields[2])
    except ValueError:
        return line
    if dof1 != 8 or dof2 != 8:
        return line
    _new_name, upstream, downstream, _basis = step
    head = upstream if fields[0].startswith("V12_U_") else downstream
    z = hydraulic_sets[fields[0]]["z"]
    pressure = WATER_UNIT_WEIGHT * max(head - z, 0.0)
    return "%s, 8, 8, %.10g" % (fields[0], pressure)


def remove_seismic_load(block):
    result = []
    dropping = False
    for line in block:
        text = line.strip()
        if text.lower().startswith("** name: seismic_equivalent_0_206g"):
            dropping = True
            continue
        if dropping:
            if text.startswith("**"):
                dropping = False
            elif text.lower().startswith("*dload") or text.startswith(","):
                continue
            else:
                dropping = False
        result.append(line)
    return result


def transform_block(block, old_name, new_step, hydraulic_sets,
                    strip_seismic=False, add_seismic=False):
    if strip_seismic:
        block = remove_seismic_load(block)
    result = []
    inserted_seismic = False
    for original in block:
        line = original
        if re.search(r"\*Step,\s*name=" + re.escape(old_name), line, re.I):
            line = re.sub(r"(\*Step,\s*name=)[^,]+",
                          r"\1" + new_step[0], line, flags=re.I)
        elif old_name in line:
            line = line.replace(old_name, new_step[0])
        if line.strip().lower().startswith(", grav, 9.81") and add_seismic:
            result.append(line)
            if not inserted_seismic:
                result.append("** Name: SEISMIC_EQUIVALENT_0_206G")
                result.append(", GRAV, 2.02086, 1., 0., 0.")
                inserted_seismic = True
            continue
        if line.strip().startswith("V12_U_") or line.strip().startswith("V12_D_"):
            line = replace_hydraulic_line(line, new_step, hydraulic_sets)
        result.append(line)
    if add_seismic and not inserted_seismic:
        raise RuntimeError("could not insert seismic equivalent gravity")
    return result


def split_blocks(lines):
    blocks = []
    index = 0
    while index < len(lines):
        if step_name(lines[index]):
            end = index
            while end < len(lines):
                if lines[end].strip().lower().startswith("*end step"):
                    end += 1
                    break
                end += 1
            blocks.append((index, end, step_name(lines[index]), lines[index:end]))
            index = end
        else:
            index += 1
    return blocks


def build(source, output, audit_csv):
    with open(source, "r", encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()
    _lines, parts, instances, _sets = parse_deck(source)
    hydraulic_sets = collect_downstream_sets(lines, parts, instances)
    blocks = split_blocks(lines)
    by_name = dict((name, block) for _start, _end, name, block in blocks)
    missing = [name for name in TARGETS if name not in by_name]
    if missing:
        raise RuntimeError("missing source steps: %s" % ", ".join(missing))
    output_lines = []
    position = 0
    for start, end, name, block in blocks:
        output_lines.extend(lines[position:start])
        if name in TARGETS:
            target = TARGETS[name]
            output_lines.extend(transform_block(
                block, name, target, hydraulic_sets,
                strip_seismic=name in ("S05_CHECK_FLOOD_AND_SEISMIC",
                                       "S06_DRAWDOWN_TO_3074M")))
        else:
            output_lines.extend(block)
        position = end
    output_lines.extend(lines[position:])

    s03_block = transform_block(
        by_name["S03_NORMAL_RESERVOIR_3076M"],
        "S03_NORMAL_RESERVOIR_3076M", SEISMIC_STEP, hydraulic_sets,
        add_seismic=True)
    insert_at = next((i for i, line in enumerate(output_lines)
                      if line.strip().lower().startswith("*end analysis")),
                     len(output_lines))
    addition = [
        "** ----------------------------------------------------------------",
        "** STEP: S07_NORMAL_RESERVOIR_SEISMIC_0P206G",
        "** V14: seismic is separate from check flood; normal reservoir heads retained.",
    ] + s03_block
    output_lines[insert_at:insert_at] = addition

    with open(output, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("** V14 DESIGN ALIGNMENT BUILT FROM V13; NO GEOMETRY NODES MODIFIED\n")
        handle.write("** Hydraulic cases are source-supported design targets; see audit CSVs.\n")
        handle.write("\n".join(output_lines) + "\n")

    fields = ["step", "upstream_head_m", "downstream_head_m", "basis",
              "geometry_modified"]
    with open(audit_csv, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for target in list(TARGETS.values()) + [SEISMIC_STEP]:
            writer.writerow([target[0], "%.2f" % target[1], "%.2f" % target[2],
                             target[3], "NO"])
    print("V14_INP=%s" % output)
    print("V14_GEOMETRY_NODE_EDITS=0")
    print("V14_HYDRAULIC_SETS=%d" % len(hydraulic_sets))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=SOURCE_DEFAULT)
    parser.add_argument("--output", default=OUTPUT_DEFAULT)
    parser.add_argument("--audit-csv", default=os.path.join(
        HERE, "3d-v14", "v14_geometry_correspondence.csv"))
    args = parser.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    build(args.source, args.output, args.audit_csv)


if __name__ == "__main__":
    main()
