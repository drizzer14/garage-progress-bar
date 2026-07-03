# -*- coding: utf-8 -*-
"""PC-only engine adapter: read the live WoT EU 2.3 client into a VehicleSnapshot.

This is the only module that touches game symbols. Every category read is wrapped
in try/except so one unreadable system degrades gracefully (spec section 8): the
category yields a safe empty default and the rest of the bar still renders.

Symbols verified against the EU 2.3 decompiled client source.
"""
import re

from CurrentVehicle import g_currentVehicle
from helpers import dependency
from skeletons.gui.shared import IItemsCache
from items import getTypeOfCompactDescr
from gui.shared.gui_items import GUI_ITEM_TYPE

from wgmod_research._compat import LOG_CURRENT_EXCEPTION, _safe, _safe_int
from wgmod_research.adapter import i18n
from wgmod_research.adapter.prestige_read import read_prestige as _read_prestige
from wgmod_research.adapter.format import (
    roman as _roman, module_big_icon as _module_big_icon,
    skilltree_icon as _skilltree_icon, humanize as _humanize,
    kpi_objs as _kpi_objs, kpi_prefix as _kpi_prefix,
    skilltree_value as _skilltree_value)
from wgmod_research.domain import types as t
from wgmod_research.domain.constants import Category
from wgmod_research.domain.resolvers.fieldmods import max_level


def _items_cache():
    # NOTE: dependency.instance() returns the live service. dependency.descriptor()
    # is only valid as a class attribute (descriptor protocol) and raises if called
    # at module level -- verified in-game.
    return dependency.instance(IItemsCache)


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
        vehicle_int_cd=_safe_int(lambda: veh.intCD, 0))


# --- helpers ---------------------------------------------------------------
# _safe / _safe_int are shared from wgmod_research._compat (imported above).

def _safe_stats():
    try:
        return _items_cache().items.stats
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return None


# Roman numerals for vehicle tiers (1..11). Used for the next-vehicle tooltip
# caption ("Tier IX"), matching the in-game tier notation.
def _unlock_name(cache, int_cd):
    """Localized display name for an unlock id, or "" on any read failure (so one
    bad prerequisite never sinks the whole unlock row)."""
    try:
        return getattr(cache.items.getItemByCD(int_cd), "userName", "") or ""
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return ""


def _read_tech_unlocks(veh, unlocks):
    """Tech-tree unlocks: modules + next vehicles (incl. Tier XI) via the
    vehicle's unlock graph. getUnlocksDescrs() yields (idx, xpCost, intCD, prereqs)."""
    try:
        cache = _items_cache()
        out = []
        for _idx, xp_cost, int_cd, prereqs in veh.getUnlocksDescrs():
            try:
                item_type = getTypeOfCompactDescr(int_cd)
                is_vehicle = item_type == GUI_ITEM_TYPE.VEHICLE
                item = cache.items.getItemByCD(int_cd)
                name = getattr(item, "userName", "") or ""
                # item.icon is the right art for both kinds, as img:// URLs:
                #  - module: the generic module-TYPE glyph (chassis/engine/tower/
                #    gun/radio under img://gui/maps/icons/modules/, 48x48) -- the
                #    same icons the in-battle info panel uses.
                #  - vehicle: the framed tech-tree-node icon (~160x100). NOT
                #    iconSmall -- that's the carousel contour strip, cropped
                #    edge-to-edge so it reads as "cut off".
                icon = getattr(item, "icon", "") or ""
                if not is_vehicle:
                    # Modules only: upgrade the 48x48 type glyph to its 80x80 `Big`
                    # sibling. Vehicle node art is a different, already-large asset.
                    icon = _module_big_icon(icon)
                # Tooltip caption: a next vehicle shows its tier ("Tier IX"); a
                # module shows its type ("Gun"/"Turret"/...). item.level on a
                # vehicle item is its tier. Both are localized to the client language
                # -- the tier word via i18n, the module type via the GUI item's own
                # already-localized `userType` (covers wheels/dual-gun/etc. too).
                if is_vehicle:
                    tier = int(getattr(item, "level", 0) or 0)
                    kind_label = i18n.tier_label(_roman(tier))
                else:
                    kind_label = getattr(item, "userType", "") or ""
            except Exception:
                LOG_CURRENT_EXCEPTION()
                is_vehicle, name, icon, kind_label = False, "", "", ""
            # Names of the prerequisite items not yet researched -> "Requires: ..."
            # in the tooltip. Only resolved when something is actually missing.
            missing = [p for p in prereqs if p not in unlocks]
            prereq_names = [nm for nm in (_unlock_name(cache, p) for p in missing) if nm]
            out.append(t.UnlockItem(
                int_cd=int_cd, name=name, icon=icon, xp_cost=int(xp_cost),
                kind=(Category.VEHICLE if is_vehicle else Category.MODULE),
                researched=(int_cd in unlocks),
                prereqs_met=(not missing),
                kind_label=kind_label, prereq_names=prereq_names))
        return out
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return []


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


def read_purchase_price(int_cd, category, veh_int_cd=0):
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
        # Already owned (bought this session or earlier) -> hide the price.
        if _safe(lambda: bool(item.isInInventory), False) \
                or _safe_int(lambda: item.inventoryCount, 0) > 0:
            return 0
        return _credits_buy_price(item)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return 0


# Localized names a skill-tree node may carry that are too generic to show, and the
# shape of ID-like image names (vehicle-specific 'mechanic' nodes, incl. the final).
_ST_GENERIC_NAMES = frozenset((u"Modification",))
_ST_ID_RE = re.compile(r"(^s\d+_|mechanic|_\d+$)", re.I)


def _skilltree_title(image_name):
    """The node's real localized title from
    R.strings.veh_skill_tree.tooltips.title.dyn(<imageName>) -- the same source the
    Upgrades screen uses (verified live: 's36_mechanic_3' -> 'Hydraulic-Driven
    Rammer', 'invisibilityWhenShooting' -> 'Concealment After Firing'). "" if absent."""
    if not image_name:
        return u""
    try:
        from gui.impl.gen import R
        from gui.impl import backport
        acc = R.strings.veh_skill_tree.tooltips.title.dyn(image_name)
        if acc is not None and acc.isValid():
            return backport.text(acc()) or u""
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return u""


def _skilltree_name(action, node_type):
    """Best readable name for a skill-tree node's tooltip. Tiered, since no single
    source covers every node type (verified live):
      1) the localized tooltips.title keyed by image name -- authoritative, covers
         perks AND signature 'mechanic' nodes;
      2) else a meaningful action loc name -- slot/config nodes give a real one
         ('Alternate Configuration: Auxiliary Loadout');
      3) else the humanized image id for a real perk; else a clean generic."""
    image_name = _safe(lambda: action.getImageName(), "") or ""
    title = _skilltree_title(image_name)
    if title:
        return title
    loc = u""
    try:
        from gui.impl import backport
        acc = action.getLocNameRes()
        loc = (backport.text(acc() if callable(acc) else acc) or u"").strip()
    except Exception:
        loc = u""
    if loc and loc not in _ST_GENERIC_NAMES:
        return loc
    if image_name and not _ST_ID_RE.search(image_name):
        return _humanize(image_name)
    return "Final Upgrade" if node_type == "final" else "Vehicle Upgrade"


def _is_skill_tree(veh):
    """True for a tier-XI "vehicle skill tree" upgrade vehicle (branching
    post-progression, tree id >= VEH_SKILL_TREE_ID_OFFSET=10000). Best-effort:
    any failure -> False, so the vehicle is treated as an ordinary (linear
    field-mod) post-progression vehicle. Verified: gui_items Vehicle exposes
    .postProgression, whose model has isVehSkillTree()."""
    try:
        if not veh.isPostProgressionExists:
            return False
        return bool(veh.postProgression.isVehSkillTree())
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return False


def _read_skill_tree(veh):
    """Aggregate the branching skill tree into
    (total_xp, spent_xp, done, total, final_icon, available). The bar stays a COUNT
    readout (owner directive: non-linear tree), but `available` carries the frontier
    nodes (not received, prerequisites met) as [ProgressionStep] for the clickable
    "Upgrades Available:" chips. done/total
    are the priced, non-ghost nodes unlocked vs. available; final_icon is the
    'final' node's art (img:// URL) for the rightmost tick. total_xp/spent_xp are
    retained for completeness but no longer drive the (count-based) bar.

    Steps come from the same veh.postProgression.iterOrderedSteps() the linear
    reader uses, but here each is a tree node: getPrice().xp, isReceived(),
    getType() ('major'/'special'/'final'/'common'/'ghost'). 'ghost' nodes are
    layout placeholders and zero-price nodes aren't purchasable, so neither counts.
    The 'final' node carries the tank's signature upgrade; its icon comes off the
    action model the same way field mods read theirs (action.getImageName()).

    CRITICAL: the skill tree is a DAG, so iterOrderedSteps() visits a node ONCE PER
    incoming parent edge -- a node with two parents is yielded twice (verified live:
    Hirschkaefer yields 32 steps for 26 unique nodes). We dedupe by stepID, else
    both the cost and the N/M count are inflated. Fully guarded -> (0,...,"") on
    any failure (bar falls back to COMPLETE)."""
    total_xp = 0
    spent_xp = 0
    done = 0
    total = 0
    final_icon = ""
    final_name = ""
    final_xp = 0
    final_effect = ""
    available = []
    seen = set()
    try:
        pp = veh.postProgression
        for step in pp.iterOrderedSteps():
            try:
                step_id = getattr(step, "stepID", None)
                if step_id in seen:
                    continue  # DAG: shared node already counted via another parent
                seen.add(step_id)
                node_type = _safe(lambda: step.getType(), "") or ""
                if node_type == "ghost":
                    continue
                price = step.getPrice()
                xp_cost = int(getattr(price, "xp", 0) or 0)
                if xp_cost <= 0:
                    continue  # not a purchasable upgrade node
                total += 1
                total_xp += xp_cost
                if bool(step.isReceived()):
                    done += 1
                    spent_xp += xp_cost
                elif _safe(lambda: step.isUnlocked(), False):
                    # AVAILABLE FRONTIER: not received but prerequisites met
                    # (isUnlocked() resolves the DAG parent rule). These become the
                    # clickable "Upgrades Available:" chips. isLocked() is its inverse
                    # (prereqs not met) -- verified live: only reachable nodes are
                    # isUnlocked. getImageName() is the perk basename -> full URL via
                    # _skilltree_icon; the localized name is generic, so humanize it.
                    image_name = _safe(lambda: step.action.getImageName(), "") or ""
                    # The node's OWN category (single key from getCategories()) -> its
                    # localized Upgrades-screen sub-heading (e.g. "Category: Firepower",
                    # "Mechanic Upgrade", "Special Upgrade").
                    cat_key = _safe(lambda: sorted(step.action.getCategories())[0], "") or ""
                    available.append(t.ProgressionStep(
                        step_id=step_id, name=_skilltree_name(step.action, node_type),
                        icon=_skilltree_icon(node_type, image_name),
                        xp_cost=xp_cost, unlocked=False,
                        description=_skilltree_effect(step.action),
                        category=i18n.skilltree_category(cat_key)))
                # the signature 'final' upgrade -> its icon + name + cost for the end
                # tick (which carries a tooltip like the available chips).
                if node_type == "final" and not final_icon:
                    action = getattr(step, "action", None)
                    if action is not None:
                        image_name = _safe(lambda: action.getImageName(), "") or ""
                        final_icon = _skilltree_icon("final", image_name)
                        final_name = _skilltree_name(action, "final")
                        final_xp = xp_cost
                        final_effect = _skilltree_effect(action)
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
        return (total_xp, spent_xp, done, total, final_icon, final_name, final_xp,
                final_effect, available)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return 0, 0, 0, 0, "", "", 0, "", []


def _read_post_progression(veh):
    """Read the vehicle's post-progression into (field_mod_steps, fm_done,
    fm_total), all clamped to the tier's level cap (the engine lists greyed
    levels above the cap; skip them). Verified in-game:

      - LEVELED field modifications (FeatureModItem / SimpleModItem /
        RoleSlotModItem): cost XP (price.xp), one per level -> bar hexagons, with
        getLevel() driving the roman numeral.
      - Multi-mod choice slots (MultiModsItem): cost no XP -> NOT on the bar.

    The counter (fm_done / fm_total) spans the LEVELED field mods within the cap
    (one per level, so fm_total == the tier cap) -- received vs total. Multi-mod
    choice slots are not counted. Only meaningful for elite vehicles with
    post-progression."""
    steps = []
    fm_done = 0
    fm_total = 0
    try:
        if not veh.isElite or not veh.isPostProgressionExists:
            return steps, 0, 0
        # Tier-XI vehicles use a branching skill tree, not the linear field-mod
        # ladder this reader assumes -- iterOrderedSteps() there yields tree nodes
        # whose getLevel()/MultiModsItem structure doesn't map to leveled hexagons,
        # so feeding them in here would render a garbled FIELD_MODS bar. They are
        # read separately by _read_skill_tree(); bail so FIELD_MODS never triggers.
        if _is_skill_tree(veh):
            return steps, 0, 0
        cap = max_level(_safe_int(lambda: veh.level, 0))
        pp = veh.postProgression
        # Each level pairs a leveled step (the XP-paid base mod) with a free
        # MultiModsItem holding two SELECTABLE VARIANTS, attached as that step's
        # child (parent = the leveled step's id). Collect those variant pairs
        # first, keyed by parent step id, so we can hang them on the leveled
        # tick's tooltip. (The leveled step's own name is a generic base mod and
        # repeats across levels; the pair is what distinguishes a level.)
        all_steps = list(pp.iterOrderedSteps())
        pairs_by_parent = {}
        for step in all_steps:
            try:
                if type(step.action).__name__ != "MultiModsItem":
                    continue
                parent = _safe(lambda: step.getParentStepID(), None)
                if parent is None:
                    continue
                pairs_by_parent[parent] = _pair_options(step.action)
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
        for step in all_steps:
            try:
                level = int(_safe(lambda: step.getLevel(), 0))
                if level and level > cap:
                    continue  # level not unlockable at this tier (greyed in-game)
                received = bool(step.isReceived())
                # multi-mod choice slots are not "field mod levels": neither bar
                # hexagons nor part of the researched/total counter.
                if type(step.action).__name__ == "MultiModsItem":
                    continue
                # counter spans the leveled field mods within the cap
                fm_total += 1
                if received:
                    fm_done += 1
                price = step.getPrice()
                xp_cost = int(getattr(price, "xp", 0) or 0)
                if xp_cost <= 0:
                    continue  # non-XP leveled step (rare) -> not on the bar
                name, icon = _step_label(step)
                pair = pairs_by_parent.get(step.stepID, [])
                steps.append(t.ProgressionStep(
                    step_id=step.stepID, name=name, icon=icon,
                    xp_cost=xp_cost, unlocked=received,
                    level=level,
                    options=[p[0] for p in pair],
                    option_effects=[p[1] for p in pair],
                    description=_action_effect(step.action)))
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
        return steps, fm_done, fm_total
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return steps, fm_done, fm_total


# The Elite-Levels ("prestige") readers live in adapter/prestige_read.py -- build_snapshot
# calls read_prestige (imported above as _read_prestige). That subsystem shares none of the
# tech/post-progression/skill-tree helpers below, so it carved out cleanly.


def _pair_options(action):
    """[(variant_name, inline_effect), ...] for a MultiModsItem's selectable
    variants, e.g. [("Reinforced Suspension", "+30% to suspension durability\n
    -5% to hull traverse speed"), ...]. Each `modification` resolves its name the
    same way a step action does (getLocNameRes -> DynAccessor -> backport.text) and
    carries its OWN KPI buffs (one per line, TAB-joined here -- the view renders one
    row each) -- so a choice level shows BOTH variants and ALL their buffs, not just
    the base mod's. TAB (not newline) because the VM joins the per-variant strings
    with newline; the view splits variants on \n, then buffs on \t. Best-effort;
    returns [] on failure, ("name", "") when a variant has no readable KPI."""
    out = []
    try:
        from gui.impl import backport
        for mod in (getattr(action, "modifications", None) or []):
            try:
                acc = mod.getLocNameRes()
                res_id = acc() if callable(acc) else acc
                name = backport.text(res_id) or ""
                if not name:
                    continue
                out.append((name, u"\t".join(_kpi_lines(mod))))
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return out


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


def _skilltree_effect(action):
    """Effect/bonus text for a tier-XI skill-tree node.

    Signature 'mechanic' perks (major/final) describe themselves in a localized
    SENTENCE template keyed by image name:
    R.strings.veh_skill_tree.tooltips.description.dyn(<imageName>), e.g. "Reduces gun
    reload time by {value}% in Pillbox mode." We fill {value} with the node's KPI
    magnitude (_skilltree_value) and strip the {colorTagOpen/Close} markup.

    Most nodes' templates are QUALITATIVE with no magnitude slot (e.g. "Reduces gun
    dispersion when your gun is damaged.") -- the number lives only in the KPI. For
    those we append the KPI's signed magnitude line(s) via _kpi_number_lines, e.g.
    "...\n-20% to dispersion of a damaged gun", so the buff shows a figure. Ordinary
    stat perks with NO template fall back to those KPI lines alone ("+10% to hull
    elevation speed"). Feature/role slots (and negligible ~zero deltas) carry no
    numbered KPI line -> "" (unchanged). Verified live (EU 2.3). Never raises."""
    try:
        from gui.impl import backport
        from gui.impl.gen import R
        image_name = _safe(lambda: action.getImageName(), "") or ""
        tmpl = ""
        if image_name:
            rid = R.strings.veh_skill_tree.tooltips.description.dyn(image_name)
            tmpl = backport.text(rid() if callable(rid) else rid) or ""
        kpi_lines = "\n".join(_kpi_number_lines(action))
        if not tmpl or tmpl.startswith("#"):
            return kpi_lines  # no sentence template -> KPI-derived line(s) only
        value = _skilltree_value(action)
        filled = (tmpl.replace("{value}", value)
                      .replace("{colorTagOpen}", "")
                      .replace("{colorTagClose}", "").strip())
        if "{value}" in tmpl:
            # Template embeds its own magnitude slot (signature 'mechanic' perks).
            # If we couldn't classify the KPI (defensive, not seen on EU 2.3), prefer
            # the KPI-derived line so a numberless "by %" doesn't reach the tooltip.
            return filled if value else (kpi_lines or filled)
        # Qualitative sentence, no magnitude slot: append the KPI's signed number(s).
        return (filled + "\n" + kpi_lines) if (filled and kpi_lines) else (filled or kpi_lines)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return ""


def _step_label(step):
    """Display name + icon for a field-mod step via its action model.

    The name is a *resource*, not a plain attribute (verified live, EU 2.3):
    `action.getLocNameRes()` returns a wulf `DynAccessor` which must be CALLED to
    yield the int resource id, which `backport.text()` then resolves to the
    localized string (e.g. "Friction Couplers Replacement (Type 1)").
    `getLocName()` alone is only the raw loc KEY ("clutches_replace_1") -- the
    earlier `action.locName`/`.name` attribute reads didn't exist, so names came
    back empty. Falls back to the raw key, then the step id."""
    name, icon = "", ""
    try:
        action = getattr(step, "action", None)
        if action is None:
            return ("step %s" % getattr(step, "stepID", "?")), ""
        try:
            icon = action.getImageName() or ""
        except Exception:
            icon = ""
        try:
            from gui.impl import backport
            acc = action.getLocNameRes()
            res_id = acc() if callable(acc) else acc
            name = backport.text(res_id) or ""
        except Exception:
            # resource lookup failed -> fall back to the raw loc key.
            try:
                name = action.getLocName() or ""
            except Exception:
                name = ""
        if name:
            return name, icon
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return ("step %s" % getattr(step, "stepID", "?")), icon
