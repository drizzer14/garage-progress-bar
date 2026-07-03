# Research: Bar disappears completely on a mode transition

_Submitted: "When vehicle transitions from one mode to another, bar disappears completely" · Status: open_

## Summary
When the selected vehicle moves from one bar mode to another (e.g. fully
researched → field mods, tier X → tier XI skill_tree, field mods done → elite), the
whole bar vanishes instead of re-rendering in the new mode. There are four distinct
code paths that can blank `#wgmod-root`; the exact repro (which transition, and
whether it's driven by progressing the same vehicle or by selecting a different
one) determines which is at fault — see Open questions.

## Findings
Only **two** JS lines ever hide the whole widget
(`src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js`):

1. **`render()` ~line 944** — `if (data.visible === false) { root.style.display =
   "none"; return; }`. This is the sink for every Python `visible=false`.
2. **`render()` ~line 1060** — `if (mode === "complete" || sMax <= sMin) {
   root.style.display = "none"; return; }`. Fires **regardless of `visible`**, but
   only on the modes that reach it: **tech_tree, field_mods, skill_tree**. Elite
   modes return earlier (~line 956 → `renderElite()`, which contains **no**
   full-widget hide), so elite/elite_rewards can only be blanked via path 1.

Python decides visibility in `builder.bar_visible()`
(`domain/builder.py:32-53`), written to the VM `visible` field in the push
(`bridge/gameface_bridge.py`, ~`:773`):
```
if hide_always:                              return False   # master switch
if mode == HIDDEN:                           return False   # resolved mode toggled off
if not in_garage:                            return False   # fail-closed allowlist
if hide_when_complete and mode == COMPLETE:  return False
return overlay_closed
```

Mode is chosen by `build_model()` (`domain/builder.py:56-150`), first-match-wins,
no fall-through once resolved: TECH_TREE (`:88-95`, empty remaining ticks = "nothing
left"), SKILL_TREE (`:104-115`, `skilltree.resolve()` returns None once
done≥total), FIELD_MODS (`:119-127`), ELITE_REWARDS (`:134-138`), ELITE
(`:139-143`), COMPLETE (`:146-150`, `ticks=[]`, scale 0/0), HIDDEN (`:70-78`
`_hidden()`, returned when the resolved mode's per-mode "Show X" toggle is off).

Re-render fires via `push()` (`gameface_bridge.py:751-849`), triggered by
`_on_vehicle_changed → refresh()` (vehicle switch) or `_on_sync_completed →
_schedule_refresh()` (same-vehicle progression after a purchase). JS update entry
is `observer.onUpdate(render)`; `render(model)` runs on every push.

## Root cause — four ranked mechanisms
1. **Degenerate scale `scale_max <= scale_min` → hide at JS ~1060 (most bug-shaped).**
   For field_mods, tick positions accumulate `running += step.xp_cost`
   (`domain/resolvers/fieldmods.py:35`); if the only remaining step(s) have
   `xp_cost == 0` (feature / role-slot / zero-priced steps), `running` stays 0 →
   `scale_max == scale_min == 0` → bar hidden **even though `visible=true` and there
   is genuinely something to show**. Same in theory for a zero-cost tech unlock
   (`builder.py:93`). Not covered by any test. This best fits "transition to another
   mode → blank" with visibility still true.
2. **Transition into a user-disabled mode → HIDDEN, not self-recovered.**
   `_hidden()` + `bar_visible` false + JS ~944. By design, BUT once a *same-vehicle*
   sync transitions into a disabled mode, `visible=false` persists until you
   re-select a vehicle. Fits perfectly if the user turned a "Show X" toggle off for
   the destination mode.
3. **Transition into COMPLETE → unconditional hide at JS ~1060** (`mode ===
   "complete"`). By design ("an empty bar adds no information"), but a no-prestige
   tank finishing its last field mod goes FIELD_MODS → COMPLETE → blank, which a
   user may report as a bug.
4. **Rolled-back push transaction** (`gameface_bridge.py` ~`:772`): the engine reads
   inside the transaction — `is_color_blind()` and per-tick purchase-price reads —
   and if either raises on the newly-resolved mode's data, the whole transaction
   rolls back and the VM is left blank. Reads are supposed to be guarded, so lower
   likelihood, but it would produce a total blank.

## Suggested approach
Pin the mechanism with the discriminator below first, then:
- **If (1):** in the JS ~1060 guard, stop treating `sMax <= sMin` as "hide" when
  there are ticks to show — e.g. hide only on `mode === "complete"` (or on empty
  ticks), and let a degenerate scale render at a floor. Alternatively fix it in
  Python: give a zero-cost field-mod/tech step a minimum position so `scale_max`
  is never degenerate while ticks exist. Prefer the Python fix if the scale is
  also used for tick placement.
- **If (2):** decide whether a disabled-mode transition should hide or fall through
  to the next enabled mode; if hide is intended, at least ensure it recovers
  correctly (it does re-push on vehicle re-select — may be acceptable as-is).
- **If (3):** this is intended; confirm with the user whether COMPLETE should still
  show a "fully done" bar rather than vanish.
- **If (4):** harden the offending read inside the transaction so it can't roll the
  whole push back.

## Touch points
- `WGModResearch.js` ~944 and ~1060 (the two hide sinks).
- `domain/builder.py:32-53` (`bar_visible`), `:56-150` (`build_model`), `:93`,
  `:124` (`_max_pos`).
- `domain/resolvers/fieldmods.py:35` (zero-cost position accumulation).
- `bridge/gameface_bridge.py` ~`:751-849` (`push`, the transaction) and `:773`
  (`visible`).
- `adapter/mod_settings.py:518-534` (`enabled_modes`).

## Verification
- **Fastest single discriminator:** at the moment of disappearance, compare the
  push log line (`LOG_NOTE("[wgmod] push mode=... ticks=...")`, ~`gameface_bridge.py:763`)
  against the resulting VM `visible` / `scaleMax`. `visible=false` → path 2 or a
  hide flag; `visible=true` but `scaleMax<=scaleMin` → path 1; `mode=complete` →
  path 3; log present but VM blank → path 4.
- REPL: for the offending vehicle post-transition, read `scaleMin`/`scaleMax`/`ticks`
  and `mod_settings.enabled_modes()`.
- Tests: `tests/test_builder.py` (transition truth table) and
  `tests/test_visibility.py` exist but neither exercises the JS `sMax<=sMin` hide
  nor a zero-cost step producing a degenerate scale — add a builder test for the
  zero-cost field-mod case if (1) is confirmed.

## Open questions (need user repro to narrow)
- **Which transition?** e.g. fully-researched→field-mods, tierX→tierXI, field-mods-
  done→elite, or last-item→complete?
- **Driven how?** By progressing/researching the *same* vehicle (sync-triggered), or
  by *selecting a different* vehicle that's in another mode (vehicle-change)?
- **Does it come back?** After switching to another vehicle and back, or only after
  a screen change? (Persistent-until-reselect points to path 2.)
- **Any "Show X" mode toggles turned off** in the mod settings (Modification list)?
  (Points to path 2.)
- Which vehicle(s)? (Lets the implementer read the exact ticks/scale in REPL.)
