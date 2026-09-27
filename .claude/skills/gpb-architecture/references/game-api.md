# WoT / BigWorld game API — this mod's usage map

The **full generic symbol catalogue** (what each WoT/BigWorld/Wulf/OpenWG symbol is, its exact
call/return shape, where it lives in the decompiled client, and the gotchas) is in the
**wotmod:architecture** harness skill's `references/game-api.md`. Read that first for any symbol.

This file records only *which module in THIS mod uses which symbol* — the mapping the harness
catalogue is deliberately generic about. All reads are wrapped in try/except so an API drift
degrades one category to a safe default instead of blanking the bar. To inspect anything live,
use the **gpb-debug-repl** skill.

## Entry / mount / listeners (`gui/mods/mod_wgmod.py`, `bridge/gameface_bridge.py`)
- Patched sub-view: `HangarVehicleParamsPresenter` (`_onLoading` mount hook, `getViewModel()` host).
- Inject: `openwg_gameface.gf_mod_inject`. VMs: `frameworks.wulf.ViewModel`/`Array`. Defer:
  `BigWorld.callback(0.0, …)`.
- Five re-armed listeners (`_LISTENERS`): `CurrentVehicle.g_currentVehicle.onChanged` (vehicle);
  `ILoadoutController.onInteractorUpdated` (loadout overlay hide); lobby
  `getLobbyStateMachine().onVisibleRouteChanged` → `visibleState.getStateID()` == `hangar/{root}`
  (garage allowlist, fail-closed); `IItemsCache.onSyncCompleted` (stats, skip `shop`/`clan`);
  `ISettingsCore.onSettingsChanged` filtered to `GRAPHICS.COLOR_BLIND` **or** a geometry key
  (`_geometry_setting_keys()` — resolution/window/interface-scale; triggers a position recompute).
- Plus `gui.g_guiResetters` (a `set`, not an Event): `_arm_gui_resetters` adds `_on_gui_reset`
  (WoT invokes every resetter on a screen-resolution / GUI-scale reset → `refresh()` re-pushes so
  the widget re-derives / rescales its position). Idempotent add, armed alongside `_LISTENERS`.

## Reads (`adapter/*_read.py`, `_read_common.py`)
- `engine_adapter.is_color_blind()` ← `ISettingsCore.getSetting(GRAPHICS.COLOR_BLIND)`.
- `tech_read` ← `veh.getUnlocksDescrs()`, `items.getTypeOfCompactDescr` + `GUI_ITEM_TYPE.VEHICLE`,
  `_read_common.blueprint_effective_cost` (blueprint discount — see catalogue's WRITE section).
  - **`unlocksDescrs` is the OUTGOING unlock graph — what this vehicle unlocks, not what it cost.**
    A vehicle's own purchase price lives on its **PARENT** node and is never in its own list; its
    successors' prices are. Default/stock modules never appear at all (they go through
    `__collectDefaultUnlocks`). So "Σ costs in `unlocksDescrs`" = *everything researchable FROM this
    vehicle* — the semantics the COMPLETE Research total deliberately reports. Engine corroboration:
    `isEliteByDefault = not self.unlocksDescrs and not self.eliteByProgression`.
    Corpus scan of EU **2.3.1.0** `item_defs/vehicles/**`: **796 of 1251** vehicle types carry no
    `<unlocks>` element at all (premiums, reward tanks, tier XI) → those show **no Research box**;
    exactly **20** tier-X tanks carry a single 325000-XP successor edge and nothing else;
    **zero-cost** unlock entries exist ONLY in the **6** Steel Hunter `_SH` types. Answers "why does
    this vehicle report 0 / no Research category" without opening the client.
- `post_progression_read` / `skill_tree_read` ← `veh.postProgression` (`isVehSkillTree`,
  `iterOrderedSteps`), effect text off `action._descriptor` / skill-tree `tooltips.description.dyn`.
  - **Which VARIANT of a choice level the player bought** ← `MultiModsItem.isPurchased()` +
    `getPurchasedIdx()` (0-based index into `.modifications`), declared in
    `gui/veh_post_progression/models/modifications.py:185-231` (siblings: `getPurchasedID()`,
    `getPurchasedModification()`). The reader already holds that item as `step.action` while
    collecting `pairs_by_parent`, so this is a read off an object in hand, not a new lookup.
    Consumed only by the COMPLETE per-level breakdown (`ProgressionStep.selected_idx`, -1 = none);
    fully guarded — a failure degrades to the generic base-mod name. **Verified live** on
    T110E5 (Tier X): 5 `MultiModsItem` steps, all purchased, `getPurchasedIdx()` returned real
    indices incl. three index-0 cases, correct variant name rendered each time. Consumer must
    range-check (`0 <= idx < len(opts)`), never truthy-test — index 0 is valid AND falsy.
    Tier-XI skill-tree vehicles produce ZERO `MultiModsItem` steps, so this path is reachable
    only on non-tier-XI elite vehicles.
- `prestige_read` ← `gui.prestige.prestige_helpers` (`hasVehiclePrestige`, `getVehiclePrestige`,
  `prestigePointsToXP`, `mapGradeIDToUI`) + `ILobbyContext…prestigeConfig`.
- `pricing_read.read_purchase_price` ← `items.getItemByCD(int_cd).buyPrices…getSignValue(CREDITS)`.
- `_read_common.vehicle_xp_stats` / `avg_battle_xp` / `account_avg_battle_xp` /
  `active_reserve_mult` / `daily_double_factor` ← dossier `getRandomStats().getAvgXP()`,
  `IBoostersController.getExpirableBoosters()`, `items.stats.multipliedVehicles` (the enriched
  "≈ M–N battles" estimate).

## Writes (`adapter/actions.py`)
- `_do_research` ← `items_actions.factory.doAction(UNLOCK_ITEM, intCD, UnlockProps(...))` (mirrors
  the discounted `xpCost`/`discount`/`xpFullCost`).
- Field-mod step ← `factory.doAction(PURCHASE_POST_PROGRESSION_STEPS, veh, [stepID])`.
- Skill tree ← `showVehicleHubVehSkillTree(veh.intCD)`. Fallbacks: `showResearchView`,
  `showVehPostProgressionView`. Every path falls back to a native screen rather than raising into JS.
