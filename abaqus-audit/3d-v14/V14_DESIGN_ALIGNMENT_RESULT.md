# V14 Design Alignment Result

## Confirmed design match

- 295.00 m longitudinal dam extent.
- Crest range interpretation 3079.00–3079.50 m; 3079.50 m maximum is accepted as the documented middle crest range.
- Main cutoff bottom 3021.00 m and thickness 1.00 m.

## Confirmed mismatch and corrected

- Downstream pore-head values were regenerated for the five required hydraulic cases.
- The mixed `S05_CHECK_FLOOD_AND_SEISMIC` case was separated: S05 is check flood only, S07 carries the 0.206 g horizontal equivalent gravity.

## Modeling equivalence

- The existing 1.00 m geomembrane is retained as an equivalent porous layer; its V13 t/k interpretation and ties are unchanged.

## Unresolved design evidence

- Cross-section slope fits, berm/platform boundary, continuous 3052.00 m dam-bottom interpretation, cutoff plinth underside, geology design surfaces and physical tailwater surface are unresolved from available model/project data.

## Solver and ODB

- CAE import: `PASS`; Data Check: `PASS`; V14 S01: `PASS`; V14 S02: `PASS`.
- Data Check warning count: `1287_DAT_1_MSG` (warnings do not include an input/analysis ERROR).
- Hydraulic steps: S03_NORMAL_RESERVOIR=NOT_VERIFIED, S04_DESIGN_FLOOD=NOT_VERIFIED, S05_CHECK_FLOOD=NOT_VERIFIED, S06_DRAWDOWN_DEADWATER=NOT_VERIFIED, S07_NORMAL_RESERVOIR_SEISMIC_0P206G=NOT_VERIFIED.
- Partial ODB frame evidence: `S01_GEOLOGICAL_INITIAL_STRESS=2; S02_CONSTRUCTION_AND_CLOSURE=2; S03_NORMAL_RESERVOIR=24; S04_DESIGN_FLOOD=0; S05_CHECK_FLOOD=0; S06_DRAWDOWN_DEADWATER=0; S07_NORMAL_RESERVOIR_SEISMIC_0P206G=0`; S03 has POR/FLVEL fields, but the formal full-run completion marker is absent, so S03 remains NOT_VERIFIED.
- Full-run status: `NOT_COMPLETED`; numerical singularity scan: `NO_SINGULARITY_OBSERVED`. Gate 3 remains UNRESOLVED because no quantitative interface POR/Qin/Qout extraction was completed.
- Full-run terminal evidence: `***ERROR: Process terminated by external request (SIGTERM or SIGINT received).`.
