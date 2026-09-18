# V15 Appurtenant Structure Rebuild — Codex Task

## Repository / branch safety

- Repository: `huleuu888-netizen/todo-list`
- Work **only** on branch `abaqus-audit-task`.
- **Do not modify `main`.**
- Preserve all existing v12, v13 and v14 outputs unchanged.
- Create a new version under `abaqus-audit/3d-v15/`.
- Use the current v14 core as the mechanical/hydraulic baseline unless a source-supported incompatibility is demonstrated.

## Why v15 is required

The retained v13/v14 core suppresses 31 appurtenant instances because restored groups reproduced rigid-body singularities without a verified mechanical support path. The current v14 therefore does **not** represent the full Duobu hub. In particular, the powerhouse, installation bay, tailwater channel, spillway and ecological release structures are not active in the retained assembly.

V15 must rebuild and restore these structures with source-supported geometry and real support/connectivity. Do **not** eliminate singularities with arbitrary node restraints, artificial Encastre constraints or unsupported blanket ties.

## Priority structures

Rebuild / verify in this order:

1. Powerhouse
   - `POWERHOUSE_UNIT_01_I`
   - `POWERHOUSE_UNIT_02_I`
   - `POWERHOUSE_UNIT_03_I`
   - `POWERHOUSE_UNIT_04_I`
2. Installation bay
   - `POWERHOUSE_INSTALLATION_BAY_I`
3. Tailwater channel
   - `TAILWATER_CHANNEL_I`
4. 8-bay spillway
   - spillway piers / right wall / left wall / chute / stilling basin components as required
5. 2-bay ecological release structure
   - `ECO_RELEASE_*`

If old Parts exist, first audit whether their coordinates, dimensions and elevations match the project source. Reuse only when defensible. Otherwise rebuild them.

## Project-source geometry that must be enforced or explicitly audited

### Powerhouse

- Riverbed-type powerhouse.
- Located between the left-bank release/spill structure and the left-bank concrete gravity sub-dam.
- Four bulb turbine-generator units.
- Main powerhouse total length: about **106.6 m**.
- Two unit blocks, two units per structural joint.
- Single unit-block length: about **35.1 m**.
- Streamwise foundation width: about **56.5 m**.
- Maximum dam height: about **47.3 m**.
- Maximum powerhouse structural height: about **51.3 m**.
- Powerhouse founding elevation: about **3029.70 m**.
- Tailrace tube bottom elevation: about **3036.90 m**.
- Intake bottom elevation: about **3035.70 m**.
- Turbine installation elevation: about **3041.0 m** for the selected bulb-unit scheme.

### Installation bay

- Located on the left side of the main powerhouse.
- Same streamwise width as the powerhouse.
- Length: about **34 m**.
- Floor elevation: **3062.00 m**.
- Same elevation as the tailwater platform.

### Tailwater channel

- Located directly downstream of the powerhouse.
- Width: about **71.6 m**.
- Channel bottom rises from **3036.90 m** at a **1:4 reverse slope** to **3053.00 m**.
- Downstream of elevation 3053.00 m, connect smoothly/horizontally to the natural riverbed.
- Concrete lining thickness: about **0.8 m**.
- Left side: concrete gravity retaining wall.
- Right side: spillway left guide wall.
- The resulting downstream exposed hydraulic boundary must be compatible with the v14 tailwater-head cases; do not retain a physically unrelated node strip solely because it existed in v13.

### Ecological release structure

- Two bays.
- Located between the powerhouse intake and the 8-bay spillway.
- Maximum discharge of one bay: about **192 m3/s**.
- Each bay is a low-level outlet with breast wall.
- Structure top length along dam axis: about **12.5 m**.
- Structure top width: about **16.0 m**.
- Maximum structure height: about **27.5 m**.
- Inlet bottom elevation: **3058.00 m**.
- Downstream energy dissipation shares the spillway stilling basin.

### Spillway

- Eight bays.
- Ecological release bays replace the former leftmost spillway bay arrangement; do not rebuild an obsolete 9-bay final layout.
- Spillway / ecological release downstream energy-dissipation system uses a common stilling basin.
- Stilling basin length: about **107 m**.
- Stilling basin slab top elevation: about **3047.50 m** in the design description.
- Downstream apron / protection must connect toward the natural riverbed.
- Spillway and powerhouse adjacency must match the final right-to-left hub ordering.

### Foundation / cutoff relation around powerhouse

- Powerhouse and installation-bay cutoff alignment lies around `坝左 0+081.00 m ~ 坝左 0+192.00 m`.
- Cutoff bottom elevation in this segment: **3011.00 m**.
- Transition to **3021.00 m** at both sides using approximately 1:1 slopes.
- Do not force the entire hub cutoff to one uniform bottom elevation.
- Powerhouse, spillway and adjacent concrete structures must have a real foundation/support load path into the geology/foundation mesh.

## Final hub ordering to preserve

From right bank to left bank, the final project arrangement is:

1. right-bank geomembrane impervious sand/gravel dam
2. 8-bay spillway
3. 2-bay ecological release structure
4. riverbed/bulb powerhouse
5. left-bank sub-dam including fishway

Do not swap powerhouse/spillway/release ordering to fit the legacy mesh.

## Required rebuild workflow

### Phase A — inventory and geometry audit

Before modifying geometry:

1. Inventory all legacy Parts and Instances related to the five priority structures.
2. For each Part/Instance, extract:
   - active/suppressed state
   - node count
   - element count
   - element type
   - X/Y/Z min/max
   - derived length/width/height
   - key bottom/top elevations
   - current section/material assignment
   - current interactions/ties/constraints
3. Compare measured values to the project-source targets above.
4. Classify each component:
   - `REUSE_AS_IS`
   - `REUSE_WITH_TRANSFORM`
   - `REBUILD_REQUIRED`
   - `INSUFFICIENT_SOURCE`

Do not silently accept legacy geometry.

### Phase B — rebuild geometry

For every `REBUILD_REQUIRED` component:

- build source-supported geometry at the correct global location;
- preserve actual streamwise and dam-axis orientation;
- provide smooth physical transitions between powerhouse, installation bay, tailwater channel, spillway, release structure, retaining walls and natural geology;
- avoid visual placeholder solids that merely resemble the structure;
- mesh with a defensible solid element family compatible with the retained baseline.

Simplifications are allowed only if documented as modeling equivalents and if they preserve:
- overall stiffness/load path,
- wetted boundaries,
- foundation contact area,
- hydraulic barrier/drainage role where relevant.

### Phase C — real support / connectivity

For each restored instance, explicitly identify its structural support path.

Acceptable paths include:
- shared conforming nodes with a compatible adjacent mesh;
- tied contact to a physically coincident foundation/adjacent concrete surface;
- mechanically valid contact where separation/sliding is intended;
- embedded or coupled relation only when physically justified.

Unacceptable fixes:
- isolated node restraints used only to stop rigid-body motion;
- blanket Encastre on appurtenant structure nodes;
- arbitrary springs;
- tie constraints across visible gaps;
- tying to the wrong geology layer solely because it is nearby.

For each connection report:
- master/slave or contact pair names;
- geometric gap/overclosure statistics;
- area/node participation;
- intended physical interpretation;
- whether pore-pressure continuity is intended or blocked.

### Phase D — incremental mechanical restoration

Restore one subsystem at a time:

1. powerhouse only
2. powerhouse + installation bay
3. + tailwater channel
4. + ecological release
5. + spillway

For each stage:
- Data Check
- S01
- S02
- inspect `.dat/.msg/.sta`
- record first singularity/zero pivot if any
- do not proceed to the next stage while the current stage has an unexplained rigid-body mode

A failure is diagnostic evidence; do not mask it.

### Phase E — hydraulic reintegration

Only after the complete restored structure passes S01/S02:

- rebuild upstream/downstream wetted surfaces using physical faces rather than inherited node strips;
- preserve v14 case heads:
  - S03 normal: upstream 3076.00 / downstream 3053.50
  - S04 design flood: upstream 3076.00 / downstream 3060.26
  - S05 check flood: upstream 3077.35 / downstream 3061.38
  - S06 drawdown/dead-water target: upstream 3074.00 / downstream 3053.50
  - S07 normal reservoir + 0.206g horizontal seismic: upstream 3076.00 / downstream 3053.50
- distinguish atmospheric seepage-face treatment from prescribed submerged hydrostatic pressure;
- verify no artificial bypass around cutoff, concrete structures or geomembrane;
- quantify interface POR continuity and boundary flux/mass balance.

## Required output files

Create at minimum:

- `abaqus-audit/3d-v15/V15_REBUILD_SCOPE.md`
- `abaqus-audit/3d-v15/V15_REBUILD_DIAGNOSIS.md`
- `abaqus-audit/3d-v15/V15_REBUILD_RESULT.md`
- `abaqus-audit/3d-v15/v15_instance_inventory.csv`
- `abaqus-audit/3d-v15/v15_geometry_audit.csv`
- `abaqus-audit/3d-v15/v15_support_path_audit.csv`
- `abaqus-audit/3d-v15/v15_contact_gap_audit.csv`
- `abaqus-audit/3d-v15/v15_validation_status.txt`
- final v15 `.inp`
- final v15 `.cae` if Abaqus/CAE is available in the environment
- Data Check `.dat/.msg/.sta`
- S01/S02 `.dat/.msg/.sta`
- hydraulic validation CSV/TXT outputs if S03-S07 are run

## Validation gates

### Gate 1 — geometry

PASS only if the priority structures exist as active instances and their key dimensions/elevations are demonstrably consistent with source design or clearly documented modeling equivalents.

### Gate 2 — support topology

PASS only if every restored structure has a verified physical load path to foundation/adjacent structures with no unsupported rigid body.

### Gate 3 — mechanical baseline

PASS only if Data Check, S01 and S02 complete without numerical singularity / zero pivot attributable to restored structures.

### Gate 4 — hydraulic boundary

PASS only if the actual wetted boundaries for the powerhouse/tailwater/spillway/release system are physically identified and per-case heads are applied to the correct faces.

### Gate 5 — hydraulic physical validation

PASS only if:
- required hydraulic cases complete,
- POR continuity is quantitatively checked where continuity is intended,
- Qin/Qout are reproducibly integrated,
- mass-balance error is reported,
- no unexplained cutoff/geomembrane/concrete bypass exists.

## Status rules

Set `VALIDATED=YES` only when all intended v15 gates actually pass.

If Abaqus execution is externally terminated by timeout/SIGTERM/SIGINT, report that as external termination and do not reinterpret it as model nonconvergence.

If geometry evidence is insufficient for an exact detail, mark it `UNRESOLVED` rather than inventing a dimension.

## Deliverable summary in final commit

At completion, provide:
- final commit SHA;
- exact list of restored active instances;
- exact list of rebuilt vs reused Parts;
- PASS/FAIL/UNRESOLVED for each gate;
- first remaining blocking error, if any;
- confirmation that v12/v13/v14 and `main` were not modified.
