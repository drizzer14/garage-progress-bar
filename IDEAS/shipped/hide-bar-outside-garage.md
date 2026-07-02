# Research: Hide the bar outside the garage

_Submitted: backlog entry "Hide the bar outside the garage" · Status: shipped (already implemented — entry pruned)_

## Outcome
Investigated during a research pass and found **already fully implemented, tested,
and committed** (commit 1084615, "feat(visibility): hide the bar outside the plain
garage"). The IDEAS.md entry was removed as a stale duplicate of shipped work.

## What's in place
- **Domain gate** `bar_visible(overlay_closed, hide_always, hide_when_complete,
  mode, in_garage)` — `domain/builder.py:32–53`. Fail-closed: `if not in_garage:
  return False`, evaluated before the overlay/settings checks.
- **Detection** `_in_garage()` — `bridge/gameface_bridge.py:188–215`. Reads the
  lobby state machine's visible leaf and returns `state_id.endswith("hangar/{root}")`
  (the plain garage; `{root}` is unique client-wide). Fail-closed on any error.
- **Live re-arm** `install_lobby_state_listener()` / `_on_lobby_state_changed()`
  subscribe to `onVisibleRouteChanged`, re-installed on every hangar mount so the
  bar hides/shows when navigating away/back.
- **Wiring** `push()` passes `_in_garage()` into `bar_visible()` (~676–678).
- **Tests** `tests/test_visibility.py` — `test_outside_garage_hides_any_mode`,
  `test_outside_garage_wins_over_open_overlay`.

Covers the playlists view, the All Vehicles browser (gotcha: `allVehicles` is the
browser, not the garage), loadout overlays, and any unknown view (fail-closed). No
remaining gaps. See also the hide-bar-outside-garage handoff memory.
