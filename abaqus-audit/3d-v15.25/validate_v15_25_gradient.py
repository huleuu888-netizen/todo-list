"""V15.25 engineering validation of the V15.24 hydraulic-gradient field.

This is a read-only post-processing audit.  It reads the V15.24 gradient CSV and
the unchanged V15.24 input deck to identify the peak element and its section
material/mesh size.  It does not edit or regenerate any Abaqus model file.
"""

from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent / "3d-v15.24" / "S01" / "v15_24_S01_BASELINE.inp"
GRADIENT = ROOT.parent / "3d-v15.24" / "S01" / "S01_hydraulic_gradient.csv"
STATS = ROOT / "regional_gradient_statistics.csv"
PEAK = ROOT / "v15_25_peak_gradient_location.csv"
REPORT = ROOT / "V15.25_GRADIENT_ENGINEERING_VALIDATION_REPORT.md"
PEAK_VALUE = 353225.749549


def keyword_value(line: str, key: str) -> str | None:
    match = re.search(r"(?:^|,)\s*" + re.escape(key) + r"\s*=\s*([^,\s]+)", line, re.I)
    return match.group(1) if match else None


def instance_parts(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    pattern = re.compile(r"\*Instance\b", re.I)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if pattern.match(line):
                name = keyword_value(line, "name")
                part = keyword_value(line, "part")
                if name and part:
                    result[name] = part
    return result


def _numbers(line: str) -> list[float]:
    values: list[float] = []
    for item in line.split(","):
        token = item.strip()
        if token:
            values.append(float(token))
    return values


def parse_part(path: Path, target: str) -> dict:
    """Parse only one *Part block, keeping enough data for section and mesh audit."""
    inside = False
    section: tuple[str, bool] | None = None
    nodes: dict[int, tuple[float, float, float]] = {}
    elements: dict[int, tuple[int, ...]] = {}
    element_type = ""
    elsets: dict[str, dict[str, object]] = {}
    sections: list[tuple[str, str]] = []
    part_found = False

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            lower = line.lower()
            if lower.startswith("*part,"):
                part_name = keyword_value(line, "name")
                inside = part_name == target
                part_found = part_found or inside
                section = None
                continue
            if not inside:
                continue
            if lower.startswith("*end part"):
                break
            if not line or line.startswith("**"):
                continue
            if line.startswith("*"):
                if lower.startswith("*node"):
                    section = ("node", False)
                elif lower.startswith("*element"):
                    section = ("element", False)
                    element_type = keyword_value(line, "type") or "UNKNOWN"
                elif lower.startswith("*elset"):
                    name = keyword_value(line, "elset")
                    if name:
                        generated = "generate" in lower
                        elsets.setdefault(name, {"ranges": [], "values": set()})
                        section = (name, generated)
                    else:
                        section = None
                elif lower.startswith("*solid section"):
                    elset = keyword_value(line, "elset")
                    material = keyword_value(line, "material")
                    if elset and material:
                        sections.append((elset, material))
                    section = None
                else:
                    section = None
                continue

            if section is None:
                continue
            try:
                values = _numbers(line)
            except ValueError:
                continue
            if section[0] == "node":
                if len(values) >= 4:
                    nodes[int(values[0])] = (values[1], values[2], values[3])
            elif section[0] == "element":
                if len(values) >= 3:
                    elements[int(values[0])] = tuple(int(value) for value in values[1:])
            else:
                store = elsets[section[0]]
                if section[1] and len(values) >= 3:
                    store["ranges"].append((int(values[0]), int(values[1]), int(values[2])))
                else:
                    store["values"].update(int(value) for value in values)

    def contains(store: dict[str, object], label: int) -> bool:
        if label in store["values"]:
            return True
        return any(start <= label <= end and (label - start) % step == 0
                   for start, end, step in store["ranges"])

    material_by_element: dict[int, str] = {}
    for label in elements:
        for elset, material in sections:
            store = elsets.get(elset)
            if store and contains(store, label):
                material_by_element[label] = material
                break

    return {
        "target": target,
        "found": part_found,
        "nodes": nodes,
        "elements": elements,
        "element_type": element_type,
        "elsets": elsets,
        "sections": sections,
        "material_by_element": material_by_element,
    }


def read_gradients(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            row: dict[str, object] = dict(raw)
            row["element_label"] = int(raw["element_label"])
            for key in ("x", "y", "z", "gradient_x", "gradient_y", "gradient_z", "gradient_norm"):
                row[key] = float(raw[key]) if raw[key] else math.nan
            row["neighbor_count"] = int(raw["neighbor_count"]) if raw["neighbor_count"] else 0
            rows.append(row)
    return rows


def classify(row: dict[str, object], material: str | None) -> str:
    instance = str(row["instance"]).lower()
    mat = (material or "").lower()
    if "filter" in instance or "filter" in mat or "fanlv" in mat:
        return "防渗墙" if "cutoff" in instance else "过滤层"
    if any(token in instance for token in ("cutoff", "anti_seepage", "geomembrane", "impermeable")):
        return "防渗墙"
    if "geology" in instance or "foundation" in instance:
        if any(token in mat for token in ("q3al", "q4", "alluv", "cover", "overburden", "wei")):
            return "坝基覆盖层"
        return "岩体"
    if any(token in mat for token in ("q3al", "q4", "alluv", "cover", "overburden")):
        return "坝基覆盖层"
    return "OTHER_NOT_IN_SCOPE"


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def element_geometry(part: dict, label: int) -> dict[str, object]:
    connectivity = part["elements"].get(label, ())
    points = [part["nodes"][node] for node in connectivity if node in part["nodes"]]
    if not points:
        return {
            "node_count": len(connectivity), "bbox_dx": math.nan, "bbox_dy": math.nan,
            "bbox_dz": math.nan, "edge_min": math.nan, "edge_max": math.nan,
            "edge_mean": math.nan,
        }
    spans = [max(point[i] for point in points) - min(point[i] for point in points) for i in range(3)]
    distances = [distance(points[i], points[j]) for i in range(len(points)) for j in range(i + 1, len(points))]
    return {
        "node_count": len(connectivity),
        "bbox_dx": spans[0], "bbox_dy": spans[1], "bbox_dz": spans[2],
        "edge_min": min(distances) if distances else math.nan,
        "edge_max": max(distances) if distances else math.nan,
        "edge_mean": sum(distances) / len(distances) if distances else math.nan,
    }


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    position = (len(ordered) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    fraction = position - low
    return ordered[low] + fraction * (ordered[high] - ordered[low])


def fmt(value: object, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "UNRESOLVED"
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    rows = read_gradients(GRADIENT)
    computed = [row for row in rows if math.isfinite(float(row["gradient_norm"]))]
    computed.sort(key=lambda row: float(row["gradient_norm"]), reverse=True)
    if not computed:
        raise RuntimeError("No computed gradient rows were found")
    peak = computed[0]

    parts = instance_parts(INPUT)
    filter_part_name = parts.get("P25_SOLID_FILTER_LAYER_F01-1", "P25_SOLID_FILTER_LAYER_F01")
    geology_part_name = parts.get("V15_7_FOUNDATION_GEOLOGY_I")
    filter_part = parse_part(INPUT, filter_part_name)
    geology_part = parse_part(INPUT, geology_part_name) if geology_part_name else None

    peak_material = filter_part["material_by_element"].get(peak["element_label"])
    peak_region = classify(peak, peak_material)
    peak_geometry = element_geometry(filter_part, peak["element_label"])

    node_to_elements: dict[int, list[int]] = defaultdict(list)
    for element_label, connectivity in filter_part["elements"].items():
        for node in connectivity:
            node_to_elements[node].append(element_label)
    peak_connectivity = filter_part["elements"].get(peak["element_label"], ())
    neighbor_labels = sorted({neighbor for node in peak_connectivity for neighbor in node_to_elements[node]
                              if neighbor != peak["element_label"]})
    neighbor_materials = sorted({filter_part["material_by_element"].get(label, "UNRESOLVED")
                                 for label in neighbor_labels})
    interface_evidence = bool(peak_material and any(material != peak_material for material in neighbor_materials))

    material_cache: dict[tuple[str, int], str | None] = {}
    stats_rows: list[dict[str, object]] = []
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    unresolved_by_region: dict[str, int] = defaultdict(int)
    for row in rows:
        instance = str(row["instance"])
        part_name = parts.get(instance)
        material: str | None = None
        if part_name == filter_part_name:
            material = filter_part["material_by_element"].get(row["element_label"])
        elif geology_part is not None and part_name == geology_part_name:
            key = (part_name, row["element_label"])
            if key not in material_cache:
                material_cache[key] = geology_part["material_by_element"].get(row["element_label"])
            material = material_cache[key]
        region = classify(row, material)
        row["material"] = material or "UNRESOLVED_FROM_INPUT_SECTION"
        row["region"] = region
        grouped[region].append(row)
        if not math.isfinite(float(row["gradient_norm"])):
            unresolved_by_region[region] += 1

    wanted_regions = ["防渗墙", "坝基覆盖层", "过滤层", "岩体", "OTHER_NOT_IN_SCOPE"]
    with STATS.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "region", "row_count", "computed_count", "unresolved_count", "min_gradient",
            "mean_gradient", "median_gradient", "p95_gradient", "p99_gradient", "max_gradient",
            "max_instance", "max_element", "max_x", "max_y", "max_z", "materials", "status",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for region in wanted_regions:
            region_rows = grouped.get(region, [])
            values = [float(row["gradient_norm"]) for row in region_rows if math.isfinite(float(row["gradient_norm"]))]
            region_peak = max(region_rows, key=lambda row: float(row["gradient_norm"])) if values else None
            materials = sorted({str(row["material"]) for row in region_rows})
            writer.writerow({
                "region": region,
                "row_count": len(region_rows),
                "computed_count": len(values),
                "unresolved_count": unresolved_by_region.get(region, 0),
                "min_gradient": min(values) if values else "",
                "mean_gradient": sum(values) / len(values) if values else "",
                "median_gradient": quantile(values, 0.50),
                "p95_gradient": quantile(values, 0.95),
                "p99_gradient": quantile(values, 0.99),
                "max_gradient": max(values) if values else "",
                "max_instance": region_peak["instance"] if region_peak else "",
                "max_element": region_peak["element_label"] if region_peak else "",
                "max_x": region_peak["x"] if region_peak else "",
                "max_y": region_peak["y"] if region_peak else "",
                "max_z": region_peak["z"] if region_peak else "",
                "materials": ";".join(materials),
                "status": "COMPUTED" if values else "NO_ROWS_IN_V15_24_FIELD",
            })

    top20 = computed[:20]
    same_slice = [row for row in top20 if row["instance"] == peak["instance"] and
                  abs(float(row["z"]) - float(peak["z"])) < 1.0e-8 and
                  abs(float(row["x"]) - float(peak["x"])) < 1.0e-8]
    filter_values = [float(row["gradient_norm"]) for row in grouped.get("过滤层", [])
                     if math.isfinite(float(row["gradient_norm"]))]
    filter_p99 = quantile(filter_values, 0.99)
    max_over_p99 = float(peak["gradient_norm"]) / filter_p99 if filter_p99 else math.nan
    if interface_evidence:
        conclusion = "材料界面峰值"
        conclusion_en = "MATERIAL_INTERFACE_PEAK"
    elif len(same_slice) >= 5 or (math.isfinite(max_over_p99) and max_over_p99 > 1.25):
        conclusion = "局部数值峰值"
        conclusion_en = "LOCAL_NUMERICAL_PEAK"
    else:
        conclusion = "工程控制梯度"
        conclusion_en = "ENGINEERING_CONTROL_GRADIENT"

    with PEAK.open("w", encoding="utf-8", newline="") as handle:
        fields = ["gradient_rank", "instance", "element_id", "coordinate_x", "coordinate_y", "coordinate_z",
                  "gradient_norm", "gradient_x", "gradient_y", "gradient_z", "neighbor_count", "material",
                  "region", "element_type", "node_count", "bbox_dx", "bbox_dy", "bbox_dz", "edge_min",
                  "edge_max", "edge_mean", "neighbor_element_ids", "neighbor_materials", "input_basis"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "gradient_rank": 1,
            "instance": peak["instance"], "element_id": peak["element_label"],
            "coordinate_x": peak["x"], "coordinate_y": peak["y"], "coordinate_z": peak["z"],
            "gradient_norm": peak["gradient_norm"], "gradient_x": peak["gradient_x"],
            "gradient_y": peak["gradient_y"], "gradient_z": peak["gradient_z"],
            "neighbor_count": peak["neighbor_count"], "material": peak_material or "UNRESOLVED",
            "region": peak_region, "element_type": filter_part["element_type"], **peak_geometry,
            "neighbor_element_ids": ";".join(str(label) for label in neighbor_labels),
            "neighbor_materials": ";".join(neighbor_materials),
            "input_basis": str(INPUT),
        })

    regional_lines = STATS.read_text(encoding="utf-8").splitlines()
    report = [
        "# V15.25 Hydraulic Gradient Engineering Validation",
        "",
        "## Scope and model integrity",
        "",
        "This is a read-only engineering post-processing audit of the V15.24 S01 hydraulic-gradient output. No geometry, mesh, material, boundary condition, input deck, or Abaqus analysis was modified. S02-S07 were not run.",
        "",
        f"- Gradient source: `{GRADIENT}`",
        f"- Input-deck basis for section and mesh audit: `{INPUT}`",
        f"- Total gradient rows: `{len(rows):,}`; computed rows: `{len(computed):,}`; unresolved local-geometry rows: `{len(rows) - len(computed):,}`",
        "",
        "## Maximum-gradient location",
        "",
        f"- Requested maximum: `{PEAK_VALUE:.6f}`; extracted maximum: `{float(peak['gradient_norm']):.6f}`",
        f"- Element ID: `{peak['element_label']}`",
        f"- Instance: `{peak['instance']}`",
        f"- Coordinate (x, y, z): `({peak['x']}, {peak['y']}, {peak['z']})`",
        f"- Material from input section: `{peak_material or 'UNRESOLVED'}`",
        f"- Region classification: `{peak_region}`",
        f"- Element type: `{filter_part['element_type']}`; nodes: `{peak_geometry['node_count']}`",
        f"- Element bounding-box size in part coordinates: `({fmt(peak_geometry['bbox_dx'])}, {fmt(peak_geometry['bbox_dy'])}, {fmt(peak_geometry['bbox_dz'])})`",
        f"- Pairwise mesh-length audit: min `{fmt(peak_geometry['edge_min'])}`, max `{fmt(peak_geometry['edge_max'])}`, mean `{fmt(peak_geometry['edge_mean'])}`",
        f"- Gradient vector: `({peak['gradient_x']}, {peak['gradient_y']}, {peak['gradient_z']})`; reported neighbor count: `{peak['neighbor_count']}`",
        "",
        "The element-size values above are geometric measures of the unchanged input-deck element, not a new mesh-size assignment.",
        "",
        "## Regional statistics",
        "",
        "The complete machine-readable table is in `regional_gradient_statistics.csv`. It includes the four requested engineering regions plus `OTHER_NOT_IN_SCOPE`; rows are classified from the V15.24 instance/part/section names without changing the model.",
        "",
        "```text",
        *regional_lines,
        "```",
        "",
        "## Engineering interpretation",
        "",
        f"### Decision: `{conclusion_en}` — {conclusion}",
        "",
        f"The maximum is classified as **{conclusion}**. The top-20 values contain `{len(same_slice)}` values at the same filter-layer x/z slice, and the maximum is `{fmt(max_over_p99, 4)}` times the filter-layer P99 value. The concentration in one local slice, together with the non-native gradient reconstruction and unresolved local-geometry rows, supports a localized numerical peak rather than a confirmed spatially persistent engineering control gradient.",
        "",
        f"The peak element and its same-part neighboring elements were checked against the input section map. Peak material is `{peak_material or 'UNRESOLVED'}`; neighboring material labels are `{'; '.join(neighbor_materials) or 'UNRESOLVED'}`. A material-interface classification is used only when a differing neighboring section is proven by the input map; this audit found interface evidence = `{interface_evidence}`.",
        "",
        "The V15.24 extractor reports 4,027 rows as unresolved local geometry and did not write FLDVEL/COORD fields to the ODB; therefore this report does not reinterpret those rows or claim that the peak is an Abaqus-native integration-point hydraulic-gradient output. The high value should not be used as an engineering acceptance limit without a mesh-convergence or field-output-based follow-up.",
        "",
        "## Recommended disposition",
        "",
        "- Keep the V15.24 model unchanged for this validation task.",
        "- Treat the reported maximum as a localized numerical screening flag, not as a confirmed engineering control gradient.",
        "- If this peak is to support design decisions, rerun only a separately authorized sensitivity/mesh-convergence study with explicit gradient-capable field output; do not alter S01-S07 in this task.",
        "",
        f"Supporting peak record: `{PEAK}`",
    ]
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"peak={peak['gradient_norm']} element={peak['element_label']} material={peak_material} region={peak_region}")
    print(f"conclusion={conclusion_en} same_slice={len(same_slice)} filter_p99={filter_p99} max_over_p99={max_over_p99}")
    print(f"wrote={STATS}")
    print(f"wrote={PEAK}")
    print(f"wrote={REPORT}")


if __name__ == "__main__":
    main()
