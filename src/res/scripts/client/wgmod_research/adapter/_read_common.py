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
from wgmod_research.adapter import format as _fmt
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


def blueprint_effective_cost(int_cd, xp_full, vlevel=None):
    """(effective_cost, discount_pct) for the VEHICLE unlock `int_cd` given its raw
    XP cost `xp_full`, applying any blueprint-fragment discount the player holds.

    `vlevel` is the vehicle's tier; pass it when the caller already holds the item
    (tech_read does) to skip a redundant getItemByCD lookup. Left None (actions.py) it
    is read here.

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
        vlevel = int(vlevel or 0) or int(getattr(cache.items.getItemByCD(int_cd), "level", 0) or 0)
        if not vlevel:
            return xp_full, 0
        disc_pct = int(bp.getBlueprintDiscount(int_cd, vlevel) or 0)
        if disc_pct <= 0:
            return xp_full, 0
        return int(bp.calculateCost(xp_full, disc_pct)), disc_pct
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return xp_full, 0


def _param_icon(kpi_name):
    """Full img:// URL of the vehParams icon for a KPI, or "" when the art doesn't
    resolve. The KPI name is remapped to a vehParams param basename (format
    .param_icon_name) and looked up through the game's OWN resource accessor, so an
    unknown/feature KPI (e.g. the signature 'value' KPI) validates to "" and never
    yields a broken icon box. Small (24x24) variant -- sized to the tooltip's body
    font. Verified live (EU 2.3): R.images.gui.maps.icons.vehParams.small.dyn(name)
    -> backport.image -> 'img://gui/maps/icons/vehParams/small/<name>.png'. Guarded."""
    try:
        name = _fmt.param_icon_name(kpi_name)
        if not name:
            return ""
        from gui.impl.gen import R
        from gui.impl import backport
        acc = R.images.gui.maps.icons.vehParams.small.dyn(name)
        if acc is not None and acc.isValid():
            return backport.image(acc()) or ""
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return ""


def _param_unit(kpi_name):
    """The bare unit for an 'add' KPI ('HP', 's', 'm', 'deg/s', 'km/h', 'mm',
    'h.p.'), or "" when the parameter carries no unit / is unmapped. Reuses the
    game's own measure-units table so the glyph matches the native params panel:
    measureUnitsForParameter(<vehParams param>) -> '#menu:tank_params/*' key ->
    makeString -> strip the wrapping parens. 'mul' KPIs never call this (they are a
    percent). Verified live (EU 2.3): avgDamage/maxHealth -> 'HP', aimingTime -> 's'.
    Guarded -- measureUnitsForParameter raises KeyError for a name it doesn't know."""
    try:
        name = _fmt.param_icon_name(kpi_name)
        if not name:
            return ""
        import gui.shared.items_parameters.formatters as PF
        from helpers.i18n import makeString
        key = PF.measureUnitsForParameter(name)
        return _fmt.strip_unit(makeString(key)) if key else ""
    except Exception:
        # KeyError for unmapped params is expected -> no unit (not an error).
        return ""


def _resolve_is_debuff(kpi_name, raw_is_debuff):
    """The buff/nerf colour flag for a KPI, corrected for the mislabelled
    "lower is better" params. The game computes KPI.isDebuff off the RAW KPI name
    against BACKWARD_QUALITY_PARAMS, but that set keys some params under their
    vehParams name only -- e.g. aim time lives there as 'aimingTime', not the KPI
    name 'vehicleGunAimSpeed' -- so a beneficial reduction misses the set and is
    flagged red. Decide membership for BOTH the KPI name and its mapped param name
    and let format.resolve_is_debuff flip the misclassified branch. Guarded: if the
    comparator import fails, fall back to the game's raw isDebuff."""
    try:
        from gui.shared.items_parameters.comparator import BACKWARD_QUALITY_PARAMS
        mapped = _fmt.param_icon_name(kpi_name)
        kpi_bw = kpi_name in BACKWARD_QUALITY_PARAMS
        param_bw = mapped in BACKWARD_QUALITY_PARAMS
        return _fmt.resolve_is_debuff(raw_is_debuff, kpi_bw, param_bw)
    except Exception:
        return raw_is_debuff


def _kpi_lines(action, numbers_only=False):
    """The effect/bonus lines for a post-progression action, from its KPI list:
    one enriched RECORD per KPI that carries a description (e.g. an icon + a green
    "+10% " + "to concealment after firing"). Empty list for actions with no KPI
    (features / role slots) or only the generic unlabeled 'value' KPI (signature
    mechanic perks -- effect not exposed as text). Best-effort, never raises.

    Each line is packed by format.kpi_record into an icon/color/value/phrase record
    (the widget splits it and renders the game's native perk-tooltip look): the
    signed numeric prefix comes from _kpi_prefix ('mul' -> percent, 'add' -> raw
    delta), the unit is appended for 'add' KPIs (_param_unit -> "+10 HP"), the
    parameter icon from _param_icon, and the buff/nerf color from KPI.isDebuff
    (NOT the sign -- a beneficial reduction like -25% fire chance is isDebuff=False
    -> green). A line without the record separator would render as plain text
    (back-compat), but every KPI line here is a record.

    With numbers_only=True, keep ONLY KPIs that carry a real signed magnitude
    (_kpi_prefix non-empty) -- used to append a figure to a tier-XI skill-tree
    sentence: a KPI whose delta rounds to a negligible ~zero (e.g. an 'add' of -0.01)
    has no prefix, and the default mode would emit its bare phrase ("to the aiming
    circle size") -- an orphaned, numberless fragment. numbers_only drops those (and
    keeps a bare prefix when the KPI has no description).

    KPI shape verified live (EU 2.3): action._descriptor.kpi -> [KPI], each with
    getDescriptionR() (DynAccessor -> backport.text -> phrase), .type, .value, .name,
    .isDebuff. A MultiModsItem variant (a `modification`) carries its KPI the same
    way. Types seen: 'mul' (percent bonuses) and 'add' (absolute deltas, e.g.
    Kranvagn's top reverse speed) -- an 'add' KPI whose number was dropped by a
    mul-only gate was the "buff missing its number" bug."""
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
            if not numbers_only and not desc:
                continue  # default mode skips the generic unlabeled 'value' KPI
            name = getattr(k, "name", "") or ""
            unit = _param_unit(name) if (getattr(k, "type", "") or "") == "add" else ""
            value_str = (prefix + " " + unit).strip() if unit else prefix
            is_debuff = _resolve_is_debuff(name, bool(getattr(k, "isDebuff", False)))
            record = _fmt.kpi_record(
                _param_icon(name), is_debuff, value_str, desc)
            lines.append(record)
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
