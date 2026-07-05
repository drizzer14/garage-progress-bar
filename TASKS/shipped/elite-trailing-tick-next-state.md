# Research: Elite band's trailing tick never gets the "next" highlight
_Submitted: full-codebase bug sweep (2026-07-04) · Status: shipped (2026-07-04)_

## Summary
A player who has achieved every sub-grade of their elite grade band but not the next
family's first grade sees NO "next"-highlighted tick at all — the very milestone
they're climbing toward renders as a dim locked badge. Confirmed by executing the
resolver on a synthetic scale; contradicts the code's own comment ("so the bar
always shows what you're climbing toward", elite.py:165). Cosmetic but real; the
window spans multiple elite levels.

## Findings
- In-band ticks get states via `_mark_states` (`domain/resolvers/elite.py:74-87`),
  which marks the FIRST unreached tick `"next"`.
- The trailing end-of-band tick (the next family's first sub-grade) is built OUTSIDE
  that helper at `elite.py:167-177` with a hardcoded
  `"achieved" if level >= ng.level else "upcoming"` — it can never be `"next"`, and
  the `"achieved"` arm is only reachable in the maxed fallback.
- Executed proof (grades iron@1/3/5/7 + bronze@10, level 8):
  states = `achieved ×4, upcoming` — no `next` anywhere. Control at level 13 (an
  in-band unreached tick exists) correctly yields a `next`.
- Not visually equivalent: `WGModResearch.css:706-709` (`wg-state-next` pip: bright
  parchment + white glow) vs `:710-713` (`wg-state-upcoming`: dim grey, "reads
  locked"); same split for emblems (`:795-801` vs `:814+`).
- `tests/test_resolver_elite.py` only covers levels where an in-band next exists.

## Root cause
The trailing tick's state is computed ad hoc at `elite.py:171-177` instead of
participating in `_mark_states`' first-unreached logic.

## Suggested approach
In `resolve_grade_band`, after `_mark_states`, set the trailing tick's state to
`"next"` when the whole band is achieved and `level < ng.level` (i.e. no in-band
tick claimed "next"). Roughly: `state = "achieved" if level >= ng.level else
("next" if all in-band achieved else "upcoming")`. Add a resolver test for the
between-families window (e.g. the executed scenario above).

## Touch points
- `src/res/scripts/client/wgmod_research/domain/resolvers/elite.py:156-177`
- `tests/test_resolver_elite.py`

## Verification
pytest (new case: all-band-achieved → trailing tick state == "next"; maxed fallback
still "achieved"). In-game sanity on any elite vehicle sitting past its band's last
sub-grade: the end-of-band badge should glow like an active target.

## Open questions
- None — pure domain, engine-free, cheap to fix.
