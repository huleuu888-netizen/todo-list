# Case Parameter Mapping v1

## 1. Basis and scope

This mapping is based on study-design commit `4b81262` and the V15.26 S01
baseline. It is a read-only object audit. No Abaqus job was run, no input deck
was generated, and no geometry, mesh, material, or boundary file was modified.

V15.26 is an engineering-response summary rather than a separate rebuilt model
deck. The model-object source used for this audit is the unchanged V15.24 S01
input retained as the V15.26 baseline source:

```text
abaqus-audit/3d-v15.24/S01/v15_24_S01_BASELINE.inp
```

The mapping therefore distinguishes between:

- an object that exists in the current input;
- a parameter that can be changed at material scope;
- a parameter that needs a new element subset or field-assignment interface;
- a study case that is not implementable until missing engineering evidence is supplied.

## 2. Confirmed anti-seepage and filter objects

| Role | Part | Instance | Material | Element Set | Current permeability entry | Mapping note |
|---|---|---|---|---|---:|---|
| Main cutoff wall | `V15_5_REFINED_P25_SOLID_CUTOFF_WALL_F13_1` | `P25_SOLID_CUTOFF_WALL_F13-1` | `P25_FANGSHENQIANG` | `V15_5_ALL` | `1e-08` | Existing porous cutoff wall; one aggregate element set |
| Anti-seepage chain | `V15_13_ANTI_SEEPAGE_CHAIN` | `V15_13_ANTI_SEEPAGE_CHAIN_I` | `P25_FANGSHENQIANG` | `V15_13_ANTI_SEEPAGE_ALL` | `1e-08` | Existing chain is one aggregate set; segment-level sets are absent |
| Upstream geomembrane | `V15_5_REFINED_V12_UPSTREAM_GEOMEMBRANE_1` | `V12_UPSTREAM_GEOMEMBRANE-1` | `GEOMEMBRANE` | `V15_5_ALL` | `4.5e-11` | Separate material and aggregate element set |
| Filter layer | `P25_SOLID_FILTER_LAYER_F01` | `P25_SOLID_FILTER_LAYER_F01-1` | `P25_FANLV` | `V15_5_ALL` | `4.47e-05` | Existing filter object; `C3D6P` and `C3D8P` element blocks are present |

The input contains a material-level `*Permeability, specific=9.81` entry. The
same `P25_FANGSHENQIANG` material is assigned to both the main cutoff wall and
the anti-seepage chain. A material edit made without splitting the material
scope would therefore affect both objects.

## 3. Foundation geology and cover-layer mapping

The foundation domain is:

| Part | Instance | Element formulations | Scope |
|---|---|---|---|
| `V15_7_FOUNDATION_GEOLOGY` | `V15_7_FOUNDATION_GEOLOGY_I` | `C3D8P`, `C3D8R` | Foundation cover, alluvial layers, Q2FGL layers, and rock sections |

### 3.1 Foundation cover and compacted backfill sets

These are the current cover/backfill element-set-to-material mappings. The
permeability values are the current scalar entries in the input and are not
newly calibrated by this audit.

| Element Set | Material | Current k | Cover/backfill role |
|---|---|---:|---|
| `FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL` | `Q3AL_III` | `8.49e-05` | Local compacted sand-gravel foundation backfill |
| `GEO_LEFT_L01_Q4DEL` | `Q4DEL` | `2.33e-05` | Left cover/colluvial layer |
| `GEO_LEFT_L03_Q4AL_SGR1` | `Q4AL_SGR1` | `5.8e-05` | Left sand-gravel cover layer |
| `GEO_LEFT_L05_Q3AL_IV2` | `Q3AL_IV2` | `2.35e-06` | Left alluvial cover layer |
| `GEO_LEFT_L06_Q3AL_IV1` | `Q3AL_IV1` | `5.48e-06` | Left alluvial cover layer |
| `GEO_LEFT_L07_Q3AL_III` | `Q3AL_III` | `8.49e-05` | Left alluvial cover layer |
| `GEO_LEFT_L08_Q3AL_II` | `Q3AL_II` | `5.89e-07` | Left alluvial cover layer |
| `GEO_LEFT_L09_Q3AL_I` | `Q3AL_I` | `1.14e-05` | Left alluvial cover layer |
| `GEO_RIVER_R02_Q4AL_SGR2` | `Q4AL_SGR2` | `2.33e-04` | River cover/sand-gravel layer |
| `GEO_RIVER_R05_Q3AL_IV2` | `Q3AL_IV2` | `2.35e-06` | River alluvial cover layer |
| `GEO_RIVER_R06_Q3AL_IV1` | `Q3AL_IV1` | `5.48e-06` | River alluvial cover layer |
| `GEO_RIVER_R07_Q3AL_III` | `Q3AL_III` | `8.49e-05` | River alluvial cover layer |
| `GEO_RIVER_R08_Q3AL_II` | `Q3AL_II` | `5.89e-07` | River alluvial cover layer |
| `GEO_RIVER_R09_Q3AL_I` | `Q3AL_I` | `1.14e-05` | River alluvial cover layer |
| `GEO_RIGHT_Q4_COLLUVIAL` | `Q4DEL` | `2.33e-05` | Right-bank colluvial cover |
| `GEO_RIGHT_R04_Q3AL_V` | `Q3AL_V` | `4.46e-06` | Right-bank alluvial cover |
| `GEO_RIGHT_HIGH_TERRACE_COVER` | `Q3AL_V` | `4.46e-06` | Right high-terrace cover |

The cover-layer mapping is present and implementable at element-set/material
scope. The current V15.26 baseline does not, however, provide a separate
random-field assignment for these sets.

### 3.2 Foundation rock sets

| Element Set | Material | Current permeability status |
|---|---|---|
| `GEO_LEFT_P2_QUARTZ_SANDSTONE` | `P2_QUARTZITE` | No `*Permeability` entry found |
| `GEO_LEFT_FOUNDATION_GRANITE` | `FRESH_GRANITE` | No `*Permeability` entry found |
| `GEO_LEFT_L10_Q2FGL_V` | `Q2FGL_V` | Scalar `1.14e-05` |
| `GEO_LEFT_L11_Q2FGL_IV` | `Q2FGL_IV` | Scalar `1.7e-06` |
| `GEO_LEFT_L12_Q2FGL_III` | `Q2FGL_III` | Scalar `3.26e-07` |
| `GEO_LEFT_L13_Q2FGL_II` | `Q2FGL_II` | Scalar `8.35e-07` |
| `GEO_LEFT_L14_Q2FGL_I` | `Q2FGL_I` | Scalar `2.5e-07` |
| `GEO_RIVER_R10_Q2FGL_V` | `Q2FGL_V` | Scalar `1.14e-05` |
| `GEO_RIVER_R11_Q2FGL_IV` | `Q2FGL_IV` | Scalar `1.7e-06` |
| `GEO_RIVER_R12_Q2FGL_III` | `Q2FGL_III` | Scalar `3.26e-07` |
| `GEO_RIVER_R13_Q2FGL_II` | `Q2FGL_II` | Scalar `8.35e-07` |
| `GEO_RIVER_R14_Q2FGL_I` | `Q2FGL_I` | Scalar `2.5e-07` |
| `GEO_RIVER_ROCK_STRONG_UNLOADED` | `ROCK_STRONG_UNLOADED` | No `*Permeability` entry found |
| `GEO_RIVER_ROCK_WEAK_UNLOADED` | `ROCK_WEAK_UNLOADED` | No `*Permeability` entry found |
| `GEO_RIVER_ROCK_DEEP_UNLOADED` | `ROCK_DEEP_UNLOADED` | No `*Permeability` entry found |
| `GEO_RIVER_FRESH_GRANITE` | `FRESH_GRANITE` | No `*Permeability` entry found |
| `GEO_RIGHT_ROCK_STRONG_UNLOADED` | `ROCK_STRONG_UNLOADED` | No `*Permeability` entry found |
| `GEO_RIGHT_ROCK_WEAK_UNLOADED` | `ROCK_WEAK_UNLOADED` | No `*Permeability` entry found |
| `GEO_RIGHT_ROCK_DEEP_UNLOADED` | `ROCK_DEEP_UNLOADED` | No `*Permeability` entry found |
| `GEO_RIGHT_FRESH_GRANITE` | `FRESH_GRANITE` | No `*Permeability` entry found |

This is the object-level reason the rock-permeability closure remains
incomplete. The Q2FGL sets have scalar permeability entries, but several
explicit rock materials do not.

## 4. S02-S07 variable mapping

| Case | Study variable | Part | Instance | Material | Element Set | Parameter to modify | Current implementation condition |
|---|---|---|---|---|---|---|---|
| S02 | Main-cutoff gap length `g` | `V15_5_REFINED_P25_SOLID_CUTOFF_WALL_F13_1` | `P25_SOLID_CUTOFF_WALL_F13-1` | `P25_FANGSHENQIANG` | `V15_5_ALL` | Local continuity/gap geometry over one pre-registered segment | **CHECK**. Whole wall exists, but no local gap subset or segment-level set exists. A future study preprocessor must derive and record a local element subset; no geometry change is authorized by this mapping task. |
| S03 | Curtain permeability ratio `kd/k0` | Main cutoff plus chain, as selected | `P25_SOLID_CUTOFF_WALL_F13-1`; `V15_13_ANTI_SEEPAGE_CHAIN_I` | Shared `P25_FANGSHENQIANG` | `V15_5_ALL`; `V15_13_ANTI_SEEPAGE_ALL` | Material-level scalar permeability, `kd=(kd/k0)k0` | **CHECK**. Feasible as a network-wide shared-material sweep. Not wall-only unless the material/section scope is split in a future derived model. Required ratios are 1, 3, 5, 10, 30, 100, 300, 1000. |
| S04 | Defect location | Main cutoff, chain, and geomembrane candidates | Main cutoff, `V15_13_ANTI_SEEPAGE_CHAIN_I`, `V12_UPSTREAM_GEOMEMBRANE-1` | `P25_FANGSHENQIANG`; `GEOMEMBRANE` | `V15_5_ALL`; `V15_13_ANTI_SEEPAGE_ALL`; `V15_5_ALL` | Apply the same fixed defect to one segment at a time | **NOT READY** for segment ranking. The chain is one aggregate set; left-bank, subdam, powerhouse/installation, spillway, and ecological-release sub-sets are not exposed as named element sets. |
| S05 | Random-field `Cv`, `Lc`, `Csp` | `V15_7_FOUNDATION_GEOLOGY`; optional curtain/filter domains | `V15_7_FOUNDATION_GEOLOGY_I`; optional curtain instances | Q3AL/Q4AL/Q2FGL and selected curtain material | The 17 cover/backfill sets above; 20 rock sets above; curtain sets if included | Spatially varying permeability field assigned to elements or a field-dependent material | **NOT READY** through the current deck interface. Current permeability is material-level scalar data; no field/distribution or element-level random-k assignment is present. |
| S06 | Foundation-rock anisotropy `kh/kv` | `V15_7_FOUNDATION_GEOLOGY` | `V15_7_FOUNDATION_GEOLOGY_I` | Q2FGL and/or verified rock materials | Q2FGL and rock sets listed above | Directional permeability tensor or anisotropy ratio | **NOT READY**. Current entries are scalar permeability; several explicit rock materials have no permeability entry. A source-backed tensor and derived material interface are required. |
| S07 | Calibrated joint uncertainty envelope | Union of the approved S02-S06 domains | Corresponding instances above | Approved derived material scopes | Approved derived subsets from S02-S06 | Joint sampled variables, with seed and realization metadata | **NOT READY**. Depends on unresolved S02 local subsets, S04 segment sets, S05 random-field interface, S06 rock tensor, and right-bank treatment. |

## 5. Right-bank curtain check

No current `Part`, `Instance`, `Material`, or `Element Set` identified in the
V15.26 source input is named or documented as a right-bank seepage curtain.
The input does contain right-bank geology sets such as
`GEO_RIGHT_R04_Q3AL_V`, `GEO_RIGHT_HIGH_TERRACE_COVER`, and the right-bank
rock sets, but these are geology sections, not a curtain object.

The V15.20 closure records also state that the right-bank curtain geometry,
continuity, thickness, material, and permeability remain unresolved and are
not inserted into the baseline. Therefore:

```text
RIGHT_BANK_CURTAIN_MAPPING = UNRESOLVED
IMPLEMENTABLE_IN_CURRENT_MODEL = NO
```

The right-bank geology can be used as an observation domain or candidate
foundation domain only. It cannot be relabeled as a curtain without
source-backed geometry and hydraulic parameters.

## 6. Random-field permeability interface check

The current input exposes permeability through material blocks, for example:

```text
*Material, name=P25_FANGSHENQIANG
*Permeability, specific=9.81
1e-08,0.
```

The same pattern is used for `P25_FANLV`, `GEOMEMBRANE`, Q3AL, Q4AL, and
Q2FGL materials where a scalar permeability is present. The current model
does not expose:

- an element-wise permeability table;
- a spatial random-field or distribution object;
- a field-variable-dependent permeability definition;
- named element subsets for each S04 anti-seepage segment.

Consequently, S05 cannot be implemented by changing one scalar material value.
A future authorized implementation must choose and document one interface,
such as explicit element-subset/material clones or a verified field-dependent
material formulation, then preserve the random seed, support scale, marginal
statistics, and realized `Csp`. That implementation is outside this mapping
task and must not overwrite V15.26.

## 7. Implementation readiness decision

| Check | Result | Reason |
|---|---|---|
| Anti-seepage material correspondence | **PASS for object inventory; CHECK for selective studies** | Main cutoff and chain share `P25_FANGSHENQIANG`; geomembrane and filter are separately mapped. |
| Foundation cover-layer regions | **PASS for existing set/material mapping** | Q3AL/Q4AL cover and compacted-backfill sets are explicitly present in `V15_7_FOUNDATION_GEOLOGY_I`. |
| Right-bank curtain | **UNRESOLVED** | No curtain Part/Instance/Material/Element Set and no source-backed final parameters. |
| S02 local defect | **CHECK** | Whole wall exists; local segment subset is missing. |
| S03 permeability sweep | **CHECK** | Direct material-level sweep is possible only at the shared `P25_FANGSHENQIANG` scope. |
| S04 location sweep | **NOT READY** | Segment-level anti-seepage element sets are missing. |
| S05 random field | **NOT READY** | No element-level or field-dependent permeability assignment interface. |
| S06 rock anisotropy | **NOT READY** | Scalar permeability only, with several rock materials lacking permeability. |
| S07 integrated envelope | **NOT READY** | Depends on unresolved prerequisites above. |

Overall:

```text
CASE_PARAMETER_MAPPING = COMPLETE
MODEL_EXECUTION_READINESS = NOT_READY_FOR_S02_S07
MODEL_FILES_MODIFIED = NO
ABAQUS_RUN = NO
```
