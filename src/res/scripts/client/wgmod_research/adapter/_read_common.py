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


def vehicle_xp_stats(int_cd):
    """(avg_xp, battle_count, max_xp) for this vehicle's RANDOM battles: the historical
    average combat XP per battle -- the same "avg XP" the garage vehicle stats show --
    the number of random battles behind it, and the best single-battle XP. All 0 when the
    tank has no random battles / the read fails. Used to estimate "battles remaining"
    beside an XP shortfall in tooltips (avg is the per-battle divisor; the count decides
    whether that average has enough sample to trust or should fall back to the
    account-wide average; max feeds the range's optimistic "best-game pace" bound).

    Symbols verified against the EU 2.3 decompiled client:
    cache.items.getVehicleDossier(intCD) -> VehicleDossier (a VehicleDossierStats), whose
    getRandomStats() is a RandomStatsBlock; getAvgXP() = getXP()/getBattlesCount() and
    returns None for 0 battles (dossier/stats.py _getAvgValue) -> coerce falsy to 0 so we
    never divide by zero downstream. getMaxXp() is the best single random battle (note the
    lower-case 'p'). Guarded like every other read (spec section 8)."""
    try:
        if not int_cd:
            return 0, 0, 0
        rs = _items_cache().items.getVehicleDossier(int_cd).getRandomStats()
        avg = rs.getAvgXP()
        return (int(avg) if avg else 0), int(rs.getBattlesCount() or 0), int(rs.getMaxXp() or 0)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return 0, 0, 0


def account_avg_battle_xp():
    """The account-wide average combat XP per RANDOM battle -- the fallback divisor for
    the "battles remaining" estimate on a tank with too few battles of its own to trust.
    0 when the account has no random battles / unreadable.

    Verified live (EU 2.3): items.getAccountDossier() -> AccountDossier; .getRandomStats()
    is an AccountRandomStatsBlock; getAvgXP() returns None for 0 battles -> coerce to 0.
    Guarded like every read (spec section 8)."""
    try:
        rs = _items_cache().items.getAccountDossier().getRandomStats()
        avg = rs.getAvgXP()
        return int(avg) if avg else 0
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return 0


def active_reserve_mult():
    """Combined multiplier (as an int PERCENT, 100 == x1.0) of any ACTIVE personal-
    reserve XP booster that grows a vehicle's combat XP. Only 'booster_xp' (vehicle XP)
    reserves count -- free-XP / crew-XP / credits reserves don't move research XP.
    Returns 100 when none is running / unreadable, so the estimate's optimistic bound
    simply doesn't widen.

    Verified live (EU 2.3): IBoostersController.getExpirableBoosters() -> {id: Booster};
    a booster is currently running iff getUsageLeftTime() > 0; effectValue is the percent
    bonus (e.g. 100 == +100%). Reserves of one resource don't stack in-game, but we
    combine multiplicatively defensively. Guarded (spec section 8)."""
    try:
        from skeletons.gui.game_control import IBoostersController
        boosters = dependency.instance(IBoostersController).getExpirableBoosters()
        mult = 1.0
        for b in boosters.values():
            try:
                if getattr(b, "boosterGuiType", "") != "booster_xp":
                    continue
                if b.getUsageLeftTime() <= 0:      # owned but not activated -> skip
                    continue
                mult *= 1.0 + (int(b.effectValue or 0) / 100.0)
            except Exception:
                continue
        return int(round(mult * 100))
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return 100


def daily_double_factor(veh):
    """The first-win-of-the-day XP factor (as an int PERCENT, 100 == x1.0) still
    available TODAY for `veh`, else 100. The shop's global first-victory factor
    (shop.dailyXPFactor, normally 2) applies when the win-multiplier mode is ALWAYS, or
    when this vehicle hasn't yet taken its daily double (intCD NOT in
    stats.multipliedVehicles) and isn't event-only.

    Mirrors the game's own daily-XP badge logic
    (carousel_data_provider.Vehicle.__init__): note the GUI item's static
    veh.dailyXPFactor is always the type's factor (2) regardless of use, so availability
    must come from stats.multipliedVehicles (the set of vehicles that HAVE already used
    today's double -- verified live: not-in-set == still available). Guarded -> 100."""
    try:
        import constants
        cache = _items_cache()
        shop = cache.items.shop
        stats = cache.items.stats
        always = shop.winXPFactorMode == constants.WIN_XP_FACTOR_MODE.ALWAYS
        used = veh.intCD in stats.multipliedVehicles
        event_only = bool(getattr(veh, "isOnlyForEventBattles", False))
        if always or (not used and not event_only):
            factor = shop.dailyXPFactor or getattr(veh, "dailyXPFactor", 1) or 1
            return int(round(float(factor) * 100))
        return 100
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return 100


def blueprint_effective_cost(int_cd, xp_full):
    """(effective_cost, discount_pct) for the VEHICLE unlock `int_cd` given its raw
    XP cost `xp_full`, applying any blueprint-fragment discount the player holds.

    Returns (int(xp_full), 0) when no fragments apply or on any failure -- so a
    degraded read never blanks or misprices the row. VEHICLE unlocks only: modules
    must keep their raw cost (WG's validator rejects a module unlocked at a differing
    cost). Mirrors the game's OWN tech-tree cost path byte-for-byte
    (techtree_dp.getBlueprintDiscountData): getBlueprintDiscount gives the discount
    for the fragments the player CURRENTLY HOLDS -- 0 when none are held / the vehicle
    is already unlocked, scaling with the held fragment count, capped at 100 -- and
    calculateCost turns full cost + percent into the paid cost. (Do NOT use
    getFragmentDiscountAndCost: it delegates to getRequiredCountAndDiscount, a
    conversion-dialog helper that returns the flat per-fragment CONFIG discount
    regardless of how many fragments are held -- a phantom discount with zero
    fragments, and not scaled by the held count. That mismatch was the regression.)
    Symbols verified live (EU 2.3): cache.items.blueprints (BlueprintsRequester)."""
    xp_full = int(xp_full or 0)
    try:
        cache = _items_cache()
        bp = getattr(cache.items, "blueprints", None)
        if bp is None or xp_full <= 0:
            return xp_full, 0
        vlevel = int(getattr(cache.items.getItemByCD(int_cd), "level", 0) or 0)
        if not vlevel:
            return xp_full, 0
        disc_pct = int(bp.getBlueprintDiscount(int_cd, vlevel) or 0)
        if disc_pct <= 0:
            return xp_full, 0
        return int(bp.calculateCost(xp_full, disc_pct)), disc_pct
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return xp_full, 0


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
