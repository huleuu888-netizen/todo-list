"""Import V15.6 foundation mesh and export actual Abaqus/CAE mesh views."""
from __future__ import print_function

import os

from abaqus import mdb, session
from abaqusConstants import PNG, SHADED, WIREFRAME

HERE = os.path.join(os.getcwd(), "abaqus-audit")
OUT_DIR = os.path.join(HERE, "3d-v15.6")
INPUT_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_6_foundation_mesh.inp")
CAE_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_6_foundation_mesh.cae")
MODEL_NAME = "V15_6_FOUNDATION_MESH"

if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]

print("V15_6_CAE_IMPORT_START %s" % INPUT_FILE)
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


GEO = lambda n: "V15_6_FOUNDATION_GEOLOGY" in n

views = [
    ("v15_6_mesh_view_full_hub", all_names,
     (1550.0, -1700.0, 3350.0), (100.0, -60.0, 3050.0)),
    ("v15_6_mesh_view_cutoff_bottom_foundation",
     visible(lambda n: "CUTOFF" in n or GEO(n)),
     (-520.0, -920.0, 3150.0), (-36.0, 3030.0, 25.0)),
    ("v15_6_mesh_view_cutoff_geomembrane_connection",
     visible(lambda n: "CUTOFF" in n or "GEOMEMBRANE" in n or GEO(n)),
     (-500.0, -900.0, 3500.0), (-36.0, 3300.0, 150.0)),
    ("v15_6_mesh_view_powerhouse_foundation",
     visible(lambda n: "POWERHOUSE" in n or GEO(n)),
     (240.0, -420.0, 3270.0), (-5.0, -70.0, 3055.0)),
    ("v15_6_mesh_view_spillway_foundation",
     visible(lambda n: "SPILLWAY" in n or GEO(n)),
     (-280.0, 380.0, 3250.0), (0.0, 35.0, 3060.0)),
    ("v15_6_mesh_view_ecological_release_foundation",
     visible(lambda n: "ECO_RELEASE" in n or GEO(n)),
     (-220.0, 80.0, 3250.0), (0.0, -5.0, 3060.0)),
    ("v15_6_mesh_view_subdam_foundation",
     visible(lambda n: "LEFT_BANK_SUBDAM" in n or GEO(n)),
     (-250.0, -240.0, 3260.0), (-88.0, -70.0, 3060.0)),
    ("v15_6_mesh_view_fishway_excavation",
     visible(lambda n: "FISHWAY" in n or GEO(n)),
     (-450.0, -500.0, 3350.0), (-95.0, -220.0, 3060.0)),
    ("v15_6_mesh_view_m3_graded_transition",
     visible(GEO),
     (-1200.0, -1100.0, 3500.0), (70.0, -180.0, 3045.0)),
    ("v15_6_mesh_view_m3_to_m4_conformal_boundary",
     visible(GEO),
     (-900.0, -900.0, 3400.0), (50.0, -120.0, 3048.0)),
    ("v15_6_mesh_view_far_field_geology",
     visible(GEO),
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
    print("V15_6_SCREENSHOT %s.png" % target)

viewport.assemblyDisplay.setValues(visibleInstances=all_names,
                                   renderStyle=SHADED)
mdb.saveAs(pathName=CAE_FILE)
print("V15_6_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
