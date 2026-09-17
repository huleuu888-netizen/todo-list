"""Import the final V13 keyword deck into Abaqus/CAE and save a CAE copy."""
from __future__ import print_function

import os

from abaqus import mdb


HERE = os.path.abspath(os.path.join(os.getcwd(), "abaqus-audit"))
OUT_DIR = os.path.join(HERE, "3d-v13")
INPUT_FILE = os.path.join(
    OUT_DIR,
    "doub_hydropower_part25_geometric_solids_v13_rigidbody_geostatic_fixed.inp")
CAE_FILE = os.path.join(
    OUT_DIR,
    "doub_hydropower_part25_geometric_solids_v13_rigidbody_geostatic_fixed.cae")

MODEL_NAME = "V13_RIGIDBODY_GEOSTATIC_FIXED"
if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]

print("V13_CAE_IMPORT_START %s" % INPUT_FILE)
mdb.ModelFromInputFile(name=MODEL_NAME, inputFileName=INPUT_FILE)
mdb.saveAs(pathName=CAE_FILE)
print("V13_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
