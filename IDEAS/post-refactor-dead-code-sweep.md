# Research: Post-refactor dead-code & stale-comment sweep (cleanup batch)
_Submitted: full-codebase bug sweep (2026-07-04) · Status: open_

## Summary
The sweep's residue: confirmed-dead code, unread wire fields, and stale
comments/docstrings. Zero runtime impact today; each is a drift trap for a future
editor. Batch them into one cleanup pass (or fix opportunistically when touching
the file anyway).

## Findings
**Wire/bridge**
- `eliteMaxLevel` (ResearchVM idx 10) and `eliteSub` (idx 12) are pushed
  (`gameface_bridge.py:475,477`) but never read by JS (the "LVL n/m" header counter
  was removed; see the comment at `WGModResearch.js:1410-1413`). Removing VM
  properties means renumbering ALL hand-maintained indices — do it only in a
  dedicated commit with in-game verify.
- `_active` (`gameface_bridge.py:40,418`) is never cleared on view teardown; the
  long-lived stats/colorblind listeners keep pushing into the torn-down presenter's
  VM during battle (harm bounded by guards: log spam + wasted snapshot builds).
  A `_onDestroy` hook or a liveness check in `push()` would quiet it.
- `elite.py:82-87,177` emits tick states `"achieved"/"next"/"upcoming"` as bare
  literals on both sides of the wire — centralize in `domain/constants.py` + a JS
  `STATE` block (same pattern as MODE/CAT/CMD/GRADE).

**Stale comments/docstrings (all confirmed false or misleading)**
- `WGModResearch.js:15` — claims "bar isn't pushed at all for HIDDEN"; Python DOES
  push a HIDDEN model with `visible=false` (JS hides via the flag first).
- `actions.py:6-8` — "Everything is guarded so a failure degrades to opening WG's
  native screen": async-phase failures bypass the except (WG's own dialogs/toasts
  cover most, see [[blueprint-discount-vehicle-unlock]]).
- `prestige_read.py:12-13` and `_read_common.py:12-13` — claim "game symbols are
  imported LOCALLY (so the module imports under pytest)"; both have module-level
  game imports and do NOT import under pytest.
- `domain/resolvers/elite.py:46-55` — `_fill_fraction` docstring says the equal
  ("maxed") sentinel maps to 0; the code returns 1.0. Not reachable as a bug (the
  game decrements `currentXP` to forbid equality; both consumers neutralize the
  maxed case) — fix the docstring, optionally harden to strict `<`.
- `WGModResearch.js:1313-1314` — claims a choice-pair field-mod level "opens the
  screen"; the code fires the purchase for any next affordable field-mod tick.
  (Likely fine — the variant choice is a separate free child step — but make the
  comment match the code after checking.)
- `_compat.py:15-22` — the grouped `LOG_*` import fallback silently no-ops BOTH
  loggers if either symbol is missing; split into two try/excepts for resilience.

**Dead CSS (WGModResearch.css × JS cross-check)**
- `.wg-cat-upgrade .wg-tick-img` (css:548-551) — unreachable; skill-tree icon ticks
  render as `.wg-final wg-chip-major` now.
- `.wg-upgrades` counter rule (css:115-122) + `setUpgrades`' show branch
  (js:571-573) — every render path hides it.
- `.wg-tab-num { padding-right: 6rem }` (css:436) — always overridden by the inline
  value `fillTabBadge` sets (js:259); tune there, not in CSS.
- JS emits `wg-grade-<family>` (js:1098) with no CSS rule; done CHIPS get `wg-done`
  (js:741) whose only CSS rule is tick-scoped (css:652) — both vestigial markers;
  either style or drop.
- `align-self: flex-start` on `.wg-tip-icon-elite` (css:941) — inert since the
  flex→block tooltip refactor.

## Suggested approach
One `chore:` commit for comments/docstrings + dead CSS (no behavior), a separate
one for the VM-field removal (wire renumbering, in-game verify), and the `_active`
liveness check as its own small `fix:`. The STATE-constants centralization fits
naturally with [[elite-trailing-tick-next-state]].

## Touch points
Listed per item above; nothing else.

## Verification
pytest + a hot-reload visual pass for the CSS deletions; full build+deploy+relaunch
only for the VM renumbering commit.

## Open questions
- Whether to bother removing the two dead VM fields at all (renumbering risk vs
  payload savings) — fine to leave with a "dead, kept to avoid renumbering" comment.
