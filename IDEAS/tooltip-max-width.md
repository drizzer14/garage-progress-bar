# Research: Max-width cap for tooltips

_Submitted: "max width for tooltips to prevent cases like in clipboard screenshot" · Status: open_

## Summary
Some tooltips grow too wide (seen in a clipboard screenshot I couldn't open — so
the exact offending tooltip is an open question below). Cap tooltip width so long
content wraps to multiple lines instead of stretching into one very wide box. This
also protects the edge-aware positioner, which assumes the tooltip is narrower than
the bar.

## Findings
There are **two** distinct tooltip elements, sized very differently:

1. **Tick tooltip — `.wg-tooltip`** (`WGModResearch.css:775-801`). Built by
   `tooltipHtml()` (`WGModResearch.js:399-436`) and `eliteTooltipHtml()`
   (`WGModResearch.js:1128`). It **already** has:
   - `min-width: 168rem;` (`:788`)
   - `max-width: 300rem;` (`:789`)
   - `white-space: normal;` (`:789` area) — so text already wraps.
   So this one is already capped. The only way it overflows 300rem is a single
   **unbreakable token** (a long word with no spaces), because there is **no
   `overflow-wrap`/`word-wrap`** set anywhere in the file.

2. **Chip tooltip — `.wg-chip-tip`** (`WGModResearch.css:1147-1170`). Created in JS
   at `WGModResearch.js:602`, shown for tier-XI upgrade chips. It has:
   - `min-width: 168rem;` (`:1157`)
   - `white-space: nowrap;` (`:1158`) — text is forced onto ONE line
   - **no `max-width`**
   With `nowrap` + no cap, long chip content stretches the box without limit. **This
   is the most likely source of the too-wide tooltip in the screenshot.**

Both tooltips are positioned by the same edge-aware clamp, **`clampTip()`**
(`WGModResearch.js:793-820`), which reads `tipEl.getBoundingClientRect().width` and
shifts the box horizontally to keep it inside the bar. The design comment at
`WGModResearch.js:787-792` states the invariant explicitly: *"the tooltip's
max-width is narrower than the bar, so it always fits."* Bar width is ~520rem, tick
cap is 300rem. **Any width cap you add must stay under the bar width** or the
horizontal clamp can no longer guarantee a fit.

No JS sets tooltip width directly — width is purely CSS (min/max-width + content).
So this is a **CSS-only** change (plus possibly flipping `nowrap`→`normal` on the
chip tip).

### Prior related fix (context)
An earlier fix made `.wg-tip-main` `display:block` and pulled the title icon
out-of-flow (`WGModResearch.css:805-840`) to stop *wrapped text* overflowing the
divider *vertically*. It did **not** touch horizontal width. `.wg-tip-text` has
`min-width:0` (`:822-824`) so titles wrap inside the cap rather than shoving the
icon off — that machinery is already in place for the tick tooltip.

## Suggested approach
CSS-only, in `WGModResearch.css`:

- **Chip tooltip** (`.wg-chip-tip`, `:1147-1170`) — the likely fix:
  - Change `white-space: nowrap;` → `white-space: normal;`
  - Add `max-width: 300rem;` (match the tick tooltip; stays under bar width)
  - If short perk names should stay one line, an alternative is to keep `nowrap`
    but add `max-width` + let it wrap only past the cap — but mixing `nowrap` with
    `max-width` won't wrap, so `normal` is required for a real cap.
- **Both tooltips** — belt-and-braces for long unbreakable tokens:
  - Add `overflow-wrap: break-word;` (and/or `word-wrap: break-word;` — Coherent is
    old, so include both) to `.wg-tip-text` (`:822`) and `.wg-chip-tip` (`:1147`).
    Verify `overflow-wrap` is honored in this Gameface build (see
    [[gameface-css-gotchas]] — several CSS features silently no-op here).

Keep any cap ≤ ~300rem to preserve the `clampTip` invariant. If the screenshot
turns out to be the *tick* tooltip overflowing, the cap is already there and the
real fix is the `overflow-wrap` line (unbreakable token) — confirm which via the
open question below.

## Touch points
- `WGModResearch.css` — `.wg-chip-tip` (`:1147-1170`), `.wg-tip-text` (`:822-824`),
  `.wg-tooltip` (`:775-801`).
- No JS change expected. If it's needed, it'd be in `clampTip()`
  (`WGModResearch.js:793-820`), but the invariant should hold if the cap stays
  under bar width.

## Verification
- Hot-reload JS/CSS per the **wgmod-build-deploy** skill (overlay must exist at
  client launch — see [[dev-loop-no-midsession-overlay]]).
- Hover a tier-XI upgrade **chip** with long content and a tick with a long
  name/effect; confirm the box wraps to multiple lines and never exceeds the cap.
- Hover ticks near both **ends** of the bar to confirm `clampTip` still keeps the
  (now guaranteed-narrow) tooltip inside the bar edges.
- Check a tooltip with a very long unbroken token to confirm `overflow-wrap` breaks
  it rather than overflowing.

## Open questions
- **Which tooltip is in the screenshot** — chip (`.wg-chip-tip`, no cap, `nowrap`)
  or tick (`.wg-tooltip`, already capped)? This decides whether the fix is
  "cap the chip tip" or "add `overflow-wrap` for an unbreakable token." If the user
  can describe the content (a perk chip vs a research/field-mod tick), that pins it.
- Does this Gameface/Coherent build honor `overflow-wrap: break-word`? Needs a live
  check; if not, a manual break or `word-break: break-all` may be required.
