# V15.14 Engineering–Model Correspondence Audit

## Scope

This audit compares the engineering entities identified in the available
project records with the V15.13 corrective assembly. It is a correspondence
audit, not a claim that the finite-element model is a one-to-one geometric
reproduction of every design drawing. The V15.13 source record remains the
controlling evidence for geometry and the V15.14 closure record must not invent
missing dimensions or hydraulic coefficients.

## Correspondence matrix

| Engineering entity | Design/source basis | V15.13 model object | Evidence used | Status | Closure note |
|---|---|---|---|---|---|
| Main dam and left-subdam system | Project application and V15.13 geometry audit | `V15_4_LEFT_BANK_SUBDAM_I`, `V15_4_POWERHOUSE_INSTALLATION_BAY_I`, related `V15_4_*` instances | V15.13 station map and CAE organization audit | CHECK | The object family is present; full drawing-dimension equivalence is not proven by the tracked audit alone. |
| Foundation cover and geological layers | Geological report and active V15.13 section audit | `V15_7_FOUNDATION_GEOLOGY_I` | `v15_13_section_level_pore_pressure_audit.csv` | PASS / CHECK | Required cover-layer families are represented; Q3AL_III remains an engineering-equivalent material mapping. |
| Main cutoff wall / anti-seepage chain | Anti-seepage alignment and measured model anchors | `V15_13_ANTI_SEEPAGE_CHAIN_I`, `P25_SOLID_CUTOFF_WALL_F13-1` | `v15_13_cutoff_connection_final.csv` | PASS | The tracked chain-to-cutoff and cutoff-to-geomembrane connections pass the V15.13 geometric audit. |
| Upstream geomembrane | V15.13 upstream barrier representation | `V12_UPSTREAM_GEOMEMBRANE-1` | `v15_13_cutoff_connection_final.csv` and permeability audit | PASS | Present and connected at the measured main-cutoff terminal edge. |
| Right-bank grout curtain | Right-bank anti-seepage design record; approximate reach only | Not represented as a solid or equivalent boundary | `v15_13_right_bank_curtain_resolution.csv` | UNRESOLVED | Axis, thickness, and equivalent hydraulic coefficient are not defensible from the tracked source. |
| Rock foundation and right-bank rock | Geological report and Lu-category records | `GEO_*_ROCK_*`, `GEO_*_FRESH_GRANITE` | `v15_13_rock_hydraulic_parameter_basis.csv` and section audit | CHECK | Rock regions exist, but hydraulic calibration is required; no Lu-to-permeability conversion is invented. |
| Fishway / ecological-release structure | Left-bank fishway geological/building records | `V15_4_FISHWAY` and V15.13 ecological-release connection | V15.13 corrective report and bad-element repair record | CHECK | The object is present and the V15.13 bad-element issue was repaired; one-to-one design dimensions remain outside the tracked evidence. |
| Spillway-to-main-dam transition | Spillway transition source statement | Measured cutoff bend, no defensible gravity-wall body | `v15_13_spillway_main_dam_transition_resolution.csv` | CHECK | The anti-seepage connection is represented; the gravity retaining-wall dimensions remain source-limited. |

## Interpretation

- `PASS` means the tracked V15.13 audit contains direct model evidence for the
  requested correspondence.
- `CHECK` means the object or family exists but engineering dimensional or
  hydraulic closure is still required.
- `UNRESOLVED` means the source does not support a defensible model entry.
- No geometry, permeability, or material coefficient is promoted to a final
  engineering value solely because it makes the model converge.

## Closure decision

The V15.13 model is suitable for continued engineering-closure auditing. It is
not yet a fully source-closed production seepage model. Production seepage
remains on hold until the right-bank curtain definition, rock hydraulic
calibration, and Q3AL_III backfill basis are closed.

