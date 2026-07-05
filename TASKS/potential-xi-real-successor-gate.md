# Research: Potential Tier XI ghost bar on lines that HAVE a real Tier XI

_Submitted: bug hunt (2026-07-05) · Status: open_

## Summary
The opt-in POTENTIAL_TIER_XI mode is meant for tier-X tanks with **no** real Tier XI, but
its gate never checks for one. A tier-X whose real tech-tree Tier-XI successor is already
researched sails through (tech tree empty, field mods done, not itself a skill-tree
vehicle) and gets the speculative "grind 325k toward a hypothetical Tier XI" bar — on a
line where the real Tier XI exists and is owned-or-unlockable. Confidence: medium (the
mechanism is verified in code; how many live lines have a tech-tree Tier XI decides how
often it fires — the model explicitly supports them, `types.py:6` "Tier XI included as an
ordinary unlock" + `test_tech_tree_includes_tier_xi_vehicle_unlock`).

## Findings
- Entry gate is only tier + not-skill-tree: `domain/builder.py:155-156`
  (`enabled ... and snapshot.tier == 10 and not snapshot.is_skill_tree`).
- The evidence it needs is already in the snapshot: `adapter/tech_read.py:106` keeps
  RESEARCHED entries in `tech_unlocks` (`researched=(int_cd in unlocks)`), with
  `kind=Category.VEHICLE` for a vehicle successor (`tech_read.py:105`). The done-marker
  reconcile relies on exactly this retention (`recent.py:164-166`).
- While the successor is UNresearched the bar correctly shows TECH_TREE (techtree.resolve
  returns remaining-only ticks, `builder.py:110-115`), so the ghost appears only after
  researching the real XI.
- Related polish to fold into the same fix:
  - Dead guard: `builder.py:158` `if pxi is not None` — `potential.resolve` never returns
    None by contract (`domain/resolvers/potential.py:15-16,27`). High confidence, trivial.
  - Hover UX: the tooltip proximity gate covers only SKILL_TREE
    (`WGModResearch.js:1672` `_wgMode !== MODE.SKILL_TREE || near.dist <= 6`); the
    potential bar has ONE tick pinned at 100% but uses nearest-anywhere, so hovering the
    far-left empty bar pops the Tier-XI tooltip. Extend the gate to POTENTIAL_TIER_XI
    (same single-milestone shape as the skill-tree final tick). Verified. Low severity.
  - Design question: `bar_visible` (`builder.py:64`) treats only COMPLETE as "fully
    progressed" for hide_when_complete; a potential-XI tank IS fully progressed in
    reality. Arguably the opt-in overrides the hide — settle and document either way.

## Root cause
The gate was written as "tier X and not a skill-tree vehicle" — a proxy for "has no real
Tier XI" that misses the third case: a real Tier XI reachable as an ordinary tech-tree
vehicle unlock, which stays in `tech_unlocks` (researched=True) after being researched.

## Suggested approach
Domain-only, engine-free: in the `builder.py:155` gate, also require
`not any(u.kind == Category.VEHICLE for u in snapshot.tech_unlocks)`. Rationale: a
tier-X's only possible vehicle successor is a Tier XI; if one exists unresearched,
TECH_TREE already wins higher in the chain, so any vehicle entry here means "real XI
exists" regardless of researched state. No adapter change needed. While in there, drop the
dead `pxi is not None` guard and add the JS proximity-gate extension.

## Touch points
- `src/res/scripts/client/wgmod_research/domain/builder.py:155-158`
- `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js:1672`
- `tests/test_resolver_potential.py` / `tests/test_builder.py` — add: tier-X with a
  researched VEHICLE unlock in tech_unlocks + potential enabled → NOT potential mode
  (falls through to elite/complete). Also close the sweep's coverage gaps:
  `bar_visible` cases for Mode.HIDDEN and Mode.POTENTIAL_TIER_XI (none exist in
  `tests/test_visibility.py`), and assert the POTENTIAL model carries the estimate
  inputs + vehicle_class (only TECH_TREE/FIELD_MODS pinned today).

## Verification
Unit: the new builder tests. In-game: enable the setting, select a tier-X that has a real
researched Tier XI → no potential bar (elite/prestige bar instead); select a tier-X with
no Tier XI line → potential bar unchanged; hover the empty left half of the potential bar
→ no tooltip until near the milestone tick.

## Open questions
- Does any live EU 2.3 tier-X currently expose a tech-tree Tier-XI successor? (REPL-check
  during the fix; the domain fix is correct regardless.)
- hide_when_complete × POTENTIAL: hide or show? (Owner call; recommend show — the user
  explicitly opted into the speculative bar.)
