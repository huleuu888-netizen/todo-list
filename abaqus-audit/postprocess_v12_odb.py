"""Write a compact, read-only summary of the available v12 Abaqus ODB."""
from __future__ import print_function
import os

from odbAccess import openOdb


HERE = os.path.abspath(os.path.join(os.getcwd(), "abaqus-audit", "3d-v12"))
ODB_PATH = os.path.join(HERE, "v12_3d_fullrun.odb")
SUMMARY_PATH = os.path.join(HERE, "v12_3d_odb_summary.txt")


def main():
    lines = [
        "v12 3-D ODB summary (read-only)",
        "odb=%s" % ODB_PATH,
    ]
    odb = None
    try:
        odb = openOdb(path=ODB_PATH, readOnly=True)
        lines.append("open=PASS")
        lines.append("steps=%s" % ",".join(odb.steps.keys()))
        for step_name, step in odb.steps.items():
            lines.append("step=%s frames=%d" % (step_name, len(step.frames)))
            if step.frames:
                frame = step.frames[-1]
                lines.append("step=%s last_frame_value=%s fields=%s" % (
                    step_name, frame.frameValue,
                    ",".join(sorted(frame.fieldOutputs.keys()))))
        lines.append("NORMAL_SEEPAGE=NOT_REACHED")
        lines.append("POR_CONTINUITY=NOT_VERIFIED")
        lines.append("HYDRAULIC_MASS_BALANCE=NOT_VERIFIED")
        lines.append("NOTE=ODB is a partial run artifact; the job stopped in the first geostatic increment.")
    except Exception as exc:
        lines.append("open=FAIL")
        lines.append("error=%s" % exc)
    finally:
        if odb is not None:
            odb.close()
    with open(SUMMARY_PATH, "w") as handle:
        handle.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
