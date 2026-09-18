# -*- coding: utf-8 -*-
"""Unit test for adapter.prb_read.is_onslaught_garage: the guarded prebattle-mode read
behind the per-garage vertical position.

All game imports in prb_read are LOCAL, so the module imports under pytest with no stubs
(debug_utils is stubbed in conftest for _compat). With the prebattle singletons absent the
read must fail soft to False -- never raise into the bridge push."""
from wgmod_research.adapter.prb_read import is_onslaught_garage


def test_is_onslaught_garage_false_without_engine():
    # gui.prb_control.* is absent under pytest -> the local import raises inside the guard
    # -> False (treated as the regular garage). Must not raise.
    assert is_onslaught_garage() is False
