# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys


target = os.path.abspath('doub_part25_2d_seepage_plastic_v2_corrected.cae')
sys.argv = ['abaqus_model_audit.py', '--', target]
execfile('abaqus_model_audit.py', {'__name__': '__main__'})
