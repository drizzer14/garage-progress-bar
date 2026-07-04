# -*- coding: utf-8 -*-
"""PC-only reader for a "done" tick's credits purchase price (EU 2.3).

Extracted from engine_adapter.py (Tier 3g): resolves the credits price shown in a
done-tick's tooltip footer -- the buy price for modules/vehicles, or the variant
install cost for a field-mod selection level. engine_adapter re-exports
read_purchase_price so the bridge's existing engine_adapter.read_purchase_price(...)
call site is unchanged. Shares the items-cache accessor via adapter._read_common.
Fully guarded: any failure yields 0 -> no footer. Symbols verified against EU 2.3.
"""
from CurrentVehicle import g_currentVehicle

from wgmod_research._compat import LOG_CURRENT_EXCEPTION, _safe, _safe_int
from wgmod_research.adapter._read_common import _items_cache
from wgmod_research.adapter.tech_read import module_installed
from wgmod_research.domain.constants import Category


def _credits_buy_price(item):
    """Credits buy price of a GUI item via the client's ItemPrices chain, or 0."""
    from gui.shared.money import Currency
    price = _safe_int(
        lambda: item.buyPrices.itemPrice.price.getSignValue(Currency.CREDITS), 0)
    if price <= 0:  # some items expose a flat .buyPrice Money instead
        price = _safe_int(lambda: item.buyPrice.getSignValue(Currency.CREDITS), 0)
    return int(price or 0)


def _fieldmod_selection_price(step_id):
    """Credits cost to install a variant for a field-mod level that offers a SELECTION,
    or 0. The leveled step is XP-paid, but its child MultiModsItem's two SimpleModItem
    variants each carry a credits install price (both the same, e.g. 150000). We read
    the child whose parent == step_id and return its first variant's credits price.
    Levels without a selection slot -> 0. Current vehicle only (done ticks are per the
    selected vehicle). Fully guarded."""
    try:
        if not g_currentVehicle.isPresent():
            return 0
        veh = g_currentVehicle.item
        for step in veh.postProgression.iterOrderedSteps():
            try:
                if type(step.action).__name__ != "MultiModsItem":
                    continue
                if _safe(lambda: step.getParentStepID(), None) != step_id:
                    continue
                for mod in (getattr(step.action, "modifications", None) or []):
                    cr = _safe_int(lambda: mod.getPrice().credits or 0, 0)
                    if cr > 0:
                        return cr
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return 0


def read_purchase_price(int_cd, category):
    """Current credits price for a "done" tick's item, or 0 to hide the footer.

    Modules / vehicles: the credits buy price, re-read fresh every sync so it drops to
    0 (footer hidden) once the item is OWNED. Field mods: the credits cost to install a
    variant for a level that offers a SELECTION (0 for levels with no selection slot).
    Fully guarded: any failure yields 0 -> no footer."""
    try:
        if not int_cd:
            return 0
        if category == Category.FIELDMOD:
            return _fieldmod_selection_price(int_cd)  # int_cd is the leveled step_id
        item = _safe(lambda: _items_cache().items.getItemByCD(int(int_cd)), None)
        if item is None:
            return 0
        # Already owned -> hide the price. Owned == in free inventory (bought this
        # session or earlier) OR mounted on the current vehicle (buy+mount installs it,
        # which drops it out of inventory). Kept in step with tech_read's `owned` so the
        # footer and the done-marker retirement agree on what "owned" means.
        if _safe(lambda: bool(item.isInInventory), False) \
                or _safe_int(lambda: item.inventoryCount, 0) > 0:
            return 0
        if g_currentVehicle.isPresent() and module_installed(item, g_currentVehicle.item):
            return 0
        return _credits_buy_price(item)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return 0
