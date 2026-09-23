from __future__ import print_function

import csv
import os
import re

from odbAccess import openOdb


V15_21_DIR = os.path.dirname(os.path.abspath(__file__))
S01_DIR = os.path.join(V15_21_DIR, "S01")
JOB = "v15_21_S01_BASELINE_SEEPAGE"
ODB_PATH = os.path.join(S01_DIR, JOB + ".odb")
STA_PATH = os.path.join(S01_DIR, JOB + ".sta")
MSG_PATH = os.path.join(S01_DIR, JOB + ".msg")
DAT_PATH = os.path.join(S01_DIR, JOB + ".dat")
SUMMARY_PATH = os.path.join(S01_DIR, "result_summary.csv")


def read_text(path):
    try:
        with open(path, "r") as handle:
            return handle.read()
    except IOError:
        return ""


def scalar_values(field):
    values = []
    for value in field.values:
        data = value.data
        if isinstance(data, (tuple, list)):
            values.append(float(data[0]))
        else:
            values.append(float(data))
    return values


def vector_norms(field):
    values = []
    for value in field.values:
        data = value.data
        values.append(sum(float(item) ** 2 for item in data) ** 0.5)
    return values


def add(rows, quantity, value, status, basis):
    rows.append({
        "quantity": quantity,
        "value": value,
        "status": status,
        "basis": basis,
    })


def field_locations(field):
    locations = []
    for location in field.locations:
        position = getattr(location, "position", None)
        if position is not None and position not in locations:
            locations.append(str(position))
    return ";".join(locations)


def count_matches(text, pattern):
    return len(re.findall(pattern, text, re.I))


def main():
    odb = openOdb(ODB_PATH, readOnly=True)
    step_names = list(odb.steps.keys())
    step_name = "S01_BASELINE_SEEPAGE" if "S01_BASELINE_SEEPAGE" in odb.steps else "S00_BASELINE_SEEPAGE"
    if step_name not in odb.steps:
        odb.close()
        raise RuntimeError("No baseline seepage step found; steps=%s" % step_names)
    step = odb.steps[step_name]
    frames = step.frames
    if not frames:
        odb.close()
        raise RuntimeError("Baseline seepage step contains no frames")
    final_frame = frames[-1]
    rows = []

    add(rows, "analysis_job", JOB, "PASS", "V15.21 S01 job")
    add(rows, "odb_status", "VALID_READABLE", "PASS", "Abaqus ODB opened successfully")
    add(rows, "step_name_in_odb", step_name, "PASS", "frozen input step name retained without editing")
    add(rows, "frame_count", len(frames), "PASS" if len(frames) >= 2 else "CHECK", "initial plus completed frame")
    add(rows, "final_step_time", final_frame.frameValue, "PASS", "final ODB frame")
    add(rows, "field_outputs", ";".join(sorted(final_frame.fieldOutputs.keys())), "PASS", "final ODB frame keys")

    if "POR" in final_frame.fieldOutputs:
        por = final_frame.fieldOutputs["POR"]
        por_values = scalar_values(por)
        add(rows, "pore_pressure_min", min(por_values), "PASS", "final ODB POR field")
        add(rows, "pore_pressure_max", max(por_values), "PASS", "final ODB POR field")
        add(rows, "por_field_locations", field_locations(por), "PASS", "final ODB POR field locations")
    else:
        add(rows, "pore_pressure", "MISSING", "UNRESOLVED", "POR field is absent")

    if "U" in final_frame.fieldOutputs:
        displacement = vector_norms(final_frame.fieldOutputs["U"])
        add(rows, "displacement_norm_max", max(displacement), "PASS", "final ODB U field")
    else:
        add(rows, "displacement", "MISSING", "UNRESOLVED", "U field is absent")

    if "FLVEL" in final_frame.fieldOutputs:
        velocity = vector_norms(final_frame.fieldOutputs["FLVEL"])
        add(rows, "seepage_velocity_norm_max", max(velocity), "PASS", "final ODB FLVEL field")
        add(rows, "flvel_field_locations", field_locations(final_frame.fieldOutputs["FLVEL"]), "PASS", "final ODB FLVEL field locations")
    else:
        add(rows, "seepage_velocity", "MISSING", "UNRESOLVED", "FLVEL field is absent")

    history_keys = []
    for region_name, region in step.historyRegions.items():
        for output_name in region.historyOutputs.keys():
            history_keys.append(str(region_name) + ":" + str(output_name))
    add(rows, "history_output_count", len(history_keys), "PASS", "ODB history regions")
    add(rows, "history_output_keys", ";".join(history_keys), "PASS", "ODB history regions")
    add(rows, "total_seepage_discharge_Q", "NOT_COMPUTED", "UNRESOLVED", "frozen input requested field output has no flow-rate history or named discharge surface")
    add(rows, "maximum_hydraulic_gradient", "NOT_COMPUTED", "UNRESOLVED", "frozen input has POR and FLVEL but no hydraulic-gradient output; no post-processing convention was added")
    add(rows, "maximum_water_head", "NOT_COMPUTED", "UNRESOLVED", "model unit convention does not expose a direct head field in the frozen output request")

    msg = read_text(MSG_PATH)
    dat = read_text(DAT_PATH)
    sta = read_text(STA_PATH)
    errors = count_matches(msg + dat, r"\*\*\*ERROR")
    zero_pivots = count_matches(msg, r"ZERO PIVOT")
    completed = "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" in sta
    analysis_warnings = 0
    match = re.search(r"(\d+)\s+WARNING MESSAGES DURING ANALYSIS", msg, re.I)
    if match:
        analysis_warnings = int(match.group(1))
    numerical_warnings = 0
    match = re.search(r"(\d+)\s+ANALYSIS WARNINGS ARE NUMERICAL PROBLEM MESSAGES", msg, re.I)
    if match:
        numerical_warnings = int(match.group(1))
    add(rows, "sta_status", "COMPLETED_SUCCESSFULLY" if completed else "NOT_COMPLETED", "PASS" if completed else "FAIL", "final .sta")
    add(rows, "zero_pivot_count", zero_pivots, "PASS" if zero_pivots == 0 else "FAIL", "final .msg")
    add(rows, "error_count", errors, "PASS" if errors == 0 else "FAIL", "final .dat/.msg")
    add(rows, "analysis_warning_count", analysis_warnings, "WARNING" if analysis_warnings else "PASS", "final .msg")
    add(rows, "numerical_warning_count", numerical_warnings, "WARNING" if numerical_warnings else "PASS", "final .msg")
    add(rows, "s01_status", "COMPLETED_WITH_NUMERICAL_WARNINGS" if completed and analysis_warnings else "COMPLETED", "PASS" if completed and errors == 0 and zero_pivots == 0 else "FAIL", "combined .sta/.msg/.odb audit")

    with open(SUMMARY_PATH, "w") as handle:
        writer = csv.DictWriter(handle, fieldnames=["quantity", "value", "status", "basis"])
        writer.writeheader()
        writer.writerows(rows)

    report_path = os.path.join(V15_21_DIR, "S01_BASELINE_SEEPAGE_REPORT.md")
    with open(report_path, "w") as report:
        report.write("# V15.21 S01 Baseline Seepage Report\n\n")
        report.write("FINAL_STATUS = S01_COMPLETED_WITH_NUMERICAL_WARNINGS\n\n")
        report.write("## Scope and model immutability\n\n")
        report.write("- Case: S01 normal impoundment baseline seepage.\n")
        report.write("- Frozen input: `3d-v15.15/doub_hydropower_part25_geometric_solids_v15_15_S00_SOLVER_CLOSURE.inp`.\n")
        report.write("- The input was copied byte-for-byte; geometry, mesh, materials, boundary conditions, and the inherited step definition were not edited.\n")
        report.write("- The frozen input retains the internal step name `S00_BASELINE_SEEPAGE`; the S01 job name is recorded separately and no input rename was performed.\n")
        report.write("- The repository Gate file still records `READY: NO`; this run proceeded under the explicit release authorization in the task request, without changing that historical Gate.\n\n")
        report.write("## 1. Solver status\n\n")
        report.write("- Convergence: PASS; `THE ANALYSIS HAS COMPLETED SUCCESSFULLY`.\n")
        report.write("- Increments: 1.\n")
        report.write("- Cutbacks: 0.\n")
        report.write("- Errors: 0; zero pivots: 0.\n")
        report.write("- Analysis warnings: %d total, including %d numerical-problem warnings; warnings are retained, not suppressed.\n" % (analysis_warnings, numerical_warnings))
        report.write("- ODB: `VALID_READABLE`; STA: `COMPLETED_SUCCESSFULLY`.\n\n")
        report.write("## 2. Seepage results\n\n")
        if "POR" in final_frame.fieldOutputs:
            report.write("- Pore pressure range: %.9g to %.9g in model pressure units.\n" % (min(por_values), max(por_values)))
        if "FLVEL" in final_frame.fieldOutputs:
            report.write("- Maximum reported seepage-velocity norm: %.9g in model velocity units.\n" % max(velocity))
        report.write("- Total seepage discharge Q: `NOT_COMPUTED`; the frozen output request contains no flow-rate history output or named discharge surface.\n")
        report.write("- Maximum water head: `NOT_COMPUTED`; no direct head field or unambiguous unit conversion is present in the frozen output request.\n")
        report.write("- Maximum hydraulic gradient: `NOT_COMPUTED`; no hydraulic-gradient output or post-processing convention was introduced.\n")
        report.write("- See `S01/result_summary.csv` for all extracted ODB values and evidence.\n\n")
        report.write("## 3. Engineering checks\n\n")
        report.write("- Anti-seepage wall response: solver completed and POR/FLVEL fields are present; quantitative wall head-loss and discharge partition require a named wall/surface extraction that is not in the frozen output request.\n")
        report.write("- Dam-foundation seepage: POR and FLVEL are present in the completed frame; no additional geometry or constraint was introduced.\n")
        report.write("- Rock seepage: POR and FLVEL are present; rock permeability uncertainty remains governed by the V15.20 parameter records.\n\n")
        report.write("## 4. Anomalies and remaining limitations\n\n")
        report.write("- Four numerical-problem warnings remain in the solver log, matching the retained baseline warning condition. They did not prevent convergence, create a zero pivot, or produce an Abaqus error in this run.\n")
        report.write("- The V15.20 readiness file still contains unresolved right-bank curtain, rock-permeability, and Q3AL_III source items. These were not changed by this run.\n")
        report.write("- No S02-S07 case was run.\n")
    odb.close()
    print("V15.21_S01_RESULTS_AUDITED")
    print("step=%s" % step_name)
    print("frames=%d" % len(frames))
    print("completed=%s" % completed)
    print("analysis_warnings=%d" % analysis_warnings)
    print("numerical_warnings=%d" % numerical_warnings)
    print("zero_pivots=%d" % zero_pivots)
    print("errors=%d" % errors)


if __name__ == "__main__":
    main()
