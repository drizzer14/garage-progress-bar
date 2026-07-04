# WoT / BigWorld game API used by the mod

Concrete game symbols the mod depends on, and where they live in the EU 2.3 decompiled
client. Game symbols are confined to the adapter layer — `engine_adapter.py` (read
orchestrator) plus the per-subsystem readers (`tech_read.py`,
`post_progression_read.py`, `skill_tree_read.py`, `prestige_read.py`,
`pricing_read.py`, `_read_common.py`), `actions.py` (writes), `i18n.py` (resource
strings) — and `bridge/` (Wulf, ModsSettingsAPI); the domain layer never imports
these. All reads are wrapped in try/except so an API drift degrades a single
category to a safe default instead of blanking the bar.

To inspect any of these live, use the **wgmod-debug-repl** skill. To re-locate a symbol
after a client patch, clone the decompiled source for the matching region/branch (see
that skill).

## Entry / mount (`gui/mods/mod_wgmod.py`, `bridge/gameface_bridge.py`)
- `gui.impl.lobby.hangar.presenters.hangar_vehicle_params_presenter.HangarVehicleParamsPresenter`
  — patched sub-view; `_onLoading` is the mount hook, `getViewModel()` the host model.
- `openwg_gameface.gf_mod_inject(host_vm, name, styles=[…], modules=[…])` — load our
  CSS/JS into the hangar document (hard dependency; import raises if OpenWG absent).
- `frameworks.wulf.ViewModel`, `frameworks.wulf.Array` — base classes for
  `ResearchVM`/`TickVM`/`UpgradeVM` (defined in `bridge/view_models.py`);
  `_addNumber/String/Bool/Array/ViewModelProperty`,
  `_addCommand`, `transaction()`, `addViewModel`, `invalidate`.
- `BigWorld.callback(0.0, fn)` — defer the coalesced refresh to the next tick (main thread).

## Listeners (`bridge/gameface_bridge.py`)
- `CurrentVehicle.g_currentVehicle.onChanged` — vehicle-selection event (list-based;
  re-arm every mount).
- `skeletons.gui.game_control.ILoadoutController` (via `helpers.dependency.instance`) —
  `.interactor` (None ⇔ plain garage), `.onInteractorUpdated` event.
- `skeletons.gui.shared.IItemsCache` — `.onSyncCompleted(updateReason, invalidItems)`
  event (long-lived singleton); reason strings `shop`/`clan` are ignored, all else
  refreshes (fail-open).
- **Lobby view detection** (hide the bar outside the plain garage):
  `gui.Scaleform.lobby_entry.getLobbyStateMachine()` → the lobby state machine (or
  `None`). `.visibleState.getStateID()` is the deepest entered leaf's hierarchical
  `parent/child` path. The plain garage is the DefaultHangarState, ending in
  **`hangar/{root}`** (verified live: `subScope/subLayer/hangar/{root}`). `{root}` is
  defined exactly once client-wide (the sole default child of the hangar state,
  `gui/impl/lobby/hangar/base/proto_states.py:335`), so it uniquely IDs the plain garage.
  NB the `allVehicles` leaf (`_AllVehiclesStatePrototype`, title "allVehicles") is the
  separate full-screen All-Vehicles BROWSER, NOT the plain garage. Playlists leaf is
  `editVehiclePlaylists`; loadout overlays are leaves under `loadout/*`.
  `.onVisibleRouteChanged` is the change Event (subscribe like `.onInteractorUpdated`;
  re-arm each mount). The bar's garage check is FAIL-CLOSED (unreadable → hide).
- **Color-blind toggle**: `skeletons.account_helpers.settings_core.ISettingsCore`
  (via `dependency.instance`) — `.getSetting(GRAPHICS.COLOR_BLIND)`
  (`account_helpers.settings_core.settings_constants.GRAPHICS`) is the read
  (`engine_adapter.is_color_blind()`); `.onSettingsChanged(diff)` is the listener
  (refresh only when `GRAPHICS.COLOR_BLIND` is in the diff; fail-open).

## Reads (`adapter/engine_adapter.py` + the per-subsystem `*_read.py` readers)
- `CurrentVehicle.g_currentVehicle` — `.isPresent()`, `.item` (the selected vehicle).
- Vehicle item: `.level`, `.isElite`, `.xp`, `.type` (class id), `.intCD`,
  `.getUnlocksDescrs()` → rows `(unlockIdx, xpCost, intCD, prereqs)`,
  `.postProgression` → `.isVehSkillTree()`, `.iterOrderedSteps()` (a DAG — DEDUPE by
  stepID; visited once per parent edge).
- `helpers.dependency.instance(IItemsCache)` → `stats.freeXP`, `stats.unlocks` (set).
- **Avg combat XP/battle** (`_read_common.vehicle_xp_stats` / `avg_battle_xp`, for the
  tooltip "≈ M–N battles" estimate): `items.getVehicleDossier(intCD)` → a `VehicleDossier`
  (`gui/shared/gui_items/dossier`, a `VehicleDossierStats`); `.getRandomStats()` →
  `RandomStatsBlock`; `.getAvgXP()` = `getXP()/getBattlesCount()` and returns **None**
  for 0 battles (`dossier/stats.py` `_getAvgValue`), so coerce falsy → 0 (never ÷0).
  `.getBattlesCount()` on the same block gives the sample size (no `getMaxXP()` — it does
  NOT exist on `RandomStatsBlock`, so the estimate's range is bonus-driven, not variance).
- **Enriched "battles remaining" estimate reads** (all guarded, verified live EU 2.3):
  - **Account-wide avg XP** (`account_avg_battle_xp`, fallback divisor for an under-sampled
    tank): `items.getAccountDossier()` → `AccountDossier`; `.getRandomStats()` →
    `AccountRandomStatsBlock`; `.getAvgXP()` (None → 0). NB `items.stats.accountDossier`
    is a raw string blob, NOT this object — use `items.getAccountDossier()`.
  - **Active personal-reserve XP multiplier** (`active_reserve_mult`, int % ×100):
    `dependency.instance(skeletons.gui.game_control.IBoostersController).getExpirableBoosters()`
    → `{goodieID: Booster}` (all OWNED expirable boosters, active or not). A `Booster` is
    currently RUNNING iff `getUsageLeftTime() > 0`; `.boosterGuiType` is a string
    (`'booster_xp'` = vehicle combat XP — the only kind that grows research XP;
    `'booster_free_xp_and_crew_xp'`, `'booster_credits'`, … don't); `.effectValue` is the
    percent bonus (e.g. `100` = +100%, `300` = +300%). Reserves of one resource don't
    stack in-game. (Boosters are NOT in `items.goodies.goodies` — those are `GoodieVariable`.)
  - **First-win-of-day factor** (`daily_double_factor`, int % ×100): the GUI item's
    `veh.dailyXPFactor` is a STATIC per-type config (always 2, set once in `Vehicle.__init__`,
    never reflects use) — so availability comes from `items.stats.multipliedVehicles`, the
    set of vehicle intCDs that HAVE ALREADY taken today's double (verified via
    `carousel_data_provider.Vehicle.__init__`: factor applies when `intCD **not in**
    multipliedVehicles`). Full rule mirrors the carousel: factor = `items.shop.dailyXPFactor`
    (normally 2) when `shop.winXPFactorMode == constants.WIN_XP_FACTOR_MODE.ALWAYS` (==1;
    `DAILY`==0) OR (`intCD not in multipliedVehicles` AND not `veh.isOnlyForEventBattles`),
    else 1.
- `items.getTypeOfCompactDescr(intCD)` + `gui.shared.gui_items.GUI_ITEM_TYPE.VEHICLE` —
  distinguish a next-vehicle unlock from a module unlock.
- Localization: `action.getLocNameRes()` returns a Wulf `DynAccessor` — CALL it for the
  res id, then `gui.impl.backport.text(res_id)`. Skill-tree names:
  `R.strings.veh_skill_tree.tooltips.title.dyn(<imageName>)` → `backport.text`.
- Post-progression **effect/bonus text** (field mods + skill-tree perks; verified
  EU 2.3 on Strv 103B + Strv 107-12): the step's `action` has NO `description`/
  `getDescriptionRes` — `getTooltip()` returns a `PostProgressionActionTooltip` ENUM
  (type selector, not text). The numeric effect lives on `action._descriptor`:
  - `SimpleModItem._descriptor` is a `Modification` with `.kpi` (list of `KPI`) and
    `.modifiers`. Each `KPI` has `.getDescriptionR()`/`.getLongDescriptionR()`
    (DynAccessor → `backport.text` → a phrase like `"to concealment after firing"`),
    `.type` (`'mul'` observed), `.value` (e.g. `1.10`, `0.99`), `.isPositive`,
    `.isDebuff`. Effect string = sign + `(value-1)*100` rounded + `"% "` + desc →
    `"+10% to concealment after firing"`.
  - `FeatureModItem` / `RoleSlotModItem._descriptor` is a `ProgressionFeature`
    (`name`, `locName`, `tooltipSection`, `imgName`) with NO `kpi` — only a richer
    descriptive name via `action.getLocSplitNameRes()` (e.g. "Alternate
    Configuration: Essentials Loadout"). No numeric effect.
  - Skill-tree nodes describe themselves in a localized SENTENCE template at
    `R.strings.veh_skill_tree.tooltips.description.dyn(<imageName>)` (imageName =
    `action.getImageName()`), e.g. "Reduces gun reload time by {value}% in Pillbox
    mode." Fill `{value}` with the node's KPI magnitude (`|kpi.value-1|*100`) and strip
    `{colorTagOpen}`/`{colorTagClose}`. This is the RIGHT effect source for skill-tree
    nodes incl. the **major/final** "mechanic" perks (whose KPI is the unlabeled generic
    `name='value'` with EMPTY `getDescriptionR()` — so the KPI-phrase path gives nothing).
    The matching title is `...tooltips.title.dyn(imageName)` (the action's own
    `getLocNameRes()` is the generic "Modification"). Returns "" for features/role-slots
    (no entry).
  - No ready KPI→text formatter at `gui.impl.lobby.common.kpi_helpers` /
    `gui.shared.formatters.kpi` (don't exist) — format the magnitude ourselves.
- Done-tick credits price (`pricing_read.read_purchase_price`):
  `items_cache.items.getItemByCD(int_cd)` → skip if `.isInInventory` /
  `.inventoryCount > 0` (owned → no footer), else
  `item.buyPrices.itemPrice.price.getSignValue(Currency.CREDITS)`
  (`gui.shared.money.Currency`), falling back to `item.buyPrice.getSignValue(...)`.
  Field-mod selection levels: the child `MultiModsItem` whose
  `getParentStepID() == step_id` → first variant's `mod.getPrice().credits`.
- Prestige (`gui.prestige.prestige_helpers as ph`):
  `ph.hasVehiclePrestige(cd, checkElite=True)` (gate),
  `ph.getVehiclePrestige(cd)` → `.currentLevel`, `.remainingPoints`,
  `ph.prestigePointsToXP(points)`, `ph.mapGradeIDToUI(prestigeMarkID)` → (family enum, sub).
  Per-level XP table comes from
  `dependency.instance(ILobbyContext).getServerSettings().prestigeConfig`.

## Writes (`adapter/actions.py`) — verified via the dev REPL
- **Tech-tree research:** `gui.shared.gui_items.items_actions.factory.doAction(
  factory.UNLOCK_ITEM, intCD, props)` where `props = UnlockProps(parentID, unlockIdx,
  xpCost, set(required), discount, xpFullCost)` from
  `gui.Scaleform.daapi.view.lobby.techtree.settings.UnlockProps`. Build the row from
  `veh.getUnlocksDescrs()`. `UnlockProps._fields =
  ('parentID','unlockIdx','xpCost','required','discount','xpFullCost')` (namedtuple);
  `xpCost` is the EFFECTIVE (post-discount) cost, `discount` is the percent, `xpFullCost`
  the raw cost. Modules always pass `discount=0`, `xpCost==xpFullCost`.
- **Blueprint fragment discount (next-vehicle unlocks only):** the requester is
  `cache.items.blueprints` (`BlueprintsRequester`, no `IBlueprintsRequester` skeleton).
  Mirror the game's OWN tech-tree cost path (`techtree_dp.getBlueprintDiscountData`):
  `getBlueprintDiscount(vehicleCD, vLevel) -> discountPct` then
  `calculateCost(xpFullCost, discountPct) -> effectiveCost` (== full − savings).
  `getBlueprintDiscount` reflects the fragments the player CURRENTLY holds — 0 when
  none are held / the vehicle is already unlocked, scaling with the held count, capped
  at 100. `vLevel` is `item.level` (a vehicle item's tier). Applies to VEHICLE unlocks
  only — WG's validator rejects a module unlocked at a differing cost, so modules stay
  on the raw cost. **Do NOT use `getFragmentDiscountAndCost`** — it delegates to
  `getRequiredCountAndDiscount`, a conversion-dialog helper that returns the flat
  per-fragment CONFIG discount regardless of fragments held (a phantom discount with
  zero fragments, not scaled by the held count). Using it was the discount regression.
- **Field-mod step:** `factory.doAction(factory.PURCHASE_POST_PROGRESSION_STEPS, veh,
  [stepID])` (same items-actions factory as tech-tree UNLOCK_ITEM). This runs WG's
  `AsyncGUIItemAction` confirm→research chain: `_confirm()` shows the dialog,
  `_action()` runs the purchase processor that actually researches. Do NOT call
  `event_dispatcher.showPostProgressionResearchDialog(veh, [stepID])` directly — it's a
  `@wg_async` coroutine that only SHOWS the confirm dialog and returns the choice
  (`AsyncReturn`); it never researches (the confirm button then does nothing).
- **Tier-XI skill tree:** `gui.shared.event_dispatcher.showVehicleHubVehSkillTree(
  veh.intCD)` — the current Upgrades screen (the older `showVehPostProgressionView` 404s
  for skill-tree vehicles).
- **Fallback screens:** `showResearchView(intCD)`, `showVehPostProgressionView(intCD)`.
  Every write path falls back to one of these rather than raising into JS.
