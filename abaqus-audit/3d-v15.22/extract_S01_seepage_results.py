from __future__ import print_function

import csv
import os

from odbAccess import openOdb


V15_22_DIR = os.path.dirname(os.path.abspath(__file__))
S01_DIR = os.path.join(os.path.dirname(V15_22_DIR), "3d-v15.21", "S01")
ODB_PATH = os.path.join(S01_DIR, "v15_21_S01_BASELINE_SEEPAGE.odb")
SUMMARY_PATH = os.path.join(S01_DIR, "result_summary.csv")
REPORT_PATH = os.path.join(os.path.dirname(V15_22_DIR), "3d-v15.21", "S01_BASELINE_SEEPAGE_REPORT.md")

QUANTITY_PATH = os.path.join(V15_22_DIR, "S01_seepage_quantity.csv")
HEAD_PATH = os.path.join(V15_22_DIR, "S01_head_distribution.csv")
GRADIENT_PATH = os.path.join(V15_22_DIR, "S01_hydraulic_gradient.csv")


def write_csv(path, rows):
    with open(path, "wb") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["metric", "value", "status", "unit", "basis", "required_output"],
        )
        writer.writeheader()
        writer.writerows(rows)


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


def field_positions(field):
    positions = []
    for location in field.locations:
        position = getattr(location, "position", None)
        if position is not None and str(position) not in positions:
            positions.append(str(position))
    return ";".join(positions)


def flatten_history_keys(step):
    keys = []
    for region_name, region in step.historyRegions.items():
        for output_name in region.historyOutputs.keys():
            keys.append(str(region_name) + ":" + str(output_name))
    return ";".join(keys)


def main():
    if not os.path.isfile(ODB_PATH):
        raise RuntimeError("S01 ODB not found: %s" % ODB_PATH)
    if not os.path.isfile(SUMMARY_PATH):
        raise RuntimeError("S01 result summary not found: %s" % SUMMARY_PATH)
    if not os.path.isfile(REPORT_PATH):
        raise RuntimeError("S01 report not found: %s" % REPORT_PATH)

    odb = openOdb(ODB_PATH, readOnly=True)
    step_name = "S01_BASELINE_SEEPAGE" if "S01_BASELINE_SEEPAGE" in odb.steps else "S00_BASELINE_SEEPAGE"
    if step_name not in odb.steps:
        odb.close()
        raise RuntimeError("Baseline step not found; available steps: %s" % list(odb.steps.keys()))
    step = odb.steps[step_name]
    if not step.frames:
        odb.close()
        raise RuntimeError("Baseline step has no frames")

    final_frame = step.frames[-1]
    fields = final_frame.fieldOutputs
    field_names = sorted(fields.keys())
    history_keys = flatten_history_keys(step)
    has_flow_field = any(name in fields for name in ("HFL", "FLUX", "Q"))
    has_head_field = any(name in fields for name in ("HEAD", "HYDRAULIC_HEAD", "PH"))
    has_gradient_field = any(name in fields for name in ("HFL", "GRAD", "HYDRAULIC_GRADIENT"))

    por_min = "NOT_AVAILABLE"
    por_max = "NOT_AVAILABLE"
    por_locations = "MISSING"
    if "POR" in fields:
        por_values = scalar_values(fields["POR"])
        por_min = min(por_values)
        por_max = max(por_values)
        por_locations = field_positions(fields["POR"])

    flvel_max = "NOT_AVAILABLE"
    flvel_locations = "MISSING"
    if "FLVEL" in fields:
        flvel_values = vector_norms(fields["FLVEL"])
        flvel_max = max(flvel_values)
        flvel_locations = field_positions(fields["FLVEL"])

    common_required_q = "Add a flow-rate history output or define a downstream integration surface with an agreed flux extraction method"
    common_required_head = "Add a direct hydraulic-head field or provide a documented unit convention and nodal POR/elevation post-processing basis"
    common_required_gradient = "Add a hydraulic-gradient field (for example HFL where supported) or provide nodal POR, coordinates, and an agreed numerical gradient method"

    write_csv(
        QUANTITY_PATH,
        [
            {"metric": "total_seepage_discharge_Q", "value": "NOT_COMPUTED", "status": "UNRESOLVED", "unit": "NOT_AVAILABLE", "basis": "No flow-rate history output, HFL/FLUX field, or named discharge surface was present in S01 ODB", "required_output": common_required_q},
            {"metric": "maximum_FLVEL_norm", "value": flvel_max, "status": "EXTRACTED" if flvel_max != "NOT_AVAILABLE" else "UNRESOLVED", "unit": "model velocity units", "basis": "Final-frame FLVEL field; this is velocity, not integrated discharge Q", "required_output": "None for this field"},
            {"metric": "FLVEL_field_positions", "value": flvel_locations, "status": "EXTRACTED" if flvel_locations != "MISSING" else "UNRESOLVED", "unit": "n/a", "basis": "Final-frame ODB field metadata", "required_output": "None for this field"},
            {"metric": "history_output_count", "value": len(history_keys.split(";")) if history_keys else 0, "status": "EXTRACTED", "unit": "records", "basis": "Final baseline step history regions", "required_output": "A flow-rate history record is still required for Q"},
            {"metric": "field_output_names", "value": ";".join(field_names), "status": "EXTRACTED", "unit": "n/a", "basis": "Final-frame ODB field keys", "required_output": "Q-related output is absent"},
        ],
    )

    write_csv(
        HEAD_PATH,
        [
            {"metric": "maximum_water_head", "value": "NOT_COMPUTED", "status": "UNRESOLVED", "unit": "NOT_AVAILABLE", "basis": "No direct HEAD/HYDRAULIC_HEAD/PH field; POR-to-head conversion is not uniquely defined by the frozen output evidence", "required_output": common_required_head},
            {"metric": "pore_pressure_min", "value": por_min, "status": "EXTRACTED" if por_min != "NOT_AVAILABLE" else "UNRESOLVED", "unit": "model pressure units", "basis": "Final-frame POR field", "required_output": "None for POR range"},
            {"metric": "pore_pressure_max", "value": por_max, "status": "EXTRACTED" if por_max != "NOT_AVAILABLE" else "UNRESOLVED", "unit": "model pressure units", "basis": "Final-frame POR field", "required_output": "None for POR range"},
            {"metric": "POR_field_positions", "value": por_locations, "status": "EXTRACTED" if por_locations != "MISSING" else "UNRESOLVED", "unit": "n/a", "basis": "Final-frame ODB field metadata", "required_output": common_required_head},
            {"metric": "head_field_present", "value": "YES" if has_head_field else "NO", "status": "EXTRACTED", "unit": "n/a", "basis": "Final-frame ODB field key audit", "required_output": common_required_head},
        ],
    )

    write_csv(
        GRADIENT_PATH,
        [
            {"metric": "maximum_hydraulic_gradient", "value": "NOT_COMPUTED", "status": "UNRESOLVED", "unit": "NOT_AVAILABLE", "basis": "No hydraulic-gradient field was present; FLVEL is velocity and is not hydraulic gradient", "required_output": common_required_gradient},
            {"metric": "gradient_field_present", "value": "YES" if has_gradient_field else "NO", "status": "EXTRACTED", "unit": "n/a", "basis": "Final-frame ODB field key audit", "required_output": common_required_gradient},
            {"metric": "available_FLVEL_norm_max", "value": flvel_max, "status": "EXTRACTED" if flvel_max != "NOT_AVAILABLE" else "UNRESOLVED", "unit": "model velocity units", "basis": "Final-frame FLVEL field; not a gradient", "required_output": "None for FLVEL"},
            {"metric": "field_output_names", "value": ";".join(field_names), "status": "EXTRACTED", "unit": "n/a", "basis": "Final-frame ODB field keys", "required_output": "Add gradient output for the requested metric"},
        ],
    )

    odb.close()
    print("V15.22_S01_RESULTS_EXTRACTED")
    print("step=%s" % step_name)
    print("fields=%s" % ";".join(field_names))
    print("history_output_count=%d" % (len(history_keys.split(";")) if history_keys else 0))
    print("flow_field_present=%s" % has_flow_field)
    print("head_field_present=%s" % has_head_field)
    print("gradient_field_present=%s" % has_gradient_field)


if __name__ == "__main__":
    main()
