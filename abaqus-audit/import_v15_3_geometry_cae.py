"""Import the V15.3 geometry-only deck and export actual CAE viewport PNGs."""
from __future__ import print_function

import os

from abaqus import mdb, session
from abaqusConstants import ON, PNG, SHADED

HERE = os.path.join(os.getcwd(), "abaqus-audit")
OUT_DIR = os.path.join(HERE, "3d-v15.3")
INPUT_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_3_geometry_correction.inp")
CAE_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_3_geometry_correction.cae")
MODEL_NAME = "V15_3_GEOMETRY_CORRECTION"

if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]

print("V15_3_CAE_IMPORT_START %s" % INPUT_FILE)
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
    print("V15_3_VIEW_DISPLAY_WARNING %s" % exc)

views = [
    ("v15_3_view_upstream", (0.0, -1900.0, 3350.0),
     (120.0, -20.0, 3060.0), (0.0, 0.0, 1.0)),
    ("v15_3_view_downstream", (0.0, 1900.0, 3350.0),
     (120.0, -20.0, 3060.0), (0.0, 0.0, 1.0)),
    ("v15_3_view_plan", (100.0, 20.0, 4700.0),
     (100.0, -40.0, 3040.0), (0.0, 1.0, 0.0)),
    ("v15_3_view_dam_axis", (1900.0, -20.0, 3300.0),
     (100.0, -40.0, 3050.0), (0.0, 0.0, 1.0)),
    ("v15_3_view_left_bank_oblique", (-1600.0, -1500.0, 3600.0),
     (120.0, -260.0, 3060.0), (0.0, 0.0, 1.0)),
    ("v15_3_view_fishway_full_route_plan", (410.0, -430.0, 3900.0),
     (250.0, -480.0, 3060.0), (0.0, 1.0, 0.0)),
    ("v15_3_view_fishway_longitudinal", (1200.0, -900.0, 3300.0),
     (300.0, -500.0, 3065.0), (0.0, 0.0, 1.0)),
    ("v15_3_view_spillway_eco_closeup", (-260.0, 420.0, 3250.0),
     (20.0, 25.0, 3060.0), (0.0, 0.0, 1.0)),
    ("v15_3_view_excavation_geology_cutaway", (-900.0, -900.0, 3300.0),
     (70.0, -180.0, 3045.0), (0.0, 0.0, 1.0)),
]

for name, camera_position, camera_target, camera_up in views:
    viewport.view.setValues(cameraPosition=camera_position,
                            cameraTarget=camera_target,
                            cameraUpVector=camera_up)
    viewport.view.fitView()
    target = os.path.join(OUT_DIR, name)
    session.printToFile(fileName=target, format=PNG, canvasObjects=(viewport,))
    print("V15_3_SCREENSHOT %s.png" % target)

mdb.saveAs(pathName=CAE_FILE)
print("V15_3_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
