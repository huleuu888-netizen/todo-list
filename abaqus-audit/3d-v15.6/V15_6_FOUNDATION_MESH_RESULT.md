# V15.6 foundation mesh interface repair result

## Scope and freeze

- Geometry unchanged: **YES**. V15.5 structural/engineering instances were copied unchanged.
- Structure mesh unchanged except interface alignment: **YES**; no structural boundary nodes were changed.
- V15.5 active inventory: 359552 nodes, 241850 elements.
- V15.6 active inventory: 685199 nodes, 544190 elements.
- Freeze audit FAIL rows: 0; classification FAIL rows: 0.

## Foundation remesh

- M3 rebuilt: **YES**. 27699 source C3D8P/C3D8R geology cells were regenerated as 330039 conformal child cells.
- The rebuilt geology is one assembly part with a global coordinate node registry; original material layers remain separate Solid Sections.
- M3/M4 source internal faces: 76108; bounded local-block face-generation iterations: 1.
- Conforming regenerated source faces: 74439; nonconforming regenerated source faces: 1669.
- Hanging/nonconformal geology interfaces remaining: **1669**; these are the bounded local-to-remote transition faces and are reported explicitly.
- Remaining separate structural-part interface rows: 10 UNRESOLVED; no Tie/contact/MPC was introduced.

## M3 acceptance metrics

- M3 median/P95/max edge: 3.03 / 11.25 / 75.00135.
- Worst M3 aspect ratio: 64.9991875 at V15_6_FOUNDATION_GEOLOGY_I:328438.
- Mesh holes: **0** relative to regenerated source-cell coverage.
- Overlapping old/new geology elements: **0**; old local cells are fully replaced.

## Audit status

- Mesh quality FAIL: 0; quality UNRESOLVED: 19.
- Critical interfaces: see `v15_6_critical_interface_mesh_audit.csv`; separate baseline structural instances are reported explicitly where shared labels cannot be created without changing the structural assembly.
- Disconnected components: see `v15_6_mesh_island_audit.csv`; intentionally separate material blocks are not merged by Tie/contact.
- Overall result: **UNRESOLVED**.

## Prohibited actions not taken

- No engineering geometry, material, permeability, density, elastic data, support, Encastre, spring, artificial nodal restraint, Tie, contact, MPC, or analysis step was added.
- Abaqus Data Check and S01-S07 were not run; no structural, seepage, stress, or convergence validation is claimed.
