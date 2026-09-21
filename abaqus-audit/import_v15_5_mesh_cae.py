"""Import the V15.5 MEDIUM mesh-only deck and export actual CAE mesh views."""
from __future__ import print_function

import os

from abaqus import mdb, session
from abaqusConstants import PNG, SHADED, WIREFRAME

HERE = os.path.join(os.getcwd(), "abaqus-audit")
OUT_DIR = os.path.join(HERE, "3d-v15.5")
INPUT_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_5_medium_mesh.inp")
CAE_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_5_medium_mesh.cae")
MODEL_NAME = "V15_5_MEDIUM_MESH_ONLY"

if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]

print("V15_5_CAE_IMPORT_START %s" % INPUT_FILE)
model = mdb.ModelFromInputFile(name=MODEL_NAME, inputFileName=INPUT_FILE)
assembly = model.rootAssembly

try:
    viewport = session.viewports["Viewport: 1"]
except KeyError:
    viewport = session.Viewport(name="Viewport: 1")
viewport.setValues(displayedObject=assembly)

all_names = tuple(assembly.instances.keys())

def visible(predicate):
    names = tuple(name for name in all_names if predicate(name.upper()))
    return names or all_names


views = [
    ("v15_5_mesh_view_full_hub", all_names,
     (1550.0, -1700.0, 3350.0), (100.0, -60.0, 3050.0)),
    ("v15_5_mesh_view_powerhouse_foundation",
     visible(lambda n: "V15_4_POWERHOUSE" in n or n.startswith("LEFT_") or n.startswith("RIVER_")),
     (240.0, -420.0, 3270.0), (-5.0, -70.0, 3055.0)),
    ("v15_5_mesh_view_flushing_outlet_local",
     visible(lambda n: "FLUSHING" in n or "POWERHOUSE_UNIT_01" in n or "POWERHOUSE_UNIT_03" in n),
     (120.0, -250.0, 3200.0), (25.0, -70.0, 3042.0)),
    ("v15_5_mesh_view_spillway_ecological_release",
     visible(lambda n: "SPILLWAY" in n or "ECO_RELEASE" in n),
     (-280.0, 380.0, 3250.0), (0.0, 35.0, 3060.0)),
    ("v15_5_mesh_view_stilling_basin_transition",
     visible(lambda n: "STILLING" in n or "CHUTE" in n or "TAILWATER" in n),
     (240.0, 260.0, 3200.0), (105.0, 70.0, 3047.0)),
    ("v15_5_mesh_view_cutoff_geomembrane_connection",
     visible(lambda n: "CUTOFF" in n or "GEOMEMBRANE" in n),
     (-500.0, -900.0, 3500.0), (-36.0, 3300.0, 150.0)),
    ("v15_5_mesh_view_cutoff_bottom_foundation",
     visible(lambda n: "CUTOFF" in n or n.startswith("LEFT_") or n.startswith("RIVER_")),
     (-520.0, -920.0, 3150.0), (-36.0, 3030.0, 25.0)),
    ("v15_5_mesh_view_subdam_fishway_crossing",
     visible(lambda n: "LEFT_BANK_SUBDAM" in n or "FISHWAY" in n),
     (-250.0, -240.0, 3260.0), (-88.0, -70.0, 3060.0)),
    ("v15_5_mesh_view_near_to_far_geology_transition",
     visible(lambda n: n.startswith(("LEFT_", "RIVER_", "RIGHT_")) or "CUTOFF" in n),
     (-1200.0, -1100.0, 3500.0), (70.0, -180.0, 3045.0)),
    ("v15_5_mesh_view_far_field_geology",
     visible(lambda n: n.startswith(("LEFT_", "RIVER_", "RIGHT_"))),
     (-1700.0, -1700.0, 4200.0), (120.0, -120.0, 3050.0)),
]

for name, names, camera_position, camera_target in views:
    viewport.assemblyDisplay.setValues(visibleInstances=names,
                                       renderStyle=WIREFRAME)
    viewport.view.setValues(cameraPosition=camera_position,
                            cameraTarget=camera_target,
                            cameraUpVector=(0.0, 0.0, 1.0))
    viewport.view.fitView()
    target = os.path.join(OUT_DIR, name)
    session.printToFile(fileName=target, format=PNG, canvasObjects=(viewport,))
    print("V15_5_SCREENSHOT %s.png" % target)

viewport.assemblyDisplay.setValues(visibleInstances=all_names,
                                   renderStyle=SHADED)
mdb.saveAs(pathName=CAE_FILE)
print("V15_5_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
