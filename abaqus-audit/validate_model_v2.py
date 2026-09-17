# -*- coding: utf-8 -*-
from __future__ import print_function

import os

from abaqus import mdb, openMdb
from abaqusConstants import DEFAULT, OFF


CAE = 'doub_part25_2d_seepage_plastic_v2_corrected.cae'
MODEL = 'Part25_2D_Seepage_Plastic_v2'
JOB = 'doub_part25_v2_datacheck'


path = os.path.abspath(CAE)
db = openMdb(pathName=path)
if JOB in mdb.jobs.keys():
    del mdb.jobs[JOB]
job = mdb.Job(
    name=JOB, model=MODEL,
    description='Issue 2 corrected model data check',
    numCpus=1, numDomains=1, multiprocessingMode=DEFAULT,
    echoPrint=OFF, modelPrint=OFF, contactPrint=OFF, historyPrint=OFF)
job.writeInput(consistencyChecking=OFF)
print('WROTE_INPUT=%s.inp' % JOB)
try:
    db.close()
except Exception:
    pass
