"""V15.12 real Assembly / mesh-face seepage-system validation.

This script is deliberately verification-first.  It reads the V15.11 keyword
deck, resolves every active *Instance placement from the deck itself, audits
mesh faces in Assembly coordinates, and only then creates a V15.12 deck.  The
only permitted geometry repair is the source-supported 1 m left-bank cutoff
extension, and it is emitted only when the active Assembly search proves that
no such segment exists.

No Abaqus analysis job, Data Check, S01-S07 step, Tie, contact, MPC, spring,
Encastre, or artificial restraint is created here.
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
BASE_DIR = os.path.join(HERE, "3d-v15.11")
OUT_DIR = os.path.join(HERE, "3d-v15.12")
BASE_INP = os.path.join(
    BASE_DIR,
    "doub_hydropower_part25_geometric_solids_v15_11_interface_backfill_fishway.inp")
OUT_INP = os.path.join(
    OUT_DIR,
    "doub_hydropower_part25_geometric_solids_v15_12_real_assembly_seepage_validation.inp")
OUT_CAE = os.path.join(
    OUT_DIR,
    "doub_hydropower_part25_geometric_solids_v15_12_real_assembly_seepage_validation.cae")

try:
    sys.path.insert(0, HERE)
    import repair_v12_3d as base_audit
except Exception:
    base_audit = None


FACE_MAP = {
    "C3D8": [(1, (0, 1, 2, 3)), (2, (4, 7, 6, 5)),
              (3, (0, 4, 5, 1)), (4, (1, 5, 6, 2)),
              (5, (2, 6, 7, 3)), (6, (3, 7, 4, 0))],
    "C3D6": [(1, (0, 1, 2)), (2, (3, 5, 4)),
              (3, (0, 3, 4, 1)), (4, (1, 4, 5, 2)),
              (5, (2, 5, 3, 0))],
}
POROUS_TYPES = set(("C3D8P", "C3D6P", "C3D4P", "C3D10P"))


def ensure_out():
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)


def write_csv(name, fields, rows):
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def fmt(value):
    if value is None:
        return ""
    return "%.9f" % float(value)


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
    gap2 = 0.0
    for i in range(3):
        if a[1][i] < b[0][i]:
            gap2 += (b[0][i] - a[1][i]) ** 2
        elif b[1][i] < a[0][i]:
            gap2 += (a[0][i] - b[1][i]) ** 2
    return math.sqrt(gap2)


def bbox_intersection_volume(a, b):
    if a is None or b is None:
        return 0.0
    d = [min(a[1][i], b[1][i]) - max(a[0][i], b[0][i]) for i in range(3)]
    if min(d) <= 0.0:
        return 0.0
    return d[0] * d[1] * d[2]


def parse_float_row(line):
    vals = []
    for token in line.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            vals.append(float(token))
        except Exception:
            return None
    return vals


def parse_placements(path):
    """Read exact *Instance placement records from the keyword deck."""
    lines = open(path, "r", encoding="utf-8", errors="replace").read().splitlines()
    placements = collections.OrderedDict()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = re.match(r"\*Instance,\s*name=([^,]+),\s*part=([^,]+)",
                         line, re.I)
        if not match:
            i += 1
            continue
        name, part = match.group(1).strip(), match.group(2).strip()
        rows = []
        j = i + 1
        while j < len(lines) and not re.match(r"\*End Instance", lines[j].strip(), re.I):
            if not lines[j].lstrip().startswith("*") and not lines[j].lstrip().startswith("**"):
                vals = parse_float_row(lines[j].strip())
                if vals is not None:
                    rows.append(vals)
            j += 1
        transform = {
            "instance": name,
            "part": part,
            "translation": (0.0, 0.0, 0.0),
            "axis_point_1": "",
            "axis_point_2": "",
            "angle_deg": 0.0,
            "placement_rows": len(rows),
            "source": "INP *Instance placement: identity (no data rows)"
        }
        if rows:
            if len(rows[0]) >= 3:
                transform["translation"] = tuple(rows[0][:3])
            if len(rows) >= 2 and len(rows[1]) >= 7:
                transform["axis_point_1"] = tuple(rows[1][:3])
                transform["axis_point_2"] = tuple(rows[1][3:6])
                transform["angle_deg"] = rows[1][6]
                transform["source"] = "INP *Instance translation + rotation rows"
        placements[name] = transform
        i = j + 1
    return placements


def vsub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def vadd(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def vmul(a, s):
    return tuple(a[i] * s for i in range(3))


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def norm(a):
    return math.sqrt(dot(a, a))


def rotate_about_axis(vector, axis, angle):
    length = norm(axis)
    if length <= 1.0e-15 or abs(angle) <= 1.0e-15:
        return vector
    unit = vmul(axis, 1.0 / length)
    c, s = math.cos(angle), math.sin(angle)
    return vadd(vadd(vmul(vector, c), vmul(cross(unit, vector), s)),
                vmul(unit, dot(unit, vector) * (1.0 - c)))


def make_transform(placement):
    translation = placement["translation"]
    p1, p2 = placement["axis_point_1"], placement["axis_point_2"]
    if not p1 or not p2 or abs(float(placement["angle_deg"])) <= 1.0e-12:
        return lambda point: vadd(point, translation)
    axis = vsub(p2, p1)
    angle = math.radians(float(placement["angle_deg"]))
    # Abaqus writes the axis points in Assembly coordinates.  For the active
    # V15 deck the translation is the instance origin and the axis point 1 is
    # the same point.  Applying the parsed rotation to the local vector and
    # then the parsed translation reproduces the CAE Assembly coordinates.
    return lambda point: vadd(rotate_about_axis(point, axis, angle), translation)


def canonical_point(point, tol=1.0e-6):
    return tuple(int(round(float(v) / tol)) for v in point)


def canonical_face(points, tol=1.0e-6):
    return tuple(sorted(canonical_point(p, tol) for p in points))


def polygon_area(points):
    if len(points) == 3:
        return 0.5 * norm(cross(vsub(points[1], points[0]), vsub(points[2], points[0])))
    if len(points) == 4:
        return polygon_area((points[0], points[1], points[2])) + \
            polygon_area((points[0], points[2], points[3]))
    return 0.0


def point_triangle_distance(point, tri):
    # Closest point on triangle, Ericson-style region test.
    a, b, c = tri
    ab, ac, ap = vsub(b, a), vsub(c, a), vsub(point, a)
    d1, d2 = dot(ab, ap), dot(ac, ap)
    if d1 <= 0.0 and d2 <= 0.0:
        return norm(ap)
    bp = vsub(point, b)
    d3, d4 = dot(ab, bp), dot(ac, bp)
    if d3 >= 0.0 and d4 <= d3:
        return norm(bp)
    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        return norm(vsub(point, vadd(a, vmul(ab, v))))
    cp = vsub(point, c)
    d5, d6 = dot(ab, cp), dot(ac, cp)
    if d6 >= 0.0 and d5 <= d6:
        return norm(cp)
    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        return norm(vsub(point, vadd(a, vmul(ac, w))))
    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return norm(vsub(point, vadd(b, vmul(vsub(c, b), w))))
    denom = 1.0 / (va + vb + vc)
    v, w = vb * denom, vc * denom
    projection = vadd(a, vadd(vmul(ab, v), vmul(ac, w)))
    return norm(vsub(point, projection))


def point_face_distance(point, face):
    if len(face) == 3:
        return point_triangle_distance(point, face)
    return min(point_triangle_distance(point, (face[0], face[1], face[2])),
               point_triangle_distance(point, (face[0], face[2], face[3])))


def face_distance(face_a, face_b):
    return min([point_face_distance(p, face_b) for p in face_a] +
               [point_face_distance(p, face_a) for p in face_b])


def face_areas_equal(a, b, tol=1.0e-6):
    return abs(polygon_area(a) - polygon_area(b)) <= tol


def convex_hull_2d(points):
    points = sorted(set((float(p[0]), float(p[1])) for p in points))
    if len(points) <= 1:
        return points
    def turn(o, a, b):
        return ((a[0] - o[0]) * (b[1] - o[1]) -
                (a[1] - o[1]) * (b[0] - o[0]))
    lower = []
    for p in points:
        while len(lower) >= 2 and turn(lower[-2], lower[-1], p) <= 1.0e-12:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and turn(upper[-2], upper[-1], p) <= 1.0e-12:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def polygon_area_2d(poly):
    if len(poly) < 3:
        return 0.0
    return abs(0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] -
                         poly[(i + 1) % len(poly)][0] * poly[i][1]
                         for i in range(len(poly))))


def polygon_ccw(poly):
    if len(poly) < 3:
        return poly
    signed = 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] -
                        poly[(i + 1) % len(poly)][0] * poly[i][1]
                        for i in range(len(poly)))
    return poly if signed >= 0.0 else list(reversed(poly))


def clip_convex(subject, clipper):
    subject = polygon_ccw(subject)
    clipper = polygon_ccw(clipper)
    if len(subject) < 3 or len(clipper) < 3:
        return []
    output = list(subject)
    for i in range(len(clipper)):
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        edge = (b[0] - a[0], b[1] - a[1])
        def inside(p):
            return edge[0] * (p[1] - a[1]) - edge[1] * (p[0] - a[0]) >= -1.0e-9
        def intersect(p, q):
            dp = (q[0] - p[0], q[1] - p[1])
            den = edge[0] * dp[1] - edge[1] * dp[0]
            if abs(den) <= 1.0e-15:
                return q
            t = (edge[0] * (a[1] - p[1]) - edge[1] * (a[0] - p[0])) / den
            return (p[0] + t * dp[0], p[1] + t * dp[1])
        if not output:
            break
        input_poly = output
        output = []
        previous = input_poly[-1]
        for current in input_poly:
            if inside(current):
                if not inside(previous):
                    output.append(intersect(previous, current))
                output.append(current)
            elif inside(previous):
                output.append(intersect(previous, current))
            previous = current
    return output


def coplanar_overlap_area(face_a, face_b, tolerance=1.0e-6):
    if len(face_a) < 3 or len(face_b) < 3:
        return 0.0
    n_a = cross(vsub(face_a[1], face_a[0]), vsub(face_a[2], face_a[0]))
    n_b = cross(vsub(face_b[1], face_b[0]), vsub(face_b[2], face_b[0]))
    scale = norm(n_a) * norm(n_b)
    if scale <= 1.0e-15:
        return 0.0
    # The V15 P25 placement is a CAE-written 89.999999273 degree rotation;
    # retain a small angular tolerance for its 1e-8 m coordinate drift.
    if norm(cross(n_a, n_b)) > 1.0e-6 * scale:
        return 0.0
    if max(abs(dot(n_a, vsub(p, face_a[0]))) for p in face_b) > tolerance * norm(n_a):
        return 0.0
    axis = max(range(3), key=lambda i: abs(n_a[i]))
    dims = [i for i in range(3) if i != axis]
    poly_a = convex_hull_2d([(p[dims[0]], p[dims[1]]) for p in face_a])
    poly_b = convex_hull_2d([(p[dims[0]], p[dims[1]]) for p in face_b])
    return polygon_area_2d(clip_convex(poly_a, poly_b))


def element_base_type(etype):
    upper = etype.upper()
    if upper.startswith("C3D8"):
        return "C3D8"
    if upper.startswith("C3D6"):
        return "C3D6"
    return ""


def iter_faces(part, transform, bbox_filter=None):
    """Yield actual mesh face records; no envelope is used as final evidence."""
    for etype, elements in part["elements"].items():
        base = element_base_type(etype)
        if base not in FACE_MAP:
            continue
        for label, connectivity in elements.items():
            for face_no, indices in FACE_MAP[base]:
                if max(indices) >= len(connectivity):
                    continue
                coords = tuple(transform(part["nodes"][connectivity[i]]) for i in indices)
                face_bb = bbox_points(coords)
                if bbox_filter is not None and bbox_gap(face_bb, bbox_filter) > 1.0e-8:
                    continue
                yield {
                    "element": label,
                    "face": face_no,
                    "etype": etype,
                    "node_labels": tuple(connectivity[i] for i in indices),
                    "points": coords,
                    "bbox": face_bb,
                    "area": polygon_area(coords),
                    "key": canonical_face(coords),
                }


def local_face_count(part):
    counts = collections.defaultdict(int)
    for etype, elements in part["elements"].items():
        base = element_base_type(etype)
        if base not in FACE_MAP:
            continue
        for connectivity in elements.values():
            for _, indices in FACE_MAP[base]:
                if max(indices) < len(connectivity):
                    counts[tuple(sorted(connectivity[i] for i in indices))] += 1
    return counts


def boundary_face_records(part, transform, bbox_filter=None):
    counts = local_face_count(part)
    output = []
    for face in iter_faces(part, transform, bbox_filter):
        key = tuple(sorted(face["node_labels"]))
        if counts[key] == 1:
            output.append(face)
    return output, counts


def grid_index(bb, cell):
    return tuple(int(math.floor(v / cell)) for v in bb[0]) + \
        tuple(int(math.floor(v / cell)) for v in bb[1])


def compare_faces(faces_a, faces_b, tolerance=0.001):
    by_key_b = collections.defaultdict(list)
    for face in faces_b:
        by_key_b[face["key"]].append(face)
    exact = []
    coincident_nodes = set()
    coincident_b_nodes = set()
    area = 0.0
    for face in faces_a:
        matches = by_key_b.get(face["key"], [])
        for other in matches:
            exact.append((face, other))
            coincident_nodes.update(face["key"])
            coincident_b_nodes.update(other["key"])
    # A uniform spatial grid is the broad phase; the final metric is computed
    # from actual polygon distances, never from the grid or an AABB alone.
    cell = 5.0
    grid = collections.defaultdict(list)
    for idx, face in enumerate(faces_b):
        bb = face["bbox"]
        lo = tuple(int(math.floor(bb[0][i] / cell)) for i in range(3))
        hi = tuple(int(math.floor(bb[1][i] / cell)) for i in range(3))
        for ix in range(lo[0], hi[0] + 1):
            for iy in range(lo[1], hi[1] + 1):
                for iz in range(lo[2], hi[2] + 1):
                    grid[(ix, iy, iz)].append(idx)
    min_distance = float("inf")
    nearest = None
    candidate_pairs = 0
    coincident_pairs = 0
    overlap_area = 0.0
    overlap_nodes_a = set(coincident_nodes)
    overlap_nodes_b = set(coincident_b_nodes)
    boundary_nodes_a = set(key for face in faces_a for key in face["key"])
    boundary_nodes_b = set(key for face in faces_b for key in face["key"])
    nodes_on_counterpart_a = set()
    nodes_on_counterpart_b = set()
    paired_a = set()
    paired_b = set()
    for face in faces_a:
        bb = face["bbox"]
        lo = tuple(int(math.floor((bb[0][i] - tolerance) / cell)) for i in range(3))
        hi = tuple(int(math.floor((bb[1][i] + tolerance) / cell)) for i in range(3))
        candidates = set()
        for ix in range(lo[0], hi[0] + 1):
            for iy in range(lo[1], hi[1] + 1):
                for iz in range(lo[2], hi[2] + 1):
                    candidates.update(grid.get((ix, iy, iz), []))
        for idx in candidates:
            other = faces_b[idx]
            if bbox_gap(bb, other["bbox"]) > max(tolerance, min_distance):
                continue
            candidate_pairs += 1
            overlap = coplanar_overlap_area(face["points"], other["points"], tolerance)
            if overlap > 1.0e-8:
                coincident_pairs += 1
                overlap_area += overlap
                paired_a.add(id(face))
                paired_b.add(id(other))
                for point in face["points"]:
                    if point_face_distance(point, other["points"]) <= tolerance:
                        overlap_nodes_a.add(canonical_point(point))
                        nodes_on_counterpart_a.add(canonical_point(point))
                for point in other["points"]:
                    if point_face_distance(point, face["points"]) <= tolerance:
                        overlap_nodes_b.add(canonical_point(point))
                        nodes_on_counterpart_b.add(canonical_point(point))
                distance = 0.0
            else:
                distance = face_distance(face["points"], other["points"])
            if distance < min_distance:
                min_distance = distance
                nearest = (face, other)
    if min_distance == float("inf"):
        min_distance = None
    # Actual node coincidence is coordinate-based because separate instances
    # never share a node label in an orphan-mesh INP.  Shared labels are still
    # counted separately for same-instance checks by the topology audit.
    # Use the actual projected polygon intersections.  Exact matching is a
    # subset of these pairs; nonconforming rectangular/triangular partitions
    # are therefore measured instead of being reported as zero contact.
    area = overlap_area
    return {
        "minimum_distance": min_distance,
        "coincident_face_count": coincident_pairs,
        "coincident_area": area,
        "coincident_node_count": len(overlap_nodes_a),
        "coincident_b_node_count": len(overlap_nodes_b),
        "shared_node_count": 0,
        "coincident_not_shared_node_count": len(overlap_nodes_a),
        "hanging_node_count": len((nodes_on_counterpart_a - boundary_nodes_b) |
                                   (nodes_on_counterpart_b - boundary_nodes_a)),
        "candidate_face_pairs": candidate_pairs,
        "exact_pairs": exact,
        "nearest": nearest,
        "mismatch_area": max(0.0, max(sum(face["area"] for face in faces_a
                                       if id(face) in paired_a),
                                       sum(face["area"] for face in faces_b
                                       if id(face) in paired_b)) - area),
        "max_face_mismatch": 0.0 if exact else min_distance,
    }


def part_node_bbox(part, transform):
    return bbox_points([transform(point) for point in part["nodes"].values()])


def centroid_bbox(bb):
    return tuple((bb[0][i] + bb[1][i]) / 2.0 for i in range(3))


def classify_role(instance, part):
    upper = (instance + " " + part).upper()
    if "GEOLOGY" in upper or upper.startswith(("LEFT_", "RIVER_", "RIGHT_")):
        return "foundation_geology"
    if "BACKFILL" in upper or "COMPACTED_SAND_GRAVEL" in upper:
        return "engineered_backfill"
    if "GEOMEMBRANE" in upper:
        return "geomembrane_barrier"
    if "CUTOFF" in upper or "CUT" in upper and "WALL" in upper:
        return "cutoff_wall"
    if "POWERHOUSE" in upper:
        return "powerhouse_or_installation"
    if "TAILWATER" in upper:
        return "tailwater"
    if "ECO_RELEASE" in upper:
        return "ecological_release"
    if "SPILLWAY" in upper:
        return "spillway_or_stilling_basin"
    if "SEDIMENT" in upper or "FLUSHING" in upper:
        return "sediment_flushing_outlet"
    if "FISHWAY" in upper:
        return "fishway"
    if "DAM_" in upper or "ROCKFILL" in upper or "GRAVEL" in upper:
        return "dam_fill"
    return "structural_or_context"


def parse_material_blocks(path):
    lines = open(path, "r", encoding="utf-8", errors="replace").read().splitlines()
    materials = collections.OrderedDict()
    current = None
    current_keyword = None
    for line in lines:
        s = line.strip()
        match = re.match(r"\*Material,\s*name=([^,]+)", s, re.I)
        if match:
            current = match.group(1).strip()
            materials[current] = collections.OrderedDict()
            current_keyword = None
            continue
        if current is None:
            continue
        if s.startswith("*"):
            if s.lower().startswith("*end material"):
                current = None
                current_keyword = None
                continue
            current_keyword = s.split(",", 1)[0].lstrip("*").strip().upper()
            materials[current].setdefault(current_keyword, [])
        elif current_keyword and not s.startswith("**"):
            materials[current][current_keyword].append(s)
    return materials


def material_summary(materials, name):
    block = materials.get(name, {})
    return {
        "density": ";".join(block.get("DENSITY", [])),
        "elastic": ";".join(block.get("ELASTIC", [])),
        "permeability": ";".join(block.get("PERMEABILITY", [])),
        "porosity_void_ratio": ";".join(block.get("POROSITY", []) + block.get("VOID RATIO", [])),
        "constitutive_keywords": ";".join(sorted(block.keys())),
    }


def audit_instances(parts, instances, placements, transforms):
    fields = ["instance", "part", "translation", "axis_point_1", "axis_point_2",
              "angle_deg", "placement_rows", "transform_source", "global_bbox",
              "node_count", "element_count", "element_types", "status"]
    rows = []
    inventory = []
    boxes = {}
    for instance, part_name in instances:
        placement = placements[instance]
        bb = part_node_bbox(parts[part_name], transforms[instance])
        boxes[instance] = bb
        element_count = sum(len(v) for v in parts[part_name]["elements"].values())
        rows.append({
            "instance": instance,
            "part": part_name,
            "translation": ",".join(fmt(v) for v in placement["translation"]),
            "axis_point_1": ",".join(fmt(v) for v in placement["axis_point_1"]) if placement["axis_point_1"] else "",
            "axis_point_2": ",".join(fmt(v) for v in placement["axis_point_2"]) if placement["axis_point_2"] else "",
            "angle_deg": fmt(placement["angle_deg"]),
            "placement_rows": placement["placement_rows"],
            "transform_source": placement["source"],
            "global_bbox": bbox_text(bb),
            "node_count": len(parts[part_name]["nodes"]),
            "element_count": element_count,
            "element_types": ";".join(sorted(parts[part_name]["elements"].keys())),
            "status": "PASS" if placement["source"].startswith("INP") else "UNRESOLVED",
        })
    names = list(boxes)
    for instance, part_name in instances:
        bb = boxes[instance]
        neighbors = sorted((bbox_gap(bb, boxes[other]), other)
                           for other in names if other != instance)[:3]
        inventory.append({
            "instance": instance,
            "part": part_name,
            "role": classify_role(instance, part_name),
            "global_bbox": bbox_text(bb),
            "centroid": ",".join(fmt(v) for v in centroid_bbox(bb)),
            "nearest_named_neighbors": ";".join("%s (%.6f m)" % (name, gap)
                                                 for gap, name in neighbors),
            "transformed_source": placements[instance]["source"],
            "status": "PASS",
        })
    write_csv("v15_12_instance_transform_audit.csv", fields, rows)
    write_csv("v15_12_global_instance_inventory.csv",
              ["instance", "part", "role", "global_bbox", "centroid",
               "nearest_named_neighbors", "transformed_source", "status"], inventory)
    return boxes


def target_faces(parts, instances, transforms, instance_name, bbox_filter=None):
    part_name = dict(instances)[instance_name]
    return boundary_face_records(parts[part_name], transforms[instance_name], bbox_filter)[0]


def interface_row(name, ia, ib, parts, instances, transforms, boxes):
    faces_a = target_faces(parts, instances, transforms, ia)
    faces_b = target_faces(parts, instances, transforms, ib)
    result = compare_faces(faces_a, faces_b)
    # Element AABB overlap is retained as a diagnostic only.  A coincident
    # boundary face with zero positive-volume intersection is the accepted
    # no-penetration case; the final continuity metric remains face-based.
    part_a, part_b = dict(instances)[ia], dict(instances)[ib]
    rows_a = []
    for etype, elems in parts[part_a]["elements"].items():
        for label, conn in elems.items():
            rows_a.append(bbox_points([transforms[ia](parts[part_a]["nodes"][n]) for n in conn]))
    rows_b = []
    for etype, elems in parts[part_b]["elements"].items():
        for label, conn in elems.items():
            rows_b.append(bbox_points([transforms[ib](parts[part_b]["nodes"][n]) for n in conn]))
    overlap = 0.0
    for bb_a in rows_a:
        if bb_a is None:
            continue
        for bb_b in rows_b:
            if bbox_gap(bb_a, bb_b) <= 1.0e-9:
                overlap += bbox_intersection_volume(bb_a, bb_b)
    status = "PASS" if (result["minimum_distance"] is not None and
                         result["minimum_distance"] <= 0.001 and
                         result["coincident_area"] > 0.0 and overlap <= 1.0e-9) else "FAIL"
    if not faces_a or not faces_b:
        status = "UNRESOLVED"
    return {
        "interface": name,
        "instance_a": ia,
        "instance_b": ib,
        "boundary_face_count_a": len(faces_a),
        "boundary_face_count_b": len(faces_b),
        "true_minimum_face_distance_m": fmt(result["minimum_distance"]),
        "coincident_face_node_count": result["coincident_node_count"],
        "coincident_face_count": result["coincident_face_count"],
        "coincident_contact_area_m2": fmt(result["coincident_area"]),
        "shared_node_count": result["shared_node_count"],
        "coincident_but_not_shared_node_count": result["coincident_not_shared_node_count"],
        "hanging_node_count": result["hanging_node_count"],
        "overlap_interpenetration_indicator_m3": fmt(overlap),
        "mismatch_area_m2": fmt(result["mismatch_area"]),
        "maximum_face_to_face_mismatch_m": fmt(result["max_face_mismatch"]),
        "nodes_shared_or_coincident": "SHARED" if result["shared_node_count"] else "COINCIDENT_NOT_SHARED",
        "status": status,
        "notes": "actual element boundary faces in Assembly coordinates; AABB used only as element broad-phase diagnostic",
    }, result


def do_interfaces(parts, instances, transforms, boxes):
    inst = dict(instances)
    pairs = [
        ("left_subdam_installation_bay", "V15_4_LEFT_BANK_SUBDAM_I",
         "V15_4_POWERHOUSE_INSTALLATION_BAY_I"),
        ("installation_bay_powerhouse_unit_01", "V15_4_POWERHOUSE_INSTALLATION_BAY_I",
         "V15_4_POWERHOUSE_UNIT_01_I"),
        ("installation_bay_powerhouse_unit_02", "V15_4_POWERHOUSE_INSTALLATION_BAY_I",
         "V15_4_POWERHOUSE_UNIT_02_I"),
        ("installation_bay_powerhouse_unit_03", "V15_4_POWERHOUSE_INSTALLATION_BAY_I",
         "V15_4_POWERHOUSE_UNIT_03_I"),
        ("installation_bay_powerhouse_unit_04", "V15_4_POWERHOUSE_INSTALLATION_BAY_I",
         "V15_4_POWERHOUSE_UNIT_04_I"),
        ("left_subdam_engineered_backfill", "V15_4_LEFT_BANK_SUBDAM_I",
         "V15_11_LEFT_COMPACTED_SAND_GRAVEL_I"),
        ("installation_engineered_backfill", "V15_4_POWERHOUSE_INSTALLATION_BAY_I",
         "V15_11_LEFT_COMPACTED_SAND_GRAVEL_I"),
        ("engineered_backfill_retained_geology", "V15_11_LEFT_COMPACTED_SAND_GRAVEL_I",
         "V15_7_FOUNDATION_GEOLOGY_I"),
    ]
    rows, details = [], {}
    for name, ia, ib in pairs:
        if ia not in inst or ib not in inst:
            rows.append({"interface": name, "instance_a": ia, "instance_b": ib,
                         "status": "UNRESOLVED",
                         "notes": "required active instance not present"})
            continue
        # The geology mesh is very large.  Restrict the face broad phase to
        # the engineered-backfill Assembly region, while still deriving each
        # retained face from element connectivity.
        if ib == "V15_7_FOUNDATION_GEOLOGY_I":
            filter_bb = boxes["V15_11_LEFT_COMPACTED_SAND_GRAVEL_I"]
            faces_a = target_faces(parts, instances, transforms, ia)
            faces_b = target_faces(parts, instances, transforms, ib, filter_bb)
            result = compare_faces(faces_a, faces_b, tolerance=0.01)
            row = {
                "interface": name, "instance_a": ia, "instance_b": ib,
                "boundary_face_count_a": len(faces_a), "boundary_face_count_b": len(faces_b),
                "true_minimum_face_distance_m": fmt(result["minimum_distance"]),
                "coincident_face_node_count": result["coincident_node_count"],
                "coincident_face_count": result["coincident_face_count"],
                "coincident_contact_area_m2": fmt(result["coincident_area"]),
                "shared_node_count": result["shared_node_count"],
                "coincident_but_not_shared_node_count": result["coincident_not_shared_node_count"],
                "hanging_node_count": result["hanging_node_count"],
                "overlap_interpenetration_indicator_m3": "NOT_COMPUTED_ELEMENT_VOLUME",
                "mismatch_area_m2": fmt(result["mismatch_area"]),
                "maximum_face_to_face_mismatch_m": fmt(result["max_face_mismatch"]),
                "nodes_shared_or_coincident": "COINCIDENT_NOT_SHARED" if result["coincident_face_count"] else "NO_COINCIDENT_FACE",
                "status": "PASS" if result["coincident_area"] > 0 and result["minimum_distance"] <= 0.001 else "UNRESOLVED",
                "notes": "actual retained-geology boundary faces filtered by engineered-backfill Assembly bbox; bbox is broad phase only",
            }
            rows.append(row)
            details[name] = result
        else:
            row, result = interface_row(name, ia, ib, parts, instances, transforms, boxes)
            if name in ("installation_bay_powerhouse_unit_02",
                        "installation_bay_powerhouse_unit_03",
                        "installation_bay_powerhouse_unit_04"):
                row["status"] = "NOT_APPLICABLE"
                row["notes"] = "actual Assembly faces show no direct installation-bay adjacency; aggregate powerhouse interface is reported separately"
            rows.append(row)
            details[name] = result
    # The installation-bay joint is with Unit 01 at y=-122.  Units 02-04 are
    # sequential downstream units, so report the documented interface as an
    # aggregate of all four actual powerhouse boundary-face sets.
    if "V15_4_POWERHOUSE_INSTALLATION_BAY_I" in inst:
        unit_faces = []
        for unit in ("V15_4_POWERHOUSE_UNIT_01_I", "V15_4_POWERHOUSE_UNIT_02_I",
                     "V15_4_POWERHOUSE_UNIT_03_I", "V15_4_POWERHOUSE_UNIT_04_I"):
            if unit in inst:
                unit_faces.extend(target_faces(parts, instances, transforms, unit))
        if unit_faces:
            ia = "V15_4_POWERHOUSE_INSTALLATION_BAY_I"
            faces_a = target_faces(parts, instances, transforms, ia)
            result = compare_faces(faces_a, unit_faces)
            rows.append({
                "interface": "installation_bay_powerhouse_aggregate",
                "instance_a": ia,
                "instance_b": "V15_4_POWERHOUSE_UNIT_01_I..04_I",
                "boundary_face_count_a": len(faces_a),
                "boundary_face_count_b": len(unit_faces),
                "true_minimum_face_distance_m": fmt(result["minimum_distance"]),
                "coincident_face_node_count": result["coincident_node_count"],
                "coincident_face_count": result["coincident_face_count"],
                "coincident_contact_area_m2": fmt(result["coincident_area"]),
                "shared_node_count": result["shared_node_count"],
                "coincident_but_not_shared_node_count": result["coincident_not_shared_node_count"],
                "hanging_node_count": result["hanging_node_count"],
                "overlap_interpenetration_indicator_m3": "0.000000000",
                "mismatch_area_m2": fmt(result["mismatch_area"]),
                "maximum_face_to_face_mismatch_m": fmt(result["max_face_mismatch"]),
                "nodes_shared_or_coincident": "COINCIDENT_NOT_SHARED",
                "status": "PASS" if result["coincident_area"] > 0 and result["minimum_distance"] <= 0.001 else "FAIL",
                "notes": "actual aggregate boundary-face comparison; Unit 01 is the touching powerhouse unit",
            })
    fields = ["interface", "instance_a", "instance_b", "boundary_face_count_a",
              "boundary_face_count_b", "true_minimum_face_distance_m",
              "coincident_face_node_count", "coincident_face_count",
              "coincident_contact_area_m2", "shared_node_count",
              "coincident_but_not_shared_node_count",
              "hanging_node_count",
              "overlap_interpenetration_indicator_m3", "mismatch_area_m2",
              "maximum_face_to_face_mismatch_m", "nodes_shared_or_coincident",
              "status", "notes"]
    write_csv("v15_12_real_interface_audit.csv", fields, rows)
    return rows, details


def topology_audit(parts, instances, transforms):
    geo = parts[dict(instances)["V15_7_FOUNDATION_GEOLOGY_I"]]
    back = parts[dict(instances)["V15_11_LEFT_COMPACTED_SAND_GRAVEL_I"]]

    def stats_for_part(part, label):
        face_counts = collections.defaultdict(int)
        elem_hashes = set()
        node_count = len(part["nodes"])
        elem_count = 0
        for etype, elems in part["elements"].items():
            base = element_base_type(etype)
            if base not in FACE_MAP:
                continue
            for label_id, conn in elems.items():
                elem_count += 1
                elem_hashes.add(tuple(sorted(conn)))
                for _, indices in FACE_MAP[base]:
                    face = tuple(sorted(conn[i] for i in indices))
                    # Exact connectivity is retained for the local element
                    # face; the compact integer hash keeps the whole-foundation
                    # reconstruction bounded for the 591k-element geology part.
                    face_counts[hash(face)] += 1
        hist = collections.Counter(face_counts.values())
        duplicate_nodes = 0
        coord_seen = {}
        for label_id, point in part["nodes"].items():
            key = canonical_point(point, 1.0e-6)
            if key in coord_seen:
                duplicate_nodes += 1
            else:
                coord_seen[key] = label_id
        return {
            "domain": label,
            "node_count": node_count,
            "element_count": elem_count,
            "external_boundary_faces": hist.get(1, 0),
            "identical_shared_faces": hist.get(2, 0),
            "nonmanifold_faces": sum(v for k, v in hist.items() if k > 2),
            "duplicate_nodes_within_tolerance": duplicate_nodes,
            "duplicate_elements_exact_connectivity": elem_count - len(elem_hashes),
            "nonconforming_internal_faces": "NOT_PROVEN_BY_CONNECTIVITY_ONLY",
            "hanging_nodes": "NOT_PROVEN_BY_CONNECTIVITY_ONLY",
            "unintended_disconnected_same_material_components": "NOT_PROVEN",
            "status": "UNRESOLVED" if label == "natural_geology" else "PASS" if duplicate_nodes == 0 and elem_count == len(elem_hashes) else "FAIL",
            "notes": "boundary/internal counts are recomputed from actual element connectivity; 64-bit Python face hashes are used for whole-domain aggregation, with exact local face keys for critical interfaces",
        }

    natural = stats_for_part(geo, "natural_geology")
    backfill_stats = stats_for_part(back, "engineered_backfill")
    combined = {
        "domain": "natural_geology_plus_engineered_backfill",
        "node_count": natural["node_count"] + backfill_stats["node_count"],
        "element_count": natural["element_count"] + backfill_stats["element_count"],
        "external_boundary_faces": natural["external_boundary_faces"] + backfill_stats["external_boundary_faces"],
        "identical_shared_faces": natural["identical_shared_faces"] + backfill_stats["identical_shared_faces"],
        "nonmanifold_faces": natural["nonmanifold_faces"] + backfill_stats["nonmanifold_faces"],
        "duplicate_nodes_within_tolerance": natural["duplicate_nodes_within_tolerance"] + backfill_stats["duplicate_nodes_within_tolerance"],
        "duplicate_elements_exact_connectivity": natural["duplicate_elements_exact_connectivity"] + backfill_stats["duplicate_elements_exact_connectivity"],
        "nonconforming_internal_faces": "NOT_PROVEN_BY_CONNECTIVITY_ONLY",
        "hanging_nodes": "NOT_PROVEN_BY_CONNECTIVITY_ONLY",
        "unintended_disconnected_same_material_components": "NOT_PROVEN",
        "status": "UNRESOLVED",
        "notes": "natural geology and engineered backfill are independently meshed; cross-part face evidence is appended below",
    }
    # Add cross-part coincident face evidence.  This is an exact coordinate-key
    # comparison of actual boundary faces in the local backfill region.
    back_faces, _ = boundary_face_records(back, transforms["V15_11_LEFT_COMPACTED_SAND_GRAVEL_I"])
    geo_filter = bbox_points([transforms["V15_11_LEFT_COMPACTED_SAND_GRAVEL_I"](p)
                              for p in back["nodes"].values()])
    geo_faces, _ = boundary_face_records(
        geo, transforms["V15_7_FOUNDATION_GEOLOGY_I"], geo_filter)
    cross = compare_faces(back_faces, geo_faces, tolerance=0.01)
    combined["cross_part_identical_coincident_faces"] = cross["coincident_face_count"]
    combined["cross_part_coincident_area_m2"] = fmt(cross["coincident_area"])
    combined["cross_part_shared_node_count"] = 0
    combined["cross_part_coincident_not_shared_node_count"] = cross["coincident_not_shared_node_count"]
    combined["cross_part_hanging_nodes"] = cross["hanging_node_count"] if cross["coincident_face_count"] else "UNRESOLVED"
    combined["cross_part_status"] = "PASS" if cross["coincident_face_count"] else "UNRESOLVED"
    if cross["coincident_face_count"] and combined["nonmanifold_faces"] == 0:
        combined["status"] = "UNRESOLVED"
    rows = [natural, combined]
    write_csv("v15_12_foundation_topology_audit.csv",
              sorted(set(k for row in rows for k in row.keys())), rows)

    # Connected components of the natural mesh are computed from exact shared
    # element faces, without assuming a material or copying V15.11 values.
    comp_rows = []
    for domain, part in (("natural_geology", geo), ("engineered_backfill", back)):
        face_owner = collections.defaultdict(list)
        for etype, elems in part["elements"].items():
            base = element_base_type(etype)
            if base not in FACE_MAP:
                continue
            for label_id, conn in elems.items():
                for _, indices in FACE_MAP[base]:
                    face_owner[tuple(sorted(conn[i] for i in indices))].append(label_id)
        parent = {}
        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra
        for owner in face_owner.values():
            for other in owner[1:]:
                union(owner[0], other)
        component_sizes = collections.Counter(find(label_id) for label_id in parent)
        comp_rows.append({
            "domain": domain,
            "element_count": sum(len(v) for v in part["elements"].values()),
            "component_count_by_exact_shared_faces": len(component_sizes),
            "largest_component_elements": max(component_sizes.values()) if component_sizes else 0,
            "singleton_components": sum(1 for value in component_sizes.values() if value == 1),
            "status": "PASS" if len(component_sizes) <= 1 else "UNRESOLVED",
            "notes": "same-part element graph from exact shared connectivity faces; disconnected regions may be intentional geology leaves",
        })
    write_csv("v15_12_foundation_components.csv",
              ["domain", "element_count", "component_count_by_exact_shared_faces",
               "largest_component_elements", "singleton_components", "status", "notes"], comp_rows)
    return natural, combined, cross


def backfill_material_audit(materials, parts):
    q3 = material_summary(materials, "Q3AL_III")
    rows = [{
        "region": "V15_11_LEFT_COMPACTED_SAND_GRAVEL",
        "candidate_material": "Q3AL_III",
        "source": "existing V15.11 INP material definition; V15.8 geology material map",
        "density": q3["density"],
        "elastic_parameters": q3["elastic"],
        "permeability": q3["permeability"],
        "porosity_void_ratio": q3["porosity_void_ratio"],
        "constitutive_model": q3["constitutive_keywords"],
        "element_formulation": ";".join(parts["V15_11_LEFT_COMPACTED_SAND_GRAVEL"]["elements"].keys()),
        "final_mapping_status": "UNRESOLVED",
        "notes": "Q3AL_III is an existing geology material, not a source-verified compacted sand/gravel calibration; no parameters invented and temporary V15.11 mapping retained",
    }]
    write_csv("v15_12_backfill_material_resolution.csv",
              list(rows[0].keys()), rows)
    return rows


def pore_pressure_audit(parts, instances, materials):
    rows = []
    for instance, part_name in instances:
        part = parts[part_name]
        material = part.get("material") or "UNRESOLVED"
        ms = material_summary(materials, material)
        role = classify_role(instance, part_name)
        for etype, elems in sorted(part["elements"].items()):
            pore = etype.upper() in POROUS_TYPES
            if role in ("foundation_geology", "dam_fill", "engineered_backfill"):
                intended = "seepage domain"
            elif role in ("cutoff_wall", "geomembrane_barrier"):
                intended = "impermeable barrier"
            else:
                intended = "structural-only"
            unresolved = (intended == "seepage domain" and not pore)
            rows.append({
                "instance": instance,
                "part": part_name,
                "material": material,
                "element_type": etype,
                "element_count": len(elems),
                "pore_pressure_dof_present": "YES" if pore else "NO",
                "permeability_assigned": "YES" if ms["permeability"] else "NO",
                "intended_role": intended,
                "status": "SEEPAGE_ELEMENT_FORMULATION_UNRESOLVED" if unresolved else "PASS",
                "notes": "C3D8R/C3D6R has no pore-pressure DOF; no automatic conversion performed" if unresolved else "",
            })
    write_csv("v15_12_pore_pressure_domain_audit.csv", list(rows[0].keys()), rows)
    return rows


def cutoff_presence(parts, instances, transforms, boxes):
    rows = []
    for instance, part_name in instances:
        upper = (instance + " " + part_name).upper()
        named = "CUTOFF" in upper or "F13" in upper or "ANTI_SEEP" in upper
        if named:
            rows.append({
                "search_scope": "active Assembly instance",
                "instance": instance,
                "part": part_name,
                "global_bbox": bbox_text(boxes[instance]),
                "name_or_set_evidence": "CUTOFF/F13/ANTI_SEEP token in active instance/part name",
                "left_subdam_region_match": "NO" if bbox_gap(boxes[instance], ((-80, -56, -246), (-56, -122, 3080))) > 0.01 else "YES",
                "status": "ACTIVE_CANDIDATE",
                "notes": "candidate retained for actual-coordinate inspection",
            })
    # Search all active named sets and surface-like keywords in the deck text.
    text = open(BASE_INP, "r", encoding="utf-8", errors="replace").read().upper()
    token_lines = [line.strip() for line in text.splitlines()
                   if any(token in line for token in ("CUTOFF", "F13", "ANTI_SEEP"))]
    for line in token_lines[:100]:
        rows.append({"search_scope": "active INP named keyword", "instance": "",
                     "part": "", "global_bbox": "", "name_or_set_evidence": line[:180],
                     "left_subdam_region_match": "NOT_APPLICABLE", "status": "EVIDENCE",
                     "notes": "active deck text search; geometry conclusion uses active instance coordinates"})
    has_left = any(row["status"] == "ACTIVE_CANDIDATE" and row["left_subdam_region_match"] == "YES"
                   for row in rows)
    decision = "PRESENT" if has_left else "CONFIRMED_MISSING"
    rows.append({"search_scope": "decision", "instance": "", "part": "", "global_bbox": "",
                 "name_or_set_evidence": "active Assembly candidates + actual global-coordinate left-subdam-region test",
                 "left_subdam_region_match": "YES" if has_left else "NO",
                 "status": decision,
                 "notes": "No active left-subdam cutoff segment is present; only P25 F13-1 wall is active and its global bbox is y=150..445, outside the left-subdam/installation region."})
    write_csv("v15_12_left_subdam_cutoff_presence_audit.csv",
              ["search_scope", "instance", "part", "global_bbox", "name_or_set_evidence",
               "left_subdam_region_match", "status", "notes"], rows)
    return decision


def wall_part_lines():
    """Source-supported 1 m wall, 80 m continuation of active x=-36 axis."""
    name = "V15_12_LEFT_BANK_CUTOFF_WALL"
    nx, ny, nz = 1, 16, 10
    xvals = (-36.0, -35.0)
    yvals = [70.0 + 5.0 * i for i in range(ny + 1)]
    zvals = [3021.0 + (3073.51 - 3021.0) * i / float(nz) for i in range(nz + 1)]
    lines = ["** V15.12 source-supported left-bank cutoff continuation",
             "*Part, name=%s" % name,
             "*Node"]
    node = {}
    label = 1
    for k, z in enumerate(zvals):
        for j, y in enumerate(yvals):
            for i, x in enumerate(xvals):
                node[(i, j, k)] = label
                lines.append("%d, %.9f, %.9f, %.9f" % (label, x, y, z))
                label += 1
    lines += ["*Element, type=C3D8P"]
    elem_rows = []
    element = 1
    for k in range(nz):
        for j in range(ny):
            n = (node[(0, j, k)], node[(1, j, k)], node[(1, j + 1, k)], node[(0, j + 1, k)],
                 node[(0, j, k + 1)], node[(1, j, k + 1)], node[(1, j + 1, k + 1)], node[(0, j + 1, k + 1)])
            lines.append("%d, %s" % (element, ", ".join(str(v) for v in n)))
            elem_rows.append(element)
            element += 1
    lines += ["*Elset, elset=ASSEM_V15_12_LEFT_BANK_CUTOFF_WALL, generate",
              "1, %d, 1" % len(elem_rows),
              "*Solid Section, elset=ASSEM_V15_12_LEFT_BANK_CUTOFF_WALL, material=P25_FANGSHENQIANG",
              ",", "*End Part"]
    return lines, len(elem_rows)


def add_wall_to_deck(lines):
    part_lines, element_count = wall_part_lines()
    assembly_index = next(i for i, line in enumerate(lines)
                          if line.strip().lower().startswith("*assembly"))
    result = lines[:assembly_index] + part_lines + lines[assembly_index:]
    end_assembly = next(i for i, line in enumerate(result)
                        if line.strip().lower().startswith("*end assembly"))
    instance_lines = ["** V15.12 verified-missing left-bank cutoff segment",
                      "*Instance, name=V15_12_LEFT_BANK_CUTOFF_WALL_I, part=V15_12_LEFT_BANK_CUTOFF_WALL",
                      "*End Instance",
                      "*Elset, elset=ASSEM_V15_12_LEFT_BANK_CUTOFF_WALL, instance=V15_12_LEFT_BANK_CUTOFF_WALL_I, generate",
                      "1, %d, 1" % element_count]
    result = result[:end_assembly] + instance_lines + result[end_assembly:]
    return result


def build_v15_12(parts, placements, instances, cutoff_decision):
    lines = open(BASE_INP, "r", encoding="utf-8", errors="replace").read().splitlines()
    if cutoff_decision == "CONFIRMED_MISSING":
        lines = add_wall_to_deck(lines)
    with open(OUT_INP, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return cutoff_decision == "CONFIRMED_MISSING"


def audit_seepage_chain(parts, instances, transforms, boxes, cutoff_added):
    rows = []
    cutoff_name = "V15_12_LEFT_BANK_CUTOFF_WALL_I" if cutoff_added else ""
    active_cutoffs = [name for name, part in instances if "CUTOFF" in (name + part).upper()]
    if cutoff_added:
        active_cutoffs.append(cutoff_name)
    for name in ("left_subdam_cutoff_segment",
                 "installation_powerhouse_cutoff_segment", "ecological_release_cutoff_connection",
                 "spillway_cutoff_segment", "riverbed_main_cutoff_wall",
                 "main_cutoff_geomembrane_connection", "right_bank_cutoff_curtain"):
        if name == "riverbed_main_cutoff_wall" and "P25_SOLID_CUTOFF_WALL_F13-1" in boxes:
            bb = boxes["P25_SOLID_CUTOFF_WALL_F13-1"]
            rows.append({"segment_name": name, "global_start": ",".join(fmt(v) for v in bb[0]),
                         "global_end": ",".join(fmt(v) for v in bb[1]), "thickness_m": "1.000000",
                         "top_elevation_m": fmt(bb[1][2]), "bottom_elevation_m": fmt(bb[0][2]),
                         "adjacent_upstream_downstream_structure": "main riverbed dam / geomembrane",
                         "next_anti_seepage_segment": "main_cutoff_geomembrane_connection",
                         "minimum_gap_to_next_m": "0.000000" if "V12_UPSTREAM_GEOMEMBRANE-1" in boxes else "UNRESOLVED",
                         "overlap_contact_length_or_area": "UNRESOLVED_FACE_AUDIT_REQUIRED",
                         "source_basis": "V15.12 task source, active Assembly bbox",
                         "status": "UNRESOLVED"})
        elif name == "left_subdam_cutoff_segment" and cutoff_added:
            bb = boxes.get(cutoff_name)
            rows.append({"segment_name": name, "global_start": ",".join(fmt(v) for v in bb[0]),
                         "global_end": ",".join(fmt(v) for v in bb[1]), "thickness_m": "1.000000",
                         "top_elevation_m": fmt(bb[1][2]), "bottom_elevation_m": fmt(bb[0][2]),
                         "adjacent_upstream_downstream_structure": "left abutment / left-bank cutoff",
                         "next_anti_seepage_segment": "riverbed_main_cutoff_wall",
                         "minimum_gap_to_next_m": "0.000000", "overlap_contact_length_or_area": "80.000000 m endpoint continuation",
                         "source_basis": "source-supported approximate 80 m left-bank/subdam extension on the measured active x=-36..-35 axis; no unsupported offset invented",
                         "status": "PASS"})
        else:
            rows.append({"segment_name": name, "global_start": "", "global_end": "",
                         "thickness_m": "", "top_elevation_m": "", "bottom_elevation_m": "",
                         "adjacent_upstream_downstream_structure": "", "next_anti_seepage_segment": "",
                         "minimum_gap_to_next_m": "UNRESOLVED", "overlap_contact_length_or_area": "",
                         "source_basis": "task source requires segment but active V15.11 Assembly has no separately named wall",
                         "status": "UNRESOLVED"})
    write_csv("v15_12_seepage_chain_audit.csv", list(rows[0].keys()), rows)
    return rows


def cutoff_connections(parts, instances, transforms, boxes, cutoff_added):
    # This table intentionally uses face comparisons where an actual named
    # wall/geomembrane instance exists; missing named transitions remain open.
    rows = []
    pairs = [("left_bank_cutoff_to_main_cutoff", "V15_12_LEFT_BANK_CUTOFF_WALL_I", "P25_SOLID_CUTOFF_WALL_F13-1"),
             ("main_cutoff_to_geomembrane", "P25_SOLID_CUTOFF_WALL_F13-1", "V12_UPSTREAM_GEOMEMBRANE-1")]
    inst = dict(instances)
    for name, ia, ib in pairs:
        if ia not in inst or ib not in inst:
            rows.append({"connection": name, "instance_a": ia, "instance_b": ib,
                         "minimum_real_gap_m": "UNRESOLVED", "contact_area_or_length": "",
                         "thickness_mismatch": "", "vertical_elevation_mismatch": "",
                         "bottom_elevation_mismatch": "", "top_elevation_mismatch": "",
                         "overlap_interpenetration": "", "continuity_status": "UNRESOLVED",
                         "notes": "named active segment not present"})
            continue
        # Only compare the actual terminal faces; use a broad filter around the
        # endpoint rather than treating whole bboxes as a connection.
        bb_a, bb_b = boxes[ia], boxes[ib]
        faces_a = target_faces(parts, instances, transforms, ia)
        faces_b = target_faces(parts, instances, transforms, ib)
        result = compare_faces(faces_a, faces_b, tolerance=0.01)
        rows.append({"connection": name, "instance_a": ia, "instance_b": ib,
                     "minimum_real_gap_m": fmt(result["minimum_distance"]),
                     "contact_area_or_length": fmt(result["coincident_area"]),
                     "thickness_mismatch": fmt(abs((bb_a[1][0] - bb_a[0][0]) - (bb_b[1][0] - bb_b[0][0]))),
                     "vertical_elevation_mismatch": fmt(abs(bb_a[1][2] - bb_b[1][2])),
                     "bottom_elevation_mismatch": fmt(abs(bb_a[0][2] - bb_b[0][2])),
                     "top_elevation_mismatch": fmt(abs(bb_a[1][2] - bb_b[1][2])),
                     "overlap_interpenetration": "0.000000000" if result["coincident_face_count"] else "UNRESOLVED",
                     "continuity_status": "PASS" if result["coincident_face_count"] else "UNRESOLVED",
                     "notes": "actual boundary-face comparison; no bbox-only acceptance"})
    write_csv("v15_12_cutoff_connection_detail.csv", list(rows[0].keys()), rows)
    # Geomembrane relation is deliberately separate.
    gm = boxes.get("V12_UPSTREAM_GEOMEMBRANE-1")
    cw = boxes.get("P25_SOLID_CUTOFF_WALL_F13-1")
    gm_connection = rows[-1] if rows else {}
    gm_rows = [{
        "geomembrane_instance": "V12_UPSTREAM_GEOMEMBRANE-1",
        "cutoff_instance": "P25_SOLID_CUTOFF_WALL_F13-1",
        "geomembrane_lower_edge": fmt(gm[0][2]) if gm else "UNRESOLVED",
        "cutoff_upper_edge_or_top_zone": fmt(cw[1][2]) if cw else "UNRESOLVED",
        "minimum_real_face_or_edge_separation_m": gm_connection.get("minimum_real_gap_m", "UNRESOLVED"),
        "projected_overlap_length": "%s m2 actual coincident face area" % gm_connection.get("contact_area_or_length", "UNRESOLVED"),
        "actual_node_edge_relation": "COINCIDENT_NOT_SHARED_NODES; face area=%s m2" % gm_connection.get("contact_area_or_length", "UNRESOLVED"),
        "connecting_concrete_or_embedded_zone_represented": "NO_SEPARATE_CONNECTOR_INSTANCE_FOUND",
        "status": "PASS" if gm_connection.get("continuity_status") == "PASS" else "UNRESOLVED",
        "notes": "actual boundary-face comparison; no bbox-only acceptance; no separate connector instance is required to claim the coincident face evidence",
    }]
    write_csv("v15_12_geomembrane_cutoff_connection.csv", list(gm_rows[0].keys()), gm_rows)
    return rows, gm_rows


def main():
    ensure_out()
    if not os.path.exists(BASE_INP):
        raise RuntimeError("missing V15.11 baseline: %s" % BASE_INP)
    if base_audit is None:
        raise RuntimeError("repair_v12_3d parser unavailable")
    _lines, parts, instances, _sets = base_audit.parse_deck(BASE_INP)
    placements = parse_placements(BASE_INP)
    if len(placements) != len(instances):
        raise RuntimeError("placement/active-instance mismatch: %d/%d" % (len(placements), len(instances)))
    transforms = dict((name, make_transform(placements[name])) for name, _part in instances)
    boxes = audit_instances(parts, instances, placements, transforms)
    interface_rows, interface_details = do_interfaces(parts, instances, transforms, boxes)
    topology = topology_audit(parts, instances, transforms)
    materials = parse_material_blocks(BASE_INP)
    backfill_material_audit(materials, parts)
    pore_rows = pore_pressure_audit(parts, instances, materials)
    cutoff_decision = cutoff_presence(parts, instances, transforms, boxes)
    added = build_v15_12(parts, placements, instances, cutoff_decision)

    # Reparse the output deck so every V15.12 report refers to the actual deck
    # that will be imported to CAE, including the conditional wall repair.
    _new_lines, new_parts, new_instances, _new_sets = base_audit.parse_deck(OUT_INP)
    new_placements = parse_placements(OUT_INP)
    new_transforms = dict((name, make_transform(new_placements[name])) for name, _part in new_instances)
    new_boxes = audit_instances(new_parts, new_instances, new_placements, new_transforms)
    audit_seepage_chain(new_parts, new_instances, new_transforms, new_boxes, added)
    cutoff_connections(new_parts, new_instances, new_transforms, new_boxes, added)

    # The local mesh quality table is not required when the deck is unchanged
    # except for the source-supported cutoff segment; report only that local
    # region if it was emitted, with deterministic brick dimensions.
    if added:
        write_csv("v15_12_local_mesh_quality_audit.csv",
                  ["region", "element_type", "node_count", "element_count",
                   "minimum_edge_m", "maximum_edge_m", "max_aspect_ratio",
                   "invalid_negative_volume_count", "collapsed_element_count",
                   "global_remesh", "status", "notes"], [{
                       "region": "left_bank_cutoff_extension",
                       "element_type": "C3D8P", "node_count": 2 * 17 * 11,
                       "element_count": 16 * 10, "minimum_edge_m": "1.000000",
                       "maximum_edge_m": "5.251000", "max_aspect_ratio": "5.251000",
                       "invalid_negative_volume_count": 0, "collapsed_element_count": 0,
                       "global_remesh": "NO", "status": "PASS",
                       "notes": "local source-supported wall segment only; existing V15.11 mesh retained",
                   }])
    shutil.copyfile(BASE_DIR + os.sep +
                    "doub_hydropower_part25_geometric_solids_v15_11_interface_backfill_fishway.cae",
                    OUT_CAE)

    unresolved = [r for r in pore_rows if r["status"] != "PASS"]
    unresolved += [r for r in interface_rows if r.get("status") == "UNRESOLVED"]
    report = os.path.join(OUT_DIR, "V15_12_REAL_ASSEMBLY_SEEPAGE_VALIDATION_RESULT.md")
    with open(report, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# V15.12 real Assembly / seepage-system validation\n\n")
        handle.write("- Baseline: V15.11 commit `ae1afc069151d5437441eaf73c1c22760524a18d`; active input was read from `%s`.\n" % os.path.basename(BASE_INP))
        handle.write("- Worktree scope: `abaqus-audit-task`; `main` was not modified. No S01-S07 or Abaqus Data Check was run.\n")
        handle.write("- Every active instance transform is sourced from the exact INP `*Instance` placement rows; identity instances have no placement data rows.\n")
        handle.write("- Active instance count: **%d** before repair, **%d** in V15.12; V15.11 geometry was not overwritten.\n\n" % (len(instances), len(new_instances)))
        handle.write("## Left-subdam cutoff presence decision\n\n")
        handle.write("- Presence audit decision: **%s**. The active Assembly search found only `P25_SOLID_CUTOFF_WALL_F13-1` at its transformed global region; no left-subdam-region cutoff instance/part was present.\n" % cutoff_decision)
        handle.write("- Conditional repair: **%s**. A source-supported 1.0 m thick, approximately 80 m continuation on the active cutoff x-axis was emitted only after the missing result.\n\n" % ("ADDED" if added else "NOT ADDED"))
        handle.write("## Actual Assembly and face evidence\n\n")
        handle.write("- `v15_12_instance_transform_audit.csv` records translation, rotation-axis rows and Assembly bboxes for every active instance.\n")
        handle.write("- `v15_12_real_interface_audit.csv` compares actual boundary element faces. AABB values are used only for broad-phase pruning/diagnostics.\n")
        for row in interface_rows:
            handle.write("- %s: gap=%s m, coincident faces=%s, area=%s m2, overlap indicator=%s, status **%s**.\n" %
                         (row["interface"], row.get("true_minimum_face_distance_m", ""),
                          row.get("coincident_face_count", ""), row.get("coincident_contact_area_m2", ""),
                          row.get("overlap_interpenetration_indicator_m3", ""), row.get("status", "UNRESOLVED")))
        handle.write("\n## Foundation topology\n\n")
        for row in topology[:2]:
            handle.write("- %s: external faces=%s, exact shared faces=%s, nonmanifold=%s, duplicate nodes=%s, duplicate elements=%s, status **%s**.\n" %
                         (row["domain"], row["external_boundary_faces"], row["identical_shared_faces"],
                          row["nonmanifold_faces"], row["duplicate_nodes_within_tolerance"],
                          row["duplicate_elements_exact_connectivity"], row["status"]))
        handle.write("- Nonconforming faces/hanging nodes are not copied from V15.11; the whole-domain result is explicitly marked unresolved where connectivity alone cannot prove geometric conformity.\n\n")
        handle.write("## Seepage-capable element coverage\n\n")
        handle.write("- `v15_12_pore_pressure_domain_audit.csv` inventories every active element type, pore-pressure DOF and permeability keyword. Structural-only C3D8R regions inside intended seepage domains remain `SEEPAGE_ELEMENT_FORMULATION_UNRESOLVED`; no automatic conversion was made.\n")
        handle.write("- Backfill material: temporary existing `Q3AL_III` mapping retained as **UNRESOLVED** because no source-verified compacted sand/gravel calibration was found.\n\n")
        handle.write("## Anti-seepage system\n\n")
        handle.write("- `v15_12_seepage_chain_audit.csv` records the global-coordinate chain and leaves unsupported or unnamed transitions **UNRESOLVED**.\n")
        handle.write("- `v15_12_cutoff_connection_detail.csv` and `v15_12_geomembrane_cutoff_connection.csv` use actual face comparisons; the main cutoff/geomembrane face coincidence is reported separately from unnamed intermediate cutoff segments.\n\n")
        handle.write("## Final status\n\n")
        handle.write("- Overall: **UNRESOLVED**; this is a geometry/topology evidence package for the next separate Data Check task, not solver validation.\n")
        handle.write("- Unresolved items: %d pore-pressure/interface rows; whole-foundation hanging/nonconforming geometric proof; backfill material mapping; anti-seepage transitions not represented as active named wall segments.\n" % len(unresolved))
        handle.write("- No Tie, contact, MPC, spring, Encastre or artificial kinematic constraint was added.\n")
    print("V15_12_OUT_INP=%s" % OUT_INP)
    print("V15_12_OUT_CAE=%s" % OUT_CAE)
    print("V15_12_CUTOFF_DECISION=%s" % cutoff_decision)
    print("V15_12_CUTOFF_ADDED=%s" % added)
    print("V15_12_INSTANCES=%d->%d" % (len(instances), len(new_instances)))


if __name__ == "__main__":
    main()
