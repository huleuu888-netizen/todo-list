# V15.20 PARAMETER CLOSURE AND S01-S07 RELEASE CODEX TASK

## Baseline

Current branch: abaqus-audit-task

Current model status:
- S00 baseline completed
- zero pivot = 0
- ODB valid readable
- STA completed successfully
- S01-S07 not started

## Objective

Close the remaining engineering release blockers before starting S01-S07 defect cases.

Do not:
- modify main branch;
- rebuild validated geometry;
- use artificial Tie, Encastre, spring or fixed-node constraints;
- change materials only to force gate PASS.

## Task 1: Right-bank curtain closure

Prepare:
`v15_20_right_bank_curtain_closure.md`

Confirm:
- spatial position;
- continuity;
- hydraulic role;
- permeability treatment;
- engineering basis.

If source data are insufficient, document an equivalent treatment and sensitivity plan.

## Task 2: Rock permeability closure

Prepare:
`v15_20_rock_permeability_closure.md`

Include:
- verified parameters;
- assumed parameters;
- calibration requirements;
- uncertainty range.

Do not use undocumented Lu-to-k conversion.

## Task 3: Q3AL_III parameter closure

Prepare:
`v15_20_Q3AL_III_parameter_closure.md`

Document:
- density basis;
- permeability basis;
- material mapping;
- equivalence assumptions.

## Task 4: S00 warning disposition

Create:
`v15_20_S00_warning_disposition.csv`

For each retained numerical warning provide:
- warning type;
- location;
- cause;
- engineering interpretation;
- influence on seepage results.

## Task 5: Release gate update

Update:
`S01_S07_READINESS_GATE.md`

Re-evaluate:
- numerical readiness;
- geometry closure;
- material closure;
- parameter source closure.

Only after all blocking items are resolved, consider S01-S07 execution.

## Return

Provide:
1. commit SHA;
2. modified files;
3. right-bank curtain status;
4. rock permeability status;
5. Q3AL_III status;
6. S01-S07 readiness result.
