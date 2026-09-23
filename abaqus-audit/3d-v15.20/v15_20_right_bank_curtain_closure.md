# V15.20 Right-Bank Curtain Closure

FINAL_STATUS = UNRESOLVED

## Scope and evidence

This closure record uses the V15.18 curtain parameter table and the V15.19
curtain verification report. No new right-bank geometry, mesh, boundary
condition, Tie, fixed node, spring, or material parameter was introduced.

## Verification

| Item | Current status | Finding |
|---|---|---|
| Spatial position | CHECK | The V15.18 table marks the right-bank curtain for checking, but no final coordinate survey, design drawing, or transformed Assembly location is included in the current evidence. |
| Geometric continuity | UNRESOLVED | Continuity into the verified foundation and right-bank geology cannot be proven from the supplied parameter tables alone. |
| Hydraulic role | CHECK | The intended role is a low-permeability right-bank seepage-control curtain; the role is not a substitute for verified geometry or k. |
| Material definition | CHECK | A curtain material role is expected, but the source-backed final material specification is not present. |
| Permeability treatment | UNRESOLVED | No final source-backed permeability value or grouting acceptance range is available. |
| Engineering basis | UNRESOLVED | The required survey/design package and hydraulic verification evidence are missing. |

## Equivalent treatment if source data remain unavailable

The candidate equivalent treatment is **not implemented in the current input
deck**. For a future sensitivity case, the right-bank curtain may be represented
as an explicitly documented low-permeability hydraulic region or as a justified
hydraulic boundary treatment, but only after the following are supplied:

1. the final curtain alignment in global Assembly coordinates;
2. the connection and termination points at the foundation, bank, and surface;
3. the grouting/material specification and accepted permeability range;
4. the decision whether the equivalent region is part of the production
   seepage domain or a sensitivity-only representation.

No equivalent coefficient is assigned here. Using a guessed concrete or grout
k would turn an evidence gap into an unsupported model assumption.

## Sensitivity plan

After the source package is available, run a documented three-case sensitivity
study using the source-backed lower bound, central value, and upper bound for
the curtain permeability. Compare total seepage discharge, head loss across
the curtain, downstream piezometric head, and maximum hydraulic gradient.
Record the geometry version, parameter source, units, convergence status, and
acceptance criterion for each case. Do not use this plan to release S01-S07
before the base geometry and parameter basis are approved.

## Closure decision

The right-bank curtain closure remains `UNRESOLVED`. The current S00 baseline
is preserved, but the global anti-seepage system is not released for S01-S07
production cases.
