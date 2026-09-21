
"""Import the v15.2 geometry-completion deck into Abaqus/CAE only."""
from __future__ import print_function
import os
from abaqus import mdb

HERE = os.path.abspath(os.path.join(os.getcwd(), "abaqus-audit"))
OUT_DIR = os.path.join(HERE, "3d-v15.2")
INPUT_FILE = os.path.join(OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_2_geometry_completion.inp")
CAE_FILE = os.path.join(OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_2_geometry_completion.cae")
MODEL_NAME = "V15_2_GEOMETRY_COMPLETION"

if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]

print("V15_2_CAE_IMPORT_START %s" % INPUT_FILE)
mdb.ModelFromInputFile(name=MODEL_NAME, inputFileName=INPUT_FILE)
mdb.saveAs(pathName=CAE_FILE)
print("V15_2_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
