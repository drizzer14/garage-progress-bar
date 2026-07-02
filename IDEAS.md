# Ideas Backlog

Recorded ideas for the mod. Entries are deleted once implemented. Each entry links
to a deeper research note under `IDEAS/` for the implementer.

## Open

### Add icons to tooltips' title block
Show a small icon in the tooltip header so each tooltip is identifiable at a glance
(module/vehicle icon next to the tech-tree name, field-mod glyph next to the
caption, grade emblem next to "Elite Level N"). Feasible and front-end-only — the
tick already carries the icon. → Research: `IDEAS/tooltip-title-icons.md`

### Bug: tier-XI "Next available" chips stop being hoverable/clickable after visiting an elite / exclusive-rewards vehicle
The tier-XI upgrade chips go dead (no hover, no click) after switching to and back
from an elite vehicle or a tier-XI-with-exclusive-rewards vehicle. Root cause
confirmed (the elite render path clears the chip array but not its cached
signature, so the return skips the rebuild); one-line fix.
→ Research: `IDEAS/tier-xi-chip-hover-bug.md`

### Tier-XI upgrades show text descriptions but not exact buff numbers
Tier-XI node tooltips render a localized sentence but often omit the magnitude
(e.g. "Reduces gun reload time by % …"). The signature "mechanic" perks carry a
generic KPI the effect formatter doesn't interpret. Isolated adapter fix; needs a
live KPI probe first. → Research: `IDEAS/tier-xi-buff-numbers.md`

### Candidate settings (for the settings system in progress)
Everything below is currently hardcoded and would make a useful user setting. Listed
by likely demand; the settings framework being built is the vehicle for these.
The recipe, per-candidate front-end-vs-domain classification, and a
split-into-tickable-entries recommendation live in the research note.
→ Research: `IDEAS/settings-framework.md`

**High impact**
- **Bar width / scale** (`WGModResearch.css`: `width: 520rem`). Shrink on small screens, grow on large.
- **Fill colors** — vehicle-XP, free-XP, complete, elite, elite-rewards fills (hardcoded hex in `WGModResearch.css` ~219–247). Accessibility/color-blind + theming.
- **Element visibility** — show/hide the category icon, the XP readout, the field-mod counter, and the "next available" skill-tree chips, for a minimal bar.

**Medium impact**
- **Shadow toggle/intensity** — pairs with the open drop-shadow idea above; let users dial it for light vs. dark hangars or turn it off (`WGModResearch.css` icon drop-shadow ~62, track shadow ~151).
- **Fill opacity** — free-XP fill and tick opacities (`WGModResearch.css` ~224/278/288/299).
- **Visibility override** — force always-show or never-show, on top of the existing auto-hide-in-loadout behavior (`gameface_bridge.py:482`, `visible` VM prop).
- **Click-to-research toggle** — view-only mode to prevent accidental spends.
- **Tooltips on/off** (`WGModResearch.js` hover handlers ~720–777).

**Low impact / niche**
- Custom or shortened mode labels (`WGModResearch.js` ~487).
- Click hit tolerance + hover proximity tuning (`WGModResearch.js` `CLICK_HIT_PCT` ~216, hover gate ~762).
- z-index, for conflicts with other UI mods (`WGModResearch.css:23`).
