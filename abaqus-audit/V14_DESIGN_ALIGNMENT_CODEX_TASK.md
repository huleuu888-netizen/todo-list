# Codex task: v14 Duobu 3-D design-alignment correction

## Repository / branch

- Repository: `huleuu888-netizen/todo-list`
- Work only on branch: `abaqus-audit-task`
- Do **not** modify `main`.
- Preserve all v12 and v13 files unchanged.
- Treat v13 as the mechanically stable core baseline, not as the final design-correspondence model.
- Existing auto-generated `abaqus-audit/3d-v14/` output is a preliminary tailwater-only pass and may be replaced/regenerated on this branch after the fixes below.

## Source baseline

Use:

`abaqus-audit/3d-v13/doub_hydropower_part25_geometric_solids_v13_rigidbody_geostatic_fixed.inp`

as the source deck for v14.

Do not silently re-enable the 31 suppressed appurtenant instances. Appurtenant restoration remains a separate unresolved task.

## Goal

Produce an auditable v14 core model in which the P25 dam geometry, cutoff/geomembrane relationship, hydraulic load cases, and geology/foundation contact interpretation are aligned with the project design data as far as the available evidence supports.

Use `PASS`, `FAIL`, and `UNRESOLVED` explicitly. Never force a geometry change merely to match a single scalar value when the design meaning is ambiguous.

---

## A. Fix the current audit logic before modifying geometry

Update `abaqus-audit/audit_v13_design_correspondence.py` (or create a v14 successor) so that the design targets are interpreted correctly.

### A1. Crest elevation

The design description is not a single 3079.00 m plane:

- middle crest elevation: **3079.50 m**
- crest transitions by slope to both end elevations: **3079.00 m**

Therefore a measured maximum crest of 3079.50 m is **not** a failure by itself. Audit the crest as a longitudinal profile/range, not as `max_z == 3079.00`.

### A2. Upstream slope break elevations

Use the documented upstream slope zoning:

- above 3070.10 m: H:V = **2.5:1**
- 3070.10 m to 3065.80 m: H:V = **1.75:1**
- below 3065.80 m: H:V = **2.5:1**

The current script value `3059.00 m` is not the correct lower slope-break elevation and must not be used.

### A3. Downstream geometry targets

- downstream slope: H:V = **2.0:1**
- berm elevation: **3065.00 m**
- berm width: **3.00 m**
- downstream pressure platform width: **10.00 m**

Do not fit slopes from the entire 3-D node cloud. Extract outer-boundary points on representative cross-sections and fit/measure each segment independently.

Recommended cross-sections: at least 5-7 stations spanning the 295 m P25 section, including both ends and the middle.

Required output:

`abaqus-audit/3d-v14/v14_cross_section_geometry.csv`

with station, side, segment, design H:V, measured H:V, elevation interval, fit quality/residual, status, and notes.

---

## B. Dam-foundation elevation audit: do not blindly extend the dam downward

Design data state:

- dam foundation elevation: **3052.00 m**
- maximum dam height: **27.00 m**

The current mesh audit found the active P25 dam-fill body minimum near **3055.00 m** and a maximum near **3079.50 m**.

Do **not** simply translate or stretch all dam-fill nodes down by 3 m.

Instead create a station-/interface-level audit of the real dam-bottom to river/foundation top relationship:

For every active P25 dam-fill region, report:

- minimum global elevation
- bottom-surface elevations by station
- adjacent river/foundation top elevation
- gap/overlap distance
- existing Tie/contact relation
- whether 3052.00 m is a local lowest foundation control elevation or a required continuous dam-bottom elevation
- status: PASS / FAIL / UNRESOLVED

Required output:

`abaqus-audit/3d-v14/v14_dam_foundation_contact_audit.csv`

Only modify geometry if the source evidence and interface audit prove that an actual missing 3052-3055 m dam/foundation region exists.

---

## C. Main cutoff wall / geomembrane audit

Current v13 main cutoff measurements:

- thickness: **1.00 m** -> retain unless evidence contradicts it
- bottom: **3021.00 m** -> retain for the main riverbed P25 section unless station-specific design evidence says otherwise
- current top: **3073.51147 m**
- current depth: **52.51147 m**

Documented design statements include:

- main riverbed cutoff wall thickness: **1.00 m**
- main riverbed wall bottom: **3021.00 m**
- maximum construction depth: **49.10 m**
- upstream cofferdam crest / upper seepage-system transition elevation: **3070.10 m**
- geomembrane above the cofferdam region connects into the cutoff-wall top through the concrete connection/plinth system

Important: **do not automatically set every cutoff-top node to 3070.10 m merely because 3021 + 49.10 = 3070.10.** The report describes 49.10 m as a maximum depth and the wall top is tied to the concrete connection/plinth geometry.

Perform a station-level audit first.

Required output:

`abaqus-audit/3d-v14/v14_cutoff_plinth_station_audit.csv`

Columns should include at least:

- station/global-Y
- wall bottom
- wall top
- wall depth
- geomembrane connection elevation
- concrete/plinth/base-underside elevation if recoverable from the model/source geometry
- design target/source basis
- delta
- PASS / FAIL / UNRESOLVED

If evidence shows the main P25 cutoff-to-geomembrane connection should be at 3070.10 m, then modify only the justified region and rebuild the geomembrane consistently. Preserve hydraulic equivalence (`t/k`) if the geomembrane remains a 1.0 m equivalent porous layer.

---

## D. Correct the hydraulic load cases

The v13 source inherited a constant downstream head of 3055.00 m for all reservoir steps. Replace this with the explicit design-condition pairs below.

### D1. Normal reservoir

- upstream H = **3076.00 m**
- downstream H = **3053.50 m**

### D2. Design flood

- upstream H = **3076.00 m** for the explicit stability-condition pair currently adopted
- downstream H = **3060.26 m**

The project text is internally inconsistent elsewhere about the design-flood upstream level. Record this inconsistency; do not hide it.

### D3. Check flood

- upstream H = **3077.35 m**
- downstream H = **3061.38 m**

### D4. Drawdown / dead-water condition

- upstream H = **3074.00 m**
- downstream H = **3053.50 m**

### D5. Seismic case must be separate from check flood

The current step name `S05_CHECK_FLOOD_AND_SEISMIC` mixes two different design cases. Do not keep them combined.

Separate the cases so that at minimum the model distinguishes:

- `S03_NORMAL_RESERVOIR`
- `S04_DESIGN_FLOOD`
- `S05_CHECK_FLOOD`
- `S06_DRAWDOWN_DEADWATER`
- `S07_NORMAL_RESERVOIR_SEISMIC_0P206G`

For the seismic condition use the normal-reservoir water pair:

- upstream 3076.00 m
- downstream 3053.50 m
- horizontal seismic coefficient/equivalent gravity remains **0.206 g** only in the seismic case

Do not apply the seismic body load to the check-flood case unless a source explicitly requires that combination.

### D6. Re-audit the physical downstream boundary surface

Do not only replace numeric pressure values on the existing `V12_D_*` node sets.

The current downstream head sets are derived from a specific drainage-body maximum-x edge and many nodes are at z = 3055.00 m. For a 3053.50 m tailwater this produces zero prescribed pore pressure on those nodes. Verify whether these nodes actually represent the real wetted downstream/tailwater boundary.

Rebuild the downstream hydraulic boundary sets/surfaces if necessary so that the prescribed head condition is applied to the physically correct external boundary.

Use:

`p = 9.81 * max(H - z, 0)` kPa

and write a reproducible audit.

Required output:

`abaqus-audit/3d-v14/v14_hydraulic_bc_audit.csv`

with step, boundary, node/surface, z, H, prescribed POR, and basis.

---

## E. Geology geometry audit

Retain the existing model-measured geology audit, but regenerate it under v14 after any justified geometry change.

For each active geology/rock instance report:

- x/y plan extents
- minimum/maximum elevation
- local base/top ranges
- local thickness min/median/max
- adjacent interface relation
- design evidence availability
- status

Do not mark a geology layer `PASS` solely because its material name matches a report layer. If station-specific design surfaces are unavailable, mark `UNRESOLVED_DESIGN_SURFACE`.

Required output:

`abaqus-audit/3d-v14/v14_geology_geometry_audit.csv`

---

## F. Preserve the proven v13 mechanical baseline unless a justified geometry change requires rerun

Do not introduce arbitrary nodal restraints or suppress additional active core parts just to obtain convergence.

Retain the genuine deep-rock `BASE_FIX` concept unless a documented redesign is required.

Any geometry change to dam/foundation/cutoff/geomembrane must trigger fresh Abaqus validation.

---

## G. Abaqus validation gates

The output must not be called `VALIDATED=YES` just because the INP is generated.

### Gate 1: input / mechanical baseline

- CAE import or input syntax: PASS
- Data Check: PASS
- S01 geostatic: complete, no numerical singularity / zero pivot
- S02 construction/geostatic stabilization: complete

### Gate 2: hydraulic cases

- S03 normal reservoir completes
- S04 design flood completes
- S05 check flood completes
- S06 drawdown/dead-water completes
- S07 seismic case completes if included in this v14 run

### Gate 3: hydraulic physical validation

At final converged S03 steady state, quantitatively check:

- POR continuity across critical exact and nonconformal interfaces
- especially left/river geology, river/right geology, dam/river foundation, geomembrane/fill, geomembrane/cutoff
- boundary-integrated `Qin`
- boundary-integrated `Qout`
- `mass_balance_error = abs(Qin-Qout)/max(abs(Qin),abs(Qout))`
- no unexplained hydraulic bypass around cutoff/geomembrane

Do not equate a mechanical Tie with proven hydraulic continuity.

---

## H. Required v14 files

Create/regenerate at least:

- `abaqus-audit/3d-v14/V14_DESIGN_ALIGNMENT_DIAGNOSIS.md`
- `abaqus-audit/3d-v14/V14_DESIGN_ALIGNMENT_RESULT.md`
- `abaqus-audit/3d-v14/v14_validation_status.txt`
- `abaqus-audit/3d-v14/v14_geometry_correspondence.csv`
- `abaqus-audit/3d-v14/v14_cross_section_geometry.csv`
- `abaqus-audit/3d-v14/v14_dam_foundation_contact_audit.csv`
- `abaqus-audit/3d-v14/v14_cutoff_plinth_station_audit.csv`
- `abaqus-audit/3d-v14/v14_geology_geometry_audit.csv`
- `abaqus-audit/3d-v14/v14_hydraulic_bc_audit.csv`
- `abaqus-audit/3d-v14/v14_hydraulic_interface_check.csv`
- `abaqus-audit/3d-v14/v14_mass_balance.txt`
- `abaqus-audit/3d-v14/v14_boundary_flux.csv`
- `abaqus-audit/3d-v14/doub_hydropower_part25_geometric_solids_v14_design_aligned.inp`
- corresponding `.cae` if Abaqus is available
- build/extraction scripts and relevant `.dat/.msg/.sta` logs

If Abaqus is unavailable in the execution environment, explicitly mark solver gates `NOT_RUN` and do not claim validation.

---

## I. Final acceptance / reporting rules

The final report must distinguish these categories:

1. **confirmed design match**
2. **confirmed mismatch and corrected**
3. **modeling equivalence** (for example the 1.0 m equivalent geomembrane layer)
4. **unresolved because design evidence is insufficient**
5. **unresolved solver/ODB verification**

Do not overwrite or rewrite historical v12/v13 results to make v14 look cleaner.

Commit all v14 work only to `abaqus-audit-task` and report the final commit SHA, exact validation status, and any remaining unresolved items.
