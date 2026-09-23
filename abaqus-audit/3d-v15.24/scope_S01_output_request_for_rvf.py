from __future__ import print_function

import hashlib
import os
import re


ROOT = os.path.dirname(os.path.abspath(__file__))
S01_DIR = os.path.join(ROOT, "S01")
SOURCE_INP = os.path.join(os.path.dirname(ROOT), "3d-v15.23", "v15_23_S01_OUTPUT_COMPLETION.inp")
TARGET_INP = os.path.join(S01_DIR, "v15_24_S01_BASELINE.inp")
AUDIT_PATH = os.path.join(ROOT, "V15.24_RVF_SCOPED_OUTPUT_AUDIT.md")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def keyword_name(line):
    stripped = line.lstrip()
    if not stripped.startswith("*"):
        return ""
    return stripped[1:].split(",", 1)[0].strip().upper()


def is_keyword(line):
    return line.lstrip().startswith("*")


def parse_model(lines):
    part_element_type = {}
    current_part = None
    instances = {}
    downstream_sets = []
    for line in lines:
        part_match = re.match(r"\*Part,\s*name=([^,\s]+)", line, re.I)
        if part_match:
            current_part = part_match.group(1).strip()
            continue
        element_match = re.match(r"\*Element,\s*type=([^,\s]+)", line, re.I)
        if element_match and current_part and current_part not in part_element_type:
            part_element_type[current_part] = element_match.group(1).strip().upper()
            continue
        instance_match = re.match(r"\*Instance,\s*name=([^,\s]+),\s*part=([^,\s]+)", line, re.I)
        if instance_match:
            instances[instance_match.group(1).strip()] = instance_match.group(2).strip()
            continue
        nset_match = re.match(r"\*Nset,\s*nset=(S00_D_[^,\s]+),\s*instance=([^,\s]+)", line, re.I)
        if nset_match:
            set_name = nset_match.group(1).strip()
            instance_name = nset_match.group(2).strip()
            part_name = instances.get(instance_name, "")
            element_type = part_element_type.get(part_name, "")
            if element_type in ("C3D8P", "C3D6P"):
                downstream_sets.append((set_name, instance_name, part_name, element_type))
    unique = []
    seen = set()
    for item in downstream_sets:
        if item[0] not in seen:
            unique.append(item)
            seen.add(item[0])
    return part_element_type, instances, unique


def output_block_bounds(lines):
    field_start = None
    history_start = None
    for index, line in enumerate(lines):
        upper = line.strip().upper()
        if upper.startswith("*OUTPUT, FIELD"):
            field_start = index
        elif field_start is not None and upper.startswith("*OUTPUT, HISTORY"):
            history_start = index
            break
    if field_start is None or history_start is None:
        raise RuntimeError("Could not locate final field/history output block")
    return field_start, history_start


def main():
    if not os.path.isfile(SOURCE_INP):
        raise RuntimeError("Missing V15.23 output-completion input: %s" % SOURCE_INP)
    with open(SOURCE_INP, "r") as handle:
        lines = handle.readlines()
    part_element_type, instances, downstream_sets = parse_model(lines)
    if not downstream_sets:
        raise RuntimeError("No downstream node sets on C3D8P/C3D6P instances were found")

    field_start, history_start = output_block_bounds(lines)
    block = lines[field_start:history_start]
    element_index = None
    for offset, line in enumerate(block):
        if keyword_name(line) == "ELEMENT OUTPUT":
            element_index = offset
            break
    if element_index is None:
        raise RuntimeError("Element Output block not found")

    prefix = ["*Output, field, variable=PRESELECT\n", "*Node Output\n", "POR, RF, U\n"]
    scoped = []
    for set_name, instance_name, part_name, element_type in downstream_sets:
        scoped.append("*Node Output, NSET=%s\n" % set_name)
        scoped.append("RVF, FLDVEL, COORD\n")
    suffix = block[element_index:]
    output_lines = lines[:field_start] + prefix + scoped + suffix + lines[history_start:]
    with open(TARGET_INP, "w") as handle:
        handle.writelines(output_lines)

    with open(AUDIT_PATH, "w") as audit:
        audit.write("# V15.24 RVF-Scoped Output Audit\n\n")
        audit.write("- Source: `%s`\n" % os.path.basename(SOURCE_INP))
        audit.write("- Target: `%s`\n" % os.path.basename(TARGET_INP))
        audit.write("- Source SHA256: `%s`\n" % sha256(SOURCE_INP))
        audit.write("- Target SHA256: `%s`\n\n" % sha256(TARGET_INP))
        audit.write("The first V15.24 run used the source input unchanged and\n")
        audit.write("failed in Abaqus/Standard output processing with a segmentation\n")
        audit.write("fault. This retry limits the added output variables to actual\n")
        audit.write("downstream node sets on C3D8P/C3D6P instances. No physical\n")
        audit.write("model keyword is changed.\n\n")
        audit.write("- Porous downstream node sets: %d\n" % len(downstream_sets))
        audit.write("- Global node output retained: `POR, RF, U`\n")
        audit.write("- Scoped node output added: `RVF, FLDVEL, COORD`\n")
        audit.write("- Element output retained: `FLVEL, POR, S, EVOL`\n\n")
        audit.write("## Scoped sets\n\n")
        for set_name, instance_name, part_name, element_type in downstream_sets:
            audit.write("- `%s` | instance `%s` | part `%s` | `%s`\n" % (set_name, instance_name, part_name, element_type))
    print("V15.24_SCOPED_OUTPUT_INPUT_GENERATED")
    print("downstream_porous_sets=%d" % len(downstream_sets))
    print("target=%s" % TARGET_INP)


if __name__ == "__main__":
    main()
