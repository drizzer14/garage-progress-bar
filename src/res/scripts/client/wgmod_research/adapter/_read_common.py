# -*- coding: utf-8 -*-
"""Shared read-side helpers used by more than one engine-coupled reader.

Extracted from engine_adapter.py (Tier 3g) so the per-subsystem readers
(``tech_read`` / ``post_progression_read`` / ``skill_tree_read`` / ``pricing_read``)
can share the items-cache accessor and the KPI-effect formatters without an import
cycle: this module imports only ``_compat``, ``format`` and live game symbols, and is
imported BY the readers (never the reverse). engine_adapter re-imports ``_safe_stats``
from here so build_snapshot's call site is unchanged.

Every read is guarded (spec section 8) so one unreadable system degrades gracefully.
Game symbols verified against the EU 2.3 decompiled client source. 2/3-compatible
(imports under pytest -- the live symbols are only touched when called in-client).
"""
from helpers import dependency
from skeletons.gui.shared import IItemsCache

from wgmod_research._compat import LOG_CURRENT_EXCEPTION
from wgmod_research.adapter.format import kpi_objs as _kpi_objs, kpi_prefix as _kpi_prefix


def _items_cache():
    # NOTE: dependency.instance() returns the live service. dependency.descriptor()
    # is only valid as a class attribute (descriptor protocol) and raises if called
    # at module level -- verified in-game.
    return dependency.instance(IItemsCache)


def _safe_stats():
    try:
        return _items_cache().items.stats
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return None


def _kpi_lines(action, numbers_only=False):
    """The effect/bonus lines for a post-progression action, from its KPI list:
    one "<signed %> <stat phrase>" string per KPI that carries a description (e.g.
    "+10% to concealment after firing"). Empty list for actions with no KPI
    (features / role slots) or only the generic unlabeled 'value' KPI (signature
    mechanic perks -- effect not exposed as text). The signed numeric prefix comes
    from _kpi_prefix ('mul' -> percent, 'add' -> raw delta). Best-effort, never raises.

    With numbers_only=True, keep ONLY KPIs that carry a real signed magnitude
    (_kpi_prefix non-empty) -- used to append a figure to a tier-XI skill-tree
    sentence: a KPI whose delta rounds to a negligible ~zero (e.g. an 'add' of -0.01)
    has no prefix, and the default mode would emit its bare phrase ("to the aiming
    circle size") -- an orphaned, numberless fragment. numbers_only drops those (and
    keeps a bare prefix when the KPI has no description).

    KPI shape verified live (EU 2.3): action._descriptor.kpi -> [KPI], each with
    getDescriptionR() (DynAccessor -> backport.text -> phrase), .type, .value.
    A MultiModsItem variant (a `modification`) carries its KPI the same way. Types seen:
    'mul' (percent bonuses) and 'add' (absolute deltas, e.g. Kranvagn's top reverse
    speed) -- an 'add' KPI whose number was dropped by a mul-only gate was the
    "buff missing its number" bug."""
    lines = []
    try:
        from gui.impl import backport
        for k in _kpi_objs(action):
            prefix = _kpi_prefix(k)
            if numbers_only and not prefix:
                continue
            try:
                acc = k.getDescriptionR()
                desc = backport.text(acc() if callable(acc) else acc) or ""
            except Exception:
                desc = ""
            if numbers_only:
                lines.append((prefix + " " + desc).strip() if desc else prefix)
            elif desc:  # default mode skips the generic unlabeled 'value' KPI
                lines.append((prefix + " " + desc) if prefix else desc)
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return lines


def _action_effect(action):
    """Newline-joined effect summary for a single action (see _kpi_lines)."""
    return "\n".join(_kpi_lines(action))


def _kpi_number_lines(action):
    """_kpi_lines restricted to KPIs carrying a real signed magnitude (see the
    numbers_only path)."""
    return _kpi_lines(action, numbers_only=True)
