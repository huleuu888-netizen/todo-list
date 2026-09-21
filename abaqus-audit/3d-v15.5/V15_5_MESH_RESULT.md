# V15.5 mesh-only refinement result

The frozen V15.4 deck was used as the sole geometry source. No engineering coordinates, materials, supports, Tie/contact, Encastre, spring, or analysis step was added.

## Geometry freeze

- V15.4 active inventory: 288095 nodes, 195428 elements.
- V15.5 active inventory: 359552 nodes, 241850 elements.
- Count change: 24.80% nodes, 23.75% elements.
- Geometry freeze: PASS; bounding boxes are compared in `v15_5_geometry_freeze_check.csv`.

## Actual mesh changes

- Remeshed instance plans: 24. Local C3D8P/C3D8R geology elements were subdivided only where centroid distance justified M3 refinement; geomembrane critical elements use in-plane subdivision and cutoff-wall thickness is not artificially reinterpreted.
- Near-field and transition/far-field geology are mutually exclusive by element centroid distance: 0-10 m, 10-60 m, and >60 m.
- Retained far-field orphan mesh was not globally refined.
- Orphan replacement map is in `v15_5_geology_remesh_map.csv`; any hanging-node risk at a retained orphan boundary remains explicitly documented.

## Mesh quality

- Quality rows: 17; FAIL: 0; UNRESOLVED: 15.
- Geometry coverage and element connectivity are checked element-by-element; zero/negative volume, collapsed, duplicate-element findings are FAIL.
- Transition audit rows: 5; critical-interface rows: 10.

## Scope limits

- Abaqus Data Check and S01-S07 were not run. No mesh convergence, structural, seepage, or stress validation is claimed.
- Remaining UNRESOLVED items concern retained orphan-mesh conformity/native geometry limitations and independent-part node/interface islands; no Tie or contact was added to hide them.
