"""Build the V15.13 S00 intact baseline seepage input from the validated deck.

This generator copies the validated parts, nodes, elements, sections, materials,
assembly placements and initial ratio conditions verbatim.  It only adds
assembly node sets and one S00 steady-state coupled-flow step.  Boundary sets
are made from the transformed assembly coordinates, not from hard-coded node
labels.  No tie, spring, encastre, or point-pinning constraint is introduced.
"""

from __future__ import print_function

import csv
import hashlib
import math
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, "abaqus-audit")
V15_DIR = os.path.join(AUDIT, "3d-v15.13")
SOURCE_INP = os.path.join(
    V15_DIR,
    "doub_hydropower_part25_geometric_solids_v15_13_corrective_execution.inp",
)
S00_INP = os.path.join(
    V15_DIR,
    "doub_hydropower_part25_geometric_solids_v15_13_S00_BASELINE_SEEPAGE.inp",
)
BOUNDARY_CSV = os.path.join(V15_DIR, "v15_13_S00_boundary_condition_audit.csv")
MANIFEST_CSV = os.path.join(V15_DIR, "v15_13_S00_model_manifest.csv")

UPSTREAM_HEAD = 3076.0
DOWNSTREAM_HEAD = 3055.0
GAMMA_WATER = 9.81
Z_BIN = 1.0
POROUS_TYPES = set(("C3D8P", "C3D6P", "C3D4P", "C3D10P"))


def import_audit_modules():
    if AUDIT not in sys.path:
        sys.path.insert(0, AUDIT)
    import repair_v12_3d  # pylint: disable=import-outside-toplevel
    import complete_v15_13_corrective_execution  # pylint: disable=import-outside-toplevel
    return repair_v12_3d, complete_v15_13_corrective_execution


def csv_write(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value):
    return "%.10g" % float(value)


def node_lines(labels):
    labels = list(sorted(labels))
    return [
        "  " + ", ".join(str(label) for label in labels[start : start + 16])
        for start in range(0, len(labels), 16)
    ]


def geometry_fingerprint(parts):
    digest = hashlib.sha256()
    for part_name in sorted(parts):
        part = parts[part_name]
        digest.update(("PART\0" + part_name + "\0").encode("utf-8"))
        for label, coords in part["nodes"].items():
            digest.update(("N\0%d\0%s\n" % (label, ",".join(fmt(v) for v in coords))).encode("utf-8"))
        for etype in sorted(part["elements"]):
            digest.update(("E\0" + etype + "\0").encode("utf-8"))
            for label, conn in part["elements"][etype].items():
                digest.update(("%d\0%s\n" % (label, ",".join(str(v) for v in conn))).encode("utf-8"))
    return digest.hexdigest()


def transformed_records(part, transform):
    return [(label, tuple(transform(coords))) for label, coords in part["nodes"].items()]


def boundary_groups(records, axis_index, side, bin_size=Z_BIN):
    """Return (groups, extreme_coordinate) using global transformed coordinates."""
    values = [coords[axis_index] for _label, coords in records]
    extreme = min(values) if side == "min" else max(values)
    selected = [(label, coords) for label, coords in records if abs(coords[axis_index] - extreme) <= 1.0e-5]
    bins = {}
    for label, coords in selected:
        z = coords[2]
        key = int(math.floor(z / bin_size + 0.5))
        bins.setdefault(key, []).append((label, z))
    groups = []
    for key in sorted(bins):
        labels = [label for label, _z in bins[key]]
        z_mean = sum(z for _label, z in bins[key]) / float(len(bins[key]))
        groups.append((labels, z_mean))
    return groups, extreme


def base_nodes(records):
    zmin = min(coords[2] for _label, coords in records)
    labels = [label for label, coords in records if abs(coords[2] - zmin) <= 1.0e-5]
    return labels, zmin


def step_value(head, z):
    return GAMMA_WATER * max(head - z, 0.0)


def add_set(lines, name, instance, labels):
    block = ["*Nset, nset=%s, instance=%s" % (name, instance)]
    block.extend(node_lines(labels))
    return block


def main():
    parser, core = import_audit_modules()
    lines, parts, instances, _assembly_sets = parser.parse_deck(SOURCE_INP)
    placements, transforms = core.transforms_for(lines, parts, instances)
    porous_instances = []
    for instance_name, part_name in instances:
        part = parts[part_name]
        if any(etype.upper() in POROUS_TYPES for etype in part["elements"]):
            porous_instances.append((instance_name, part_name))
    if len(porous_instances) != 14:
        raise RuntimeError("expected 14 porous instances, found %d" % len(porous_instances))

    fingerprint = geometry_fingerprint(parts)
    assembly_blocks = []
    bc_records = []
    base_records = []
    pressure_records = []
    set_index = 0
    for instance_name, part_name in porous_instances:
        records = transformed_records(parts[part_name], transforms[instance_name])
        short = "P%02d" % set_index
        base, zmin = base_nodes(records)
        base_name = "S00_BASE_%02d" % set_index
        assembly_blocks.extend(add_set(lines, base_name, instance_name, base))
        base_records.append({
            "instance": instance_name,
            "part": part_name,
            "set": base_name,
            "node_count": len(base),
            "z_min": fmt(zmin),
        })
        upstream_groups, xmin = boundary_groups(records, 0, "min")
        downstream_groups, xmax = boundary_groups(records, 0, "max")
        for side, groups, head, extreme, prefix in (
            ("UPSTREAM", upstream_groups, UPSTREAM_HEAD, xmin, "U"),
            ("DOWNSTREAM", downstream_groups, DOWNSTREAM_HEAD, xmax, "D"),
        ):
            for group_index, (labels, zmean) in enumerate(groups):
                set_name = "S00_%s_%02d_%04d" % (prefix, set_index, group_index)
                assembly_blocks.extend(add_set(lines, set_name, instance_name, labels))
                pressure = step_value(head, zmean)
                pressure_records.append({
                    "set": set_name,
                    "side": side,
                    "instance": instance_name,
                    "part": part_name,
                    "node_count": len(labels),
                    "z_mean": zmean,
                    "pressure": pressure,
                })
            bc_records.append({
                "boundary_name": "S00_%s_%02d" % (side, set_index),
                "location": "%s x=%s transformed assembly plane; %d pressure bins" % (instance_name, fmt(extreme), len(groups)),
                "type": "pore pressure DOF 8, hydrostatic node-set values",
                "value": "p=9.81*max(%s-z,0) kPa" % (fmt(head)),
                "source": "V13/V15 S03 normal-reservoir convention; transformed Assembly coordinates",
                "status": "PASS_SOURCE_HEAD" if set_index == 11 else "ENGINEERING_ASSUMPTION_COMPONENT_BOUNDARY",
            })
        set_index += 1

    # The source deck has a single datacheck-only step at EOF.  Replace only
    # that analysis tail; all preceding parts, instances and material blocks
    # remain byte-for-byte unchanged in the generated prefix.
    step_start = None
    for index, line in enumerate(lines):
        if line.strip().lower().startswith("*step, name=datacheck_only"):
            step_start = index
            break
    if step_start is None:
        raise RuntimeError("DATACHECK_ONLY step not found")
    end_assembly = None
    for index, line in enumerate(lines):
        if index > step_start:
            break
        if line.strip().lower() == "*end assembly":
            end_assembly = index
    if end_assembly is None:
        raise RuntimeError("End Assembly not found")

    out_lines = list(lines[:end_assembly])
    out_lines.extend(["** S00_BASELINE_SEEPAGE assembly boundary sets generated from transformed coordinates"])
    out_lines.extend(assembly_blocks)
    out_lines.extend(lines[end_assembly:step_start])
    out_lines.extend([
        "** S00 baseline: intact system, no defects, no degradation, no random field",
        "** Mechanical support is applied to the actual minimum-Z face of each porous instance.",
        "** No point pinning, Encastre, spring, MPC, or Tie constraint is used.",
        "*Step, name=S00_BASELINE_SEEPAGE, nlgeom=NO",
        "*Soils, consolidation, end=SS, utol=1000.",
        "1.0e-4, 1.0e9, 1.0e-10, 1.0e7, 1.0e-6",
        "*Boundary",
    ])
    for record in base_records:
        out_lines.extend([
            "%s, 1, 1, 0." % record["set"],
            "%s, 2, 2, 0." % record["set"],
            "%s, 3, 3, 0." % record["set"],
        ])
    for record in pressure_records:
        out_lines.append("%s, 8, 8, %s" % (record["set"], fmt(record["pressure"])))
    out_lines.extend([
        "*Output, field, variable=PRESELECT",
        "*Node Output",
        "POR, RF, U",
        "*Element Output, directions=YES",
        "FLVEL, POR, S, EVOL",
        "*Output, history, variable=PRESELECT",
        "*End Step",
    ])

    with open(S00_INP, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(out_lines) + "\n")

    bc_rows = [
        {
            "boundary_name": "S00_BASE_SUPPORT",
            "location": "actual minimum-Z face of each of 14 porous instances",
            "type": "U1=U2=U3=0 on distributed base-face node sets",
            "value": "0",
            "source": "physical bottom/support face derived from transformed Assembly coordinates",
            "status": "APPLIED_PHYSICAL_SUPPORT",
        },
    ]
    bc_rows.extend(bc_records)
    bc_rows.extend([
        {
            "boundary_name": "S00_FOUNDATION_LATERAL",
            "location": "foundation geology outer faces not selected as upstream/downstream planes",
            "type": "natural hydraulic no-flow",
            "value": "not prescribed",
            "source": "closed geological domain boundary; no artificial flux boundary",
            "status": "PASS_NATURAL_NO_FLOW",
        },
        {
            "boundary_name": "S00_INITIAL_PORE_PRESSURE",
            "location": "14 existing V12_RATIO assembly sets",
            "type": "initial void ratio; no fixed initial pressure",
            "value": "ratio=0.5 inherited from v15.13 corrective deck",
            "source": "v15_13_initial_condition_audit.csv",
            "status": "AUDITED_NOT_PRESCRIBED",
        },
        {
            "boundary_name": "S00_PERMEABILITY",
            "location": "active porous materials",
            "type": "existing *Permeability definitions",
            "value": "preserved from validated deck",
            "source": "v15_13_permeability_material_audit.csv",
            "status": "PASS_WITH_ENGINEERING_ASSUMPTIONS",
        },
        {
            "boundary_name": "RIGHT_BANK_CURTAIN",
            "location": "right bank curtain",
            "type": "not represented as a new structure or boundary",
            "value": "unresolved",
            "source": "v15_13_right_bank_curtain_resolution.csv",
            "status": "UNRESOLVED",
        },
        {
            "boundary_name": "Q3AL_III",
            "location": "backfill geology",
            "type": "existing permeability and void-ratio assumption",
            "value": "preserved active deck value",
            "source": "v15_13_backfill_material_final_basis.csv",
            "status": "ENGINEERING_EQUIVALENT_ASSUMPTION",
        },
    ])
    csv_write(
        BOUNDARY_CSV,
        ["boundary_name", "location", "type", "value", "source", "status"],
        bc_rows,
    )

    csv_write(
        MANIFEST_CSV,
        ["item", "value", "status", "notes"],
        [
            {"item": "source_input", "value": os.path.basename(SOURCE_INP), "status": "VALIDATED_BASELINE", "notes": "current abaqus-audit-task HEAD; user-requested 091376e2 is not present locally or on origin"},
            {"item": "output_input", "value": os.path.basename(S00_INP), "status": "GENERATED", "notes": "S00_BASELINE_SEEPAGE only"},
            {"item": "porous_instance_count", "value": len(porous_instances), "status": "PASS", "notes": "14 actual assembly instances with C3D*P elements"},
            {"item": "geometry_fingerprint", "value": fingerprint, "status": "PRESERVED", "notes": "nodes/elements/part names and connectivity from source deck"},
            {"item": "upstream_head_m", "value": UPSTREAM_HEAD, "status": "SOURCE_HEAD", "notes": "normal reservoir convention"},
            {"item": "downstream_head_m", "value": DOWNSTREAM_HEAD, "status": "SOURCE_HEAD", "notes": "normal reservoir convention"},
            {"item": "random_field", "value": "none", "status": "PASS", "notes": "S00 intact baseline"},
            {"item": "defects", "value": "none", "status": "PASS", "notes": "S00 intact baseline"},
            {"item": "z_pressure_bin_m", "value": Z_BIN, "status": "ENGINEERING_DISCRETIZATION", "notes": "hydrostatic pressure applied at group mean elevation"},
            {"item": "assembly_set_count", "value": len(base_records) + len(pressure_records), "status": "GENERATED", "notes": "distributed base, upstream, downstream sets"},
        ],
    )
    print("Generated %s" % S00_INP)
    print("Porous instances: %d" % len(porous_instances))
    print("Boundary sets: %d" % (len(base_records) + len(pressure_records)))
    print("Geometry fingerprint: %s" % fingerprint)


if __name__ == "__main__":
    main()
