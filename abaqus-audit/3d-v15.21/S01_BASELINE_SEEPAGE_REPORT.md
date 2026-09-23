# V15.21 S01 Baseline Seepage Report

FINAL_STATUS = S01_COMPLETED_WITH_NUMERICAL_WARNINGS

## Scope and model immutability

- Case: S01 normal impoundment baseline seepage.
- Frozen input: `3d-v15.15/doub_hydropower_part25_geometric_solids_v15_15_S00_SOLVER_CLOSURE.inp`.
- The input was copied byte-for-byte; geometry, mesh, materials, boundary conditions, and the inherited step definition were not edited.
- The frozen input retains the internal step name `S00_BASELINE_SEEPAGE`; the S01 job name is recorded separately and no input rename was performed.
- The repository Gate file still records `READY: NO`; this run proceeded under the explicit release authorization in the task request, without changing that historical Gate.

## 1. Solver status

- Convergence: PASS; `THE ANALYSIS HAS COMPLETED SUCCESSFULLY`.
- Increments: 1.
- Cutbacks: 0.
- Errors: 0; zero pivots: 0.
- Analysis warnings: 5 total, including 4 numerical-problem warnings; warnings are retained, not suppressed.
- ODB: `VALID_READABLE`; STA: `COMPLETED_SUCCESSFULLY`.

## 2. Seepage results

- Pore pressure range: -3282.87622 to 3286.01904 in model pressure units.
- Maximum reported seepage-velocity norm: 0.0643400031 in model velocity units.
- Total seepage discharge Q: `NOT_COMPUTED`; the frozen output request contains no flow-rate history output or named discharge surface.
- Maximum water head: `NOT_COMPUTED`; no direct head field or unambiguous unit conversion is present in the frozen output request.
- Maximum hydraulic gradient: `NOT_COMPUTED`; no hydraulic-gradient output or post-processing convention was introduced.
- See `S01/result_summary.csv` for all extracted ODB values and evidence.

## 3. Engineering checks

- Anti-seepage wall response: solver completed and POR/FLVEL fields are present; quantitative wall head-loss and discharge partition require a named wall/surface extraction that is not in the frozen output request.
- Dam-foundation seepage: POR and FLVEL are present in the completed frame; no additional geometry or constraint was introduced.
- Rock seepage: POR and FLVEL are present; rock permeability uncertainty remains governed by the V15.20 parameter records.

## 4. Anomalies and remaining limitations

- Four numerical-problem warnings remain in the solver log, matching the retained baseline warning condition. They did not prevent convergence, create a zero pivot, or produce an Abaqus error in this run.
- The V15.20 readiness file still contains unresolved right-bank curtain, rock-permeability, and Q3AL_III source items. These were not changed by this run.
- No S02-S07 case was run.
