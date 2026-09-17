"""Import the V14 design-aligned keyword deck into Abaqus/CAE."""
from __future__ import print_function

import os

from abaqus import mdb

HERE = os.path.abspath(os.path.join(os.getcwd(), "abaqus-audit"))
OUT_DIR = os.path.join(HERE, "3d-v14")
INPUT_FILE = os.path.join(OUT_DIR, "doub_hydropower_part25_geometric_solids_v14_design_aligned.inp")
CAE_FILE = os.path.join(OUT_DIR, "doub_hydropower_part25_geometric_solids_v14_design_aligned.cae")
MODEL_NAME = "V14_DESIGN_ALIGNED"

if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]

print("V14_CAE_IMPORT_START %s" % INPUT_FILE)
mdb.ModelFromInputFile(name=MODEL_NAME, inputFileName=INPUT_FILE)
mdb.saveAs(pathName=CAE_FILE)
print("V14_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
