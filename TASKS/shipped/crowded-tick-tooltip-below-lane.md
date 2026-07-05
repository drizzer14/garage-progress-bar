# Research: On crowded ticks, show the tooltip below the pushed-down tick (lane-aware, bar-position reversed)

_Submitted: "On crowded ticks, display tooltip below the tick that got pushed down, instead of overlaying the tick. Consider bar position to properly reverse such tooltips" · Status: shipped (commit 95a0ae5 "fix: drop crowded-tick tooltip below the lane-shifted glyph")_

> Note: this note was recreated by the plan saver after the fact — the original
> was captured as an untracked file and lost when the implementing session pruned
> the backlog entry. The authoritative record of the fix is commit 95a0ae5.

## Summary
When ticks are too close together the widget de-crowds them by dropping some
glyphs into a lower "lane" (`lane * 30rem` below the track). The shared tooltip
anchored to the track's base at a fixed `36rem` drop and ignored the lane offset —
so hovering a dropped (lane ≥ 1) glyph rendered the tooltip on top of that glyph.
The ask: anchor the tooltip below the actual (lane-offset) glyph, and make the
above/below flip respect the bar's on-screen position, not just viewport-bottom
overflow.

## Findings
Front-end files:
- JS: `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js`
- CSS: `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.css`

**Lane stacking.** The `--- De-crowding ---` block (JS ~846-937) assigned each
glyph a lane (`LANE_STEP_REM = 30`, `MAX_LANES = 2`); `applyLane()` applied the
drop as `translateX(-50%) translateY(lane*30rem)` on the glyph element plus a
`.wg-tick-stem`. The lane value was available per tick (`place[i].lane` / `s.lane`)
but not passed to the tooltip.

**Tooltip.** A single shared `.wg-tooltip`; `show(body, leftPct)` set only the
horizontal position, and the vertical anchor was pure CSS
(`.wg-tooltip { top:100%; margin-top:36rem }`), so it ignored the lane. `clampTip()`
was the only reposition logic and flipped the tooltip above only on viewport-bottom
overflow — never based on the bar's stored position.

**Bar position.** `position:fixed`; dragged position stored as px on
`root.style.left/top` (seeded from Python `data.posX/posY`, `applyPosition`).
No near-top/near-bottom classification was stored.

## Suggested approach (as captured)
Thread the hovered tick's lane into `show()` and offset `margin-top` by
`lane*30rem`; choose `clampTip`'s default orientation from the bar's on-screen y,
keeping the viewport-overflow flip as a final safety clamp.

## Outcome
Shipped in commit 95a0ae5. See the diff for the final implementation.
