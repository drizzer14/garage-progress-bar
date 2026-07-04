# Research: Skill-tree chip tooltip shows a bogus vehicle-XP shortfall (node count used as XP)
_Submitted: full-codebase bug sweep (2026-07-04) · Status: open_

## Summary
Hovering an **unaffordable** "Next available" chip in skill_tree mode shows a
shortfall sub-line computed from the unlocked-node COUNT instead of vehicle XP —
e.g. cost 10 000 with 5 nodes unlocked renders "-9 995" regardless of actual XP.
Confirmed end-to-end by an adversarial verifier. A second, related divergence:
chips fire the purchase command with **no affordability gate**, unlike bar ticks.

## Findings
- In skill_tree mode `fillVehicle` is a node count by design:
  `domain/resolvers/skilltree.py:57` (`"fill": done`) →
  `domain/builder.py:113` (`fill_vehicle=st["fill"]`) →
  `bridge/gameface_bridge.py:469` (`setFillVehicle`).
- `WGModResearch.js:1168` reads it as `fv`, and `js:1235` passes it into
  `renderNextAvailable(..., spendableXp, fv)`; `js:761` forwards it to
  `xpFracHtml(spendableXp, xp, XP_ICON, fillVehicle)`.
- `xpFracHtml` (`js:337-363`) renders the per-currency sub-line whenever
  `vehLeft = need - (vehHave|0)` exceeds the total shortfall — true whenever
  `spendableXp > fv`, i.e. virtually always. So the bogus line shows on every
  unaffordable chip. The render() author knew `fv` is a count here — the comment at
  `js:1182-1183` refuses `setXp()` for exactly this reason — but line 1235 passes
  the same value into the chip tooltips.
- Chips are NOT affordability-filtered: `adapter/skill_tree_read.py:141-158`
  includes every prereqs-met frontier node regardless of XP, so unaffordable chips
  are routinely visible.
- Affordability-gate divergence (same area): `js:767-769` gives every non-done chip
  `cmd: CMD.UNLOCK_FIELD_MOD` unconditionally, while bar field-mod ticks require
  `t.affordable` (`js:1324`) and tech ticks `affordable && !locked` (`js:1326-1328`).
  Clicking an unaffordable chip fires `PURCHASE_POST_PROGRESSION_STEPS` anyway (and
  `_record_click` stashes a pending — see [[done-marker-reconcile-false-promotion]]).
- REFUTED during verification (do NOT chase): `upgradesSig` omitting `fv` cannot
  cause stale chips — no game event changes `fv` without also changing the
  signature (`n`/actionIds/spendableXp co-move). If the fix threads real vehicle XP
  into the tooltips, THEN add it to the sig.

## Root cause
`WGModResearch.js:1235` reuses the mode-ambiguous `fv` (fillVehicle) for chip
tooltips; in skill_tree mode that field carries the count axis, not XP. The model
currently exposes no true vehicle-XP field in skill_tree mode (`spendableXp` is
vehicle+free combined).

## Suggested approach
Simplest: pass `undefined` instead of `fv` in skill_tree mode — `xpFracHtml`
already skips the sub-line when `vehHave === undefined` (`js:352` guard), leaving
just the correct combined shortfall. Richer: add a real `vehicleXp` model field and
use it (then also fold it into `upgradesSig`). For the gate: give non-done chips
`cmd` only when `spendableXp >= u.xpRequired`, matching bar-tick behavior (and let
the tooltip's red cost speak for the rest).

## Touch points
- `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js:761, 767-769, 1235`
  (+ `794-804` if a new field joins the signature)
- Optional richer fix: `bridge/view_models.py` + `bridge/gameface_bridge.py` +
  `domain/builder.py` (new `vehicleXp` field)

## Verification
In-game/hot-reload: tier-XI vehicle, ensure an unaffordable frontier chip exists,
hover → the sub-line either disappears (simple fix) or shows the true vehicle-XP
shortfall; click an unaffordable chip → no command fired. JS/CSS only → hot-reload
via sync_gameface (overlay must exist at launch).

## Open questions
- Product call: should unaffordable chips be visually dimmed too (like `wg-locked`
  ticks), or is the red cost in the tooltip enough?
