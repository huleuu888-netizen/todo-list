# V15 geometry-only audit

## Scope

This deliverable contains geometry only. No S01-S02 mechanical steps, S03-S07 hydraulic cases, solver run, contact optimization, material change, rigid-body repair, node restraint, Encastre, spring, or new V15 Tie was generated in the geometry-only deck.

Source geometry: doub_hydropower_part25_geometric_solids_v15_appurtenance_rebuild.inp; output geometry deck: doub_hydropower_part25_geometric_solids_v15_geometry_only.inp.

## Layout result

- Right-to-left / high-Y-to-low-Y order: spillway -> ecological release -> powerhouse; installation bay is immediately left of the powerhouse in X.
- Tailwater begins at the powerhouse downstream X face and extends downstream with a 64.4 m reverse-slope segment followed by the level connection envelope.
- The v14 left-bank geology/excavation context is reused and not overwritten; no artificial excavation depression was introduced.
- The layout PNG is v15_layout_check.png; numeric evidence is in v15_geometry_inventory.csv and v15_dimension_check.csv.

## Major instances

| Group | Instances | Geometry | Status |
|---|---:|---|---|
| POWERHOUSE | 4 | 106.6 m Y x 56.5 m X; founding 3029.70; top 3081.00 | PASS |
| INSTALLATION_BAY | 1 | 34 m X; floor plane 3062.00; shared Y envelope | PASS |
| TAILWATER | 1 | 71.6 m Y; hydraulic datum 3036.90 -> 3053.00; lining 0.8 m | PASS |
| ECO_RELEASE | 2 | two 12.5 m bays; inlet bottom 3058.00; height 27.5 m | PASS |
| SPILLWAY | 8 bays + walls + basin | eight bays; common basin 107 m X; slab datum 3047.50 | PASS |
| LEFT_BANK_CONTEXT | retained v14 | existing geology/excavation context reused | REUSED |

## Stop rule

No S01-S07 job, Data Check, or finite-element calculation was run for this geometry-only task. The model is ready for a later, separately authorized analysis task.
