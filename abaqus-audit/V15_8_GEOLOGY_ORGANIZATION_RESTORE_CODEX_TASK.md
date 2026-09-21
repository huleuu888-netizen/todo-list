# V15.8 geology organization restoration task for Codex

## Objective

Continue from commit `41c06994c98fc5af495f2805b4beaaf68d8cd0ee`.

The v15.7 geometry and mesh are the frozen baseline.

The problem to fix is model organization, not mesh density:

- the model contains many Parts, but only about 58 active Instances;
- the former left-bank / riverbed / right-bank geological units are no longer visible as separate recognizable items in the Assembly tree;
- most geology is now contained inside one large instance:
  `V15_7_FOUNDATION_GEOLOGY_I`;
- the model looks geometrically complete, but geological identity is difficult to inspect, isolate, assign, and audit.

V15.8 must restore clear geological organization **without destroying the conformal geology mesh achieved in v15.7**.

Work only on:

`abaqus-audit-task`

Do not modify `main`.

Create all new outputs under:

`abaqus-audit/3d-v15.8/`

Do not overwrite earlier versions.

Do not run S01-S07.

---

# 1. Critical modeling rule

Do NOT blindly split the v15.7 foundation geology into many independent mesh instances if that would destroy shared-node continuity.

The v15.7 geology reached:

- continuous-geology nonconforming faces = 0;
- hanging nodes = 0.

These conditions must remain true.

Preferred organization:

- one conformal foundation geology mesh Part/Instance for analysis continuity;
- many clearly named geological Element Sets / Assembly Sets / Section assignments for geological identity;
- clean material and layer mapping;
- easy Display Group isolation in Abaqus/CAE.

The user must be able to identify and isolate each geological unit even if the final analysis still uses one conformal geology instance.

---

# 2. Create a clean new model

Create a new model inside the CAE named:

`V15_8_GEOLOGY_ORGANIZED`

Do not keep the new model cluttered with obsolete duplicate Parts from earlier construction stages.

Copy only the currently active v15.7 engineering Parts and the active foundation geology mesh needed by the final assembly.

Do not delete older models from the source CAE.

The new v15.8 model should contain:

- active engineering Parts;
- active engineering Instances;
- one conformal foundation geology Part/Instance unless a different organization can preserve true node continuity;
- materials;
- sections;
- sets;
- surfaces required by the active model.

Create:

`v15_8_active_part_instance_audit.csv`

with:

- part name;
- active instance name;
- role;
- node count;
- element count;
- active in assembly YES/NO;
- retained / obsolete;
- notes.

Also create:

`v15_8_unused_part_audit.csv`

listing all legacy/uninstantiated Parts that were intentionally excluded from the clean v15.8 model.

Do not silently delete provenance; document it.

---

# 3. Restore geological identity using explicit leaf sets

Reconstruct mutually exclusive geological leaf sets from the v15.7 foundation geology using original source-instance / source-layer provenance.

Use the previous source geology naming where available.

At minimum create separate logical sets for the left bank, riverbed, and right bank geological units.

Examples include, as applicable:

## Left bank

- `GEO_LEFT_P2_QUARTZ_SANDSTONE`
- `GEO_LEFT_FOUNDATION_GRANITE`
- `GEO_LEFT_L01_Q4DEL`
- `GEO_LEFT_L03_Q4AL_SGR1`
- `GEO_LEFT_L05_Q3AL_IV2`
- `GEO_LEFT_L06_Q3AL_IV1`
- `GEO_LEFT_L07_Q3AL_III`
- `GEO_LEFT_L08_Q3AL_II`
- `GEO_LEFT_L09_Q3AL_I`
- `GEO_LEFT_L10_Q2FGL_V`
- `GEO_LEFT_L11_Q2FGL_IV`
- `GEO_LEFT_L12_Q2FGL_III`
- `GEO_LEFT_L13_Q2FGL_II`
- `GEO_LEFT_L14_Q2FGL_I`

## Riverbed

- `GEO_RIVER_R02_Q4AL_SGR2`
- `GEO_RIVER_R05_Q3AL_IV2`
- `GEO_RIVER_R06_Q3AL_IV1`
- `GEO_RIVER_R07_Q3AL_III`
- `GEO_RIVER_R08_Q3AL_II`
- `GEO_RIVER_R09_Q3AL_I`
- `GEO_RIVER_R10_Q2FGL_V`
- `GEO_RIVER_R11_Q2FGL_IV`
- `GEO_RIVER_R12_Q2FGL_III`
- `GEO_RIVER_R13_Q2FGL_II`
- `GEO_RIVER_R14_Q2FGL_I`
- `GEO_RIVER_ROCK_STRONG_UNLOADED`
- `GEO_RIVER_ROCK_WEAK_UNLOADED`
- `GEO_RIVER_ROCK_DEEP_UNLOADED`
- `GEO_RIVER_FRESH_GRANITE`

## Right bank

- `GEO_RIGHT_Q4_COLLUVIAL`
- `GEO_RIGHT_R04_Q3AL_V`
- `GEO_RIGHT_HIGH_TERRACE_COVER`
- `GEO_RIGHT_ROCK_STRONG_UNLOADED`
- `GEO_RIGHT_ROCK_WEAK_UNLOADED`
- `GEO_RIGHT_ROCK_DEEP_UNLOADED`
- `GEO_RIGHT_FRESH_GRANITE`

Use actual source names from the repository/audit files when they differ.

Do not invent geological units that did not exist in the source model.

---

# 4. Leaf-set coverage rule

The geological leaf sets must satisfy:

- every foundation-geology element belongs to exactly one leaf geological set;
- no foundation-geology element is missing;
- no element belongs to two different leaf geological sets.

Composite convenience sets may overlap, but leaf sets may not.

Create:

`v15_8_geology_set_coverage_audit.csv`

with:

- geology leaf set;
- source provenance;
- material;
- section;
- element count;
- node count;
- bbox;
- duplicate leaf membership count;
- missing membership count;
- status.

Global acceptance:

- duplicate leaf membership = 0;
- unclassified foundation elements = 0.

---

# 5. Restore material / section mapping

For every geology leaf set, verify:

`geology set -> section -> material`

The material assignment must remain physically equivalent to v15.7.

Do not change:

- density;
- elastic parameters;
- permeability;
- porosity;
- pore-pressure element formulation;
- any existing constitutive parameter.

Create:

`v15_8_geology_material_section_map.csv`

with:

- geology set;
- original source layer;
- section name;
- material name;
- element type;
- element count;
- status.

If two geographical units use the same material, they may share one Material object, but they must still remain separately identifiable through geological sets.

---

# 6. Add assembly-level geological sets

Create Assembly-level sets mirroring the Part-level geological leaf sets.

Example:

- Part set: `GEO_LEFT_L01_Q4DEL`
- Assembly set: `ASSEM_GEO_LEFT_L01_Q4DEL`

This is required so the user can isolate geology directly from the Assembly context.

The user should be able to use:

`Tools -> Display Group -> Create -> Sets`

and select one geological unit by name.

---

# 7. Create geological composite groups

Also create convenient composite sets:

- `ASSEM_GEO_LEFT_ALL`
- `ASSEM_GEO_RIVER_ALL`
- `ASSEM_GEO_RIGHT_ALL`
- `ASSEM_GEO_COVER_ALL`
- `ASSEM_GEO_WEATHERED_ROCK_ALL`
- `ASSEM_GEO_FRESH_ROCK_ALL`
- `ASSEM_GEO_FOUNDATION_ALL`

These are for visualization only and may overlap logically.

Do not use composite-set overlap when judging leaf-set uniqueness.

---

# 8. Do not reintroduce overlapping geology instances

Do not create visualization-only duplicate geology Instances on top of the analysis geology.

No duplicate overlapping element bodies are allowed.

If separate geology Parts are created for inspection, they must be suppressed from the analysis assembly and clearly labeled:

`VIS_ONLY_DO_NOT_ANALYZE`

Preferred solution remains one analysis geology instance plus named sets.

---

# 9. Preserve v15.7 mesh exactly where possible

Compare v15.7 and v15.8 foundation geology.

Target:

- same external foundation-geology bbox;
- same node coordinates;
- same element connectivity;
- same element count;
- same node count;
- same material distribution;
- same nonconforming-face count = 0;
- same hanging-node count = 0.

Do not remesh merely to restore organization.

Create:

`v15_8_geology_mesh_freeze_audit.csv`

with:

- metric;
- v15.7;
- v15.8;
- delta;
- status.

---

# 10. Preserve all engineering structures

Do not change or remesh:

- dam-fill bodies;
- cutoff wall;
- geomembrane;
- powerhouse units;
- installation bay;
- tailwater structures;
- spillway;
- ecological release;
- stilling basin;
- left-bank sub-dam;
- fishway;
- sediment-flushing outlets.

Create:

`v15_8_engineering_freeze_audit.csv`

with bounding boxes, node counts, element counts, and coordinate-change count.

---

# 11. Clean model tree

The v15.8 model tree should be understandable.

Recommended organization:

## Parts

Keep only active Parts used in v15.8 plus the single active geology Part.

## Assembly Instances

Keep only active Instances.

## Sets

Use clear prefixes:

- `GEO_` for Part-level geology leaf sets;
- `ASSEM_GEO_` for Assembly geology sets;
- existing engineering set names may remain.

## Materials

Use meaningful existing material names.

## Sections

Use geological section names that indicate the material/layer where possible.

Do not leave hundreds of obsolete temporary Parts in the new v15.8 model.

---

# 12. Required visual verification

If Abaqus/CAE is available, create real CAE screenshots showing:

1. model tree with clean active Parts;
2. Assembly tree with active Instances;
3. foundation geology isolated;
4. one left-bank geology set isolated;
5. one riverbed geology set isolated;
6. one right-bank geology set isolated;
7. all left-bank geology composite set;
8. all riverbed geology composite set;
9. all right-bank geology composite set;
10. full hub with geology visible.

The screenshots must show that geological units are selectable by name.

---

# 13. Required outputs

Create under:

`abaqus-audit/3d-v15.8/`

Required:

- v15.8 CAE;
- v15.8 INP;
- `V15_8_GEOLOGY_ORGANIZATION_RESULT.md`;
- `v15_8_active_part_instance_audit.csv`;
- `v15_8_unused_part_audit.csv`;
- `v15_8_geology_set_coverage_audit.csv`;
- `v15_8_geology_material_section_map.csv`;
- `v15_8_geology_mesh_freeze_audit.csv`;
- `v15_8_engineering_freeze_audit.csv`;
- `v15_8_geology_instance_set_catalog.csv`;
- real CAE screenshots.

The result report must state:

- number of Parts in v15.7 vs v15.8;
- number of active Instances in v15.7 vs v15.8;
- number of geological leaf sets;
- number of assembly geology sets;
- number of unclassified geology elements;
- number of duplicate leaf memberships;
- whether material assignments were preserved;
- whether geology node coordinates/connectivity were preserved;
- final nonconforming geology face count;
- final hanging-node count;
- PASS / FAIL / UNRESOLVED.

---

# 14. Acceptance criteria

V15.8 is acceptable only if:

- geological identity is visible and selectable in CAE;
- each original geological unit is represented by a named geological leaf set;
- Assembly-level geology sets exist;
- all foundation elements are classified;
- duplicate leaf membership = 0;
- unclassified geology elements = 0;
- material / section assignments are preserved;
- no overlapping duplicate geology Instances are introduced;
- v15.7 conformal geology mesh is not degraded;
- nonconforming geology faces remain 0;
- hanging nodes remain 0;
- engineering geometry and structural meshes remain unchanged.

---

# 15. Prohibited

Do not:

- redesign geometry;
- remesh the geology unless absolutely necessary for a bookkeeping defect;
- split geology into independent analysis instances if that breaks continuity;
- duplicate overlapping geology;
- alter materials;
- alter density;
- alter permeability;
- alter elastic parameters;
- add Tie/contact/MPC;
- run S01-S07;
- modify `main`.

---

# Final delivery

Commit all v15.8 work to:

`abaqus-audit-task`

Push normally.

Do not force-push.

Return:

- final commit SHA;
- changed-file list;
- final CAE path;
- final INP path;
- Part count;
- active Instance count;
- geology leaf-set count;
- assembly geology-set count;
- material/section mapping status;
- nonconforming-face count;
- hanging-node count;
- screenshot paths.
