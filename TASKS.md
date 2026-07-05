# Tasks Backlog

Recorded ideas and bugs for the mod. Entries are deleted once implemented. Each entry
links to a deeper research note under `TASKS/` for the implementer.

## Open

### Potential Tier XI ghost bar on lines that HAVE a real Tier XI
The opt-in speculative bar's gate never checks `tech_unlocks` for a researched real
Tier-XI vehicle successor, so it can show on lines where the real XI exists. Includes
related polish: tooltip proximity gate, dead guard, coverage gaps.
→ Research: `TASKS/potential-xi-real-successor-gate.md`

### Widget hover/render perf batch (+ stale tooltip after push)
Tooltip innerHTML + layout flip rebuilt on every mousemove; bar rect read twice per move;
tick strip fully rebuilt per push with no signature guard — which also leaves a visible
tooltip showing the previous vehicle's data until the pointer moves.
→ Research: `TASKS/widget-hover-render-perf.md`

### First-run position seed pins the bar to px (resolution drift)
The one-time seed persists the measured CSS-default spot as fixed pixels, so the
vh-relative default AND the Reset target go stale after any resolution change.
→ Research: `TASKS/position-seed-resolution-drift.md`

### Skill-tree done chip never promotes when the unlock empties the frontier
`recent._is_done`'s `bool(avail)` guard makes an emptied-but-incomplete frontier
unconfirmable — the pending marker silently expires. Fix via positive done-count evidence.
→ Research: `TASKS/skilltree-done-chip-empty-frontier.md`

### Cache slow-moving adapter reads recomputed on every push
Battles-estimate inputs (incl. a full booster iteration) and the heavy prestige reward-art
read recompute per push regardless of mode; plus two micro double-computes.
→ Research: `TASKS/adapter-per-push-read-caching.md`

### Release/docs version-reference hygiene
The release skill's "7 files" list wrongly includes README.md (self-contradiction); the
client version 2.3.0.1 is duplicated across ~7 files with no check_version coverage;
CONTRIBUTING.md's layout listing is stale.
→ Research: `TASKS/release-docs-version-hygiene.md`

### Build-tooling hardening batch
OS-cruft filter for the package copy, build-before-clean deploy ordering, clean_dist
debug-package exclusion, minifier preflight import, -OO for the debug builder.
→ Research: `TASKS/build-tooling-hardening.md`

### Widget hygiene nits (low-stakes JS/CSS cleanups)
Phantom lane reservation for the done marker, stale active-chip ref in elite renders,
`{}` MAP-arg symmetry, dead/dubious CSS rules, and the capstone direct-unlock design
question.
→ Research: `TASKS/widget-hygiene-nits.md`
