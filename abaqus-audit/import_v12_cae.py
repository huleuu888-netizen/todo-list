"""Import the corrected v12 input deck into Abaqus/CAE and save a CAE copy."""
from __future__ import print_function

import os

from abaqus import mdb


# Abaqus/CAE noGUI does not define __file__; the launcher runs from the repo
# root, so resolve the checked-in audit directory from the current directory.
HERE = os.path.abspath(os.path.join(os.getcwd(), "abaqus-audit"))
OUT_DIR = os.path.join(HERE, "3d-v12")
INPUT_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v12_hydro_corrected.inp")
CAE_FILE = os.path.join(
    OUT_DIR, "doub_hydropower_part25_geometric_solids_v12_hydro_corrected.cae")

MODEL_NAME = "V12_3D_HYDRO_CORRECTED"
if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]

print("V12_CAE_IMPORT_START %s" % INPUT_FILE)
mdb.ModelFromInputFile(name=MODEL_NAME, inputFileName=INPUT_FILE)
mdb.saveAs(pathName=CAE_FILE)
print("V12_CAE_IMPORT_COMPLETE %s" % CAE_FILE)
