# V15.20 Right-Bank Curtain Final Closure

Right-bank curtain: UNRESOLVED

FINAL_STATUS = UNRESOLVED

## A. Geometry definition

| Property | Final closure record | Status |
|---|---|---|
| Spatial position | A final global Assembly-coordinate alignment is not present in the current V15.18-V15.20 evidence package. | UNRESOLVED |
| Start range | The upstream/downstream or bank-to-foundation start point is not supplied as a verified coordinate or design reference. | UNRESOLVED |
| End range | The termination point and tie-in to the right-bank boundary/foundation are not supplied as a verified coordinate or design reference. | UNRESOLVED |
| Thickness | No source-backed curtain or equivalent-zone thickness is supplied. | UNRESOLVED |
| Continuity | Continuity through the right-bank geology and connection to the verified anti-seepage system cannot be proven from the current tables. | UNRESOLVED |

The existing V15.19 result `CHECK / UNRESOLVED / CHECK / UNRESOLVED` is retained;
no geometry is promoted to PASS by inference from the S00 solver completion.

## B. Hydraulic treatment decision

The V15.20 release treatment is:

```text
SENSITIVITY_ANALYSIS_VARIABLE
```

This means the right-bank curtain is not inserted or altered in the current
baseline input deck. A future sensitivity case may use a source-backed
equivalent low-permeability region, or another documented hydraulic treatment,
only after its global coordinates, extent, thickness, material role, and
permeability bounds are approved.

The candidate equivalent treatment is therefore a sensitivity option, not a
hidden boundary condition and not an artificial Tie or fixed constraint.

## C. Parameter record

| Parameter | Current value | Material role | Source | Status |
|---|---|---|---|---|
| Permeability | `NOT_DEFINED_FOR_RELEASE` | Right-bank seepage-control curtain/grouting | V15.18 `Curtain_Grouting_Final_Parameter_Table.csv`; V15.19 curtain verification; no independent final coefficient | UNRESOLVED |
| Material role | Low-permeability curtain or approved equivalent hydraulic region | Seepage-control feature, not a structural restraint | Engineering role stated in V15.18/V15.19 audit only | CHECK |
| Sensitivity bounds | `NOT_ASSIGNED` | Lower/central/upper source-backed cases required | No defensible source range supplied | UNRESOLVED |

No permeability number is invented or frozen. An undocumented Lu-to-k
conversion or a generic concrete/grout value is prohibited.

## Closure requirements

Before the right-bank curtain can become `PASS`, provide:

1. final global Assembly coordinates;
2. verified start/end, thickness, and continuity;
3. material/grouting specification and hydraulic role;
4. source-backed permeability value or bounded range;
5. an approved sensitivity plan and acceptance criterion.

Until these are available, S01-S07 remain blocked.
