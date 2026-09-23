from odbAccess import openOdb
import sys
import os

path = [arg for arg in sys.argv[1:] if not arg.startswith('-')][-1]
out_path = os.path.join(os.getcwd(), 'v15_24_odb_inspection.txt')
out = open(out_path, 'w')
def log(*args):
    line = ' '.join(str(x) for x in args)
    print(line)
    out.write(line + '\n')
    out.flush()

odb = openOdb(path=path, readOnly=True)
log('ODB', path)
log('ROOT_INSTANCES', ','.join(sorted(odb.rootAssembly.instances.keys())))
for step_name, step in odb.steps.items():
    log('STEP', step_name, 'FRAMES', len(step.frames))
    for i, frame in enumerate(step.frames):
        log('FRAME', i, 'VALUE', frame.frameValue, 'DESCRIPTION', frame.description)
        log('FIELD_KEYS', ','.join(sorted(frame.fieldOutputs.keys())))
        for key in sorted(frame.fieldOutputs.keys()):
            field = frame.fieldOutputs[key]
            log('FIELD', key, 'POSITION', field.locations[0].position if field.locations else 'NONE', 'VALUES', len(field.values))
        if i >= 2:
            break
odb.close()
out.close()
