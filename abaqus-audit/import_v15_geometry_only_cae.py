
"""Import the v15 geometry-only keyword deck into Abaqus/CAE without running analysis."""
from __future__ import print_function
import os
from abaqus import mdb

HERE = os.path.abspath(os.path.join(os.getcwd(), "abaqus-audit"))
OUT_DIR = os.path.join(HERE, "3d-v15")
INPUT_FILE = os.path.join(OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_geometry_only.inp")
CAE_FILE = os.path.join(OUT_DIR, "doub_hydropower_part25_geometric_solids_v15_geometry_only.cae")
MODEL_NAME = "V15_GEOMETRY_ONLY"

if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]

print("V15_GEOMETRY_ONLY_CAE_IMPORT_START %s" % INPUT_FILE)
mdb.ModelFromInputFile(name=MODEL_NAME, inputFileName=INPUT_FILE)
mdb.saveAs(pathName=CAE_FILE)
print("V15_GEOMETRY_ONLY_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
