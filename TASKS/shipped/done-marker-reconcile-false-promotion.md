# Research: Done-marker reconcile can promote a cancelled click into a false "done" marker
_Submitted: full-codebase bug sweep (2026-07-04) · Status: shipped (2026-07-04)_

## Summary
Three confirmed weaknesses in the session done-marker reconcile (`adapter/recent.py`),
worst first: (1) a cancelled bar click becomes a permanent green "done" marker for a
NEVER-researched item if any later sync's read degrades to an empty list; (2) a
pending click never expires, so researching the same item later via WG's native
screen promotes it as "done via the bar" and evicts the vehicle's genuine latest
marker; (3) an unreadable vehicle id collapses to key 0, which two vehicles can
share. All three verified adversarially with step-by-step scenarios.

## Findings
- **Polarity bug (1):** `recent.py:113-117` (TECHTREE) and `:123-125` (SKILLTREE)
  decide "done" by ABSENCE — `item_id not in remaining` / `not in avail`. The
  readers deliberately return `[]` on any failure (`tech_read.py:80-82`,
  `skill_tree_read.py:174-176`), `build_snapshot` does NOT abort on a degraded
  category (`engine_adapter.py:81`), and `push()` calls `recent.decorate(model,
  snap)` unconditionally for any non-None snapshot (`gameface_bridge.py:439-445`).
  An empty list satisfies the absence test → the pending is promoted into
  `_done[veh]` (promotion is mode-independent, `recent.py:86-89`) and then injected
  on every healthy push for the rest of the session — alongside the real,
  still-unresearched tick. FIELDMOD (`recent.py:118-122`) is presence-based — the
  SAFE polarity; the fix is to make the other two match it.
- **No expiry (2):** nothing clears `_pending` except promotion, replacement by a
  newer `record()` (`recent.py:51`), or test-only `clear()` (`:68-69`). Scenario:
  click → cancel → later research the item on WG's own screen → next decorate
  promotes the stale pending (now genuinely absent) as a bar-made marker, evicting
  the previous genuine `_done[veh]`. Marker content is factually true ("item is
  researched") but misattributed, and replace-latest semantics break.
- **Zero-key leak (3):** both `record` (`recent.py:53`, via `gameface_bridge.py:293`)
  and `decorate` (`recent.py:83`) coerce an unreadable `vehicle_int_cd` to 0 with no
  `if not veh: return` guard, so failing vehicles share key 0. Confirmed mechanism,
  practically remote (needs `veh.intCD` to raise while `g_currentVehicle.item`
  succeeded, at both ends).
- Test gaps (from the sweep, for the fix's test list): empty-list reconcile for
  TECHTREE/SKILLTREE; SKILLTREE cancel; FIELDMOD pending with absent step;
  `decorate(None, snap)` / `(model, None)`; `model.ticks is None`; veh id 0;
  pending replaced before confirmation; cross-mode marker injection.

## Root cause
`_is_done`'s absence polarity for TECHTREE/SKILLTREE composes badly with the
adapter's designed fail-soft-to-`[]` behavior; `_pending` has no lifetime bound and
no "the action actually started" signal; vehicle key 0 is not rejected.

## Suggested approach
1. Flip TECHTREE/SKILLTREE `_is_done` to require positive evidence: promoted only
   when the item is CONFIRMED gone from a NON-EMPTY list (i.e.
   `remaining and item_id not in remaining`) — a failed read then just defers
   reconcile, which is the safe direction. (For SKILLTREE, `avail` empty is also the
   legit end-state; use `snapshot.skilltree_done`/`total` movement or the
   `is_skill_tree` + received check as the positive signal instead — needs a little
   care, the note-taker's suggestion is the `remaining`-guard shape.)
2. Bound `_pending`: clear it on vehicle switch away (decorate for a different veh),
   or timestamp it via `BigWorld.time()`-free counter (no wall clock in domain —
   count decorates: expire after N reconciles without promotion).
3. Reject `veh_int_cd == 0` in both `record()` and `decorate()` (no marker beats a
   wrong marker).

## Touch points
- `src/res/scripts/client/wgmod_research/adapter/recent.py:44-125`
- `src/res/scripts/client/wgmod_research/bridge/gameface_bridge.py:284-330` (record path)
- `tests/test_recent.py` (all the gap cases above)

## Verification
Pure-domain: pytest with the new cases (empty-list + pending must NOT promote;
pending expires after N decorates; veh 0 rejected). Live sanity: click a tech tick,
cancel, play a sync-heavy session, confirm no phantom green check appears.

## Open questions
- Expiry policy for (2): clear-on-vehicle-switch is simplest but drops the marker if
  the user browses the carousel between click and sync — count-based expiry (e.g.
  ~5 reconciles) is safer. User preference?
