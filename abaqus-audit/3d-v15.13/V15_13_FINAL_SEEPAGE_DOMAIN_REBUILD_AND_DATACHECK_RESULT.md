# V15.13 final seepage-domain rebuild and Data Check gate

- Baseline: `doub_hydropower_part25_geometric_solids_v15_11_interface_backfill_fishway.inp` (V15.11); the V15.12 deck was not used as the geometry baseline.
- Branch target: `abaqus-audit-task`; no main-branch edit was made by this script.
- The supplied V15.13 task file was absent from the workspace; the explicit user order and the V15.12 governing requirements were used as the execution contract.

## Phase A — Assembly coordinate chain

- Traceable active-instance transform gate: **PASS**. Transforms come from the exact `*Instance` placement rows.
- The generated global bboxes are diagnostics from transformed nodes; they are not used as final interface proof.

## Anti-seepage rebuild

- The V15.12 `Y=70..150 m` left-bank wall is explicitly excluded. The output deck contains no `V15_12_LEFT_BANK_CUTOFF_WALL` instance.
- No new left-bank cutoff wall was added because the available source evidence does not identify a unique global Assembly line; adding one would invent geometry.
- The active V15.11 wall/geomembrane and missing chain segments are reported in `v15_13_seepage_chain_audit.csv`.

## Real interface checks

- `left_subdam_installation_bay`: gap=0.000000000 m, contact area=14.028125000 m2, coincident faces=20, interpenetrating element pairs=0, status **PASS**.
- `installation_bay_powerhouse_unit_01`: gap=0.000000000 m, contact area=89.547500000 m2, coincident faces=159, interpenetrating element pairs=0, status **PASS**.
- `left_subdam_engineered_backfill`: gap=0.000000000 m, contact area=473.875000000 m2, coincident faces=464, interpenetrating element pairs=0, status **PASS**.
- `installation_engineered_backfill`: gap=0.000000000 m, contact area=115.002750000 m2, coincident faces=74, interpenetrating element pairs=0, status **PASS**.
- `engineered_backfill_retained_geology`: gap=0.000000000 m, contact area=312.041875000 m2, coincident faces=129, interpenetrating element pairs=0, status **PASS**.
- No support percentage or zero unsupported area is claimed from a partial face sample.

## Geology Section-level pore-pressure audit

- Audited geology Section rows: **36**; unresolved rows: **10**.
- Any geological Section using a structural-only element or a material without `*Permeability` remains unresolved; no automatic C3D8R conversion or material parameter invention was made.

## Foundation topology

- `natural_geology`: elements=591301, external faces=104098, exact shared faces=1721854, nonmanifold=0, duplicate nodes=0, duplicate elements=0, status **UNRESOLVED**.
- `engineered_backfill`: elements=838, external faces=2236, exact shared faces=1396, nonmanifold=0, duplicate nodes=0, duplicate elements=0, status **UNRESOLVED**.
- `natural_geology_plus_engineered_backfill`: elements=592139, external faces=SEE_COMPONENT_ROWS, exact shared faces=SEE_COMPONENT_ROWS, nonmanifold=SEE_COMPONENT_ROWS, duplicate nodes=CROSS_PART_NODE_LABELS_SEPARATE, duplicate elements=SEE_COMPONENT_ROWS, status **UNRESOLVED**.
- Geometric nonconforming-face/hanging-node/component sweep is not replaced with copied V15.12 zeros; it remains a blocking unresolved gate.

## Pre-Data-Check Gate

- `Phase_A_coordinate_chain`: **PASS** — evidence recorded
- `V15_12_Y70_to_Y150_extension_excluded`: **PASS** — evidence recorded
- `real_left_bank_interfaces`: **FAIL** — contact/support/penetration evidence is incomplete
- `foundation_geometric_conformity`: **FAIL** — geometric nonconforming-face, hanging-node, and component sweep is unresolved
- `geology_section_pore_pressure_coverage`: **FAIL** — structural-only or no-permeability geology sections remain in the seepage domain
- `backfill_material_resolution`: **FAIL** — Q3AL_III remains a temporary unresolved mapping
- `anti_seepage_chain_continuity`: **FAIL** — required left-bank/structure transition segments are not represented and proven
- `geomembrane_cutoff_connection`: **FAIL** — real connection face check did not pass
- `Pre_Data_Check_Gate`: **FAIL** — at least one critical gate is not PASS; Abaqus Data Check must not run

- Abaqus Data Check status: **NOT_RUN**.
- Data Check was correctly withheld because all critical gates were not PASS.

## Output deck

- INP: `D:\Backup\Documents\ChatGPT\多步水电站\todo-list\abaqus-audit\3d-v15.13\doub_hydropower_part25_geometric_solids_v15_13_final_seepage_rebuild.inp`
- CAE: `D:\Backup\Documents\ChatGPT\多步水电站\todo-list\abaqus-audit\3d-v15.13\doub_hydropower_part25_geometric_solids_v15_13_final_seepage_rebuild.cae` (V15.11 CAE copied without inheriting the V15.12 extension)
- No Tie, contact, MPC, spring, Encastre, artificial kinematic constraint, S01-S07 run, or solver validation was added.
