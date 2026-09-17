# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import os
import sys

import abaqusConstants as ac
from abaqus import mdb, openMdb


SOURCE_NAME = 'doub_part25_2d_seepage_plastic_v1.cae'
TARGET_NAME = 'doub_part25_2d_seepage_plastic_v2_corrected.cae'
SOURCE_MODEL = 'Part25_2D_Seepage_Plastic'
TARGET_MODEL = 'Part25_2D_Seepage_Plastic_v2'
SEEPAGE_STEP = 'GRAVITY_AND_STEADY_SEEPAGE'

# Authoritative dry densities. Dam-zone values come from the wind-dry unit
# weights in project_application.txt table 5.2.3 (converted by rho=gamma/g).
# Foundation values come from the dry-density column in tables 25/28 of
# 土体物理力学性质数据.docx.
DRY_DENSITY = {
    'MAT_BAKESHALI': 21.6e3 / 9.81,
    'MAT_BAKESHALI_NUM_ELASTIC': 21.6e3 / 9.81,
    'MAT_BIQILIAO': 14.6e3 / 9.81,
    'MAT_FANGSHENQIANG': 2440.0,
    'MAT_FANLVCENG': 21.6e3 / 9.81,
    'MAT_FANLVCENG_NUM_ELASTIC': 21.6e3 / 9.81,
    'MAT_PAISHUI': 19.7e3 / 9.81,
    'MAT_Q2': 2130.0,
    'MAT_Q2_NUM_ELASTIC': 2130.0,
    'MAT_Q6': 1700.0,
    'MAT_Q7': 2130.0,
    'MAT_Q8': 1740.0,
    'MAT_Q9': 2130.0,
    'MAT_Q10': 2130.0,
    'MAT_Q11': 2130.0,
    'MAT_Q12': 1760.0,
    'MAT_WEIYANJITI': 19.2e3 / 9.81,
    'MAT_WEIYANSHALI': 21.6e3 / 9.81,
}


def density_value(material):
    return float(material.density.table[0][0])


def assignment_map(model, part):
    """Resolve the effective (last-applied) section/material per element."""
    result = {}
    for assignment in part.sectionAssignments:
        section_name = str(assignment.sectionName)
        material_name = str(model.sections[section_name].material)
        region = assignment.region
        if hasattr(region, 'elements'):
            region_name = str(getattr(region, 'name', 'UNRESOLVED'))
            elements = region.elements
        else:
            region_name = str(region[0])
            elements = part.sets[region_name].elements
        for element in elements:
            result[int(element.label)] = (region_name, section_name, material_name)
    return result


def bc_magnitude(bc, step_name):
    try:
        values = bc.getValuesInStep(stepName=step_name)
        return float(values['magnitude'])
    except Exception:
        try:
            return float(bc.magnitude)
        except Exception:
            return None


def validate_heads(model, instance):
    result = {'upstream': [], 'downstream': []}
    for name in model.boundaryConditions.keys():
        text = str(name)
        if text.startswith('BC_UPSTREAM_H158_5_NODE_'):
            group = 'upstream'
            head = 158.5
        elif text.startswith('BC_DOWNSTREAM_H135_NODE_'):
            group = 'downstream'
            head = 135.0
        else:
            continue
        label = int(text.rsplit('_', 1)[1])
        node = instance.nodes.sequenceFromLabels(labels=(label,))[0]
        z = float(node.coordinates[1])
        expected = max(0.0, 9810.0 * (head - z))
        actual = bc_magnitude(model.boundaryConditions[name], SEEPAGE_STEP)
        result[group].append({
            'bc': text,
            'node': label,
            'z': z,
            'expected': expected,
            'actual': actual,
            'absolute_error': None if actual is None else abs(actual - expected),
        })
    return result


def main():
    root = os.path.abspath(os.getcwd())
    source = os.path.join(root, SOURCE_NAME)
    target = os.path.join(root, TARGET_NAME)
    log_path = os.path.join(root, 'v2_build_log.json')

    if not os.path.isfile(source):
        raise RuntimeError('Missing source CAE: ' + source)
    if os.path.exists(target):
        raise RuntimeError('Refusing to overwrite existing target: ' + target)

    db = openMdb(pathName=source)
    model = db.models[SOURCE_MODEL]
    part = model.parts['PART25_2D']
    instance = model.rootAssembly.instances['PART25_2D-1']
    log = {
        'source': source,
        'target': target,
        'density_changes': [],
        'cohesion': 'Retained at 100 Pa numerical regularization; source design cohesion is 0 kPa.',
        'cpe3p_constant_available': bool(hasattr(ac, 'CPE3P')),
        'triangles': [],
        'step_changes': [],
        'head_validation': {},
    }

    for name in sorted(DRY_DENSITY.keys()):
        material = model.materials[name]
        old_value = density_value(material)
        new_value = float(DRY_DENSITY[name])
        material.Density(table=((new_value,),))
        log['density_changes'].append({
            'material': name,
            'old': old_value,
            'new': new_value,
        })

    assignments = assignment_map(model, part)
    for element in part.elements:
        if str(element.type) != 'CPE3':
            continue
        region, sec, material = assignments.get(
            int(element.label), ('UNRESOLVED', 'UNRESOLVED', 'UNRESOLVED'))
        log['triangles'].append({
            'label': int(element.label),
            'assignment_region': region,
            'section': sec,
            'material': material,
            'original_type': str(element.type),
            'corrected_type': str(element.type),
            'reason': ('Abaqus 2022 has no CPE3P element code; retaining CPE3 avoids '
                       'creating an invalid input deck or incompatible orphan mesh.'),
        })

    # Insert a true geostatic procedure immediately after Initial. Keep the
    # legacy static step only as a suppressed comparison record.
    model.steps.changeKey(
        fromName='GRAVITY_INITIALIZATION',
        toName='GRAVITY_INITIALIZATION_LEGACY_SUPPRESSED')
    model.GeostaticStep(
        name='GRAVITY_INITIALIZATION', previous='Initial', nlgeom=ac.OFF,
        timePeriod=1.0, timeIncrementationMethod=ac.AUTOMATIC,
        initialInc=1.0e-5, minInc=1.0e-10,
        maxInc=0.01, maxNumInc=10000, utol=0.01)
    model.steps['GRAVITY_INITIALIZATION_LEGACY_SUPPRESSED'].suppress()
    log['step_changes'].append(
        'Inserted automatic-increment GeostaticStep GRAVITY_INITIALIZATION '
        '(initialInc=1e-5, minInc=1e-10, maxInc=0.01, maxNumInc=10000) after '
        'Initial with maximum displacement change UTOL=0.01 m; suppressed '
        'legacy StaticStep; no artificial stabilization.')

    if 'GRAVITY' in model.loads.keys():
        del model.loads['GRAVITY']
    model.Gravity(
        name='GRAVITY', createStepName='GRAVITY_INITIALIZATION',
        comp2=-9.81, distributionType=ac.UNIFORM)

    if 'BC_INITIAL_DRAINED_PORE' in model.boundaryConditions.keys():
        del model.boundaryConditions['BC_INITIAL_DRAINED_PORE']
    model.PorePressureBC(
        name='BC_INITIAL_DRAINED_PORE',
        createStepName='GRAVITY_INITIALIZATION',
        region=instance.sets['ALL_NODES'], magnitude=0.0)
    model.boundaryConditions['BC_INITIAL_DRAINED_PORE'].deactivate(SEEPAGE_STEP)

    soils = model.steps[SEEPAGE_STEP]
    soils.setValues(
        timePeriod=1.0e9, utol=1000.0,
        initialInc=1.0e-4, minInc=1.0e-10,
        maxInc=1.0e7, maxNumInc=10000)
    log['step_changes'].append(
        'Set soils step END=SS, UTOL=1000 Pa/increment, timePeriod=1e9 s, '
        'initialInc=1e-4 s, minInc=1e-10 s, maxInc=1e7 s, maxNumInc=10000, '
        'steady pore-pressure rate tolerance=1e-6 Pa/s.')

    log['head_validation'] = validate_heads(model, instance)

    db.models.changeKey(fromName=SOURCE_MODEL, toName=TARGET_MODEL)

    # Abaqus/CAE 2022 exposes the SoilsStep end attribute as a numeric value
    # in setValues(), not as the documented END=SS switch. Apply the supported
    # input-keyword form after all API edits, then validate it with a data check.
    renamed = db.models[TARGET_MODEL]
    renamed.keywordBlock.synchVersions(storeNodesAndElements=False)
    replaced_soils = False
    for index, block in enumerate(renamed.keywordBlock.sieBlocks):
        text = str(block)
        if text.lstrip().lower().startswith('*soils'):
            lines = text.splitlines()
            lines[0] = '*Soils, consolidation, end=SS, utol=1000.0'
            values = [value.strip() for value in lines[1].split(',')]
            while values and values[-1] == '':
                values.pop()
            while len(values) < 4:
                values.append('')
            values.append('1.0e-6')
            lines[1] = ', '.join(values)
            renamed.keywordBlock.replace(index, '\n'.join(lines))
            replaced_soils = True
            break
    if not replaced_soils:
        raise RuntimeError('Could not locate *Soils keyword block for END=SS')

    db.saveAs(pathName=target)
    db.close()

    with open(log_path, 'w') as handle:
        json.dump(log, handle, indent=2, sort_keys=True)
    print('V2_BUILD_COMPLETE ' + target)
    print('TRIANGLES=%d CPE3P_AVAILABLE=%s' %
          (len(log['triangles']), log['cpe3p_constant_available']))


if __name__ == '__main__':
    main()
