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
        unlock_idx, xp_cost, _item_cd, required = row[0], row[1], row[2], row[3]
        # UnlockProps(parentID, unlockIdx, xpCost, required, discount, xpFullCost).
        props = UnlockProps(veh.intCD, int(unlock_idx), int(xp_cost),
                            set(required), 0, int(xp_cost))
        actions_factory.doAction(actions_factory.UNLOCK_ITEM, int_cd, props)
        return True
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
