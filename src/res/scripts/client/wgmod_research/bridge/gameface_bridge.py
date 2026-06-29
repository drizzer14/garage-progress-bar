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
import BigWorld
from frameworks.wulf import ViewModel, Array
from debug_utils import LOG_CURRENT_EXCEPTION, LOG_NOTE
from CurrentVehicle import g_currentVehicle
from helpers import dependency
from skeletons.gui.game_control import ILoadoutController
from skeletons.gui.shared import IItemsCache

from wgmod_research.adapter import engine_adapter
from wgmod_research.domain.builder import build_model
import openwg_gameface

WIDGET_NAME = "WGModResearch"
DATA_PROP = "wgResearch"
COUI = "coui://gui/gameface/mods/drizzer14/WGModResearch"

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

# Our handler for items-cache syncs (free-XP conversion, research/field-mod
# purchases, post-battle XP, prestige changes -- everything that mutates the XP
# state without a vehicle re-selection). Same strong-ref rationale as above. The
# items cache is a long-lived DI singleton (its event list is NOT torn down on
# battle exit), so re-arming on mount is unnecessary but harmless -- we keep the
# idempotent membership check for symmetry and hot-reload safety.
_stats_listener = None

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


class TickVM(ViewModel):
    def __init__(self, properties=10, commands=0):
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


class ResearchVM(ViewModel):
    def __init__(self, properties=15, commands=0):
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

    def setCombatXp(self, v):
        self._setNumber(13, v)

    def setVisible(self, v):
        self._setBool(14, v)

    @staticmethod
    def getTicksType():
        return TickVM


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
        model = build_model(snap)
        LOG_NOTE("[wgmod] push mode=%s ticks=%d fillV=%d fillF=%d" % (
            model.mode, len(model.ticks), model.fill_vehicle, model.fill_free))
        with rvm.transaction() as tx:
            tx.setVisible(_bar_visible())
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
            tx.setCombatXp(model.combat_xp or 0)
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
                arr.addViewModel(tv)
            arr.invalidate()
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
