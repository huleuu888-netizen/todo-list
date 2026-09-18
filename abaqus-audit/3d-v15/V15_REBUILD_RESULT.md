# V15 rebuild result

The v15 deck and incremental mechanical-gate inputs were generated from v14 and checked with Abaqus. The task gate stopped after stage-1 S02 exposed numerical singularities; later stages and hydraulic steps were not claimed.

- Rebuilt Parts: 19 new V15 Parts, one for every active priority Instance.
- Reused Parts: retained v14 core Parts only; legacy appurtenant Parts were audited but not instantiated.
- Active v15 Instances: 19.
- Geometry gate: PASS for explicit scalar source targets; exact detailed hydraulic openings, reinforcement, and surveyed foundation surface remain UNRESOLVED.
- Support gate: UNRESOLVED; only the installation-bay surface Tie passed the measured-contact and conflict checks, while the other 18 new support paths were deferred.
- Abaqus full-deck Data Check: PASS; 35 unconnected-region warnings, no fatal errors.
- Stage-1 S01: PASS (increment completed). Stage-1 S02: UNRESOLVED (numerical singularities, including POWERHOUSE_UNIT_04_I node 44 DOF 3; job externally stopped).
- Stage-2 through stage-5 S01/S02 and hydraulic S03-S07: NOT RUN under the task stop rule; hydraulic boundary and physical validation remain UNRESOLVED.
- Constraint audit: no new node restraints, Encastre, springs, or unsupported blanket Ties.
- Overall: VALIDATED=NO.
