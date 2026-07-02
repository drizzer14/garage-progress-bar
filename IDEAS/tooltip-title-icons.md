# Research: Add icons to tooltips' title block

_Submitted: "Add icons to tooltips' title block" · Status: open_

## Summary
Put a small icon in the tooltip header so each tooltip is identifiable at a
glance — e.g. the tech-tree module/component icon next to the name, the field-mod
glyph next to "Field Modification I", the grade emblem next to "Elite Level N".
Today the header is text-only. **Verdict: feasible, front-end-only, ~30–50 lines
(JS builder + one CSS rule). No Python changes needed.**

## Findings
The tooltip header is built in `tooltipHtml()` — `WGModResearch.js:264–301` —
from two classes: `wg-tip-caption` (kind/category caption) and `wg-tip-name`
(the item name), joined by `joinSections()` (~209). Per category:
- **fieldmod** (~268–278): `wg-tip-caption` "Field Modification <roman>", then
  either `variantsHtml()` for choice levels or a single `wg-tip-name`.
- **tech-tree** (~280–287): `wg-tip-caption` = `t.kindLabel` ("Gun"/"Tier IX"),
  then `wg-tip-name`.
- **elite / elite_rewards**: separate `eliteTooltipHtml()` (~959–974), same two
  classes.

**The icon data already exists on the tick** — no new Python flow required. Every
resolver populates `Tick.icon` (`domain/types.py:42`):
- tech-tree → `UnlockItem.icon` (module glyph or vehicle thumbnail), `techtree.py`
- field-mods → `ProgressionStep.icon`, `fieldmods.py:39`
- elite → grade emblem URL via `_emblem_url()`, `elite.py:148`; rewards → `r.icon`
- skill-tree → only the final tick carries `skilltree_final_icon`

So in the JS builder the icon is available as `t.icon`. There are also fallback
maps already in JS: `CAT_ICON` (~10–16) has generic per-mode glyphs
(research/fieldModification/vehSkillTree) usable when `t.icon` is empty.

## Suggested approach
1. In `tooltipHtml()` (and `eliteTooltipHtml()`), when `t.icon` is set, prepend an
   icon div to the header row:
   `<div class="wg-tip-icon" style="background-image:url('<t.icon>')"></div>`.
   Wrap icon + caption in a flex row (`wg-tip-header`).
2. Add CSS `.wg-tip-icon` — reuse the proven `.wg-xp-ico` sizing (16rem,
   `background-size:contain`, no-repeat, optional `drop-shadow`). See CSS ~155.
3. Fallback to `CAT_ICON[mode]` when `t.icon` is empty (field-mod/elite generic
   glyph); skip for the non-final skill-tree count ticks (no icon, no tooltip).
4. Choice-level field mods: put the icon next to the "Field Modification I"
   caption only, not per variant (per-variant icons would need new Python data —
   out of scope for MVP).

The background-image pattern is already proven in tooltips-adjacent code:
`.wg-chip-ico` (~925) and `.wg-tick-img` (~501) render `img://` icons fine.

## Touch points
- `WGModResearch.js` — `tooltipHtml()` (~264) and `eliteTooltipHtml()` (~959).
- `WGModResearch.css` — new `.wg-tip-icon` / `.wg-tip-header` rule near `.wg-xp-ico`.

## Verification
- No new Python tests needed (`Tick.icon` already covered by resolver tests).
- Build + deploy, then in-game hover each mode: tech-tree tick shows module/vehicle
  icon next to "Gun"/"Tier IX"; field-mod shows glyph next to caption; elite shows
  grade emblem next to "Elite Level N"; skill-tree final tick shows the perk icon.
- Edge checks: missing icon → text-only, still readable; tooltip height unchanged
  (flex, same line-height); `clampTip()` still keeps it on-screen.

## Open questions / Gameface notes
- Gameface quirks to respect (see gameface-css-gotchas memory): box-shadow needs a
  fill; if `gap` misbehaves use `margin-right` on the icon div. background-image +
  `img://` is safe.
- Which icon to prefer per category is a taste call — start with tech-tree module
  icons (highest impact, always populated) and validate legibility at 16rem.
