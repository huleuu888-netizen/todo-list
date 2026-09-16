# Codex task: create a corrected Abaqus CAE without overwriting the original

Work on branch `abaqus-audit-task`.

## Input model
Use the same source CAE that was successfully audited:

`D:\Backup\Documents\ChatGPT\多步水电站\Codex生成模型\outputs\doub_part25_2d_seepage_plastic_v1.cae`

Do **not** modify or overwrite this original file.

Create a new model database named:

`doub_part25_2d_seepage_plastic_v2_corrected.cae`

Prefer working from an ASCII-only temporary directory if Abaqus 2022 has path encoding problems.

## Goal
Correct the model issues identified from the audit, while preserving geometry, partitions, section layout, mesh topology where possible, water levels, and the original model for comparison.

The model uses an m-N-s SI unit system: length m, force N, time s, stress Pa, density kg/m^3, permeability m/s, gravity 9.81 m/s^2, water specific weight 9810 N/m^3.

## 1. Correct material Density to dry skeleton density
The current density values appear to be saturated/wet bulk densities. For Abaqus pore-pressure elements, use dry skeleton density rather than saturated bulk density so pore-water self-weight is not double-counted.

Before modifying, search the existing workspace/model-generation scripts/parameter files for the original density definitions and determine whether each supplied value is documented as dry density, natural density, wet density, or saturated density. If an authoritative dry-density value exists, use it and record the source in the change log.

If no authoritative dry-density value is found, use the following provisional dry-density values derived from the audited current density and void ratio using:

`rho_d = rho_sat - rho_w * e/(1+e)`, with `rho_w = 1000 kg/m^3`.

Apply these provisional values only when no better source value exists:

- MAT_BAKESHALI: 2199 kg/m^3
- MAT_BAKESHALI_NUM_ELASTIC: 2199 kg/m^3
- MAT_BIQILIAO: 1489 kg/m^3
- MAT_FANGSHENQIANG: 2435 kg/m^3 (difference is negligible; keeping 2440 is acceptable if this is concrete/very low porosity)
- MAT_FANLVCENG: 2202 kg/m^3
- MAT_FANLVCENG_NUM_ELASTIC: 2202 kg/m^3
- MAT_PAISHUI: 2008 kg/m^3
- MAT_Q2: 2110 kg/m^3
- MAT_Q2_NUM_ELASTIC: 2110 kg/m^3
- MAT_Q6: 2103 kg/m^3
- MAT_Q7: 1759 kg/m^3
- MAT_Q8: 1735 kg/m^3
- MAT_Q9: 1871 kg/m^3
- MAT_Q10: 2188 kg/m^3
- MAT_Q11: 2178 kg/m^3
- MAT_Q12: 2116 kg/m^3
- MAT_WEIYANJITI: 1955 kg/m^3
- MAT_WEIYANSHALI: 2042 kg/m^3

Keep permeability water specific weight at `9810 N/m^3`; that value is consistent with the SI unit system.

## 2. Check Mohr-Coulomb cohesion units before changing
The audited keyword file shows `*Mohr Coulomb Hardening` with `100., 0.` for many materials. In the current SI unit system this means 100 Pa = 0.1 kPa.

Do not blindly replace this value.

Search the model-generation scripts, parameter tables, spreadsheets, or nearby project files for intended cohesion `c` values and their units.

- If the source says `c = 100 kPa`, set Abaqus value to `100000 Pa`.
- If the source deliberately uses a near-zero cohesion (for example 0.1 kPa as a numerical regularization for granular material), retain `100 Pa` and record that it is intentional.
- If different materials have different cohesion values, apply the source values individually rather than using one value for every material.
- If the intended values cannot be established, leave cohesion unchanged and clearly flag it as unresolved in the report rather than guessing.

## 3. Replace the gravity initialization procedure with a proper geostatic initialization when feasible
The current `GRAVITY_INITIALIZATION` is a regular `StaticStep` with gravity and numerical stabilization. Create a proper geostatic initialization for the corrected model so the initial stress field, gravity, and constraints are checked for equilibrium before seepage loading.

Requirements:
- Preserve the existing gravity magnitude/direction: `9.81`, direction `(0, -1)`.
- Preserve bottom fixed and side roller mechanical constraints.
- Preserve the existing initial geostatic stress definition initially, then verify equilibrium.
- If a single global geostatic stress gradient is inconsistent with the corrected material densities, improve the initial stress assignment if practical; otherwise document the mismatch and allow the geostatic step to equilibrate it with small initial increments.
- Do not use artificial stabilization unless needed after trying a normal geostatic step; if stabilization is required, report why.

If Abaqus/CAE API limitations prevent direct conversion of the existing step, create a new GeostaticStep, move/activate the necessary gravity and BCs, then remove or suppress the old regular static initialization in the copied model only.

## 4. Correct the so-called steady seepage step
The audited `GRAVITY_AND_STEADY_SEEPAGE` step is actually a transient consolidation step with `timePeriod=100 s` and `end=PERIOD`. For a dam-scale model with permeabilities down to 1e-8 to 1e-7 m/s, 100 seconds is not a meaningful steady-state seepage duration.

Modify the corrected model so the seepage result is genuinely steady-state or converged to steady state.

Preferred approach:
- Use the Abaqus soils procedure in a steady-state-compatible configuration.
- If using consolidation to reach steady state, use a steady-state termination criterion (`END=SS`) with an appropriate convergence tolerance instead of forcing termination at 100 s.
- Preserve the upstream water level H=158.5 m and downstream water level H=135 m pore-pressure boundary distributions.
- Do not alter the hydraulic head values merely to improve convergence.
- Keep water specific weight = 9810 N/m^3.

Record the exact keyword/API settings used for the corrected seepage step.

## 5. Audit and correct the 41 CPE3 elements
The model contains 4692 `CPE4P` elements and 41 ordinary `CPE3` elements. Ordinary CPE3 elements do not carry pore-pressure DOF, so any CPE3 located in a porous/seepage region can interrupt the hydraulic field.

Identify every one of the 41 CPE3 elements and report its section/material assignment.

For any of these elements that belong to a material/region intended to participate in seepage, convert the element formulation to the corresponding pore-pressure triangle (`CPE3P`) while preserving connectivity and section assignment.

If any CPE3 is intentionally nonporous, leave it unchanged and state why.

Pay special attention to `SEC_FANGSHENQIANG`: the material has permeability `1e-8 m/s`. If its elements are ordinary CPE3, the defined permeability is ineffective and the wall behaves as perfectly impermeable. If the design intent is a low-permeability wall rather than a mathematically impermeable wall, use pore-pressure elements there.

## 6. Preserve hydraulic boundary conditions
Do not change the existing upstream/downstream pore-pressure BC values unless a clear inconsistency with H=158.5 m and H=135 m is found.

Check representative boundary nodes against `p = gamma_w * (H - z)` using `gamma_w = 9810 N/m^3` and record whether the existing pressure values are consistent.

## 7. Validation and outputs
After modifications:

1. Save the copied CAE as `doub_part25_2d_seepage_plastic_v2_corrected.cae`.
2. Run the existing `abaqus_model_audit.py` against the corrected CAE.
3. Export corrected keyword text without node/element coordinates if possible.
4. Perform at least an Abaqus data check / model consistency check. If practical, run the geostatic step and seepage step and report whether they converge. Do not claim convergence if only a data check was performed.
5. Never overwrite the source CAE.

Commit these text outputs to branch `abaqus-audit-task` under `abaqus-audit/`:

- `MODIFY_RESULT.md` — concise change log: old value -> new value, source/rationale, unresolved assumptions
- `abaqus_model_audit_v2.txt`
- `Part25_2D_Seepage_Plastic_v2_keywords_no_mesh.txt`
- `v2_validation_status.txt` — Abaqus version, exact commands, data-check/run status, warnings/errors

If the corrected `.cae` is small enough and repository policy permits binary files, also commit it under `abaqus-audit/`; otherwise leave it in the existing workspace outputs directory and record its exact path and SHA-256 in `v2_validation_status.txt`.

## Important constraints
- Do not overwrite the original CAE.
- Do not modify `main`; stay on `abaqus-audit-task`.
- Do not invent cohesion values if source data cannot be found.
- Do not change water levels or geometry merely to make the analysis converge.
- Prefer traceable changes and a clear report over silent guesses.
