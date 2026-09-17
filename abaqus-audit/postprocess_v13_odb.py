"""Summarize the V13 ODB without making unsupported hydraulic claims."""
from __future__ import print_function

import os

from odbAccess import openOdb


HERE = os.path.abspath(os.path.join(os.getcwd(), "abaqus-audit"))
V13 = os.path.join(HERE, "3d-v13")
JOB = "v13_final_geo2_full"
ODB_PATH = os.path.join(V13, JOB + ".odb")
OUT_PATH = os.path.join(V13, "v13_odb_summary.txt")


def main():
    odb = openOdb(path=ODB_PATH, readOnly=True)
    try:
        with open(OUT_PATH, "w") as handle:
            handle.write("job=%s\n" % JOB)
            handle.write("odb=%s\n" % ODB_PATH)
            handle.write("steps=%d\n" % len(odb.steps))
            for name, step in odb.steps.items():
                field_names = set()
                if step.frames:
                    for key in step.frames[-1].fieldOutputs.keys():
                        field_names.add(key)
                handle.write("step=%s frames=%d last_frame_fields=%s\n" %
                             (name, len(step.frames), ",".join(sorted(field_names))))
            por_present = False
            for step in odb.steps.values():
                if step.frames and "POR" in step.frames[-1].fieldOutputs:
                    por_present = True
            handle.write("POR_FIELD_PRESENT=%s\n" %
                         ("YES" if por_present else "NO"))
            handle.write("HYDRAULIC_INTERFACE_CONTINUITY=NOT_VERIFIED\n")
            handle.write("MASS_BALANCE=NOT_COMPUTED\n")
            handle.write("NOTE=Field presence is evidence of requested output only; "
                         "it is not a continuity or mass-balance pass.\n")
    finally:
        odb.close()
    print("V13_ODB_SUMMARY=%s" % OUT_PATH)


if __name__ == "__main__":
    main()
