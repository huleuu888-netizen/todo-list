# V15.7 final geology mesh cleanup task for Codex

## Objective

Continue from commit `b2c380c5f960ed3564f16e02b79f36e2bfd53c9f`.

The v15.6 geometry and engineering-structure meshes are the frozen baseline.

This task is the final pre-Data-Check mesh cleanup.

The only goals are:

1. eliminate nonconformal / hanging-node interfaces inside continuous geology;
2. remove abnormal near-field geology elements around the hub;
3. repair M3-to-M4 grading;
4. correct mesh-audit classification and acceptance logic.

Do not redesign any structure.

Do not run S01-S07.

Do not run structural or seepage validation.

Work only on branch:

`abaqus-audit-task`

Do not modify `main`.

Create all new outputs under:

`abaqus-audit/3d-v15.7/`

Do not overwrite previous versions.

---

# 1. Freeze geometry and all engineering structural meshes

Preserve v15.6 engineering geometry and structural meshes exactly.

Do not remesh or move:

- right-bank dam;
- geomembrane;
- cutoff wall;
- powerhouse;
- powerhouse flushing outlets;
- installation bay;
- tailwater;
- spillway;
- ecological-release structure;
- stilling basin;
- left-bank sub-dam;
- fishway.

Only geology/foundation mesh may be changed.

Create:

`v15_7_freeze_check.csv`

Report for every non-geology engineering instance:

- v15.6 bounding box;
- v15.7 bounding box;
- node count;
- element count;
- changed-node-coordinate count;
- status.

Any unexplained geometry or structural-node change is FAIL.

---

# 2. Important interface rule for v15.7

Do not force structure-to-foundation shared nodes in this mesh-only task.

The following are allowed to remain separate part/instance interfaces:

- powerhouse / foundation;
- spillway / foundation;
- ecological release / foundation;
- stilling basin / foundation;
- tailwater / foundation;
- sub-dam / foundation;
- fishway concrete / geology;
- cutoff wall / foundation;
- geomembrane / cutoff wall.

For those interfaces, check only:

- no geometric penetration;
- no unintended gap;
- surface location consistency;
- reasonable adjacent mesh-size ratio.

Do not add Tie/contact/MPC in this task.

Shared-node conformity is mandatory only for geology-to-geology interfaces that represent one continuous geological medium.

---

# 3. Primary defect: eliminate the remaining 1669 nonconformal geology faces

The v15.6 report explicitly records:

- conforming regenerated source faces: 74439;
- nonconforming regenerated source faces: 1669.

The v15.7 primary acceptance target is:

**continuous-geology nonconforming faces = 0**

Do not merely relabel those interfaces.

For every one of the 1669 nonconforming geology faces:

1. identify the source geology layer;
2. identify the adjacent element blocks;
3. expand the repair region to a clean block boundary;
4. remove the affected local elements;
5. regenerate both sides with compatible boundary subdivisions;
6. merge coincident geology nodes where they represent the same continuous medium;
7. confirm one-to-one face connectivity.

Do not use Tie/contact/MPC to connect geology.

---

# 4. Preferred repair strategy

Do not use isolated one-to-eight subdivision if it leaves hanging nodes.

Use one of these methods.

## Method A — full local block regeneration

Preferred.

For each defective interface:

- choose a rectangular / sweepable contiguous block containing the bad interface;
- remove the entire block to clean outer faces;
- preserve original geological/material boundaries;
- generate a new structured/swept C3D8P-compatible mesh;
- match outer retained-mesh boundary subdivisions exactly;
- merge all coincident geology nodes.

## Method B — explicit transition cells

Only where Method A is impractical.

- construct controlled 1-to-2 transition bands;
- all internal nodes must be shared;
- no T-junction topology;
- no hanging node;
- outer retained boundary must still match exactly.

---

# 5. Repair abnormal near-field geology elements

Do not globally remesh all M3 geology.

Instead, locate and repair abnormal elements and one or more neighbor rings.

Create a candidate set with any of:

- centroid within 60 m of engineering structures AND edge > 15 m;
- aspect ratio > 8;
- M3 element with P95-driving outlier geometry;
- element involved in a nonconformal geology face;
- element next to a repaired transition block.

For each candidate:

- inspect adjacent topology;
- rebuild the local block, not just the single element;
- preserve material assignment and layer boundaries.

Create:

`v15_7_bad_element_repair_map.csv`

with:

- original instance;
- original element label;
- reason selected;
- original min/median/max edge;
- original aspect ratio;
- repaired block id;
- new element count;
- final status.

---

# 6. M3 target mesh after cleanup

Do not make every M3 element the same size.

Use graded bands:

## M3-A: 0-8 m
Target characteristic edge:

**1.5-3.0 m**

## M3-B: 8-20 m
Target:

**3.0-4.5 m**

## M3-C: 20-40 m
Target:

**4.5-6.5 m**

## M3-D: 40-60 m
Target:

**6.0-9.0 m**

The current v15.6 M3-D P95 around 21 m is too coarse and must be repaired.

---

# 7. M4 transition and far field

Use:

## M4 transition
approximately **8-15 m**

## ordinary far field
approximately **10-20 m**

## remote outer boundary
may remain larger than 20 m if genuinely remote.

Classify truly remote oversized elements as:

`M4_REMOTE_BOUNDARY`

Remote-boundary cells must not be counted when judging near-foundation mesh quality.

Do not globally refine the full domain.

---

# 8. M3-to-M4 transition target

The v15.6 M3-C to M3-D ratio is too abrupt.

Build a smoother transition.

For each adjacent band calculate:

- median ratio;
- P90 ratio;
- P95 ratio.

Preferred adjacent-band P95 ratio:

**<= 1.5**

Maximum acceptable with documented geology-layer constraint:

**<= 2.0**

A direct jump > 5 is FAIL.

---

# 9. Continuous geology connectivity

The v15.6 mesh-island audit shows multiple disconnected components that were not intended to be separate continuous geology blocks.

For v15.7:

- preserve truly separate material blocks only where they are physically/geometrically separate;
- connect accidentally disconnected pieces of the same continuous geological domain;
- merge coincident geology nodes where appropriate;
- preserve material boundaries using element sets / sections, not by breaking continuous geometry into accidental islands.

Create:

`v15_7_geology_component_audit.csv`

For each component report:

- component id;
- source layers;
- node count;
- element count;
- bounding box;
- physically intended separate: YES/NO;
- final disposition;
- status.

Target:

**unintended continuous-geology disconnected components = 0**

---

# 10. Correct region-classification audit

The previous audit omitted the requested region-classification file.

Create:

`v15_7_region_classification_audit.csv`

Top-level mutually exclusive classes:

- DAM_FILL;
- GEOMEMBRANE;
- CUTOFF_WALL;
- STRUCTURAL_CONCRETE;
- M3_A_FOUNDATION_GEOLOGY;
- M3_B_FOUNDATION_GEOLOGY;
- M3_C_FOUNDATION_GEOLOGY;
- M3_D_FOUNDATION_GEOLOGY;
- M4_TRANSITION_GEOLOGY;
- M4_FAR_FIELD_GEOLOGY;
- M4_REMOTE_BOUNDARY.

Use unique identity:

`instance_name + element_label`

Report:

- unique element count;
- duplicate membership count;
- conflicting membership count;
- missing-classification count;
- status.

Target:

- duplicate membership = 0;
- conflicting membership = 0.

Dam-fill elements must never be counted as geology.

---

# 11. Recalculate all mesh metrics from actual element connectivity

Do not use instance bounding boxes.

For every region calculate from real element edges:

- min edge;
- median edge;
- P90;
- P95;
- max edge;
- max aspect ratio;
- invalid/negative volume;
- collapsed elements;
- duplicate elements;
- duplicate nodes;
- nonmanifold faces;
- disconnected components.

Use Abaqus native mesh-quality metrics when available.

---

# 12. Final acceptance criteria

For the **overall M3 foundation geology**:

Target:

- median edge <= **6 m**;
- P95 edge <= **10 m**;
- max edge <= **15 m**, except explicitly documented boundary-transition exceptions outside the engineering influence zone;
- aspect ratio <= **8** for normal M3 elements;
- invalid/negative volume = 0;
- collapsed elements = 0;
- duplicate elements = 0;
- continuous-geology nonconforming faces = 0;
- hanging nodes inside continuous geology = 0;
- mesh holes = 0;
- overlapping old/new geology elements = 0.

For **M3-D** specifically:

- median preferably <= 9 m;
- P95 preferably <= 12 m;
- no 20+ m P95 transition band.

If a target is not achieved, mark FAIL or UNRESOLVED.

Do not mark PASS simply because no negative-volume element exists.

---

# 13. Structure-to-foundation surface compatibility audit

Although shared nodes are not mandatory here, create:

`v15_7_structure_foundation_surface_audit.csv`

Interfaces:

- cutoff wall / foundation;
- powerhouse / foundation;
- installation bay / foundation;
- spillway / foundation;
- ecological release / foundation;
- stilling basin / foundation;
- tailwater / foundation;
- sub-dam / foundation;
- fishway excavation / geology.

Report:

- minimum geometric gap;
- maximum geometric gap;
- penetration volume/count if any;
- structure-side median/P95 mesh edge;
- geology-side median/P95 mesh edge;
- local mesh-size ratio;
- status.

Target:

- no unintended penetration;
- no unintended open gap;
- no direct extreme mesh-size jump.

Do not require shared-node count to be nonzero for these interfaces.

---

# 14. Required screenshots

If Abaqus/CAE is available, export actual viewport screenshots with element edges visible.

Required:

1. full hub mesh;
2. all repaired nonconformal geology zones overview;
3. cutoff-wall bottom foundation;
4. powerhouse foundation;
5. spillway foundation;
6. ecological-release foundation;
7. sub-dam foundation;
8. M3-A/M3-B transition;
9. M3-B/M3-C transition;
10. M3-C/M3-D transition;
11. M3-D/M4 transition;
12. far-field / remote-boundary geology.

Do not use synthetic drawings.

---

# 15. Required outputs

Create under:

`abaqus-audit/3d-v15.7/`

Required files:

- final v15.7 INP;
- final v15.7 CAE if Abaqus is available;
- `V15_7_FINAL_GEOLOGY_MESH_RESULT.md`;
- `v15_7_freeze_check.csv`;
- `v15_7_bad_element_repair_map.csv`;
- `v15_7_region_classification_audit.csv`;
- `v15_7_geology_component_audit.csv`;
- `v15_7_geology_interface_conformity.csv`;
- `v15_7_mesh_density_audit.csv`;
- `v15_7_mesh_quality_audit.csv`;
- `v15_7_mesh_transition_audit.csv`;
- `v15_7_structure_foundation_surface_audit.csv`;
- `v15_7_mesh_inventory.csv`;
- actual CAE mesh screenshots.

The final report must explicitly state:

- geometry unchanged: YES/NO;
- structural mesh unchanged: YES/NO;
- starting nonconforming geology faces: 1669;
- final nonconforming geology faces;
- final hanging-node count inside continuous geology;
- unintended disconnected geology components;
- M3 median/P95/max edge;
- M3-D median/P95/max edge;
- worst M3 aspect ratio;
- mesh-hole count;
- overlap count;
- total node/element counts;
- PASS / FAIL / UNRESOLVED summary.

---

# 16. Prohibited

Do not:

- change engineering geometry;
- remesh already-good structural parts;
- change materials;
- change permeability;
- change density;
- change elastic parameters;
- add Encastre;
- add springs;
- add artificial nodal restraints;
- add Tie/contact/MPC to hide geology mesh incompatibility;
- run S01-S07;
- claim structural validation;
- claim seepage validation;
- claim mesh convergence;
- globally refine all geology;
- modify `main`.

---

# Completion condition

V15.7 is complete only when:

- continuous-geology nonconforming faces are reduced from 1669 to **0**, or any irreducible residual is individually documented and the overall status remains UNRESOLVED;
- no hanging-node topology remains inside continuous geology;
- no unintended disconnected continuous-geology components remain;
- M3 outlier elements around the hub are repaired;
- M3-D no longer contains the current excessively coarse transition pattern;
- geometry and structural meshes remain frozen.

After v15.7, stop mesh redesign and proceed to a separate Abaqus Data Check task.

---

# Final delivery

Commit all v15.7 work to:

`abaqus-audit-task`

Push normally.

Do not force-push.

Return:

- final commit SHA;
- changed-file list;
- nonconforming-face count before/after;
- hanging-node count;
- unintended geology-component count;
- M3 median/P95/max edge;
- M3-D median/P95/max edge;
- worst M3 aspect ratio;
- total nodes/elements;
- final INP path;
- final CAE path;
- screenshot paths.
