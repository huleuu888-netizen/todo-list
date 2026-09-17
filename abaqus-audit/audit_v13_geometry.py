"""Audit geometric proximity between v13 appurtenances and the core system."""
from __future__ import print_function

import csv
import math
import os

import build_v13_models
import repair_v12_3d


ROOT = os.path.abspath(os.path.join(os.getcwd(), "abaqus-audit"))
SOURCE = os.path.join(
    ROOT, "3d-v12",
    "doub_hydropower_part25_geometric_solids_v12_hydro_corrected.inp")
OUTPUT = os.path.join(ROOT, "3d-v13", "v13_support_candidates.csv")


def coordinates(instance, part_name, parts):
    return [
        (label, repair_v12_3d.global_coord(instance, part_name, coord))
        for label, coord in parts[part_name]["nodes"].items()
    ]


def bbox(points):
    coords = [point for _, point in points]
    return tuple((min(point[axis] for point in coords),
                  max(point[axis] for point in coords)) for axis in range(3))


def bbox_distance(a, b):
    delta = []
    for axis in range(3):
        if a[axis][1] < b[axis][0]:
            delta.append(b[axis][0] - a[axis][1])
        elif b[axis][1] < a[axis][0]:
            delta.append(a[axis][0] - b[axis][1])
        else:
            delta.append(0.0)
    return math.sqrt(sum(value * value for value in delta)), delta


def nearest_nodes(a, b):
    best = (float("inf"), None, None)
    for label_a, point_a in a:
        for label_b, point_b in b:
            distance = math.sqrt(sum(
                (point_a[axis] - point_b[axis]) ** 2 for axis in range(3)))
            if distance < best[0]:
                best = (distance, label_a, label_b)
    return best


def fmt_box(value):
    return ";".join("%.6g:%.6g" % pair for pair in value)


def main():
    _, source_parts, instances, _ = repair_v12_3d.parse_deck(SOURCE)
    parts = repair_v12_3d.corrected_parts(source_parts)
    instance_parts = dict(instances)
    all_coords = dict(
        (instance, coordinates(instance, part, parts))
        for instance, part in instances)
    all_boxes = dict((name, bbox(points)) for name, points in all_coords.items())
    core = [
        name for name, _ in instances
        if name not in build_v13_models.APPURTENANT
    ]
    rows = []
    for appurtenant in sorted(build_v13_models.APPURTENANT):
        if appurtenant not in instance_parts:
            continue
        candidates = []
        for support in core:
            box_distance, axis_gap = bbox_distance(
                all_boxes[appurtenant], all_boxes[support])
            candidates.append((
                box_distance, support, axis_gap))
        candidates.sort(key=lambda item: (item[0], item[1]))
        for rank, candidate in enumerate(candidates[:3], 1):
            box_distance, support, axis_gap = candidate
            node_distance, app_node, support_node = nearest_nodes(
                all_coords[appurtenant], all_coords[support])
            rows.append({
                "instance": appurtenant,
                "instance_bbox_xyz": fmt_box(all_boxes[appurtenant]),
                "candidate_rank": rank,
                "support_instance": support,
                "support_bbox_xyz": fmt_box(all_boxes[support]),
                "bbox_gap_m": "%.9g" % box_distance,
                "axis_gap_xyz_m": ";".join("%.9g" % value for value in axis_gap),
                "nearest_node_distance_m": "%.9g" % node_distance,
                "instance_node": app_node,
                "support_node": support_node,
                "bbox_overlap": "YES" if box_distance == 0.0 else "NO",
            })
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    fields = [
        "instance", "instance_bbox_xyz", "candidate_rank",
        "support_instance", "support_bbox_xyz", "bbox_gap_m",
        "axis_gap_xyz_m", "nearest_node_distance_m",
        "instance_node", "support_node", "bbox_overlap",
    ]
    with open(OUTPUT, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print("SUPPORT_AUDIT=%s" % OUTPUT)
    for row in rows:
        if row["candidate_rank"] == 1:
            print("%s -> %s bbox_gap=%s node_gap=%s overlap=%s" % (
                row["instance"], row["support_instance"], row["bbox_gap_m"],
                row["nearest_node_distance_m"], row["bbox_overlap"]))


if __name__ == "__main__":
    main()
