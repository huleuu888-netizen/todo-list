# V15.19 Curtain Grouting Final Verification Report

FINAL_STATUS = UNRESOLVED

## Scope

This verification is based on the V15.18 parameter-freeze files and the
validated V15.15 S00 evidence. It is a document-only audit. No geometry,
mesh, boundary condition, material value, tie, or fixed constraint was added
or changed, and S01-S07 were not run.

## Evidence reviewed

- `abaqus-audit/3d-v15.18/Curtain_Grouting_Final_Parameter_Table.csv`
- `abaqus-audit/3d-v15.18/V15.18_ENGINEERING_PARAMETER_FREEZE_REPORT.md`
- `abaqus-audit/3d-v15.17/Curtain_Grouting_Parameter_Closure_V15.17.csv`
- `abaqus-audit/3d-v15.15/v15_15_S00_result_summary.csv`
- `abaqus-audit/3d-v15.15/v15_15_solver_readiness_gate.csv`

The evidence is sufficient to confirm retention of the previously validated
anti-seepage objects, but it is not sufficient to independently close every
spatial coordinate, material basis, and permeability value.

## Verification matrix

| Region | Spatial position | Geometric continuity | Material definition | Permeability state | Overall | Verification note |
|---|---|---|---|---|---|---|
| Right bank curtain | CHECK | UNRESOLVED | CHECK | UNRESOLVED | UNRESOLVED | V15.18 explicitly requires geometry and permeability verification; no reliable final coordinate/material package is present. |
| Foundation curtain | CHECK | CHECK | CHECK | CHECK | CHECK | V15.18 records the model definition as verified, but the supplied table does not include a final coordinate survey or independent grouting parameter source. |
| Left-bank 80 m extension | PASS (inherited) | PASS (inherited) | CHECK | CHECK | CHECK | Retained from the V15.15/V15.17 validated anti-seepage system; parameter verification remains separate from geometry retention. |
| Left subdam curtain | PASS (inherited) | PASS (inherited) | CHECK | CHECK | CHECK | Existing connection is preserved; no new material or k basis was supplied in V15.18. |
| Powerhouse / installation curtain | PASS (inherited) | PASS (inherited) | CHECK | CHECK | CHECK | Existing connection is preserved; final engineering parameter evidence is incomplete. |
| Ecological-release connection | PASS (inherited) | PASS (inherited) | CHECK | CHECK | CHECK | Existing transition is preserved; the current files do not independently verify the hydraulic coefficient. |
| Spillway transition | PASS (inherited) | PASS (inherited) | CHECK | CHECK | CHECK | Existing transition is preserved; no unsupported dimension or parameter was introduced. |
| Main cutoff wall | PASS (inherited) | PASS (inherited) | CHECK | CHECK | CHECK | Existing wall is retained; material and grouting/permeability basis still requires review. |
| Geomembrane connection | PASS (inherited) | PASS (inherited) | CHECK | CHECK | CHECK | Existing connection is retained; current coefficient is not recalibrated by V15.19. |

## Check definitions

- `PASS` means the existing audit trail supports the stated item for the
  current model scope.
- `CHECK` means the object or current model definition is present, but an
  independent final engineering basis is still required.
- `UNRESOLVED` means the evidence is insufficient to release the item for
  production seepage interpretation.

## Conclusion

The right-bank curtain remains the direct blocking item. The previously
validated curtain geometry is preserved, but parameter verification is not
equivalent to adding a tie or imposing a fixed condition. The model therefore
remains suitable as the completed S00 baseline with warnings, but it is not
released for S01-S07 production cases.
