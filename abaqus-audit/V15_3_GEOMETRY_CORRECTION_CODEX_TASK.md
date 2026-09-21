# V15.3 geometry correction task for Codex

## Goal

Continue from commit `58fdf1dd4f81403e52d6aa40d9f1fe20ef3be5a7` and correct the remaining geometry errors in the Duobu hydropower 3D model.

This remains a **geometry-only** task.

Do **not** perform S01-S07, solver debugging, material tuning, contact optimization, rigid-body repair, or hydraulic validation.

## Branch and version safety

- Work only on branch `abaqus-audit-task`.
- Do not modify `main`.
- Do not overwrite v12, v13, v14, v15, or v15.2.
- Create all new outputs under:
  `abaqus-audit/3d-v15.3/`
- Use the current v15.2 geometry as the starting point.
- Preserve already-correct powerhouse, installation-bay, and tailwater major envelopes unless a local correction is needed to connect corrected geometry.

---

## 1. Correct the fishway: current v15.2 route is incomplete

The current v15.2 fishway is only a short simplified body and does not represent the actual route length/elevation development.

### Required design geometry

Use the following documented fishway layout:

- total fishway length: approximately **1407.57 m**;
- fishway starts near the downstream left side of the powerhouse tailwater outlet;
- first reach extends downstream along the left side of the tailwater channel;
- fishway reaches about station `0+382.12` before the road-crossing reach;
- station `0+382.12 ~ 0+416.00`: crosses the powerhouse access road;
- station `0+416.00 ~ 0+948.00`: returns upstream along the left side of the access road;
- station `0+948.00 ~ 0+955.00`: passes through the left-bank sub-dam;
- after crossing the sub-dam, continue upstream along the left-bank slope;
- outlet structures occur near stations `1+250` and `1+270`;
- transition continues at least toward station `1+370`;
- total route should remain consistent with the documented total length.

### Fishway elevation targets

Use these source-supported values:

- entrance / lower fishway around elevation **3053.00 m**;
- reach `0+015 ~ 0+382.12`: fishway platform rises approximately **3053.00 -> 3058.50 m**;
- road crossing `0+382.12 ~ 0+416.00`: bottom elevation approximately **3059.00 m**;
- downstream-to-upstream return reach continues climbing;
- outlet chamber bottom elevation near **3072.50 m**;
- outlet chamber top elevation approximately **3079.00 m**;
- transition reach `1+270 ~ 1+370`: bottom elevation approximately **3072.50 -> 3073.50 m**.

### Fishway section

Retain simplified structural section:

- clear passage width: **2.0 m**;
- side-wall thickness: **0.5 m**;
- bottom-slab thickness: **0.5 m**.

For the reach along the tailwater left slope:

- supporting bottom platform width approximately **4.0 m** where represented;
- local concrete slope below the platform should reflect the documented **1:2.25** relationship where feasible.

After the sub-dam crossing:

- represent the fishway in the upstream left-bank excavated trapezoidal corridor;
- side excavation slope approximately **1:1.75**.

Do not reduce the whole fishway back to a 200-300 m schematic path.

If exact plan coordinates are unavailable, preserve station-based length/elevation logic and mark only unresolved plan details as `UNRESOLVED`; do not shorten the engineering route.

---

## 2. Correct the left-bank sub-dam height and crest

The current v15.2 sub-dam top around elevation 3060 m is incorrect.

### Required correction

- final sub-dam crest elevation: **3079.00 m**;
- geometrically connect the sub-dam to the left-bank terrain;
- maintain a credible upstream and downstream face rather than a simple rectangular block;
- preserve the fishway crossing through the sub-dam;
- keep the foundation footprint compatible with the left-bank excavation / fill context.

Do not invent unsupported detailed slopes. If exact face slopes are not available, use a conservative simplified stepped/gravity-type profile and flag the exact slope geometry `UNRESOLVED`.

---

## 3. Correct the fishway sub-dam crossing opening

The current audit reports a modeled opening of roughly 4.0 x 7.0 m, while the documented crossing opening is:

- **2.5 m x 7.0 m**

Correct the opening geometry to the documented dimensions.

The opening must be a real void through the sub-dam, not positive-volume overlap between fishway and dam solid.

---

## 4. Correct ecological-release geometry

The current v15.2 geometry incorrectly treats 12.5 m as the clear width of each ecological-release bay.

### Documented geometry

The ecological-release structure has:

- 2 low-level bays;
- total dam-axis length: **12.50 m**;
- left pier thickness: **3.0 m**;
- center pier thickness: **2.5 m**;
- right pier thickness: **2.0 m**;
- each working-gate opening: **2.5 m x 5.0 m** (width x height);
- inlet bottom elevation: **3058.00 m**;
- upstream/downstream chamber length approximately **30 m**;
- maximum structure height about **27.5 m**;
- crest / top width around **16.0 m** where represented.

### Required correction

Rebuild the two ecological-release openings so that:

- each opening clear width is **2.5 m**;
- each opening clear height is **5.0 m**;
- pier thicknesses match 3.0 / 2.5 / 2.0 m;
- the whole dam-axis extent remains consistent with **12.50 m**;
- the two openings remain true voids;
- downstream geometry continues toward the shared stilling basin.

Update the dimension audit so it no longer reports “12.5 m per bay” as PASS.

---

## 5. Correct spillway opening width and spillway structural layout

The spillway remains an 8-bay final arrangement.

### Documented opening dimensions

For each spillway bay:

- clear gate/opening width: **7.00 m**;
- inspection gate opening height: approximately **7.73 m**;
- working radial-gate opening height: approximately **5.20 m**;
- spillway chamber streamwise length: approximately **30 m**;
- final crest/top elevation: approximately **3079.00 m**.

### Required correction

Rebuild the spillway so the clear bay width is **7.00 m**, not 10 m.

Maintain:

- 8 open bays;
- intermediate piers;
- left and right side structures;
- actual open hydraulic corridors;
- no solid blocks occupying the flow openings.

Do not infer unsupported pier thicknesses from the current v15.2 geometry. Use source-supported dimensions where available; otherwise retain the minimum geometry necessary and mark uncertain pier-width details `UNRESOLVED`.

---

## 6. Correct the spillway stilling-basin slab thickness

The current v15.2 model incorrectly uses a **0.8 m** slab thickness for the spillway stilling basin.

The documented spillway stilling basin is:

- length: **107 m**;
- slab top elevation: **3047.50 m**;
- slab thickness: **2.50 m**.

### Required correction

Change the stilling basin so that:

- top remains at **3047.50 m**;
- slab bottom is approximately **3045.00 m**;
- slab thickness is **2.50 m**;
- downstream anti-scour transition is geometrically continuous where modeled.

The **0.8 m** thickness belongs to the tailwater-channel concrete lining and must remain there, not in the spillway stilling basin.

---

## 7. Preserve the tailwater geometry that is already correct

Keep the validated tailwater major geometry:

- width approximately **71.6 m**;
- upstream hydraulic bottom elevation **3036.90 m**;
- downstream elevation **3053.00 m**;
- approximately **1:4** reverse slope;
- reverse-slope length about **64.4 m**;
- concrete lining thickness about **0.8 m**.

Only modify the tailwater locally if required for:

- fishway route integration;
- left-bank retaining geometry;
- natural riverbed transition;
- powerhouse tailrace continuity.

---

## 8. Perform real geology Boolean excavation, not only excavation envelopes

This is a required geometry correction.

The v15.2 model created excavation cutter/envelope bodies but did **not** actually cut the retained v14 geology.

### Required operation

For each applicable geology body:

1. identify which retained geology instances intersect the local excavation;
2. create the excavation cutter body;
3. Boolean-cut the retained geology;
4. keep the resulting cut geology in the final v15.3 model;
5. remove/suppress the standalone excavation tool body from the final visible engineering assembly unless it is intentionally retained only for audit.

Required local excavations:

- powerhouse;
- installation bay;
- spillway;
- ecological release;
- stilling basin;
- tailwater channel;
- left-bank sub-dam;
- fishway where it is embedded in slope/terrain.

The final model must not show both:
- uncut original geology, and
- an overlapping excavation cutter.

### Required audit

For each excavation report:

- affected geology Instance(s);
- cutter Instance;
- Boolean result Instance;
- target founding elevation;
- interference before cut;
- interference after cut;
- status PASS / FAIL / UNRESOLVED.

If Abaqus Boolean operations cannot be completed from the available deck, do not claim PASS. Leave that item `UNRESOLVED`.

---

## 9. Improve natural riverbed and retaining-wall continuity

Where source-supported, add or correct the important visible interfaces:

- tailwater left side: concrete gravity retaining wall;
- tailwater right side: spillway left guide wall;
- spillway / powerhouse elevation transition;
- natural downstream riverbed after the tailwater channel;
- natural downstream protection after the stilling basin.

Do not model detailed hydraulic appurtenances unless needed for the overall geometry.

---

## 10. Geometry audit requirements

This task remains geometry-only.

Do not run solver jobs.

Audit at least the following:

### Major dimensions

- 4 powerhouse units;
- powerhouse total envelope;
- installation bay;
- tailwater width/elevations/lining;
- 8 spillway openings at 7.00 m clear width;
- 2 ecological-release openings at 2.5 x 5.0 m;
- ecological-release total dam-axis length 12.50 m;
- stilling basin 107 m length and 2.50 m thickness;
- left-bank sub-dam crest 3079.00 m;
- fishway crossing opening 2.5 x 7.0 m;
- fishway total route length approximately 1407.57 m;
- fishway key station/elevation checks.

### Geometry consistency

Check:

- no positive-volume overlap between structural solids except documented shared interfaces;
- hydraulic openings are actual voids;
- fishway route passes through the sub-dam opening;
- sub-dam no longer stops at elevation 3060 m;
- ecological-release openings are not 12.5 m wide;
- spillway openings are not 10 m wide;
- stilling basin is not 0.8 m thick;
- excavation cutter bodies are not left overlapping uncut geology;
- tailwater remains geometrically continuous with powerhouse and downstream riverbed.

---

## 11. Visual verification

Generate **actual Abaqus/CAE viewport screenshots** if Abaqus is available.

Do not substitute synthetic 2D projection drawings for Abaqus screenshots.

Required views:

1. upstream;
2. downstream;
3. plan/top;
4. dam-axis;
5. left-bank oblique;
6. fishway full-route plan view;
7. fishway longitudinal/elevation-oriented view;
8. spillway + ecological-release close-up;
9. excavation/geology cutaway view.

Each screenshot must be visually distinct.

The upstream and downstream screenshots must not be identical files.

If Abaqus viewport export is unavailable, state this explicitly and do not claim the generated schematic images are CAE screenshots.

---

## 12. Required outputs

Create under `abaqus-audit/3d-v15.3/`:

- corrected geometry INP;
- corrected CAE if Abaqus is available;
- `V15_3_GEOMETRY_RESULT.md`;
- `v15_3_instance_inventory.csv`;
- `v15_3_dimension_audit.csv`;
- `v15_3_opening_audit.csv`;
- `v15_3_excavation_boolean_audit.csv`;
- `v15_3_interference_audit.csv`;
- `v15_3_fishway_station_audit.csv`;
- actual Abaqus/CAE screenshots where available.

The result report must explicitly state whether each of these is PASS / FAIL / UNRESOLVED:

- powerhouse geometry;
- installation bay;
- tailwater;
- spillway;
- ecological release;
- stilling basin;
- left-bank sub-dam;
- fishway;
- geology Boolean excavation;
- full-hub geometry completeness.

---

## 13. Explicitly prohibited

Do not:

- run S01-S07;
- perform Data Check for solver validation;
- change material parameters;
- add nodal restraints;
- add Encastre;
- add springs;
- add artificial supports;
- add Tie/contact to eliminate singularities;
- tune mesh for convergence;
- claim mechanical validation;
- claim seepage validation.

This task ends when the **3D geometry** is corrected and audited.

## Final delivery

Commit all v15.3 geometry corrections to `abaqus-audit-task` and push normally.

Do not force-push.

Return:

- final commit SHA;
- changed-file list;
- exact structures corrected;
- PASS / FAIL / UNRESOLVED geometry summary;
- final INP path;
- final CAE path if generated;
- actual Abaqus screenshot paths if generated.
