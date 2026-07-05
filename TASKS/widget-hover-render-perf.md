# Research: Widget hover/render perf batch (+ stale tooltip after push)

_Submitted: bug hunt (2026-07-05) · Status: open_

## Summary
Three verified hot-path inefficiencies in WGModResearch.js, plus one small user-visible
bug the same work fixes: the tooltip is rebuilt (innerHTML + layout read/flip) on every
single mousemove even when nothing changed; the bar's rect is force-read twice per
mousemove; and the tick strip is fully rebuilt on every model push with no signature
guard (the chips row already has one). Side effect of the unguarded path: a visible
tooltip is never refreshed by render(), so after a vehicle switch with the cursor held
still it keeps showing the previous vehicle's data until the pointer moves. Confidence:
medium (all verified by direct read); impact is smoothness/CPU in the garage, not
correctness of research actions.

## Findings
- `show()` sets `tipEl.innerHTML = body` and runs `clampTip` (which resets inline styles,
  reads `getBoundingClientRect`, and may flip above the bar) unconditionally:
  `WGModResearch.js:1636-1642`, called from the mousemove handler at `js:1663` (exact-hit
  path) and `js:1673` (nearest path). Hovering one tick re-parses the tooltip DOM on
  every pointer event.
- `barRect()` (a `querySelector(".wg-ticks")` + `getBoundingClientRect()`) is recomputed
  twice per mousemove — once inside `nearestClick` (cursor affordance, `js:1658-1659`)
  and once inside `nearestByX` (tooltip target, `js:1667`); `chipAt` additionally calls
  `getBoundingClientRect()` per chip (`js:743-759` area). Forced layout reads per event.
- `renderTicks` starts with `ticksEl.innerHTML = ""` and rebuilds every tick node on
  every push (`js:1126-1157`); callers at `js:1415` (main bar) and `js:1610` (elite).
  The chips row has a `_wgSig` signature guard; the tick strip has none, so a burst of
  coalesced `onSyncCompleted` pushes churns the whole strip and wipes a hovered tick's
  DOM node mid-hover.
- Stale-tooltip bug: `render()` deliberately doesn't touch tooltip visibility
  (`js:1363-1367` and the matching comment at `js:1622-1623`), and content only updates
  on the next mousemove — so a same-position cursor shows vehicle A's tick data over
  vehicle B's bar until moved. Low severity, but a render-side "re-show/hide if content
  under cursor changed" falls out of the signature work naturally.

## Root cause
The hover path was written for correctness on a small widget and never guarded; each
enhancement (lanes, chips, clamp/flip, battle estimates) added per-event work without a
"did anything change?" check. Ticks predate the chips' signature pattern.

## Suggested approach
- In `show()`: early-return when `body`, `leftPct`, and `lane` equal the currently shown
  ones (stash on `tipEl._wg*`); this alone removes most per-mousemove work.
- Compute `barRect()` once per mousemove event and pass it to `nearestClick`/`nearestByX`
  (both already take the element; add a rect param).
- Give `renderTicks` a per-mode signature like the chips' `_wgSig` (serialize the exact
  fields the tick DOM consumes: position/class/glyph/body/lane) and skip the rebuild on
  match; on mismatch ALSO refresh-or-hide the visible tooltip (fixes the stale-tooltip
  bug).
- Gameface constraint reminder: keep DOM writes batched; no reliance on `:not()`; test
  under the minified build (rjsmin) as usual.

## Touch points
- `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js:1636-1642, 1643-1674,
  743-759, 1126-1157, 1415, 1610, 1363-1367`

## Verification
In-game (JS hot-reloads via sync_gameface + overlay-at-launch): hover a tick and jiggle
the cursor — tooltip stable, no flicker; switch vehicles with the cursor held over the
bar — tooltip updates or hides immediately; rapid research clicks (sync bursts) — no
visible strip flicker, hovered tooltip survives. No pytest surface (JS-only).

## Open questions
- None blocking. Optional: measure with the debug REPL/FPS overlay before/after if the
  win needs quantifying.
