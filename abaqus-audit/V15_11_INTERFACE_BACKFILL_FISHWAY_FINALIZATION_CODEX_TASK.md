# V15.11 interface, backfill and fishway finalization task

## Baseline

Continue from commit:

`c7ded8ff485cb2dff92421bf1ee0fe180628fac5`

Use the v15.10 model as the baseline.

Work only on:

`abaqus-audit-task`

Do not modify `main`.

Create all outputs under:

`abaqus-audit/3d-v15.11/`

Do not overwrite v15.10.

Do not run S01-S07.

This task is intended to be the **last geometry/interface cleanup before a separate Abaqus Data Check task**.

---

# 1. Critical issues to fix

V15.10 corrected the dam-axis order, but its own interface audit still contains three unresolved modeling problems:

1. `subdam_installation_bay` has an actual nearest-surface gap of about **22.15 m** yet was marked PASS.
2. `subdam_local_geology` has an actual nearest-surface gap of about **5.225 m** yet was marked PASS.
3. the relocated fishway has geometric length **1450.20671 m** versus source station length **1407.57 m**, delta **42.63671 m**.

The first two PASS labels are invalid. A common Y coordinate is not sufficient to prove a structural joint, and absence of overlap is not sufficient to prove a foundation is supported.

V15.11 must correct the geometry, not merely relabel the audits.

---

# 2. Preserve the accepted dam-axis sequence

Do not undo the v15.10 Y layout:

- left-bank sub-dam: `Y=-245.700..-156.000 m`;
- installation bay: `Y=-156.000..-122.000 m`;
- powerhouse begins at `Y=-122.000 m`.

Preserve:

- sub-dam crest length = 89.70 m;
- installation-bay length = 34.00 m;
- installation-bay floor elevation = 3062.00 m;
- powerhouse geometry;
- v15.9 sediment-flushing corrections;
- eco-release / spillway layout;
- 8 spillway bays;
- 109 m flood-release frontage.

Only change X/Z placement or local interface geometry where required by this task.

---

# 3. Correct the real sub-dam / installation-bay structural joint

## Current defect

V15.10 reports:

- sub-dam X envelope approximately `-101..-86.15 m`;
- installation-bay X envelope approximately `-64..-7.5 m`;
- nearest physical surface distance about **22.15 m**.

Therefore the two structures do not form a real structural joint even though both end/start at `Y=-156 m`.

## Source requirement

The source identifies:

- a joint between gravity-dam block 1 and the installation bay;
- a joint between installation bay and powerhouse;
- the installation bay lies on the left side of the powerhouse;
- the left-bank sub-dam is immediately adjacent to the installation-bay side.

## Required correction

Reposition/rebuild the **sub-dam streamwise X placement** so that at `Y=-156 m` it physically meets the installation-bay dam block.

Do not simply translate the sub-dam until bounding boxes touch.

Determine the correct X position using, in order:

1. the actual assembly-coordinate dam/cutoff-wall alignment;
2. the installation-bay structural cross-section at `Y=-156 m`;
3. the source sub-dam section geometry;
4. the source statement that the left-sub-dam cutoff wall is aligned with the left-bank structure cutoff system.

The current part-local cutoff-wall bbox must not be treated as an assembly coordinate. Audit the transformed Assembly geometry.

### Structural-joint acceptance

At the sub-dam / installation-bay joint:

- minimum actual surface gap <= **1 mm**;
- unintended overlap volume = **0**;
- actual contact/intersection area > **0**;
- the contact must occur at the intended dam-block cross-section, not through an accidental corner touch;
- sub-dam Y end remains `-156.000 m`;
- installation-bay Y start remains `-156.000 m`.

Create:

`v15_11_subdam_installation_joint_audit.csv`

with:

- sub-dam X/Z section at joint;
- installation-bay X/Z section at joint;
- minimum face distance;
- contact area;
- overlap volume;
- cutoff-wall relative offset;
- status.

Any gap greater than 1 mm must be FAIL/UNRESOLVED, not PASS.

---

# 4. Verify the installation-bay / powerhouse interface physically

V15.10 only verified their common Y plane.

Perform a real face-to-face audit at `Y=-122 m`.

Required:

- minimum surface gap;
- actual contact area;
- overlap volume;
- X/Z overlapping extent.

If the installation-bay lower foundation envelope is offset relative to the powerhouse but still has a physically valid documented structural joint, preserve it.

If there is no physical joint, report it as UNRESOLVED before changing the powerhouse.

Do not modify powerhouse geometry in this task unless a source-documented correction is absolutely required.

Create:

`v15_11_installation_powerhouse_joint_audit.csv`.

---

# 5. Correct the 5.225 m sub-dam foundation gap

## Source requirement

The source states:

- the powerhouse sides use backfilled sand/gravel as foundation for the installation bay and left sub-dam;
- near the installation bay, the left-sub-dam foundation is compacted backfilled sand/gravel;
- the left-sub-dam local backfill/foundation datum is around elevation **3059.00 m**;
- the natural left-side foundation is an excavated slope, so the entire 89.7 m sub-dam does not necessarily use one uniform backfill prism.

Therefore a 5.225 m empty vertical/spatial gap cannot simply be accepted.

## Required modeling approach

Build only the **source-supported local compacted sand/gravel backfill region** necessary to connect:

- the installation-bay foundation;
- the inner/right end of the left-bank sub-dam;
- the actual retained geology/excavation surface.

Do not fill the entire left-bank slope with an arbitrary rectangular block.

Use the actual retained-geology surface as the lower/side boundary and the structure foundation surface as the upper boundary.

### Preferred topology

Prefer integrating the backfill into the conformal foundation mesh so that:

- backfill-to-geology internal interfaces are conformal/shared-node interfaces;
- no hanging nodes are created;
- no overlapping geology remains;
- the backfill region has its own named set/section identity.

Suggested names:

- `FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL`
- `ASSEM_FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL`
- `SEC_FOUNDATION_LEFT_COMPACTED_SAND_GRAVEL`

Do not classify this engineered backfill as a natural geology leaf set unless the existing model organization requires it.

## Material mapping rule

First search the existing model and source-derived material definitions for an explicit compacted sand/gravel or backfill material.

Do not invent density, elastic parameters, permeability, porosity, or strength.

If an exact backfill material exists, use it.

If no exact backfill material exists but an existing sand/gravel material is used elsewhere for the documented compacted fill, reuse that existing material and mark the mapping source.

If the only defensible temporary mapping is an existing `Q3AL_III`-type sand/gravel material, it may be used **only as an explicitly documented modeling assumption**:

`BACKFILL_MATERIAL_MAPPING_UNRESOLVED`

Do not silently claim it is source-verified.

Because the later study includes seepage, the engineered backfill must retain pore-pressure/seepage capability if the selected material formulation supports it; prefer a pore-pressure solid element such as C3D8P rather than converting the backfill into a purely structural C3D8R region.

Create:

`v15_11_backfill_material_basis.csv`.

---

# 6. Backfill / foundation acceptance

After repair:

- sub-dam foundation-to-backfill minimum gap <= **1 mm** in the backfilled portion;
- installation-bay foundation-to-backfill minimum gap <= **1 mm** where backfill is required;
- backfill-to-retained-geology internal gap = **0**;
- backfill-to-geology nonconforming faces = **0**;
- hanging nodes = **0**;
- overlap volume between backfill and retained geology = **0**;
- overlap volume between backfill and structural solids = **0** except coincident interface surfaces;
- no unsupported 5.225 m void remains beneath the corrected sub-dam near the installation-bay side.

Create:

`v15_11_foundation_support_audit.csv`.

Report actual supported-area percentage of the sub-dam base, separated into:

- natural/excavated foundation;
- compacted backfill foundation;
- unsupported.

Acceptance:

`unsupported base area = 0`

unless a documented opening is intended.

---

# 7. Refit the fishway to the source station length

## Current defect

V15.10:

- source/station length = **1407.57 m**;
- geometric route length = **1450.20671 m**;
- delta = **+42.63671 m**.

The problem was created by forcing the through-dam crossing to the outer edge of the relocated sub-dam and then connecting it with a long diagonal reach.

## Source constraints to preserve

- total fishway length = **1407.57 m**;
- fish 0+015 to 0+382.12: tailwater-left-slope reach;
- fish 0+382.12 to 0+416: access-road crossing reach;
- fish 0+416 to 0+948: along the left side of the access road;
- fish 0+948 to 0+955: through left sub-dam;
- through-dam opening = **2.5 m x 7.0 m**;
- after crossing, route continues on the upstream left-bank side;
- source station 1+250 and 1+270 outlet structures and later transition must retain their station relationships.

## Required correction

Do **not** force the crossing to `Y=-245.700..-243.200` merely because it is the outer edge of the sub-dam.

Choose the fishway crossing location **within the corrected 89.70 m sub-dam** so that:

1. the 0+416 -> 0+948 route can remain physically plausible along the access-road side;
2. the 0+948 -> 0+955 through-dam section is exactly 7 m by station;
3. the route is continuous;
4. cumulative geometric length matches the stationing.

The stationing must govern the route length.

### Length tolerances

Target:

- 0+416 -> 0+948 geometric centerline length = **532.00 m +/- 0.50 m**;
- 0+948 -> 0+955 = **7.00 m +/- 0.05 m**;
- total centerline length = **1407.57 m +/- 0.50 m**.

If exact surveyed plan coordinates are unavailable, use the simplest physically plausible polyline/curve consistent with the described access-road alignment and clearly label the plan shape as simplified.

Do not retain a 42.64 m length error.

Create:

`v15_11_fishway_station_length_audit.csv`

with cumulative geometric length at at least:

- 0+015;
- 0+104.77;
- 0+382.12;
- 0+416;
- 0+948;
- 0+955;
- 1+250;
- 1+270;
- 1+370;
- route end 1+407.57.

For every station report:

- target chainage;
- geometric cumulative length;
- delta;
- coordinate;
- status.

---

# 8. Preserve fishway section geometry

Do not change the source-based fishway functional dimensions merely to force route length.

Preserve, where already modeled:

- through-dam opening 2.5 x 7.0 m;
- passage width approximately 2.0 m;
- wall/bottom thickness approximately 0.5 m where applicable;
- downstream entrance elevations;
- upstream outlet elevations;
- station identities.

Only the plan alignment and affected local mesh should change.

---

# 9. Re-audit the cutoff-wall relationship in Assembly coordinates

V15.10 marked the cutoff-wall relationship PASS without actually updating the local sub-dam arrangement.

V15.11 shall measure the relevant cutoff-wall geometry in **Assembly/global coordinates**, after all transforms.

Verify:

- left-sub-dam cutoff line;
- installation-bay / powerhouse cutoff line;
- continuity/alignment of the anti-seepage system;
- whether a connecting plate/transition is required geometrically.

Do not alter the entire cutoff wall unless the source and actual global-coordinate audit require it.

Create:

`v15_11_cutoff_alignment_audit.csv`.

---

# 10. Real interface auditing rules

Do not use only AABB/bounding-box separation.

For every critical interface, use actual geometry/mesh faces or element-face proximity.

At minimum audit:

- sub-dam / installation bay;
- installation bay / powerhouse;
- sub-dam / compacted backfill;
- installation bay / compacted backfill;
- backfill / retained geology;
- fishway / sub-dam opening;
- fishway / local foundation;
- cutoff wall / left-bank structures.

For each report:

- actual minimum surface distance;
- actual overlap volume;
- contact/coincident area;
- face/node counts;
- status.

A positive physical gap may not be marked PASS merely because dam-axis stationing matches.

---

# 11. Local mesh policy

Do not globally remesh.

Preserve all unaffected v15.10 meshes.

Only regenerate:

- shifted/repositioned left-sub-dam geometry if needed;
- local sub-dam/installation joint;
- new compacted-backfill region;
- immediately adjacent foundation cells required for conformity;
- refitted fishway reach/crossing.

Report actual mesh statistics from connectivity:

- min edge;
- median edge;
- P95 edge;
- max edge;
- max aspect ratio;
- invalid/negative volume;
- collapsed elements.

Suggested scale:

- sub-dam structural mesh ~1-2.5 m;
- fishway crossing ~0.25-1.5 m locally;
- compacted backfill ~1.5-3 m near structures, grading outward;
- do not create abrupt >2:1 local size jumps where avoidable.

Create:

`v15_11_local_mesh_quality_audit.csv`.

---

# 12. Preserve model organization

Keep the v15.10 clean organization.

Existing natural geology sets, sections and materials must remain identifiable.

If engineered backfill is added, document it separately.

Required:

- natural geology unclassified elements = 0;
- duplicate natural-geology leaf membership = 0;
- nonconforming continuous-foundation faces = 0;
- hanging nodes = 0;
- no duplicate overlapping foundation bodies.

Create:

`v15_11_foundation_set_coverage_audit.csv`.

---

# 13. Required actual CAE screenshots

If Abaqus/CAE is available, export actual viewport screenshots:

1. full hub plan;
2. left sub-dam + installation bay + powerhouse plan;
3. sub-dam/installation joint close-up with mesh;
4. installation/powerhouse joint close-up;
5. section through sub-dam/installation joint showing X/Z contact;
6. compacted-backfill foundation body/region;
7. sub-dam foundation support view with geology/backfill;
8. fishway 0+416 -> 0+955 plan;
9. fishway through-dam crossing;
10. cutoff-wall alignment in left-bank area;
11. local foundation mesh;
12. full corrected left-bank layout.

Do not use synthetic diagrams as substitutes.

---

# 14. Required outputs

Create under:

`abaqus-audit/3d-v15.11/`

Required:

- v15.11 CAE;
- v15.11 INP;
- `V15_11_INTERFACE_BACKFILL_FISHWAY_RESULT.md`;
- `v15_11_subdam_installation_joint_audit.csv`;
- `v15_11_installation_powerhouse_joint_audit.csv`;
- `v15_11_backfill_material_basis.csv`;
- `v15_11_foundation_support_audit.csv`;
- `v15_11_fishway_station_length_audit.csv`;
- `v15_11_cutoff_alignment_audit.csv`;
- `v15_11_interface_audit.csv`;
- `v15_11_local_mesh_quality_audit.csv`;
- `v15_11_foundation_set_coverage_audit.csv`;
- actual CAE screenshots.

The result report must explicitly state:

- final sub-dam X/Y bbox;
- final installation-bay bbox;
- sub-dam/installation minimum gap and contact area;
- installation/powerhouse minimum gap and contact area;
- backfill region volume and material/section mapping;
- sub-dam supported-base percentage;
- unsupported-base percentage;
- fishway total geometric length;
- fishway 0+416->0+948 length;
- fishway crossing bbox;
- cutoff-wall alignment result;
- nonconforming foundation faces;
- hanging nodes;
- PASS / FAIL / UNRESOLVED summary.

---

# 15. Acceptance criteria

V15.11 is acceptable only if:

- sub-dam and installation bay form a real physical structural joint, not merely a shared Y coordinate;
- sub-dam/installation gap <= 1 mm;
- joint contact area > 0;
- unintended overlap volume = 0;
- installation/powerhouse interface is physically audited;
- the 5.225 m unsupported local sub-dam foundation void is eliminated by real foundation/backfill geometry or proven source-correct geometry;
- unsupported sub-dam base area = 0;
- backfill/geology interfaces are conformal with hanging nodes = 0;
- fishway total geometric length is within 0.50 m of 1407.57 m;
- 0+416->0+948 length is within 0.50 m of 532.00 m;
- through-dam section is within the corrected sub-dam and 7.00 m by station;
- natural geology identity remains usable;
- no global remesh is performed.

After this task, do not start another geometry redesign cycle unless V15.11 produces a genuine source contradiction.

Proceed next to a separate Abaqus Data Check task.

---

# 16. Prohibited

Do not:

- change main;
- force-push;
- globally remesh;
- change unrelated spillway/eco/tailwater/powerhouse geometry;
- invent material properties;
- add Tie/contact/MPC/springs/artificial restraints;
- run S01-S07;
- claim the model is solver-validated;
- mark positive unsupported gaps as PASS.

---

# Final delivery

Commit all v15.11 work to:

`abaqus-audit-task`

Push normally.

Return:

- final commit SHA;
- changed-file list;
- final CAE path;
- final INP path;
- joint audit summary;
- foundation/backfill summary;
- fishway station-length summary;
- cutoff alignment summary;
- local mesh-quality summary;
- screenshot paths.
