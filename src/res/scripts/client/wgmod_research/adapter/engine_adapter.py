# -*- coding: utf-8 -*-
"""PC-only engine adapter: read the live WoT EU 2.3 client into a VehicleSnapshot.

This is the only module that touches game symbols. Every category read is wrapped
in try/except so one unreadable system degrades gracefully (spec section 8): the
category yields a safe empty default and the rest of the bar still renders.

Symbols verified against the EU 2.3 decompiled client source.
"""
from CurrentVehicle import g_currentVehicle
from helpers import dependency
from skeletons.gui.shared import IItemsCache
from items import getTypeOfCompactDescr
from gui.shared.gui_items import GUI_ITEM_TYPE
from debug_utils import LOG_CURRENT_EXCEPTION

from wgmod_research.domain import types as t
from wgmod_research.domain.resolvers.fieldmods import max_level


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

    is_skill_tree = _is_skill_tree(veh)
    fm_steps, fm_done, fm_total = _read_post_progression(veh)
    st_total_xp, st_spent_xp, st_done, st_total = (
        _read_skill_tree(veh) if is_skill_tree else (0, 0, 0, 0))
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
        skilltree_done=st_done, skilltree_total=st_total)


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
                # item.icon is the right art for both kinds, as img:// URLs:
                #  - module: the generic module-TYPE glyph (chassis/engine/tower/
                #    gun/radio under img://gui/maps/icons/modules/, 48x48) -- the
                #    same icons the in-battle info panel uses.
                #  - vehicle: the framed tech-tree-node icon (~160x100). NOT
                #    iconSmall -- that's the carousel contour strip, cropped
                #    edge-to-edge so it reads as "cut off".
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
    """Aggregate the branching skill tree into (total_xp, spent_xp, done, total) --
    no per-node detail (owner directive). The bar is a monotonic "% upgraded"
    readout: total_xp is the FIXED full-upgrade cost (sum of every priced node),
    spent_xp the cumulative XP already invested (sum of the RECEIVED nodes' prices),
    and done/total the priced, non-ghost nodes unlocked vs. available (the header
    N/M counter).

    Steps come from the same veh.postProgression.iterOrderedSteps() the linear
    reader uses, but here each is a tree node: getPrice().xp, isReceived(),
    getType() ('major'/'special'/'final'/'common'/'ghost'). 'ghost' nodes are
    layout placeholders and zero-price nodes aren't purchasable, so neither counts.

    CRITICAL: the skill tree is a DAG, so iterOrderedSteps() visits a node ONCE PER
    incoming parent edge -- a node with two parents is yielded twice (verified live:
    Hirschkaefer yields 32 steps for 26 unique nodes). We dedupe by stepID, else
    both the cost and the N/M count are inflated. Fully guarded -> (0, 0, 0, 0) on
    any failure (bar falls back to COMPLETE)."""
    total_xp = 0
    spent_xp = 0
    done = 0
    total = 0
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
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
        return total_xp, spent_xp, done, total
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return 0, 0, 0, 0


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
                steps.append(t.ProgressionStep(
                    step_id=step.stepID, name=name, icon=icon,
                    xp_cost=xp_cost, unlocked=received,
                    level=level,
                    options=pairs_by_parent.get(step.stepID, [])))
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
        return steps, fm_done, fm_total
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return steps, fm_done, fm_total


def _prestige_defaults():
    # NB: every key here must match what build_snapshot reads off the prestige
    # dict. A missing key makes build_snapshot raise -> push() bails -> the bar
    # silently keeps the previous vehicle. elite_level_xp is a {level -> xp} map
    # (the success path sets it via _read_level_xp); default to {} so the
    # early-return paths (e.g. non-elite vehicles) stay well-formed.
    return dict(has_prestige=False, elite_level=0, elite_max_level=0,
                elite_current_xp=0, elite_next_xp=0,
                elite_grades=[], elite_rewards=[], elite_level_xp={})


def _read_prestige(veh):
    """Read the Elite-Levels ("prestige") state into the snapshot's prestige
    fields (EU 2.3). Best-effort and fully guarded: any failure degrades to
    has_prestige=False so the bar falls back to the COMPLETE "fully researched"
    badge.

    Sources (gui.prestige.prestige_helpers, deps auto-injected):
      - hasVehiclePrestige(cd, checkElite=True): gate (elite + prestige enabled).
      - getVehiclePrestige(cd) -> (currentLevel, remainingPoints).
      - getCurrentProgress(cd, lvl, pts) -> (currentXP, nextLvlXP); the (-1,-1)
        no-data and (1,1) maxed sentinels are handled downstream in the resolver.
      - getSortedGrades(cd) -> grade thresholds (incl. the synthetic MAX entry,
        whose level is the cap); mapGradeIDToUI maps the mark to (family, sub).
      - getMilestones / getVehicleAchievedMilestones -> tier-exclusive rewards.
    """
    out = _prestige_defaults()
    try:
        from gui.prestige import prestige_helpers as ph
    except Exception:
        return out
    try:
        veh_cd = veh.intCD
        if not ph.hasVehiclePrestige(veh_cd, checkElite=True):
            return out
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return out

    out["has_prestige"] = True
    prestige = _safe(lambda: ph.getVehiclePrestige(veh_cd), None)
    cur_level = _safe_int(lambda: prestige.currentLevel, 0) if prestige is not None else 0
    remaining = _safe_int(lambda: prestige.remainingPoints, 0) if prestige is not None else 0
    out["elite_level"] = cur_level
    cxp, nxp = _safe(lambda: tuple(ph.getCurrentProgress(veh_cd, cur_level, remaining)),
                     (-1, -1))
    out["elite_current_xp"] = int(cxp)
    out["elite_next_xp"] = int(nxp)

    grades = _read_elite_grades(ph, veh_cd)
    out["elite_grades"] = grades
    out["elite_max_level"] = grades[-1].level if grades else cur_level

    out["elite_rewards"] = _read_elite_rewards(ph, veh_cd, cur_level)
    out["elite_level_xp"] = _read_level_xp(ph, veh_cd)
    return out


def _read_level_xp(ph, veh_cd):
    """{level -> cumulative combat XP required to REACH that level}. The prestige
    config's per-vehicle points array holds the per-level cost (points[L-1] = the
    cost of level L; points[0] == 0); cumulative points to reach level L is
    sum(points[0:L]), converted to XP via prestigePointsToXP. Best-effort -> {}."""
    out = {}
    try:
        from skeletons.gui.lobby_context import ILobbyContext
        cfg = dependency.instance(ILobbyContext).getServerSettings().prestigeConfig
        points = cfg.getVehiclePoints(veh_cd)
        if not points:
            return out
        cum = 0
        for i, p in enumerate(points):
            cum += int(p or 0)
            out[i + 1] = int(ph.prestigePointsToXP(cum))
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return out


def _read_elite_grades(ph, veh_cd):
    """[EliteGrade] from getSortedGrades(), each mark mapped to its complex-grade
    family + sub-grade via mapGradeIDToUI. The PrestigeLevelGrade enum value is
    the family id ('iron'..'enamel'/'prestige')."""
    out = []
    try:
        for g in ph.getSortedGrades(veh_cd):
            try:
                grade_enum, sub = ph.mapGradeIDToUI(g.prestigeMarkID)
                family = getattr(grade_enum, "value", str(grade_enum))
                out.append(t.EliteGrade(level=int(g.level), grade=family,
                                        sub=int(sub), main=bool(g.main)))
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return out


def _read_elite_rewards(ph, veh_cd, cur_level):
    """[EliteReward] for the tier-exclusive milestone rewards. Empty unless the
    vehicle's tier enables them (getMilestones non-empty). `achieved` mirrors the
    game's rule: reached AND recorded in the achieved set."""
    out = []
    try:
        milestones = ph.getMilestones(veh_cd) or {}
        if not milestones:
            return out
        achieved = _safe(lambda: ph.getVehicleAchievedMilestones(veh_cd), set()) or set()
        for level in sorted(milestones):
            try:
                is_done = bool(cur_level >= level and level in achieved)
                icon, label, type_label = _read_reward_art(
                    ph, veh_cd, level, milestones, is_done)
                out.append(t.EliteReward(
                    level=int(level), achieved=is_done,
                    icon=icon, label=label, type_label=type_label))
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return out


def _read_reward_art(ph, veh_cd, level, milestones, is_done):
    """(icon_url, name, type_label) for a milestone reward. The reward is a
    customization (2D style / attachment / stat-tracker); its thumbnail is an
    img:// URL: styles expose `.icon` as img://<previewIcon>, others `.iconUrl`
    (getTextureLinkByID -> img://). Falls back to the generic per-type bonus icon,
    then none. Entirely best-effort."""
    icon, label, type_label = "", "", ""
    try:
        from gui.impl.lobby.vehicle_hub.sub_presenters.veh_skill_tree.utils import (
            getPrestigeBonus, PrestigeBonusContext, PrestigeCustomizationBonusUIPacker)
        from gui.impl.gen.view_models.views.lobby.vehicle_hub.views.sub_models.veh_skill_tree.rewards_slot_model import RewardStatus
        from gui.shared.gui_items import getItemTypeID
        state = RewardStatus.ACHIEVED if is_done else RewardStatus.AVAILABLE
        bonus = getPrestigeBonus(milestones, PrestigeBonusContext(veh_cd, level, state))
        if bonus is None:
            return icon, label, type_label
        custs = bonus.getCustomizations()
        if not custs:
            return icon, label, type_label
        c11n = bonus.getC11nItem(custs[0])
        label = _safe(lambda: c11n.userName, "") or ""
        # Prefer an img:// thumbnail; .icon is img:// only for styles.
        candidate = _safe(lambda: c11n.icon, "") or ""
        if not candidate.startswith("img://"):
            candidate = _safe(lambda: c11n.iconUrl, "") or candidate
        if not candidate.startswith("img://"):
            candidate = _safe(lambda: c11n.getBonusIcon("small"), "") or candidate
        icon = candidate if candidate.startswith("img://") else ""
        item_type_id = _safe(lambda: getItemTypeID(custs[0].get("custType")), None)
        if item_type_id is not None:
            title, _desc = PrestigeCustomizationBonusUIPacker.getTextInfoByItemTypeID(item_type_id)
            type_label = title or ""
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return icon, label, type_label


def _pair_options(action):
    """The selectable variant names of a MultiModsItem's pair, e.g.
    ["Anti-Reflective Optics Coating", "External Vision System"]. Each entry in
    action.modifications resolves its display name the same way a step action
    does (getLocNameRes() -> DynAccessor -> backport.text). Best-effort; returns
    [] on any failure."""
    out = []
    try:
        from gui.impl import backport
        for mod in (getattr(action, "modifications", None) or []):
            try:
                acc = mod.getLocNameRes()
                res_id = acc() if callable(acc) else acc
                name = backport.text(res_id) or ""
                if name:
                    out.append(name)
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return out


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
