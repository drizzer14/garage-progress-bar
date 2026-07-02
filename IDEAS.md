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

### Open Field Mods screen after researching a field mod via the bar
After a field modification is researched by clicking a bar tick, open the Field
Modifications (post-progression) screen so the player can select/configure the
variant. The nav helper already exists — `_open_field_mods_screen(veh)` in
`actions.py` (`showVehPostProgressionView`), currently used only as an error
fallback. Challenge: the purchase is an async confirm→research chain with no
synchronous success hook, so success must be caught via the action's completion
callback or a pending-open flag consumed on the next `onSyncCompleted`. Must gate on
vehicle kind — tier-XI chips also emit `unlockFieldMod` and would 404 on that view.
→ Research: IDEAS/open-field-mods-after-research.md
