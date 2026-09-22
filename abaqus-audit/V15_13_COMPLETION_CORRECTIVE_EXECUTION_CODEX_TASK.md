# V15.13 Completion / Corrective Execution Task

## 1. Objective

This is **not a new V15.14 task**.

Continue the existing V15.13 work from GitHub commit:

`e7296bdedb19187537eaf981991b7ca8074518ee`

Branch:

`abaqus-audit-task`

The purpose is to complete the work that the previous V15.13 execution did not actually perform.

The previous execution correctly diagnosed several problems, but it mostly copied the V15.11 CAE/INP into `3d-v15.13` and stopped at the gate. That behavior is not sufficient for this completion pass.

This task requires **real corrective modeling where the source and geometry support it**, and a truthful stop only where a defensible source/model solution is genuinely unavailable.

Do not modify `main`.

Do not create `3d-v15.14`.

Update/replace the existing V15.13 outputs under:

`abaqus-audit/3d-v15.13/`

Preserve old audit files when useful for traceability, but the final V15.13 files must clearly supersede the earlier incomplete results.

---

# 2. Mandatory files to read before doing anything

Read these repository files first:

1. `abaqus-audit/V15_13_FINAL_SEEPAGE_DOMAIN_REBUILD_AND_DATACHECK_CODEX_TASK.md`
2. `abaqus-audit/3d-v15.13/V15_13_FINAL_SEEPAGE_DOMAIN_REBUILD_AND_DATACHECK_RESULT.md`
3. `abaqus-audit/3d-v15.13/v15_13_pre_datacheck_gate.csv`
4. `abaqus-audit/3d-v15.13/v15_13_phase_a_coordinate_chain.csv`
5. `abaqus-audit/3d-v15.13/v15_13_seepage_chain_audit.csv`
6. `abaqus-audit/3d-v15.13/v15_13_geology_section_pore_pressure_audit.csv`
7. `abaqus-audit/3d-v15.13/v15_13_foundation_topology_audit.csv`
8. `abaqus-audit/3d-v15.13/v15_13_real_interface_audit.csv`
9. `abaqus-audit/audit_v15_13_final_rebuild.py`

Also inspect the current V15.13 CAE/INP and the actual source-report excerpts already used by the project.

Do not proceed if the original V15.13 task file is not present. It is now present in GitHub and must be treated as the governing contract.

---

# 3. Current known failures that must be addressed

The existing V15.13 pre-gate currently fails on:

- real left-bank interfaces;
- foundation geometric conformity;
- geology Section-level pore-pressure coverage;
- backfill material resolution;
- anti-seepage chain continuity;
- geomembrane/cutoff connection.

The previous V15.13 execution also did not produce the exact required canonical files:

- `V15_13_FINAL_SEEPAGE_DOMAIN_RESULT.md`
- `v15_13_section_level_pore_pressure_audit.csv`
- `v15_13_foundation_topology_final.csv`
- `v15_13_cutoff_connection_final.csv`

These files must be created in this completion pass.

Do not create empty placeholders.

---

# 4. Absolute prohibition on another copy-only rebuild

The previous script used:

`shutil.copyfile(BASE_INP, OUT_INP)`

and

`shutil.copyfile(BASE_CAE, OUT_CAE)`

with a V15.11 baseline.

That is allowed only as an initial working copy.

The final V15.13 result must record actual changes in:

`v15_13_mesh_change_audit.csv`

or explicitly state that a specific subsystem could not be changed because a critical source constraint remained unresolved.

A file renamed to V15.13 with unchanged V15.11 geometry is NOT a completed V15.13 model.

---

# 5. Coordinate convention and current verified structure chain

Use:

- X = streamwise;
- Y = dam-axis;
- Z = elevation.

Current verified Y ranges:

- left sub-dam: `-245.700 .. -156.000`
- installation bay: `-156.000 .. -122.000`
- powerhouse: approximately `-122.000 .. -15.400`
- ecological release: `-15.400 .. -2.900`
- spillway/frontage region: approximately `-2.900 .. 93.600`
- main P25 sand/gravel dam system: approximately `150.000 .. 445.000`

Increasing Y moves from the left-bank side toward the main/right-bank dam side.

Therefore "向左岸延伸80m" must move toward **more negative Y**.

Never recreate the incorrect V15.12 `Y=70..150` segment as a left-bank extension.

---

# 6. Source-controlled anti-seepage facts

Treat the following source facts as mandatory constraints:

- vertical concrete cutoff wall system;
- wall thickness = **1.0 m**;
- main riverbed wall bottom = **3021.00 m**;
- powerhouse/installation central deep reach bottom = **3011.00 m**;
- both sides of that deep reach transition approximately **1:1** back to 3021.00 m;
- left-sub-dam cutoff bottom = **3021.00 m**;
- left-sub-dam cutoff is aligned with the left-side powerhouse/installation anti-seepage line;
- left-bank cutoff extends approximately **80 m toward the left abutment**;
- main riverbed wall connects to the upper composite geomembrane;
- spillway wall connects through a connecting plate and turns near the right retaining wall;
- right-bank cutoff connects to a grout curtain;
- right-bank curtain extends about **100 m** into the right bank;
- powerhouse, installation, ecological release, spillway and left sub-dam are part of one anti-seepage system.

Also preserve the known source discrepancy:

- one source passage places the left-sub-dam wall around `坝上 0-009.50 m`;
- another detailed left-sub-dam passage uses approximately `坝上 0-014.50 m`.

Do not hide this 5 m discrepancy.

---

# 7. First corrective gate — solve the left-structure cutoff axis before building walls

Before creating any new wall solids, create:

`v15_13_left_structure_cutoff_axis_solution.csv`

Use at least these independent constraints:

1. actual installation-bay and powerhouse global geometry;
2. source upstream offset for powerhouse/installation cutoff;
3. left-sub-dam source cross-section;
4. left-sub-dam source cutoff offset;
5. the real left-sub-dam/installation structural joint;
6. existing foundation/backfill geometry.

For every candidate X axis report:

- candidate X;
- source basis;
- residual against installation/powerhouse geometry;
- residual against left-sub-dam section;
- whether it lies physically inside/under both required structures;
- confidence.

## Mandatory contradiction check

The current left-sub-dam global X range is approximately:

`-70.85 .. -56.00`

while the current installation bay spans approximately:

`-64.00 .. -7.50`.

If the source-supported common cutoff axis lies outside the current left-sub-dam cross-section, this proves the left-sub-dam X placement is still incorrect.

In that case:

- do not force the wall outside the dam;
- do not bend the wall artificially just to touch the dam;
- locally reposition/rebuild the left-sub-dam cross-section in X so that:
  - the structural joint at Y=-156 remains real;
  - the source cross-section is preserved;
  - the common left-structure cutoff axis actually passes through the intended foundation zone;
  - fishway and backfill are updated consistently.

This correction is allowed even though earlier tasks treated the sub-dam X location as accepted.

Preserve the sub-dam Y length and source section dimensions.

---

# 8. If left-sub-dam X is corrected, move dependent geometry coherently

If the sub-dam must move/rebuild in X:

- preserve Y=-245.7..-156;
- preserve 89.70 m dam-axis length;
- preserve crest width 7.0 m;
- preserve upstream/downstream slopes;
- preserve source foundation elevations;
- preserve the installation joint;
- refit the fishway through-dam crossing to the moved section;
- preserve fishway total centerline length target approximately 1407.57 m;
- rebuild only the affected engineered backfill;
- do not move powerhouse, eco release or spillway to compensate.

Create:

`v15_13_left_subdam_x_correction_audit.csv`

with old/new bbox and all preserved source dimensions.

---

# 9. Build the left-bank anti-seepage system only after the axis is solved

Required physical segments:

## 9.1 Left-bank abutment extension

From the outer/left end of the left-sub-dam wall:

- extend approximately 80 m toward more-negative Y;
- bottom = 3021.00 m;
- thickness = 1.0 m;
- use the solved left-structure X alignment.

If left-sub-dam wall reaches Y=-245.7, the nominal extension endpoint is near Y=-325.7, subject to actual geology/domain boundary verification.

## 9.2 Left-sub-dam wall

- span the actual sub-dam;
- thickness 1.0 m;
- bottom 3021.00 m;
- connect physically to the abutment extension;
- connect physically to installation/powerhouse anti-seepage geometry.

## 9.3 Installation/powerhouse wall

- use the solved left-structure X line;
- represent the 3011.00 m deep reach only where source stationing requires it;
- transition approximately 1:1 to 3021.00 m outside the deep reach;
- do not use a uniform bottom elevation over the whole segment.

## 9.4 Ecological-release connection

The 2-bay ecological-release structure is physically between powerhouse and spillway.

Provide the source-supported cutoff/connection geometry beneath or through this reach.

Do not create a separate named wall merely for naming convenience if a connection plate/embedded wall representation is more faithful.

## 9.5 Spillway wall

Represent the spillway anti-seepage reach with bottom about 3021.00 m unless a more specific source value exists.

Use actual spillway geometry.

## 9.6 Spillway-to-main-dam transition

The model has an approximately 56 m-class Y interval between the spillway structural end and the main P25 system.

The source states that gravity retaining walls exist between the spillway and sand/gravel dam.

Search the source/repository for the actual transition/retaining-wall geometry.

If enough dimensions are available:

- add the missing structural transition and its anti-seepage connection.

If dimensions are not sufficient:

- do not invent the full retaining wall;
- still create the source-supported cutoff bend/connection only if its geometry is defensible;
- keep the structural retaining-wall body as an explicit unresolved item.

## 9.7 Main riverbed wall

Retain P25 only after confirming the true global position is still correct.

## 9.8 Right-bank curtain

Search for an existing grout-curtain or equivalent low-permeability region.

If absent:

- do not invent a solid curtain thickness;
- represent the intended hydraulic boundary only if the analysis methodology supports an explicit equivalent boundary;
- otherwise keep this final segment unresolved.

---

# 10. Required anti-seepage chain evidence

Create:

`v15_13_cutoff_alignment_segments.csv`

and:

`v15_13_cutoff_connection_final.csv`

For every adjacent pair report:

- segment A/B names;
- start/end coordinates;
- thickness;
- top/bottom elevation;
- real minimum gap;
- real coincident/contact area or edge length;
- shared/coincident nodes;
- positive-volume overlap count;
- source basis;
- status.

Acceptance for a physical wall-to-wall connection:

- gap <= 1 mm;
- unintended positive-volume interpenetration = 0;
- actual contact/connection length or area > 0.

Do not use bbox equality as final evidence.

---

# 11. Fix the main cutoff / geomembrane connection

Current V15.13 audit reports:

- minimum distance = 0;
- 397 coincident face pairs;
- 594 coincident-but-not-shared nodes;
- 695 hanging nodes;
- 395 interpenetrating element pairs;
- status UNRESOLVED.

This must be investigated geometrically.

Required procedure:

1. isolate only the physical terminal connection zone;
2. inspect actual element solids/faces;
3. distinguish true intended embed/contact from positive-volume overlap;
4. trim/partition/rebuild the local geomembrane/cutoff connection if needed;
5. preserve source geometry and thickness;
6. prefer a conformal/common interface where numerically reasonable.

Final acceptance:

- physical gap <= 1 mm;
- positive-volume interpenetrating element pairs = 0;
- no unexplained barrier discontinuity;
- no false "PASS" based on a large-area coincident broad-phase match.

Create canonical file:

`v15_13_geomembrane_cutoff_connection_final.csv`

and update:

`v15_13_cutoff_connection_final.csv`.

---

# 12. Convert the engineered backfill/geology interface into a truly conformal seepage mesh

The current independent backfill Part is geometrically coincident with retained geology but does not form a trustworthy continuous pore-pressure mesh.

Preferred implementation:

1. use the natural geology Part as the receiving analysis mesh;
2. identify the actual cells occupied by the engineered backfill;
3. remove conflicting geology cells only where needed;
4. append backfill cells into the same foundation Part;
5. reuse existing geology interface node labels wherever coordinates match;
6. create new nodes only for true interior/new boundary points;
7. preserve a distinct element set:
   `FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL`;
8. preserve a distinct Section/material assignment;
9. remove/suppress the standalone backfill instance after successful integration.

If the meshes do not align exactly, perform only a local conformal remesh.

Do not add Tie merely to hide the discontinuity.

---

# 13. Exact conformity acceptance for continuous seepage media

For:

- engineered backfill <-> natural geology;
- natural-geology internal material boundaries intended to be continuous;

require:

- shared interface nodes;
- hanging nodes = 0;
- nonconforming internal faces = 0;
- positive-volume overlap = 0;
- unexplained gap = 0.

Create canonical:

`v15_13_foundation_topology_final.csv`

This file must contain actual computed values, not:

- NOT_PROVEN;
- NOT_COMPUTED;
- SEE_COMPONENT_ROWS.

Those placeholders are not acceptable in the final completion pass.

If the sweep cannot be computed, the completion status must remain STOPPED_UNRESOLVED.

---

# 14. Compute the actual foundation connected components

The previous V15.13 output left component counts as NOT_COMPUTED.

Now compute them.

Build an element adjacency graph using exact shared element faces after the conformal backfill repair.

Report for:

- full natural geology;
- each geology leaf/material;
- integrated backfill;
- entire seepage foundation domain.

Create:

`v15_13_foundation_component_resolution.csv`

For each disconnected component report:

- component ID;
- bbox;
- element count;
- material/leaf sets;
- neighboring component;
- physical gap;
- classification:
  - INTENDED_SEPARATE_DOMAIN
  - DIFFERENT_MATERIAL_CONFORMAL_INTERFACE
  - SAME_DOMAIN_MESH_DISCONNECT
  - EXTERNAL_DOMAIN_BOUNDARY
  - UNRESOLVED.

Any `SAME_DOMAIN_MESH_DISCONNECT` must be locally repaired.

---

# 15. Section-level pore-pressure audit — keep all 36 geology rows

The current V15.13 correctly identified 36 geology Section rows.

Preserve this improvement.

Create the canonical file:

`v15_13_section_level_pore_pressure_audit.csv`

It must report:

- geological element set;
- Section;
- Material;
- element formulation;
- element count;
- pore-pressure DOF;
- permeability;
- hydraulic role;
- source basis;
- final action;
- status.

The current 10 failing rock-related rows must not be hidden.

---

# 16. Rock hydraulic treatment — source first, no invented permeability

Current unresolved rock-related regions include:

- P2 quartz sandstone;
- fresh granite;
- strongly unloaded rock;
- weakly unloaded rock;
- deeply unloaded rock;
- corresponding river/right-bank rock regions.

The source report provides hydraulic categories such as:

- shallow strongly unloaded rock: strong permeability, approximately >=100 Lu;
- weak/deep unloaded rock: mainly medium permeability, approximately 10-100 Lu;
- locally intact deep rock: locally weak permeability, approximately 0.1-1 Lu.

These are **Lu test categories**, not direct Abaqus permeability coefficients.

Do not directly convert Lu to m/s using an arbitrary formula.

Required procedure:

1. search the full report and repository for explicit hydraulic conductivity/permeability values already used in seepage calculations;
2. search existing historical model materials/scripts for rock permeability;
3. if an exact source-derived coefficient exists, assign it with a traceable citation/source field;
4. if only Lu categories exist, do NOT pretend they are calibrated k-values.

If no defensible k exists:

- keep those rock materials flagged `HYDRAULIC_CALIBRATION_REQUIRED`;
- do not globally convert those regions to C3D8P for production seepage;
- geometry/topology may still be completed;
- final status must distinguish solver geometry readiness from production seepage calibration readiness.

Create:

`v15_13_rock_hydraulic_parameter_basis.csv`.

---

# 17. Element formulation conversion rules

Do NOT globally convert all C3D8R.

For each of the 36 geology regions:

Convert C3D8R -> C3D8P only when:

- the region is intended to transmit groundwater; AND
- a defensible permeability definition exists.

Keep structural-only formulation only when there is a defensible reason for exclusion from the seepage domain.

When conversion is valid:

- preserve node coordinates;
- preserve element connectivity;
- preserve element-set identity;
- change only element formulation and material/Section as required.

Create:

`v15_13_element_formulation_changes.csv`.

Every changed element set must have a source/engineering basis.

---

# 18. Correct hydraulic-role classification for dam materials

Re-audit:

- drainage bodies;
- filter layers;
- gravel dam shell;
- upstream gravel fill;
- main rockfill;
- impermeable fill;
- cutoff wall;
- geomembrane.

A drainage/filter region with permeability and pore-pressure DOFs should not be called "structural-only" if its intended function is hydraulic.

Create:

`v15_13_dam_hydraulic_role_audit.csv`.

This is an audit classification correction unless model formulation is genuinely wrong.

---

# 19. Backfill material resolution

Current temporary mapping is:

`Q3AL_III`

Do not silently promote it to verified.

Search for a left-sub-dam/installation-specific compacted sand-gravel parameter set.

The report confirms compacted sand/gravel is used in this structural area, but the exact numerical calibration must be source-supported.

Create canonical:

`v15_13_backfill_material_final_basis.csv`

Allowed status:

- VERIFIED_SOURCE_MAPPING
- ENGINEERING_EQUIVALENT_ASSUMPTION
- UNRESOLVED

If using Q3AL_III as an engineering-equivalent assumption, state that explicitly.

Do not call it source-verified unless the source actually says so.

---

# 20. Structural joints versus seepage-domain interfaces

Do not confuse these two classes.

## Structural joints

Examples:

- sub-dam / installation;
- installation / powerhouse;
- powerhouse / ecological release;
- ecological release / spillway.

These may legitimately use coincident but non-shared structural meshes.

For these report:

- real gap;
- real contact area;
- penetration;
- joint classification.

Do not require shared nodes unless the intended model requires continuity.

## Continuous seepage-media interfaces

Examples:

- backfill / geology;
- same continuous geological domain.

These must be conformal/shared-node unless a specific pore-pressure transfer formulation is deliberately used.

Create:

`v15_13_structural_joint_audit.csv`.

---

# 21. Required full geometric/topological sweeps

The previous output used placeholders such as:

- NOT_PROVEN_BY_GEOMETRIC_FACE_SWEEP;
- NOT_COMPUTED.

These must now be replaced by actual calculations.

Implement a real sweep using:

- exact element connectivity;
- global coordinates;
- coordinate hashing/spatial indexing;
- actual boundary-face geometry;
- component graph traversal.

For the final foundation domain calculate:

- external faces;
- shared internal faces;
- nonconforming internal faces;
- hanging nodes;
- duplicate nodes;
- duplicate elements;
- nonmanifold faces;
- connected components;
- positive-volume overlap pairs.

No copied values from V15.12/V15.13.

---

# 22. Required canonical output files

The final completion pass must create/update all of these:

1. `V15_13_FINAL_SEEPAGE_DOMAIN_RESULT.md`
2. `v15_13_global_coordinate_basis.csv`
3. `v15_13_dam_axis_chain.csv`
4. `v15_13_left_structure_cutoff_axis_solution.csv`
5. `v15_13_left_subdam_x_correction_audit.csv` if sub-dam X changes
6. `v15_13_source_station_to_model_map.csv`
7. `v15_13_cutoff_alignment_segments.csv`
8. `v15_13_cutoff_connection_final.csv`
9. `v15_13_geomembrane_cutoff_connection_final.csv`
10. `v15_13_foundation_topology_final.csv`
11. `v15_13_foundation_component_resolution.csv`
12. `v15_13_geology_component_diagnosis.csv`
13. `v15_13_section_level_pore_pressure_audit.csv`
14. `v15_13_rock_hydraulic_parameter_basis.csv`
15. `v15_13_element_formulation_changes.csv`
16. `v15_13_dam_hydraulic_role_audit.csv`
17. `v15_13_backfill_material_final_basis.csv`
18. `v15_13_structural_joint_audit.csv`
19. `v15_13_spillway_main_dam_transition_resolution.csv`
20. `v15_13_mesh_change_audit.csv`
21. `v15_13_local_mesh_quality.csv`
22. `v15_13_pre_datacheck_gate.csv`
23. final V15.13 CAE
24. final V15.13 INP
25. actual CAE screenshots.

Do not substitute differently named "almost equivalent" files for the four previously missing canonical files.

---

# 23. Required screenshots

Export actual Abaqus/CAE viewport screenshots:

1. full hub with global axes;
2. complete dam-axis chain;
3. left sub-dam / installation / powerhouse plan;
4. solved left-structure cutoff axis;
5. left-bank 80 m extension;
6. left-sub-dam cutoff section;
7. installation/powerhouse deep-wall 3011 m reach;
8. ecological-release/spillway connection;
9. spillway-to-main-dam transition;
10. main cutoff/geomembrane local connection before/after;
11. right-bank curtain representation;
12. backfill/geology conformal mesh;
13. geology connected-component display;
14. geology Section/material display;
15. pore-pressure-capable element display;
16. final full seepage-domain overview.

Do not use synthetic drawings as substitutes.

---

# 24. Mesh-quality checks

For every changed region report:

- element type;
- node count;
- element count;
- min edge;
- median edge;
- P95 edge;
- max edge;
- max aspect ratio;
- negative/invalid volume count;
- collapsed elements;
- duplicate elements.

No invalid/negative/collapsed elements are acceptable.

No global remesh.

---

# 25. Pre-Data-Check gate — stricter final version

Update:

`v15_13_pre_datacheck_gate.csv`

Critical rows must include:

- original V15.13 task read successfully;
- no copy-only completion;
- coordinate convention resolved;
- left/right direction resolved;
- V15.12 misplaced wall absent;
- left-structure cutoff axis solved;
- left-sub-dam cutoff physically inside correct structure;
- left-bank 80 m extension direction correct;
- installation/powerhouse wall geometry resolved;
- ecological-release connection resolved;
- spillway wall resolved;
- spillway/main-dam transition resolved or explicitly source-limited;
- main cutoff/geomembrane positive-volume overlap = 0;
- right-bank curtain representation resolved or explicitly outside current model scope with justified boundary condition;
- backfill/geology shared-node conformity PASS;
- continuous foundation hanging nodes = 0;
- continuous foundation nonconforming faces = 0;
- same-domain disconnects = 0;
- all 36 geology Sections audited;
- all intended seepage regions have pore-pressure-capable elements AND defensible permeability, otherwise production-seepage gate FAIL;
- backfill material status explicit;
- no invalid/collapsed elements;
- all active continuum elements have valid Sections/Materials.

---

# 26. Separate two readiness concepts

The final report must explicitly distinguish:

## A. Geometry / solver Data Check readiness

Can the model be checked by Abaqus without unresolved geometry/topology defects?

## B. Production seepage-calibration readiness

Are all seepage-domain materials, especially rock masses, supported by defensible permeability values?

It is possible for A to PASS while B remains unresolved.

If A passes but B fails:

- Data Check may be run;
- production seepage analysis must NOT be declared ready.

This prevents unknown rock permeability from blocking useful solver validation while still preserving scientific honesty.

---

# 27. Conditional Abaqus Data Check

Run Abaqus Data Check only if the **geometry/solver-readiness** critical gate is PASS.

Do not require production hydraulic calibration to be complete merely to execute Data Check, provided all active element/material definitions are syntactically valid.

If Data Check is run, capture:

- .dat
- .msg
- .sta
- job INP
- return code
- exact warnings/errors.

Create:

`v15_13_datacheck_issue_register.csv`

with:

- severity;
- exact Abaqus message;
- affected part/instance/set/element;
- interpretation;
- required fix;
- status.

Do not suppress warnings.

---

# 28. Final report first line — mandatory

Create:

`abaqus-audit/3d-v15.13/V15_13_FINAL_SEEPAGE_DOMAIN_RESULT.md`

The first line must be exactly one of:

`FINAL_STATUS = STOPPED_UNRESOLVED`

`FINAL_STATUS = GEOMETRY_READY_HYDRAULICS_UNRESOLVED`

`FINAL_STATUS = DATACHECK_COMPLETED_WITH_ISSUES`

`FINAL_STATUS = DATACHECK_CLEAN_HYDRAULICS_UNRESOLVED`

`FINAL_STATUS = DATACHECK_CLEAN_SEEPAGE_READY`

Do not omit this field.

---

# 29. Fail-fast assertions

The completion script must terminate or mark FAIL if any of these occur:

- the original V15.13 task file was not read;
- V15.12 misplaced wall is active;
- left-bank extension goes toward increasing Y;
- a wall is created outside its intended structure without source proof;
- a continuous seepage interface has hanging nodes > 0;
- a continuous seepage interface has nonconforming faces > 0;
- geomembrane/cutoff has positive-volume interpenetration after repair;
- a geology leaf set is omitted from Section-level audit;
- a permeability value is invented without source/explicit assumption label;
- a copy-only V15.11 -> V15.13 result is presented as completion.

A truthful failure is preferable to another false PASS.

---

# 30. Git and delivery rules

Work only on:

`abaqus-audit-task`

Do not modify `main`.

Do not force-push.

Do not create V15.14.

Commit the V15.13 completion as a new commit on top of:

`e7296bdedb19187537eaf981991b7ca8074518ee`

Suggested commit message:

`audit: complete v15.13 corrective seepage rebuild`

Return:

- final commit SHA;
- changed-file list;
- final status;
- final CAE/INP path;
- whether left-sub-dam X changed;
- final anti-seepage chain;
- foundation conformity counts;
- geology Section audit summary;
- unresolved rock hydraulic parameters;
- backfill material status;
- Data Check status;
- all remaining FAIL/UNRESOLVED items.

Do not report completion until the new commit is pushed to `abaqus-audit-task`.
