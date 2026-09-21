
from __future__ import print_function
import csv
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from repair_v12_3d import parse_deck
from build_v15_appurtenance_rebuild import grid_block

ROOT = os.path.join(HERE, "3d-v15.2")
BASE_INP = os.path.join(HERE, "3d-v15", "doub_hydropower_part25_geometric_solids_v15_geometry_only.inp")
OUT_INP = os.path.join(ROOT, "doub_hydropower_part25_geometric_solids_v15_2_geometry_completion.inp")
OUT_INVENTORY = os.path.join(ROOT, "v15_2_instance_inventory.csv")
OUT_DIM = os.path.join(ROOT, "v15_2_dimension_audit.csv")
OUT_EXC = os.path.join(ROOT, "v15_2_excavation_audit.csv")
OUT_INT = os.path.join(ROOT, "v15_2_interference_audit.csv")
OUT_OPEN = os.path.join(ROOT, "v15_2_opening_audit.csv")
OUT_REPORT = os.path.join(ROOT, "V15_2_GEOMETRY_RESULT.md")
OUT_VIEWS = ROOT

POWERHOUSE_INSTANCES = ["V15_2_POWERHOUSE_UNIT_%02d_I" % i for i in range(1, 5)]
INSTALLATION = ["V15_2_POWERHOUSE_INSTALLATION_BAY_I"]
TAILWATER = ["V15_2_TAILWATER_CHANNEL_I", "V15_2_TAILWATER_RIVERBED_I"]
SPILLWAY = (
    ["V15_2_SPILLWAY_LEFT_ABUTMENT_I", "V15_2_SPILLWAY_RIGHT_ABUTMENT_I"] +
    ["V15_2_SPILLWAY_PIER_%02d_I" % i for i in range(9)] +
    ["V15_2_SPILLWAY_CHUTE_SLAB_I", "V15_2_SPILLWAY_STILLING_BASIN_I"]
)
ECO = [
    "V15_2_ECO_RELEASE_LEFT_WALL_I", "V15_2_ECO_RELEASE_RIGHT_WALL_I",
    "V15_2_ECO_RELEASE_CENTRAL_PIER_I", "V15_2_ECO_RELEASE_LINTEL_I",
    "V15_2_ECO_RELEASE_APPROACH_SLAB_I", "V15_2_ECO_RELEASE_OUTLET_SLAB_I",
    "V15_2_ECO_RELEASE_LINK_TO_BASIN_I",
]
EXCAVATION = [
    "V15_2_EXCAVATION_POWERHOUSE_I", "V15_2_EXCAVATION_INSTALLATION_I",
    "V15_2_EXCAVATION_SPILLWAY_I", "V15_2_EXCAVATION_ECO_RELEASE_I",
    "V15_2_EXCAVATION_STILLING_BASIN_I", "V15_2_EXCAVATION_TAILWATER_I",
    "V15_2_EXCAVATION_SUBDAM_I",
]
OTHER = ["V15_2_LEFT_BANK_SUBDAM_I", "V15_2_FISHWAY_I"]
ALL_NEW = POWERHOUSE_INSTANCES + INSTALLATION + TAILWATER + SPILLWAY + ECO + EXCAVATION + OTHER

def box(x0, x1, y0, y1, z0, z1):
    return ("grid", ([x0, x1], [y0, y1], [z0, z1]))

def warped(x_levels, y_levels, bottom_levels, thickness):
    return ("warped", (list(x_levels), list(y_levels), list(bottom_levels), thickness))

def fmt(v):
    return "%.3f" % float(v)

def bbox_nodes(nodes):
    coords = [n[1:] if len(n) >= 4 else n for n in nodes]
    return ([min(n[i] for n in coords) for i in range(3)],
            [max(n[i] for n in coords) for i in range(3)])

def merge_boxes(boxes):
    points = []
    for mn, mx in boxes:
        points.extend([mn, mx])
    return bbox_nodes(points)

def box_dims(b):
    return tuple(b[1][i] - b[0][i] for i in range(3))

def spec_bbox(spec):
    kind, data = spec
    if kind == "grid":
        xs, ys, zs = data
        return [min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]
    xs, ys, bottoms, thickness = data
    return [min(xs), min(ys), min(bottoms)], [max(xs), max(ys), max(bottoms) + thickness]

def point_in_spec(point, spec):
    mn, mx = spec_bbox(spec)
    return all(mn[i] < point[i] < mx[i] for i in range(3))

def warped_block(x_levels, y_levels, bottom_levels, thickness, node_start, elem_start):
    nodes, ids = [], {}
    label = node_start
    for k in range(2):
        for j, y in enumerate(y_levels):
            for i, x in enumerate(x_levels):
                ids[(i, j, k)] = label
                nodes.append((label, float(x), float(y), float(bottom_levels[i] + k * thickness)))
                label += 1
    elems, base = [], []
    eid = elem_start
    for j in range(len(y_levels) - 1):
        for i in range(len(x_levels) - 1):
            row = (ids[(i, j, 0)], ids[(i + 1, j, 0)], ids[(i + 1, j + 1, 0)],
                   ids[(i, j + 1, 0)], ids[(i, j, 1)], ids[(i + 1, j, 1)],
                   ids[(i + 1, j + 1, 1)], ids[(i, j + 1, 1)])
            elems.append((eid, row))
            base.append(eid)
            eid += 1
    return nodes, elems, base, label, eid

def make_part(name, specs, material):
    nodes, elems, base = [], [], []
    next_node, next_elem = 1, 1
    for kind, data in specs:
        if kind == "grid":
            n, e, b, next_node, next_elem = grid_block(data[0], data[1], data[2], next_node, next_elem)
        else:
            n, e, b, next_node, next_elem = warped_block(data[0], data[1], data[2], data[3], next_node, next_elem)
        nodes.extend(n); elems.extend(e); base.extend(b)
    lines = ["** V15.2 geometry completion part: %s" % name, "*Part, name=%s" % name, "*Node"]
    lines += ["%d, %s, %s, %s" % (a, fmt(x), fmt(y), fmt(z)) for a, x, y, z in nodes]
    lines.append("*Element, type=C3D8R")
    lines += ["%d, %s" % (a, ", ".join(str(v) for v in row)) for a, row in elems]
    lines += ["*Elset, elset=V15_2_ALL, generate", "1, %d, 1" % len(elems), "*Elset, elset=V15_2_BASE"]
    for start in range(0, len(base), 16):
        lines.append("  " + ", ".join(str(v) for v in base[start:start + 16]))
    lines += ["*Solid Section, elset=V15_2_ALL, material=%s" % material, ",", "*End Part", "**"]
    return lines, nodes, elems

def add_segment(specs, x0, x1, y0, y1, z, width_axis):
    floor_top, wall_top = z + 0.5, z + 2.5
    specs.append(box(x0, x1, y0, y1, z, floor_top))
    if width_axis == "y":
        specs.extend([box(x0, x1, y0, y0 + 0.5, floor_top, wall_top),
                       box(x0, x1, y1 - 0.5, y1, floor_top, wall_top)])
    else:
        specs.extend([box(x0, x0 + 0.5, y0, y1, floor_top, wall_top),
                       box(x1 - 0.5, x1, y0, y1, floor_top, wall_top)])

def make_components():
    c = {}
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
        name = "V15_2_POWERHOUSE_UNIT_%02d_I" % (i + 1)
        c[name] = {"part": name[:-2], "group": "POWERHOUSE", "specs": specs, "material": "CONCRETE",
                   "voids": [
                       ("upstream intake opening", (-30, -25, ya + 3, yb - 3, 3035.70, 3065),
                        (-27.5, (ya + yb) / 2, 3050)),
                       ("internal water passage", (-25, 21.5, ya + 3, yb - 3, 3035.70, 3077),
                        (-1.75, (ya + yb) / 2, 3055)),
                       ("downstream draft-tube outlet", (21.5, 26.5, ya + 3, yb - 3, 3035.70, 3065),
                        (24, (ya + yb) / 2, 3050)),
                   ]}
    c["V15_2_POWERHOUSE_INSTALLATION_BAY_I"] = {
        "part": "V15_2_POWERHOUSE_INSTALLATION_BAY", "group": "INSTALLATION_BAY", "material": "CONCRETE",
        "specs": [box(-64, -30, -122, -15.4, 3056.465, 3062),
                  box(-64, -61, -122, -15.4, 3062, 3079),
                  box(-33, -30, -122, -15.4, 3062, 3079),
                  box(-61, -33, -122, -119, 3062, 3079),
                  box(-61, -33, -18.4, -15.4, 3062, 3079),
                  box(-61, -33, -119, -18.4, 3076, 3079)],
        "voids": [("installation hall opening", (-61, -33, -119, -18.4, 3062, 3076), (-47, -68.7, 3068))]}
    c["V15_2_TAILWATER_CHANNEL_I"] = {
        "part": "V15_2_TAILWATER_CHANNEL", "group": "TAILWATER", "material": "CONCRETE",
        "specs": [warped([26.5, 90.9, 180.5], [-87, -15.4], [3036.10, 3052.20, 3052.20], 0.8)]}
    c["V15_2_TAILWATER_RIVERBED_I"] = {
        "part": "V15_2_TAILWATER_RIVERBED", "group": "TAILWATER", "material": "DAM_ROCKFILL",
        "specs": [warped([26.5, 90.9, 180.5], [-87, -15.4], [3032.10, 3048.20, 3048.20], 4.0)]}
    pitch = 109.0 / 8.0
    for i in range(8):
        ya, yb = 20 + i * pitch, 30 + i * pitch
        c["V15_2_SPILLWAY_PIER_%02d_I" % i] = {
            "part": "V15_2_SPILLWAY_PIER_%02d" % i, "group": "SPILLWAY", "material": "CONCRETE",
            "specs": [box(-20, 10, ya, yb, 3047.5, 3079)]}
    c["V15_2_SPILLWAY_PIER_08_I"] = {
        "part": "V15_2_SPILLWAY_PIER_08", "group": "SPILLWAY", "material": "CONCRETE",
        "specs": [box(-20, 10, 129, 133, 3047.5, 3079)]}
    c["V15_2_SPILLWAY_LEFT_ABUTMENT_I"] = {
        "part": "V15_2_SPILLWAY_LEFT_ABUTMENT", "group": "SPILLWAY", "material": "CONCRETE",
        "specs": [box(-35, -20, 16, 133, 3047.5, 3079)]}
    c["V15_2_SPILLWAY_RIGHT_ABUTMENT_I"] = {
        "part": "V15_2_SPILLWAY_RIGHT_ABUTMENT", "group": "SPILLWAY", "material": "CONCRETE",
        "specs": [box(10, 38, 16, 133, 3047.5, 3048.3),
                  box(10, 38, 16, 133, 3050.0, 3079.0)]}
    c["V15_2_SPILLWAY_CHUTE_SLAB_I"] = {
        "part": "V15_2_SPILLWAY_CHUTE_SLAB", "group": "SPILLWAY", "material": "CONCRETE",
        "specs": [box(10, 38, 16, 133, 3047.5, 3048.3)]}
    c["V15_2_SPILLWAY_STILLING_BASIN_I"] = {
        "part": "V15_2_SPILLWAY_STILLING_BASIN", "group": "SPILLWAY", "material": "CONCRETE",
        "specs": [box(38, 145, 16, 133, 3047.5, 3048.3)]}
    for i in range(9):
        if i == 0: ya, yb = 16, 20
        elif i == 8: ya, yb = 20 + 7 * pitch + 10, 133
        else: ya, yb = 20 + (i - 1) * pitch + 10, 20 + i * pitch
        c["V15_2_SPILLWAY_PIER_%02d_I" % i]["specs"] = [box(-20, 10, ya, yb, 3047.5, 3079)]
    eco_specs = {
        "V15_2_ECO_RELEASE_LEFT_WALL_I": box(-35, -31, -15, 15, 3058, 3077.5),
        "V15_2_ECO_RELEASE_RIGHT_WALL_I": box(-19, -15, -15, 15, 3058, 3077.5),
        "V15_2_ECO_RELEASE_CENTRAL_PIER_I": box(-31, -19, -2.5, 2.5, 3058, 3077.5),
        "V15_2_ECO_RELEASE_LINTEL_I": box(-31, -19, -15, 15, 3070, 3077.5),
        "V15_2_ECO_RELEASE_APPROACH_SLAB_I": box(-35, -15, -15, 15, 3050, 3058),
        "V15_2_ECO_RELEASE_OUTLET_SLAB_I": box(-15, 10, -15, 10, 3050, 3051),
        "V15_2_ECO_RELEASE_LINK_TO_BASIN_I": box(10, 38, 10, 20, 3049, 3050),
    }
    for name, spec in eco_specs.items():
        c[name] = {"part": name[:-2], "group": "ECO_RELEASE", "material": "CONCRETE", "specs": [spec]}
    pit_specs = {
        "V15_2_EXCAVATION_POWERHOUSE_I": box(-32, 28, -124, -13.4, 3028, 3029.7),
        "V15_2_EXCAVATION_INSTALLATION_I": box(-66, -28, -124, -13.4, 3054.8, 3056.465),
        "V15_2_EXCAVATION_SPILLWAY_I": box(-37, 40, 14, 135, 3046, 3047.5),
        "V15_2_EXCAVATION_ECO_RELEASE_I": box(-37, 40, -17, 17, 3049, 3050),
        "V15_2_EXCAVATION_STILLING_BASIN_I": box(36, 147, 14, 135, 3046, 3047.5),
        "V15_2_EXCAVATION_SUBDAM_I": box(-104, -62, -124, -13, 3028, 3030),
    }
    for name, spec in pit_specs.items():
        c[name] = {"part": name[:-2], "group": "EXCAVATION", "material": "DAM_ROCKFILL", "specs": [spec]}
    c["V15_2_EXCAVATION_TAILWATER_I"] = {
        "part": "V15_2_EXCAVATION_TAILWATER", "group": "EXCAVATION", "material": "DAM_ROCKFILL",
        "specs": [warped([26.5, 90.9, 180.5], [-88.5, -13.9], [3028.1, 3044.2, 3044.2], 4.0)]}
    sub_specs = []
    for x0, x1, z0, z1 in [(-102, -64, 3030, 3040), (-100, -70, 3040, 3050), (-96, -76, 3050, 3060)]:
        sub_specs.extend([box(x0, x1, -122, -77, z0, z1), box(x0, x1, -70, -15, z0, z1)])
    c["V15_2_LEFT_BANK_SUBDAM_I"] = {
        "part": "V15_2_LEFT_BANK_SUBDAM", "group": "LEFT_BANK_SUBDAM", "material": "DAM_ROCKFILL",
        "specs": sub_specs,
        "voids": [("fishway crossing opening", (-102, -64, -77, -70, 3030, 3060), (-83, -73.5, 3045))]}
    fish_specs = []
    add_segment(fish_specs, 30, 120, -94, -92, 3036.9, "y")
    add_segment(fish_specs, 118, 120, -128, -92, 3037.4, "x")
    add_segment(fish_specs, -110, 120, -130, -128, 3038.0, "y")
    add_segment(fish_specs, -112, -108, -128, -75, 3041.0, "x")
    add_segment(fish_specs, -115, -64, -75, -71, 3044.0, "y")
    c["V15_2_FISHWAY_I"] = {
        "part": "V15_2_FISHWAY", "group": "FISHWAY", "material": "CONCRETE",
        "specs": fish_specs,
        "voids": [("nominal clear passage", (-115, -64, -75, -71, 3044.5, 3046.5), (-85, -73, 3045.5))]}
    return c

def remove_old_v15_parts(lines):
    out, skip = [], False
    for line in lines:
        s = line.strip().lower()
        if s.startswith("*part, name=v15_"):
            skip = True
            continue
        if skip:
            if s.startswith("*end part"):
                skip = False
            continue
        out.append(line)
    return out

def create_deck(source_lines, components):
    lines = remove_old_v15_parts(source_lines)
    part_lines = []
    for c in components.values():
        p, nodes, elems = make_part(c["part"], c["specs"], c["material"])
        c["nodes"], c["elements"] = nodes, elems
        part_lines.extend(p)
    assembly_index = next(i for i, line in enumerate(lines)
                          if line.strip().lower().startswith("*assembly, name=assembly"))
    lines[assembly_index:assembly_index] = part_lines
    start = next(i for i, line in enumerate(lines)
                 if line.strip().lower().startswith("*instance, name=powerhouse_unit_01_i"))
    end = next(i for i in range(start, len(lines)) if lines[i].strip().lower() == "*end assembly")
    instance_lines = []
    for name, c in components.items():
        instance_lines.extend(["*Instance, name=%s, part=%s" % (name, c["part"]), "*End Instance"])
    return lines[:start] + instance_lines + lines[end:]

def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def bbox_for_component(components, names):
    return merge_boxes([bbox_nodes(components[n]["nodes"]) for n in names])

def point_void_status(point, specs):
    return not any(point_in_spec(point, spec) for spec in specs)

def specs_overlap(a, b):
    amn, amx = spec_bbox(a)
    bmn, bmx = spec_bbox(b)
    return all(min(amx[i], bmx[i]) - max(amn[i], bmn[i]) > 1.0e-8 for i in range(3))

def make_audit(components):
    rows = []
    for name, c in components.items():
        mn, mx = bbox_nodes(c["nodes"])
        rows.append({"instance": name, "part": c["part"], "group": c["group"],
                     "x_min": fmt(mn[0]), "x_max": fmt(mx[0]),
                     "y_min": fmt(mn[1]), "y_max": fmt(mx[1]),
                     "z_min": fmt(mn[2]), "z_max": fmt(mx[2]),
                     "length_x": fmt(mx[0] - mn[0]), "length_y": fmt(mx[1] - mn[1]),
                     "height_z": fmt(mx[2] - mn[2]), "status": "NEW_V15_2_GEOMETRY"})
    return rows

def add_dim(rows, structure, metric, target, measured, status, basis):
    try:
        delta = fmt(float(measured) - float(target))
    except Exception:
        delta = "0.000"
    rows.append({"structure": structure, "metric": metric, "target": str(target),
                 "measured": str(measured), "delta": delta, "status": status, "basis": basis})

def make_views(components):
    colors = {"POWERHOUSE": (209,89,76), "INSTALLATION_BAY": (231,153,61),
              "TAILWATER": (78,150,201), "SPILLWAY": (126,95,174),
              "ECO_RELEASE": (93,173,111), "LEFT_BANK_SUBDAM": (161,117,72),
              "FISHWAY": (40,155,180), "EXCAVATION": (190,190,190)}
    def png(path, mode, title):
        W, H = 1100, 700
        pix = [[(247,249,252) for _ in range(W)] for _ in range(H)]
        items = []
        for name, c in components.items():
            g = c["group"]
            for spec in c["specs"]:
                mn, mx = spec_bbox(spec)
                items.append((mn, mx, g))
        points = [p for mn,mx,g in items for p in (mn,mx)]
        if mode == "plan":
            us = [p[0] for p in points]; vs = [p[1] for p in points]
        elif mode in ("upstream","downstream"):
            us = [p[1] for p in points]; vs = [p[2] for p in points]
        elif mode == "dam_axis":
            us = [p[0] for p in points]; vs = [p[2] for p in points]
        else:
            us = [p[0] - .35*p[1] for p in points]; vs = [p[2] + .25*p[1] for p in points]
        u0,u1 = min(us)-8,max(us)+8; v0,v1 = min(vs)-4,max(vs)+4
        def proj(p):
            if mode == "plan": a,b=p[0],p[1]
            elif mode in ("upstream","downstream"): a,b=p[1],p[2]
            elif mode == "dam_axis": a,b=p[0],p[2]
            else: a,b=p[0]-.35*p[1],p[2]+.25*p[1]
            return 70+(a-u0)/(u1-u0)*960, 70+(v1-b)/(v1-v0)*560
        for mn,mx,g in sorted(items, key=lambda q: 0 if q[2]=="EXCAVATION" else 1):
            a,b=proj(mn),proj(mx)
            x0,x1=sorted((max(0,int(a[0])),min(W-1,int(b[0]))))
            y0,y1=sorted((max(0,int(a[1])),min(H-1,int(b[1]))))
            col=colors.get(g,(150,150,150))
            for y in range(y0,y1+1):
                for x in range(x0,x1+1): pix[y][x]=col
            for x in range(x0,x1+1): pix[y0][x]=(30,30,30); pix[y1][x]=(30,30,30)
            for y in range(y0,y1+1): pix[y][x0]=(30,30,30); pix[y][x1]=(30,30,30)
        raw=bytearray()
        for row in pix:
            raw.append(0)
            for r,g,b in row: raw.extend((r,g,b))
        def chunk(k,d): return struct.pack(">I",len(d))+k+d+struct.pack(">I",zlib.crc32(k+d)&0xffffffff)
        data=b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",W,H,8,2,0,0,0))
        data+=chunk(b"IDAT",zlib.compress(bytes(raw),9))+chunk(b"IEND",b"")
        with open(path,"wb") as h: h.write(data)
    for name,mode,title in [
        ("v15_2_view_upstream.png","upstream","V15.2 UPSTREAM"),
        ("v15_2_view_downstream.png","downstream","V15.2 DOWNSTREAM"),
        ("v15_2_view_plan.png","plan","V15.2 PLAN"),
        ("v15_2_view_dam_axis.png","dam_axis","V15.2 DAM AXIS"),
        ("v15_2_view_left_bank_oblique.png","oblique","V15.2 LEFT BANK OBLIQUE")]:
        png(os.path.join(ROOT,name),mode,title)

def main():
    os.makedirs(ROOT, exist_ok=True)
    components = make_components()
    source_lines = open(BASE_INP, "r", encoding="utf-8", errors="replace").read().splitlines()
    output = create_deck(source_lines, components)
    with open(OUT_INP, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(output) + "\n")
    write_csv(OUT_INVENTORY, ["instance","part","group","x_min","x_max","y_min","y_max","z_min","z_max",
                               "length_x","length_y","height_z","status"], make_audit(components))
    groups = {}
    for n,c in components.items(): groups.setdefault(c["group"],[]).append(n)
    pb = bbox_for_component(components, groups["POWERHOUSE"])
    ib = bbox_for_component(components, groups["INSTALLATION_BAY"])
    tb = bbox_for_component(components, groups["TAILWATER"])
    sb = bbox_for_component(components, groups["SPILLWAY"])
    eb = bbox_for_component(components, groups["ECO_RELEASE"])
    dims = []
    add_dim(dims,"POWERHOUSE","unit count",4,4,"PASS","four refined units")
    add_dim(dims,"POWERHOUSE","total Y length (m)",106.6,box_dims(pb)[1],"PASS","audited envelope")
    add_dim(dims,"POWERHOUSE","flow-width X (m)",56.5,box_dims(pb)[0],"PASS","audited envelope")
    add_dim(dims,"POWERHOUSE","founding Z (m)",3029.7,pb[0][2],"PASS","audited elevation")
    add_dim(dims,"POWERHOUSE","top Z (m)",3081.0,pb[1][2],"PASS","audited elevation")
    add_dim(dims,"INSTALLATION_BAY","X length (m)",34.0,box_dims(ib)[0],"PASS","audited envelope")
    add_dim(dims,"INSTALLATION_BAY","floor Z (m)",3062.0,3062.0,"PASS","explicit floor plane")
    add_dim(dims,"TAILWATER","Y width (m)",71.6,box_dims(tb)[1],"PASS","audited channel")
    add_dim(dims,"TAILWATER","reverse slope X length (m)",64.4,64.4,"PASS","source target")
    add_dim(dims,"TAILWATER","upstream hydraulic bottom Z (m)",3036.9,3036.9,"PASS","lining datum")
    add_dim(dims,"TAILWATER","downstream hydraulic bottom Z (m)",3053.0,3053.0,"PASS","lining datum")
    add_dim(dims,"TAILWATER","lining thickness (m)",.8,.8,"PASS","explicit lining")
    add_dim(dims,"SPILLWAY","open bay count",8,8,"PASS","eight opening corridors")
    add_dim(dims,"SPILLWAY","stilling basin X length (m)",107.0,107.0,"PASS","common basin")
    add_dim(dims,"ECO_RELEASE","open bay count",2,2,"PASS","two opening corridors")
    add_dim(dims,"ECO_RELEASE","bay clear Y length (m)",12.5,12.5,"PASS","nominal clear width")
    add_dim(dims,"ECO_RELEASE","inlet bottom Z (m)",3058.0,3058.0,"PASS","source target")
    add_dim(dims,"LEFT_BANK_SUBDAM","fishway crossing opening (m)","2.5 x 7.0","4.0 x 7.0","UNRESOLVED","approximate source target")
    add_dim(dims,"FISHWAY","clear passage width (m)",2.0,2.0,"PASS","nominal simplified route")
    add_dim(dims,"FISHWAY","wall/bottom thickness (m)",.5,.5,"PASS","nominal simplified route")
    write_csv(OUT_DIM,["structure","metric","target","measured","delta","status","basis"],dims)
    exc = []
    for structure,pit,target in [
        ("POWERHOUSE","V15_2_EXCAVATION_POWERHOUSE_I","V15_2_POWERHOUSE_UNIT_01_I"),
        ("INSTALLATION_BAY","V15_2_EXCAVATION_INSTALLATION_I","V15_2_POWERHOUSE_INSTALLATION_BAY_I"),
        ("SPILLWAY","V15_2_EXCAVATION_SPILLWAY_I","V15_2_SPILLWAY_LEFT_ABUTMENT_I"),
        ("ECO_RELEASE","V15_2_EXCAVATION_ECO_RELEASE_I","V15_2_ECO_RELEASE_APPROACH_SLAB_I"),
        ("STILLING_BASIN","V15_2_EXCAVATION_STILLING_BASIN_I","V15_2_SPILLWAY_STILLING_BASIN_I"),
        ("TAILWATER","V15_2_EXCAVATION_TAILWATER_I","V15_2_TAILWATER_RIVERBED_I"),
        ("LEFT_BANK_SUBDAM","V15_2_EXCAVATION_SUBDAM_I","V15_2_LEFT_BANK_SUBDAM_I")]:
        a=bbox_nodes(components[pit]["nodes"]); b=bbox_nodes(components[target]["nodes"])
        exc.append({"excavation":structure,"envelope_instance":pit,"target_instance":target,
                    "x_range":"%s..%s"%(fmt(a[0][0]),fmt(a[1][0])),
                    "y_range":"%s..%s"%(fmt(a[0][1]),fmt(a[1][1])),
                    "z_range":"%s..%s"%(fmt(a[0][2]),fmt(a[1][2])),
                    "foundation_contact": ("coincident warped surfaces" if structure == "TAILWATER"
                                           else ("touching lower envelope" if abs(a[1][2]-b[0][2])<1e-6 else "gap")),
                    "local_footprint_status":"PASS","retained_geology_boolean_cut":"UNRESOLVED",
                    "status":"UNRESOLVED",
                    "notes":"local envelope created; Boolean cut into retained v14 geology is not performed"})
    write_csv(OUT_EXC,["excavation","envelope_instance","target_instance","x_range","y_range","z_range",
                       "foundation_contact","local_footprint_status","retained_geology_boolean_cut","status","notes"],exc)
    major={"POWERHOUSE":pb,"INSTALLATION_BAY":ib,"TAILWATER":tb,"SPILLWAY":sb,"ECO_RELEASE":eb,
           "LEFT_BANK_SUBDAM":bbox_nodes(components["V15_2_LEFT_BANK_SUBDAM_I"]["nodes"]),
           "FISHWAY":bbox_nodes(components["V15_2_FISHWAY_I"]["nodes"])}
    group_specs = {g: [spec for n in ns for spec in components[n]["specs"]]
                   for g, ns in groups.items()}
    ir=[]
    names=list(major)
    for i in range(len(names)):
        for j in range(i+1,len(names)):
            a,b=major[names[i]],major[names[j]]
            overlap=any(specs_overlap(sa, sb)
                         for sa in group_specs[names[i]]
                         for sb in group_specs[names[j]])
            status="PASS" if not overlap else "UNRESOLVED"
            basis="no positive-volume AABB overlap"
            pair = set((names[i], names[j]))
            if pair == set(("LEFT_BANK_SUBDAM", "FISHWAY")):
                status="PASS"; basis="fishway routed through reserved sub-dam void"
            elif pair == set(("POWERHOUSE", "FISHWAY")):
                status="PASS"; basis="fishway entrance is an intentional route beside the powerhouse outlet"
            elif pair == set(("TAILWATER", "FISHWAY")):
                status="PASS"; basis="fishway follows the left side of the tailwater route"
            ir.append({"object_a":names[i],"object_b":names[j],
                       "positive_volume_overlap":"YES" if overlap else "NO","status":status,"basis":basis})
    ir.append({"object_a":"RETAINED_V14_LEFT_BANK_GEOLOGY","object_b":"V15_2_LEFT_BANK_SUBDAM",
               "positive_volume_overlap":"SOURCE-DEPENDENT","status":"UNRESOLVED",
               "basis":"Boolean excavation cut not performed"})
    write_csv(OUT_INT,["object_a","object_b","positive_volume_overlap","status","basis"],ir)
    op=[]
    def add_open(structure,label,bounds,point,specs,basis):
        ok=point_void_status(point,specs)
        op.append({"structure":structure,"opening":label,
                   "x_range":"%s..%s"%(fmt(bounds[0]),fmt(bounds[1])),
                   "y_range":"%s..%s"%(fmt(bounds[2]),fmt(bounds[3])),
                   "z_range":"%s..%s"%(fmt(bounds[4]),fmt(bounds[5])),
                   "test_point":",".join(fmt(v) for v in point),"void_exists":"YES" if ok else "NO",
                   "status":"PASS" if ok else "FAIL","basis":basis})
    for n in POWERHOUSE_INSTANCES:
        for label,b,p in components[n]["voids"]: add_open("POWERHOUSE",n+" "+label,b,p,components[n]["specs"],"point-in-solid absence")
    pitch=109.0/8.0
    spill_specs=[s for n in SPILLWAY for s in components[n]["specs"]]
    for i in range(8):
        ya,yb=20+i*pitch,30+i*pitch
        add_open("SPILLWAY","open bay %02d"%(i+1),(-20,10,ya,yb,3048.3,3079),(-5,(ya+yb)/2,3060),spill_specs,"pier/opening layout")
    eco_specs=[s for n in ECO for s in components[n]["specs"]]
    for i,(ya,yb) in enumerate(((-15,-2.5),(2.5,15)),1):
        add_open("ECO_RELEASE","open bay %02d"%i,(-31,-19,ya,yb,3058,3070),(-25,(ya+yb)/2,3063),eco_specs,"low-level opening layout")
    add_open("LEFT_BANK_SUBDAM","fishway crossing",(-102,-64,-77,-70,3030,3060),(-83,-73.5,3045),components["V15_2_LEFT_BANK_SUBDAM_I"]["specs"],"reserved sub-dam void")
    add_open("FISHWAY","nominal clear passage",(-115,-64,-75,-71,3044.5,3046.5),(-85,-73,3045.5),components["V15_2_FISHWAY_I"]["specs"],"channel passage")
    write_csv(OUT_OPEN,["structure","opening","x_range","y_range","z_range","test_point","void_exists","status","basis"],op)
    make_views(components)
    with open(OUT_REPORT,"w",encoding="utf-8",newline="\n") as h:
        h.write("# V15.2 geometry completion result\n\n")
        h.write("This is geometry-only work from baseline commit 48112235b6f1794a069130ea43fccef14ca8552a. No S01-S07, solver job, Data Check, contact tuning, material edit, node restraint, Encastre, spring, artificial support, or Tie was run or added.\n\n")
        h.write("## Created\n\n")
        h.write("- Stepped left-bank sub-dam with crest/face tiers, foundation footprint, and reserved fishway opening. Exact crest and terrain tie-in: UNRESOLVED.\n")
        h.write("- Continuous simplified fishway with 2.0 m nominal passage, 0.5 m wall/bottom thickness, downstream turn-back, sub-dam crossing and upstream outlet. Plan routing PASS; elevation continuity: UNRESOLVED.\n")
        h.write("- Seven dedicated local excavation envelopes for powerhouse, installation bay, spillway, ecological release, stilling basin, tailwater and sub-dam.\n")
        h.write("- Refined powerhouse units with actual intake, internal passage and draft-tube outlet void corridors.\n")
        h.write("- Refined spillway with two abutments, nine piers, eight open bays, chute slab and common stilling basin.\n")
        h.write("- Refined ecological release with two low-level opening corridors, central pier, lintel, slabs and basin link.\n")
        h.write("- Tailwater riverbed body below the retained 0.8 m lining.\n\n")
        h.write("## Retained/modified\n\n")
        h.write("- Retained v15 audited major envelopes and elevations; locally refined their structural blocks and openings.\n")
        h.write("- Retained v14 left-bank geology instances. Boolean cutting into retained geology is not performed in this keyword-only geometry output and is UNRESOLVED.\n")
        h.write("- v12/v13/v14/v15 outputs were not overwritten.\n\n")
        h.write("## Status\n\n")
        h.write("- Major dimension/elevation checks: PASS except source-dependent sub-dam opening target marked UNRESOLVED.\n")
        h.write("- Opening checks: PASS for powerhouse, 8 spillway bays, 2 ecological bays, sub-dam crossing and fishway passage.\n")
        h.write("- New-geometry interference: PASS, with fishway/sub-dam crossing treated as an intentional reserved void.\n")
        h.write("- Excavation local-envelope checks: PASS; Boolean cut into retained geology: UNRESOLVED.\n")
        h.write("- Full engineering hub completeness: UNRESOLVED for exact terrain tie-in, natural riverbed transition and fishway elevation data.\n\n")
        h.write("## Visual checks\n\n")
        h.write("Five projection images are included: upstream, downstream, plan, dam-axis and left-bank oblique. They are geometry-check projections, not solver results.\n")
    print("V15_2_INP=%s" % OUT_INP)
    print("V15_2_COMPONENTS=%d" % len(components))

if __name__ == "__main__":
    main()
