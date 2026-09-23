# S02-S07 Research Case Definition v1

## 1. Scope and baseline

This document defines the follow-on research cases for the V15.26 S01 engineering baseline. It is a study-design artifact only. It does not modify the Abaqus model, generate an input deck, run Abaqus, or overwrite the S01 baseline.

The reference case is the intact S01 normal-impoundment result:

- Total seepage discharge: `Q = 265.859330922` model volume/time units.
- Maximum hydraulic head: `3412.0875296` model length units.
- Regional P95 gradient values are taken from `regional_hydraulic_response_baseline.csv`.
- The filter-layer high-gradient cluster remains a V15.25 localized numerical-peak flag. It is not treated as a confirmed engineering control gradient.

The study matrix is machine-readable in `study_case_matrix_v1.csv`. Every future case must retain the V15.26 geometry, mesh, material framework, and boundary framework unless a later study protocol explicitly approves a new model version. S01 files are immutable comparison data.

## 2. Research objectives

The sequence is designed to separate four questions:

1. How does a single, deterministic anti-seepage defect change total discharge and local gradients?
2. How sensitive is the response to a curtain permeability degradation ratio?
3. Which anti-seepage segment is most hydraulically vulnerable when the same defect is moved spatially?
4. How do heterogeneity, spatial correlation, anisotropy, and approved combined uncertainty affect the response envelope?

The design separates deterministic attribution cases (S02-S04), spatial uncertainty (S05), material-form uncertainty (S06), and integrated validation (S07). S07 is not a substitute for the one-factor cases.

## 3. Common controls and outputs

### 3.1 Fixed controls

For S02-S07, keep the following fixed unless the case definition explicitly names the single variable being studied:

- V15.26 geometry and anti-seepage layout.
- V15.26 mesh and element formulation.
- Normal-impoundment upstream and downstream boundary system.
- Initial-condition and solver settings already accepted for S01.
- Material definitions outside the pre-registered study domain.
- The S01 output definitions and post-processing conventions.

No artificial tie, fixed node, spring, Encastre, or arbitrary constraint may be introduced to make a study case converge. If a case fails, retain the failure evidence and mark that case unresolved.

### 3.2 Required response metrics

Each completed case should report:

- `Q`: total seepage discharge using the same scoped RVF integration convention as S01.
- `Delta_Q` and `Q/Q_S01`.
- Maximum hydraulic head and `Delta_Hmax` relative to S01.
- P95 hydraulic gradient in 防渗墙, 坝基覆盖层, 岩体, and 过滤层.
- Peak gradient value, element/instance, coordinate, material, and region.
- The count of computed and unresolved gradient rows.
- Solver status, increments, cutbacks, warnings, ODB readability, and STA completion.

The V15.24/V15.25 limitation remains active: reconstructed gradients must not be presented as a native Abaqus hydraulic-gradient field unless the required native field output is actually present.

## 4. Case definitions

### S01 — intact baseline

S01 is the reference case and is already completed. It has no defect, degradation, or random field. Its Q, maximum head, regional P95 gradients, and peak-location record are the normalization basis for all deltas and ratios.

### S02 — single curtain continuity defect

Purpose: quantify the response to one localized continuity loss without confounding it with a permeability sweep or random field.

- Variable: gap length `g` in one pre-registered main-cutoff test segment.
- Levels: `0, 1, 5, 10, 20 m`.
- Keep the gap treatment, gap location, material outside the gap, mesh, and boundary system fixed.
- `g=0` is a control rerun only if needed to verify the S01 comparison pipeline. It must reproduce S01 within the declared numerical tolerance.
- No second gap, distributed degradation, or random field is allowed in S02.

Paper relation: deterministic defect severity, discharge amplification, and the onset of a meaningful hydraulic-gradient change.

### S03 — curtain permeability degradation

Purpose: establish the deterministic degradation law for the selected anti-seepage curtain material.

Use exactly the requested ratios:

```text
kd/k0 = 1, 3, 5, 10, 30, 100, 300, 1000
```

Here `k0` is the V15.26 reference permeability of the pre-registered curtain material and `kd` is the degraded value. Only that material/domain permeability changes. Geometry, mesh, other materials, and boundaries remain unchanged.

Paper relation: permeability-degradation sensitivity, nonlinear response, and identification of response regimes.

### S04 — defect-location sensitivity

Purpose: rank the hydraulic importance of the validated anti-seepage segments.

Use one identical defect in one location at a time. The proposed fixed defect is `g=5 m`, with the same hydraulic treatment in every location:

- left-bank 80 m extension;
- left subdam curtain;
- powerhouse/installation-bay curtain;
- spillway transition;
- ecological-release connection;
- main cutoff wall.

No simultaneous defects are allowed. The location list must be frozen before execution and recorded in the case manifest.

Paper relation: spatial vulnerability map and prioritization of inspection or remediation zones.

### S05 — spatial random-field degradation

Purpose: quantify how random heterogeneity and connected low-permeability or high-permeability paths alter the baseline response.

The random-field record must include the random seed, marginal mean, marginal standard deviation, transformation, grid/element support, and the realized field statistics. The required parameters are:

- Coefficient of variation: `Cv = 0.10, 0.20, 0.30, 0.50, 0.80`.
- Correlation length: `Lc = 10, 25, 50, 100, 200 m`.
- Spatial connectivity index: `Csp = 0.00, 0.25, 0.50, 0.75, 1.00`.

Define spatial connectivity as:

```text
Csp = volume of the largest connected degraded cluster / total degraded-cluster volume
```

The connectivity threshold and neighborhood rule must be fixed before sampling. `Csp=0` represents disconnected degradation and `Csp=1` represents one fully connected degraded cluster under the chosen domain definition. The exact realized value, not only the target bin, must be reported.

Use Latin-hypercube screening for the three random-field parameters, followed by fixed-seed realizations for the response envelope. Hold the mean field and marginal distribution convention fixed when isolating the effects of `Cv`, `Lc`, or `Csp`.

Paper relation: stochastic heterogeneity, connected seepage-path formation, and uncertainty in Q and regional gradients.

### S06 — foundation-rock anisotropy sensitivity

Purpose: assess whether directional rock permeability redistributes seepage independently of curtain degradation.

- Variable: `kh/kv` in the pre-registered foundation-rock domain.
- Levels: `1, 3, 10, 30, 100`.
- Preserve the same mean reference permeability and all curtain properties.
- Do not convert Lu measurements to permeability without a documented calibration basis.

Paper relation: anisotropic foundation control, downstream redistribution, and sensitivity of gradient localization.

### S07 — calibrated combined uncertainty envelope

Purpose: produce an engineering response envelope only after the one-factor sensitivities and random-field protocol have been reviewed.

- Inputs: approved distributions or posterior ranges from S02-S06 only.
- Outputs: P05, P50, and P95 for Q, maximum head, and the four regional P95 gradients, plus exceedance probabilities for pre-registered engineering thresholds.
- Minimum design: 200 fixed-seed realizations, with a documented independent validation split.
- No new defect location, material law, boundary condition, or geometry change may be introduced in S07.
- If the prior cases do not support a parameter statistically, keep that parameter unresolved rather than inventing a distribution.

Paper relation: uncertainty synthesis, model validation, and engineering decision support. S07 is an integrated uncertainty case and must not be interpreted as a one-factor causal result.

## 5. Study execution and acceptance rules

Before running any case, create a case manifest containing the parent commit, input hash, changed variable, fixed variables, random seed if applicable, and output requests. Never overwrite S01 or V15.26 files.

For every case, compare against the S01 baseline using the same units and extraction method. A case is `VALID_FOR_COMPARISON` only if the solver completed, the ODB is readable, the STA is complete, zero pivot is zero, and required response fields are present. Otherwise mark the case `UNRESOLVED` and preserve the failure evidence.

The design intentionally leaves the following as calibration or approval items rather than silently closing them: right-bank curtain treatment, rock permeability basis, Q3AL_III verification, and any engineering threshold used to interpret a gradient exceedance.
