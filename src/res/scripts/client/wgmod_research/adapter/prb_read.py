# -*- coding: utf-8 -*-
"""Prebattle / queue-mode read: which garage the player is currently sitting in.

One guarded engine read, same discipline as the other adapter readers (spec section 8):
all game imports are LOCAL so this module imports under pytest with no stubs, and the
whole read is wrapped -> a safe default (False) so a wrong/absent signal can never break
the bar. The Onslaught garage reuses the SAME default hangar view as the plain garage
(so gameface_bridge._in_garage admits it and the bar renders there); the only thing that
distinguishes it is the prebattle dispatcher's active functional mode.
"""
from wgmod_research._compat import LOG_CURRENT_EXCEPTION


def is_onslaught_garage():
    """True when the visible garage is the Onslaught garage (not the plain random-battle
    garage). Used only to pick the per-garage vertical position; fail-soft -> False (treat
    as the regular garage) if the prebattle singletons are absent/unreadable."""
    try:
        # Onslaught garage is internally Comp7; FUNCTIONAL_FLAG.COMP7 confirmed live on
        # client 2.4.0.0 (REPL). Entity via getDispatcher().getEntity().
        from gui.prb_control.dispatcher import g_prbLoader
        from gui.prb_control.settings import FUNCTIONAL_FLAG
        entity = g_prbLoader.getDispatcher().getEntity()
        return bool(entity.getModeFlags() & FUNCTIONAL_FLAG.COMP7)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return False
