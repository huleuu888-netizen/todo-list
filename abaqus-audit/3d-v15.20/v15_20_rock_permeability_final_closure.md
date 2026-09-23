# V15.20 Rock Permeability Final Closure

FINAL_STATUS = CALIBRATION_REQUIRED

## Classification rule

- `VERIFIED`: a hydraulic parameter has a test result or reliable source with
  units and applicability.
- `ASSUMED`: the value is an engineering equivalent or existing model mapping,
  with the assumption explicitly identified.
- `CALIBRATION_REQUIRED`: a parameter is needed for later seepage interpretation
  but no defensible source-backed value or uncertainty range is available.

## Final classification

| Material or region | Current treatment | Hydraulic parameter class | Final status |
|---|---|---|---|
| `FRESH_GRANITE` regions | Structural-only material without active `*Permeability` in V15.15 S00 | CALIBRATION_REQUIRED if represented as porous rock | CALIBRATION_REQUIRED |
| `P2_QUARTZITE` regions | Structural-only material without active `*Permeability` in V15.15 S00 | CALIBRATION_REQUIRED if represented as porous rock | CALIBRATION_REQUIRED |
| `ROCK_DEEP_UNLOADED` regions | Structural-only material without active `*Permeability` in V15.15 S00 | CALIBRATION_REQUIRED if represented as porous rock | CALIBRATION_REQUIRED |
| `ROCK_STRONG_UNLOADED` regions | Structural-only material without active `*Permeability` in V15.15 S00 | CALIBRATION_REQUIRED if represented as porous rock | CALIBRATION_REQUIRED |
| `ROCK_WEAK_UNLOADED` regions | Structural-only material without active `*Permeability` in V15.15 S00 | CALIBRATION_REQUIRED if represented as porous rock | CALIBRATION_REQUIRED |
| Active Q2FGL/Q3AL/Q4AL porous geology mappings | Existing coefficients are present in the input deck | ASSUMED until source verification; calibration required for final interpretation | ASSUMED / CALIBRATION_REQUIRED |

### VERIFIED

No rock hydraulic k in the current evidence package meets the `VERIFIED`
classification. The structural-only implementation is verified as a model
formulation, but that fact is not a verified permeability parameter.

### ASSUMED

The existing active porous geological coefficients are retained as model
assumptions. Representative ranges captured from the current deck are:

- Q2FGL: `2.5e-07` to `1.14e-05`;
- Q3AL: `5.89e-07` to `8.49e-05`;
- Q4AL/Q4DEL: `5.8e-05` to `2.33e-04`.

These are not newly assigned values and are not frozen as verified rock data.

### CALIBRATION_REQUIRED

The five structural-rock material families require a hydraulic basis if they
are to participate in production seepage interpretation. The active porous
geology assumptions also require comparison with laboratory, packer/Lugeon,
piezometric, and discharge evidence.

## Prohibited conversion and uncertainty

No undocumented Lu-to-k conversion is made. No arbitrary uncertainty interval
is assigned. The lower/central/upper range must come from accepted source data
and a documented inversion or sensitivity study.

## Closure decision

The rock permeability framework is complete, but the engineering parameter is
not finally closed. Status remains `CALIBRATION_REQUIRED`, and this item blocks
S01-S07 release.
