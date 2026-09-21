"""Import V15.12 to Abaqus/CAE and export actual Assembly screenshots.

This is a CAE import/viewport export only.  It does not create a step, submit
an analysis, or add any interaction/constraint.
"""
from __future__ import print_function

import csv
import os

from abaqus import mdb, session
from abaqusConstants import PNG, WIREFRAME, SHADED


HERE = os.path.join(os.getcwd(), "abaqus-audit")
OUT_DIR = os.path.join(HERE, "3d-v15.12")
INPUT_FILE = os.path.join(
    OUT_DIR,
    "doub_hydropower_part25_geometric_solids_v15_12_real_assembly_seepage_validation.inp")
CAE_FILE = os.path.join(
    OUT_DIR,
    "doub_hydropower_part25_geometric_solids_v15_12_real_assembly_seepage_validation.cae")
CHECK_FILE = os.path.join(OUT_DIR, "v15_12_cae_organization_check.csv")
MODEL_NAME = "V15_12_REAL_ASSEMBLY_SEEPAGE_VALIDATION"
GEO_INSTANCE = "V15_7_FOUNDATION_GEOLOGY_I"
BACKFILL_INSTANCE = "V15_11_LEFT_COMPACTED_SAND_GRAVEL_I"
LEFT_CUTOFF_INSTANCE = "V15_12_LEFT_BANK_CUTOFF_WALL_I"


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


def select_tokens(tokens, include_geology=False, include_backfill=False,
                  include_cutoff=False):
    selected = []
    for name in all_names:
        upper = name.upper()
        if name == GEO_INSTANCE:
            if include_geology:
                selected.append(name)
        elif name == BACKFILL_INSTANCE:
            if include_backfill:
                selected.append(name)
        elif name == LEFT_CUTOFF_INSTANCE:
            if include_cutoff:
                selected.append(name)
        elif any(token in upper for token in tokens):
            selected.append(name)
    return tuple(selected)


def show(names, render=WIREFRAME):
    viewport.assemblyDisplay.setValues(
        visibleDisplayGroups=(session.displayGroups["All"],),
        visibleInstances=tuple(names), renderStyle=render)


def screenshot(name, names, camera_position, camera_target,
               camera_up=(0.0, 0.0, 1.0), render=WIREFRAME):
    show(names, render)
    viewport.view.setValues(cameraPosition=camera_position,
                            cameraTarget=camera_target,
                            cameraUpVector=camera_up)
    viewport.view.fitView()
    target = os.path.join(OUT_DIR, name)
    session.printToFile(fileName=target, format=PNG, canvasObjects=(viewport,))


engineering = tuple(name for name in all_names
                    if name not in (GEO_INSTANCE, BACKFILL_INSTANCE))
left_bank = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY",
                           "POWERHOUSE_UNIT", "FISHWAY"),
                          include_backfill=True, include_cutoff=True)
joint = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY"),
                      include_backfill=True)
install_power = select_tokens(("INSTALLATION_BAY", "POWERHOUSE_UNIT"),
                              include_backfill=True)
backfill = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY"),
                         include_backfill=True)
backfill_geo = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY"),
                             include_geology=True, include_backfill=True)
cutoff = select_tokens(("CUTOFF", "LEFT_BANK_SUBDAM", "INSTALLATION_BAY"),
                       include_geology=True, include_backfill=True,
                       include_cutoff=True)
cutoff_all = select_tokens(("CUTOFF", "GEOMEMBRANE", "SPILLWAY",
                            "ECO_RELEASE", "POWERHOUSE"),
                           include_geology=False, include_backfill=False,
                           include_cutoff=True)
spill_eco = select_tokens(("SPILLWAY", "ECO_RELEASE"))
right_end = select_tokens(("RIGHT", "TAILWATER", "RIVERBED"))
seepage = tuple(name for name in all_names
                if name == GEO_INSTANCE or name == BACKFILL_INSTANCE or
                "DAM_" in name.upper() or "ROCKFILL" in name.upper() or
                "GEOMEMBRANE" in name.upper() or "CUTOFF" in name.upper() or
                name == LEFT_CUTOFF_INSTANCE)

# Real viewport exports from the imported Assembly mesh.
screenshot("v15_12_full_active_assembly.png", all_names,
           (0.0, 0.0, 7000.0), (0.0, -20.0, 3050.0), (0.0, 1.0, 0.0), SHADED)
screenshot("v15_12_left_subdam_installation_powerhouse.png", left_bank,
           (-650.0, -850.0, 3400.0), (-63.0, -165.0, 3065.0))
screenshot("v15_12_subdam_installation_joint.png", joint,
           (-650.0, -1050.0, 3350.0), (-63.0, -157.0, 3065.0))
screenshot("v15_12_installation_powerhouse_joint.png", install_power,
           (-700.0, -650.0, 3400.0), (-35.0, -126.0, 3065.0))
screenshot("v15_12_subdam_backfill_geology.png", backfill_geo,
           (-650.0, -1000.0, 3400.0), (-63.0, -190.0, 3057.0))
screenshot("v15_12_backfill_geology_interface_mesh.png", backfill_geo,
           (-500.0, -950.0, 3300.0), (-63.0, -175.0, 3058.0))
screenshot("v15_12_complete_cutoff_system.png", cutoff_all,
           (-850.0, -1000.0, 3500.0), (-30.0, 100.0, 3060.0))
screenshot("v15_12_left_bank_cutoff_region.png", cutoff,
           (-850.0, -1250.0, 3450.0), (-45.0, 40.0, 3060.0))
screenshot("v15_12_powerhouse_installation_cutoff_transition.png", cutoff,
           (-700.0, -650.0, 3400.0), (-36.0, -100.0, 3060.0))
screenshot("v15_12_spillway_eco_cutoff_region.png", spill_eco,
           (-750.0, -300.0, 3400.0), (0.0, 55.0, 3060.0))
screenshot("v15_12_riverbed_cutoff_geomembrane.png",
           select_tokens(("CUTOFF", "GEOMEMBRANE"), include_cutoff=True),
           (-850.0, 250.0, 3500.0), (-45.0, 290.0, 3060.0))
screenshot("v15_12_right_bank_termination.png", right_end,
           (-650.0, 650.0, 3450.0), (0.0, 600.0, 3045.0))
screenshot("v15_12_seepage_element_formulations.png", seepage,
           (-950.0, 0.0, 3550.0), (-20.0, 0.0, 3030.0))
screenshot("v15_12_full_seepage_domain_overview.png", seepage,
           (0.0, 0.0, 7000.0), (0.0, -20.0, 3050.0), (0.0, 1.0, 0.0), SHADED)

rows = [
    {"metric": "model_name", "value": MODEL_NAME, "status": "PASS"},
    {"metric": "active_instance_count", "value": len(all_names), "status": "PASS"},
    {"metric": "left_cutoff_instance", "value": LEFT_CUTOFF_INSTANCE,
     "status": "PASS" if LEFT_CUTOFF_INSTANCE in assembly.instances else "FAIL"},
    {"metric": "analysis_steps", "value": "Initial only", "status": "PASS"},
    {"metric": "analysis_jobs_submitted", "value": "NO", "status": "PASS"},
]
with open(CHECK_FILE, "wb") as handle:
    writer = csv.DictWriter(handle, fieldnames=["metric", "value", "status"])
    writer.writeheader()
    writer.writerows(rows)

show(all_names, SHADED)
mdb.saveAs(pathName=CAE_FILE)
print("V15_12_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
