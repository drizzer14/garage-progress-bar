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

### JS mode/category/command constant sweep
Follow-up to the Tier 3g refactor. `WGModResearch.js` switches on mode / category /
command names as **bare string literals** scattered across ~30 sites; the Python side
already centralized them (`domain/types.py` `Mode`, `domain/constants.py` `Category`,
`bridge/view_models.py` commands). A value drift or typo on the JS side fails
SILENTLY (a tick renders wrong or a click no-ops — no exception), so hoist them into a
single source-of-truth block at the top of the JS mirroring the Python enums. Low
priority, but verify live (no compile check on JS).
→ Research: IDEAS/js-constant-sweep.md
