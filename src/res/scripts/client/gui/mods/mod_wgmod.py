# -*- coding: utf-8 -*-
"""WGMod research-progress bar — entry point (EU 2.3).

Mount path (verified in-game): WoT 2.3 loads only packaged .wotmod. OpenWG's JS
injector only acts on hangar SUB-views, so we patch a hangar sub-view
(HangarVehicleParamsPresenter) to inject our widget assets and expose our data
model; the widget JS renders from that model. We recompute on vehicle change.

OpenWG Gameface is a hard dependency. Python 2.7 (BigWorld) runtime.
"""
from debug_utils import LOG_NOTE, LOG_CURRENT_EXCEPTION
from CurrentVehicle import g_currentVehicle

MOD_NAME = "Research Progress"
MOD_VERSION = "0.1.0"

_active_rvm = None


def _install():
    import openwg_gameface  # noqa: F401  (hard dependency; raises if absent)
    from gui.impl.lobby.hangar.presenters.hangar_vehicle_params_presenter import (
        HangarVehicleParamsPresenter as P)
    from wgmod_research.bridge import gameface_bridge as bridge

    if getattr(P, "_wgmod_patched", False):
        return

    _orig_onLoading = P._onLoading
    _orig_finalize = P._finalize

    def _onLoading(self, *args, **kwargs):
        _orig_onLoading(self, *args, **kwargs)
        global _active_rvm
        try:
            _active_rvm = bridge.attach(self.getViewModel())
            bridge.push(_active_rvm)
        except Exception:
            LOG_CURRENT_EXCEPTION()

    def _finalize(self, *args, **kwargs):
        global _active_rvm
        _active_rvm = None
        _orig_finalize(self, *args, **kwargs)

    P._onLoading = _onLoading
    P._finalize = _finalize
    P._wgmod_patched = True

    def _on_vehicle_changed(*args, **kwargs):
        try:
            if _active_rvm is not None:
                bridge.push(_active_rvm)
        except Exception:
            LOG_CURRENT_EXCEPTION()

    g_currentVehicle.onChanged += _on_vehicle_changed
    LOG_NOTE("[%s] v%s installed (sub-view inject + data)" % (MOD_NAME, MOD_VERSION))


try:
    _install()
except Exception:
    LOG_CURRENT_EXCEPTION()
