# v12 3-D hydro-mechanical correction result

## Scope and preservation

The exact v11 source was read from `D:\Backup\Documents\ChatGPT\多步水电站\Codex生成模型\outputs\doub_hydropower_part25_geometric_solids_v11_hydro.inp` and was not modified. v12 is a corrected copy with an exported keyword deck.

- Source SHA-256: `52C39E6A713F423D4BC4F29742B323D6FDA3CBB80CE2C47A82C2F5124A742A27`
- Abaqus unit system: m-kN-s-tonne; pressure in kPa; gravity 9.81 m/s2 in global -Z.
- Main model domain: 295 m P25 riverbed section, with the existing left/river/right geology and appurtenant structures retained.

## Changes versus v11

- Regions with task/source-supported permeability (14 Q geology zones, dam fill/cutoff, and the geomembrane) use C3D8P/C3D6P; unsupported rock/foundation materials remain C3D8R and are flagged in the element/material CSVs.
- S01 is `*Geostatic`; S02-S06 are coupled pore-fluid `*Soils, consolidation, end=SS` steps with pore output.
- All 14 geological/foundation permeability values are present in `v12_3d_materials.csv`.
- Constant mechanical pressure loads were removed. Direct head BCs use p=9.81 max(H-z,0).
- Cutoff wall local thickness is 1.0 m (x=-36 to -35) and main-section base is z/local elevation 3021.0 m; the separate powerhouse wall remains at its source geometry.
- An actual assigned upstream geomembrane equivalent C3D8P layer is connected to the existing upstream fill surface and cutoff top.
- Density conversions are applied only to explicit report unit-weight examples; unsupported source-unit cases are marked.

## Permeability table

See `v12_3d_materials.csv`; geological source values are cm/s divided by 100 to m/s.

- `Q4DEL`: 2.33e-05 m/s
- `Q4AL_SGR2`: 0.000233 m/s
- `Q4AL_SGR1`: 5.8e-05 m/s
- `Q3AL_V`: 4.46e-06 m/s
- `Q3AL_IV2`: 2.35e-06 m/s
- `Q3AL_IV1`: 5.48e-06 m/s
- `Q3AL_III`: 8.49e-05 m/s
- `Q3AL_II`: 5.89e-07 m/s
- `Q3AL_I`: 1.14e-05 m/s
- `Q2FGL_V`: 1.14e-05 m/s
- `Q2FGL_IV`: 1.7e-06 m/s
- `Q2FGL_III`: 3.26e-07 m/s
- `Q2FGL_II`: 8.35e-07 m/s
- `Q2FGL_I`: 2.5e-07 m/s
- GEOMEMBRANE: 4.5e-11 m/s; equivalent layer thickness 1.0 m; t/k=2.2222e10 s.
- CUTOFF WALL: 1.0e-8 m/s.

## Hydraulic boundary conditions

- S03 normal: upstream H=3076.00 m.
- S04 design-flood discharge: H=3076.00 m hold level because a separate supported design-flood level is not provided; this is unresolved.
- S05 check flood: upstream H=3077.35 m.
- S06 drawdown/dead-water: upstream H=3074.00 m.
- Downstream/tailwater: H=3055.00 m, the documented 3054-3056 m normal river range; flood-case tailwater variation is unresolved.

## Connectivity and hydraulic continuity

- Exact face groups: 40; aggregate nonconformal groups: 3; total generated mechanical Ties including geomembrane: 44.
- Exact-interface hydraulic `*Equation` groups: 0 / 0 node pairs; exact pressure continuity is carried by the corresponding surface Tie constraints because Abaqus eliminates tied secondary DOF 8.
- Nonconformal aggregate Ties require Abaqus ODB verification of boundary POR continuity; no unsupported claim is made here.

## Initial stress, sequence, and plasticity

S01 establishes gravity/geostatic equilibrium, S02 is a labelled construction/closure stabilization step on the active mesh, S03 normal impoundment, S04 design-flood hold, S05 check flood plus 0.206g equivalent horizontal gravity, and S06 drawdown. True element activation staging and source-complete plastic dilation remain unresolved; baseline is elastic coupled seepage.

## BX decision

BX01/BX02/BX03 are within the intended retained right-bank domain and were repositioned to report ranges. The linear z remap preserves plan footprint but is a geometric correction, not a substitute for DBK-D-34-37 surveyed surfaces.

## Validation status

CAE import passed in Abaqus 2022 and the corrected INP passed Abaqus/Standard datacheck (1118 warnings in the DAT file and 1 warning in the MSG file). The coupled job `v12_3d_fullrun` was stopped in S01 geostatic increment 1 after severe numerical-singularity/divergence messages; its partial ODB contains one S01 frame at time 0.0 and no frames in S02-S06. Normal seepage, POR continuity, and hydraulic mass balance are therefore not claimed. The complete status is recorded in `v12_3d_validation_status.txt`.
