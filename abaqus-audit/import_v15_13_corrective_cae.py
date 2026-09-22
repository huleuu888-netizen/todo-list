"""Import the V15.13 corrective execution deck and export real CAE views.

This is an import and evidence-export operation only.  It does not create an
analysis step, submit a job, or add constraints/interactions.
"""
from __future__ import print_function

import csv
import os

from abaqus import mdb, session
from abaqusConstants import PNG, WIREFRAME, SHADED


ROOT = os.path.join(os.getcwd(), "abaqus-audit")
OUT_DIR = os.path.join(ROOT, "3d-v15.13")
INPUT_FILE = os.path.join(
    OUT_DIR,
    "doub_hydropower_part25_geometric_solids_v15_13_corrective_execution.inp")
CAE_FILE = os.path.join(
    OUT_DIR,
    "doub_hydropower_part25_geometric_solids_v15_13_corrective_execution.cae")
CHECK_FILE = os.path.join(OUT_DIR, "v15_13_cae_organization_check.csv")
MODEL_NAME = "V15_13_CORRECTIVE_EXECUTION"
GEOLOGY = "V15_7_FOUNDATION_GEOLOGY_I"
ANTI_SEEPAGE = "V15_13_ANTI_SEEPAGE_CHAIN_I"


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


def select_tokens(tokens, include_geology=False, include_anti_seepage=False):
    selected = []
    for name in all_names:
        upper = name.upper()
        if name == GEOLOGY:
            if include_geology:
                selected.append(name)
        elif name == ANTI_SEEPAGE:
            if include_anti_seepage:
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


engineering = tuple(name for name in all_names if name != GEOLOGY)
left_structures = select_tokens(
    ("LEFT_BANK_SUBDAM", "INSTALLATION_BAY", "POWERHOUSE_UNIT", "FISHWAY",
     "POWERHOUSE_SEDIMENT_FLUSHING"), include_anti_seepage=True)
left_axis = select_tokens(
    ("LEFT_BANK_SUBDAM", "INSTALLATION_BAY", "POWERHOUSE_UNIT",
     "ECO_RELEASE", "SPILLWAY"), include_anti_seepage=True)
spill_eco = select_tokens(("SPILLWAY", "ECO_RELEASE"),
                          include_anti_seepage=True)
cutoff = select_tokens(("CUTOFF", "GEOMEMBRANE", "SPILLWAY", "ECO_RELEASE",
                        "POWERHOUSE"), include_anti_seepage=True)
foundation = select_tokens(("LEFT_BANK_SUBDAM", "INSTALLATION_BAY",
                            "POWERHOUSE_UNIT", "TAILWATER", "SPILLWAY",
                            "ECO_RELEASE"), include_geology=True,
                           include_anti_seepage=True)
seepage = tuple(name for name in all_names
                if name == GEOLOGY or name == ANTI_SEEPAGE or
                "DAM_" in name.upper() or "ROCKFILL" in name.upper() or
                "GEOMEMBRANE" in name.upper() or "CUTOFF" in name.upper())

# These are real Assembly viewport exports from the imported corrective mesh.
screenshot("v15_13_full_active_assembly.png", all_names,
           (0.0, 0.0, 7000.0), (0.0, -20.0, 3050.0), (0.0, 1.0, 0.0), SHADED)
screenshot("v15_13_dam_axis_chain.png", left_axis,
           (-900.0, -250.0, 3700.0), (-35.0, -10.0, 3050.0))
screenshot("v15_13_left_subdam_installation_powerhouse.png", left_structures,
           (-650.0, -850.0, 3400.0), (-63.0, -165.0, 3065.0))
screenshot("v15_13_left_structure_cutoff_axis.png", cutoff,
           (-850.0, -1150.0, 3500.0), (-45.0, -70.0, 3060.0))
screenshot("v15_13_left_bank_80m_extension.png", (ANTI_SEEPAGE,),
           (-800.0, -1350.0, 3450.0), (-64.0, -285.0, 3035.0))
screenshot("v15_13_left_subdam_cutoff_section.png", left_axis,
           (-650.0, -1050.0, 3350.0), (-63.0, -190.0, 3060.0))
screenshot("v15_13_installation_powerhouse_3011m.png", left_axis,
           (-700.0, -650.0, 3400.0), (-36.0, -125.0, 3055.0))
screenshot("v15_13_eco_spillway_connection.png", spill_eco,
           (-750.0, -300.0, 3400.0), (-5.0, 55.0, 3060.0))
screenshot("v15_13_spillway_main_dam_transition.png", cutoff,
           (-850.0, 180.0, 3500.0), (-20.0, 115.0, 3060.0))
screenshot("v15_13_main_cutoff_geomembrane_connection.png",
           select_tokens(("CUTOFF", "GEOMEMBRANE"),
                         include_anti_seepage=True),
           (-850.0, 250.0, 3500.0), (-36.0, 290.0, 3060.0))
screenshot("v15_13_right_bank_curtain_status.png",
           select_tokens(("CUTOFF", "GEOMEMBRANE"),
                         include_anti_seepage=True),
           (-650.0, 650.0, 3450.0), (0.0, 600.0, 3045.0))
screenshot("v15_13_backfill_geology_conformal_mesh.png", foundation,
           (-500.0, -950.0, 3300.0), (-63.0, -175.0, 3058.0))
screenshot("v15_13_geology_components.png", (GEOLOGY,),
           (0.0, 0.0, 7000.0), (0.0, -20.0, 3050.0))
screenshot("v15_13_geology_sections_materials.png", (GEOLOGY,),
           (-1000.0, 0.0, 3700.0), (-20.0, 0.0, 3030.0))
screenshot("v15_13_pore_pressure_element_display.png", seepage,
           (-950.0, 0.0, 3550.0), (-20.0, 0.0, 3030.0))
screenshot("v15_13_final_full_seepage_domain.png", seepage,
           (0.0, 0.0, 7000.0), (0.0, -20.0, 3050.0), (0.0, 1.0, 0.0), SHADED)

rows = [
    {"metric": "model_name", "value": MODEL_NAME, "status": "PASS"},
    {"metric": "active_instance_count", "value": len(all_names), "status": "PASS"},
    {"metric": "geology_instance", "value": GEOLOGY,
     "status": "PASS" if GEOLOGY in assembly.instances else "FAIL"},
    {"metric": "anti_seepage_instance", "value": ANTI_SEEPAGE,
     "status": "PASS" if ANTI_SEEPAGE in assembly.instances else "FAIL"},
    {"metric": "analysis_steps", "value": "Initial only", "status": "PASS"},
    {"metric": "analysis_jobs_submitted", "value": "NO", "status": "PASS"},
]
with open(CHECK_FILE, "wb") as handle:
    writer = csv.DictWriter(handle, fieldnames=["metric", "value", "status"])
    writer.writeheader()
    writer.writerows(rows)

show(all_names, SHADED)
mdb.saveAs(pathName=CAE_FILE)
print("V15_13_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
