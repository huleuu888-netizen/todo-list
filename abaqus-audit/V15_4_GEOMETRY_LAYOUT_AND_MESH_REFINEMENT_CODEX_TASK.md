# V15.4 geometry-layout correction and targeted mesh refinement task for Codex

## Goal

Continue from commit `02c7d1664a37d1c008ef48a91e0a8f495d3241f0`.

This task has two phases, in this strict order:

1. correct the remaining **3D geometry / spatial-layout errors** in v15.3;
2. only after the geometry is frozen, perform a **targeted mesh refinement and mesh-quality audit**.

Do not run S01-S07 in this task.

Do not modify `main`.

Work only on `abaqus-audit-task`.

Create all new outputs under:

`abaqus-audit/3d-v15.4/`

Do not overwrite v12, v13, v14, v15, v15.2, or v15.3.

---

# PHASE A — GEOMETRY / SPATIAL LAYOUT CORRECTION

## A1. Keep the global hub ordering fixed

The final hub order from right bank to left bank must remain:

1. right-bank geomembrane sand-gravel dam;
2. 8-bay spillway;
3. 2-bay ecological-release structure;
4. 4-unit riverbed powerhouse;
5. installation bay / left-side powerhouse support area;
6. left-bank sub-dam containing the fishway crossing;
7. left-bank terrain.

Do not move the left-bank sub-dam hundreds of metres away merely to satisfy the fishway route length.

The powerhouse, installation bay, ecological release and spillway define the fixed hub reference frame.

---

## A2. Correct the left-bank sub-dam position

The current v15.3 left-bank sub-dam is spatially incorrect because it is located hundreds of metres away from the powerhouse / installation-bay zone.

### Required correction

- move/rebuild the left-bank sub-dam immediately adjacent to the powerhouse / installation-bay side;
- keep the crest elevation at **3079.00 m**;
- make the sub-dam part of the continuous dam-axis closure;
- connect it geometrically to the left-bank terrain;
- maintain a plausible gravity/stepped profile;
- keep the fishway crossing opening as a real void;
- the fishway opening must remain **2.5 m x 7.0 m**.

Exact surveyed face slopes may remain `UNRESOLVED` if unsupported.

### Acceptance check

The sub-dam centroid / bounding box must be near the powerhouse / installation bay, not near the far downstream fishway turnaround.

The geometry report must explicitly calculate:

- minimum distance from installation-bay solid to sub-dam solid;
- minimum distance from powerhouse-side reference plane to sub-dam;
- whether the dam-axis chain is spatially continuous.

---

## A3. Rebuild the fishway route without moving the sub-dam

The current v15.3 fishway reaches 1407.57 m by using a station-based orthogonal path, but that path effectively dragged the sub-dam to the wrong location.

### Correct modeling logic

Fix the powerhouse and left-bank sub-dam first.

Then construct the fishway around those fixed engineering landmarks.

Known route constraints:

- total route length approximately **1407.57 m**;
- entrance is on the downstream left side of the powerhouse tailwater outlet;
- the fishway initially follows the left side of the tailwater channel;
- the first major downstream reach extends about **380 m**;
- the route then turns back upstream;
- station `0+382.12 ~ 0+416.00`: access-road crossing;
- station `0+416.00 ~ 0+948.00`: upstream-return reach;
- station `0+948.00 ~ 0+955.00`: passes through the left-bank sub-dam;
- station `0+955 ~ 1+250`: upstream-side route;
- outlet structures near `1+250` and `1+270`;
- transition `1+270 ~ 1+370`;
- total route reaches approximately `1+407.57`.

### Elevation constraints

Use:

- lower entrance around **3053.00 m**;
- `0+015 ~ 0+382.12`: approximately **3053.00 -> 3058.50 m**;
- `0+382.12 ~ 0+416.00`: approximately **3059.00 m**;
- sub-dam crossing reach: preserve continuity;
- outlet chamber bottom near **3072.50 m**;
- outlet chamber top near **3079.00 m**;
- `1+270 ~ 1+370`: approximately **3072.50 -> 3073.50 m**.

### Section

Retain:

- clear passage width **2.0 m**;
- wall thickness **0.5 m**;
- bottom slab thickness **0.5 m**.

### Important rule

Do **not** require every fishway station to be represented by a single straight X- or Y-aligned segment.

Use a polyline / spline / piecewise-sweep route that:

- respects the actual fixed hub geometry;
- provides the documented total station length;
- returns to the real left-bank sub-dam;
- does not relocate the sub-dam.

If exact surveyed horizontal alignment is unavailable, mark the plan alignment as `UNRESOLVED`, but preserve the correct engineering relationship.

---

## A4. Correct the abnormal spillway right-end geometry

The current v15.3 model has an abnormal terminal spillway pier / block approximately **36 m** wide.

That is not acceptable as a normal intermediate pier.

### Required correction

- keep exactly **8 open spillway bays**;
- keep each clear bay width **7.00 m**;
- keep the gate/opening heights already corrected;
- keep the chamber streamwise length approximately **30 m**;
- keep crest elevation approximately **3079.00 m**;
- retain realistic intermediate piers;
- replace the 36 m terminal “pier” with an explicit right abutment / side structure / transition block, if a large transition width is actually needed;
- do not label a large closure block as an ordinary pier.

The final inventory must distinguish:

- intermediate pier(s);
- left side wall / abutment;
- right side wall / abutment;
- transition / guide-wall structure.

No individual object named `PIER_XX` should carry an obviously artificial 30+ m dam-axis width merely to absorb unused span.

---

## A5. Correct ecological-release vertical geometry

The v15.3 model currently interprets the documented “maximum height 27.5 m” as:

`3058.0 + 27.5 = 3085.5 m`

This is not acceptable as a direct inference.

### Known geometry to retain

- two bays;
- each working opening width approximately **2.5 m**;
- each working opening height approximately **5.0 m** (or 5.2 m where matching the gate-system source is intentionally chosen and documented);
- inlet bottom elevation **3058.00 m**;
- total dam-axis length **12.50 m**;
- left pier **3.0 m**;
- center pier **2.5 m**;
- right pier **2.0 m**;
- chamber length approximately **30 m**;
- overall hub crest system near **3079.00 m**.

### Required correction

Rebuild the upper structure so that:

- the principal dam-top / crest relationship remains near **3079.00 m**;
- the 27.5 m value is treated as a structural maximum-height descriptor, not blindly added to the inlet sill;
- any deeper foundation / base used to satisfy the overall 27.5 m structural height must be represented below the inlet opening if source geometry supports it;
- if exact foundation bottom is not available, mark the exact overall height reconciliation `UNRESOLVED`.

Do not allow the visible top of the ecological-release structure to rise to 3085.5 m unless a direct source supports that elevation.

---

## A6. Add the missing two sediment-flushing outlets inside the powerhouse

The source design includes a sediment-flushing system inside the powerhouse unit piers.

### Layout

- sediment-flushing system located in the unit-section intermediate piers;
- **2 units share 1 flushing outlet**;
- total = **2 flushing outlets** for the 4-unit powerhouse.

### Source-supported opening data

For each flushing outlet:

- upstream accident-gate sill elevation: **3037.00 m**;
- upstream opening size: **2.5 m x 2.0 m**;
- downstream working-gate sill elevation: **3043.00 m**;
- downstream opening size: **2.5 m x 2.0 m**.

### Required geometry

Add two real flow corridors/voids through the relevant powerhouse intermediate-pier zones.

The geometry should reflect:

- 2-unit-per-outlet arrangement;
- upstream intake opening;
- internal flushing passage;
- downstream outlet;
- no positive-volume collision with the main unit water passages.

Do not model detailed gates or hydraulic machinery.

Add a `v15_4_sediment_flushing_audit.csv` with:

- outlet 01 / outlet 02;
- host unit-pier region;
- upstream sill elevation;
- downstream sill elevation;
- width;
- height;
- continuity status.

---

## A7. Geology / excavation correction

The v15.3 orphan-mesh element-removal approach is acceptable only as an interim representation.

For v15.4:

- preserve all successfully removed conflicting orphan-mesh cells;
- do not restore the uncut geology;
- do not claim native solid Boolean certification unless a true CAE geometry Boolean has actually been performed;
- where native geometry is unavailable, keep the result explicitly labeled `ORPHAN_MESH_EXCAVATION_RESULT`;
- ensure no excavation cutter remains active and overlapping the final geology.

Also correct excavation geometry after relocating the sub-dam and rerouting the fishway.

---

# PHASE B — TARGETED MESH REFINEMENT

Only start this phase after all Phase-A geometry checks are PASS or explicitly UNRESOLVED for source-data limitations.

## B1. Do not globally refine the entire 3D model

A uniformly fine mesh across the whole deep geological domain is prohibited.

Use **graded local refinement**.

---

## B2. Preserve element formulation unless there is a clear reason to change it

- retain the current geology pore-pressure-compatible solid formulation where applicable;
- do not change all element types merely to improve appearance;
- prioritize structured / swept hexahedral topology where geometry permits;
- avoid unnecessary tetrahedral conversion of large regular blocks.

If an existing orphan mesh cannot be remeshed directly, document that limitation and refine by creating locally improved replacement mesh only where justified.

---

## B3. Mesh refinement zones

### Zone M1 — very fine local geometry

Refine around:

- cutoff-wall / geomembrane connection;
- spillway openings and pier corners;
- ecological-release openings;
- powerhouse intake openings;
- powerhouse tailrace / draft-tube openings;
- new sediment-flushing outlets;
- fishway sub-dam opening;
- local foundation corners;
- thin concrete lining / slab transition regions.

Target characteristic size: **0.5 to 1.0 m**.

For thin 3D solids, aim for **2-3 elements through thickness** when computationally reasonable.

### Zone M2 — refined structural zone

For powerhouse, installation bay, spillway, ecological release, stilling basin, tailwater, sub-dam and fishway:

Target characteristic size: **1.0 to 2.5 m**.

### Zone M3 — near-foundation geology

Immediately below and around the main structures and cutoff wall:

Target characteristic size: **2 to 5 m**.

### Zone M4 — far-field geology

For remote geology:

Use a substantially coarser mesh, approximately **8 to 20+ m** depending on topology.

---

## B4. Mesh-transition requirement

Avoid abrupt size jumps.

Prefer a growth ratio <= **1.3-1.5** between adjacent refinement bands.

Use transition partitions / bias seeding where possible.

---

## B5. Mesh-quality requirements

Check at least:

- aspect ratio;
- element distortion / shape metric;
- Jacobian or equivalent Abaqus quality indicator where available;
- minimum and maximum edge length;
- warped/skewed elements;
- zero/negative volume;
- disconnected mesh islands;
- duplicate nodes/elements;
- accidental sliver elements.

No negative-volume, zero-volume, or collapsed elements are allowed.

---

## B6. Mesh-density audit by engineering region

Create `v15_4_mesh_density_audit.csv`.

Include:

- region;
- element type;
- minimum element size;
- representative element size;
- maximum element size;
- element count;
- node count;
- refinement zone M1/M2/M3/M4;
- status;
- reason.

Required regions:

- right-bank dam;
- geomembrane;
- cutoff wall;
- powerhouse;
- powerhouse flushing outlets;
- installation bay;
- tailwater;
- spillway;
- ecological release;
- stilling basin;
- left-bank sub-dam;
- fishway;
- near-foundation geology;
- far-field geology.

---

## B7. Mesh convergence preparation only

Do not run load cases yet.

Prepare three mesh levels for later convergence testing:

- `COARSE`
- `MEDIUM`
- `FINE_LOCAL`

The v15.4 working CAE may use `MEDIUM`.

Create `v15_4_mesh_convergence_plan.csv` with region-by-region seed sizes for all three levels.

Do not claim mesh convergence until later simulations are actually run.

---

# PHASE C — FINAL GEOMETRY + MESH AUDIT

Verify geometry:

- sub-dam adjacent to powerhouse / installation-bay zone;
- fishway reaches the real sub-dam while preserving approximately 1407.57 m station length;
- sub-dam crest 3079.00 m;
- fishway crossing 2.5 x 7.0 m;
- spillway 8 bays x 7.0 m clear width;
- no artificial 36 m intermediate pier;
- ecological-release visible crest compatible with ~3079 m;
- 2 ecological-release openings;
- 2 powerhouse sediment-flushing outlets;
- tailwater clear channel width remains 71.6 m;
- excavation geometry updated for moved sub-dam and fishway.

Verify mesh:

- local refinement at openings and foundations;
- no uniform global over-refinement;
- smooth transition to coarse geology;
- no invalid elements;
- per-region counts reported;
- no accidental mesh holes.

---

# REQUIRED OUTPUTS

Create under `abaqus-audit/3d-v15.4/`:

- corrected v15.4 INP;
- corrected v15.4 CAE if Abaqus is available;
- `V15_4_GEOMETRY_MESH_RESULT.md`;
- `v15_4_instance_inventory.csv`;
- `v15_4_dimension_audit.csv`;
- `v15_4_layout_audit.csv`;
- `v15_4_opening_audit.csv`;
- `v15_4_sediment_flushing_audit.csv`;
- `v15_4_excavation_audit.csv`;
- `v15_4_interference_audit.csv`;
- `v15_4_fishway_station_audit.csv`;
- `v15_4_mesh_density_audit.csv`;
- `v15_4_mesh_quality_audit.csv`;
- `v15_4_mesh_convergence_plan.csv`;
- actual Abaqus viewport screenshots where available.

Required screenshots include full hub, upstream, downstream, dam-axis, left-bank oblique, fishway full route, sub-dam crossing close-up, sediment-flushing close-up, spillway/ecological-release close-up, and mesh views of powerhouse, spillway/eco, sub-dam/fishway and structure-to-geology transition.

Screenshots must be actual CAE viewport images, not synthetic diagrams.

---

# PROHIBITED IN THIS TASK

Do not:

- run S01-S07;
- claim mechanical or seepage validation;
- add artificial constraints to suppress singularities;
- change materials;
- globally refine the whole geological domain;
- overwrite previous versions;
- modify `main`.

---

# FINAL DELIVERY

Commit all v15.4 geometry and mesh work to `abaqus-audit-task`.

Push normally. Do not force-push.

Return:

- final commit SHA;
- changed-file list;
- geometry PASS / FAIL / UNRESOLVED summary;
- mesh-quality PASS / FAIL / UNRESOLVED summary;
- total node / element counts;
- per-region mesh counts;
- final INP path;
- final CAE path;
- screenshot paths.
