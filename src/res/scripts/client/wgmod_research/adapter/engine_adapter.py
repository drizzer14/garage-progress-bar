# -*- coding: utf-8 -*-
"""PC-only engine adapter: read the live WoT EU 2.3 client into a VehicleSnapshot.

This is the orchestrator for the read side: build_snapshot() assembles a
VehicleSnapshot by delegating each category to its own reader module, and is the
only place they are composed. The per-subsystem readers live alongside:

  - tech_read.read_tech_unlocks            -- tech-tree modules + next vehicles
  - post_progression_read.read_post_progression -- linear field modifications
  - skill_tree_read.read_skill_tree / is_skill_tree -- tier-XI vehicle skill tree
  - prestige_read.read_prestige            -- Elite Levels ("prestige")
  - pricing_read.read_purchase_price       -- done-tick credits footer
  - _read_common                           -- items-cache + KPI helpers shared above

Each is imported here under its old private alias so build_snapshot's call sites are
unchanged, and read_purchase_price is re-exported so the bridge's
engine_adapter.read_purchase_price(...) call site keeps working. Every category read
is wrapped in try/except so one unreadable system degrades gracefully (spec section
8): the category yields a safe empty default and the rest of the bar still renders.

Symbols verified against the EU 2.3 decompiled client source.
"""
from CurrentVehicle import g_currentVehicle
from helpers import dependency

from wgmod_research._compat import LOG_CURRENT_EXCEPTION, _safe, _safe_int
from wgmod_research.adapter._read_common import _safe_stats, avg_battle_xp as _avg_battle_xp
from wgmod_research.adapter.tech_read import read_tech_unlocks as _read_tech_unlocks
from wgmod_research.adapter.post_progression_read import (
    read_post_progression as _read_post_progression)
from wgmod_research.adapter.skill_tree_read import (
    read_skill_tree as _read_skill_tree, is_skill_tree as _is_skill_tree)
from wgmod_research.adapter.prestige_read import read_prestige as _read_prestige
# Re-exported: the bridge calls engine_adapter.read_purchase_price(...).
from wgmod_research.adapter.pricing_read import read_purchase_price  # noqa: F401
from wgmod_research.domain import types as t


def is_color_blind():
    """True when WoT's own color-blind mode is enabled (Settings -> the 'isColorBlind'
    graphics option). Read-only; the bridge pushes this to the widget so it can swap to
    a color-blind-safe palette. Imports are local and the whole read is guarded ->
    False (fail to the standard palette) so a settings-API change can never raise into
    the bridge. Symbol verified against the EU 2.3 decompiled client
    (account_helpers/settings_core)."""
    try:
        from skeletons.account_helpers.settings_core import ISettingsCore
        from account_helpers.settings_core.settings_constants import GRAPHICS
        return bool(dependency.instance(ISettingsCore).getSetting(GRAPHICS.COLOR_BLIND))
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return False


def build_snapshot():
    """Read the selected vehicle into a VehicleSnapshot, or None if unavailable."""
    if not g_currentVehicle.isPresent():
        return None
    try:
        veh = g_currentVehicle.item
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return None

    stats = _safe_stats()
    free_xp = _safe_int(lambda: stats.freeXP, 0) if stats is not None else 0
    unlocks = _safe(lambda: stats.unlocks, set()) if stats is not None else set()

    is_skill_tree = _is_skill_tree(veh)
    fm_steps, fm_done, fm_total = _read_post_progression(veh)
    (st_total_xp, st_spent_xp, st_done, st_total, st_final_icon,
     st_final_name, st_final_xp, st_final_effect, st_available) = (
        _read_skill_tree(veh) if is_skill_tree else (0, 0, 0, 0, "", "", 0, "", []))
    prestige = _read_prestige(veh)

    return t.VehicleSnapshot(
        tier=_safe_int(lambda: veh.level, 0),
        is_elite=_safe(lambda: bool(veh.isElite), False),
        vehicle_xp=_safe_int(lambda: veh.xp, 0),
        free_xp=int(free_xp),
        tech_unlocks=_read_tech_unlocks(veh, unlocks),
        field_mod_steps=fm_steps,
        fieldmods_done=fm_done, fieldmods_total=fm_total,
        vehicle_class=_safe(lambda: veh.type, "") or "",
        has_prestige=prestige["has_prestige"],
        elite_level=prestige["elite_level"],
        elite_max_level=prestige["elite_max_level"],
        elite_current_xp=prestige["elite_current_xp"],
        elite_next_xp=prestige["elite_next_xp"],
        elite_grades=prestige["elite_grades"],
        elite_rewards=prestige["elite_rewards"],
        # .get() so a future missing prestige key degrades gracefully instead of
        # raising and blanking the whole bar (see _prestige_defaults).
        elite_level_xp=prestige.get("elite_level_xp", {}),
        is_skill_tree=is_skill_tree,
        skilltree_total_xp=st_total_xp, skilltree_spent_xp=st_spent_xp,
        skilltree_done=st_done, skilltree_total=st_total,
        skilltree_final_icon=st_final_icon, skilltree_final_name=st_final_name,
        skilltree_final_xp=st_final_xp, skilltree_final_effect=st_final_effect,
        skilltree_available=st_available,
        vehicle_int_cd=_safe_int(lambda: veh.intCD, 0),
        avg_battle_xp=_avg_battle_xp(_safe_int(lambda: veh.intCD, 0)))
