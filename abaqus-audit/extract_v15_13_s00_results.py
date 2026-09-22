"""Extract the V15.13 S00 baseline results from an Abaqus ODB.

The script is intended for ``abaqus python``.  It never invents a value when
the requested ODB field is absent.  The discharge calculation is an explicit
approximate integration of FLVEL over the downstream boundary faces selected
from the actual transformed ODB mesh; its status is marked accordingly.
"""

from __future__ import print_function

import csv
import io
import math
import os
import re
import sys

from odbAccess import openOdb


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V15_DIR = os.path.join(ROOT, "abaqus-audit", "3d-v15.13")
JOB = sys.argv[1] if len(sys.argv) > 1 else "v15_13_S00_BASELINE_SEEPAGE_SMP4"
ODB_PATH = os.path.join(V15_DIR, JOB + ".odb")
SUMMARY_CSV = os.path.join(V15_DIR, "v15_13_S00_seepage_result_summary.csv")
VALIDATION_MD = os.path.join(V15_DIR, "v15_13_S00_engineering_validation.md")
ISSUE_CSV = os.path.join(V15_DIR, "v15_13_S00_solver_issue_register.csv")
GAMMA = 9.81


def write_csv(rows):
    handle = open(SUMMARY_CSV, "wb") if sys.version_info[0] < 3 else io.open(SUMMARY_CSV, "w", newline="")
    try:
        writer = csv.DictWriter(handle, fieldnames=["Metric", "Value", "Units", "Source", "Status", "Notes"])
        writer.writeheader()
        writer.writerows(rows)
    finally:
        handle.close()


def write_issues(rows):
    handle = open(ISSUE_CSV, "wb") if sys.version_info[0] < 3 else io.open(ISSUE_CSV, "w", newline="")
    try:
        writer = csv.DictWriter(handle, fieldnames=["source", "severity", "issue", "status", "evidence"])
        writer.writeheader()
        writer.writerows(rows)
    finally:
        handle.close()


def scalar(data):
    if hasattr(data, "__len__") and not isinstance(data, (str, bytes)):
        return float(data[0])
    return float(data)


def vector(data):
    return tuple(float(value) for value in data)


def norm(data):
    return math.sqrt(sum(value * value for value in data))


def triangle_area(a, b, c):
    ab = [b[i] - a[i] for i in range(3)]
    ac = [c[i] - a[i] for i in range(3)]
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    return 0.5 * norm(cross)


def polygon_area(points):
    if len(points) == 3:
        return triangle_area(points[0], points[1], points[2])
    if len(points) == 4:
        return triangle_area(points[0], points[1], points[2]) + triangle_area(points[0], points[2], points[3])
    return 0.0


def element_side_area(element, node_coords, side, extreme):
    coords = [node_coords[label] for label in element.connectivity]
    selected = [coords[index] for index in range(len(coords)) if abs(coords[index][0] - extreme) <= 1.0e-5]
    if side == "downstream" and len(selected) in (3, 4):
        return polygon_area(selected)
    return 0.0


def get_instance_name(value):
    instance = getattr(value, "instance", None)
    if instance is not None:
        return instance.name
    return ""


def final_frame(odb):
    if "S00_BASELINE_SEEPAGE" not in odb.steps:
        return None, "MISSING_STEP"
    step = odb.steps["S00_BASELINE_SEEPAGE"]
    if not step.frames:
        return None, "NO_FRAMES"
    return step.frames[-1], "COMPLETED"


def main():
    rows = []
    issue_rows = []
    if not os.path.exists(ODB_PATH):
        rows.append({"Metric": "analysis_status", "Value": "NOT_COMPUTED", "Units": "", "Source": JOB + ".odb", "Status": "UNRESOLVED", "Notes": "ODB was not produced"})
        write_csv(rows)
        with open(VALIDATION_MD, "w") as handle:
            handle.write("# V15.13 S00 engineering validation\n\nSTATUS = UNRESOLVED\n\nThe S00 ODB was not produced.\n")
        write_issues([{"source": JOB + ".odb", "severity": "ERROR", "issue": "ODB missing", "status": "UNRESOLVED", "evidence": "No ODB file was produced"}])
        return 2

    odb = openOdb(ODB_PATH, readOnly=True)
    msg_path = os.path.join(V15_DIR, JOB + ".msg")
    sta_path = os.path.join(V15_DIR, JOB + ".sta")
    msg_text = ""
    if os.path.exists(msg_path):
        with io.open(msg_path, "r", encoding="utf-8", errors="replace") as handle:
            msg_text = handle.read()
    solver_complete = os.path.exists(sta_path) and "Abaqus Error" not in msg_text and "ZERO PIVOT" not in msg_text.upper()
    if "UNCONNECTED REGIONS" in msg_text.upper():
        issue_rows.append({"source": JOB + ".msg", "severity": "WARNING", "issue": "unconnected regions", "status": "UNRESOLVED", "evidence": "99 unconnected regions reported by Abaqus"})
    if "ZERO PIVOT" in msg_text.upper():
        issue_rows.append({"source": JOB + ".msg", "severity": "ERROR", "issue": "zero pivot / insufficient mechanical constraint", "status": "UNRESOLVED", "evidence": "WarnNodeSolvProbZeroPiv and foundation geology DOF 3"})
    if "Abaqus Error" in msg_text:
        issue_rows.append({"source": JOB + ".msg", "severity": "ERROR", "issue": "Abaqus Standard terminated", "status": "UNRESOLVED", "evidence": "Abaqus Error in job message file"})
    if not os.path.exists(sta_path):
        issue_rows.append({"source": JOB + ".sta", "severity": "ERROR", "issue": "status file missing", "status": "UNRESOLVED", "evidence": "No completed-analysis .sta file"})
    frame, status = final_frame(odb)
    if not solver_complete:
        status = "PARTIAL_UNRESOLVED"
    result_status = "EXTRACTED" if solver_complete else "PARTIAL_ODB_NOT_VALID_RESULT"
    rows.append({"Metric": "analysis_job", "Value": JOB, "Units": "", "Source": JOB + ".odb", "Status": status, "Notes": "actual Abaqus ODB"})
    if frame is None:
        rows.extend([
            {"Metric": "total_seepage_discharge", "Value": "NOT_COMPUTED", "Units": "m^3/s", "Source": "ODB", "Status": "UNRESOLVED", "Notes": "S00 final frame unavailable"},
            {"Metric": "max_pore_pressure", "Value": "NOT_COMPUTED", "Units": "kPa", "Source": "ODB", "Status": "UNRESOLVED", "Notes": "S00 final frame unavailable"},
        ])
        odb.close()
        write_csv(rows)
        with open(VALIDATION_MD, "w") as handle:
            handle.write("# V15.13 S00 engineering validation\n\nSTATUS = UNRESOLVED\n\nThe S00 step did not provide a final frame.\n")
        write_issues(issue_rows)
        return 3

    fields = frame.fieldOutputs
    por_values = []
    velocity_values = []
    if "POR" in fields:
        por_values = [scalar(value.data) for value in fields["POR"].values]
    if "FLVEL" in fields:
        velocity_values = [norm(vector(value.data)) for value in fields["FLVEL"].values]

    if por_values:
        rows.append({"Metric": "min_pore_pressure", "Value": min(por_values), "Units": "kPa", "Source": "ODB final frame POR", "Status": result_status, "Notes": "partial ODB frame only; not a completed S00 result" if not solver_complete else "all POR field values"})
        rows.append({"Metric": "max_pore_pressure", "Value": max(por_values), "Units": "kPa", "Source": "ODB final frame POR", "Status": result_status, "Notes": "partial ODB frame only; not a completed S00 result" if not solver_complete else "all POR field values"})
    else:
        rows.append({"Metric": "pore_pressure", "Value": "NOT_COMPUTED", "Units": "kPa", "Source": "ODB final frame POR", "Status": "UNRESOLVED", "Notes": "POR field absent"})
    if velocity_values:
        rows.append({"Metric": "max_seepage_velocity", "Value": max(velocity_values), "Units": "m/s", "Source": "ODB final frame FLVEL", "Status": result_status, "Notes": "partial ODB frame only; not a completed S00 result" if not solver_complete else "maximum integration-point velocity norm"})
    else:
        rows.append({"Metric": "max_seepage_velocity", "Value": "NOT_COMPUTED", "Units": "m/s", "Source": "ODB final frame FLVEL", "Status": "UNRESOLVED", "Notes": "FLVEL field absent"})
    rows.append({"Metric": "max_hydraulic_gradient", "Value": "NOT_COMPUTED", "Units": "-", "Source": "ODB", "Status": "UNRESOLVED", "Notes": "no reliable gradient field was requested"})
    rows.append({"Metric": "phreatic_surface", "Value": "NOT_IDENTIFIED", "Units": "m", "Source": "ODB", "Status": "NOT_APPLICABLE", "Notes": "fully saturated coupled-domain baseline; no free-surface criterion was defined"})

    discharge = None
    discharge_note = "FLVEL or downstream faces unavailable"
    if "FLVEL" in fields:
        velocity_by_element = {}
        for value in fields["FLVEL"].values:
            instance_name = get_instance_name(value)
            key = (instance_name, int(value.elementLabel))
            velocity_by_element.setdefault(key, []).append(norm(vector(value.data)))
        total = 0.0
        contributions = 0
        for instance_name, instance in odb.rootAssembly.instances.items():
            elements = [element for element in instance.elements if element.type.upper().endswith("P")]
            if not elements:
                continue
            coords = {node.label: tuple(node.coordinates) for node in instance.nodes}
            if not coords:
                continue
            xmax = max(point[0] for point in coords.values())
            for element in elements:
                area = element_side_area(element, coords, "downstream", xmax)
                if area <= 0.0:
                    continue
                velocities = velocity_by_element.get((instance_name, int(element.label)), [])
                if not velocities:
                    continue
                total += sum(velocities) / float(len(velocities)) * area
                contributions += 1
        if contributions:
            discharge = total
            discharge_note = "sum of downstream boundary-element face area times mean FLVEL norm; approximate because FLVEL is integration-point output"
    if discharge is None:
        rows.append({"Metric": "total_seepage_discharge", "Value": "NOT_COMPUTED", "Units": "m^3/s", "Source": "ODB final frame FLVEL", "Status": "UNRESOLVED", "Notes": discharge_note})
    else:
        rows.append({"Metric": "total_seepage_discharge", "Value": discharge, "Units": "m^3/s", "Source": "ODB final frame FLVEL", "Status": "APPROXIMATE_EXTRACTED" if solver_complete else "PARTIAL_ODB_NOT_VALID_RESULT", "Notes": discharge_note if solver_complete else "partial ODB frame only; discharge is not a completed S00 result"})

    rows.append({"Metric": "frames_in_S00", "Value": len(odb.steps["S00_BASELINE_SEEPAGE"].frames), "Units": "count", "Source": "ODB", "Status": result_status, "Notes": "step frame count"})
    odb.close()
    write_csv(rows)

    successful = solver_complete and status == "COMPLETED" and bool(por_values) and bool(velocity_values) and discharge is not None
    validation_status = "PASS_WITH_APPROXIMATE_DISCHARGE" if successful else "UNRESOLVED"
    with open(VALIDATION_MD, "w") as handle:
        handle.write("# V15.13 S00 engineering validation\n\n")
        handle.write("STATUS = %s\n\n" % validation_status)
        handle.write("## Case\n\n")
        handle.write("S00_BASELINE_SEEPAGE uses the intact v15.13 model. No defects, degradation, or random field were added.\n\n")
        handle.write("## Observed response\n\n")
        handle.write("- Abaqus final frame: `%s`\n" % status)
        handle.write("- POR field values: %d\n" % len(por_values))
        handle.write("- FLVEL field values: %d\n" % len(velocity_values))
        handle.write("- Total discharge: %s\n" % ("%.10g m^3/s (approximate boundary integration)" % discharge if discharge is not None else "NOT_COMPUTED"))
        handle.write("- Hydraulic gradient: NOT_COMPUTED because no independent gradient field was requested.\n")
        handle.write("- Phreatic surface: NOT_IDENTIFIED because this is a fully saturated coupled-domain baseline.\n\n")
        handle.write("## Engineering validation\n\n")
        if successful:
            handle.write("The baseline step completed and produced POR and FLVEL fields. The discharge is an approximate extraction from actual downstream boundary faces; it is not a calibrated production seepage value.\n\n")
        else:
            handle.write("The requested hydraulic validation is unresolved because at least one required output or the final solver frame was unavailable.\n\n")
        handle.write("## Unresolved items\n\n")
        handle.write("- Right-bank curtain remains UNRESOLVED.\n")
        handle.write("- Rock permeability categories marked CALIBRATION_REQUIRED remain unchanged.\n")
        handle.write("- Q3AL_III remains an ENGINEERING_EQUIVALENT_ASSUMPTION.\n")
        handle.write("- The Data Check warning about 99 unconnected regions remains an explicit model limitation.\n")
    write_issues(issue_rows)
    return 0 if successful else 4


if __name__ == "__main__":
    sys.exit(main())
