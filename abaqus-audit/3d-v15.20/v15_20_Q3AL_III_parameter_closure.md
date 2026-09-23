# V15.20 Q3AL_III Parameter Closure

FINAL_STATUS = UNRESOLVED

## Current model mapping

| Use | Model name | Current density | Current permeability | Mapping status |
|---|---|---:|---:|---|
| Compacted sand/gravel engineered backfill | `Q3AL_III` | `2.13` | `8.49e-05` | ENGINEERING_EQUIVALENT_ASSUMPTION |
| Q3AL_III alluvial geology layer | `Q3AL_III` | `2.13` | `8.49e-05` | ENGINEERING_ASSUMPTION |

The values are read from the existing V15.15 active input and prior V15.13
material audits. They are not reassigned or adjusted by V15.20.

## Density basis

The current density `2.13` is the model mapping used for both listed roles.
The repository contains no source record that independently verifies the bulk
density for both the engineered backfill and the natural alluvial layer under
their respective moisture/compaction states. The density is therefore
`CHECK`, not source-verified final data.

## Permeability basis

The current `8.49e-05` coefficient is present in the active deck and in the
V15.13 backfill/material audit. That establishes traceability to the model,
but not independent field or laboratory verification. The coefficient remains
`UNRESOLVED` for final production use.

## Equivalence assumptions

- The compacted engineered backfill is represented by the Q3AL_III model name
  as an engineering equivalent because no dedicated calibrated backfill
  material is available in the current evidence.
- The same model name also represents a natural Q3AL_III geology layer; this
  mapping must not be treated as proof that the two materials have identical
  hydraulic behavior.
- No numerical adjustment is allowed solely to obtain a passing solver result.

## Closure and sensitivity plan

Obtain separate density and permeability evidence for the backfill and natural
layer. If the project elects to retain the equivalent mapping, document the
engineering approval and run source-backed lower/central/upper sensitivity
cases, comparing discharge, head loss, and gradients. Until then, retain the
current values for audit traceability only and keep the release status
`UNRESOLVED`.
