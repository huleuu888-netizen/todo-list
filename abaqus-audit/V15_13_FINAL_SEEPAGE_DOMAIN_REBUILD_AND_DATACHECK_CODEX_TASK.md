# V15.13 final seepage-domain rebuild + conditional Data Check task

## Purpose

This task is intentionally stricter than all previous geometry/audit tasks.

The repeated revisions through V15.12 show that the model is now broadly usable geometrically, but several critical seepage-system facts remain inconsistent or only partially verified. V15.13 must therefore use a **fail-fast, source-first, geometry-evidence-first workflow**.

The goal is NOT to create another superficially "PASS" version.

The goal is to produce one model that is either:

1. **READY_FOR_DATACHECK** with all critical geometry/topology gates satisfied; or
2. **STOPPED_UNRESOLVED** with the baseline preserved and exact reasons documented.

Do not silently "repair" uncertain geometry.

---

# 0. Baseline, branch, safety

Continue from:

`9945d797646a7fa626487279b3353612973eeb59`

Use V15.12 as the audit baseline, but **do not automatically carry forward the V15.12 added left-bank cutoff wall** because its global placement is inconsistent with the left-bank structure chain.

Work only on:

`abaqus-audit-task`

Do not modify:

`main`

Create all outputs under:

`abaqus-audit/3d-v15.13/`

Do not overwrite V15.12.

Do not force-push.

Do not run S01-S07.

Abaqus Data Check is allowed only at the end of this task and only if every geometry/topology acceptance gate below is satisfied.

---

# 1. Authoritative coordinate convention

Use the current proven model convention:

- X = streamwise direction;
- Y = dam-axis / left-right hub direction;
- Z = elevation.

The active Assembly order in V15.12 proves that increasing Y moves from the left-bank structures toward the right-bank/main-dam side.

Current verified structural Y ranges:

- left-bank sub-dam: `Y=-245.700 .. -156.000 m`;
- installation bay: `Y=-156.000 .. -122.000 m`;
- powerhouse: `Y=-122.000 .. -15.400 m`;
- ecological-release structure: `Y=-15.400 .. -2.900 m`;
- spillway structural frontage: approximately `Y=-2.900 .. 93.600 m`;
- current main sand/gravel dam P25 system begins near `Y=150.000 m` and continues to about `Y=445.000 m`.

Therefore:

- "向左岸延伸" must move toward **more negative Y**;
- a wall segment at `Y=70..150` cannot represent an 80 m extension toward the left bank from the left-sub-dam.

This directional rule is mandatory.

---

# 2. Source facts that shall govern the rebuild

Use the project report as the governing source.

## 2.1 Final hub order

Final right-to-left order is:

`right-bank geomembrane sand/gravel dam -> 8-bay spillway -> 2-bay ecological release -> powerhouse -> left-bank sub-dam including fishway`

The model's increasing-Y direction is the reverse of the above textual right-to-left order, i.e. from left-bank sub-dam toward main/right-bank dam.

## 2.2 Anti-seepage system

The source explicitly states:

- foundation anti-seepage uses a vertical cutoff-wall system;
- wall thickness = **1.0 m**;
- main riverbed sand/gravel-dam wall bottom = **3021.00 m**;
- powerhouse/installation segment contains a deeper portion with bottom **3011.00 m** over the documented central reach;
- both sides transition approximately **1:1** back to **3021.00 m**;
- left-sub-dam cutoff bottom = **3021.00 m**;
- left-sub-dam cutoff is on the same anti-seepage alignment as the left-side structures;
- left-bank cutoff continues approximately **80 m toward the left abutment**;
- main riverbed cutoff connects to the upper composite geomembrane;
- spillway cutoff connects through a connecting plate and changes alignment near the right retaining wall;
- right-bank cutoff connects to a grout curtain;
- powerhouse, installation bay, spillway, ecological release and left sub-dam are part of one anti-seepage system.

## 2.3 Left-sub-dam cutoff source discrepancy

Two report passages use different upstream-offset station descriptions for the left-sub-dam cutoff:

- one passage gives approximately `坝上 0-009.50 m`;
- another detailed left-sub-dam passage gives approximately `坝上 0-014.50 m`.

Do not silently select one.

Record:

`LEFT_SUBDAM_CUTOFF_AXIS_SOURCE_DISCREPANCY = 5.0 m`

Then resolve the model X location using actual structural geometry, adjacent installation/powerhouse cutoff evidence, and source drawings/section context.

If the exact X location cannot be uniquely established, keep the X coordinate unresolved and do not invent a wall axis.

---

# 3. Mandatory Phase A — rebuild a single trusted global-coordinate map BEFORE changing geometry

Create:

`v15_13_global_coordinate_basis.csv`

For every critical structure include:

- instance;
- source physical name;
- true Assembly bbox from INP/CAE transform;
- X upstream/downstream extent;
- Y left/right extent;
- Z extent;
- source design length/width/elevation;
- coordinate interpretation;
- confidence: VERIFIED / DERIVED / UNRESOLVED.

Critical structures:

- left-bank sub-dam;
- installation bay;
- powerhouse units;
- ecological release;
- spillway left/right abutments;
- spillway piers/openings;
- right-side spillway-to-main-dam retaining-wall region;
- main sand/gravel dam;
- geomembrane;
- existing P25 cutoff wall;
- left-bank engineered backfill;
- foundation geology.

Also create:

`v15_13_dam_axis_chain.csv`

Required ordered Y chain:

1. left-bank outer region;
2. left-bank sub-dam;
3. installation bay;
4. powerhouse;
5. ecological release;
6. spillway;
7. spillway-to-main-dam transition / retaining-wall region;
8. sand/gravel main dam;
9. right-bank abutment / grout-curtain region.

For each adjacent pair report:

- end Y of first;
- start Y of second;
- actual gap;
- whether source expects a structure in the gap;
- status.

### Hard gate A

Do not modify any cutoff-wall geometry until this chain is produced and the left/right direction is internally consistent.

---

# 4. Remove or quarantine the incorrect V15.12 left-bank wall

The V15.12 added instance:

`V15_12_LEFT_BANK_CUTOFF_WALL_I`

has global Y approximately:

`70 .. 150 m`

This cannot represent an 80 m extension toward the left bank from a left-sub-dam located at:

`Y=-245.7 .. -156 m`

Therefore V15.13 must NOT preserve it as a valid left-bank cutoff wall.

Required treatment:

- remove it from the V15.13 active Assembly; or
- suppress/quarantine it as `OBSOLETE_V15_12_MISPLACED_LEFT_CUTOFF` if provenance must be retained.

Do not reclassify it as correct merely because it touches the P25 wall.

Do not repurpose it as another structure unless independent source evidence proves that its exact geometry corresponds to a documented right-side transition.

Create:

`v15_13_v15_12_cutoff_disposition.csv`

with reason and final status.

---

# 5. Reconstruct the anti-seepage chain by physical structure, not by name

Create a continuous chain model from left bank to right bank.

The chain must be divided into physical segments:

## Segment A — left-bank abutment extension

- must extend approximately **80 m toward more negative Y** beyond the left-side end of the left-sub-dam cutoff;
- wall bottom approximately **3021.00 m**;
- thickness **1.0 m**;
- exact X axis must match the resolved left-sub-dam cutoff axis.

If the left-sub-dam outer end remains `Y=-245.7 m`, the nominal outer extension endpoint should be near:

`Y=-325.7 m`

This is only a chainage consequence of the current verified Y axis and 80 m source length; verify against surrounding geology/domain boundaries before finalizing.

## Segment B — left-sub-dam cutoff

- must span the actual left-sub-dam dam-axis region;
- Y coverage should correspond to the left-sub-dam length, currently approximately `-245.7 .. -156.0 m`;
- bottom **3021.00 m**;
- thickness **1.0 m**;
- connect to the left-bank extension;
- connect to the installation/powerhouse anti-seepage system through the source-supported connection logic.

## Segment C — installation-bay / powerhouse cutoff

- must cover the installation and powerhouse anti-seepage reach;
- use source-documented wall alignment;
- central deeper reach bottom = **3011.00 m** where applicable;
- transition about **1:1** to bottom **3021.00 m** at both sides;
- do not force the entire segment to 3011 m;
- do not force the entire segment to 3021 m.

The source deep-wall station range shall be preserved in a source-coordinate table and mapped to model Y only after anchor reconciliation.

## Segment D — ecological-release connection

- ecological-release structure is directly between powerhouse and spillway;
- anti-seepage continuity must cross this 12.5 m dam-axis reach;
- if the source treats the wall as a continuation/connection plate under the structure rather than a separately named wall part, represent it accordingly;
- do not invent a separate wall instance merely to satisfy naming.

## Segment E — spillway cutoff

- span the 8-bay spillway reach;
- bottom **3021.00 m** unless source explicitly gives another local value;
- use actual spillway upstream/foundation geometry;
- connect to the right retaining-wall/transition zone.

## Segment F — spillway-to-main-dam transition / retaining-wall region

Current active structures leave approximately:

`Y=93.6 .. 150.0 m`

between spillway and P25/main-dam system.

The source explicitly states that gravity retaining walls exist between the spillway and sand/gravel dam.

Do not leave this interval as an unexplained empty transition.

Required:

- search the report/drawings/repository for the actual retaining-wall geometry;
- if an active retaining-wall part exists under a non-obvious name, identify it;
- if missing and source dimensions are sufficient, add the required structural transition;
- if source dimensions are insufficient, do not invent the full retaining wall; create only the anti-seepage connection geometry that is explicitly supported and mark structural-wall geometry unresolved.

The cutoff line may bend/turn in this transition according to the source.

## Segment G — main riverbed cutoff

Retain the validated P25 wall only if its actual global position remains correct.

Current active P25 global range is approximately:

- X=-36..-35;
- Y=150..445;
- Z bottom 3021.

This segment:

- thickness 1.0 m;
- bottom 3021.00 m;
- connects upward to geomembrane where documented.

## Segment H — geomembrane connection

Keep source-supported physical connection between:

- main cutoff;
- upper composite geomembrane.

Actual edge/face relation must be audited.

## Segment I — right-bank grout curtain

The source states:

- cutoff/grout system continues into the right abutment;
- dam-right 0+244.37 to 0+295.00 includes curtain connection beneath the wall;
- curtain extends approximately **100 m into the right bank**;
- curtain bottom is tied to the main-wall bottom level around **3021.00 m**.

Do not invent a solid curtain thickness if the source does not define one.

If the current model does not explicitly represent the curtain:

- create a dedicated source-status record;
- do not claim full left-to-right seepage-chain closure until the numerical representation of the curtain is defined.

If an equivalent low-permeability grout-zone representation already exists, identify and audit it.

---

# 6. Build a station-to-model coordinate reconciliation table

Create:

`v15_13_source_station_to_model_map.csv`

For every source station or line used to place a cutoff segment include:

- source station notation;
- source structure;
- source upstream/downstream offset;
- mapped model structure;
- mapped X;
- mapped Y range;
- anchor evidence;
- residual/error;
- confidence.

At minimum include:

- main riverbed cutoff axis;
- powerhouse/installation cutoff axis;
- deeper powerhouse/installation wall reach;
- left-sub-dam cutoff axis;
- spillway/right-retaining-wall bend;
- right-bank curtain start/end.

### Hard gate B

A cutoff segment may only be created when its placement is supported by:

- at least one explicit source station/offset AND
- one actual neighboring structure/face anchor.

If these two forms of evidence disagree by more than the chosen tolerance, status must be UNRESOLVED and geometry creation must stop for that segment.

---

# 7. Do not use one straight X line for the whole system unless proven

The source gives different upstream offsets for different structural regions and explicitly states that the spillway wall changes direction near the right retaining wall.

Therefore:

- left-sub-dam / powerhouse / installation may share one local alignment;
- spillway / main riverbed wall may use another;
- a transition/connecting plate may be required between alignments.

Do not set every wall to `X=-35.5 m` merely because the main P25 wall is there.

Do not set every wall to the left-sub-dam upstream face either.

Create:

`v15_13_cutoff_alignment_segments.csv`

with one row per straight/transition segment.

---

# 8. Rebuild the left-bank engineered backfill as a conformal seepage region

V15.12 real-face audit found the backfill/geology interface to be geometrically coincident but not node-shared, with a substantial hanging-node count.

This is not acceptable for a single continuous pore-pressure domain if no Tie/pore-pressure constraint is being used.

Preferred final organization:

- integrate the engineered compacted sand/gravel cells into the **same foundation analysis mesh/Part** as the natural geology, while preserving a distinct element set and Section/material identity;
- reuse existing natural-geology interface nodes wherever possible;
- locally remesh only the affected zone.

Keep an explicit set such as:

`FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL`

and corresponding Assembly-level set.

Do NOT lose material identity merely because it is moved into the same mesh part.

If same-part integration is technically impossible, an alternative may be used only if it produces mathematically continuous pore-pressure transfer and is explicitly documented.

Do not add Tie in this task merely to hide a nonconforming seepage mesh.

---

# 9. Backfill material treatment

Current temporary mapping:

`Q3AL_III`

shall remain provisional unless the source explicitly validates it for the left-sub-dam/installation backfill.

The report does support compacted sand/gravel backfill in this structural area, but exact calibrated constitutive and seepage parameters must not be inferred from a different foundation-treatment section without evidence.

Create:

`v15_13_backfill_material_final_basis.csv`

Fields:

- region;
- source description;
- candidate material;
- density;
- elastic parameters;
- permeability;
- porosity/void ratio;
- relative density requirement if available;
- source location;
- status.

Allowed final status:

- VERIFIED_SOURCE_MAPPING;
- ENGINEERING_EQUIVALENT_ASSUMPTION;
- UNRESOLVED.

If not VERIFIED, do not describe it as final calibrated material.

---

# 10. Recompute whole-foundation topology from actual coordinates

This time the topology audit must use exact node coordinates and actual face geometry, not only same-element connectivity.

Recompute separately for:

1. natural geology;
2. natural geology + engineered backfill;
3. full seepage foundation domain.

Report:

- external boundary faces;
- exact shared internal faces;
- coordinate-coincident non-shared faces;
- nonconforming internal faces;
- hanging nodes;
- duplicate nodes;
- duplicate elements;
- nonmanifold faces;
- connected components;
- connected components per material/leaf set;
- unintended disconnected same-material components.

Create:

`v15_13_foundation_topology_final.csv`

and:

`v15_13_foundation_component_resolution.csv`.

### Hard acceptance

For interfaces intended to be one continuous seepage domain:

- hanging nodes = 0;
- nonconforming internal faces = 0;
- coordinate-coincident-but-not-shared interface nodes = 0;
- duplicate elements = 0;
- nonmanifold faces = 0.

Do not mark PASS if any of the above are nonzero.

---

# 11. Resolve the current 5 natural-geology components

V15.12 reports 5 natural-geology connected components.

Do not automatically merge them.

For each component determine:

- spatial bbox;
- contained geology leaf sets;
- material identity;
- whether separation corresponds to a real geology-domain boundary;
- whether the two sides physically touch;
- whether they should transmit seepage.

Create:

`v15_13_geology_component_diagnosis.csv`

Classification must be one of:

- INTENDED_SEPARATE_DOMAIN;
- SAME_DOMAIN_MESH_DISCONNECT;
- DIFFERENT_MATERIAL_CONFORMAL_INTERFACE;
- DOMAIN_BOUNDARY;
- UNRESOLVED.

Any `SAME_DOMAIN_MESH_DISCONNECT` must be repaired locally before acceptance.

---

# 12. Replace the current Part-level pore-pressure audit with a Section/Set-level audit

The V15.12 pore-pressure audit is insufficient because the foundation geology Part contains many Section/material regions, while the audit can collapse them into a single Part-level material label.

V15.13 must audit by:

- Part;
- Element Set;
- Section Assignment;
- Material;
- element type.

Create:

`v15_13_section_level_pore_pressure_audit.csv`

For every one of the actual geological leaf sets report:

- leaf set;
- section;
- material;
- element types;
- element count;
- permeability present;
- pore-pressure DOF present;
- intended seepage role;
- final action;
- status.

Use the actual set names in the model.

Do not invent geology units.

---

# 13. Decide C3D8P/C3D8R conversion region-by-region

Current foundation geology includes a large population of C3D8R elements.

Do not globally convert all C3D8R.

For each geological Section/leaf set:

## Convert structural-only solid -> pore-pressure solid ONLY IF:

- the region is physically part of the groundwater/seepage domain; and
- a valid permeability definition exists or is explicitly source-supported; and
- the topology can remain unchanged.

Preferred direct formulation replacements when geometry/connectivity are unchanged:

- C3D8R -> C3D8P;
- C3D6R -> C3D6P;
- corresponding pore-pressure formulation for any other supported continuum element.

Do not change node coordinates or connectivity merely to change element formulation.

## Keep structural-only if:

- the region is intentionally outside the seepage domain; or
- it represents structural concrete; or
- seepage exclusion is explicitly justified.

## Leave UNRESOLVED if:

- the region should conduct groundwater but lacks a defensible permeability/material definition.

Create:

`v15_13_element_formulation_changes.csv`.

Every changed element set must be listed explicitly.

---

# 14. Verify the dam-fill seepage domain

Re-audit the P25 dam materials by element set/section.

Confirm:

- gravel dam shell;
- upstream gravel fill;
- main rockfill;
- filter;
- drainage body;
- impermeable fill;
- cutoff;
- geomembrane representation.

Check:

- element type;
- permeability;
- pore-pressure DOF;
- intended hydraulic role.

Do not label drainage/filter zones "structural-only" if they are actually intended to carry seepage.

Correct only the audit classification unless the model formulation itself is wrong.

Create:

`v15_13_dam_hydraulic_role_audit.csv`.

---

# 15. Validate cutoff-wall and geomembrane geometry using real faces

For every adjacent anti-seepage segment:

- actual minimum gap;
- actual contact/coincident edge/face length;
- shared/coincident nodes;
- top mismatch;
- bottom mismatch;
- wall-thickness mismatch;
- unintended overlap volume.

Create:

`v15_13_cutoff_connection_final.csv`.

Critical transitions:

- left-bank extension -> left-sub-dam cutoff;
- left-sub-dam -> installation cutoff;
- installation -> powerhouse cutoff;
- powerhouse -> ecological-release connection;
- ecological release -> spillway cutoff;
- spillway -> right retaining-wall transition;
- right retaining-wall transition -> main P25 cutoff;
- main cutoff -> geomembrane;
- main cutoff -> right-bank curtain representation.

No transition may be marked PASS solely from endpoint/bbox equality.

---

# 16. Revalidate major structural interfaces but do not require shared nodes for structural joints

Structural joints are different from continuous seepage-media interfaces.

For:

- sub-dam / installation bay;
- installation bay / powerhouse;
- powerhouse / ecological release;
- ecological release / spillway;

report geometric contact but do NOT force shared nodes if a real structural joint is intended.

Status categories:

- GEOMETRIC_JOINT_READY_FOR_INTERACTION;
- CONTINUOUS_MESH;
- GAP_ERROR;
- OVERLAP_ERROR;
- UNRESOLVED.

Do not call hanging nodes across an intended structural joint a seepage-mesh failure unless pore-pressure continuity is actually required there.

Create:

`v15_13_structural_joint_audit.csv`.

---

# 17. Right-side spillway-to-main-dam transition must be explicitly resolved

Current model coordinates show a substantial dam-axis interval between the spillway and the P25 main dam.

This interval must not remain unnamed.

Create:

`v15_13_spillway_main_dam_transition_resolution.csv`

Determine whether the interval contains:

- source-documented gravity retaining wall;
- cutoff-wall bend/transition;
- dam fill;
- construction-stage geometry that was omitted;
- or a genuine modeling gap.

If the gravity retaining wall is missing:

- search source geometry first;
- add it only when dimensions are defensible;
- otherwise preserve an explicit UNRESOLVED structural-wall item while still avoiding an unsupported artificial solid.

The anti-seepage connection itself must not remain as an unexplained 56 m-class gap.

---

# 18. Preserve already-correct geometry

Unless a conflict is proven, freeze:

- 4 powerhouse units;
- installation bay Y length = 34 m;
- installation-bay floor elevation = 3062 m;
- left-sub-dam Y extent and 89.70 m total length;
- fishway station-refitted route around 1407.57 m;
- sediment-flushing outlets;
- 2 ecological-release openings;
- 8 spillway openings;
- 109 m combined flood-release frontage;
- tailwater;
- stilling basin;
- sediment outlet corrections.

Do not start another general geometry redesign.

---

# 19. Mesh policy

No global remesh.

Only local mesh changes are allowed for:

- corrected anti-seepage segments;
- spillway/main-dam transition if source-supported geometry is added;
- backfill/geology conformal integration;
- local geology repair of proven same-domain disconnects;
- direct element-formulation conversion that preserves existing connectivity.

Create:

`v15_13_mesh_change_audit.csv`

For each changed region report:

- old nodes/elements;
- new nodes/elements;
- coordinates changed YES/NO;
- connectivity changed YES/NO;
- element type changed;
- reason;
- source basis;
- quality before/after.

---

# 20. Mesh-quality acceptance

For every changed local region report:

- min edge;
- median edge;
- P95 edge;
- max edge;
- max aspect ratio;
- invalid/negative volume count;
- collapsed element count;
- duplicate element count.

Create:

`v15_13_local_mesh_quality.csv`.

No invalid/negative volume or collapsed element is acceptable.

---

# 21. Automated assertions — task must fail rather than produce false PASS

The build/audit script must contain explicit assertions or fail conditions.

At minimum:

- no active instance named `V15_12_LEFT_BANK_CUTOFF_WALL_I` unless proven reclassified;
- no continuous seepage-media interface with hanging nodes > 0;
- no continuous seepage-media interface with nonconforming faces > 0;
- no unsupported sub-dam base area > tolerance;
- no anti-seepage chain segment with an unexplained physical gap;
- no geological leaf set omitted from the Section-level pore-pressure audit;
- no changed element formulation without a listed source/engineering basis;
- no Data Check run if any CRITICAL gate is unresolved.

A script failure is preferable to a misleading PASS.

---

# 22. Required visual review

Export real Abaqus/CAE screenshots, not synthetic plots.

Required views:

1. full hub plan with global axes;
2. dam-axis chain with labels;
3. left bank: outer extension + sub-dam + installation + powerhouse;
4. left-sub-dam cutoff alignment in plan;
5. installation/powerhouse cutoff alignment;
6. deeper 3011 m cutoff reach in elevation/section;
7. ecological-release/spillway cutoff continuity;
8. spillway/right-retaining-wall/main-dam transition;
9. main cutoff + geomembrane connection;
10. right-bank curtain endpoint/representation;
11. backfill/geology conformal mesh;
12. geology component display groups;
13. geological Section/material display groups;
14. pore-pressure-capable vs structural-only element display groups;
15. full final seepage-domain overview.

---

# 23. Pre-Data-Check acceptance gate

Create:

`v15_13_pre_datacheck_gate.csv`

Mandatory rows:

- global coordinate chain resolved;
- V15.12 misplaced wall removed/quarantined;
- left-bank extension direction correct;
- left-sub-dam cutoff resolved;
- installation/powerhouse cutoff resolved;
- ecological-release connection resolved;
- spillway cutoff resolved;
- spillway-main-dam transition resolved;
- main cutoff/geomembrane connection resolved;
- right-bank curtain representation resolved or explicitly excluded with justified boundary treatment;
- backfill-geology hanging nodes = 0;
- continuous foundation nonconforming faces = 0;
- same-domain disconnects = 0;
- Section-level pore-pressure audit complete;
- intended seepage regions use pore-pressure-capable elements or are explicitly unresolved;
- no invalid/collapsed elements;
- model has material/section assignment for every active continuum element.

Status:

- PASS;
- FAIL;
- UNRESOLVED.

### Hard gate C

Run Data Check only if every critical row is PASS.

If any critical row is FAIL/UNRESOLVED:

- do not run Data Check;
- do not claim readiness;
- finish with `STOPPED_UNRESOLVED`.

---

# 24. Conditional Abaqus Data Check

Only if Hard Gate C passes:

Create a Data Check job based on the final V15.13 model.

Do not run a full analysis.

Capture:

- .dat;
- .msg;
- .sta;
- job input deck;
- Data Check status.

Search for at least:

- ERROR;
- WARNING;
- zero/negative volume;
- excessive distortion;
- disconnected/unconnected region;
- missing material;
- missing section;
- missing surface/set;
- duplicate node/element;
- overconstraint;
- singularity;
- unsupported pore-pressure formulation;
- invalid permeability/material requirement.

Create:

`v15_13_datacheck_issue_register.csv`

with:

- severity;
- exact Abaqus message;
- affected instance/set/element;
- interpretation;
- required action;
- status.

No message may be hidden.

---

# 25. Required outputs

Create under:

`abaqus-audit/3d-v15.13/`

Required regardless of final gate:

- `V15_13_FINAL_SEEPAGE_DOMAIN_RESULT.md`;
- `v15_13_global_coordinate_basis.csv`;
- `v15_13_dam_axis_chain.csv`;
- `v15_13_v15_12_cutoff_disposition.csv`;
- `v15_13_source_station_to_model_map.csv`;
- `v15_13_cutoff_alignment_segments.csv`;
- `v15_13_backfill_material_final_basis.csv`;
- `v15_13_foundation_topology_final.csv`;
- `v15_13_foundation_component_resolution.csv`;
- `v15_13_geology_component_diagnosis.csv`;
- `v15_13_section_level_pore_pressure_audit.csv`;
- `v15_13_element_formulation_changes.csv`;
- `v15_13_dam_hydraulic_role_audit.csv`;
- `v15_13_cutoff_connection_final.csv`;
- `v15_13_structural_joint_audit.csv`;
- `v15_13_spillway_main_dam_transition_resolution.csv`;
- `v15_13_mesh_change_audit.csv`;
- `v15_13_local_mesh_quality.csv`;
- `v15_13_pre_datacheck_gate.csv`;
- real CAE screenshots.

If geometry/topology gate passes, also require:

- final V15.13 CAE;
- final V15.13 INP;
- Data Check files;
- `v15_13_datacheck_issue_register.csv`.

If gate fails:

- still produce a diagnostic CAE/INP only if necessary for inspection;
- label it `NOT_READY_FOR_ANALYSIS`;
- do not label it final solver-ready.

---

# 26. Final report format

`V15_13_FINAL_SEEPAGE_DOMAIN_RESULT.md` must begin with exactly one of:

`FINAL_STATUS = READY_FOR_DATACHECK`

`FINAL_STATUS = DATACHECK_COMPLETED_WITH_ISSUES`

`FINAL_STATUS = DATACHECK_CLEAN`

`FINAL_STATUS = STOPPED_UNRESOLVED`

Then explicitly report:

- active instance count;
- final dam-axis structure chain;
- disposition of V15.12 misplaced wall;
- final left-bank cutoff Y extent;
- final left-bank extension direction and length;
- left-sub-dam cutoff X/Y/Z basis;
- installation/powerhouse cutoff basis;
- spillway/main-dam transition basis;
- main cutoff/geomembrane result;
- right-bank curtain status;
- backfill/geology shared-node result;
- foundation hanging nodes;
- foundation nonconforming faces;
- geology component classification;
- geological leaf-set count audited;
- number of seepage-domain elements by formulation;
- number of unresolved material/permeability regions;
- Data Check status if run;
- exact unresolved items.

---

# 27. Prohibited

Do not:

- modify main;
- force-push;
- globally remesh;
- assume "left bank" means positive Y;
- preserve the V15.12 Y=70..150 wall as a valid left-bank extension without proof;
- create one straight cutoff line through every structure without source support;
- invent retaining-wall dimensions;
- invent permeability/material values;
- mark coordinate-coincident non-shared seepage interfaces as conformal;
- mark hanging nodes > 0 as PASS for a continuous seepage domain;
- use Part-level single-material inference for the multi-material geology Part;
- globally convert C3D8R to C3D8P;
- run S01-S07;
- run Data Check before the pre-Data-Check gate passes.

---

# 28. Final delivery to GitHub

Commit all V15.13 work to:

`abaqus-audit-task`

Push normally.

Return:

- final commit SHA;
- changed-file list;
- final status;
- final CAE path if created;
- final INP path if created;
- dam-axis chain summary;
- anti-seepage chain summary;
- backfill/geology conformity summary;
- geology component summary;
- Section-level pore-pressure summary;
- Data Check result if run;
- all remaining unresolved items.

The task is successful if it produces a trustworthy stop condition. A truthful `STOPPED_UNRESOLVED` is better than another incorrect "PASS".
