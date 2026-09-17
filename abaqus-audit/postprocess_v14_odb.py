"""Summarize the V14 ODB and preserve explicit NOT VERIFIED hydraulic gates."""
from __future__ import print_function

import os

from odbAccess import openOdb

HERE = os.path.abspath(os.path.join(os.getcwd(), "abaqus-audit"))
OUT_DIR = os.path.join(HERE, "3d-v14")
ODB_FILE = os.path.join(OUT_DIR, "v14_full.odb")
SUMMARY = os.path.join(OUT_DIR, "v14_odb_summary.txt")

def main():
    odb = openOdb(path=ODB_FILE, readOnly=True)
    try:
        with open(SUMMARY, "w") as handle:
            handle.write("job=v14_full\n")
            handle.write("steps=%d\n" % len(odb.steps))
            for name, step in odb.steps.items():
                fields = set()
                if step.frames:
                    fields.update(step.frames[-1].fieldOutputs.keys())
                handle.write("step=%s frames=%d last_frame_fields=%s\n" %
                             (name, len(step.frames), ",".join(sorted(fields))))
            por_present = False
            for step in odb.steps.values():
                if step.frames and "POR" in step.frames[-1].fieldOutputs:
                    por_present = True
            handle.write("POR_FIELD_PRESENT=%s\n" % ("YES" if por_present else "NO"))
            handle.write("FLVEL_FIELD_PRESENT=%s\n" % (
                "YES" if any(step.frames and "FLVEL" in step.frames[-1].fieldOutputs
                              for step in odb.steps.values()) else "NO"))
            handle.write("INTERFACE_POR_CONTINUITY=UNRESOLVED\n")
            handle.write("BOUNDARY_FLUX=UNRESOLVED\n")
            handle.write("MASS_BALANCE=UNRESOLVED\n")
            handle.write("NOTE=Field presence does not prove interface continuity or Qin/Qout balance.\n")
    finally:
        odb.close()
    print("V14_ODB_SUMMARY=%s" % SUMMARY)

if __name__ == "__main__":
    main()
