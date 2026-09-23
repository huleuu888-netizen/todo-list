# Rock Permeability Calibration — V15.17

## Status

`CALIBRATION_REQUIRED` / `UNRESOLVED`

This file records the current model values and their evidence status. It does
not assign a new permeability and does not modify the V15.15 input deck.

## Current structural-rock materials

The current V15.15 S00 input defines the following structural geology
materials without an Abaqus `*Permeability` block:

| Material | Current density in input | Current hydraulic treatment | Calibration status |
|---|---:|---|---|
| `FRESH_GRANITE` | 2.68 | Non-porous structural formulation; no active k in the deck | `CALIBRATION_REQUIRED` if later represented as a porous rock domain |
| `P2_QUARTZITE` | 2.67 | Non-porous structural formulation; no active k in the deck | `CALIBRATION_REQUIRED` if later represented as a porous rock domain |
| `ROCK_DEEP_UNLOADED` | 2.62 | Non-porous structural formulation; no active k in the deck | `CALIBRATION_REQUIRED` |
| `ROCK_STRONG_UNLOADED` | 2.45 | Non-porous structural formulation; no active k in the deck | `CALIBRATION_REQUIRED` |
| `ROCK_WEAK_UNLOADED` | 2.55 | Non-porous structural formulation; no active k in the deck | `CALIBRATION_REQUIRED` |

The absence of a permeability value for these C3D8R structural materials is
not converted into zero permeability and is not filled with a guessed granite
or Lu-to-k conversion.

## Current active porous geological coefficients

The following values are read from the existing V15.15 `*Material` /
`*Permeability, specific=9.81` blocks. They are reported in the established
active-deck convention used by the V15.13 audit (`m^2`); the value is not
reinterpreted here.

| Material | Current k | Evidence status | Required next action |
|---|---:|---|---|
| `Q2FGL_I` | `2.5e-07` | `ENGINEERING_ASSUMPTION` | Verify against layer tests or calibrate |
| `Q2FGL_II` | `8.35e-07` | `ENGINEERING_ASSUMPTION` | Verify against layer tests or calibrate |
| `Q2FGL_III` | `3.26e-07` | `ENGINEERING_ASSUMPTION` | Verify against layer tests or calibrate |
| `Q2FGL_IV` | `1.7e-06` | `ENGINEERING_ASSUMPTION` | Verify against layer tests or calibrate |
| `Q2FGL_V` | `1.14e-05` | `ENGINEERING_ASSUMPTION` | Verify against layer tests or calibrate |
| `Q3AL_I` | `1.14e-05` | `ENGINEERING_ASSUMPTION` | Verify against layer tests or calibrate |
| `Q3AL_II` | `5.89e-07` | `ENGINEERING_ASSUMPTION` | Verify against layer tests or calibrate |
| `Q3AL_III` | `8.49e-05` | `ENGINEERING_EQUIVALENT_ASSUMPTION` | Separate geology evidence from engineered backfill and calibrate |
| `Q3AL_IV1` | `5.48e-06` | `ENGINEERING_ASSUMPTION` | Verify against layer tests or calibrate |
| `Q3AL_IV2` | `2.35e-06` | `ENGINEERING_ASSUMPTION` | Verify against layer tests or calibrate |
| `Q3AL_V` | `4.46e-06` | `ENGINEERING_ASSUMPTION` | Verify against layer tests or calibrate |
| `Q4AL_SGR1` | `5.8e-05` | `ENGINEERING_ASSUMPTION` | Verify against layer tests or calibrate |
| `Q4AL_SGR2` | `2.33e-04` | `ENGINEERING_ASSUMPTION` | Verify against layer tests or calibrate |
| `Q4DEL` | `2.33e-05` | `ENGINEERING_ASSUMPTION` | Verify against layer tests or calibrate |

The V15.13 permeability audit is the source classification for these values:
the coefficients already exist in the active deck, but no independent source
or field calibration was supplied. Therefore they remain assumptions for
engineering interpretation.

## Calibration basis and plan

1. Confirm geological unit mapping and whether each unit is intended to be a
   porous seepage domain or a structural-only domain.
2. Gather layer-specific laboratory permeability, packer/Lugeon evidence, and
   seepage monitoring data with units and test conditions.
3. If direct values are unavailable, perform a documented inverse calibration
   against measured heads, discharge, and piezometric gradients. Do not convert
   Lu values by an undocumented universal factor.
4. Run a bounded sensitivity study around the verified range and record the
   calibration objective, parameter bounds, observations, and residuals.
5. Only after review, update the model input in a separately authorized change;
   V15.17 itself makes no parameter change.

## Readiness consequence

The current V15.15 S00 solver completion is valid as a baseline execution
record. Rock permeability calibration remains `UNRESOLVED`, so production
S01-S07 seepage interpretation is not yet released.
