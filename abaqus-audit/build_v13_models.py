"""Build cumulative v13 diagnostic decks from the validated v12 keyword deck."""
from __future__ import print_function

import argparse
import os
import re


ROOT = os.path.abspath(os.path.join(os.getcwd(), "abaqus-audit"))
SOURCE = os.path.join(
    ROOT, "3d-v12",
    "doub_hydropower_part25_geometric_solids_v12_hydro_corrected.inp")
OUTPUT_DIR = os.path.join(ROOT, "3d-v13")

BX = {
    "RIGHT_BX01_I", "RIGHT_BX02_I", "RIGHT_BX03_I",
}
POWERHOUSE = {
    "POWERHOUSE_UNIT_01_I", "POWERHOUSE_UNIT_02_I",
    "POWERHOUSE_UNIT_03_I", "POWERHOUSE_UNIT_04_I",
    "POWERHOUSE_INSTALLATION_BAY_I", "TAILWATER_CHANNEL_I",
    "CUTOFF_WALL_POWERHOUSE_I", "RIGHT_CURTAIN_GROUTING_ZONE_I",
}
SPILLWAY = {
    "SPILLWAY_BAY_%02d_I" % index for index in range(1, 9)
} | {
    "SPILLWAY_STILLING_BASIN_I", "SPILLWAY_LEFT_WALL_I",
    "SPILLWAY_RIGHT_WALL_I",
}
SMALL_APPURTENANCES = {
    "FISHWAY_SEGMENT_%02d_I" % index for index in range(1, 7)
} | {
    "ECO_RELEASE_01_I", "ECO_RELEASE_02_I", "LEFT_SUBDAM_I",
}
APPURTENANT = BX | POWERHOUSE | SPILLWAY | SMALL_APPURTENANCES

VARIANT_GROUPS = {
    "core": (),
    "bx": (BX,),
    "powerhouse": (POWERHOUSE,),
    "spillway": (SPILLWAY,),
    "small": (SMALL_APPURTENANCES,),
    "full": (BX, POWERHOUSE, SPILLWAY, SMALL_APPURTENANCES),
}


def retained_appurtenances(variant):
    retained = set()
    for group in VARIANT_GROUPS[variant]:
        retained.update(group)
    return retained


def instance_name(line):
    match = re.match(r"\*Instance,\s*name=([^,]+),", line.strip(), re.I)
    return match.group(1) if match else None


def referenced_instance(line):
    if not re.match(r"\*(?:Elset|Nset),", line.strip(), re.I):
        return None
    match = re.search(r"\binstance=([^,]+)", line, re.I)
    return match.group(1).strip() if match else None


def filter_assembly(lines, suppressed):
    result = []
    in_assembly = False
    dropping_instance = False
    dropping_set = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"\*Assembly,", stripped, re.I):
            in_assembly = True
        if in_assembly and dropping_instance:
            if re.match(r"\*End Instance", stripped, re.I):
                dropping_instance = False
            continue
        if in_assembly and dropping_set:
            if stripped.startswith("*"):
                dropping_set = False
            else:
                continue
        if in_assembly:
            name = instance_name(line)
            if name in suppressed:
                dropping_instance = True
                continue
            ref = referenced_instance(line)
            if ref in suppressed:
                dropping_set = True
                continue
        result.append(line)
        if re.match(r"\*End Assembly", stripped, re.I):
            in_assembly = False
    return result


def keep_only_s01(lines):
    result = []
    seen_step = False
    for line in lines:
        if re.match(r"\*Step,", line.strip(), re.I):
            if seen_step:
                break
            seen_step = True
        result.append(line)
        if seen_step and re.match(r"\*End Step", line.strip(), re.I):
            break
    return result


def geology_only_s01_gravity(lines):
    result = []
    in_s01 = False
    replaced = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"\*Step,\s*name=S01_GEOLOGICAL_INITIAL_STRESS", stripped, re.I):
            in_s01 = True
        elif in_s01 and re.match(r"\*End Step", stripped, re.I):
            in_s01 = False
        if in_s01 and not replaced and re.match(
                r"^,\s*GRAV,\s*9\.81,\s*0\.,\s*0\.,\s*-1\.", stripped, re.I):
            result.append("ALL_GEOLOGY, GRAV, 9.81, 0., 0., -1.")
            replaced = True
        else:
            result.append(line)
    if not replaced:
        raise RuntimeError("S01 gravity line was not found")
    return result


def construction_geostatic(lines):
    result = []
    in_s02 = False
    skip_data = False
    replaced = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"\*Step,\s*name=S02_CONSTRUCTION_AND_CLOSURE", stripped, re.I):
            in_s02 = True
        elif in_s02 and re.match(r"\*End Step", stripped, re.I):
            in_s02 = False
        if skip_data:
            if stripped.startswith("*"):
                skip_data = False
            else:
                skip_data = False
                continue
        if in_s02 and re.match(r"\*Soils,", stripped, re.I):
            result.append("*Geostatic, utol=0.01")
            result.append("1., 1., 1e-05, 1.")
            skip_data = True
            replaced = True
            continue
        result.append(line)
    if not replaced:
        raise RuntimeError("S02 soils procedure was not found")
    return result


def annotate(lines, variant, suppressed):
    marker = [
        "**",
        "** V13 diagnostic variant: %s" % variant,
        "** Suppressed appurtenant instances: %s" % (
            ", ".join(sorted(suppressed)) if suppressed else "NONE"),
        "**",
    ]
    insert_at = next(index for index, line in enumerate(lines)
                     if re.match(r"\*Heading", line.strip(), re.I)) + 1
    return lines[:insert_at] + marker + lines[insert_at:]


def build(variant, full_steps=False):
    with open(SOURCE, "r", encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()
    retained = retained_appurtenances(variant)
    suppressed = APPURTENANT - retained
    lines = filter_assembly(lines, suppressed)
    lines = geology_only_s01_gravity(lines)
    lines = construction_geostatic(lines)
    if not full_steps:
        lines = keep_only_s01(lines)
    lines = annotate(lines, variant, suppressed)
    if full_steps and variant == "core":
        name = (
            "doub_hydropower_part25_geometric_solids_"
            "v13_rigidbody_geostatic_fixed.inp")
    else:
        name = "v13_%s_s01.inp" % variant
    path = os.path.join(OUTPUT_DIR, name)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    print("V13_VARIANT=%s" % variant)
    print("OUTPUT=%s" % path)
    print("RETAINED_APPURTENANCES=%d" % len(retained))
    print("SUPPRESSED_APPURTENANCES=%d" % len(suppressed))
    print("FULL_STEPS=%s" % ("YES" if full_steps else "NO"))
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("variant", choices=sorted(VARIANT_GROUPS))
    parser.add_argument("--full-steps", action="store_true")
    args = parser.parse_args()
    build(args.variant, full_steps=args.full_steps)


if __name__ == "__main__":
    main()
