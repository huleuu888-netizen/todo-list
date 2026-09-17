# Abaqus v3 repair task — geostatic convergence and porous-mesh cleanup

Repository: `huleuu888-netizen/todo-list`
Branch: `abaqus-audit-task`
Base corrected model: `abaqus-audit/doub_part25_2d_seepage_plastic_v2_corrected.cae`
Base model name: `Part25_2D_Seepage_Plastic_v2`

## Safety / preservation requirements

- DO NOT modify `main`.
- DO NOT overwrite the original v1 CAE.
- DO NOT overwrite the v2 CAE.
- Create a new v3 copy named exactly:
  `doub_part25_2d_seepage_plastic_v3_geostatic_fixed.cae`
- Preserve all verified v2 material properties unless this task explicitly requires a change.
- Preserve upstream head H=158.5 m and downstream head H=135 m.
- Preserve permeability water specific weight 9810 N/m3.
- Preserve the currently verified cohesion regularization at 100 Pa; do not reinterpret it as 100 kPa.
- Record every model change in a human-readable report.

## Current known state from v2

The v2 model passed Abaqus/Standard 2022 data check but did not complete the full analysis.
The run was terminated in `GRAVITY_INITIALIZATION` after about 137 increments at step time about 0.0511, with the increment reduced to about 4.52e-7. The seepage step was never reached.

The v2 mesh contains:
- 4692 CPE4P elements
- 41 CPE3 elements

All 41 CPE3 elements are located in porous materials and therefore should participate in pore-pressure/seepage behavior, but CPE3 has no pore-pressure DOF. Abaqus 2022 does not support a direct CPE3P replacement.

The v2 data check also reported 19 distorted elements.

## Main objective

Produce a v3 model that:
1. achieves a genuinely equilibrated initial geostatic state,
2. removes the hydraulic discontinuity caused by the 41 CPE3 elements through supported local remeshing,
3. repairs the 19 distorted elements where feasible,
4. successfully reaches and runs the steady-state seepage step,
5. preserves the validated material parameters and hydraulic boundary heads from v2.

## Phase 1 — diagnose the geostatic nonconvergence before modifying anything

Run the v2 model only through the geostatic step and collect enough output to identify why equilibrium fails.

Required diagnostics:
- parse `.msg`, `.dat`, `.sta`, and available `.odb` output,
- identify elements/nodes associated with the largest residual forces, excessive displacement increments, severe distortion, and first plastic yielding,
- report whether nonconvergence is global or concentrated in a small number of regions,
- identify which material zones the problematic elements belong to,
- report the maximum displacement reached during geostatic initialization,
- report whether large plastic zones appear during the geostatic step,
- report any repeated cutback, negative eigenvalue, excessive distortion, or material instability messages.

Write the diagnostic result to:
`abaqus-audit/V3_GEOSTATIC_DIAGNOSIS.md`

Do not proceed by blindly reducing the increment size. Diagnose the mismatch first.

## Phase 2 — rebuild the initial stress strategy

The v2 model retained one global geostatic initial-stress gradient while the material dry densities were corrected zone by zone. This global stress field is not guaranteed to be consistent with the new self-weight distribution.

Rebuild the initial effective stress field with the following principles:

1. Separate foundation/native ground from dam-fill zones.
2. Use actual corrected dry densities from v2 for self-weight calculations.
3. Use elevation/depth-consistent vertical effective stress instead of one global gradient where possible.
4. Do not assume K0=1 everywhere unless project source data explicitly support it.
5. Search the existing project source files for documented K0 / lateral earth-pressure coefficient / in-situ stress assumptions.
6. If a documented K0 exists for a zone, use it and cite the source in the result report.
7. If no reliable K0 source exists, do not invent a highly specific value. Use a conservative, clearly documented engineering assumption and run sensitivity checks if necessary.
8. Prefer zone-wise initial stress definitions for foundation strata.
9. For dam-fill materials, avoid forcing an unrealistic pre-existing in-situ stress field if the model can instead reach equilibrium by gravity from a reasonable starting condition. If feasible without redesigning the whole project workflow, use a staged/self-weight initialization for dam-fill zones. If not feasible, document the approximation used.

For the geostatic procedure itself:
- keep a true `GeostaticStep`,
- use `timePeriod=1.0`,
- first test an initial increment comparable to the full step (`initialInc=1.0`) rather than starting at 1e-5,
- allow automatic cutbacks only if necessary,
- do not add artificial stabilization unless a specific local instability is identified and justified,
- keep displacement tolerance physically meaningful and document any change.

The acceptance target is not merely “job runs”; the geostatic step should finish with small displacements and without a large artificial plastic zone caused by initial imbalance.

## Phase 3 — fix the 41 CPE3 porous-region triangles

All 41 existing CPE3 elements are hydraulically inappropriate because they lie in porous materials.

Do NOT try to rename CPE3 to a nonexistent CPE3P.

Preferred repair:
- locally repartition/remesh the affected regions with supported pore-pressure elements,
- prefer CPE4P where a compatible quadrilateral mesh can be created,
- if a triangular topology is unavoidable, use a supported Abaqus 2022 pore-pressure triangular formulation and make the surrounding mesh connectivity compatible,
- preserve geometry and material-zone boundaries,
- do not alter the cutoff-wall geometry or hydraulic head boundaries,
- avoid introducing hanging/incompatible nodes.

After remeshing, the final seepage domain should contain zero ordinary CPE3 elements.

Generate a table listing every former CPE3 element region, old labels, new element formulation, and affected material zone.

## Phase 4 — repair the 19 distorted elements

Extract the exact 19 distorted element labels from the v2 data-check output.

For each distorted element:
- identify its material zone,
- determine whether it overlaps one of the CPE3 remeshing regions,
- repair locally by improving partitioning, seeding, element aspect ratio, skewness, and transition quality,
- avoid unnecessary global remeshing.

After v3 remeshing, run a new data check and report whether any distorted-element warnings remain.

## Phase 5 — steady-state seepage

Only after the geostatic step completes successfully should the seepage step be executed.

Retain the v2 steady-state intent:
- `SoilsStep`
- `consolidation`
- `end=SS`
- upstream H=158.5 m
- downstream H=135 m

Keep the v2 pore-pressure-rate steady-state criterion initially (`1e-6 Pa/s`) unless convergence diagnostics show it must be adjusted. If adjusted, document the reason and final value.

Verify:
- the seepage step is actually reached,
- the steady-state criterion is satisfied rather than merely reaching a time limit,
- pore-pressure contours are physically continuous across all remeshed regions,
- FLVEL is available throughout the porous seepage domain,
- no former CPE3 hydraulic gaps remain,
- upstream/downstream boundary pressures still satisfy `p = 9810 * max(H-z, 0)` within numerical rounding.

## Required validation sequence

Run, in order:
1. Abaqus data check on v3.
2. Geostatic-only validation run.
3. Full run through steady-state seepage.
4. Re-run the audit script on the final v3 CAE.

Do not claim success if only the data check passes.

## Required outputs

Commit all text outputs to `abaqus-audit/`:

- `V3_GEOSTATIC_DIAGNOSIS.md`
- `V3_FIX_RESULT.md`
- `abaqus_model_audit_v3.txt`
- `Part25_2D_Seepage_Plastic_v3_keywords_no_mesh.txt`
- `v3_validation_status.txt`
- `v3_problem_elements.csv` (old/new element mapping, distorted elements, material zones)

Also create and preserve:
- `abaqus-audit/doub_part25_2d_seepage_plastic_v3_geostatic_fixed.cae`

If the CAE is too large for a normal GitHub content write, still save it in the existing project output workspace and clearly record the exact local path and SHA-256 in `V3_FIX_RESULT.md`; commit all scripts and text reports to GitHub.

## Validation report must include

- Abaqus version and exact commands used,
- source v2 SHA-256 and final v3 SHA-256,
- exact initial stress strategy used by zone,
- K0 values/assumptions and their sources,
- geostatic convergence history summary,
- maximum geostatic displacement,
- whether plastic yielding occurs during geostatic initialization and where,
- old and new counts of CPE3/CPE4P/other pore-pressure elements,
- old and new distorted-element counts,
- data-check warnings/errors,
- full-run completion status,
- proof that the steady-state seepage criterion was reached,
- hydraulic-head boundary verification,
- any unresolved limitations.

## Success criteria

Do not mark the task complete unless all of the following are true, or explicitly document which criterion remains unresolved:

- v1 and v2 remain unchanged,
- `main` remains unchanged,
- v3 data check passes,
- geostatic step completes,
- geostatic displacement is acceptably small and explained,
- no large artificial plastic zone caused by initial imbalance,
- zero ordinary CPE3 elements remain in porous regions,
- distorted-element warnings are eliminated or materially reduced and justified,
- seepage step is reached,
- steady-state criterion is reached,
- H=158.5 m / H=135 m hydraulic boundaries are preserved,
- final audit files are committed to `abaqus-audit-task`.

Keep the associated GitHub issue open after completion so ChatGPT can inspect the outputs.