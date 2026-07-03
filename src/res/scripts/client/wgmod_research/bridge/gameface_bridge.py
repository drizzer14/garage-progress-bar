# -*- coding: utf-8 -*-
"""Bridge: attach our Gameface widget to a hangar sub-view and push the model.

OpenWG's JS injector (gui/gameface/js/index.js) scans hangar SUB-views for a
`ModInjectModel` and loads the listed assets into the hangar document. So we
inject onto a sub-view's ViewModel (HangarVehicleParamsPresenter) and also hang
our own data model on it (property `wgResearch`), which the widget JS reads via
ModelObserver("WGModResearch").

ViewModel API (string/number/array, transaction, addViewModel, _addViewModelProperty)
was verified live in the EU 2.3 client.
"""
import json

import BigWorld
from frameworks.wulf import ViewModel, Array
from debug_utils import LOG_CURRENT_EXCEPTION, LOG_NOTE
from CurrentVehicle import g_currentVehicle
from helpers import dependency
from skeletons.gui.game_control import ILoadoutController
from skeletons.gui.shared import IItemsCache

from wgmod_research.adapter import engine_adapter
from wgmod_research.adapter import actions
from wgmod_research.adapter import i18n
from wgmod_research.adapter import recent
from wgmod_research.domain.builder import build_model, bar_visible
from wgmod_research.bridge import mod_settings
import openwg_gameface

WIDGET_NAME = "WGModResearch"
DATA_PROP = "wgResearch"
COUI = "coui://gui/gameface/mods/14th_ua/WGModResearch"

# (host_vm, rvm) for the currently-mounted widget. Importable so the entry point
# and the dev REPL can drive refreshes without poking module-private state.
_active = None

# Our onChanged handler. g_currentVehicle.onChanged is a list-based Event that
# stores STRONG refs to its delegates -- but WoT tears down and rebuilds the
# hangar space on battle entry/exit, repopulating that list with WG's own
# presenters while dropping ours. So subscribing once is not enough; we must
# re-arm on every mount. We keep a module-global ref to the same function object
# so the membership check below stays stable across re-arms.
_listener = None

# Our handler for tank-setup (loadout) open/close. Same strong-ref + self-healing
# rationale as the vehicle listener above.
_loadout_listener = None

# Our handler for lobby view changes (garage <-> playlists / other views). Same
# strong-ref + self-healing rationale; lets us hide the bar when the vehicle-params
# sub-view stays mounted on a non-garage view (e.g. the playlists screen).
_lobby_state_listener = None

# Our handler for items-cache syncs (free-XP conversion, research/field-mod
# purchases, post-battle XP, prestige changes -- everything that mutates the XP
# state without a vehicle re-selection). Same strong-ref rationale as above. The
# items cache is a long-lived DI singleton (its event list is NOT torn down on
# battle exit), so re-arming on mount is unnecessary but harmless -- we keep the
# idempotent membership check for symmetry and hot-reload safety.
_stats_listener = None

# Our handler for the player toggling WoT's color-blind mode. settingsCore is a
# long-lived DI singleton (event list not torn down on battle exit), so like the
# stats listener re-arming on mount is unnecessary but harmless; kept for symmetry
# and hot-reload safety.
_colorblind_listener = None

# Set while a coalesced refresh is already queued for the next tick, so a burst of
# onSyncCompleted fires (one server action often triggers several) collapses to a
# single deferred refresh(). See _schedule_refresh.
_refresh_pending = False

# Items-cache sync reasons the bar can safely IGNORE -- pure account/economy noise
# that never changes the XP state, fill, or ticks. Everything else (inventory,
# vehicle, stats, init, and any unknown/future reason) refreshes the bar. Matched
# as strings and FAIL-OPEN, so we couple to no fragile reason-constant imports and
# only ever skip the clearly-irrelevant syncs.
_IGNORED_SYNC_REASONS = frozenset(("shop", "clan"))


def _on_vehicle_changed(*args, **kwargs):
    try:
        ok = refresh()
        LOG_NOTE("[wgmod] onChanged -> refresh ok=%s" % ok)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_interactor_updated(*args, **kwargs):
    # The loadout interactor was set (tank-setup / ammo overlay opened) or cleared
    # (back to the plain garage). Re-push so the bar hides / shows accordingly.
    try:
        refresh()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_lobby_state_changed(*args, **kwargs):
    # The visible lobby view changed (garage <-> playlists / other views). A view
    # change does not necessarily re-mount the sub-view, so re-push here so the bar
    # hides when we leave the plain garage and shows again when we return.
    try:
        refresh()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_settings_changed(diff):
    # settingsCore.onSettingsChanged(diff): a dict of the settings that changed. Only
    # re-push when the color-blind flag is among them, so we don't refresh on every
    # unrelated settings tweak. Guarded and fail-open (refresh if the diff is
    # unreadable) so a settings-API shape change can't silently freeze the palette.
    try:
        from account_helpers.settings_core.settings_constants import GRAPHICS
        if diff is None or GRAPHICS.COLOR_BLIND in diff:
            refresh()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _reason_affects_bar(reason):
    """True if this items-cache sync reason can change what the bar shows. Refreshes
    for everything except the known-irrelevant reasons (_IGNORED_SYNC_REASONS),
    FAIL-OPEN on unknown/empty so a new or unrecognized reason still refreshes."""
    try:
        if not reason:
            return True
        return str(reason) not in _IGNORED_SYNC_REASONS
    except Exception:
        return True


def _on_sync_completed(*args, **kwargs):
    # IItemsCache.onSyncCompleted(updateReason, invalidItems). Use *args so any
    # live-arity drift can't raise. Skip clearly-irrelevant reasons, then coalesce.
    try:
        reason = args[0] if args else ""
        if not _reason_affects_bar(reason):
            return
        _schedule_refresh()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _schedule_refresh():
    """Coalesce a refresh onto the next tick. A single server action often fires
    onSyncCompleted several times; the pending flag collapses them to one push.
    Deferring also fixes ordering: CurrentVehicle rebuilds g_currentVehicle.item
    in its OWN onSyncCompleted handler, so reading next tick guarantees veh.xp is
    fresh (not one event behind freeXP). BigWorld.callback runs on the main thread,
    so the push transaction is safe -- never use a timer thread here."""
    global _refresh_pending
    if _refresh_pending:
        return
    _refresh_pending = True
    try:
        BigWorld.callback(0.0, _do_scheduled_refresh)
    except Exception:
        # Couldn't schedule -> clear the flag and refresh inline as a fallback.
        _refresh_pending = False
        LOG_CURRENT_EXCEPTION()
        try:
            refresh()
        except Exception:
            LOG_CURRENT_EXCEPTION()


def _do_scheduled_refresh():
    global _refresh_pending
    _refresh_pending = False
    try:
        refresh()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _bar_visible():
    """True only in the plain garage. The tank-setup overlays (shells/ammo,
    consumables, equipment, optional devices) keep the vehicle-params panel mounted
    to show stat changes, so the bar must be hidden explicitly while one is open.
    A live loadout interactor is exactly that 'a setup overlay is open' signal.
    Guarded -> True (fail open: show the bar) if the controller is unreadable."""
    try:
        return dependency.instance(ILoadoutController).interactor is None
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return True


def _in_garage():
    """True only when the plain garage view is the visible lobby state. The
    vehicle-params sub-view we inject into stays mounted on other lobby views
    (notably the playlists / battle-type selection screen), so the bar must be
    hidden explicitly there. The lobby state machine's visible leaf state carries
    a hierarchical id; the plain garage is the DefaultHangarState, whose id ends in
    'hangar/{root}' (verified live: 'subScope/subLayer/hangar/{root}'). '{root}' is
    defined exactly once in the client -- the sole default child of the hangar
    state -- so this uniquely identifies the plain garage and excludes the full
    'All Vehicles' browser ('.../hangar/allVehicles'), the playlists screen
    ('.../editVehiclePlaylists'), and every other view.

    Guarded -> False (FAIL CLOSED: show ONLY in the confirmed garage) if the state
    machine is missing or unreadable. This is the opposite default from
    _bar_visible() by design -- a positive garage confirmation is required."""
    try:
        from gui.Scaleform.lobby_entry import getLobbyStateMachine
        machine = getLobbyStateMachine()
        if machine is None:
            return False
        state = machine.visibleState
        if state is None:
            return False
        state_id = state.getStateID() or ""
        return state_id.endswith("hangar/{root}")
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return False


def install_vehicle_listener():
    """Ensure our handler is subscribed to vehicle-selection changes.

    Self-healing and idempotent: re-adds our handler iff it is not currently in
    g_currentVehicle.onChanged. Safe to call on every hangar mount -- the battle
    exit teardown drops our delegate, and this restores it. We check actual list
    membership rather than a 'did we ever subscribe' flag, which was the bug:
    the flag stayed set while the event had silently lost our handler.
    """
    global _listener
    if _listener is None:
        _listener = _on_vehicle_changed
    try:
        if _listener not in g_currentVehicle.onChanged:
            g_currentVehicle.onChanged += _listener
            LOG_NOTE("[wgmod] vehicle listener (re)armed")
    except Exception:
        LOG_CURRENT_EXCEPTION()


def install_loadout_listener():
    """Ensure our handler is subscribed to loadout interactor changes, so the bar
    hides/shows as the tank-setup (ammo) overlay opens/closes. Self-healing and
    idempotent, same as install_vehicle_listener -- safe to call on every mount."""
    global _loadout_listener
    if _loadout_listener is None:
        _loadout_listener = _on_interactor_updated
    try:
        ctrl = dependency.instance(ILoadoutController)
        if _loadout_listener not in ctrl.onInteractorUpdated:
            ctrl.onInteractorUpdated += _loadout_listener
            LOG_NOTE("[wgmod] loadout listener (re)armed")
    except Exception:
        LOG_CURRENT_EXCEPTION()


def install_lobby_state_listener():
    """Ensure our handler is subscribed to lobby view changes, so the bar hides
    when we leave the plain garage (e.g. the playlists screen) and shows again on
    return. Self-healing and idempotent, same as install_loadout_listener -- safe
    to call on every mount. Guarded: if the state machine isn't available yet the
    subscribe is skipped and retried on the next mount."""
    global _lobby_state_listener
    if _lobby_state_listener is None:
        _lobby_state_listener = _on_lobby_state_changed
    try:
        from gui.Scaleform.lobby_entry import getLobbyStateMachine
        machine = getLobbyStateMachine()
        if machine is not None and _lobby_state_listener not in machine.onVisibleRouteChanged:
            machine.onVisibleRouteChanged += _lobby_state_listener
            LOG_NOTE("[wgmod] lobby state listener (re)armed")
    except Exception:
        LOG_CURRENT_EXCEPTION()


def install_stats_listener():
    """Ensure our handler is subscribed to items-cache syncs, so the bar updates
    when XP state changes without a vehicle re-selection (free-XP conversion,
    research / field-mod purchases, post-battle XP, prestige changes). Self-healing
    and idempotent, same as the other installers -- safe to call on every mount."""
    global _stats_listener
    if _stats_listener is None:
        _stats_listener = _on_sync_completed
    try:
        cache = dependency.instance(IItemsCache)
        if _stats_listener not in cache.onSyncCompleted:
            cache.onSyncCompleted += _stats_listener
            LOG_NOTE("[wgmod] stats listener (re)armed")
    except Exception:
        LOG_CURRENT_EXCEPTION()


def install_colorblind_listener():
    """Ensure our handler is subscribed to settings changes, so the bar re-colors live
    when the player toggles WoT's color-blind mode. Self-healing and idempotent, same
    as the other installers -- safe to call on every mount. Guarded: if settingsCore
    isn't available yet the subscribe is skipped and retried on the next mount."""
    global _colorblind_listener
    if _colorblind_listener is None:
        _colorblind_listener = _on_settings_changed
    try:
        from skeletons.account_helpers.settings_core import ISettingsCore
        core = dependency.instance(ISettingsCore)
        if _colorblind_listener not in core.onSettingsChanged:
            core.onSettingsChanged += _colorblind_listener
            LOG_NOTE("[wgmod] colorblind listener (re)armed")
    except Exception:
        LOG_CURRENT_EXCEPTION()


# --- Reverse channel: handlers for JS click commands -------------------------
# The widget JS invokes the ResearchVM commands when a clickable tick is clicked.
# Each handler reads the tick identity Wulf delivered and delegates to the
# write-side `actions` module (which touches the game's research / unlock APIs).
# After a successful action the game fires onSyncCompleted, which the stats
# listener already turns into a bar refresh -- so handlers do not refresh here.

def _map_get(a, key):
    """Read `key` from a JS-supplied argument that may be a plain dict or a Wulf-wrapped
    map. Returns None if unreadable."""
    if isinstance(a, dict):
        return a.get(key)
    getter = getattr(a, "get", None)
    if callable(getter):
        try:
            return a.get(key)
        except Exception:
            return None
    return None


def _cmd_int_arg(args):
    """Extract the int id a JS command invocation carried. Wulf delivers a single
    MAP argument (the JS side wraps the id as {value: id}); pull our key out of it,
    tolerating a plain dict, a wrapped map, or a bare scalar. 0 = nothing usable."""
    try:
        if not args:
            return 0
        a = args[0]
        if isinstance(a, dict):
            a = a.get("value", a.get("id"))
        else:
            getter = getattr(a, "get", None)
            if callable(getter):
                try:
                    a = a.get("value")
                except Exception:
                    pass
        try:
            return int(a)
        except (TypeError, ValueError):
            return 0
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return 0


def _record_click(int_cd):
    """Capture the item just clicked for the session "done" marker BEFORE the async
    research fires (a researched item vanishes from the snapshot afterwards). Reads a
    fresh snapshot, classifies by what the id actually is, and stashes display data.
    Guarded: a failure here must never block the actual research action."""
    try:
        snap = engine_adapter.build_snapshot()
        if snap is None:
            return
        veh = getattr(snap, "vehicle_int_cd", 0) or 0
        # Tech-tree unlock (global int_cd)?
        for u in (snap.tech_unlocks or []):
            if getattr(u, "int_cd", None) == int_cd and not getattr(u, "researched", False):
                recent.record(recent.TECHTREE, veh, int_cd,
                              name=u.name, icon=u.icon, category=u.kind,
                              kind_label=getattr(u, "kind_label", ""),
                              xp_cost=getattr(u, "xp_cost", 0))
                return
        # Tier-XI upgrade node (frontier chip; per-vehicle step_id)?
        if getattr(snap, "is_skill_tree", False):
            for s in (snap.skilltree_available or []):
                if getattr(s, "step_id", None) == int_cd:
                    recent.record(recent.SKILLTREE, veh, int_cd,
                                  name=s.name, icon=s.icon,
                                  category=getattr(s, "category", ""),
                                  effect=getattr(s, "description", ""),
                                  xp_cost=getattr(s, "xp_cost", 0))
                    return
        # Field-mod step (per-vehicle step_id).
        for s in (snap.field_mod_steps or []):
            if getattr(s, "step_id", None) == int_cd and not getattr(s, "unlocked", False):
                recent.record(recent.FIELDMOD, veh, int_cd,
                              name=s.name, icon=s.icon, category="fieldmod",
                              level=getattr(s, "level", 0),
                              effect=getattr(s, "description", ""),
                              xp_cost=getattr(s, "xp_cost", 0))
                return
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_research_unlock(*args):
    try:
        int_cd = _cmd_int_arg(args)
        LOG_NOTE("[wgmod] researchUnlock intCD=%s" % int_cd)
        if int_cd:
            _record_click(int_cd)
            actions.research_unlock(int_cd)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_unlock_field_mod(*args):
    try:
        step_id = _cmd_int_arg(args)
        LOG_NOTE("[wgmod] unlockFieldMod stepID=%s" % step_id)
        if step_id:
            _record_click(step_id)
            actions.unlock_field_mod(step_id)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_open_skill_tree(*args):
    try:
        LOG_NOTE("[wgmod] openSkillTree")
        actions.open_skill_tree()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_open_research(*args):
    try:
        LOG_NOTE("[wgmod] openResearch")
        actions.open_research()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_open_field_mods(*args):
    try:
        LOG_NOTE("[wgmod] openFieldMods")
        actions.open_field_mods()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _cmd_xy_arg(args):
    """Extract the (x, y) pixel pair a JS `setPosition` invocation carried. Wulf
    delivers a single MAP argument ({x, y}); pull both keys, tolerating a plain dict
    or a wrapped map. Missing/invalid -> 0 (auto)."""
    def as_int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0
    try:
        if not args:
            return 0, 0
        a = args[0]
        return as_int(_map_get(a, "x")), as_int(_map_get(a, "y"))
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return 0, 0


def _on_set_position(*args):
    try:
        x, y = _cmd_xy_arg(args)
        # The widget marks its default-position SEED with seed=1 (measured while the bar
        # sits at its CSS default). That value becomes the reset target; a plain drag omits
        # it. See mod_settings.set_position / _store_default_position.
        is_seed = bool(_map_get(args[0], "seed")) if args else False
        LOG_NOTE("[wgmod] setPosition x=%s y=%s seed=%s" % (x, y, is_seed))
        mod_settings.set_position(x, y, is_default=is_seed)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _connect_commands(rvm):
    """Wire the reverse-channel commands to their handlers. The command objects
    are Wulf events that support +=. A fresh ResearchVM is created per attach(),
    so there's no double-subscription to guard against."""
    try:
        rvm.researchUnlock += _on_research_unlock
        rvm.unlockFieldMod += _on_unlock_field_mod
        rvm.openSkillTree += _on_open_skill_tree
        rvm.openResearch += _on_open_research
        rvm.openFieldMods += _on_open_field_mods
        rvm.setPosition += _on_set_position
    except Exception:
        LOG_CURRENT_EXCEPTION()


class TickVM(ViewModel):
    def __init__(self, properties=16, commands=0):
        super(TickVM, self).__init__(properties=properties, commands=commands)

    def _initialize(self):
        super(TickVM, self)._initialize()
        self._addNumberProperty("position", 0)   # 0
        self._addNumberProperty("xpRequired", 0)  # 1
        self._addStringProperty("category", "")  # 2
        self._addStringProperty("name", "")      # 3
        self._addBoolProperty("affordable", False)  # 4
        self._addBoolProperty("locked", False)   # 5
        self._addStringProperty("icon", "")      # 6 (img:// URL, may be empty)
        self._addNumberProperty("level", 0)      # 7 (field-mod level -> roman)
        self._addStringProperty("options", "")   # 8 (pair variants, \n-joined)
        self._addStringProperty("state", "")     # 9 (elite mark: achieved/next/upcoming)
        self._addNumberProperty("actionId", 0)   # 10 (tech-tree int_cd / field-mod step_id; 0 = not clickable)
        self._addStringProperty("kindLabel", "")  # 11 (tech-tree: "Gun"/"Tier IX" caption)
        self._addStringProperty("prereqNames", "")  # 12 (locked tech-tree: blockers, \n-joined)
        self._addStringProperty("effect", "")     # 13 (field-mod KPI bonus lines, \n-joined)
        self._addStringProperty("optionEffects", "")  # 14 (per-variant buffs, \n-joined, aligned w/ options)
        self._addBoolProperty("done", False)      # 15 (session "done" marker: green check + open-screen click)

    def setPosition(self, v):
        self._setNumber(0, v)

    def setXpRequired(self, v):
        self._setNumber(1, v)

    def setCategory(self, v):
        self._setString(2, v)

    def setName(self, v):
        self._setString(3, v)

    def setAffordable(self, v):
        self._setBool(4, v)

    def setLocked(self, v):
        self._setBool(5, v)

    def setIcon(self, v):
        self._setString(6, v)

    def setLevel(self, v):
        self._setNumber(7, v)

    def setOptions(self, v):
        self._setString(8, v)

    def setState(self, v):
        self._setString(9, v)

    def setActionId(self, v):
        self._setNumber(10, v)

    def setKindLabel(self, v):
        self._setString(11, v)

    def setPrereqNames(self, v):
        self._setString(12, v)

    def setEffect(self, v):
        self._setString(13, v)

    def setOptionEffects(self, v):
        self._setString(14, v)

    def setDone(self, v):
        self._setBool(15, v)


class UpgradeVM(ViewModel):
    """One available tier-XI upgrade node -> a clickable 'Upgrades Available' chip."""
    def __init__(self, properties=7, commands=0):
        super(UpgradeVM, self).__init__(properties=properties, commands=commands)

    def _initialize(self):
        super(UpgradeVM, self)._initialize()
        self._addNumberProperty("actionId", 0)    # 0 (skill-tree step_id)
        self._addStringProperty("icon", "")        # 1 (img:// URL)
        self._addStringProperty("name", "")        # 2
        self._addNumberProperty("xpRequired", 0)   # 3
        self._addStringProperty("effect", "")      # 4 (perk KPI bonus lines, \n-joined)
        self._addStringProperty("category", "")    # 5 (localized node sub-heading caption)
        self._addBoolProperty("done", False)       # 6 (session "done" marker: green check + open-screen click)

    def setActionId(self, v):
        self._setNumber(0, v)

    def setIcon(self, v):
        self._setString(1, v)

    def setName(self, v):
        self._setString(2, v)

    def setXpRequired(self, v):
        self._setNumber(3, v)

    def setEffect(self, v):
        self._setString(4, v)

    def setCategory(self, v):
        self._setString(5, v)

    def setDone(self, v):
        self._setBool(6, v)


class ResearchVM(ViewModel):
    def __init__(self, properties=22, commands=6):
        super(ResearchVM, self).__init__(properties=properties, commands=commands)

    def _initialize(self):
        super(ResearchVM, self)._initialize()
        self._addStringProperty("mode", "")        # 0
        self._addNumberProperty("scaleMin", 0)     # 1
        self._addNumberProperty("scaleMax", 0)     # 2
        self._addNumberProperty("fillVehicle", 0)  # 3
        self._addNumberProperty("fillFree", 0)     # 4
        self._addArrayProperty("ticks", Array())   # 5
        self._addNumberProperty("fieldModsDone", 0)   # 6
        self._addNumberProperty("fieldModsTotal", 0)  # 7
        self._addStringProperty("vehicleClass", "")  # 8 (for elite badge)
        self._addNumberProperty("eliteLevel", 0)     # 9
        self._addNumberProperty("eliteMaxLevel", 0)  # 10
        self._addStringProperty("eliteGrade", "")    # 11 (grade family id)
        self._addNumberProperty("eliteSub", 0)       # 12 (current sub-grade 1..4)
        self._addNumberProperty("combatXp", 0)       # 13 (cumulative combat XP)
        self._addBoolProperty("visible", True)        # 14 (false hides the bar)
        self._addArrayProperty("availUpgrades", Array())  # 15 ([UpgradeVM] -> chips)
        self._addNumberProperty("spendableXp", 0)    # 16 (vehicle XP + free XP, for affordability)
        self._addBoolProperty("colorBlind", False)   # 17 (mirror WoT's color-blind mode)
        self._addNumberProperty("posX", 0)           # 18 (bar center-x px; 0 = auto/CSS default)
        self._addNumberProperty("posY", 0)           # 19 (bar top px; 0 = auto/CSS default)
        self._addStringProperty("eliteCurrentIcon", "")  # 20 (current-grade emblem for the category icon)
        self._addStringProperty("labels", "")        # 21 (JSON bundle of localized widget labels; see i18n.widget_labels)
        # Reverse channel: JS click handlers invoke these commands. Each returns a
        # command object that connect_commands() wires to a Python handler. Wulf
        # delivers the JS-supplied argument(s) to those handlers.
        self.researchUnlock = self._addCommand("researchUnlock")    # arg: tech-tree int_cd
        self.unlockFieldMod = self._addCommand("unlockFieldMod")    # arg: field-mod step_id
        self.openSkillTree = self._addCommand("openSkillTree")      # no arg
        self.openResearch = self._addCommand("openResearch")        # no arg (done tech-tree marker click)
        self.openFieldMods = self._addCommand("openFieldMods")      # no arg (done field-mod marker click)
        self.setPosition = self._addCommand("setPosition")          # arg: {x, y} px (drag / seed)

    def setMode(self, v):
        self._setString(0, v)

    def setScaleMin(self, v):
        self._setNumber(1, v)

    def setScaleMax(self, v):
        self._setNumber(2, v)

    def setFillVehicle(self, v):
        self._setNumber(3, v)

    def setFillFree(self, v):
        self._setNumber(4, v)

    def getTicks(self):
        return self._getArray(5)

    def setFieldModsDone(self, v):
        self._setNumber(6, v)

    def setFieldModsTotal(self, v):
        self._setNumber(7, v)

    def setVehicleClass(self, v):
        self._setString(8, v)

    def setEliteLevel(self, v):
        self._setNumber(9, v)

    def setEliteMaxLevel(self, v):
        self._setNumber(10, v)

    def setEliteGrade(self, v):
        self._setString(11, v)

    def setEliteSub(self, v):
        self._setNumber(12, v)

    def setEliteCurrentIcon(self, v):
        self._setString(20, v)

    def setLabels(self, v):
        self._setString(21, v)

    def setCombatXp(self, v):
        self._setNumber(13, v)

    def setVisible(self, v):
        self._setBool(14, v)

    def getAvailUpgrades(self):
        return self._getArray(15)

    def setSpendableXp(self, v):
        self._setNumber(16, v)

    def setColorBlind(self, v):
        self._setBool(17, v)

    def setPosX(self, v):
        self._setNumber(18, v)

    def setPosY(self, v):
        self._setNumber(19, v)

    @staticmethod
    def getTicksType():
        return TickVM

    @staticmethod
    def getAvailUpgradesType():
        return UpgradeVM


def attach(host_vm):
    """Load assets into the hangar doc + expose our data model on the sub-view.
    Returns the ResearchVM instance to push into, or None on failure."""
    global _active
    try:
        openwg_gameface.gf_mod_inject(
            host_vm, WIDGET_NAME,
            styles=[COUI + "/WGModResearch.css"],
            modules=[COUI + "/WGModResearch.js"])
        rvm = ResearchVM()
        _connect_commands(rvm)
        # Retry settings registration here: by the first hangar mount every mod
        # (including ModsSettingsAPI) is loaded, so the import that may have failed
        # at entry-point install time now succeeds. Idempotent once registered.
        mod_settings.init()
        host_vm._addViewModelProperty(DATA_PROP, rvm)
        _active = (host_vm, rvm)
        return rvm
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return None


def refresh():
    """Re-push the current vehicle's model into the mounted widget."""
    if _active is None:
        LOG_NOTE("[wgmod] refresh: no active widget")
        return False
    push(_active[1], host_vm=_active[0])
    return True


def push(rvm, host_vm=None):
    """Recompute the model for the selected vehicle and write it into rvm."""
    if rvm is None:
        return
    try:
        snap = engine_adapter.build_snapshot()
        if snap is None:
            return
        model = build_model(snap, mod_settings.enabled_modes())
        # Session "done" markers: promote a confirmed click and inject the current
        # vehicle's marker (a first tick / first chip). Engine-free + guarded.
        recent.decorate(model, snap)
        LOG_NOTE("[wgmod] push mode=%s ticks=%d fillV=%d fillF=%d" % (
            model.mode, len(model.ticks), model.fill_vehicle, model.fill_free))
        # Resolve localized labels OUTSIDE the transaction: a bad resource id must never
        # abort the model write (a rolled-back transaction blanks the whole bar).
        try:
            labels_json = json.dumps(i18n.widget_labels(), ensure_ascii=True)
        except Exception:
            LOG_CURRENT_EXCEPTION()
            labels_json = "{}"
        with rvm.transaction() as tx:
            tx.setVisible(bar_visible(_bar_visible(), mod_settings.hide_always(),
                                      mod_settings.hide_when_complete(), model.mode,
                                      _in_garage()))
            tx.setColorBlind(engine_adapter.is_color_blind())
            # Localized widget labels (client-language, sourced from WG's own strings);
            # JSON so the whole bundle rides one field. ensure_ascii escapes non-ASCII
            # (e.g. Cyrillic) to \uXXXX, which JS JSON.parse decodes back.
            tx.setLabels(labels_json)
            tx.setPosX(mod_settings.pos_x())
            tx.setPosY(mod_settings.pos_y())
            tx.setMode(model.mode)
            tx.setScaleMin(model.scale_min)
            tx.setScaleMax(model.scale_max)
            tx.setFillVehicle(model.fill_vehicle)
            tx.setFillFree(model.fill_free)
            tx.setFieldModsDone(model.fieldmods_done)
            tx.setFieldModsTotal(model.fieldmods_total)
            tx.setVehicleClass(model.vehicle_class or "")
            tx.setEliteLevel(model.elite_level or 0)
            tx.setEliteMaxLevel(model.elite_max_level or 0)
            tx.setEliteGrade(model.elite_grade or "")
            tx.setEliteSub(model.elite_sub or 0)
            tx.setEliteCurrentIcon(getattr(model, "elite_current_icon", "") or "")
            tx.setCombatXp(model.combat_xp or 0)
            tx.setSpendableXp(model.spendable_xp or 0)
            arr = tx.getTicks()
            arr.clear()
            for t in model.ticks:
                tv = TickVM()
                tv.setPosition(t.xp_position)
                tv.setXpRequired(t.xp_required)
                tv.setCategory(t.category)
                tv.setName(t.name or "")
                tv.setAffordable(bool(t.affordable))
                tv.setLocked(bool(t.locked))
                tv.setIcon(t.icon or "")
                tv.setLevel(t.level or 0)
                tv.setOptions("\n".join(t.options or []))
                tv.setState(t.state or "")
                tv.setActionId(t.action_id or 0)
                tv.setKindLabel(getattr(t, "kind_label", "") or "")
                tv.setPrereqNames("\n".join(getattr(t, "prereq_names", None) or []))
                tv.setEffect(getattr(t, "effect", "") or "")
                tv.setOptionEffects("\n".join(getattr(t, "option_effects", None) or []))
                tv.setDone(bool(getattr(t, "done", False)))
                arr.addViewModel(tv)
            arr.invalidate()
            # Available tier-XI upgrade nodes -> the clickable header chips.
            ua = tx.getAvailUpgrades()
            ua.clear()
            for up in model.avail_upgrades:
                uv = UpgradeVM()
                uv.setActionId(getattr(up, "step_id", 0) or 0)
                uv.setIcon(getattr(up, "icon", "") or "")
                uv.setName(getattr(up, "name", "") or "")
                uv.setXpRequired(getattr(up, "xp_cost", 0) or 0)
                uv.setEffect(getattr(up, "description", "") or "")
                uv.setCategory(getattr(up, "category", "") or "")
                uv.setDone(bool(getattr(up, "done", False)))
                ua.addViewModel(uv)
            ua.invalidate()
        # Nudge the host sub-view so its data re-syncs to JS (nested-model
        # updates may not bubble a data-changed event on their own).
        if host_vm is not None:
            try:
                with host_vm.transaction() as _h:
                    pass
            except Exception:
                pass
    except Exception:
        LOG_CURRENT_EXCEPTION()
