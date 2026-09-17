# v13 design correspondence audit

Source deck: `doub_hydropower_part25_geometric_solids_v13_rigidbody_geostatic_fixed.inp`

## Dam geometry

Upstream side: **MIN_X** — geomembrane is closer to min-x dam envelope (9.88e+03 vs 1.13e+04 cumulative m).

|Item|Design|Measured|Status|
|---|---:|---:|---|
|dam_length|295.000000|295.000000|PASS|
|crest_elevation|3079.000000|3079.500000|FAIL|
|foundation_elevation|3052.000000|3055.000000|FAIL|
|maximum_dam_height|27.000000|24.500000|FAIL|

### Slopes

|Segment|Design H:V|Measured H:V|R2|Status|
|---|---:|---:|---:|---|
|upstream_lower|2.500000|14.894261|0.244310|FAIL|
|upstream_middle|1.750000|0.949858|0.007311|FAIL|
|upstream_upper|2.500000|2.484064|0.082948|FAIL|
|downstream_lower|2.000000|2.489248|0.029508|FAIL|
|downstream_upper|2.000000|2.362832|0.101353|FAIL|

Berm/platform node-level candidates are in `v13_horizontal_feature_candidates.csv`. They are not promoted to PASS unless the outer-boundary interpretation is unique; CAE visual confirmation is required when multiple candidates exist.

## Main cutoff / geomembrane

|Item|Design|Measured|Status|
|---|---:|---:|---|
|cutoff_min_bottom|3021.000000|3021.000000|PASS|
|cutoff_thickness|1.000000|1.000000|PASS|
|cutoff_max_depth|49.100000|52.511470|FAIL|
|cutoff_top_global_max|VARIABLE; follows concrete plinth/base underside|3073.511470|UNRESOLVED|

The cutoff maximum depth above is computed at each global-Y station as top-bottom. `3070.10 m` is **not** assumed to be the cutoff top. The model maximum top remains UNRESOLVED until compared with the station-specific concrete plinth/base underside.

## Hydraulic design targets

|Step|Upstream m|Downstream m|
|---|---:|---:|
|S03_NORMAL_RESERVOIR_3076M|3076.00|3053.50|
|S04_DESIGN_FLOOD_3580CMS|3076.00|3060.26|
|S05_CHECK_FLOOD_AND_SEISMIC|3077.35|3061.38|
|S06_DRAWDOWN_TO_3074M|3074.00|3053.50|

The current v13 deck inherited 3055.00 m downstream heads; these targets are written separately so the correction can be generated without changing v13 in place.

## Geology

`v13_geology_geometry_audit.csv` contains model-measured top/base ranges, plan extents, and local vertical-thickness statistics for every active geology/rock instance. Status remains `UNRESOLVED_DESIGN_SURFACE` where station-specific design geological surfaces are not available as machine-readable coordinates; no false PASS is assigned.
