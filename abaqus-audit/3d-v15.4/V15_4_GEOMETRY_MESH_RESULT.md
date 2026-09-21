# V15.4 geometry and targeted mesh refinement result

Geometry correction and mesh refinement continue from commit `02c7d1664a37d1c008ef48a91e0a8f495d3241f0`. Phase A geometry was completed before Phase B local mesh generation. No S01-S07, solver job or Data Check was run. No material, restraint, Encastre, spring, artificial support or Tie was added.

## Geometry correction

- The left-bank sub-dam is back in the fixed hub frame at x=-112..-64, y=-122..-15, adjacent to the installation-bay interface; crest 3079.00 m and true 2.5 m x 7.0 m fishway void.
- The fishway retains station length 1407.57 m while returning to the real local sub-dam at station 0+948..0+955; the long route is piecewise rather than relocating the sub-dam.
- The spillway has eight 7.0 m bays, seven explicit intermediate piers and an explicit right abutment; no 30+ m object is classified as a pier.
- The ecological-release crest is held at 3079.00 m; the 27.5 m maximum-height reconciliation is explicitly UNRESOLVED because the source foundation datum is not direct.
- Two sediment-flushing outlets were added, one shared by units 1-2 and one by units 3-4, with 2.5 m x 2.0 m upstream/downstream voids at the documented sills.
- v15.3 orphan-mesh excavation results were preserved; additional local cut cells were removed for the relocated sub-dam and fixed-hub fishway. No active cutter instance remains.

## Geometry status

- Dimension audit: PASS=19, UNRESOLVED=1. Layout audit: PASS=8, UNRESOLVED=1. Opening audit: PASS=28. Sediment-flushing audit: PASS=2. Fishway station audit: PASS=11.
- Excavation audit: UNRESOLVED=9; native Boolean certification remains UNRESOLVED because the retained geology is orphan C3D8P mesh.
- Interference audit: PASS=20, UNRESOLVED=4. Overall geometry: PASS for corrected hub layout and required openings, with source-data UNRESOLVED items for exact fishway survey, eco foundation reconciliation and native geology Boolean provenance.

## Targeted mesh refinement

- Mesh levels prepared: COARSE, MEDIUM and FINE_LOCAL. The working v15.4 deck uses local graded structural meshes; remote geology is not globally refined.
- Density audit rows: 14. Quality audit rows: 14; quality FAIL rows: 0. Total active mesh inventory: 288095 nodes, 195428 elements.
- Mesh quality: PASS for generated structured C3D8R components with no zero/negative-volume or duplicate-element findings; retained orphan geology remesh limitations are UNRESOLVED rather than hidden.

## Version safety

All outputs are under `abaqus-audit/3d-v15.4/`. v12/v13/v14/v15/v15.2/v15.3 outputs were not overwritten.
