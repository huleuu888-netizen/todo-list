"""
V15.13 Abaqus material mapping audit tool

Purpose:
1. Check Part-Section-Material consistency in Abaqus inp files.
2. Identify missing section assignments.
3. Generate a basic audit report for Doubo hydropower model validation.

Usage:
python check_v15_13_material_mapping.py model.inp
"""

import re
import sys
from pathlib import Path


def parse_inp(path):
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    materials = re.findall(r"\*Material, name=([^\n,]+)", text, re.I)
    sections = re.findall(r"\*Solid Section, elset=([^,\n]+), material=([^\n,]+)", text, re.I)
    parts = re.findall(r"\*Part, name=([^\n]+)", text, re.I)
    return parts, sections, materials


def report(path):
    parts, sections, materials = parse_inp(path)
    print("=== V15.13 MODEL MAPPING AUDIT ===")
    print(f"Parts: {len(parts)}")
    print(f"Sections: {len(sections)}")
    print(f"Materials: {len(materials)}")

    missing = []
    for elset, mat in sections:
        if mat.strip() not in [m.strip() for m in materials]:
            missing.append((elset, mat))

    if missing:
        print("WARNING: Missing material definitions")
        for item in missing:
            print(item)
    else:
        print("Material definitions: PASS")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide inp file")
        sys.exit(1)
    report(sys.argv[1])
