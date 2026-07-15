# -*- coding: utf-8 -*-
"""WGMod research-progress bar — entry point (EU 2.3).

Mount path (verified in-game): WoT 2.3 loads only packaged .wotmod. OpenWG's JS
injector only acts on hangar SUB-views and keeps ONE `ModInjectModel` per sub-view
(last-writer-wins), so two mods on the same sub-view overwrite each other. We inject
COLLISION-AWARE: patch a priority-ordered set of always-mounted hangar sub-views (the
crew panel preferred, the ammunition panel as fallback) and place our widget on the
first FREE one, yielding to any mod that claimed it first (see bridge.note_mount). The
sibling MoE Calculator uses HangarVehicleParamsPresenter, which the crew preference
already sidesteps; the fallback additionally protects against arbitrary third-party
mods. The widget JS self-locates its data by feature name ("WGModResearch") across all
sub-views (OpenWG model.js), so the chosen sub-view is transparent to the front-end.
We recompute on vehicle change.

OpenWG Gameface is a hard dependency. Python 2.7 (BigWorld) runtime.
"""
# LOG_CURRENT_EXCEPTION straight from the engine (always on, error paths only);
# LOG_NOTE via _compat so it goes through the same _DEBUG gate as the rest of the mod
# and never spams a player's python.log on the normal path.
from debug_utils import LOG_CURRENT_EXCEPTION
from wgmod_research._compat import LOG_NOTE

MOD_NAME = "Garage Progress Bar"
MOD_VERSION = "1.1.0"


def _patch_presenter(bridge, P, name):
    """Monkey-patch one candidate sub-view presenter's _onLoading so that, on every
    mount, we re-arm listeners and (re)place our widget via the collision-aware
    bridge.note_mount. Idempotent per presenter class."""
    if getattr(P, "_wgmod_patched", False):
        return

    _orig_onLoading = P._onLoading

    def _onLoading(self, *args, **kwargs):
        _orig_onLoading(self, *args, **kwargs)
        try:
            # Re-arm on every mount: the battle-exit hangar teardown rebuilds the
            # onChanged delegate list with WG's own presenters but drops ours, so
            # a once-only subscription stops firing after the first battle. The
            # installer is idempotent (membership-checked), so re-arming every mount is
            # safe and also keeps things working across hot reloads.
            bridge.install_all_listeners()
            placed = bridge.note_mount(name, self.getViewModel())
            if placed is not None:
                host_vm, rvm = placed
                bridge.push(rvm, host_vm=host_vm)
        except Exception:
            LOG_CURRENT_EXCEPTION()

    P._onLoading = _onLoading
    P._wgmod_patched = True


def _install():
    import openwg_gameface  # noqa: F401  (hard dependency; raises if absent)
    from wgmod_research.bridge import gameface_bridge as bridge
    from wgmod_research.bridge import mod_settings

    # Register our settings panel with ModsSettingsAPI (optional dependency; guarded
    # and idempotent). If MSA hasn't loaded yet, bridge.attach() retries on first mount.
    mod_settings.init()

    # Candidate hangar sub-views to inject onto, PREFERRED FIRST. OpenWG keeps one
    # ModInjectModel per sub-view (last-writer-wins), so rather than clobber a mod that
    # already claimed a sub-view we place onto the first FREE candidate and yield the
    # rest (see bridge.note_mount). The crew panel stays preferred -- uncontested by the
    # sibling MoE Calculator, which uses HangarVehicleParamsPresenter; the ammunition
    # panel (LoadoutPresenter) is the fallback. Both are ViewComponents defining their
    # own _onLoading, so each patch stays isolated to that one class.
    from gui.impl.lobby.hangar.presenters.crew_presenter import CrewPresenter
    from gui.impl.lobby.hangar.presenters.loadout_presenter import LoadoutPresenter
    candidates = (("crew", CrewPresenter), ("loadout", LoadoutPresenter))
    bridge.set_candidate_order([name for name, _ in candidates])
    for name, P in candidates:
        _patch_presenter(bridge, P, name)

    # Arm once now (for the install that happens while already in the hangar);
    # each patched _onLoading re-arms on every subsequent mount.
    bridge.install_all_listeners()
    LOG_NOTE("[%s] v%s installed (collision-aware sub-view inject + data)" % (
        MOD_NAME, MOD_VERSION))


try:
    _install()
except Exception:
    LOG_CURRENT_EXCEPTION()
