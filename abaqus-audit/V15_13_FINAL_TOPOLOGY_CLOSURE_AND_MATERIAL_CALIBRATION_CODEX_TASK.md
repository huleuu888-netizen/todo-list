# V15.13 Final Topology Closure and Material Calibration Task

## Baseline

Continue from commit:

`53776cadf26aa06ba62383e0758eda4e02a936e2`

Branch:

`abaqus-audit-task`

Do not create V15.14.
Do not modify main.
Do not force push.

This is a final closure task. The objective is NOT to redesign the model. The objective is to close the remaining five blockers before Abaqus Data Check.

Current V15.13 achievements that must be preserved:

- left-bank cutoff alignment corrected;
- left-bank extension toward negative Y completed;
- powerhouse / installation / ecological-release / spillway anti-seepage transition created;
- backfill integrated into geology Part;
- 36 geology Sections audited;
- geomembrane-cutoff interface repaired (gap=0, positive-volume penetration=0);
- no artificial Encastre, spring, Tie, or fake constraints used.

Do not undo these corrections.

---

# Remaining blockers to solve

## 1. Foundation topology closure (highest priority)

Current problems:

- 8 nonconforming faces remain at backfill-geology interface;
- foundation hanging nodes remain unresolved;
- same-domain disconnected components remain unresolved.

Required actions:

1. Recompute topology using actual element connectivity and global coordinates.
2. Locate every remaining nonconforming face and hanging node.
3. Repair only affected local regions.
4. Preserve material Sections and element sets.
5. Do not use Tie to hide a nonconformal seepage mesh.

Final requirements for continuous seepage regions:

- hanging nodes = 0;
- nonconforming internal faces = 0;
- duplicate nodes = 0;
- duplicate elements = 0;
- positive-volume overlap = 0.

Create:

`v15_13_foundation_topology_final.csv`

`v15_13_foundation_component_resolution.csv`

The files must contain computed values, not NOT_COMPUTED placeholders.

---

# 2. Geology Section pore-pressure completion

Keep the existing 36-section audit.

Do not globally convert C3D8R.

For each geology Section report:

- element type;
- element count;
- permeability status;
- pore-pressure DOF status;
- hydraulic role;
- final decision.

Create:

`v15_13_section_level_pore_pressure_audit.csv`

For regions intended for seepage:

- use pore-pressure-capable elements;
- require defensible permeability data.

For unresolved rock hydraulic parameters:

Do not invent k values.

Use status:

`HYDRAULIC_CALIBRATION_REQUIRED`

Create:

`v15_13_rock_hydraulic_parameter_basis.csv`

---

# 3. Backfill material resolution

Current mapping:

`Q3AL_III`

Determine whether this is:

- verified source mapping;
- engineering equivalent assumption;
- unresolved.

Do not silently upgrade temporary mapping to final calibration.

Create:

`v15_13_backfill_material_final_basis.csv`

---

# 4. Remaining structural uncertainty

## Spillway-main dam retaining wall

Current issue:

The source indicates a gravity retaining wall between spillway and sand/gravel dam, but dimensions are insufficient.

Actions:

- search existing model/source files first;
- if geometry exists, identify and include it;
- if dimensions remain unavailable, do not invent a wall.

Record:

`v15_13_spillway_main_dam_transition_resolution.csv`

## Right-bank curtain

Do not invent a solid curtain thickness.

Identify whether:

- an equivalent low-permeability region exists;
- a hydraulic boundary representation is appropriate;
- the item remains unresolved.

---

# 5. Anti-seepage final audit

Recheck the complete chain:

left-bank extension → left sub-dam → installation → powerhouse → ecological release → spillway → transition → main cutoff → geomembrane → right bank.

Use real faces/edges, not bounding boxes.

Report:

- minimum gap;
- contact length/area;
- shared nodes;
- penetration;
- continuity status.

Create:

`v15_13_cutoff_connection_final.csv`

---

# 6. Abaqus Data Check gate

Before running Data Check, update:

`v15_13_pre_datacheck_gate.csv`

Data Check is allowed only when geometry/topology critical items pass.

If rock hydraulic calibration remains unresolved but model definitions are valid, distinguish:

- solver Data Check readiness;
- production seepage analysis readiness.

Do not claim seepage-ready unless material calibration is complete.

---

# 7. Required final files

Update/create:

- V15_13_FINAL_SEEPAGE_DOMAIN_RESULT.md
- v15_13_foundation_topology_final.csv
- v15_13_foundation_component_resolution.csv
- v15_13_section_level_pore_pressure_audit.csv
- v15_13_rock_hydraulic_parameter_basis.csv
- v15_13_backfill_material_final_basis.csv
- v15_13_cutoff_connection_final.csv
- v15_13_pre_datacheck_gate.csv

The first line of the final report must be one of:

`FINAL_STATUS = STOPPED_UNRESOLVED`

`FINAL_STATUS = GEOMETRY_READY_HYDRAULICS_UNRESOLVED`

`FINAL_STATUS = DATACHECK_COMPLETED_WITH_ISSUES`

`FINAL_STATUS = DATACHECK_CLEAN_HYDRAULICS_UNRESOLVED`

`FINAL_STATUS = DATACHECK_CLEAN_SEEPAGE_READY`

---

# Final delivery

Commit to:

`abaqus-audit-task`

Return:

- commit SHA;
- changed files;
- final status;
- remaining unresolved items;
- Data Check result if executed.
