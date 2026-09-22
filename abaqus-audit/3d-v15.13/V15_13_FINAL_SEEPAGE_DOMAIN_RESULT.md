FINAL_STATUS = STOPPED_UNRESOLVED

# V15.13 corrective seepage-domain completion

- Governing original task read before execution: **YES** (`V15_13_FINAL_SEEPAGE_DOMAIN_REBUILD_AND_DATACHECK_CODEX_TASK.md`).
- Corrective task read before execution: **YES** (`V15_13_COMPLETION_CORRECTIVE_EXECUTION_CODEX_TASK.md`).
- Baseline: V15.11 tracked interface/backfill deck; no V15.14 was created; V15.12 and earlier versions are unchanged.
- Active instance count: **59**; final corrective INP differs from the V15.11 baseline.

## Corrective geometry

- Left-structure cutoff axis: selected `X=-64..-63 m` for the left-subdam/installation reach from actual installation min-X face and existing subdam cross-section; transition to `X=-30..-29 m` at the actual powerhouse min-X anchor. No left-subdam X move was required.
- Left-bank extension: **80.0 m toward more-negative Y**, `-245.7 -> -325.7 m`, bottom 3021 m, thickness 1 m.
- Installation/powerhouse wall: 1 m wall with 3011 m central bottom and explicit 1:1 bottom transitions at Y=-156/-146 and Y=-25.4/-15.4.
- Ecological-release connection: represented continuously from Y=-15.4 to -2.9 m.
- Spillway/main-dam cutoff: represented through spillway and a measured-anchor bend `X=-20..-19 -> -36..-35` over Y=93.6..150 m. The gravity retaining-wall body remains source-limited/unresolved.
- V15.12 misplaced Y=70..150 wall: absent from the final Assembly.
- Main cutoff/geomembrane: inclined terminal upper-edge nodes with X>-36.0 were clipped to the measured P25 cutoff plane X=-36.0; changed nodes=101; final positive-volume overlap is reported from the actual face sweep.

## Foundation conformity and components

- Engineered backfill was integrated into the existing geology Part as `FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL` with Q3AL_III and C3D8P; the standalone backfill instance was removed. Reused geology nodes=81; new interior nodes=2013; integrated elements=12.
- `natural_geology_plus_integrated_backfill`: nodes=643206, elements=591313, external faces=104170, exact shared faces=1721854, nonconforming faces=8, hanging nodes=UNRESOLVED, duplicate nodes=0, duplicate elements=0, nonmanifold=0, status **UNRESOLVED**.
- `backfill_geology_interface`: nodes=2094, elements=12, external faces=72, exact shared faces=0, nonconforming faces=8, hanging nodes=UNRESOLVED, duplicate nodes=0, duplicate elements=0, nonmanifold=0, status **UNRESOLVED**.
- Foundation component count computed by exact shared-face graph: **17**.

## Geological Sections and hydraulics

- Geological leaf Sections audited: **36** (required 36).
- Rock-related unresolved regions are retained without invented permeability or global C3D8R->C3D8P conversion; see `v15_13_rock_hydraulic_parameter_basis.csv`.
- Backfill material status: **ENGINEERING_EQUIVALENT_ASSUMPTION**, not source-verified calibration.

## Gates and Data Check

- `original_v15_13_task_read`: **PASS** — evidence recorded
- `no_copy_only_completion`: **PASS** — evidence recorded
- `coordinate_convention_and_left_right_direction`: **PASS** — evidence recorded
- `left_structure_cutoff_axis_solved`: **PASS** — evidence recorded
- `V15_12_misplaced_wall_absent`: **PASS** — evidence recorded
- `left_bank_80m_extension_direction`: **PASS** — evidence recorded
- `installation_powerhouse_geometry`: **PASS** — evidence recorded
- `ecological_release_connection`: **PASS** — evidence recorded
- `spillway_cutoff_and_transition`: **UNRESOLVED** — gravity retaining wall dimensions not defensible
- `main_cutoff_geomembrane_positive_overlap`: **PASS** — evidence recorded
- `right_bank_curtain_representation`: **UNRESOLVED** — source defines approximate curtain extent but not numerical representation
- `backfill_geology_shared_node_conformity`: **UNRESOLVED** — local same-Part conformality not proven
- `continuous_foundation_hanging_nodes`: **UNRESOLVED** — hanging/nonconforming face sweep unresolved
- `same_domain_disconnects`: **UNRESOLVED** — component classification requires no same-domain mesh disconnect
- `all_36_geology_sections_audited`: **PASS** — evidence recorded
- `production_seepage_formulation_and_permeability`: **UNRESOLVED** — rock regions lack defensible calibrated permeability
- `no_invalid_collapsed_elements`: **PASS** — evidence recorded
- `active_continuum_sections_materials`: **PASS** — evidence recorded
- `geometry_solver_readiness_gate`: **UNRESOLVED** — one or more critical geometry/topology items unresolved

- Abaqus Data Check: **NOT_RUN_PRE_GATE**. It was run only if the geometry/solver-readiness gate passed. S01-S07: **NOT RUN**.
- Right-bank grout-curtain representation remains unresolved because the source gives approximate extent but no defensible numerical thickness/equivalent boundary definition.
- Spillway-to-main-dam gravity retaining-wall body remains unresolved because source dimensions were insufficient; only the source-supported anti-seepage connection bend was added.

## Deliverables

- Corrective INP: `D:\Backup\Documents\ChatGPT\多步水电站\todo-list\abaqus-audit\3d-v15.13\doub_hydropower_part25_geometric_solids_v15_13_corrective_execution.inp`
- Corrective CAE: `D:\Backup\Documents\ChatGPT\多步水电站\todo-list\abaqus-audit\3d-v15.13\doub_hydropower_part25_geometric_solids_v15_13_corrective_execution.cae`
