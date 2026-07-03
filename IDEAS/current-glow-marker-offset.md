# Research: Shift current-position glow marker left to overlay the fill

_Submitted: "Shift current position glow tick a bit to the left so it perfectly overlays the progress instead of sitting on its edge" · Status: open_

## Summary
The white glowing current-position marker (`.wg-cur`, shipped in 517753f) sits
straddling the fill's leading edge — half its bloom over the filled progress, half
over the empty track. It should sit a touch further left so the glow reads as
overlaying the progress rather than balancing on its tip.

## Findings
The marker element is a single `<div class="wg-cur">` (`WGModResearch.js:606`),
positioned per render by setting `left` to the fill's leading-edge percentage:
- Multi-segment (tech-tree / skill_tree): `curEl.style.left = (vehW + freeW) + "%"`
  (`WGModResearch.js:1062-1063`).
- Single-segment (elite / elite_rewards): `curEl.style.left = pct(fillPos) + "%"`
  (`WGModResearch.js:1322-1323`).

Both paths point the marker's `left` at exactly the fill edge and share one CSS
rule (`WGModResearch.css:282-301`):
```css
#wgmod-root .wg-cur {
    position: absolute;
    width: 2.5rem;
    margin-left: -1.25rem;   /* <-- centers the 2.5rem box ON the edge */
    ...
}
```

## Root cause
`margin-left: -1.25rem` is exactly half the 2.5rem width, so the marker is
**centered** on the leading-edge x. Its glow therefore extends equally to both
sides of the edge — the right half spills onto the still-empty track, which reads
as the marker "sitting on the edge" instead of on the progress.

## Suggested approach
CSS-only, one line — make `margin-left` more negative so the box shifts left onto
the filled side. Because both render paths use the same element and rule, this
nudges the marker uniformly in every mode; no JS change.

- To seat the marker's right edge flush at the fill edge (fully on the fill):
  `margin-left: -2.5rem` (a full width left).
- For a subtler "a bit to the left" that still slightly overlaps the edge, try
  `margin-left: -1.75rem` to `-2rem`.

Start around `-2rem` and eyeball it; it's a taste tweak, so tune live. Nothing else
(width, glow, transition) needs to change.

## Touch points
- `WGModResearch.css:287` — the `margin-left` on `.wg-cur` (the only change).

## Verification
- In-game (relaunch — overlay loads at launch): open the garage on a partially
  progressed vehicle in each mode (tech-tree, skill_tree, elite, elite_rewards) and
  confirm the glow now sits over the filled bar, not straddling its front. Check at
  ~0% and ~100% progress that it doesn't clip off either end oddly.
- Pure widget CSS — no pytest surface.

## Open questions
- Exact offset is a visual-taste call — confirm the final value with the user
  against a screenshot.
