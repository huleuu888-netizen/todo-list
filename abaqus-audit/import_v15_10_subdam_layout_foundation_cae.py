"""Import V15.10 and export actual Abaqus/CAE geometry-review screenshots."""
from __future__ import print_function

import csv
import os

from abaqus import mdb, session
from abaqusConstants import PNG, WIREFRAME, SHADED
import regionToolset

HERE = os.path.join(os.getcwd(), "abaqus-audit")
OUT_DIR = os.path.join(HERE, "3d-v15.10")
INPUT_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_10_subdam_layout_foundation.inp")
CAE_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_10_subdam_layout_foundation.cae")
CHECK_FILE = os.path.join(OUT_DIR, "v15_10_cae_organization_check.csv")
CATALOG_FILE = os.path.join(
    HERE, "3d-v15.8", "v15_8_geology_instance_set_catalog.csv")
MODEL_NAME = "V15_10_SUBDAM_LAYOUT_FOUNDATION"
GEO_PART = "V15_7_FOUNDATION_GEOLOGY"
GEO_INSTANCE = "V15_7_FOUNDATION_GEOLOGY_I"

if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]

model = mdb.ModelFromInputFile(name=MODEL_NAME, inputFileName=INPUT_FILE)
assembly = model.rootAssembly
geo_part = model.parts[GEO_PART]
all_names = tuple(assembly.instances.keys())

try:
    viewport = session.viewports["Viewport: 1"]
except KeyError:
    viewport = session.Viewport(name="Viewport: 1")
viewport.setValues(displayedObject=assembly)


def select_tokens(tokens, include_geology=False):
    selected = []
    for name in all_names:
        upper = name.upper()
        if name == GEO_INSTANCE:
            if include_geology:
                selected.append(name)
        elif any(token in upper for token in tokens):
            selected.append(name)
    return tuple(selected)


def show(names):
    viewport.assemblyDisplay.setValues(
        visibleDisplayGroups=(session.displayGroups["All"],),
        visibleInstances=tuple(names), renderStyle=WIREFRAME)


def screenshot(name, names, camera_position, camera_target,
               camera_up=(0.0, 0.0, 1.0)):
    show(names)
    viewport.view.setValues(cameraPosition=camera_position,
                            cameraTarget=camera_target,
                            cameraUpVector=camera_up)
    viewport.view.fitView()
    target = os.path.join(OUT_DIR, name)
    session.printToFile(fileName=target, format=PNG, canvasObjects=(viewport,))


engineering = tuple(name for name in all_names if name != GEO_INSTANCE)
hub_left = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY",
                          "POWERHOUSE_UNIT", "FISHWAY"))
joint = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY", "FISHWAY"))
fish = select_tokens(("LEFT_BANK_SUBDAM", "FISHWAY"))
old_footprint = select_tokens(("INSTALLATION_BAY", "POWERHOUSE_UNIT", "FISHWAY"),
                              include_geology=True)
geo_local = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY", "FISHWAY"),
                          include_geology=True)
cutoff_local = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY",
                              "CUTOFF_WALL"), include_geology=True)

# Screenshots are captured before SectionAssignment, while CAE still shows the
# imported mesh and element edges directly from the keyword deck.
screenshot("v15_10_full_hub_plan", all_names,
           (0.0, 0.0, 7000.0), (0.0, -100.0, 3050.0), (0.0, 1.0, 0.0))
screenshot("v15_10_left_subdam_installation_powerhouse", hub_left,
           (-650.0, -700.0, 3400.0), (-65.0, -170.0, 3065.0))
screenshot("v15_10_dam_axis_sequence", engineering,
           (1300.0, -1800.0, 3400.0), (20.0, -40.0, 3055.0))
screenshot("v15_10_subdam_installation_joint", joint,
           (-650.0, -1050.0, 3350.0), (-80.0, -205.0, 3065.0))
screenshot("v15_10_corrected_subdam_mesh", fish,
           (-750.0, -2100.0, 3350.0), (-95.0, -240.0, 3065.0))
screenshot("v15_10_fishway_through_corrected_subdam", fish,
           (-700.0, -2350.0, 3200.0), (-96.0, -244.5, 3061.0))
screenshot("v15_10_subdam_geology_interface", geo_local,
           (-750.0, -2150.0, 3450.0), (-95.0, -230.0, 3055.0))
screenshot("v15_10_old_v159_subdam_footprint", old_footprint,
           (-650.0, -650.0, 3300.0), (-85.0, -105.0, 3060.0))
screenshot("v15_10_local_geology_mesh", geo_local,
           (-1000.0, -1500.0, 3400.0), (-70.0, -205.0, 3045.0))
screenshot("v15_10_cutoff_wall_relationship", cutoff_local,
           (-850.0, -1900.0, 3400.0), (-80.0, -205.0, 3060.0))

# Recreate explicit geology Section identities and Part-level assignments
# after the viewport captures.  No material definition is edited.
leaf_rows = []
with open(CATALOG_FILE, "r") as handle:
    for row in csv.DictReader(handle):
        if row["set_scope"] == "PART_LEAF":
            leaf_rows.append(row)

section_status = []
for row in leaf_rows:
    set_name = row["set_name"]
    section_name = row["section"]
    material_name = row["material"]
    if set_name not in geo_part.sets:
        section_status.append((set_name, "MISSING_PART_SET"))
        continue
    if section_name not in model.sections:
        model.HomogeneousSolidSection(name=section_name,
                                      material=material_name, thickness=None)
    region = regionToolset.Region(elements=geo_part.sets[set_name].elements)
    geo_part.SectionAssignment(region=region, sectionName=section_name)
    section_status.append((set_name, "PASS"))

part_set_count = 0
for name in geo_part.sets.keys():
    if name.startswith("GEO_"):
        part_set_count += 1
assembly_set_count = 0
for name in assembly.sets.keys():
    if name.startswith("ASSEM_GEO_"):
        assembly_set_count += 1
sections_ok = True
for _name, status in section_status:
    if status != "PASS":
        sections_ok = False
check_rows = [
    {"metric": "model_name", "value": MODEL_NAME, "status": "PASS"},
    {"metric": "active_part_count", "value": len(model.parts),
     "status": "PASS" if len(model.parts) == len(all_names) else "FAIL"},
    {"metric": "active_instance_count", "value": len(all_names),
     "status": "PASS"},
    {"metric": "geology_part_set_count", "value": part_set_count,
     "status": "PASS" if part_set_count >= 43 else "FAIL"},
    {"metric": "assembly_geology_set_count", "value": assembly_set_count,
     "status": "PASS" if assembly_set_count >= 43 else "FAIL"},
    {"metric": "named_geology_section_count", "value": len(section_status),
     "status": "PASS" if sections_ok else "FAIL"},
    {"metric": "analysis_steps", "value": "Initial only", "status": "PASS"},
]
with open(CHECK_FILE, "wb") as handle:
    writer = csv.DictWriter(handle, fieldnames=["metric", "value", "status"])
    writer.writeheader()
    writer.writerows(check_rows)

show(all_names)
viewport.assemblyDisplay.setValues(renderStyle=SHADED)
mdb.saveAs(pathName=CAE_FILE)
print("V15_10_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
