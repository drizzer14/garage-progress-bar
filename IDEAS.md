# Ideas Backlog

Recorded ideas for the mod. Entries are deleted once implemented. Each entry links
to a deeper research note under `IDEAS/` for the implementer.

## Open

### Tooltip icons — use highest-quality assets
Two real gaps. (1) Tech-tree **module** glyphs: mod uses the 48×48
`img://gui/maps/icons/modules/<type>.png` but an 80×80 `<type>Big.png` ships in the
same dir (what the tech-tree screen uses) — swap to `Big` for the module kind at
`engine_adapter.py:160`. (2) Elite-reward thumbnail fallback uses
`getBonusIcon("small")` (`engine_adapter.py:603`) shown at 30–52rem — swap to a
larger size arg. Grade emblems (72×72), vehicle nodes, and skill perks (`large`) are
already maxed. (Corrects the earlier "modules ship nothing larger" claim.)
→ Research: IDEAS/tooltip-icon-quality.md

### Purchase price (credits) on "done" tick tooltips
A researched ("done") tick's tooltip currently shows no footer — add the item's
credits purchase price there, styled like the XP cost line. Hook is the `t.done`
branch in `tooltipHtml` (~js:469, currently `foot = ""`). Needs a credits buy-price
read in the adapter (`engine_adapter.py`), a new `price` field threaded through
UnlockItem → recent store → Tick → a new `TickVM` VM property, and a credits glyph
(`img://gui/maps/icons/components/tooltip/credits.png`, 16×16) reusing `.wg-tip-xp`.
→ Research: IDEAS/done-tick-purchase-price.md

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
