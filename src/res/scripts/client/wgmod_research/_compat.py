# -*- coding: utf-8 -*-
"""Engine-shim + best-effort guard helpers shared across the adapter/bridge layers.

`debug_utils` is a game symbol: it exists in the running client but not under the
Python 3.13 test interpreter. Rather than copy-paste the guarded fallback import in
every module, they import `LOG_CURRENT_EXCEPTION` / `LOG_NOTE` from here -- one place
that resolves the real thing in-client and degrades to a no-op out of client (so the
engine-free helper modules still import under pytest).

`_safe` / `_safe_int` are the read-side guard idiom (run a getter, log + fall back to a
default on any failure) lifted here so more than one module can share them.

Adapter/bridge only -- the engine-free `domain/` layer must NOT import this. 2/3-compatible.
"""
# Dev-trace gate. LOG_CURRENT_EXCEPTION always fires (real errors, in `except` blocks
# only); LOG_NOTE is informational chatter that runs on the normal path (every refresh,
# hangar mount, listener re-arm and click) and would otherwise spam a player's
# python.log. So LOG_NOTE is routed through a gate that is a no-op unless _DEBUG -- flip
# _DEBUG to True only for a local dev build; the shipped mod stays quiet.
_DEBUG = False

try:
    from debug_utils import LOG_CURRENT_EXCEPTION, LOG_NOTE as _LOG_NOTE
except Exception:
    def LOG_CURRENT_EXCEPTION():
        pass

    def _LOG_NOTE(*args, **kwargs):
        pass


def LOG_NOTE(*args, **kwargs):
    """Informational trace -- suppressed unless _DEBUG so a shipped build never writes
    dev chatter to the player's python.log. Callers keep using LOG_NOTE unchanged."""
    if _DEBUG:
        _LOG_NOTE(*args, **kwargs)


def _safe(fn, default):
    """Call `fn`; return its value, or `default` on None / any exception (logged)."""
    try:
        value = fn()
        return default if value is None else value
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return default


def _safe_int(fn, default):
    return int(_safe(fn, default))
