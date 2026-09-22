"""Run the V15.14 engineering-closure audit over the tracked V15.13 record.

The audit is deliberately conservative: it checks correspondence, material
mapping, cover-layer presence, and seepage-barrier representation without
inventing missing geometry or hydraulic coefficients.  It writes a compact
cover-layer audit and a Markdown closure report.  A non-clean result is valid
output for this phase; production seepage must remain on hold until unresolved
engineering inputs are closed.
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import OrderedDict
from pathlib import Path


REQUIRED_LAYERS = OrderedDict([
    ("Q4del", ("Q4DEL",)),
    ("Q4al-Sgr2", ("Q4AL_SGR2",)),
    ("Q3al-V", ("Q3AL_V",)),
    ("Q3al-IV", ("Q3AL_IV1", "Q3AL_IV2", "Q3AL_IV")),
    ("Q3al-III", ("Q3AL_III",)),
    ("Q3al-II", ("Q3AL_II",)),
    ("Q3al-I", ("Q3AL_I",)),
    ("Q2fgl", ("Q2FGL_",)),
])


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def yes(value):
    return str(value or "").strip().upper() in {"YES", "TRUE", "PASS"}


def norm(value):
    return re.sub(r"[^A-Z0-9_]", "", str(value or "").upper())


def material_matches(material, patterns):
    value = norm(material)
    return any(
        value.startswith(pattern) if pattern.endswith("_") else value == pattern
        for pattern in patterns
    )


def existing_text(path):
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def parse_inp_symbols(path):
    text = existing_text(path)
    return {
        "parts": set(re.findall(r"^\*Part,\s*name=([^,\s]+)", text, re.I | re.M)),
        "instances": set(re.findall(r"^\*Instance,\s*name=([^,\s]+)", text, re.I | re.M)),
        "materials": set(re.findall(r"^\*Material,\s*name=([^,\s]+)", text, re.I | re.M)),
    }


def check_foundation_layers(section_rows):
    rows = []
    for layer, patterns in REQUIRED_LAYERS.items():
        matches = [row for row in section_rows if material_matches(row.get("material"), patterns)]
        geometry = any(int(float(row.get("element_count", "0") or 0)) > 0 for row in matches)
        material = bool(matches and all(row.get("material", "").strip() for row in matches))
        permeability = any(yes(row.get("permeability")) for row in matches)
        status = "PASS" if geometry and material and permeability else "UNRESOLVED"
        if status == "PASS" and layer in {"Q3al-IV", "Q3al-III", "Q2fgl"}:
            status = "CHECK"
        rows.append({
            "Engineering_Layer": layer,
            "Model_Material_Families": ";".join(sorted({row.get("material", "") for row in matches})),
            "Geometry_Exists": "YES" if geometry else "NO",
            "Material_Exists": "YES" if material else "NO",
            "Permeability_Exists": "YES" if permeability else "NO",
            "Parameter_Basis": "Engineering-equivalent or variant mapping requires confirmation" if status == "CHECK" else "Tracked V15.13 section mapping",
            "Status": status,
            "Required_Action": "Confirm source layer/variant and parameter basis" if status != "PASS" else "None for presence audit",
        })
    return rows


def check_cutoff_wall(v15_dir, symbols):
    rows = read_csv(v15_dir / "v15_13_cutoff_connection_final.csv")
    passing = [row for row in rows if (row.get("status") or "").upper() == "PASS"]
    chain = "V15_13_ANTI_SEEPAGE_CHAIN_I" in symbols["instances"]
    main = "P25_SOLID_CUTOFF_WALL_F13-1" in symbols["instances"]
    geomembrane = "V12_UPSTREAM_GEOMEMBRANE-1" in symbols["instances"]
    return {
        "status": "PASS" if chain and main and geomembrane and passing else "UNRESOLVED",
        "chain_instance": chain,
        "main_cutoff_instance": main,
        "geomembrane_instance": geomembrane,
        "passing_connections": len(passing),
        "note": "Right-bank curtain is separately unresolved; this check covers the represented chain only.",
    }


def check_grouting_curtain(v15_dir):
    rows = read_csv(v15_dir / "v15_13_right_bank_curtain_resolution.csv")
    unresolved = [row for row in rows if (row.get("status") or "").upper() != "PASS"]
    return {
        "status": "UNRESOLVED" if unresolved else "PASS",
        "rows": len(rows),
        "unresolved_rows": len(unresolved),
        "note": "No axis, thickness, or equivalent hydraulic coefficient is invented." if unresolved else "Source-backed representation recorded.",
    }


def check_material_mapping(v15_dir, output_dir, layer_rows):
    closure_path = output_dir / "Material_Property_Closure_V15_14.csv"
    closure_rows = read_csv(closure_path) if closure_path.exists() else []
    closure_materials = {norm(row.get("Material")) for row in closure_rows}
    required_materials = {norm(layer) for layer in REQUIRED_LAYERS}
    # The table uses engineering names while the section audit uses model names;
    # presence is checked through the layer audit and closure-table coverage.
    table_complete = required_materials.issubset(closure_materials)
    layer_presence = all(row["Status"] != "UNRESOLVED" for row in layer_rows)
    rock_rows = read_csv(v15_dir / "v15_13_rock_hydraulic_parameter_basis.csv")
    rock_calibration = any("CALIBRATION" in (row.get("status") or "").upper() for row in rock_rows)
    q3al_check = any(row.get("Engineering_Layer") == "Q3al-III" and row.get("Status") != "PASS" for row in layer_rows)
    if not table_complete or not layer_presence:
        status = "UNRESOLVED"
    elif rock_calibration or q3al_check:
        status = "CHECK"
    else:
        status = "PASS"
    return {
        "status": status,
        "closure_table_complete": table_complete,
        "layer_presence_complete": layer_presence,
        "rock_calibration_required": rock_calibration,
        "q3al_iii_requires_confirmation": q3al_check,
        "note": "Active deck values are preserved as audit evidence; they are not promoted to source-closed design values.",
    }


def build_report(v15_dir, output_dir, layer_rows, cutoff, curtain, materials, symbols):
    correspondence = "CHECK" if "UNRESOLVED" in existing_text(v15_dir / "V15_13_FINAL_SEEPAGE_DOMAIN_RESULT.md") else "PASS"
    production = "HOLD / UNRESOLVED" if curtain["status"] != "PASS" or materials["status"] != "PASS" or correspondence == "CHECK" else "READY FOR REVIEW"
    report = [
        "# V15.14 Engineering Closure Audit Report",
        "",
        "## Decision",
        "",
        f"- Engineering closure state: **IN PROGRESS**",
        f"- Geometry Solver Readiness inherited from V15.13: **PASS**",
        f"- Production Seepage Readiness: **{production}**",
        "- S01-S07 execution: **NOT AUTHORIZED BY THIS AUDIT**",
        "",
        "This report verifies model correspondence and input completeness. It does not change the V15.13 CAE/INP geometry and does not invent a right-bank curtain or rock permeability coefficient.",
        "",
        "## Automated checks",
        "",
        f"| Check | Status | Evidence / note |",
        "|---|---|---|",
        f"| Cutoff wall and represented anti-seepage chain | **{cutoff['status']}** | {cutoff['passing_connections']} tracked connection rows pass; chain/main cutoff/geomembrane instances present={cutoff['chain_instance'] and cutoff['main_cutoff_instance'] and cutoff['geomembrane_instance']} |",
        f"| Right-bank grouting curtain | **{curtain['status']}** | {curtain['note']} |",
        f"| Foundation cover-layer presence | **{'PASS' if all(row['Status'] != 'UNRESOLVED' for row in layer_rows) else 'UNRESOLVED'}** | Eight required engineering families were checked against the V15.13 section audit. |",
        f"| Material mapping and closure table | **{materials['status']}** | {materials['note']} |",
        f"| Engineering–model one-to-one correspondence | **{correspondence}** | Existing V15.13 report still contains source-limited items. |",
        "",
        "## Cover-layer audit",
        "",
        "| Layer | Geometry | Material | Permeability | Status |",
        "|---|---:|---:|---:|---|",
    ]
    report.extend(
        f"| {row['Engineering_Layer']} | {row['Geometry_Exists']} | {row['Material_Exists']} | {row['Permeability_Exists']} | {row['Status']} |"
        for row in layer_rows
    )
    report.extend([
        "",
        "## Pending items",
        "",
        "1. Curtain grouting permeability calibration.",
        "2. Right-bank curtain geometry verification.",
        "3. Q3AL_III parameter confirmation for natural and engineered-backfill use.",
        "4. Rock permeability inversion/calibration for the tracked Lu-category regions.",
        "",
        "## Guardrails",
        "",
        "- No V15.14 CAE or INP geometry is generated by this audit.",
        "- No existing V15.13 permeability value is silently reinterpreted or replaced.",
        "- The right-bank curtain remains `UNRESOLVED` until its axis, thickness, and equivalent hydraulic definition are source-supported.",
        "- The V15.13 corrected deck remains the analysis baseline; S01-S07 should follow only after the pending items are closed.",
        "",
        "## Reproduction",
        "",
        "Run from `abaqus-audit/3d-v15.14/`:",
        "",
        "```text",
        "python complete_v15_14_engineering_closure.py",
        "```",
        "",
        f"Audit symbols found in the tracked V15.13 INP: {len(symbols['instances'])} instances, {len(symbols['parts'])} parts, {len(symbols['materials'])} materials.",
    ])
    (output_dir / "V15_14_ENGINEERING_CLOSURE_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main(argv=None):
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v15-dir", type=Path, default=here.parent / "3d-v15.13")
    parser.add_argument("--output-dir", type=Path, default=here)
    parser.add_argument("--strict", action="store_true", help="exit non-zero if production inputs are not closed")
    args = parser.parse_args(argv)
    args.v15_dir = args.v15_dir.resolve()
    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    section_rows = read_csv(args.v15_dir / "v15_13_section_level_pore_pressure_audit.csv")
    layer_rows = check_foundation_layers(section_rows)
    with (args.output_dir / "Cover_Layer_Audit.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(layer_rows[0]))
        writer.writeheader()
        writer.writerows(layer_rows)

    inp_candidates = sorted(args.v15_dir.glob("*.inp"))
    symbols = parse_inp_symbols(inp_candidates[0]) if inp_candidates else {"parts": set(), "instances": set(), "materials": set()}
    cutoff = check_cutoff_wall(args.v15_dir, symbols)
    curtain = check_grouting_curtain(args.v15_dir)
    materials = check_material_mapping(args.v15_dir, args.output_dir, layer_rows)
    build_report(args.v15_dir, args.output_dir, layer_rows, cutoff, curtain, materials, symbols)

    print("V15_14_CLOSURE_REPORT=%s" % (args.output_dir / "V15_14_ENGINEERING_CLOSURE_REPORT.md"))
    print("V15_14_COVER_LAYER_AUDIT=%s" % (args.output_dir / "Cover_Layer_Audit.csv"))
    print("V15_14_CUTOFF_STATUS=%s" % cutoff["status"])
    print("V15_14_CURTAIN_STATUS=%s" % curtain["status"])
    print("V15_14_MATERIAL_STATUS=%s" % materials["status"])
    if args.strict and (curtain["status"] != "PASS" or materials["status"] != "PASS"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

