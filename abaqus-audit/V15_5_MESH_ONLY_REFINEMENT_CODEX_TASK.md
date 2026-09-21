# V15.5 mesh-only refinement task for Codex

## Objective

Continue from commit `82a54e9def606e72049dfee030f92b8265076c47`.

The v15.4 geometry is the frozen baseline.

This task is **mesh-only**.

Do not change the engineering geometry unless a zero-thickness/sliver partition must be repaired solely to make the existing geometry meshable. Any such repair must preserve the external geometry and be documented.

Work only on branch:

`abaqus-audit-task`

Do not modify `main`.

Create all new outputs under:

`abaqus-audit/3d-v15.5/`

Do not overwrite v12, v13, v14, v15, v15.2, v15.3, or v15.4.

Do not run S01-S07 in this task.

---

# 1. Preserve v15.4 geometry exactly

Retain the corrected v15.4 layout:

- 4-unit powerhouse;
- installation bay;
- 2 powerhouse sediment-flushing outlets;
- tailwater channel;
- 8-bay spillway;
- 2-bay ecological-release structure;
- stilling basin;
- left-bank sub-dam;
- full fishway route;
- right-bank dam;
- cutoff wall;
- geomembrane;
- retained geological layering.

Do not move:

- powerhouse;
- spillway;
- ecological-release structure;
- sub-dam;
- fishway;
- cutoff wall;
- geomembrane.

Before remeshing, compare v15.4 and v15.5 instance bounding boxes.

All engineering geometry bounding boxes must match v15.4 within numerical tolerance.

Create:

`v15_5_geometry_freeze_check.csv`

with:

- instance;
- v15.4 bounding box;
- v15.5 bounding box;
- coordinate delta;
- PASS / FAIL.

---

# 2. Correct the current mesh-audit logic before judging mesh quality

The v15.4 reports have two audit problems that must be corrected.

## 2.1 Near-field and far-field geology must be different regions

The current audit reports identical node/element counts for near-foundation and far-field geology.

This is not an acceptable regional audit.

Classify geology by spatial distance to active engineering structures.

Use actual element centroids, not part-level bounding boxes.

At minimum classify:

- M3_NEAR_FOUNDATION;
- M4_TRANSITION_GEOLOGY;
- M4_FAR_FIELD_GEOLOGY.

The same element must not be counted simultaneously as both near-field and far-field.

## 2.2 Mesh edge lengths must be element-by-element

Do not estimate element size from an entire part or instance bounding box.

For each element:

1. use its actual connectivity;
2. calculate all physical element edge lengths;
3. derive minimum, representative/median, P95, and maximum edge length;
4. calculate element-level aspect ratio from actual connected edges or use Abaqus native mesh-quality results.

The reported 1000+ m “edge lengths” must be verified using real connectivity.

If the current value came from instance bounding boxes, replace it with the correct element-level metric.

---

# 3. Mesh strategy

Do not uniformly refine the complete 3D geological domain.

Use graded local refinement.

The working v15.5 model shall use a **MEDIUM engineering mesh**.

Prepare COARSE and FINE_LOCAL seed plans for later convergence analysis, but do not run load cases.

---

# 4. M1 very-fine zones

Use the finest mesh only at locations where geometry or future seepage/stress gradients justify it.

Target characteristic edge length:

**0.5-1.0 m**

Apply to:

- 1 m cutoff wall and its immediate foundation contact;
- cutoff-wall / geomembrane junction;
- geomembrane termination / connection region;
- powerhouse intake openings;
- powerhouse draft-tube / tailrace outlet openings;
- both sediment-flushing outlets;
- spillway bay corners and pier/opening transitions;
- ecological-release openings;
- fishway crossing through the left-bank sub-dam;
- abrupt slab / wall / foundation corners;
- local thin concrete transitions.

### Cutoff wall

The cutoff wall is approximately 1 m thick.

Where feasible, use approximately **2 elements through the 1 m wall thickness** in the local critical zone.

If this produces unacceptable element topology in a retained orphan section, document the limitation rather than creating distorted elements.

### Geomembrane equivalent layer

The retained geomembrane is an equivalent 3D hydraulic layer from the previous model.

Do not reinterpret its thickness as a physical geomembrane thickness.

Refine its in-plane mesh around:

- cutoff-wall connection;
- structure interfaces;
- future defect-study zones.

Avoid the current situation where long in-plane elements reach roughly 30 m in critical regions.

Preferred local in-plane scale near connections / defect-study zones:

**1-3 m**

Away from those zones, a coarser in-plane mesh may remain.

---

# 5. M2 structural zones

Target characteristic edge length:

**1.0-2.5 m**

Apply to:

- powerhouse concrete;
- installation bay;
- spillway piers / abutments / lintels;
- ecological-release structure;
- stilling basin;
- tailwater channel slab / lining / retaining walls;
- left-bank sub-dam;
- fishway concrete body.

Use structured / swept hexahedral topology where practical.

Do not convert regular blocks to tetrahedra merely for convenience.

Preserve current C3D8R-type structural formulation unless a documented local reason requires otherwise.

---

# 6. M3 near-foundation geology

This is the main deficiency in v15.4.

Define a true near-foundation refinement domain using element-centroid distance to the main structures.

Use approximately:

- 0-10 m from foundation/contact surfaces: **1.5-3 m**;
- 10-30 m from structures: **3-5 m**;
- 30-60 m transition band: **5-8 m**.

Apply around:

- powerhouse foundation;
- installation bay;
- spillway;
- ecological release;
- stilling basin;
- tailwater;
- left-bank sub-dam;
- fishway excavation;
- cutoff wall.

The vertical refinement should follow actual geological layer interfaces.

Do not erase geological layering.

Do not merge distinct materials into one homogenized mesh region.

---

# 7. M4 far-field geology

Beyond the local engineering influence zone, retain a coarser mesh.

Target scale:

**8-20 m** for ordinary far-field regions.

Larger elements may remain only where:

- they are genuinely remote from the hub;
- they do not span important layer boundaries;
- they do not produce unacceptable aspect ratio / distortion;
- they are not caused by an audit bug.

Do not refine the entire 1500 m-scale domain to 2 m.

The `FINE_LOCAL` convergence plan must still keep far-field geology coarse.

---

# 8. Required orphan-geology remeshing workflow

The current geology is largely retained orphan C3D8P mesh.

Do not simply relabel the existing orphan mesh as “refined”.

First determine which of these workflows is feasible.

## Preferred workflow A — native geometry exists

If usable native geometric cells/surfaces exist:

1. partition the geology into M3/M4 bands;
2. assign graded seeds;
3. regenerate C3D8P-compatible mesh;
4. preserve geological interfaces and material assignments.

## Workflow B — only orphan mesh exists

If no usable native geometry exists:

1. preserve the far-field orphan mesh;
2. identify elements inside the M3 near-foundation replacement volume;
3. remove only those local orphan elements;
4. reconstruct a local refined mesh from the existing geological interface node/surface data;
5. preserve the same external geological boundaries and material regions;
6. create a compatible transition interface to the retained far-field mesh.

At the interface between replacement mesh and retained orphan mesh:

- prefer shared/merged nodes;
- otherwise create a geometrically matching node pattern;
- do **not** add Tie/contact in this task.

No overlapping old/new geological elements are permitted.

No mesh holes are permitted.

Document every replaced geology block.

Create:

`v15_5_geology_remesh_map.csv`

with:

- source geology instance;
- material/layer;
- retained element count;
- removed element count;
- replacement element count;
- interface-node count;
- conformity status;
- M3/M4 classification.

---

# 9. Mesh transition

Avoid abrupt changes in mesh size.

Preferred growth ratio between adjacent refinement bands:

**<= 1.3-1.5**

Use:

- biased edge seeding;
- transitional partitions;
- intermediate mesh bands.

Do not connect a 0.5 m M1 mesh directly to a 10-20 m M4 mesh in a single layer.

Create a transition audit for:

- cutoff-wall to foundation;
- powerhouse to geology;
- spillway to geology;
- sub-dam to geology;
- tailwater to geology.

---

# 10. Mesh quality checks

Use Abaqus native mesh-quality tools where available.

Otherwise calculate quality from actual element connectivity.

Audit at least:

- minimum edge length;
- median edge length;
- P95 edge length;
- maximum edge length;
- aspect ratio;
- Jacobian / shape metric if available;
- skew / warpage where meaningful;
- zero volume;
- negative volume;
- collapsed elements;
- duplicate elements;
- duplicate nodes;
- disconnected mesh islands;
- non-manifold / unconnected local mesh regions;
- abrupt size-transition ratio.

Do not report a region as PASS solely because no negative volume exists.

### Advisory quality targets

For newly generated structured meshes:

- structural M1/M2: aim for aspect ratio <= 5;
- near-foundation M3: aim for aspect ratio <= 8;
- far-field M4: aim for aspect ratio <= 15 where practical.

If an element exceeds those advisory values:

- list it;
- locate it;
- state whether it is acceptable or requires repair.

Any:

- zero-volume element;
- negative-volume element;
- collapsed element;
- accidental duplicate element

is FAIL.

---

# 11. Critical-interface mesh audit

Create a dedicated audit for future seepage / stress work.

Check mesh density at:

1. cutoff wall top;
2. cutoff wall bottom;
3. cutoff-wall / foundation interface;
4. cutoff-wall / geomembrane connection;
5. geomembrane near connection zone;
6. powerhouse-foundation contact;
7. spillway-foundation contact;
8. ecological-release foundation;
9. sub-dam foundation;
10. fishway crossing through sub-dam.

Create:

`v15_5_critical_interface_mesh_audit.csv`

with:

- interface;
- local element types;
- minimum edge;
- median edge;
- maximum edge;
- elements through thickness where applicable;
- node conformity;
- status;
- notes.

---

# 12. Mesh density output

Create:

`v15_5_mesh_density_audit.csv`

Required regions:

- right-bank dam;
- geomembrane critical zone;
- geomembrane far zone;
- cutoff wall;
- cutoff-wall bottom zone;
- powerhouse;
- powerhouse flushing outlets;
- installation bay;
- tailwater;
- spillway;
- ecological release;
- stilling basin;
- left-bank sub-dam;
- fishway;
- M3 near-foundation geology;
- M4 transition geology;
- M4 far-field geology.

For each report:

- element type;
- min edge;
- median edge;
- P95 edge;
- max edge;
- element count;
- node count;
- refinement class;
- PASS / FAIL / UNRESOLVED.

---

# 13. Mesh convergence plan

Create:

`v15_5_mesh_convergence_plan.csv`

Prepare only the seed plans.

Do not run analyses.

Use three levels:

## COARSE

- M1: 1.5-2.0 m;
- M2: 2.5-4.0 m;
- M3: 4-8 m;
- M4: 15-30 m.

## MEDIUM — working v15.5 mesh

- M1: 0.5-1.0 m;
- M2: 1.0-2.5 m;
- M3: 1.5-8 m graded by distance;
- M4: 8-20 m.

## FINE_LOCAL

Refine only the local engineering zones:

- M1: approximately 0.35-0.75 m;
- M2: approximately 0.75-1.5 m;
- M3 near interfaces: approximately 1-4 m;
- M4 remains approximately 8-20 m.

Do **not** set the whole far-field geology to 2 m in FINE_LOCAL.

---

# 14. Node/element-count control

The objective is not simply to maximize element count.

Report:

- v15.4 total nodes/elements;
- v15.5 total nodes/elements;
- percentage increase;
- counts added in M1;
- counts added in M2;
- counts added in M3;
- counts retained in M4.

If the v15.5 model becomes excessively large because far-field geology was accidentally refined, treat this as FAIL and revise the mesh.

---

# 15. Actual Abaqus viewport verification

If Abaqus/CAE is available, export actual viewport screenshots with element edges visible.

Required mesh views:

1. full hub mesh;
2. powerhouse + foundation mesh;
3. flushing outlet local mesh;
4. spillway / ecological-release mesh;
5. stilling basin transition mesh;
6. cutoff-wall / geomembrane connection mesh;
7. cutoff-wall bottom / foundation mesh;
8. sub-dam / fishway crossing mesh;
9. near-foundation-to-far-field geology transition;
10. far-field geology mesh.

Do not use synthetic drawings as substitutes for CAE mesh screenshots.

---

# 16. Required outputs

Create under `abaqus-audit/3d-v15.5/`:

- final MEDIUM mesh INP;
- final MEDIUM mesh CAE if Abaqus is available;
- `V15_5_MESH_RESULT.md`;
- `v15_5_geometry_freeze_check.csv`;
- `v15_5_geology_remesh_map.csv`;
- `v15_5_mesh_density_audit.csv`;
- `v15_5_mesh_quality_audit.csv`;
- `v15_5_mesh_transition_audit.csv`;
- `v15_5_critical_interface_mesh_audit.csv`;
- `v15_5_mesh_convergence_plan.csv`;
- `v15_5_mesh_inventory.csv`;
- actual CAE mesh screenshots where available.

The result report must explicitly state:

- whether geometry remained unchanged;
- which regions were actually remeshed;
- whether near-field and far-field geology are now distinct;
- whether geomembrane critical zones were refined;
- whether cutoff-wall critical zones were refined;
- total nodes/elements;
- mesh-quality PASS / FAIL / UNRESOLVED;
- any remaining orphan-mesh limitations.

---

# 17. Prohibited

Do not:

- change engineering geometry;
- move structures;
- alter materials;
- alter permeability/density/elastic parameters;
- add supports;
- add Encastre;
- add springs;
- add Tie/contact merely for mesh compatibility;
- run S01-S07;
- claim mesh convergence;
- claim structural validation;
- claim seepage validation;
- globally refine all geology to a fine mesh;
- modify `main`.

---

# Final delivery

Commit all v15.5 mesh-only work to `abaqus-audit-task`.

Push normally.

Do not force-push.

Return:

- final commit SHA;
- changed-file list;
- v15.4 vs v15.5 node/element counts;
- regions actually remeshed;
- maximum / P95 element edge lengths by region;
- worst element-quality locations;
- remaining UNRESOLVED items;
- final INP path;
- final CAE path;
- screenshot paths.
