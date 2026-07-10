# Tasks Backlog

Recorded ideas and bugs for the mod. Entries are deleted once implemented. Each entry
links to a deeper research note under `TASKS/` for the implementer.

## Open

### Widget render-path rebuild-skip (deferred perf; needs in-game verify)
The per-mousemove wins (show() early-return, single barRect read) and the stale-tooltip fix
(hide on data change) are DONE. What remains is the `renderTicks` skip-rebuild on an unchanged
per-mode signature — deferred because it interacts subtly with the lane/`hot` bottom + tick-meta
state and can only be validated in-game (JS hot-reload).
→ Research: `TASKS/widget-hover-render-perf.md`

### Cache slow-moving adapter reads (deferred perf; live-REPL only)
The testable micro-fixes are DONE (builder threads `est`/`spendable` into `_elite_model`;
`blueprint_effective_cost` takes the level from the caller). The memoization LAYER — account-wide
reads (avg battle XP, reserve mult, daily-double) + per-vehicle reads (vehicle XP stats, prestige
reward art), invalidated on stats-sync — remains deferred: it's a pure perf change to fail-soft
adapter code whose invalidation timing can only be validated with the live debug REPL.
→ Research: `TASKS/adapter-per-push-read-caching.md`

### Widget hygiene: remaining CSS-consistency nits (low, verify-only)
The behavioral/dead-code nits are DONE (done-marker excluded from lane computation; elite render
clears the active-chip ref; no-arg commands pass `{}`; dead `align-self` rule removed). What
remains are two low-value CSS-consistency items that need a live hot-reload check, not a fix:
normalize `.wg-tab-art`'s `background` shorthand to longhand, and confirm the
`.wg-tip-rem-veh + .wg-tip-battles` adjacent-sibling combinator renders in Coherent. The
capstone direct-unlock question was settled (keep screen-only; documented in gpb-widget).
→ Research: `TASKS/widget-hygiene-nits.md`
