# V15.13 S00 engineering validation

STATUS = UNRESOLVED

## Case

S00_BASELINE_SEEPAGE uses the intact v15.13 model. No defects, degradation, or random field were added.

## Observed response

- Abaqus final frame: `PARTIAL_UNRESOLVED`
- POR field values: 4060526
- FLVEL field values: 3545312
- Total discharge: 0 m^3/s (approximate boundary integration)
- Hydraulic gradient: NOT_COMPUTED because no independent gradient field was requested.
- Phreatic surface: NOT_IDENTIFIED because this is a fully saturated coupled-domain baseline.

## Engineering validation

The requested hydraulic validation is unresolved because at least one required output or the final solver frame was unavailable.

## Unresolved items

- Right-bank curtain remains UNRESOLVED.
- Rock permeability categories marked CALIBRATION_REQUIRED remain unchanged.
- Q3AL_III remains an ENGINEERING_EQUIVALENT_ASSUMPTION.
- The Data Check warning about 99 unconnected regions remains an explicit model limitation.
