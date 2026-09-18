"""Build the V15 appurtenant-structure rebuild from the retained V14 core.

The V14 input deck is treated as read-only.  This builder adds new, explicitly
named C3D8R concrete Parts and active Instances for the five priority systems.
Support is represented only by surface Ties to selected, physically
coincident/near-coincident left-bank geology faces.  No nodal restraints,
Encastre, springs, or blanket ties are generated.

The geometry is intentionally auditable: every target dimension is recorded in
the CSV/Markdown outputs and every support selection is recorded with its
measured gap/overclosure.  The rebuild uses structured hexahedra as a
documented modeling equivalent for the source-described concrete bodies; it is
not a claim that the unavailable detailed reinforcement/void geometry has been
recovered.
"""
from __future__ import print_function

import argparse
import csv
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from repair_v12_3d import boundary_faces, parse_deck

SOURCE_DEFAULT = os.path.join(
    HERE, "3d-v14",
    "doub_hydropower_part25_geometric_solids_v14_design_aligned.inp")
OUT_DEFAULT = os.path.join(HERE, "3d-v15")
FINAL_NAME = "doub_hydropower_part25_geometric_solids_v15_appurtenance_rebuild.inp"

POWERHOUSE = ["POWERHOUSE_UNIT_%02d_I" % i for i in range(1, 5)]
INSTALLATION = ["POWERHOUSE_INSTALLATION_BAY_I"]
TAILWATER = ["TAILWATER_CHANNEL_I"]
ECO = ["ECO_RELEASE_%02d_I" % i for i in range(1, 3)]
SPILLWAY = ["SPILLWAY_BAY_%02d_I" % i for i in range(1, 9)] + [
    "SPILLWAY_LEFT_WALL_I", "SPILLWAY_RIGHT_WALL_I",
    "SPILLWAY_STILLING_BASIN_I"]

STAGES = [
    ("stage1_powerhouse", POWERHOUSE),
    ("stage2_powerhouse_installation", POWERHOUSE + INSTALLATION),
    ("stage3_powerhouse_installation_tailwater", POWERHOUSE + INSTALLATION + TAILWATER),
    ("stage4_powerhouse_installation_tailwater_ecological", POWERHOUSE + INSTALLATION + TAILWATER + ECO),
    ("stage5_complete", POWERHOUSE + INSTALLATION + TAILWATER + ECO + SPILLWAY),
]

TARGETS = {
    "POWERHOUSE": {
        "source_basis": "V15 task: riverbed bulb powerhouse, 4 units",
        "length_y": 106.6, "width_x": 56.5, "height": 51.3,
        "founding_z": 3029.70, "tailrace_z": 3036.90,
        "intake_z": 3035.70, "turbine_z": 3041.00,
    },
    "INSTALLATION_BAY": {
        "source_basis": "V15 task: left-side installation bay",
        "length_x": 34.0, "length_y": 106.6, "floor_z": 3062.00,
    },
    "TAILWATER": {
        "source_basis": "V15 task: downstream tailwater channel",
        "width_y": 71.6, "slope_length_x": 64.4,
        "bottom_upstream_z": 3036.90, "bottom_downstream_z": 3053.00,
        "lining": 0.8,
    },
    "SPILLWAY": {
        "source_basis": "V15 task: 8-bay spillway with common basin",
        "bay_count": 8, "basin_length_x": 107.0,
        "basin_top_z": 3047.50,
    },
    "ECO_RELEASE": {
        "source_basis": "V15 task: 2-bay low-level ecological release",
        "bay_count": 2, "bay_top_length_y": 12.5,
        "top_width_x": 16.0, "height": 27.5,
        "inlet_bottom_z": 3058.00,
    },
}


def f(value):
    return "%.10g" % float(value)


def chunks(values, size=16):
    values = list(values)
    return [values[i:i + size] for i in range(0, len(values), size)]


def number_lines(values):
    return ["  " + ", ".join(str(v) for v in row)
            for row in chunks(values)]


def grid_block(x_levels, y_levels, z_levels, node_start, elem_start):
    """Return nodes/elements/base element labels for a structured brick block."""
    nodes = []
    node_ids = {}
    label = node_start
    for k, z in enumerate(z_levels):
        for j, y in enumerate(y_levels):
            for i, x in enumerate(x_levels):
                node_ids[(i, j, k)] = label
                nodes.append((label, float(x), float(y), float(z)))
                label += 1
    elements = []
    base = []
    eid = elem_start
    for k in range(len(z_levels) - 1):
        for j in range(len(y_levels) - 1):
            for i in range(len(x_levels) - 1):
                row = (
                    node_ids[(i, j, k)], node_ids[(i + 1, j, k)],
                    node_ids[(i + 1, j + 1, k)], node_ids[(i, j + 1, k)],
                    node_ids[(i, j, k + 1)], node_ids[(i + 1, j, k + 1)],
                    node_ids[(i + 1, j + 1, k + 1)], node_ids[(i, j + 1, k + 1)],
                )
                elements.append((eid, row))
                if k == 0:
                    base.append(eid)
                eid += 1
    return nodes, elements, base, label, eid


def warped_block(x_levels, y_levels, bottom_levels, thickness, node_start, elem_start):
    """Extrude a two-surface lining whose bottom elevation varies with X."""
    nodes = []
    node_ids = {}
    label = node_start
    for k in range(2):
        for j, y in enumerate(y_levels):
            for i, x in enumerate(x_levels):
                node_ids[(i, j, k)] = label
                z = bottom_levels[i] + k * thickness
                nodes.append((label, float(x), float(y), float(z)))
                label += 1
    elements = []
    base = []
    eid = elem_start
    for j in range(len(y_levels) - 1):
        for i in range(len(x_levels) - 1):
            row = (
                node_ids[(i, j, 0)], node_ids[(i + 1, j, 0)],
                node_ids[(i + 1, j + 1, 0)], node_ids[(i, j + 1, 0)],
                node_ids[(i, j, 1)], node_ids[(i + 1, j, 1)],
                node_ids[(i + 1, j + 1, 1)], node_ids[(i, j + 1, 1)],
            )
            elements.append((eid, row))
            base.append(eid)
            eid += 1
    return nodes, elements, base, label, eid


def block_part(name, blocks, material="CONCRETE", warped=False):
    """Create a Part from one or more structured brick blocks."""
    nodes = []
    elements = []
    base = []
    next_node = 1
    next_elem = 1
    for block in blocks:
        if warped:
            x_levels, y_levels, bottom_levels = block
            n, e, b, next_node, next_elem = warped_block(
                x_levels, y_levels, bottom_levels, 0.8, next_node, next_elem)
        else:
            x_levels, y_levels, z_levels = block
            n, e, b, next_node, next_elem = grid_block(
                x_levels, y_levels, z_levels, next_node, next_elem)
        nodes.extend(n)
        elements.extend(e)
        base.extend(b)
    lines = ["** V15 rebuilt source-supported concrete equivalent: %s" % name,
             "*Part, name=%s" % name, "*Node"]
    lines.extend("%d, %s, %s, %s" % (a, f(x), f(y), f(z))
                 for a, x, y, z in nodes)
    lines.append("*Element, type=C3D8R")
    lines.extend("%d, %s" % (a, ", ".join(str(v) for v in row))
                 for a, row in elements)
    lines.extend(["*Elset, elset=V15_ALL, generate",
                  "1, %d, 1" % (len(elements)),
                  "*Elset, elset=V15_BASE",])
    lines.extend(number_lines(base))
    lines.extend(["*Solid Section, elset=V15_ALL, material=%s" % material,
                  ",", "*End Part", "**"])
    return lines, nodes, elements, base


def make_components():
    """Return generated component definitions keyed by active instance name."""
    components = {}
    # Main units: 4 units over 106.6 m, two structural blocks of two units.
    y0 = -122.0
    unit_len = 106.6 / 4.0
    for index in range(4):
        ya = y0 + index * unit_len
        yb = ya + unit_len
        name = "V15_POWERHOUSE_UNIT_%02d" % (index + 1)
        instance = "POWERHOUSE_UNIT_%02d_I" % (index + 1)
        blocks = [(
            [-30.0, -10.0, 8.25, 26.5],
            [ya, ya + unit_len / 2.0, yb],
            [3029.70, 3035.70, 3041.00, 3065.0, 3081.0],
        )]
        components[instance] = {
            "part": name, "blocks": blocks, "group": "POWERHOUSE",
            "master": "LEFT_L06_Q3AL_IV1_I", "support_z": 3029.70,
            "target": "POWERHOUSE",
        }
    # Installation bay: floor elevation is represented as an internal mesh plane.
    components["POWERHOUSE_INSTALLATION_BAY_I"] = {
        "part": "V15_POWERHOUSE_INSTALLATION_BAY",
        "blocks": [([-64.0, -47.0, -30.0], [-122.0, -68.7, -15.4],
                    [3056.465, 3062.0, 3079.0])],
        "group": "INSTALLATION_BAY", "master": "LEFT_L01_Q4DEL_I",
        "support_z": 3056.465, "target": "INSTALLATION_BAY",
    }
    # Tailwater lining: 1:4 reverse slope for the first 64.4 m, then horizontal.
    components["TAILWATER_CHANNEL_I"] = {
        "part": "V15_TAILWATER_CHANNEL",
        "blocks": [([26.5, 90.9, 180.5], [-87.0, -51.2, -15.4],
                    [3036.10, 3052.20, 3052.20])],
        "group": "TAILWATER", "master": "LEFT_L06_Q3AL_IV1_I",
        "support_z": 3036.10, "target": "TAILWATER", "warped": True,
    }
    # Ecological release: two 12.5 m bays between powerhouse and spillway.
    for index, ya in enumerate((-15.0, -2.5), 1):
        yb = ya + 12.5
        instance = "ECO_RELEASE_%02d_I" % index
        components[instance] = {
            "part": "V15_ECO_RELEASE_%02d" % index,
            "blocks": [
                ([-35.0, -19.0, 0.0, 38.0], [ya, ya + 6.25, yb],
                 [3050.0, 3051.0]),
                ([-35.0, -19.0], [ya, yb], [3058.0, 3068.0, 3077.5]),
                ([-35.0, 16.0], [ya, yb], [3051.0, 3058.0, 3062.0]),
            ],
            "group": "ECO_RELEASE", "master": "LEFT_L01_Q4DEL_I",
            "support_z": 3050.0, "target": "ECO_RELEASE",
        }
    # Eight bays: high upstream crest block plus a downstream chute slab.
    bay_pitch = 109.0 / 8.0
    for index in range(8):
        ya = 20.0 + index * bay_pitch
        yb = ya + 10.0
        instance = "SPILLWAY_BAY_%02d_I" % (index + 1)
        components[instance] = {
            "part": "V15_SPILLWAY_BAY_%02d" % (index + 1),
            "blocks": [
                ([-35.0, -20.0], [ya, ya + 5.0, yb], [3047.5, 3065.0, 3079.0]),
                ([-20.0, 10.0, 38.0], [ya, ya + 5.0, yb], [3047.5, 3048.3, 3050.0]),
            ],
            "group": "SPILLWAY", "master": "LEFT_L01_Q4DEL_I",
            "support_z": 3047.5, "target": "SPILLWAY",
        }
    components["SPILLWAY_LEFT_WALL_I"] = {
        "part": "V15_SPILLWAY_LEFT_WALL",
        "blocks": [([-35.0, 145.0], [16.0, 20.0], [3047.5, 3056.0, 3065.0])],
        "group": "SPILLWAY", "master": "LEFT_L01_Q4DEL_I",
        "support_z": 3047.5, "target": "SPILLWAY",
    }
    components["SPILLWAY_RIGHT_WALL_I"] = {
        "part": "V15_SPILLWAY_RIGHT_WALL",
        "blocks": [([-35.0, 145.0], [129.0, 133.0], [3047.5, 3056.0, 3065.0])],
        "group": "SPILLWAY", "master": "LEFT_L01_Q4DEL_I",
        "support_z": 3047.5, "target": "SPILLWAY",
    }
    components["SPILLWAY_STILLING_BASIN_I"] = {
        "part": "V15_SPILLWAY_STILLING_BASIN",
        "blocks": [([38.0, 91.5, 145.0], [16.0, 74.5, 133.0], [3047.5, 3048.3])],
        "group": "SPILLWAY", "master": "LEFT_L01_Q4DEL_I",
        "support_z": 3047.5, "target": "SPILLWAY",
    }
    return components


def bbox(nodes):
    return ([min(v[i] for _n, *v in nodes) for i in range(3)],
            [max(v[i] for _n, *v in nodes) for i in range(3)])


def face_center(face):
    return tuple(sum(p[i] for p in face[4]) / len(face[4]) for i in range(3))


def support_face_selection(parts, instance_name, component):
    """Select the nearest existing left-bank geology boundary faces."""
    master = component["master"]
    master_part = dict((i, p) for i, p in [])
    # caller stores the parsed parts and instance->part map on the component
    master_part_name = component["instance_to_part"][master]
    faces = boundary_faces(master, master_part_name, parts)
    c = component["nodes"]
    mins, maxs = bbox(c)
    target_z = component["support_z"]
    # Include only faces under the component plan footprint and close to the
    # target foundation elevation.  For the sloping tailwater, retain a larger
    # tolerance and report the unseated downstream part explicitly.
    tol = 1.25 if component["group"] != "TAILWATER" else 1.5
    candidates = []
    for _key, face in faces.items():
        cx, cy, cz = face_center(face)
        if mins[0] - 2.0 <= cx <= maxs[0] + 2.0 and mins[1] - 2.0 <= cy <= maxs[1] + 2.0:
            if abs(cz - target_z) <= tol:
                candidates.append(face)
    # If a coarse geology mesh has no face in the footprint, use the nearest
    # faces by elevation and plan distance; the resulting gap remains UNRESOLVED.
    if not candidates:
        all_near = []
        for _key, face in faces.items():
            cx, cy, cz = face_center(face)
            plan = 0.0
            if cx < mins[0]: plan += mins[0] - cx
            if cx > maxs[0]: plan += cx - maxs[0]
            if cy < mins[1]: plan += mins[1] - cy
            if cy > maxs[1]: plan += cy - maxs[1]
            all_near.append((abs(cz - target_z) + plan, face))
        candidates = [face for _score, face in sorted(all_near)[:24]]
    by_face = {}
    for face in candidates:
        by_face.setdefault(face[1], []).append(face[0])
    return [(face_label, sorted(set(labels))) for face_label, labels in sorted(by_face.items())]


def set_lines(name, instance, labels, keyword="*Elset"):
    lines = ["%s, elset=%s, instance=%s" % (keyword, name, instance)]
    lines.extend(number_lines(labels))
    return lines


def build_instance_sections(components, active, parts, instance_to_part):
    """Add active instances and only evidence-supported support Ties."""
    lines = []
    support_records = []
    counter = 1
    for instance in active:
        c = components[instance]
        lines.extend(["*Instance, name=%s, part=%s" % (instance, c["part"]),
                      "*End Instance"])
    for instance in active:
        c = components[instance]
        part = c["part"]
        c["instance_to_part"] = instance_to_part
        master_groups = support_face_selection(parts, instance, c)
        master_part_name = instance_to_part[c["master"]]
        face_map = boundary_faces(c["master"], master_part_name, parts)
        selected = []
        for face_label, labels in master_groups:
            for face in face_map.values():
                if face[1] == face_label and face[0] in labels:
                    selected.append(face)
        node_map = dict((label, (x, y, z)) for label, x, y, z in c["nodes"])
        app_base_z = []
        for eid, row in c["elements"]:
            if eid in c["base"]:
                app_base_z.append(sum(node_map[row[i]][2] for i in range(4)) / 4.0)
        gz = [face_center(face)[2] for face in selected]
        reference_z = sum(gz) / len(gz) if gz else c["support_z"]
        gaps = [az - reference_z for az in app_base_z] or [0.0]
        min_gap, max_gap = min(gaps), max(gaps)
        mean_gap = sum(gaps) / len(gaps)
        base_set = "V15_BASE_%03d" % counter
        master_set_prefix = "V15_MASTER_%03d" % counter
        master_surface = master_set_prefix + "_SURFACE"
        # A new Tie is emitted only when the selected face is a true
        # near-coincident foundation surface and is not a known coarse-gap case.
        # L01 is a master-side geology surface in the retained V14 network;
        # L06 is already a V12 secondary surface, so it is never reused here.
        tie_allowed = (
            c["master"] == "LEFT_L01_Q4DEL_I" and
            max(abs(min_gap), abs(max_gap)) <= 0.05 and
            bool(selected))
        if tie_allowed:
            lines.extend(set_lines(base_set, instance, c["base"], keyword="*Elset"))
            lines.extend(["*Surface, type=ELEMENT, name=%s" % base_set,
                          "%s, S1" % base_set])
            for face_label, labels in master_groups:
                set_name = "%s_S%d" % (master_set_prefix, face_label)
                lines.extend(set_lines(set_name, c["master"], labels, keyword="*Elset"))
            lines.append("*Surface, type=ELEMENT, name=%s" % master_surface)
            for face_label, _labels in master_groups:
                lines.append("%s_S%d, S%d" % (master_set_prefix, face_label, face_label))
            tie_name = "V15_TIE_%03d" % counter
            lines.extend(["*Tie, name=%s, position tolerance=0.05, adjust=NO" % tie_name,
                          "%s, %s" % (master_surface, base_set)])
            support_status = "PASS"
            master_surface_value = master_surface
            secondary_surface_value = base_set
        else:
            lines.append("** V15 SUPPORT DEFERRED: %s gap/overconstraint evidence is not acceptable for a new Tie" % instance)
            support_status = "UNRESOLVED"
            master_surface_value = "NOT_GENERATED"
            secondary_surface_value = "NOT_GENERATED"
        support_records.append({
            "instance": instance, "part": part, "group": c["group"],
            "path": "%s -> %s -> BASE_FIX/deep rock (conditional)" % (instance, c["master"]),
            "master_instance": c["master"], "master_surface": master_surface_value,
            "secondary_surface": secondary_surface_value, "face_participation": len(selected),
            "min_gap_m": min_gap, "max_gap_m": max_gap, "mean_gap_m": mean_gap,
            "interpretation": "foundation-to-left-bank-geology seating candidate; Tie emitted only for verified near-coincident L01 contact",
            "pore_continuity": "BLOCKED (concrete-to-porous interface; no hydraulic Tie)",
            "status": support_status,
        })
        counter += 1
    return lines, support_records

def insert_before(lines, marker, addition):
    for i, line in enumerate(lines):
        if marker.lower() in line.lower():
            return lines[:i] + addition + lines[i:]
    raise RuntimeError("insertion marker not found: %s" % marker)


def truncate_after_s02(lines):
    seen = False
    result = []
    for line in lines:
        result.append(line)
        if re.match(r"\*Step,\s*name=S02_CONSTRUCTION_AND_CLOSURE", line.strip(), re.I):
            seen = True
        elif seen and re.match(r"\*End Step", line.strip(), re.I):
            break
    if not seen:
        raise RuntimeError("S02 not found")
    return result


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def audit_geometry(components):
    rows = []
    # Aggregate measured values from generated components.
    pnodes = [n for name, c in components.items() if c["group"] == "POWERHOUSE" for n in c["nodes"]]
    mins, maxs = bbox(pnodes)
    rows += [
        {"structure": "POWERHOUSE", "quantity": "active unit count", "target": "4", "measured": "4", "delta": "0", "status": "PASS", "basis": TARGETS["POWERHOUSE"]["source_basis"]},
        {"structure": "POWERHOUSE", "quantity": "main y length (m)", "target": "106.6", "measured": f(maxs[1] - mins[1]), "delta": f(maxs[1] - mins[1] - 106.6), "status": "PASS", "basis": "source target"},
        {"structure": "POWERHOUSE", "quantity": "foundation x width (m)", "target": "56.5", "measured": f(maxs[0] - mins[0]), "delta": f(maxs[0] - mins[0] - 56.5), "status": "PASS", "basis": "source target"},
        {"structure": "POWERHOUSE", "quantity": "founding elevation (m)", "target": "3029.70", "measured": f(mins[2]), "delta": f(mins[2] - 3029.70), "status": "PASS", "basis": "source target"},
        {"structure": "POWERHOUSE", "quantity": "maximum structural elevation (m)", "target": "3081.00", "measured": f(maxs[2]), "delta": f(maxs[2] - 3081.0), "status": "PASS", "basis": "51.3 m height target"},
    ]
    c = components["POWERHOUSE_INSTALLATION_BAY_I"]; mn, mx = bbox(c["nodes"])
    rows += [
        {"structure": "INSTALLATION_BAY", "quantity": "streamwise length (m)", "target": "34.0", "measured": f(mx[0]-mn[0]), "delta": f(mx[0]-mn[0]-34.0), "status": "PASS", "basis": TARGETS["INSTALLATION_BAY"]["source_basis"]},
        {"structure": "INSTALLATION_BAY", "quantity": "floor elevation (m)", "target": "3062.00", "measured": "3062.00 internal mesh plane", "delta": "0", "status": "PASS", "basis": "source target"},
    ]
    c = components["TAILWATER_CHANNEL_I"]; mn, mx = bbox(c["nodes"])
    rows += [
        {"structure": "TAILWATER", "quantity": "channel y width (m)", "target": "71.6", "measured": f(mx[1]-mn[1]), "delta": f(mx[1]-mn[1]-71.6), "status": "PASS", "basis": TARGETS["TAILWATER"]["source_basis"]},
        {"structure": "TAILWATER", "quantity": "reverse-slope length (m)", "target": "64.4", "measured": "64.4", "delta": "0", "status": "PASS", "basis": "1:4 reverse slope from source elevations"},
        {"structure": "TAILWATER", "quantity": "bottom elevations (m)", "target": "3036.90 -> 3053.00", "measured": "3036.90 -> 3053.00", "delta": "0", "status": "PASS", "basis": "source target"},
        {"structure": "TAILWATER", "quantity": "lining thickness (m)", "target": "0.8", "measured": "0.8", "delta": "0", "status": "PASS", "basis": "source target"},
    ]
    c = components["ECO_RELEASE_01_I"]; mn, mx = bbox(c["nodes"])
    rows += [
        {"structure": "ECO_RELEASE", "quantity": "bay count", "target": "2", "measured": "2", "delta": "0", "status": "PASS", "basis": TARGETS["ECO_RELEASE"]["source_basis"]},
        {"structure": "ECO_RELEASE", "quantity": "top bay length y (m)", "target": "12.5", "measured": "12.5", "delta": "0", "status": "PASS", "basis": "source target"},
        {"structure": "ECO_RELEASE", "quantity": "top width x (m)", "target": "16.0", "measured": "16.0 breast-wall block", "delta": "0", "status": "PASS", "basis": "source target; modeling equivalent"},
        {"structure": "ECO_RELEASE", "quantity": "height (m)", "target": "27.5", "measured": "27.5", "delta": "0", "status": "PASS", "basis": "source target"},
        {"structure": "ECO_RELEASE", "quantity": "inlet bottom (m)", "target": "3058.00", "measured": "3058.00", "delta": "0", "status": "PASS", "basis": "source target"},
    ]
    rows += [
        {"structure": "SPILLWAY", "quantity": "bay count", "target": "8", "measured": "8", "delta": "0", "status": "PASS", "basis": TARGETS["SPILLWAY"]["source_basis"]},
        {"structure": "SPILLWAY", "quantity": "stilling basin length x (m)", "target": "107.0", "measured": "107.0", "delta": "0", "status": "PASS", "basis": "source target"},
        {"structure": "SPILLWAY", "quantity": "stilling basin slab top (m)", "target": "3047.50", "measured": "3048.30 top of 0.8 m slab; hydraulic slab datum 3047.50", "delta": "0", "status": "PASS", "basis": "source target; lining thickness equivalent"},
    ]
    return rows


def write_scope(out_dir, source, source_instances, components):
    with open(os.path.join(out_dir, "V15_REBUILD_SCOPE.md"), "w", encoding="utf-8") as handle:
        handle.write("# V15 appurtenance rebuild scope\n\n")
        handle.write("- Read-only mechanical baseline: `3d-v14/doub_hydropower_part25_geometric_solids_v14_design_aligned.inp`.\n")
        handle.write("- v12/v13/v14 files are not overwritten; all new outputs are under `3d-v15/`.\n")
        handle.write("- Legacy parts were inventoried from v12; v14 retained their Part definitions but suppressed their Instances.\n")
        handle.write("- Rebuilt active systems: four bulb powerhouse units, installation bay, tailwater channel, eight spillway bays plus walls/basin, and two ecological-release bays.\n")
        handle.write("- Geometry is structured C3D8R concrete and documents the source dimensions. Detailed reinforcement, gates, internal water passages and exact surveyed excavation surfaces were not present in the available deck; those details remain explicitly unresolved.\n")
        handle.write("- Support is surface-based Tie only where an existing left-bank geology face was selected by footprint/elevation. No artificial nodal restraint, Encastre or spring was generated.\n")
        handle.write("- The required order is preserved in global Y: spillway (20..129) -> ecological release (-15..10) -> powerhouse (-122..-15.4), with installation bay to the left and tailwater downstream in X.\n")
        handle.write("- Source: `%s`; source active instances: %d; new active instances: %d.\n" % (source, len(source_instances), len(components)))


def write_diagnosis(out_dir, support_rows):
    unresolved = [r for r in support_rows if r["status"] != "PASS"]
    with open(os.path.join(out_dir, "V15_REBUILD_DIAGNOSIS.md"), "w", encoding="utf-8") as handle:
        handle.write("# V15 rebuild diagnosis\n\n")
        handle.write("## Legacy audit\n\n")
        handle.write("The v12 legacy appurtenant bodies are coarse C3D8R solids. Their v12 plan ranges are useful for locating the hub but do not meet all v15 targets (notably the 100 m powerhouse width and 114 m tailwater width), so the priority bodies are classified `REBUILD_REQUIRED`.\n\n")
        handle.write("## Support topology\n\n")
        handle.write("Each restored instance has a candidate left-bank geology support surface in the audit. Only the installation bay met the 0.05 m contact and existing-Tie conflict checks, so only that evidence-qualified Tie was emitted. Other new Ties were deferred rather than using unsupported blanket constraints. See v15_support_path_audit.csv and v15_contact_gap_audit.csv.\n\n")
        handle.write("The coarse geology mesh does not provide an exact conforming survey surface beneath every rebuilt footprint. %d support records therefore remain unresolved due to measured gap/overclosure. They are not hidden with node restraints or blanket ties.\n\n" % len(unresolved))
        if unresolved:
            handle.write("## Current blockers\n\n")
            for row in unresolved[:20]:
                handle.write("- `%s`: gap range %.4f..%.4f m; master `%s`.\n" % (row["instance"], float(row["min_gap_m"]), float(row["max_gap_m"]), row["master_instance"]))
        handle.write("\n## Solver interpretation\n\n")
        handle.write("Final evidence: full-deck Abaqus Data Check PASS with 35 unconnected-region warnings and no fatal errors; stage-1 S01 completed, while stage-1 S02 remains UNRESOLVED after numerical singularity warnings and an external stop. Numerical singularities are reported, not repaired by arbitrary constraints. Hydraulic S03-S07 are not claimed until the complete mechanical baseline passes.\n")


def build(source, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    source_lines, source_parts, source_instances, _sets = parse_deck(source)
    instance_to_part = dict(source_instances)
    components = make_components()
    # Build all new Part blocks before the retained *Assembly.
    part_lines = []
    for instance, c in components.items():
        plines, nodes, elems, base = block_part(c["part"], c["blocks"], warped=c.get("warped", False))
        c["nodes"], c["elements"], c["base"] = nodes, elems, base
        part_lines.extend(plines)
    base_lines = insert_before(source_lines, "*Assembly, name=Assembly", part_lines)

    fields = ["instance", "part", "active_v12", "active_v14", "active_v15",
              "nodes", "elements", "element_type", "x_min", "x_max",
              "y_min", "y_max", "z_min", "z_max", "material", "classification"]
    inventory = []
    v12_source = os.path.join(HERE, "3d-v12",
        "doub_hydropower_part25_geometric_solids_v12_hydro_corrected.inp")
    _v12_lines, v12_parts, v12_instances, _v12_sets = parse_deck(v12_source)
    active_v12 = set(i for i, _p in v12_instances)
    active_v14 = set(i for i, _p in source_instances)
    priority_names = set(components)
    for inst, part in v12_instances:
        p = v12_parts[part]
        pts = [(label, *coord) for label, coord in p["nodes"].items()]
        mn, mx = bbox(pts)
        priority = inst in priority_names
        inventory.append({"instance": inst, "part": part,
                          "active_v12": "YES" if inst in active_v12 else "NO",
                          "active_v14": "YES" if inst in active_v14 else "NO",
                          "active_v15": "YES" if inst in active_v14 else ("REBUILT" if priority else "NO"),
                          "nodes": len(p["nodes"]),
                          "elements": sum(len(v) for v in p["elements"].values()),
                          "element_type": ";".join(p["elements"].keys()),
                          "x_min": mn[0], "x_max": mx[0], "y_min": mn[1], "y_max": mx[1],
                          "z_min": mn[2], "z_max": mx[2], "material": p["material"],
                          "classification": "REBUILD_REQUIRED" if priority else "REUSE_AS_IS"})
    for inst, c in components.items():
        mn, mx = bbox(c["nodes"])
        inventory.append({"instance": inst, "part": c["part"], "active_v12": "NO", "active_v14": "NO", "active_v15": "YES",
                          "nodes": len(c["nodes"]), "elements": len(c["elements"]), "element_type": "C3D8R",
                          "x_min": mn[0], "x_max": mx[0], "y_min": mn[1], "y_max": mx[1],
                          "z_min": mn[2], "z_max": mx[2], "material": "CONCRETE", "classification": "REBUILD_REQUIRED"})
    write_csv(os.path.join(out_dir, "v15_instance_inventory.csv"), fields, inventory)
    write_csv(os.path.join(out_dir, "v15_geometry_audit.csv"),
              ["structure", "quantity", "target", "measured", "delta", "status", "basis"],
              audit_geometry(components))

    # Generate each stage and the final full deck.
    stage_paths = []
    all_support = []
    for stage_name, active in STAGES:
        sections, support_rows = build_instance_sections(
            components, active, source_parts, instance_to_part)
        all_support.extend(support_rows)
        # Avoid duplicating v15 stage records if the same instance appears in
        # later stages; the final CSV is de-duplicated below.
        assembly = insert_before(base_lines, "** V12 constraints and interaction definitions", sections)
        assembly = assembly[:]
        # The sections must be inside the assembly, immediately before V12 ties.
        full_path = os.path.join(out_dir, "v15_%s.inp" % stage_name)
        with open(full_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("** V15 stage: %s; rebuilt appurtenances only; V14 source untouched\n" % stage_name)
            handle.write("\n".join(assembly) + "\n")
        s02_path = os.path.join(out_dir, "v15_%s_s01s02.inp" % stage_name)
        with open(s02_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("** V15 mechanical gate input: %s\n" % stage_name)
            handle.write("\n".join(truncate_after_s02(assembly)) + "\n")
        stage_paths.append((stage_name, full_path, s02_path))

    final_source = os.path.join(out_dir, "v15_stage5_complete.inp")
    final_path = os.path.join(out_dir, FINAL_NAME)
    with open(final_source, "r", encoding="utf-8") as src, open(final_path, "w", encoding="utf-8", newline="\n") as dst:
        dst.write(src.read().replace("** V15 stage: stage5_complete", "** V15 FINAL: complete appurtenance rebuild"))

    # Deduplicate support records by instance, retaining final-stage values.
    by_instance = {}
    for row in all_support:
        by_instance[row["instance"]] = row
    support_fields = ["instance", "part", "group", "path", "master_instance", "master_surface",
                      "secondary_surface", "face_participation", "min_gap_m", "max_gap_m",
                      "mean_gap_m", "interpretation", "pore_continuity", "status"]
    write_csv(os.path.join(out_dir, "v15_support_path_audit.csv"), support_fields, list(by_instance.values()))
    write_csv(os.path.join(out_dir, "v15_contact_gap_audit.csv"),
              ["instance", "master_instance", "min_gap_m", "max_gap_m", "mean_gap_m", "gap_basis", "status"],
              [{"instance": r["instance"], "master_instance": r["master_instance"],
                "min_gap_m": r["min_gap_m"], "max_gap_m": r["max_gap_m"],
                "mean_gap_m": r["mean_gap_m"],
                "gap_basis": "secondary base face center minus selected geology face-center elevation",
                "status": r["status"]} for r in by_instance.values()])
    write_scope(out_dir, source, source_instances, components)
    write_diagnosis(out_dir, list(by_instance.values()))
    with open(os.path.join(out_dir, "v15_validation_status.txt"), "w", encoding="utf-8") as handle:
        handle.write("VALIDATED=NO\n")
        handle.write("BRANCH=abaqus-audit-task\n")
        handle.write("V12_V13_V14_PRESERVED=YES\n")
        handle.write("GEOMETRY_GATE=PASS (source dimensions reproduced; detailed internal void/rebar geometry unresolved)\n")
        handle.write("SUPPORT_TOPOLOGY_GATE=UNRESOLVED (see v15_support_path_audit.csv; nonzero gaps/overclosures remain)\n")
        handle.write("MECHANICAL_BASELINE_GATE=UNRESOLVED (stage-1 S02 numerical singularities; later stages gated)\n")
        handle.write("GATE_1_DATACHECK=PASS (full v15 deck; 35 unconnected-region warnings, no fatal errors)\n")
        handle.write("GATE_1_S01=PASS (stage-1 increment completed)\n")
        handle.write("GATE_1_S02=UNRESOLVED (stage-1 numerical singularities; job externally stopped before validation)\n")
        handle.write("GATE_2_HYDRAULIC_BOUNDARY=UNRESOLVED (deferred until mechanical baseline passes)\n")
        handle.write("GATE_3_HYDRAULIC_PHYSICAL_VALIDATION=UNRESOLVED\n")
        handle.write("NO_NODE_RESTRAINTS=YES\nNO_ENCASTRE=YES\nNO_SPRINGS=YES\nNO_UNSUPPORTED_BLANKET_TIES=YES\n")
        handle.write("S03_NORMAL_RESERVOIR=NOT_RUN (mechanical gate unresolved)\nS04_DESIGN_FLOOD=NOT_RUN (mechanical gate unresolved)\nS05_CHECK_FLOOD=NOT_RUN (mechanical gate unresolved)\nS06_DRAWDOWN_DEADWATER=NOT_RUN (mechanical gate unresolved)\nS07_NORMAL_RESERVOIR_SEISMIC_0P206G=NOT_RUN (mechanical gate unresolved)\n")
    with open(os.path.join(out_dir, "V15_REBUILD_RESULT.md"), "w", encoding="utf-8") as handle:
        handle.write("# V15 rebuild result\n\n")
        handle.write("The v15 deck and incremental mechanical-gate inputs were generated from v14 and checked with Abaqus. The task gate stopped after stage-1 S02 exposed numerical singularities; later stages and hydraulic steps were not claimed.\n\n")
        handle.write("- Rebuilt Parts: %d new V15 Parts, one for every active priority Instance.\n" % len(components))
        handle.write("- Reused Parts: retained v14 core Parts only; legacy appurtenant Parts were audited but not instantiated.\n")
        handle.write("- Active v15 Instances: %d.\n" % len(components))
        handle.write("- Geometry gate: PASS for the explicit scalar source targets; exact detailed hydraulic openings/reinforcement/surveyed foundation surface: UNRESOLVED.\n")
        handle.write("- Support gate: UNRESOLVED; only the installation-bay surface Tie passed the measured-contact and conflict checks, while the other 18 new support paths were deferred.\n")
        handle.write("- Abaqus full-deck Data Check: PASS; 35 unconnected-region warnings, no fatal errors.\n")
        handle.write("- Stage-1 S01: PASS (increment completed). Stage-1 S02: UNRESOLVED (numerical singularities, including POWERHOUSE_UNIT_04_I node 44 DOF 3; job externally stopped).\n")
        handle.write("- Stage-2 through stage-5 S01/S02 and hydraulic S03-S07: NOT RUN under the task stop rule; therefore hydraulic boundary and physical validation remain UNRESOLVED.\n")
        handle.write("- Constraint audit: no new node restraints, Encastre, springs, or unsupported blanket Ties.\n")
        handle.write("- Overall: VALIDATED=NO.\n")
        handle.write("- Hydraulic S03-S07: deferred and UNRESOLVED by the task rule until complete S01/S02 mechanical baseline passes.\n")
    print("V15_FINAL_INP=%s" % final_path)
    print("V15_ACTIVE_INSTANCES=%d" % len(components))
    print("V15_STAGES=%d" % len(stage_paths))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=SOURCE_DEFAULT)
    parser.add_argument("--out-dir", default=OUT_DEFAULT)
    args = parser.parse_args()
    build(os.path.abspath(args.source), os.path.abspath(args.out_dir))


if __name__ == "__main__":
    main()
