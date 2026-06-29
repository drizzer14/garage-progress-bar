# -*- coding: utf-8 -*-
"""WGMod research-progress bar — entry point (EU 2.3).

Mount path (verified in-game): WoT 2.3 loads only packaged .wotmod. OpenWG's JS
injector only acts on hangar SUB-views, so we patch a hangar sub-view
(HangarVehicleParamsPresenter) to inject our widget assets and expose our data
model; the widget JS renders from that model. We recompute on vehicle change.

OpenWG Gameface is a hard dependency. Python 2.7 (BigWorld) runtime.
"""
from debug_utils import LOG_NOTE, LOG_CURRENT_EXCEPTION

MOD_NAME = "Research Progress"
MOD_VERSION = "0.1.1"


def _install():
    import openwg_gameface  # noqa: F401  (hard dependency; raises if absent)
    from gui.impl.lobby.hangar.presenters.hangar_vehicle_params_presenter import (
        HangarVehicleParamsPresenter as P)
    from wgmod_research.bridge import gameface_bridge as bridge

    if getattr(P, "_wgmod_patched", False):
        return

    _orig_onLoading = P._onLoading

    def _onLoading(self, *args, **kwargs):
        _orig_onLoading(self, *args, **kwargs)
        try:
            # Re-arm on every mount: the battle-exit hangar teardown rebuilds the
            # onChanged delegate list with WG's own presenters but drops ours, so
            # a once-only subscription stops firing after the first battle. Same for
            # the loadout listener (hides the bar while the ammo/setup overlay opens).
            # The stats listener (items-cache syncs -> live XP updates) is on a
            # long-lived singleton so it survives teardown, but re-arm it too: the
            # installer is idempotent and this keeps it working across hot reloads.
            bridge.install_vehicle_listener()
            bridge.install_loadout_listener()
            bridge.install_stats_listener()
            rvm = bridge.attach(self.getViewModel())
            bridge.push(rvm, host_vm=self.getViewModel())
        except Exception:
            LOG_CURRENT_EXCEPTION()

    P._onLoading = _onLoading
    P._wgmod_patched = True

    # Arm once now (for the install that happens while already in the hangar);
    # _onLoading re-arms on every subsequent mount.
    bridge.install_vehicle_listener()
    bridge.install_loadout_listener()
    bridge.install_stats_listener()
    LOG_NOTE("[%s] v%s installed (sub-view inject + data)" % (MOD_NAME, MOD_VERSION))


try:
    _install()
except Exception:
    LOG_CURRENT_EXCEPTION()
