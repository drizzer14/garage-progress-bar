---
name: wgmod-architecture
description: Architecture and code conventions for the Garage Progress Bar WoT mod — the engine-free domain / adapter / Wulf-bridge layering, the mode state machine, and the Python-side data flows and gotchas (listener re-arming, Wulf MAP-arg, engine-free domain). Use whenever editing or extending the mod's Python, adding a new bar mode, tracing how a click becomes a research action, or debugging why the bar doesn't update. (For the JS/CSS widget rendering, see wgmod-widget; for live game symbols, see references/game-api.md.)
---

# wgmod architecture & conventions

Strict layering with read/write separation; the domain layer is engine-free and
unit-tested without the game.

```
src/res/scripts/client/
  gui/mods/mod_wgmod.py               # ENTRY POINT — monkey-patches a hangar sub-view
  wgmod_research/
    _compat.py                        # engine shims: LOG_* fallbacks + _safe/_safe_int guards
                                      #   (lets adapter/bridge modules import under pytest)
    adapter/engine_adapter.py         # READ orchestrator: build_snapshot() composes the readers
    adapter/tech_read.py              #   reader: tech-tree modules + next vehicles
    adapter/post_progression_read.py  #   reader: linear field modifications
    adapter/skill_tree_read.py        #   reader: tier-XI skill tree (+ is_skill_tree)
    adapter/prestige_read.py          #   reader: Elite Levels ("prestige")
    adapter/pricing_read.py           #   reader: done-tick credits purchase price
    adapter/_read_common.py           #   shared read helpers (items-cache accessor, KPI text)
    adapter/actions.py                # WRITE-ONLY: invoke WG's research/unlock APIs
    adapter/format.py                 # pure formatting helpers (roman, icons, KPI) — tested
    adapter/i18n.py                   # widget labels from the game's OWN resource strings
    adapter/recent.py                 # session "done" markers (optimistic record + reconcile) — tested
    bridge/gameface_bridge.py         # listeners, refresh scheduling, click handlers, push/marshal
    bridge/view_models.py             # Wulf VMs: ResearchVM/TickVM/UpgradeVM (hand-numbered indices)
    bridge/wulf_args.py               # engine-free MAP-arg parsing (cmd_int_arg/cmd_xy_arg) — tested
    bridge/mod_settings.py            # ModsSettingsAPI panel: per-mode toggles, auto-hide, position
    domain/types.py                   # engine-free data types (2/3 compatible) + Mode
    domain/constants.py               # Category / GradeFamily string ids — the JS wire contract
    domain/builder.py                 # MODE STATE MACHINE (build_model + bar_visible)
    domain/resolvers/{techtree,fieldmods,skilltree,elite}.py  # pure snapshot -> ticks
src/res/gui/gameface/mods/14th_ua/WGModResearch/
  WGModResearch.{js,css}              # widget: ModelObserver -> DOM render + click/hover (see wgmod-widget skill)
```

Refactor lineage: `engine_adapter.py` was a 593-LOC monolith; the reads were carved
into the per-subsystem `*_read.py` modules, which engine_adapter re-imports under its
old private aliases (`_read_tech_unlocks`, `_read_prestige`, …) so `build_snapshot()`
call sites are unchanged. `read_purchase_price` is re-exported for the bridge.
Similarly, the VMs moved from gameface_bridge into `view_models.py`, and arg parsing
into `wulf_args.py` (bridge re-imports as `_cmd_int_arg` etc.).

## Forward flow (game -> bar)
`mod_wgmod._install()` patches `HangarVehicleParamsPresenter._onLoading`. On each
mount it injects JS/CSS via `openwg_gameface.gf_mod_inject`, hangs a `ResearchVM` on
the sub-view model (property `wgResearch`), then `bridge.push()`:
`engine_adapter.build_snapshot()` (delegates to the readers) →
`builder.build_model(snapshot, enabled=mod_settings.enabled_modes())` (picks a `Mode`,
calls the matching resolver) → the bridge writes the `ResearchProgressModel` into the
`ResearchVM` inside a Wulf `transaction()`, plus the extra channel fields: `labels`
(JSON bundle from `i18n.widget_labels()`), `colorBlind`
(`engine_adapter.is_color_blind()`), `posX`/`posY` (saved bar position),
`eliteCurrentIcon`, `spendableXp`, done-tick `price`
(`engine_adapter.read_purchase_price`). JS `ModelObserver("WGModResearch")` re-renders.

## Reverse flow (clicks -> research)
JS `invokeCommand()` calls a Wulf command on `wgResearch`. Six commands
(`view_models.py`): `researchUnlock` (tech-tree int_cd) / `unlockFieldMod`
(field-mod or skill-tree step_id) / `openSkillTree` / `openResearch` /
`openFieldMods` (no arg — done-marker clicks open the native screen) /
`setPosition` ({x, y} px from Ctrl+drag or first-run seed). Handlers parse args via
`wulf_args.cmd_int_arg` / `cmd_xy_arg` and delegate to `actions.py` (research
actions run WG's own unlock flow) or `mod_settings.set_position`. Before firing a
research action the bridge calls `_record_click()` → `recent.record(...)` so the
item can render as a "done" marker after it vanishes from the snapshot
(optimistic-record; reconciled on the next sync). Handlers do NOT refresh — the
game's resulting `onSyncCompleted` does.

## Mode state machine (`builder.build_model`, priority order)
TECH_TREE (any unlock remaining) → SKILL_TREE (tier-XI branching tree, count-based) →
FIELD_MODS → ELITE_REWARDS (unearned tier-XI milestone rewards) → ELITE (prestige
grade band) → COMPLETE. Each resolver returns ticks/dict the builder maps onto
`ResearchProgressModel`.

Per-mode user toggles: `build_model` takes `enabled` (set of Mode strings left ON;
None = all on). If the vehicle RESOLVES to a mode that is toggled off, `_emit()`
returns a `Mode.HIDDEN` placeholder — there is **no fall-through** to a
lower-priority mode. `bar_visible(overlay_closed, hide_always, hide_when_complete,
mode, in_garage)` combines that with the master hide switch, the hide-when-complete
option, the tank-setup-overlay state, and the fail-closed garage allowlist
(`in_garage` comes from the lobby state machine — only the plain `hangar/{root}`
view shows the bar).

## Conventions that bite if you miss them
- **Listeners self-heal and re-arm on EVERY mount.** Battle exit tears down the hangar
  and rebuilds the event lists with WG's presenters, dropping ours. The table-driven
  `_LISTENERS` in gameface_bridge names **five** subscriptions: `vehicle`
  (`g_currentVehicle.onChanged` → refresh), `loadout` (`onInteractorUpdated` → hide
  while a tank-setup overlay is open), `lobby state` (`onVisibleRouteChanged` →
  hide off the plain garage), `stats` (items-cache `onSyncCompleted` → live XP
  updates), `colorblind` (`onSettingsChanged`, filtered to the color-blind flag).
  `_arm()` checks actual list membership (not a "did we subscribe" flag) and MUST
  store the augmented Event back onto the attribute (`event += h; setattr(...)`) —
  WoT's `+=` doesn't reliably mutate in place. `install_all_listeners()` re-arms all
  five each `_onLoading`.
- **Sync refreshes are coalesced** onto the next tick via `BigWorld.callback(0.0, …)`
  (`_refresh_pending`); clearly-irrelevant sync reasons (`shop`, `clan`) are skipped,
  fail-open for unknown reasons.
- **Wulf commands take a single MAP arg.** JS wraps a scalar id as `{value: id}`;
  `wulf_args.cmd_int_arg` unwraps it (dict, Wulf-wrapped map, or bare scalar all
  tolerated; 0 = nothing usable). `setPosition` carries `{x, y}` via `cmd_xy_arg`.
  A bare scalar is rejected by Gameface as "not a map".
- **Every game read fails soft.** Readers wrap reads in `_compat._safe`/`_safe_int`
  (or local try/except) so one unreadable system degrades to a safe empty default and
  the rest of the bar still renders. Never let a read raise into the bridge.
- **actions.py never raises into JS** — every path falls back to opening WG's native
  screen rather than a silent spend or crash.
- **Tech-tree ticks are priced PER ITEM, not cumulatively.** `techtree.py` places each
  tick at its own cost (`xp_position = cost`, `affordable = cost <= spendable`) because
  tech-tree items are independently researchable (each has its own prereqs + cost) —
  a cumulative running sum wrongly inflates a module's position and blocks its
  affordability. Field mods are the exception (`fieldmods.py` stays cumulative — they
  unlock in sequence). Cost is `getattr(u, "xp_cost_effective", u.xp_cost)`:
  `xp_cost_effective` carries the blueprint-fragment-discounted price for a
  next-VEHICLE unlock (set in `tech_read` via `_read_common.blueprint_effective_cost`;
  modules keep raw cost — WG's validator rejects a module unlocked at a differing
  cost), and `actions._do_research` mirrors it into `UnlockProps` (discounted xpCost +
  discount% + raw xpFullCost) so the click unlocks at the shown price.
- **Done-marker reconcile uses POSITIVE evidence, and expires.** `recent._is_done`
  confirms a click by presence + a truthy flag (tech-tree: item still in `tech_unlocks`
  with `researched=True`), NOT by absence — because the readers deliberately degrade to
  `[]` on failure, and an absence test would turn one bad read into a permanent false
  green check. Skill-tree has no per-node flag so it keeps the absence test but guards
  the empty list (`bool(avail) and item_id not in avail`). A pending that never confirms
  (cancelled/failed click) is dropped after `_PENDING_MAX_RECONCILES` (~5) reconciles
  (count-based, no wall clock — engine-free/testable), and `veh_int_cd == 0` is rejected
  in both `record()` and `decorate()` so a failing vehicle can't share the sentinel key.
- **ModsSettingsAPI replaces, doesn't merge.** `updateModSettings` swaps the WHOLE
  settings dict and doesn't persist by itself — every write (toggles, position,
  reset) must pass the full dict and call `saveState()` (see
  `mod_settings.set_position`). Settings template is versioned (`settingsVersion` 2).
- **Domain layer is engine-free.** Resolvers/builder/types import no game symbols;
  game symbols live ONLY in the adapter layer (`engine_adapter` + the `*_read`
  modules, `actions.py`, `i18n.py`) and `bridge/` (catalogued in
  `references/game-api.md`). `_compat.py` shims the `LOG_*` helpers so those modules
  still import under pytest. `tests/conftest.py` puts `src/res/scripts/client` on
  `sys.path`; add a resolver/builder test when you add behavior.

## Key data types
`VehicleSnapshot` (adapter output / domain input), `ResearchProgressModel` (builder
output → bridge writes into `ResearchVM`), `Tick` (one mark: `category` drives glyph +
clickability; `action_id` = tech-tree int_cd / field-mod step_id, 0 = not clickable) —
all in `domain/types.py`. The `ResearchVM`/`TickVM`/`UpgradeVM` Wulf shapes live in
`bridge/view_models.py`: their numeric property indices are **hand-maintained** and
must match the `_addXProperty` registration order (`_setNumber(i, v)` addresses the
i-th registered property — reordering without renumbering silently mismaps fields).
The JS reads properties by NAME, and the mode/category/grade/command **string values**
are mirrored in the JS `MODE`/`CAT`/`CMD`/`GRADE` constants (top of WGModResearch.js)
— keep `domain/types.py Mode`, `domain/constants.py`, and the `view_models.py`
command names in lockstep with them (see the wgmod-widget skill).

## Adding a new read or write?
The concrete WoT/BigWorld symbols the adapter and actions depend on — and where they
live in the decompiled client — are catalogued in `references/game-api.md`. Read it
before adding a new game read (a `*_read.py` module) or unlock action (`actions.py`).
