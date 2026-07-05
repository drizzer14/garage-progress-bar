# WoT / BigWorld game API — this mod's usage map

The **full generic symbol catalogue** (what each WoT/BigWorld/Wulf/OpenWG symbol is, its exact
call/return shape, where it lives in the decompiled client, and the gotchas) is in the
**wotmod-architecture** harness skill's `references/game-api.md`. Read that first for any symbol.

This file records only *which module in THIS mod uses which symbol* — the mapping the harness
catalogue is deliberately generic about. All reads are wrapped in try/except so an API drift
degrades one category to a safe default instead of blanking the bar. To inspect anything live,
use the **wgmod-debug-repl** skill.

## Entry / mount / listeners (`gui/mods/mod_wgmod.py`, `bridge/gameface_bridge.py`)
- Patched sub-view: `HangarVehicleParamsPresenter` (`_onLoading` mount hook, `getViewModel()` host).
- Inject: `openwg_gameface.gf_mod_inject`. VMs: `frameworks.wulf.ViewModel`/`Array`. Defer:
  `BigWorld.callback(0.0, …)`.
- Five re-armed listeners (`_LISTENERS`): `CurrentVehicle.g_currentVehicle.onChanged` (vehicle);
  `ILoadoutController.onInteractorUpdated` (loadout overlay hide); lobby
  `getLobbyStateMachine().onVisibleRouteChanged` → `visibleState.getStateID()` == `hangar/{root}`
  (garage allowlist, fail-closed); `IItemsCache.onSyncCompleted` (stats, skip `shop`/`clan`);
  `ISettingsCore.onSettingsChanged` filtered to `GRAPHICS.COLOR_BLIND` (colorblind).

## Reads (`adapter/*_read.py`, `_read_common.py`)
- `engine_adapter.is_color_blind()` ← `ISettingsCore.getSetting(GRAPHICS.COLOR_BLIND)`.
- `tech_read` ← `veh.getUnlocksDescrs()`, `items.getTypeOfCompactDescr` + `GUI_ITEM_TYPE.VEHICLE`,
  `_read_common.blueprint_effective_cost` (blueprint discount — see catalogue's WRITE section).
- `post_progression_read` / `skill_tree_read` ← `veh.postProgression` (`isVehSkillTree`,
  `iterOrderedSteps`), effect text off `action._descriptor` / skill-tree `tooltips.description.dyn`.
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
