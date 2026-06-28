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
from frameworks.wulf import ViewModel, Array
from debug_utils import LOG_CURRENT_EXCEPTION, LOG_NOTE
from CurrentVehicle import g_currentVehicle

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


def _on_vehicle_changed(*args, **kwargs):
    try:
        ok = refresh()
        LOG_NOTE("[wgmod] onChanged -> refresh ok=%s" % ok)
    except Exception:
        LOG_CURRENT_EXCEPTION()


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


class TickVM(ViewModel):
    def __init__(self, properties=6, commands=0):
        super(TickVM, self).__init__(properties=properties, commands=commands)

    def _initialize(self):
        super(TickVM, self)._initialize()
        self._addNumberProperty("position", 0)   # 0
        self._addNumberProperty("xpRequired", 0)  # 1
        self._addStringProperty("category", "")  # 2
        self._addStringProperty("name", "")      # 3
        self._addBoolProperty("affordable", False)  # 4
        self._addBoolProperty("locked", False)   # 5

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


class ResearchVM(ViewModel):
    def __init__(self, properties=6, commands=0):
        super(ResearchVM, self).__init__(properties=properties, commands=commands)

    def _initialize(self):
        super(ResearchVM, self)._initialize()
        self._addStringProperty("mode", "")        # 0
        self._addNumberProperty("scaleMin", 0)     # 1
        self._addNumberProperty("scaleMax", 0)     # 2
        self._addNumberProperty("fillVehicle", 0)  # 3
        self._addNumberProperty("fillFree", 0)     # 4
        self._addArrayProperty("ticks", Array())   # 5

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
            tx.setMode(model.mode)
            tx.setScaleMin(model.scale_min)
            tx.setScaleMax(model.scale_max)
            tx.setFillVehicle(model.fill_vehicle)
            tx.setFillFree(model.fill_free)
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
