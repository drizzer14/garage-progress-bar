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
from debug_utils import LOG_CURRENT_EXCEPTION

from wgmod_research.adapter import engine_adapter
from wgmod_research.domain.builder import build_model
import openwg_gameface

WIDGET_NAME = "WGModResearch"
DATA_PROP = "wgResearch"
COUI = "coui://gui/gameface/mods/drizzer14/WGModResearch"


class TickVM(ViewModel):
    def __init__(self, properties=5, commands=0):
        super(TickVM, self).__init__(properties=properties, commands=commands)

    def _initialize(self):
        super(TickVM, self)._initialize()
        self._addNumberProperty("position", 0)   # 0
        self._addNumberProperty("xpRequired", 0)  # 1
        self._addStringProperty("category", "")  # 2
        self._addStringProperty("name", "")      # 3
        self._addBoolProperty("affordable", False)  # 4

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
    try:
        openwg_gameface.gf_mod_inject(
            host_vm, WIDGET_NAME,
            styles=[COUI + "/WGModResearch.css"],
            modules=[COUI + "/WGModResearch.js"])
        rvm = ResearchVM()
        host_vm._addViewModelProperty(DATA_PROP, rvm)
        return rvm
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return None


def push(rvm):
    """Recompute the model for the selected vehicle and write it into rvm."""
    if rvm is None:
        return
    try:
        snap = engine_adapter.build_snapshot()
        if snap is None:
            return
        model = build_model(snap)
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
                arr.addViewModel(tv)
            arr.invalidate()
    except Exception:
        LOG_CURRENT_EXCEPTION()
