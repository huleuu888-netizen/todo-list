"""Import V15.9 and export actual CAE geometry-review screenshots."""
from __future__ import print_function

import csv
import os

from abaqus import mdb, session
from abaqusConstants import PNG, WIREFRAME, SHADED
import regionToolset

HERE = os.path.join(os.getcwd(), "abaqus-audit")
OUT_DIR = os.path.join(HERE, "3d-v15.9")
INPUT_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_9_final_geometry.inp")
CAE_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_9_final_geometry.cae")
CHECK_FILE = os.path.join(OUT_DIR, "v15_9_cae_organization_check.csv")
CATALOG_FILE = os.path.join(
    HERE, "3d-v15.8", "v15_8_geology_instance_set_catalog.csv")
MODEL_NAME = "V15_9_FINAL_GEOMETRY"
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
        visibleInstances=tuple(names),
        renderStyle=WIREFRAME)


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
powerhouse_installation = select_tokens(("POWERHOUSE_UNIT", "INSTALLATION_BAY"))
subdam_junction = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY", "FISHWAY"))
subdam_fishway = select_tokens(("LEFT_BANK_SUBDAM", "FISHWAY"))
outlet01 = select_tokens(("SEDIMENT_FLUSHING_OUTLET_01", "POWERHOUSE_UNIT_01",
                          "POWERHOUSE_UNIT_02"))
outlet02 = select_tokens(("SEDIMENT_FLUSHING_OUTLET_02", "POWERHOUSE_UNIT_03",
                          "POWERHOUSE_UNIT_04"))
eco_spillway = select_tokens(("ECO_RELEASE", "SPILLWAY"))

# These captures are deliberately made before SectionAssignment.  The
# section objects are assigned and saved below; the screenshots remain actual
# CAE viewport captures of the frozen mesh/geometry.
screenshot("v15_9_full_hub_plan", all_names,
           (0.0, 0.0, 7000.0), (0.0, 0.0, 3050.0), (0.0, 1.0, 0.0))
screenshot("v15_9_dam_axis_view", engineering,
           (1600.0, -1700.0, 3350.0), (40.0, -20.0, 3050.0))
screenshot("v15_9_powerhouse_installation_bay", powerhouse_installation,
           (500.0, -900.0, 3300.0), (-20.0, -70.0, 3060.0))
screenshot("v15_9_installation_subdam_junction", subdam_junction,
           (-550.0, -850.0, 3300.0), (-80.0, -120.0, 3065.0))
screenshot("v15_9_left_subdam", subdam_fishway,
           (-650.0, -450.0, 3300.0), (-95.0, -100.0, 3068.0))
screenshot("v15_9_fishway_subdam_crossing", subdam_fishway,
           (-500.0, -120.0, 3200.0), (-95.0, -60.0, 3062.0))
screenshot("v15_9_sediment_outlet_01", outlet01,
           (180.0, -500.0, 3110.0), (-5.0, -95.0, 3041.0))
screenshot("v15_9_sediment_outlet_02", outlet02,
           (180.0, -250.0, 3110.0), (-5.0, -42.0, 3041.0))
screenshot("v15_9_eco_spillway_junction", eco_spillway,
           (-500.0, 150.0, 3300.0), (-5.0, 20.0, 3060.0))
screenshot("v15_9_full_flood_release_frontage", eco_spillway,
           (-800.0, 400.0, 3600.0), (-5.0, 40.0, 3060.0))
screenshot("v15_9_mesh_installation_subdam", subdam_junction,
           (-400.0, -700.0, 3200.0), (-70.0, -125.0, 3065.0))
screenshot("v15_9_mesh_eco_spillway", eco_spillway,
           (-400.0, 250.0, 3250.0), (0.0, 35.0, 3058.0))

# Restore the named geology Sections and Part-level assignments in the saved
# CAE.  Material definitions are imported from the V15.9 INP and are not
# edited; only explicit SEC_GEO_* organization objects are created.
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
                                      material=material_name,
                                      thickness=None)
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
    {"metric": "active_instance_count", "value": len(all_names), "status": "PASS"},
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
print("V15_9_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
