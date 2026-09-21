# V15.9 final geometry correction task for Codex

## Objective

Continue from commit `6fdd9c9403cea3c38fa59053b61b0d1f5e239203`.

The v15.8 geology organization is accepted as the baseline:

- keep the clean `V15_8_GEOLOGY_ORGANIZED` model structure;
- keep all 36 geology leaf sets and 43 assembly geology sets;
- keep geology Material/Section mappings;
- keep the conformal geology mesh wherever geometry is unaffected;
- preserve `nonconforming geology faces = 0` and `hanging nodes = 0`.

V15.9 shall correct the remaining source-documented engineering geometry issues before Abaqus Data Check.

Work only on:

`abaqus-audit-task`

Do not modify `main`.

Create outputs under:

`abaqus-audit/3d-v15.9/`

Do not overwrite previous versions.

Do not run S01-S07.

---

# 1. Coordinate convention and source-first rule

Current model convention:

- X = streamwise direction;
- Y = dam-axis direction;
- Z = elevation.

Before changing any coordinate, compare the current v15.8 geometry against the source report and document the interpretation.

Do not preserve an old coordinate simply because it existed in v15.4-v15.8.

Do not invent unsupported dimensions.

If two source passages describe different physical widths, distinguish the corresponding structural envelopes instead of forcing one number onto all elevations.

Create:

`v15_9_source_geometry_basis.csv`

with:

- structure;
- source wording;
- interpreted physical meaning;
- target X span;
- target Y span;
- target Z/elevation;
- status;
- notes.

---

# 2. Critical correction A — installation bay

## Current error

The v15.8 installation bay is:

- X = -64 to -30 m -> 34 m streamwise;
- Y = -122 to -15.4 m -> 106.6 m dam-axis.

This is a transposed / inherited powerhouse envelope and must not be preserved.

## Source constraints

The source gives:

- main powerhouse total dam-axis length = **106.6 m**;
- main powerhouse streamwise foundation width = **56.5 m**;
- installation bay is on the **left side of the main powerhouse**;
- installation bay length = **34 m**;
- installation floor elevation = **3062.00 m**;
- one report passage says the installation bay is "same width as the powerhouse";
- another passage states "installation bay width 20 m, length 34 m".

## Required interpretation

Treat these as two potentially different physical widths:

1. **dam-block / foundation envelope**:
   - dam-axis length must be **34 m**;
   - streamwise foundation envelope may follow the powerhouse foundation width, approximately **56.5 m**, where supported by the detailed hydraulic-structure section;

2. **upper installation-room/superstructure usable width**:
   - may be approximately **20 m** where the source specifically refers to the installation bay room/building width.

Do not model the full installation bay as 34 m streamwise x 106.6 m dam-axis.

### Required geometry

- place the installation bay immediately on the left-bank side of the powerhouse;
- set dam-axis Y span to approximately **34 m**;
- retain floor elevation **3062.00 m**;
- construct the lower/foundation block and upper room envelope separately if needed to reconcile 56.5 m foundation width vs 20 m room width;
- preserve the structural joint between installation bay and powerhouse;
- regenerate the affected local excavation/foundation region.

### Acceptance

Audit separately:

- installation-bay foundation X width;
- installation-bay Y length;
- upper-room X width;
- floor elevation;
- adjacency to powerhouse;
- no reuse of 106.6 m as installation-bay Y length.

---

# 3. Critical correction B — left-bank sub-dam

## Current error

The v15.8 left-bank sub-dam envelope is approximately:

- X = -112 to -64 m;
- Y = -122 to -15 m;

giving about **107 m** dam-axis length.

This does not match the source.

## Source constraints

The left-bank sub-dam is a concrete gravity dam.

Documented values:

- crest length = **89.70 m**;
- crest width = **7.0 m**;
- upper upstream face vertical;
- below elevation **3072.00 m**, upstream slope = **1:0.2**;
- upper downstream face vertical;
- below elevation **3072.00 m**, downstream slope = **1:0.6**;
- below elevation **3062.00 m**, the section becomes rectangular and extends approximately 2 m upstream and 2.5 m downstream;
- maximum dam height about 20 m;
- local backfill near powerhouse reaches approximately **3059.00 m**;
- source states four dam sections:
  - block 1 = **42.6 m**;
  - other three blocks = **15 m each**;
- source also states total crest length **89.70 m**.

The arithmetic `42.6 + 15 + 15 + 15 = 87.6 m` does not equal 89.70 m.

## Required handling

Do not hide this discrepancy.

- enforce overall crest length **89.70 m** as the governing total envelope;
- preserve the documented 42.6 m + 15 m + 15 m + 15 m section logic;
- identify the remaining **2.10 m** explicitly as `SOURCE_LENGTH_RECONCILIATION_UNRESOLVED` unless the report/drawing provides a joint/transition/closure explanation;
- do not invent a fifth dam block;
- do not stretch a documented 15 m block to absorb the difference without evidence.

### Geometry requirements

- rebuild the sub-dam so its Y-axis crest extent is **89.70 m**;
- crest width = **7.0 m**;
- use the documented 3072 m slope break;
- include the 3059 m local foundation/backfill relationship;
- retain the fishway passage through the sub-dam at the documented route;
- relocate/rebuild the fishway crossing only as necessary to remain inside the corrected sub-dam;
- keep crest system compatible with the project crest elevation around 3079 m.

### Acceptance

Create:

`v15_9_subdam_section_audit.csv`

with:

- total crest length;
- crest width;
- block 1 length;
- blocks 2-4 lengths;
- unresolved 2.10 m reconciliation;
- upstream slope;
- downstream slope;
- fishway crossing position;
- status.

---

# 4. Critical correction C — powerhouse sediment-flushing outlets

## Current deficiency

The current outlet audit represents both flushing corridors only as **2.5 m x 2.0 m**.

This is incomplete.

## Source constraints

For the sediment-flushing system:

- total = **2 outlets**;
- one outlet serves each pair of units;
- upstream entrance sill elevation = **3037.00 m**;
- upstream entrance opening = **2.5 m x 2.0 m**;
- downstream sill elevation = **3043.00 m**;
- downstream system includes:
  - working gate opening **2.5 m x 2.0 m**;
  - outlet maintenance gate opening **2.5 m x 3.0 m**.

## Required geometry

For each of the two outlets, model a continuous corridor with:

1. upstream entrance:
   - 2.5 x 2.0 m;
   - sill Z = 3037.00 m;

2. internal passage:
   - continuous through the intermediate-pier region;

3. downstream working-gate section:
   - 2.5 x 2.0 m;
   - sill Z = 3043.00 m;

4. downstream maintenance-gate / enlarged outlet section:
   - **2.5 x 3.0 m**;
   - preserve the documented downstream sill relationship.

Do not model the whole passage as one constant 2.5 x 2.0 m rectangular void.

Do not add detailed gate leaves or machinery.

### Acceptance

Create:

`v15_9_sediment_flushing_geometry_audit.csv`

with:

- outlet 01/02;
- unit-pair served;
- upstream width/height/sill;
- downstream working-gate width/height/sill;
- downstream maintenance-gate width/height;
- passage continuity;
- collision with main unit waterways;
- status.

---

# 5. Critical correction D — ecological release to spillway continuity

## Current error

In v15.8:

- ecological release ends near Y = -2.5 m;
- spillway structural zone begins near Y = 16 m;

leaving an unexplained dam-axis gap of about **18.5 m**.

The source states the ecological-release structure:

- is directly between the powerhouse intake and the 8-bay spillway;
- left side connects to the powerhouse intake;
- right side connects to the 8-bay spillway;
- total ecological-release dam-axis length = **12.50 m**;
- 2 working openings, each **2.5 m x 5.0 m**;
- left pier = 3.0 m;
- center pier = 2.5 m;
- right pier = 2.0 m;
- chamber streamwise length = 30 m;
- inlet bottom = 3058.00 m.

The source also states:

- the 8 spillway bays plus the 2 ecological-release bays form a combined flood-release frontage of approximately **109.00 m**.

## Required correction

Rebuild the ecological-release / spillway dam-axis arrangement so that:

- ecological release is directly adjacent to the powerhouse side;
- ecological release is directly adjacent to the spillway side;
- no unexplained 18.5 m open gap remains;
- exactly 2 ecological openings remain;
- exactly 8 spillway openings remain;
- spillway clear opening width remains **7.00 m each**;
- ecological total Y length remains **12.50 m**;
- combined flood-release frontage is checked against **109.00 m**.

Do not simply translate only one structure without checking:

- tailwater;
- common stilling basin;
- abutments;
- guide walls;
- foundation excavation;
- cutoff-wall alignment.

## Spillway width reconciliation

Do not invent intermediate-pier thicknesses if the source is not explicit.

Use these hard constraints:

- 8 x 7.0 m clear openings;
- 12.5 m ecological-release total width;
- combined flood-release frontage ~109.0 m.

The remaining width must be assigned to documented piers / abutments / transition structures.

If exact pier/abutment widths cannot be sourced, keep their exact subdivision `UNRESOLVED`, but the global frontage and adjacency must be correct.

Create:

`v15_9_flood_frontage_audit.csv`

with:

- powerhouse-side boundary;
- ecological-release span;
- ecological-to-spillway interface gap;
- 8 spillway bay widths;
- intermediate/side structure widths;
- total combined flood-release frontage;
- target 109.00 m;
- status.

---

# 6. Preserve corrected geometry that is already acceptable

Unless affected locally by the four corrections above, preserve:

- powerhouse 4-unit arrangement;
- powerhouse 106.6 m total dam-axis length;
- powerhouse 56.5 m streamwise foundation width;
- tailwater clear width 71.6 m;
- 8 spillway openings at 7 m clear width;
- ecological-release opening dimensions;
- 107 m stilling-basin length;
- 2.5 m stilling-basin slab thickness;
- fishway full route and stationing;
- fishway 2.5 x 7.0 m sub-dam crossing;
- geology leaf sets / assembly sets;
- geology Material/Section mappings;
- cutoff-wall and geomembrane organization.

Do not reintroduce obsolete 9-bay spillway geometry.

---

# 7. Geology and excavation update

Only remesh geology where one of the four corrected structures changes its footprint or excavation.

Requirements:

- preserve the v15.8 geology set names and material identities;
- preserve leaf-set uniqueness;
- preserve nonconforming geology faces = 0;
- preserve hanging nodes = 0;
- no overlapping old/new geology cells;
- no excavation cutter left as an active overlapping body;
- update geology element membership for any locally regenerated cells.

Create:

`v15_9_local_geology_update_audit.csv`

with:

- affected geology set;
- removed elements;
- replacement elements;
- material preserved;
- conformity status;
- hanging-node count;
- overlap count;
- status.

---

# 8. Mesh policy

Do not globally remesh the model.

Only locally remesh:

- corrected installation-bay / sub-dam foundation;
- corrected sediment-flushing openings;
- corrected ecological-release / spillway interface;
- directly affected geology.

Keep the existing v15.8 mesh elsewhere.

Target local structural mesh scale should remain consistent with the accepted working mesh:

- small openings: ~0.5-1.0 m;
- main structural solids: ~1.0-2.5 m;
- local foundation geology: graded ~2-10 m.

Do not increase the global model size unnecessarily.

---

# 9. Geometry and organization verification

Create:

`v15_9_geometry_change_audit.csv`

For every engineering instance report:

- v15.8 bbox;
- v15.9 bbox;
- changed YES/NO;
- reason;
- source basis;
- status.

Only structures affected by this task should change.

Also verify:

- 36 geology leaf sets retained or correctly updated;
- Assembly geology sets retained;
- unclassified geology elements = 0;
- duplicate geology leaf membership = 0.

---

# 10. Actual CAE visual verification

If Abaqus/CAE is available, export actual viewport screenshots.

Required:

1. full hub plan;
2. dam-axis view;
3. powerhouse + corrected installation bay;
4. installation-bay / sub-dam junction;
5. corrected left-bank sub-dam;
6. fishway crossing through corrected sub-dam;
7. sediment-flushing outlet 01;
8. sediment-flushing outlet 02;
9. ecological-release / spillway junction;
10. full 8-spillway + 2-eco flood-release frontage;
11. local mesh around installation bay/sub-dam;
12. local mesh around eco/spillway interface.

Do not use synthetic diagrams as substitutes.

---

# 11. Required outputs

Create under:

`abaqus-audit/3d-v15.9/`

Required:

- v15.9 CAE;
- v15.9 INP;
- `V15_9_FINAL_GEOMETRY_RESULT.md`;
- `v15_9_source_geometry_basis.csv`;
- `v15_9_geometry_change_audit.csv`;
- `v15_9_installation_bay_audit.csv`;
- `v15_9_subdam_section_audit.csv`;
- `v15_9_sediment_flushing_geometry_audit.csv`;
- `v15_9_flood_frontage_audit.csv`;
- `v15_9_local_geology_update_audit.csv`;
- `v15_9_geology_set_coverage_audit.csv`;
- `v15_9_mesh_local_quality_audit.csv`;
- actual CAE screenshots.

The final result report must explicitly state:

- installation-bay Y length;
- installation-bay lower/foundation X width;
- installation-bay upper-room X width;
- installation floor elevation;
- left-sub-dam total crest length;
- left-sub-dam block-length reconciliation;
- number of sediment-flushing outlets;
- upstream/downstream outlet opening dimensions;
- eco-to-spillway gap;
- combined flood-release frontage;
- geology nonconforming-face count;
- hanging-node count;
- unclassified geology-element count;
- PASS / FAIL / UNRESOLVED summary.

---

# 12. Prohibited

Do not:

- alter material parameters;
- alter permeability;
- alter density;
- alter elastic parameters;
- globally remesh the geology;
- add Tie/contact/MPC;
- add artificial restraints;
- run S01-S07;
- claim structural/seepage validation;
- modify `main`.

---

# Completion condition

V15.9 is complete when:

- installation bay no longer uses the erroneous 106.6 m dam-axis length;
- installation bay is reconciled with the documented 34 m length and source width interpretations;
- left sub-dam total crest length is corrected to 89.70 m, with the 2.10 m source discrepancy explicitly documented;
- both sediment-flushing outlets include the downstream 2.5 x 3.0 m maintenance-gate section;
- ecological release is directly connected to the spillway with no unexplained 18.5 m gap;
- 8 spillway + 2 ecological-release frontage is checked against 109.00 m;
- geology organization remains usable;
- continuous geology remains conformal.

After V15.9, proceed to a separate Abaqus Data Check task rather than another geometry redesign cycle.

---

# Final delivery

Commit all v15.9 work to:

`abaqus-audit-task`

Push normally.

Do not force-push.

Return:

- final commit SHA;
- changed-file list;
- final CAE path;
- final INP path;
- installation-bay dimensions;
- left-sub-dam dimensions;
- sediment-flushing outlet dimensions;
- eco/spillway frontage audit;
- geology conformity summary;
- screenshot paths.
