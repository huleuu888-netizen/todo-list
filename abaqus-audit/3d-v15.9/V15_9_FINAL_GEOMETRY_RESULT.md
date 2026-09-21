# V15.9 final geometry correction result

## Scope and preservation

- Baseline: V15.8 geology organization commit 6fdd9c9403cea3c38fa59053b61b0d1f5e239203.
- Engineering Parts/Instances: 58/58 -> 58/58; only the four requested correction groups changed.
- V15.8 geology Part, 36 leaf sets, 43 Assembly sets, material/Section identities: PRESERVED.
- Geology mesh: conformal topology frozen; nonconforming faces **0**; hanging nodes **0**.
- No material parameter change, Tie/contact/MPC, artificial restraint, or global remesh was introduced.

## Installation bay

- Y/dam-axis length: **34.000 m** (-156.000..-122.000 (34.000 m)).
- Lower/foundation X width: **56.500 m** (-64.000..-7.500 (56.500 m)).
- Upper-room X width: **20.000 m** (-47.500..-27.500 (20.000 m)).
- Floor elevation: **3062.000 m**.
- Powerhouse adjacency: direct at Y=-122.000; the erroneous 106.600 m installation-bay Y envelope is absent.

## Left-bank sub-dam

- Governing crest length: **89.700 m**; crest width **7.000 m**.
- Sections retained as 42.600 + 15.000 + 15.000 + 15.000 m = 87.600 m.
- Remaining **2.100 m** is explicitly `SOURCE_LENGTH_RECONCILIATION_UNRESOLVED`; no fifth block or stretched block was invented.
- Slope break: **3072.000 m**; local foundation/backfill datum: **3059.000 m**.
- Fishway crossing remains inside the corrected sub-dam envelope at the documented local route.

## Sediment flushing

- Exactly **2** continuous outlets, one for units 01-02 and one for units 03-04.
- Upstream and downstream working openings: **2.500 x 2.000 m** at sills 3037.000 m and 3043.000 m.
- Downstream maintenance-gate section: **2.500 x 3.000 m** per outlet.

## Ecological release and spillway

- Eco span: **12.500 m**, directly between powerhouse and spillway.
- Eco-to-spillway interface gap: **0.000 m**.
- Spillway clear openings: **8 x 7.000 m**; ecological openings: **2 x 2.500 x 5.000 m**.
- Combined flood-release frontage: **109.000 m**, target 109.000 m.
- Exact side-closure/intermediate-pier subdivision remains **UNRESOLVED** where the source is not explicit; global frontage and adjacency PASS.

## Verification summary

- Geometry change audit: **PASS**; non-target engineering geometry retained.
- Geology set coverage: **PASS**; unclassified elements **0**; duplicate leaf membership **0**.
- Local mesh policy: **PASS**; only corrected engineering regions were regenerated; no global remesh.
- Overall: **PASS WITH EXPLICIT SOURCE UNRESOLVED ITEMS**.
- Abaqus Data Check: **NOT RUN** by task scope.
- S01-S07: **NOT RUN** by task scope.
