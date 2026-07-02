# Ideas Backlog

Recorded ideas for the mod. Entries are deleted once implemented. Each entry links
to a deeper research note under `IDEAS/` for the implementer.

## Open

### Tooltip "N/M XP" — total-XP icon + XP remaining
In the cost footer that reads `have / need XP`, replace the literal "XP" with the
game's total-XP icon, and show how much XP is left to reach the target — plus a
"without free XP" variant (remaining if only the vehicle's own XP counted). The
icon (`XP_ICON`) and the vehicle/free-XP split already exist; work is mostly in one
JS helper (`xpFracHtml`) + CSS.
→ Research: IDEAS/tooltip-xp-icon-and-remaining.md

### Brighter glowing marker at the current progress position
Add a bright, blurred/glowing marker at the bar's current fill edge (the player's
current level), modeled on WoT's Battle Pass in-chapter progress bar. Position is
the existing fill-edge percentage `pct(sMin + fv + ff)` — no data changes; a new
`.wg-cur` element + CSS glow, added in both `render()` and `renderElite()`. Reuse
the confirmed `box-shadow`/`drop-shadow` glow (as in `wg-aff`); `filter: blur()` is
unsafe in this Gameface build — simulate the blur with a soft glow.
→ Research: IDEAS/current-level-glow-marker.md

### Show total XP near the Tier-XI upgrades counter
Skill_tree mode shows only the count-based "N/M upgrades" readout, not the total-XP
figure every other mode shows. Add total spendable XP next to the counter. Pure
frontend — `data.spendableXp` (= vehicle_xp + free_xp) is already plumbed to the
skill_tree branch; just render it (format with `fmtXp` + `XP_ICON`, don't reuse
`setXp()` which sums the node-count fields). A spare hidden `.wg-upgrades` slot can
host the second figure. No Python/i18n changes.
→ Research: IDEAS/skill-tree-total-xp-readout.md
