# V15.10 left-bank sub-dam layout and foundation-interface correction task

## Baseline

Continue from commit:

`b4607c722a171222344fe4faa0b296fa1aaf3515`

Use v15.9 as the starting model.

Work only on:

`abaqus-audit-task`

Do not modify `main`.

Create new outputs under:

`abaqus-audit/3d-v15.10/`

Do not overwrite v15.9.

Do not run S01-S07.

---

# 1. Objective

V15.9 corrected the installation bay, sediment-flushing outlets, and eco/spillway frontage, but the left-bank sub-dam was placed on the wrong side of the installation bay.

The source layout sequence is:

`left-bank sub-dam -> installation bay -> powerhouse -> ecological release -> spillway`

The source explicitly documents:

- a structural joint between gravity-dam block 1 and the installation bay;
- a structural joint between the installation bay and powerhouse;
- left-sub-dam foundation near the installation bay uses compacted backfilled sand/gravel;
- installation bay lies on the left side of the powerhouse;
- installation bay length = 34 m;
- left-bank sub-dam crest length = 89.70 m.

V15.10 shall correct only this left-bank arrangement and the local foundation/excavation consequences.

---

# 2. Coordinate convention

Keep the current model convention:

- X = streamwise;
- Y = dam-axis;
- Z = elevation.

Current accepted v15.9 installation bay:

- Y = **-156.000 to -122.000 m**
- length = **34.000 m**

Therefore the corrected left-bank sub-dam shall be placed directly on the outer/left-bank side of the installation bay.

Target governing Y extent:

`Y = -245.700 to -156.000 m`

Total dam-axis crest length:

`89.700 m`

The interface at:

`Y = -156.000 m`

shall represent the sub-dam / installation-bay structural joint.

Do not preserve the v15.9 sub-dam location:

`Y = -147.700 to -58.000 m`

because that overlaps the installation-bay / powerhouse dam-axis range.

---

# 3. Rebuild the left-bank sub-dam at the corrected location

Preserve the source-based cross-section already adopted in v15.9:

- crest length = 89.70 m;
- crest width = 7.0 m;
- crest elevation = approximately 3079.00 m;
- slope break elevation = 3072.00 m;
- upstream slope below 3072 m = 1:0.2;
- downstream slope below 3072 m = 1:0.6;
- below elevation 3062 m use the documented rectangular lower-section logic;
- local foundation/backfill datum near the installation bay = approximately 3059.00 m.

Do not change these dimensions unless the source report explicitly requires it.

Keep the source discrepancy:

`42.6 + 15 + 15 + 15 = 87.6 m`

versus total crest length:

`89.70 m`

explicitly marked:

`SOURCE_LENGTH_RECONCILIATION_UNRESOLVED = 2.10 m`

Do not invent a fifth block and do not silently stretch a 15 m block.

Create:

`v15_10_subdam_layout_audit.csv`

with:

- old Y extent;
- new Y extent;
- total crest length;
- crest width;
- installation-bay interface Y;
- block-length logic;
- unresolved 2.10 m;
- slopes;
- base/backfill elevations;
- status.

---

# 4. Preserve installation bay and powerhouse

Do not modify the v15.9 installation-bay geometry:

- Y length = 34.0 m;
- lower/foundation X width = 56.5 m;
- upper-room X width = 20.0 m;
- floor elevation = 3062.0 m.

Do not modify the powerhouse geometry.

Verify the dam-axis sequence numerically:

1. sub-dam right/inner end = Y -156.000;
2. installation-bay left/outer end = Y -156.000;
3. installation-bay powerhouse-side end = Y -122.000;
4. powerhouse begins at Y -122.000.

Create:

`v15_10_dam_axis_sequence_audit.csv`

with gap/overlap checks.

Required:

- sub-dam to installation-bay gap = 0;
- installation-bay to powerhouse gap = 0;
- unintended overlap = 0.

---

# 5. Relocate the fishway passage through the corrected sub-dam

The source fishway route must remain physically continuous.

Preserve the documented fishway stationing and geometry:

- total fishway length = 1407.57 m;
- fish 0+948 to 0+955 is the through-dam section;
- through-dam opening = 2.5 m x 7.0 m;
- upstream continuation after the sub-dam crossing remains on the left-bank upstream side;
- downstream route remains connected to the existing tailwater-side route.

The v15.9 fishway through-dam opening was placed inside the old sub-dam location.

V15.10 shall:

- relocate the through-dam opening into the corrected sub-dam;
- reconnect the adjacent fishway centerline smoothly;
- preserve station length 0+948 to 0+955 for the through-dam section;
- preserve total route length as closely as practical;
- do not create a detached fishway segment.

Create:

`v15_10_fishway_relocation_audit.csv`

with:

- old crossing bbox;
- new crossing bbox;
- opening width/height;
- downstream connection;
- upstream connection;
- route continuity;
- stationing status;
- total-length delta;
- status.

---

# 6. Correct the local geology / excavation relationship

This is mandatory.

The v15.9 audit claimed:

- removed geology elements = 0;
- replacement geology elements = 0;

even though major structures had moved.

Do not repeat this assumption.

For the corrected sub-dam and installation-bay area, perform a real spatial check against the active foundation geology.

Required checks:

## A. New corrected sub-dam footprint

Determine whether any active geology elements occupy the physical volume that should be excavated / replaced by the sub-dam or its local foundation treatment.

Target:

- unintended structure-geology volumetric overlap = 0.

If geology occupies the corrected structural volume:

- remove only the affected geology cells/elements;
- preserve geology layer identity and material mapping;
- rebuild local conformal transition only where necessary.

## B. Old v15.9 sub-dam footprint

Check whether the previous sub-dam location created an excavation void or removed geology.

If an old excavation void exists where no structure remains:

- restore the corresponding geology using the original surrounding layer/material identity;
- make the restored mesh conformal with adjacent geology.

If no old geology was ever removed, state that explicitly and prove it by element/topology comparison.

## C. Installation-bay local foundation

Verify the installation bay and corrected sub-dam both sit on the intended local backfill/foundation region and do not penetrate retained geology incorrectly.

Create:

`v15_10_structure_geology_intersection_audit.csv`

with:

- region;
- structure;
- structure bbox;
- geology candidate count;
- actual intersecting geology element count;
- estimated intersection volume if available;
- removed elements;
- restored elements;
- overlap after repair;
- unintended gap;
- status.

Do not use only bbox overlap as proof of physical intersection.

---

# 7. Local geology organization must remain usable

Preserve the v15.8/v15.9 geology organization:

- 36 geology leaf sets;
- 43 Assembly geology sets;
- Material/Section identities;
- no unclassified foundation elements;
- no duplicate leaf membership.

Any locally regenerated geology elements must be assigned back to the correct leaf set.

Create:

`v15_10_geology_set_coverage_audit.csv`

Acceptance:

- unclassified geology elements = 0;
- duplicate leaf membership = 0;
- nonconforming geology faces = 0;
- hanging nodes = 0.

---

# 8. Rebuild only the affected local meshes

Do not globally remesh the model.

Only remesh:

- corrected left-bank sub-dam;
- relocated fishway through-dam section;
- local foundation/backfill/geology cells directly affected by the move.

Preserve all other v15.9 meshes.

For the corrected sub-dam, report actual mesh statistics from element connectivity, not target seed values.

Create:

`v15_10_local_mesh_quality_audit.csv`

Required columns:

- region;
- element type;
- node count;
- element count;
- actual min edge;
- actual median edge;
- actual P95 edge;
- actual max edge;
- max aspect ratio;
- invalid/negative volume count;
- collapsed element count;
- status.

For the left-bank sub-dam, do not mark PASS from a nominal `0.5-2.5 m target` alone.

Suggested structural target:

- representative edge about 1-2.5 m;
- local smaller cells around fishway opening as needed;
- avoid extreme aspect ratios.

---

# 9. Verify all moved-structure interfaces

Check these specific interfaces after correction:

- sub-dam / installation bay;
- sub-dam / local geology;
- installation bay / local geology;
- fishway / sub-dam opening;
- fishway / geology around the crossing;
- left-bank cutoff-wall alignment relative to the corrected left-bank structures.

For each report:

- geometric gap;
- overlap;
- nearest-surface distance;
- mesh-size ratio;
- status.

Do not add Tie/contact/MPC in this task.

---

# 10. Preserve all unaffected v15.9 corrections

Do not change:

- installation bay dimensions;
- powerhouse geometry;
- two sediment-flushing outlets;
- eco-release / spillway adjacency;
- 8 spillway clear openings;
- 109 m combined flood-release frontage;
- tailwater;
- stilling basin;
- geomembrane;
- cutoff wall except only if a local visual/audit update is needed;
- geology parameters.

Do not run S01-S07.

---

# 11. Required CAE screenshots

If Abaqus/CAE is available, export actual viewport screenshots:

1. full hub plan;
2. left-bank sub-dam + installation bay + powerhouse plan;
3. dam-axis view showing the sequence;
4. sub-dam / installation-bay joint;
5. corrected sub-dam mesh;
6. fishway through corrected sub-dam;
7. new sub-dam / geology interface;
8. old v15.9 sub-dam footprint after correction;
9. local geology mesh with element edges;
10. cutoff-wall relationship near the corrected left-bank structures.

Do not use synthetic diagrams.

---

# 12. Required outputs

Create under:

`abaqus-audit/3d-v15.10/`

Required:

- v15.10 CAE;
- v15.10 INP;
- `V15_10_LAYOUT_FOUNDATION_RESULT.md`;
- `v15_10_subdam_layout_audit.csv`;
- `v15_10_dam_axis_sequence_audit.csv`;
- `v15_10_fishway_relocation_audit.csv`;
- `v15_10_structure_geology_intersection_audit.csv`;
- `v15_10_geology_set_coverage_audit.csv`;
- `v15_10_local_mesh_quality_audit.csv`;
- `v15_10_interface_audit.csv`;
- actual CAE screenshots.

The result report must explicitly state:

- final sub-dam Y extent;
- installation-bay Y extent;
- powerhouse Y extent;
- sub-dam -> installation bay gap/overlap;
- installation bay -> powerhouse gap/overlap;
- fishway crossing bbox;
- fishway route continuity;
- structure-geology overlap count before/after;
- restored old-footprint geology element count;
- unclassified geology-element count;
- nonconforming-face count;
- hanging-node count;
- actual sub-dam mesh min/median/P95/max edge;
- max sub-dam aspect ratio;
- PASS / FAIL / UNRESOLVED summary.

---

# 13. Completion criteria

V15.10 is complete only if:

- left-bank sub-dam is entirely on the outer/left-bank side of the installation bay;
- sub-dam and installation bay are directly adjacent at Y = -156.000 m;
- installation bay remains directly adjacent to the powerhouse at Y = -122.000 m;
- no unexplained dam-axis overlap remains;
- fishway through-dam section is inside the corrected sub-dam and continuous;
- corrected structure footprints have no unintended overlap with active geology;
- any obsolete old-footprint excavation is restored or explicitly proven not to exist;
- geology sets/material mapping remain complete;
- nonconforming geology faces = 0;
- hanging nodes = 0.

After V15.10, stop geometry redesign and proceed to a separate Abaqus Data Check task.

---

# Final delivery

Commit all v15.10 work to:

`abaqus-audit-task`

Push normally.

Do not force-push.

Return:

- final commit SHA;
- changed-file list;
- final CAE path;
- final INP path;
- dam-axis sequence audit;
- fishway relocation summary;
- structure-geology intersection summary;
- local mesh-quality summary;
- screenshot paths.
