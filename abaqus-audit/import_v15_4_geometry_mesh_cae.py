"""Import the V15.4 geometry/mesh deck and export actual CAE viewport PNGs."""
from __future__ import print_function

import os

from abaqus import mdb, session
from abaqusConstants import PNG, SHADED, WIREFRAME

HERE = os.path.join(os.getcwd(), "abaqus-audit")
OUT_DIR = os.path.join(HERE, "3d-v15.4")
INPUT_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_4_geometry_mesh.inp")
CAE_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_4_geometry_mesh.cae")
MODEL_NAME = "V15_4_GEOMETRY_MESH"

if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]

print("V15_4_CAE_IMPORT_START %s" % INPUT_FILE)
model = mdb.ModelFromInputFile(name=MODEL_NAME, inputFileName=INPUT_FILE)

try:
    viewport = session.viewports["Viewport: 1"]
except KeyError:
    viewport = session.Viewport(name="Viewport: 1")
viewport.setValues(displayedObject=model.rootAssembly)

try:
    viewport.assemblyDisplay.setValues(
        visibleInstances=tuple(model.rootAssembly.instances.keys()),
        renderStyle=SHADED)
except Exception as exc:
    print("V15_4_VIEW_DISPLAY_WARNING %s" % exc)

views = [
    ("v15_4_view_upstream", (0.0, -1900.0, 3350.0),
     (120.0, -20.0, 3060.0), (0.0, 0.0, 1.0), SHADED),
    ("v15_4_view_downstream", (0.0, 1900.0, 3350.0),
     (120.0, -20.0, 3060.0), (0.0, 0.0, 1.0), SHADED),
    ("v15_4_view_plan", (100.0, 20.0, 4700.0),
     (100.0, -40.0, 3040.0), (0.0, 1.0, 0.0), SHADED),
    ("v15_4_view_dam_axis", (1900.0, -20.0, 3300.0),
     (100.0, -40.0, 3050.0), (0.0, 0.0, 1.0), SHADED),
    ("v15_4_view_left_bank_oblique", (-1600.0, -1500.0, 3600.0),
     (120.0, -260.0, 3060.0), (0.0, 0.0, 1.0), SHADED),
    ("v15_4_view_fishway_full_route_plan", (410.0, -430.0, 3900.0),
     (250.0, -480.0, 3060.0), (0.0, 1.0, 0.0), SHADED),
    ("v15_4_view_subdam_closeup", (-260.0, -250.0, 3250.0),
     (-88.0, -70.0, 3060.0), (0.0, 0.0, 1.0), SHADED),
    ("v15_4_view_flushing_closeup", (150.0, -240.0, 3220.0),
     (95.0, -70.0, 3058.0), (0.0, 0.0, 1.0), SHADED),
    ("v15_4_view_spillway_eco_closeup", (-260.0, 420.0, 3250.0),
     (20.0, 25.0, 3060.0), (0.0, 0.0, 1.0), SHADED),
    ("v15_4_mesh_view_powerhouse", (220.0, -420.0, 3250.0),
     (-5.0, -70.0, 3055.0), (0.0, 0.0, 1.0), WIREFRAME),
    ("v15_4_mesh_view_spillway", (-280.0, 380.0, 3220.0),
     (-5.0, 55.0, 3055.0), (0.0, 0.0, 1.0), WIREFRAME),
    ("v15_4_mesh_view_subdam", (-240.0, -220.0, 3220.0),
     (-88.0, -70.0, 3060.0), (0.0, 0.0, 1.0), WIREFRAME),
    ("v15_4_mesh_view_structure_geology", (-1100.0, -1000.0, 3400.0),
     (70.0, -180.0, 3045.0), (0.0, 0.0, 1.0), WIREFRAME),
]

for name, camera_position, camera_target, camera_up, render_style in views:
    viewport.assemblyDisplay.setValues(renderStyle=render_style)
    viewport.view.setValues(cameraPosition=camera_position,
                            cameraTarget=camera_target,
                            cameraUpVector=camera_up)
    viewport.view.fitView()
    target = os.path.join(OUT_DIR, name)
    session.printToFile(fileName=target, format=PNG, canvasObjects=(viewport,))
    print("V15_4_SCREENSHOT %s.png" % target)

viewport.assemblyDisplay.setValues(renderStyle=SHADED)
mdb.saveAs(pathName=CAE_FILE)
print("V15_4_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
