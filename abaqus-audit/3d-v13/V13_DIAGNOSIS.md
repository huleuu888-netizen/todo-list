# V13 Diagnosis — rigid-body and geostatic audit

## Gate 1A evidence

The V12 MSG/DAT corpus was parsed before changing the V13 deck. It produced 192 evidence rows covering 30 affected instances.
The affected instances are:

CUTOFF_WALL_POWERHOUSE_I, ECO_RELEASE_01_I, ECO_RELEASE_02_I, FISHWAY_SEGMENT_01_I, FISHWAY_SEGMENT_02_I, FISHWAY_SEGMENT_03_I, FISHWAY_SEGMENT_04_I, FISHWAY_SEGMENT_05_I, FISHWAY_SEGMENT_06_I, LEFT_SUBDAM_I, POWERHOUSE_INSTALLATION_BAY_I, POWERHOUSE_UNIT_01_I, POWERHOUSE_UNIT_02_I, POWERHOUSE_UNIT_03_I, POWERHOUSE_UNIT_04_I, RIGHT_BX01_I, RIGHT_BX02_I, RIGHT_BX03_I, RIGHT_CURTAIN_GROUTING_ZONE_I, SPILLWAY_BAY_01_I, SPILLWAY_BAY_02_I, SPILLWAY_BAY_03_I, SPILLWAY_BAY_04_I, SPILLWAY_BAY_05_I, SPILLWAY_BAY_06_I, SPILLWAY_BAY_08_I, SPILLWAY_LEFT_WALL_I, SPILLWAY_RIGHT_WALL_I, SPILLWAY_STILLING_BASIN_I, TAILWATER_CHANNEL_I

The failures are distributed across appurtenant concrete/deformation bodies, not only the retained dam-foundation system. The V13 restoration tests below reproduce this as numerical singularity/rigid-body behavior when each group is reintroduced without a verified load path.

## Root-cause classification

- A: main dam, riverbed foundation/geology, left/right geology, cutoff and geomembrane are retained.
- B: powerhouse and spillway bodies are treated as supported-but-not-monolithic; their source mesh has no verified supporting interface in this audit, so they remain suppressed from the validated baseline.
- C: fishway, ecological release and left-subdam bodies are nonessential to the core geostatic baseline and are suppressed.
- D: RIGHT_BX01/02/03 are retained only as diagnostic candidates. Their nearest-node gaps to the right fresh granite are approximately 15.000, 8.125 and 55.408 m; no conformal tie is emitted, so they are suppressed.

No arbitrary nodal restraints were added to cure the singularities. The retained BASE_FIX is the pre-existing designated deep-rock support set.
