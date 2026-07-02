# Research: Tier-XI upgrades show text descriptions but not exact buff numbers

_Submitted: "Tier XI upgrades don't show exact buffs, just their text descriptions" · Status: open_

## Summary
Tier-XI skill-tree node tooltips render a localized sentence but frequently drop
the numeric magnitude, e.g. "Reduces gun reload time by % in Pillbox mode." with
no number. The gap is specifically the signature "mechanic" perks. Root cause
confirmed; fix is isolated to one adapter function.

## Root cause
`_skilltree_effect()` — `adapter/engine_adapter.py:732–770` — fills the localized
template's `{value}` slot by scanning the node's KPI objects and matching on
`kpi.type`:
```python
for k in _kpi_objs(action):
    v = getattr(k, "value", None)
    if isinstance(v, bool) or not isinstance(v, (int, float)): continue
    v = float(v)
    ktype = getattr(k, "type", "") or ""
    if ktype == "mul": value = _fmt_num(abs((v - 1.0) * 100.0)); break   # ~760
    if ktype == "add": value = _fmt_num(abs(v)); break                   # ~763
# no match -> value stays "" -> template returned with {value} unfilled
```
Only `mul` and `add` are handled. Signature/final "mechanic" perks carry a KPI
whose `name` is the literal string `"value"`, whose `getDescriptionR()` is empty,
and whose `type` is **not** `mul`/`add` — so the loop falls through leaving
`value = ""`, and the sentence renders numberless. The magnitude IS present in
`kpi.value`; the code just doesn't know how to interpret that KPI's type.

## Contrast: field mods (the sibling issue)
Field mods build their lines from `_kpi_lines()` / `_action_effect()`
(`engine_adapter.py:686/717`), which read `getDescriptionR()` for the phrase and
prefix it with the signed magnitude. Skill-tree nodes differ because the phrase
comes from a separate `veh_skill_tree.tooltips.description` template keyed by the
node's image name (not from the KPI), and the mechanic-perk KPI is the generic
unlabeled `value`. So the two "missing numbers" symptoms have different plumbing.

## Affected display points (data flow)
Both flow: `engine_adapter._skilltree_effect()` → snapshot → `skilltree.resolve()`
→ model → VM → JS tooltip.
- **Final end-tick effect**: `final_effect = _skilltree_effect(action)`
  (~354) → `snapshot.skilltree_final_effect` → tick `effect` → JS `t.effect`.
- **"Upgrades Available" chip description**: `description=_skilltree_effect(step.action)`
  (~344) → `avail_upgrades[].description` → JS `u.effect`.

## Suggested approach
Extend the KPI loop in `_skilltree_effect()` with a fallback for the generic
mechanic-perk KPI (keep `mul`/`add` first). Preferred, explicit path:
- If `getattr(k, "name", "") == "value"` and type isn't `mul`/`add`, treat it as a
  multiplier: `value = _fmt_num(abs((v - 1.0) * 100.0))`.
- Fallback heuristic if `name` isn't reliable: if `v` is within ~±0.5 of 1.0 treat
  as multiplier (percent), else additive (raw). Flag this heuristic honestly — it
  needs a live check.

This is a natural extension of commit 35996e7, which already broadened the handler
beyond `mul` to accept `add`. Isolated to one ~40-line function; skill-tree only,
does not touch field mods.

## Live probe before coding (wgmod-debug-repl)
On a tier-XI vehicle with a signature perk (agent suggested Hirschkäfer):
`g_currentVehicle.item.postProgression.iterOrderedSteps()` → a final/major node →
inspect `step.action._descriptor.kpi[0]`: read `.type`, `.name`, `.value`,
`getDescriptionR()`. Confirm what `type`/`name` the numberless perks actually
carry so the fallback keys on the real shape, not a guess.

## Touch points
- `adapter/engine_adapter.py` — `_skilltree_effect()` (~732–770).
- `tests/test_resolver_skilltree.py` — add a mock KPI with `name="value"` /
  empty type and assert the number now fills.

## Verification
- Unit: mock KPI object (name=`value`, type missing, value=1.05) → effect string
  contains "5" not a bare "%".
- In-game: on the probed tier-XI vehicle, the final-tick and chip tooltips show the
  magnitude (e.g. "…by 5%…") instead of "…by %…".
