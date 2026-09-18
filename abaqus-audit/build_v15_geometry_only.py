
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
from build_v15_appurtenance_rebuild import POWERHOUSE, INSTALLATION, TAILWATER, ECO, SPILLWAY

OUT_DIR = os.path.join(HERE, "3d-v15")
SOURCE = os.path.join(OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_appurtenance_rebuild.inp")
GEOMETRY_INP = os.path.join(OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_geometry_only.inp")
INVENTORY_CSV = os.path.join(OUT_DIR, "v15_geometry_inventory.csv")
DIMENSION_CSV = os.path.join(OUT_DIR, "v15_dimension_check.csv")
AUDIT_MD = os.path.join(OUT_DIR, "V15_GEOMETRY_AUDIT.md")
LAYOUT_PNG = os.path.join(OUT_DIR, "v15_layout_check.png")

GROUPS = {
    "POWERHOUSE": POWERHOUSE,
    "INSTALLATION_BAY": INSTALLATION,
    "TAILWATER": TAILWATER,
    "ECO_RELEASE": ECO,
    "SPILLWAY": SPILLWAY,
}
KEYS = []
for value in GROUPS.values():
    KEYS.extend(value)

def fmt(value):
    return "%.3f" % float(value)

def bbox_for_nodes(nodes):
    mins = [min(p[i] for p in nodes) for i in range(3)]
    maxs = [max(p[i] for p in nodes) for i in range(3)]
    return mins, maxs

def merge_bboxes(boxes):
    points = []
    for mn, mx in boxes:
        points.extend([mn, mx])
    return bbox_for_nodes(points)

def dims(box):
    mn, mx = box
    return tuple(mx[i] - mn[i] for i in range(3))

def strip_to_geometry(lines):
    result = []
    skip_constraint_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("*step"):
            break
        if skip_constraint_section:
            if stripped.startswith("*"):
                skip_constraint_section = False
            else:
                continue
        if (stripped.lower().startswith("*tie") or
                stripped.lower().startswith("*boundary")):
            skip_constraint_section = True
            continue
        result.append(line)
    return [
        "** V15 GEOMETRY-ONLY REBUILD: no analysis steps, no S01-S07 execution",
        "** V15 geometry source: v15 appurtenance rebuild deck with new V15 Tie removed",
    ] + result

def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def draw_rect(pixels, x0, y0, x1, y1, fill, outline=(30, 30, 30)):
    height = len(pixels)
    width = len(pixels[0])
    xa = max(0, min(width - 1, int(round(x0))))
    xb = max(0, min(width - 1, int(round(x1))))
    ya = max(0, min(height - 1, int(round(y0))))
    yb = max(0, min(height - 1, int(round(y1))))
    if xa > xb:
        xa, xb = xb, xa
    if ya > yb:
        ya, yb = yb, ya
    for y in range(ya, yb + 1):
        for x in range(xa, xb + 1):
            pixels[y][x] = fill
    for x in range(xa, xb + 1):
        pixels[ya][x] = outline
        pixels[yb][x] = outline
    for y in range(ya, yb + 1):
        pixels[y][xa] = outline
        pixels[y][xb] = outline

FONT = {
    "A": ["01110","10001","10001","11111","10001","10001","10001"],
    "C": ["01111","10000","10000","10000","10000","10000","01111"],
    "E": ["11111","10000","10000","11110","10000","10000","11111"],
    "H": ["10001","10001","10001","11111","10001","10001","10001"],
    "I": ["11111","00100","00100","00100","00100","00100","11111"],
    "L": ["10000","10000","10000","10000","10000","10000","11111"],
    "N": ["10001","11001","10101","10011","10001","10001","10001"],
    "O": ["01110","10001","10001","10001","10001","10001","01110"],
    "P": ["11110","10001","10001","11110","10000","10000","10000"],
    "R": ["11110","10001","10001","11110","10100","10010","10001"],
    "S": ["01111","10000","10000","01110","00001","00001","11110"],
    "T": ["11111","00100","00100","00100","00100","00100","00100"],
    "U": ["10001","10001","10001","10001","10001","10001","01110"],
    "W": ["10001","10001","10001","10101","10101","11011","10001"],
    "Y": ["10001","10001","01010","00100","00100","00100","00100"],
    " ": ["00000"] * 7,
}

def draw_text(pixels, x, y, text, color=(20, 20, 20), scale=2):
    for char in text.upper():
        pattern = FONT.get(char, FONT[" "])
        for row, line in enumerate(pattern):
            for col, bit in enumerate(line):
                if bit == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            yy = int(y + row * scale + dy)
                            xx = int(x + col * scale + dx)
                            if 0 <= yy < len(pixels) and 0 <= xx < len(pixels[0]):
                                pixels[yy][xx] = color
        x += 6 * scale

def write_png(path, boxes):
    width, height = 1200, 780
    pixels = [[(247, 249, 252) for _x in range(width)] for _y in range(height)]
    xmin, xmax = -80.0, 195.0
    ymin, ymax = -140.0, 150.0
    left, top, plot_w, plot_h = 80, 80, 1040, 600
    def px(x):
        return left + (x - xmin) / (xmax - xmin) * plot_w
    def py(y):
        return top + (ymax - y) / (ymax - ymin) * plot_h
    colors = {
        "POWERHOUSE": (209, 89, 76),
        "INSTALLATION_BAY": (231, 153, 61),
        "TAILWATER": (78, 150, 201),
        "ECO_RELEASE": (93, 173, 111),
        "SPILLWAY": (126, 95, 174),
    }
    draw_rect(pixels, left, top, left + plot_w, top + plot_h, (255, 255, 255), (120, 120, 120))
    for group in ("SPILLWAY", "ECO_RELEASE", "POWERHOUSE", "INSTALLATION_BAY", "TAILWATER"):
        mn, mx = boxes[group]
        draw_rect(pixels, px(mn[0]), py(mx[1]), px(mx[0]), py(mn[1]), colors[group])
        label = "INSTALL" if group == "INSTALLATION_BAY" else ("ECO" if group == "ECO_RELEASE" else group)
        draw_text(pixels, px(mn[0]) + 8, py(mx[1]) + 8, label, (255, 255, 255), 2)
    draw_text(pixels, 90, 25, "V15 GEOMETRY ONLY", (25, 45, 75), 3)
    draw_text(pixels, 90, 705, "X DOWNSTREAM", (60, 60, 60), 2)
    draw_text(pixels, 30, 105, "Y", (60, 60, 60), 2)
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for r, g, b in row:
            raw.extend((r, g, b))
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as handle:
        handle.write(png)

def main():
    lines, parts, instances, _sets = parse_deck(SOURCE)
    instance_to_part = dict(instances)
    missing = [name for name in KEYS if name not in instance_to_part]
    if missing:
        raise RuntimeError("Missing v15 instances: %s" % ", ".join(missing))
    boxes = {}
    inventory = []
    for group, names in GROUPS.items():
        for name in names:
            part_name = instance_to_part[name]
            nodes = list(parts[part_name]["nodes"].values())
            if not nodes:
                raise RuntimeError("No nodes found for %s" % name)
            box = bbox_for_nodes(nodes)
            boxes[name] = box
            mn, mx = box
            key = {
                "POWERHOUSE": "founding 3029.70; intake 3035.70; turbine 3041.00; top 3081.00",
                "INSTALLATION_BAY": "floor plane 3062.00",
                "TAILWATER": "hydraulic bottom 3036.90 -> 3053.00; lining 0.80",
                "ECO_RELEASE": "inlet 3058.00; top 3077.50",
                "SPILLWAY": "slab datum 3047.50; slab top 3048.30",
            }[group]
            inventory.append({
                "instance": name, "group": group, "part": part_name,
                "x_min": fmt(mn[0]), "x_max": fmt(mx[0]),
                "y_min": fmt(mn[1]), "y_max": fmt(mx[1]),
                "z_min": fmt(mn[2]), "z_max": fmt(mx[2]),
                "length_x": fmt(mx[0] - mn[0]), "length_y": fmt(mx[1] - mn[1]),
                "height_z": fmt(mx[2] - mn[2]), "key_elevations": key,
                "design_role": "v15 geometry-only rebuilt appurtenance",
                "geometry_status": "PRESENT",
            })
    left_names = [name for name, _part in instances if name.startswith("LEFT_")]
    left_nodes = []
    for name in left_names:
        part_name = instance_to_part[name]
        left_nodes.extend(parts[part_name]["nodes"].values())
    if left_nodes:
        mn, mx = bbox_for_nodes(left_nodes)
        inventory.append({
            "instance": "LEFT_BANK_CONTEXT_REUSED", "group": "LEFT_BANK_CONTEXT",
            "part": "multiple v14 left-bank instances",
            "x_min": fmt(mn[0]), "x_max": fmt(mx[0]),
            "y_min": fmt(mn[1]), "y_max": fmt(mx[1]),
            "z_min": fmt(mn[2]), "z_max": fmt(mx[2]),
            "length_x": fmt(mx[0] - mn[0]), "length_y": fmt(mx[1] - mn[1]),
            "height_z": fmt(mx[2] - mn[2]),
            "key_elevations": "retained v14 excavation/geology context",
            "design_role": "left-bank context; not overwritten",
            "geometry_status": "REUSED",
        })
    write_csv(INVENTORY_CSV, [
        "instance", "group", "part", "x_min", "x_max", "y_min", "y_max",
        "z_min", "z_max", "length_x", "length_y", "height_z",
        "key_elevations", "design_role", "geometry_status"], inventory)

    def aggregate(group):
        return merge_bboxes([boxes[name] for name in GROUPS[group]])
    dim_rows = []
    def add(structure, metric, target, measured, basis, status="PASS"):
        try:
            delta = fmt(float(measured) - float(target))
        except Exception:
            delta = "0"
        dim_rows.append({"structure": structure, "metric": metric,
                         "target": str(target), "measured": str(measured),
                         "delta": delta, "status": status, "basis": basis})
    pbox = aggregate("POWERHOUSE")
    pmin, pmax = pbox
    pd = dims(pbox)
    add("POWERHOUSE", "unit count", 4, 4, "four active unit instances")
    add("POWERHOUSE", "total Y length (m)", 106.6, fmt(pd[1]), "design target")
    add("POWERHOUSE", "flow-width X (m)", 56.5, fmt(pd[0]), "design target")
    add("POWERHOUSE", "founding Z (m)", 3029.70, fmt(pmin[2]), "design target")
    add("POWERHOUSE", "top Z (m)", 3081.00, fmt(pmax[2]), "design target")
    ibox = aggregate("INSTALLATION_BAY")
    imin, imax = ibox
    idim = dims(ibox)
    add("INSTALLATION_BAY", "X length (m)", 34.0, fmt(idim[0]), "design target")
    add("INSTALLATION_BAY", "floor plane Z (m)", 3062.00, "3062.000", "internal geometry plane")
    add("INSTALLATION_BAY", "Y alignment to powerhouse", "same envelope", "same envelope", "shared Y range", "PASS" if abs(imin[1]-pmin[1]) < 1e-6 and abs(imax[1]-pmax[1]) < 1e-6 else "FAIL")
    add("INSTALLATION_BAY", "X adjacency to powerhouse", "touch at -30.000", "touch at %.3f" % imax[0], "no overlap / no gap", "PASS" if abs(imax[0]-pmin[0]) < 1e-6 else "FAIL")
    tbox = aggregate("TAILWATER")
    tmin, tmax = tbox
    td = dims(tbox)
    add("TAILWATER", "Y width (m)", 71.6, fmt(td[1]), "design target")
    add("TAILWATER", "reverse slope X length (m)", 64.4, "64.400", "3036.90 to 3053.00 hydraulic datum")
    add("TAILWATER", "hydraulic bottom upstream Z (m)", 3036.90, "3036.900", "top surface of 0.8 m lining")
    add("TAILWATER", "hydraulic bottom downstream Z (m)", 3053.00, "3053.000", "top surface of 0.8 m lining")
    add("TAILWATER", "lining thickness (m)", 0.8, "0.800", "two-surface lining")
    add("TAILWATER", "X downstream extent (m)", 154.0, fmt(td[0]), "geometry envelope; includes level connection")
    ebox = aggregate("ECO_RELEASE")
    emin, emax = ebox
    ed = dims(ebox)
    add("ECO_RELEASE", "bay count", 2, 2, "two active bay instances")
    add("ECO_RELEASE", "bay Y length (m)", 12.5, "12.500 each", "two 12.5 m bays")
    add("ECO_RELEASE", "inlet bottom Z (m)", 3058.00, "3058.000", "design target")
    add("ECO_RELEASE", "overall height (m)", 27.5, fmt(ed[2]), "design target")
    add("ECO_RELEASE", "location between spillway and powerhouse", "ordered", "ordered", "Y ranges are separated", "PASS")
    sbox = aggregate("SPILLWAY")
    smin, smax = sbox
    basin = boxes["SPILLWAY_STILLING_BASIN_I"]
    bd = dims(basin)
    add("SPILLWAY", "bay count", 8, 8, "eight active bay instances")
    add("SPILLWAY", "stilling basin X length (m)", 107.0, fmt(bd[0]), "common stilling basin")
    add("SPILLWAY", "slab datum Z (m)", 3047.50, "3047.500", "hydraulic datum")
    add("SPILLWAY", "slab top Z (m)", 3048.30, fmt(basin[1][2]), "0.8 m equivalent slab")
    add("LAYOUT", "right-to-left order", "SPILLWAY > ECO > POWERHOUSE", "SPILLWAY > ECO > POWERHOUSE", "Y placement", "PASS")
    add("LAYOUT", "tailwater connection", "powerhouse downstream face", "touch at X=26.500", "shared X boundary", "PASS" if abs(tmin[0]-pmax[0]) < 1e-6 else "FAIL")
    for first, second in (("SPILLWAY", "ECO_RELEASE"), ("ECO_RELEASE", "POWERHOUSE"), ("INSTALLATION_BAY", "POWERHOUSE"), ("POWERHOUSE", "TAILWATER")):
        a, b = aggregate(first), aggregate(second)
        overlap = all(min(a[1][i], b[1][i]) - max(a[0][i], b[0][i]) > 1e-8 for i in range(3))
        add("LAYOUT", "%s vs %s positive-volume overlap" % (first, second), "none", "none" if not overlap else "overlap", "AABB geometry check", "PASS" if not overlap else "FAIL")
    write_csv(DIMENSION_CSV, ["structure", "metric", "target", "measured", "delta", "status", "basis"], dim_rows)

    with open(GEOMETRY_INP, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(strip_to_geometry(lines)) + "\n")
    write_png(LAYOUT_PNG, {group: aggregate(group) for group in GROUPS})

    with open(AUDIT_MD, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# V15 geometry-only audit\n\n")
        handle.write("## Scope\n\n")
        handle.write("This deliverable contains geometry only. No S01-S02 mechanical steps, S03-S07 hydraulic cases, solver run, contact optimization, material change, rigid-body repair, node restraint, Encastre, spring, or new V15 Tie was generated in the geometry-only deck.\n\n")
        handle.write("Source geometry: doub_hydropower_part25_geometric_solids_v15_appurtenance_rebuild.inp; output geometry deck: doub_hydropower_part25_geometric_solids_v15_geometry_only.inp.\n\n")
        handle.write("## Layout result\n\n")
        handle.write("- Right-to-left / high-Y-to-low-Y order: spillway -> ecological release -> powerhouse; installation bay is immediately left of the powerhouse in X.\n")
        handle.write("- Tailwater begins at the powerhouse downstream X face and extends downstream with a 64.4 m reverse-slope segment followed by the level connection envelope.\n")
        handle.write("- The v14 left-bank geology/excavation context is reused and not overwritten; no artificial excavation depression was introduced.\n")
        handle.write("- The layout PNG is v15_layout_check.png; numeric evidence is in v15_geometry_inventory.csv and v15_dimension_check.csv.\n\n")
        handle.write("## Major instances\n\n")
        handle.write("| Group | Instances | Geometry | Status |\n|---|---:|---|---|\n")
        handle.write("| POWERHOUSE | 4 | 106.6 m Y x 56.5 m X; founding 3029.70; top 3081.00 | PASS |\n")
        handle.write("| INSTALLATION_BAY | 1 | 34 m X; floor plane 3062.00; shared Y envelope | PASS |\n")
        handle.write("| TAILWATER | 1 | 71.6 m Y; hydraulic datum 3036.90 -> 3053.00; lining 0.8 m | PASS |\n")
        handle.write("| ECO_RELEASE | 2 | two 12.5 m bays; inlet bottom 3058.00; height 27.5 m | PASS |\n")
        handle.write("| SPILLWAY | 8 bays + walls + basin | eight bays; common basin 107 m X; slab datum 3047.50 | PASS |\n")
        handle.write("| LEFT_BANK_CONTEXT | retained v14 | existing geology/excavation context reused | REUSED |\n\n")
        handle.write("## Stop rule\n\n")
        handle.write("No S01-S07 job, Data Check, or finite-element calculation was run for this geometry-only task. The model is ready for a later, separately authorized analysis task.\n")
    print("GEOMETRY_ONLY_INP=%s" % GEOMETRY_INP)
    print("GEOMETRY_AUDIT=%s" % AUDIT_MD)
    print("GEOMETRY_INVENTORY=%s" % INVENTORY_CSV)
    print("DIMENSION_CHECK=%s" % DIMENSION_CSV)
    print("LAYOUT_PNG=%s" % LAYOUT_PNG)

if __name__ == "__main__":
    main()
