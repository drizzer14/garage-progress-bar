# -*- coding: utf-8 -*-
"""PC-only engine adapter: read the live WoT EU 2.3 client into a VehicleSnapshot.

This is the only module that touches game symbols. Every category read is wrapped
in try/except so one unreadable system degrades gracefully (spec section 8): the
category yields a safe empty default and the rest of the bar still renders.

Symbols verified against the EU 2.3 decompiled source — see
docs/superpowers/research/decompiled-findings.md.
"""
from CurrentVehicle import g_currentVehicle
from helpers import dependency
from skeletons.gui.shared import IItemsCache
from items import getTypeOfCompactDescr
from gui.shared.gui_items import GUI_ITEM_TYPE
from debug_utils import LOG_CURRENT_EXCEPTION

from wgmod_research.domain import types as t


def _items_cache():
    # NOTE: dependency.instance() returns the live service. dependency.descriptor()
    # is only valid as a class attribute (descriptor protocol) and raises if called
    # at module level -- verified in-game.
    return dependency.instance(IItemsCache)


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

    return t.VehicleSnapshot(
        tier=_safe_int(lambda: veh.level, 0),
        is_elite=_safe(lambda: bool(veh.isElite), False),
        vehicle_xp=_safe_int(lambda: veh.xp, 0),
        free_xp=int(free_xp),
        tech_unlocks=_read_tech_unlocks(veh, unlocks),
        field_mod_steps=_read_field_mods(veh))


# --- helpers ---------------------------------------------------------------

def _safe(fn, default):
    try:
        value = fn()
        return default if value is None else value
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return default


def _safe_int(fn, default):
    return int(_safe(fn, default))


def _safe_stats():
    try:
        return _items_cache().items.stats
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return None


def _read_tech_unlocks(veh, unlocks):
    """Tech-tree unlocks: modules + next vehicles (incl. Tier XI) via the
    vehicle's unlock graph. getUnlocksDescrs() yields (idx, xpCost, intCD, prereqs)."""
    try:
        cache = _items_cache()
        out = []
        for _idx, xp_cost, int_cd, prereqs in veh.getUnlocksDescrs():
            try:
                is_vehicle = getTypeOfCompactDescr(int_cd) == GUI_ITEM_TYPE.VEHICLE
                item = cache.items.getItemByCD(int_cd)
                name = getattr(item, "userName", "") or ""
                icon = getattr(item, "icon", "") or ""
            except Exception:
                LOG_CURRENT_EXCEPTION()
                is_vehicle, name, icon = False, "", ""
            out.append(t.UnlockItem(
                int_cd=int_cd, name=name, icon=icon, xp_cost=int(xp_cost),
                kind=("vehicle" if is_vehicle else "module"),
                researched=(int_cd in unlocks),
                prereqs_met=all(p in unlocks for p in prereqs)))
        return out
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return []


def _read_field_mods(veh):
    """Field Modifications ("upgrades"): post-progression tree steps paid with XP.
    Only emitted for elite vehicles that actually have post-progression."""
    try:
        if not veh.isElite or not veh.isPostProgressionExists:
            return []
        pp = veh.postProgression
        out = []
        for step in pp.iterOrderedSteps():
            try:
                price = step.getPrice()
                xp_cost = int(getattr(price, "xp", 0) or 0)
                if xp_cost <= 0:
                    continue  # non-XP step (e.g. credits buy-pair) -> not on the bar
                name, icon = _step_label(step)
                out.append(t.ProgressionStep(
                    step_id=step.stepID, name=name, icon=icon,
                    xp_cost=xp_cost, unlocked=bool(step.isReceived())))
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
        return out
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return []


def _step_label(step):
    """Best-effort name/icon for a field-mod step via its action model.
    Falls back to the step id; refined during in-game verification."""
    try:
        action = getattr(step, "action", None)
        if action is not None:
            name = getattr(action, "locName", None) or getattr(action, "name", "") or ""
            icon = getattr(action, "imgName", "") or ""
            return name, icon
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return ("step %s" % getattr(step, "stepID", "?")), ""
