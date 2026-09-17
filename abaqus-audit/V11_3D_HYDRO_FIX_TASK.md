# Codex task: rebuild/correct the Multi/Duobu hydropower 3D Abaqus hydro-mechanical model

Work only on branch `abaqus-audit-task`. Do **not** modify `main` and do **not** overwrite the existing 2D v1/v2/v3 models.

## Input model

Primary 3D model files:

- `doub_hydropower_part25_geometric_solids_v11_hydro.cae`
- `doub_hydropower_part25_geometric_solids_v11_hydro.inp`

If the files are not already under the repository/workspace, stop and report `MISSING_3D_INPUT` instead of substituting any 2D model.

The current INP was checked against these source reports:

- `4 地质报告.doc`
- `多布项目申请报告（王洪亮20130421)cm4.doc`

Use the values explicitly listed in this task as the authoritative working values when the source DOC files are unavailable. Do not invent missing data.

## Required output model

Create a corrected copy named:

- `doub_hydropower_part25_geometric_solids_v12_hydro_corrected.cae`
- `doub_hydropower_part25_geometric_solids_v12_hydro_corrected.inp`

Do not overwrite v11.

## Current high-priority defects already identified

### A1. Independent parts/instances are not properly connected

The current INP contains many independent 3D parts/instances, but no effective `*Tie`, contact or MPC network was found for the interfaces. Visual touching is not enough in Abaqus.

Required correction:

1. Prefer a conformal/shared-node topology for the continuous dam-foundation-geology domain. If practical, merge/partition instances while preserving material regions and named sets.
2. If shared-node remeshing is not practical, define explicit compatible tie constraints for every physically bonded interface.
3. For pore-pressure coupled regions, verify hydraulic continuity across the interface as well as displacement continuity. Do not create a mechanically tied but hydraulically disconnected model.
4. Run a connectivity audit and list every interface that is merged/tied.
5. The corrected model must not contain free-floating solids or rigid-body regions.

### A2. The current `hydro` model is not a real pore-pressure/seepage model

The current mesh is primarily `C3D8R` / `C3D6` and the analysis steps are ordinary `*Static` steps. Permeability keywords alone do not create a seepage solution without pore-pressure DOFs.

Required correction:

1. Convert porous dam/foundation/geology solids to supported pore-pressure elements, primarily `C3D8P` and `C3D6P` (or the closest supported coupled pore-pressure 3D formulation available in the installed Abaqus version).
2. Keep truly nonporous structural solids separate only where physically justified.
3. Use an appropriate coupled pore-fluid diffusion / consolidation / soils procedure for the hydraulic steps rather than ordinary static steps.
4. Verify that pore pressure is an active solution DOF in the corrected model.
5. Export the corrected keyword deck and explicitly document the final element types by region.

### A3. Foundation/geological permeability is missing or incomplete

The current dam-zone permeability unit conversion is mostly correct, but the geological/foundation materials do not consistently contain permeability.

Use the following report values. The source report values are in cm/s; the Abaqus working values below are already converted to m/s by dividing by 100.

| Geological material | K source (cm/s) | K for model (m/s) |
|---|---:|---:|
| Q4DEL | 2.33E-3 | 2.33E-5 |
| Q4AL_SGR2 | 2.33E-2 | 2.33E-4 |
| Q4AL_SGR1 | 5.80E-3 | 5.80E-5 |
| Q3AL_V | 4.46E-4 | 4.46E-6 |
| Q3AL_IV2 | 2.35E-4 | 2.35E-6 |
| Q3AL_IV1 | 5.48E-4 | 5.48E-6 |
| Q3AL_III | 8.49E-3 | 8.49E-5 |
| Q3AL_II | 5.89E-5 | 5.89E-7 |
| Q3AL_I | 1.14E-3 | 1.14E-5 |
| Q2FGL_V | 1.14E-3 | 1.14E-5 |
| Q2FGL_IV | 1.70E-4 | 1.70E-6 |
| Q2FGL_III | 3.26E-5 | 3.26E-7 |
| Q2FGL_II | 8.35E-5 | 8.35E-7 |
| Q2FGL_I | 2.50E-5 | 2.50E-7 |

Preserve the already-correct dam-zone permeability conversion unless the model audit proves otherwise. Reference values used in the project report include:

- dam gravel/sand: `2.95E-2 cm/s = 2.95E-4 m/s`
- filter: `4.47E-3 cm/s = 4.47E-5 m/s`
- drainage: `2.25 cm/s = 2.25E-2 m/s`
- impervious fill: `5.1E-5 cm/s = 5.1E-7 m/s`
- geomembrane: `4.5E-9 cm/s = 4.5E-11 m/s`
- cutoff wall: `1.0E-6 cm/s = 1.0E-8 m/s`

Document every final K value and its unit.

### A4. Hydraulic loading is currently physically incorrect

The existing model uses uniform pressures approximately 220, 250, 285 and 80 kPa on selected faces. This is not a valid hydrostatic distribution and is not consistent with the documented water levels.

Use these engineering water levels as the primary source values:

- normal reservoir level: `3076.00 m`
- flood-season/dead-water level: `3074.00 m`
- check flood level: `3077.35 m`

Required correction:

1. Replace constant-face pressures with elevation-dependent water head / pore-pressure boundary conditions.
2. For a point at elevation z under an upstream water surface H, use the hydrostatic relation `p = gamma_w * (H - z)` where submerged, and zero above the water surface.
3. Prefer direct pore-pressure/head boundary conditions on the porous upstream boundary for seepage calculations rather than using only mechanical pressure.
4. Apply downstream head using the documented downstream/tailwater level appropriate to each step. If the exact downstream level for a step cannot be supported by source data, flag it as unresolved rather than guessing.
5. Mechanical water pressure on exposed structural faces may be added separately if required for stress analysis, but it must be consistent with the same water surface.
6. Verify the resulting pressure profile at several elevations and include those checks in the report.

### A5. Cutoff wall geometry is inconsistent with the report

The current v11 main cutoff wall appears about 2 m thick and reaches roughly elevation 3017.98 m.

For the main riverbed gravel dam section, use:

- wall thickness: `1.0 m`
- wall base elevation: `3021.00 m`
- reported maximum construction depth: about `49.10 m`
- connect the wall top to the upstream geomembrane system

Important exception for the whole-project model:

- powerhouse/installation-bay cutoff wall segment from approximately dam-left 0+081 to 0+192 has base elevation `3011.00 m`
- transition to `3021.00 m` with approximately 1:1 slopes

If this v11/v12 model only represents the 295 m main gravel-dam section, do not incorrectly extend the 3011 m powerhouse depth through the entire main dam. Document which physical segment the model represents.

### A6. Geomembrane material exists but is not assigned to an actual model region

The current INP defines a `GEOMEMBRANE` material, but it is not meaningfully assigned to a part/section in the structural model.

Required correction:

1. Create an actual upstream geomembrane/seepage barrier from the relevant cofferdam elevation upward and connect it to the cutoff wall top.
2. Do not create an impractically thin 3D solid if that destroys mesh quality. A shell/membrane/interface/equivalent thin hydraulic layer is acceptable if the hydraulic resistance is preserved.
3. Preserve equivalent hydraulic resistance `t / k` when using an equivalent thickness.
4. Document the representation, thickness, permeability and connection to the cutoff wall.

## Secondary corrections

### B1. Add soil plasticity where the study requires plastic zones/stability

The current materials are mostly only `Density + Elastic`.

If the v12 model is intended for seepage-stress-plastic analysis, add a defensible soil plasticity model, preferably Mohr-Coulomb for the soil/gravel regions when supported by the source parameters.

Known report values include dry/saturated unit weights and friction angles for dam zones and foundation layers. Do not invent dilation angle. If dilation angle or another required parameter is not supported by the source documents, mark it `UNRESOLVED` and either keep an elastic verification model or run a clearly labeled sensitivity case.

### B2. Replace fake construction step with a real initial-stress/construction sequence

The current construction step is effectively just another gravity/static step.

Preferred sequence:

1. natural geology/foundation initial stress equilibrium
2. construction/staged activation of dam and relevant zones if required by the study
3. normal reservoir impoundment to 3076 m
4. steady/semi-steady seepage equilibrium
5. check flood / earthquake cases as appropriate
6. drawdown to 3074 m or other documented operating level

Use geostatic initialization where feasible. Do not start a deep foundation model from zero stress and treat the first gravity step as final in-situ stress without checking equilibrium.

If staged construction is outside the intended scope, clearly state the simplification and at minimum establish a stable gravity/geostatic initial state before hydraulic loading.

### B3. Correct the right-bank deformation-body geometry (BX01/BX02/BX03) or exclude it explicitly

Source report reference ranges:

- BX01: top about 3305 m, base about 2990 m
- BX02: top about 3201 m, base about 3005 m
- BX03: top about 3170 m, base about 3040 m

The current v11 BX02/BX03 solids appear substantially too high.

Required correction:

1. If right-bank deformation bodies are part of the analysis domain, rebuild/reposition them to the documented elevation ranges and preserve the intended plan location.
2. If the current study is only the main-riverbed dam seepage section and these bodies are outside the justified model domain, remove/exclude them rather than retaining incorrectly located solids.
3. State the decision in the result report.

### B4. Density consistency

The dam material report values are often unit weights in kN/m3, not mass density.

If the working unit system is m-kN-s-tonne and gravity is 9.81 m/s2, convert unit weight by:

`rho [t/m3] = gamma [kN/m3] / 9.81`

Examples:

- 21.6 kN/m3 -> about `2.202 t/m3`
- 14.6 kN/m3 -> about `1.488 t/m3`
- 19.7 kN/m3 -> about `2.008 t/m3`
- 19.2 kN/m3 -> about `1.957 t/m3`

Do not blindly change geological densities that are already source dry densities in g/cm3; in this unit system, 1 g/cm3 = 1 t/m3.

### B5. Crest elevation/version consistency

The reports contain design-version differences. The detailed design/finalized values are preferred over the simplified geologic-check geometry.

Use and document one consistent choice:

- standard/final crest: about `3079.00 m`
- seismic settlement allowance may require main central crest around `3080.00 m`, grading to 3079.00 m at the sides

Do not mix the older simplified 3051/3078/1:3 geologic-check section with the later detailed main-dam geometry without clearly labeling the simplification.

## Required model validation

Do not claim success because CAE opens or data check passes. Perform the following where Abaqus is available:

1. CAE opens and regenerates without geometry errors.
2. Keyword export succeeds.
3. Data check succeeds.
4. No unsupported/ordinary non-pore-pressure elements remain in porous seepage regions.
5. No unconnected physical regions remain.
6. Initial geostatic/gravity equilibrium completes with acceptable force residuals.
7. Normal-reservoir seepage step converges/reaches the intended steady-state criterion.
8. Pore-pressure/head field is continuous across bonded geological interfaces.
9. Upstream head corresponds to 3076 m and pressure varies correctly with elevation.
10. Report total inflow/outflow or another mass-balance check and quantify the mismatch.
11. Check for negative Jacobians, severe distortion and zero-pivot/singularity warnings.
12. Verify cutoff wall and geomembrane hydraulic barrier behavior.
13. If plasticity is enabled, verify that plastic parameters are source-supported and document any assumptions.

If a step fails, do not hide it. Record the exact failure and last converged increment/time.

## Required files to commit back to branch `abaqus-audit-task`

Place these under `abaqus-audit/3d-v12/` where practical:

- `V11_3D_HYDRO_DIAGNOSIS.md`
- `V12_3D_HYDRO_FIX_RESULT.md`
- `v12_3d_validation_status.txt`
- `v12_3d_materials.csv`
- `v12_3d_interfaces.csv`
- `v12_3d_element_types.csv`
- `v12_3d_hydraulic_bc_check.csv`
- `v12_3d_keywords_no_mesh.txt`
- any Abaqus noGUI repair/rebuild script(s)
- `doub_hydropower_part25_geometric_solids_v12_hydro_corrected.cae`
- `doub_hydropower_part25_geometric_solids_v12_hydro_corrected.inp`

If a CAE binary cannot be committed because of environment or size limitations, commit the exact repair script plus exported INP and clearly state how to regenerate the CAE.

## Result-report checklist

`V12_3D_HYDRO_FIX_RESULT.md` must include:

- what was changed vs v11
- what was deliberately not changed
- final unit system
- final element types by region
- complete permeability table
- complete density table with source/converted units
- interface/connectivity strategy
- cutoff wall dimensions/elevations
- geomembrane representation
- hydraulic boundary conditions by step
- initial stress / construction sequence
- BX01/BX02/BX03 decision
- solver/data-check results
- remaining unresolved items

## Safety rule for source ambiguity

When the two reports disagree, do not silently choose a value. Prefer the later detailed project-design value only when the context makes that clear, and record the conflict in the diagnosis/result report. If the choice materially affects the model and cannot be justified, leave it unresolved and ask for a decision.
