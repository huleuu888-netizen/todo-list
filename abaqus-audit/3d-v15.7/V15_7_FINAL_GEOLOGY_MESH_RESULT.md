# V15.7 final geology mesh cleanup result

## Scope and frozen baseline

- Geometry unchanged: **YES**. V15.6 engineering parts are copied unchanged.
- Structural mesh unchanged: **YES**. Only the V15.6 geology part/instance is replaced.
- V15.6 active inventory: 685199 nodes, 544190 elements.
- V15.7 active inventory: 955497 nodes, 805945 elements.
- Freeze check FAIL rows: 0; classification FAIL rows: 0.

## Geology repair

- Starting nonconforming geology faces: **1669** (V15.6 recorded value).
- Source geology cells rebuilt: **27699**; repaired candidate rows: **27345**.
- Compatible face-propagation iterations: **18**.
- Final continuous same-material nonconforming faces: **0**.
- Final all-geology nonconforming faces: **0**.
- Final hanging-node count inside continuous geology: **0**.
- Unintended disconnected continuous-geology components: **4**.
- Mesh holes: **0** in regenerated source-cell coverage; overlap count: **0**.

## M3 and transition metrics

- M3 median/P95/max edge: **6.6667675 / 10 / 13.6366091**.
- M3-D median/P95/max edge: **8.00013225 / 10 / 13.6366091**.
- Worst M3 aspect ratio: **52.08375** at `V15_7_FOUNDATION_GEOLOGY_I:391702`.
- M3 quality invalid/negative volume, collapsed, duplicate element counts: **0 / 0 / 0**.
- Mesh transition ratios are in `v15_7_mesh_transition_audit.csv`; any unresolved far-field advisory is retained explicitly.

## Required outputs and status

- Total nodes/elements: **955497 / 805945**.
- Overall result: **UNRESOLVED**.
- Abaqus Data Check: **NOT RUN**.
- S01-S07: **NOT RUN**.
- Structural validation, seepage validation, and mesh convergence are not claimed.

## Prohibited actions not taken

- No engineering geometry, structural mesh, material, permeability, density, elastic parameter, Encastre, spring, artificial nodal restraint, Tie, contact, MPC, or analysis step was added.
- Structure-to-foundation surfaces remain separate part interfaces and are audited without forced shared nodes.
