# Research: Estimated battles remaining alongside XP remaining in tooltips

_Submitted: "Display estimated battles remaining alongside XP remaining in tooltips" · Status: open_

## Summary
When a tooltip shows an XP shortfall ("-<n> XP" to research/unlock/reach), also show a
rough "≈ N battles" figure so the player knows how far off the milestone is in play
terms. Estimate = `ceil(xp_remaining / avg_combat_xp_per_battle)` for the selected
vehicle. Purely additive to the existing remaining sub-line — no change to bar geometry
or the XP math already in place.

## Where it plugs in (front-end)
The whole feature funnels through **one** function:
- `xpFracHtml(have, need, iconUrl, vehHave)` — `WGModResearch.js:310`. This renders the
  cost headline + the `.wg-tip-xp-rem` shortfall sub-line for **every** mode
  (tech-tree footer `:523`, field-mod footer, elite grade `_mark_states` ticks, and
  skill-tree chips `:734`). Add the battles line here once and all modes inherit it.
- The shortfall it already computes: `left = need - have` (total, free XP counted) and
  `vehLeft = need - vehHave` (combat XP alone). **Base the battles estimate on the
  combat-XP shortfall**, because only combat XP accrues by playing *this* vehicle
  (free XP is a shared account pool that doesn't grow per battle on one tank). Use
  `vehLeft` when present, else `left`.
- Emit the battles figure as its own span inside `.wg-tip-xp-rem` (new `.wg-tip-battles`
  class), language-neutral like the existing "-<n>" figures — e.g. `≈ 12` + a battle
  glyph, no translatable "battles"/"left" word. A tank/battle glyph candidate:
  `img://gui/maps/icons/...` (pick one during impl; the elite readout already uses
  `library/xpIcon_23x22.png` for combat XP — a "battles played" icon lives under the
  stats/profile icon sets).

## The crux: where does avg XP/battle come from? (needs a REPL probe)
The mod does **not** read any per-battle average today. `build_snapshot`
(`adapter/engine_adapter.py:54`) reads only `stats.freeXP`, `stats.unlocks`, and
`veh.xp`/`.level`/`.isElite`. A **new read** is required, plus a new
`VehicleSnapshot` field (`domain/types.py`) carried through to a ViewModel number
(`bridge/view_models.py`) so JS can read it.

Likely source — the per-vehicle dossier via `IItemsCache` (confine to
`engine_adapter.py`, wrap in try/except like every other read):
- `_items_cache().items.getVehicleDossier(intCD)` → a dossier object whose random-battle
  block exposes battles count + total/avg XP (candidate accessors:
  `.getRandomStats().getBattlesCount()` / `.getXP()` / `.getAvgXP()`).
- Compute `avg = total_xp / battles` (or use `getAvgXP()` directly), guard `battles > 0`.

**This API surface is unverified — probe it live before coding** (wgmod-debug-repl):
confirm the dossier accessor name on `IItemsCache.items`, confirm the random-stats block
method, and confirm `intCD` is the right key (the snapshot already has `vehicle_int_cd`).
If `getVehicleDossier` doesn't exist, the account dossier / profile stats controller is
the fallback; re-locate against the decompiled EU 2.3 client.

## Suggested approach
1. **Adapter read** (`engine_adapter.py`, new helper e.g. `_read_avg_battle_xp(veh)` —
   or in `pricing_read.py`/a new reader once the Tier-3g carve-up lands): return an int
   avg combat XP/battle, or `0` when `battles == 0` / unreadable.
2. **Snapshot** (`domain/types.py`): add `avg_battle_xp` (int, default 0). Wire it in
   `build_snapshot`.
3. **ViewModel** (`bridge/view_models.py` + wherever the header numbers are added):
   expose it as a number on the VM so JS gets it alongside `spendableXp`.
4. **JS** (`WGModResearch.js`): read the VM number into the same module-scope the other
   XP figures use (`spendableXp`/`fillVehicle` are threaded into render), pass it into
   `xpFracHtml`, and render `≈ ceil(shortfall / avg)` when `avg > 0` and short.
5. **CSS**: `.wg-tip-battles` styling to sit inline after the remaining figures.

## Design / correctness notes
- **Hide when avg is 0** (no battles on this tank, or unreadable) — never divide by zero,
  never show "≈ ∞". The line simply doesn't appear, like the vehicle-only figure already
  self-suppresses.
- It's a *historical* average, not premium/x2-adjusted or booster-aware — label it as an
  estimate (the `≈` prefix does this without a translated word).
- Elite mode's shortfall is already combat-XP based (`COMBAT_XP_ICON`), so the same
  combat-XP-per-battle divisor is consistent there.
- Only shown while short (inside the `have < need` branch); once affordable the whole
  sub-line is omitted, so no "0 battles" noise.

## Touch points
- Edit: `adapter/engine_adapter.py` (new read + wire into `build_snapshot`),
  `domain/types.py` (`VehicleSnapshot.avg_battle_xp`), `bridge/view_models.py`
  (+ header VM number wiring), `WGModResearch.js` (`xpFracHtml` + read the VM number),
  `WGModResearch.css` (`.wg-tip-battles`).
- Model to copy for a new engine read: the existing `_safe_stats`/`stats.freeXP` path.
- Note: if done after the engine_adapter carve-up (`finish-engine-adapter-split.md`),
  the new read belongs in a `*_read.py` module, not `engine_adapter.py`.

## Verification
- `python -m pytest -q` — add a domain/type test for the new field default; the divisor
  math itself lives in JS (untested layer).
- Engine read is live-only (imports game symbols): build + deploy + relaunch, then on a
  vehicle **with** battles confirm "≈ N" appears and roughly matches
  `shortfall / (garage stats avg XP)`; on a **fresh** vehicle (0 battles) confirm the
  battles line is absent. Check tech-tree, field-mod, elite, and skill-tree tooltips.
- `python.log` clean of tracebacks from the new dossier read.

## Open questions
- Exact dossier API (`getVehicleDossier` + random-stats accessors) — **probe first.**
- Battle glyph choice (a "battles played" icon vs. reusing a tank silhouette).
- Divisor policy: pure combat XP/battle (recommended) vs. including the small auto-free-XP
  slice each battle grants — keep it simple (combat only) unless it reads as too pessimistic.
