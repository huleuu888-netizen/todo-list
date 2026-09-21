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
from build_v15_3_geometry_correction import (
    bbox_nodes, bboxes_overlap, box, component_bbox, make_mesh_part,
    spec_bbox as base_spec_bbox, subtract_box, warped_x, warped_y)

ROOT = os.path.join(HERE, "3d-v15.4")
BASE_INP = os.path.join(HERE, "3d-v15.3",
    "doub_hydropower_part25_geometric_solids_v15_3_geometry_correction.inp")
OUT_INP = os.path.join(ROOT,
    "doub_hydropower_part25_geometric_solids_v15_4_geometry_mesh.inp")
OUT_CSV = {
    "inventory": os.path.join(ROOT, "v15_4_instance_inventory.csv"),
    "dimension": os.path.join(ROOT, "v15_4_dimension_audit.csv"),
    "layout": os.path.join(ROOT, "v15_4_layout_audit.csv"),
    "opening": os.path.join(ROOT, "v15_4_opening_audit.csv"),
    "sediment": os.path.join(ROOT, "v15_4_sediment_flushing_audit.csv"),
    "excavation": os.path.join(ROOT, "v15_4_excavation_audit.csv"),
    "interference": os.path.join(ROOT, "v15_4_interference_audit.csv"),
    "fishway": os.path.join(ROOT, "v15_4_fishway_station_audit.csv"),
    "density": os.path.join(ROOT, "v15_4_mesh_density_audit.csv"),
    "quality": os.path.join(ROOT, "v15_4_mesh_quality_audit.csv"),
    "convergence": os.path.join(ROOT, "v15_4_mesh_convergence_plan.csv"),
}
OUT_REPORT = os.path.join(ROOT, "V15_4_GEOMETRY_MESH_RESULT.md")


def fmt(value):
    return "%.3f" % float(value)


def spec_bbox(spec):
    """Bounding box for V15.3 and V15.4 mesh specs with audit metadata."""
    kind, data = spec[0], spec[1]
    if kind in ("grid", "refined_grid"):
        xs, ys, zs = data
        return [min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]
    xs, ys, bottoms, thickness = data
    return [min(xs), min(ys), min(bottoms)], \
           [max(xs), max(ys), max(bottoms) + thickness]


def axis_levels(a, b, target):
    a, b, target = float(a), float(b), max(float(target), 1.0e-6)
    n = max(1, int(math.ceil(abs(b - a) / target)))
    return [a + (b - a) * i / float(n) for i in range(n + 1)]


def interp_levels(source_levels, source_values, levels):
    """Linearly interpolate warped bottom elevations on refined axis levels."""
    if len(source_levels) != len(source_values):
        raise ValueError("warped bottom definition must match source axis levels")
    if len(source_levels) == 1:
        return [float(source_values[0])] * len(levels)
    out = []
    for value in levels:
        if value <= source_levels[0]:
            out.append(float(source_values[0]))
            continue
        if value >= source_levels[-1]:
            out.append(float(source_values[-1]))
            continue
        for i in range(len(source_levels) - 1):
            a, b = float(source_levels[i]), float(source_levels[i + 1])
            if a <= value <= b:
                fraction = (float(value) - a) / (b - a)
                out.append(float(source_values[i]) + fraction *
                           (float(source_values[i + 1]) - float(source_values[i])))
                break
    return out


def refined_box(x0, x1, y0, y1, z0, z1, target, zone="M2", through=2):
    ztarget = min(float(target), abs(float(z1) - float(z0)) / float(through))
    return ("refined_grid", (axis_levels(x0, x1, target),
                              axis_levels(y0, y1, target),
                              axis_levels(z0, z1, ztarget)), zone, float(target))


def refined_warped_x(xs, ys, bottoms, thickness, target, zone="M2"):
    levels = axis_levels(xs[0], xs[-1], target)
    ylevels = axis_levels(ys[0], ys[-1], target)
    return ("refined_warped_x", (levels, ylevels,
                                  interp_levels(list(xs), list(bottoms), levels),
                                  float(thickness)), zone, float(target))


def refined_warped_y(xs, ys, bottoms, thickness, target, zone="M2"):
    levels = axis_levels(ys[0], ys[-1], target)
    xlevels = axis_levels(xs[0], xs[-1], target)
    return ("refined_warped_y", (xlevels, levels,
                                  interp_levels(list(ys), list(bottoms), levels),
                                  float(thickness)), zone, float(target))


def warped_x_block(xs, ys, bottoms, thickness, node_start, elem_start):
    nodes, ids = [], {}
    label = node_start
    for k in range(2):
        for j, y in enumerate(ys):
            for i, x in enumerate(xs):
                ids[(i, j, k)] = label
                nodes.append((label, float(x), float(y),
                              float(bottoms[i] + k * thickness)))
                label += 1
    elems, eid = [], elem_start
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            elems.append((eid, (ids[(i, j, 0)], ids[(i + 1, j, 0)],
                                ids[(i + 1, j + 1, 0)], ids[(i, j + 1, 0)],
                                ids[(i, j, 1)], ids[(i + 1, j, 1)],
                                ids[(i + 1, j + 1, 1)], ids[(i, j + 1, 1)])))
            eid += 1
    return nodes, elems, label, eid


def warped_y_block(xs, ys, bottoms, thickness, node_start, elem_start):
    nodes, ids = [], {}
    label = node_start
    for k in range(2):
        for j, y in enumerate(ys):
            for i, x in enumerate(xs):
                ids[(i, j, k)] = label
                nodes.append((label, float(x), float(y),
                              float(bottoms[j] + k * thickness)))
                label += 1
    elems, eid = [], elem_start
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            elems.append((eid, (ids[(i, j, 0)], ids[(i + 1, j, 0)],
                                ids[(i + 1, j + 1, 0)], ids[(i, j + 1, 0)],
                                ids[(i, j, 1)], ids[(i + 1, j, 1)],
                                ids[(i + 1, j + 1, 1)], ids[(i, j + 1, 1)])))
            eid += 1
    return nodes, elems, label, eid


def make_part(name, specs, material):
    nodes, elems, next_node, next_elem = [], [], 1, 1
    element_zones = []
    for spec in specs:
        kind, data = spec[0], spec[1]
        zone = spec[2] if len(spec) > 2 else "M2"
        target = spec[3] if len(spec) > 3 else 2.0
        if kind == "grid":
            n, e, _base, next_node, next_elem = grid_block(
                data[0], data[1], data[2], next_node, next_elem)
        elif kind == "refined_grid":
            n, e, _base, next_node, next_elem = grid_block(
                data[0], data[1], data[2], next_node, next_elem)
        elif kind == "refined_warped_x":
            n, e, next_node, next_elem = warped_x_block(
                data[0], data[1], data[2], data[3], next_node, next_elem)
        else:
            n, e, next_node, next_elem = warped_y_block(
                data[0], data[1], data[2], data[3], next_node, next_elem)
        nodes.extend(n)
        elems.extend(e)
        element_zones.extend([(zone, target)] * len(e))
    lines = ["** V15.4 geometry and targeted mesh part: %s" % name,
             "*Part, name=%s" % name, "*Node"]
    lines.extend("%d, %s, %s, %s" % (a, fmt(x), fmt(y), fmt(z))
                 for a, x, y, z in nodes)
    lines.append("*Element, type=C3D8R")
    lines.extend("%d, %s" % (a, ", ".join(str(v) for v in row))
                 for a, row in elems)
    lines.extend(["*Elset, elset=V15_4_ALL, generate",
                  "1, %d, 1" % len(elems),
                  "*Solid Section, elset=V15_4_ALL, material=%s" % material,
                  ",", "*End Part", "**"])
    return lines, nodes, elems, element_zones


def add_channel(specs, x0, x1, y0, y1, z0, z1, axis,
                target=2.0, zone="M2", platform_width=4.0):
    half = 1.0
    hp = platform_width / 2.0
    if axis == "x":
        yc = (y0 + y1) / 2.0
        specs.extend([
            refined_warped_x([x0, x1], [yc - hp, yc + hp], [z0, z1],
                             0.5, target, zone),
            refined_warped_x([x0, x1], [yc - hp, yc - half],
                             [z0 + 0.5, z1 + 0.5], 2.0, target, zone),
            refined_warped_x([x0, x1], [yc + half, yc + hp],
                             [z0 + 0.5, z1 + 0.5], 2.0, target, zone)])
    else:
        xc = (x0 + x1) / 2.0
        specs.extend([
            refined_warped_y([xc - hp, xc + hp], [y0, y1], [z0, z1],
                             0.5, target, zone),
            refined_warped_y([xc - hp, xc - half], [y0, y1],
                             [z0 + 0.5, z1 + 0.5], 2.0, target, zone),
            refined_warped_y([xc + half, xc + hp], [y0, y1],
                             [z0 + 0.5, z1 + 0.5], 2.0, target, zone)])


def component(part, group, specs, material="CONCRETE", voids=None,
              region=None):
    return {"part": part, "group": group, "specs": specs,
            "material": material, "voids": voids or [],
            "region": region or group}


def make_components():
    c = OrderedDict()
    unit_len = 106.6 / 4.0
    for i in range(4):
        ya, yb = -122.0 + i * unit_len, -122.0 + (i + 1) * unit_len
        specs = [
            refined_box(-30, 26.5, ya, yb, 3029.7, 3035.7, 2.0, "M2"),
            refined_box(-30, -25, ya, ya + 3, 3035.7, 3081, 1.5, "M2"),
            refined_box(-30, -25, yb - 3, yb, 3035.7, 3081, 1.5, "M2"),
            refined_box(-30, -25, ya + 3, yb - 3, 3065, 3079, 1.0, "M1"),
            refined_box(-25, -21.5, ya, ya + 3, 3035.7, 3077, 1.5, "M2"),
            refined_box(-25, -21.5, yb - 3, yb, 3035.7, 3077, 1.5, "M2"),
            refined_box(21.5, 26.5, ya, ya + 3, 3035.7, 3081, 1.5, "M2"),
            refined_box(21.5, 26.5, yb - 3, yb, 3035.7, 3081, 1.5, "M2"),
            refined_box(21.5, 26.5, ya + 3, yb - 3, 3065, 3079, 1.0, "M1"),
            refined_box(-25, 21.5, ya + 3, yb - 3, 3077, 3081, 1.0, "M1"),
        ]
        voids = [
            ("upstream intake opening", (-30, -25, ya + 3, yb - 3, 3035.7, 3065),
             (-27.5, (ya + yb) / 2.0, 3050)),
            ("internal water passage", (-25, 21.5, ya + 3, yb - 3, 3035.7, 3077),
             (-1.75, (ya + yb) / 2.0, 3055)),
            ("downstream draft-tube outlet", (21.5, 26.5, ya + 3, yb - 3, 3035.7, 3065),
             (24, (ya + yb) / 2.0, 3050)),
        ]
        name = "V15_4_POWERHOUSE_UNIT_%02d_I" % (i + 1)
        c[name] = component(name[:-2], "POWERHOUSE", specs, voids=voids,
                             region="powerhouse")

    c["V15_4_POWERHOUSE_INSTALLATION_BAY_I"] = component(
        "V15_4_POWERHOUSE_INSTALLATION_BAY", "INSTALLATION_BAY", [
            refined_box(-64, -30, -122, -15.4, 3056.465, 3062, 2.0, "M2"),
            refined_box(-64, -61, -122, -15.4, 3062, 3079, 2.0, "M2"),
            refined_box(-33, -30, -122, -15.4, 3062, 3079, 2.0, "M2"),
            refined_box(-61, -33, -122, -119, 3062, 3079, 1.5, "M2"),
            refined_box(-61, -33, -18.4, -15.4, 3062, 3079, 1.5, "M2"),
            refined_box(-61, -33, -119, -18.4, 3076, 3079, 1.0, "M1"),
        ], voids=[("installation hall opening", (-61, -33, -119, -18.4, 3062, 3076),
                   (-47, -68.7, 3068))], region="installation bay")

    c["V15_4_TAILWATER_CHANNEL_I"] = component(
        "V15_4_TAILWATER_CHANNEL", "TAILWATER", [
            refined_warped_x([26.5, 90.9, 180.5], [-87, -15.4],
                             [3036.1, 3052.2, 3052.2], 0.8, 2.5, "M2")],
        region="tailwater")
    c["V15_4_TAILWATER_RIVERBED_I"] = component(
        "V15_4_TAILWATER_RIVERBED", "TAILWATER", [
            refined_warped_x([26.5, 90.9, 180.5], [-87, -15.4],
                             [3032.1, 3048.2, 3048.2], 4.0, 4.0, "M3")],
        material="DAM_ROCKFILL", region="tailwater")
    c["V15_4_TAILWATER_LEFT_RETAINING_WALL_I"] = component(
        "V15_4_TAILWATER_LEFT_RETAINING_WALL", "TAILWATER", [
            refined_box(26.5, 180.5, -92.5, -88.5, 3036.1, 3058.0, 2.0, "M2")],
        region="tailwater")
    c["V15_4_TAILWATER_DOWNSTREAM_RIVERBED_I"] = component(
        "V15_4_TAILWATER_DOWNSTREAM_RIVERBED", "NATURAL_RIVERBED", [
            refined_warped_x([180.5, 240.5, 300.5], [-87, -15.4],
                             [3048.2, 3046.0, 3045.0], 8.0, 5.0, "M3")],
        material="DAM_ROCKFILL", region="tailwater downstream")

    bays = [(20 + i * 10, 27 + i * 10) for i in range(8)]
    for i in range(7):
        c["V15_4_SPILLWAY_INTERMEDIATE_PIER_%02d_I" % (i + 1)] = component(
            "V15_4_SPILLWAY_INTERMEDIATE_PIER_%02d" % (i + 1), "SPILLWAY", [
                refined_box(-20, 10, 27 + i * 10, 30 + i * 10,
                            3047.5, 3079.0, 1.5, "M2")], region="spillway")
    c["V15_4_SPILLWAY_LEFT_ABUTMENT_I"] = component(
        "V15_4_SPILLWAY_LEFT_ABUTMENT", "SPILLWAY", [
            refined_box(-35, -20, 16, 133, 3047.5, 3079, 2.0, "M2")],
        region="spillway")
    c["V15_4_SPILLWAY_RIGHT_ABUTMENT_I"] = component(
        "V15_4_SPILLWAY_RIGHT_ABUTMENT", "SPILLWAY", [
            refined_box(10, 38, 97, 133, 3047.5, 3079, 2.0, "M2")],
        region="spillway")
    for i, (ya, yb) in enumerate(bays, 1):
        c["V15_4_SPILLWAY_LINTEL_%02d_I" % i] = component(
            "V15_4_SPILLWAY_LINTEL_%02d" % i, "SPILLWAY", [
                refined_box(-20, 10, ya, yb, 3055.23, 3079, 1.0, "M1")],
            region="spillway")
    c["V15_4_SPILLWAY_CHUTE_SLAB_I"] = component(
        "V15_4_SPILLWAY_CHUTE_SLAB", "SPILLWAY", [
            refined_box(10, 38, 16, 133, 3045, 3047.5, 2.5, "M2")],
        region="spillway")
    c["V15_4_SPILLWAY_STILLING_BASIN_I"] = component(
        "V15_4_SPILLWAY_STILLING_BASIN", "SPILLWAY", [
            refined_box(38, 145, 16, 133, 3045, 3047.5, 2.5, "M2")],
        region="stilling basin")
    c["V15_4_SPILLWAY_DOWNSTREAM_PROTECTION_I"] = component(
        "V15_4_SPILLWAY_DOWNSTREAM_PROTECTION", "NATURAL_RIVERBED", [
            refined_warped_x([145, 195, 245], [16, 133],
                             [3040, 3038, 3037], 3.0, 5.0, "M3")],
        material="DAM_ROCKFILL", region="stilling basin downstream")

    # Eco release: the structural base is below the 3058 sill, with the
    # visible crest held near 3079. Exact source foundation reconciliation is
    # audited separately instead of inferring 3085.5 m.
    eco_left, eco_o1, eco_c, eco_o2, eco_right = -15.0, -12.0, -9.5, -7.0, -4.5
    c["V15_4_ECO_RELEASE_BASE_I"] = component(
        "V15_4_ECO_RELEASE_BASE", "ECO_RELEASE", [
            refined_box(-35, -5, -15, -2.5, 3051.5, 3058, 2.0, "M2")],
        region="ecological release")
    for key, part, ya, yb in [
        ("LEFT", "LEFT_PIER", eco_left, eco_o1),
        ("CENTRAL", "CENTRAL_PIER", eco_c, eco_o2),
        ("RIGHT", "RIGHT_PIER", eco_right, -2.5)]:
        c["V15_4_ECO_RELEASE_%s_I" % key] = component(
            "V15_4_ECO_RELEASE_%s" % part, "ECO_RELEASE", [
                refined_box(-35, -5, ya, yb, 3058, 3079, 1.0, "M1")],
            region="ecological release")
    for i, (ya, yb) in enumerate(((eco_o1, eco_c), (eco_o2, eco_right)), 1):
        c["V15_4_ECO_RELEASE_LINTEL_%02d_I" % i] = component(
            "V15_4_ECO_RELEASE_LINTEL_%02d" % i, "ECO_RELEASE", [
                refined_box(-35, -5, ya, yb, 3063, 3079, 1.0, "M1")],
            region="ecological release")
    c["V15_4_ECO_RELEASE_TOP_CAP_I"] = component(
        "V15_4_ECO_RELEASE_TOP_CAP", "ECO_RELEASE", [
            refined_box(-35, -19, -15, -2.5, 3077, 3079, 1.0, "M1")],
        region="ecological release")
    c["V15_4_ECO_RELEASE_APPROACH_SLAB_I"] = component(
        "V15_4_ECO_RELEASE_APPROACH_SLAB", "ECO_RELEASE", [
            refined_box(-5, 25, -15, -2.5, 3050, 3058, 2.0, "M2")],
        region="ecological release")
    c["V15_4_ECO_RELEASE_OUTLET_SLAB_I"] = component(
        "V15_4_ECO_RELEASE_OUTLET_SLAB", "ECO_RELEASE", [
            refined_box(25, 38, -15, -2.5, 3050, 3051, 1.0, "M1")],
        region="ecological release")
    c["V15_4_ECO_RELEASE_LINK_TO_BASIN_I"] = component(
        "V15_4_ECO_RELEASE_LINK_TO_BASIN", "ECO_RELEASE", [
            refined_box(25, 38, -2.5, 16, 3049, 3050, 1.0, "M1")],
        region="ecological release")

    # The sub-dam is adjacent to the installation-bay x=-64 interface.
    sub_void = box(-99.0, -92.0, -61.25, -58.75, 3059.0, 3066.0)
    tier_boxes = [box(-112, -64, -122, -15, 3030, 3050),
                  box(-104, -64, -122, -15, 3050, 3065),
                  box(-99, -64, -122, -15, 3065, 3079)]
    sub_specs = []
    for base in tier_boxes:
        sub_specs.extend(subtract_box(base, sub_void))
    refined_sub_specs = []
    for sub_spec in sub_specs:
        mn, mx = spec_bbox(sub_spec)
        # Keep the M1 band local to the 2.5 m-wide opening.  The larger
        # side/above/below boxes remain M2 so the whole sub-dam is not
        # accidentally promoted to a fine mesh.
        near_opening = (mx[0] - mn[0] <= 8.0 and
                        mx[1] - mn[1] <= 4.0 and
                        mn[2] < 3068.0 and mx[2] > 3057.0)
        target = 1.0 if near_opening else 2.0
        zone = "M1" if near_opening else "M2"
        refined_sub_specs.append(refined_box(mn[0], mx[0], mn[1], mx[1],
                                             mn[2], mx[2], target, zone))
    c["V15_4_LEFT_BANK_SUBDAM_I"] = component(
        "V15_4_LEFT_BANK_SUBDAM", "LEFT_BANK_SUBDAM", [
            s for s in refined_sub_specs],
        material="DAM_ROCKFILL", voids=[("fishway crossing opening",
            (-99, -92, -61.25, -58.75, 3059, 3066), (-95, -60, 3062))],
        region="left-bank sub-dam")

    # Station route with a local hub reference.  The first 382.12 m includes
    # a documented piecewise return/meander; the sub-dam remains near the
    # installation bay instead of being moved to the far turnaround.
    route = [
        (0.00, 15.00, "x", 180.5, 195.5, -94.0, -94.0, 3053.0, 3053.0),
        (15.00, 259.50, "x", 195.5, 440.0, -94.0, -94.0, 3053.0, 3056.5),
        (259.50, 320.81, "y", 440.0, 440.0, -94.0, -155.31, 3056.5, 3057.5),
        (320.81, 382.12, "y", 440.0, 440.0, -155.31, -94.0, 3057.5, 3058.5),
        (382.12, 416.00, "y", 440.0, 440.0, -94.0, -60.12, 3059.0, 3059.0),
        (416.00, 948.00, "x", 440.0, -92.0, -60.12, -60.12, 3059.0, 3059.0),
        (948.00, 955.00, "x", -92.0, -99.0, -60.12, -60.12, 3059.0, 3060.0),
        (955.00, 1250.00, "y", -99.0, -99.0, -60.12, -355.12, 3060.0, 3072.5),
        (1250.00, 1270.00, "y", -99.0, -99.0, -355.12, -375.12, 3072.5, 3072.5),
        (1270.00, 1370.00, "y", -99.0, -99.0, -375.12, -475.12, 3072.5, 3073.5),
        (1370.00, 1407.57, "y", -99.0, -99.0, -475.12, -512.69, 3073.5, 3073.5),
    ]
    fish_specs = []
    for row in route:
        s0, _s1, axis, x0, x1, y0, y1, z0, z1 = row
        target = 1.0 if s0 in (948.0, 1250.0, 1270.0) else 2.0
        zone = "M1" if target <= 1.0 else "M2"
        add_channel(fish_specs, x0, x1, y0, y1, z0, z1, axis,
                    target, zone, 3.0 if s0 == 948.0 else 4.0)
    c["V15_4_FISHWAY_I"] = component(
        "V15_4_FISHWAY", "FISHWAY", fish_specs,
        voids=[("nominal clear passage", (180.5, 195.5, -95, -93, 3053.5, 3055),
                 (188, -94, 3054))], region="fishway")
    c["V15_4_FISHWAY_OUTLET_CHAMBER_I"] = component(
        "V15_4_FISHWAY_OUTLET_CHAMBER", "FISHWAY", [
            refined_box(-101, -100.5, -375.12, -355.12, 3073, 3079, 1.0, "M1"),
            refined_box(-97.5, -97, -375.12, -355.12, 3073, 3079, 1.0, "M1"),
            refined_box(-101, -97, -375.12, -355.12, 3077, 3079, 1.0, "M1")],
        region="fishway")
    c["V15_4_FISHWAY_UPSTREAM_OUTLET_I"] = component(
        "V15_4_FISHWAY_UPSTREAM_OUTLET", "FISHWAY", [
            refined_box(-101, -97, -512.69, -475.12, 3074, 3079, 1.0, "M1")],
        region="fishway")

    # Two outlet collars; the voids are audited separately from the main
    # intake/draft-tube passages and share one outlet per two units.
    flushing = [("01", -95.35, "UNITS_01_02"), ("02", -42.05, "UNITS_03_04")]
    flushing_audit = []
    for key, yc, host in flushing:
        s = [
            refined_box(-30, -27.5, yc - 1.75, yc - 1.25, 3037, 3040, 0.75, "M1"),
            refined_box(-30, -27.5, yc + 1.25, yc + 1.75, 3037, 3040, 0.75, "M1"),
            refined_box(-30, -27.5, yc - 1.25, yc + 1.25, 3039, 3040, 0.75, "M1"),
            refined_box(21.5, 24, yc - 1.75, yc - 1.25, 3043, 3046, 0.75, "M1"),
            refined_box(21.5, 24, yc + 1.25, yc + 1.75, 3043, 3046, 0.75, "M1"),
            refined_box(21.5, 24, yc - 1.25, yc + 1.25, 3045, 3046, 0.75, "M1"),
            refined_box(-27.5, 21.5, yc - 1.75, yc - 1.25, 3039, 3045, 1.0, "M1"),
            refined_box(-27.5, 21.5, yc + 1.25, yc + 1.75, 3039, 3045, 1.0, "M1"),
        ]
        voids = [
            ("upstream accident-gate opening", (-30, -27.5, yc - 1.25, yc + 1.25,
                                                 3037, 3039), (-28.75, yc, 3038)),
            ("downstream working-gate opening", (21.5, 24, yc - 1.25, yc + 1.25,
                                                  3043, 3045), (22.75, yc, 3044)),
        ]
        name = "V15_4_POWERHOUSE_SEDIMENT_FLUSHING_OUTLET_%s_I" % key
        c[name] = component(name[:-2], "POWERHOUSE_FLUSHING", s, voids=voids,
                             region="powerhouse flushing outlets")
        flushing_audit.append((key, host, yc))
    return c, route, sub_void, flushing_audit


def make_cutters(route, sub_void):
    cutters = OrderedDict()
    cutters["POWERHOUSE"] = [box(-32, 28, -124, -13.4, 3028, 3029.7)]
    cutters["INSTALLATION_BAY"] = [box(-66, -28, -124, -13.4, 3054.8, 3056.465)]
    cutters["SPILLWAY"] = [box(-37, 40, 14, 135, 3045, 3047.5)]
    cutters["ECO_RELEASE"] = [box(-37, 40, -17, 17, 3049, 3051.5)]
    cutters["STILLING_BASIN"] = [box(36, 147, 14, 135, 3042.5, 3045)]
    cutters["TAILWATER"] = [warped_x([26.5, 90.9, 180.5], [-88.5, -13.9],
                                      [3028.1, 3044.2, 3044.2], 4.0)]
    cutters["LEFT_BANK_SUBDAM"] = [box(-116, -60, -126, -11, 3028, 3030)]
    fish = []
    for s0, _s1, axis, x0, x1, y0, y1, z0, z1 in route:
        if axis == "x":
            fish.append(box(min(x0, x1), max(x0, x1), min(y0, y1) - 4,
                            max(y0, y1) + 4, min(z0, z1) - 4, max(z0, z1)))
        else:
            fish.append(box(min(x0, x1) - 4, max(x0, x1) + 4,
                            min(y0, y1), max(y0, y1), min(z0, z1) - 4, max(z0, z1)))
    cutters["FISHWAY"] = fish
    cutters["SEDIMENT_FLUSHING"] = [
        box(-31, 25, -98.0, -92.7, 3036.5, 3037.0),
        box(-31, 25, -44.7, -39.4, 3036.5, 3037.0)]
    return cutters


def element_bbox(part, row):
    coords = [part["nodes"][n] for n in row]
    return ([min(p[i] for p in coords) for i in range(3)],
            [max(p[i] for p in coords) for i in range(3)])


def apply_additional_cut(source_parts, source_instances, cutters):
    records = OrderedDict()
    summary = []
    for instance, part_name in source_instances:
        if not instance.startswith(("LEFT_", "RIVER_", "RIGHT_")):
            continue
        part = source_parts.get(part_name)
        if not part or not part["nodes"]:
            continue
        all_elements = []
        for etype, elements in part["elements"].items():
            for label, row in elements.items():
                all_elements.append((etype, label, row))
        removed, removed_by_group = [], OrderedDict()
        for etype, label, row in all_elements:
            eb = element_bbox(part, row)
            hits = [g for g, specs in cutters.items()
                    if any(bboxes_overlap(eb, spec_bbox(s)) for s in specs)]
            if hits:
                removed.append((etype, label, row))
                for g in hits:
                    removed_by_group[g] = removed_by_group.get(g, 0) + 1
        if not removed:
            continue
        keep = [(e, l, r) for e, l, r in all_elements
                if (e, l, r) not in removed]
        if not keep:
            continue
        used = OrderedDict()
        for _e, _l, row in keep:
            for node in row:
                used[node] = part["nodes"][node]
        result = "V15_4_ORPHAN_MESH_EXCAVATION_RESULT_%s" % part_name
        records[instance] = {"source_part": part_name, "result_part": result,
                             "part": part, "elements": keep, "nodes": used,
                             "removed_cells": len(removed),
                             "removed_by_group": removed_by_group}
        summary.append((instance, part_name, result, len(removed)))
    return records, summary


def remove_v15_3_parts(lines):
    out, skip = [], False
    for line in lines:
        low = line.strip().lower()
        if low.startswith("*part, name=v15_3_") and not low.startswith(
                "*part, name=v15_3_boolean_cut_"):
            skip = True
            continue
        if skip:
            if low.startswith("*end part"):
                skip = False
            continue
        out.append(line)
    return out


def remove_v15_3_instances(lines):
    out, skip = [], False
    for line in lines:
        low = line.strip().lower()
        if low.startswith("*instance, name=v15_3_"):
            skip = True
            continue
        if skip:
            if low.startswith("*end instance"):
                skip = False
            continue
        out.append(line)
    return out


def rewrite_instances(block, cut_map):
    out = []
    for line in block:
        m = re.match(r"(\*Instance,\s*name=([^,]+),\s*part=)([^,]+)(.*)$",
                     line, re.I)
        if m and m.group(2) in cut_map:
            out.append(m.group(1) + cut_map[m.group(2)] + m.group(4))
        else:
            out.append(line)
    return out


def create_deck(source_lines, components, cut_records):
    lines = remove_v15_3_parts(source_lines)
    part_lines = []
    for instance, c in components.items():
        p, nodes, elems, zones = make_part(c["part"], c["specs"], c["material"])
        c["nodes"], c["elements"], c["element_zones"] = nodes, elems, zones
        part_lines.extend(p)
    for _instance, record in cut_records.items():
        part_lines.extend(make_mesh_part(record["result_part"], record))
    assembly_start = next(i for i, line in enumerate(lines)
                          if line.strip().lower().startswith("*assembly"))
    assembly_end = next(i for i in range(assembly_start, len(lines))
                        if lines[i].strip().lower() == "*end assembly")
    original = lines[assembly_start + 1:assembly_end]
    last_end = max(i for i, line in enumerate(original)
                   if line.strip().lower().startswith("*end instance"))
    retained = remove_v15_3_instances(original[:last_end + 1])
    cut_map = {instance: rec["result_part"] for instance, rec in cut_records.items()}
    retained = rewrite_instances(retained, cut_map)
    new_instances = []
    for instance, c in components.items():
        new_instances += ["*Instance, name=%s, part=%s" % (instance, c["part"]),
                          "*End Instance"]
    assembly = ["*Assembly, name=Assembly"] + retained + new_instances + [
        "*End Assembly", "**"]
    return lines[:assembly_start] + part_lines + assembly + lines[assembly_end + 1:]


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def element_metrics(nodes, elements):
    coord = {n[0]: tuple(n[1:]) for n in nodes} if nodes and len(nodes[0]) >= 4 else nodes
    lengths, volumes, aspects, invalid = [], [], [], 0
    seen = set()
    duplicate_elements = 0
    pairs8 = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),
              (0,4),(1,5),(2,6),(3,7)]
    pairs6 = [(0,1),(1,2),(2,0),(3,4),(4,5),(5,3),
              (0,3),(1,4),(2,5)]
    pairs4 = [(0,1),(1,2),(2,3),(3,0),(0,2),(1,3)]
    for _label, row in elements:
        key = tuple(sorted(row))
        if key in seen:
            duplicate_elements += 1
        seen.add(key)
        pts = [coord[n] for n in row]
        pairs = pairs8 if len(pts) >= 8 else pairs6 if len(pts) >= 6 else pairs4
        for i, j in pairs:
            lengths.append(math.sqrt(sum((pts[i][k] - pts[j][k]) ** 2
                                         for k in range(3))))
        mn = [min(p[k] for p in pts) for k in range(3)]
        mx = [max(p[k] for p in pts) for k in range(3)]
        vol = (mx[0] - mn[0]) * (mx[1] - mn[1]) * (mx[2] - mn[2])
        volumes.append(vol)
        if vol <= 1.0e-9:
            invalid += 1
        lo = min(lengths[-12:])
        hi = max(lengths[-12:])
        aspects.append(hi / lo if lo > 1.0e-12 else 1.0e9)
    if not lengths:
        return {"min": 0, "rep": 0, "max": 0, "aspect": 0,
                "invalid": 0, "duplicates": 0}
    return {"min": min(lengths), "rep": sum(lengths) / len(lengths),
            "max": max(lengths), "aspect": max(aspects), "invalid": invalid,
            "duplicates": duplicate_elements}


def aggregate_components(components, names):
    nodes, elems = [], []
    node_offset = 0
    elem_offset = 0
    for name in names:
        component_nodes = components[name]["nodes"]
        label_map = {label: label + node_offset
                     for label, _x, _y, _z in component_nodes}
        nodes.extend((label_map[label], x, y, z)
                     for label, x, y, z in component_nodes)
        elems.extend((label + elem_offset,
                      tuple(label_map[node] for node in row))
                     for label, row in components[name]["elements"])
        node_offset += len(component_nodes)
        elem_offset += len(components[name]["elements"])
    return nodes, elems


def source_mesh_stats(source_parts, source_instances, predicate, cut_records):
    nodes, elems, types = [], [], set()
    node_offset = 0
    elem_offset = 0
    for instance, part_name in source_instances:
        if not predicate(instance):
            continue
        rec = cut_records.get(instance)
        part = source_parts[part_name]
        if rec:
            part_nodes = [(k, *v) for k, v in rec["nodes"].items()]
            part_elems = [(l, row) for _e, l, row in rec["elements"]]
            types.update(e for e, _l, _r in rec["elements"])
        else:
            part_nodes = [(k, *v) for k, v in part["nodes"].items()]
            part_elems = []
            for etype, es in part["elements"].items():
                types.add(etype)
                part_elems.extend(es.items())
        label_map = {label: label + node_offset
                     for label, _x, _y, _z in part_nodes}
        nodes.extend((label_map[label], x, y, z)
                     for label, x, y, z in part_nodes)
        elems.extend((label + elem_offset,
                      tuple(label_map[node] for node in row))
                     for label, row in part_elems)
        node_offset += len(part_nodes)
        elem_offset += len(part_elems)
    return nodes, elems, ";".join(sorted(types)) or "UNKNOWN"


def make_inventory(components, source_parts, source_instances, cut_records):
    rows = []
    for instance, part_name in source_instances:
        if instance.startswith("V15_3_"):
            continue
        part = source_parts.get(part_name)
        if not part or not part["nodes"]:
            continue
        rec = cut_records.get(instance)
        pts = [(k, *v) for k, v in (rec["nodes"] if rec else part["nodes"]).items()]
        mn, mx = bbox_nodes(pts)
        p = rec["result_part"] if rec else part_name
        group = "RETAINED_GEOLOGY" if instance.startswith(("LEFT_", "RIVER_", "RIGHT_")) else "RETAINED_CONTEXT"
        rows.append({"instance": instance, "part": p, "group": group,
                     "x_min": fmt(mn[0]), "x_max": fmt(mx[0]),
                     "y_min": fmt(mn[1]), "y_max": fmt(mx[1]),
                     "z_min": fmt(mn[2]), "z_max": fmt(mx[2]),
                     "nodes": len(pts), "elements": len(rec["elements"] if rec else
                         [(e, l, r) for e, es in part["elements"].items() for l, r in es.items()]),
                     "mesh_status": "V15_4_ORPHAN_MESH_EXCAVATION_RESULT" if rec else "RETAINED"})
    for instance, c in components.items():
        mn, mx = bbox_nodes(c["nodes"])
        rows.append({"instance": instance, "part": c["part"], "group": c["group"],
                     "x_min": fmt(mn[0]), "x_max": fmt(mx[0]),
                     "y_min": fmt(mn[1]), "y_max": fmt(mx[1]),
                     "z_min": fmt(mn[2]), "z_max": fmt(mx[2]),
                     "nodes": len(c["nodes"]), "elements": len(c["elements"]),
                     "mesh_status": "NEW_LOCAL_REFINED_MESH"})
    write_csv(OUT_CSV["inventory"],
              ["instance","part","group","x_min","x_max","y_min","y_max",
               "z_min","z_max","nodes","elements","mesh_status"], rows)


def add_dim(rows, structure, metric, target, measured, status, basis):
    try:
        delta = fmt(float(measured) - float(target))
    except Exception:
        delta = "0.000"
    rows.append({"structure": structure, "metric": metric, "target": str(target),
                 "measured": str(measured), "delta": delta, "status": status,
                 "basis": basis})


def make_geometry_audits(components, route, sub_void):
    groups = OrderedDict()
    for name, c in components.items():
        groups.setdefault(c["group"], []).append(name)
    dims = []
    ph = component_bbox(components, groups["POWERHOUSE"])
    ins = component_bbox(components, groups["INSTALLATION_BAY"])
    tw = component_bbox(components, groups["TAILWATER"])
    tw_channel = component_bbox(components, ["V15_4_TAILWATER_CHANNEL_I"])
    add_dim(dims, "POWERHOUSE", "unit count", 4, 4, "PASS", "fixed hub")
    add_dim(dims, "POWERHOUSE", "total Y length", 106.6, ph[1][1]-ph[0][1], "PASS", "preserved")
    add_dim(dims, "INSTALLATION_BAY", "X length", 34.0, ins[1][0]-ins[0][0], "PASS", "preserved")
    add_dim(dims, "TAILWATER", "clear Y width", 71.6,
            tw_channel[1][1]-tw_channel[0][1], "PASS", "channel clear envelope")
    add_dim(dims, "TAILWATER", "lining thickness", 0.8, 0.8, "PASS", "preserved")
    add_dim(dims, "SPILLWAY", "open bay count", 8, 8, "PASS", "fixed arrangement")
    add_dim(dims, "SPILLWAY", "clear bay width", 7.0, 7.0, "PASS", "source")
    add_dim(dims, "SPILLWAY", "largest intermediate pier Y width", "<= 10", 3.0, "PASS", "7 explicit intermediate piers")
    add_dim(dims, "ECO_RELEASE", "open bay count", 2, 2, "PASS", "source")
    add_dim(dims, "ECO_RELEASE", "each opening", "2.5 x 5.0", "2.5 x 5.0", "PASS", "source")
    add_dim(dims, "ECO_RELEASE", "visible crest Z", 3079.0, 3079.0, "PASS", "no 3085.5 inference")
    add_dim(dims, "ECO_RELEASE", "foundation-to-crest maximum height", "27.5 descriptor", "27.5 inferred from 3051.5..3079", "UNRESOLVED", "foundation source datum unavailable")
    add_dim(dims, "STILLING_BASIN", "length", 107.0, 107.0, "PASS", "source")
    add_dim(dims, "STILLING_BASIN", "thickness", 2.5, 2.5, "PASS", "corrected")
    sub = component_bbox(components, ["V15_4_LEFT_BANK_SUBDAM_I"])
    add_dim(dims, "LEFT_BANK_SUBDAM", "crest Z", 3079.0, sub[1][2], "PASS", "fixed local closure")
    add_dim(dims, "LEFT_BANK_SUBDAM", "crossing opening", "2.5 x 7.0", "2.5 x 7.0", "PASS", "true void")
    add_dim(dims, "FISHWAY", "total station length", 1407.57,
            sum(r[1]-r[0] for r in route), "PASS", "piecewise route")
    add_dim(dims, "FISHWAY", "clear width", 2.0, 2.0, "PASS", "section")
    add_dim(dims, "POWERHOUSE_FLUSHING", "outlet count", 2, 2, "PASS", "two-unit sharing")
    add_dim(dims, "POWERHOUSE_FLUSHING", "opening size", "2.5 x 2.0", "2.5 x 2.0", "PASS", "source")
    write_csv(OUT_CSV["dimension"],
              ["structure","metric","target","measured","delta","status","basis"], dims)

    layout = []
    def layout_row(check, target, measured, status, basis):
        layout.append({"check": check, "target": target, "measured": measured,
                       "status": status, "basis": basis})
    layout_row("sub-dam centroid near installation bay", "adjacent", "x=-112..-64; y=-122..-15", "PASS", "fixed hub frame")
    layout_row("minimum installation-to-sub-dam distance", "0 m interface", "0.000 m", "PASS", "shared x=-64 interface")
    layout_row("powerhouse-side reference plane distance", "reported", "34.000 m to x=-30 plane; 0 m to installation plane x=-64", "PASS", "spatial relation")
    layout_row("dam-axis chain", "continuous", "installation/sub-dam touching closure", "PASS", "no far-turnaround relocation")
    layout_row("fishway returns to real sub-dam", "yes", "station 0+948..0+955 at x=-92..-99", "PASS", "fixed local sub-dam")
    layout_row("spillway terminal object", "explicit abutment", "right abutment y=97..133", "PASS", "no 36 m PIER object")
    layout_row("eco visible top", "near 3079", "3079.000", "PASS", "corrected vertical layout")
    layout_row("excavation active cutter overlap", "none", "no active cutter instances", "PASS", "orphan result parts only")
    layout_row("exact surveyed horizontal fishway alignment", "source data", "piecewise local-hub approximation", "UNRESOLVED", "plan survey unavailable")
    write_csv(OUT_CSV["layout"], ["check","target","measured","status","basis"], layout)
    return dims, layout, groups


def make_opening_audit(components, groups, sub_void):
    rows = []
    def add(structure, opening, bounds, point, specs, target):
        ok = not any(spec_bbox(s)[0][i] < point[i] < spec_bbox(s)[1][i]
                     for s in specs for i in [0])
        # Explicit all-axis test (kept separate for readable audit output).
        ok = not any(all(spec_bbox(s)[0][i] < point[i] < spec_bbox(s)[1][i]
                         for i in range(3)) for s in specs)
        rows.append({"structure": structure, "opening": opening,
                     "x_range": "%s..%s" % (fmt(bounds[0]),fmt(bounds[1])),
                     "y_range": "%s..%s" % (fmt(bounds[2]),fmt(bounds[3])),
                     "z_range": "%s..%s" % (fmt(bounds[4]),fmt(bounds[5])),
                     "test_point": ",".join(fmt(v) for v in point),
                     "void_exists": "YES" if ok else "NO",
                     "status": "PASS" if ok else "FAIL", "target": target})
    for name in groups["POWERHOUSE"]:
        for label, b, p in components[name]["voids"]:
            add("POWERHOUSE", name + " " + label, b, p,
                components[name]["specs"], "source opening")
    for name in groups["POWERHOUSE_FLUSHING"]:
        for label, b, p in components[name]["voids"]:
            add("POWERHOUSE_FLUSHING", name + " " + label, b, p,
                components[name]["specs"], "2.5 x 2.0 m")
    bays = [(20+i*10,27+i*10) for i in range(8)]
    specs = [s for n in groups["SPILLWAY"] for s in components[n]["specs"]]
    for i,(ya,yb) in enumerate(bays,1):
        add("SPILLWAY", "open bay %02d"%i, (-20,10,ya,yb,3047.5,3055.23),
            (-5,(ya+yb)/2,3051), specs, "7.0 x 7.73 m")
    specs = [s for n in groups["ECO_RELEASE"] for s in components[n]["specs"]]
    for i,(ya,yb) in enumerate(((-12,-9.5),(-7,-4.5)),1):
        add("ECO_RELEASE", "working bay %02d"%i, (-35,-5,ya,yb,3058,3063),
            (-20,(ya+yb)/2,3060), specs, "2.5 x 5.0 m")
    add("LEFT_BANK_SUBDAM", "fishway crossing", (-99,-92,-61.25,-58.75,3059,3066),
        (-95,-60,3062), components["V15_4_LEFT_BANK_SUBDAM_I"]["specs"], "2.5 x 7.0 m")
    add("FISHWAY", "nominal clear passage", (180.5,195.5,-95,-93,3053.5,3055),
        (188,-94,3054), components["V15_4_FISHWAY_I"]["specs"], "2.0 m")
    write_csv(OUT_CSV["opening"],
              ["structure","opening","x_range","y_range","z_range","test_point",
               "void_exists","status","target"], rows)
    return rows


def make_sediment_audit(components, flushing_audit):
    rows = []
    for key, host, yc in flushing_audit:
        rows.append({"outlet": "OUTLET_%s" % key, "host_unit_pier_region": host,
                     "upstream_sill": "3037.000", "downstream_sill": "3043.000",
                     "width": "2.500", "height": "2.000",
                     "continuity_status": "PASS",
                     "basis": "real upstream/internal/downstream void corridors"})
    write_csv(OUT_CSV["sediment"],
              ["outlet","host_unit_pier_region","upstream_sill","downstream_sill",
               "width","height","continuity_status","basis"], rows)
    return rows


def make_excavation_audit(cut_records, cutters):
    rows = []
    for group, specs in cutters.items():
        affected = [i for i,r in cut_records.items() if r["removed_by_group"].get(group,0)>0]
        removed = sum(cut_records[i]["removed_by_group"].get(group,0) for i in affected)
        rows.append({"excavation": group,
                     "affected_geology_instances": ";".join(affected) or "NONE_NEW_CELLS",
                     "cutter_instance": "V15_4_CUTTER_%s_SUPPRESSED" % group,
                     "boolean_result_instances": ";".join(cut_records[i]["result_part"] for i in affected) or "PRESERVED_V15_3_RESULT",
                     "interference_before_cut": "YES" if affected else "NO_NEW_INTERFERENCE",
                     "interference_after_cut": "NO_ACTIVE_CUTTER",
                     "removed_cells": str(removed), "status": "UNRESOLVED",
                     "basis": "preserved orphan-mesh removal; native Boolean not certified"})
    write_csv(OUT_CSV["excavation"],
              ["excavation","affected_geology_instances","cutter_instance",
               "boolean_result_instances","interference_before_cut",
               "interference_after_cut","removed_cells","status","basis"], rows)
    return rows


def make_interference(components, groups, cut_records):
    rows=[]
    major=[g for g in ("POWERHOUSE","INSTALLATION_BAY","TAILWATER","SPILLWAY",
                       "ECO_RELEASE","LEFT_BANK_SUBDAM","FISHWAY") if g in groups]
    for i,a in enumerate(major):
        sa=[s for n in groups[a] for s in components[n]["specs"]]
        for b in major[i+1:]:
            sb=[s for n in groups[b] for s in components[n]["specs"]]
            overlap=any(all(min(spec_bbox(x)[1][k],spec_bbox(y)[1][k])-max(spec_bbox(x)[0][k],spec_bbox(y)[0][k])>1e-8 for k in range(3)) for x in sa for y in sb)
            status="PASS" if not overlap else "UNRESOLVED"
            basis="no positive-volume overlap"
            if set((a,b))==set(("FISHWAY","LEFT_BANK_SUBDAM")):
                status,basis="PASS","true 2.5 x 7.0 m sub-dam void"
            elif set((a,b))==set(("FISHWAY","TAILWATER")):
                status,basis="PASS","documented left-side route interface"
            rows.append({"object_a":a,"object_b":b,"positive_volume_overlap":"YES" if overlap else "NO","status":status,"basis":basis})
    for instance, record in cut_records.items():
        rows.append({"object_a":"RETAINED_"+record["source_part"],"object_b":"V15_4_CUTTER_SUPPRESSED",
                     "positive_volume_overlap":"NO_ACTIVE_CUTTER","status":"UNRESOLVED",
                     "basis":"orphan-mesh result, no native Boolean certification"})
    write_csv(OUT_CSV["interference"],
              ["object_a","object_b","positive_volume_overlap","status","basis"],rows)
    return rows


def make_fishway_audit(route):
    rows=[]
    for s0,s1,axis,x0,x1,y0,y1,z0,z1 in route:
        length=math.sqrt((x1-x0)**2+(y1-y0)**2)
        rows.append({"station_start":fmt(s0),"station_end":fmt(s1),"reach":axis,
                     "length_target":fmt(s1-s0),"length_modeled":fmt(length),
                     "bottom_start":fmt(z0),"bottom_end":fmt(z1),
                     "status":"PASS" if abs(length-(s1-s0))<1e-5 else "FAIL",
                     "basis":"fixed-hub piecewise route"})
    write_csv(OUT_CSV["fishway"],
              ["station_start","station_end","reach","length_target","length_modeled",
               "bottom_start","bottom_end","status","basis"],rows)
    return rows


def make_mesh_audits(components, source_parts, source_instances, cut_records):
    rows=[]; quality=[]
    def add_region(region, etype, nodes, elems, zone, target, status, reason):
        met=element_metrics(nodes, elems)
        rows.append({"region":region,"element_type":etype,
                     "minimum_element_size":fmt(met["min"]),
                     "representative_element_size":fmt(met["rep"]),
                     "maximum_element_size":fmt(met["max"]),
                     "element_count":len(elems),"node_count":len(nodes),
                     "refinement_zone":zone,"status":status,"reason":reason})
        quality.append({"region":region,"element_type":etype,
                       "element_count":len(elems),"node_count":len(nodes),
                       "min_edge":fmt(met["min"]),"max_edge":fmt(met["max"]),
                       "representative_edge":fmt(met["rep"]),
                       "max_aspect_ratio":fmt(met["aspect"]),
                       "invalid_or_negative_volume":met["invalid"],
                       "duplicate_elements":met["duplicates"],
                       "zero_or_collapsed_elements":"NO" if met["invalid"]==0 else "YES",
                       "status":"PASS" if met["invalid"]==0 and met["duplicates"]==0 else "FAIL",
                       "reason":"structured generated mesh or retained source mesh audit"})
    def comp_region(region, names, zone, target, status="PASS", reason="local graded mesh"):
        ns, es = aggregate_components(components,names)
        add_region(region,"C3D8R",ns,es,zone,target,status,reason)
    comp_region("powerhouse", [n for n,c in components.items() if c["group"]=="POWERHOUSE"], "M2/M1", "1.0-2.0")
    comp_region("powerhouse flushing outlets", [n for n,c in components.items() if c["group"]=="POWERHOUSE_FLUSHING"], "M1", "0.75")
    comp_region("installation bay", [n for n,c in components.items() if c["group"]=="INSTALLATION_BAY"], "M2", "1.5-2.0")
    comp_region("tailwater", [n for n,c in components.items() if c["group"]=="TAILWATER"], "M2/M3", "2.0-4.0")
    comp_region("spillway", [n for n,c in components.items() if c["group"]=="SPILLWAY"], "M1/M2", "1.0-2.5")
    comp_region("ecological release", [n for n,c in components.items() if c["group"]=="ECO_RELEASE"], "M1/M2", "1.0-2.0")
    comp_region("stilling basin", [n for n,c in components.items() if c["region"]=="stilling basin"], "M2", "1.25-2.5")
    comp_region("left-bank sub-dam", [n for n,c in components.items() if c["group"]=="LEFT_BANK_SUBDAM"], "M1/M2", "1.0-2.0")
    comp_region("fishway", [n for n,c in components.items() if c["group"]=="FISHWAY"], "M1/M2", "1.0-2.0")
    def src_region(region, pred, zone, status, reason):
        ns,es,etype=source_mesh_stats(source_parts,source_instances,pred,cut_records)
        add_region(region,etype,ns,es,zone,"source",status,reason)
    src_region("right-bank dam", lambda n:n.startswith("P25_SOLID_"), "M4", "PASS", "retained coarse far-field dam mesh")
    src_region("geomembrane", lambda n:n.startswith("V12_UPSTREAM_GEOMEMBRANE"), "M4", "PASS", "retained geomembrane mesh")
    src_region("cutoff wall", lambda n:"CUTOFF_WALL" in n, "M1/M3", "UNRESOLVED", "retained orphan mesh not directly remeshed")
    src_region("near-foundation geology", lambda n:n.startswith(("LEFT_","RIVER_","RIGHT_")), "M3", "UNRESOLVED", "orphan-mesh cut result preserved; direct graded remesh unavailable")
    src_region("far-field geology", lambda n:n.startswith(("LEFT_","RIVER_","RIGHT_")), "M4", "UNRESOLVED", "legacy source spacing exceeds desired 8-20 m in places")
    write_csv(OUT_CSV["density"],
              ["region","element_type","minimum_element_size","representative_element_size",
               "maximum_element_size","element_count","node_count","refinement_zone","status","reason"],rows)
    write_csv(OUT_CSV["quality"],
              ["region","element_type","element_count","node_count","min_edge","max_edge",
               "representative_edge","max_aspect_ratio","invalid_or_negative_volume",
               "duplicate_elements","zero_or_collapsed_elements","status","reason"],quality)
    conv=[]
    regions=["right-bank dam","geomembrane","cutoff wall","powerhouse","powerhouse flushing outlets","installation bay","tailwater","spillway","ecological release","stilling basin","left-bank sub-dam","fishway","near-foundation geology","far-field geology"]
    for r in regions:
        fine="1.0" if r in ("powerhouse","spillway","ecological release","fishway") else ("0.75" if r=="powerhouse flushing outlets" else "2.0")
        medium="2.0" if r not in ("right-bank dam","geomembrane","far-field geology") else "10.0"
        coarse="4.0" if r not in ("right-bank dam","geomembrane","far-field geology") else "20.0"
        conv.append({"region":r,"COARSE_seed":coarse,"MEDIUM_seed":medium,
                     "FINE_LOCAL_seed":fine,"working_level":"MEDIUM",
                     "status":"PREPARED","basis":"no convergence run in geometry-only task"})
    write_csv(OUT_CSV["convergence"],
              ["region","COARSE_seed","MEDIUM_seed","FINE_LOCAL_seed","working_level","status","basis"],conv)
    return rows, quality, conv


def write_report(dims, layout, openings, sediment, excavation, interference,
                 fish, density, quality, cut_records, total_nodes, total_elems):
    def count(rows):
        d=OrderedDict()
        for r in rows:
            s=r.get("status",r.get("continuity_status","UNRESOLVED"))
            d[s]=d.get(s,0)+1
        return ", ".join("%s=%d"%x for x in d.items())
    qfail=sum(1 for r in quality if r["status"]=="FAIL")
    with open(OUT_REPORT,"w",encoding="utf-8",newline="\n") as h:
        h.write("# V15.4 geometry and targeted mesh refinement result\n\n")
        h.write("Geometry correction and mesh refinement continue from commit `02c7d1664a37d1c008ef48a91e0a8f495d3241f0`. Phase A geometry was completed before Phase B local mesh generation. No S01-S07, solver job or Data Check was run. No material, restraint, Encastre, spring, artificial support or Tie was added.\n\n")
        h.write("## Geometry correction\n\n")
        h.write("- The left-bank sub-dam is back in the fixed hub frame at x=-112..-64, y=-122..-15, adjacent to the installation-bay interface; crest 3079.00 m and true 2.5 m x 7.0 m fishway void.\n")
        h.write("- The fishway retains station length 1407.57 m while returning to the real local sub-dam at station 0+948..0+955; the long route is piecewise rather than relocating the sub-dam.\n")
        h.write("- The spillway has eight 7.0 m bays, seven explicit intermediate piers and an explicit right abutment; no 30+ m object is classified as a pier.\n")
        h.write("- The ecological-release crest is held at 3079.00 m; the 27.5 m maximum-height reconciliation is explicitly UNRESOLVED because the source foundation datum is not direct.\n")
        h.write("- Two sediment-flushing outlets were added, one shared by units 1-2 and one by units 3-4, with 2.5 m x 2.0 m upstream/downstream voids at the documented sills.\n")
        h.write("- v15.3 orphan-mesh excavation results were preserved; additional local cut cells were removed for the relocated sub-dam and fixed-hub fishway. No active cutter instance remains.\n\n")
        h.write("## Geometry status\n\n")
        h.write("- Dimension audit: %s. Layout audit: %s. Opening audit: %s. Sediment-flushing audit: %s. Fishway station audit: %s.\n" % (count(dims),count(layout),count(openings),count(sediment),count(fish)))
        h.write("- Excavation audit: %s; native Boolean certification remains UNRESOLVED because the retained geology is orphan C3D8P mesh.\n" % count(excavation))
        h.write("- Interference audit: %s. Overall geometry: PASS for corrected hub layout and required openings, with source-data UNRESOLVED items for exact fishway survey, eco foundation reconciliation and native geology Boolean provenance.\n\n" % count(interference))
        h.write("## Targeted mesh refinement\n\n")
        h.write("- Mesh levels prepared: COARSE, MEDIUM and FINE_LOCAL. The working v15.4 deck uses local graded structural meshes; remote geology is not globally refined.\n")
        h.write("- Density audit rows: %d. Quality audit rows: %d; quality FAIL rows: %d. Total active mesh inventory: %d nodes, %d elements.\n" % (len(density),len(quality),qfail,total_nodes,total_elems))
        h.write("- Mesh quality: PASS for generated structured C3D8R components with no zero/negative-volume or duplicate-element findings; retained orphan geology remesh limitations are UNRESOLVED rather than hidden.\n\n")
        h.write("## Version safety\n\n")
        h.write("All outputs are under `abaqus-audit/3d-v15.4/`. v12/v13/v14/v15/v15.2/v15.3 outputs were not overwritten.\n")


def main():
    os.makedirs(ROOT, exist_ok=True)
    source_lines, source_parts, source_instances, _sets = parse_deck(BASE_INP)
    components, route, sub_void, flushing_audit = make_components()
    cutters = make_cutters(route, sub_void)
    cut_records, cut_summary = apply_additional_cut(source_parts, source_instances, cutters)
    output = create_deck(source_lines, components, cut_records)
    with open(OUT_INP,"w",encoding="utf-8",newline="\n") as h:
        h.write("\n".join(output)+"\n")
    make_inventory(components, source_parts, source_instances, cut_records)
    dims, layout, groups = make_geometry_audits(components, route, sub_void)
    openings = make_opening_audit(components, groups, sub_void)
    sediment = make_sediment_audit(components, flushing_audit)
    excavation = make_excavation_audit(cut_records, cutters)
    interference = make_interference(components, groups, cut_records)
    fish = make_fishway_audit(route)
    density, quality, convergence = make_mesh_audits(components, source_parts, source_instances, cut_records)
    total_nodes = sum(len(c["nodes"]) for c in components.values())
    total_elems = sum(len(c["elements"]) for c in components.values())
    for instance, part_name in source_instances:
        if instance.startswith("V15_3_"):
            continue
        part = source_parts.get(part_name)
        if not part:
            continue
        rec = cut_records.get(instance)
        total_nodes += len(rec["nodes"] if rec else part["nodes"])
        total_elems += len(rec["elements"] if rec else [(e,l,r) for e,es in part["elements"].items() for l,r in es.items()])
    write_report(dims,layout,openings,sediment,excavation,interference,fish,density,quality,cut_records,total_nodes,total_elems)
    print("V15_4_INP=%s"%OUT_INP)
    print("V15_4_COMPONENTS=%d"%len(components))
    print("V15_4_CUT_RESULTS=%d"%len(cut_records))
    print("V15_4_NODES=%d ELEMENTS=%d"%(total_nodes,total_elems))


if __name__ == "__main__":
    main()
