# Research: Tier-XI "Next available" chips die after visiting an elite / exclusive-rewards vehicle

_Submitted: "after switching vehicles, tier XI next upgrades are not hoverable/clickable anymore" → clarified: "only after switching to and from an elite vehicle or tier XI with exclusive rewards" · Status: shipped_

## Shipped resolution
Fixed as diagnosed: `renderElite()` now nulls the `.wg-next` chip signature
(`nextSig._wgSig = null`) alongside clearing `hotEl._wgChips`, so returning to a
skill-tree vehicle recomputes a differing signature and rebuilds the chips instead of
taking the stale re-show branch. In-game verified (chip hover/click survive the
elite round-trip). (`WGModResearch.js`, `renderElite`.)

## Summary
The tier-XI "Next available:" upgrade chips stop responding to hover and click
after the user switches TO an elite (or tier-XI-with-exclusive-rewards) vehicle
and back to the same skill-tree vehicle. **Root cause confirmed. One-line fix.**

## Root cause
An asymmetric state reset between the two render paths (`WGModResearch.js`):

- The chips are only rebuilt when their signature changes. `render()` (~781–795):
  ```js
  if (mode === "skill_tree" && nextEl && !onlyFinal) {
      const sig = upgradesSig(data.availUpgrades, spendableXp);   // ~782
      if (nextEl._wgSig !== sig) {                                // ~783
          nextEl._wgSig = sig;
          setActiveChip(hotEl, null);
          renderNextAvailable(nextEl, data.availUpgrades, hotEl, spendableXp); // repopulates hotEl._wgChips (~474)
      } else {
          nextEl.style.display = "flex";   // ~788: re-show WITHOUT rebuilding
      }
  } else {
      nextEl._wgSig = null;   // ~791: non-skill_tree clears BOTH
      hotEl._wgChips = [];     // ~792
      ...
  }
  ```
- Elite modes branch out early (~718–723) into `renderElite()`, which sets
  `hotEl._wgChips = []` (~992) **but never resets `nextEl._wgSig`.**

Sequence that breaks it: skill-tree vehicle X builds chips → `nextEl._wgSig` = sigX.
Switch to elite Y → `renderElite` empties `hotEl._wgChips`, leaves `_wgSig` = sigX.
Return to X → recomputed sig equals the stale sigX, so `render()` takes the
"re-show without rebuild" branch (~788). The chip DOM is shown, but `hotEl._wgChips`
is still empty. Hover/click hit-testing (`chipAt()` ~492, called from the mousemove
handler ~1147 and click handler ~1239) short-circuits on empty `_wgChips` → dead
chips.

## Suggested approach
Null the signature wherever the chips array is emptied. In `renderElite()` (~992),
grab the `.wg-next` element and clear its signature alongside the array:
```js
const nextEl = root.querySelector(".wg-next");
hotEl._wgChips = [];
if (nextEl) nextEl._wgSig = null;   // <-- add: force a rebuild on return
```
This makes `nextEl._wgSig !== sig` true on return, so `renderNextAvailable()` runs
and repopulates `hotEl._wgChips`. The non-skill_tree else-branch (~791) already
does this correctly; this just restores symmetry for the elite early-return path.
(Confirm the exact `.wg-next` selector against `renderNextAvailable`'s `nextEl`.)

## Edge cases (all verified safe with the fix)
- elite→elite: no skill_tree path runs; both fields stay cleared.
- skill_tree→skill_tree (different vehicle): sig differs → rebuild anyway.
- skill_tree→skill_tree (same sig, no elite between): intentional re-show path
  preserved (keeps a hovered tooltip stable across background model pushes).
- fully-upgraded (`onlyFinal`): falls to the else-branch (~790) which clears both.

## Touch points
- `WGModResearch.js` — `renderElite()` (~992). Single addition.

## Verification
- In-game repro: select a tier-XI vehicle with available nodes (chips hover/click
  work) → switch to any elite / exclusive-rewards vehicle (chips row hides) →
  switch back → BEFORE fix chips are dead; AFTER fix hover shows the tooltip and
  click fires the unlock.
- Optional unit coverage: assert `upgradesSig()` is deterministic and that a
  cleared `_wgSig` forces a rebuild. Existing JS behaviour isn't unit-tested, so a
  manual check is the primary gate.
- Coherent devtools: inspect `hotEl._wgChips.length` and `nextEl._wgSig` before/
  after the switch.
