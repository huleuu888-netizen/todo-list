"""Extract Gate 1A singularity evidence from every v12 Abaqus MSG/DAT log."""
from __future__ import print_function

import csv
import glob
import os
import re


ROOT = os.path.abspath(os.path.join(os.getcwd(), "abaqus-audit"))
SOURCE_DIR = os.path.join(ROOT, "3d-v12")
OUTPUT_DIR = os.path.join(ROOT, "3d-v13")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "v13_singularity_instances.csv")

NODE_RE = re.compile(
    r"([A-Za-z0-9_\-]+)\.(\d+)\s+D\.O\.F\.\s*(\d+)", re.I)
EVENT_PATTERNS = (
    ("NUMERICAL_SINGULARITY", re.compile(r"NUMERICAL SINGULARITY", re.I)),
    ("ZERO_PIVOT", re.compile(r"ZERO PIVOT", re.I)),
    ("EXCESSIVE_RIGID_BODY_MOTION",
     re.compile(r"(EXCESSIVE.*(?:RIGID BODY|MOTION)|RIGID BODY.*EXCESSIVE)", re.I)),
    ("SOLVER_SINGULARITY",
     re.compile(r"SOLVER PROBLEM.*SINGULAR|SINGULAR MATRIX", re.I)),
)


def classification(instance):
    name = instance.upper()
    if name.startswith("FISHWAY_"):
        return (
            "fishway / small appurtenance (C)",
            "suppress in core; restore fishway group only after defining real support/contact")
    if name.startswith("SPILLWAY_"):
        return (
            "spillway structure (B)",
            "suppress in core; restore spillway group with supporting-foundation contact/tie")
    if name.startswith("POWERHOUSE_"):
        return (
            "powerhouse structure (B)",
            "suppress in core; restore powerhouse group with a verified foundation load path")
    if re.match(r"(LEFT|RIGHT)_BX0[123]_I$", name):
        return (
            "right/left-bank deformation body (D)",
            "suppress in core; retain only after actual overlap/support to bank geology is verified")
    if name.startswith(("P25_", "LEFT_", "RIGHT_", "RIVER_")):
        return (
            "main dam/foundation/geology (A)",
            "retain; repair only with shared nodes or a geometrically valid supporting interface")
    return (
        "other appurtenant structure (C)",
        "suppress in core; inspect geometry and restore only with source-supported load path")


def clean_context(lines, start, stop):
    chunks = []
    for line in lines[max(0, start):min(len(lines), stop)]:
        text = " ".join(line.strip().split())
        if text:
            chunks.append(text)
    return " | ".join(chunks)


def extract_file(path, records, general):
    with open(path, "r", errors="replace") as handle:
        lines = handle.readlines()
    for index, line in enumerate(lines):
        event = None
        for event_name, pattern in EVENT_PATTERNS:
            if pattern.search(line):
                event = event_name
                break
        if event is None:
            continue
        context = clean_context(lines, index, index + 4)
        match = NODE_RE.search(context)
        if match:
            instance, node, dof = match.groups()
            category, action = classification(instance)
            key = (instance, node, dof, event)
            if key not in records:
                records[key] = {
                    "instance": instance,
                    "node": node,
                    "dof": dof,
                    "event": event,
                    "source_file": os.path.basename(path),
                    "line": index + 1,
                    "context": context,
                    "category": category,
                    "action": action,
                }
        else:
            key = (os.path.basename(path), index + 1, event)
            if key not in general:
                general[key] = {
                    "instance": "",
                    "node": "",
                    "dof": "",
                    "event": event,
                    "source_file": os.path.basename(path),
                    "line": index + 1,
                    "context": context,
                    "category": "global/unspecified",
                    "action": "correlate with the immediately preceding solver node diagnostics",
                }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    records = {}
    general = {}
    paths = sorted(glob.glob(os.path.join(SOURCE_DIR, "*.msg")) +
                   glob.glob(os.path.join(SOURCE_DIR, "*.dat")))
    for path in paths:
        extract_file(path, records, general)
    rows = list(records.values()) + list(general.values())
    rows.sort(key=lambda row: (
        row["instance"], int(row["node"] or 0), int(row["dof"] or 0),
        row["source_file"], row["line"]))
    fields = [
        "instance_name", "node_label", "dof", "event_type",
        "first_source_file", "first_occurrence_line", "first_context",
        "physical_component_category", "proposed_action",
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "instance_name": row["instance"],
                "node_label": row["node"],
                "dof": row["dof"],
                "event_type": row["event"],
                "first_source_file": row["source_file"],
                "first_occurrence_line": row["line"],
                "first_context": row["context"],
                "physical_component_category": row["category"],
                "proposed_action": row["action"],
            })
    singular_instances = sorted(set(row["instance"] for row in rows
                                    if row["instance"]))
    print("EVIDENCE_CSV=%s" % OUTPUT_CSV)
    print("EVIDENCE_ROWS=%d" % len(rows))
    print("SINGULAR_INSTANCES=%d" % len(singular_instances))
    for instance in singular_instances:
        print(instance)


if __name__ == "__main__":
    main()
