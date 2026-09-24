# Right-Bank Curtain Parameter Closure Report

PARAMETER_CLOSURE_STATUS = UNRESOLVED

## 1. Scope and evidence boundary

This is a read-only parameter-closure audit for the current S01 baseline on
branch `abaqus-audit-task`. It does not modify the input deck or CAE model,
does not create a Part, and does not run Abaqus.

- Current branch baseline commit: `baf7c41bd6c6a2a934934cbfc012ea07bfdb72d7`
- S01 model input audited:
  `abaqus-audit/3d-v15.24/S01/v15_24_S01_BASELINE.inp`
- V15.26 baseline summary:
  `abaqus-audit/3d-v15.26/S01_ENGINEERING_BASELINE_SUMMARY.md`
- Existing design-correspondence audit:
  `abaqus-audit/study-design/S01_FINAL_DESIGN_CORRESPONDENCE_AUDIT.md`

The requested file `right_bank_curtain_modification_plan_v1.md` is not present
in the current branch working tree or reachable Git history. It therefore
cannot be treated as an engineering source in this closure. The report uses
the existing V15.13-V15.20 evidence package and the S01 input itself, and
keeps every unsupported parameter unresolved.

## 2. Parameter-source classification

### A. Engineering-data parameters currently available

The only explicit extent statement found in the current evidence is in
`abaqus-audit/3d-v15.13/v15_13_right_bank_curtain_resolution.csv`:

> approximately 100 m downstream/right-bank curtain stated in source audit

That record explicitly says that the global axis, thickness, and equivalent
hydraulic coefficient are not defensible, and its status is `UNRESOLVED`.
This is retained as an approximate design intent, not frozen as a geometric
endpoint.

The V15.20 closure records define the hydraulic role as a right-bank
seepage-control curtain or an approved equivalent low-permeability region,
but they do not provide coordinates, depth, thickness, or permeability. The
selected V15.20 treatment is `SENSITIVITY_ANALYSIS_VARIABLE`; no curtain was
entered into the baseline deck.

### B. Parameters and objects already present in the S01 model

The model contains a unified foundation-geology Part and a right-bank
assembly partition. It does not contain a curtain object.

| Model item | Current value/evidence | Closure meaning |
|---|---|---|
| Foundation geology Part | `V15_7_FOUNDATION_GEOLOGY` | Present |
| Foundation geology Instance | `V15_7_FOUNDATION_GEOLOGY_I` | Present; no instance transform recorded |
| Right-bank aggregate element set | `GEO_RIGHT_ALL` / `ASSEM_GEO_RIGHT_ALL` | Present |
| Right-bank geology bounding box | min `(-600.0, 445.0, 2600.0)`; max `(900.0, 850.0, 3426.4)`; span `(1500.0, 405.0, 826.4)` | Candidate host domain only; not a curtain |
| Main cutoff wall | Part `V15_5_REFINED_P25_SOLID_CUTOFF_WALL_F13_1`; Instance `P25_SOLID_CUTOFF_WALL_F13-1`; Set `V15_5_ALL`; Material `P25_FANGSHENQIANG` | Existing anti-seepage object |
| Main wall bounding box | min `(-36.0, 150.000038, 3021.0)`; max `(-35.0, 445.000039, 3073.51)` | Its downstream/right-side edge is near `y = 445 m` |
| Candidate geology interface | Right-bank geology minimum `y = 445.0 m` | Geometric candidate only; not source-backed curtain alignment |
| Wall-to-right-geology shared nodes | `0` in the audited S01 input | Current interface is not proven conformal |

The near-contact at `y ≈ 445 m` is not sufficient to infer the curtain start
point. The coordinate system, curtain axis, and engineering tie-in must come
from a verified design source.

## 3. Right-bank geology material partitions

The following right-bank regions exist in the current geology Part. The
material assignments are model mappings, not approved curtain parameters.

| Element set | Assembly set | Elements | Material | Current hydraulic definition | Bounding box in current Assembly coordinates |
|---|---|---:|---|---|---|
| `GEO_RIGHT_Q4_COLLUVIAL` | `ASSEM_GEO_RIGHT_Q4_COLLUVIAL` | 1,848 | `Q4DEL` | density `1.8`; permeability `2.33e-05` | min `(-600,445,3074.9)`; max `(900,850,3426.4)` |
| `GEO_RIGHT_R04_Q3AL_V` | `ASSEM_GEO_RIGHT_R04_Q3AL_V` | 3,696 | `Q3AL_V` | density `1.8`; permeability `4.46e-06` | min `(-600,445,3059.4)`; max `(900,850,3423.4)` |
| `GEO_RIGHT_HIGH_TERRACE_COVER` | `ASSEM_GEO_RIGHT_HIGH_TERRACE_COVER` | 392 | `Q3AL_V` | density `1.8`; permeability `4.46e-06` | min `(-600,615,3271.73)`; max `(900,790,3398.2)` |
| `GEO_RIGHT_ROCK_STRONG_UNLOADED` | `ASSEM_GEO_RIGHT_ROCK_STRONG_UNLOADED` | 7,392 | `ROCK_STRONG_UNLOADED` | density `2.45`; no `*Permeability` entry | min `(-600,445,3029.4)`; max `(900,850,3376.4)` |
| `GEO_RIGHT_ROCK_WEAK_UNLOADED` | `ASSEM_GEO_RIGHT_ROCK_WEAK_UNLOADED` | 3,816 | `ROCK_WEAK_UNLOADED` | density `2.55`; no `*Permeability` entry | min `(-600,445,3014.4)`; max `(900,850,3346.4)` |
| `GEO_RIGHT_ROCK_DEEP_UNLOADED` | `ASSEM_GEO_RIGHT_ROCK_DEEP_UNLOADED` | 26,112 | `ROCK_DEEP_UNLOADED` | density `2.62`; no `*Permeability` entry | min `(-600,445,2884.4)`; max `(900,850,3331.4)` |
| `GEO_RIGHT_FRESH_GRANITE` | `ASSEM_GEO_RIGHT_FRESH_GRANITE` | 25,872 | `FRESH_GRANITE` | density `2.68`; no `*Permeability` entry | min `(-600,445,2600.0)`; max `(900,850,3201.4)` |

The aggregate `GEO_RIGHT_ALL` contains 69,128 elements and 74,674 unique
nodes in the audited input. The absence of a permeability definition for the
rock materials is a separate unresolved material issue; it cannot be repaired
by assigning a guessed curtain value.

## 4. Required curtain parameter closure

| Required parameter | Engineering-data status | Model status | Closure result |
|---|---|---|---|
| Start position | No verified Assembly coordinate or design reference | Candidate host interface is near `y = 445 m` | `UNRESOLVED` |
| End position | No verified inland endpoint | No curtain geometry from which to measure an endpoint | `UNRESOLVED` |
| Extension length | Approximate `100 m` appears in the V15.13 source audit | No curtain set or geometry exists | `CHECK_ONLY`, not frozen |
| Curtain axis/direction | Not supplied | Cannot infer from the right-bank geology bounding box | `UNRESOLVED` |
| Depth range | No top/bottom elevation or drilling depth supplied | No curtain elements exist | `UNRESOLVED` |
| Bottom elevation | Not supplied | Existing rock bottom is not a curtain bottom | `UNRESOLVED` |
| Thickness or equivalent-zone width | Not supplied | No curtain Part or partition exists | `UNRESOLVED` |
| Connection to existing cutoff | No verified tie-in coordinates supplied | Main-wall/right-geology shared-node count is `0` | `UNRESOLVED` |
| Contact with right-bank rock | Geological host domain is present | No dedicated curtain-rock interface exists | `UNRESOLVED` |
| Curtain material | No source-backed material specification | No curtain material exists | `UNRESOLVED` |
| Curtain permeability | No approved value or range; Lu-to-k conversion prohibited | Existing rock k is also absent for the rock materials | `UNRESOLVED` |

## 5. Explicit new objects required in a future authorized model change

The following names are reserved as the requested future modeling objects;
none of them exists in the current S01 input and none was created in this
audit.

| Object type | Required name | Current presence | Required closure before creation |
|---|---|---|---|
| Part | `Right_Bank_Curtain` | `MISSING` | Approved Assembly-coordinate geometry, depth, thickness/equivalent width, and interface surfaces |
| Material | `Right_Bank_Curtain_Material` | `MISSING` | Source-backed grout/curtain hydraulic role, density if needed, permeability value or bounded range, units, and acceptance basis |
| Element Set | `Right_Bank_Curtain_SET` | `MISSING` | Element labels after local mesh generation and verified membership |
| Instance | `Right_Bank_Curtain_I` (recommended future name) | `MISSING` | Approved Part placement and transformation |

The future Part must be a seepage-domain object, not a structural restraint.
Its interface with the right-bank geology and existing anti-seepage chain
should be conformal/shared-node geometry where feasible. An unsupported Tie,
fixed-node condition, spring, or Encastre must not be used to conceal a
geometric or hydraulic gap.

## 6. Recommended modeling方案 after data completion

1. Obtain the missing source-backed plan or survey package and express the
   curtain start, endpoint, axis, top, and bottom in the same global Assembly
   coordinate system as the S01 input.
2. Confirm whether the stated `100 m` is measured along the curtain axis,
   along a bank normal, or along another engineering reference. Do not map it
   to an arbitrary global x/y span.
3. Define the curtain depth and bottom elevation from the design or drilling
   record. Do not use the bottom of `GEO_RIGHT_ALL` as a substitute.
4. Create `Right_Bank_Curtain` only after the geometry is approved. Place its
   start at the verified cutoff/geomembrane transition and extend it into the
   verified right-bank rock domain with a source-backed thickness or approved
   equivalent-zone width.
5. Assign `Right_Bank_Curtain_Material` only after the grout specification
   and permeability basis are supplied. Keep lower/central/upper values as a
   documented sensitivity range if the engineering source provides a range.
6. Generate `Right_Bank_Curtain_SET`, locally remesh the affected region, and
   verify positive element volume, duplicate elements, nonconforming faces,
   hanging nodes, and shared-node/interface continuity.
7. Re-run the correspondence and parameter audits before authorizing a new
   input deck or any S02-S07 case. Preserve the existing S01 baseline as an
   immutable comparison case.

## 7. Data still required

- The missing `right_bank_curtain_modification_plan_v1.md`, or the original
  design drawing/survey it represents.
- Global Assembly coordinates for the start and end points and the curtain
  axis definition.
- Curtain top and bottom elevations, effective depth, thickness, and/or
  equivalent-zone width.
- Verified connection coordinates to the main cutoff/geomembrane and the
  right-bank rock interface.
- Grout or curtain material specification, permeability units, measured or
  accepted range, and source/quality-control basis.
- Rock hydraulic parameters or an approved calibration plan for the affected
  `ROCK_*` and `FRESH_GRANITE` regions.
- Mesh/interface acceptance criteria for the new local domain.

## 8. Risks and decision

The principal risks are an incorrect interpretation of the 100 m direction,
an unsupported depth or thickness assumption, a nonconformal interface at the
current `y ≈ 445 m` candidate boundary, and assigning a guessed permeability
to either the curtain or the rock. Any of these would change the S01 hydraulic
baseline rather than simply close a documentation gap.

Decision:

```text
RIGHT_BANK_CURTAIN_PARAMETER_CLOSURE = UNRESOLVED
RIGHT_BANK_CURTAIN_GEOMETRY = NOT_CREATED
RIGHT_BANK_CURTAIN_MATERIAL = NOT_CREATED
RIGHT_BANK_CURTAIN_SET = NOT_CREATED
ABAQUS_RUN = NOT_PERFORMED
MODEL_MODIFICATION = NOT_PERFORMED
```

The current model is suitable for documenting the missing parameter package,
but it is not ready for an authorized right-bank curtain implementation until
the listed source data are supplied and verified.
