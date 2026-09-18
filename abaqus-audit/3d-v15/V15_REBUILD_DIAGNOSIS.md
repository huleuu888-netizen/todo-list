# V15 rebuild diagnosis

## Legacy audit

The v12 legacy appurtenant bodies are coarse C3D8R solids. Their v12 plan ranges are useful for locating the hub but do not meet all v15 targets (notably the 100 m powerhouse width and 114 m tailwater width), so the priority bodies are classified `REBUILD_REQUIRED`.

## Support topology

Each restored instance has a candidate left-bank geology support surface in the audit. Only the installation bay met the 0.05 m contact and existing-Tie conflict checks, so only that evidence-qualified Tie was emitted. Other new Ties were deferred rather than using unsupported blanket constraints. See v15_support_path_audit.csv and v15_contact_gap_audit.csv.

The coarse geology mesh does not provide an exact conforming survey surface beneath every rebuilt footprint. 18 support records therefore remain unresolved due to measured gap/overclosure. They are not hidden with node restraints or blanket ties.

## Current blockers

- `POWERHOUSE_UNIT_01_I`: gap range -0.5646..-0.5646 m; master `LEFT_L06_Q3AL_IV1_I`.
- `POWERHOUSE_UNIT_02_I`: gap range -1.0899..-1.0899 m; master `LEFT_L06_Q3AL_IV1_I`.
- `POWERHOUSE_UNIT_03_I`: gap range 1.0736..1.0736 m; master `LEFT_L06_Q3AL_IV1_I`.
- `POWERHOUSE_UNIT_04_I`: gap range -1.0899..-1.0899 m; master `LEFT_L06_Q3AL_IV1_I`.
- `TAILWATER_CHANNEL_I`: gap range 7.9323..15.9823 m; master `LEFT_L06_Q3AL_IV1_I`.
- `ECO_RELEASE_01_I`: gap range -0.8662..7.1338 m; master `LEFT_L01_Q4DEL_I`.
- `ECO_RELEASE_02_I`: gap range -0.2403..7.7597 m; master `LEFT_L01_Q4DEL_I`.
- `SPILLWAY_BAY_01_I`: gap range -3.7202..-3.7202 m; master `LEFT_L01_Q4DEL_I`.
- `SPILLWAY_BAY_02_I`: gap range -3.8653..-3.8653 m; master `LEFT_L01_Q4DEL_I`.
- `SPILLWAY_BAY_03_I`: gap range -3.6405..-3.6405 m; master `LEFT_L01_Q4DEL_I`.
- `SPILLWAY_BAY_04_I`: gap range -3.3218..-3.3218 m; master `LEFT_L01_Q4DEL_I`.
- `SPILLWAY_BAY_05_I`: gap range -4.8260..-4.8260 m; master `LEFT_L01_Q4DEL_I`.
- `SPILLWAY_BAY_06_I`: gap range -4.4065..-4.4065 m; master `LEFT_L01_Q4DEL_I`.
- `SPILLWAY_BAY_07_I`: gap range -4.3646..-4.3646 m; master `LEFT_L01_Q4DEL_I`.
- `SPILLWAY_BAY_08_I`: gap range -5.0344..-5.0344 m; master `LEFT_L01_Q4DEL_I`.
- `SPILLWAY_LEFT_WALL_I`: gap range 0.4000..0.4000 m; master `LEFT_L01_Q4DEL_I`.
- `SPILLWAY_RIGHT_WALL_I`: gap range -2.8369..-2.8369 m; master `LEFT_L01_Q4DEL_I`.
- `SPILLWAY_STILLING_BASIN_I`: gap range 0.6108..0.6108 m; master `LEFT_L01_Q4DEL_I`.

## Solver interpretation

Final evidence: full-deck Abaqus Data Check PASS with 35 unconnected-region warnings and no fatal errors; stage-1 S01 completed, while stage-1 S02 remains UNRESOLVED after numerical singularity warnings and an external stop. Numerical singularities are reported, not repaired by arbitrary constraints. Hydraulic S03-S07 are not claimed until the complete mechanical baseline passes.
