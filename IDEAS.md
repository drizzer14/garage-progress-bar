# Ideas Backlog

Recorded ideas for the mod. Entries are deleted once implemented. Each entry links
to a deeper research note under `IDEAS/` for the implementer.

## Open

### wgmods.net release .zip (mod + dependencies + bilingual readme)
Mod is approved on wgmods.net. Add a new release deliverable alongside the unchanged
GitHub release: a `.zip` bundling the mod `.wotmod` + required dependency payload(s)
(OpenWG GameFace + ModsSettingsAPI — both already vendored under `installer/vendor/`;
approved on wgmods.net bundled in the archive) + a short `readme.txt` with install
instructions in **English and Ukrainian**. Process/packaging change only (update the
`wgmod-release` skill §3 + commit a bilingual readme template).
→ Research: IDEAS/wgmods-net-release-zip.md

### Estimated battles remaining alongside XP remaining in tooltips
When a tooltip shows an XP shortfall ("-<n> XP"), also show a rough "≈ N battles" figure
= `ceil(combat_xp_remaining / avg_combat_xp_per_battle)`. Front-end funnels through one
function (`xpFracHtml`, WGModResearch.js), so all modes inherit it. The crux is the data:
the mod reads no per-battle average today, so it needs a NEW engine read (likely the
per-vehicle dossier via `IItemsCache` — API unverified, probe live first) + a new
snapshot field + VM number. Hide the line when the tank has 0 battles.
→ Research: IDEAS/estimated-battles-remaining.md

### BUG: Tier-XI capstone tick tooltip says "Prerequisites not met" while purchasable
With only the final skill-tree node remaining, the bar force-brightens the final tick
as available and clickable — but its tooltip shows "Prerequisites not met" and never
the node's cost (the resolver hard-locks every remaining tick; the tooltip was never
taught the capstone case). Found twice independently in the 2026-07-04 sweep.
→ Research: IDEAS/skilltree-capstone-tooltip.md

### BUG: Skill-tree chip tooltip shows a bogus XP shortfall (node count used as XP)
Unaffordable "Next available" chips show a shortfall line computed from the
unlocked-node COUNT instead of vehicle XP (e.g. "-9 995" for a 10k node with 5 nodes
done). Same area: chips fire the purchase with no affordability gate, unlike bar ticks.
Verified end-to-end.
→ Research: IDEAS/skilltree-chip-xp-shortfall.md

### BUG: Dragging the bar flush to the top edge silently loses the position
The drag clamp allows y=0, but 0 is the "auto" sentinel on both sides — next model
push snaps the bar back to the CSS default and re-seeds, discarding the drag. Clamp
to ≥1 (+ guard zero writes in the bridge). Found twice independently.
→ Research: IDEAS/drag-top-edge-position-loss.md

### BUG: Done-marker reconcile can promote a cancelled click into a false marker
recent.py decides "done" by ABSENCE for tech/skill-tree, and the readers deliberately
degrade to [] on failure — one bad read turns a cancelled click into a permanent false
green check. Plus: pendings never expire (native-screen research adopts them), and an
unreadable vehicle id collapses to shared key 0. All three adversarially confirmed.
→ Research: IDEAS/done-marker-reconcile-false-promotion.md

### BUG: Blueprint discounts ignored for the next-vehicle tick
With blueprint fragments held, the vehicle tick prices at the undiscounted cost:
affordability understates, and clicking in the between-costs window ends in the
exchange-XP dialog or a silent post-confirm failure. Modules are correct as-is (raw
cost is required by WG's validator). Verified against the decompiled client.
→ Research: IDEAS/blueprint-discount-vehicle-unlock.md

### BUG: Elite band's trailing tick never gets the "next" highlight
Past the last sub-grade of a band, no tick shows the bright "next" state — the
milestone being climbed toward renders dim/locked (the trailing tick's state is
hardcoded outside _mark_states). Executed proof; cosmetic, cheap domain fix.
→ Research: IDEAS/elite-trailing-tick-next-state.md

### Dev/release tooling gaps (shadowing + version-check coverage)
Five confirmed small gaps: deploy leaves .pyc shadows and never warns about the
gameface overlay; build_debug_wotmod has no Py2.7 guard; the installer's cleanup glob
eats the _debug.wotmod; check_version.py can't see dist/INSTALL.txt or prose refs.
→ Research: IDEAS/build-tooling-gaps.md

### Post-refactor dead-code & stale-comment sweep (cleanup batch)
Confirmed-dead wire fields (eliteMaxLevel/eliteSub), dead CSS rules, vestigial
classes, and half a dozen false comments/docstrings left behind by shipped features
and the refactor. Zero runtime impact; batch-fix to remove drift traps.
→ Research: IDEAS/post-refactor-dead-code-sweep.md
