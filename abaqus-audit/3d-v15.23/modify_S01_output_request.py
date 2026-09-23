from __future__ import print_function

import hashlib
import os
import re


V15_23_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_INP = os.path.join(
    os.path.dirname(V15_23_DIR),
    "3d-v15.21",
    "S01",
    "v15_21_S01_BASELINE_SEEPAGE.inp",
)
OUTPUT_INP = os.path.join(V15_23_DIR, "v15_23_S01_OUTPUT_COMPLETION.inp")
AUDIT_PATH = os.path.join(V15_23_DIR, "V15.23_OUTPUT_REQUEST_GENERATION_AUDIT.md")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def is_keyword(line):
    return line.lstrip().startswith("*")


def keyword_name(line):
    if not is_keyword(line):
        return ""
    return line.lstrip()[1:].split(",", 1)[0].strip().upper()


def variable_tokens(lines, start):
    values = []
    index = start
    while index < len(lines) and not is_keyword(lines[index]):
        for token in lines[index].strip().split(","):
            token = token.strip()
            if token and token.upper() not in values:
                values.append(token.upper())
        index += 1
    return values, index


def replace_output_block(lines, node_vars, element_vars):
    output_start = None
    history_start = None
    for index, line in enumerate(lines):
        upper = line.strip().upper()
        if upper.startswith("*OUTPUT, FIELD"):
            output_start = index
        elif output_start is not None and upper.startswith("*OUTPUT, HISTORY"):
            history_start = index
            break
    if output_start is None or history_start is None:
        raise RuntimeError("Could not locate field/history output block")

    block = lines[output_start:history_start]
    node_index = None
    element_index = None
    for offset, line in enumerate(block):
        name = keyword_name(line)
        if name == "NODE OUTPUT":
            node_index = offset
        elif name == "ELEMENT OUTPUT":
            element_index = offset
    if node_index is None or element_index is None:
        raise RuntimeError("Could not locate Node Output and Element Output blocks")

    # This deck has one data block after each output keyword. Preserve all
    # unrelated lines and only replace the requested variable lists.
    new_block = []
    offset = 0
    while offset < len(block):
        line = block[offset]
        name = keyword_name(line)
        new_block.append(line)
        offset += 1
        if name == "NODE OUTPUT":
            _, end = variable_tokens(block, offset)
            new_block.append(", ".join(node_vars) + "\n")
            offset = end
        elif name == "ELEMENT OUTPUT":
            _, end = variable_tokens(block, offset)
            new_block.append(", ".join(element_vars) + "\n")
            offset = end

    return lines[:output_start] + new_block + lines[history_start:]


def main():
    if not os.path.isfile(SOURCE_INP):
        raise RuntimeError("Source S01 input not found: %s" % SOURCE_INP)

    with open(SOURCE_INP, "r") as handle:
        source_lines = handle.readlines()

    source_text = "".join(source_lines)
    source_node_vars, source_node_end = [], None
    source_element_vars, source_element_end = [], None
    for index, line in enumerate(source_lines):
        name = keyword_name(line)
        if name == "NODE OUTPUT" and source_node_end is None:
            source_node_vars, source_node_end = variable_tokens(source_lines, index + 1)
        elif name == "ELEMENT OUTPUT" and source_element_end is None:
            source_element_vars, source_element_end = variable_tokens(source_lines, index + 1)

    node_vars = list(source_node_vars)
    for variable in ("POR", "RF", "U", "COORD", "RVF", "FLDVEL"):
        if variable not in node_vars:
            node_vars.append(variable)
    element_vars = list(source_element_vars)
    for variable in ("FLVEL", "POR", "S", "EVOL"):
        if variable not in element_vars:
            element_vars.append(variable)

    output_lines = replace_output_block(source_lines, node_vars, element_vars)
    with open(OUTPUT_INP, "w") as handle:
        handle.writelines(output_lines)

    output_text = "".join(output_lines)
    with open(AUDIT_PATH, "w") as audit:
        audit.write("# V15.23 Output Request Generation Audit\n\n")
        audit.write("- Source input: `%s`\n" % os.path.basename(SOURCE_INP))
        audit.write("- Output-complete input: `%s`\n" % os.path.basename(OUTPUT_INP))
        audit.write("- Source SHA256: `%s`\n" % sha256(SOURCE_INP))
        audit.write("- Generated output SHA256: `%s`\n\n" % sha256(OUTPUT_INP))
        audit.write("## Output-only changes\n\n")
        audit.write("- Original input was read-only and was not overwritten.\n")
        audit.write("- Geometry, mesh, material data, permeability, loads, and boundary data were not edited.\n")
        audit.write("- Node output before: `%s`\n" % ", ".join(source_node_vars))
        audit.write("- Node output after: `%s`\n" % ", ".join(node_vars))
        audit.write("- Element output before: `%s`\n" % ", ".join(source_element_vars))
        audit.write("- Element output after: `%s`\n\n" % ", ".join(element_vars))
        audit.write("## Meaning of added variables\n\n")
        audit.write("- `POR`: pore fluid pressure; retained as the primary pressure field.\n")
        audit.write("- `RVF`: reaction fluid volume flux at nodes with prescribed pore pressure; this is the candidate boundary-flow quantity for Q.\n")
        audit.write("- `FLDVEL`: nodal fluid velocity; `FLVEL` remains the element integration-point effective velocity.\n")
        audit.write("- `COORD`: nodal coordinates needed to associate pressure with elevation for documented head/gradient post-processing.\n")
        audit.write("- No fabricated `HEAD` or hydraulic-gradient keyword was inserted.\n")
        audit.write("- `CFF` was not added because the source deck has no concentrated fluid-flow (`*CFLOW`) boundary; `RVF` matches the existing prescribed pore-pressure (`DOF 8`) boundaries.\n")
        audit.write("- Output block count after generation: %d field blocks and %d history blocks.\n" % (len(re.findall(r"^\*Output, field", output_text, re.I | re.M)), len(re.findall(r"^\*Output, history", output_text, re.I | re.M))))
    print("V15.23_OUTPUT_INPUT_GENERATED")
    print("source=%s" % SOURCE_INP)
    print("output=%s" % OUTPUT_INP)
    print("node_output=%s" % ",".join(node_vars))
    print("element_output=%s" % ",".join(element_vars))


if __name__ == "__main__":
    main()
