# -*- coding: utf-8 -*-
"""PC-only write-side: perform the research / field-mod unlocks the user clicks.

Counterpart to engine_adapter.py, which only READS. Each public function resolves
the currently-selected vehicle and runs WG's own research/unlock flow, then the
game's onSyncCompleted (already wired in the bridge) refreshes the bar. Everything
is guarded so a failure degrades to opening WG's native screen for that item --
never a raise back into the JS bridge, never a silent spend.

Symbols verified live in the EU 2.3 client via the dev REPL (the game's own
context-menu "Research" handler uses exactly this path):

  * Tech-tree research: ItemsActionsFactory (the module
    `gui.shared.gui_items.items_actions.factory`) .doAction(UNLOCK_ITEM, itemCD,
    UnlockProps). UnlockProps (from techtree.settings) is built from the vehicle's
    own unlock-graph row: (unlockIdx, xpCost, itemCD, required).
  * Field-mod step: the items-actions factory PURCHASE_POST_PROGRESSION_STEPS
    action -- WG's confirm-then-research flow (see unlock_field_mod). NOT
    event_dispatcher.showPostProgressionResearchDialog, which only shows the
    confirm dialog and returns the choice; it never researches.
  * Screens (tier-XI final tick, choice-pair levels, and every fallback):
    event_dispatcher.showVehPostProgressionView / showResearchView.
"""
from CurrentVehicle import g_currentVehicle

from wgmod_research._compat import LOG_CURRENT_EXCEPTION, LOG_NOTE


# --- public API (called by the bridge command handlers) ----------------------

def research_unlock(int_cd):
    """Research/unlock the tech-tree item `int_cd` for the selected vehicle."""
    veh = _current_vehicle()
    if veh is None:
        return
    try:
        row = _find_unlock_row(veh, int_cd)
        if row is None:
            LOG_NOTE("[wgmod] research_unlock: %s not an available unlock" % int_cd)
            _open_research_screen(veh)
            return
        if not _do_research(veh, int_cd, row):
            _open_research_screen(veh)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        _open_research_screen(veh)


def unlock_field_mod(step_id):
    """Research the post-progression step `step_id` for the selected vehicle, via
    WG's own confirm-and-research flow.

    NB: this must go through the items-actions FACTORY, not
    `showPostProgressionResearchDialog` directly. That event_dispatcher helper is a
    `@wg_async` coroutine that only SHOWS the confirm dialog and returns the user's
    choice (`raise AsyncReturn(result)`) -- it does not research anything. WG's own
    post-progression screen wires it up via the PURCHASE_POST_PROGRESSION_STEPS
    action (AsyncGUIItemAction): its `_confirm()` shows that same dialog and, only if
    confirmed, its `_action()` runs the purchase processor that actually researches
    the step. `factory.doAction` runs that confirm->research chain -- the exact
    counterpart to the tech-tree UNLOCK_ITEM path in `_do_research`. Verified against
    the EU 2.3 decompiled client (post_progression_cfg_component.__onPurchaseClick)."""
    veh = _current_vehicle()
    if veh is None:
        return
    try:
        import gui.shared.gui_items.items_actions.factory as actions_factory
        actions_factory.doAction(
            actions_factory.PURCHASE_POST_PROGRESSION_STEPS, veh, [int(step_id)])
    except Exception:
        LOG_CURRENT_EXCEPTION()
        _open_field_mods_screen(veh)


def buy_and_mount(int_cd):
    """Buy the researched module `int_cd` and install it on the selected vehicle in one
    action -- WG's own "Buy and equip" path. Invoked by a click on a "done" tech-tree
    MODULE marker.

    Goes through the items-actions FACTORY, like the tech-tree unlock (UNLOCK_ITEM) and
    field-mod (PURCHASE_POST_PROGRESSION_STEPS) paths. `doAction` is `@adisp_process`: it
    runs WG's own credits-exchange / confirm dialogs and never raises into the caller, so
    the short-credits and cancel flows are handled by the game. On any failure we fall
    back to opening the research screen -- never a raise back into the JS bridge.

    NB: use BUY_AND_INSTALL_AND_SELL_ITEM. The bare BUY_AND_INSTALL_ITEM constant
    ('buyAndInstallItemAction') is NOT in the factory's _ACTION_MAP. Analog:
    research_cm_handlers.buyModule (EU 2.3 decompiled client)."""
    veh = _current_vehicle()
    if veh is None:
        return
    try:
        import gui.shared.gui_items.items_actions.factory as actions_factory
        actions_factory.doAction(
            actions_factory.BUY_AND_INSTALL_AND_SELL_ITEM, int(int_cd), veh.intCD)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        _open_research_screen(veh)


def open_skill_tree():
    """Open WG's current Upgrades screen for the tier-XI final tick. Uses the
    vehicle-hub skill-tree route -- the older showVehPostProgressionView loads a
    legacy view that 404s (verified). Falls back to the research view."""
    veh = _current_vehicle()
    if veh is None:
        return
    try:
        from gui.shared.event_dispatcher import showVehicleHubVehSkillTree
        showVehicleHubVehSkillTree(veh.intCD)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        _open_research_screen(veh)


def open_research():
    """Open WG's research (tech-tree) screen for the selected vehicle. Invoked by a
    click on a "done" tech-tree marker -- navigation only, never a re-research."""
    veh = _current_vehicle()
    if veh is None:
        return
    _open_research_screen(veh)


def open_field_mods():
    """Open WG's Field Modifications (post-progression) screen for the selected
    vehicle. Invoked by a click on a "done" field-mod marker -- navigation only."""
    veh = _current_vehicle()
    if veh is None:
        return
    _open_field_mods_screen(veh)


# --- tech-tree unlock --------------------------------------------------------

def _do_research(veh, int_cd, row):
    """Run WG's tech-tree unlock action for `int_cd`. Returns True if it started,
    False (-> caller opens the research screen) if a needed symbol was unreachable.

    `row` is the vehicle's own unlock-graph tuple (unlockIdx, xpCost, itemCD,
    required) -- the same shape engine_adapter reads."""
    try:
        from gui.Scaleform.daapi.view.lobby.techtree.settings import UnlockProps
        import gui.shared.gui_items.items_actions.factory as actions_factory
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return False
    try:
        # ALL tech-tree unlocks (vehicles AND modules): let the GAME build the
        # UnlockProps, exactly as its own research/context-menu handlers do, instead
        # of hand-building from the selected vehicle's edge. See _native_unlock_props.
        # This keeps the bar's confirm dialog + the actual unlock byte-identical to
        # native -- crucially for a convergent (multi-parent) vehicle node whose
        # per-parent edge costs differ (SU-152: 93000 from KV-2 vs 31500 from SU-100),
        # where the selected-edge cost was higher than native AND would overcharge.
        props = _native_unlock_props(veh, int_cd)
        if props is None:
            # Safety fallback only (game data provider unreachable, or a not-currently-
            # available item): build props from the selected vehicle's own unlock-graph
            # row. Modules keep the raw cost (discount 0) -- WG's validator rejects a
            # module unlocked at a differing cost; a fallen-back vehicle still gets the
            # held-fragment discount.
            unlock_idx, xp_cost, _item_cd, required = row[0], row[1], row[2], row[3]
            xp_full = int(xp_cost)
            xp_eff, discount = xp_full, 0
            if _is_vehicle_cd(int_cd):
                from wgmod_research.adapter._read_common import blueprint_effective_cost
                xp_eff, discount = blueprint_effective_cost(int_cd, xp_full)
            props = UnlockProps(veh.intCD, int(unlock_idx), int(xp_eff),
                                set(required), int(discount), xp_full)
        actions_factory.doAction(actions_factory.UNLOCK_ITEM, int_cd, props)
        return True
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return False


def _native_unlock_props(veh, int_cd):
    """The game's OWN UnlockProps for unlocking `int_cd` from `veh`, so the bar unlocks
    at exactly the game's price/parent. Returns None on any failure or if the item isn't
    a currently-valid unlock (DEFAULT_UNLOCK_PROPS has parentID 0), so the caller falls
    back to the selected-vehicle edge.

      * VEHICLE -> g_techTreeDP.getUnlockProps(cd, level): the CHEAPEST AVAILABLE parent
        + blueprint-fragment discount, matching research_cm_handlers.unlockVehicle. This
        is what stops a convergent node (SU-152) being mispriced to the selected edge.
      * MODULE  -> g_techTreeDP.getAllPossibleItems2Unlock(veh, unlocks)[cd]: the game's
        own per-item props. getUnlockProps is vehicle-tree-only (returns the default for
        a module). A module has a single parent (this vehicle) and no discount, so its
        props equal the hand-built ones -- verified live, 0 mismatches -- but sourcing
        them from the game keeps every item on one authoritative path."""
    try:
        from gui.Scaleform.daapi.view.lobby.techtree.techtree_dp import g_techTreeDP
        from wgmod_research.adapter._read_common import _items_cache
        cache = _items_cache()
        if _is_vehicle_cd(int_cd):
            level = getattr(cache.items.getItemByCD(int_cd), "level", 0)
            props = g_techTreeDP.getUnlockProps(int_cd, level)
        else:
            unlocks = cache.items.stats.unlocks
            props = g_techTreeDP.getAllPossibleItems2Unlock(veh, unlocks).get(int_cd)
        if props is None or not getattr(props, "parentID", 0):
            return None
        return props
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return None


def _is_vehicle_cd(int_cd):
    """True if `int_cd` is a vehicle compact descriptor (vs a module). Guarded ->
    False on any failure, so research falls back to the raw-cost module path."""
    try:
        from items import getTypeOfCompactDescr
        from gui.shared.gui_items import GUI_ITEM_TYPE
        return getTypeOfCompactDescr(int_cd) == GUI_ITEM_TYPE.VEHICLE
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return False


def _find_unlock_row(veh, int_cd):
    """The (unlockIdx, xpCost, itemCD, required) graph row for `int_cd`, or None
    if it isn't a currently-available unlock for this vehicle."""
    try:
        for row in veh.getUnlocksDescrs():
            if row[2] == int_cd:
                return row
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return None


# --- vehicle resolution + native-screen fallbacks ----------------------------

def _current_vehicle():
    try:
        if not g_currentVehicle.isPresent():
            return None
        return g_currentVehicle.item
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return None


def _open_research_screen(veh):
    """Open WG's research (tech-tree) screen for the vehicle."""
    try:
        from gui.shared.event_dispatcher import showResearchView
        showResearchView(veh.intCD)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _open_field_mods_screen(veh):
    """Open WG's post-progression / tier-XI skill-tree screen, falling back to the
    research view if the post-progression view is unavailable."""
    try:
        from gui.shared.event_dispatcher import showVehPostProgressionView
        showVehPostProgressionView(veh.intCD)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        try:
            from gui.shared.event_dispatcher import showResearchView
            showResearchView(veh.intCD)
        except Exception:
            LOG_CURRENT_EXCEPTION()
