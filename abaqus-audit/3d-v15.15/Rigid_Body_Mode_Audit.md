# V15.15 Rigid-Body Mode Audit

## Evidence from V15.13

- Source input: `v15_13_S00_BASELINE_SEEPAGE.inp`.
- Source Assembly instances: 59.
- Instances containing pore-pressure elements: 14.
- C3D8R-only structural instances placed in source S00: 45.
- Source solver warning: 99 unconnected regions.
- Source numerical-singularity records captured: 100.

The source CAE audit reports no boundary conditions and no interactions. The generated V15.13 S00 input added bottom U1/U2/U3 sets only for the 14 porous instances; the C3D8R-only structure instances therefore entered the coupled step as unsupported mechanical bodies. The first singularity records identify powerhouse, spillway, tailwater, and other structural instances, which is consistent with the 99-region warning.

## Boundary-condition audit

- Bottom support: present on actual minimum-Z nodes for each active porous instance; not a point pin and not Encastre.
- Lateral mechanical support: none; no lateral U constraint was added.
- Pore-pressure support: transformed upstream/downstream hydrostatic node sets already present in S00; no fixed pressure node was invented.
- Initial pore pressure: V15.15 adds a 5 m-binned hydrostatic field using the midpoint head 3065.5 m on actual active pore nodes to avoid an artificial zero-pressure start.
- Ties, springs, MPCs, and contact interactions: none.
- Material permeability: unchanged.

## V15.15 closure action

Only the 14 instances containing C3D8P/C3D6P elements remain instantiated in the V15.15 S00 active Assembly. All 45 non-hydraulic C3D8R-only part definitions remain in the input for traceability, but are not active solver bodies in this seepage step. This is a solver-domain correction based on element formulation and missing support evidence, not an artificial rigid-body constraint.

## Source singularity sample

- `V15_4_POWERHOUSE_UNIT_01_I.6161`, DOF 3
- `V15_4_POWERHOUSE_UNIT_01_I.6160`, DOF 2
- `V15_4_POWERHOUSE_UNIT_01_I.6160`, DOF 3
- `V15_4_POWERHOUSE_UNIT_01_I.6167`, DOF 1
- `V15_4_POWERHOUSE_UNIT_01_I.6167`, DOF 2
- `V15_4_POWERHOUSE_UNIT_01_I.6167`, DOF 3
- `V15_4_POWERHOUSE_UNIT_04_I.2367`, DOF 3
- `V15_4_POWERHOUSE_UNIT_04_I.2370`, DOF 2
- `V15_4_POWERHOUSE_UNIT_04_I.2370`, DOF 3
- `V15_4_POWERHOUSE_UNIT_04_I.2363`, DOF 1
- `V15_4_POWERHOUSE_UNIT_04_I.2363`, DOF 2
- `V15_4_POWERHOUSE_UNIT_04_I.2363`, DOF 3
- `V15_4_SPILLWAY_RIGHT_ABUTMENT_I.841`, DOF 3
- `V15_4_SPILLWAY_RIGHT_ABUTMENT_I.827`, DOF 2
- `V15_4_SPILLWAY_RIGHT_ABUTMENT_I.827`, DOF 3
- `V15_4_SPILLWAY_RIGHT_ABUTMENT_I.826`, DOF 1
- `V15_4_SPILLWAY_RIGHT_ABUTMENT_I.826`, DOF 2
- `V15_4_SPILLWAY_RIGHT_ABUTMENT_I.826`, DOF 3
- `V15_4_POWERHOUSE_UNIT_03_I.6589`, DOF 2
- `V15_4_POWERHOUSE_UNIT_03_I.6458`, DOF 2

## Final V15.15 verification

- Final Data Check job: `v15_15_S00_SOLVER_CLOSURE_DC5`; no input error, zero-volume/negative-volume error, zero pivot, or Data Check numerical-singularity record.
- Final S00 job: `v15_15_S00_SOLVER_CLOSURE_RUN5`; one period-1.0 increment, zero cutbacks, `.sta` completed successfully, and readable `.odb` with two frames.
- Final full-run zero-pivot count: 0.
- Final full-run solver-problem warnings: 4; these remain reported as numerical warnings and were not hidden.
