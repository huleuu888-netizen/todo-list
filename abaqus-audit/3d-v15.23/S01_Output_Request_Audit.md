# V15.23 S01 Output Request Audit

## Current S01 output variables

The frozen S01 input contains one field-output block and one preselected
history-output block:

```text
*Output, field, variable=PRESELECT
*Node Output
POR, RF, U
*Element Output, directions=YES
FLVEL, POR, S, EVOL
*Output, history, variable=PRESELECT
```

The completed ODB confirms the final-frame field keys are:

```text
E; EVOL; FLVEL; POR; RF; S; SAT; U; VOIDR
```

The history database contains 25 assembly energy/time records. It does not
contain a boundary flow-rate history.

## Missing variables and why they are missing

### Hydraulic head

`HEAD` is not a direct output variable in this coupled pore-pressure output
set. `POR` is pore fluid pressure. A hydraulic/piezometric head result must be
formed from pressure, elevation, fluid specific weight, and the model's
self-consistent unit convention. The existing ODB does not contain a direct
head field, and V15.23 does not invent one.

### Flow rate

`FLVEL` is the pore-fluid effective velocity at element integration points. It
is not a boundary-integrated discharge. The source input also does not request
`RVF`, the reaction fluid volume flux associated with prescribed pore-pressure
boundaries. The model uses prescribed pore pressure at DOF 8 on `S00_U_*` and
`S00_D_*` boundary node sets, so `RVF` is the appropriate next candidate for
boundary-flow extraction. `CFF` was not added because the source deck contains
no concentrated fluid-flow (`*CFLOW`) boundary.

### Hydraulic gradient

No direct hydraulic-gradient output is present. `HFL` must not be used as a
hydraulic-gradient substitute because it is a heat-flux output variable. The
gradient must be calculated from a documented pressure/elevation basis, or
from a supported pore-flow post-processing method after the required outputs
are available.

### Velocity

`FLVEL` already exists as element integration-point effective velocity. The
output-completion input additionally requests `FLDVEL` as nodal fluid velocity
to support boundary and nodal post-processing.

## POR audit

The V15.22 extraction read `POR` as a scalar field and reported both field
locations present in the ODB: `INTEGRATION_POINT` and `NODAL`. This is not a
variable-name or scalar/vector read error. The range
`-3282.876220703125` to `3286.01904296875` is raw model pore pressure in the
model's pressure units. It should not be relabeled as water head.

The large range may reflect the model pressure scale, prescribed boundary
values, initial pore-pressure values, and the combination of nodal and
integration-point locations. A physical anomaly cannot be proven from the
global min/max alone. The next audit must map POR values to the actual
upstream/downstream node sets and elevations before assigning a head or
gradient interpretation.

## V15.23 output-only correction

`modify_S01_output_request.py` creates
`v15_23_S01_OUTPUT_COMPLETION.inp` without overwriting the frozen S01 input.
The generated input adds these node outputs:

```text
POR, RF, U, COORD, RVF, FLDVEL
```

It retains these element outputs:

```text
FLVEL, POR, S, EVOL
```

No geometry, mesh, material, permeability, load, or boundary data are
changed. No artificial constraint or stabilization is added.

## References

- Abaqus/Standard nodal variables, including `RVF`, `FLDVEL`, `CFF`, and
  `COORD`: <https://docs.software.vt.edu/abaqusv2025/English/SIMACAEOUTRefMap/simaout-c-std-nodalvariables.htm>
- Abaqus/Standard element integration-point variables, including `POR` and
  `FLVEL`: <https://docs.software.vt.edu/abaqusv2025/English/SIMACAEOUTRefMap/simaout-c-std-elementintegrationpointvariables.htm>
- Abaqus self-consistent unit convention:
  <https://docs.software.vt.edu/abaqusv2025/English/SIMACAEMODRefMap/simamod-c-conventions.htm>
