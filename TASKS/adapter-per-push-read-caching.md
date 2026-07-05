# Research: Cache slow-moving adapter reads recomputed on every push

_Submitted: bug hunt (2026-07-05) · Status: PARTIALLY DONE (2026-07-05)_

## Progress (2026-07-05) — micro-fixes done; the caching layer deferred
- **DONE** `blueprint_effective_cost(int_cd, xp_full, vlevel=None)` — `tech_read` now passes the
  tier it already read, skipping the redundant `getItemByCD` (actions.py still falls back to the
  lookup). Behaviour-preserving.
- **DONE** builder threads `est` + `spendable` into `_elite_model(...)` instead of recomputing
  `_est(snapshot)` + `vehicle_xp + free_xp` a second time. Covered by the existing elite tests
  (191→194 green).
- **DEFERRED** the memoization LAYER (account-wide + per-vehicle caches invalidated on stats-sync).
  It's a pure perf change ("no correctness problem" per the summary) to fail-soft adapter code
  that imports live game symbols (not pytest-importable), so its cache-invalidation timing —
  reserve expiry, reward art after a prestige level-up — can only be validated with the live
  debug REPL. Left for a session that can profile + verify in-client.

---
_Original research below._

## Summary
`build_snapshot()` runs on every coalesced `onSyncCompleted`/vehicle-change push, and
several of its reads recompute values that change rarely (or never within a session) —
including one that iterates all expirable boosters and one that does heavy
packer/customization lookups per reward. None of this is a correctness problem (all reads
are guarded and fail soft); it's garage-idle CPU spent re-deriving static answers.
Confidence: medium (call graph verified by direct read; actual per-push cost not yet
profiled in-client).

## Findings
- `adapter/engine_adapter.py:85,116-118` — every push recomputes the four
  battles-estimate inputs, which feed ONLY the tooltip range:
  `_vehicle_xp_stats(int_cd)` (dossier read), `_account_avg_battle_xp()` (account
  dossier; vehicle-independent), `_active_reserve_mult()` (iterates all expirable
  boosters; vehicle-independent), `_daily_double_factor(veh)`.
- `adapter/prestige_read.py` — `read_prestige(veh)` runs for EVERY vehicle regardless of
  the mode the builder will pick (`engine_adapter.py:78`), and its `_read_reward_art`
  (`prestige_read.py:146-184`) performs per-reward imports + style-packer/customization
  lookups whose results are static per vehicle+level.
- Micro (same theme, fold in):
  - `_read_common.py:162` `blueprint_effective_cost` re-fetches `getItemByCD(int_cd)`
    just to read `.level`, when the caller already holds the item
    (`tech_read.py:57,101-102`) — pass the level in.
  - `domain/builder.py:81` builds `est = _est(snapshot)` that the elite paths never use;
    `_elite_model` calls `_est(snapshot)` + recomputes `spendable_xp` again
    (`builder.py:210-211`). Pure-Python dict churn, trivial.

## Root cause
Each estimate/prestige enrichment was added incrementally onto the single build_snapshot
orchestration point with per-call guards but no session/vehicle-scoped memoization layer.

## Suggested approach
Small, targeted caches — no framework:
- Account-wide values (`_account_avg_battle_xp`, `_active_reserve_mult`,
  `_daily_double_factor` if account-scoped): memoize with a short TTL or invalidate on
  the stats-sync listener the bridge already has (it re-arms per mount; piggyback there).
- Per-vehicle values (`_vehicle_xp_stats`, reward art): key a small dict by
  `veh.intCD` (+ prestige level for art), cleared on stats sync. Reward art could also be
  computed lazily only when the resolved mode is ELITE_REWARDS — but that inverts the
  adapter→domain layering (adapter can't see the mode), so prefer the per-vehicle cache.
- Do the two micro fixes outright (pass level into blueprint_effective_cost; thread `est`
  /`spendable` into `_elite_model`).
Keep every cache read guarded and fail-soft, matching the adapter conventions.

## Touch points
- `src/res/scripts/client/wgmod_research/adapter/engine_adapter.py:69-118`
- `src/res/scripts/client/wgmod_research/adapter/_read_common.py` (stats helpers + blueprint)
- `src/res/scripts/client/wgmod_research/adapter/prestige_read.py:146-184`
- `src/res/scripts/client/wgmod_research/adapter/tech_read.py:101-102`
- `src/res/scripts/client/wgmod_research/domain/builder.py:81,202-211`
- `tests/` — builder micro-fix is testable; adapter caches are live-only (REPL).

## Verification
156-test suite stays green (domain micro-fixes covered). Live: REPL-probe that a garage
idle with periodic syncs hits the caches (counter probe), tooltip estimates unchanged,
reserve expiry still reflected within one sync of expiring (TTL/invalidation check).

## Open questions
- Is there a booster-expiry event worth listening to, or is stats-sync invalidation
  enough? (Reserve expiring mid-session should update the optimistic bound reasonably
  soon.)
