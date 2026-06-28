# -*- coding: utf-8 -*-
"""
WGMod — entry point.

Files matching `mod_*.py` placed in scripts/client/gui/mods/ are imported by
the game's mod loader at client startup (alphabetical order). The import side
effects below are what "install" the mod's behavior.

Target runtime: Python 2.7 (BigWorld). Keep this 2.7-compatible.
"""
from __future__ import print_function

from debug_utils import LOG_NOTE, LOG_CURRENT_EXCEPTION

MOD_NAME = "WGMod"
MOD_VERSION = "0.1.0"


def _init():
    """Called once when the module is imported by the mod loader."""
    LOG_NOTE("[{0}] loaded v{1}".format(MOD_NAME, MOD_VERSION))
    _install_hooks()


def _install_hooks():
    """
    Install behavior by monkey-patching game classes.

    The standard pattern: keep a reference to the original method, replace it
    with your own, and call the original from inside yours so you extend rather
    than break stock behavior. Example (guarded so a class/signature change in
    a future patch can't crash the client):

        from gui.Scaleform.daapi.view.lobby.hangar.Hangar import Hangar

        _orig_populate = Hangar._populate
        def _patched_populate(self):
            _orig_populate(self)            # run stock behavior first
            LOG_NOTE("[{0}] hangar populated".format(MOD_NAME))
        Hangar._populate = _patched_populate
    """
    try:
        pass  # TODO: add real hooks here
    except Exception:
        LOG_CURRENT_EXCEPTION()


_init()
