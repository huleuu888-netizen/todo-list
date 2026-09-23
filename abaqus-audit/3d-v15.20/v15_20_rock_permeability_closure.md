# V15.20 Rock Permeability Closure

FINAL_STATUS = UNRESOLVED

## Rule

This closure records evidence status only. It does not add a permeability
coefficient to the structural-rock materials and does not convert Lu values to
k by an undocumented factor.

## Verified parameters

No structural-rock permeability parameter is currently verified for release.
The V15.15 S00 input treats `FRESH_GRANITE`, `P2_QUARTZITE`,
`ROCK_DEEP_UNLOADED`, `ROCK_STRONG_UNLOADED`, and `ROCK_WEAK_UNLOADED` as
structural-only materials without an active `*Permeability` definition. That
is a verified statement about the current deck, not a verified hydraulic k.

## Current assumed/model-captured parameters

The active porous geological layers carry model coefficients, but the V15.13
and V15.19 audits classify them as engineering assumptions rather than
source-verified values. Representative current values are:

| Material family | Current model k | Status |
|---|---:|---|
| `Q2FGL_I` through `Q2FGL_V` | `2.5e-07` to `1.14e-05` | ENGINEERING_ASSUMPTION |
| `Q3AL_I` through `Q3AL_V` | `5.89e-07` to `8.49e-05` | ENGINEERING_ASSUMPTION / ENGINEERING_EQUIVALENT_ASSUMPTION |
| `Q4AL_SGR1`, `Q4AL_SGR2`, `Q4DEL` | `5.8e-05` to `2.33e-04` | ENGINEERING_ASSUMPTION |

These values are recorded from the existing deck. They are not changed in
V15.20 and are not called verified rock parameters.

## Calibration requirements

1. Confirm the geological unit and whether it is a porous seepage domain or a
   structural-only region.
2. Obtain laboratory permeability, packer/Lugeon, monitoring, or equivalent
   source evidence with units and test conditions.
3. Define source-backed lower, central, and upper bounds.
4. Calibrate or invert against piezometric heads and seepage discharge using a
   documented objective and acceptance tolerance.
5. Review the calibrated values before any production-case input change.

## Uncertainty range

`UNRESOLVED`: no defensible numerical uncertainty interval is supplied in the
current repository. V15.20 therefore does not invent a range, apply a blanket
factor, or claim that the current model coefficient is a verified field value.
The sensitivity range must be derived from the accepted source evidence.

## Closure decision

Rock permeability remains `CALIBRATION_REQUIRED / UNRESOLVED`. The existing
S00 computation is preserved as a baseline, but this parameter gap blocks
release of S01-S07 production interpretation.
