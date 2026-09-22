# -*- coding: utf-8 -*-
"""Read-only Abaqus/CAE structure audit for the V15.13 corrective model.

Run from the v15.13 directory with:
  abaqus cae noGUI=..\audit_v15_13_cae_structure.py
"""

from __future__ import print_function

import os

from abaqus import openMdb


CAE_FILE = "doub_hydropower_part25_geometric_solids_v15_13_corrective_execution.cae"
REPORT = "v15_13_cae_structure_audit.txt"
PARTS_CSV = "v15_13_cae_part_inventory.csv"


def emit(handle, text=""):
    handle.write(str(text) + "\n")


def main():
    cae_path = os.path.abspath(CAE_FILE)
    mdb = openMdb(pathName=cae_path)
    with open(REPORT, "w") as report, open(PARTS_CSV, "w") as parts_csv:
        emit(report, "CAE = " + cae_path)
        emit(report, "MODELS = %s" % list(mdb.models.keys()))
        emit(report, "JOBS = %s" % list(mdb.jobs.keys()))
        parts_csv.write("model,part,nodes,elements,element_types\n")
        for model_name in mdb.models.keys():
            model = mdb.models[model_name]
            assembly = model.rootAssembly
            emit(report, "\n[MODEL] %s" % model_name)
            emit(report, "PARTS = %s" % list(model.parts.keys()))
            emit(report, "MATERIALS = %s" % list(model.materials.keys()))
            emit(report, "SECTIONS = %s" % list(model.sections.keys()))
            emit(report, "STEPS = %s" % list(model.steps.keys()))
            emit(report, "BOUNDARY_CONDITIONS = %s" % list(model.boundaryConditions.keys()))
            emit(report, "PREDEFINED_FIELDS = %s" % list(model.predefinedFields.keys()))
            emit(report, "INTERACTIONS = %s" % list(model.interactions.keys()))
            emit(report, "ASSEMBLY_INSTANCES = %s" % list(assembly.instances.keys()))
            emit(report, "ASSEMBLY_SETS = %s" % list(assembly.sets.keys()))
            emit(report, "ASSEMBLY_SURFACES = %s" % list(assembly.surfaces.keys()))
            emit(report, "ASSEMBLY_ENGINEERING_FEATURES = %s" % assembly.engineeringFeatures)
            emit(report, "\n[STEPS]")
            for step_name in model.steps.keys():
                step = model.steps[step_name]
                emit(report, "%s | class=%s | timePeriod=%s | maxNumInc=%s" % (
                    step_name, step.__class__.__name__,
                    getattr(step, "timePeriod", ""), getattr(step, "maxNumInc", "")))
            emit(report, "\n[BOUNDARY_CONDITIONS]")
            for name in model.boundaryConditions.keys():
                bc = model.boundaryConditions[name]
                emit(report, "%s | class=%s | createStep=%s | region=%s" % (
                    name, bc.__class__.__name__, getattr(bc, "createStepName", ""),
                    getattr(getattr(bc, "region", None), "name", "")))
            emit(report, "\n[PREDEFINED_FIELDS]")
            for name in model.predefinedFields.keys():
                field = model.predefinedFields[name]
                emit(report, "%s | class=%s | createStep=%s | region=%s" % (
                    name, field.__class__.__name__, getattr(field, "createStepName", ""),
                    getattr(getattr(field, "region", None), "name", "")))
            emit(report, "\n[INTERACTIONS]")
            for name in model.interactions.keys():
                interaction = model.interactions[name]
                emit(report, "%s | class=%s" % (name, interaction.__class__.__name__))
            emit(report, "\n[PART_INVENTORY]")
            for part_name in model.parts.keys():
                part = model.parts[part_name]
                counts = {}
                for element in part.elements:
                    counts[element.type] = counts.get(element.type, 0) + 1
                emit(report, "%s | nodes=%d | elements=%d | types=%s" % (
                    part_name, len(part.nodes), len(part.elements), counts))
                parts_csv.write("%s,%s,%d,%d,%s\n" % (
                    model_name, part_name, len(part.nodes), len(part.elements),
                    ";".join("%s:%d" % (key, counts[key]) for key in sorted(counts))))
    try:
        mdb.close()
    except Exception:
        pass
    print("CAE_STRUCTURE_AUDIT_COMPLETE %s" % os.path.abspath(REPORT))


if __name__ == "__main__":
    main()
