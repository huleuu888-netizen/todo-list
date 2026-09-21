# V15.2 geometry completion task for Codex

## Goal

Continue from the geometry-only model at commit `48112235b6f1794a069130ea43fccef14ca8552a` and complete the remaining 3D geometry of the Duobu hydropower hub.

This is a **geometry-only** task.

Do **not** perform finite-element analysis, mechanical stabilization, seepage analysis, contact tuning, material changes, or solver troubleshooting in this task.

## Branch and file safety

- Work only on branch `abaqus-audit-task`.
- Do not modify `main`.
- Do not overwrite or delete v12, v13, v14, or v15 outputs.
- Create all new outputs under:
  `abaqus-audit/3d-v15.2/`
- Use commit `48112235b6f1794a069130ea43fccef14ca8552a` as the geometry baseline unless a newer commit on the same branch only adds this task file.

## Preserve the geometry that is already correct

Do not rebuild the following from scratch unless a local geometric correction is necessary:

- 4-unit powerhouse
- powerhouse installation bay
- tailwater channel
- 8-bay spillway
- 2-bay ecological-release structure
- common spillway/ecological stilling basin

Preserve the current major dimensions and elevations already audited as PASS.

## 1. Complete the left-bank hub geometry

Add the missing left-bank structures so that the hub is geometrically complete.

### 1.1 Left-bank sub-dam

Build an explicit left-bank sub-dam solid.

Requirements:

- connect the powerhouse / installation-bay side to the natural left-bank terrain;
- include a real crest, upstream face, downstream face, and foundation footprint;
- do not model it as a simple floating rectangular block;
- reserve the fishway crossing opening through the sub-dam;
- the fishway crossing opening should be represented as an actual void/opening, not overlapping solids.

Where source geometry is insufficient, keep the item explicitly marked `UNRESOLVED` rather than inventing dimensions.

### 1.2 Fishway

Build a continuous simplified fishway geometry.

Use the known routing logic:

- entrance near the downstream left side of the powerhouse tailwater outlet;
- continue along the left side of the tailwater channel;
- extend downstream;
- turn back upstream;
- pass through the left-bank sub-dam;
- continue to the upstream outlet.

Geometry requirements:

- use a continuous channel body, preferably path/sweep-style geometry;
- nominal clear passage width: about 2.0 m;
- wall thickness: about 0.5 m;
- bottom thickness: about 0.5 m;
- retain the principal elevation changes and route shape;
- include the sub-dam crossing opening, approximately 2.5 m x 7 m where applicable.

Do not model every vertical-slot baffle in this stage unless the source geometry makes it straightforward.

## 2. Rebuild excavation / terrain-cut geometry around the structures

The existing v14 left-bank geology context must no longer behave like a generic oversized depression.

Create separate engineering excavation envelopes for:

- powerhouse foundation pit;
- installation-bay foundation pit;
- spillway foundation excavation;
- ecological-release foundation excavation;
- stilling-basin excavation;
- tailwater-channel excavation.

Use actual structure footprints and known elevations to cut the retained geology / terrain.

Preferred modeling logic:

1. retain the existing geology bodies;
2. generate dedicated excavation cutter bodies;
3. Boolean-cut the geology using those cutter bodies;
4. keep the resulting geology as the final geometry context.

Do not replace all local excavations with one large artificial pit.

The final geometry should show each structure seated in a corresponding local excavation and the tailwater channel cut into the riverbed.

## 3. Improve powerhouse hydraulic geometry

Keep the audited powerhouse envelope:

- total Y length: about 106.6 m;
- flow-direction X width: about 56.5 m;
- foundation elevation: about 3029.70 m;
- intake bottom: about 3035.70 m;
- turbine installation elevation: about 3041.00 m.

Add simplified but explicit hydraulic openings:

- upstream intake openings;
- equivalent internal water-passage voids;
- downstream tailrace / draft-tube outlet openings.

These must be actual voids/openings where feasible.

Do not leave the powerhouse as a fully solid concrete box if that makes the intake and tailwater passage physically impossible.

Detailed electromechanical equipment is not required.

## 4. Refine spillway geometry into true open bays

Keep the final 8-bay arrangement.

The spillway should visually and geometrically read as:

`pier | opening | pier | opening | ... | pier`

Requirements:

- retain 8 open flow bays;
- create left abutment / side wall, intermediate piers, and right side wall;
- ensure the flow bays are actual openings rather than eight adjacent solid blocks;
- retain the common downstream stilling basin;
- avoid positive-volume overlap between piers, bays, walls, and basin.

Keep the current design targets already used in v15 where source-supported.

## 5. Refine ecological-release geometry into two true low-level openings

Keep two bays.

Requirements:

- represent two actual low-level flow openings;
- preserve inlet-bottom elevation near 3058.00 m;
- preserve the overall geometry relationship between spillway and powerhouse;
- connect the downstream side geometrically toward the common stilling basin;
- do not represent the two release bays as simple fully solid blocks.

## 6. Tailwater channel and riverbed connection

Preserve:

- channel width: about 71.6 m;
- upstream hydraulic bottom elevation: 3036.90 m;
- downstream hydraulic bottom elevation: 3053.00 m;
- reverse slope approximately 1:4;
- reverse-slope length about 64.4 m;
- lining thickness about 0.8 m where represented.

Modify the surrounding riverbed so that the tailwater channel is an actual riverbed excavation.

The geometry should transition continuously from the powerhouse tailwater outlet to the tailwater channel and then to the natural downstream riverbed.

Do not leave the channel as an isolated slab or floating body.

## 7. Geometry-only quality checks

Do not run S01-S07 or any Abaqus solver job.

Perform geometry checks only:

- active Instance inventory;
- XYZ bounding boxes;
- major design-dimension check;
- major elevation check;
- positive-volume overlap / interference check;
- opening / void existence check;
- excavation consistency check;
- continuity of powerhouse-to-tailwater geometry;
- continuity of spillway/ecological-release-to-stilling-basin geometry;
- left-bank sub-dam and fishway routing check.

For every uncertain source-dependent geometry item, use one of:

- PASS
- FAIL
- UNRESOLVED

Do not fabricate missing engineering dimensions.

## 8. Required visual checks

If the local Abaqus / rendering environment allows it, export at least five geometry views:

1. upstream view;
2. downstream view;
3. plan / top view;
4. dam-axis view;
5. left-bank oblique view.

The views should make it possible to visually verify:

- 8 spillway openings;
- 2 ecological-release openings;
- 4-unit powerhouse;
- installation bay;
- tailwater channel;
- left-bank sub-dam;
- fishway route;
- local foundation excavations;
- absence of one oversized generic left-bank pit.

## 9. Required outputs

Create under `abaqus-audit/3d-v15.2/`:

- updated geometry INP;
- updated CAE if Abaqus is available;
- `V15_2_GEOMETRY_RESULT.md`;
- `v15_2_instance_inventory.csv`;
- `v15_2_dimension_audit.csv`;
- `v15_2_excavation_audit.csv`;
- `v15_2_interference_audit.csv`;
- `v15_2_opening_audit.csv`;
- geometry-check images where available.

The result report must state clearly:

- which structures were newly created;
- which v15 structures were retained;
- which geometry was locally modified;
- which items remain `UNRESOLVED`;
- whether the full hub geometry is visually and dimensionally complete.

## 10. Explicitly prohibited in this task

Do not:

- run S01, S02, S03, S04, S05, S06, or S07;
- modify material parameters;
- add node restraints;
- add Encastre constraints;
- add springs;
- add artificial supports;
- add Tie/contact merely to suppress numerical singularities;
- tune meshes for convergence;
- claim mechanical or hydraulic validation.

This task ends when the 3D geometry is completed and audited.

## Final delivery

Commit all v15.2 geometry work to `abaqus-audit-task` and push normally.

Do not force-push.

Return:

- final commit SHA;
- changed-file list;
- structures created or modified;
- geometry PASS / FAIL / UNRESOLVED summary;
- paths of the final INP / CAE and geometry-check images.
