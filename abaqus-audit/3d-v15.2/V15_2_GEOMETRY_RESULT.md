# V15.2 geometry completion result

This is geometry-only work from baseline commit 48112235b6f1794a069130ea43fccef14ca8552a. No S01-S07, solver job, Data Check, contact tuning, material edit, node restraint, Encastre, spring, artificial support, or Tie was run or added.

## Created

- Stepped left-bank sub-dam with crest/face tiers, foundation footprint, and reserved fishway opening. Exact crest and terrain tie-in: UNRESOLVED.
- Continuous simplified fishway with 2.0 m nominal passage, 0.5 m wall/bottom thickness, downstream turn-back, sub-dam crossing and upstream outlet. Plan routing PASS; elevation continuity: UNRESOLVED.
- Seven dedicated local excavation envelopes for powerhouse, installation bay, spillway, ecological release, stilling basin, tailwater and sub-dam.
- Refined powerhouse units with actual intake, internal passage and draft-tube outlet void corridors.
- Refined spillway with two abutments, nine piers, eight open bays, chute slab and common stilling basin.
- Refined ecological release with two low-level opening corridors, central pier, lintel, slabs and basin link.
- Tailwater riverbed body below the retained 0.8 m lining.

## Retained/modified

- Retained v15 audited major envelopes and elevations; locally refined their structural blocks and openings.
- Retained v14 left-bank geology instances. Boolean cutting into retained geology is not performed in this keyword-only geometry output and is UNRESOLVED.
- v12/v13/v14/v15 outputs were not overwritten.

## Status

- Major dimension/elevation checks: PASS except source-dependent sub-dam opening target marked UNRESOLVED.
- Opening checks: PASS for powerhouse, 8 spillway bays, 2 ecological bays, sub-dam crossing and fishway passage.
- New-geometry interference: PASS, with fishway/sub-dam crossing treated as an intentional reserved void.
- Excavation local-envelope checks: PASS; Boolean cut into retained geology: UNRESOLVED.
- Full engineering hub completeness: UNRESOLVED for exact terrain tie-in, natural riverbed transition and fishway elevation data.

## Visual checks

Five projection images are included: upstream, downstream, plan, dam-axis and left-bank oblique. They are geometry-check projections, not solver results.
