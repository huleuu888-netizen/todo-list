# Codex task: v13 repair of 3D Duobu hydro-mechanical model

Work only on branch `abaqus-audit-task`. Do not modify `main`. Do not overwrite v11 or v12.

Base model:
- `abaqus-audit/3d-v12/doub_hydropower_part25_geometric_solids_v12_hydro_corrected.cae`
- `abaqus-audit/3d-v12/doub_hydropower_part25_geometric_solids_v12_hydro_corrected.inp`

## Primary diagnosis from v12

The v12 data check passes, but the full run fails in `S01` Geostatic, increment 1, with many displacement-DOF numerical singularities. The first-priority defect is therefore mechanical connectivity / rigid-body freedom, not material density, permeability, or time-increment size.

The v12 message file reports numerical singularities on instances including, but not limited to:
- `FISHWAY_SEGMENT_01_I` through multiple fishway segments
- `SPILLWAY_BAY_01_I`, `SPILLWAY_BAY_02_I`, `SPILLWAY_BAY_06_I`
- `SPILLWAY_LEFT_WALL_I`
- `POWERHOUSE_UNIT_02_I`, `POWERHOUSE_UNIT_04_I`
- `RIGHT_BX02_I`

The singularities are predominantly DOF 1/2/3, so treat them first as unconstrained mechanical rigid-body modes.

The warning `THERE ARE 35 UNCONNECTED REGIONS IN THE MODEL` is not by itself the success criterion because Abaqus notes that contact-surface SFM elements can increase this count. The correct criterion is absence of unintended free-floating physical regions and absence of structural numerical singularities / zero pivots.

## Required v13 repair sequence

### Gate 1A: extract and classify all singular instances

1. Parse the v12 `.msg` and `.dat` files and produce a complete list of all nodes and instances involved in:
   - `NUMERICAL SINGULARITY`
   - zero pivots
   - excessive rigid-body motion
   - solver singularity warnings.
2. Write this list to `v13_singularity_instances.csv` with:
   - instance name
   - node label
   - DOF
   - first occurrence line/context
   - physical component category
   - proposed action.
3. Do not modify the model before generating this evidence table.

### Gate 1B: repair mechanical connectivity / rigid-body freedom

For every singular instance, classify it into one of these categories:

A. Physically bonded to the main dam/foundation system
- Prefer shared-node/conformal connectivity where practical.
- Otherwise define a valid surface-based tie to the actual supporting/adjacent structure.
- Do not tie an instance to a distant or non-overlapping surface merely to suppress a singularity.

B. Physically supported but not monolithically bonded
- Define the source-supported contact or support condition.
- Ensure all six rigid-body modes are restrained by the real support/contact network.

C. Nonessential appurtenant structure for the baseline dam seepage/geostatic model
- Temporarily suppress it in the baseline core model rather than adding artificial displacement constraints.
- Examples may include fishway segments or other small structures if they are not required to establish the dam/foundation stress and seepage field.
- Record every suppressed instance and justification.

D. Right-bank deformation bodies BX01/BX02/BX03
- Keep only if physically part of the retained analysis domain and mechanically connected.
- If retained, establish actual support/connectivity to surrounding geology.
- Do not apply arbitrary nodal restraints simply to force convergence.

### Gate 1C: core-model isolation test

Create a diagnostic core model containing only the essential system needed for the dam seepage/geostatic baseline:
- main dam zones
- riverbed foundation/geology
- left/right bank geology needed for support
- cutoff wall
- geomembrane/equivalent barrier where required.

Temporarily suppress nonessential appurtenant structures for this diagnostic model.

Run a data check and `S01` Geostatic on this core model before restoring appurtenant structures.

Core-model success criterion:
- no DOF 1/2/3 numerical singularity or zero pivot,
- no unintended free-floating physical instance,
- `S01` completes.

### Gate 1D: reintroduce appurtenant structures incrementally

Restore suppressed structure groups one at a time, rerunning a Geostatic verification after each group:
1. BX bodies if retained
2. powerhouse structures
3. spillway structures
4. fishway / eco-release / other small appurtenances.

Record the first group that reintroduces a singularity. Repair its support/interface before proceeding.

## Main-system interface audit

The v12 interface table already contains 40 exact ties and several aggregate ties. Do not delete working ties blindly.

However, explicitly investigate these known unresolved conditions:
- `RIVER_RIGHT_GEOLOGY_NONCONFORMAL` was reported `SKIPPED_NO_NONOVERLAP_SURFACE`; determine whether this represents a real missing physical connection or a geometry gap.
- Nonconformal dam-foundation and left/river geology aggregate ties must be checked for actual geometric overlap and valid slave/master surfaces.
- Geomembrane-to-fill and geomembrane-to-cutoff ties must remain physically connected and must not introduce free rigid bodies.

Generate `v13_interfaces.csv` with:
- interface name
- side A / side B
- physical relation
- actual geometric overlap distance / gap
- connection method
- mechanical status
- hydraulic continuity status
- retained / modified / removed.

## Boundary-condition audit

Do not solve singularities by fully fixing arbitrary nodes.

Verify the external boundary condition scheme for the main foundation domain. A defensible baseline may use:
- bottom external boundary: vertical restraint (`U3=0`) plus the minimum additional constraints required to remove global horizontal rigid-body modes,
- lateral external boundaries: normal-displacement restraint only,
- front/back section boundaries: normal-displacement restraint if the model represents a constrained 3D section.

Use the actual global axes and geometry. Document every BC set and its physical meaning.

For each retained independent structural body, verify that it has a physical load path to the supported foundation/system. No retained part may remain with a free rigid-body mode.

## Geostatic strategy after mechanical stability is achieved

Do not start by reducing the initial increment below the v12 value simply to mask a connectivity problem.

Once Gate 1 passes:
1. Keep a simple elastic baseline first.
2. Run `S01` Geostatic with a full-step-sized initial increment (`initialInc` comparable to `timePeriod`, e.g. 1.0 for a 1.0 step) and automatic cutback available.
3. If it still fails after singularities are removed, then diagnose initial-stress imbalance.
4. Separate natural foundation/geology initial stress from constructed dam fill where feasible.
5. Prefer zone-wise geostatic initial stress for natural strata using documented densities/unit weights and justified K0 values.
6. Do not invent unsupported K0 values. If source K0 is unavailable, clearly document the baseline assumption and sensitivity range.
7. Do not assign a natural in-situ geostatic field to the constructed dam fill if a construction/gravity initialization can be used instead.

A staged-construction improvement is preferred after the elastic core model is stable:
- natural geology/foundation geostatic equilibrium,
- dam construction or gravity buildup,
- then reservoir impoundment / seepage.

## Hydraulic continuity and seepage validation

Do not claim hydraulic continuity merely because a mechanical tie exists.

After `S01` Geostatic completes:
1. Run the normal-reservoir step at upstream `H=3076.00 m` and downstream/tailwater `H=3055.00 m` unless the source specifies otherwise.
2. Use the existing `*Soils, consolidation, end=SS` steady-state termination strategy.
3. Verify paired-interface pore pressures across all porous-to-porous ties/nonconformal interfaces.
4. Extract normal flow / seepage flux on both sides where possible.
5. Verify the cutoff wall and geomembrane form a continuous low-permeability barrier with no geometric bypass.
6. Compute total inflow and outflow and report
   `mass_balance_error = abs(Qin-Qout)/max(abs(Qin),abs(Qout))`.

Do not claim success if the normal seepage step is not actually reached or does not satisfy the steady-state criterion.

## Three mandatory acceptance gates

### Gate 1 — Mechanical stability
PASS only if:
- no unintended free-floating physical instance remains,
- no DOF 1/2/3 numerical singularity or zero pivot in the retained model,
- all retained structures have a real load path to the support system,
- core model and restored full model both complete `S01` Geostatic.

Do not require the raw Abaqus `UNCONNECTED REGIONS` count to be exactly zero if remaining counts are demonstrably caused only by surface/contact auxiliary elements. Explain every residual count.

### Gate 2 — Geostatic equilibrium
PASS only if:
- `S01` completes,
- equilibrium residuals are acceptable,
- displacements are physically reasonable,
- no severe divergence/distortion remains,
- the initial-stress strategy is documented.

### Gate 3 — Normal steady seepage
PASS only if:
- the normal-reservoir pore-pressure step is actually entered and completes via the intended steady-state criterion,
- upstream and downstream head conditions are verified,
- POR is continuous across retained porous interfaces within a documented tolerance,
- inflow/outflow balance is reported,
- no artificial hydraulic disconnect is introduced by ties or nonconformal interfaces.

Only call v13 `VALIDATED` if all three gates pass.

## Required v13 outputs

Create a new corrected model; do not overwrite v12:
- `doub_hydropower_part25_geometric_solids_v13_rigidbody_geostatic_fixed.cae`
- exported `.inp`

Place results under `abaqus-audit/3d-v13/` where practical:
- `V13_DIAGNOSIS.md`
- `V13_FIX_RESULT.md`
- `v13_validation_status.txt`
- `v13_singularity_instances.csv`
- `v13_interfaces.csv`
- `v13_boundary_conditions.csv`
- `v13_element_types.csv`
- `v13_hydraulic_interface_check.csv`
- `v13_mass_balance.txt`
- `v13_keywords_no_mesh.txt`
- Abaqus repair/validation scripts
- final corrected CAE and INP
- core-model diagnostic job logs
- full-model Geostatic and normal-seepage `.msg/.dat/.sta` outputs where feasible.

## Reporting requirements

`V13_FIX_RESULT.md` must explicitly state:
- which v12 singular instances were found,
- what action was taken for each,
- which instances were suppressed in the core diagnostic model and why,
- whether any were later restored,
- the final mechanical connection strategy,
- any remaining `UNCONNECTED REGIONS` warning and why it is benign or not,
- Geostatic completion status,
- normal seepage completion status,
- hydraulic continuity findings,
- mass-balance result,
- unresolved issues.

Do not hide failures. If any gate fails, state `GATE_1_FAIL`, `GATE_2_FAIL`, or `GATE_3_FAIL` and record the exact first failing node/instance/step/increment.
