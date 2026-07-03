# Ideas Backlog

Recorded ideas for the mod. Entries are deleted once implemented. Each entry links
to a deeper research note under `IDEAS/` for the implementer.

## Open

### Max-width cap for tooltips
Some tooltips grow too wide instead of wrapping (seen in a screenshot). The tick
tooltip `.wg-tooltip` is already capped at `max-width: 300rem`, but the **chip**
tooltip `.wg-chip-tip` has `white-space: nowrap` and no cap, so long content
stretches it — likely culprit. Also no `overflow-wrap` anywhere, so a long
unbreakable token can overflow even the tick cap. CSS-only fix; keep any cap under
the bar width so the edge-aware `clampTip` invariant holds.
→ Research: IDEAS/tooltip-max-width.md

### Tooltip icons — use highest-quality assets
Two real gaps. (1) Tech-tree **module** glyphs: mod uses the 48×48
`img://gui/maps/icons/modules/<type>.png` but an 80×80 `<type>Big.png` ships in the
same dir (what the tech-tree screen uses) — swap to `Big` for the module kind at
`engine_adapter.py:160`. (2) Elite-reward thumbnail fallback uses
`getBonusIcon("small")` (`engine_adapter.py:603`) shown at 30–52rem — swap to a
larger size arg. Grade emblems (72×72), vehicle nodes, and skill perks (`large`) are
already maxed. (Corrects the earlier "modules ship nothing larger" claim.)
→ Research: IDEAS/tooltip-icon-quality.md

### Tech-tree / tier-XI-reward tooltip icons too tall
The title-block icon in tech-tree and tier-XI exclusive-reward tooltips reads as too
tall. Both route through the same fixed 52rem square `.wg-tip-icon`: `contain`
scales portrait reward art to full 52rem height, and `.wg-tip-main-icon`'s 52rem
`min-height` dwarfs short tech-tree text. Below-bar ticks already use smaller
per-category boxes; the tooltip doesn't. Fix: category-aware icon box (mostly CSS,
one-line JS class). Related: IDEAS/tooltip-icon-quality.md.
→ Research: IDEAS/tooltip-icons-too-tall.md

### Purchase price (credits) on "done" tick tooltips
A researched ("done") tick's tooltip currently shows no footer — add the item's
credits purchase price there, styled like the XP cost line. Hook is the `t.done`
branch in `tooltipHtml` (~js:469, currently `foot = ""`). Needs a credits buy-price
read in the adapter (`engine_adapter.py`), a new `price` field threaded through
UnlockItem → recent store → Tick → a new `TickVM` VM property, and a credits glyph
(`img://gui/maps/icons/components/tooltip/credits.png`, 16×16) reusing `.wg-tip-xp`.
→ Research: IDEAS/done-tick-purchase-price.md

### Shift current-position glow marker left onto the fill
The `.wg-cur` glow marker is centered on the fill's leading edge (`margin-left:
-1.25rem` = half its 2.5rem width, `css:287`), so half its bloom spills onto the
empty track. Shift it left (e.g. `margin-left: -2rem`) so it overlays the progress
instead of straddling the edge. CSS-only one-liner; affects all modes uniformly.
→ Research: IDEAS/current-glow-marker-offset.md

### Bar disappears completely on a mode transition
When the selected vehicle moves from one bar mode to another, the whole bar vanishes
instead of re-rendering in the new mode. Two JS lines hide `#wgmod-root` (~944 on
`visible=false`; ~1060 on `mode==="complete" || sMax<=sMin`). Four candidate
mechanisms; most bug-shaped is a degenerate `scale_max<=scale_min` (e.g. field_mods
with a zero-cost remaining step, `fieldmods.py:35`) hiding a bar that has content.
Needs a live repro to pin which. Fastest discriminator: push log line vs resulting
`visible`/`scaleMax`.
→ Research: IDEAS/mode-transition-bar-disappears.md

### Release 0.4.0 (gated on all other open items)
Cut the 0.4.0 release once every other open item above is *shipped* (verified
in-game + committed), not just code-complete. Release mechanics live in the
`wgmod-release` skill; this entry is the gate/reminder. Prune the shipped entries as
they land, then run the release and delete this entry last.
→ Research: IDEAS/release-0-4-0.md
