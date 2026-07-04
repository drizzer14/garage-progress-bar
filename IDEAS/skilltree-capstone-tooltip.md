# Research: Tier-XI capstone tick shows "Prerequisites not met" while purchasable
_Submitted: full-codebase bug sweep (2026-07-04) · Status: open_

## Summary
On a tier-XI vehicle with every skill-tree node unlocked except the final capstone,
the bar's final tick is deliberately force-brightened as "the available node" and is
clickable — but hovering it shows **"Prerequisites not met"** and never shows the
node's XP cost. Found independently by two sweep agents; confirmed by direct read.

## Findings
- The resolver marks EVERY remaining skill-tree tick locked:
  `domain/resolvers/skilltree.py:50-51` — `affordable=(i <= done)`, `locked=(i > done)`.
  Since `resolve()` returns None once `done >= total`, the final tick is locked in
  every state the mode renders — including the capstone-only state where it is in
  fact the purchasable frontier node.
- The JS knows this state is special: `WGModResearch.js:1301-1302` forces the final
  tick's class to `wg-aff` (bright) when `onlyFinal`, and it gets `cmd:
  CMD.OPEN_SKILL_TREE` (clickable). But `tooltipHtml` was never taught the same:
  `WGModResearch.js:541-548` — `t.locked` takes the prereq branch, and skill-tree
  ticks carry no `prereqNames`, so the generic "Prerequisites not met" renders.
- Related same-area wart: even if the tick were not locked, the linear footer
  `WGModResearch.js:550` computes the shortfall from `t.position` (a node INDEX on
  the count axis, not XP) and `fv` (the node count — see
  [[skilltree-chip-xp-shortfall]]); the real cost sits unused in `t.xpRequired`
  (set by `skilltree.py:49` explicitly "-> its end-tick tooltip").

## Root cause
`skilltree.py:51` conflates "right of the fill on the count axis" with "locked";
the JS `onlyFinal` special-case (added later) corrected the glyph state but not the
tooltip branch, and the tooltip footer for skill-tree ticks was never wired to
`t.xpRequired`.

## Suggested approach
Two candidate fixes; the domain one is cleaner:
1. **Domain:** in `skilltree.py`, mark the final tick `locked=False` (and
   `affordable=spendable >= final_xp`?) when it is the only remaining node — i.e.
   `done == total - 1`. Careful: `affordable` also drives the bright class in
   non-capstone states; check `test_resolver_skilltree.py` expectations.
2. **JS:** in the linear spec, when `onlyFinal && t.icon`, build the tooltip footer
   from `t.xpRequired` (an `xpFracHtml(spendableXp, t.xpRequired, XP_ICON,
   /*real veh xp or omit*/)`) instead of falling into the locked branch.
Either way the footer must use `t.xpRequired`, NOT `t.position`, as the need.

## Touch points
- `src/res/scripts/client/wgmod_research/domain/resolvers/skilltree.py:44-52`
- `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js:541-550, 1296-1308`
- `tests/test_resolver_skilltree.py` (add the capstone-state case)

## Verification
pytest for the resolver change; in-game (or REPL-driven model inspection): tier-XI
vehicle with only the capstone remaining → hover the final tick → expect name +
cost footer, not "Prerequisites not met". The known test vehicle family for
skill-tree work is tier-XI (Kranvagn-line probes were used before).

## Open questions
- Should the capstone tooltip show affordability shading (red shortfall) like chips
  do, or just the cost? (Chips already show the cost; consistency suggests yes.)
