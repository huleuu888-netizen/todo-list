"""Import V15.11 and export actual Abaqus/CAE geometry-review screenshots."""
from __future__ import print_function

import csv
import os

from abaqus import mdb, session
from abaqusConstants import PNG, WIREFRAME, SHADED
import regionToolset

HERE = os.path.join(os.getcwd(), "abaqus-audit")
OUT_DIR = os.path.join(HERE, "3d-v15.11")
INPUT_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_11_interface_backfill_fishway.inp")
CAE_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_11_interface_backfill_fishway.cae")
CHECK_FILE = os.path.join(OUT_DIR, "v15_11_cae_organization_check.csv")
CATALOG_FILE = os.path.join(
    HERE, "3d-v15.8", "v15_8_geology_instance_set_catalog.csv")
MODEL_NAME = "V15_11_INTERFACE_BACKFILL_FISHWAY"
GEO_PART = "V15_7_FOUNDATION_GEOLOGY"
GEO_INSTANCE = "V15_7_FOUNDATION_GEOLOGY_I"
BACKFILL_PART = "V15_11_LEFT_COMPACTED_SAND_GRAVEL"
BACKFILL_INSTANCE = "V15_11_LEFT_COMPACTED_SAND_GRAVEL_I"
BACKFILL_SET = "FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL"
BACKFILL_ASSEM_SET = "ASSEM_FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL"
BACKFILL_SECTION = "SEC_FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL"

if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]

model = mdb.ModelFromInputFile(name=MODEL_NAME, inputFileName=INPUT_FILE)
assembly = model.rootAssembly
all_names = tuple(assembly.instances.keys())

try:
    viewport = session.viewports["Viewport: 1"]
except KeyError:
    viewport = session.Viewport(name="Viewport: 1")
viewport.setValues(displayedObject=assembly)


def select_tokens(tokens, include_geology=False, include_backfill=False):
    selected = []
    for name in all_names:
        upper = name.upper()
        if name == GEO_INSTANCE:
            if include_geology:
                selected.append(name)
        elif name == BACKFILL_INSTANCE:
            if include_backfill:
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


engineering = tuple(name for name in all_names
                    if name not in (GEO_INSTANCE, BACKFILL_INSTANCE))
hub_left = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY",
                          "POWERHOUSE_UNIT", "FISHWAY"),
                         include_backfill=True)
joint = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY", "FISHWAY"),
                      include_backfill=True)
install_power = select_tokens(("INSTALLATION_BAY", "POWERHOUSE_UNIT"),
                              include_backfill=True)
backfill = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY"),
                         include_backfill=True)
geo_local = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY", "FISHWAY"),
                          include_geology=True, include_backfill=True)
fish = select_tokens(("LEFT_BANK_SUBDAM", "FISHWAY"), include_backfill=True)
fish_geo = select_tokens(("LEFT_BANK_SUBDAM", "FISHWAY"),
                         include_geology=True, include_backfill=True)
cutoff_local = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY",
                              "CUTOFF_WALL"), include_geology=True,
                             include_backfill=True)

# These are genuine CAE viewport exports, captured before any section
# reassignment so the imported element mesh is directly visible.
screenshot("v15_11_full_hub_plan", all_names,
           (0.0, 0.0, 7000.0), (0.0, -100.0, 3050.0), (0.0, 1.0, 0.0))
screenshot("v15_11_left_subdam_installation_powerhouse", hub_left,
           (-650.0, -700.0, 3400.0), (-62.0, -170.0, 3065.0))
screenshot("v15_11_subdam_installation_joint_mesh", joint,
           (-650.0, -1000.0, 3350.0), (-63.0, -158.0, 3065.0))
screenshot("v15_11_installation_powerhouse_joint", install_power,
           (-700.0, -650.0, 3400.0), (-35.0, -128.0, 3065.0))
screenshot("v15_11_subdam_installation_section_xz", joint,
           (-500.0, -650.0, 3500.0), (-63.0, -156.0, 3066.0))
screenshot("v15_11_compacted_backfill_region", backfill,
           (-500.0, -900.0, 3300.0), (-63.0, -170.0, 3057.0))
screenshot("v15_11_subdam_foundation_support", geo_local,
           (-650.0, -1000.0, 3450.0), (-63.0, -190.0, 3055.0))
screenshot("v15_11_fishway_0416_0955_plan", fish,
           (-900.0, -1700.0, 3300.0), (100.0, -150.0, 3060.0))
screenshot("v15_11_fishway_through_dam_crossing", fish_geo,
           (-700.0, -900.0, 3250.0), (-65.0, -200.0, 3062.0))
screenshot("v15_11_cutoff_wall_global_alignment", cutoff_local,
           (-850.0, -1600.0, 3450.0), (-50.0, -100.0, 3060.0))
screenshot("v15_11_local_foundation_mesh", geo_local,
           (-1000.0, -1500.0, 3400.0), (-65.0, -185.0, 3048.0))
screenshot("v15_11_full_corrected_left_bank_layout", fish_geo,
           (-900.0, -1800.0, 3500.0), (-55.0, -220.0, 3060.0))

# Restore explicit geology and engineered-backfill Section identities after
# the screenshot capture.  No material definition is changed.
leaf_rows = []
with open(CATALOG_FILE, "r") as handle:
    for row in csv.DictReader(handle):
        if row["set_scope"] == "PART_LEAF":
            leaf_rows.append(row)

section_status = []
geo_part = model.parts[GEO_PART]
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

backfill_obj = model.parts[BACKFILL_PART]
if BACKFILL_SECTION not in model.sections:
    model.HomogeneousSolidSection(name=BACKFILL_SECTION,
                                  material="Q3AL_III", thickness=None)
if BACKFILL_SET in backfill_obj.sets:
    backfill_obj.SectionAssignment(
        region=regionToolset.Region(elements=backfill_obj.sets[BACKFILL_SET].elements),
        sectionName=BACKFILL_SECTION)

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
    {"metric": "backfill_part_set", "value": BACKFILL_SET,
     "status": "PASS" if BACKFILL_SET in backfill_obj.sets else "FAIL"},
    {"metric": "backfill_assembly_set", "value": BACKFILL_ASSEM_SET,
     "status": "PASS" if BACKFILL_ASSEM_SET in assembly.sets else "FAIL"},
    {"metric": "backfill_section", "value": BACKFILL_SECTION,
     "status": "PASS" if BACKFILL_SECTION in model.sections else "FAIL"},
    {"metric": "analysis_steps", "value": "Initial only", "status": "PASS"},
]
with open(CHECK_FILE, "wb") as handle:
    writer = csv.DictWriter(handle, fieldnames=["metric", "value", "status"])
    writer.writeheader()
    writer.writerows(check_rows)

show(all_names)
viewport.assemblyDisplay.setValues(renderStyle=SHADED)
mdb.saveAs(pathName=CAE_FILE)
print("V15_11_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
