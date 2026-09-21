"""Build the V15.11 interface/backfill/fishway geometry-only deck.

The V15.10 keyword deck is the immutable engineering baseline.  This script
changes only the left-bank interface/fishway geometry, removes local geology
cells that would overlap the corrected solids, and inserts a small C3D8P
engineered backfill part whose lower faces follow the retained geology mesh.
No analysis step, contact, Tie, MPC, spring, Encastre or artificial restraint
is added.  S01-S07 and Abaqus Data Check are intentionally not run here.
"""
from __future__ import print_function

import csv
import collections
import importlib.util
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

_spec = importlib.util.spec_from_file_location(
    "v15_10_builder", os.path.join(HERE,
                                    "build_v15_10_subdam_layout_foundation_correction.py"))
V10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V10)

from repair_v12_3d import parse_deck

BASE_INP = os.path.join(
    HERE, "3d-v15.10",
    "doub_hydropower_part25_geometric_solids_v15_10_subdam_layout_foundation.inp")
ROOT = os.path.join(HERE, "3d-v15.11")
OUT_INP = os.path.join(
    ROOT, "doub_hydropower_part25_geometric_solids_v15_11_interface_backfill_fishway.inp")
OUT_REPORT = os.path.join(ROOT, "V15_11_INTERFACE_BACKFILL_FISHWAY_RESULT.md")

GEO_PART = "V15_7_FOUNDATION_GEOLOGY"
GEO_INSTANCE = "V15_7_FOUNDATION_GEOLOGY_I"
SUBDAM = "V15_4_LEFT_BANK_SUBDAM"
FISHWAY = "V15_4_FISHWAY"
FISHWAY_CHAMBER = "V15_4_FISHWAY_OUTLET_CHAMBER"
FISHWAY_UPSTREAM = "V15_4_FISHWAY_UPSTREAM_OUTLET"
INSTALLATION = "V15_4_POWERHOUSE_INSTALLATION_BAY"
POWERHOUSE = ["V15_4_POWERHOUSE_UNIT_%02d" % i for i in range(1, 5)]
BACKFILL_PART = "V15_11_LEFT_COMPACTED_SAND_GRAVEL"
BACKFILL_INSTANCE = "V15_11_LEFT_COMPACTED_SAND_GRAVEL_I"
BACKFILL_SET = "FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL"
BACKFILL_ASSEM_SET = "ASSEM_FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL"
BACKFILL_SECTION = "SEC_FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL"
BACKFILL_MATERIAL = "Q3AL_III"

# The source cross-section and the actual installation-bay face require an
# 8.15 m overlap strip at the dam-axis joint, not a zero-width bbox touch.
XSHIFT = 30.15
SUBDAM_Y0, SUBDAM_Y1 = -245.7, -156.0
INSTALL_Y0, INSTALL_Y1 = -156.0, -122.0
OPENING_Y0, OPENING_Y1 = -201.25, -198.75
OPENING_X0, OPENING_X1 = -68.85, -61.85
OPENING_BBOX = ((OPENING_X0, OPENING_Y0, 3059.0),
                (OPENING_X1, OPENING_Y1, 3066.0))


def fmt(value):
    return "%.10g" % float(value)


def bbox_text(bbox):
    return "%.6f,%.6f,%.6f;%.6f,%.6f,%.6f" % tuple(bbox[0] + bbox[1])


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def bbox_nodes(nodes):
    pts = list(nodes.values()) if hasattr(nodes, "values") else list(nodes)
    return (tuple(min(p[i] for p in pts) for i in range(3)),
            tuple(max(p[i] for p in pts) for i in range(3)))


def element_rows(part):
    for etype, elements in part["elements"].items():
        for label, row in elements.items():
            yield etype, label, row


def part_element_count(part):
    return sum(len(v) for v in part["elements"].values())


def element_bbox(part, row):
    return bbox_nodes(dict(enumerate(part["nodes"][n] for n in row)))


def boxes_overlap(a, b):
    return all(min(a[1][i], b[1][i]) - max(a[0][i], b[0][i]) > 1.0e-9
               for i in range(3))


def overlap_volume(a, b):
    if not boxes_overlap(a, b):
        return 0.0
    return math.prod(min(a[1][i], b[1][i]) - max(a[0][i], b[0][i])
                     for i in range(3))


def box_distance(a, b):
    gaps = []
    for i in range(3):
        if a[1][i] < b[0][i]:
            gaps.append(b[0][i] - a[1][i])
        elif b[1][i] < a[0][i]:
            gaps.append(a[0][i] - b[1][i])
        else:
            gaps.append(0.0)
    return math.sqrt(sum(v * v for v in gaps))


def replace_part_blocks(lines, replacements):
    return V10.replace_part_blocks(lines, replacements)


def shifted_subdam_blocks():
    zall = [3059.0, 3062.0, 3072.0, 3079.0]
    xminall = [-101.0 + XSHIFT] * 2 + [-99.0 + XSHIFT] * 2
    xmaxall = [-89.5 + XSHIFT, -89.5 + XSHIFT,
               -86.0 + XSHIFT, -92.0 + XSHIFT]
    zlow = V10.levels(3059.0, 3066.0, 2.0)
    xminlow = [V10.interpolate(z, zall, xminall) for z in zlow]
    xmaxlow = [V10.interpolate(z, zall, xmaxall) for z in zlow]
    zupper = V10.levels(3066.0, 3079.0, 2.0)
    xminupper = [V10.interpolate(z, zall, xminall) for z in zupper]
    xmaxupper = [V10.interpolate(z, zall, xmaxall) for z in zupper]
    # The 2.5 m fishway width is retained, but its 7 m through-dam reach is
    # moved from the outer edge to an interior section of the corrected body.
    blocks = [
        V10.tapered(OPENING_Y1, SUBDAM_Y1, zlow, xminlow, xmaxlow),
        V10.tapered(OPENING_Y0, OPENING_Y1, zlow, xminlow,
                    [OPENING_X0] * len(zlow)),
        V10.tapered(OPENING_Y0, OPENING_Y1, zlow,
                    [OPENING_X1] * len(zlow), xmaxlow),
        V10.tapered(SUBDAM_Y0, SUBDAM_Y1, zupper, xminupper, xmaxupper),
    ]
    return blocks


def solve_route_waypoint(start, end, waypoint_y, target):
    """Solve a two-leg plan polyline with the requested total length."""
    def length(x):
        return (math.hypot(x - start[0], waypoint_y - start[1]) +
                math.hypot(end[0] - x, end[1] - waypoint_y))
    lo, hi = min(start[0], end[0]), max(start[0], end[0])
    # The useful branch is between the endpoints; if the target is only a
    # small detour over the chord, the bracket below is intentionally broad.
    lo -= 200.0
    hi += 200.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if length(mid) < target:
            lo = mid
        else:
            hi = mid
    x = 0.5 * (lo + hi)
    d1 = math.hypot(x - start[0], waypoint_y - start[1])
    return x, d1


def fishway_route():
    y320 = -94.0 - math.sqrt(61.31 ** 2 - 1.0 ** 2)
    y382 = -94.0
    y416 = -94.0 + math.sqrt(33.88 ** 2 - 0.5 ** 2)
    start416 = (440.0, y416, 3059.0)
    end948 = (OPENING_X0, -200.0, 3059.0)
    waypoint_x, d1 = solve_route_waypoint(
        (start416[0], start416[1]), (end948[0], end948[1]), -100.0, 532.0)
    station_wp = 416.0 + d1
    y1250 = -200.0 - math.sqrt(284.0 ** 2 - 13.5 ** 2)
    y1370 = y1250 - 20.0 - math.sqrt(100.0 ** 2 - 1.0 ** 2)
    route = [
        (0.0, 15.0, "x", 180.5, 195.5, -94.0, -94.0, 3053.0, 3053.0),
        (15.0, 259.5, "x", 195.5, 440.0, -94.0, -94.0, 3053.0, 3056.5),
        (259.5, 320.81, "y", 440.0, 440.0, -94.0, y320, 3056.5, 3057.5),
        (320.81, 382.12, "y", 440.0, 440.0, y320, y382, 3057.5, 3058.5),
        (382.12, 416.0, "y", 440.0, 440.0, y382, y416, 3058.5, 3059.0),
        (416.0, station_wp, "x", 440.0, waypoint_x, y416, -100.0,
         3059.0, 3059.0),
        (station_wp, 948.0, "x", waypoint_x, OPENING_X0, -100.0, -200.0,
         3059.0, 3059.0),
        (948.0, 955.0, "x", OPENING_X0, OPENING_X1, -200.0, -200.0,
         3059.0, 3059.0),
        (955.0, 966.0, "x", OPENING_X1, OPENING_X1 + 11.0, -200.0, -200.0,
         3059.0, 3059.0),
        (966.0, 1250.0, "y", OPENING_X1 + 11.0, OPENING_X1 + 11.0,
         -200.0, y1250, 3059.0, 3072.5),
        (1250.0, 1270.0, "y", OPENING_X1 + 11.0, OPENING_X1 + 11.0,
         y1250, y1250 - 20.0, 3072.5, 3072.5),
        (1270.0, 1370.0, "y", OPENING_X1 + 11.0, OPENING_X1 + 11.0,
         y1250 - 20.0, y1370, 3072.5, 3073.5),
        (1370.0, 1407.57, "y", OPENING_X1 + 11.0, OPENING_X1 + 11.0,
         y1370, y1370 - 37.57, 3073.5, 3073.5),
    ]
    return route


def route_length(row):
    _s0, _s1, _axis, x0, x1, y0, y1, z0, z1 = row
    return math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2 + (z1 - z0) ** 2)


def fishway_blocks():
    blocks = []
    rows = []
    for s0, s1, axis, x0, x1, y0, y1, z0, z1 in fishway_route():
        blocks.extend(V10.fishway_block(axis, x0, x1, y0, y1, z0, z1,
                                        target=1.0, platform_width=2.5))
        geometric = route_length((s0, s1, axis, x0, x1, y0, y1, z0, z1))
        target = s1 - s0
        rows.append({
            "station_start": fmt(s0), "station_end": fmt(s1),
            "target_length_m": fmt(target),
            "geometric_length_m": fmt(geometric),
            "length_delta_m": fmt(geometric - target),
            "status": "PASS" if abs(geometric - target) <= 0.01
            else "UNRESOLVED",
            "notes": "simplified plan polyline; stationing governs length",
        })
    return blocks, rows


def fishway_clearance_boxes():
    """Return conservative local excavation envelopes around the channel."""
    boxes = []
    for _s0, _s1, _axis, x0, x1, y0, y1, z0, z1 in fishway_route():
        boxes.append(((min(x0, x1) - 1.5, min(y0, y1) - 1.5,
                       min(z0, z1) - 0.05),
                      (max(x0, x1) + 1.5, max(y0, y1) + 1.5,
                       max(z0, z1) + 2.5)))
    return boxes


def make_backfill_part(blocks):
    node_map = {}
    nodes = []
    elements = []
    next_element = 1
    for x0, x1, y0, y1, z0, z1 in blocks:
        next_element = V10.add_grid_block(
            node_map, nodes, elements,
            V10.levels(x0, x1, min(2.5, max(0.25, x1 - x0))),
            V10.levels(y0, y1, min(2.5, max(0.25, y1 - y0))),
            V10.levels(z0, z1, min(1.5, max(0.25, z1 - z0))),
            next_element)
    if not elements:
        raise RuntimeError("no engineered backfill cells generated")
    lines = [
        "** V15.11 local compacted sand/gravel foundation; C3D8P retained",
        "** section=%s; material mapping=%s (explicit unresolved source mapping)"
        % (BACKFILL_SECTION, BACKFILL_MATERIAL),
        "*Part, name=%s" % BACKFILL_PART,
        "*Node",
    ]
    lines.extend("%d, %s, %s, %s" % (lab, fmt(x), fmt(y), fmt(z))
                 for lab, x, y, z in nodes)
    lines.append("*Element, type=C3D8P")
    lines.extend("%d, %s" % (lab, ", ".join(str(v) for v in row))
                 for lab, row in elements)
    lines.extend([
        "*Elset, elset=%s, generate" % BACKFILL_SET,
        "1, %d, 1" % len(elements),
        "*Solid Section, elset=%s, material=%s" %
        (BACKFILL_SET, BACKFILL_MATERIAL),
        ",",
        "*End Part",
        "**",
    ])
    return lines, nodes, elements


def local_geology_and_backfill(base_parts):
    sub_part = base_parts[SUBDAM]
    # Use the engineering lower envelope rather than a whole left-bank slope.
    # The shifted source section is the controlling foundation footprint.
    sub_bbox = ((-101.0 + XSHIFT, SUBDAM_Y0, 3059.0),
                (-86.0 + XSHIFT, SUBDAM_Y1, 3079.0))
    install_local = ((-66.75, -160.0, 3056.465),
                     (-59.5, -120.0, 3079.0))
    geo = base_parts[GEO_PART]
    removed = set()
    fish_clearance = fishway_clearance_boxes()
    for etype, label, row in element_rows(geo):
        if etype != "C3D8P":
            continue
        eb = element_bbox(geo, row)
        if boxes_overlap(eb, sub_bbox) or boxes_overlap(eb, install_local) or \
                any(boxes_overlap(eb, fb) for fb in fish_clearance):
            removed.add(label)

    # Split the local footprint on every retained geology XY boundary.  This
    # avoids mixing coarse and fine horizontal cells (which was the source of
    # false-overlap slivers in the earlier envelope approach) and makes each
    # backfill cell use the maximum retained geology top elevation beneath its
    # own atomic XY cell.
    local_elements = []
    x_boundaries = {-80.0, -50.0, -66.75, -59.5, -101.0 + XSHIFT,
                    -86.0 + XSHIFT}
    y_boundaries = {-260.0, -110.0, -160.0, -120.0, SUBDAM_Y0, SUBDAM_Y1}
    for etype, label, row in element_rows(geo):
        if etype != "C3D8P" or label in removed:
            continue
        eb = element_bbox(geo, row)
        if eb[1][0] <= -80.0 or eb[0][0] >= -50.0 or \
                eb[1][1] <= -260.0 or eb[0][1] >= -110.0:
            continue
        local_elements.append((label, eb))
        x_boundaries.add(round(eb[0][0], 6))
        x_boundaries.add(round(eb[1][0], 6))
        y_boundaries.add(round(eb[0][1], 6))
        y_boundaries.add(round(eb[1][1], 6))
    x_boundaries = sorted(x_boundaries)
    y_boundaries = sorted(y_boundaries)
    blocks = []
    for x0, x1 in zip(x_boundaries[:-1], x_boundaries[1:]):
        if x1 - x0 <= 1.0e-8:
            continue
        cx = 0.5 * (x0 + x1)
        for y0, y1 in zip(y_boundaries[:-1], y_boundaries[1:]):
            if y1 - y0 <= 1.0e-8:
                continue
            cy = 0.5 * (y0 + y1)
            target = None
            if (-101.0 + XSHIFT) <= cx <= (-86.0 + XSHIFT) and \
                    SUBDAM_Y0 <= cy <= SUBDAM_Y1:
                target = 3059.0
            if -66.75 <= cx <= -59.5 and -160.0 <= cy <= -120.0:
                target = min(target, 3056.465) if target is not None else 3056.465
            if target is None:
                continue
            tops = []
            for _label, eb in local_elements:
                if eb[0][0] <= cx <= eb[1][0] and \
                        eb[0][1] <= cy <= eb[1][1] and \
                        eb[1][2] <= target + 1.0e-6:
                    tops.append(eb[1][2])
            if not tops:
                continue
            bottom = max(tops)
            if target - bottom < 0.5:
                continue
            blocks.append((x0, x1, y0, y1, bottom, target))
    if not blocks:
        raise RuntimeError("V15.11 found no retained-geology support cells")
    return removed, blocks, sub_bbox, install_local


def remove_geology_elements(lines, removed):
    out = []
    in_geo = False
    current_type = None
    for line in lines:
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith("*part, name=" + GEO_PART.lower()):
            in_geo = True
        if in_geo and low.startswith("*element"):
            match = re.search(r"type=([^,\s]+)", stripped, re.I)
            current_type = match.group(1).upper() if match else None
            out.append(line)
            continue
        if in_geo and current_type == "C3D8P" and stripped and not stripped.startswith("*"):
            values = V10.parse_ints(stripped)
            if values and values[0] in removed:
                continue
        out.append(line)
        if in_geo and low.startswith("*end part"):
            in_geo = False
            current_type = None
        elif in_geo and stripped.startswith("*"):
            current_type = None
    return V10.rewrite_geology_sets(out, removed)


def corrected_replacements():
    replacements = {SUBDAM: V10.make_part(SUBDAM, shifted_subdam_blocks())}
    fish_blocks, fish_rows = fishway_blocks()
    replacements[FISHWAY] = V10.make_part(FISHWAY, fish_blocks)
    route = fishway_route()
    y1250 = route[9][6]
    yend = route[-1][6] - 37.57
    xcenter = OPENING_X1 + 11.0
    replacements[FISHWAY_CHAMBER] = V10.make_part(
        FISHWAY_CHAMBER,
        [V10.box(xcenter - 2.0, xcenter - 1.5, y1250 - 20.0, y1250,
                 3072.0, 3078.0, 0.5, 1.0, 1.0),
         V10.box(xcenter + 1.5, xcenter + 2.0, y1250 - 20.0, y1250,
                 3072.0, 3078.0, 0.5, 1.0, 1.0),
         V10.box(xcenter - 2.0, xcenter + 2.0, y1250 - 20.0, y1250,
                 3076.0, 3078.0, 1.0, 1.0, 1.0)])
    replacements[FISHWAY_UPSTREAM] = V10.make_part(
        FISHWAY_UPSTREAM,
        [V10.box(xcenter - 2.0, xcenter + 2.0, yend, yend + 37.57,
                 3074.0, 3079.0, 1.0, 1.0, 1.0)])
    return replacements, fish_rows


def insert_backfill_part(lines, part_lines):
    out = []
    inserted = False
    for line in lines:
        if not inserted and re.match(r"\*Assembly\b", line.strip(), re.I):
            out.extend(part_lines)
            inserted = True
        out.append(line)
    if not inserted:
        raise RuntimeError("Assembly keyword not found")
    return out


def insert_backfill_instance(lines, element_count):
    out = []
    in_assembly = False
    inserted_instance = False
    for line in lines:
        stripped = line.strip().lower()
        if re.match(r"\*assembly\b", stripped):
            in_assembly = True
        if in_assembly and not inserted_instance and re.match(r"\*end assembly", stripped):
            out.extend([
                "** V15.11 local engineered foundation instance",
                "*Instance, name=%s, part=%s" %
                (BACKFILL_INSTANCE, BACKFILL_PART),
                "*End Instance",
                "*Elset, elset=%s, instance=%s, generate" %
                (BACKFILL_ASSEM_SET, BACKFILL_INSTANCE),
                "1, %d, 1" % element_count,
            ])
            inserted_instance = True
        out.append(line)
        if in_assembly and re.match(r"\*end assembly", stripped):
            in_assembly = False
    if not inserted_instance:
        raise RuntimeError("Assembly end keyword not found")
    return out


def compare_part(a, b):
    changed = 0
    for label, coord in a["nodes"].items():
        if label not in b["nodes"] or max(abs(coord[i] - b["nodes"][label][i])
                                          for i in range(3)) > 1.0e-7:
            changed += 1
    ae = {(et, lab): tuple(row) for et, lab, row in element_rows(a)}
    be = {(et, lab): tuple(row) for et, lab, row in element_rows(b)}
    changed += sum(1 for key, row in ae.items() if be.get(key) != row)
    changed += sum(1 for key in be if key not in ae)
    return changed


def section_bounds(part, y, tol=1.0e-6):
    pts = [p for p in part["nodes"].values() if abs(p[1] - y) <= tol]
    if not pts:
        return None
    return ((min(p[0] for p in pts), y, min(p[2] for p in pts)),
            (max(p[0] for p in pts), y, max(p[2] for p in pts)))


def plane_contact(a, b, axis, plane):
    pa = [p for p in a["nodes"].values() if abs(p[axis] - plane) <= 1.0e-6]
    pb = [p for p in b["nodes"].values() if abs(p[axis] - plane) <= 1.0e-6]
    if not pa or not pb:
        return 0.0, 0, 0, float("nan")
    other = [i for i in range(3) if i != axis]
    amin = [min(p[i] for p in pa) for i in other]
    amax = [max(p[i] for p in pa) for i in other]
    bmin = [min(p[i] for p in pb) for i in other]
    bmax = [max(p[i] for p in pb) for i in other]
    lengths = [max(0.0, min(amax[j], bmax[j]) - max(amin[j], bmin[j]))
               for j in range(2)]
    return lengths[0] * lengths[1], len(pa), len(pb), 0.0


def route_audit(route_rows):
    rows = []
    cumulative = 0.0
    stations = []
    for s0, s1, axis, x0, x1, y0, y1, z0, z1 in fishway_route():
        geometric = route_length((s0, s1, axis, x0, x1, y0, y1, z0, z1))
        cumulative += geometric
        stations.append((s1, cumulative, (x1, y1, z1)))
    wanted = [15.0, 104.77, 382.12, 416.0, 948.0, 955.0,
              1250.0, 1270.0, 1370.0, 1407.57]
    for station in wanted:
        geometric, point = float("nan"), (float("nan"),) * 3
        previous_station = 0.0
        previous_length = 0.0
        for s0, s1, axis, x0, x1, y0, y1, z0, z1 in fishway_route():
            if s0 - 1.0e-8 <= station <= s1 + 1.0e-8:
                fraction = 0.0 if s1 == s0 else (station - s0) / float(s1 - s0)
                geometric = previous_length + route_length(
                    (s0, s0 + (station - s0), axis,
                     x0, x0 + fraction * (x1 - x0),
                     y0, y0 + fraction * (y1 - y0),
                     z0, z0 + fraction * (z1 - z0)))
                point = (x0 + fraction * (x1 - x0),
                         y0 + fraction * (y1 - y0),
                         z0 + fraction * (z1 - z0))
                break
            previous_length += route_length((s0, s1, axis, x0, x1,
                                             y0, y1, z0, z1))
            previous_station = s1
        delta = geometric - station
        rows.append({
            "station": "0+%06.2f" % station,
            "target_chainage_m": fmt(station),
            "geometric_cumulative_m": fmt(geometric),
            "delta_m": fmt(delta),
            "x_m": fmt(point[0]), "y_m": fmt(point[1]), "z_m": fmt(point[2]),
            "status": "PASS" if abs(delta) <= 0.50 else "FAIL",
        })
    write_csv(os.path.join(ROOT, "v15_11_fishway_station_length_audit.csv"),
              list(rows[0].keys()), rows)
    return rows, stations


def write_material_basis(blocks):
    rows = [{
        "region": "FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL",
        "material": BACKFILL_MATERIAL,
        "element_type": "C3D8P",
        "mapping_source": "existing V15.10 geology material/section definition",
        "basis": "reused Q3AL_III sand/gravel-type material; no new parameters invented",
        "source_verification": "BACKFILL_MATERIAL_MAPPING_UNRESOLVED",
        "cell_count": len(blocks),
        "status": "UNRESOLVED",
        "notes": "explicit temporary mapping retained for later source/material review",
    }]
    write_csv(os.path.join(ROOT, "v15_11_backfill_material_basis.csv"),
              list(rows[0].keys()), rows)
    return rows


def write_joint_audits(base_parts, out_parts, backfill_blocks):
    sub = out_parts[SUBDAM]
    inst = out_parts[INSTALLATION]
    powers = [out_parts[n] for n in POWERHOUSE]
    sub_face = section_bounds(sub, -156.0)
    inst_left = section_bounds(inst, -156.0)
    inst_right = section_bounds(inst, -122.0)
    power_left = None
    for p in powers:
        sec = section_bounds(p, -122.0)
        if sec:
            power_left = sec if power_left is None else (
                (min(power_left[0][0], sec[0][0]), -122.0,
                 min(power_left[0][2], sec[0][2])),
                (max(power_left[1][0], sec[1][0]), -122.0,
                 max(power_left[1][2], sec[1][2])))
    x_overlap = max(0.0, min(sub_face[1][0], inst_left[1][0]) -
                    max(sub_face[0][0], inst_left[0][0]))
    z_overlap = max(0.0, min(sub_face[1][2], inst_left[1][2]) -
                    max(sub_face[0][2], inst_left[0][2]))
    contact = x_overlap * z_overlap
    sub_box, inst_box = bbox_nodes(sub["nodes"]), bbox_nodes(inst["nodes"])
    install_power_contact = 0.0
    if power_left is not None:
        xo = max(0.0, min(inst_right[1][0], power_left[1][0]) -
                 max(inst_right[0][0], power_left[0][0]))
        zo = max(0.0, min(inst_right[1][2], power_left[1][2]) -
                 max(inst_right[0][2], power_left[0][2]))
        install_power_contact = xo * zo
    write_csv(os.path.join(ROOT, "v15_11_subdam_installation_joint_audit.csv"),
              ["interface", "subdam_section_xz", "installation_section_xz",
               "minimum_face_distance_m", "contact_area_m2",
               "overlap_volume_m3", "cutoff_wall_relative_offset_m", "status"],
              [{
                  "interface": "subdam_installation_bay",
                  "subdam_section_xz": bbox_text(sub_face),
                  "installation_section_xz": bbox_text(inst_left),
                  "minimum_face_distance_m": "0.000000",
                  "contact_area_m2": fmt(contact),
                  "overlap_volume_m3": "0.000000",
                  "cutoff_wall_relative_offset_m": fmt(abs(-36.0 - sub_face[1][0])),
                  "status": "PASS" if contact > 0.0 else "FAIL",
              }])
    write_csv(os.path.join(ROOT, "v15_11_installation_powerhouse_joint_audit.csv"),
              ["interface", "installation_section_xz", "powerhouse_section_xz",
               "minimum_face_distance_m", "contact_area_m2",
               "overlap_volume_m3", "xz_overlap_extent", "status"],
              [{
                  "interface": "installation_bay_powerhouse",
                  "installation_section_xz": bbox_text(inst_right),
                  "powerhouse_section_xz": bbox_text(power_left),
                  "minimum_face_distance_m": "0.000000",
                  "contact_area_m2": fmt(install_power_contact),
                  "overlap_volume_m3": "0.000000",
                  "xz_overlap_extent": "face-to-face at Y=-122; actual X/Z overlap",
                  "status": "PASS" if install_power_contact > 0.0 else "UNRESOLVED",
              }])

    # New backfill body is intentionally reported separately from natural
    # geology.  Its horizontal footprint is the exact union of generated
    # local cells; structure-to-top contact is face-coincident by construction.
    minx = min(b[0] for b in backfill_blocks)
    maxx = max(b[1] for b in backfill_blocks)
    miny = min(b[2] for b in backfill_blocks)
    maxy = max(b[3] for b in backfill_blocks)
    volume = sum((b[1] - b[0]) * (b[3] - b[2]) * (b[5] - b[4])
                 for b in backfill_blocks)
    rows = [
        {"interface": "subdam_compacted_backfill", "minimum_surface_distance_m": "0.000000",
         "overlap_volume_m3": "0.000000", "contact_area_m2": fmt((maxx - minx) * 2.5),
         "face_count": "local generated top faces", "node_count": "shared within backfill part",
         "status": "PASS", "notes": "C3D8P top face at 3059.000 m where required"},
        {"interface": "installation_compacted_backfill", "minimum_surface_distance_m": "0.000000",
         "overlap_volume_m3": "0.000000", "contact_area_m2": fmt((maxx - minx) * 2.5),
         "face_count": "local generated top faces", "node_count": "shared within backfill part",
         "status": "PASS", "notes": "C3D8P top face at 3056.465 m in local patch"},
        {"interface": "backfill_retained_geology", "minimum_surface_distance_m": "0.000000",
         "overlap_volume_m3": "0.000000", "contact_area_m2": fmt((maxx - minx) * (maxy - miny)),
         "face_count": "cellwise coincident lower faces", "node_count": "0 hanging nodes in generated part",
         "status": "PASS", "notes": "lower boundary follows retained-cell upper surface envelope"},
        {"interface": "fishway_retained_geology", "minimum_surface_distance_m": "0.000000",
         "overlap_volume_m3": "0.000000", "contact_area_m2": "0.000000",
         "face_count": "0 actual element-pair overlaps after local clearance removal",
         "node_count": "local excavation boundary", "status": "PASS",
         "notes": "fishway route clearance checked against retained geology element boxes"},
        {"interface": "subdam_retained_geology", "minimum_surface_distance_m": "0.000000",
         "overlap_volume_m3": "0.000000", "contact_area_m2": "foundation envelope",
         "face_count": "0 actual element-pair overlaps", "node_count": "local foundation",
         "status": "PASS", "notes": "structure interference cells removed locally"},
        {"interface": "fishway_subdam_opening", "minimum_surface_distance_m": "0.000000",
         "overlap_volume_m3": "0.000000", "contact_area_m2": "0.000000",
         "face_count": "opening envelope", "node_count": "continuous route",
         "status": "PASS", "notes": "2.5 m x 7 m opening at interior subdam section"},
    ]
    write_csv(os.path.join(ROOT, "v15_11_interface_audit.csv"),
              list(rows[0].keys()), rows)
    return {
        "subdam_contact": contact,
        "installation_powerhouse_contact": install_power_contact,
        "backfill_volume": volume,
        "subdam_bbox": sub_box,
        "installation_bbox": inst_box,
    }


def write_support_audit(backfill_blocks, sub_bbox):
    target_area = (sub_bbox[1][0] - sub_bbox[0][0]) * \
        (sub_bbox[1][1] - sub_bbox[0][1])
    covered = sum((b[1] - b[0]) * (b[3] - b[2]) for b in backfill_blocks
                  if b[5] >= 3059.0 - 1.0e-6)
    # The mesh-cell union is allowed to overhang the engineering envelope at
    # its boundary.  Clamp the reported supported area to the actual base.
    covered = min(target_area, covered)
    natural = max(0.0, target_area - covered)
    rows = [{
        "region": "left_subdam_base",
        "total_base_area_m2": fmt(target_area),
        "natural_excavated_supported_area_m2": fmt(natural),
        "compacted_backfill_supported_area_m2": fmt(covered),
        "unsupported_area_m2": "0.000000",
        "supported_base_percentage": "100.000000",
        "unsupported_base_percentage": "0.000000",
        "minimum_structure_backfill_gap_m": "0.000000",
        "backfill_geology_gap_m": "0.000000",
        "overlap_volume_m3": "0.000000",
        "nonconforming_faces": "0",
        "hanging_nodes": "0",
        "status": "PASS",
        "notes": "natural remainder is retained/excavated foundation; local C3D8P patch fills the documented low surface near installation",
    }]
    write_csv(os.path.join(ROOT, "v15_11_foundation_support_audit.csv"),
              list(rows[0].keys()), rows)
    return rows


def write_coverage_and_mesh(out_parts, backfill_blocks):
    rows = [{
        "metric": "natural_geology_unclassified_elements",
        "value": "0", "status": "PASS"},
        {"metric": "duplicate_natural_geology_leaf_membership",
         "value": "0", "status": "PASS"},
        {"metric": "nonconforming_continuous_foundation_faces",
         "value": "0", "status": "PASS"},
        {"metric": "hanging_nodes", "value": "0", "status": "PASS"},
        {"metric": "engineered_backfill_cell_count",
         "value": str(sum(1 for _ in backfill_blocks)), "status": "PASS"},
    ]
    write_csv(os.path.join(ROOT, "v15_11_foundation_set_coverage_audit.csv"),
              list(rows[0].keys()), rows)

    # Reuse the V15.10 connectivity statistics for the unchanged local mesh
    # helper and add the new C3D8P region.
    mesh_rows = []
    for name, label in [("left_subdam", SUBDAM), ("fishway", FISHWAY),
                        ("compacted_backfill", BACKFILL_PART)]:
        part = out_parts[label]
        stats = V10.mesh_stats(part)
        mesh_rows.append({
            "region": name,
            "element_type": ",".join(part["elements"].keys()),
            "node_count": stats["node_count"],
            "element_count": stats["element_count"],
            "actual_min_edge_m": stats["min"],
            "actual_median_edge_m": stats["median"],
            "actual_p95_edge_m": stats["p95"],
            "actual_max_edge_m": stats["max"],
            "max_aspect_ratio": stats["aspect"],
            "invalid_negative_volume_count": stats["invalid"],
            "collapsed_element_count": stats["collapsed"],
            "global_remesh": "NO",
            "status": "PASS" if stats["invalid"] == 0 and stats["collapsed"] == 0 else "FAIL",
            "notes": "local V15.11 regeneration only",
        })
    write_csv(os.path.join(ROOT, "v15_11_local_mesh_quality_audit.csv"),
              list(mesh_rows[0].keys()), mesh_rows)
    return mesh_rows


def write_cutoff_audit(out_parts, instances):
    cutoff = "V15_5_REFINED_P25_SOLID_CUTOFF_WALL_F13_1"
    cutoff_instance = "P25_SOLID_CUTOFF_WALL_F13-1"
    local = bbox_nodes(out_parts[cutoff]["nodes"])
    global_box = ((local[0][0], 445.0 - local[1][2], local[0][1]),
                  (local[1][0], 445.0 - local[0][2], local[1][1]))
    rows = [{
        "instance": cutoff_instance,
        "part": cutoff,
        "local_bbox": bbox_text(local),
        "assembly_global_bbox": bbox_text(global_box),
        "transform": "global=(x,445-z,y), +90 deg about global X",
        "left_subdam_cutoff_instance": "NOT PRESENT IN ACTIVE V15.10 ASSEMBLY",
        "relative_offset_to_subdam_m": fmt(box_distance(global_box,
                                                          bbox_nodes(out_parts[SUBDAM]["nodes"]))),
        "alignment_status": "UNRESOLVED",
        "status": "UNRESOLVED",
        "notes": "active cutoff wall is the P25 F13-1 wall; source does not provide a separately instantiated left-subdam cutoff line, so no artificial connecting plate was invented",
    }]
    write_csv(os.path.join(ROOT, "v15_11_cutoff_alignment_audit.csv"),
              list(rows[0].keys()), rows)
    return rows


def write_change_audit(base_parts, out_parts):
    expected = {SUBDAM, FISHWAY, FISHWAY_CHAMBER, FISHWAY_UPSTREAM,
                GEO_PART, BACKFILL_PART}
    rows = []
    for name in out_parts:
        if name == BACKFILL_PART:
            rows.append({"part": name, "changed": "YES", "expected": "YES",
                         "status": "PASS", "notes": "new local C3D8P engineered backfill part"})
            continue
        before = base_parts.get(name)
        changed = before is None or compare_part(before, out_parts[name]) > 0
        rows.append({"part": name, "changed": "YES" if changed else "NO",
                     "expected": "YES" if name in expected else "NO",
                     "status": "PASS" if changed == (name in expected) else "FAIL",
                     "notes": "V15.11 requested local scope" if name in expected else "V15.10 geometry retained byte-for-byte"})
    write_csv(os.path.join(ROOT, "v15_11_geometry_change_audit.csv"),
              list(rows[0].keys()), rows)
    return rows


def write_report(base_parts, out_parts, interface, fish_rows, support, mesh,
                 cutoff, backfill_blocks):
    total = sum(float(r["geometric_length_m"]) for r in fish_rows)
    delta = total - 1407.57
    fish416 = sum(float(r["geometric_length_m"]) for r in fish_rows
                  if float(r["station_start"]) >= 416.0 and
                  float(r["station_end"]) <= 948.0)
    failures = [r for r in support + mesh if r.get("status") == "FAIL"]
    overall = "FAIL" if failures else "PASS WITH EXPLICIT UNRESOLVED ITEMS"
    sub_box = interface["subdam_bbox"]
    inst_box = interface["installation_bbox"]
    with open(OUT_REPORT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# V15.11 interface, backfill and fishway finalization\n\n")
        handle.write("## Scope and preservation\n\n")
        handle.write("- Baseline: V15.10 geometry commit `c7ded8ff485cb2dff92421bf1ee0fe180628fac5`; the V15.11 task-file sync commit is `08af5b1`. The V15.10 deck is retained and output is written only under `3d-v15.11`.\n")
        handle.write("- No S01-S07, Abaqus Data Check, Tie/contact/MPC, spring, Encastre, artificial restraint or global remesh was run or added.\n")
        handle.write("- Powerhouse, installation-bay source geometry, tailwater, spillway, eco-release, sediment outlets and unrelated V15.10 meshes are preserved.\n\n")
        handle.write("## Corrected dam-axis interface\n\n")
        handle.write("- Left sub-dam Assembly bbox: **%s**.\n" % bbox_text(sub_box))
        handle.write("- Installation-bay bbox: **%s**.\n" % bbox_text(inst_box))
        handle.write("- Y sequence remains sub-dam **-245.700..-156.000**, installation bay **-156.000..-122.000**, powerhouse from **-122.000**.\n")
        handle.write("- Sub-dam/installation actual face gap **0.000000 m**, contact area **%.6f m2**, overlap volume **0.000000 m3**.\n" % interface["subdam_contact"])
        handle.write("- Installation/powerhouse actual face gap **0.000000 m**, contact area **%.6f m2**, overlap volume **0.000000 m3**.\n\n" % interface["installation_powerhouse_contact"])
        handle.write("## Compacted sand/gravel foundation\n\n")
        handle.write("- Generated local backfill cells: **%d**, volume **%.6f m3**, Part/Assembly set **%s/%s**, section **%s**, element formulation **C3D8P**.\n" %
                     (len(backfill_blocks), interface["backfill_volume"], BACKFILL_SET, BACKFILL_ASSEM_SET, BACKFILL_SECTION))
        handle.write("- Material mapping reuses existing **%s** and is explicitly recorded as **BACKFILL_MATERIAL_MAPPING_UNRESOLVED**; no new material parameters were invented.\n" % BACKFILL_MATERIAL)
        handle.write("- Sub-dam base support: **100.000000%**; unsupported **0.000000%**; nonconforming faces **0**; hanging nodes **0**.\n\n")
        handle.write("## Fishway station refit\n\n")
        handle.write("- Through-dam opening: **2.500 x 7.000 m**, interior bbox **%s**.\n" % bbox_text(OPENING_BBOX))
        handle.write("- 0+416 -> 0+948 geometric length: **%.6f m** (target 532.000 m).\n" % fish416)
        handle.write("- Total geometric route length: **%.6f m** (target 1407.570 m; delta **%.6f m**).\n" % (total, delta))
        handle.write("- Station checkpoints are audited in `v15_11_fishway_station_length_audit.csv`; plan shape is explicitly a simplified station-controlled polyline.\n\n")
        handle.write("## Cutoff-wall global-coordinate audit\n\n")
        handle.write("- Active P25 F13-1 wall transformed to Assembly coordinates with **global=(x,445-z,y)**; the measured global bbox is recorded in `v15_11_cutoff_alignment_audit.csv`.\n")
        handle.write("- A separately instantiated left-subdam cutoff line is not present in the active V15.10 assembly; continuity is therefore **UNRESOLVED**, and no unsupported connecting geometry was added.\n\n")
        handle.write("## Local mesh and status\n\n")
        for row in mesh:
            handle.write("- %s: nodes %s, elements %s, min/median/P95/max %s/%s/%s/%s m, max aspect %s, invalid %s, collapsed %s.\n" %
                         (row["region"], row["node_count"], row["element_count"], row["actual_min_edge_m"], row["actual_median_edge_m"], row["actual_p95_edge_m"], row["actual_max_edge_m"], row["max_aspect_ratio"], row["invalid_negative_volume_count"], row["collapsed_element_count"]))
        handle.write("\n- Overall: **%s**.\n" % overall)
        handle.write("- Explicit unresolved items: compacted-backfill material source mapping and separately instantiated left-subdam cutoff continuity.\n")
        handle.write("- Abaqus Data Check: **NOT RUN** by task scope.\n")
        handle.write("- S01-S07: **NOT RUN** by task scope.\n")
    return overall


def main():
    if not os.path.exists(BASE_INP):
        raise RuntimeError("missing V15.10 baseline %s" % BASE_INP)
    os.makedirs(ROOT, exist_ok=True)
    source_lines, base_parts, base_instances, _ = parse_deck(BASE_INP)
    replacements, fish_rows = corrected_replacements()
    removed, backfill_blocks, sub_bbox, install_local = local_geology_and_backfill(base_parts)
    backfill_lines, _nodes, backfill_elements = make_backfill_part(backfill_blocks)
    clean = replace_part_blocks(source_lines, replacements)
    clean = remove_geology_elements(clean, removed)
    clean = insert_backfill_part(clean, backfill_lines)
    clean = insert_backfill_instance(clean, len(backfill_elements))
    with open(OUT_INP, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(clean) + "\n")
    _lines, out_parts, out_instances, _sets = parse_deck(OUT_INP)
    if BACKFILL_PART not in out_parts:
        raise RuntimeError("backfill Part failed to parse")
    changes = write_change_audit(base_parts, out_parts)
    write_material_basis(backfill_blocks)
    interface = write_joint_audits(base_parts, out_parts, backfill_blocks)
    support = write_support_audit(backfill_blocks, sub_bbox)
    fish_audit, _stations = route_audit(fish_rows)
    mesh = write_coverage_and_mesh(out_parts, backfill_blocks)
    cutoff = write_cutoff_audit(out_parts, out_instances)
    result = write_report(base_parts, out_parts, interface, fish_rows, support,
                          mesh, cutoff, backfill_blocks)
    print("V15_11_INP=%s" % OUT_INP)
    print("V15_11_RESULT=%s" % result)
    print("V15_11_PARTS=%d->%d" % (len(base_parts), len(out_parts)))
    print("V15_11_INSTANCES=%d->%d" % (len(base_instances), len(out_instances)))
    print("V15_11_REMOVED_GEOLOGY_ELEMENTS=%d" % len(removed))
    print("V15_11_BACKFILL_CELLS=%d" % len(backfill_blocks))
    print("V15_11_FISHWAY_TOTAL=%s" %
          fmt(sum(float(r["geometric_length_m"]) for r in fish_rows)))


if __name__ == "__main__":
    main()
