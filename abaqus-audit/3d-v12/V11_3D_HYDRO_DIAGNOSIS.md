# v11 3-D hydro-mechanical diagnosis

- Source v11 SHA-256: `52C39E6A713F423D4BC4F29742B323D6FDA3CBB80CE2C47A82C2F5124A742A27` (read-only; not overwritten).
- Source parts/instances: 78/78.
- v11 porous mesh used ordinary `C3D8R/C3D6` and ordinary `*Static`; no pore-pressure DOF.
- v11 had no effective interface tie/contact network; 40 exact boundary-pair groups were found by audit.
- v11 geological/foundation materials lacked the 14 report-based permeability entries.
- v11 used constant face pressures 220/250/285/80 kPa rather than elevation-dependent heads.
- v11 main cutoff wall was 2.0 m thick with base about 3017.98 m; BX02/BX03 exceeded the report elevation ranges.
- v11 defined `GEOMEMBRANE` but did not assign it to an actual region.

## Corrective choices

- Exact coincident boundary faces receive surface-based Tie constraints; nonconformal left/river/right geology and dam/foundation boundaries receive aggregate Ties with documented tolerances.
- Exact coupled-interface pore pressure is carried by the surface Tie constraint; an additional DOF 8 `*Equation` is intentionally not emitted because Abaqus eliminates tied secondary DOF 8. Aggregate nonconformal hydraulic continuity remains a solver verification item.
- The v12 geomembrane is an actual 1.0 m equivalent C3D8P layer from z=3055.0 to the cutoff top z=3073.51147 m; `t/k` is explicit in the result report.
- Plasticity is not enabled in the baseline because a complete source-supported dilation set is unavailable; no dilation was invented.
- BX01/BX02/BX03 are retained and linearly repositioned to report ranges (2990-3305, 3005-3201, 3040-3170 m).
