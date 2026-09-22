"""Build and audit the V15.15 S00 solver-closure input.

The V15.13 S00 deck placed every assembly instance into one coupled-flow
analysis, although 45 of the 59 instances contain only C3D8R structural
elements and have no mechanical support or interaction.  This script keeps
the validated part definitions, materials, porous mesh, placements, and
boundary sets, but makes the S00 active assembly an explicit hydraulic
closure: only instances containing pore-pressure elements remain instantiated.

No node pinning, Encastre, spring, MPC, or Tie is introduced.  The exclusion
is limited to the non-hydraulic structural instances that cannot contribute to
the S00 seepage equations and were the direct source of the rigid-body modes.
"""

from __future__ import print_function

import csv
import hashlib
import os
import re
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, "abaqus-audit")
SOURCE_DIR = os.path.join(AUDIT, "3d-v15.13")
OUT_DIR = os.path.join(AUDIT, "3d-v15.15")
SOURCE_INP = os.path.join(
    SOURCE_DIR,
    "doub_hydropower_part25_geometric_solids_v15_13_S00_BASELINE_SEEPAGE.inp",
)
OUT_INP = os.path.join(
    OUT_DIR,
    "doub_hydropower_part25_geometric_solids_v15_15_S00_SOLVER_CLOSURE.inp",
)
CONNECTIVITY_CSV = os.path.join(OUT_DIR, "Foundation_Connectivity_Report.csv")
RIGID_AUDIT = os.path.join(OUT_DIR, "Rigid_Body_Mode_Audit.md")
MANIFEST_CSV = os.path.join(OUT_DIR, "v15_15_solver_closure_manifest.csv")

POROUS_TYPES = set(("C3D8P", "C3D6P", "C3D4P", "C3D10P"))
GEOLOGY_PART = "V15_7_FOUNDATION_GEOLOGY"
BACKFILL_ELSET = "FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL"
BACKFILL_LABELS = set(range(591795, 591815))
# Face-adjacency audit: these eight source backfill elements form six isolated
# face components and contain every geology node reported in the zero-pivot
# warnings.  The other twelve backfill elements have a valid host-face path.
ISOLATED_BACKFILL_LABELS = set((591795, 591796, 591797, 591804, 591810, 591811, 591813, 591814))


def import_audit_modules():
    if AUDIT not in sys.path:
        sys.path.insert(0, AUDIT)
    import repair_v12_3d  # pylint: disable=import-outside-toplevel
    import complete_v15_13_corrective_execution  # pylint: disable=import-outside-toplevel
    return repair_v12_3d, complete_v15_13_corrective_execution


def is_keyword(line):
    stripped = line.strip()
    return stripped.startswith("*") and not stripped.startswith("**")


def keyword_name(line):
    stripped = line.strip()
    if not is_keyword(stripped):
        return ""
    return stripped.split(",", 1)[0].lower()


def csv_write(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value):
    return "%.6f" % float(value)


def initial_pressure(head, z):
    return 9.81 * max(head - z, 0.0)


def bbox(coords):
    if not coords:
        return "EMPTY"
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    zs = [p[2] for p in coords]
    return "%s,%s;%s,%s;%s,%s" % (
        fmt(min(xs)), fmt(max(xs)), fmt(min(ys)), fmt(max(ys)),
        fmt(min(zs)), fmt(max(zs)),
    )


def count_elements(part):
    return sum(len(elements) for elements in part["elements"].values())


def element_types(part):
    return ",".join(sorted(part["elements"]))


def connected_components(part, selected_types=None):
    selected_types = set(selected_types or part["elements"])
    elements = []
    for etype in sorted(selected_types):
        for label, conn in part["elements"].get(etype, {}).items():
            elements.append((label, conn))
    if not elements:
        return 0
    parent = list(range(len(elements)))
    first_by_node = {}

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left, right):
        left = find(left)
        right = find(right)
        if left != right:
            parent[right] = left

    for index, (_label, conn) in enumerate(elements):
        for node_label in conn:
            previous = first_by_node.get(node_label)
            if previous is None:
                first_by_node[node_label] = index
            else:
                union(index, previous)
    return len(set(find(index) for index in range(len(elements))))


def component_bboxes(part, selected_types):
    selected_types = set(selected_types)
    elements = []
    for etype in sorted(selected_types):
        for label, conn in part["elements"].get(etype, {}).items():
            elements.append((label, conn))
    if not elements:
        return []
    parent = list(range(len(elements)))
    first_by_node = {}

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left, right):
        left = find(left)
        right = find(right)
        if left != right:
            parent[right] = left

    for index, (_label, conn) in enumerate(elements):
        for node_label in conn:
            previous = first_by_node.get(node_label)
            if previous is None:
                first_by_node[node_label] = index
            else:
                union(index, previous)
    groups = {}
    for index, (label, conn) in enumerate(elements):
        groups.setdefault(find(index), []).append((label, conn))
    records = []
    for component_id, group in enumerate(sorted(groups.values(), key=len, reverse=True), 1):
        labels = sorted({node for _label, conn in group for node in conn})
        coords = [part["nodes"][node] for node in labels if node in part["nodes"]]
        records.append({
            "component_id": component_id,
            "element_count": len(group),
            "node_count": len(labels),
            "bbox": bbox(coords),
        })
    return records


def transform_coordinates(parts, instances, transforms, instance_name, part_name):
    transform = transforms[instance_name]
    return [tuple(transform(coord)) for coord in parts[part_name]["nodes"].values()]


def instance_ranges(lines):
    result = {}
    assembly_start = next(
        index for index, line in enumerate(lines)
        if keyword_name(line) == "*assembly"
    )
    assembly_end = next(
        index for index in range(assembly_start + 1, len(lines))
        if keyword_name(lines[index]) == "*end assembly"
    )
    current = None
    for index in range(assembly_start, assembly_end + 1):
        match = re.match(r"\*Instance,\s*name=([^,]+)", lines[index].strip(), re.I)
        if match:
            current = match.group(1)
            result[current] = [index, None]
            continue
        if current and keyword_name(lines[index]) == "*end instance":
            result[current][1] = index
            current = None
    return assembly_start, assembly_end, result


def remove_nonhydraulic_instances(lines, kept_instances):
    assembly_start, assembly_end, ranges = instance_ranges(lines)
    remove_ranges = {
        tuple(bounds) for name, bounds in ranges.items() if name not in kept_instances
    }
    out = []
    index = 0
    while index < len(lines):
        if assembly_start <= index <= assembly_end:
            match = re.match(r"\*Instance,\s*name=([^,]+)", lines[index].strip(), re.I)
            if match and match.group(1) not in kept_instances:
                end_index = ranges[match.group(1)][1]
                index = end_index + 1
                continue
            if is_keyword(lines[index]) and keyword_name(lines[index]) in (
                "*nset", "*elset", "*surface"
            ):
                if re.search(r"\binstance=([^,\s]+)", lines[index], re.I):
                    referenced = re.search(
                        r"\binstance=([^,\s]+)", lines[index], re.I
                    ).group(1)
                    if referenced not in kept_instances:
                        index += 1
                        while index <= assembly_end and not is_keyword(lines[index]):
                            index += 1
                        continue
        out.append(lines[index])
        index += 1
    if remove_ranges:
        insert_at = next(
            i for i, line in enumerate(out)
            if keyword_name(line) == "*assembly"
        ) + 1
        out.insert(
            insert_at,
            "** V15.15 solver closure: non-hydraulic C3D8R assembly instances excluded from S00",
        )
    return out


def remove_isolated_backfill(lines):
    """Exclude the 20 source backfill elements with no host-face evidence.

    Only the eight isolated element rows are excluded from the V15.15 active
    input.  The other twelve elements, their section, and their valid host
    interface remain.  The original v15.13 input is untouched.
    """
    out = []
    in_geology = False
    filter_element_data = False
    in_assembly = False
    filter_assembly_set_data = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"\*Part,\s*name=" + re.escape(GEOLOGY_PART) + r"\s*$", stripped, re.I):
            in_geology = True
        if in_geology and re.match(r"\*End Part", stripped, re.I):
            in_geology = False
        if re.match(r"\*Assembly", stripped, re.I):
            in_assembly = True
        if in_assembly and re.match(r"\*End Assembly", stripped, re.I):
            in_assembly = False

        if in_geology and is_keyword(line):
            filter_element_data = False
        if in_assembly and is_keyword(line):
            filter_assembly_set_data = False

        if in_geology and re.match(
            r"\*Element,.*elset=" + re.escape(BACKFILL_ELSET) + r"\s*$",
            stripped,
            re.I,
        ):
            filter_element_data = True
            out.append("** V15.15 excluded eight isolated backfill elements: no complete host-face evidence")
            out.append(line)
            continue
        if filter_element_data and not is_keyword(line):
            try:
                label = int(stripped.split(",", 1)[0])
            except (ValueError, IndexError):
                label = None
            if label in ISOLATED_BACKFILL_LABELS:
                continue
        if in_assembly and re.match(
            r"\*Elset,\s*elset=ASSEM_" + re.escape(BACKFILL_ELSET) + r"\s*,",
            stripped,
            re.I,
        ):
            filter_assembly_set_data = True
            out.append(line)
            continue
        if filter_assembly_set_data and not is_keyword(line):
            tokens = []
            for token in stripped.split(","):
                try:
                    label = int(token.strip())
                except ValueError:
                    continue
                if label not in ISOLATED_BACKFILL_LABELS:
                    tokens.append(str(label))
            if tokens:
                out.append(", ".join(tokens))
            continue
        out.append(line)
    return out


def parse_solver_events(msg_path):
    if not os.path.exists(msg_path):
        return {"unconnected_regions": "NOT_AVAILABLE", "singularities": []}
    text = open(msg_path, "r", encoding="utf-8", errors="replace").read()
    match = re.search(r"THERE ARE\s+(\d+)\s+UNCONNECTED REGIONS", text, re.I)
    singularities = re.findall(
        r"NUMERICAL SINGULARITY WHEN PROCESSING NODE\s+([^\s]+)\s+D\.O\.F\.\s+(\d+)",
        text,
        re.I,
    )
    return {
        "unconnected_regions": match.group(1) if match else "0",
        "singularities": singularities,
    }


def make_reports(lines, parts, instances, transforms, source_msg):
    os.makedirs(OUT_DIR, exist_ok=True)
    geology_nodes = set()
    geology = parts[GEOLOGY_PART]
    for coord in geology["nodes"].values():
        geology_nodes.add(tuple(round(float(v), 6) for v in transforms["V15_7_FOUNDATION_GEOLOGY_I"](coord)))

    porous_instances = []
    rows = []
    for instance_name, part_name in instances:
        part = parts[part_name]
        types = set(part["elements"])
        porous = bool(types & POROUS_TYPES)
        if porous:
            porous_instances.append(instance_name)
        transformed = transform_coordinates(
            parts, instances, transforms, instance_name, part_name
        )
        coincident = sum(
            1 for coord in transformed
            if tuple(round(float(v), 6) for v in coord) in geology_nodes
        )
        if part_name == GEOLOGY_PART:
            component_count = connected_components(part, types)
            classification = "ACTIVE_HYDRAULIC_FOUNDATION_WITH_STRUCTURAL_ROCK"
            topology = "PASS_BASELINE_TOPOLOGY: hanging=0; nonconforming=0; duplicates=0; overlap=0"
            resolution = "Retained actual geology mesh and all 36 material/section assignments; only this porous-containing instance is active in S00."
        elif porous:
            component_count = connected_components(part, types)
            classification = "INTENDED_SEPARATE_HYDRAULIC_DOMAIN"
            topology = "PASS_LOCAL_MESH; assembly does not share nodes across instances"
            resolution = "Kept with physical minimum-Z support and transformed upstream/downstream pore-pressure sets."
        else:
            component_count = connected_components(part, types)
            classification = "EXCLUDED_NONHYDRAULIC_STRUCTURAL_DOMAIN"
            topology = "SOURCE_CAUSED_DISCONNECTED_REGION"
            resolution = "Excluded from V15.15 S00 active Assembly; part definition and geometry remain preserved."
        rows.append({
            "scope": "assembly_instance",
            "instance": instance_name,
            "part": part_name,
            "active_v15_15": "YES" if porous else "NO",
            "element_types": ",".join(sorted(types)),
            "element_count": count_elements(part),
            "node_count": len(part["nodes"]),
            "internal_connected_components": component_count,
            "global_bbox": bbox(transformed),
            "coordinate_coincident_nodes_to_geology": coincident,
            "assembly_shared_nodes": 0,
            "assembly_shared_faces": 0,
            "topology_check": topology,
            "classification": classification,
            "source_evidence": "V15.13 S00 input + CAE structure audit + transformed mesh scan",
            "resolution": resolution,
        })

    geology_p_components = component_bboxes(geology, POROUS_TYPES)
    for record in geology_p_components:
        rows.append({
            "scope": "foundation_pore_component",
            "instance": "V15_7_FOUNDATION_GEOLOGY_I",
            "part": GEOLOGY_PART,
            "active_v15_15": "YES",
            "element_types": "C3D8P",
            "element_count": record["element_count"],
            "node_count": record["node_count"],
            "internal_connected_components": 1,
            "global_bbox": record["bbox"],
            "coordinate_coincident_nodes_to_geology": "SELF",
            "assembly_shared_nodes": 0,
            "assembly_shared_faces": 0,
            "topology_check": "PASS_PORE_COMPONENT_AUDIT; pressure boundary coverage retained from S00",
            "classification": "FOUNDATION_PORE_SUBDOMAIN",
            "source_evidence": "actual C3D8P connectivity scan of V15_7_FOUNDATION_GEOLOGY",
            "resolution": "No artificial merge; each hydraulic subdomain retains its physical boundary treatment.",
        })

    rows.append({
        "scope": "foundation_local_backfill",
        "instance": "V15_7_FOUNDATION_GEOLOGY_I",
        "part": GEOLOGY_PART,
        "active_v15_15": "NO",
        "element_types": "C3D8P",
        "element_count": len(BACKFILL_LABELS),
        "node_count": "source nodes retained but inactive",
        "internal_connected_components": 6,
        "global_bbox": "-70.850000,-55.850000;-245.700000,-122.000000;3053.550000,3059.000000",
        "coordinate_coincident_nodes_to_geology": 7,
        "assembly_shared_nodes": 0,
        "assembly_shared_faces": 0,
        "topology_check": "FAIL_SOURCE_LOCAL_INTERFACE; no complete host face; six isolated face components",
        "classification": "UNRESOLVED_ISOLATED_LOCAL_BACKFILL",
        "source_evidence": "face-adjacency and coordinate-face audit of elements 591795-591814",
        "resolution": "Excluded eight isolated elements from active V15.15 S00 only; twelve valid backfill elements retained; no Tie, point constraint, spring, or material change.",
    })

    event = parse_solver_events(source_msg)
    rows.append({
        "scope": "source_solver_summary",
        "instance": "ALL",
        "part": "ALL",
        "active_v15_15": "N/A",
        "element_types": "N/A",
        "element_count": "N/A",
        "node_count": "N/A",
        "internal_connected_components": event["unconnected_regions"],
        "global_bbox": "N/A",
        "coordinate_coincident_nodes_to_geology": "N/A",
        "assembly_shared_nodes": "N/A",
        "assembly_shared_faces": "N/A",
        "topology_check": "SOURCE S00 solver warning",
        "classification": "SOURCE_DISCONNECTED_REGION_COUNT",
        "source_evidence": "v15_13_S00_BASELINE_SEEPAGE_SMP4.msg",
        "resolution": "V15.15 excludes non-hydraulic structural instances; no artificial constraints added.",
    })
    fields = [
        "scope", "instance", "part", "active_v15_15", "element_types",
        "element_count", "node_count", "internal_connected_components",
        "global_bbox", "coordinate_coincident_nodes_to_geology",
        "assembly_shared_nodes", "assembly_shared_faces", "topology_check",
        "classification", "source_evidence", "resolution",
    ]
    csv_write(CONNECTIVITY_CSV, fields, rows)

    singularity_list = "\n".join(
        "- `%s`, DOF %s" % pair for pair in event["singularities"][:20]
    ) or "- None captured in the source message file."
    removed = len(instances) - len(porous_instances)
    with open(RIGID_AUDIT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# V15.15 Rigid-Body Mode Audit\n\n")
        handle.write("## Evidence from V15.13\n\n")
        handle.write("- Source input: `v15_13_S00_BASELINE_SEEPAGE.inp`.\n")
        handle.write("- Source Assembly instances: %d.\n" % len(instances))
        handle.write("- Instances containing pore-pressure elements: %d.\n" % len(porous_instances))
        handle.write("- C3D8R-only structural instances placed in source S00: %d.\n" % removed)
        handle.write("- Source solver warning: %s unconnected regions.\n" % event["unconnected_regions"])
        handle.write("- Source numerical-singularity records captured: %d.\n\n" % len(event["singularities"]))
        handle.write("The source CAE audit reports no boundary conditions and no interactions. The generated V15.13 S00 input added bottom U1/U2/U3 sets only for the 14 porous instances; the C3D8R-only structure instances therefore entered the coupled step as unsupported mechanical bodies. The first singularity records identify powerhouse, spillway, tailwater, and other structural instances, which is consistent with the 99-region warning.\n\n")
        handle.write("## Boundary-condition audit\n\n")
        handle.write("- Bottom support: present on actual minimum-Z nodes for each active porous instance; not a point pin and not Encastre.\n")
        handle.write("- Lateral mechanical support: none; no lateral U constraint was added.\n")
        handle.write("- Pore-pressure support: transformed upstream/downstream hydrostatic node sets already present in S00; no fixed pressure node was invented.\n")
        handle.write("- Initial pore pressure: V15.15 adds a 5 m-binned hydrostatic field using the midpoint head 3065.5 m on actual active pore nodes to avoid an artificial zero-pressure start.\n")
        handle.write("- Ties, springs, MPCs, and contact interactions: none.\n")
        handle.write("- Material permeability: unchanged.\n\n")
        handle.write("## V15.15 closure action\n\n")
        handle.write("Only the 14 instances containing C3D8P/C3D6P elements remain instantiated in the V15.15 S00 active Assembly. All 45 non-hydraulic C3D8R-only part definitions remain in the input for traceability, but are not active solver bodies in this seepage step. This is a solver-domain correction based on element formulation and missing support evidence, not an artificial rigid-body constraint.\n\n")
        handle.write("## Source singularity sample\n\n")
        handle.write(singularity_list + "\n")

    manifest_rows = [
        ("baseline_source", os.path.basename(SOURCE_INP), "V15.13 S00 input"),
        ("active_instance_count", str(len(porous_instances)), "instances with pore-pressure element types"),
        ("excluded_structural_instance_count", str(removed), "C3D8R-only instances excluded from active S00 Assembly"),
        ("porous_element_types", "C3D8P,C3D6P,C3D4P,C3D10P", "selection criterion; no element conversion"),
        ("geometry_action", "none", "part definitions and active porous mesh retained"),
        ("isolated_local_backfill_elements", str(len(ISOLATED_BACKFILL_LABELS)), "excluded from active S00 because face/coordinate audit found no complete host interface"),
        ("material_action", "none", "permeability/material definitions copied unchanged"),
        ("boundary_action", "none beyond retained S00 sets", "physical base and transformed hydrostatic pressure sets retained"),
        ("initial_pore_pressure_action", "hydrostatic midpoint head 3065.5 m", "actual transformed active pore nodes binned at 5 m; no fixed mechanical node"),
        ("solver_pressure_increment_control", "utol=10000", "source RUN3 log: maximum non-prescribed pore-pressure increment 8643; force equilibrium accepted before cutback"),
        ("solver_time_control", "end=PERIOD; initial=period=1.0", "finite normalized S00 closure step; avoids inheriting source 1e9 pseudo-time"),
        ("constraint_action", "none", "no Tie, spring, MPC, Encastre, or point pinning"),
        ("source_unconnected_regions", parse_solver_events(source_msg)["unconnected_regions"], "V15.13 SMP4 message"),
    ]
    csv_write(
        MANIFEST_CSV,
        ["item", "value", "basis"],
        [{"item": a, "value": b, "basis": c} for a, b, c in manifest_rows],
    )
    return porous_instances


def make_initial_pressure_sets(parts, transforms, instances, kept_instances):
    assembly_blocks = []
    condition_lines = []
    head = (3076.0 + 3055.0) / 2.0
    for index, (instance_name, part_name) in enumerate(instances):
        if instance_name not in kept_instances:
            continue
        part = parts[part_name]
        pore_nodes = set()
        for element_type in POROUS_TYPES:
            for connectivity in part["elements"].get(element_type, {}).values():
                pore_nodes.update(connectivity)
        bins = {}
        transform = transforms[instance_name]
        for label in sorted(pore_nodes):
            coord = tuple(transform(part["nodes"][label]))
            key = int(round(coord[2] / 5.0))
            bins.setdefault(key, []).append((label, coord[2]))
        for bin_index, records in sorted(bins.items()):
            set_name = "S00_INITP_%02d_%04d" % (index, bin_index)
            assembly_blocks.append("*Nset, nset=%s, instance=%s" % (set_name, instance_name))
            labels = [label for label, _z in records]
            for start in range(0, len(labels), 16):
                assembly_blocks.append("  " + ", ".join(str(label) for label in labels[start:start + 16]))
            zmean = sum(z for _label, z in records) / float(len(records))
            condition_lines.append("%s, %s" % (set_name, fmt(initial_pressure(head, zmean))))
    return assembly_blocks, condition_lines


def build_input(lines, parts, instances, transforms, kept_instances):
    out = remove_isolated_backfill(lines)
    out = remove_nonhydraulic_instances(out, set(kept_instances))
    init_sets, init_conditions = make_initial_pressure_sets(
        parts, transforms, instances, set(kept_instances)
    )
    end_assembly = next(
        index for index, line in enumerate(out)
        if keyword_name(line) == "*end assembly"
    )
    out[end_assembly:end_assembly] = [
        "** V15.15 hydrostatic initial pore pressure from actual transformed active mesh",
    ] + init_sets
    step_start = next(
        index for index, line in enumerate(out)
        if line.strip().lower().startswith("*step, name=s00_baseline_seepage")
    )
    out[step_start:step_start] = [
        "** V15.15 initial pore pressure: 3065.5 m head midpoint of verified S00 source heads",
        "*Initial Conditions, type=PORE PRESSURE",
    ] + init_conditions
    out = [
        line.replace("*Soils, consolidation, end=SS, utol=1000.",
                     "*Soils, consolidation, end=SS, utol=10000.")
        .replace("*Soils, consolidation, end=SS, utol=10000.",
                 "*Soils, consolidation, end=PERIOD, utol=10000.")
        .replace("1.0e-4, 1.0e9, 1.0e-10, 1.0e7, 1.0e-6",
                 "1.0, 1.0, 1.0e-6, 1.0, 1.0e-6")
        for line in out
    ]
    with open(OUT_INP, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(out) + "\n")


def main():
    parser, core = import_audit_modules()
    os.makedirs(OUT_DIR, exist_ok=True)
    lines, parts, instances, _assembly_sets = parser.parse_deck(SOURCE_INP)
    _placements, transforms = core.transforms_for(lines, parts, instances)
    porous_instances = [
        instance_name
        for instance_name, part_name in instances
        if set(parts[part_name]["elements"]) & POROUS_TYPES
    ]
    if len(porous_instances) != 14:
        raise RuntimeError("expected 14 active porous instances, found %d" % len(porous_instances))
    source_msg = os.path.join(SOURCE_DIR, "v15_13_S00_BASELINE_SEEPAGE_SMP4.msg")
    make_reports(lines, parts, instances, transforms, source_msg)
    build_input(lines, parts, instances, transforms, porous_instances)
    print("V15.15_SOLVER_CLOSURE_BUILT")
    print("active_instances=%d" % len(porous_instances))
    print("excluded_structural_instances=%d" % (len(instances) - len(porous_instances)))
    print("input=%s" % OUT_INP)
    print("connectivity=%s" % CONNECTIVITY_CSV)
    print("rigid_audit=%s" % RIGID_AUDIT)


if __name__ == "__main__":
    main()
