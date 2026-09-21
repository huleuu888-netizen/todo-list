# V15.10 left-bank sub-dam layout and foundation-interface correction

## Scope

- Baseline: V15.9 commit `b4607c722a171222344fe4faa0b296fa1aaf3515`; only the four local fishway/sub-dam Parts were regenerated.
- V15.9 installation bay, powerhouse, tailwater, sediment outlets and eco/spillway frontage are retained unchanged. Geology receives only the 110-cell local foundation-interface repair required by this task; layer/material/Section identities remain.
- No S01-S07, Abaqus Data Check, contact, Tie, MPC, spring, Encastre, artificial restraint or global remesh was run or added.

## Dam-axis sequence

- Corrected left-bank sub-dam: **Y=-245.700..-156.000 m**; crest length **89.700 m**; crest width **7.000 m**.
- Installation bay: **Y=-156.000..-122.000 m**, unchanged; powerhouse starts at **Y=-122.000 m**, unchanged.
- Sub-dam -> installation-bay gap/overlap: **0.000/0.000 m** on the governing dam-axis envelope.
- Installation-bay -> powerhouse gap/overlap: **0.000/0.000 m**. Unintended dam-axis overlap: **0.000 m**.
- The source arithmetic 42.600+15.000+15.000+15.000=87.600 m versus 89.700 m remains `SOURCE_LENGTH_RECONCILIATION_UNRESOLVED=2.100 m`.

## Fishway relocation

- Through-dam station **0+948..0+955** is inside the corrected sub-dam at bbox **X=-99..-92, Y=-245.700..-243.200, Z=3059..3066 m**.
- Opening envelope is **2.500 x 7.000 m**; the route is continuous and the post-crossing reach proceeds to decreasing Y outside the corrected sub-dam.
- Geometric total route length is **1450.20671 m** against the 1407.570 m station target; delta **42.63670986 m** is explicitly UNRESOLVED because the source survey does not define the relocated diagonal approach.

## Structure-geology relation

- Element-level spatial checks report corrected sub-dam, installation-bay and fishway crossing geology overlap **0 elements / 0.000000 m3**.
- V15.9 did not remove geology at the old sub-dam footprint: restored old-footprint elements **0**. The only geology topology change is the local installation-foundation excision of **110 C3D8P cells**; node coordinates and nonlocal layer connectivity remain unchanged.
- Geology organization remains **36 leaf sets, 43 Assembly sets, 36 named Sections**; unclassified **0**, duplicate leaf membership **0**, nonconforming faces **0**, hanging nodes **0**.

## Local mesh quality

- Corrected sub-dam actual mesh: nodes **3838**, elements **2756**, min/median/P95/max edge **1/1.902126627/2.4916667/2.5 m**, max aspect ratio **2.4916667**, invalid/negative volume **0**, collapsed **0**.
- Only the corrected sub-dam, fishway crossing and directly affected local audit region were regenerated; global remesh **NO**.

## Status

- Overall: **PASS WITH EXPLICIT UNRESOLVED ITEMS**.
- Abaqus Data Check: **NOT RUN** by task scope.
- S01-S07: **NOT RUN** by task scope.
