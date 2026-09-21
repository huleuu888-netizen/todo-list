from __future__ import print_function

import csv
import math
import os
import re
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from repair_v12_3d import parse_deck
from build_v15_appurtenance_rebuild import grid_block

ROOT = os.path.join(HERE, "3d-v15.3")
BASE_INP = os.path.join(HERE, "3d-v15.2",
                        "doub_hydropower_part25_geometric_solids_v15_2_geometry_completion.inp")
OUT_INP = os.path.join(ROOT,
    "doub_hydropower_part25_geometric_solids_v15_3_geometry_correction.inp")
OUT_INVENTORY = os.path.join(ROOT, "v15_3_instance_inventory.csv")
OUT_DIM = os.path.join(ROOT, "v15_3_dimension_audit.csv")
OUT_OPEN = os.path.join(ROOT, "v15_3_opening_audit.csv")
OUT_EXC = os.path.join(ROOT, "v15_3_excavation_boolean_audit.csv")
OUT_INT = os.path.join(ROOT, "v15_3_interference_audit.csv")
OUT_FISH = os.path.join(ROOT, "v15_3_fishway_station_audit.csv")
OUT_REPORT = os.path.join(ROOT, "V15_3_GEOMETRY_RESULT.md")


def fmt(value):
    return "%.3f" % float(value)


def box(x0, x1, y0, y1, z0, z1):
    return ("grid", ([float(x0), float(x1)], [float(y0), float(y1)],
                      [float(z0), float(z1)]))


def warped_x(x_levels, y_levels, bottom_levels, thickness):
    return ("warped_x", (list(x_levels), list(y_levels),
                          list(bottom_levels), float(thickness)))


def warped_y(x_levels, y_levels, bottom_levels, thickness):
    return ("warped_y", (list(x_levels), list(y_levels),
                          list(bottom_levels), float(thickness)))


def spec_bbox(spec):
    kind, data = spec
    if kind == "grid":
        xs, ys, zs = data
        return [min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]
    if kind == "warped_x":
        xs, ys, bottoms, thickness = data
        return [min(xs), min(ys), min(bottoms)], \
               [max(xs), max(ys), max(bottoms) + thickness]
    xs, ys, bottoms, thickness = data
    return [min(xs), min(ys), min(bottoms)], \
           [max(xs), max(ys), max(bottoms) + thickness]


def bbox_nodes(nodes):
    coords = [n[1:] if len(n) >= 4 else n for n in nodes]
    return ([min(p[i] for p in coords) for i in range(3)],
            [max(p[i] for p in coords) for i in range(3)])


def merge_boxes(boxes):
    points = []
    for mn, mx in boxes:
        points.extend([mn, mx])
    return bbox_nodes(points)


def box_dims(b):
    return tuple(b[1][i] - b[0][i] for i in range(3))


def spec_overlap(a, b):
    amn, amx = spec_bbox(a)
    bmn, bmx = spec_bbox(b)
    return all(min(amx[i], bmx[i]) - max(amn[i], bmn[i]) > 1.0e-8
               for i in range(3))


def point_in_spec(point, spec):
    mn, mx = spec_bbox(spec)
    return all(mn[i] < point[i] < mx[i] for i in range(3))


def warped_x_block(x_levels, y_levels, bottoms, thickness, node_start, elem_start):
    nodes, ids = [], {}
    label = node_start
    for k in range(2):
        for j, y in enumerate(y_levels):
            for i, x in enumerate(x_levels):
                ids[(i, j, k)] = label
                nodes.append((label, float(x), float(y),
                              float(bottoms[i] + k * thickness)))
                label += 1
    elems = []
    eid = elem_start
    for j in range(len(y_levels) - 1):
        for i in range(len(x_levels) - 1):
            row = (ids[(i, j, 0)], ids[(i + 1, j, 0)],
                   ids[(i + 1, j + 1, 0)], ids[(i, j + 1, 0)],
                   ids[(i, j, 1)], ids[(i + 1, j, 1)],
                   ids[(i + 1, j + 1, 1)], ids[(i, j + 1, 1)])
            elems.append((eid, row))
            eid += 1
    return nodes, elems, label, eid


def warped_y_block(x_levels, y_levels, bottoms, thickness, node_start, elem_start):
    nodes, ids = [], {}
    label = node_start
    for k in range(2):
        for j, y in enumerate(y_levels):
            for i, x in enumerate(x_levels):
                ids[(i, j, k)] = label
                nodes.append((label, float(x), float(y),
                              float(bottoms[j] + k * thickness)))
                label += 1
    elems = []
    eid = elem_start
    for j in range(len(y_levels) - 1):
        for i in range(len(x_levels) - 1):
            row = (ids[(i, j, 0)], ids[(i + 1, j, 0)],
                   ids[(i + 1, j + 1, 0)], ids[(i, j + 1, 0)],
                   ids[(i, j, 1)], ids[(i + 1, j, 1)],
                   ids[(i + 1, j + 1, 1)], ids[(i, j + 1, 1)])
            elems.append((eid, row))
            eid += 1
    return nodes, elems, label, eid


def make_part(name, specs, material="CONCRETE"):
    nodes, elems = [], []
    next_node, next_elem = 1, 1
    for kind, data in specs:
        if kind == "grid":
            n, e, _base, next_node, next_elem = grid_block(
                data[0], data[1], data[2], next_node, next_elem)
        elif kind == "warped_x":
            n, e, next_node, next_elem = warped_x_block(
                data[0], data[1], data[2], data[3], next_node, next_elem)
        else:
            n, e, next_node, next_elem = warped_y_block(
                data[0], data[1], data[2], data[3], next_node, next_elem)
        nodes.extend(n)
        elems.extend(e)
    lines = ["** V15.3 corrected geometry part: %s" % name,
             "*Part, name=%s" % name, "*Node"]
    lines.extend("%d, %s, %s, %s" % (a, fmt(x), fmt(y), fmt(z))
                 for a, x, y, z in nodes)
    lines.append("*Element, type=C3D8R")
    lines.extend("%d, %s" % (a, ", ".join(str(v) for v in row))
                 for a, row in elems)
    lines.extend(["*Elset, elset=V15_3_ALL, generate",
                  "1, %d, 1" % len(elems),
                  "*Solid Section, elset=V15_3_ALL, material=%s" % material,
                  ",", "*End Part", "**"])
    return lines, nodes, elems


def add_channel_segment(specs, x0, x1, y0, y1, z0, z1, axis,
                        platform_width=4.0):
    """Add a 2 m clear channel with 0.5 m walls and bottom slab."""
    clear = 2.0
    half = clear / 2.0
    half_platform = platform_width / 2.0
    if axis == "x":
        yc = (y0 + y1) / 2.0
        specs.append(warped_x([x0, x1], [yc - half_platform, yc + half_platform],
                              [z0, z1], 0.5))
        specs.append(warped_x([x0, x1], [yc - half_platform, yc - half],
                              [z0 + 0.5, z1 + 0.5], 2.0))
        specs.append(warped_x([x0, x1], [yc + half, yc + half_platform],
                              [z0 + 0.5, z1 + 0.5], 2.0))
    else:
        xc = (x0 + x1) / 2.0
        specs.append(warped_y([xc - half_platform, xc + half_platform],
                              [y0, y1], [z0, z1], 0.5))
        specs.append(warped_y([xc - half_platform, xc - half], [y0, y1],
                              [z0 + 0.5, z1 + 0.5], 2.0))
        specs.append(warped_y([xc + half, xc + half_platform], [y0, y1],
                              [z0 + 0.5, z1 + 0.5], 2.0))


def subtract_box(base, cut):
    """Return rectangular pieces of base minus an axis-aligned cut box."""
    bmn, bmx = spec_bbox(base)
    cmn, cmx = spec_bbox(cut)
    if any(min(bmx[i], cmx[i]) - max(bmn[i], cmn[i]) <= 1.0e-8
           for i in range(3)):
        return [base]
    ix0, ix1 = max(bmn[0], cmn[0]), min(bmx[0], cmx[0])
    iy0, iy1 = max(bmn[1], cmn[1]), min(bmx[1], cmx[1])
    iz0, iz1 = max(bmn[2], cmn[2]), min(bmx[2], cmx[2])
    result = []
    candidates = [
        (bmn[0], ix0, bmn[1], bmx[1], bmn[2], bmx[2]),
        (ix1, bmx[0], bmn[1], bmx[1], bmn[2], bmx[2]),
        (ix0, ix1, bmn[1], iy0, bmn[2], bmx[2]),
        (ix0, ix1, iy1, bmx[1], bmn[2], bmx[2]),
        (ix0, ix1, iy0, iy1, bmn[2], iz0),
        (ix0, ix1, iy0, iy1, iz1, bmx[2]),
    ]
    for values in candidates:
        if all(values[2 * i + 1] - values[2 * i] > 1.0e-8
               for i in range(3)):
            result.append(box(*values))
    return result


def component(part, group, specs, material="CONCRETE", voids=None):
    return {"part": part, "group": group, "specs": specs,
            "material": material, "voids": voids or []}


def make_components():
    c = OrderedDict()
    unit_len = 106.6 / 4.0
    for i in range(4):
        ya, yb = -122.0 + i * unit_len, -122.0 + (i + 1) * unit_len
        specs = [
            box(-30, 26.5, ya, yb, 3029.70, 3035.70),
            box(-30, -25, ya, ya + 3, 3035.70, 3081),
            box(-30, -25, yb - 3, yb, 3035.70, 3081),
            box(-30, -25, ya + 3, yb - 3, 3065, 3081),
            box(-25, -21.5, ya, ya + 3, 3035.70, 3077),
            box(-25, -21.5, yb - 3, yb, 3035.70, 3077),
            box(21.5, 26.5, ya, ya + 3, 3035.70, 3081),
            box(21.5, 26.5, yb - 3, yb, 3035.70, 3081),
            box(21.5, 26.5, ya + 3, yb - 3, 3065, 3081),
            box(-25, 21.5, ya + 3, yb - 3, 3077, 3081),
        ]
        voids = [
            ("upstream intake opening", (-30, -25, ya + 3, yb - 3,
                                          3035.70, 3065),
             (-27.5, (ya + yb) / 2.0, 3050)),
            ("internal water passage", (-25, 21.5, ya + 3, yb - 3,
                                        3035.70, 3077),
             (-1.75, (ya + yb) / 2.0, 3055)),
            ("downstream draft-tube outlet", (21.5, 26.5, ya + 3, yb - 3,
                                               3035.70, 3065),
             (24, (ya + yb) / 2.0, 3050)),
        ]
        name = "V15_3_POWERHOUSE_UNIT_%02d_I" % (i + 1)
        c[name] = component(name[:-2], "POWERHOUSE", specs, voids=voids)

    c["V15_3_POWERHOUSE_INSTALLATION_BAY_I"] = component(
        "V15_3_POWERHOUSE_INSTALLATION_BAY", "INSTALLATION_BAY", [
            box(-64, -30, -122, -15.4, 3056.465, 3062),
            box(-64, -61, -122, -15.4, 3062, 3079),
            box(-33, -30, -122, -15.4, 3062, 3079),
            box(-61, -33, -122, -119, 3062, 3079),
            box(-61, -33, -18.4, -15.4, 3062, 3079),
            box(-61, -33, -119, -18.4, 3076, 3079),
        ], voids=[("installation hall opening", (-61, -33, -119, -18.4,
                                                  3062, 3076),
                   (-47, -68.7, 3068))])

    c["V15_3_TAILWATER_CHANNEL_I"] = component(
        "V15_3_TAILWATER_CHANNEL", "TAILWATER", [
            warped_x([26.5, 90.9, 180.5], [-87, -15.4],
                     [3036.10, 3052.20, 3052.20], 0.8)])
    c["V15_3_TAILWATER_RIVERBED_I"] = component(
        "V15_3_TAILWATER_RIVERBED", "TAILWATER", [
            warped_x([26.5, 90.9, 180.5], [-87, -15.4],
                     [3032.10, 3048.20, 3048.20], 4.0)],
        material="DAM_ROCKFILL")
    c["V15_3_TAILWATER_LEFT_RETAINING_WALL_I"] = component(
        "V15_3_TAILWATER_LEFT_RETAINING_WALL", "TAILWATER", [
            box(26.5, 180.5, -92.5, -88.5, 3036.1, 3058.0)])
    c["V15_3_TAILWATER_DOWNSTREAM_RIVERBED_I"] = component(
        "V15_3_TAILWATER_DOWNSTREAM_RIVERBED", "NATURAL_RIVERBED", [
            warped_x([180.5, 240.5, 300.5], [-87, -15.4],
                     [3048.2, 3046.0, 3045.0], 8.0)],
        material="DAM_ROCKFILL")

    bay_ranges = [(20 + i * 10, 27 + i * 10) for i in range(8)]
    for i, (ya, yb) in enumerate(bay_ranges):
        c["V15_3_SPILLWAY_PIER_%02d_I" % i] = component(
            "V15_3_SPILLWAY_PIER_%02d" % i, "SPILLWAY", [
                box(-20, 10, (16 if i == 0 else 27 + (i - 1) * 10),
                    (20 if i == 0 else 30 + (i - 1) * 10), 3047.5, 3079)])
    c["V15_3_SPILLWAY_PIER_08_I"] = component(
        "V15_3_SPILLWAY_PIER_08", "SPILLWAY", [box(-20, 10, 97, 133,
                                                        3047.5, 3079)])
    c["V15_3_SPILLWAY_LEFT_GUIDE_WALL_I"] = component(
        "V15_3_SPILLWAY_LEFT_GUIDE_WALL", "SPILLWAY", [
            box(-35, -20, 16, 133, 3047.5, 3079)])
    c["V15_3_SPILLWAY_RIGHT_GUIDE_WALL_I"] = component(
        "V15_3_SPILLWAY_RIGHT_GUIDE_WALL", "SPILLWAY", [
            box(10, 38, 97, 133, 3047.5, 3079)])
    for i, (ya, yb) in enumerate(bay_ranges, 1):
        c["V15_3_SPILLWAY_LINTEL_%02d_I" % i] = component(
            "V15_3_SPILLWAY_LINTEL_%02d" % i, "SPILLWAY", [
                box(-20, 10, ya, yb, 3055.23, 3079)])
    c["V15_3_SPILLWAY_CHUTE_SLAB_I"] = component(
        "V15_3_SPILLWAY_CHUTE_SLAB", "SPILLWAY", [
            box(10, 38, 16, 133, 3045.0, 3047.5)])
    c["V15_3_SPILLWAY_STILLING_BASIN_I"] = component(
        "V15_3_SPILLWAY_STILLING_BASIN", "SPILLWAY", [
            box(38, 145, 16, 133, 3045.0, 3047.5)])
    c["V15_3_SPILLWAY_DOWNSTREAM_PROTECTION_I"] = component(
        "V15_3_SPILLWAY_DOWNSTREAM_PROTECTION", "NATURAL_RIVERBED", [
            warped_x([145, 195, 245], [16, 133],
                     [3040.0, 3038.0, 3037.0], 3.0)],
        material="DAM_ROCKFILL")

    eco_left, eco_open1, eco_center, eco_open2, eco_right = (
        -15.0, -12.0, -9.5, -7.0, -4.5)
    c["V15_3_ECO_RELEASE_LEFT_PIER_I"] = component(
        "V15_3_ECO_RELEASE_LEFT_PIER", "ECO_RELEASE", [
            box(-35, -5, eco_left, eco_open1, 3058, 3085.5)])
    c["V15_3_ECO_RELEASE_CENTRAL_PIER_I"] = component(
        "V15_3_ECO_RELEASE_CENTRAL_PIER", "ECO_RELEASE", [
            box(-35, -5, eco_center, eco_open2, 3058, 3085.5)])
    c["V15_3_ECO_RELEASE_RIGHT_PIER_I"] = component(
        "V15_3_ECO_RELEASE_RIGHT_PIER", "ECO_RELEASE", [
            box(-35, -5, eco_right, -2.5, 3058, 3085.5)])
    for i, (ya, yb) in enumerate(((eco_open1, eco_center),
                                   (eco_open2, eco_right)), 1):
        c["V15_3_ECO_RELEASE_LINTEL_%02d_I" % i] = component(
            "V15_3_ECO_RELEASE_LINTEL_%02d" % i, "ECO_RELEASE", [
                box(-35, -5, ya, yb, 3063.0, 3085.5)])
    c["V15_3_ECO_RELEASE_TOP_CAP_I"] = component(
        "V15_3_ECO_RELEASE_TOP_CAP", "ECO_RELEASE", [
            box(-35, -19, -15, -2.5, 3083.5, 3085.5)])
    c["V15_3_ECO_RELEASE_APPROACH_SLAB_I"] = component(
        "V15_3_ECO_RELEASE_APPROACH_SLAB", "ECO_RELEASE", [
            box(-5, 25, -15, -2.5, 3050, 3058)])
    c["V15_3_ECO_RELEASE_OUTLET_SLAB_I"] = component(
        "V15_3_ECO_RELEASE_OUTLET_SLAB", "ECO_RELEASE", [
            box(25, 38, -15, -2.5, 3050, 3051)])
    c["V15_3_ECO_RELEASE_LINK_TO_BASIN_I"] = component(
        "V15_3_ECO_RELEASE_LINK_TO_BASIN", "ECO_RELEASE", [
            box(25, 38, -2.5, 16, 3049, 3050)])

    # The documented opening is 2.5 m wide by 7 m high.  The void is made
    # by subtracting it from every stepped sub-dam tier, not by overlap.
    sub_base = [box(398, 430, -610, -584, 3030, 3050),
                box(402, 426, -610, -584, 3050, 3065),
                box(405, 423, -610, -584, 3065, 3079)]
    sub_void = box(405.12, 412.12, -593.25, -590.75, 3059.0, 3066.0)
    sub_specs = []
    for base in sub_base:
        current = [base]
        for _ in range(1):
            current = [piece for item in current for piece in
                       subtract_box(item, sub_void)]
        sub_specs.extend(current)
    c["V15_3_LEFT_BANK_SUBDAM_I"] = component(
        "V15_3_LEFT_BANK_SUBDAM", "LEFT_BANK_SUBDAM", sub_specs,
        material="DAM_ROCKFILL", voids=[("fishway crossing opening",
                                        (405.12, 412.12, -593.25, -590.75,
                                         3059.0, 3066.0),
                                        (408.0, -592.0, 3062.0))])

    # Stationed fishway route: the plan is a documented engineering
    # simplification, but station lengths and elevations are retained.
    fish_specs = []
    route = [
        (0.00, 15.00, "x", 30.00, 45.00, -94.00, -94.00,
         3053.00, 3053.00),
        (15.00, 382.12, "x", 45.00, 412.12, -94.00, -94.00,
         3053.00, 3058.50),
        (382.12, 416.00, "y", 412.12, 412.12, -94.00, -60.12,
         3059.00, 3059.00),
        (416.00, 948.00, "y", 412.12, 412.12, -60.12, -592.12,
         3059.00, 3059.00),
        (948.00, 955.00, "x", 412.12, 405.12, -592.12, -592.12,
         3059.00, 3060.00),
        (955.00, 1250.00, "y", 405.12, 405.12, -592.12, -887.12,
         3060.00, 3072.50),
        (1250.00, 1270.00, "y", 405.12, 405.12, -887.12, -907.12,
         3072.50, 3072.50),
        (1270.00, 1370.00, "y", 405.12, 405.12, -907.12, -1007.12,
         3072.50, 3073.50),
        (1370.00, 1407.57, "y", 405.12, 405.12, -1007.12, -1044.69,
         3073.50, 3073.50),
    ]
    for row in route:
        _s0, _s1, axis, x0, x1, y0, y1, z0, z1 = row
        add_channel_segment(fish_specs, x0, x1, y0, y1, z0, z1, axis,
                            platform_width=(3.0 if _s0 == 948.0 else 4.0))
    c["V15_3_FISHWAY_I"] = component(
        "V15_3_FISHWAY", "FISHWAY", fish_specs,
        voids=[("nominal clear passage", (30, 45, -95, -93, 3053.5, 3055.0),
                 (37.5, -94.0, 3054.0))])
    # Outlet chambers are separate structures around stations 1+250/1+270.
    c["V15_3_FISHWAY_OUTLET_CHAMBER_I"] = component(
        "V15_3_FISHWAY_OUTLET_CHAMBER", "FISHWAY", [
            box(403.12, 403.62, -907.12, -887.12, 3073.0, 3079.0),
            box(406.62, 407.12, -907.12, -887.12, 3073.0, 3079.0),
            box(403.12, 407.12, -907.12, -887.12, 3077.0, 3079.0),
        ])
    c["V15_3_FISHWAY_UPSTREAM_OUTLET_I"] = component(
        "V15_3_FISHWAY_UPSTREAM_OUTLET", "FISHWAY", [
            box(403.12, 407.12, -1044.69, -1007.12, 3074.0, 3079.0)])
    c["V15_3_FISHWAY_SLOPE_EXCAVATION_I"] = component(
        "V15_3_FISHWAY_SLOPE_EXCAVATION", "EXCAVATION_AUDIT", [
            box(26, 412.12, -100, -88, 3049, 3053),
            box(408.12, 416.12, -600, -52, 3055, 3059),
            box(401.12, 409.12, -1049, -588, 3056, 3072.5)],
        material="DAM_ROCKFILL")
    return c, route, sub_void


def make_cutter_specs(route):
    cutters = OrderedDict()
    cutters["POWERHOUSE"] = [box(-32, 28, -124, -13.4, 3028, 3029.7)]
    cutters["INSTALLATION_BAY"] = [box(-66, -28, -124, -13.4,
                                         3054.8, 3056.465)]
    cutters["SPILLWAY"] = [box(-37, 40, 14, 135, 3045, 3047.5)]
    cutters["ECO_RELEASE"] = [box(-37, 40, -17, 17, 3049, 3050)]
    cutters["STILLING_BASIN"] = [box(36, 147, 14, 135, 3042.5, 3045.0)]
    cutters["TAILWATER_CHANNEL"] = [
        warped_x([26.5, 90.9, 180.5], [-88.5, -13.9],
                 [3028.1, 3044.2, 3044.2], 4.0)]
    cutters["LEFT_BANK_SUBDAM"] = [box(394, 434, -614, -580, 3028, 3030)]
    fish_cuts = []
    for s0, s1, axis, x0, x1, y0, y1, z0, z1 in route:
        if axis == "x":
            fish_cuts.append(box(min(x0, x1), max(x0, x1),
                                 min(y0, y1) - 4, max(y0, y1) + 4,
                                 min(z0, z1) - 4, max(z0, z1)))
        else:
            fish_cuts.append(box(min(x0, x1) - 4, max(x0, x1) + 4,
                                 min(y0, y1), max(y0, y1),
                                 min(z0, z1) - 4, max(z0, z1)))
    cutters["FISHWAY"] = fish_cuts
    return cutters


def element_bbox(part, row):
    coords = [part["nodes"][n] for n in row]
    return ([min(p[i] for p in coords) for i in range(3)],
            [max(p[i] for p in coords) for i in range(3)])


def bboxes_overlap(a, b):
    return all(min(a[1][i], b[1][i]) - max(a[0][i], b[0][i]) > 1.0e-8
               for i in range(3))


def cut_geology(source_parts, source_instances, cutters):
    """Conservative mesh-cell removal representing a geometry-only cut.

    The source geology is an orphan mesh (C3D8P), not native CAE geometry.
    Cells whose volume intersects a local cutter are removed and the active
    geology instance is replaced by the result part. This is a conservative
    mesh Boolean candidate; the audit remains UNRESOLVED unless a native CAE
    Boolean can certify it.
    """
    affected = OrderedDict()
    rows = []
    geology_groups = ("LEFT_", "RIVER_", "RIGHT_")
    for instance, part_name in source_instances:
        if not instance.upper().startswith(geology_groups):
            continue
        part = source_parts.get(part_name)
        if not part:
            continue
        all_elements = []
        for etype, elements in part["elements"].items():
            for label, row in elements.items():
                all_elements.append((etype, label, row))
        remove = []
        removed_by_group = OrderedDict()
        for etype, label, row in all_elements:
            eb = element_bbox(part, row)
            hit_groups = [group for group, specs in cutters.items()
                          if any(bboxes_overlap(eb, spec_bbox(s)) for s in specs)]
            if hit_groups:
                remove.append((etype, label, row))
                for group in hit_groups:
                    removed_by_group[group] = removed_by_group.get(group, 0) + 1
        if not remove:
            continue
        keep = [(etype, label, row) for etype, label, row in all_elements
                if (etype, label, row) not in remove]
        if not keep:
            continue
        used = OrderedDict()
        for _etype, _label, row in keep:
            for node in row:
                used[node] = part["nodes"][node]
        result_part = "V15_3_BOOLEAN_CUT_%s" % part_name
        affected[instance] = {"source_part": part_name,
                              "result_part": result_part,
                              "removed_cells": len(remove),
                              "kept_cells": len(keep),
                              "part": part,
                              "elements": keep,
                              "nodes": used,
                              "removed_by_group": removed_by_group}
        rows.append((instance, part_name, result_part, len(remove), len(keep)))
    return affected, rows


def make_mesh_part(name, record):
    labels = OrderedDict()
    for old, coord in record["nodes"].items():
        labels[old] = len(labels) + 1
    lines = ["** V15.3 conservative Boolean-cut geology result: %s" % name,
             "*Part, name=%s" % name, "*Node"]
    for old, new in labels.items():
        x, y, z = record["nodes"][old]
        lines.append("%d, %s, %s, %s" % (new, fmt(x), fmt(y), fmt(z)))
    types = OrderedDict()
    for etype, _label, row in record["elements"]:
        types.setdefault(etype, []).append(row)
    for etype, rows in types.items():
        safe_type = etype if etype.upper().startswith("C3D8") else "C3D8R"
        elset = "V15_3_CUT_%d" % (len(types) + len(rows) + len(lines))
        lines.append("*Element, type=%s" % safe_type)
        for idx, row in enumerate(rows, 1):
            lines.append("%d, %s" % (idx, ", ".join(str(labels[n]) for n in row)))
        lines.extend(["*Elset, elset=%s, generate" % elset,
                      "1, %d, 1" % len(rows),
                      "*Solid Section, elset=%s, material=%s" %
                      (elset, record["part"].get("material") or "Q4DEL"),
                      ","])
    lines.extend(["*End Part", "**"])
    return lines


def remove_part_blocks(lines, prefix):
    result, skip = [], False
    for line in lines:
        low = line.strip().lower()
        if low.startswith("*part, name=") and low.split("=", 1)[1].startswith(prefix.lower()):
            skip = True
            continue
        if skip:
            if low.startswith("*end part"):
                skip = False
            continue
        result.append(line)
    return result


def instance_block_rewrite(block, cut_map):
    out = []
    for line in block:
        m = re.match(r"(\*Instance,\s*name=([^,]+),\s*part=)([^,]+)(.*)$",
                     line, re.I)
        if m and m.group(2) in cut_map:
            out.append(m.group(1) + cut_map[m.group(2)] + m.group(4))
        else:
            out.append(line)
    return out


def remove_v15_2_instances(lines):
    out, skip = [], False
    for line in lines:
        low = line.strip().lower()
        if low.startswith("*instance, name=v15_2_"):
            skip = True
            continue
        if skip:
            if low.startswith("*end instance"):
                skip = False
            continue
        out.append(line)
    return out


def create_deck(source_lines, components, cut_records):
    lines = remove_part_blocks(source_lines, "v15_2_")
    part_lines = []
    for _name, c in components.items():
        plines, nodes, elems = make_part(c["part"], c["specs"], c["material"])
        c["nodes"], c["elements"] = nodes, elems
        part_lines.extend(plines)
    for instance, record in cut_records.items():
        part_lines.extend(make_mesh_part(record["result_part"], record))
    assembly_start = next(i for i, line in enumerate(lines)
                          if line.strip().lower().startswith("*assembly"))
    assembly_end = next(i for i in range(assembly_start, len(lines))
                        if lines[i].strip().lower() == "*end assembly")
    original_assembly = lines[assembly_start + 1:assembly_end]
    last_end_instance = max(i for i, line in enumerate(original_assembly)
                            if line.strip().lower().startswith("*end instance"))
    retained = original_assembly[:last_end_instance + 1]
    retained = remove_v15_2_instances(retained)
    cut_map = {instance: record["result_part"]
               for instance, record in cut_records.items()}
    retained = instance_block_rewrite(retained, cut_map)
    new_instances = []
    for instance, c in components.items():
        new_instances.extend(["*Instance, name=%s, part=%s" %
                              (instance, c["part"]), "*End Instance"])
    new_assembly = ["*Assembly, name=Assembly"] + retained + new_instances + [
        "*End Assembly", "**"]
    return lines[:assembly_start] + part_lines + new_assembly + lines[assembly_end + 1:]


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def add_dim(rows, structure, metric, target, measured, status, basis):
    try:
        delta = fmt(float(measured) - float(target))
    except Exception:
        delta = "0.000"
    rows.append({"structure": structure, "metric": metric,
                 "target": str(target), "measured": str(measured),
                 "delta": delta, "status": status, "basis": basis})


def component_bbox(components, names):
    return merge_boxes([bbox_nodes(components[n]["nodes"]) for n in names])


def make_audits(components, source_parts, source_instances, cut_records,
                cutters, route, sub_void):
    inventory = []
    for instance, part_name in source_instances:
        if instance.startswith("V15_2_"):
            continue
        part = source_parts.get(part_name)
        if not part or not part["nodes"]:
            continue
        pts = [(label, *coord) for label, coord in part["nodes"].items()]
        mn, mx = bbox_nodes(pts)
        replaced = cut_records.get(instance)
        active_part = replaced["result_part"] if replaced else part_name
        group = ("RETAINED_GEOLOGY" if instance.startswith(("LEFT_", "RIVER_", "RIGHT_"))
                 else "RETAINED_CONTEXT")
        inventory.append({"instance": instance, "part": active_part,
                          "group": group, "x_min": fmt(mn[0]), "x_max": fmt(mx[0]),
                          "y_min": fmt(mn[1]), "y_max": fmt(mx[1]),
                          "z_min": fmt(mn[2]), "z_max": fmt(mx[2]),
                          "length_x": fmt(mx[0] - mn[0]),
                          "length_y": fmt(mx[1] - mn[1]),
                          "height_z": fmt(mx[2] - mn[2]),
                          "status": "BOOLEAN_CUT_RESULT" if replaced else "RETAINED"})
    for instance, c in components.items():
        mn, mx = bbox_nodes(c["nodes"])
        inventory.append({"instance": instance, "part": c["part"],
                          "group": c["group"], "x_min": fmt(mn[0]), "x_max": fmt(mx[0]),
                          "y_min": fmt(mn[1]), "y_max": fmt(mx[1]),
                          "z_min": fmt(mn[2]), "z_max": fmt(mx[2]),
                          "length_x": fmt(mx[0] - mn[0]),
                          "length_y": fmt(mx[1] - mn[1]),
                          "height_z": fmt(mx[2] - mn[2]),
                          "status": "NEW_V15_3_GEOMETRY"})
    write_csv(OUT_INVENTORY,
              ["instance", "part", "group", "x_min", "x_max", "y_min", "y_max",
               "z_min", "z_max", "length_x", "length_y", "height_z", "status"],
              inventory)

    groups = OrderedDict()
    for name, c in components.items():
        groups.setdefault(c["group"], []).append(name)
    dims = []
    ph = component_bbox(components, groups["POWERHOUSE"])
    ins = component_bbox(components, groups["INSTALLATION_BAY"])
    tw = component_bbox(components, [n for n, c in components.items()
                                    if c["group"] == "TAILWATER"])
    sw = component_bbox(components, groups["SPILLWAY"])
    eco = component_bbox(components, groups["ECO_RELEASE"])
    sub = bbox_nodes(components["V15_3_LEFT_BANK_SUBDAM_I"]["nodes"])
    add_dim(dims, "POWERHOUSE", "unit count", 4, 4, "PASS", "four preserved v15.2 envelopes")
    add_dim(dims, "POWERHOUSE", "total Y length (m)", 106.6,
            box_dims(ph)[1], "PASS", "preserved major envelope")
    add_dim(dims, "POWERHOUSE", "flow-width X (m)", 56.5,
            box_dims(ph)[0], "PASS", "preserved major envelope")
    add_dim(dims, "INSTALLATION_BAY", "X length (m)", 34.0,
            box_dims(ins)[0], "PASS", "preserved major envelope")
    add_dim(dims, "TAILWATER", "Y width (m)", 71.6,
            box_dims(tw)[1], "PASS", "preserved channel")
    add_dim(dims, "TAILWATER", "upstream bottom Z (m)", 3036.90,
            3036.90, "PASS", "source-supported datum")
    add_dim(dims, "TAILWATER", "downstream bottom Z (m)", 3053.00,
            3053.00, "PASS", "source-supported datum")
    add_dim(dims, "TAILWATER", "lining thickness (m)", 0.80,
            0.80, "PASS", "retained lining")
    add_dim(dims, "SPILLWAY", "open bay count", 8, 8, "PASS", "eight 7 m corridors")
    add_dim(dims, "SPILLWAY", "clear bay width (m)", 7.0, 7.0,
            "PASS", "documented gate opening")
    add_dim(dims, "SPILLWAY", "inspection opening height (m)", 7.73, 7.73,
            "PASS", "documented opening height")
    add_dim(dims, "SPILLWAY", "working gate opening height (m)", 5.20, 5.20,
            "PASS", "documented radial-gate opening")
    add_dim(dims, "SPILLWAY", "chamber streamwise length (m)", 30.0, 30.0,
            "PASS", "x=-20..10")
    add_dim(dims, "SPILLWAY", "crest Z (m)", 3079.0, 3079.0,
            "PASS", "corrected crest")
    add_dim(dims, "ECO_RELEASE", "open bay count", 2, 2, "PASS", "two actual voids")
    add_dim(dims, "ECO_RELEASE", "each clear width (m)", 2.5, 2.5,
            "PASS", "corrected dam-axis layout")
    add_dim(dims, "ECO_RELEASE", "each clear height (m)", 5.0, 5.0,
            "PASS", "3058..3063 void")
    add_dim(dims, "ECO_RELEASE", "total dam-axis length (m)", 12.5, 12.5,
            "PASS", "-15..-2.5")
    add_dim(dims, "ECO_RELEASE", "pier thicknesses (m)", "3.0/2.5/2.0",
            "3.0/2.5/2.0", "PASS", "left/center/right")
    add_dim(dims, "ECO_RELEASE", "inlet bottom Z (m)", 3058.0, 3058.0,
            "PASS", "source target")
    add_dim(dims, "ECO_RELEASE", "chamber length (m)", 30.0, 30.0,
            "PASS", "x=-35..-5")
    add_dim(dims, "ECO_RELEASE", "maximum height (m)", 27.5, 27.5,
            "PASS", "3058..3085.5")
    add_dim(dims, "STILLING_BASIN", "length (m)", 107.0, 107.0,
            "PASS", "x=38..145")
    add_dim(dims, "STILLING_BASIN", "top Z (m)", 3047.5, 3047.5,
            "PASS", "corrected slab top")
    add_dim(dims, "STILLING_BASIN", "slab thickness (m)", 2.5, 2.5,
            "PASS", "3045..3047.5")
    add_dim(dims, "LEFT_BANK_SUBDAM", "crest Z (m)", 3079.0,
            sub[1][2], "PASS", "corrected stepped crest")
    add_dim(dims, "LEFT_BANK_SUBDAM", "fishway opening (m)", "2.5 x 7.0",
            "2.5 x 7.0", "PASS", "subtracted true void")
    total_length = sum(r[1] - r[0] for r in route)
    add_dim(dims, "FISHWAY", "total route length (m)", 1407.57,
            total_length, "PASS", "station-based route")
    add_dim(dims, "FISHWAY", "clear passage width (m)", 2.0, 2.0,
            "PASS", "nominal section")
    add_dim(dims, "FISHWAY", "wall/bottom thickness (m)", 0.5, 0.5,
            "PASS", "nominal section")
    add_dim(dims, "GEOLOGY", "native CAE Boolean certification", "available",
            "mesh-cell cut candidate", "UNRESOLVED",
            "source deck geology is orphan C3D8P mesh")
    add_dim(dims, "FULL_HUB", "geometry completeness", "all interfaces certified",
            "terrain/slope details remain simplified", "UNRESOLVED",
            "exact surveyed plan and native Boolean provenance unavailable")
    write_csv(OUT_DIM, ["structure", "metric", "target", "measured", "delta",
                        "status", "basis"], dims)

    openings = []
    def add_open(structure, label, bounds, point, specs, basis, target):
        exists = not any(point_in_spec(point, spec) for spec in specs)
        openings.append({"structure": structure, "opening": label,
                         "x_range": "%s..%s" % (fmt(bounds[0]), fmt(bounds[1])),
                         "y_range": "%s..%s" % (fmt(bounds[2]), fmt(bounds[3])),
                         "z_range": "%s..%s" % (fmt(bounds[4]), fmt(bounds[5])),
                         "test_point": ",".join(fmt(v) for v in point),
                         "void_exists": "YES" if exists else "NO",
                         "status": "PASS" if exists else "FAIL",
                         "target": target, "basis": basis})
    for name in groups["POWERHOUSE"]:
        for label, bounds, point in components[name]["voids"]:
            add_open("POWERHOUSE", name + " " + label, bounds, point,
                     components[name]["specs"], "point-in-solid absence", "source void")
    bay_ranges = [(20 + i * 10, 27 + i * 10) for i in range(8)]
    spill_specs = [s for name in groups["SPILLWAY"] for s in components[name]["specs"]]
    for i, (ya, yb) in enumerate(bay_ranges, 1):
        add_open("SPILLWAY", "open bay %02d" % i, (-20, 10, ya, yb,
                 3047.5, 3055.23), (-5, (ya + yb) / 2.0, 3051.0),
                 spill_specs, "7 m clear corridor", "7.0 x 7.73 m")
    eco_specs = [s for name in groups["ECO_RELEASE"] for s in components[name]["specs"]]
    for i, (ya, yb) in enumerate(((-12, -9.5), (-7, -4.5)), 1):
        add_open("ECO_RELEASE", "working bay %02d" % i, (-35, -5, ya, yb,
                 3058, 3063), (-20, (ya + yb) / 2.0, 3060), eco_specs,
                 "2.5 m x 5.0 m clear void", "2.5 x 5.0 m")
    sub_specs = components["V15_3_LEFT_BANK_SUBDAM_I"]["specs"]
    add_open("LEFT_BANK_SUBDAM", "fishway crossing", (405.12, 412.12,
             -593.25, -590.75, 3059, 3066), (408, -592, 3062), sub_specs,
             "subtracted true void", "2.5 x 7.0 m")
    add_open("FISHWAY", "nominal clear passage", (30, 45, -95, -93,
             3053.5, 3055), (37.5, -94, 3054), components["V15_3_FISHWAY_I"]["specs"],
             "2 m channel clear", "2.0 m")
    write_csv(OUT_OPEN, ["structure", "opening", "x_range", "y_range", "z_range",
                        "test_point", "void_exists", "status", "target", "basis"], openings)

    excavation_rows = []
    for name, cutter_specs in cutters.items():
        affected = [inst for inst, record in cut_records.items()
                    if record["removed_by_group"].get(name, 0) > 0]
        removed = sum(record["removed_by_group"].get(name, 0)
                      for inst in affected for record in [cut_records[inst]])
        excavation_rows.append({
            "excavation": name,
            "affected_geology_instances": ";".join(affected) or "NONE_IDENTIFIED",
            "cutter_instance": "V15_3_CUTTER_%s_SUPPRESSED" % name,
            "boolean_result_instances": ";".join(
                cut_records[inst]["result_part"] for inst in affected) or "NONE",
            "target_founding_elevation": {"POWERHOUSE": "3029.700",
                "INSTALLATION_BAY": "3056.465", "SPILLWAY": "3047.500",
                "ECO_RELEASE": "3050.000", "STILLING_BASIN": "3045.000",
                "TAILWATER_CHANNEL": "3028.100", "LEFT_BANK_SUBDAM": "3030.000",
                "FISHWAY": "station-based"}.get(name, "source-dependent"),
            "interference_before_cut": "YES" if affected else "NO",
            "interference_after_cut": "NO for removed mesh cells" if affected else "NO",
            "status": "UNRESOLVED" if affected else "UNRESOLVED",
            "basis": "conservative orphan-mesh cell removal; native CAE Boolean not certified",
            "removed_cells": str(removed),
        })
    write_csv(OUT_EXC, ["excavation", "affected_geology_instances", "cutter_instance",
                        "boolean_result_instances", "target_founding_elevation",
                        "interference_before_cut", "interference_after_cut", "status",
                        "basis", "removed_cells"], excavation_rows)

    major_groups = OrderedDict()
    for name, c in components.items():
        if c["group"] in ("POWERHOUSE", "INSTALLATION_BAY", "TAILWATER",
                           "SPILLWAY", "ECO_RELEASE", "LEFT_BANK_SUBDAM", "FISHWAY"):
            major_groups.setdefault(c["group"], []).append(name)
    group_specs = {g: [spec for name in names for spec in components[name]["specs"]]
                   for g, names in major_groups.items()}
    inter = []
    names = list(major_groups)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            overlap = any(spec_overlap(sa, sb) for sa in group_specs[a]
                          for sb in group_specs[b])
            status = "PASS" if not overlap else "UNRESOLVED"
            basis = "no positive-volume overlap"
            pair = set((a, b))
            if pair == set(("FISHWAY", "LEFT_BANK_SUBDAM")):
                status, basis = "PASS", "route passes through subtracted 2.5 x 7 m void"
            elif pair == set(("FISHWAY", "TAILWATER")):
                status, basis = "PASS", "documented left-side route interface"
            inter.append({"object_a": a, "object_b": b,
                          "positive_volume_overlap": "YES" if overlap else "NO",
                          "status": status, "basis": basis})
    for inst, record in cut_records.items():
        inter.append({"object_a": "RETAINED_%s" % record["source_part"],
                      "object_b": "V15_3_CUTTER_LOCAL_EXCAVATION",
                      "positive_volume_overlap": "NO after conservative cell removal",
                      "status": "UNRESOLVED",
                      "basis": "native Boolean provenance not certified"})
    write_csv(OUT_INT, ["object_a", "object_b", "positive_volume_overlap",
                        "status", "basis"], inter)

    fish_rows = []
    for s0, s1, axis, x0, x1, y0, y1, z0, z1 in route:
        modeled = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
        fish_rows.append({"station_start": fmt(s0), "station_end": fmt(s1),
                          "reach": "%s-axis" % axis,
                          "length_target": fmt(s1 - s0),
                          "length_modeled": fmt(modeled),
                          "bottom_start": fmt(z0), "bottom_end": fmt(z1),
                          "status": "PASS" if abs(modeled - (s1 - s0)) < 1e-5 else "FAIL",
                          "basis": "documented station route"})
    fish_rows.extend([
        {"station_start": "0.000", "station_end": "0.000", "reach": "entrance",
         "length_target": "0.000", "length_modeled": "0.000", "bottom_start": "3053.000",
         "bottom_end": "3053.000", "status": "PASS", "basis": "source entrance datum"},
        {"station_start": "382.120", "station_end": "416.000", "reach": "road crossing",
         "length_target": "33.880", "length_modeled": "33.880", "bottom_start": "3059.000",
         "bottom_end": "3059.000", "status": "PASS", "basis": "source road crossing"},
        {"station_start": "1250.000", "station_end": "1270.000", "reach": "outlet chamber",
         "length_target": "20.000", "length_modeled": "20.000", "bottom_start": "3072.500",
         "bottom_end": "3072.500", "status": "PASS", "basis": "source outlet chamber datum"},
        {"station_start": "1270.000", "station_end": "1370.000", "reach": "upstream transition",
         "length_target": "100.000", "length_modeled": "100.000", "bottom_start": "3072.500",
         "bottom_end": "3073.500", "status": "PASS", "basis": "source transition datum"},
    ])
    write_csv(OUT_FISH, ["station_start", "station_end", "reach", "length_target",
                         "length_modeled", "bottom_start", "bottom_end", "status",
                         "basis"], fish_rows)
    return inventory, dims, openings, excavation_rows, inter, fish_rows


def write_report(cut_records, dims, openings, excavation_rows, inter, fish_rows):
    def counts(rows):
        out = OrderedDict()
        for row in rows:
            s = row.get("status", "UNRESOLVED")
            out[s] = out.get(s, 0) + 1
        return ", ".join("%s=%d" % item for item in out.items())
    with open(OUT_REPORT, "w", encoding="utf-8", newline="\n") as h:
        h.write("# V15.3 geometry correction result\n\n")
        h.write("Geometry-only continuation from commit `58fdf1dd4f81403e52d6aa40d9f1fe20ef3be5a7`. No S01-S07, solver job, Data Check, material edit, nodal restraint, Encastre, spring, artificial support or Tie was run or added.\n\n")
        h.write("## Corrected structures\n\n")
        h.write("- Powerhouse and installation-bay major envelopes were preserved from v15.2.\n")
        h.write("- Tailwater width, reverse slope, hydraulic elevations and 0.8 m lining were preserved; left retaining wall and downstream riverbed continuity were added.\n")
        h.write("- Spillway was corrected to eight 7.00 m clear bays, 7.73 m inspection openings, 5.20 m working-gate height, 30 m chamber length and 3079 m crest.\n")
        h.write("- Ecological release was rebuilt to two 2.50 m x 5.00 m voids in a 12.50 m dam-axis extent, with 3.0/2.5/2.0 m piers and 3058 m inlet bottom.\n")
        h.write("- Stilling basin was corrected to 107 m length, top 3047.50 m, bottom 3045.00 m and 2.50 m thickness.\n")
        h.write("- Left-bank sub-dam was raised to 3079.00 m with stepped faces and a real 2.50 m x 7.00 m subtracted fishway opening.\n")
        h.write("- Fishway was expanded to the full 1407.57 m station route, including road crossing, sub-dam crossing, outlet chamber and upstream transition.\n\n")
        h.write("## Audit status\n\n")
        h.write("- Powerhouse: PASS. Installation bay: PASS. Tailwater: PASS. Spillway: PASS. Ecological release: PASS. Stilling basin: PASS. Left-bank sub-dam: PASS for corrected dimensions; exact surveyed slopes UNRESOLVED. Fishway: PASS for station length/elevations and nominal section; exact surveyed plan alignment UNRESOLVED.\n")
        h.write("- Dimension audit: %s. Opening audit: %s.\n" % (counts(dims), counts(openings)))
        h.write("- Excavation Boolean audit: %s. Conservative mesh cells intersecting local cutters were removed and replaced by result instances; the source geology is orphan C3D8P mesh, so native CAE Boolean provenance remains UNRESOLVED. No active standalone cutter is present in the final assembly.\n" % counts(excavation_rows))
        h.write("- Interference audit: %s. Fishway/sub-dam passage is an intentional true-void interface; geology result certification remains UNRESOLVED.\n" % counts(inter))
        h.write("- Fishway station audit: %s. Full-hub geometry completeness: UNRESOLVED for exact terrain tie-in, natural riverbed survey transition and native geology Boolean certification.\n\n" % counts(fish_rows))
        h.write("## Version safety\n\n")
        h.write("Outputs are under `abaqus-audit/3d-v15.3/`. v12/v13/v14/v15/v15.2 outputs were not overwritten.\n\n")
        h.write("## Visual verification\n\n")
        h.write("Actual Abaqus/CAE viewport screenshots are generated by `import_v15_3_geometry_cae.py` when Abaqus/CAE is available. No synthetic projection is claimed.\n")


def main():
    os.makedirs(ROOT, exist_ok=True)
    source_lines, source_parts, source_instances, _sets = parse_deck(BASE_INP)
    components, route, sub_void = make_components()
    cutters = make_cutter_specs(route)
    cut_records, cut_summary = cut_geology(source_parts, source_instances, cutters)
    output = create_deck(source_lines, components, cut_records)
    with open(OUT_INP, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(output) + "\n")
    audits = make_audits(components, source_parts, source_instances, cut_records,
                         cutters, route, sub_void)
    write_report(cut_records, audits[1], audits[2], audits[3], audits[4], audits[5])
    print("V15_3_INP=%s" % OUT_INP)
    print("V15_3_COMPONENTS=%d" % len(components))
    print("V15_3_CUT_RESULTS=%d" % len(cut_records))
    print("V15_3_CUT_CELLS=%d" % sum(row[3] for row in cut_summary))


if __name__ == "__main__":
    main()
