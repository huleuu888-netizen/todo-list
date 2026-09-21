# V15.6 foundation mesh interface repair task for Codex

## Objective

Continue from commit `0eb0355722f9ab9cc86035dd602716ba18adadeb`.

The v15.5 engineering geometry and structural mesh are the frozen baseline.

This task is focused on one problem only:

**repair the foundation/geology mesh around the structures so that the near-field mesh is actually refined, transitions gradually into the far field, and has no hanging-node / nonconformal orphan-mesh interfaces.**

Do not redesign the hub.

Do not modify engineering geometry.

Do not run S01-S07.

Work only on branch:

`abaqus-audit-task`

Do not modify `main`.

Create all new outputs under:

`abaqus-audit/3d-v15.6/`

Do not overwrite any earlier version.

---

# 1. Freeze all v15.5 engineering geometry and structural meshes

Preserve exactly:

- right-bank dam geometry;
- geomembrane geometry;
- cutoff-wall geometry;
- powerhouse geometry;
- powerhouse sediment-flushing outlets;
- installation bay;
- tailwater;
- spillway;
- ecological-release structure;
- stilling basin;
- left-bank sub-dam;
- fishway;
- all v15.5 structure locations and dimensions.

Do not alter the already-refined structural meshes unless a boundary-face node pattern must be copied into the adjacent foundation mesh for conformity.

The intended working structural mesh remains approximately:

- M1 critical regions: 0.5-1.0 m;
- M2 main structures: 1.0-2.5 m.

Create:

`v15_6_geometry_and_structure_freeze_check.csv`

Compare v15.5 and v15.6:

- instance bounding boxes;
- structural node count;
- structural element count;
- changed structural node coordinates;
- PASS / FAIL.

Any unexplained engineering-coordinate change is FAIL.

---

# 2. Main defect to repair

The v15.5 audit identified the following unacceptable conditions:

- M3 near-foundation geology median edge is around 5.5 m but P95 is about 43 m;
- some M3 elements reach about 150 m edge length;
- transition ratios from structure to foundation are far above the desired range;
- many remeshed geology blocks are marked:
  `GEOMETRIC_COVERAGE_PRESERVED_HANGING_NODE_RISK`;
- independent mesh islands remain in several structural/geological regions;
- current regional classification mixes some dam and geology statistics.

V15.6 must repair these issues rather than only relabel them.

---

# 3. Conformal mesh is mandatory at repaired foundation interfaces

For all newly repaired near-foundation regions:

- no hanging nodes;
- no T-junction node patterns;
- no overlapping old/new elements;
- no open mesh gaps;
- no duplicate coincident nodes left unmerged;
- no Tie;
- no contact;
- no MPC used merely to repair mesh incompatibility.

Preferred interface condition:

**shared nodes and conformal element faces.**

If two adjacent regions represent the same continuous medium, their interface node coordinates and face subdivisions must match one-to-one.

For pore-pressure solids, displacement and pore-pressure continuity must be achievable through the same shared-node topology.

---

# 4. Foundation remesh zones

Rebuild the local geology around the following engineering regions:

1. cutoff wall;
2. geomembrane/cutoff connection;
3. powerhouse foundation;
4. installation-bay foundation;
5. spillway foundation;
6. ecological-release foundation;
7. stilling-basin foundation;
8. tailwater foundation/excavation;
9. left-bank sub-dam foundation;
10. fishway excavation/crossing region.

The surrounding geology must remain divided by original geological/material layers.

Do not homogenize different geological units merely to simplify meshing.

---

# 5. Required graded M3 foundation mesh

Use true distance-based refinement from engineering contact surfaces.

## Band M3-A: immediate foundation zone

Distance from structure/foundation interface:

**0-8 m**

Target characteristic edge:

**1.5-3.0 m**

For cutoff wall bottom and other highly localized interfaces, use smaller values where necessary.

## Band M3-B: inner transition

Distance:

**8-20 m**

Target edge:

**3-4.5 m**

## Band M3-C: outer transition

Distance:

**20-40 m**

Target edge:

**4.5-6.5 m**

## Band M3-D: final local transition

Distance:

**40-60 m**

Target edge:

**6.5-9 m**

After that, connect into M4 geology.

These are engineering targets, not rigid values. Mesh topology and geological layers control the exact seeds.

The purpose is to eliminate the current situation where a 1-2 m structural mesh connects almost immediately to 40-150 m geology elements.

---

# 6. Far-field M4 geology

Keep the remote geology coarse.

Preferred ordinary far-field edge scale:

**8-20 m**

Do not globally refine the full geological model.

Where the original domain contains very large remote cells, cells larger than 20 m may remain only if all of the following are true:

- they are safely outside the 60 m local engineering zone;
- they do not intersect structure influence regions;
- they do not cross important material boundaries incorrectly;
- aspect ratio is acceptable;
- they do not cause a sudden interface jump back into the M3 zone.

Very remote outer-boundary cells may remain larger than 20 m if justified, but they must be classified separately as:

`M4_REMOTE_BOUNDARY`

and must not be included in near-foundation quality statistics.

---

# 7. Required transition topology

Do not use simple one-to-eight local subdivision that leaves the parent-element boundary nonconformal.

Use one of these approaches:

## Preferred method A — regenerate a larger conformal block

For each affected geological layer:

1. select a sufficiently large contiguous local block;
2. remove the complete block back to a clean coarse-grid boundary;
3. rebuild the entire block with a conformal structured/swept mesh;
4. match the outer boundary exactly to the retained coarse orphan mesh;
5. use integer-compatible edge subdivisions.

## Method B — explicit transition blocks

Where a full block rebuild is not practical:

- create intermediate transition cells;
- use 1-to-2 or similarly controlled hexahedral grading;
- ensure all external faces match the retained orphan mesh exactly;
- ensure all internal interfaces share nodes.

Do not create hanging-node octree-style transitions.

---

# 8. Cutoff-wall/foundation mesh

The cutoff wall is approximately 1 m thick and is already locally refined.

Preserve the wall mesh unless interface-face compatibility requires node alignment.

At the cutoff-wall bottom:

- foundation contact mesh should be comparable in local scale;
- target foundation edge immediately adjacent to wall: approximately **1-2 m**;
- do not connect a ~1 m wall directly to 40+ m geology cells;
- create at least two local transition bands before reaching 5+ m geology.

Audit:

- wall-bottom face node count;
- matching foundation face node count;
- coincident shared-node count;
- unmatched nodes;
- local edge-size ratio.

Target unmatched-node count:

**0**

---

# 9. Powerhouse / spillway / sub-dam foundation interfaces

For each of these:

- powerhouse;
- spillway;
- ecological release;
- stilling basin;
- tailwater;
- left-bank sub-dam;

construct a conformal foundation mesh directly below the contact region.

Required local mesh transition:

- structure contact-side size: approximately 1-2.5 m;
- first foundation layer: approximately 1.5-3 m;
- then 3-4.5 m;
- then 4.5-6.5 m;
- then 6.5-9 m;
- then M4.

Avoid foundation elements with:

- aspect ratio > 8 in M3;
- extremely thin sliver shapes;
- edge ratios that result only from layer thickness errors.

---

# 10. Fishway and left-bank local geology

Preserve the fishway geometry and its structural mesh.

Repair only the geology around:

- fishway trench/excavation;
- sub-dam crossing;
- upstream slope route where local geology was previously cut/remeshed.

The fishway concrete should not become an isolated mesh island if it is intended to be continuous with adjacent concrete pieces.

Do not create extra Tie/contact in this task.

Document structural discontinuities separately if the fishway is intentionally modeled as multiple independent blocks.

---

# 11. Correct regional classification and audit logic

The v15.5 audit mixed some right-bank dam and geology statistics.

V15.6 must classify by explicit instance/material group first, then by distance.

Required top-level groups:

- DAM_FILL;
- GEOMEMBRANE;
- CUTOFF_WALL;
- STRUCTURAL_CONCRETE;
- M3_FOUNDATION_GEOLOGY;
- M4_TRANSITION_GEOLOGY;
- M4_FAR_FIELD_GEOLOGY;
- M4_REMOTE_BOUNDARY.

A dam-fill element must never appear in geology statistics.

A geology element must not simultaneously appear in M3 and M4.

Use unique element identity:

`instance_name + element_label`

to prevent double counting.

Create:

`v15_6_region_classification_audit.csv`

with:

- region;
- unique element count;
- duplicate membership count;
- conflicting classification count;
- status.

All duplicate/conflicting membership counts should be zero.

---

# 12. Recalculate mesh quality from actual connectivity

Use actual element connectivity and node coordinates.

For each region report:

- minimum edge;
- median edge;
- P90;
- P95;
- maximum edge;
- aspect ratio;
- Jacobian/shape metric where available;
- invalid volume count;
- collapsed element count;
- duplicate element count;
- duplicate node count;
- disconnected island count.

Do not infer edge size from part bounding boxes.

---

# 13. Mandatory acceptance criteria for M3

For `M3_FOUNDATION_GEOLOGY`, aim for:

- median edge <= **6 m**;
- P95 edge <= **10 m**;
- max edge <= **15 m** except explicitly documented geological-transition exceptions;
- advisory aspect ratio <= **8**;
- hanging nodes = **0**;
- duplicate coincident nodes at conformal interfaces = **0**;
- mesh holes = **0**;
- overlapping old/new elements = **0**.

If these cannot be achieved, mark the region FAIL or UNRESOLVED.

Do not mark PASS merely because the model contains no negative-volume elements.

---

# 14. Mandatory acceptance criteria for size transitions

Create direct contact-side transition metrics.

For each interface:

- structure P95;
- first-foundation-band P95;
- second-foundation-band P95;
- outer-foundation-band P95;
- M4 transition P95.

Interfaces:

1. cutoff wall to foundation;
2. powerhouse to foundation;
3. spillway to foundation;
4. ecological release to foundation;
5. stilling basin to foundation;
6. tailwater to foundation;
7. sub-dam to foundation;
8. fishway excavation to geology.

Preferred adjacent-band size ratio:

**<= 1.5**

Allow up to **2.0** only where a geological-layer thickness forces it and document the reason.

Any direct >5x jump at an engineering contact is FAIL.

---

# 15. Disconnected-island audit

The v15.5 quality report lists multiple disconnected islands in several regions.

V15.6 must determine whether each island is:

- an intended separate engineering block;
- an unintended disconnected mesh;
- a duplicated mesh fragment;
- a consequence of separate part instances.

Create:

`v15_6_mesh_island_audit.csv`

For every disconnected component report:

- instance;
- component id;
- node count;
- element count;
- bounding box;
- intended/accidental;
- disposition;
- PASS / FAIL / UNRESOLVED.

Do not automatically merge intentionally separate concrete structures.

But for a single continuous geological layer, unintended disconnected components are not acceptable.

---

# 16. Interface node conformity audit

Create:

`v15_6_interface_node_conformity.csv`

Required interfaces:

- cutoff wall / foundation;
- geomembrane / cutoff connection region;
- powerhouse / foundation;
- installation bay / foundation;
- spillway / foundation;
- ecological release / foundation;
- stilling basin / foundation;
- tailwater / foundation;
- sub-dam / foundation;
- remeshed M3 / retained M4 geology.

Report:

- side A face nodes;
- side B face nodes;
- exact-coordinate matches;
- unmatched A nodes;
- unmatched B nodes;
- coincident-but-separate node pairs;
- shared-node count;
- conformity status.

For continuous geology-to-geology interfaces:

- unmatched nodes = 0;
- coincident-but-separate node pairs = 0;
- shared-node topology required.

---

# 17. Node and element count control

Do not optimize by maximizing total element count.

Report v15.5 vs v15.6:

- total nodes;
- total elements;
- structural nodes/elements;
- M3 geology nodes/elements;
- M4 transition nodes/elements;
- M4 far-field nodes/elements.

A moderate increase in M3 is expected.

A large increase in M4 far field should be treated as a warning.

---

# 18. Mesh convergence plan update

Do not run convergence analysis.

Update:

`v15_6_mesh_convergence_plan.csv`

Use:

## COARSE
- structure critical zones: 1.5-2.0 m;
- structures: 2.5-4 m;
- M3: 3-10 m graded;
- M4: 15-30 m.

## MEDIUM — v15.6 working model
- M1: 0.5-1.0 m;
- M2: 1.0-2.5 m;
- M3: 1.5-9 m graded;
- M4: 8-20 m.

## FINE_LOCAL
- M1: 0.35-0.75 m;
- M2: 0.75-1.5 m;
- M3: 1-6 m graded;
- M4 remains 8-20 m.

Never set the entire M4 far field to 2 m.

---

# 19. Actual Abaqus/CAE screenshots

If Abaqus/CAE is available, export actual mesh viewport screenshots.

Required:

1. full hub mesh;
2. cutoff-wall bottom and foundation;
3. cutoff-wall / geomembrane connection;
4. powerhouse foundation;
5. spillway foundation;
6. ecological-release foundation;
7. sub-dam foundation;
8. fishway excavation;
9. M3 graded transition;
10. M3-to-M4 conformal boundary;
11. far-field geology.

Element edges must be visible.

Do not substitute synthetic drawings.

---

# 20. Required outputs

Create under `abaqus-audit/3d-v15.6/`:

- final MEDIUM-mesh INP;
- final CAE if Abaqus is available;
- `V15_6_FOUNDATION_MESH_RESULT.md`;
- `v15_6_geometry_and_structure_freeze_check.csv`;
- `v15_6_region_classification_audit.csv`;
- `v15_6_geology_remesh_map.csv`;
- `v15_6_mesh_density_audit.csv`;
- `v15_6_mesh_quality_audit.csv`;
- `v15_6_mesh_transition_audit.csv`;
- `v15_6_interface_node_conformity.csv`;
- `v15_6_mesh_island_audit.csv`;
- `v15_6_critical_interface_mesh_audit.csv`;
- `v15_6_mesh_convergence_plan.csv`;
- actual CAE screenshots where available.

The result report must explicitly state:

- geometry unchanged: YES/NO;
- structure mesh unchanged except interface alignment: YES/NO;
- M3 rebuilt: YES/NO;
- hanging nodes remaining: count;
- nonconformal geology interfaces remaining: count;
- mesh holes: count;
- overlapping old/new geology elements: count;
- M3 median/P95/max edge;
- worst M3 aspect ratio;
- maximum structure-to-foundation adjacent-band ratio;
- total node/element counts;
- PASS / FAIL / UNRESOLVED summary.

---

# 21. Prohibited

Do not:

- change engineering geometry;
- change materials;
- change permeability;
- change density;
- change elastic parameters;
- add Encastre;
- add springs;
- add artificial nodal restraints;
- add Tie/contact/MPC to hide mesh incompatibility;
- run S01-S07;
- claim structural validation;
- claim seepage validation;
- claim mesh convergence;
- globally refine all geology;
- modify `main`.

---

# Final delivery

Commit all v15.6 work to:

`abaqus-audit-task`

Push normally.

Do not force-push.

Return:

- final commit SHA;
- changed-file list;
- v15.5 vs v15.6 nodes/elements;
- M3 median/P95/max edge;
- worst M3 aspect ratio;
- number of repaired hanging-node interfaces;
- number of remaining nonconformal interfaces;
- mesh-hole count;
- overlap count;
- final INP path;
- final CAE path;
- screenshot paths.
