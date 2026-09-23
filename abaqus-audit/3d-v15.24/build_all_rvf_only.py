from __future__ import print_function

import os
import re


ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(os.path.dirname(ROOT), '3d-v15.23', 'v15_23_S01_OUTPUT_COMPLETION.inp')
TARGET = os.path.join(ROOT, 'S01', 'v15_24_S01_BASELINE_RVF_ONLY.inp')


def parse_downstream_sets(lines):
    part_types = {}
    current_part = None
    instances = {}
    found = []
    for line in lines:
        match = re.match(r'\*Part,\s*name=([^,\s]+)', line, re.I)
        if match:
            current_part = match.group(1).strip()
            continue
        match = re.match(r'\*Element,\s*type=([^,\s]+)', line, re.I)
        if match and current_part and current_part not in part_types:
            part_types[current_part] = match.group(1).strip().upper()
            continue
        match = re.match(r'\*Instance,\s*name=([^,\s]+),\s*part=([^,\s]+)', line, re.I)
        if match:
            instances[match.group(1).strip()] = match.group(2).strip()
            continue
        match = re.match(r'\*Nset,\s*nset=(S00_D_[^,\s]+),\s*instance=([^,\s]+)', line, re.I)
        if match:
            name = match.group(1).strip()
            part = instances.get(match.group(2).strip(), '')
            if part_types.get(part, '') in ('C3D8P', 'C3D6P'):
                found.append(name)
    result = []
    seen = set()
    for name in found:
        if name not in seen:
            result.append(name)
            seen.add(name)
    return result


def main():
    with open(SOURCE, 'r') as handle:
        lines = handle.readlines()
    sets = parse_downstream_sets(lines)
    field_start = None
    history_start = None
    for index, line in enumerate(lines):
        upper = line.strip().upper()
        if upper.startswith('*OUTPUT, FIELD'):
            field_start = index
        elif field_start is not None and upper.startswith('*OUTPUT, HISTORY'):
            history_start = index
            break
    if field_start is None or history_start is None:
        raise RuntimeError('Could not locate output block')
    block = lines[field_start:history_start]
    element_index = None
    for offset, line in enumerate(block):
        if line.strip().upper().startswith('*ELEMENT OUTPUT'):
            element_index = offset
            break
    if element_index is None:
        raise RuntimeError('Could not locate element output block')
    output = ['*Output, field, variable=PRESELECT\n', '*Node Output\n', 'POR, RF, U\n']
    for name in sets:
        output.extend(['*Node Output, NSET=%s\n' % name, 'RVF\n'])
    output.extend(block[element_index:])
    with open(TARGET, 'w') as handle:
        handle.writelines(lines[:field_start] + output + lines[history_start:])
    print('ALL_RVF_ONLY_INPUT_GENERATED')
    print('DOWNSTREAM_SET_COUNT=%d' % len(sets))
    print('TARGET=%s' % TARGET)


if __name__ == '__main__':
    main()
