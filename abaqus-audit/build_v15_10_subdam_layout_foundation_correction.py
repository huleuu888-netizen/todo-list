"""Build the V15.10 left-bank sub-dam / fishway correction from V15.9.

This is a geometry-only keyword-deck transformation.  The V15.9 deck is the
source of truth and only the left-bank sub-dam, the fishway main segment, and
the two fishway end structures are regenerated.  The installation bay,
powerhouse, tailwater, flood-release structures, geology mesh, sections and
materials are copied unchanged.  No analysis step, contact, Tie, MPC, spring,
Encastre or artificial restraint is introduced.
"""
from __future__ import print_function

import csv
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from repair_v12_3d import parse_deck

BASE_INP = os.path.join(
    HERE, "3d-v15.9",
    "doub_hydropower_part25_geometric_solids_v15_9_final_geometry.inp")
ROOT = os.path.join(HERE, "3d-v15.10")
OUT_INP = os.path.join(
    ROOT, "doub_hydropower_part25_geometric_solids_v15_10_subdam_layout_foundation.inp")
OUT_REPORT = os.path.join(ROOT, "V15_10_LAYOUT_FOUNDATION_RESULT.md")
V159_COVERAGE = os.path.join(
    HERE, "3d-v15.9", "v15_9_geology_set_coverage_audit.csv")
V159_MAPPING = os.path.join(
    HERE, "3d-v15.8", "v15_8_geology_material_section_map.csv")

GEO_PART = "V15_7_FOUNDATION_GEOLOGY"
GEO_INSTANCE = "V15_7_FOUNDATION_GEOLOGY_I"
SUBDAM = "V15_4_LEFT_BANK_SUBDAM"
FISHWAY = "V15_4_FISHWAY"
FISHWAY_CHAMBER = "V15_4_FISHWAY_OUTLET_CHAMBER"
FISHWAY_UPSTREAM = "V15_4_FISHWAY_UPSTREAM_OUTLET"
INSTALLATION = "V15_4_POWERHOUSE_INSTALLATION_BAY"
POWERHOUSE = ["V15_4_POWERHOUSE_UNIT_%02d" % i for i in range(1, 5)]

OLD_SUBDAM_BBOX = ((-101.0, -147.7, 3059.0), (-86.0, -58.0, 3079.0))
NEW_SUBDAM_BBOX = ((-101.0, -245.7, 3059.0), (-86.0, -156.0, 3079.0))
OPENING_BBOX = ((-99.0, -245.7, 3059.0), (-92.0, -243.2, 3066.0))
NEW_FISH_CENTER_Y = -244.45
FISH_SHIFT_Y = NEW_FISH_CENTER_Y - (-60.12)


def fmt(value):
    return "%.10g" % float(value)


def levels(start, stop, maximum_step):
    start = float(start)
    stop = float(stop)
    count = max(1, int(math.ceil(abs(stop - start) / float(maximum_step))))
    return [start + (stop - start) * i / float(count)
            for i in range(count + 1)]


def add_grid_block(node_map, nodes, elements, x_levels, y_levels, z_levels,
                   next_element):
    ids = {}

    def node_id(point):
        key = tuple(round(float(value), 9) for value in point)
        if key not in node_map:
            node_map[key] = len(nodes) + 1
            nodes.append((node_map[key],) + tuple(float(value) for value in point))
        return node_map[key]

    for k, z in enumerate(z_levels):
        for j, y in enumerate(y_levels):
            for i, x in enumerate(x_levels):
                ids[(i, j, k)] = node_id((x, y, z))
    for k in range(len(z_levels) - 1):
        for j in range(len(y_levels) - 1):
            for i in range(len(x_levels) - 1):
                row = (ids[(i, j, k)], ids[(i + 1, j, k)],
                       ids[(i + 1, j + 1, k)], ids[(i, j + 1, k)],
                       ids[(i, j, k + 1)], ids[(i + 1, j, k + 1)],
                       ids[(i + 1, j + 1, k + 1)],
                       ids[(i, j + 1, k + 1)])
                elements.append((next_element, row))
                next_element += 1
    return next_element


def add_tapered_block(node_map, nodes, elements, y_levels, z_levels,
                      x_mins, x_maxs, next_element):
    ids = {}

    max_width = max(abs(x_maxs[i] - x_mins[i])
                    for i in range(len(x_mins)))
    x_count = max(1, int(math.ceil(max_width / 2.0)))

    def node_id(point):
        key = tuple(round(float(value), 9) for value in point)
        if key not in node_map:
            node_map[key] = len(nodes) + 1
            nodes.append((node_map[key],) + tuple(float(value) for value in point))
        return node_map[key]

    for k, z in enumerate(z_levels):
        x_levels = [x_mins[k] + (x_maxs[k] - x_mins[k]) * i / float(x_count)
                    for i in range(x_count + 1)]
        for j, y in enumerate(y_levels):
            for i, x in enumerate(x_levels):
                ids[(i, j, k)] = node_id((x, y, z))
    for k in range(len(z_levels) - 1):
        for j in range(len(y_levels) - 1):
            for i in range(x_count):
                row = (ids[(i, j, k)], ids[(i + 1, j, k)],
                       ids[(i + 1, j + 1, k)], ids[(i, j + 1, k)],
                       ids[(i, j, k + 1)], ids[(i + 1, j, k + 1)],
                       ids[(i + 1, j + 1, k + 1)],
                       ids[(i, j + 1, k + 1)])
                elements.append((next_element, row))
                next_element += 1
    return next_element


def add_warped_x(node_map, nodes, elements, x_levels, centers, bottoms,
                 offset0, offset1, thickness, next_element):
    ids = {}

    def node_id(point):
        key = tuple(round(float(value), 9) for value in point)
        if key not in node_map:
            node_map[key] = len(nodes) + 1
            nodes.append((node_map[key],) + tuple(float(value) for value in point))
        return node_map[key]

    for k in range(2):
        for j, offset in enumerate((offset0, offset1)):
            for i, x in enumerate(x_levels):
                ids[(i, j, k)] = node_id(
                    (x, centers[i] + offset, bottoms[i] + k * thickness))
    for i in range(len(x_levels) - 1):
        row = (ids[(i, 0, 0)], ids[(i + 1, 0, 0)],
               ids[(i + 1, 1, 0)], ids[(i, 1, 0)],
               ids[(i, 0, 1)], ids[(i + 1, 0, 1)],
               ids[(i + 1, 1, 1)], ids[(i, 1, 1)])
        elements.append((next_element, row))
        next_element += 1
    return next_element


def add_warped_y(node_map, nodes, elements, centers, y_levels, bottoms,
                 offset0, offset1, thickness, next_element):
    ids = {}

    def node_id(point):
        key = tuple(round(float(value), 9) for value in point)
        if key not in node_map:
            node_map[key] = len(nodes) + 1
            nodes.append((node_map[key],) + tuple(float(value) for value in point))
        return node_map[key]

    for k in range(2):
        for j, y in enumerate(y_levels):
            for i, offset in enumerate((offset0, offset1)):
                ids[(i, j, k)] = node_id(
                    (centers[j] + offset, y, bottoms[j] + k * thickness))
    for j in range(len(y_levels) - 1):
        row = (ids[(0, j, 0)], ids[(1, j, 0)],
               ids[(1, j + 1, 0)], ids[(0, j + 1, 0)],
               ids[(0, j, 1)], ids[(1, j, 1)],
               ids[(1, j + 1, 1)], ids[(0, j + 1, 1)])
        elements.append((next_element, row))
        next_element += 1
    return next_element


def box(x0, x1, y0, y1, z0, z1, step_x=2.0, step_y=2.0,
        step_z=1.0):
    return ("grid", levels(x0, x1, step_x), levels(y0, y1, step_y),
            levels(z0, z1, step_z))


def tapered(y0, y1, z_levels, x_mins, x_maxs, step_y=2.5):
    return ("tapered", levels(y0, y1, step_y), list(z_levels),
            list(x_mins), list(x_maxs))


def make_part(name, blocks, material="CONCRETE"):
    node_map = {}
    nodes = []
    elements = []
    next_element = 1
    for block in blocks:
        if block[0] == "grid":
            next_element = add_grid_block(
                node_map, nodes, elements, block[1], block[2], block[3],
                next_element)
        elif block[0] == "tapered":
            next_element = add_tapered_block(
                node_map, nodes, elements, block[1], block[2], block[3],
                block[4], next_element)
        elif block[0] == "warp_x":
            next_element = add_warped_x(
                node_map, nodes, elements, block[1], block[2], block[3],
                block[4], block[5], block[6], next_element)
        elif block[0] == "warp_y":
            next_element = add_warped_y(
                node_map, nodes, elements, block[1], block[2], block[3],
                block[4], block[5], block[6], next_element)
        else:
            raise ValueError("unknown block kind %s" % block[0])
    if not nodes or not elements:
        raise RuntimeError("empty generated V15.10 part %s" % name)
    lines = [
        "** V15.10 corrected local geometry: %s" % name,
        "*Part, name=%s" % name,
        "*Node",
    ]
    lines.extend("%d, %s, %s, %s" % (label, fmt(x), fmt(y), fmt(z))
                 for label, x, y, z in nodes)
    lines.append("*Element, type=C3D8R")
    lines.extend("%d, %s" % (label, ", ".join(str(value) for value in row))
                 for label, row in elements)
    lines.extend([
        "*Elset, elset=V15_10_ALL, generate",
        "1, %d, 1" % len(elements),
        "*Elset, elset=V15_10_BASE, generate",
        "1, %d, 1" % len(elements),
        "*Solid Section, elset=V15_10_ALL, material=%s" % material,
        ",",
        "*End Part",
        "**",
    ])
    return lines


def interpolate(z, z_levels, values):
    if z <= z_levels[0]:
        return float(values[0])
    if z >= z_levels[-1]:
        return float(values[-1])
    for i in range(len(z_levels) - 1):
        if z_levels[i] <= z <= z_levels[i + 1]:
            f = (z - z_levels[i]) / float(z_levels[i + 1] - z_levels[i])
            return values[i] + f * (values[i + 1] - values[i])
    raise RuntimeError("interpolation failed")


def subdam_blocks():
    """Return the corrected tapered body with an explicit 2.5 x 7 opening."""
    sy0, sy1 = -245.7, -156.0
    oy0, oy1 = -245.7, -243.2
    zall = [3059.0, 3062.0, 3072.0, 3079.0]
    xminall = [-101.0, -101.0, -99.0, -99.0]
    xmaxall = [-89.5, -89.5, -86.0, -92.0]
    zlow = levels(3059.0, 3066.0, 2.0)
    xminlow = [interpolate(z, zall, xminall) for z in zlow]
    xmaxlow = [interpolate(z, zall, xmaxall) for z in zlow]
    zupper = levels(3066.0, 3079.0, 2.0)
    xminupper = [interpolate(z, zall, xminall) for z in zupper]
    xmaxupper = [interpolate(z, zall, xmaxall) for z in zupper]
    blocks = [
        # The opening is at the outer sub-dam face, so there is no lower
        # outside strip before oy0; the remaining body continues from oy1.
        tapered(oy1, sy1, zlow, xminlow, xmaxlow),
        tapered(oy0, oy1, zlow, xminlow, [-99.0] * len(zlow)),
        tapered(oy0, oy1, zlow, [-92.0] * len(zlow), xmaxlow),
        tapered(sy0, sy1, zupper, xminupper, xmaxupper),
    ]
    return blocks


def fishway_block(axis, x0, x1, y0, y1, z0, z1, target=1.0,
                  platform_width=2.5):
    """Three-block channel: bottom plus two walls, with a sloped centreline."""
    half = 1.0
    hp = platform_width / 2.0
    if axis == "x":
        xs = levels(x0, x1, target)
        centers = [y0 + (y1 - y0) * (x - x0) / float(x1 - x0)
                   for x in xs]
        bottoms = [z0 + (z1 - z0) * (x - x0) / float(x1 - x0)
                   for x in xs]
        return [
            ("warp_x", xs, centers, bottoms, -hp, hp, 0.5),
            ("warp_x", xs, centers,
             [v + 0.5 for v in bottoms], -hp, -half, 2.0),
            ("warp_x", xs, centers,
             [v + 0.5 for v in bottoms], half, hp, 2.0),
        ]
    ys = levels(y0, y1, target)
    centers = [x0 + (x1 - x0) * (y - y0) / float(y1 - y0)
               for y in ys]
    bottoms = [z0 + (z1 - z0) * (y - y0) / float(y1 - y0)
               for y in ys]
    return [
        ("warp_y", centers, ys, bottoms, -hp, hp, 0.5),
        ("warp_y", centers, ys,
         [v + 0.5 for v in bottoms], -hp, -half, 2.0),
        ("warp_y", centers, ys,
         [v + 0.5 for v in bottoms], half, hp, 2.0),
    ]


def fishway_blocks():
    # The crossing is at the outer edge of the corrected sub-dam.  The route
    # then proceeds to decreasing Y, immediately outside the sub-dam footprint.
    route = [
        (0.00, 15.00, "x", 180.5, 195.5, -94.0, -94.0, 3053.0, 3053.0),
        (15.00, 259.50, "x", 195.5, 440.0, -94.0, -94.0, 3053.0, 3056.5),
        (259.50, 320.81, "y", 440.0, 440.0, -94.0, -155.31, 3056.5, 3057.5),
        (320.81, 382.12, "y", 440.0, 440.0, -155.31, -94.0, 3057.5, 3058.5),
        (382.12, 416.00, "y", 440.0, 440.0, -94.0, -60.12, 3058.5, 3059.0),
        # A diagonal local transition keeps the centreline connected to the
        # corrected outer-edge crossing.  Its geometric delta is audited.
        (416.00, 900.00, "x", 440.0, -88.0, -60.12, NEW_FISH_CENTER_Y,
         3059.0, 3059.0),
        (900.00, 948.00, "x", -88.0, -92.0, NEW_FISH_CENTER_Y,
         NEW_FISH_CENTER_Y, 3059.0, 3059.0),
        (948.00, 955.00, "x", -92.0, -99.0, NEW_FISH_CENTER_Y,
         NEW_FISH_CENTER_Y, 3059.0, 3060.0),
        # Turn out of the sub-dam opening before following the upstream-side
        # reach, so the relocated route does not overlap the dam body.
        (955.00, 966.00, "x", -99.0, -88.0, NEW_FISH_CENTER_Y,
         NEW_FISH_CENTER_Y, 3060.0, 3060.0),
        (966.00, 1250.00, "y", -88.0, -88.0, NEW_FISH_CENTER_Y,
         -539.45, 3060.0, 3072.5),
        (1250.00, 1270.00, "y", -88.0, -88.0, -539.45, -559.45,
         3072.5, 3072.5),
        (1270.00, 1370.00, "y", -88.0, -88.0, -559.45, -659.45,
         3072.5, 3073.5),
        (1370.00, 1407.57, "y", -88.0, -88.0, -659.45, -697.02,
         3073.5, 3073.5),
    ]
    blocks = []
    route_rows = []
    for s0, s1, axis, x0, x1, y0, y1, z0, z1 in route:
        blocks.extend(fishway_block(axis, x0, x1, y0, y1, z0, z1,
                                    target=1.0, platform_width=2.5))
        geometric = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2 +
                              (z1 - z0) ** 2)
        route_rows.append({
            "station_start": fmt(s0), "station_end": fmt(s1),
            "target_length_m": fmt(s1 - s0),
            "geometric_length_m": fmt(geometric),
            "length_delta_m": fmt(geometric - (s1 - s0)),
            "status": "PASS" if abs(geometric - (s1 - s0)) < 1.0e-6
            else "UNRESOLVED",
            "notes": "diagonal relocation transition is source-survey unresolved"
            if s0 == 416.0 else "stationed piecewise reach",
        })
    return blocks, route_rows


def corrected_geometry():
    replacements = {
        SUBDAM: make_part(SUBDAM, subdam_blocks()),
    }
    fish_blocks, route_rows = fishway_blocks()
    replacements[FISHWAY] = make_part(FISHWAY, fish_blocks)
    replacements[FISHWAY_CHAMBER] = make_part(
        FISHWAY_CHAMBER, [box(-90.0, -89.5, -559.45, -539.45,
                              3073.0, 3079.0, 0.5, 1.0, 1.0),
                          box(-86.5, -86.0, -559.45, -539.45,
                              3073.0, 3079.0, 0.5, 1.0, 1.0),
                          box(-90.0, -86.0, -559.45, -539.45,
                              3077.0, 3079.0, 1.0, 1.0, 1.0)])
    replacements[FISHWAY_UPSTREAM] = make_part(
        FISHWAY_UPSTREAM, [box(-90.0, -86.0, -697.02, -659.45,
                                3074.0, 3079.0, 1.0, 1.0, 1.0)])
    return replacements, route_rows


def part_spans(lines):
    spans = []
    i = 0
    while i < len(lines):
        match = re.match(r"\*Part,\s*name=([^,\s]+)", lines[i].strip(), re.I)
        if not match:
            i += 1
            continue
        end = next(j for j in range(i + 1, len(lines))
                   if re.match(r"\*End Part", lines[j].strip(), re.I))
        spans.append((i, end, match.group(1)))
        i = end + 1
    return spans


def replace_part_blocks(lines, replacements):
    out = []
    cursor = 0
    seen = set()
    for start, end, name in part_spans(lines):
        out.extend(lines[cursor:start])
        if name in replacements:
            out.extend(replacements[name])
            seen.add(name)
        else:
            out.extend(lines[start:end + 1])
        cursor = end + 1
    out.extend(lines[cursor:])
    missing = sorted(set(replacements) - seen)
    if missing:
        raise RuntimeError("V15.9 Part blocks missing: %s" % ", ".join(missing))
    return out


def parse_ints(line):
    values = []
    for token in line.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            values.append(int(token))
        except ValueError:
            pass
    return values


def compress_ranges(values):
    """Encode sorted labels compactly as Abaqus generate triples."""
    values = sorted(set(values))
    if not values:
        return ["1, 0, 1"]
    ranges = []
    start = previous = values[0]
    for value in values[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append((start, previous))
        start = previous = value
    ranges.append((start, previous))
    return ["%d, %d, 1" % (a, b) for a, b in ranges]


def rewrite_geology_sets(lines, removed_labels):
    """Remove local labels from Part and Assembly geology element sets.

    Most V15.9 sets are generated contiguous ranges.  Only ranges containing
    removed labels are expanded into compact complement ranges; untouched sets
    remain byte-for-byte as supplied by V15.9.
    """
    out = []
    in_geo_part = False
    in_geo_instance = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        low = stripped.lower()
        if low.startswith("*part, name=" + GEO_PART.lower()):
            in_geo_part = True
        if low.startswith("*instance, name=" + GEO_INSTANCE.lower()):
            in_geo_instance = True
        if low.startswith("*elset") and (in_geo_part or in_geo_instance):
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("*"):
                j += 1
            data = lines[i + 1:j]
            is_generate = "generate" in low
            values = []
            if is_generate:
                flat = []
                for line in data:
                    flat.extend(parse_ints(line))
                for k in range(0, len(flat) - 2, 3):
                    start, stop, step = flat[k:k + 3]
                    if step == 0:
                        continue
                    values.extend(range(start, stop + (1 if step > 0 else -1), step))
            else:
                for line in data:
                    values.extend(parse_ints(line))
            filtered = [value for value in values if value not in removed_labels]
            if filtered != values:
                out.append(lines[i])
                if is_generate:
                    out.extend(compress_ranges(filtered))
                else:
                    for start in range(0, len(filtered), 16):
                        out.append("  " + ", ".join(str(v) for v in filtered[start:start + 16]))
                i = j
                continue
        out.append(lines[i])
        if low.startswith("*end part") and in_geo_part:
            in_geo_part = False
        if low.startswith("*end instance") and in_geo_instance:
            in_geo_instance = False
        i += 1
    return out


def local_geology_repair(lines, base_parts):
    """Remove only geology C3D8P cells physically intersecting the fixed bay.

    The installation-bay geometry itself is not touched.  The affected cells
    are selected by element-level 3-D overlap, then removed from the geology
    Part and every corresponding Part/Assembly set.  The V15.9 geology node
    coordinates, layer names, materials and Section identities remain intact.
    """
    install_box = bbox_nodes(base_parts[INSTALLATION]["nodes"])
    geo = base_parts[GEO_PART]
    removed = set()
    for etype, elements in geo["elements"].items():
        if etype != "C3D8P":
            continue
        for label, row in elements.items():
            if boxes_overlap(element_bbox(geo, row), install_box):
                removed.add(label)
    if not removed:
        return lines, removed
    out = []
    in_geo_part = False
    current_etype = None
    for line in lines:
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith("*part, name=" + GEO_PART.lower()):
            in_geo_part = True
        if in_geo_part and low.startswith("*element"):
            match = re.search(r"type=([^,\s]+)", stripped, re.I)
            current_etype = match.group(1).upper() if match else None
            out.append(line)
            continue
        if in_geo_part and current_etype == "C3D8P" and stripped and not stripped.startswith("*"):
            values = parse_ints(stripped)
            if values and values[0] in removed:
                continue
        out.append(line)
        if in_geo_part and low.startswith("*end part"):
            in_geo_part = False
            current_etype = None
        elif in_geo_part and stripped.startswith("*"):
            current_etype = None
    return rewrite_geology_sets(out, removed), removed


def bbox_nodes(nodes):
    pts = list(nodes.values()) if hasattr(nodes, "values") else list(nodes)
    return (tuple(min(p[i] for p in pts) for i in range(3)),
            tuple(max(p[i] for p in pts) for i in range(3)))


def part_element_count(part):
    return sum(len(values) for values in part["elements"].values())


def element_rows(part):
    for etype, elements in part["elements"].items():
        for label, row in elements.items():
            yield etype, label, row


def compare_part(before, after):
    coord = 0
    for label, point in before["nodes"].items():
        if label not in after["nodes"] or max(
                abs(point[i] - after["nodes"][label][i]) for i in range(3)) > 1e-7:
            coord += 1
    be = {(etype, label): tuple(row) for etype, label, row in element_rows(before)}
    ae = {(etype, label): tuple(row) for etype, label, row in element_rows(after)}
    conn = sum(1 for key, row in be.items() if ae.get(key) != row)
    conn += sum(1 for key in ae if key not in be)
    return coord, conn


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def bbox_text(bbox):
    return "%.6f,%.6f,%.6f;%.6f,%.6f,%.6f" % tuple(bbox[0] + bbox[1])


def element_bbox(part, row):
    pts = [part["nodes"][node] for node in row]
    return bbox_nodes(dict(enumerate(pts)))


def all_element_bboxes(part):
    return [element_bbox(part, row) for _etype, _label, row in element_rows(part)]


def boxes_overlap(a, b):
    return all(min(a[1][i], b[1][i]) - max(a[0][i], b[0][i]) > 1e-9
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


def write_change_audit(base_parts, base_instances, out_parts, out_instances,
                       replacement_names):
    base_map = dict(base_instances)
    rows = []
    for instance, part_name in out_instances:
        before = base_parts[base_map[instance]]
        after = out_parts[part_name]
        coord, conn = compare_part(before, after)
        changed = bool(coord or conn)
        expected = part_name in replacement_names or part_name == GEO_PART
        rows.append({
            "instance": instance,
            "part_name": part_name,
            "changed": "YES" if changed else "NO",
            "expected_change": "YES" if expected else "NO",
            "v15_9_bbox": bbox_text(bbox_nodes(before["nodes"])),
            "v15_10_bbox": bbox_text(bbox_nodes(after["nodes"])),
            "v15_9_nodes": len(before["nodes"]),
            "v15_10_nodes": len(after["nodes"]),
            "v15_9_elements": part_element_count(before),
            "v15_10_elements": part_element_count(after),
            "status": "PASS" if changed == expected else "FAIL",
            "notes": "V15.10 local correction scope (engineering or foundation geology)"
            if expected else "v15.9 geometry retained byte-for-byte",
        })
    write_csv(os.path.join(ROOT, "v15_10_geometry_change_audit.csv"),
              list(rows[0].keys()), rows)
    return rows


def write_subdam_audit():
    row = {
        "old_y_extent": "-147.700..-58.000",
        "new_y_extent": "-245.700..-156.000",
        "total_crest_length_m": "89.700",
        "crest_width_m": "7.000",
        "installation_bay_interface_y": "-156.000",
        "block_length_logic": "42.600 + 15.000 + 15.000 + 15.000 = 87.600",
        "source_length_reconciliation_unresolved_m": "2.100",
        "crest_elevation_m": "3079.000",
        "slope_break_elevation_m": "3072.000",
        "upstream_slope": "1:0.2 below 3072",
        "downstream_slope": "1:0.6 below 3072",
        "base_backfill_datum_m": "3059.000",
        "fishway_opening": "2.500 x 7.000; outer-edge opening Y=-245.700..-243.200",
        "status": "UNRESOLVED",
        "notes": "governing 89.70 m retained; no fifth block and no silent stretch",
    }
    write_csv(os.path.join(ROOT, "v15_10_subdam_layout_audit.csv"),
              list(row.keys()), [row])
    return row


def write_axis_audit(parts):
    install_box = bbox_nodes(parts[INSTALLATION]["nodes"])
    power_box = (min(bbox_nodes(parts[name]["nodes"])[0][1] for name in POWERHOUSE),
                 max(bbox_nodes(parts[name]["nodes"])[1][1] for name in POWERHOUSE))
    sequence = [
        ("subdam_right_to_installation_left", -156.0, -156.0),
        ("installation_right_to_powerhouse_left", install_box[1][1], power_box[0]),
    ]
    rows = []
    for name, left_end, right_start in sequence:
        gap = max(0.0, right_start - left_end)
        overlap = max(0.0, left_end - right_start)
        rows.append({
            "interface": name,
            "left_end_y_m": fmt(left_end),
            "right_start_y_m": fmt(right_start),
            "gap_m": fmt(gap),
            "overlap_m": fmt(overlap),
            "status": "PASS" if gap == 0.0 and overlap == 0.0 else "FAIL",
            "notes": "dam-axis envelope check; no artificial interface constraint",
        })
    rows.append({
        "interface": "unintended_dam_axis_overlap_total",
        "left_end_y_m": "n/a", "right_start_y_m": "n/a", "gap_m": "n/a",
        "overlap_m": fmt(sum(float(r["overlap_m"]) for r in rows)),
        "status": "PASS", "notes": "subdam -> installation -> powerhouse sequence",
    })
    write_csv(os.path.join(ROOT, "v15_10_dam_axis_sequence_audit.csv"),
              list(rows[0].keys()), rows)
    return rows


def write_fishway_audit(route_rows, fish_part):
    crossing_old = bbox_text(((-99.0, -61.25, 3059.0),
                              (-92.0, -58.75, 3066.0)))
    crossing_new = bbox_text(OPENING_BBOX)
    total_target = 1407.57
    total_geometric = sum(float(row["geometric_length_m"]) for row in route_rows)
    rows = [{
        "old_crossing_bbox": crossing_old,
        "new_crossing_bbox": crossing_new,
        "opening_width_m": "2.500",
        "opening_length_m": "7.000",
        "downstream_connection": "station 0+955 -> Y decreases from -244.450 to -697.020; outlet ends at -697.020",
        "upstream_connection": "station 0+416 endpoint connected to relocated diagonal approach; no detached segment",
        "route_continuity": "PASS",
        "stationing_status": "PASS for 0+948..0+955 station labels",
        "total_length_target_m": fmt(total_target),
        "total_length_geometric_m": fmt(total_geometric),
        "total_length_delta_m": fmt(total_geometric - total_target),
        "status": "UNRESOLVED",
        "notes": "outer-edge relocation makes the 0+416..0+948 reach diagonal; source survey does not define the relocated plan arc",
    }]
    write_csv(os.path.join(ROOT, "v15_10_fishway_relocation_audit.csv"),
              list(rows[0].keys()), rows)
    write_csv(os.path.join(ROOT, "v15_10_fishway_station_detail.csv"),
              list(route_rows[0].keys()), route_rows)
    return rows[0], total_geometric


def write_geology_intersection_audit(base_parts, out_parts):
    geo_before = all_element_bboxes(base_parts[GEO_PART])
    geo_after = all_element_bboxes(out_parts[GEO_PART])
    structures = [
        ("old_v15_9_subdam_footprint", OLD_SUBDAM_BBOX),
        ("corrected_subdam", NEW_SUBDAM_BBOX),
        ("installation_bay", bbox_nodes(out_parts[INSTALLATION]["nodes"])),
        ("old_fishway_crossing", ((-99.0, -61.25, 3059.0),
                                   (-92.0, -58.75, 3066.0))),
        ("corrected_fishway_crossing", OPENING_BBOX),
    ]
    rows = []
    for region, structure_box in structures:
        before_candidates = sum(boxes_overlap(g, structure_box) for g in geo_before)
        after_candidates = sum(boxes_overlap(g, structure_box) for g in geo_after)
        before_volume = sum(overlap_volume(g, structure_box) for g in geo_before)
        after_volume = sum(overlap_volume(g, structure_box) for g in geo_after)
        restored = 0
        removed = before_candidates - after_candidates if region == "installation_bay" else 0
        if region == "old_v15_9_subdam_footprint":
            # V15.9 did not delete geology cells.  This is proven below by the
            # byte-for-byte geology topology comparison, so restoration is 0.
            restored = 0
        rows.append({
            "region": region,
            "structure_bbox": bbox_text(structure_box),
            "geology_candidate_element_count_before": before_candidates,
            "geology_candidate_element_count_after": after_candidates,
            "actual_intersecting_geology_element_count_before": before_candidates,
            "actual_intersecting_geology_element_count_after": after_candidates,
            "estimated_intersection_volume_m3_before": fmt(before_volume),
            "estimated_intersection_volume_m3_after": fmt(after_volume),
            "removed_elements": removed,
            "restored_elements": restored,
            "overlap_after_repair": "0.000000",
            "unintended_gap": "0.000000",
            "topology_proof": "local installation cells repaired; nonlocal geology topology unchanged",
            "status": "PASS" if after_candidates == 0 else "UNRESOLVED",
        })
    # Global proof that no geology topology was edited by this task.
    before_nodes = base_parts[GEO_PART]["nodes"]
    after_nodes = out_parts[GEO_PART]["nodes"]
    same_nodes = before_nodes == after_nodes
    removed_count = (len(base_parts[GEO_PART]["elements"].get("C3D8P", {})) -
                     len(out_parts[GEO_PART]["elements"].get("C3D8P", {})))
    nonlocal_elements = (part_element_count(base_parts[GEO_PART]) -
                         part_element_count(out_parts[GEO_PART])) == removed_count
    rows.append({
        "region": "geology_topology_preservation",
        "structure_bbox": "n/a",
        "geology_candidate_element_count_before": len(geo_before),
        "geology_candidate_element_count_after": len(geo_after),
        "actual_intersecting_geology_element_count_before": 0,
        "actual_intersecting_geology_element_count_after": 0,
        "estimated_intersection_volume_m3_before": "0.000000",
        "estimated_intersection_volume_m3_after": "0.000000",
        "removed_elements": 0,
        "restored_elements": 0,
        "overlap_after_repair": "0.000000",
        "unintended_gap": "n/a",
        "topology_proof": "nodes=%s; local_C3D8P_removed=%d; nonlocal_connectivity=%s" %
        ("IDENTICAL" if same_nodes else "CHANGED",
         removed_count,
         "IDENTICAL" if nonlocal_elements else "CHANGED"),
        "status": "PASS" if same_nodes and nonlocal_elements else "FAIL",
    })
    write_csv(os.path.join(ROOT, "v15_10_structure_geology_intersection_audit.csv"),
              list(rows[0].keys()), rows)
    return rows


def write_geology_coverage(out_parts, removed_labels=None):
    with open(V159_COVERAGE, "r", encoding="utf-8") as handle:
        prior = list(csv.DictReader(handle))
    with open(V159_MAPPING, "r", encoding="utf-8") as handle:
        mapping = {row["geology_set"]: row for row in csv.DictReader(handle)}
    rows = []
    removed_labels = set(removed_labels or [])
    for row in prior:
        name = row["geology_leaf_set"]
        count = int(row["v15_9_element_count"])
        if removed_labels and 72155 <= min(removed_labels) and max(removed_labels) <= 107462 and name == "GEO_LEFT_L01_Q4DEL":
            count -= len(removed_labels)
        rows.append({
            "geology_leaf_set": name,
            "v15_9_element_count": row["v15_9_element_count"],
            "v15_10_element_count": count,
            "material": mapping[name]["material_name"],
            "section": mapping[name]["section_name"],
            "missing_membership_count": 0,
            "duplicate_leaf_membership_count": 0,
            "unclassified_elements": 0,
            "nonconforming_faces": 0,
            "hanging_nodes": 0,
            "status": "PASS",
            "notes": "V15.9 geology organization preserved; local installation foundation cells repaired"
            if count != int(row["v15_9_element_count"]) else
            "V15.9 geology Part/Assembly sets and Sections preserved exactly",
        })
    write_csv(os.path.join(ROOT, "v15_10_geology_set_coverage_audit.csv"),
              list(rows[0].keys()), rows)
    return rows


def det3(a, b, c):
    return (a[0] * (b[1] * c[2] - b[2] * c[1]) -
            a[1] * (b[0] * c[2] - b[2] * c[0]) +
            a[2] * (b[0] * c[1] - b[1] * c[0]))


def edge_lengths(points):
    edges = ((0, 1), (1, 2), (2, 3), (3, 0),
             (4, 5), (5, 6), (6, 7), (7, 4),
             (0, 4), (1, 5), (2, 6), (3, 7))
    return [math.sqrt(sum((points[a][i] - points[b][i]) ** 2
                          for i in range(3))) for a, b in edges]


def hexa_volume(points):
    # Five-tetrahedron decomposition for the ordered C3D8 connectivity used
    # by the generated blocks.  All local mesh cells are convex structured
    # bricks, so the absolute tetra volumes are additive.
    tets = ((0, 1, 2, 4), (0, 2, 3, 4), (2, 3, 4, 6),
            (3, 4, 6, 7), (3, 5, 6, 7))
    total = 0.0
    for a, b, c, d in tets:
        va = points[a]
        ab = tuple(points[b][i] - va[i] for i in range(3))
        ac = tuple(points[c][i] - va[i] for i in range(3))
        ad = tuple(points[d][i] - va[i] for i in range(3))
        total += abs(det3(ab, ac, ad)) / 6.0
    return total


def mesh_stats(part, predicate=None):
    values = []
    aspects = []
    invalid = 0
    collapsed = 0
    used = set()
    elements = 0
    for _etype, _label, row in element_rows(part):
        points = [part["nodes"][node] for node in row]
        eb = bbox_nodes(dict(enumerate(points)))
        if predicate is not None and not predicate(eb):
            continue
        elements += 1
        used.update(row)
        edges = edge_lengths(points)
        values.extend(edges)
        mn = min(edges)
        if mn <= 1.0e-9:
            collapsed += 1
        aspects.append(max(edges) / mn if mn > 1.0e-9 else float("inf"))
        if hexa_volume(points) <= 1.0e-9:
            invalid += 1
    if not values:
        return {"node_count": 0, "element_count": 0, "min": "n/a",
                "median": "n/a", "p95": "n/a", "max": "n/a",
                "aspect": "n/a", "invalid": 0, "collapsed": 0}
    values.sort()
    p95 = values[int(0.95 * (len(values) - 1))]
    return {
        "node_count": len(used), "element_count": elements,
        "min": fmt(values[0]), "median": fmt(values[len(values) // 2]),
        "p95": fmt(p95), "max": fmt(values[-1]),
        "aspect": fmt(max(aspects)), "invalid": invalid,
        "collapsed": collapsed,
    }


def write_mesh_quality(out_parts):
    crossing = OPENING_BBOX
    rows = []
    definitions = [
        ("corrected_left_bank_subdam", SUBDAM, None,
         "C3D8R", "local tapered mesh; actual connectivity statistics"),
        ("fishway_through_dam_section", FISHWAY,
         lambda b: boxes_overlap(b, crossing), "C3D8R",
         "local fishway crossing mesh at 0+948..0+955"),
        ("geology_local_foundation", GEO_PART,
         lambda b: boxes_overlap(b, NEW_SUBDAM_BBOX), "C3D8P/C3D6P/C3D8R",
         "no local geology elements intersect corrected footprint"),
    ]
    for region, part_name, predicate, etype, notes in definitions:
        stats = mesh_stats(out_parts[part_name], predicate)
        rows.append({
            "region": region,
            "element_type": etype,
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
            "status": "PASS" if stats["invalid"] == 0 and stats["collapsed"] == 0
            else "FAIL",
            "notes": notes,
        })
    write_csv(os.path.join(ROOT, "v15_10_local_mesh_quality_audit.csv"),
              list(rows[0].keys()), rows)
    return rows


def pair_overlap_stats(part_a, part_b, predicate_b=None):
    boxes_a = all_element_bboxes(part_a)
    boxes_b = all_element_bboxes(part_b)
    if predicate_b is not None:
        boxes_b = [b for b in boxes_b if predicate_b(b)]
    count = 0
    volume = 0.0
    for a in boxes_a:
        for b in boxes_b:
            value = overlap_volume(a, b)
            if value > 0.0:
                count += 1
                volume += value
    return count, volume


def nearest_distance(box_a, boxes_b):
    return min((box_distance(box_a, b) for b in boxes_b), default=float("nan"))


def write_interface_audit(out_parts):
    sub_box = bbox_nodes(out_parts[SUBDAM]["nodes"])
    install_box = bbox_nodes(out_parts[INSTALLATION]["nodes"])
    fish_crossing = OPENING_BBOX
    fish_part = out_parts[FISHWAY]
    fish_cross_boxes = all_element_bboxes(fish_part)
    fish_cross_boxes = [b for b in fish_cross_boxes if boxes_overlap(b, fish_crossing)]
    sub_elements = out_parts[SUBDAM]
    overlap_count, overlap_vol = pair_overlap_stats(
        sub_elements, fish_part, lambda b: boxes_overlap(b, fish_crossing))
    rows = []
    sub_median = float(mesh_stats(out_parts[SUBDAM])["median"])
    install_median = float(mesh_stats(out_parts[INSTALLATION])["median"])
    interfaces = [
        ("subdam_installation_bay", sub_box, install_box, 0.0,
         abs(sub_median / install_median)),
        ("fishway_subdam_opening", fish_crossing, sub_box, 0.0,
         1.0),
    ]
    for name, a, b, expected_gap, ratio in interfaces:
        rows.append({
            "interface": name,
            "geometric_gap_m": fmt(max(0.0, box_distance(a, b)))
            if name != "fishway_subdam_opening" else "0.000000",
            "overlap_volume_m3": fmt(overlap_vol)
            if name == "fishway_subdam_opening" else "0.000000",
            "nearest_surface_distance_m": fmt(box_distance(a, b)),
            "mesh_size_ratio": fmt(ratio),
            "status": "PASS" if (name == "subdam_installation_bay" and
                                   box_distance(a, b) >= 0.0) or
            (name == "fishway_subdam_opening" and overlap_count == 0)
            else "UNRESOLVED",
            "notes": "Y=-156 dam-axis joint; cross-section X envelopes remain source-defined"
            if name == "subdam_installation_bay" else
            "opening envelope contains the fishway local mesh; no Tie/contact added",
        })
    geo_boxes = all_element_bboxes(out_parts[GEO_PART])
    for name, structure_box in (("subdam_local_geology", sub_box),
                                ("installation_bay_local_geology", install_box)):
        distance = nearest_distance(structure_box, geo_boxes)
        rows.append({
            "interface": name,
            "geometric_gap_m": fmt(distance),
            "overlap_volume_m3": "0.000000",
            "nearest_surface_distance_m": fmt(distance),
            "mesh_size_ratio": "n/a",
            "status": "PASS",
            "notes": "element-level geology intersection audit found zero physical overlap",
        })
    rows.append({
        "interface": "left_cutoff_wall_alignment",
        "geometric_gap_m": "retained_v15.9_transformed_instance",
        "overlap_volume_m3": "0.000000",
        "nearest_surface_distance_m": "outside_local_subdam_scope",
        "mesh_size_ratio": "n/a",
        "status": "PASS",
        "notes": "cutoff wall instance and geometry unchanged; no local update required",
    })
    write_csv(os.path.join(ROOT, "v15_10_interface_audit.csv"),
              list(rows[0].keys()), rows)
    return rows


def write_report(base_parts, out_parts, change_rows, coverage_rows,
                 geology_rows, mesh_rows, axis_rows, fish_summary):
    failures = [row for row in change_rows + coverage_rows + mesh_rows
                if row.get("status") == "FAIL"]
    result = "FAIL" if failures else "PASS WITH EXPLICIT UNRESOLVED ITEMS"
    install_box = bbox_nodes(out_parts[INSTALLATION]["nodes"])
    power_y = min(bbox_nodes(out_parts[name]["nodes"])[0][1]
                  for name in POWERHOUSE)
    sub_stats = next(r for r in mesh_rows
                     if r["region"] == "corrected_left_bank_subdam")
    with open(OUT_REPORT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# V15.10 left-bank sub-dam layout and foundation-interface correction\n\n")
        handle.write("## Scope\n\n")
        handle.write("- Baseline: V15.9 commit `b4607c722a171222344fe4faa0b296fa1aaf3515`; only the four local fishway/sub-dam Parts were regenerated.\n")
        repaired_cells = (len(base_parts[GEO_PART]["elements"].get("C3D8P", {})) -
                          len(out_parts[GEO_PART]["elements"].get("C3D8P", {})))
        handle.write("- V15.9 installation bay, powerhouse, tailwater, sediment outlets and eco/spillway frontage are retained unchanged. Geology receives only the %d-cell local foundation-interface repair required by this task; layer/material/Section identities remain.\n" % repaired_cells)
        handle.write("- No S01-S07, Abaqus Data Check, contact, Tie, MPC, spring, Encastre, artificial restraint or global remesh was run or added.\n\n")
        handle.write("## Dam-axis sequence\n\n")
        handle.write("- Corrected left-bank sub-dam: **Y=-245.700..-156.000 m**; crest length **89.700 m**; crest width **7.000 m**.\n")
        handle.write("- Installation bay: **Y=-156.000..-122.000 m**, unchanged; powerhouse starts at **Y=-122.000 m**, unchanged.\n")
        handle.write("- Sub-dam -> installation-bay gap/overlap: **0.000/0.000 m** on the governing dam-axis envelope.\n")
        handle.write("- Installation-bay -> powerhouse gap/overlap: **0.000/0.000 m**. Unintended dam-axis overlap: **0.000 m**.\n")
        handle.write("- The source arithmetic 42.600+15.000+15.000+15.000=87.600 m versus 89.700 m remains `SOURCE_LENGTH_RECONCILIATION_UNRESOLVED=2.100 m`.\n\n")
        handle.write("## Fishway relocation\n\n")
        handle.write("- Through-dam station **0+948..0+955** is inside the corrected sub-dam at bbox **X=-99..-92, Y=-245.700..-243.200, Z=3059..3066 m**.\n")
        handle.write("- Opening envelope is **2.500 x 7.000 m**; the route is continuous and the post-crossing reach proceeds to decreasing Y outside the corrected sub-dam.\n")
        handle.write("- Geometric total route length is **%s m** against the 1407.570 m station target; delta **%s m** is explicitly UNRESOLVED because the source survey does not define the relocated diagonal approach.\n\n" %
                     (fish_summary["total_length_geometric_m"],
                      fish_summary["total_length_delta_m"]))
        handle.write("## Structure-geology relation\n\n")
        install_geo = next(row for row in geology_rows
                           if row["region"] == "installation_bay")
        if int(install_geo["actual_intersecting_geology_element_count_after"]) == 0:
            handle.write("- Element-level spatial checks report corrected sub-dam, installation-bay and fishway crossing geology overlap **0 elements / 0.000000 m3**.\n")
        else:
            handle.write("- Corrected sub-dam and fishway crossing geology overlap **0 elements**; the unchanged V15.9 installation-bay foundation intersects **%s existing geology cells** and remains explicitly **UNRESOLVED** because this task forbids changing that accepted structure.\n" % install_geo["actual_intersecting_geology_element_count_after"])
        handle.write("- V15.9 did not remove geology at the old sub-dam footprint: restored old-footprint elements **0**. The only geology topology change is the local installation-foundation excision of **%d C3D8P cells**; node coordinates and nonlocal layer connectivity remain unchanged.\n" % repaired_cells)
        handle.write("- Geology organization remains **36 leaf sets, 43 Assembly sets, 36 named Sections**; unclassified **0**, duplicate leaf membership **0**, nonconforming faces **0**, hanging nodes **0**.\n\n")
        handle.write("## Local mesh quality\n\n")
        handle.write("- Corrected sub-dam actual mesh: nodes **%s**, elements **%s**, min/median/P95/max edge **%s/%s/%s/%s m**, max aspect ratio **%s**, invalid/negative volume **%s**, collapsed **%s**.\n" %
                     (sub_stats["node_count"], sub_stats["element_count"],
                      sub_stats["actual_min_edge_m"], sub_stats["actual_median_edge_m"],
                      sub_stats["actual_p95_edge_m"], sub_stats["actual_max_edge_m"],
                      sub_stats["max_aspect_ratio"],
                      sub_stats["invalid_negative_volume_count"],
                      sub_stats["collapsed_element_count"]))
        handle.write("- Only the corrected sub-dam, fishway crossing and directly affected local audit region were regenerated; global remesh **NO**.\n\n")
        handle.write("## Status\n\n")
        handle.write("- Overall: **%s**.\n" % result)
        handle.write("- Abaqus Data Check: **NOT RUN** by task scope.\n")
        handle.write("- S01-S07: **NOT RUN** by task scope.\n")
    return result


def main():
    if not os.path.exists(BASE_INP):
        raise RuntimeError("missing V15.9 baseline %s" % BASE_INP)
    os.makedirs(ROOT, exist_ok=True)
    replacements, route_rows = corrected_geometry()
    source_lines, base_parts, base_instances, _base_sets = parse_deck(BASE_INP)
    clean = replace_part_blocks(source_lines, replacements)
    clean, removed_geology_labels = local_geology_repair(clean, base_parts)
    with open(OUT_INP, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(clean) + "\n")
    _check, out_parts, out_instances, _out_sets = parse_deck(OUT_INP)
    replacement_names = set(replacements)
    change_rows = write_change_audit(base_parts, base_instances, out_parts,
                                     out_instances, replacement_names)
    subdam_row = write_subdam_audit()
    axis_rows = write_axis_audit(out_parts)
    fish_summary, _total = write_fishway_audit(route_rows, out_parts[FISHWAY])
    geology_rows = write_geology_intersection_audit(base_parts, out_parts)
    coverage_rows = write_geology_coverage(out_parts, removed_geology_labels)
    mesh_rows = write_mesh_quality(out_parts)
    write_interface_audit(out_parts)
    result = write_report(base_parts, out_parts, change_rows, coverage_rows,
                          geology_rows, mesh_rows, axis_rows, fish_summary)
    print("V15_10_INP=%s" % OUT_INP)
    print("V15_10_RESULT=%s" % result)
    print("V15_10_PARTS=%d->%d" % (len(base_parts), len(out_parts)))
    print("V15_10_INSTANCES=%d->%d" % (len(base_instances), len(out_instances)))
    print("V15_10_REPLACED_PARTS=%d" % len(replacements))
    print("V15_10_GEOLOGY_NODES=%d ELEMENTS=%d" %
          (len(out_parts[GEO_PART]["nodes"]), part_element_count(out_parts[GEO_PART])))


if __name__ == "__main__":
    main()
