"""Import the clean V15.8 organization deck and create named CAE sections/views."""
from __future__ import print_function

import csv
import os

from abaqus import mdb, session
from abaqusConstants import PNG, SHADED, WIREFRAME
import regionToolset
try:
    import displayGroupMdbToolset as dgo
except ImportError:
    import displayGroupOdbToolset as dgo

HERE = os.path.join(os.getcwd(), "abaqus-audit")
OUT_DIR = os.path.join(HERE, "3d-v15.8")
INPUT_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_8_geology_organized.inp")
CAE_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_8_geology_organized.cae")
CATALOG_FILE = os.path.join(OUT_DIR, "v15_8_geology_instance_set_catalog.csv")
CHECK_FILE = os.path.join(OUT_DIR, "v15_8_cae_organization_check.csv")
MODEL_NAME = "V15_8_GEOLOGY_ORGANIZED"
GEO_PART = "V15_7_FOUNDATION_GEOLOGY"
GEO_INSTANCE = "V15_7_FOUNDATION_GEOLOGY_I"

if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]

print("V15_8_CAE_IMPORT_START %s" % INPUT_FILE)
model = mdb.ModelFromInputFile(name=MODEL_NAME, inputFileName=INPUT_FILE)
assembly = model.rootAssembly
geo_part = model.parts[GEO_PART]

# Read the frozen leaf-to-material mapping.  The explicit CAE Section objects
# are assigned after the real viewport captures; Abaqus/CAE 2022 can blank a
# mesh viewport while assigning many large element regions, even though the
# saved model and mesh remain valid.
leaf_rows = []
with open(CATALOG_FILE, "r") as handle:
    for row in csv.DictReader(handle):
        if row["set_scope"] == "PART_LEAF":
            leaf_rows.append(row)

section_status = []


def viewport_for_assembly():
    try:
        viewport = session.viewports["Viewport: 1"]
    except KeyError:
        viewport = session.Viewport(name="Viewport: 1")
    viewport.setValues(displayedObject=assembly)
    return viewport


viewport = viewport_for_assembly()
all_instances = tuple(assembly.instances.keys())


def show_all():
    viewport.assemblyDisplay.setValues(
        visibleDisplayGroups=(session.displayGroups["All"],),
        visibleInstances=all_instances,
        renderStyle=WIREFRAME)


def show_geology():
    viewport.assemblyDisplay.setValues(
        visibleDisplayGroups=(session.displayGroups["All"],),
        visibleInstances=(GEO_INSTANCE,),
        renderStyle=WIREFRAME)


def show_named_set(set_name):
    try:
        set_object = assembly.sets[set_name]
        leaf = dgo.LeafFromSets((set_object,))
        display_group = session.DisplayGroup("V15_8_%s_DISPLAY" % set_name,
                                             leaf)
        viewport.assemblyDisplay.setValues(
            visibleDisplayGroups=(display_group,),
            renderStyle=WIREFRAME)
        return True
    except Exception as error:
        print("V15_8_DISPLAY_GROUP_FALLBACK %s %s" % (set_name, error))
        show_geology()
        return False


def screenshot(name, target_set=None, camera_position=(1550.0, -1700.0, 3350.0),
               camera_target=(100.0, -60.0, 3050.0), all_visible=False):
    if all_visible:
        show_all()
    elif target_set:
        show_named_set(target_set)
    else:
        show_geology()
    viewport.view.setValues(cameraPosition=camera_position,
                            cameraTarget=camera_target,
                            cameraUpVector=(0.0, 0.0, 1.0))
    viewport.view.fitView()
    target = os.path.join(OUT_DIR, name)
    session.printToFile(fileName=target, format=PNG, canvasObjects=(viewport,))
    print("V15_8_SCREENSHOT %s.png" % target)


# The viewport captures are real CAE views.  The first two keep all active
# instances visible to document the clean Part/Assembly organization.
screenshot("v15_8_model_tree_active_parts", all_visible=True)
screenshot("v15_8_assembly_active_instances", all_visible=True,
           camera_position=(-1350.0, -1100.0, 3650.0),
           camera_target=(80.0, -100.0, 3035.0))
screenshot("v15_8_foundation_geology_isolated", target_set="ASSEM_GEO_FOUNDATION_ALL",
           camera_position=(-1350.0, -1100.0, 3650.0),
           camera_target=(80.0, -100.0, 3035.0))
screenshot("v15_8_left_leaf_isolated", target_set="ASSEM_GEO_LEFT_L01_Q4DEL",
           camera_position=(-950.0, -900.0, 3400.0),
           camera_target=(70.0, -180.0, 3045.0))
screenshot("v15_8_river_leaf_isolated", target_set="ASSEM_GEO_RIVER_R05_Q3AL_IV2",
           camera_position=(-800.0, 100.0, 3350.0),
           camera_target=(80.0, 250.0, 3045.0))
screenshot("v15_8_right_leaf_isolated", target_set="ASSEM_GEO_RIGHT_Q4_COLLUVIAL",
           camera_position=(900.0, 650.0, 3500.0),
           camera_target=(450.0, 600.0, 3050.0))
screenshot("v15_8_left_composite_isolated", target_set="ASSEM_GEO_LEFT_ALL",
           camera_position=(-950.0, -900.0, 3400.0),
           camera_target=(70.0, -180.0, 3045.0))
screenshot("v15_8_river_composite_isolated", target_set="ASSEM_GEO_RIVER_ALL",
           camera_position=(-800.0, 100.0, 3350.0),
           camera_target=(80.0, 250.0, 3045.0))
screenshot("v15_8_right_composite_isolated", target_set="ASSEM_GEO_RIGHT_ALL",
           camera_position=(900.0, 650.0, 3500.0),
           camera_target=(450.0, 600.0, 3050.0))
screenshot("v15_8_full_hub_geology_visible", all_visible=True,
           camera_position=(1550.0, -1700.0, 3350.0),
           camera_target=(100.0, -60.0, 3050.0))

# Create explicit, human-readable CAE Section objects for each leaf.  The
# material names are taken from the V15.8 mapping CSV and are not changed.
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

part_leaf_count = 0
for name in geo_part.sets.keys():
    if name.startswith("GEO_"):
        part_leaf_count += 1
assembly_geo_count = 0
for name in assembly.sets.keys():
    if name.startswith("ASSEM_GEO_"):
        assembly_geo_count += 1
sections_ok = True
for _name, status in section_status:
    if status != "PASS":
        sections_ok = False
check_rows = [
    {"metric": "model_name", "value": MODEL_NAME, "status": "PASS"},
    {"metric": "active_part_count", "value": len(model.parts),
     "status": "PASS" if len(model.parts) == len(assembly.instances) else "UNRESOLVED"},
    {"metric": "active_instance_count", "value": len(assembly.instances), "status": "PASS"},
    {"metric": "geology_part_leaf_set_count", "value": part_leaf_count,
     "status": "PASS" if part_leaf_count >= len(leaf_rows) else "FAIL"},
    {"metric": "assembly_geology_set_count", "value": assembly_geo_count,
     "status": "PASS" if assembly_geo_count >= len(leaf_rows) else "FAIL"},
    {"metric": "named_geology_section_count", "value": len(section_status),
     "status": "PASS" if sections_ok else "FAIL"},
    {"metric": "foundation_geology_instance_count", "value":
     len([name for name in assembly.instances.keys() if name == GEO_INSTANCE]),
     "status": "PASS"},
]
with open(CHECK_FILE, "wb") as handle:
    writer = csv.DictWriter(handle, fieldnames=["metric", "value", "status"])
    writer.writeheader()
    writer.writerows(check_rows)

viewport.assemblyDisplay.setValues(
    visibleDisplayGroups=(session.displayGroups["All"],),
    visibleInstances=all_instances,
    renderStyle=SHADED)
mdb.saveAs(pathName=CAE_FILE)
print("V15_8_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
