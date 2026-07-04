# Ideas Backlog

Recorded ideas for the mod. Entries are deleted once implemented. Each entry links
to a deeper research note under `IDEAS/` for the implementer.

## Open

### Estimated battles remaining alongside XP remaining in tooltips
When a tooltip shows an XP shortfall ("-<n> XP"), also show a rough "≈ N battles" figure
= `ceil(combat_xp_remaining / avg_combat_xp_per_battle)`. Front-end funnels through one
function (`xpFracHtml`, WGModResearch.js), so all modes inherit it. The crux is the data:
the mod reads no per-battle average today, so it needs a NEW engine read (likely the
per-vehicle dossier via `IItemsCache` — API unverified, probe live first) + a new
snapshot field + VM number. Hide the line when the tank has 0 battles.
→ Research: IDEAS/estimated-battles-remaining.md
