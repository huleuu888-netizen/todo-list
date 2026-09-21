# V15.12 real Assembly / interface / seepage-system validation task

## Baseline

Continue from commit:

`ae1afc069151d5437441eaf73c1c22760524a18d`

Use the v15.11 CAE/INP as the baseline.

Work only on:

`abaqus-audit-task`

Do not modify `main`.

Create all new outputs under:

`abaqus-audit/3d-v15.12/`

Do not overwrite v15.11.

Do not run S01-S07.

This task is a **verification-first task**. Geometry may be changed only when a real Assembly-level check proves a missing or incorrect physical feature.

---

# 1. Why V15.12 is required

V15.11 improved the left-bank layout, backfill, and fishway, but several audits were generated from scripted envelope logic rather than from actual Abaqus Assembly faces/topology.

Examples that must not be treated as final proof:

- a shared Y coordinate was used as part of the interface logic;
- some minimum gaps were written directly as 0;
- unsupported foundation area was forced to 0 after coverage logic;
- nonconforming-face and hanging-node counts were reported without a fresh whole-model topology reconstruction;
- the cutoff-wall transform was hard-coded as `global=(x,445-z,y)` rather than read from the actual active Instance transform.

Therefore V15.12 must replace these surrogate checks with real Assembly-level evidence.

---

# 2. Source-controlled seepage-system requirements

Use the project report as the governing source for these items.

The source states:

- foundation anti-seepage uses a vertical concrete cutoff wall;
- cutoff-wall thickness = **1.0 m**;
- cutoff-wall bottom elevations are approximately **3011.00 m to 3021.00 m** depending on the structure segment;
- the main riverbed sand/gravel dam cutoff wall connects to the upper composite geomembrane;
- the spillway, powerhouse, ecological-release structure and left-bank sub-dam use cutoff-wall / connecting-plate / water-retaining-structure continuity;
- the powerhouse + installation-bay cutoff-wall axis is at the documented upstream line and the segment at dam-left 0+081.00 to 0+192.00 has bottom elevation **3011.00 m**, transitioning about 1:1 to **3021.00 m** at both sides;
- the left-bank sub-dam cutoff-wall axis is on the same anti-seepage line as the left-bank structures, bottom elevation **3021.00 m**;
- the left-bank cutoff wall extends approximately **80 m** into the abutment;
- important vertical joints such as powerhouse/installation and powerhouse/spillway use dedicated water-stop treatment.

Do not invent a new anti-seepage alignment that is not supported by the source.

---

# 3. Read the real active Assembly transforms

## Mandatory method

Use one of the following, in priority order:

1. Abaqus/CAE Python API on the actual v15.11 CAE;
2. if CAE API is unavailable, parse the exact `*Instance` placement/rotation data from the v15.11 INP;
3. if neither is available, stop and report `UNRESOLVED`.

Do not use manually assumed or hard-coded transforms.

For every active instance, output:

- instance name;
- part name;
- translation vector;
- rotation axis / point / angle, if any;
- any additional transform;
- true Assembly/global bbox;
- node count;
- element count.

Create:

`v15_12_instance_transform_audit.csv`

Acceptance:

- every active instance has a traceable transform source;
- no instance global bbox is produced from an undocumented hard-coded formula.

---

# 4. Rebuild a trustworthy global-coordinate inventory

Create:

`v15_12_global_instance_inventory.csv`

At minimum include all active:

- dam-fill components;
- geomembrane;
- cutoff wall;
- powerhouse units;
- installation bay;
- tailwater;
- ecological release;
- spillway;
- stilling basin;
- sediment-flushing outlets;
- left-bank sub-dam;
- fishway;
- engineered backfill;
- foundation geology.

For each report:

- true global bbox;
- centroid;
- nearest named neighboring structures;
- transformed source;
- status.

Do not infer adjacency from part-local coordinates.

---

# 5. Real face-level interface checker

Implement a reusable interface checker based on actual mesh faces.

For each element type in the participating parts:

- derive all element faces from connectivity;
- transform face nodes into global Assembly coordinates;
- identify boundary faces;
- compare boundary-face geometry between the two target regions.

The checker must report:

- true minimum node-to-face / face-to-face distance;
- coincident-face node count;
- coincident-face count;
- coincident/contact area;
- overlap/interpenetration indicator;
- mismatch area;
- maximum face-to-face mismatch;
- whether nodes are actually shared, merely coincident, or separated.

Bounding boxes may be used only as a broad-phase filter.

They may not be the final proof.

Create:

`v15_12_real_interface_audit.csv`

---

# 6. Revalidate the left-bank interfaces using real faces

Recheck:

## A. left sub-dam / installation bay

Required:

- true minimum gap <= **1 mm**;
- contact/coincident area > 0;
- no volumetric penetration;
- report whether nodes are shared or the interface is only geometrically coincident.

## B. installation bay / powerhouse

Same requirements.

## C. left sub-dam / engineered backfill

Report:

- supported sub-dam base area;
- unsupported base area;
- real face-coincident area;
- maximum local support gap.

## D. installation bay / engineered backfill

Same.

## E. engineered backfill / retained geology

Report:

- actual coincident interface area;
- real shared-node count;
- coincident-but-not-shared node count;
- hanging-node count;
- mismatch area;
- interpenetrating elements.

Do not report 100% support unless the full base-face audit proves it.

Create:

`v15_12_left_bank_interface_detail.csv`.

---

# 7. Whole-foundation topology reconstruction

Recompute from the actual v15.11/v15.12 mesh:

- external boundary faces;
- internal faces;
- identical shared faces;
- coincident but non-shared faces;
- nonconforming internal interfaces;
- hanging nodes;
- duplicate nodes;
- duplicate elements;
- nonmanifold faces/edges;
- unintended disconnected same-material components.

Do this for:

- natural geology only;
- natural geology + engineered backfill;
- full foundation domain.

Create:

`v15_12_foundation_topology_audit.csv`

and:

`v15_12_foundation_components.csv`.

Do not copy zero values from v15.11.

Acceptance for intended continuous foundation interfaces:

- hanging nodes = 0;
- nonconforming internal faces = 0;
- duplicate elements = 0;
- duplicate nodes within tolerance = 0 unless intentionally merged/retained and explained;
- unintended disconnected same-material components = 0 or explicitly justified.

---

# 8. Revalidate engineered backfill material mapping

V15.11 temporarily mapped the compacted sand/gravel backfill to:

`Q3AL_III`

with:

`BACKFILL_MATERIAL_MAPPING_UNRESOLVED`.

Search:

- the existing model material definitions;
- source-derived material tables already present in the repository;
- the project report where available.

Determine whether there is a source-supported compacted sand/gravel / backfill material.

Do not invent parameters.

Create:

`v15_12_backfill_material_resolution.csv`

with:

- candidate material;
- source;
- density;
- elastic parameters;
- permeability;
- porosity/void-ratio data if present;
- constitutive model;
- element formulation;
- final mapping status.

If the exact material cannot be verified:

- keep the current temporary mapping;
- retain status `UNRESOLVED`;
- do not claim final seepage calibration.

---

# 9. Audit pore-pressure / seepage-capable element coverage

This is mandatory before the later seepage study.

Inventory every active element type in:

- dam fill;
- natural geology;
- engineered backfill;
- cutoff wall;
- geomembrane representation;
- other materials that are intended to transmit or block seepage.

Create:

`v15_12_pore_pressure_domain_audit.csv`

For each region report:

- element type;
- element count;
- pore-pressure DOF present YES/NO;
- permeability assigned YES/NO;
- intended role:
  - seepage domain;
  - impermeable barrier;
  - structural-only;
  - unresolved.

Important:

- `C3D8P/C3D6P` are pore-pressure-capable;
- `C3D8R` is not a pore-pressure element.

Do not automatically convert all C3D8R elements.

Instead identify every region where a structural-only element lies inside a domain that is supposed to participate in seepage.

Mark those regions:

`SEEPAGE_ELEMENT_FORMULATION_UNRESOLVED`

This includes any rock/foundation region intended to conduct groundwater.

---

# 10. Reconstruct the entire anti-seepage chain in global coordinates

Create an explicit ordered anti-seepage-system inventory from left bank to right bank.

At minimum inspect:

- left-bank abutment extension;
- left-bank sub-dam cutoff segment;
- installation-bay / powerhouse cutoff segment;
- ecological-release cutoff connection;
- spillway cutoff segment;
- main riverbed sand/gravel-dam cutoff wall;
- composite geomembrane connection;
- right-bank cutoff/curtain connection if present.

Create:

`v15_12_seepage_chain_audit.csv`

For each segment report:

- segment name;
- actual global start/end coordinates;
- thickness;
- top elevation;
- bottom elevation;
- adjacent upstream/downstream structure;
- next anti-seepage segment;
- minimum gap to next segment;
- overlap/contact length or area;
- source basis;
- status.

The final chain must show whether the anti-seepage system is continuous from left bank to right bank.

---

# 11. Determine whether the left-sub-dam cutoff wall is actually missing

V15.11 reported:

`left_subdam_cutoff_instance = NOT PRESENT`

Do not immediately add geometry.

First search all active parts/instances/sets/surfaces for:

- another cutoff-wall segment;
- a structure-embedded cutoff region;
- a hidden/renamed left-bank cutoff part;
- a continuous wall encoded inside another instance.

Use actual global coordinates.

Create:

`v15_12_left_subdam_cutoff_presence_audit.csv`.

Possible outcomes:

## Outcome A — existing geometry is present

If an existing segment is found:

- document it;
- correct naming/sets if needed;
- do not duplicate it.

## Outcome B — geometry is genuinely missing

Only then add the missing left-bank sub-dam cutoff segment.

---

# 12. If missing, add the source-supported left-bank cutoff segment

Only execute this section if Section 11 proves it is absent.

Required source basis:

- wall thickness = **1.0 m**;
- left-sub-dam cutoff axis aligned with the documented left-bank anti-seepage line;
- wall bottom elevation = **3021.00 m** in the left-sub-dam/left-bank segment;
- left-bank extension approximately **80 m**;
- connect continuously to the powerhouse/installation-bank anti-seepage system;
- do not invent an unsupported offset or deepening.

Where the powerhouse/installation segment is governed by the deeper design:

- preserve the documented **3011.00 m** bottom over the specified central segment;
- preserve the approximate **1:1** transition back toward 3021.00 m.

The added wall must:

- have its own clear Part/Instance/Set naming;
- use the existing verified cutoff-wall material/Section;
- avoid duplicate overlap with existing walls;
- be locally remeshed only;
- be assigned an analysis-appropriate element formulation consistent with the existing cutoff-wall modeling strategy.

Suggested names:

- `V15_12_LEFT_BANK_CUTOFF_WALL`
- `V15_12_LEFT_BANK_CUTOFF_WALL_I`
- `ASSEM_V15_12_LEFT_BANK_CUTOFF_WALL`

Do not alter the existing wall unless required for a real continuity repair.

---

# 13. Real wall-to-wall / wall-to-structure interface checks

For all anti-seepage transitions, use real face/edge geometry.

Audit:

- left-bank cutoff -> sub-dam/installation cutoff;
- installation/powerhouse cutoff -> eco-release cutoff;
- eco-release -> spillway cutoff;
- spillway cutoff -> riverbed/main-dam cutoff;
- riverbed cutoff -> geomembrane;
- right-bank cutoff -> curtain if modeled.

Report:

- minimum real gap;
- contact length/area;
- thickness mismatch;
- vertical elevation mismatch;
- bottom-elevation mismatch;
- top-elevation mismatch;
- overlap/interpenetration;
- continuity status.

Create:

`v15_12_cutoff_connection_detail.csv`.

---

# 14. Geomembrane-to-cutoff connection

The source says the main riverbed cutoff wall connects to the upper composite geomembrane.

Verify this in actual Assembly coordinates.

Report:

- geomembrane lower edge;
- cutoff-wall upper edge/top zone;
- minimum separation;
- projected overlap length;
- actual node/edge relation;
- whether a connecting concrete/embedded zone is represented;
- status.

Do not simply accept bbox overlap.

Create:

`v15_12_geomembrane_cutoff_connection.csv`.

---

# 15. No invented interface constraints in this task

Do not add:

- Tie;
- contact;
- MPC;
- springs;
- Encastre;
- artificial kinematic constraints.

This task verifies geometry/topology and repairs genuinely missing physical solids only.

Analysis interaction definitions will be handled after Data Check planning.

---

# 16. Real CAE screenshots

If Abaqus/CAE is available, export real viewport screenshots showing:

1. full active Assembly with instance names;
2. left-bank sub-dam / installation / powerhouse;
3. true sub-dam-installation joint close-up;
4. installation-powerhouse joint close-up;
5. sub-dam base with engineered backfill and retained geology;
6. backfill/geology interface mesh;
7. complete cutoff-wall system in global coordinates;
8. left-bank cutoff region;
9. powerhouse/installation cutoff transition;
10. spillway/eco cutoff region;
11. riverbed cutoff / geomembrane connection;
12. right-bank termination;
13. seepage-capable versus structural-only element-type display groups;
14. full seepage-domain overview.

Do not use synthetic diagrams as substitutes for real CAE views.

---

# 17. Required outputs

Create under:

`abaqus-audit/3d-v15.12/`

Required:

- v15.12 CAE;
- v15.12 INP;
- `V15_12_REAL_ASSEMBLY_SEEPAGE_VALIDATION_RESULT.md`;
- `v15_12_instance_transform_audit.csv`;
- `v15_12_global_instance_inventory.csv`;
- `v15_12_real_interface_audit.csv`;
- `v15_12_left_bank_interface_detail.csv`;
- `v15_12_foundation_topology_audit.csv`;
- `v15_12_foundation_components.csv`;
- `v15_12_backfill_material_resolution.csv`;
- `v15_12_pore_pressure_domain_audit.csv`;
- `v15_12_seepage_chain_audit.csv`;
- `v15_12_left_subdam_cutoff_presence_audit.csv`;
- `v15_12_cutoff_connection_detail.csv`;
- `v15_12_geomembrane_cutoff_connection.csv`;
- `v15_12_local_mesh_quality_audit.csv` if geometry is changed;
- actual CAE screenshots.

---

# 18. Required evidence in the result report

The report must explicitly distinguish:

## Verified by actual Abaqus/global geometry

Examples:

- true instance transforms;
- true global bbox;
- real face gap;
- real contact area;
- real shared-node count;
- actual hanging nodes;
- actual nonconforming faces.

## Derived/approximate

Examples:

- source-based station interpolation;
- simplified unsurveyed fishway plan.

## Unresolved

Examples:

- backfill material if source values remain unavailable;
- seepage element formulation where C3D8R remains in an intended groundwater-conducting region;
- any cutoff-wall connection that cannot be proven.

Do not label approximate or assumed values as PASS without qualification.

---

# 19. Acceptance criteria

V15.12 may be considered ready for the next Data Check stage only if:

- all active instance transforms are traceable from CAE/INP;
- critical left-bank interfaces are checked with real faces, not only envelopes;
- unsupported left-sub-dam base area is truly zero or explicitly justified;
- natural geology + backfill have no unintended hanging nodes/nonconforming interfaces;
- seepage-domain element-type coverage is documented;
- the anti-seepage chain is explicitly traced in global coordinates;
- the left-sub-dam cutoff-wall presence/absence is resolved;
- if it was missing, a source-supported local segment is added;
- cutoff-wall / geomembrane connections have no unexplained physical gaps;
- no unrelated geometry is changed;
- no global remesh is performed.

If any of these remain unresolved, report them clearly and do not claim the model is ready for production seepage analysis.

---

# 20. Prohibited

Do not:

- modify `main`;
- force-push;
- globally remesh;
- hard-code Assembly transforms without reading them from CAE/INP;
- hard-code `gap=0`, `hanging_nodes=0`, `unsupported_area=0`, or PASS;
- use bbox overlap as final proof of interface continuity;
- invent cutoff-wall geometry before proving it is missing;
- invent material parameters;
- automatically convert all C3D8R to pore-pressure elements;
- add analysis constraints/interactions;
- run S01-S07;
- claim solver validation.

---

# Final delivery

Commit all v15.12 work to:

`abaqus-audit-task`

Push normally.

Do not force-push.

Return:

- final commit SHA;
- changed-file list;
- final CAE path;
- final INP path;
- active-instance transform summary;
- real-interface summary;
- foundation-topology summary;
- seepage-element coverage summary;
- anti-seepage-chain summary;
- left-subdam-cutoff resolution;
- geomembrane/cutoff connection result;
- unresolved items;
- screenshot paths.

After V15.12, the next task should be a separate Abaqus Data Check / model-definition validation task.
