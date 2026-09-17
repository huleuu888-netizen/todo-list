# v14 design alignment scope

v14 is generated from the converged v13 core baseline without overwriting v13.

Changes in this pure-Python generation pass are deliberately limited to source-supported downstream/tailwater heads:

- S03 normal: 3053.50 m
- S04 design flood: 3060.26 m
- S05 check flood: 3061.38 m
- S06 drawdown/dead water: 3053.50 m

Upstream heads are retained as S03=3076.00 m, S04=3076.00 m, S05=3077.35 m, S06=3074.00 m. The supplied project text contains an internal inconsistency for the design-flood upstream level; the explicit stability-condition pair is retained rather than silently selecting another narrative value.

Geometry is not numerically altered in this pass. `../3d-v13/design-correspondence/` contains direct mesh measurements. In particular, 3070.10 m is not automatically imposed as the main cutoff-wall top because the report defines the wall top by the concrete plinth/base underside and gives 49.10 m as a maximum wall depth, not as a universal wall height.

This workflow cannot create an Abaqus CAE database. The v14 INP must be imported/saved in Abaqus/CAE and re-run before v14 can be called solver-validated.
