# V15.12 real Assembly / seepage-system validation

- Baseline: V15.11 commit `ae1afc069151d5437441eaf73c1c22760524a18d`; active input was read from `doub_hydropower_part25_geometric_solids_v15_11_interface_backfill_fishway.inp`.
- Worktree scope: `abaqus-audit-task`; `main` was not modified. No S01-S07 or Abaqus Data Check was run.
- Every active instance transform is sourced from the exact INP `*Instance` placement rows; identity instances have no placement data rows.
- Active instance count: **59** before repair, **60** in V15.12; V15.11 geometry was not overwritten.

## Left-subdam cutoff presence decision

- Presence audit decision: **CONFIRMED_MISSING**. The active Assembly search found only `P25_SOLID_CUTOFF_WALL_F13-1` at its transformed global region; no left-subdam-region cutoff instance/part was present.
- Conditional repair: **ADDED**. A source-supported 1.0 m thick, approximately 80 m continuation on the active cutoff x-axis was emitted only after the missing result.

## Actual Assembly and face evidence

- `v15_12_instance_transform_audit.csv` records translation, rotation-axis rows and Assembly bboxes for every active instance.
- `v15_12_real_interface_audit.csv` compares actual boundary element faces. AABB values are used only for broad-phase pruning/diagnostics.
- left_subdam_installation_bay: gap=0.000000000 m, coincident faces=20, area=14.028125000 m2, overlap indicator=0.000000000, status **PASS**.
- installation_bay_powerhouse_unit_01: gap=0.000000000 m, coincident faces=159, area=89.547500000 m2, overlap indicator=0.000000000, status **PASS**.
- installation_bay_powerhouse_unit_02: gap= m, coincident faces=0, area=0.000000000 m2, overlap indicator=0.000000000, status **NOT_APPLICABLE**.
- installation_bay_powerhouse_unit_03: gap= m, coincident faces=0, area=0.000000000 m2, overlap indicator=0.000000000, status **NOT_APPLICABLE**.
- installation_bay_powerhouse_unit_04: gap= m, coincident faces=0, area=0.000000000 m2, overlap indicator=0.000000000, status **NOT_APPLICABLE**.
- left_subdam_engineered_backfill: gap=0.000000000 m, coincident faces=464, area=473.875000000 m2, overlap indicator=0.000000000, status **PASS**.
- installation_engineered_backfill: gap=0.000000000 m, coincident faces=74, area=115.002750000 m2, overlap indicator=0.000000000, status **PASS**.
- engineered_backfill_retained_geology: gap=0.000000000 m, coincident faces=129, area=312.041875000 m2, overlap indicator=NOT_COMPUTED_ELEMENT_VOLUME, status **PASS**.
- installation_bay_powerhouse_aggregate: gap=0.000000000 m, coincident faces=159, area=89.547500000 m2, overlap indicator=0.000000000, status **PASS**.

## Foundation topology

- natural_geology: external faces=104098, exact shared faces=1721854, nonmanifold=0, duplicate nodes=0, duplicate elements=0, status **UNRESOLVED**.
- natural_geology_plus_engineered_backfill: external faces=106334, exact shared faces=1723250, nonmanifold=0, duplicate nodes=0, duplicate elements=0, status **UNRESOLVED**.
- Nonconforming faces/hanging nodes are not copied from V15.11; the whole-domain result is explicitly marked unresolved where connectivity alone cannot prove geometric conformity.

## Seepage-capable element coverage

- `v15_12_pore_pressure_domain_audit.csv` inventories every active element type, pore-pressure DOF and permeability keyword. Structural-only C3D8R regions inside intended seepage domains remain `SEEPAGE_ELEMENT_FORMULATION_UNRESOLVED`; no automatic conversion was made.
- Backfill material: temporary existing `Q3AL_III` mapping retained as **UNRESOLVED** because no source-verified compacted sand/gravel calibration was found.

## Anti-seepage system

- `v15_12_seepage_chain_audit.csv` records the global-coordinate chain and leaves unsupported or unnamed transitions **UNRESOLVED**.
- `v15_12_cutoff_connection_detail.csv` and `v15_12_geomembrane_cutoff_connection.csv` use actual face comparisons; the main cutoff/geomembrane face coincidence is reported separately from unnamed intermediate cutoff segments.

## Final status

- Overall: **UNRESOLVED**; this is a geometry/topology evidence package for the next separate Data Check task, not solver validation.
- Unresolved items: 2 pore-pressure/interface rows; whole-foundation hanging/nonconforming geometric proof; backfill material mapping; anti-seepage transitions not represented as active named wall segments.
- No Tie, contact, MPC, spring, Encastre or artificial kinematic constraint was added.
