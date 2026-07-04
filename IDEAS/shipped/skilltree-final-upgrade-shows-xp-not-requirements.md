# Research: BUG — Final tier-XI upgrade shows xp/battles left instead of unlock requirements

_Submitted: "Final tier xi upgrade now shows xp/battles left instead of unlock requirements" · Status: open_

## Summary
When the final tier-XI skill-tree upgrade (the capstone tick) is **unaffordable and
not yet the purchasable frontier** (its real prerequisites aren't met yet), its
tooltip renders the cost + "-N XP" + "≈ M–N battles" shortfall block instead of its
unlock-requirements text ("Required: …" / "Prerequisites not met"). The recently
shipped estimated-battles feature is the *trigger of the report*, not the cause — it
appended the eye-catching battles line to a shortfall block that was already
wrongly displacing the requirements text.

## Findings
Front-end: `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js`.

**The shortfall line (`xpFracHtml`, ~:380-434).** The whole "xp left / ≈ battles"
sub-line is gated on unaffordability (`have < need`): affordable → bare cost
headline only; unaffordable → cost + `-N XP` (`wg-tip-rem-tot`) + the new
`≈ M–N battles` span (`wg-tip-battles`). Commits `ebf0392` / `370e3f0` only
*inserted* the battles span inside the pre-existing `have < need` block and threaded
an `est` arg through callers — they did **not** change any branch selection.

**The tooltip footer branch order (`tooltipHtml`, ~:582-633) — the crux:**
```js
if (t.done) { foot = creditsHtml(t.price); }
else if (t.category === CAT.UPGRADE && t.icon && t.xpRequired) {   // :612 CAPSTONE branch
    foot = xpFracHtml(spendableXp, t.xpRequired, XP_ICON, undefined, est);
} else if (t.locked) {                                             // :619 "UNLOCK REQUIREMENTS"
    const reqs = splitLines(t.prereqNames);
    foot = reqs.length
        ? '…' + L("requires","Required:") + " " + reqs.join(", ") + '…'
        : '…' + L("prereqNotMet","Prerequisites not met") + '…';
} else { foot = xpFracHtml(spendableXp, t.position, XP_ICON, fillVehicle, est); }
```
"Unlock requirements" = the `t.locked` branch (:619-626). The capstone branch
(:612) sits **before** it, so a final tick never reaches the requirements branch.

## Root cause
The resolver (`domain/resolvers/skilltree.py:40-52`) gives **only the final tick**
an `icon`, `name`, and `xp_required` in *every* skill-tree state, and marks ticks
right of the fill `locked`. So the final tick **always** satisfies the :612 gate
`t.category === CAT.UPGRADE && t.icon && t.xpRequired` — not just when it's the
purchasable frontier. That branch was added deliberately by the shipped
`skilltree-capstone-tooltip` fix to replace "Prerequisites not met" with the cost
*when the capstone is the only node left*, but its gate is too broad.

The glyph logic gets this right via an `onlyFinal` frontier flag:
- `onlyFinal` def (~:1327): `mode===SKILL_TREE && stTotal>0 && stDone===stTotal-1 && availUpgrades>=1`
- glyph brighten (~:1401): `if (onlyFinal && mode===SKILL_TREE && t.icon) stateClass=" wg-aff"`

…but the tooltip call (~:1439) `tooltipHtml(t, spendableXp, fv, battleEst)` **does
not pass `onlyFinal`**, so `tooltipHtml` can't tell the purchasable frontier from a
still-gated final tick. Result: whenever the final upgrade is unaffordable but
`done < total-1` (prereqs genuinely unmet), it routes through :612 → `xpFracHtml`
(cost + `-N XP` + `≈ battles`) and skips the :619 requirements branch. Exactly the
reported symptom.

Why "now": before the battles feature an unaffordable capstone already showed
cost + `-N XP` (same wrong branch); the battles span just made the missing
requirements text obvious enough to report.

## Suggested approach
Narrow the :612 capstone branch to the purchasable-frontier state so a still-gated
final tick falls through to the `t.locked` requirements branch:
1. Thread `onlyFinal` (or the frontier condition) into the `tooltipHtml` call at
   ~:1439 — it's already computed for the glyph pass in the same render scope.
2. Change the :612 gate to `onlyFinal && t.category === CAT.UPGRADE && t.icon && t.xpRequired`
   (or equivalent). When the final tick is not the frontier, it hits `t.locked` and
   shows "Required: …" / "Prerequisites not met" as intended.
3. Keep the capstone-cost behaviour intact for the genuine frontier case (the
   scenario the `skilltree-capstone-tooltip` fix was built for).

Front-end-only, no Python change — the resolver already flags the tick correctly;
this is purely a tooltip branch-selection bug.

## Touch points
- `WGModResearch.js` `tooltipHtml` (~:582-633, gate at :612) — narrow the capstone branch.
- `WGModResearch.js` render loop tooltip call (~:1439) + `onlyFinal` def (~:1327) —
  pass the frontier flag through.
- (Reference only, no edit) `domain/resolvers/skilltree.py:40-52` — why the final
  tick always carries icon/xp_required.

## Verification
- JS-only → hot-reload (`sync_gameface`; overlay must exist at client launch).
- Pick a tier-XI vehicle with the skill-tree bar where the final upgrade is **not**
  the next purchasable node (several nodes still locked before it) and hover the
  final tick: it should show its unlock requirements ("Required: …" or
  "Prerequisites not met"), NOT cost + battles.
- Then advance to the state where the capstone IS the only node left (frontier) and
  confirm it still shows the cost (+ shortfall/battles when short) — i.e. the
  `skilltree-capstone-tooltip` fix is preserved.
- Regression-check a normal (non-final) locked tick still shows requirements.

## Open questions
- Should the frontier capstone, when unaffordable, keep showing the battles line, or
  is the battles line only wanted on tech-tree/field-mod ticks? (The report is about
  the *non-frontier* case; the frontier case is arguably correct — confirm with the
  user whether battles-on-capstone is desired at all.)
- Does the same over-broad gate affect the "Next available" chip path
  (`renderNextAvailable` ~:839, which has no requirements branch)? Chips are only
  the frontier by construction, so likely fine — but worth a glance.
