# Research: Dragging the bar flush to the top edge silently loses the saved position
_Submitted: full-codebase bug sweep (2026-07-04) · Status: shipped (2026-07-04)_

## Summary
Ctrl+dragging the bar to the very top of the screen persists `posY=0` — but 0 is
the "auto/unseeded" sentinel on both sides of the wire, so on the next model push
the bar snaps back to the CSS default and the user's placement (including the X
coordinate) is discarded and re-seeded. Found independently by two sweep agents.

## Findings
- The drag clamp allows exactly 0: `WGModResearch.js:1580` — `cy = Math.max(0, …)`;
  `onUp` sends `{x, y: 0}` via `CMD.SET_POSITION` (`js:1589-1592`).
- Python persists it as-is: `bridge/mod_settings.py` `clamp_pos` (`:55-65`) keeps 0,
  and 0 is documented there as "auto".
- The JS reader treats EITHER coordinate being 0 as fully auto:
  `applyPosition` (`js:944`) — `if (x > 0 && y > 0)`; the else branch clears the
  inline position AND re-seeds the settings from the CSS-default layout
  (`js:955-968`, `seed:1`), overwriting the stored reset-default.
- The bar sticks at the dragged spot until the next push (vehicle switch, XP tick,
  sync), then jumps — so the failure looks like a random snap-back.
- Related hardening (low, from the same sweep): `_on_set_position`
  (`gameface_bridge.py:371-381`) persists whatever `cmd_xy_arg` returns, and that
  helper's failure signature is `(0, 0)` — a malformed Wulf delivery resets the
  saved position instead of no-oping. A shared "reject (x<=0 or y<=0) writes unless
  explicitly seeding" guard would cover both.

## Root cause
In-band sentinel: 0 is simultaneously a legal drag coordinate (top edge) and the
"no saved position" marker, with no separation between the two meanings.

## Suggested approach
Smallest fix: clamp the drag to `>= 1` on both axes (`Math.max(1, …)` in the onUp
computation) so a legal drag can never emit the sentinel. Belt-and-braces: in
`_on_set_position`, ignore non-seed writes where either coordinate is <= 0.
Do NOT change the sentinel itself — 0-means-auto is baked into `clamp_pos`, the
panel steppers, reset handling, and `applyPosition`.

## Touch points
- `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js:1580, 1589-1592`
- `src/res/scripts/client/wgmod_research/bridge/gameface_bridge.py:371-381` (guard)
- `tests/test_position.py` (cover clamp_pos + the new guard semantics if Python-side)

## Verification
In-game: Ctrl+drag the bar flush to the top, release, switch vehicles → the bar
must stay at (x, 1) rather than snapping to center. Panel steppers must show the
dragged coords. JS part hot-reloads; the bridge guard needs build+deploy+relaunch.

## Open questions
- None blocking; purely which side(s) to fix (recommend both).
