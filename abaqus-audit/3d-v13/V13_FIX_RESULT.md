# V13 Fix Result

## Implemented changes

- Source: V12 corrected keyword deck; V12/V11 files were not overwritten.
- V13 S01 applies gravity to `ALL_GEOLOGY` only, separating natural geology/foundation initial stress from constructed fill.
- V13 S02 uses a geostatic gravity-buildup procedure with a full initial increment.
- The main dam, riverbed foundation/geology, left/right geology, cutoff and geomembrane interfaces remain in the retained deck.
- All 31 appurtenant instances are suppressed in the retained baseline because a valid supporting surface/shared-node path could not be demonstrated from the source mesh.

## Core evidence

Core S01 (`v13_core_geo_s01`) datacheck and analysis completed with no numerical singularity or zero-pivot diagnostic; the status file records the exact evidence.
Core S02 is included in the final full-step deck and uses the V13 geostatic procedure.

## Incremental restoration evidence

- BX: first singularity = `RIGHT_BX02_I.6 DOF 2`; status = `UNREPAIRED_RESTORE_FAIL`; source = `v13_bx_s01_unrepaired.msg`.
- POWERHOUSE: first singularity = `POWERHOUSE_INSTALLATION_BAY_I.23 DOF 3`; status = `UNREPAIRED_RESTORE_FAIL`; source = `v13_powerhouse_s01_unrepaired.msg`.
- SPILLWAY: first singularity = `SPILLWAY_RIGHT_WALL_I.13 DOF 1`; status = `UNREPAIRED_RESTORE_FAIL`; source = `v13_spillway_s01_unrepaired.msg`.
- SMALL_APPURTENANCES: first singularity = `FISHWAY_SEGMENT_01_I.2 DOF 1`; status = `UNREPAIRED_RESTORE_FAIL`; source = `v13_small_s01_unrepaired.msg`.

These failures are why the appurtenant groups are not silently retained or fixed with artificial node constraints.

## Hydraulic qualification

S03 uses the requested upstream head 3076 m, downstream head 3055 m and `end=SS`. The final normal-reservoir run status is `COMPLETED`. POR continuity and boundary-integrated mass balance are reported as NOT_VERIFIED/NOT_COMPUTED because the current output request does not provide a validated flux-history integral.
The six-step retained-baseline run reached S05. S05 stopped at increment 1 after time-integration-accuracy cut-backs; the Abaqus MSG records `THE ANALYSIS HAS NOT BEEN COMPLETED`. No DOF singularity or zero-pivot warning was observed in this run.

## Acceptance interpretation

The retained core baseline is mechanically/geostatically stable in the tested S01 run. The original full appurtenant assembly is not validated: every tested restoration group exhibits rigid-body singularity without a real support path. Therefore the overall V13 status is NOT_VALIDATED and the unresolved river/right aggregate interface plus hydraulic checks remain explicit open items.
