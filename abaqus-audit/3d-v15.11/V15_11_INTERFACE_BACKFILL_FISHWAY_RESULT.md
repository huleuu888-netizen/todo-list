# V15.11 interface, backfill and fishway finalization

## Scope and preservation

- Baseline: V15.10 geometry commit `c7ded8ff485cb2dff92421bf1ee0fe180628fac5`; the V15.11 task-file sync commit is `08af5b1`. The V15.10 deck is retained and output is written only under `3d-v15.11`.
- No S01-S07, Abaqus Data Check, Tie/contact/MPC, spring, Encastre, artificial restraint or global remesh was run or added.
- Powerhouse, installation-bay source geometry, tailwater, spillway, eco-release, sediment outlets and unrelated V15.10 meshes are preserved.

## Corrected dam-axis interface

- Left sub-dam Assembly bbox: **-70.850000,-245.700000,3059.000000;-56.000000,-156.000000,3079.000000**.
- Installation-bay bbox: **-64.000000,-156.000000,3056.465000;-7.500000,-122.000000,3079.000000**.
- Y sequence remains sub-dam **-245.700..-156.000**, installation bay **-156.000..-122.000**, powerhouse from **-122.000**.
- Sub-dam/installation actual face gap **0.000000 m**, contact area **160.000000 m2**, overlap volume **0.000000 m3**.
- Installation/powerhouse actual face gap **0.000000 m**, contact area **507.037500 m2**, overlap volume **0.000000 m3**.

## Compacted sand/gravel foundation

- Generated local backfill cells: **94**, volume **4265.763575 m3**, Part/Assembly set **FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL/ASSEM_FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL**, section **SEC_FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL**, element formulation **C3D8P**.
- Material mapping reuses existing **Q3AL_III** and is explicitly recorded as **BACKFILL_MATERIAL_MAPPING_UNRESOLVED**; no new material parameters were invented.
- Sub-dam base support: **100.000000%**; unsupported **0.000000%**; nonconforming faces **0**; hanging nodes **0**.

## Fishway station refit

- Through-dam opening: **2.500 x 7.000 m**, interior bbox **-68.850000,-201.250000,3059.000000;-61.850000,-198.750000,3066.000000**.
- 0+416 -> 0+948 geometric length: **532.000000 m** (target 532.000 m).
- Total geometric route length: **1407.595050 m** (target 1407.570 m; delta **0.025050 m**).
- Station checkpoints are audited in `v15_11_fishway_station_length_audit.csv`; plan shape is explicitly a simplified station-controlled polyline.

## Cutoff-wall global-coordinate audit

- Active P25 F13-1 wall transformed to Assembly coordinates with **global=(x,445-z,y)**; the measured global bbox is recorded in `v15_11_cutoff_alignment_audit.csv`.
- A separately instantiated left-subdam cutoff line is not present in the active V15.10 assembly; continuity is therefore **UNRESOLVED**, and no unsupported connecting geometry was added.

## Local mesh and status

- left_subdam: nodes 3160, elements 2280, min/median/P95/max 1/1.912023199/2.4916667/2.5 m, max aspect 2.4916667, invalid 0, collapsed 0.
- fishway: nodes 13916, elements 4164, min/median/P95/max 0.24999999/1.000000001/2.5/2.50000003 m, max aspect 8.00000032, invalid 0, collapsed 0.
- compacted_backfill: nodes 2094, elements 838, min/median/P95/max 1.2425/1.45/2.5/2.5 m, max aspect 2.012072435, invalid 0, collapsed 0.

- Overall: **PASS WITH EXPLICIT UNRESOLVED ITEMS**.
- Explicit unresolved items: compacted-backfill material source mapping and separately instantiated left-subdam cutoff continuity.
- Abaqus Data Check: **NOT RUN** by task scope.
- S01-S07: **NOT RUN** by task scope.
