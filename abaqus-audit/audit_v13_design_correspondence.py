#!/usr/bin/env python3
"""Audit v13 geometry against documented Duobu/P25 design values.

Pure Python; no Abaqus license is required.  It reads the exported v13 INP,
uses the same P25 local->global transform as repair_v12_3d.py, measures the
actual mesh, and writes machine-readable CSVs plus a Markdown summary.

This script does NOT force geometry to match a number.  In particular,
3070.10 m is treated as a documented cofferdam/slope-break elevation, not as
an automatic cutoff-wall-top elevation.  The cutoff is checked station by
station against its documented 1.0 m thickness, 3021.0 m minimum bottom and
49.10 m maximum depth.
"""
from __future__ import annotations

import argparse
import collections
import csv
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from repair_v12_3d import parse_deck, global_coord

DAM_PARTS = {
    "P25_SOLID_DRAINAGE_BODY_F00",
    "P25_SOLID_FILTER_LAYER_F01",
    "P25_SOLID_DAM_SHELL_GRAVEL_F02",
    "P25_SOLID_DRAINAGE_BODY_F03",
    "P25_SOLID_DAM_SHELL_GRAVEL_F06",
    "P25_SOLID_DAM_SHELL_GRAVEL_F08",
    "P25_SOLID_MAIN_ROCKFILL_F09",
    "P25_SOLID_UPSTREAM_GRAVEL_FILL_F10",
    "P25_SOLID_MAIN_ROCKFILL_F11",
    "P25_SOLID_IMPERMEABLE_FILL_F12",
}
CUTOFF_PART = "P25_SOLID_CUTOFF_WALL_F13"
GEOMEMBRANE_PART = "V12_UPSTREAM_GEOMEMBRANE"

DESIGN = {
    "dam_length_m": 295.0,
    "crest_elevation_m": 3079.0,
    "foundation_elevation_m": 3052.0,
    "max_dam_height_m": 27.0,
    "upstream_upper_hv": 2.5,
    "upstream_middle_hv": 1.75,
    "upstream_lower_hv": 2.5,
    "downstream_hv": 2.0,
    "slope_break_upper_m": 3070.10,
    "slope_break_lower_m": 3059.00,
    "berm_elevation_m": 3065.0,
    "berm_width_m": 3.0,
    "pressure_platform_width_m": 10.0,
    "cutoff_thickness_m": 1.0,
    "cutoff_min_bottom_m": 3021.0,
    "cutoff_max_depth_m": 49.10,
}

HEADS = {
    "S03_NORMAL_RESERVOIR_3076M": (3076.00, 3053.50, "normal stability case"),
    "S04_DESIGN_FLOOD_3580CMS": (3076.00, 3060.26, "explicit design-flood stability case; upstream source text is internally inconsistent elsewhere"),
    "S05_CHECK_FLOOD_AND_SEISMIC": (3077.35, 3061.38, "check-flood stability case"),
    "S06_DRAWDOWN_TO_3074M": (3074.00, 3053.50, "dead-water/drawdown stability case"),
}


def f(v):
    return "%.6f" % float(v)


def bbox(points):
    xs = [p[0] for p in points]; ys = [p[1] for p in points]; zs = [p[2] for p in points]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def close(a, b, tol):
    return abs(float(a) - float(b)) <= tol


def status_close(actual, expected, tol):
    return "PASS" if close(actual, expected, tol) else "FAIL"


def linear_fit(points):
    """Fit x = a*z+b and return a,b,R2,max residual."""
    if len(points) < 2:
        return None
    zs = [p[0] for p in points]
    xs = [p[1] for p in points]
    zbar = sum(zs) / len(zs); xbar = sum(xs) / len(xs)
    den = sum((z-zbar)**2 for z in zs)
    if den <= 1e-12:
        return None
    a = sum((z-zbar)*(x-xbar) for z, x in zip(zs, xs)) / den
    b = xbar - a*zbar
    ss_res = sum((x-(a*z+b))**2 for z, x in zip(zs, xs))
    ss_tot = sum((x-xbar)**2 for x in xs)
    r2 = 1.0 - ss_res/ss_tot if ss_tot > 1e-12 else 1.0
    max_res = max(abs(x-(a*z+b)) for z, x in zip(zs, xs))
    return a, b, r2, max_res


def grouped_envelope(points, dz=0.01):
    levels = collections.defaultdict(list)
    for x, _y, z in points:
        key = round(z / dz) * dz
        levels[key].append(x)
    out = []
    for z in sorted(levels):
        out.append((z, min(levels[z]), max(levels[z]), len(levels[z])))
    return out


def nearest_side_to_geomembrane(envelope, gm_points):
    if not gm_points or not envelope:
        return "MIN_X", "no geomembrane nodes available; conventional upstream=min-x fallback"
    # Compare geomembrane x with nearest-elevation envelope on both sides.
    total_min = total_max = 0.0; n = 0
    for gx, _gy, gz in gm_points:
        row = min(envelope, key=lambda r: abs(r[0]-gz))
        total_min += abs(gx-row[1]); total_max += abs(gx-row[2]); n += 1
    if total_min <= total_max:
        return "MIN_X", "geomembrane is closer to min-x dam envelope (%.3g vs %.3g cumulative m)" % (total_min, total_max)
    return "MAX_X", "geomembrane is closer to max-x dam envelope (%.3g vs %.3g cumulative m)" % (total_max, total_min)


def slope_row(name, envelope, side_index, z0, z1, expected):
    pts = [(z, row[side_index]) for row in envelope for z in [row[0]] if z0-1e-6 <= z <= z1+1e-6]
    fit = linear_fit(pts)
    if fit is None:
        return [name, f(z0), f(z1), f(expected), "", "", "", "UNRESOLVED", "insufficient envelope levels"]
    a, _b, r2, max_res = fit
    hv = abs(a)
    # A mesh slope is accepted if H:V is within 0.15 and the line fit is coherent.
    st = "PASS" if abs(hv-expected) <= 0.15 and r2 >= 0.97 else "FAIL"
    return [name, f(z0), f(z1), f(expected), f(hv), f(r2), f(max_res), st,
            "%d elevation levels" % len(pts)]


def same_level_candidate_spans(points, target, z_target=None, z_tol=0.06, side="MAX_X"):
    byz = collections.defaultdict(set)
    for x, _y, z in points:
        if z_target is not None and abs(z-z_target) > z_tol:
            continue
        byz[round(z, 3)].add(round(x, 5))
    candidates = []
    for z, xs_set in byz.items():
        xs = sorted(xs_set)
        if len(xs) < 2:
            continue
        # Adjacent horizontal node spans are less likely to combine unrelated internal zones.
        for a, b in zip(xs[:-1], xs[1:]):
            span = b-a
            candidates.append((abs(span-target), z, a, b, span))
    candidates.sort()
    return candidates[:10]


def geology_stats(points):
    # Estimate local vertical layer thickness by identical plan-coordinate columns.
    columns = collections.defaultdict(list)
    for x, y, z in points:
        columns[(round(x, 4), round(y, 4))].append(z)
    top = []; base = []; thickness = []
    for zs in columns.values():
        if len(zs) >= 2:
            lo, hi = min(zs), max(zs)
            if hi-lo > 1e-6:
                base.append(lo); top.append(hi); thickness.append(hi-lo)
    bb = bbox(points)
    return {
        "xmin": bb[0], "xmax": bb[1], "ymin": bb[2], "ymax": bb[3],
        "zmin": bb[4], "zmax": bb[5],
        "base_min": min(base) if base else bb[4], "base_max": max(base) if base else bb[4],
        "top_min": min(top) if top else bb[5], "top_max": max(top) if top else bb[5],
        "tmin": min(thickness) if thickness else float("nan"),
        "tmed": statistics.median(thickness) if thickness else float("nan"),
        "tmax": max(thickness) if thickness else float("nan"),
        "columns": len(thickness),
    }


def collect_instance_points(parts, instances):
    out = collections.OrderedDict()
    for inst, part in instances:
        if part not in parts:
            continue
        out[inst] = (part, [global_coord(inst, part, c) for c in parts[part]["nodes"].values()])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out_dir")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    _lines, parts, instances, _sets = parse_deck(args.inp)
    ip = collect_instance_points(parts, instances)

    dam_points = []
    gm_points = []
    cutoff_points = []
    for _inst, (part, pts) in ip.items():
        if part in DAM_PARTS:
            dam_points.extend(pts)
        elif part == GEOMEMBRANE_PART:
            gm_points.extend(pts)
        elif part == CUTOFF_PART:
            cutoff_points.extend(pts)
    if not dam_points:
        raise SystemExit("No active P25 dam-fill points found")

    envelope = grouped_envelope(dam_points)
    upstream_side, upstream_reason = nearest_side_to_geomembrane(envelope, gm_points)
    upstream_index = 1 if upstream_side == "MIN_X" else 2
    downstream_index = 2 if upstream_index == 1 else 1
    dbb = bbox(dam_points)
    length = dbb[3]-dbb[2]
    crest = dbb[5]
    foundation = dbb[4]
    height = crest-foundation

    geom_rows = [
        ["dam_length", "m", f(DESIGN["dam_length_m"]), f(length), f(length-DESIGN["dam_length_m"]), status_close(length, DESIGN["dam_length_m"], 0.05), "global Y extent of active dam-fill mesh"],
        ["crest_elevation", "m", f(DESIGN["crest_elevation_m"]), f(crest), f(crest-DESIGN["crest_elevation_m"]), status_close(crest, DESIGN["crest_elevation_m"], 0.05), "maximum global Z of active dam-fill mesh"],
        ["foundation_elevation", "m", f(DESIGN["foundation_elevation_m"]), f(foundation), f(foundation-DESIGN["foundation_elevation_m"]), status_close(foundation, DESIGN["foundation_elevation_m"], 0.10), "minimum global Z of active dam-fill mesh; cutoff excluded"],
        ["maximum_dam_height", "m", f(DESIGN["max_dam_height_m"]), f(height), f(height-DESIGN["max_dam_height_m"]), status_close(height, DESIGN["max_dam_height_m"], 0.10), "crest minus minimum active dam-fill elevation"],
    ]

    slopes = [
        slope_row("upstream_lower", envelope, upstream_index, foundation, DESIGN["slope_break_lower_m"], DESIGN["upstream_lower_hv"]),
        slope_row("upstream_middle", envelope, upstream_index, DESIGN["slope_break_lower_m"], DESIGN["slope_break_upper_m"], DESIGN["upstream_middle_hv"]),
        slope_row("upstream_upper", envelope, upstream_index, DESIGN["slope_break_upper_m"], min(crest, DESIGN["crest_elevation_m"]), DESIGN["upstream_upper_hv"]),
        slope_row("downstream_lower", envelope, downstream_index, foundation, DESIGN["berm_elevation_m"]-0.05, DESIGN["downstream_hv"]),
        slope_row("downstream_upper", envelope, downstream_index, DESIGN["berm_elevation_m"]+0.05, min(crest, DESIGN["crest_elevation_m"]), DESIGN["downstream_hv"]),
    ]

    berm_candidates = same_level_candidate_spans(dam_points, DESIGN["berm_width_m"], DESIGN["berm_elevation_m"], 0.08)
    platform_candidates = same_level_candidate_spans(dam_points, DESIGN["pressure_platform_width_m"], None)

    with open(os.path.join(args.out_dir, "v13_dam_geometry_audit.csv"), "w", newline="", encoding="utf-8") as h:
        w = csv.writer(h); w.writerow(["item","unit","design","model_measured","difference","status","basis"]); w.writerows(geom_rows)
        w.writerow([]); w.writerow(["slope_segment","z_min","z_max","design_H_to_V","model_H_to_V","R2","max_residual_m","status","basis"]); w.writerows(slopes)
        w.writerow([]); w.writerow(["upstream_side_identification", upstream_side, upstream_reason])

    with open(os.path.join(args.out_dir, "v13_horizontal_feature_candidates.csv"), "w", newline="", encoding="utf-8") as h:
        w = csv.writer(h); w.writerow(["feature","target_width_m","z_m","x0_m","x1_m","span_m","abs_error_m","interpretation"])
        for err,z,a,b,span in berm_candidates:
            w.writerow(["3065_berm",3.0,f(z),f(a),f(b),f(span),f(err),"node-level candidate; verify outer boundary in CAE if not unique"])
        for err,z,a,b,span in platform_candidates:
            w.writerow(["downstream_pressure_platform",10.0,f(z),f(a),f(b),f(span),f(err),"node-level candidate; verify outer boundary in CAE if not unique"])

    cutoff_summary = []
    if cutoff_points:
        cbb = bbox(cutoff_points)
        by_station = collections.defaultdict(list)
        for x,y,z in cutoff_points:
            by_station[round(y,4)].append((x,z))
        stations = []
        for y, vals in sorted(by_station.items()):
            xs = [v[0] for v in vals]; zs = [v[1] for v in vals]
            stations.append((y,min(zs),max(zs),max(zs)-min(zs),min(xs),max(xs),max(xs)-min(xs)))
        max_depth_station = max(stations, key=lambda r:r[3]) if stations else None
        thicknesses = [r[6] for r in stations if r[6] > 1e-8]
        representative_thickness = statistics.median(thicknesses) if thicknesses else cbb[1]-cbb[0]
        cutoff_summary = [
            ["cutoff_min_bottom", "m", f(DESIGN["cutoff_min_bottom_m"]), f(cbb[4]), f(cbb[4]-DESIGN["cutoff_min_bottom_m"]), status_close(cbb[4],DESIGN["cutoff_min_bottom_m"],0.02), "global minimum Z"],
            ["cutoff_thickness", "m", f(DESIGN["cutoff_thickness_m"]), f(representative_thickness), f(representative_thickness-DESIGN["cutoff_thickness_m"]), status_close(representative_thickness,DESIGN["cutoff_thickness_m"],0.02), "median station x-span"],
            ["cutoff_max_depth", "m", f(DESIGN["cutoff_max_depth_m"]), f(max_depth_station[3]), f(max_depth_station[3]-DESIGN["cutoff_max_depth_m"]), status_close(max_depth_station[3],DESIGN["cutoff_max_depth_m"],0.15), "station-by-station max(top-bottom), not global extrema subtraction"],
            ["cutoff_top_global_max", "m", "VARIABLE; follows concrete plinth/base underside", f(cbb[5]), "", "UNRESOLVED", "must compare to station-specific design plinth underside; 3070.10 is not imposed automatically"],
        ]
        with open(os.path.join(args.out_dir, "v13_cutoff_stations.csv"), "w", newline="", encoding="utf-8") as h:
            w=csv.writer(h); w.writerow(["global_y_m","bottom_z_m","top_z_m","depth_m","xmin_m","xmax_m","thickness_x_m"])
            for row in stations: w.writerow([f(v) for v in row])
    else:
        cutoff_summary = [["cutoff_wall", "", "present", "not found", "", "FAIL", "active main cutoff part missing"]]

    gm_bb = bbox(gm_points) if gm_points else None
    with open(os.path.join(args.out_dir, "v13_cutoff_geomembrane_audit.csv"), "w", newline="", encoding="utf-8") as h:
        w=csv.writer(h); w.writerow(["item","unit","design","model_measured","difference","status","basis"]); w.writerows(cutoff_summary)
        if gm_bb:
            w.writerow(["geomembrane_z_range","m","upstream face to cutoff/plinth connection","%.6f..%.6f"%(gm_bb[4],gm_bb[5]),"","MODEL_EQUIVALENT","1.0 m equivalent C3D8P layer; not literal membrane thickness"])
            if cutoff_points:
                w.writerow(["geomembrane_cutoff_top_alignment","m","connected to cutoff top",f(gm_bb[5]-bbox(cutoff_points)[5]),"","PASS" if abs(gm_bb[5]-bbox(cutoff_points)[5])<=0.02 else "FAIL","difference of maximum global Z values"])
        else:
            w.writerow(["geomembrane","","present","not found","","FAIL","active equivalent geomembrane part missing"])

    geology_rows=[]
    for inst,(part,pts) in ip.items():
        upper = part.upper()
        if not (upper.startswith("LEFT_") or upper.startswith("RIVER_") or upper.startswith("RIGHT_")):
            continue
        if not any(tag in upper for tag in ("Q4","Q3","Q2","ROCK","GRANITE","QUARTZ","FOUNDATION")):
            continue
        s=geology_stats(pts)
        geology_rows.append([inst,part,f(s["xmin"]),f(s["xmax"]),f(s["ymin"]),f(s["ymax"]),f(s["zmin"]),f(s["zmax"]),f(s["base_min"]),f(s["base_max"]),f(s["top_min"]),f(s["top_max"]),"" if math.isnan(s["tmin"]) else f(s["tmin"]),"" if math.isnan(s["tmed"]) else f(s["tmed"]),"" if math.isnan(s["tmax"]) else f(s["tmax"]),s["columns"],"UNRESOLVED_DESIGN_SURFACE","model measured; station-specific design geological surfaces required for one-to-one PASS"])
    with open(os.path.join(args.out_dir,"v13_geology_geometry_audit.csv"),"w",newline="",encoding="utf-8") as h:
        w=csv.writer(h); w.writerow(["instance","part","xmin","xmax","ymin","ymax","zmin","zmax","base_z_min","base_z_max","top_z_min","top_z_max","local_thickness_min","local_thickness_median","local_thickness_max","vertical_columns","status","basis"]); w.writerows(geology_rows)

    with open(os.path.join(args.out_dir,"v13_design_bc_target.csv"),"w",newline="",encoding="utf-8") as h:
        w=csv.writer(h); w.writerow(["step","upstream_head_m","downstream_head_m","basis"])
        for step,(hu,hd,basis) in HEADS.items(): w.writerow([step,f(hu),f(hd),basis])

    md=os.path.join(args.out_dir,"V13_DESIGN_CORRESPONDENCE_AUDIT.md")
    with open(md,"w",encoding="utf-8") as h:
        h.write("# v13 design correspondence audit\n\n")
        h.write("Source deck: `%s`\n\n"%os.path.basename(args.inp))
        h.write("## Dam geometry\n\n")
        h.write("Upstream side: **%s** — %s.\n\n"%(upstream_side,upstream_reason))
        h.write("|Item|Design|Measured|Status|\n|---|---:|---:|---|\n")
        for r in geom_rows: h.write("|%s|%s|%s|%s|\n"%(r[0],r[2],r[3],r[5]))
        h.write("\n### Slopes\n\n|Segment|Design H:V|Measured H:V|R2|Status|\n|---|---:|---:|---:|---|\n")
        for r in slopes: h.write("|%s|%s|%s|%s|%s|\n"%(r[0],r[3],r[4] or "—",r[5] or "—",r[7]))
        h.write("\nBerm/platform node-level candidates are in `v13_horizontal_feature_candidates.csv`. They are not promoted to PASS unless the outer-boundary interpretation is unique; CAE visual confirmation is required when multiple candidates exist.\n\n")
        h.write("## Main cutoff / geomembrane\n\n|Item|Design|Measured|Status|\n|---|---:|---:|---|\n")
        for r in cutoff_summary: h.write("|%s|%s|%s|%s|\n"%(r[0],r[2],r[3],r[5]))
        if cutoff_points:
            h.write("\nThe cutoff maximum depth above is computed at each global-Y station as top-bottom. `3070.10 m` is **not** assumed to be the cutoff top. The model maximum top remains UNRESOLVED until compared with the station-specific concrete plinth/base underside.\n\n")
        h.write("## Hydraulic design targets\n\n|Step|Upstream m|Downstream m|\n|---|---:|---:|\n")
        for step,(hu,hd,_basis) in HEADS.items(): h.write("|%s|%.2f|%.2f|\n"%(step,hu,hd))
        h.write("\nThe current v13 deck inherited 3055.00 m downstream heads; these targets are written separately so the correction can be generated without changing v13 in place.\n\n")
        h.write("## Geology\n\n`v13_geology_geometry_audit.csv` contains model-measured top/base ranges, plan extents, and local vertical-thickness statistics for every active geology/rock instance. Status remains `UNRESOLVED_DESIGN_SURFACE` where station-specific design geological surfaces are not available as machine-readable coordinates; no false PASS is assigned.\n")

    print("WROTE", args.out_dir)
    print("DAM bbox", tuple(round(v,6) for v in dbb), "upstream", upstream_side)
    if cutoff_points:
        print("CUTOFF bbox", tuple(round(v,6) for v in bbox(cutoff_points)))
        print("CUTOFF max station depth", round(max_depth_station[3],6), "at y", max_depth_station[0])

if __name__ == "__main__":
    main()
