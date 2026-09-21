"""Import V15.7 final geology mesh and export actual Abaqus/CAE views."""
from __future__ import print_function

import os

from abaqus import mdb, session
from abaqusConstants import PNG, SHADED, WIREFRAME

HERE = os.path.join(os.getcwd(), "abaqus-audit")
OUT_DIR = os.path.join(HERE, "3d-v15.7")
INPUT_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_7_final_geology_mesh.inp")
CAE_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_7_final_geology_mesh.cae")
MODEL_NAME = "V15_7_FINAL_GEOLOGY_MESH"

if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]

print("V15_7_CAE_IMPORT_START %s" % INPUT_FILE)
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


GEO = lambda n: "V15_7_FOUNDATION_GEOLOGY" in n

views = [
    ("v15_7_mesh_view_full_hub", all_names,
     (1550.0, -1700.0, 3350.0), (100.0, -60.0, 3050.0)),
    ("v15_7_mesh_view_repaired_geology_overview", visible(GEO),
     (-1350.0, -1100.0, 3650.0), (80.0, -100.0, 3035.0)),
    ("v15_7_mesh_view_cutoff_wall_bottom_foundation",
     visible(lambda n: "CUTOFF" in n or GEO(n)),
     (-520.0, -920.0, 3150.0), (-36.0, 3030.0, 25.0)),
    ("v15_7_mesh_view_powerhouse_foundation",
     visible(lambda n: "POWERHOUSE" in n or GEO(n)),
     (240.0, -420.0, 3270.0), (-5.0, -70.0, 3055.0)),
    ("v15_7_mesh_view_spillway_foundation",
     visible(lambda n: "SPILLWAY" in n or GEO(n)),
     (-280.0, 380.0, 3250.0), (0.0, 35.0, 3060.0)),
    ("v15_7_mesh_view_ecological_release_foundation",
     visible(lambda n: "ECO_RELEASE" in n or GEO(n)),
     (-220.0, 80.0, 3250.0), (0.0, -5.0, 3060.0)),
    ("v15_7_mesh_view_subdam_foundation",
     visible(lambda n: "LEFT_BANK_SUBDAM" in n or GEO(n)),
     (-250.0, -240.0, 3260.0), (-88.0, -70.0, 3060.0)),
    ("v15_7_mesh_view_m3a_m3b_transition", visible(GEO),
     (-950.0, -900.0, 3400.0), (70.0, -180.0, 3045.0)),
    ("v15_7_mesh_view_m3b_m3c_transition", visible(GEO),
     (-800.0, -700.0, 3350.0), (55.0, -120.0, 3050.0)),
    ("v15_7_mesh_view_m3c_m3d_transition", visible(GEO),
     (-700.0, -500.0, 3350.0), (40.0, -80.0, 3045.0)),
    ("v15_7_mesh_view_m3d_m4_transition", visible(GEO),
     (-900.0, -900.0, 3450.0), (50.0, -120.0, 3048.0)),
    ("v15_7_mesh_view_far_field_remote_boundary", visible(GEO),
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
    print("V15_7_SCREENSHOT %s.png" % target)

viewport.assemblyDisplay.setValues(visibleInstances=all_names,
                                   renderStyle=SHADED)
mdb.saveAs(pathName=CAE_FILE)
print("V15_7_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
