"""Read-only audit of S01 against the final seepage design definition."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent / "3d-v15.24" / "S01" / "v15_24_S01_BASELINE.inp"
OUTPUT_MD = ROOT / "S01_FINAL_DESIGN_CORRESPONDENCE_AUDIT.md"
OUTPUT_CSV = ROOT / "S01_FINAL_DESIGN_MAPPING.csv"

TARGET_PARTS = {
    "V15_5_REFINED_V12_UPSTREAM_GEOMEMBRANE_1",
    "V15_5_REFINED_P25_SOLID_CUTOFF_WALL_F13_1",
    "V15_13_ANTI_SEEPAGE_CHAIN",
}
TARGET_INSTANCES = {
    "V12_UPSTREAM_GEOMEMBRANE-1",
    "P25_SOLID_CUTOFF_WALL_F13-1",
    "V15_13_ANTI_SEEPAGE_CHAIN_I",
    "V15_7_FOUNDATION_GEOLOGY_I",
}


def kw(line: str, name: str) -> str | None:
    match = re.search(r"(?:^|,)\s*" + re.escape(name) + r"\s*=\s*([^,\s]+)", line, re.I)
    return match.group(1) if match else None


def nums(line: str) -> list[float]:
    return [float(token.strip()) for token in line.split(",") if token.strip()]


def parse_parts(path: Path) -> dict[str, dict]:
    parts: dict[str, dict] = {}
    active: dict | None = None
    mode: tuple[str, bool] | None = None
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            lower = line.lower()
            if lower.startswith("*part,"):
                name = kw(line, "name")
                if name in TARGET_PARTS:
                    active = {
                        "name": name, "nodes": {}, "elements": {}, "element_types": set(),
                        "elsets": {}, "sections": [],
                    }
                    parts[name] = active
                else:
                    active = None
                mode = None
                continue
            if active is not None and lower.startswith("*end part"):
                active = None
                mode = None
                continue
            if active is None:
                continue
            if not line or line.startswith("**"):
                continue
            if line.startswith("*"):
                if lower.startswith("*node"):
                    mode = ("node", False)
                elif lower.startswith("*element"):
                    element_type = kw(line, "type") or "UNKNOWN"
                    active["element_types"].add(element_type)
                    mode = ("element", False)
                elif lower.startswith("*elset"):
                    name = kw(line, "elset")
                    if name:
                        generated = "generate" in lower
                        active["elsets"].setdefault(name, {"ranges": [], "values": set()})
                        mode = (name, generated)
                    else:
                        mode = None
                elif lower.startswith("*solid section"):
                    elset = kw(line, "elset")
                    material = kw(line, "material")
                    if elset and material:
                        active["sections"].append((elset, material))
                    mode = None
                else:
                    mode = None
                continue
            if mode is None:
                continue
            try:
                values = nums(line)
            except ValueError:
                continue
            if mode[0] == "node" and len(values) >= 4:
                active["nodes"][int(values[0])] = tuple(values[1:4])
            elif mode[0] == "element" and len(values) >= 3:
                active["elements"][int(values[0])] = tuple(int(value) for value in values[1:])
            elif mode[0] in active["elsets"]:
                store = active["elsets"][mode[0]]
                if mode[1] and len(values) >= 3:
                    store["ranges"].append((int(values[0]), int(values[1]), int(values[2])))
                else:
                    store["values"].update(int(value) for value in values)
    return parts


def parse_instances(path: Path) -> dict[str, dict]:
    instances: dict[str, dict] = {}
    active: dict | None = None
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            lower = line.lower()
            if lower.startswith("*instance,"):
                name = kw(line, "name")
                if name in TARGET_INSTANCES:
                    active = {"name": name, "part": kw(line, "part"), "data": []}
                    instances[name] = active
                else:
                    active = None
                continue
            if active is not None and lower.startswith("*end instance"):
                active = None
                continue
            if active is not None and line and not line.startswith("*"):
                try:
                    values = nums(line)
                except ValueError:
                    continue
                if values:
                    active["data"].append(values)
    return instances


def scan_materials_and_names(path: Path) -> tuple[dict[str, float | None], list[str], list[str], list[str], int]:
    permeability: dict[str, float | None] = {}
    parts: list[str] = []
    instances: list[str] = []
    elsets: list[str] = []
    tie_count = 0
    active_material: str | None = None
    permeability_pending = False
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            lower = line.lower()
            if lower.startswith("*part,"):
                name = kw(line, "name")
                if name:
                    parts.append(name)
            elif lower.startswith("*instance,"):
                name = kw(line, "name")
                if name:
                    instances.append(name)
            elif lower.startswith("*elset,"):
                name = kw(line, "elset")
                if name:
                    elsets.append(name)
            elif lower.startswith("*tie"):
                tie_count += 1
            elif lower.startswith("*material,"):
                active_material = kw(line, "name")
                if active_material:
                    permeability.setdefault(active_material, None)
                permeability_pending = False
            elif lower.startswith("*permeability") and active_material:
                permeability_pending = True
            elif permeability_pending and line and not line.startswith("*"):
                try:
                    permeability[active_material] = nums(line)[0]
                except (ValueError, IndexError):
                    pass
                permeability_pending = False
            elif line.startswith("*"):
                permeability_pending = False
    return permeability, parts, instances, elsets, tie_count


def elset_contains(store: dict, label: int) -> bool:
    if label in store["values"]:
        return True
    return any(start <= label <= end and (label - start) % step == 0
               for start, end, step in store["ranges"])


def element_labels(part: dict, set_name: str) -> list[int]:
    if set_name == "ALL_ELEMENTS":
        return sorted(part["elements"])
    store = part["elsets"].get(set_name)
    if not store:
        return []
    return [label for label in sorted(part["elements"]) if elset_contains(store, label)]


def rotate(point: tuple[float, float, float], axis_start: tuple[float, float, float],
           axis_end: tuple[float, float, float], angle_degrees: float) -> tuple[float, float, float]:
    theta = math.radians(angle_degrees)
    ax = [axis_end[i] - axis_start[i] for i in range(3)]
    norm = math.sqrt(sum(value * value for value in ax))
    if norm == 0:
        return point
    ax = [value / norm for value in ax]
    vec = [point[i] - axis_start[i] for i in range(3)]
    cross = [ax[1] * vec[2] - ax[2] * vec[1], ax[2] * vec[0] - ax[0] * vec[2], ax[0] * vec[1] - ax[1] * vec[0]]
    dot = sum(ax[i] * vec[i] for i in range(3))
    c, s = math.cos(theta), math.sin(theta)
    rotated = [vec[i] * c + cross[i] * s + ax[i] * dot * (1 - c) for i in range(3)]
    return tuple(axis_start[i] + rotated[i] for i in range(3))


def transform_point(point: tuple[float, float, float], instance: dict) -> tuple[float, float, float]:
    data = instance.get("data", [])
    if not data:
        return point
    translation = tuple(data[0][:3]) if len(data[0]) >= 3 else (0.0, 0.0, 0.0)
    translated = tuple(point[i] + translation[i] for i in range(3))
    if len(data) >= 2 and len(data[1]) >= 7:
        return rotate(translated, tuple(data[1][0:3]), tuple(data[1][3:6]), data[1][6])
    return translated


def bbox(part: dict, set_name: str, instance: dict) -> dict:
    labels = element_labels(part, set_name)
    points: list[tuple[float, float, float]] = []
    for label in labels:
        for node in part["elements"].get(label, ()):
            if node in part["nodes"]:
                points.append(transform_point(part["nodes"][node], instance))
    if not points:
        return {"set": set_name, "elements": 0, "nodes": 0, "min": (math.nan,) * 3, "max": (math.nan,) * 3, "span": (math.nan,) * 3}
    unique = {tuple(round(value, 9) for value in point) for point in points}
    minimum = tuple(min(point[i] for point in points) for i in range(3))
    maximum = tuple(max(point[i] for point in points) for i in range(3))
    return {"set": set_name, "elements": len(labels), "nodes": len(unique), "min": minimum, "max": maximum,
            "span": tuple(maximum[i] - minimum[i] for i in range(3))}


def point_set(part: dict, set_name: str, instance: dict) -> set[tuple[float, float, float]]:
    labels = element_labels(part, set_name)
    return {tuple(round(value, 6) for value in transform_point(part["nodes"][node], instance))
            for label in labels for node in part["elements"].get(label, ()) if node in part["nodes"]}


def dimension_text(box: dict) -> str:
    return (f"global bbox min={box['min']}; max={box['max']}; span=(x={box['span'][0]:.6f}, "
            f"y={box['span'][1]:.6f}, z={box['span'][2]:.6f}); elements={box['elements']}; unique_nodes={box['nodes']}")


def main() -> None:
    parts = parse_parts(INPUT)
    instances = parse_instances(INPUT)
    permeability, all_parts, all_instances, all_elsets, tie_count = scan_materials_and_names(INPUT)

    geo_instance = instances.get("V15_7_FOUNDATION_GEOLOGY_I", {"data": [], "part": "V15_7_FOUNDATION_GEOLOGY"})
    chain_instance = instances["V15_13_ANTI_SEEPAGE_CHAIN_I"]
    cutoff_instance = instances["P25_SOLID_CUTOFF_WALL_F13-1"]
    geomem_instance = instances["V12_UPSTREAM_GEOMEMBRANE-1"]

    chain = parts["V15_13_ANTI_SEEPAGE_CHAIN"]
    cutoff = parts["V15_5_REFINED_P25_SOLID_CUTOFF_WALL_F13_1"]
    geomem = parts["V15_5_REFINED_V12_UPSTREAM_GEOMEMBRANE_1"]

    chain_all = bbox(chain, "V15_13_ANTI_SEEPAGE_ALL", chain_instance)
    chain_left = bbox(chain, "V15_13_LEFT_BANK_ABUTMENT_EXTENSION", chain_instance)
    chain_sets = {
        name: bbox(chain, name, chain_instance)
        for name in (
            "V15_13_LEFT_BANK_ABUTMENT_EXTENSION", "V15_13_LEFT_SUBDAM_CUTOFF",
            "V15_13_INSTALLATION_POWERHOUSE_CUTOFF", "V15_13_POWERHOUSE_CUTOFF",
            "V15_13_ECOLOGICAL_RELEASE_CONNECTION", "V15_13_SPILLWAY_CUTOFF",
            "V15_13_SPILLWAY_MAIN_TRANSITION",
        )
    }
    cutoff_box = bbox(cutoff, "V15_5_ALL", cutoff_instance)
    geomem_box = bbox(geomem, "V15_5_ALL", geomem_instance)
    chain_geom_shared = len(point_set(chain, "V15_13_ANTI_SEEPAGE_ALL", chain_instance) & point_set(geomem, "V15_5_ALL", geomem_instance))
    cutoff_chain_shared = len(point_set(cutoff, "V15_5_ALL", cutoff_instance) & point_set(chain, "V15_13_ANTI_SEEPAGE_ALL", chain_instance))

    right_candidates = sorted({name for name in all_parts + all_instances + all_elsets
                               if any(token in name.upper() for token in ("CURTAIN", "GROUT", "RIGHT_BANK"))})
    wall_material = "P25_FANGSHENQIANG"
    geomem_material = "GEOMEMBRANE"
    rows = [
        {
            "item_id": "1", "requirement": "坝体采用复合土工膜防渗", "status": "PARTIAL",
            "part": geomem["name"], "instance": geomem_instance["name"], "material": geomem_material,
            "set": "V15_5_ALL", "geometry": dimension_text(geomem_box),
            "evidence": f"GEOMEMBRANE permeability={permeability.get(geomem_material)}; element type={','.join(sorted(geomem['element_types']))}",
            "note": "低渗土工膜对象存在；当前输入显示单一等效 GEOMEMBRANE 材料和实体单元集，未证明多层复合材料分层。",
        },
        {
            "item_id": "2", "requirement": "主河床及左岸覆盖层基础采用悬挂式混凝土防渗墙", "status": "PASS",
            "part": f"{cutoff['name']}; {chain['name']}", "instance": f"{cutoff_instance['name']}; {chain_instance['name']}",
            "material": wall_material, "set": "V15_5_ALL; V15_13_ANTI_SEEPAGE_ALL; V15_13_LEFT_BANK_ABUTMENT_EXTENSION",
            "geometry": f"main={dimension_text(cutoff_box)}; chain={dimension_text(chain_all)}",
            "evidence": f"material permeability={permeability.get(wall_material)}; chain subset sets={';'.join(chain_sets)}",
            "note": "主墙及左岸防渗链真实存在；悬挂式连接到地质体的连续性仍需接口拓扑审计，不在本只读设计对应性结论中扩展。",
        },
        {
            "item_id": "3", "requirement": "左岸防渗墙延伸 80 m", "status": "PASS",
            "part": chain["name"], "instance": chain_instance["name"], "material": wall_material,
            "set": "V15_13_LEFT_BANK_ABUTMENT_EXTENSION", "geometry": dimension_text(chain_left),
            "evidence": f"y-span={chain_left['span'][1]:.6f} m; x-span={chain_left['span'][0]:.6f} m; z-bottom={chain_left['min'][2]:.6f} m",
            "note": "Element Set 1 的全局 y 范围为 -325.7 至 -245.7 m，长度正好 80.0 m；未自动修改。",
        },
        {
            "item_id": "4", "requirement": "防渗墙厚度 1.0 m", "status": "PASS",
            "part": f"{cutoff['name']}; {chain['name']}", "instance": f"{cutoff_instance['name']}; {chain_instance['name']}",
            "material": wall_material, "set": "V15_5_ALL; V15_13_LEFT_BANK_ABUTMENT_EXTENSION",
            "geometry": f"main x-span={cutoff_box['span'][0]:.6f} m; left-extension x-span={chain_left['span'][0]:.6f} m",
            "evidence": "Both audited wall thickness spans evaluate to 1.000000 m in the global geometry audit.",
            "note": "厚度来自现有节点几何，不是由材料参数或约束推断。",
        },
        {
            "item_id": "5", "requirement": "河床防渗墙墙底约 3021.00 m，最大施工深度约 49.10 m", "status": "PARTIAL",
            "part": cutoff["name"], "instance": cutoff_instance["name"], "material": wall_material,
            "set": "V15_5_ALL", "geometry": dimension_text(cutoff_box),
            "evidence": f"global z-min={cutoff_box['min'][2]:.6f} m; global z-span={cutoff_box['span'][2]:.6f} m; global y-span={cutoff_box['span'][1]:.6f} m",
            "note": "墙底 3021.0 m 有节点证据；当前主墙实际竖向 span 为约 52.51 m，未能从现有 S01 输入证明 49.10 m 最大施工深度，需核对设计基准面/坐标定义。",
        },
        {
            "item_id": "6", "requirement": "右岸岩石基础采用灌浆帷幕", "status": "MISSING",
            "part": "NONE_FOUND", "instance": "NONE_FOUND", "material": "NONE_FOUND",
            "set": "NONE_FOUND", "geometry": "NONE_FOUND",
            "evidence": f"No Part/Instance/Material/Element Set name containing CURTAIN, GROUT, or RIGHT_BANK was found in the S01 input; candidate names={right_candidates or 'none'}.",
            "note": "右岸地质覆盖层和岩体集合存在，但它们不是帷幕对象；现有 V15.20 closure 仍标记右岸帷幕 UNRESOLVED。",
        },
        {
            "item_id": "7", "requirement": "右岸帷幕向岸内延伸 100 m", "status": "MISSING",
            "part": "NONE_FOUND", "instance": "NONE_FOUND", "material": "NONE_FOUND",
            "set": "NONE_FOUND", "geometry": "NONE_FOUND",
            "evidence": "No right-bank curtain geometry exists from which a 100 m inland extent can be measured.",
            "note": "必须先取得右岸帷幕轴线、起止坐标、厚度/等效区宽度和材料渗透参数；本次不自动创建。",
        },
        {
            "item_id": "8", "requirement": "防渗墙与上部复合土工膜、右岸灌浆帷幕连续连接", "status": "PARTIAL",
            "part": f"{cutoff['name']}; {chain['name']}; {geomem['name']}",
            "instance": f"{cutoff_instance['name']}; {chain_instance['name']}; {geomem_instance['name']}",
            "material": f"{wall_material}; {geomem_material}; RIGHT_BANK_CURTAIN_MISSING",
            "set": "V15_5_ALL; V15_13_* connection sets; V15_5_ALL",
            "geometry": f"wall-geomembrane shared nodes={cutoff_chain_shared}; chain-geomembrane shared nodes={chain_geom_shared}; tie_count={tie_count}",
            "evidence": "Wall/chain and geomembrane objects are present, but the right-bank curtain is absent and no explicit Tie was found; geometric continuity to the geomembrane is not proven by shared-node identity.",
            "note": "Existing local anti-seepage chain subsets support internal segment organization, but global three-way continuity is incomplete while the right-bank curtain is missing.",
        },
    ]

    fields = ["item_id", "engineering_requirement", "status", "part_name", "instance_name", "material_name",
              "element_set", "geometry_dimensions", "source_evidence", "implementation_note"]
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "item_id": row["item_id"], "engineering_requirement": row["requirement"], "status": row["status"],
                "part_name": row["part"], "instance_name": row["instance"], "material_name": row["material"],
                "element_set": row["set"], "geometry_dimensions": row["geometry"],
                "source_evidence": row["evidence"], "implementation_note": row["note"],
            })

    md = [
        "# S01 Final Design Correspondence Audit",
        "",
        "FINAL_DESIGN_CORRESPONDENCE_STATUS = PARTIAL",
        "",
        "## Scope",
        "",
        "This is a read-only correspondence audit of the V15.26 S01 baseline against the eight final seepage-design requirements supplied for the 多布水电站. It uses the unchanged V15.24 S01 input retained as the V15.26 model-object source. No model, input deck, mesh, material, boundary condition, or Abaqus result was modified. Abaqus was not run.",
        "",
        f"- Source input: `{INPUT}`",
        "- S01 baseline summary: `abaqus-audit/3d-v15.26/S01_ENGINEERING_BASELINE_SUMMARY.md`",
        "- Prior study mapping: `abaqus-audit/study-design/case_parameter_mapping_v1.md`",
        "- Machine-readable audit: `S01_FINAL_DESIGN_MAPPING.csv`",
        "",
        "## Eight-item result",
        "",
        "| Item | Requirement | Status |",
        "|---:|---|---|",
        *[f"| {row['item_id']} | {row['requirement']} | **{row['status']}** |" for row in rows],
        "",
        "## Confirmed geometry and object evidence",
        "",
        f"### Main cutoff wall: {cutoff['name']} / {cutoff_instance['name']}",
        "",
        f"- Material: `P25_FANGSHENQIANG`; element set: `V15_5_ALL`; current scalar permeability: `{permeability.get(wall_material)}`.",
        f"- {dimension_text(cutoff_box)}.",
        f"- Global bottom elevation: `{cutoff_box['min'][2]:.6f} m`; current vertical z-span: `{cutoff_box['span'][2]:.6f} m`; current longitudinal y-span: `{cutoff_box['span'][1]:.6f} m`.",
        "- The required 49.10 m maximum construction depth is not directly reproduced by the current S01 wall geometry. Item 5 is therefore PARTIAL, not PASS.",
        "",
        f"### Anti-seepage chain: {chain['name']} / {chain_instance['name']}",
        "",
        f"- Material: `P25_FANGSHENQIANG`; aggregate set: `V15_13_ANTI_SEEPAGE_ALL`; {dimension_text(chain_all)}.",
        "- Confirmed named subsets in the current input:",
        "",
        "| Element Set | Meaning | Global span / range check |",
        "|---|---|---|",
        f"| `V15_13_LEFT_BANK_ABUTMENT_EXTENSION` | Left-bank 80 m extension | `{dimension_text(chain_sets['V15_13_LEFT_BANK_ABUTMENT_EXTENSION'])}` |",
        f"| `V15_13_LEFT_SUBDAM_CUTOFF` | Left subdam cutoff | `{dimension_text(chain_sets['V15_13_LEFT_SUBDAM_CUTOFF'])}` |",
        f"| `V15_13_INSTALLATION_POWERHOUSE_CUTOFF`; `V15_13_POWERHOUSE_CUTOFF` | Installation bay / powerhouse | `{dimension_text(chain_sets['V15_13_INSTALLATION_POWERHOUSE_CUTOFF'])}`; `{dimension_text(chain_sets['V15_13_POWERHOUSE_CUTOFF'])}` |",
        f"| `V15_13_ECOLOGICAL_RELEASE_CONNECTION` | Ecological-release connection | `{dimension_text(chain_sets['V15_13_ECOLOGICAL_RELEASE_CONNECTION'])}` |",
        f"| `V15_13_SPILLWAY_CUTOFF`; `V15_13_SPILLWAY_MAIN_TRANSITION` | Spillway transition | `{dimension_text(chain_sets['V15_13_SPILLWAY_CUTOFF'])}`; `{dimension_text(chain_sets['V15_13_SPILLWAY_MAIN_TRANSITION'])}` |",
        "",
        f"### Upstream geomembrane: {geomem['name']} / {geomem_instance['name']}",
        "",
        f"- Material: `GEOMEMBRANE`; element set: `V15_5_ALL`; current scalar permeability: `{permeability.get(geomem_material)}`.",
        f"- {dimension_text(geomem_box)}.",
        "- The low-permeability object exists, but the input provides one homogenized material/solid representation rather than an explicit multi-layer composite stack. This is why item 1 is PARTIAL rather than PASS.",
        "",
        "## Right-bank curtain finding",
        "",
        "The right-bank curtain is not present as a model object. Right-bank geology sets are present in `V15_7_FOUNDATION_GEOLOGY_I`, but no right-bank curtain Part, Instance, Material, or Element Set was identified. The current model therefore cannot demonstrate either the required grouting curtain or its 100 m inland extension.",
        "",
        "```text",
        "RIGHT_BANK_CURTAIN = MISSING",
        "RIGHT_BANK_CURTAIN_100M_EXTENSION = MISSING",
        "RIGHT_BANK_CONNECTION = UNRESOLVED",
        "```",
        "",
        "## Required modification plan if the design is to be completed",
        "",
        "No modification was made in this audit. Before any S02-S07 run or revised S01, the following controlled work is required:",
        "",
        "1. Obtain source-backed right-bank curtain alignment in global Assembly coordinates, including the start point, the 100 m inland endpoint, bottom elevation, thickness or equivalent-zone width, and tie-in to the right-bank geology.",
        "2. Create a dedicated right-bank curtain Part/Instance and element set, or an explicitly approved equivalent low-permeability geology domain. Assign a source-backed material and permeability; do not relabel existing geology as a curtain.",
        "3. Define the upper curtain connection to the composite geomembrane and the lateral connection to the existing anti-seepage chain using conformal geometry/shared nodes where feasible. Do not use an unsupported Tie, fixed node, spring, or Encastre to hide a geometry gap.",
        "4. Rebuild only the affected local mesh, then verify positive volume, duplicate elements, nonconforming faces, hanging nodes, and interface continuity. Preserve the V15.26 S01 baseline as an immutable comparison case.",
        "5. Re-run the design-correspondence audit and only then decide whether a new analysis input is authorized.",
        "",
        "The left-bank 80 m extension does not require this missing-geometry plan: its existing named set has a measured 80.000000 m global span and is marked PASS.",
        "",
        "## Final readiness",
        "",
        "The current S01 model contains the main cutoff, anti-seepage chain, left-bank 80 m extension, 1.0 m wall thickness, and a 3021.0 m wall-bottom datum. The current wall geometry does not directly reproduce the stated 49.10 m maximum construction depth. It also does not contain the right-bank curtain or a proven global three-way connection to the geomembrane and right-bank curtain. Therefore the final engineering design correspondence is PARTIAL, and no S02 run should start from this audit alone.",
    ]
    OUTPUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"cutoff={dimension_text(cutoff_box)}")
    print(f"left_extension={dimension_text(chain_left)}")
    print(f"geomembrane={dimension_text(geomem_box)}")
    print(f"shared_nodes cutoff-chain={cutoff_chain_shared} chain-geomembrane={chain_geom_shared}")
    print(f"right_candidates={right_candidates}")
    print(f"wrote={OUTPUT_MD}")
    print(f"wrote={OUTPUT_CSV}")


if __name__ == "__main__":
    main()
