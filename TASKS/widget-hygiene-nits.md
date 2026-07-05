# Research: Widget hygiene nits (low-stakes JS/CSS cleanups)

_Submitted: bug hunt (2026-07-05) · Status: open_

## Summary
A batch of small, verified oddities in WGModResearch.js/.css — none user-breaking, each
either a one-frame cosmetic wobble, dead code, or a fragility against Gameface/Coherent
quirks. Bundle into one cleanup pass (all JS/CSS, so the whole batch hot-reloads).
Confidence: per-item below; severity low across the board.

## Findings
- **Phantom lane reservation for the done marker.** `computeLanes` reserves a de-crowding
  footprint at `pct(0) = 0%` for the done tick (its predicate matches the marker's icon),
  but the tick loop force-renders the done marker in lane 0 overhanging the left edge —
  so the reservation can bump a REAL near-left tick into lane 1 for no visual reason
  (`WGModResearch.js:1413-1414` vs `1023,1464`). Cosmetic mis-stack; exclude the done
  marker from lane computation. Confidence: medium.
- **Stale active-chip ref in elite renders.** `renderElite` resets `hotEl._wgChips = []`
  and nulls the sig but never `setActiveChip(hotEl, null)` — `_wgActiveChip` points at an
  orphaned chip node until the next mousemove (`js:1516-1523`). Mitigated by `.wg-next`
  being hidden in elite; clear it anyway. Confidence: high (mechanism), trivial.
- **No-arg commands break the file's own invariant.** `openSkillTree`/`openResearch`/
  `openFieldMods` are invoked as `host[name]()` with zero args (`js:704-718`) while the
  code elsewhere documents that Wulf commands need a MAP arg (the historical gotcha).
  Works today; pass `{}` for symmetry/future-proofing. Confidence: high.
- **CSS:**
  - `.wg-tip-icon-elite { align-self: flex-start }` is dead — parent `.wg-tip-main` is
    `display:block` and the icon is `position:absolute`; leftover from the old flex-row
    tooltip (`WGModResearch.css:940-945`). Delete. Confidence: high.
  - `.wg-tab-art` uses the `background: … no-repeat center / contain` shorthand with the
    `/ size` syntax while the rest of the file deliberately uses longhand
    `background-size` for Coherent reliability (`css:424`). It ships and renders, so
    mostly refuted as a bug — normalize to longhand for consistency. Confidence: high
    (inconsistency), low (risk).
  - `.wg-tip-rem-veh + .wg-tip-battles` relies on the adjacent-sibling combinator
    (`css:1129`); Coherent's `:not()` is known-unreliable and `+` is unverified — if it
    ever fails, the affordable-via-free-XP tooltip row regains a double gap silently.
    Verify `+` live once (REPL/hot-reload) and either keep with a comment or replace
    with a class set JS-side. Confidence: low (speculative).
- **Design question to settle (not a defect until decided):** in the capstone-only state
  the suppressed chip's one-click unlock (`UNLOCK_FIELD_MOD`) is unavailable — the lone
  final node is reachable only via the bar tick's `OPEN_SKILL_TREE` (screen)
  (`js:1442-1443` vs `868-872`). Likely deliberate (the aabcb80 capstone-tooltip work
  gated this state); confirm with the owner and either document it in wgmod-widget or
  restore the direct-unlock affordance on the final tick when it IS the frontier.

## Root cause
Accumulated feature layers (lanes, chips, elite tab, tooltip redesigns) left small
inconsistencies behind; none rose to bug level individually.

## Suggested approach
One JS/CSS-only cleanup commit: lane-exclude the done marker, clear active chip in
renderElite, `{}`-arg the no-arg commands, delete the dead CSS rule, longhand the
background shorthand, live-verify `+` (then comment or replace). Settle the capstone
question with the owner first — it's the only behavioral item.

## Touch points
- `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js:704-718, 1023,
  1413-1414, 1442-1443, 1464, 1516-1523`
- `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.css:424, 940-945, 1129`

## Verification
Hot-reload loop: a tech-tree bar with a done marker + a tick near 0% shows both in lane 0
(no phantom bump); elite modes unaffected; done-marker clicks still open screens (the
`{}` arg change must not break the no-arg handlers — check the Python side ignores the
arg); tooltip battles row keeps single-gap spacing.

## Open questions
- Capstone-only direct-unlock: restore or document? (Owner call.)
