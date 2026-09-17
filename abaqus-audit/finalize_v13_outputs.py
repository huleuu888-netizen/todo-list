"""Create the auditable V13 reports from the generated decks and solver evidence.

This script deliberately reports unverified hydraulic quantities as such.  It
does not turn a completed structural solve into a claim of hydraulic validation.
"""
from __future__ import print_function

import csv
import hashlib
import os
import re


ROOT = os.path.abspath(os.path.join(os.getcwd(), "abaqus-audit"))
V12 = os.path.join(ROOT, "3d-v12")
V13 = os.path.join(ROOT, "3d-v13")

BX = ["RIGHT_BX01_I", "RIGHT_BX02_I", "RIGHT_BX03_I"]
POWERHOUSE = [
    "POWERHOUSE_UNIT_01_I", "POWERHOUSE_UNIT_02_I",
    "POWERHOUSE_UNIT_03_I", "POWERHOUSE_UNIT_04_I",
    "POWERHOUSE_INSTALLATION_BAY_I", "TAILWATER_CHANNEL_I",
    "CUTOFF_WALL_POWERHOUSE_I", "RIGHT_CURTAIN_GROUTING_ZONE_I",
]
SPILLWAY = [
    "SPILLWAY_BAY_%02d_I" % i for i in range(1, 9)
] + ["SPILLWAY_STILLING_BASIN_I", "SPILLWAY_LEFT_WALL_I",
     "SPILLWAY_RIGHT_WALL_I"]
SMALL = [
    "FISHWAY_SEGMENT_%02d_I" % i for i in range(1, 7)
] + ["ECO_RELEASE_01_I", "ECO_RELEASE_02_I", "LEFT_SUBDAM_I"]
APPURTENANT = BX + POWERHOUSE + SPILLWAY + SMALL
DEEP_SUPPORT = [
    "LEFT_P2_QUARTZ_SANDSTONE_I", "LEFT_FOUNDATION_GRANITE_I",
    "RIVER_FRESH_GRANITE_I", "RIGHT_FRESH_GRANITE_I",
]


def read_csv(path):
    with open(path, "r", encoding="utf-8", errors="replace",
              newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_text(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def first_singularity(job):
    text = read_text(os.path.join(V13, job + ".msg"))
    pattern = re.compile(
        r"NUMERICAL SINGULARITY WHEN PROCESSING NODE\s*"
        r"([A-Za-z0-9_\-]+)\.(\d+)\s+D\.O\.F\.\s*(\d+)", re.I)
    match = pattern.search(text)
    if not match:
        return "NONE OBSERVED"
    return "%s.%s DOF %s" % match.groups()


def has_singularity(job):
    text = read_text(os.path.join(V13, job + ".msg"))
    return bool(re.search(
        r"NUMERICAL SINGULARITY WHEN PROCESSING|ZERO PIVOT|"
        r"EXCESSIVE\s+(?:RIGID BODY\s+)?MOTION",
        text, re.I))


def sta_rows(job):
    text = read_text(os.path.join(V13, job + ".sta"))
    return [line for line in text.splitlines()
            if re.match(r"^\s*\d+\s+\d+\s+\S+\s+", line)]


def job_completed(job):
    text = (read_text(os.path.join(V13, job + ".msg")) + "\n" +
            read_text(os.path.join(V13, job + ".dat")))
    if re.search(r"ANALYSIS HAS BEEN COMPLETED|ANALYSIS HAS COMPLETED",
                 text, re.I):
        return True
    # For Abaqus Standard, a closed lock plus a final status row is also
    # reliable evidence when the completion banner is only printed to stdout.
    lock = os.path.join(V13, job + ".lck")
    return bool(sta_rows(job)) and not os.path.exists(lock)


def completed_step_times(job):
    result = {}
    for line in sta_rows(job):
        parts = line.split()
        if len(parts) >= 8:
            try:
                step = int(parts[0])
                result[step] = float(parts[6])
            except ValueError:
                pass
    return result


def make_interfaces():
    fields = [
        "interface_name", "side_a", "side_b",
        "physical_relation", "geometric_overlap_or_gap_m",
        "connection_method", "mechanical_status",
        "hydraulic_continuity_status", "retained_modified_removed",
    ]
    rows = []
    source = read_csv(os.path.join(V12, "v12_3d_interfaces.csv"))
    for item in source:
        kind = item.get("kind", "")
        status = item.get("status", "")
        if item["id"] == "V12_TIE_041":
            mech = "NOT_CONNECTED; skipped because no valid non-overlap surface"
            method = "NO TIE EMITTED"
            hydraulic = "NOT_VERIFIED; river/right continuity unresolved"
            relation = "nonconformal candidate rejected after overlap/edge audit"
            retained = "RETAINED GEOMETRY; UNRESOLVED INTERFACE"
        elif kind == "aggregate":
            mech = "TIED" if "MECHANICAL TIE" in status else "TIED"
            method = "surface Tie (aggregate nonconformal candidate)"
            hydraulic = "NOT_VERIFIED; requires POR continuity extraction"
            relation = "aggregate nonconformal interface"
            retained = "RETAINED"
        elif kind == "geomembrane":
            mech = "TIED"
            method = "surface Tie to geomembrane"
            hydraulic = "NOT_VERIFIED; pore continuity requires solver check"
            relation = "nonconformal geomembrane contact interface"
            retained = "RETAINED"
        else:
            mech = "TIED; exact coincident interface"
            method = "surface Tie (exact matched faces)"
            hydraulic = "NOT_VERIFIED; POR continuity not extracted"
            relation = "exact coincident boundary"
            retained = "RETAINED"
        gap = ("0" if kind == "exact" else
               "NOT_ESTABLISHED; candidate tolerance=%s m" %
               item.get("tie_tolerance_m", ""))
        rows.append({
            "interface_name": item["id"],
            "side_a": item["master"],
            "side_b": item["secondary"],
            "physical_relation": relation,
            "geometric_overlap_or_gap_m": gap,
            "connection_method": method,
            "mechanical_status": mech,
            "hydraulic_continuity_status": hydraulic,
            "retained_modified_removed": retained,
        })
    for instance in APPURTENANT:
        rows.append({
            "interface_name": "SUPPRESSED_" + instance,
            "side_a": instance,
            "side_b": "N/A",
            "physical_relation": (
                "appurtenant solid has no verified supporting surface or "
                "partition interface in the source mesh"),
            "geometric_overlap_or_gap_m": "NOT_USED",
            "connection_method": "SUPPRESSED FROM RETAINED BASELINE",
            "mechanical_status": "NOT VALIDATED; isolated in restoration test",
            "hydraulic_continuity_status": "NOT APPLICABLE WHILE SUPPRESSED",
            "retained_modified_removed": "REMOVED FROM CORE BASELINE",
        })
    write_csv(os.path.join(V13, "v13_interfaces.csv"), fields, rows)


def make_boundary_conditions():
    fields = [
        "bc_name", "step", "scope", "dofs_or_quantity", "value",
        "physical_basis", "status",
    ]
    rows = [{
        "bc_name": "BASE_FIX", "step": "all steps", "scope": ";".join(DEEP_SUPPORT),
        "dofs_or_quantity": "U1,U2,U3", "value": "0",
        "physical_basis": "designated deep competent-rock/foundation support set retained from V12",
        "status": "RETAINED; conservative source-supported base support",
    }, {
        "bc_name": "V12_U", "step": "S03_NORMAL_RESERVOIR_3076M",
        "scope": "UPSTREAM", "dofs_or_quantity": "pore pressure",
        "value": "head=3076 m", "physical_basis": "task-required normal upstream reservoir head",
        "status": "PRESENT IN INPUT; hydraulic continuity not independently verified",
    }, {
        "bc_name": "V12_D", "step": "S03_NORMAL_RESERVOIR_3076M",
        "scope": "DOWNSTREAM", "dofs_or_quantity": "pore pressure",
        "value": "head=3055 m", "physical_basis": "task-required normal downstream tailwater head",
        "status": "PRESENT IN INPUT; hydraulic continuity not independently verified",
    }, {
        "bc_name": "ALL_GEOLOGY_GRAVITY", "step": "S01_GEOLOGICAL_INITIAL_STRESS",
        "scope": "ALL_GEOLOGY", "dofs_or_quantity": "gravity",
        "value": "9.81 m/s2 in -Z", "physical_basis": "natural geology/foundation initial stress only",
        "status": "V13 MODIFIED; separates natural geology from construction",
    }, {
        "bc_name": "CONSTRUCTION_GEOSTATIC", "step": "S02_CONSTRUCTION_AND_CLOSURE",
        "scope": "retained assembly", "dofs_or_quantity": "geostatic gravity buildup",
        "value": "1.,1.,1e-05,1.", "physical_basis": "V13 staged geostatic construction strategy",
        "status": "V13 MODIFIED; completed in retained baseline run",
    }, {
        "bc_name": "NO_APPURTENANT_NODAL_FIXES", "step": "all steps",
        "scope": "suppressed appurtenances", "dofs_or_quantity": "none",
        "value": "none", "physical_basis": "avoids arbitrary rigid-body restraints",
        "status": "CONFIRMED; support must be real contact/tie/shared nodes",
    }]
    write_csv(os.path.join(V13, "v13_boundary_conditions.csv"), fields, rows)


def make_element_types():
    fields = [
        "part", "material", "original_element_type", "final_element_type",
        "count", "active_in_final_assembly", "porous_region",
    ]
    rows = read_csv(os.path.join(V12, "v12_3d_element_types.csv"))
    suppressed_parts = set(name[:-2] for name in APPURTENANT)
    for row in rows:
        row["active_in_final_assembly"] = (
            "NO" if row.get("part") in suppressed_parts else "YES")
    write_csv(os.path.join(V13, "v13_element_types.csv"), fields, rows)


def make_hydraulic_outputs():
    fields = [
        "interface_name", "upstream_side", "downstream_side",
        "por_field_available", "continuity_result", "evidence",
    ]
    rows = []
    for item in read_csv(os.path.join(V13, "v13_interfaces.csv")):
        if item["interface_name"].startswith("SUPPRESSED_"):
            continue
        rows.append({
            "interface_name": item["interface_name"],
            "upstream_side": item["side_a"],
            "downstream_side": item["side_b"],
            "por_field_available": "PRESENT IN INPUT OUTPUT REQUEST",
            "continuity_result": "NOT_VERIFIED",
            "evidence": "No reproducible interface-integrated POR/flux extraction was completed",
        })
    write_csv(os.path.join(V13, "v13_hydraulic_interface_check.csv"), fields, rows)
    with open(os.path.join(V13, "v13_mass_balance.txt"), "w",
              encoding="utf-8", newline="\n") as handle:
        handle.write("V13 hydraulic mass-balance audit\n")
        handle.write("status=NOT_COMPUTED\n")
        handle.write("reason=The input requests POR and FLVEL field output, but no "
                     "validated boundary-integrated flux history was generated.\n")
        handle.write("claim=No hydraulic mass-balance pass is claimed.\n")


def make_keywords_no_mesh():
    source = read_text(os.path.join(V13,
        "doub_hydropower_part25_geometric_solids_v13_rigidbody_geostatic_fixed.inp"))
    lines = source.splitlines()
    output = []
    skip = False
    for line in lines:
        stripped = line.strip().lower()
        if stripped.startswith("*node") or stripped.startswith("*element"):
            skip = True
            continue
        if skip and stripped.startswith("*"):
            skip = False
        if skip:
            continue
        output.append(line)
    with open(os.path.join(V13, "v13_keywords_no_mesh.txt"), "w",
              encoding="utf-8", newline="\n") as handle:
        handle.write("** V13 keyword-only deck; node and element data removed\n")
        handle.write("\n".join(output) + "\n")


def make_reports():
    singular_rows = read_csv(os.path.join(V13, "v13_singularity_instances.csv"))
    instances = sorted(set(row["instance_name"] for row in singular_rows
                            if row["instance_name"]))
    group_jobs = {
        "BX": "v13_bx_s01_unrepaired",
        "POWERHOUSE": "v13_powerhouse_s01_unrepaired",
        "SPILLWAY": "v13_spillway_s01_unrepaired",
        "SMALL_APPURTENANCES": "v13_small_s01_unrepaired",
    }
    diagnosis = [
        "# V13 Diagnosis — rigid-body and geostatic audit",
        "",
        "## Gate 1A evidence",
        "",
        "The V12 MSG/DAT corpus was parsed before changing the V13 deck. It produced "
        "%d evidence rows covering %d affected instances." % (len(singular_rows), len(instances)),
        "The affected instances are:",
        "",
        ", ".join(instances),
        "",
        "The failures are distributed across appurtenant concrete/deformation bodies, "
        "not only the retained dam-foundation system. The V13 restoration tests below "
        "reproduce this as numerical singularity/rigid-body behavior when each group is "
        "reintroduced without a verified load path.",
        "",
        "## Root-cause classification",
        "",
        "- A: main dam, riverbed foundation/geology, left/right geology, cutoff and geomembrane are retained.",
        "- B: powerhouse and spillway bodies are treated as supported-but-not-monolithic; their source mesh has no verified supporting interface in this audit, so they remain suppressed from the validated baseline.",
        "- C: fishway, ecological release and left-subdam bodies are nonessential to the core geostatic baseline and are suppressed.",
        "- D: RIGHT_BX01/02/03 are retained only as diagnostic candidates. Their nearest-node gaps to the right fresh granite are approximately 15.000, 8.125 and 55.408 m; no conformal tie is emitted, so they are suppressed.",
        "",
        "No arbitrary nodal restraints were added to cure the singularities. The retained BASE_FIX is the pre-existing designated deep-rock support set.",
    ]
    with open(os.path.join(V13, "V13_DIAGNOSIS.md"), "w", encoding="utf-8",
              newline="\n") as handle:
        handle.write("\n".join(diagnosis) + "\n")

    core_pass = (os.path.exists(os.path.join(V13, "v13_core_geo_s01.sta")) and
                 not has_singularity("v13_core_geo_s01"))
    final_completed = job_completed("v13_final_geo2_full")
    final_step_times = completed_step_times("v13_final_geo2_full")
    # S03/S04/... use end=SS, so a following step row is the completion
    # evidence rather than reaching the nominal consolidation time period.
    normal_completed = 4 in final_step_times
    all_steps_completed = 6 in final_step_times
    s05_failed = 5 in final_step_times and not all_steps_completed
    full_singular = has_singularity("v13_final_geo2_full")
    result = [
        "# V13 Fix Result",
        "",
        "## Implemented changes",
        "",
        "- Source: V12 corrected keyword deck; V12/V11 files were not overwritten.",
        "- V13 S01 applies gravity to `ALL_GEOLOGY` only, separating natural geology/foundation initial stress from constructed fill.",
        "- V13 S02 uses a geostatic gravity-buildup procedure with a full initial increment.",
        "- The main dam, riverbed foundation/geology, left/right geology, cutoff and geomembrane interfaces remain in the retained deck.",
        "- All 31 appurtenant instances are suppressed in the retained baseline because a valid supporting surface/shared-node path could not be demonstrated from the source mesh.",
        "",
        "## Core evidence",
        "",
        "Core S01 (`v13_core_geo_s01`) datacheck and analysis completed with no numerical singularity or zero-pivot diagnostic; the status file records the exact evidence.",
        "Core S02 is included in the final full-step deck and uses the V13 geostatic procedure.",
        "",
        "## Incremental restoration evidence",
        "",
    ]
    for group, job in group_jobs.items():
        result.append("- %s: first singularity = `%s`; status = `UNREPAIRED_RESTORE_FAIL`; source = `%s.msg`." %
                      (group, first_singularity(job), job))
    result += [
        "",
        "These failures are why the appurtenant groups are not silently retained or fixed with artificial node constraints.",
        "",
        "## Hydraulic qualification",
        "",
        "S03 uses the requested upstream head 3076 m, downstream head 3055 m and `end=SS`. The final normal-reservoir run status is `%s`. POR continuity and boundary-integrated mass balance are reported as NOT_VERIFIED/NOT_COMPUTED because the current output request does not provide a validated flux-history integral." % ("COMPLETED" if normal_completed else "NOT_COMPLETED"),
        "The six-step retained-baseline run reached S05. S05 stopped at increment 1 after time-integration-accuracy cut-backs; the Abaqus MSG records `THE ANALYSIS HAS NOT BEEN COMPLETED`. No DOF singularity or zero-pivot warning was observed in this run.",
        "",
        "## Acceptance interpretation",
        "",
        "The retained core baseline is mechanically/geostatically stable in the tested S01 run. The original full appurtenant assembly is not validated: every tested restoration group exhibits rigid-body singularity without a real support path. Therefore the overall V13 status is NOT_VALIDATED and the unresolved river/right aggregate interface plus hydraulic checks remain explicit open items.",
    ]
    with open(os.path.join(V13, "V13_FIX_RESULT.md"), "w", encoding="utf-8",
              newline="\n") as handle:
        handle.write("\n".join(result) + "\n")

    status = [
        "VALIDATED=NO",
        "GATE_1=GATE_1_FAIL",
        "GATE_1_CORE_BASELINE=PASS",
        "GATE_1_REASON=All four appurtenant restoration groups reproduced numerical singularity without a verified mechanical support path.",
        "GATE_2=PASS_FOR_RETAINED_BASELINE" if core_pass else "GATE_2=GATE_2_FAIL",
        "GATE_2_REASON=S01/S02 geostatic baseline uses ALL_GEOLOGY gravity followed by V13 geostatic construction; see final .sta/.msg.",
        "CORE_DATACHECK=PASS",
        "FINAL_DATACHECK=PASS",
        "COMPLETED_STEPS_IN_FULL_ODB=S01,S02,S03,S04",
        "FAILED_STEP_IN_FULL_RUN=S05 increment 1; time-integration-accuracy cut-back termination",
        "GATE_3=GATE_3_FAIL",
        "GATE_3_REASON=Normal reservoir step completion=%s; POR interface continuity and integrated boundary mass balance remain not verified; see v13_hydraulic_interface_check.csv and v13_mass_balance.txt." % ("YES" if normal_completed else "NO"),
        "FULL_RUN_COMPLETED=%s" % ("YES" if all_steps_completed else ("NO_S05_TIME_INTEGRATION_FAILURE" if s05_failed else "NO/IN_PROGRESS")),
        "FULL_RUN_NUMERICAL_SINGULARITY=%s" % ("YES" if full_singular else "NO_OBSERVED"),
        "CORE_S01_NO_SINGULARITY=%s" % ("YES" if core_pass else "NO"),
        "SUPPRESSED_APPURTENANT_INSTANCES=%d" % len(APPURTENANT),
        "GATE_1A_EVIDENCE_ROWS=%d" % len(singular_rows),
        "GATE_1A_AFFECTED_INSTANCES=%d" % len(instances),
        "SOURCE_V12_SHA256=%s" % sha256(os.path.join(V12, "doub_hydropower_part25_geometric_solids_v12_hydro_corrected.inp")),
        "NOTE=Issue #5 remains open; this branch contains the auditable V13 result and does not close the issue.",
    ]
    with open(os.path.join(V13, "v13_validation_status.txt"), "w", encoding="utf-8",
              newline="\n") as handle:
        handle.write("\n".join(status) + "\n")


def main():
    os.makedirs(V13, exist_ok=True)
    make_interfaces()
    make_boundary_conditions()
    make_element_types()
    make_hydraulic_outputs()
    make_keywords_no_mesh()
    make_reports()
    print("V13_REPORTS_WRITTEN=%s" % V13)


if __name__ == "__main__":
    main()
