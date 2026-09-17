# Abaqus corrected-model result (Issue #2)

## Deliverables

- Corrected copy: `doub_part25_2d_seepage_plastic_v2_corrected.cae`
- Model: `Part25_2D_Seepage_Plastic_v2`
- Source CAE was not overwritten. Its SHA-256 remains `E3FCFC71322137A00A678CA46FD1B307A8B3D1C3E7ECD6407CD2111C75775A84`.
- Corrected CAE SHA-256: `CD41A35B85BEE11080A2A6BA46C25F0BBF52AC53AFBBFDDA45A0BAE6ABAFC9DE`.

## Density corrections

All values are kg/m3. Dam-zone dry densities are from the wind-dry unit weights in `Codex生成模型/work/project_application.txt`, table 5.2.3, converted with `rho = gamma / 9.81`. Foundation dry densities are from the `干密度 γd` column in tables 25 and 28 of `土体物理力学性质数据.docx`. The concrete cutoff-wall density is unchanged.

| Material | Old | New |
| --- | ---: | ---: |
| MAT_BAKESHALI | 2405.71 | 2201.83 |
| MAT_BAKESHALI_NUM_ELASTIC | 2405.71 | 2201.83 |
| MAT_BIQILIAO | 1957.19 | 1488.28 |
| MAT_FANGSHENQIANG | 2440.00 | 2440.00 |
| MAT_FANLVCENG | 2375.13 | 2201.83 |
| MAT_FANLVCENG_NUM_ELASTIC | 2375.13 | 2201.83 |
| MAT_PAISHUI | 2283.38 | 2008.15 |
| MAT_Q2 | 2375.13 | 2130.00 |
| MAT_Q2_NUM_ELASTIC | 2375.13 | 2130.00 |
| MAT_Q6 | 2436.29 | 1700.00 |
| MAT_Q7 | 2069.32 | 2130.00 |
| MAT_Q8 | 2089.70 | 1740.00 |
| MAT_Q9 | 2130.48 | 2130.00 |
| MAT_Q10 | 2436.29 | 2130.00 |
| MAT_Q11 | 2426.10 | 2130.00 |
| MAT_Q12 | 2426.10 | 1760.00 |
| MAT_WEIYANJITI | 2283.38 | 1957.19 |
| MAT_WEIYANSHALI | 2375.13 | 2201.83 |

Permeability water specific weight remains 9810 N/m3.

## Cohesion review

The generation report identifies the source model-table cohesion as 0 kPa. `postprocess_part25_2d_seepage_plastic.py` explicitly applies `max(cohesion * 1000, 100)` in the Pa-based model, documenting 100 Pa (0.1 kPa) as numerical regularization. Therefore the existing `*Mohr Coulomb Hardening` value `100., 0.` was deliberately retained; it was not reinterpreted as 100 kPa.

## Procedure changes

- Replaced the active regular static gravity initialization with `GeostaticStep` `GRAVITY_INITIALIZATION`; the original static step is retained only as suppressed `GRAVITY_INITIALIZATION_LEGACY_SUPPRESSED` for traceability.
- Geostatic keyword/API settings: `*Geostatic, utol=0.01` and `1e-05, 1., 1e-10, 0.01`, maximum 10,000 increments. Gravity remains `(0, -9.81)`. Bottom fixed and side roller constraints are preserved. No artificial stabilization is used.
- The original global geostatic stress definition is preserved. Because one global gradient cannot exactly match all corrected densities, the new geostatic step is allowed to equilibrate with small automatic increments; no unverified layer-by-layer stress field was invented.
- Replaced the forced 100 s termination with steady-state soils termination: `*Soils, consolidation, end=SS, utol=1000.0` and `0.0001, 1e+09, 1e-10, 1e+07, 1.0e-6`. The fifth value is the steady pore-pressure-rate criterion in Pa/s.
- Initial drained pore pressure is active in the geostatic step and deactivated in the seepage step.

## CPE3 audit and unresolved Abaqus 2022 limitation

All 41 triangles are assigned to porous materials with permeability, so all are intended to participate in seepage. Their effective last-applied section/material assignments are:

| Assignment / material | Element labels |
| --- | --- |
| SEC_PAISHUI / MAT_PAISHUI | 3852, 3853, 3854, 3855, 4005, 4006, 4007, 4008, 4009 |
| NUM_ELASTIC_FANLVCENG / MAT_FANLVCENG_NUM_ELASTIC | 3870 |
| SEC_BAKESHALI / MAT_BAKESHALI | 3894, 3895, 3896, 3897, 3898, 3899, 3900, 4177, 4178 |
| NUM_ELASTIC_BAKESHALI / MAT_BAKESHALI_NUM_ELASTIC | 4179, 4222 |
| SEC_Q2 / MAT_Q2 | 4031, 4033 |
| NUM_ELASTIC_Q2 / MAT_Q2_NUM_ELASTIC | 4032, 4034 |
| SEC_WEIYANJITI / MAT_WEIYANJITI | 4251, 4252, 4312, 4313, 4314 |
| SEC_WEIYANSHALI / MAT_WEIYANSHALI | 4295, 4296, 4297 |
| SEC_BIQILIAO / MAT_BIQILIAO | 4325, 4326, 4327 |
| SEC_Q8 / MAT_Q8 | 4346, 4347, 4348, 4349, 4350 |

**Unresolved:** Abaqus 2022 does not expose or accept a `CPE3P` element code (the first supported plane-strain pore-pressure triangle is higher order, such as `CPE6MP`). Consequently, converting these existing 3-node orphan-mesh elements to the requested `CPE3P` would create an invalid input deck. They remain `CPE3`. A complete hydraulic fix requires local remeshing to a supported pore-pressure topology; this was not done because it would change connectivity/mesh topology beyond the task's preservation constraint. No CPE3 elements were found in `SEC_FANGSHENQIANG`.

## Hydraulic heads

The pressure distributions were not changed. Direct checks of the generated input against `p = 9810(H-z)` found:

- Upstream H=158.5 m: 90 nodes, maximum absolute difference 5 Pa (input precision rounding).
- Downstream H=135 m: 78 nodes, maximum absolute difference 0.5 Pa.

## Validation summary

The final regenerated input passed Abaqus/Standard 2022 data check. A full analysis attempt was stopped during the geostatic step after 137 increments at step time about 0.0511 because progress had reduced to increments of about `4.52e-7`; it did not reach the seepage step and convergence is not claimed. See `v2_validation_status.txt` for exact commands and warnings.
