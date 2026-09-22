FINAL_STATUS = DATACHECK_COMPLETED_WITH_ISSUES

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

- Engineered backfill was integrated into the existing geology Part as `FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL` with Q3AL_III and C3D8P; the standalone backfill instance was removed. Reused geology nodes=81; new interior nodes=2016; integrated elements=20; near-coincident backfill nodes coalesced=4.
- `natural_geology_plus_integrated_backfill`: nodes=643209, elements=591321, external faces=104160, exact shared faces=1721883, nonconforming faces=0, hanging nodes=0, duplicate nodes=0, duplicate elements=0, nonmanifold=0, positive-volume overlap pairs=0, status **PASS**.
- `backfill_geology_interface`: nodes=2094, elements=20, external faces=98, exact shared faces=13, nonconforming faces=0, hanging nodes=0, duplicate nodes=0, duplicate elements=0, nonmanifold=0, positive-volume overlap pairs=0, status **PASS**.
- Foundation component count computed by exact shared-face graph: **11**. Components are not force-merged; each row has a task-allowed final classification and material/Section evidence.

## Geological Sections and hydraulics

- Geological leaf Sections audited: **36** (required 36).
- Rock-related unresolved regions are retained without invented permeability or global C3D8R->C3D8P conversion; see `v15_13_rock_hydraulic_parameter_basis.csv`.
- Backfill material status: **ENGINEERING_EQUIVALENT_ASSUMPTION**, not source-verified calibration.

## Data Check error repair

- Locally repaired negative-Jacobian elements: **3042 before -> 0 after**. The repair is limited to the reversed `V15_4_FISHWAY` C3D8R connectivity; coordinates and part geometry were not changed.
- Active initial-ratio Node Sets restored: **14**, audited in `v15_13_initial_condition_audit.csv`.
- Permeability definitions were audited without inventing rock coefficients; see `v15_13_permeability_material_audit.csv`.

## Gates and Data Check

- `original_v15_13_task_read`: **PASS** — evidence recorded
- `no_copy_only_completion`: **PASS** — evidence recorded
- `coordinate_convention_and_left_right_direction`: **PASS** — evidence recorded
- `left_structure_cutoff_axis_solved`: **PASS** — evidence recorded
- `V15_12_misplaced_wall_absent`: **PASS** — evidence recorded
- `left_bank_80m_extension_direction`: **PASS** — evidence recorded
- `installation_powerhouse_geometry`: **PASS** — evidence recorded
- `ecological_release_connection`: **PASS** — evidence recorded
- `main_cutoff_geomembrane_positive_overlap`: **PASS** — evidence recorded
- `backfill_geology_shared_node_conformity`: **PASS** — evidence recorded
- `continuous_foundation_hanging_nodes`: **PASS** — evidence recorded
- `foundation_component_resolution`: **PASS** — evidence recorded
- `all_36_geology_sections_organized`: **PASS** — evidence recorded
- `no_invalid_collapsed_elements`: **PASS** — evidence recorded
- `active_continuum_sections_materials`: **PASS** — evidence recorded
- `geometry_solver_readiness_gate`: **PASS** — evidence recorded
- `spillway_transition_source_resolution`: **UNRESOLVED** — gravity retaining-wall dimensions not defensible
- `right_bank_curtain_source_resolution`: **UNRESOLVED** — no defensible axis, thickness, or equivalent hydraulic coefficient
- `rock_hydraulic_parameter_basis`: **UNRESOLVED** — some rock permeability values require calibration
- `backfill_material_basis`: **UNRESOLVED** — Q3AL_III is an engineering equivalent assumption
- `production_seepage_readiness_gate`: **UNRESOLVED** — production seepage inputs remain source-limited/calibration-required

- Geometry Solver Readiness: **PASS**.
- Production Seepage Readiness: **UNRESOLVED**.
- Abaqus Data Check: **COMPLETED_WITH_ISSUES**. It was run only after the Geometry Solver Readiness gate passed. S01-S07: **NOT RUN**. The corrected run has `.dat` and `.msg`; Abaqus did not emit `.sta` for this datacheck-only job.
- Data Check evidence is recorded in `v15_13_datacheck_issue_register.csv` and `v15_13_datacheck_status.csv`; artifact presence and all detected issue counts are reported there.
- Right-bank grout-curtain representation remains unresolved because the source gives approximate extent but no defensible numerical thickness/equivalent boundary definition.
- Spillway-to-main-dam gravity retaining-wall body remains unresolved because source dimensions were insufficient; only the source-supported anti-seepage connection bend was added.

## S00 baseline seepage validation

- Case: **S00_BASELINE_SEEPAGE**; intact anti-seepage system, no defects, no degradation, and no random field.
- Generated input: `doub_hydropower_part25_geometric_solids_v15_13_S00_BASELINE_SEEPAGE.inp`. Its node/element geometry fingerprint is recorded in `v15_13_S00_model_manifest.csv` and matches the corrective source deck.
- Boundary audit: `v15_13_S00_boundary_condition_audit.csv`. Upstream head is 3076 m and downstream head is 3055 m using transformed Assembly-coordinate node sets. Component pressure boundaries are explicitly marked engineering assumptions; no Tie, spring, Encastre, or point-pinning constraint was added.
- Data Check: **COMPLETED_WITH_ISSUES** for `v15_13_S00_BASELINE_SEEPAGE`; no input `***ERROR`, no negative/zero-volume error, and no initial-condition/permeability error. The Data Check reported 5,395 `.dat` warnings, one `.msg` warning, and 99 unconnected regions.
- Full S00 Standard run: **UNRESOLVED / ABORTED** for `v15_13_S00_BASELINE_SEEPAGE_SMP4`. Abaqus reported zero pivots in DOF 3 of `V15_7_FOUNDATION_GEOLOGY_I`, a 99-region disconnect warning, and an excessive displacement/pressure correction. The run was stopped after the real failure evidence appeared; no artificial constraint was introduced to hide it.
- S00 result summary: `v15_13_S00_seepage_result_summary.csv`. Total discharge, hydraulic gradient, and engineering validation are **NOT_COMPUTED/UNRESOLVED** because the solver did not produce a completed `.sta` result. The partial ODB is retained locally but is not treated as a valid baseline result.
- S00 issue register: `v15_13_S00_solver_issue_register.csv`. S01-S07 were **NOT RUN**.

## Deliverables

- Corrective INP: `D:\Backup\Documents\ChatGPT\多步水电站\todo-list\abaqus-audit\3d-v15.13\doub_hydropower_part25_geometric_solids_v15_13_corrective_execution.inp`
- Corrective CAE: `D:\Backup\Documents\ChatGPT\多步水电站\todo-list\abaqus-audit\3d-v15.13\doub_hydropower_part25_geometric_solids_v15_13_corrective_execution.cae`

## V15.14 Pending Items

V15.14 adds an engineering-closure audit layer without changing the V15.13 CAE/INP geometry or inventing unresolved hydraulic inputs.

1. Curtain grouting permeability calibration.
2. Right-bank curtain geometry verification.
3. Q3AL_III parameter confirmation for natural and engineered-backfill use.
4. Rock permeability inversion/calibration for the tracked Lu-category regions.

The V15.14 closure audit status remains `IN PROGRESS`; Production Seepage Readiness remains `UNRESOLVED` and S01-S07 remain not run. See `3d-v15.14/V15_14_ENGINEERING_CLOSURE_REPORT.md` and `3d-v15.14/V15_14_ENGINEERING_MODEL_CORRESPONDENCE.md`.
