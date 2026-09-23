# V15.20 Q3AL_III Final Parameter Basis

FINAL_STATUS = CALIBRATION_REQUIRED

## Current values

| Parameter | Current value | Classification |
|---|---:|---|
| Density | `2.13` | ASSUMED |
| Permeability | `8.49e-05` | CALIBRATION_REQUIRED |

## Source and traceability

- The values are captured from the existing V15.15 active input deck.
- The compacted sand/gravel mapping is documented in
  `v15_13_backfill_material_final_basis.csv`.
- The active geology mapping is documented in
  `v15_13_permeability_material_audit.csv`.
- V15.18 records density and permeability as pending/check items rather than
  source-verified final parameters.

This establishes model traceability only. It does not establish an independent
laboratory or field source for both Q3AL_III uses.

## Equivalence basis

The engineering backfill is represented by the `Q3AL_III` model name as an
engineering equivalent because no dedicated calibrated backfill coefficient is
present in the current evidence. The same model name is also used for a
natural Q3AL_III alluvial geology layer. The two uses must not be assumed to
have identical hydraulic behavior without an approved equivalence basis.

## Applicable scope

- The density and permeability apply only to the existing Q3AL_III mappings
  recorded in the current input and audit tables.
- They are not a universal value for other alluvial layers, rock materials,
  curtains, or structural-only regions.
- They are retained for audit traceability and are not modified to improve
  solver convergence.

## Final classification

- Density: `ASSUMED` pending separate compaction/moisture and natural-layer
  source confirmation.
- Permeability: `CALIBRATION_REQUIRED` pending direct evidence or a reviewed
  bounded inversion.
- Overall Q3AL_III parameter basis: `CALIBRATION_REQUIRED`.

No `VERIFIED` status is claimed. Before S01-S07, provide source-backed bounds
or formal approval of the equivalent mapping and define lower/central/upper
sensitivity cases for discharge, hydraulic gradient, and pore pressure.
