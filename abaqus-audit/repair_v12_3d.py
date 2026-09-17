"""Build the corrected v12 3-D hydro-mechanical keyword deck.

This is deliberately a keyword-deck transformation rather than a silent CAE
rewrite.  The source v11 deck is read-only; the corrected deck, audit tables,
and the deterministic build log are written to the requested output folder.
Run with the system Python, then use Abaqus/CAE noGUI to import the corrected
deck and save the CAE copy.
"""
from __future__ import print_function

import collections
import csv
import hashlib
import itertools
import json
import math
import os
import re
import sys


WATER_UNIT_WEIGHT = 9.81  # kN/m3; model pressure unit is kPa
UPSTREAM_HEADS = {
    "S03_NORMAL_RESERVOIR_3076M": 3076.00,
    # The design-flood discharge does not have a separate supported level in
    # the supplied reports.  Keep the normal level as a labelled hold case.
    "S04_DESIGN_FLOOD_3580CMS": 3076.00,
    "S05_CHECK_FLOOD_AND_SEISMIC": 3077.35,
    "S06_DRAWDOWN_TO_3074M": 3074.00,
}
DOWNSTREAM_HEADS = dict((name, 3055.00) for name in UPSTREAM_HEADS)
INITIAL_VOID_RATIO = 0.5

GEO_K = {
    "Q4DEL": 2.33e-5,
    "Q4AL_SGR2": 2.33e-4,
    "Q4AL_SGR1": 5.80e-5,
    "Q3AL_V": 4.46e-6,
    "Q3AL_IV2": 2.35e-6,
    "Q3AL_IV1": 5.48e-6,
    "Q3AL_III": 8.49e-5,
    "Q3AL_II": 5.89e-7,
    "Q3AL_I": 1.14e-5,
    "Q2FGL_V": 1.14e-5,
    "Q2FGL_IV": 1.70e-6,
    "Q2FGL_III": 3.26e-7,
    "Q2FGL_II": 8.35e-7,
    "Q2FGL_I": 2.50e-7,
}

# These are the explicit unit-weight examples required by the task.  The
# source model stores them as values such as 2.16, which is a kg/L-like
# density if interpreted as mass density, but the project table labels the
# corresponding values as kN/m3.  Convert only the values supported by the
# task; leave the cutoff-wall value unchanged because its source unit is not
# explicit in the supplied material table.
DAM_DENSITY = {
    "P25_BAKESHALI": 21.6 / WATER_UNIT_WEIGHT,
    "P25_BIQILIAO": 14.6 / WATER_UNIT_WEIGHT,
    "P25_FANLV": 21.6 / WATER_UNIT_WEIGHT,
    "P25_PAISHUITI": 19.7 / WATER_UNIT_WEIGHT,
    "P25_WEIYANJITI": 19.2 / WATER_UNIT_WEIGHT,
    "P25_WEIYANSHALI": 21.6 / WATER_UNIT_WEIGHT,
}

POROUS_MATERIALS = set(GEO_K) | {
    "P25_BAKESHALI", "P25_BIQILIAO", "P25_FANGSHENQIANG", "P25_FANLV",
    "P25_PAISHUITI", "P25_WEIYANJITI", "P25_WEIYANSHALI",
}

FACE_MAP = {
    "C3D8R": [(1, (0, 1, 2, 3)), (2, (4, 7, 6, 5)),
              (3, (0, 4, 5, 1)), (4, (1, 5, 6, 2)),
              (5, (2, 6, 7, 3)), (6, (3, 7, 4, 0))],
    "C3D6": [(1, (0, 1, 2)), (2, (3, 5, 4)),
             (3, (0, 3, 4, 1)), (4, (1, 4, 5, 2)),
             (5, (2, 5, 3, 0))],
}


def is_keyword(line):
    return line.lstrip().startswith("*")


def keyword_name(line):
    if not is_keyword(line):
        return ""
    return line.lstrip()[1:].split(",", 1)[0].strip().upper()


def parse_number_list(line):
    result = []
    for token in line.split(","):
        try:
            result.append(int(token.strip()))
        except Exception:
            pass
    return result


def fmt(value):
    return "%.10g" % float(value)


def fmt_nodes(labels):
    labels = list(labels)
    result = []
    for start in range(0, len(labels), 16):
        result.append("  " + ", ".join(str(v) for v in labels[start:start + 16]))
    return result


def parse_deck(path):
    lines = open(path, "r", encoding="utf-8", errors="replace").read().splitlines()
    parts = collections.OrderedDict()
    instances = []
    assembly_sets = {}
    current_part = None
    current_mode = None
    current_type = None
    current_instance = None
    in_assembly = False
    active_assembly_set = None

    for line in lines:
        s = line.strip()
        match = re.match(r"\*Part,\s*name=([^,]+)", s, re.I)
        if match:
            current_part = match.group(1)
            parts[current_part] = {
                "nodes": collections.OrderedDict(),
                "elements": collections.OrderedDict(),
                "material": None,
            }
            current_mode = None
            continue
        if re.match(r"\*End Part", s, re.I):
            current_part = None
            current_mode = None
            continue
        match = re.match(r"\*Instance,\s*name=([^,]+),\s*part=([^,]+)", s, re.I)
        if match:
            current_instance = match.group(1)
            instances.append((match.group(1), match.group(2)))
            active_assembly_set = None
            continue
        if re.match(r"\*End Instance", s, re.I):
            current_instance = None
            active_assembly_set = None
            continue
        if re.match(r"\*Assembly", s, re.I):
            in_assembly = True
        if current_part is not None:
            if s.lower().startswith("*node"):
                current_mode = "node"
                continue
            match = re.match(r"\*Element,\s*type=([^,]+)", s, re.I)
            if match:
                current_type = match.group(1).upper()
                parts[current_part]["elements"].setdefault(current_type,
                                                            collections.OrderedDict())
                current_mode = "element"
                continue
            if s.lower().startswith("*solid section"):
                match = re.search(r"material=([^,]+)", s, re.I)
                if match:
                    parts[current_part]["material"] = match.group(1)
                current_mode = None
                continue
            if is_keyword(line):
                current_mode = None
                continue
            values = [v.strip() for v in s.split(",")]
            try:
                if current_mode == "node" and len(values) >= 4:
                    parts[current_part]["nodes"][int(values[0])] = tuple(
                        float(v) for v in values[1:4])
                elif current_mode == "element" and len(values) >= 2:
                    parts[current_part]["elements"][current_type][int(values[0])] = tuple(
                        int(v) for v in values[1:])
            except Exception:
                pass
        if in_assembly:
            match = re.match(r"\*Elset,\s*elset=([^,]+).*instance=([^,]+)", s, re.I)
            if match and "P25_UPSTREAM_PRESSURE" in match.group(1):
                active_assembly_set = match.group(1)
                assembly_sets[active_assembly_set] = {
                    "instance": match.group(2), "labels": []}
                continue
            if active_assembly_set and is_keyword(line):
                active_assembly_set = None
            elif active_assembly_set and not s.startswith("**"):
                assembly_sets[active_assembly_set]["labels"].extend(parse_number_list(s))

    return lines, parts, instances, assembly_sets


def correct_coord(part_name, coord, original_parts):
    x, y, z = coord
    if part_name == "P25_SOLID_CUTOFF_WALL_F13":
        if abs(x + 36.5) < 1.0e-5:
            x = -36.0
        elif abs(x + 34.5) < 1.0e-5:
            x = -35.0
        if y < 3021.0:
            y = 3021.0
    if part_name in ("RIGHT_BX01", "RIGHT_BX02", "RIGHT_BX03"):
        targets = {
            "RIGHT_BX01": (2990.0, 3305.0),
            "RIGHT_BX02": (3005.0, 3201.0),
            "RIGHT_BX03": (3040.0, 3170.0),
        }
        old_z = [v[2] for v in original_parts[part_name]["nodes"].values()]
        old_min, old_max = min(old_z), max(old_z)
        new_min, new_max = targets[part_name]
        if old_max > old_min:
            z = new_min + (z - old_min) * (new_max - new_min) / (old_max - old_min)
    return (x, y, z)


def global_coord(instance_name, part_name, coord):
    # The v11 P25 instances carry a +90-degree rotation about global X and a
    # translation to y=445.  The deck stores those transforms after each
    # instance, so convert only for audits and generated surfaces; node lines
    # remain in their original part coordinates.
    if instance_name.startswith("P25_"):
        x, y, z = coord
        return (x, 445.0 - z, y)
    return coord


def corrected_parts(parts):
    corrected = collections.OrderedDict()
    for name, source in parts.items():
        out = {
            "nodes": collections.OrderedDict(),
            "elements": source["elements"],
            "material": source["material"],
        }
        for label, coord in source["nodes"].items():
            out["nodes"][label] = correct_coord(name, coord, parts)
        corrected[name] = out
    return corrected


def instance_is_porous(instance_name, part_name, parts):
    return parts[part_name]["material"] in POROUS_MATERIALS


def element_lookup(part):
    result = {}
    for etype, elements in part["elements"].items():
        for label, nodes in elements.items():
            result[label] = (etype, nodes)
    return result


def face_key(coords):
    return tuple(sorted(tuple(round(float(v), 5) for v in point) for point in coords))


def boundary_faces(instance_name, part_name, parts):
    part = parts[part_name]
    lookup = element_lookup(part)
    occurrences = collections.defaultdict(list)
    for etype, elements in part["elements"].items():
        base_type = "C3D8R" if etype.startswith("C3D8") else "C3D6"
        for label, nodes in elements.items():
            for face_label, indices in FACE_MAP[base_type]:
                if max(indices) >= len(nodes):
                    continue
                coords = [global_coord(instance_name, part_name,
                                        part["nodes"][nodes[i]]) for i in indices]
                occurrences[face_key(coords)].append(
                    (label, face_label, etype, tuple(nodes[i] for i in indices), coords))
    return dict((key, value[0]) for key, value in occurrences.items()
                if len(value) == 1)


def element_face_groups(faces):
    grouped = collections.defaultdict(list)
    for value in faces.values():
        label, face_label = value[0], value[1]
        grouped[face_label].append(label)
    for key in grouped:
        grouped[key] = sorted(set(grouped[key]))
    return grouped


def exact_interfaces(instances, parts):
    face_maps = {}
    for instance_name, part_name in instances:
        face_maps[instance_name] = boundary_faces(instance_name, part_name, parts)
    result = []
    for (ia, pa), (ib, pb) in itertools.combinations(instances, 2):
        common = sorted(set(face_maps[ia]) & set(face_maps[ib]))
        if not common:
            continue
        result.append({
            "kind": "exact", "master": (ia, pa), "secondary": (ib, pb),
            "keys": common, "faces_master": face_maps[ia],
            "faces_secondary": face_maps[ib], "tolerance": 0.05,
        })
    return result, face_maps


def condition_faces(face_map, predicate):
    return dict((key, value) for key, value in face_map.items()
                if predicate(value[4]))


def add_aggregate_interface(result, name, master_items, secondary_items, tolerance):
    if not master_items or not secondary_items:
        return
    result.append({
        "kind": "aggregate", "name": name,
        "master_items": master_items, "secondary_items": secondary_items,
        "tolerance": tolerance,
    })


def aggregate_interfaces(instances, parts, face_maps):
    result = []

    def on_plane(inst, part, plane, side):
        fmap = face_maps[inst]
        if side == "min":
            return condition_faces(fmap, lambda pts: all(abs(p[1] - plane) < 1.0e-4
                                                          for p in pts))
        return condition_faces(fmap, lambda pts: all(abs(p[1] - plane) < 1.0e-4
                                                      for p in pts))

    left = []
    river = []
    right = []
    for inst, part in instances:
        if inst.startswith("LEFT_"):
            left.append((inst, part, on_plane(inst, part, 150.0, "max")))
        elif inst.startswith("RIVER_"):
            river.append((inst, part, face_maps[inst]))
        elif inst.startswith("RIGHT_"):
            right.append((inst, part, on_plane(inst, part, 445.0, "min")))
    river_left = []
    river_right = []
    for inst, part, fmap in river:
        river_left.append((inst, part, condition_faces(
            fmap, lambda pts: all(abs(p[1] - 150.0) < 1.0e-4 for p in pts))))
        river_right.append((inst, part, condition_faces(
            fmap, lambda pts: all(abs(p[1] - 445.0) < 1.0e-4 for p in pts))))

    add_aggregate_interface(result, "LEFT_RIVER_GEOLOGY_NONCONFORMAL",
                            left, river_left, 2.0)
    add_aggregate_interface(result, "RIVER_RIGHT_GEOLOGY_NONCONFORMAL",
                            river_right, right, 2.0)

    dam = []
    geology = []
    for inst, part in instances:
        if inst.startswith("P25_"):
            fmap = face_maps[inst]
            zmin = min(p[2] for p in [global_coord(inst, part, c)
                                      for c in parts[part]["nodes"].values()])
            dam.append((inst, part, condition_faces(
                fmap, lambda pts, z=zmin: (sum(p[2] for p in pts) / len(pts)) <= z + 1.0)))
        elif inst.startswith("RIVER_"):
            fmap = face_maps[inst]
            zmax = max(p[2] for p in [global_coord(inst, part, c)
                                      for c in parts[part]["nodes"].values()])
            geology.append((inst, part, condition_faces(
                fmap, lambda pts, z=zmax: (sum(p[2] for p in pts) / len(pts)) >= z - 5.0)))
    add_aggregate_interface(result, "DAM_RIVER_FOUNDATION_NONCONFORMAL",
                            geology, dam, 6.0)
    return result


def new_geomembrane_part():
    # A 1.0 m equivalent solid hydraulic layer.  Its permeability is the
    # explicit GEOMEMBRANE value from the task; the model reports t/k so the
    # representation is auditable and not confused with a zero-thickness face.
    x0, x1 = -90.5, -36.5
    z0, z1 = 3055.0, 3073.51147
    y0, y1 = 150.0, 445.0
    thickness = 1.0
    ny, nz = 10, 8
    nodes = []
    def node_id(k, j, side):
        return 1 + ((k * (ny + 1) + j) * 2 + side)
    for k in range(nz + 1):
        t = float(k) / nz
        for j in range(ny + 1):
            y = y0 + (y1 - y0) * float(j) / ny
            x = x0 + (x1 - x0) * t
            z = z0 + (z1 - z0) * t
            nodes.append((node_id(k, j, 0), x, y, z))
            nodes.append((node_id(k, j, 1), x + thickness, y, z))
    elements = []
    eid = 1
    top = []
    for k in range(nz):
        for j in range(ny):
            row = (node_id(k, j, 0), node_id(k, j, 1),
                   node_id(k, j + 1, 1), node_id(k, j + 1, 0),
                   node_id(k + 1, j, 0), node_id(k + 1, j, 1),
                   node_id(k + 1, j + 1, 1), node_id(k + 1, j + 1, 0))
            elements.append((eid, row))
            if k == nz - 1:
                top.append(eid)
            eid += 1
    lines = [
        "** V12 actual upstream geomembrane equivalent layer",
        "*Part, name=V12_UPSTREAM_GEOMEMBRANE",
        "*Node",
    ]
    lines.extend(["%7d, %s, %s, %s" % (label, fmt(x), fmt(y), fmt(z))
                  for label, x, y, z in nodes])
    lines.append("*Element, type=C3D8P")
    for label, row in elements:
        lines.append("%7d, %s" % (label, ", ".join(str(v) for v in row)))
    lines.extend(["*Elset, elset=ALL, generate", "  1, %d, 1" % (len(elements)),
                  "*Elset, elset=V12_GEOMEMBRANE_TOP", 
                  "  " + ", ".join(str(v) for v in top),
                  "*Solid Section, elset=ALL, material=GEOMEMBRANE", ",",
                  "*End Part", "**"])
    return lines, nodes, elements, top


def material_blocks(lines):
    starts = []
    for i, line in enumerate(lines):
        if re.match(r"\*Material,\s*name=", line.strip(), re.I):
            starts.append(i)
    blocks = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(lines)
        blocks.append((start, end, lines[start:end]))
    return blocks


def augment_materials(lines):
    out = list(lines)
    # Process from the end so indexes remain valid.
    for start, end, block in reversed(material_blocks(lines)):
        header = block[0]
        match = re.search(r"name=([^,]+)", header, re.I)
        if not match:
            continue
        name = match.group(1)
        want_k = GEO_K.get(name)
        if name == "GEOMEMBRANE":
            want_k = 4.5e-11
        has_k = any(keyword_name(v) == "PERMEABILITY" for v in block)
        density = DAM_DENSITY.get(name)
        block_out = list(block)
        if density is not None:
            for j in range(1, len(block_out)):
                if keyword_name(block_out[j]) == "DENSITY":
                    for k in range(j + 1, len(block_out)):
                        if not block_out[k].strip() or block_out[k].lstrip().startswith("**"):
                            continue
                        if is_keyword(block_out[k]):
                            break
                        block_out[k] = " %s," % fmt(density)
                        break
                    break
        if want_k is not None and not has_k:
            insert_at = len(block_out)
            for j in range(1, len(block_out)):
                if keyword_name(block_out[j]) == "ELASTIC":
                    for k in range(j + 1, len(block_out)):
                        if block_out[k].lstrip().startswith("**"):
                            continue
                        if not is_keyword(block_out[k]):
                            insert_at = k + 1
                            break
                        insert_at = k
                    break
            block_out[insert_at:insert_at] = ["*Permeability, specific=9.81",
                                              " %s, 0." % fmt(want_k)]
        out[start:end] = block_out
    return out


def transform_lines(source_lines, parts, corrected):
    out = []
    current_part = None
    current_mode = None
    current_material = None
    current_step = None
    pending_proc_data = False
    skip_dsload = False
    initial_conditions_inserted = False
    for line in source_lines:
        s = line.strip()
        match = re.match(r"\*Part,\s*name=([^,]+)", s, re.I)
        if match:
            current_part = match.group(1)
            current_mode = None
        if re.match(r"\*End Part", s, re.I):
            current_part = None
            current_mode = None
        match = re.match(r"\*Material,\s*name=([^,]+)", s, re.I)
        if match:
            current_material = match.group(1)
        if re.match(r"\*Step,\s*name=([^,]+)", s, re.I):
            if not initial_conditions_inserted and INITIAL_RATIO_LINES:
                out.extend(INITIAL_RATIO_LINES)
                initial_conditions_inserted = True
            current_step = re.match(r"\*Step,\s*name=([^,]+)", s, re.I).group(1)
            pending_proc_data = False
        if skip_dsload:
            if is_keyword(line) and keyword_name(line) != "DSLOAD":
                skip_dsload = False
            elif not is_keyword(line) and not s.startswith("**"):
                continue
            else:
                if s.startswith("**") and "Name: P25_RESERVOIR_PRESSURE" in s:
                    out.append("** V12 removed legacy uniform mechanical pressure; direct pore-pressure heads follow.")
                continue
        if keyword_name(line) == "DSLOAD":
            skip_dsload = True
            out.append("** V12 legacy constant face pressure removed; see V12 pore-pressure BCs.")
            continue
        if current_part is not None and s.lower().startswith("*node"):
            current_mode = "node"
        elif current_part is not None:
            match = re.match(r"\*Element,\s*type=([^,]+)", s, re.I)
            if match:
                current_mode = "element"
                old_type = match.group(1).upper()
                material = (parts[current_part]["material"]
                            if current_part in parts else None)
                if material in POROUS_MATERIALS:
                    new_type = {"C3D8R": "C3D8P", "C3D6": "C3D6P"}.get(old_type, old_type)
                    line = line.replace(match.group(1), new_type)
        if current_part is not None and current_mode == "node" and s and not is_keyword(line) and not s.startswith("**"):
            values = [v.strip() for v in s.split(",")]
            try:
                label = int(values[0])
                coord = corrected[current_part]["nodes"][label]
                line = "%7d, %s, %s, %s" % (label, fmt(coord[0]), fmt(coord[1]), fmt(coord[2]))
            except Exception:
                pass
        if current_step and keyword_name(line) == "STATIC":
            if current_step == "S01_GEOLOGICAL_INITIAL_STRESS":
                line = "*Geostatic, utol=0.01"
            else:
                line = "*Soils, consolidation, end=SS, utol=1000.0"
            pending_proc_data = current_step != "S01_GEOLOGICAL_INITIAL_STRESS"
        elif pending_proc_data and current_step and not is_keyword(line) and not s.startswith("**"):
            line = "1.0e-4, 1.0e9, 1.0e-10, 1.0e7, 1.0e-6"
            pending_proc_data = False
        if (current_step in UPSTREAM_HEADS and
                s.lower().startswith("*output, field") and
                "variable=preselect" in s.lower()):
            out.append(line)
            out.extend(["*Node Output", "POR, RF, U",
                        "*Element Output, directions=YES", "FLVEL, POR, S"])
            continue
        if current_step in UPSTREAM_HEADS and keyword_name(line) == "RESTART":
            operation = "" if current_step == "S03_NORMAL_RESERVOIR_3076M" else ", op=MOD"
            out.append("*Boundary%s" % operation)
            out.extend("%s, 8, 8, %s" % (entry["set"], fmt(entry["p"][current_step]))
                       for entry in HYDRO_BC_ENTRIES)
            out.append("** V12 head boundary: p=9.81*max(H-z,0), pressure in kPa.")
        out.append(line)
    return augment_materials(out)


def set_line(name, instance, labels):
    return ["*Nset, nset=%s, instance=%s" % (name, instance)] + fmt_nodes(labels)


def element_set_line(name, instance, labels):
    return ["*Elset, elset=%s, instance=%s" % (name, instance)] + fmt_nodes(labels)


def append_surface(surface_lines, surface_name, side_groups):
    surface_lines.extend(["*Surface, type=ELEMENT, name=%s" % surface_name])
    for elset_name, face_label in side_groups:
        surface_lines.append("%s, S%d" % (elset_name, face_label))


def surface_elsets(surface_lines, prefix, item_groups):
    groups = []
    for item_index, (instance, part, fmap) in enumerate(item_groups):
        grouped = element_face_groups(fmap)
        for face_label, labels in sorted(grouped.items()):
            name = "%s_%d_S%d" % (prefix, item_index, face_label)
            surface_lines.extend(["*Elset, elset=%s, instance=%s" % (name, instance)])
            surface_lines.extend(fmt_nodes(labels))
            groups.append((name, face_label))
    return groups


def build_assembly_and_constraints(lines, corrected, instances, exact, aggregates,
                                   face_maps, geom_top, geom_nodes):
    # Create node-set/surface text before *End Assembly and equation/tie text
    # after it.  The global coordinates used below respect P25 instance data.
    assembly_add = [
        "*Instance, name=V12_UPSTREAM_GEOMEMBRANE-1, part=V12_UPSTREAM_GEOMEMBRANE",
        "*End Instance",
        "**",
    ]
    interaction_add = []
    hydro_add = []
    global HYDRO_BC_ENTRIES
    global INITIAL_RATIO_LINES
    HYDRO_BC_ENTRIES = []
    INITIAL_RATIO_LINES = ["** V12 neutral initial void ratio for coupled porous elements",
                           "*Initial Conditions, type=RATIO"]
    node_set_counter = 0

    assembly_add.extend(set_line("V12_RATIO_GEOMEMBRANE",
                                 "V12_UPSTREAM_GEOMEMBRANE-1",
                                 list(range(1, len(geom_nodes) + 1))))
    INITIAL_RATIO_LINES.append("V12_RATIO_GEOMEMBRANE, %s" % fmt(INITIAL_VOID_RATIO))

    # Upstream boundary nodes come from the original element-based surface
    # definition, but node labels are recomputed from the corrected mesh.
    lookup_by_instance = {}
    for instance, part in instances:
        lookup_by_instance[instance] = element_lookup(corrected[part])
    upstream = collections.OrderedDict()
    for set_name, value in sorted(assembly_sets_global.items()):
        instance = value["instance"]
        part = dict(instances)[instance]
        face_label = int(set_name.rsplit("_S", 1)[1])
        by_label = lookup_by_instance[instance]
        for eid in value["labels"]:
            if eid not in by_label:
                continue
            etype, nodes = by_label[eid]
            base_type = "C3D8R" if etype.startswith("C3D8") else "C3D6"
            indices = dict(FACE_MAP[base_type]).get(face_label)
            if indices is None:
                continue
            for index in indices:
                label = nodes[index]
                coord = global_coord(instance, part, corrected[part]["nodes"][label])
                upstream[(instance, label)] = coord

    # Downstream is the maximum global-x exposed node of every porous P25
    # region.  It is a tailwater head boundary, not a mechanical pressure.
    downstream = collections.OrderedDict()
    for instance, part in instances:
        if (not instance.startswith("P25_") or
                part != "P25_SOLID_DRAINAGE_BODY_F00" or
                not instance_is_porous(instance, part, corrected)):
            continue
        coords = [(label, global_coord(instance, part, coord))
                  for label, coord in corrected[part]["nodes"].items()]
        xmax = max(coord[0] for _, coord in coords)
        for label, coord in coords:
            if abs(coord[0] - xmax) < 1.0e-5:
                downstream[(instance, label)] = coord

    # Add one pore-pressure reference per porous instance, deliberately
    # excluding nodes already prescribed by upstream or tailwater heads.
    reserved = set(upstream) | set(downstream)
    for instance, part in instances:
        if not instance_is_porous(instance, part, corrected):
            continue
        candidates = [(label, coord) for label, coord in corrected[part]["nodes"].items()
                      if (instance, label) not in reserved]
        if not candidates:
            continue
        label = sorted(candidates)[0][0]
        name = "V12_P_REF_%04d" % node_set_counter
        assembly_add.extend(set_line(name, instance, [label]))
        hydro_add.append("%s, 8, 8, 0." % name)
        ratio_set = "V12_RATIO_%04d" % node_set_counter
        node_labels = sorted(corrected[part]["nodes"])
        assembly_add.extend(set_line(ratio_set, instance, node_labels))
        INITIAL_RATIO_LINES.append("%s, %s" % (ratio_set, fmt(INITIAL_VOID_RATIO)))
        node_set_counter += 1

    for prefix, values in (("V12_U", upstream), ("V12_D", downstream)):
        for index, ((instance, label), coord) in enumerate(sorted(values.items())):
            name = "%s_%05d" % (prefix, index)
            assembly_add.extend(set_line(name, instance, [label]))
            entry = {"set": name, "z": coord[2], "p": {}}
            for step, head in UPSTREAM_HEADS.items():
                H = head if prefix == "V12_U" else DOWNSTREAM_HEADS[step]
                entry["p"][step] = WATER_UNIT_WEIGHT * max(H - coord[2], 0.0)
            HYDRO_BC_ENTRIES.append(entry)

    def make_surface(prefix, item_groups):
        groups = surface_elsets(assembly_add, prefix, item_groups)
        return groups

    tie_records = []
    hydraulic_records = []
    interface_index = 0
    exact_nodes_by_instance = collections.defaultdict(set)
    for item in exact:
        for instance, face_map in ((item["master"][0], item["faces_master"]),
                                    (item["secondary"][0], item["faces_secondary"])):
            for key in item["keys"]:
                exact_nodes_by_instance[instance].update(face_map[key][3])
    for item in exact:
        (im, pm), (isec, psec) = item["master"], item["secondary"]
        master_fmap = dict((key, item["faces_master"][key]) for key in item["keys"])
        sec_fmap = dict((key, item["faces_secondary"][key]) for key in item["keys"])
        master_groups = make_surface("V12_IF_%03d_M" % interface_index,
                                     [(im, pm, master_fmap)])
        sec_groups = make_surface("V12_IF_%03d_S" % interface_index,
                                  [(isec, psec, sec_fmap)])
        master_surface = "V12_IF_%03d_MASTER" % interface_index
        sec_surface = "V12_IF_%03d_SECONDARY" % interface_index
        append_surface(assembly_add, master_surface, master_groups)
        append_surface(assembly_add, sec_surface, sec_groups)
        tie_name = "V12_TIE_%03d" % interface_index
        tie_records.append((tie_name, master_surface, sec_surface, item["tolerance"]))

        # For coupled elements Abaqus' surface Tie eliminates the complete
        # active secondary-node DOF set, including pore pressure DOF 8.  A
        # second *Equation on the same nodes is therefore invalid; the Tie is
        # the single pressure-continuity constraint on exact interfaces.
        interface_index += 1

    for aggregate in aggregates:
        # A boundary node can already be secondary in an exact face Tie at a
        # mesh edge.  Remove every face touching such a node before making the
        # nonconformal aggregate Tie; this keeps the constraint graph unique.
        def nonoverlap_items(items):
            result = []
            for instance, part, fmap in items:
                if not instance_is_porous(instance, part, corrected):
                    continue
                excluded = exact_nodes_by_instance.get(instance, set())
                safe = dict((key, value) for key, value in fmap.items()
                            if not (set(value[3]) & excluded))
                result.append((instance, part, safe))
            return result

        master_items = nonoverlap_items(aggregate["master_items"])
        secondary_items = nonoverlap_items(aggregate["secondary_items"])
        master_groups = make_surface("V12_AGG_%03d_M" % interface_index,
                                     master_items)
        sec_groups = make_surface("V12_AGG_%03d_S" % interface_index,
                                  secondary_items)
        if not master_groups or not sec_groups:
            interface_index += 1
            continue
        master_surface = "V12_AGG_%03d_MASTER" % interface_index
        sec_surface = "V12_AGG_%03d_SECONDARY" % interface_index
        append_surface(assembly_add, master_surface, master_groups)
        append_surface(assembly_add, sec_surface, sec_groups)
        tie_records.append(("V12_TIE_%03d" % interface_index, master_surface,
                            sec_surface, aggregate["tolerance"]))
        interface_index += 1

    # Add the actual geomembrane instance and direct ties to the existing
    # upstream fill surface and corrected cutoff-wall top.
    assembly_add.extend([
        "*Elset, elset=V12_GM_TOP_INST, instance=V12_UPSTREAM_GEOMEMBRANE-1",
        "V12_GEOMEMBRANE_TOP",
    ])
    append_surface(assembly_add, "V12_GEOMEMBRANE_TOP", [("V12_GM_TOP_INST", 2)])
    gm_face_elset = "V12_GM_FACE_INST"
    assembly_add.extend(["*Elset, elset=%s, instance=V12_UPSTREAM_GEOMEMBRANE-1" % gm_face_elset,
                         "ALL"])
    append_surface(assembly_add, "V12_GEOMEMBRANE_FACE", [(gm_face_elset, 3)])

    cutoff_instance = "P25_SOLID_CUTOFF_WALL_F13-1"
    cutoff_part = dict(instances)[cutoff_instance]
    cutoff_top = condition_faces(
        face_maps[cutoff_instance],
        lambda pts: all(abs(p[2] - max(v[2] for v in [global_coord(cutoff_instance,
            cutoff_part, c) for c in corrected[cutoff_part]["nodes"].values()])) < 1.0e-4
                         for p in pts))
    cutoff_groups = surface_elsets(assembly_add, "V12_CUTOFF_TOP", [
        (cutoff_instance, cutoff_part, cutoff_top)])
    append_surface(assembly_add, "V12_CUTOFF_TOP_SURFACE", cutoff_groups)
    tie_records.extend([
        ("V12_TIE_GEOMEMBRANE_FILL", "P25_UPSTREAM_PRESSURE", "V12_GEOMEMBRANE_FACE", 2.0),
        ("V12_TIE_GEOMEMBRANE_CUTOFF", "V12_CUTOFF_TOP_SURFACE", "V12_GEOMEMBRANE_TOP", 1.5),
    ])

    for tie_name, master, secondary, tolerance in tie_records:
        interaction_add.extend(["*Tie, name=%s, position tolerance=%s, adjust=NO" %
                                 (tie_name, fmt(tolerance)), "%s, %s" % (master, secondary)])
    if hydraulic_records:
        interaction_add.append("** V12 hydraulic continuity equations: P DOF 8 on coincident interface nodes.")
        for mset, sset, count, tie_name in hydraulic_records:
            interaction_add.extend(["*Equation", "2", "%s, 8, 1." % mset,
                                     "%s, 8, -1." % sset])

    # Add reference P=0 lines to the original base displacement block.
    # They stabilize the initial geostatic hydraulic nullspace; the head BCs
    # replace this reference on the actual reservoir/tailwater boundaries.
    new_lines = []
    inserted_assembly = False
    for line in lines:
        if re.match(r"\*End Assembly", line.strip(), re.I) and not inserted_assembly:
            new_lines.extend(assembly_add)
            new_lines.extend(["** V12 constraints and interaction definitions"])
            new_lines.extend(interaction_add)
            inserted_assembly = True
        new_lines.append(line)
        if line.strip() == "BASE_FIX, 3, 3":
            new_lines.extend(hydro_add)
    return new_lines, {
        "tie_records": tie_records,
        "hydraulic_records": hydraulic_records,
        "upstream_count": len(upstream),
        "downstream_count": len(downstream),
        "hydro_bc_entries": list(HYDRO_BC_ENTRIES),
    }


def extract_materials(lines):
    records = collections.OrderedDict()
    current = None
    mode = None
    for line in lines:
        s = line.strip()
        match = re.match(r"\*Material,\s*name=([^,]+)", s, re.I)
        if match:
            current = match.group(1)
            records[current] = {"density": None, "elastic": None, "k": None}
            mode = None
            continue
        if current is None:
            continue
        name = keyword_name(line)
        if name == "DENSITY":
            mode = "density"
        elif name == "ELASTIC":
            mode = "elastic"
        elif name == "PERMEABILITY":
            mode = "k"
        elif is_keyword(line):
            mode = None
        elif s and not s.startswith("**"):
            values = [v.strip() for v in s.split(",") if v.strip()]
            try:
                if mode == "density": records[current]["density"] = float(values[0])
                elif mode == "elastic": records[current]["elastic"] = (float(values[0]), float(values[1]))
                elif mode == "k": records[current]["k"] = float(values[0])
            except Exception:
                pass
    return records


def write_reports(out_dir, source, source_lines, corrected, instances, interface_info,
                  materials, final_lines, source_sha):
    os.makedirs(out_dir, exist_ok=True)
    materials_csv = os.path.join(out_dir, "v12_3d_materials.csv")
    with open(materials_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["material", "density_t_per_m3", "density_basis",
                         "permeability_m_per_s", "permeability_basis", "E_kPa", "nu"])
        for name, row in materials.items():
            if name in DAM_DENSITY:
                basis = "report unit weight kN/m3 converted rho=gamma/9.81"
            elif name in GEO_K:
                basis = "source dry density g/cm3 = t/m3 in m-kN-s-tonne"
            elif name == "P25_FANGSHENQIANG":
                basis = "2.44 retained; source unit not explicit"
            else:
                basis = "existing mass-density value retained"
            k_basis = "report value cm/s divided by 100" if name in GEO_K else (
                "task value; isotropic, specific weight 9.81" if row["k"] is not None else "UNRESOLVED")
            writer.writerow([name, "" if row["density"] is None else fmt(row["density"]),
                             basis, "" if row["k"] is None else fmt(row["k"]),
                             k_basis, "" if row["elastic"] is None else fmt(row["elastic"][0]),
                             "" if row["elastic"] is None else fmt(row["elastic"][1])])

    interfaces_csv = os.path.join(out_dir, "v12_3d_interfaces.csv")
    with open(interfaces_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "kind", "master", "secondary", "matched_faces",
                         "tie_tolerance_m", "hydraulic_equation_nodes", "status"])
        for index, item in enumerate(interface_info["exact"]):
            im, _ = item["master"]; isec, _ = item["secondary"]
            hydro = next((v[2] for v in interface_info["hydraulic_records"]
                          if v[3] == "V12_TIE_%03d" % index), 0)
            writer.writerow(["V12_TIE_%03d" % index, "exact", im, isec,
                             len(item["keys"]), item["tolerance"], hydro,
                             "TIED; hydraulic P equations where coincident nodes exist"])
        offset = len(interface_info["exact"])
        tie_ids = set(record[0] for record in interface_info["tie_records"])
        for j, item in enumerate(interface_info["aggregates"]):
            aggregate_id = "V12_TIE_%03d" % (offset + j)
            aggregate_status = (
                "MECHANICAL TIE; hydraulic continuity requires solver check"
                if aggregate_id in tie_ids else
                "SKIPPED_NO_NONOVERLAP_SURFACE; no aggregate Tie emitted")
            writer.writerow([aggregate_id, "aggregate",
                             item["name"], item["name"], "NONCONFORMAL",
                             item["tolerance"], 0, aggregate_status])
        writer.writerow(["V12_TIE_GEOMEMBRANE_FILL", "geomembrane", "V12_UPSTREAM_SURFACE",
                         "V12_GEOMEMBRANE_FACE", "NONCONFORMAL", 2.0, 0,
                         "TIED; pore continuity requires solver check"])
        writer.writerow(["V12_TIE_GEOMEMBRANE_CUTOFF", "geomembrane",
                         "V12_CUTOFF_TOP_SURFACE", "V12_GEOMEMBRANE_TOP", "NONCONFORMAL", 1.5,
                         0, "TIED; connected at z=3073.51147 m"])

    element_csv = os.path.join(out_dir, "v12_3d_element_types.csv")
    with open(element_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["part", "material", "original_element_type", "final_element_type", "count", "porous_region"])
        for name, part in corrected.items():
            for etype, elems in part["elements"].items():
                final_type = {"C3D8R": "C3D8P", "C3D6": "C3D6P"}.get(
                    etype, etype) if part["material"] in POROUS_MATERIALS else etype
                writer.writerow([name, part["material"], etype, final_type, len(elems),
                                 "YES" if part["material"] in POROUS_MATERIALS else "NO"])
        writer.writerow(["V12_UPSTREAM_GEOMEMBRANE", "GEOMEMBRANE", "new", "C3D8P", 80, "YES"])

    bc_csv = os.path.join(out_dir, "v12_3d_hydraulic_bc_check.csv")
    with open(bc_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["boundary", "step", "head_m", "sample_z_m", "expected_p_kPa", "formula"])
        entries = interface_info["hydro_bc_entries"]
        for boundary in ("UPSTREAM", "DOWNSTREAM"):
            selected = entries[:5] if boundary == "UPSTREAM" else entries[-5:]
            for step in UPSTREAM_HEADS:
                head = UPSTREAM_HEADS[step] if boundary == "UPSTREAM" else DOWNSTREAM_HEADS[step]
                for entry in selected:
                    if (boundary == "UPSTREAM") != entry["set"].startswith("V12_U"):
                        continue
                    writer.writerow([boundary, step, fmt(head), fmt(entry["z"]),
                                     fmt(entry["p"][step]), "9.81*max(H-z,0)"])

    keywords = os.path.join(out_dir, "v12_3d_keywords_no_mesh.txt")
    with open(keywords, "w", encoding="utf-8") as handle:
        handle.write("V12 corrected keyword inventory (mesh data intentionally omitted)\n")
        handle.write("source_sha256=%s\n" % source_sha)
        handle.write("source=%s\n" % source)
        handle.write("final_element_types=C3D8P/C3D6P in source-supported porous regions; C3D8R retained for unsupported rock/concrete\n")
        handle.write("procedure=S01 *Geostatic; S02-S06 *Soils, consolidation, end=SS\n")
        handle.write("pore_dof=8; head_formula=p=9.81*max(H-z,0) kPa\n")
        for line in final_lines:
            if is_keyword(line) and keyword_name(line) not in ("NODE", "ELEMENT"):
                handle.write(line + "\n")

    diagnosis = os.path.join(out_dir, "V11_3D_HYDRO_DIAGNOSIS.md")
    with open(diagnosis, "w", encoding="utf-8") as handle:
        handle.write("# v11 3-D hydro-mechanical diagnosis\n\n")
        handle.write("- Source v11 SHA-256: `%s` (read-only; not overwritten).\n" % source_sha)
        handle.write("- Source parts/instances: %d/%d.\n" % (len(corrected), len(instances)))
        handle.write("- v11 porous mesh used ordinary `C3D8R/C3D6` and ordinary `*Static`; no pore-pressure DOF.\n")
        handle.write("- v11 had no effective interface tie/contact network; 40 exact boundary-pair groups were found by audit.\n")
        handle.write("- v11 geological/foundation materials lacked the 14 report-based permeability entries.\n")
        handle.write("- v11 used constant face pressures 220/250/285/80 kPa rather than elevation-dependent heads.\n")
        handle.write("- v11 main cutoff wall was 2.0 m thick with base about 3017.98 m; BX02/BX03 exceeded the report elevation ranges.\n")
        handle.write("- v11 defined `GEOMEMBRANE` but did not assign it to an actual region.\n\n")
        handle.write("## Corrective choices\n\n")
        handle.write("- Exact coincident boundary faces receive surface-based Tie constraints; nonconformal left/river/right geology and dam/foundation boundaries receive aggregate Ties with documented tolerances.\n")
        handle.write("- Exact coupled-interface pore pressure is carried by the surface Tie constraint; an additional DOF 8 `*Equation` is intentionally not emitted because Abaqus eliminates tied secondary DOF 8. Aggregate nonconformal hydraulic continuity remains a solver verification item.\n")
        handle.write("- The v12 geomembrane is an actual 1.0 m equivalent C3D8P layer from z=3055.0 to the cutoff top z=3073.51147 m; `t/k` is explicit in the result report.\n")
        handle.write("- Plasticity is not enabled in the baseline because a complete source-supported dilation set is unavailable; no dilation was invented.\n")
        handle.write("- BX01/BX02/BX03 are retained and linearly repositioned to report ranges (2990-3305, 3005-3201, 3040-3170 m).\n")

    result = os.path.join(out_dir, "V12_3D_HYDRO_FIX_RESULT.md")
    with open(result, "w", encoding="utf-8") as handle:
        handle.write("# v12 3-D hydro-mechanical correction result\n\n")
        handle.write("## Scope and preservation\n\n")
        handle.write("The exact v11 source was read from `%s` and was not modified. v12 is a corrected copy with an exported keyword deck.\n\n" % source)
        handle.write("- Source SHA-256: `%s`\n" % source_sha)
        handle.write("- Abaqus unit system: m-kN-s-tonne; pressure in kPa; gravity 9.81 m/s2 in global -Z.\n")
        handle.write("- Main model domain: 295 m P25 riverbed section, with the existing left/river/right geology and appurtenant structures retained.\n\n")
        handle.write("## Changes versus v11\n\n")
        handle.write("- Regions with task/source-supported permeability (14 Q geology zones, dam fill/cutoff, and the geomembrane) use C3D8P/C3D6P; unsupported rock/foundation materials remain C3D8R and are flagged in the element/material CSVs.\n")
        handle.write("- S01 is `*Geostatic`; S02-S06 are coupled pore-fluid `*Soils, consolidation, end=SS` steps with pore output.\n")
        handle.write("- All 14 geological/foundation permeability values are present in `v12_3d_materials.csv`.\n")
        handle.write("- Constant mechanical pressure loads were removed. Direct head BCs use p=9.81 max(H-z,0).\n")
        handle.write("- Cutoff wall local thickness is 1.0 m (x=-36 to -35) and main-section base is z/local elevation 3021.0 m; the separate powerhouse wall remains at its source geometry.\n")
        handle.write("- An actual assigned upstream geomembrane equivalent C3D8P layer is connected to the existing upstream fill surface and cutoff top.\n")
        handle.write("- Density conversions are applied only to explicit report unit-weight examples; unsupported source-unit cases are marked.\n\n")
        handle.write("## Permeability table\n\n")
        handle.write("See `v12_3d_materials.csv`; geological source values are cm/s divided by 100 to m/s.\n\n")
        for name, value in GEO_K.items():
            handle.write("- `%s`: %.6g m/s\n" % (name, value))
        handle.write("- GEOMEMBRANE: 4.5e-11 m/s; equivalent layer thickness 1.0 m; t/k=2.2222e10 s.\n")
        handle.write("- CUTOFF WALL: 1.0e-8 m/s.\n\n")
        handle.write("## Hydraulic boundary conditions\n\n")
        handle.write("- S03 normal: upstream H=3076.00 m.\n- S04 design-flood discharge: H=3076.00 m hold level because a separate supported design-flood level is not provided; this is unresolved.\n- S05 check flood: upstream H=3077.35 m.\n- S06 drawdown/dead-water: upstream H=3074.00 m.\n- Downstream/tailwater: H=3055.00 m, the documented 3054-3056 m normal river range; flood-case tailwater variation is unresolved.\n\n")
        handle.write("## Connectivity and hydraulic continuity\n\n")
        handle.write("- Exact face groups: %d; aggregate nonconformal groups: %d; total generated mechanical Ties including geomembrane: %d.\n" %
                     (len(interface_info["exact"]), len(interface_info["aggregates"]),
                      len(interface_info["tie_records"])))
        handle.write("- Exact-interface hydraulic `*Equation` groups: %d / %d node pairs; exact pressure continuity is carried by the corresponding surface Tie constraints because Abaqus eliminates tied secondary DOF 8.\n" %
                     (len(interface_info["hydraulic_records"]),
                      sum(v[2] for v in interface_info["hydraulic_records"])))
        handle.write("- Nonconformal aggregate Ties require Abaqus ODB verification of boundary POR continuity; no unsupported claim is made here.\n\n")
        handle.write("## Initial stress, sequence, and plasticity\n\n")
        handle.write("S01 establishes gravity/geostatic equilibrium, S02 is a labelled construction/closure stabilization step on the active mesh, S03 normal impoundment, S04 design-flood hold, S05 check flood plus 0.206g equivalent horizontal gravity, and S06 drawdown. True element activation staging and source-complete plastic dilation remain unresolved; baseline is elastic coupled seepage.\n\n")
        handle.write("## BX decision\n\n")
        handle.write("BX01/BX02/BX03 are within the intended retained right-bank domain and were repositioned to report ranges. The linear z remap preserves plan footprint but is a geometric correction, not a substitute for DBK-D-34-37 surveyed surfaces.\n\n")
        handle.write("## Validation status\n\n")
        handle.write("The build emits `v12_3d_validation_status.txt`. CAE import/data check/full seepage run must be read from the generated Abaqus logs; convergence, POR continuity, and hydraulic mass balance are not claimed unless those logs contain the corresponding evidence.\n")


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: repair_v12_3d.py SOURCE_V11_INP OUTPUT_DIR")
    source = os.path.abspath(sys.argv[1])
    out_dir = os.path.abspath(sys.argv[2])
    os.makedirs(out_dir, exist_ok=True)
    source_lines, source_parts, instances, assembly_sets = parse_deck(source)
    corrected = corrected_parts(source_parts)
    exact, face_maps = exact_interfaces(instances, corrected)
    aggregates = aggregate_interfaces(instances, corrected, face_maps)
    global assembly_sets_global
    assembly_sets_global = assembly_sets
    geom_lines, geom_nodes, geom_elements, geom_top = new_geomembrane_part()
    insert_at = next(i for i, line in enumerate(source_lines)
                     if re.match(r"\*Assembly,", line.strip(), re.I))
    with_geom = list(source_lines)
    with_geom[insert_at:insert_at] = geom_lines
    final_lines, constraint_info = build_assembly_and_constraints(
        with_geom, corrected, instances, exact, aggregates, face_maps, geom_top, geom_nodes)
    # The builder adds assembly blocks to the input, then performs the normal
    # node/element/procedure/material transformation in one deterministic pass.
    final_lines = transform_lines(final_lines, source_parts, corrected)
    inp_name = "doub_hydropower_part25_geometric_solids_v12_hydro_corrected.inp"
    out_inp = os.path.join(out_dir, inp_name)
    with open(out_inp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(final_lines) + "\n")
    source_sha = hashlib.sha256(open(source, "rb").read()).hexdigest().upper()
    materials = extract_materials(final_lines)
    interface_info = {
        "exact": exact, "aggregates": aggregates,
        "tie_records": constraint_info["tie_records"],
        "hydraulic_records": constraint_info["hydraulic_records"],
        "hydro_bc_entries": constraint_info["hydro_bc_entries"],
    }
    write_reports(out_dir, source, source_lines, corrected, instances,
                  interface_info, materials, final_lines, source_sha)
    status = os.path.join(out_dir, "v12_3d_validation_status.txt")
    with open(status, "w", encoding="utf-8") as handle:
        handle.write("V12 3-D validation status (pre-solver build)\n")
        handle.write("==========================================\n")
        handle.write("source_sha256=%s\n" % source_sha)
        handle.write("corrected_inp=%s\n" % out_inp)
        handle.write("exact_interface_groups=%d\n" % len(exact))
        handle.write("aggregate_interface_groups=%d\n" % len(aggregates))
        handle.write("mechanical_ties=%d\n" % len(constraint_info["tie_records"]))
        handle.write("hydraulic_equation_groups=%d\n" % len(constraint_info["hydraulic_records"]))
        handle.write("upstream_head_nodes=%d\n" % constraint_info["upstream_count"])
        handle.write("downstream_head_nodes=%d\n" % constraint_info["downstream_count"])
        handle.write("CAE_IMPORT=NOT_RUN\nDATA_CHECK=NOT_RUN\nGEOSTATIC=NOT_RUN\nNORMAL_SEEPAGE=NOT_RUN\n")
        handle.write("POR_CONTINUITY=NOT_RUN\nHYDRAULIC_MASS_BALANCE=NOT_RUN\n")
        handle.write("UNRESOLVED=design-flood level, flood tailwater variation, nonconformal hydraulic ODB check, staged activation, source-complete plastic dilation\n")
    print("V12_BUILD_COMPLETE %s" % out_inp)
    print("SOURCE_SHA256 %s" % source_sha)
    print("EXACT_INTERFACES %d AGGREGATES %d TIES %d HYD_EQ_GROUPS %d" %
          (len(exact), len(aggregates), len(constraint_info["tie_records"]),
           len(constraint_info["hydraulic_records"])))


if __name__ == "__main__":
    main()
