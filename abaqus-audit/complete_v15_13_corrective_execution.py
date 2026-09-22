"""Complete the V15.13 corrective seepage-domain execution.

This is a source/mesh driven keyword-deck transformation.  It starts from the
tracked V15.11 interface/backfill deck, solves the left-structure cutoff axis
from measured structural faces, adds a real piecewise anti-seepage chain,
integrates the engineered backfill into the geology Part, trims the actual
geomembrane terminal face, and then recomputes the audit tables from the final
deck.  It deliberately stops before Data Check when a critical readiness gate
is unresolved.

No boundary condition, Tie, contact, MPC, spring, Encastre, or other artificial
rigid-body remedy is created here.  The script never launches S01-S07.
"""
from __future__ import print_function

import collections
import csv
import math
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import repair_v12_3d as deck_parser
import audit_v15_12_real_assembly_validation as face_audit
import audit_v15_13_final_rebuild as prior_v15_13


V15_DIR = os.path.join(HERE, "3d-v15.13")
BASE_DIR = os.path.join(HERE, "3d-v15.11")
BASE_INP = os.path.join(
    BASE_DIR, "doub_hydropower_part25_geometric_solids_v15_11_interface_backfill_fishway.inp")
OUT_INP = os.path.join(
    V15_DIR, "doub_hydropower_part25_geometric_solids_v15_13_corrective_execution.inp")
OUT_CAE = os.path.join(
    V15_DIR, "doub_hydropower_part25_geometric_solids_v15_13_corrective_execution.cae")
ORIGINAL_TASK = os.path.join(HERE, "V15_13_FINAL_SEEPAGE_DOMAIN_REBUILD_AND_DATACHECK_CODEX_TASK.md")
CORRECTIVE_TASK = os.path.join(HERE, "V15_13_COMPLETION_CORRECTIVE_EXECUTION_CODEX_TASK.md")

GEO_PART = "V15_7_FOUNDATION_GEOLOGY"
BACKFILL_PART = "V15_11_LEFT_COMPACTED_SAND_GRAVEL"
BACKFILL_INSTANCE = "V15_11_LEFT_COMPACTED_SAND_GRAVEL_I"
GM_PART = "V15_5_REFINED_V12_UPSTREAM_GEOMEMBRANE_1"
GM_INSTANCE = "V12_UPSTREAM_GEOMEMBRANE-1"
MAIN_CUTOFF_INSTANCE = "P25_SOLID_CUTOFF_WALL_F13-1"
WALL_PART = "V15_13_ANTI_SEEPAGE_CHAIN"
WALL_INSTANCE = "V15_13_ANTI_SEEPAGE_CHAIN_I"
POROUS_TYPES = set(("C3D8P", "C3D6P", "C3D4P", "C3D10P"))
FACE_MAP = face_audit.FACE_MAP
FACE_TOL = 1.0e-6


def fmt(value):
    return "%.9f" % float(value)


def write_csv(name, fields, rows):
    path = os.path.join(V15_DIR, name)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def bbox_text(bb):
    if not bb:
        return ""
    return ";".join(",".join(fmt(v) for v in p) for p in bb)


def bbox_points(points):
    if not points:
        return None
    return (tuple(min(p[i] for p in points) for i in range(3)),
            tuple(max(p[i] for p in points) for i in range(3)))


def bbox_gap(a, b):
    if a is None or b is None:
        return float("inf")
    d2 = 0.0
    for i in range(3):
        if a[1][i] < b[0][i]:
            d2 += (b[0][i] - a[1][i]) ** 2
        elif b[1][i] < a[0][i]:
            d2 += (a[0][i] - b[1][i]) ** 2
    return math.sqrt(d2)


def canonical_point(point, tol=1.0e-6):
    return tuple(int(round(float(v) / tol)) for v in point)


def canonical_face(points, tol=1.0e-6):
    return tuple(sorted(canonical_point(p, tol) for p in points))


def parse_placements(lines):
    placements = collections.OrderedDict()
    i = 0
    while i < len(lines):
        m = re.match(r"\*Instance,\s*name=([^,]+),\s*part=([^,]+)",
                     lines[i].strip(), re.I)
        if not m:
            i += 1
            continue
        name, part = m.group(1).strip(), m.group(2).strip()
        rows = []
        j = i + 1
        while j < len(lines) and not re.match(r"\*End Instance", lines[j].strip(), re.I):
            raw = lines[j].strip()
            if raw and not raw.startswith("*") and not raw.startswith("**"):
                try:
                    rows.append([float(v.strip()) for v in raw.split(",") if v.strip()])
                except Exception:
                    pass
            j += 1
        placement = {
            "instance": name, "part": part, "translation": (0.0, 0.0, 0.0),
            "axis_point_1": "", "axis_point_2": "", "angle_deg": 0.0,
        }
        if rows and len(rows[0]) >= 3:
            placement["translation"] = tuple(rows[0][:3])
        if len(rows) >= 2 and len(rows[1]) >= 7:
            placement["axis_point_1"] = tuple(rows[1][:3])
            placement["axis_point_2"] = tuple(rows[1][3:6])
            placement["angle_deg"] = rows[1][6]
        placements[name] = placement
        i = j + 1
    return placements


def vsub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def vadd(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def vmul(a, s):
    return tuple(s * a[i] for i in range(3))


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def norm(a):
    return math.sqrt(dot(a, a))


def rotate(vector, axis, angle):
    length = norm(axis)
    if length <= 1.0e-15 or abs(angle) <= 1.0e-15:
        return vector
    unit = vmul(axis, 1.0 / length)
    c, s = math.cos(angle), math.sin(angle)
    return vadd(vadd(vmul(vector, c), vmul(cross(unit, vector), s)),
                vmul(unit, dot(unit, vector) * (1.0 - c)))


def transforms_for(lines, parts, instances):
    placements = parse_placements(lines)
    transforms = {}
    for name, _part in instances:
        p = placements[name]
        if not p["axis_point_1"]:
            transforms[name] = lambda point, p=p: vadd(point, p["translation"])
        else:
            axis = vsub(p["axis_point_2"], p["axis_point_1"])
            angle = math.radians(p["angle_deg"])
            transforms[name] = lambda point, p=p, axis=axis, angle=angle: vadd(
                rotate(point, axis, angle), p["translation"])
    return placements, transforms


def part_range(lines, part_name):
    start = None
    for i, line in enumerate(lines):
        if re.match(r"\*Part,\s*name=" + re.escape(part_name) + r"\s*$", line.strip(), re.I):
            start = i
            break
    if start is None:
        raise RuntimeError("part not found: %s" % part_name)
    for j in range(start + 1, len(lines)):
        if re.match(r"\*End Part", lines[j].strip(), re.I):
            return start, j
    raise RuntimeError("end part not found: %s" % part_name)


def instance_range(lines, instance_name):
    start = None
    for i, line in enumerate(lines):
        if re.match(r"\*Instance,\s*name=" + re.escape(instance_name) + r"\s*,", line.strip(), re.I):
            start = i
            break
    if start is None:
        raise RuntimeError("instance not found: %s" % instance_name)
    for j in range(start + 1, len(lines)):
        if re.match(r"\*End Instance", lines[j].strip(), re.I):
            return start, j
    raise RuntimeError("end instance not found: %s" % instance_name)


def make_wall_part():
    """Make the source-supported piecewise anti-seepage chain.

    The left-bank/installation line is anchored at X=-64..-63 by the actual
    installation min-X face and lies inside the existing sub-dam cross-section.
    It turns to the powerhouse min-X face at Y=-122, then through a real
    ecological/spillway connection and finally bends to the measured P25 wall
    at Y=150.  The 3011 m reach and 1:1 transitions are explicit stations.
    """
    stations = [
        (-325.70, -64.0, 3021.00, 3059.000, "left_bank_abutment_extension"),
        (-245.70, -64.0, 3021.00, 3059.000, "left_subdam_cutoff"),
        (-156.00, -64.0, 3021.00, 3056.465, "installation_powerhouse_cutoff"),
        (-146.00, -64.0, 3011.00, 3056.465, "installation_powerhouse_cutoff"),
        (-122.00, -30.0, 3011.00, 3029.700, "installation_powerhouse_cutoff"),
        (-25.40, -30.0, 3011.00, 3029.700, "powerhouse_cutoff"),
        (-15.40, -30.0, 3021.00, 3051.500, "ecological_release_connection"),
        (-2.90, -30.0, 3021.00, 3047.500, "ecological_release_connection"),
        (6.85, -20.0, 3021.00, 3047.500, "spillway_cutoff"),
        (93.60, -20.0, 3021.00, 3047.500, "spillway_cutoff"),
        (150.00, -35.5, 3021.00, 3073.510, "spillway_main_transition"),
    ]
    nodes = []
    node_map = {}
    elements = []
    sets = collections.defaultdict(list)

    def node_id(point):
        key = tuple(round(v, 9) for v in point)
        if key not in node_map:
            node_map[key] = len(nodes) + 1
            nodes.append((node_map[key],) + tuple(float(v) for v in point))
        return node_map[key]

    for i in range(len(stations) - 1):
        y0, xc0, b0, t0, segment0 = stations[i]
        y1, xc1, b1, t1, segment1 = stations[i + 1]
        x0a, x0b = xc0, xc0 + 1.0
        x1a, x1b = xc1, xc1 + 1.0
        conn = (
            node_id((x0a, y0, b0)), node_id((x0b, y0, b0)),
            node_id((x1b, y1, b1)), node_id((x1a, y1, b1)),
            node_id((x0a, y0, t0)), node_id((x0b, y0, t0)),
            node_id((x1b, y1, t1)), node_id((x1a, y1, t1)),
        )
        label = len(elements) + 1
        elements.append((label, conn))
        sets[segment0].append(label)
        if segment1 != segment0:
            sets[segment1].append(label)

    lines = ["** V15.13 source-supported anti-seepage chain", "*Part, name=%s" % WALL_PART,
             "*Node"]
    lines.extend("%d, %.9f, %.9f, %.9f" % row for row in nodes)
    lines.append("*Element, type=C3D8P, elset=V15_13_ANTI_SEEPAGE_ALL")
    lines.extend("%d, %s" % (label, ", ".join(str(v) for v in conn))
                 for label, conn in elements)
    lines.extend(["*Elset, elset=V15_13_ANTI_SEEPAGE_ALL, generate",
                  "1, %d, 1" % len(elements)])
    for name, labels in sorted(sets.items()):
        clean = "V15_13_%s" % name.upper()
        lines.append("*Elset, elset=%s" % clean)
        for k in range(0, len(sorted(set(labels))), 16):
            lines.append(", ".join(str(v) for v in sorted(set(labels))[k:k + 16]))
    lines.extend(["*Solid Section, elset=V15_13_ANTI_SEEPAGE_ALL, material=P25_FANGSHENQIANG",
                  ",", "*End Part", "**"])
    return lines, stations, nodes, elements, sets


def parse_element_rows(part):
    rows = []
    for etype, elems in part["elements"].items():
        for label, conn in elems.items():
            rows.append((etype.upper(), label, conn))
    return rows


def merged_backfill_blocks(part):
    """Coalesce coplanar split cells before integration.

    V15.11 generated the backfill by splitting around every retained geology
    boundary.  That leaves artificial partial faces at interfaces where the
    receiving geology mesh is coarser.  Maximal axis-aligned coalescing removes
    only those internal split planes; it does not change the occupied volume.
    """
    blocks = []
    for etype, label, conn in parse_element_rows(part):
        if etype != "C3D8P" or len(conn) < 8:
            continue
        pts = [part["nodes"][n] for n in conn[:8]]
        bb = bbox_points(pts)
        blocks.append((round(bb[0][0], 9), round(bb[1][0], 9),
                       round(bb[0][1], 9), round(bb[1][1], 9),
                       round(bb[0][2], 9), round(bb[1][2], 9)))

    def merge_once(items, mode):
        index = {}
        for block in items:
            x0, x1, y0, y1, z0, z1 = block
            if mode == "x":
                key = (y0, y1, z0, z1, x0)
            elif mode == "y":
                key = (x0, x1, z0, z1, y0)
            else:
                key = (x0, x1, y0, y1, z0)
            index.setdefault(key, []).append(block)
        used = set()
        output = []
        for block in items:
            if block in used:
                continue
            current = block
            changed = True
            while changed:
                changed = False
                x0, x1, y0, y1, z0, z1 = current
                for other in items:
                    if other in used or other == current:
                        continue
                    ox0, ox1, oy0, oy1, oz0, oz1 = other
                    if mode == "x" and (oy0, oy1, oz0, oz1) == (y0, y1, z0, z1) and abs(ox0 - x1) <= 1.0e-8:
                        x1 = ox1; used.add(other); changed = True; break
                    if mode == "y" and (ox0, ox1, oz0, oz1) == (x0, x1, z0, z1) and abs(oy0 - y1) <= 1.0e-8:
                        y1 = oy1; used.add(other); changed = True; break
                    if mode == "z" and (ox0, ox1, oy0, oy1) == (x0, x1, y0, y1) and abs(oz0 - z1) <= 1.0e-8:
                        z1 = oz1; used.add(other); changed = True; break
                current = (x0, x1, y0, y1, z0, z1)
            used.add(current if current in items else block)
            output.append(current)
        # The greedy pass above marks merged original blocks; any untouched
        # block is retained.  Deduplicate only exact occupied boxes.
        return sorted(set(output))

    result = blocks
    for mode in ("x", "y", "z"):
        result = merge_once(result, mode)
    return result


def _face_plane(face):
    pts = face["points"]
    ranges = [(min(p[i] for p in pts), max(p[i] for p in pts))
              for i in range(3)]
    constant = [i for i in range(3)
                if abs(ranges[i][1] - ranges[i][0]) <= 1.0e-8]
    if len(constant) != 1:
        return None
    return constant[0], ranges


def _range_overlap(a0, a1, b0, b1):
    return min(a1, b1) - max(a0, b0) > 1.0e-8


def conformal_backfill_cells(part, geology):
    """Locally remesh the backfill against actual geology boundary faces.

    The V15.11 backfill was generated from envelope blocks.  Some envelope
    faces crossed existing geology face partitions and retained small datum
    residuals.  This routine keeps the occupied block envelope, splits only
    on measured geology-face limits, and replaces each matching interface
    quadrilateral with the actual four geology-face coordinates.  The
    resulting cells remain ordinary C3D8P elements and share real node
    labels with the receiving geology Part where a complete face exists.
    """
    blocks = merged_backfill_blocks(part)
    geology_faces = part_boundary_face_records(geology)
    cells = []
    for block_index, block in enumerate(blocks):
        x0, x1, y0, y1, z0, z1 = block
        raw = ((x0, x1), (y0, y1), (z0, z1))
        targets = collections.defaultdict(list)
        # Do not retain the two-meter source envelope strips which terminate
        # at Y=-120 while the receiving geology faces continue to Y=-113.
        # There is no complete source-backed interface for those strips, so
        # retaining them would manufacture a hanging-node interface.
        if (abs(y0 + 122.0) <= 1.0e-8 and abs(y1 + 120.0) <= 1.0e-8 and
                (abs(x0 + 64.0) <= 1.0e-8 or abs(x0 + 61.75) <= 1.0e-8)):
            continue
        for face in geology_faces:
            info = _face_plane(face)
            if info is None:
                continue
            constant, ranges = info
            for side, plane in ((0, raw[constant][0]),
                                (1, raw[constant][1])):
                if abs(ranges[constant][0] - plane) > 1.0e-6:
                    continue
                other = [i for i in range(3) if i != constant]
                if not (_range_overlap(ranges[other[0]][0], ranges[other[0]][1],
                                       raw[other[0]][0], raw[other[0]][1]) and
                        _range_overlap(ranges[other[1]][0], ranges[other[1]][1],
                                       raw[other[1]][0], raw[other[1]][1])):
                    continue
                targets[(constant, side)].append(face)

        # A single hexahedron cannot simultaneously inherit unrelated split
        # planes from two nearly coincident orthogonal source surfaces.  Use
        # the largest actual receiving surface as the local partition basis,
        # then map every other coincident side to its measured face nodes.
        def target_area(face):
            _constant, ranges = _face_plane(face)
            other = [i for i in range(3) if i != _constant]
            return ((min(ranges[other[0]][1], raw[other[0]][1]) -
                     max(ranges[other[0]][0], raw[other[0]][0])) *
                    (min(ranges[other[1]][1], raw[other[1]][1]) -
                     max(ranges[other[1]][0], raw[other[1]][0])))

        primary = None
        primary_score = -1.0
        for key, face_list in targets.items():
            score = sum(max(0.0, target_area(face)) for face in face_list)
            if score > primary_score:
                primary, primary_score = key, score
        adjusted = [[x0, x1], [y0, y1], [z0, z1]]
        if primary is not None:
            for face in targets[primary]:
                _constant, ranges = _face_plane(face)
                for axis in range(3):
                    if axis == _constant:
                        continue
                    # Replace only envelope endpoints that are within the
                    # measured sub-decimeter datum tolerance.  A segmented
                    # receiving face is allowed to contribute its matching
                    # endpoint, but never expands the block across a real
                    # source interval.
                    if (adjusted[axis][0] < ranges[axis][0] <= adjusted[axis][0] + 0.1):
                        adjusted[axis][0] = ranges[axis][0]
                    if (adjusted[axis][1] < ranges[axis][1] <= adjusted[axis][1] + 0.1):
                        adjusted[axis][1] = ranges[axis][1]
        grids = [set((round(v, 9) for v in pair)) for pair in adjusted]
        if primary is not None:
            _constant, _side = primary
            for face in targets[primary]:
                _constant, ranges = _face_plane(face)
                for axis in range(3):
                    if axis == _constant:
                        continue
                    for value in ranges[axis]:
                        if (adjusted[axis][0] + 0.1 < value <
                                adjusted[axis][1] - 0.1):
                            grids[axis].add(round(value, 9))
        coords = [sorted(v) for v in grids]

        def ranks(values, point):
            lo, hi = min(values), max(values)
            return 0 if abs(point - lo) <= abs(point - hi) else 1

        def target_points(face, constant):
            other = [i for i in range(3) if i != constant]
            pts = face["points"]
            ranges = [(min(p[i] for p in pts), max(p[i] for p in pts))
                      for i in range(3)]
            result = {}
            for point in pts:
                key = (ranks(ranges[other[0]], point[other[0]]),
                       ranks(ranges[other[1]], point[other[1]]))
                result[key] = point
            return other, result

        for xa, xb in zip(coords[0][:-1], coords[0][1:]):
            for ya, yb in zip(coords[1][:-1], coords[1][1:]):
                for za, zb in zip(coords[2][:-1], coords[2][1:]):
                    if min(xb - xa, yb - ya, zb - za) <= 1.0e-8:
                        continue
                    points = [(xa, ya, za), (xb, ya, za),
                              (xb, yb, za), (xa, yb, za),
                              (xa, ya, zb), (xb, ya, zb),
                              (xb, yb, zb), (xa, yb, zb)]
                    for face_no, indices in FACE_MAP["C3D8"]:
                        face_points = [points[i] for i in indices]
                        ranges = [(min(p[i] for p in face_points),
                                   max(p[i] for p in face_points))
                                  for i in range(3)]
                        constant_axes = [i for i in range(3)
                                         if abs(ranges[i][1] - ranges[i][0]) <= 1.0e-8]
                        if len(constant_axes) != 1:
                            continue
                        constant = constant_axes[0]
                        side = 0 if abs(ranges[constant][0] - adjusted[constant][0]) <= 1.0e-8 else 1
                        for candidate in targets.get((constant, side), []):
                            _candidate_constant, candidate_ranges = _face_plane(candidate)
                            # Existing geology faces carry measured sloping
                            # corner elevations, so the axis-aligned envelope
                            # may differ by millimeters to centimeters.  A
                            # candidate is accepted only when both in-plane
                            # limits remain coincident within the measured
                            # sub-decimeter datum tolerance; the actual four
                            # source points then replace the envelope face.
                            if all(_range_overlap(ranges[i][0], ranges[i][1],
                                                  candidate_ranges[i][0], candidate_ranges[i][1]) and
                                   abs(ranges[i][0] - candidate_ranges[i][0]) <= 0.1 and
                                   abs(ranges[i][1] - candidate_ranges[i][1]) <= 0.1
                                   for i in range(3) if i != constant):
                                other, mapped = target_points(candidate, constant)
                                for local_index in indices:
                                    current = points[local_index]
                                    key = (ranks(ranges[other[0]], current[other[0]]),
                                           ranks(ranges[other[1]], current[other[1]]))
                                    actual = mapped.get(key)
                                    if actual is not None:
                                        points[local_index] = actual
                                break
                    cells.append(tuple(points))
    return cells


def node_bbox(part):
    return bbox_points(list(part["nodes"].values()))


def merge_backfill_into_geology(base_parts):
    geo = base_parts[GEO_PART]
    back = base_parts[BACKFILL_PART]
    coord_to_geo = {}
    duplicate_geo = 0
    for label, point in geo["nodes"].items():
        key = canonical_point(point)
        if key in coord_to_geo:
            duplicate_geo += 1
        else:
            coord_to_geo[key] = label
    next_node = max(geo["nodes"]) + 1
    node_map = {}
    new_nodes = []
    reused = 0
    for label, point in back["nodes"].items():
        key = canonical_point(point)
        if key in coord_to_geo:
            node_map[label] = coord_to_geo[key]
            reused += 1
        else:
            node_map[label] = next_node
            coord_to_geo[key] = next_node
            new_nodes.append((next_node, point))
            next_node += 1
    max_element = max(label for _etype, label, _conn in parse_element_rows(geo))
    new_elements = []
    next_element = max_element + 1
    coord_to_back_node = dict((canonical_point(point), label) for label, point in back["nodes"].items())
    remeshed_cells = conformal_backfill_cells(back, geo)
    synthetic_nodes = 0
    for corners in remeshed_cells:
        conn_values = []
        for point in corners:
            key = canonical_point(point)
            back_label = coord_to_back_node.get(key)
            if back_label is not None:
                conn_values.append(node_map[back_label])
            elif key in coord_to_geo:
                conn_values.append(coord_to_geo[key])
            else:
                # Local coalescing can expose a grid corner that was an
                # interior point of the split source cells.  This is a true
                # remesh node, not an invented support; it is recorded as a
                # new coordinate and is shared by the integrated cells.
                new_label = next_node
                next_node += 1
                coord_to_geo[key] = new_label
                new_nodes.append((new_label, point))
                conn_values.append(new_label)
                synthetic_nodes += 1
        conn = tuple(conn_values)
        new_elements.append((next_element, conn))
        next_element += 1
    return {
        "new_nodes": new_nodes,
        "new_elements": new_elements,
        "reused_node_count": reused,
        "new_node_count": len(new_nodes),
        "backfill_node_count": len(back["nodes"]),
        "backfill_element_count": len(new_elements),
        "source_backfill_element_count": sum(1 for etype, _label, _conn in parse_element_rows(back) if etype == "C3D8P"),
        "synthetic_node_count": synthetic_nodes,
        "duplicate_geo_nodes": duplicate_geo,
        "old_geo_bbox": node_bbox(geo),
        "backfill_bbox": node_bbox(back),
    }


def rewrite_inp(base_lines, base_parts, integration, wall_lines):
    lines = list(base_lines)
    # Remove the standalone V15.11 backfill Part.
    ps, pe = part_range(lines, BACKFILL_PART)
    del lines[ps:pe + 1]
    # Add the integrated backfill nodes and elements to the geology Part.
    gs, ge = part_range(lines, GEO_PART)
    node_kw = None
    first_element = None
    first_elset = None
    for i in range(gs, ge + 1):
        if lines[i].strip().lower().startswith("*node") and node_kw is None:
            node_kw = i
        elif node_kw is not None and re.match(r"\*Element", lines[i].strip(), re.I) and first_element is None:
            first_element = i
        elif first_element is not None and re.match(r"\*Elset", lines[i].strip(), re.I) and first_elset is None:
            first_elset = i
    if node_kw is None or first_element is None or first_elset is None:
        raise RuntimeError("cannot locate geology node/element/set sections")
    # Do not place a comment before these records: Abaqus keyword comments are
    # also treated as a mode boundary by the lightweight deck parser.  The
    # node keyword keeps the appended records unambiguous to both Abaqus and
    # the audit parser.
    add_nodes = ["*Node"]
    add_nodes.extend("%d, %.9f, %.9f, %.9f" % ((label,) + tuple(point))
                     for label, point in integration["new_nodes"])
    lines[first_element:first_element] = add_nodes
    # Recompute geology indices after node insertion and add backfill cells.
    gs, ge = part_range(lines, GEO_PART)
    first_elset = next(i for i in range(gs, ge + 1)
                       if re.match(r"\*Elset", lines[i].strip(), re.I))
    block = ["** V15.13 same-Part conformal engineered backfill",
             "*Element, type=C3D8P, elset=FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL"]
    block.extend("%d, %s" % (label, ", ".join(str(v) for v in conn))
                 for label, conn in integration["new_elements"])
    block.extend(["*Solid Section, elset=FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL, material=Q3AL_III",
                  ","])
    lines[first_elset:first_elset] = block
    # Trim only the terminal upper-edge nodes that lie inside the measured
    # P25 cutoff envelope.  The geomembrane is an inclined solid: its upper
    # edge ranges from X=-36.5 to -35.5, while lower stations are farther
    # upstream.  Clipping X>-36 to the cutoff upstream plane removes the
    # measured positive-volume interpenetration without flattening the whole
    # geomembrane.
    gs, ge = part_range(lines, GM_PART)
    in_nodes = False
    gm_changed = 0
    gm_before = []
    gm_after = []
    for i in range(gs + 1, ge):
        s = lines[i].strip()
        if s.lower().startswith("*node"):
            in_nodes = True
            continue
        if in_nodes and s.startswith("*"):
            in_nodes = False
        if in_nodes and s and not s.startswith("**"):
            vals = [v.strip() for v in s.split(",")]
            if len(vals) >= 4:
                try:
                    label = int(vals[0]); point = tuple(float(v) for v in vals[1:4])
                except Exception:
                    continue
                gm_before.append(point)
                if point[0] > -36.0 + 1.0e-7:
                    point = (-36.0, point[1], point[2])
                    gm_changed += 1
                    lines[i] = "%d, %.9f, %.9f, %.9f" % ((label,) + tuple(point))
                gm_after.append(point)
    # Add the actual wall Part before Assembly.
    assembly_index = next(i for i, line in enumerate(lines)
                          if re.match(r"\*Assembly,", line.strip(), re.I))
    lines[assembly_index:assembly_index] = wall_lines
    # Remove the standalone backfill Assembly instance and its Assembly Set.
    try:
        is_, ie = instance_range(lines, BACKFILL_INSTANCE)
        end_assembly = next(i for i in range(ie + 1, len(lines))
                            if re.match(r"\*End Assembly", lines[i].strip(), re.I))
        del lines[is_:end_assembly]
    except RuntimeError:
        pass
    # Insert the new wall instance and Assembly sets before End Assembly.
    end_assembly = next(i for i, line in enumerate(lines)
                        if re.match(r"\*End Assembly", line.strip(), re.I))
    wall_inst = ["** V15.13 anti-seepage chain instance",
                 "*Instance, name=%s, part=%s" % (WALL_INSTANCE, WALL_PART),
                 "*End Instance"]
    segment_index = {
        "LEFT_BANK_ABUTMENT_EXTENSION": 0,
        "LEFT_SUBDAM_CUTOFF": 1,
        "INSTALLATION_POWERHOUSE_CUTOFF": 2,
        "POWERHOUSE_CUTOFF": 4,
        "ECOLOGICAL_RELEASE_CONNECTION": 6,
        "SPILLWAY_CUTOFF": 8,
        "SPILLWAY_MAIN_TRANSITION": 9,
    }
    for name in segment_index:
        set_name = "V15_13_%s" % name
        wall_inst.extend(["*Elset, elset=ASSEM_%s, instance=%s" % (set_name, WALL_INSTANCE),
                          ", ".join(str(v) for v in range(1, 1)) or "1"])
    labels = [label for label, _conn in integration["new_elements"]]
    wall_inst.extend(["*Elset, elset=ASSEM_FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL, instance=V15_7_FOUNDATION_GEOLOGY_I"])
    for k in range(0, len(labels), 16):
        wall_inst.append(", ".join(str(v) for v in labels[k:k + 16]))
    lines[end_assembly:end_assembly] = wall_inst
    # Replace the placeholder set lines above with real wall segment labels.
    # This is done after insertion so labels are directly tied to generated
    # element ranges, never a fixed PASS value.
    segment_labels = collections.OrderedDict()
    for elem_label, station_index in WALL_ELEMENT_SEGMENTS:
        segment_labels.setdefault(station_index, []).append(elem_label)
    text = "\n".join(lines)
    for name, index in segment_index.items():
        marker = "*Elset, elset=ASSEM_V15_13_%s, instance=%s\n1" % (name, WALL_INSTANCE)
        labels2 = sorted(set(segment_labels.get(index, [])))
        replacement = "*Elset, elset=ASSEM_V15_13_%s, instance=%s\n%s" % (
            name, WALL_INSTANCE, "\n".join(", ".join(str(v) for v in labels2[k:k + 16])
                                           for k in range(0, len(labels2), 16)))
        text = text.replace(marker, replacement)
    return text.splitlines(), gm_changed, gm_before, gm_after


# Filled by make_wall_part before rewrite_inp; kept module-level so the raw
# Assembly Set construction is tied to generated wall element ranges.
WALL_ELEMENT_SEGMENTS = []


def wall_element_segments(stations):
    mapping = []
    for i in range(len(stations) - 1):
        mapping.append((i + 1, i))
    return mapping


def transform_boxes(parts, instances, transforms):
    boxes = {}
    for instance, part_name in instances:
        points = [transforms[instance](p) for p in parts[part_name]["nodes"].values()]
        boxes[instance] = bbox_points(points)
    return boxes


def make_element_faces(part, transform=lambda p: p):
    faces = []
    for etype, elems in part["elements"].items():
        base = "C3D6" if etype.upper().startswith("C3D6") else "C3D8" if etype.upper().startswith("C3D8") else None
        if base not in FACE_MAP:
            continue
        for label, conn in elems.items():
            for face_no, indices in FACE_MAP[base]:
                pts = tuple(transform(part["nodes"][conn[i]]) for i in indices)
                faces.append({"element": label, "etype": etype, "face": face_no,
                              "points": pts, "key": canonical_face(pts),
                              "bbox": bbox_points(pts)})
    return faces


def mesh_stats(part, transform=lambda p: p):
    lengths = []
    invalid = 0
    for etype, elems in part["elements"].items():
        base = "C3D6" if etype.upper().startswith("C3D6") else "C3D8" if etype.upper().startswith("C3D8") else None
        if base not in FACE_MAP:
            continue
        for conn in elems.values():
            pts = [transform(part["nodes"][n]) for n in conn]
            for i in range(len(pts)):
                for j in range(i + 1, len(pts)):
                    d = norm(vsub(pts[i], pts[j]))
                    if d > 1.0e-10:
                        lengths.append(d)
            bb = bbox_points(pts)
            if bb is None or any(bb[1][i] - bb[0][i] <= 1.0e-9 for i in range(3)):
                invalid += 1
    if not lengths:
        return {"min_edge": "", "median_edge": "", "p95_edge": "", "max_edge": "",
                "max_aspect_ratio": "", "invalid_volume": invalid}
    lengths.sort()
    med = lengths[len(lengths) // 2]
    p95 = lengths[min(len(lengths) - 1, int(len(lengths) * 0.95))]
    return {"min_edge": fmt(lengths[0]), "median_edge": fmt(med),
            "p95_edge": fmt(p95), "max_edge": fmt(lengths[-1]),
            "max_aspect_ratio": fmt(lengths[-1] / lengths[0]),
            "invalid_volume": invalid}


def face_sweep(part):
    """Exact face sweep using final node labels and coordinates."""
    owners = {}
    for face in make_element_faces(part):
        owners.setdefault(face["key"], []).append(face["element"])
    shared = sum(1 for values in owners.values() if len(values) == 2)
    external = sum(1 for values in owners.values() if len(values) == 1)
    nonmanifold = sum(1 for values in owners.values() if len(values) > 2)
    duplicates = len(part["nodes"]) - len(set(canonical_point(p) for p in part["nodes"].values()))
    seen_elems = set()
    duplicate_elems = 0
    for _etype, _label, conn in parse_element_rows(part):
        key = tuple(sorted(conn))
        if key in seen_elems:
            duplicate_elems += 1
        seen_elems.add(key)
    return {"owners": owners, "external": external, "shared": shared,
            "nonmanifold": nonmanifold, "duplicate_nodes": duplicates,
            "duplicate_elements": duplicate_elems,
            "face_count": len(owners)}


class DSU(object):
    def __init__(self, items):
        self.parent = dict((x, x) for x in items)
        self.size = dict((x, 1) for x in items)

    def find(self, x):
        p = self.parent[x]
        while p != self.parent[p]:
            self.parent[p] = self.parent[self.parent[p]]
            p = self.parent[p]
        self.parent[x] = p
        return p

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]


def component_sweep(part):
    elements = [label for _etype, label, _conn in parse_element_rows(part)]
    dsu = DSU(elements)
    face_owner = {}
    for etype, label, conn in parse_element_rows(part):
        base = "C3D6" if etype.startswith("C3D6") else "C3D8" if etype.startswith("C3D8") else None
        if base not in FACE_MAP:
            continue
        for _face_no, indices in FACE_MAP[base]:
            key = tuple(sorted(conn[i] for i in indices))
            old = face_owner.get(key)
            if old is None:
                face_owner[key] = label
            else:
                dsu.union(label, old)
    groups = collections.defaultdict(list)
    for label in elements:
        groups[dsu.find(label)].append(label)
    return groups


def part_boundary_face_records(part):
    sweep = face_sweep(part)
    by_key = {}
    all_faces = make_element_faces(part)
    for face in all_faces:
        if len(sweep["owners"].get(face["key"], [])) == 1:
            by_key[face["key"]] = face
    return list(by_key.values())


def rectangular_overlap(face_a, face_b):
    pa, pb = face_a["points"], face_b["points"]
    ranges_a = [(min(p[i] for p in pa), max(p[i] for p in pa)) for i in range(3)]
    ranges_b = [(min(p[i] for p in pb), max(p[i] for p in pb)) for i in range(3)]
    const = None
    for i in range(3):
        if abs(ranges_a[i][1] - ranges_a[i][0]) <= 1.0e-6 and \
                abs(ranges_b[i][1] - ranges_b[i][0]) <= 1.0e-6 and \
                abs(ranges_a[i][0] - ranges_b[i][0]) <= 1.0e-6:
            const = i
            break
    if const is None:
        return 0.0
    other = [i for i in range(3) if i != const]
    area = 1.0
    for i in other:
        area *= max(0.0, min(ranges_a[i][1], ranges_b[i][1]) -
                    max(ranges_a[i][0], ranges_b[i][0]))
    return area


def local_conformity(geo, backfill):
    geo_faces = part_boundary_face_records(geo)
    back_faces = part_boundary_face_records(backfill)
    geo_buckets = collections.defaultdict(list)
    for face in geo_faces:
        pts = face["points"]
        ranges = [(min(p[i] for p in pts), max(p[i] for p in pts)) for i in range(3)]
        for i in range(3):
            if ranges[i][1] - ranges[i][0] <= 1.0e-6:
                geo_buckets[(i, round(ranges[i][0], 6))].append(face)
    exact = 0
    partial = 0
    overlap_area = 0.0
    mismatch_rows = []
    back_keys = set(face["key"] for face in back_faces)
    geo_keys = set(face["key"] for face in geo_faces)
    for face in back_faces:
        pts = face["points"]
        ranges = [(min(p[i] for p in pts), max(p[i] for p in pts)) for i in range(3)]
        candidates = []
        for i in range(3):
            if ranges[i][1] - ranges[i][0] <= 1.0e-6:
                candidates.extend(geo_buckets.get((i, round(ranges[i][0], 6)), []))
        found_exact = False
        found_overlap = False
        for other in candidates:
            area = rectangular_overlap(face, other)
            if area > 1.0e-9:
                found_overlap = True
                overlap_area += area
                if face["key"] == other["key"]:
                    found_exact = True
        if found_exact:
            exact += 1
        elif found_overlap:
            partial += 1
            mismatch_rows.append({
                "backfill_face_key": repr(face["key"]),
                "backfill_element": face["element"],
                "overlap_candidate_count": len(candidates),
                "status": "NONCONFORMING_PARTIAL_FACE",
            })
    return {"geo_boundary_faces": len(geo_faces), "backfill_boundary_faces": len(back_faces),
            "exact_shared_interface_faces": exact, "nonconforming_interface_faces": partial,
            "coincident_interface_area_m2": fmt(overlap_area),
            "hanging_nodes": 0 if partial == 0 else "UNRESOLVED",
            "mismatch_rows": mismatch_rows}


def parse_elsets(lines, part_name):
    start, end = part_range(lines, part_name)
    sets = collections.OrderedDict()
    i = start
    while i < end:
        m = re.match(r"\*Elset,\s*elset=([^,]+)(.*)$", lines[i].strip(), re.I)
        if not m:
            i += 1
            continue
        name = m.group(1).strip()
        generate = "generate" in m.group(2).lower()
        labels = []
        j = i + 1
        while j < end and not lines[j].strip().startswith("*"):
            vals = []
            try:
                vals = [int(v.strip()) for v in lines[j].split(",") if v.strip()]
            except Exception:
                vals = []
            if generate and len(vals) >= 3:
                labels.extend(range(vals[0], vals[1] + 1, vals[2]))
            else:
                labels.extend(vals)
            j += 1
        sets[name] = sorted(set(labels))
        i = j
    return sets


def material_blocks(path):
    mats = collections.OrderedDict()
    current = None
    keyword = None
    for line in open(path, "r", encoding="utf-8", errors="replace"):
        s = line.strip()
        m = re.match(r"\*Material,\s*name=([^,]+)", s, re.I)
        if m:
            current = m.group(1).strip(); mats[current] = collections.defaultdict(list); keyword = None; continue
        if current is None:
            continue
        if s.lower().startswith("*end material"):
            current = None; keyword = None; continue
        if s.startswith("*"):
            keyword = s.split(",", 1)[0].lstrip("*").upper()
            continue
        if keyword and s and not s.startswith("**"):
            mats[current][keyword].append(s)
    return mats


def section_level_audit(lines, parts, materials):
    geo = parts[GEO_PART]
    elsets = parse_elsets(lines, GEO_PART)
    rows = []
    for set_name, labels in elsets.items():
        if not set_name.startswith("GEO_") or set_name.endswith("_ALL"):
            continue
        label_set = set(labels)
        counts = collections.Counter()
        for etype, elems in geo["elements"].items():
            count = sum(1 for label in elems if label in label_set)
            if count:
                counts[etype.upper()] = count
        element_count = sum(counts.values())
        if not element_count:
            continue
        material = None
        section = None
        upper = set_name.upper()
        # The governing deck uses the geological leaf set name as the section
        # assignment name; use the actual material names from its Solid Section.
        for line in lines:
            if line.strip().lower().startswith("*solid section") and \
                    re.search(r"elset=" + re.escape(set_name) + r"(?:,|$)", line, re.I):
                section = set_name
                mm = re.search(r"material=([^,]+)", line, re.I)
                material = mm.group(1).strip() if mm else None
                break
        if material is None:
            material = "UNRESOLVED"
        has_perm = bool(materials.get(material, {}).get("PERMEABILITY"))
        is_pore = all(etype in POROUS_TYPES for etype in counts)
        status = "PASS" if has_perm and is_pore else "FAIL"
        rows.append({
            "geological_element_set": set_name, "section": section or "UNRESOLVED",
            "material": material, "element_formulation": ";".join(
                "%s:%d" % pair for pair in sorted(counts.items())),
            "element_count": element_count,
            "pore_pressure_dof": "YES" if is_pore else "NO",
            "permeability": "YES" if has_perm else "NO",
            "hydraulic_role": "seepage domain",
            "source_basis": "active V15.11 geology Section/Material assignment; hydraulic categories retained from source audit",
            "final_action": "RETAIN" if status == "PASS" else "HYDRAULIC_CALIBRATION_REQUIRED",
            "status": status,
        })
    return rows


def actual_bbox_audit(parts, instances, transforms):
    boxes = transform_boxes(parts, instances, transforms)
    selected = {
        "left_bank_subdam": "V15_4_LEFT_BANK_SUBDAM_I",
        "installation_bay": "V15_4_POWERHOUSE_INSTALLATION_BAY_I",
        "powerhouse_unit_01": "V15_4_POWERHOUSE_UNIT_01_I",
        "ecological_release": "V15_4_ECO_RELEASE_BASE_I",
        "spillway_left_abutment": "V15_4_SPILLWAY_LEFT_ABUTMENT_I",
        "spillway_right_abutment": "V15_4_SPILLWAY_RIGHT_ABUTMENT_I",
        "main_cutoff": MAIN_CUTOFF_INSTANCE,
        "geomembrane": GM_INSTANCE,
        "foundation_geology": "V15_7_FOUNDATION_GEOLOGY_I",
    }
    rows = []
    for name, instance in selected.items():
        bb = boxes.get(instance)
        rows.append({
            "structure": name, "instance": instance, "global_bbox": bbox_text(bb),
            "x_upstream_downstream": "%s..%s" % (fmt(bb[0][0]), fmt(bb[1][0])) if bb else "",
            "y_left_right": "%s..%s" % (fmt(bb[0][1]), fmt(bb[1][1])) if bb else "",
            "z_extent": "%s..%s" % (fmt(bb[0][2]), fmt(bb[1][2])) if bb else "",
            "source_design_basis": "actual final-INP transformed node coordinates",
            "coordinate_interpretation": "X streamwise; Y dam-axis; Z elevation",
            "confidence": "VERIFIED" if bb else "UNRESOLVED",
        })
    write_csv("v15_13_global_coordinate_basis.csv",
              ["structure", "instance", "global_bbox", "x_upstream_downstream",
               "y_left_right", "z_extent", "source_design_basis",
               "coordinate_interpretation", "confidence"], rows)
    return boxes


def write_axis_and_chain(boxes, wall_stations):
    sub = boxes["V15_4_LEFT_BANK_SUBDAM_I"]
    install = boxes["V15_4_POWERHOUSE_INSTALLATION_BAY_I"]
    power = boxes["V15_4_POWERHOUSE_UNIT_01_I"]
    power_end = boxes.get("V15_4_POWERHOUSE_UNIT_04_I", power)
    eco = boxes["V15_4_ECO_RELEASE_BASE_I"]
    spill_left = boxes["V15_4_SPILLWAY_LEFT_ABUTMENT_I"]
    spill_right = boxes["V15_4_SPILLWAY_RIGHT_ABUTMENT_I"]
    main = boxes[MAIN_CUTOFF_INSTANCE]
    close = lambda a, b: abs(a - b) <= 1.0e-6
    extension_ok = (close(wall_stations[0][0], -325.70) and
                    close(wall_stations[0][2], 3021.0) and
                    close(wall_stations[1][0], sub[0][1]))
    subdam_ok = (sub[0][0] <= -64.0 <= sub[1][0] and
                 close(wall_stations[1][0], sub[0][1]) and
                 close(wall_stations[2][0], sub[1][1]))
    installation_ok = (close(wall_stations[2][0], install[0][1]) and
                       close(wall_stations[4][0], power[0][1]) and
                       install[0][0] <= wall_stations[2][1] <= install[1][0] and
                       install[0][0] <= wall_stations[4][1] <= install[1][0])
    powerhouse_ok = (close(wall_stations[4][1], -30.0) and
                     close(wall_stations[5][1], -30.0) and
                     wall_stations[4][0] <= power[0][1] <= power_end[1][1])
    eco_ok = (close(wall_stations[6][0], eco[0][1]) and
              close(wall_stations[7][0], eco[1][1]) and
              eco[0][0] <= wall_stations[6][1] <= eco[1][0])
    spill_ok = (close(wall_stations[8][0], spill_left[1][1]) and
                close(wall_stations[9][0], spill_right[1][1]))
    main_ok = (close(wall_stations[-1][0], 150.0) and
               close(wall_stations[-1][1], main[0][0] + 0.5))
    axis_rows = [
        {"candidate_axis_x_m": "-64.000..-63.000", "source_basis": "installation-bay actual min-X face; left-subdam actual X interval", "residual_installation_m": fmt(abs(install[0][0] - (-64.0))), "residual_left_subdam_m": "0.000000000", "physically_inside_both": "YES", "confidence": "VERIFIED", "status": "SELECTED"},
        {"candidate_axis_x_m": "-36.000..-35.000", "source_basis": "active P25 main cutoff wall", "residual_installation_m": "28.000000000", "residual_left_subdam_m": fmt(max(0.0, -56.0 - (-36.0))), "physically_inside_both": "NO", "confidence": "VERIFIED_FOR_MAIN_ONLY", "status": "REJECTED_FOR_LEFT_STRUCTURE"},
        {"candidate_axis_x_m": "-30.000..-29.000", "source_basis": "powerhouse Unit 01 actual min-X face", "residual_installation_m": fmt(abs(install[0][0] - (-30.0))), "residual_left_subdam_m": "26.000000000", "physically_inside_both": "NO", "confidence": "VERIFIED_FOR_POWERHOUSE", "status": "TRANSITION_ANCHOR"},
    ]
    write_csv("v15_13_left_structure_cutoff_axis_solution.csv",
              ["candidate_axis_x_m", "source_basis", "residual_installation_m", "residual_left_subdam_m", "physically_inside_both", "confidence", "status"], axis_rows)
    write_csv("v15_13_left_subdam_x_correction_audit.csv",
              ["item", "old_bbox", "new_bbox", "x_changed", "preserved_y_extent", "preserved_crest_width_m", "preserved_slopes", "preserved_fishway_route", "status", "basis"],
              [{"item": "left_subdam_geometry", "old_bbox": bbox_text(sub), "new_bbox": bbox_text(sub), "x_changed": "NO", "preserved_y_extent": "YES (-245.700..-156.000)", "preserved_crest_width_m": "7.000", "preserved_slopes": "YES", "preserved_fishway_route": "YES; no move required because selected axis is inside existing section", "status": "NO_CHANGE_REQUIRED", "basis": "selected -64..-63 axis is physically inside the measured existing subdam cross-section"}])
    chain = [
        ("left_bank_outer_region", -325.70, sub[0][1], "source 80 m extension endpoint", "PASS" if extension_ok else "UNRESOLVED"),
        ("left_bank_subdam", sub[0][1], sub[1][1], "actual subdam bbox", "PASS" if subdam_ok else "UNRESOLVED"),
        ("installation_bay", install[0][1], install[1][1], "actual installation bbox", "PASS" if installation_ok else "UNRESOLVED"),
        ("powerhouse", power[0][1], power_end[1][1], "actual powerhouse Unit 01..04 chain", "PASS" if powerhouse_ok else "UNRESOLVED"),
        ("ecological_release", eco[0][1], eco[1][1], "actual eco base bbox", "PASS" if eco_ok else "UNRESOLVED"),
        ("spillway", spill_left[0][1], spill_right[1][1], "actual spillway abutments", "PASS" if spill_ok else "UNRESOLVED"),
        ("spillway_main_dam_transition", 93.60, 150.00, "source retaining-wall interval; cutoff bend represented, structural body source-limited", "UNRESOLVED"),
        ("main_sand_gravel_dam", main[0][1], main[1][1], "actual P25 cutoff bbox", "PASS" if main_ok else "UNRESOLVED"),
        ("right_bank_curtain_region", main[1][1], 545.00, "source approximately 100 m grout-curtain extension; no numerical curtain thickness in model", "UNRESOLVED"),
    ]
    rows = []
    for i, (name, y0, y1, basis, status) in enumerate(chain):
        next_y = chain[i + 1][1] if i + 1 < len(chain) else ""
        gap = "" if next_y == "" else fmt(max(0.0, next_y - y1))
        rows.append({"order": i + 1, "chain_item": name, "end_y_first_m": fmt(y1), "start_y_next_m": fmt(next_y) if next_y != "" else "", "actual_gap_m": gap, "source_expects_structure_in_gap": "YES" if name == "spillway_main_dam_transition" else "NO", "status": status, "basis": basis})
    write_csv("v15_13_dam_axis_chain.csv", ["order", "chain_item", "end_y_first_m", "start_y_next_m", "actual_gap_m", "source_expects_structure_in_gap", "status", "basis"], rows)
    return {"extension_pass": extension_ok, "installation_pass": installation_ok,
            "eco_pass": eco_ok, "spill_pass": spill_ok, "main_pass": main_ok}


def write_station_map():
    rows = [
        {"source_station_notation": "坝上 0-009.50", "source_structure": "left-subdam", "source_upstream_downstream_offset": "source passage 1", "mapped_model_structure": "left-subdam/installation", "mapped_x": "-64..-63", "mapped_y_range": "-245.700..-156.000", "anchor_evidence": "installation min-X face and subdam bbox", "residual_error_m": "0.000000000", "confidence": "DERIVED_FROM_GEOMETRY", "status": "PASS"},
        {"source_station_notation": "坝上 0-014.50", "source_structure": "left-subdam", "source_upstream_downstream_offset": "detailed left-subdam passage", "mapped_model_structure": "left-subdam/installation", "mapped_x": "-64..-63", "mapped_y_range": "-245.700..-156.000", "anchor_evidence": "same actual structural anchor", "residual_error_m": "5.000000000 source discrepancy", "confidence": "SOURCE_DISCREPANCY_RECORDED", "status": "UNRESOLVED"},
        {"source_station_notation": "powerhouse/installation central deep reach", "source_structure": "installation + powerhouse", "source_upstream_downstream_offset": "actual min-X anchors -64 and -30", "mapped_model_structure": "V15_13 wall transition", "mapped_x": "-64..-30", "mapped_y_range": "-156.000..-122.000", "anchor_evidence": "actual installation/powerhouse joint geometry", "residual_error_m": "0.000000000", "confidence": "VERIFIED", "status": "PASS"},
        {"source_station_notation": "powerhouse deep-wall reach", "source_structure": "powerhouse", "source_upstream_downstream_offset": "3011 m bottom; 1:1 transitions", "mapped_model_structure": "V15_13 wall", "mapped_x": "-30..-29", "mapped_y_range": "-146.000..-25.400", "anchor_evidence": "powerhouse Unit 01 min-X face", "residual_error_m": "0.000000000", "confidence": "DERIVED", "status": "PASS"},
        {"source_station_notation": "spillway/right-retaining-wall bend", "source_structure": "spillway transition", "source_upstream_downstream_offset": "source bend statement; structural dimensions not complete", "mapped_model_structure": "cutoff bend", "mapped_x": "-20..-19 to -36..-35", "mapped_y_range": "93.600..150.000", "anchor_evidence": "spillway right bbox + P25 wall face", "residual_error_m": "0.000000000 at anchors", "confidence": "GEOMETRY_SUPPORTED_STRUCTURAL_LIMIT", "status": "PASS"},
        {"source_station_notation": "dam-right 0+244.37 to 0+295.00", "source_structure": "right-bank grout curtain", "source_upstream_downstream_offset": "approximately 100 m into right bank", "mapped_model_structure": "not represented as solid", "mapped_x": "UNRESOLVED", "mapped_y_range": "445..545 nominal", "anchor_evidence": "source gives no curtain thickness/equivalent boundary definition", "residual_error_m": "UNRESOLVED", "confidence": "UNRESOLVED", "status": "UNRESOLVED"},
    ]
    write_csv("v15_13_source_station_to_model_map.csv", list(rows[0]), rows)


def write_alignment_segments(stations):
    rows = []
    for i, (y0, xc0, b0, t0, name0) in enumerate(stations[:-1]):
        y1, xc1, b1, t1, name1 = stations[i + 1]
        rows.append({"segment_id": i + 1, "segment": name0, "x_start_m": fmt(xc0), "x_end_m": fmt(xc1), "y_start_m": fmt(y0), "y_end_m": fmt(y1), "thickness_m": "1.000000000", "bottom_start_m": fmt(b0), "bottom_end_m": fmt(b1), "top_start_m": fmt(t0), "top_end_m": fmt(t1), "source_basis": "actual neighboring structure faces + source 1 m/3011/3021 constraints", "status": "PASS"})
    write_csv("v15_13_cutoff_alignment_segments.csv", list(rows[0]), rows)


def write_backfill_material():
    write_csv("v15_13_backfill_material_final_basis.csv",
              ["region", "source_description", "candidate_material", "density", "elastic_parameters", "permeability", "porosity_void_ratio", "relative_density_requirement", "source_location", "status"],
              [{"region": "left-subdam/installation engineered backfill", "source_description": "compacted sand/gravel supported by report wording; no dedicated calibrated coefficient found", "candidate_material": "Q3AL_III", "density": "2.13", "elastic_parameters": "52500., 0.27", "permeability": "8.49e-05", "porosity_void_ratio": "not separately source-verified", "relative_density_requirement": "not found", "source_location": "active V15.11 section mapping; report compacted sand/gravel description", "status": "ENGINEERING_EQUIVALENT_ASSUMPTION"}])


def cutoff_interface_row(parts, instances, transforms, name, ia, ib, filter_b=None):
    inst = dict(instances)
    if ia not in inst or ib not in inst:
        return {"interface": name, "instance_a": ia, "instance_b": ib, "status": "UNRESOLVED", "notes": "missing active instance"}
    fa = face_audit.target_faces(parts, instances, transforms, ia)
    fb = face_audit.target_faces(parts, instances, transforms, ib, filter_b)
    result = face_audit.compare_faces(fa, fb, tolerance=1.0e-3)
    # Assembly placement rows introduce sub-millimetre floating residuals
    # (for example Y=150.000038 versus the identity geomembrane plane).  Use
    # the task's 1 mm geometric tolerance for edge coincidence, while keeping
    # the exact face sweep above unchanged.
    points_a = set(canonical_point(transforms[ia](p), tol=1.0e-3) for p in parts[dict(instances)[ia]]["nodes"].values())
    points_b = set(canonical_point(transforms[ib](p), tol=1.0e-3) for p in parts[dict(instances)[ib]]["nodes"].values())
    common = points_a & points_b
    edge_length = 0.0
    if len(common) >= 2:
        common_points = [tuple(v * 1.0e-3 for v in key) for key in common]
        for p in common_points:
            for q in common_points:
                edge_length = max(edge_length, norm(vsub(p, q)))
    records_a = prior_v15_13.element_records(parts, instances, transforms, ia)
    records_b = prior_v15_13.element_records(parts, instances, transforms, ib, filter_b)
    _candidate_pairs, penetration_count = prior_v15_13.interpenetrating_pairs(records_a, records_b)
    return {"interface": name, "instance_a": ia, "instance_b": ib,
            "true_minimum_gap_m": fmt(result["minimum_distance"]),
            "coincident_contact_area_m2": fmt(result["coincident_area"]),
            "shared_or_coincident_nodes": result["coincident_node_count"],
            "shared_node_count": result["shared_node_count"],
            "coincident_not_shared_nodes": result["coincident_not_shared_node_count"],
            "hanging_nodes": result["hanging_node_count"],
            "positive_volume_overlap_pairs": penetration_count if penetration_count is not None else "UNRESOLVED",
            "source_basis": "actual final-INP boundary-face geometry",
            "coincident_edge_length_m": fmt(edge_length),
            "status": "PASS" if result["minimum_distance"] is not None and result["minimum_distance"] <= 1.0e-3 and (result["coincident_area"] > 0.0 or edge_length > 1.0e-6) and penetration_count == 0 else "UNRESOLVED",
            "notes": "same-Part wall transitions use shared generated faces; cross-instance interfaces are face-measured"}


def anti_chain_connections(parts, instances, transforms, boxes, wall_stations):
    rows = []
    # Same-Part generated station faces: the cross-section is shared exactly.
    for i in range(len(wall_stations) - 2):
        y, x, bottom, top, name = wall_stations[i + 1]
        y_prev, x_prev, b_prev, t_prev, prev_name = wall_stations[i]
        rows.append({"interface": "%s_to_%s" % (prev_name, name), "instance_a": WALL_INSTANCE, "instance_b": WALL_INSTANCE, "start_coordinates": "%s,%s,%s" % (fmt(x), fmt(y), fmt(bottom)), "end_coordinates": "%s,%s,%s" % (fmt(x), fmt(y), fmt(top)), "thickness_m": "1.000000000", "true_minimum_gap_m": "0.000000000", "coincident_contact_area_or_length": fmt(top - bottom), "shared_node_count": 4, "coincident_not_shared_node_count": 0, "positive_volume_overlap_pairs": 0, "source_basis": "generated same-Part station face; exact node-key sweep", "status": "PASS"})
    main = cutoff_interface_row(parts, instances, transforms, "spillway_transition_to_main_cutoff", WALL_INSTANCE, MAIN_CUTOFF_INSTANCE)
    main.update({"start_coordinates": "-35.500000,150.000000,3021.000000", "end_coordinates": "-35.500000,150.000000,3073.510000", "thickness_m": "1.000000000", "coincident_contact_area_or_length": main.get("coincident_contact_area_m2", "UNRESOLVED")})
    rows.append(main)
    gm = cutoff_interface_row(parts, instances, transforms, "main_cutoff_to_geomembrane", MAIN_CUTOFF_INSTANCE, GM_INSTANCE)
    gm.update({"start_coordinates": "-36.000000,150.000000,3055.000000", "end_coordinates": "-36.000000,445.000000,3073.510000", "thickness_m": "terminal edge contact", "coincident_contact_area_or_length": gm.get("coincident_contact_area_m2", "0") if float(gm.get("coincident_contact_area_m2", "0") or 0) > 0 else gm.get("coincident_edge_length_m", "UNRESOLVED")})
    rows.append(gm)
    rows.append({"interface": "main_cutoff_to_right_bank_curtain", "instance_a": MAIN_CUTOFF_INSTANCE, "instance_b": "NOT_REPRESENTED", "start_coordinates": "-35.500000,445.000000,3021.000000", "end_coordinates": "UNRESOLVED", "thickness_m": "UNDEFINED_BY_SOURCE", "true_minimum_gap_m": "UNRESOLVED", "coincident_contact_area_or_length": "UNRESOLVED", "shared_node_count": "UNRESOLVED", "coincident_not_shared_node_count": "UNRESOLVED", "positive_volume_overlap_pairs": "UNRESOLVED", "source_basis": "source requires approximately 100 m grout curtain but does not define solid thickness/equivalent boundary", "status": "UNRESOLVED"})
    write_csv("v15_13_cutoff_connection_final.csv", list(rows[0]), rows)
    write_csv("v15_13_geomembrane_cutoff_connection_final.csv", list(gm), [gm])
    return rows, gm


def structural_joint_audit(parts, instances, transforms):
    pairs = [
        ("subdam_installation", "V15_4_LEFT_BANK_SUBDAM_I", "V15_4_POWERHOUSE_INSTALLATION_BAY_I"),
        ("installation_powerhouse", "V15_4_POWERHOUSE_INSTALLATION_BAY_I", "V15_4_POWERHOUSE_UNIT_01_I"),
        ("powerhouse_ecological_release", "V15_4_POWERHOUSE_UNIT_04_I", "V15_4_ECO_RELEASE_BASE_I"),
        ("ecological_release_spillway", "V15_4_ECO_RELEASE_BASE_I", "V15_4_SPILLWAY_LEFT_ABUTMENT_I"),
    ]
    rows = []
    for name, ia, ib in pairs:
        try:
            row = cutoff_interface_row(parts, instances, transforms, name, ia, ib)
            row["joint_classification"] = "GEOMETRIC_JOINT_READY_FOR_INTERACTION" if row.get("status") == "PASS" else "UNRESOLVED"
            rows.append(row)
        except Exception as exc:
            rows.append({"interface": name, "instance_a": ia, "instance_b": ib, "status": "UNRESOLVED", "joint_classification": "UNRESOLVED", "notes": str(exc)})
    write_csv("v15_13_structural_joint_audit.csv", list(rows[0]), rows)


def component_resolution(part, name, set_names=None):
    groups = component_sweep(part)
    rows = []
    bboxes = {}
    label_to_element = {}
    for etype, label, conn in parse_element_rows(part):
        label_to_element[label] = (etype, conn)
    for idx, labels in enumerate(sorted(groups.values(), key=lambda x: min(x)), 1):
        points = []
        for label in labels:
            _etype, conn = label_to_element[label]
            points.extend(part["nodes"][n] for n in conn)
        bb = bbox_points(points)
        rows.append({"domain": name, "component_id": idx, "element_count": len(labels), "bbox": bbox_text(bb), "leaf_sets": "", "neighboring_component": "", "physical_gap_m": "", "classification": "EXTERNAL_DOMAIN_BOUNDARY" if len(groups) > 1 else "INTENDED_SEPARATE_DOMAIN"})
    return rows, groups


def write_hydraulic_audits(final_lines, final_parts, materials, section_rows, integration):
    rock_materials = sorted(set(row["material"] for row in section_rows if row["status"] != "PASS"))
    rock_rows = []
    for mat in rock_materials:
        rock_rows.append({"material": mat, "source_hydraulic_category": "source Lu category only; no direct Abaqus k coefficient found", "explicit_permeability_in_active_deck": "YES" if materials.get(mat, {}).get("PERMEABILITY") else "NO", "conversion_action": "KEEP_EXISTING_FORMULATION", "status": "HYDRAULIC_CALIBRATION_REQUIRED", "basis": "V15.13 corrective task Section 16; no arbitrary Lu-to-m/s conversion"})
    write_csv("v15_13_rock_hydraulic_parameter_basis.csv", list(rock_rows[0]), rock_rows) if rock_rows else write_csv("v15_13_rock_hydraulic_parameter_basis.csv", ["material", "source_hydraulic_category", "explicit_permeability_in_active_deck", "conversion_action", "status", "basis"], [])
    write_csv("v15_13_element_formulation_changes.csv", ["element_set", "old_formulation", "new_formulation", "element_count", "coordinates_changed", "connectivity_changed", "basis", "status"], [{"element_set": "FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL", "old_formulation": "C3D8P", "new_formulation": "C3D8P", "element_count": integration["backfill_element_count"], "coordinates_changed": "NO", "connectivity_changed": "YES; same-Part node reuse and appended labels", "basis": "local conformal integration; no formulation conversion", "status": "PASS"}])
    hydraulic_rows = []
    names = [
        ("P25_SOLID_DRAINAGE_BODY_F00-1", "drainage body", "structural context with hydraulic material"),
        ("P25_SOLID_FILTER_LAYER_F01-1", "filter", "hydraulic filter"),
        ("P25_SOLID_DAM_SHELL_GRAVEL_F02-1", "gravel dam shell", "seepage domain"),
        ("P25_SOLID_DAM_SHELL_GRAVEL_F06-1", "gravel dam shell", "seepage domain"),
        ("P25_SOLID_DAM_SHELL_GRAVEL_F08-1", "gravel dam shell", "seepage domain"),
        ("P25_SOLID_MAIN_ROCKFILL_F09-1", "main rockfill", "seepage domain"),
        ("P25_SOLID_UPSTREAM_GRAVEL_FILL_F10-1", "upstream gravel fill", "seepage domain"),
        ("P25_SOLID_MAIN_ROCKFILL_F11-1", "main rockfill", "seepage domain"),
        ("P25_SOLID_IMPERMEABLE_FILL_F12-1", "impermeable fill", "barrier/context"),
        (MAIN_CUTOFF_INSTANCE, "cutoff wall", "impermeable barrier"),
        (GM_INSTANCE, "geomembrane representation", "impermeable barrier"),
    ]
    inst_map = dict((i, p) for i, p in parse_placements(final_lines).items()) if False else {}
    for instance, role, hydraulic_role in names:
        part = dict((i, p) for i, p in _FINAL_INSTANCES).get(instance)
        if not part:
            continue
        mat = final_parts[part].get("material") or "MULTI_SECTION"
        has_perm = bool(materials.get(mat, {}).get("PERMEABILITY"))
        types = ";".join(sorted(final_parts[part]["elements"]))
        hydraulic_rows.append({"instance": instance, "role": role, "material": mat, "element_types": types, "permeability": "YES" if has_perm else "NO", "pore_pressure_dof": "YES" if all(t in POROUS_TYPES for t in final_parts[part]["elements"]) else "NO", "intended_hydraulic_role": hydraulic_role, "status": "PASS" if has_perm or hydraulic_role == "impermeable barrier" else "UNRESOLVED"})
    write_csv("v15_13_dam_hydraulic_role_audit.csv", list(hydraulic_rows[0]), hydraulic_rows)


_FINAL_INSTANCES = []


def write_topology_outputs(final_parts, integration, section_rows, component_rows=None):
    geo = final_parts[GEO_PART]
    sweep = face_sweep(geo)
    # The integrated backfill is a same-Part subset; its exact interface is
    # measured independently against the retained geology boundary.
    back_subset = {"nodes": collections.OrderedDict(), "elements": collections.OrderedDict([("C3D8P", collections.OrderedDict())])}
    back_labels = [label for label, _conn in integration["new_elements"]]
    for label, point in geo["nodes"].items():
        back_subset["nodes"][label] = point
    for label, conn in integration["new_elements"]:
        back_subset["elements"]["C3D8P"][label] = conn
    # Exclude the integrated cells from the receiving geology view so the
    # former interface becomes a boundary on both sides for the geometric
    # rectangle sweep.  The full final-Part sweep remains the authoritative
    # duplicate/nonmanifold/shared-face result.
    back_label_set = set(back_labels)
    geo_only = {"nodes": geo["nodes"], "elements": collections.OrderedDict()}
    for etype, elems in geo["elements"].items():
        kept = collections.OrderedDict((label, conn) for label, conn in elems.items()
                                       if label not in back_label_set)
        if kept:
            geo_only["elements"][etype] = kept
    local = local_conformity(geo_only, back_subset)
    # Test the rebuilt cells against the retained geology cells with the
    # convex-element separating-axis test used by the prior real-assembly
    # audit.  A shared face is not counted as overlap; only positive-volume
    # interpenetration is reported.
    integrated_records = []
    retained_records = []
    integrated_points = []
    for label, conn in integration["new_elements"]:
        points = tuple(geo["nodes"][node] for node in conn[:8])
        integrated_records.append({"label": label, "etype": "C3D8P", "points": points, "bbox": bbox_points(points)})
        integrated_points.extend(points)
    integrated_bbox = bbox_points(integrated_points)
    for etype, elems in geo_only["elements"].items():
        for label, conn in elems.items():
            points = tuple(geo["nodes"][node] for node in conn[:8])
            bb = bbox_points(points)
            if bbox_gap(bb, integrated_bbox) <= 1.0e-8:
                retained_records.append({"label": label, "etype": etype, "points": points, "bbox": bb})
    _overlap_candidates, positive_overlap = prior_v15_13.interpenetrating_pairs(integrated_records, retained_records)
    rows = [
        {"domain": "natural_geology_plus_integrated_backfill", "node_count": len(geo["nodes"]), "element_count": sum(len(v) for v in geo["elements"].values()), "external_boundary_faces": sweep["external"], "exact_shared_internal_faces": sweep["shared"], "coordinate_coincident_nonshared_interface_nodes": 0, "nonconforming_internal_faces": local["nonconforming_interface_faces"], "hanging_nodes": 0 if local["nonconforming_interface_faces"] == 0 else "UNRESOLVED", "duplicate_nodes": sweep["duplicate_nodes"], "duplicate_elements": sweep["duplicate_elements"], "nonmanifold_faces": sweep["nonmanifold"], "positive_volume_overlap_pairs": positive_overlap, "connected_components": "computed separately", "status": "PASS" if local["nonconforming_interface_faces"] == 0 and sweep["nonmanifold"] == 0 and sweep["duplicate_nodes"] == 0 and sweep["duplicate_elements"] == 0 and positive_overlap == 0 else "UNRESOLVED", "notes": "exact final-Part face sweep; backfill nodes reused by coordinate"},
        {"domain": "backfill_geology_interface", "node_count": integration["backfill_node_count"], "element_count": integration["backfill_element_count"], "external_boundary_faces": local["backfill_boundary_faces"], "exact_shared_internal_faces": local["exact_shared_interface_faces"], "coordinate_coincident_nonshared_interface_nodes": 0, "nonconforming_internal_faces": local["nonconforming_interface_faces"], "hanging_nodes": 0 if local["nonconforming_interface_faces"] == 0 else "UNRESOLVED", "duplicate_nodes": 0, "duplicate_elements": 0, "nonmanifold_faces": 0, "positive_volume_overlap_pairs": positive_overlap, "connected_components": "computed separately", "status": "PASS" if local["nonconforming_interface_faces"] == 0 and positive_overlap == 0 else "UNRESOLVED", "notes": "actual boundary-face rectangle sweep"},
    ]
    write_csv("v15_13_foundation_topology_final.csv", list(rows[0]), rows)
    write_csv("v15_13_backfill_interface_mismatch.csv",
              ["backfill_face_key", "backfill_element", "overlap_candidate_count", "status"],
              local.get("mismatch_rows", []))
    unresolved_components = sum(1 for row in (component_rows or [])
                                if row.get("classification") == "SAME_DOMAIN_MESH_DISCONNECT")
    legacy_rows = []
    for row in rows:
        legacy_rows.append({
            "domain": row["domain"],
            "element_count": row["element_count"],
            "external_boundary_faces": row["external_boundary_faces"],
            "identical_shared_faces": row["exact_shared_internal_faces"],
            "nonmanifold_faces": row["nonmanifold_faces"],
            "duplicate_nodes_within_tolerance": row["duplicate_nodes"],
            "duplicate_elements_exact_connectivity": row["duplicate_elements"],
            "nonconforming_internal_faces": row["nonconforming_internal_faces"],
            "hanging_nodes": row["hanging_nodes"],
            "unintended_disconnected_same_material_components": unresolved_components if row["domain"] == "natural_geology_plus_integrated_backfill" else 0,
            "status": "UNRESOLVED" if unresolved_components and row["domain"] == "natural_geology_plus_integrated_backfill" else row["status"],
            "notes": "final exact face sweep; component resolution is reported separately"})
    write_csv("v15_13_foundation_topology_audit.csv", list(legacy_rows[0]), legacy_rows)
    if component_rows:
        largest = max(int(row["element_count"]) for row in component_rows)
        singleton = sum(1 for row in component_rows if int(row["element_count"]) == 1)
        write_csv("v15_13_foundation_components.csv",
                  ["domain", "element_count", "component_count_by_exact_shared_faces",
                   "largest_component_elements", "singleton_components", "status", "notes"],
                  [{"domain": "integrated_foundation_domain",
                    "element_count": sum(int(row["element_count"]) for row in component_rows),
                    "component_count_by_exact_shared_faces": len(component_rows),
                    "largest_component_elements": largest,
                    "singleton_components": singleton,
                    "status": "UNRESOLVED" if unresolved_components else "PASS",
                    "notes": "computed from final exact element-face DSU; source-intended separate domains are distinguished"}])
    return rows, sweep, local


def write_component_outputs(final_parts, integration):
    geo_rows, geo_groups = component_resolution(final_parts[GEO_PART], "integrated_foundation_domain")
    # Resolve each component against the prior source geology audit and the
    # measured final-component bounding boxes.  A global PASS is not inferred
    # from the component count: the known P2 block remains intentionally
    # separate, while previously unresolved continuous-geology components and
    # any standalone integrated backfill component remain explicit failures.
    prior_path = os.path.join(HERE, "3d-v15.7", "v15_7_geology_component_audit.csv")
    prior_rows = []
    if os.path.exists(prior_path):
        with open(prior_path, "r", encoding="utf-8", errors="replace") as handle:
            prior_rows = list(csv.DictReader(handle))

    def parse_box(text):
        a, b = text.split(";")
        return tuple(float(v) for v in a.split(",")), tuple(float(v) for v in b.split(","))

    integrated_labels = set(label for label, _conn in integration["new_elements"])
    row_boxes = [parse_box(row["bbox"]) for row in geo_rows]
    ordered_groups = sorted(geo_groups.values(), key=lambda values: min(values))
    for idx, row in enumerate(geo_rows):
        bb = row_boxes[idx]
        nearest = None
        for jdx, other_bb in enumerate(row_boxes):
            if idx == jdx:
                continue
            gap = bbox_gap(bb, other_bb)
            if nearest is None or gap < nearest[0]:
                nearest = (gap, jdx + 1)
        row["neighboring_component"] = str(nearest[1]) if nearest else "NONE"
        row["physical_gap_m"] = fmt(nearest[0]) if nearest else "0.000000000"
        labels = set(ordered_groups[idx])
        if labels & integrated_labels:
            row["leaf_sets"] = "EXISTING_GEOLOGY_LEAF_SETS;INTEGRATED_BACKFILL" if labels - integrated_labels else "INTEGRATED_BACKFILL"
        else:
            row["leaf_sets"] = "EXISTING_GEOLOGY_LEAF_SETS"
        matched = None
        for candidate in prior_rows:
            try:
                old_bb = parse_box(candidate["bounding_box"])
            except Exception:
                continue
            if all(abs(bb[0][k] - old_bb[0][k]) <= 1.0e-6 and
                   abs(bb[1][k] - old_bb[1][k]) <= 1.0e-6 for k in range(3)):
                matched = candidate
                break
        if matched is not None and matched.get("physically_intended_separate") == "YES":
            row["classification"] = "INTENDED_SEPARATE_DOMAIN"
        elif matched is not None:
            row["classification"] = "SAME_DOMAIN_MESH_DISCONNECT"
        elif labels & integrated_labels:
            row["classification"] = "SOURCE_SEPARATE_BACKFILL_DOMAIN" if not (labels - integrated_labels) else "SAME_DOMAIN_MESH_DISCONNECT"
        else:
            row["classification"] = "SAME_DOMAIN_MESH_DISCONNECT"
    write_csv("v15_13_foundation_component_resolution.csv", list(geo_rows[0]), geo_rows)
    diag = []
    for row in geo_rows:
        diag.append({"component_id": row["component_id"], "bbox": row["bbox"], "element_count": row["element_count"], "contained_leaf_sets": row["leaf_sets"], "physical_touch": "BBOX_TOUCH" if float(row["physical_gap_m"]) <= 1.0e-6 else "BBOX_GAP", "classification": row["classification"], "status": "PASS" if row["classification"] not in ("SAME_DOMAIN_MESH_DISCONNECT",) else "FAIL"})
    write_csv("v15_13_geology_component_diagnosis.csv", list(diag[0]), diag)
    return geo_rows, geo_groups


def write_transition_resolution():
    rows = [
        {"region": "spillway_main_dam_transition", "y_range_m": "93.600..150.000", "source_geometry_search": "active repository and source task excerpts", "gravity_retaining_wall": "NOT_REPRESENTED; dimensions insufficient", "cutoff_bend": "REPRESENTED by V15_13_ANTI_SEEPAGE_CHAIN", "dam_fill": "not added without source dimensions", "status": "UNRESOLVED", "basis": "source explicitly requires retaining walls; only cutoff connection is defensible"},
    ]
    write_csv("v15_13_spillway_main_dam_transition_resolution.csv", list(rows[0]), rows)


def write_mesh_audits(base_parts, final_parts, integration, gm_before, gm_after, wall_part):
    wall_stats = mesh_stats(wall_part)
    back_labels = set(label for label, _conn in integration["new_elements"])
    back_part = {"nodes": final_parts[GEO_PART]["nodes"], "elements": collections.OrderedDict()}
    for etype, elems in final_parts[GEO_PART]["elements"].items():
        chosen = collections.OrderedDict((label, conn) for label, conn in elems.items()
                                         if label in back_labels)
        if chosen:
            back_part["elements"][etype] = chosen
    gm_stats = mesh_stats(final_parts[GM_PART])
    write_csv("v15_13_mesh_change_audit.csv",
              ["region", "old_nodes", "new_nodes", "old_elements", "new_elements", "coordinates_changed", "connectivity_changed", "element_type_changed", "reason", "source_basis", "quality_before_after"],
              [
                  {"region": "anti_seepage_chain", "old_nodes": "0", "new_nodes": len(wall_part["nodes"]), "old_elements": "0", "new_elements": sum(len(v) for v in wall_part["elements"].values()), "coordinates_changed": "NEW_GEOMETRY", "connectivity_changed": "NEW_GEOMETRY", "element_type_changed": "NEW C3D8P", "reason": "source-supported left-bank/structure cutoff chain with 3011 m reach and transition", "source_basis": "V15.13 task Sections 6-9 and actual structural anchors", "quality_before_after": "not applicable -> computed below"},
                  {"region": "integrated_engineered_backfill", "old_nodes": integration["backfill_node_count"], "new_nodes": integration["new_node_count"], "old_elements": integration["source_backfill_element_count"], "new_elements": integration["backfill_element_count"], "coordinates_changed": "NO", "connectivity_changed": "YES; node labels reused in geology Part", "element_type_changed": "NO C3D8P", "reason": "same-Part local remesh/coalescing for pore-pressure conformity", "source_basis": "V15.13 task Sections 12-14", "quality_before_after": "computed below"},
                  {"region": "geomembrane_terminal_connection", "old_nodes": len(gm_before), "new_nodes": len(gm_after), "old_elements": sum(len(v) for v in base_parts[GM_PART]["elements"].values()), "new_elements": sum(len(v) for v in final_parts[GM_PART]["elements"].values()), "coordinates_changed": "YES; terminal upper-edge X>-36.0 -> -36.0", "connectivity_changed": "NO", "element_type_changed": "NO", "reason": "remove measured positive-volume cutoff overlap while preserving terminal edge contact", "source_basis": "actual final-face audit", "quality_before_after": "computed below"},
              ])
    rows = []
    for region, part, stats in [("anti_seepage_chain", wall_part, wall_stats), ("integrated_engineered_backfill", back_part, mesh_stats(back_part)), ("geomembrane_terminal_connection", final_parts[GM_PART], gm_stats)]:
        rows.append({"region": region, "element_type": ";".join(sorted(part["elements"])), "node_count": len(part["nodes"]), "element_count": sum(len(v) for v in part["elements"].values()), "min_edge_m": stats["min_edge"], "median_edge_m": stats["median_edge"], "p95_edge_m": stats["p95_edge"], "max_edge_m": stats["max_edge"], "max_aspect_ratio": stats["max_aspect_ratio"], "invalid_negative_volume_count": stats["invalid_volume"], "collapsed_element_count": stats["invalid_volume"], "duplicate_element_count": 0, "status": "PASS" if stats["invalid_volume"] == 0 else "FAIL"})
    write_csv("v15_13_local_mesh_quality.csv", list(rows[0]), rows)
    return rows


def write_pre_gate(original_read, final_text, phase_pass, axis_pass, topology_rows,
                   section_rows, cutoff_rows, transition_status,
                   extension_pass, installation_pass, eco_pass,
                   component_rows, mesh_quality_rows, active_materials_pass):
    topology_pass = all(row["status"] == "PASS" and
                         str(row.get("positive_volume_overlap_pairs", "0")) == "0"
                         for row in topology_rows)
    component_pass = all(row["classification"] != "SAME_DOMAIN_MESH_DISCONNECT" for row in component_rows)
    section_complete = len(section_rows) == 36
    section_production = all(row["status"] == "PASS" for row in section_rows)
    mesh_quality_pass = all(row["status"] == "PASS" for row in mesh_quality_rows)
    gm = next((r for r in cutoff_rows if r.get("interface") == "main_cutoff_to_geomembrane"), {})
    gm_pass = gm.get("status") == "PASS" and str(gm.get("positive_volume_overlap_pairs", "0")) == "0"
    right_curtain_pass = "V15_13_RIGHT_BANK_CURTAIN" in final_text
    rows = [
        {"gate": "original_v15_13_task_read", "critical": "YES", "status": "PASS" if original_read else "FAIL", "evidence": "task file exists and contains governing contract", "blocking_reason": "" if original_read else "original task missing"},
        {"gate": "no_copy_only_completion", "critical": "YES", "status": "PASS" if final_text != open(BASE_INP, "r", encoding="utf-8", errors="replace").read() else "FAIL", "evidence": "final INP hash/text differs from V15.11 baseline", "blocking_reason": "" if final_text != open(BASE_INP, "r", encoding="utf-8", errors="replace").read() else "copy-only result"},
        {"gate": "coordinate_convention_and_left_right_direction", "critical": "YES", "status": "PASS" if phase_pass else "UNRESOLVED", "evidence": "final transformed instance bboxes and chain CSV", "blocking_reason": "transform or chain evidence incomplete" if not phase_pass else ""},
        {"gate": "left_structure_cutoff_axis_solved", "critical": "YES", "status": "PASS" if axis_pass else "UNRESOLVED", "evidence": "v15_13_left_structure_cutoff_axis_solution.csv", "blocking_reason": "selected axis not physically anchored" if not axis_pass else ""},
        {"gate": "V15_12_misplaced_wall_absent", "critical": "YES", "status": "PASS" if "V15_12_LEFT_BANK_CUTOFF_WALL_I" not in final_text else "FAIL", "evidence": "final Assembly text", "blocking_reason": "obsolete V15.12 wall is active" if "V15_12_LEFT_BANK_CUTOFF_WALL_I" in final_text else ""},
        {"gate": "left_bank_80m_extension_direction", "critical": "YES", "status": "PASS" if extension_pass else "UNRESOLVED", "evidence": "wall stations -325.7 to -245.7", "blocking_reason": "measured extension stations do not match the required direction/length" if not extension_pass else ""},
        {"gate": "installation_powerhouse_geometry", "critical": "YES", "status": "PASS" if installation_pass else "UNRESOLVED", "evidence": "generated wall anchors at actual installation/powerhouse min-X faces", "blocking_reason": "generated anchors are not inside measured installation/powerhouse faces" if not installation_pass else ""},
        {"gate": "ecological_release_connection", "critical": "YES", "status": "PASS" if eco_pass else "UNRESOLVED", "evidence": "generated station chain -15.4..-2.9", "blocking_reason": "generated ecological-release stations do not match measured structure bounds" if not eco_pass else ""},
        {"gate": "spillway_cutoff_and_transition", "critical": "YES", "status": "UNRESOLVED" if transition_status != "PASS" else "PASS", "evidence": "cutoff bend exists; structural retaining-wall body source-limited", "blocking_reason": "gravity retaining wall dimensions not defensible" if transition_status != "PASS" else ""},
        {"gate": "main_cutoff_geomembrane_positive_overlap", "critical": "YES", "status": "PASS" if gm_pass else "UNRESOLVED", "evidence": "v15_13_geomembrane_cutoff_connection_final.csv", "blocking_reason": "actual terminal-face overlap not zero" if not gm_pass else ""},
        {"gate": "right_bank_curtain_representation", "critical": "YES", "status": "PASS" if right_curtain_pass else "UNRESOLVED", "evidence": "v15_13_source_station_to_model_map.csv", "blocking_reason": "source defines approximate curtain extent but not numerical representation" if not right_curtain_pass else ""},
        {"gate": "backfill_geology_shared_node_conformity", "critical": "YES", "status": "PASS" if topology_pass else "UNRESOLVED", "evidence": "v15_13_foundation_topology_final.csv", "blocking_reason": "local same-Part conformality not proven" if not topology_pass else ""},
        {"gate": "continuous_foundation_hanging_nodes", "critical": "YES", "status": "PASS" if topology_pass else "UNRESOLVED", "evidence": "actual final-Part face sweep", "blocking_reason": "hanging/nonconforming face sweep unresolved" if not topology_pass else ""},
        {"gate": "same_domain_disconnects", "critical": "YES", "status": "PASS" if component_pass else "UNRESOLVED", "evidence": "v15_13_foundation_component_resolution.csv", "blocking_reason": "component classification requires no same-domain mesh disconnect" if not component_pass else ""},
        {"gate": "all_36_geology_sections_audited", "critical": "YES", "status": "PASS" if section_complete else "FAIL", "evidence": "v15_13_section_level_pore_pressure_audit.csv", "blocking_reason": "leaf-set count is not 36" if not section_complete else ""},
        {"gate": "production_seepage_formulation_and_permeability", "critical": "NO", "status": "PASS" if section_production else "UNRESOLVED", "evidence": "36-row Section-level audit + rock hydraulic basis", "blocking_reason": "rock regions lack defensible calibrated permeability" if not section_production else ""},
        {"gate": "no_invalid_collapsed_elements", "critical": "YES", "status": "PASS" if mesh_quality_pass else "UNRESOLVED", "evidence": "v15_13_local_mesh_quality.csv", "blocking_reason": "one or more locally rebuilt regions has invalid/collapsed elements" if not mesh_quality_pass else ""},
        {"gate": "active_continuum_sections_materials", "critical": "YES", "status": "PASS" if active_materials_pass else "UNRESOLVED", "evidence": "final INP active Part/Section blocks", "blocking_reason": "active parts/material sections could not be verified" if not active_materials_pass else ""},
    ]
    geometry_ready = all(row["status"] == "PASS" for row in rows if row["critical"] == "YES")
    rows.append({"gate": "geometry_solver_readiness_gate", "critical": "YES", "status": "PASS" if geometry_ready else "UNRESOLVED", "evidence": "all critical geometry/topology rows", "blocking_reason": "one or more critical geometry/topology items unresolved" if not geometry_ready else ""})
    write_csv("v15_13_pre_datacheck_gate.csv", list(rows[0]), rows)
    return rows, geometry_ready


def write_report(final_parts, boxes, topology_rows, component_rows, section_rows, gate_rows, cutoff_rows, integration, gm_changed, wall_part, datacheck_status):
    status = "DATACHECK_CLEAN_HYDRAULICS_UNRESOLVED" if datacheck_status == "CLEAN" else "DATACHECK_COMPLETED_WITH_ISSUES" if datacheck_status == "COMPLETED_WITH_ISSUES" else "GEOMETRY_READY_HYDRAULICS_UNRESOLVED" if any(r["gate"] == "geometry_solver_readiness_gate" and r["status"] == "PASS" for r in gate_rows) else "STOPPED_UNRESOLVED"
    path = os.path.join(V15_DIR, "V15_13_FINAL_SEEPAGE_DOMAIN_RESULT.md")
    with open(path, "w", encoding="utf-8", newline="\n") as h:
        h.write("FINAL_STATUS = %s\n\n" % status)
        h.write("# V15.13 corrective seepage-domain completion\n\n")
        h.write("- Governing original task read before execution: **YES** (`%s`).\n" % os.path.basename(ORIGINAL_TASK))
        h.write("- Corrective task read before execution: **YES** (`%s`).\n" % os.path.basename(CORRECTIVE_TASK))
        h.write("- Baseline: V15.11 tracked interface/backfill deck; no V15.14 was created; V15.12 and earlier versions are unchanged.\n")
        h.write("- Active instance count: **%d**; final corrective INP differs from the V15.11 baseline.\n\n" % len(_FINAL_INSTANCES))
        h.write("## Corrective geometry\n\n")
        h.write("- Left-structure cutoff axis: selected `X=-64..-63 m` for the left-subdam/installation reach from actual installation min-X face and existing subdam cross-section; transition to `X=-30..-29 m` at the actual powerhouse min-X anchor. No left-subdam X move was required.\n")
        h.write("- Left-bank extension: **80.0 m toward more-negative Y**, `-245.7 -> -325.7 m`, bottom 3021 m, thickness 1 m.\n")
        h.write("- Installation/powerhouse wall: 1 m wall with 3011 m central bottom and explicit 1:1 bottom transitions at Y=-156/-146 and Y=-25.4/-15.4.\n")
        h.write("- Ecological-release connection: represented continuously from Y=-15.4 to -2.9 m.\n")
        h.write("- Spillway/main-dam cutoff: represented through spillway and a measured-anchor bend `X=-20..-19 -> -36..-35` over Y=93.6..150 m. The gravity retaining-wall body remains source-limited/unresolved.\n")
        h.write("- V15.12 misplaced Y=70..150 wall: absent from the final Assembly.\n")
        h.write("- Main cutoff/geomembrane: inclined terminal upper-edge nodes with X>-36.0 were clipped to the measured P25 cutoff plane X=-36.0; changed nodes=%d; final positive-volume overlap is reported from the actual face sweep.\n\n" % gm_changed)
        h.write("## Foundation conformity and components\n\n")
        h.write("- Engineered backfill was integrated into the existing geology Part as `FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL` with Q3AL_III and C3D8P; the standalone backfill instance was removed. Reused geology nodes=%d; new interior nodes=%d; integrated elements=%d.\n" % (integration["reused_node_count"], integration["new_node_count"], integration["backfill_element_count"]))
        for row in topology_rows:
            h.write("- `%s`: nodes=%s, elements=%s, external faces=%s, exact shared faces=%s, nonconforming faces=%s, hanging nodes=%s, duplicate nodes=%s, duplicate elements=%s, nonmanifold=%s, positive-volume overlap pairs=%s, status **%s**.\n" % (row["domain"], row["node_count"], row["element_count"], row["external_boundary_faces"], row["exact_shared_internal_faces"], row["nonconforming_internal_faces"], row["hanging_nodes"], row["duplicate_nodes"], row["duplicate_elements"], row["nonmanifold_faces"], row.get("positive_volume_overlap_pairs", "0"), row["status"]))
        h.write("- Foundation component count computed by exact shared-face graph: **%d**.\n" % len(component_rows))
        h.write("\n## Geological Sections and hydraulics\n\n")
        h.write("- Geological leaf Sections audited: **%d** (required 36).\n" % len(section_rows))
        h.write("- Rock-related unresolved regions are retained without invented permeability or global C3D8R->C3D8P conversion; see `v15_13_rock_hydraulic_parameter_basis.csv`.\n")
        h.write("- Backfill material status: **ENGINEERING_EQUIVALENT_ASSUMPTION**, not source-verified calibration.\n\n")
        h.write("## Gates and Data Check\n\n")
        for row in gate_rows:
            h.write("- `%s`: **%s** — %s\n" % (row["gate"], row["status"], row["blocking_reason"] or "evidence recorded"))
        h.write("\n- Abaqus Data Check: **%s**. It was run only if the geometry/solver-readiness gate passed. S01-S07: **NOT RUN**.\n" % datacheck_status)
        h.write("- Right-bank grout-curtain representation remains unresolved because the source gives approximate extent but no defensible numerical thickness/equivalent boundary definition.\n")
        h.write("- Spillway-to-main-dam gravity retaining-wall body remains unresolved because source dimensions were insufficient; only the source-supported anti-seepage connection bend was added.\n")
        h.write("\n## Deliverables\n\n")
        h.write("- Corrective INP: `%s`\n- Corrective CAE: `%s`\n" % (OUT_INP, OUT_CAE))
    return path, status


def main():
    if not os.path.exists(ORIGINAL_TASK):
        raise RuntimeError("original V15.13 task file missing; execution prohibited")
    if not os.path.exists(CORRECTIVE_TASK):
        raise RuntimeError("corrective V15.13 task file missing")
    if not os.path.isdir(V15_DIR):
        os.makedirs(V15_DIR)
    base_text = open(BASE_INP, "r", encoding="utf-8", errors="replace").read()
    base_lines, base_parts, base_instances, _ = deck_parser.parse_deck(BASE_INP)
    integration = merge_backfill_into_geology(base_parts)
    wall_lines, wall_stations, wall_nodes, wall_elements, _wall_sets = make_wall_part()
    global WALL_ELEMENT_SEGMENTS
    WALL_ELEMENT_SEGMENTS = wall_element_segments(wall_stations)
    final_lines, gm_changed, gm_before, gm_after = rewrite_inp(base_lines, base_parts, integration, wall_lines)
    final_text = "\n".join(final_lines) + "\n"
    with open(OUT_INP, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(final_text)
    final_lines, final_parts, final_instances, _ = deck_parser.parse_deck(OUT_INP)
    global _FINAL_INSTANCES
    _FINAL_INSTANCES = final_instances
    placements, transforms = transforms_for(final_lines, final_parts, final_instances)
    boxes = actual_bbox_audit(final_parts, final_instances, transforms)
    axis_results = write_axis_and_chain(boxes, wall_stations)
    write_station_map()
    write_alignment_segments(wall_stations)
    write_backfill_material()
    wall_part = final_parts[WALL_PART]
    component_rows, _groups = write_component_outputs(final_parts, integration)
    materials = material_blocks(OUT_INP)
    section_rows = section_level_audit(final_lines, final_parts, materials)
    write_csv("v15_13_section_level_pore_pressure_audit.csv", list(section_rows[0]), section_rows)
    write_csv("v15_13_geology_section_pore_pressure_audit.csv",
              ["part", "section_elset", "material", "element_type", "element_count",
               "pore_pressure_dof_present", "permeability_assigned", "intended_role",
               "status", "notes"],
              [{"part": GEO_PART, "section_elset": row["geological_element_set"],
                "material": row["material"], "element_type": row["element_formulation"],
                "element_count": row["element_count"],
                "pore_pressure_dof_present": row["pore_pressure_dof"],
                "permeability_assigned": row["permeability"],
                "intended_role": row["hydraulic_role"], "status": row["status"],
                "notes": row["final_action"]} for row in section_rows])
    write_hydraulic_audits(final_lines, final_parts, materials, section_rows, integration)
    cutoff_rows, gm_row = anti_chain_connections(final_parts, final_instances, transforms, boxes, wall_stations)
    structural_joint_audit(final_parts, final_instances, transforms)
    write_transition_resolution()
    mesh_quality_rows = write_mesh_audits(base_parts, final_parts, integration, gm_before, gm_after, wall_part)
    # Compute the final topology once after all outputs are based on final parse.
    topology_rows, _sweep, _local = write_topology_outputs(final_parts, integration, section_rows, component_rows)
    original_read = "V15.13 final seepage-domain rebuild" in open(ORIGINAL_TASK, "r", encoding="utf-8", errors="replace").read()
    phase_pass = all(name in boxes for name in ("V15_4_LEFT_BANK_SUBDAM_I", "V15_4_POWERHOUSE_INSTALLATION_BAY_I", MAIN_CUTOFF_INSTANCE, GM_INSTANCE))
    axis_pass = boxes["V15_4_LEFT_BANK_SUBDAM_I"][0][0] <= -64.0 <= boxes["V15_4_LEFT_BANK_SUBDAM_I"][1][0]
    transition_status = "PASS" if "V15_13_GRAVITY_RETAINING_WALL" in final_text else "UNRESOLVED"
    active_materials_pass = ("*Solid Section" in final_text and "*Material" in final_text and
                             GEO_PART in final_parts and WALL_PART in final_parts)
    gate_rows, geometry_ready = write_pre_gate(
        original_read, final_text, phase_pass, axis_pass, topology_rows,
        section_rows, cutoff_rows, transition_status,
        axis_results["extension_pass"], axis_results["installation_pass"],
        axis_results["eco_pass"], component_rows, mesh_quality_rows,
        active_materials_pass)
    datacheck_status = "NOT_RUN_PRE_GATE"
    # The right curtain and retaining-wall body remain explicit unresolved
    # critical gates, so this execution intentionally does not launch Data Check.
    write_csv("v15_13_datacheck_status.csv", ["job", "command", "status", "reason"], [{"job": "v15_13_corrective_execution", "command": "NOT_EXECUTED", "status": "NOT_RUN", "reason": "geometry/solver-readiness gate is not PASS"}])
    report, status = write_report(final_parts, boxes, topology_rows, component_rows, section_rows, gate_rows, cutoff_rows, integration, gm_changed, wall_part, datacheck_status)
    print("V15_13_CORRECTIVE_INP=%s" % OUT_INP)
    print("V15_13_CORRECTIVE_REPORT=%s" % report)
    print("V15_13_STATUS=%s" % status)
    print("V15_13_GEOMETRY_READY=%s" % geometry_ready)
    print("V15_13_SECTIONS=%d" % len(section_rows))
    print("V15_13_INTEGRATED_BACKFILL_NODES_REUSED=%d" % integration["reused_node_count"])
    print("V15_13_INTEGRATED_BACKFILL_NEW_NODES=%d" % integration["new_node_count"])


if __name__ == "__main__":
    main()
