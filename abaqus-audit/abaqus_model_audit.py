# -*- coding: utf-8 -*-
# Run inside Abaqus/CAE, for example:
# abaqus cae noGUI=abaqus_model_audit.py -- doub_part25_2d_seepage_plastic_v1.cae
#
# It writes:
#   abaqus_model_audit.txt
#   <model_name>_keywords_no_mesh.txt
#
from __future__ import print_function
import os
import sys

from abaqus import *
from abaqusConstants import *

def safe_get(obj, name):
    try:
        return getattr(obj, name)
    except:
        return None

def safe_table(obj):
    if obj is None:
        return None
    try:
        return obj.table
    except:
        return None

def emit(fp, s=""):
    try:
        fp.write(str(s) + "\n")
    except:
        fp.write(repr(s) + "\n")

def audit_material(fp, mat_name, mat):
    emit(fp, "\n[MATERIAL] " + str(mat_name))

    props = [
        ("density", "Density"),
        ("elastic", "Elastic"),
        ("plastic", "Plastic"),
        ("mohrCoulombPlasticity", "Mohr-Coulomb"),
        ("druckerPrager", "Drucker-Prager"),
        ("clayPlasticity", "Clay Plasticity"),
        ("permeability", "Permeability"),
        ("porousElastic", "Porous Elastic"),
        ("porousBulkModuli", "Porous Bulk Moduli"),
        ("sorption", "Sorption"),
        ("moistureSwelling", "Moisture Swelling"),
        ("expansion", "Expansion"),
    ]

    for attr, label in props:
        obj = safe_get(mat, attr)
        if obj is not None:
            emit(fp, "  %s:" % label)
            table = safe_table(obj)
            if table is not None:
                emit(fp, "    table = %s" % (table,))
            for extra in ("specificWeight", "inertialDragCoefficient", "type",
                          "temperatureDependency", "dependencies"):
                v = safe_get(obj, extra)
                if v is not None:
                    emit(fp, "    %s = %s" % (extra, v))

def main():
    args = sys.argv
    cae_path = None
    if "--" in args:
        tail = args[args.index("--") + 1:]
        if tail:
            cae_path = tail[0]
    if not cae_path:
        cae_path = "doub_part25_2d_seepage_plastic_v1.cae"

    cae_path = os.path.abspath(cae_path)
    out_dir = os.path.dirname(cae_path)
    report_path = os.path.join(out_dir, "abaqus_model_audit.txt")

    mdb_obj = openMdb(pathName=cae_path)

    fp = open(report_path, "w")
    emit(fp, "CAE = " + cae_path)
    emit(fp, "MODELS = %s" % list(mdb_obj.models.keys()))
    emit(fp, "JOBS = %s" % list(mdb_obj.jobs.keys()))

    for model_name in mdb_obj.models.keys():
        model = mdb_obj.models[model_name]
        emit(fp, "\n" + "=" * 78)
        emit(fp, "[MODEL] " + str(model_name))
        emit(fp, "=" * 78)

        emit(fp, "\nPARTS = %s" % list(model.parts.keys()))
        emit(fp, "MATERIALS = %s" % list(model.materials.keys()))
        emit(fp, "SECTIONS = %s" % list(model.sections.keys()))
        emit(fp, "STEPS = %s" % list(model.steps.keys()))
        emit(fp, "BCS = %s" % list(model.boundaryConditions.keys()))
        emit(fp, "LOADS = %s" % list(model.loads.keys()))
        emit(fp, "PREDEFINED FIELDS = %s" % list(model.predefinedFields.keys()))
        emit(fp, "INTERACTIONS = %s" % list(model.interactions.keys()))

        emit(fp, "\n--- MATERIAL DETAILS ---")
        for mat_name in model.materials.keys():
            audit_material(fp, mat_name, model.materials[mat_name])

        emit(fp, "\n--- STEP DETAILS ---")
        for step_name in model.steps.keys():
            st = model.steps[step_name]
            emit(fp, "[STEP] %s | class=%s" % (step_name, st.__class__.__name__))
            for attr in ("timePeriod", "initialInc", "minInc", "maxInc",
                         "maxNumInc", "nlgeom", "utol", "cetol", "end"):
                v = safe_get(st, attr)
                if v is not None:
                    emit(fp, "  %s = %s" % (attr, v))

        emit(fp, "\n--- LOAD DETAILS ---")
        for name in model.loads.keys():
            obj = model.loads[name]
            emit(fp, "[LOAD] %s | class=%s" % (name, obj.__class__.__name__))
            for attr in ("createStepName", "comp1", "comp2", "comp3",
                         "magnitude", "distributionType", "field",
                         "gravComp1", "gravComp2", "gravComp3"):
                v = safe_get(obj, attr)
                if v is not None:
                    emit(fp, "  %s = %s" % (attr, v))

        emit(fp, "\n--- BOUNDARY CONDITION DETAILS ---")
        for name in model.boundaryConditions.keys():
            obj = model.boundaryConditions[name]
            emit(fp, "[BC] %s | class=%s" % (name, obj.__class__.__name__))
            for attr in ("createStepName", "u1", "u2", "u3", "ur1", "ur2", "ur3",
                         "magnitude", "distributionType", "fieldName"):
                v = safe_get(obj, attr)
                if v is not None:
                    emit(fp, "  %s = %s" % (attr, v))

        emit(fp, "\n--- PREDEFINED FIELD DETAILS ---")
        for name in model.predefinedFields.keys():
            obj = model.predefinedFields[name]
            emit(fp, "[FIELD] %s | class=%s" % (name, obj.__class__.__name__))
            for attr in ("createStepName", "magnitude", "verticalCoord1",
                         "verticalCoord2", "stressMag1", "stressMag2", "lateralCoeff1",
                         "lateralCoeff2", "porePressure1", "porePressure2", "voidRatio1"):
                v = safe_get(obj, attr)
                if v is not None:
                    emit(fp, "  %s = %s" % (attr, v))

        emit(fp, "\n--- MESH / ELEMENT TYPE SUMMARY ---")
        for part_name in model.parts.keys():
            p = model.parts[part_name]
            emit(fp, "[PART] %s | nodes=%s elements=%s" %
                 (part_name, len(p.nodes), len(p.elements)))
            counts = {}
            for e in p.elements:
                try:
                    t = e.type
                except:
                    t = "UNKNOWN"
                counts[t] = counts.get(t, 0) + 1
            emit(fp, "  element types = %s" % counts)

        try:
            model.keywordBlock.synchVersions(storeNodesAndElements=False)
            kw_path = os.path.join(out_dir, "%s_keywords_no_mesh.txt" % str(model_name).replace(" ", "_"))
            kf = open(kw_path, "w")
            for block in model.keywordBlock.sieBlocks:
                kf.write(str(block))
                if not str(block).endswith("\n"):
                    kf.write("\n")
            kf.close()
            emit(fp, "\nKEYWORD DUMP = " + kw_path)
        except Exception as e:
            emit(fp, "\nKEYWORD DUMP FAILED: %s" % e)

    fp.close()
    print("Audit complete:", report_path)
    try:
        mdb_obj.close()
    except:
        pass

if __name__ == "__main__":
    main()
