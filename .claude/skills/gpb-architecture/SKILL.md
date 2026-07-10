---
name: gpb-architecture
description: Architecture of the Garage Progress Bar WoT mod specifically — its concrete wgmod_research file tree, the six bar modes + priority order, the resolvers, per-item tech-tree pricing, blueprint discount, done-marker reconcile, and the ResearchVM/TickVM/UpgradeVM shapes. Use when editing or extending THIS mod's Python, adding a bar mode, tracing a click→research action, or debugging why the bar doesn't update. (For the reusable engine-free domain/adapter/bridge discipline and the conventions that bite, see the wotmod-architecture harness skill; for the JS/CSS widget, gpb-widget; for live game symbols, references/game-api.md.)
---

# wgmod architecture (this mod's specifics)

The reusable pattern — engine-free `domain/` vs `adapter/` (reads+writes) vs `bridge/`
(Wulf/Gameface), and the conventions that bite (listeners re-arm every mount, Wulf MAP-arg,
fail-soft reads, `_compat.py` shim, ModsSettingsAPI replace+saveState, hand-numbered VM
indices, import≠ready) — lives in the **wotmod-architecture** harness skill. This skill is
how the Garage Progress Bar realizes it.

```
src/res/scripts/client/
  gui/mods/mod_wgmod.py               # ENTRY POINT — monkey-patches a hangar sub-view
  wgmod_research/
    _compat.py                        # engine shims: LOG_* fallbacks + _safe/_safe_int guards
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
  WGModResearch.{js,css}              # widget (see gpb-widget skill)
```

Refactor lineage: `engine_adapter.py` was a 593-LOC monolith; reads were carved into the
per-subsystem `*_read.py` modules, which engine_adapter re-imports under its old private
aliases (`_read_tech_unlocks`, `_read_prestige`, …) so `build_snapshot()` call sites are
unchanged. `read_purchase_price` is re-exported for the bridge. Similarly the VMs moved from
gameface_bridge into `view_models.py`, arg parsing into `wulf_args.py` (bridge re-imports as
`_cmd_int_arg` etc.).

## Forward flow (game → bar)
`mod_wgmod._install()` patches `HangarVehicleParamsPresenter._onLoading`. On each mount it
injects JS/CSS via `openwg_gameface.gf_mod_inject`, hangs a `ResearchVM` on the sub-view model
(property `wgResearch`), then `bridge.push()`: `engine_adapter.build_snapshot()` →
`builder.build_model(snapshot, enabled=mod_settings.enabled_modes())` (picks a `Mode`, calls
the matching resolver) → the bridge writes the `ResearchProgressModel` into `ResearchVM` in a
Wulf `transaction()`, plus channel fields: `labels` (JSON from `i18n.widget_labels()`),
`colorBlind`, `posX`/`posY`, `eliteCurrentIcon`, `spendableXp`, done-tick `price`. JS
`ModelObserver("WGModResearch")` re-renders.

## Reverse flow (clicks → research)
JS `invokeCommand()` calls a Wulf command on `wgResearch`. Six commands (`view_models.py`):
`researchUnlock` (tech-tree int_cd) / `unlockFieldMod` (field-mod or skill-tree step_id) /
`openSkillTree` / `openResearch` / `openFieldMods` (no arg — done-marker clicks open the
native screen) / `setPosition` ({x, y} px). Handlers parse args via `wulf_args.cmd_int_arg` /
`cmd_xy_arg` and delegate to `actions.py` or `mod_settings.set_position`. Before a research
action the bridge calls `_record_click()` → `recent.record(...)` so the item can render as a
"done" marker after it vanishes (optimistic-record; reconciled next sync). Handlers do NOT
refresh — the game's `onSyncCompleted` does.

## Mode state machine (`builder.build_model`, priority order)
TECH_TREE (any unlock remaining) → SKILL_TREE (tier-XI branching tree, count-based) →
FIELD_MODS → ELITE_REWARDS (unearned tier-XI milestone rewards) → ELITE (prestige grade band)
→ COMPLETE. `build_model` takes `enabled` (Mode strings left ON; None = all). If a vehicle
RESOLVES to a mode toggled off, `_emit()` returns a `Mode.HIDDEN` placeholder — **no
fall-through** to a lower-priority mode. `bar_visible(overlay_closed, hide_always,
hide_when_complete, mode, in_garage)` combines that with the master hide switch, the
hide-when-complete option, the tank-setup-overlay state, and the fail-closed garage allowlist
(`in_garage` = only the plain `hangar/{root}` view).

## Conventions specific to this mod
- **Tech-tree ticks are priced PER ITEM, not cumulatively.** `techtree.py` places each tick at
  its own cost (`xp_position = cost`, `affordable = cost <= spendable`) — items are
  independently researchable. Field mods are the exception (`fieldmods.py` stays cumulative —
  they unlock in sequence). Cost is `getattr(u, "xp_cost_effective", u.xp_cost)`:
  `xp_cost_effective` carries the blueprint-fragment-discounted price for a next-VEHICLE unlock
  (set in `tech_read` via `_read_common.blueprint_effective_cost`; modules keep raw cost — WG's
  validator rejects a module unlocked at a differing cost), and `actions._do_research` mirrors
  it into `UnlockProps` (discounted xpCost + discount% + raw xpFullCost).
- **Done-marker reconcile uses POSITIVE evidence, and expires.** `recent._is_done` confirms a
  click by presence + a truthy flag (tech-tree: still in `tech_unlocks` with `researched=True`),
  NOT by absence — the readers deliberately degrade to `[]` on failure, so an absence test would
  turn one bad read into a permanent false check. Skill-tree has no per-node flag so it keeps
  the absence test but guards the empty list. A pending that never confirms is dropped after
  `_PENDING_MAX_RECONCILES` (~5, count-based/testable); `veh_int_cd == 0` is rejected in both
  `record()` and `decorate()`.
- Settings template is versioned (`settingsVersion` 2).

## Key data types
`VehicleSnapshot` (adapter output / domain input), `ResearchProgressModel` (builder output →
bridge writes into `ResearchVM`), `Tick` (`category` drives glyph + clickability; `action_id`
= tech-tree int_cd / field-mod step_id, 0 = not clickable) — all in `domain/types.py`. The
`ResearchVM`/`TickVM`/`UpgradeVM` Wulf shapes live in `bridge/view_models.py`; their numeric
property indices are hand-maintained and must match `_addXProperty` registration order. The JS
reads by NAME, and the mode/category/grade/command string values are mirrored in the JS
`MODE`/`CAT`/`CMD`/`GRADE` constants — keep `domain/types.py Mode`, `domain/constants.py`, and
the `view_models.py` command names in lockstep (see gpb-widget).

## Adding a new read or write?
The concrete WoT/BigWorld symbols this mod uses — and which reader/action each lives in — are
in `references/game-api.md`. The full generic symbol catalogue is the **wotmod-architecture**
harness skill's `references/game-api.md`. Read before adding a `*_read.py` or an `actions.py` path.
