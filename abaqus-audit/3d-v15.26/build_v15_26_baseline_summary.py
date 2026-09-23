"""Build the S01 engineering baseline summary from V15.24 and V15.25 outputs.

This is a read-only aggregation.  It does not edit an Abaqus model or run an
analysis case.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
V15_24_REPORT = ROOT.parent / "3d-v15.24" / "V15.24_S01_BASELINE_RESULT_REPORT.md"
V15_24_FLOW = ROOT.parent / "3d-v15.24" / "S01" / "S01_flow_rate.csv"
V15_25_STATS = ROOT.parent / "3d-v15.25" / "regional_gradient_statistics.csv"
OUTPUT_CSV = ROOT / "regional_hydraulic_response_baseline.csv"
OUTPUT_REPORT = ROOT / "S01_ENGINEERING_BASELINE_SUMMARY.md"

REGIONS = ["防渗墙", "坝基覆盖层", "岩体", "过滤层"]


def first_float(pattern: str, text: str, label: str) -> float:
    match = re.search(pattern, text, re.I)
    if not match:
        raise RuntimeError(f"Could not find {label} in V15.24 report")
    return float(match.group(1))


def read_q() -> tuple[float, str]:
    with V15_24_FLOW.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("metric") == "total_Q_magnitude":
                return float(row["value"]), row.get("unit", "model volume/time units")
    report_text = V15_24_REPORT.read_text(encoding="utf-8")
    return first_float(r"Q_magnitude\s*=\s*`?([0-9.eE+-]+)", report_text, "Q"), "model volume/time units"


def read_gradient_stats() -> dict[str, dict[str, str]]:
    with V15_25_STATS.open("r", encoding="utf-8", newline="") as handle:
        rows = {row["region"]: row for row in csv.DictReader(handle)}
    missing = [region for region in REGIONS if region not in rows]
    if missing:
        raise RuntimeError(f"Missing regional P95 rows: {', '.join(missing)}")
    return rows


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    report_text = V15_24_REPORT.read_text(encoding="utf-8")
    q, q_unit = read_q()
    max_head = first_float(r"Head maximum:\s*`?([0-9.eE+-]+)", report_text, "maximum head")
    stats = read_gradient_stats()

    source_report = str(V15_24_REPORT)
    source_stats = str(V15_25_STATS)
    rows: list[dict[str, object]] = [
        {
            "case": "S01_BASELINE_SEEPAGE",
            "metric": "total_seepage_discharge_Q",
            "region": "ALL_MODEL",
            "value": q,
            "unit": q_unit,
            "source": source_report,
            "status": "COMPUTED",
            "computed_count": "",
            "unresolved_count": "",
            "notes": "V15.24 total_Q_magnitude from scoped downstream RVF integration",
        },
        {
            "case": "S01_BASELINE_SEEPAGE",
            "metric": "maximum_hydraulic_head",
            "region": "ALL_MODEL",
            "value": max_head,
            "unit": "model length units",
            "source": source_report,
            "status": "COMPUTED",
            "computed_count": "",
            "unresolved_count": "",
            "notes": "V15.24 POR-based hydraulic head maximum",
        },
    ]
    for region in REGIONS:
        source = stats[region]
        rows.append({
            "case": "S01_BASELINE_SEEPAGE",
            "metric": "regional_p95_hydraulic_gradient",
            "region": region,
            "value": float(source["p95_gradient"]),
            "unit": "model head/length units",
            "source": source_stats,
            "status": "COMPUTED",
            "computed_count": source["computed_count"],
            "unresolved_count": source["unresolved_count"],
            "notes": "V15.25 regional gradient statistic; unresolved rows excluded from percentile",
        })

    fields = ["case", "metric", "region", "value", "unit", "source", "status",
              "computed_count", "unresolved_count", "notes"]
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    table_lines = [
        "| 指标 | 区域 | 数值 | 单位 | 状态 |",
        "|---|---|---:|---|---|",
        f"| 总渗流量 Q | 全模型 | `{q:.12g}` | {q_unit} | COMPUTED |",
        f"| 最大水头 | 全模型 | `{max_head:.12g}` | model length units | COMPUTED |",
    ]
    for region in REGIONS:
        source = stats[region]
        table_lines.append(
            f"| P95 水力梯度 | {region} | `{float(source['p95_gradient']):.12g}` | model head/length units | COMPUTED |"
        )

    report = [
        "# S01 Engineering Baseline Summary",
        "",
        "## Scope",
        "",
        "This report defines the S01 intact-model engineering baseline for later S02-S07 comparisons. It is a read-only aggregation of the completed V15.24 S01 response and V15.25 gradient validation. No geometry, mesh, material, boundary condition, input deck, or Abaqus model was modified. S02-S07 were not run.",
        "",
        f"- V15.24 source report: `{V15_24_REPORT}`",
        f"- V15.24 flow summary: `{V15_24_FLOW}`",
        f"- V15.25 regional gradient statistics: `{V15_25_STATS}`",
        "",
        "## Baseline response",
        "",
        *table_lines,
        "",
        "Q is the V15.24 `total_Q_magnitude`, obtained from the scoped downstream RVF integration. Maximum head is the V15.24 POR-derived hydraulic-head maximum. Regional P95 values are copied from the V15.25 computed-gradient population; unresolved local-geometry rows are excluded from each percentile and retained in the CSV audit columns.",
        "",
        "## Engineering use and limitations",
        "",
        "- Use this file as the intact S01 comparison baseline for later defect or degradation cases.",
        "- The filter-layer P95 gradient is `344254.635291`; V15.25 classified the associated high-gradient cluster as a localized numerical peak, not a confirmed engineering control gradient.",
        "- The baseline retains the V15.24 output limitations: gradient values were reconstructed from POR and mesh topology, not read from a native Abaqus hydraulic-gradient field; unresolved local-geometry rows remain documented.",
        "- Do not compare later cases against a silently revised baseline. Any output-definition or mesh change requires a new explicitly labeled baseline.",
        "",
        f"Machine-readable summary: `{OUTPUT_CSV}`",
    ]
    OUTPUT_REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Q={q}")
    print(f"max_head={max_head}")
    for region in REGIONS:
        print(f"p95[{region}]={stats[region]['p95_gradient']}")
    print(f"wrote={OUTPUT_CSV}")
    print(f"wrote={OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
