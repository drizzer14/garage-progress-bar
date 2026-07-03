# -*- coding: utf-8 -*-
"""PC-only reader for the Elite-Levels ("prestige") subsystem (EU 2.3).

Extracted from engine_adapter.py: this is the single most self-contained read
subsystem -- it touches only gui.prestige.prestige_helpers (+ the lobby context for the
per-level XP costs) and shares none of engine_adapter's tech/post-progression helpers, so
it carves out cleanly with no import cycle. engine_adapter.build_snapshot() calls
read_prestige() and maps the returned dict onto the snapshot's prestige fields.

Best-effort and fully guarded throughout: any failure degrades to has_prestige=False so
the bar falls back to the COMPLETE "fully researched" badge. All game symbols are imported
LOCALLY inside the functions (so the module imports under pytest too, like the rest of the
adapter's engine-coupled readers -- though it's exercised only live).
"""
from helpers import dependency

from wgmod_research._compat import LOG_CURRENT_EXCEPTION, _safe, _safe_int
from wgmod_research.domain import types as t


def _prestige_defaults():
    # NB: every key here must match what build_snapshot reads off the prestige
    # dict. A missing key makes build_snapshot raise -> push() bails -> the bar
    # silently keeps the previous vehicle. elite_level_xp is a {level -> xp} map
    # (the success path sets it via _read_level_xp); default to {} so the
    # early-return paths (e.g. non-elite vehicles) stay well-formed.
    return dict(has_prestige=False, elite_level=0, elite_max_level=0,
                elite_current_xp=0, elite_next_xp=0,
                elite_grades=[], elite_rewards=[], elite_level_xp={})


def read_prestige(veh):
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
            # Prefer the largest bonus-icon variant; fall back to "small" if "big"
            # isn't a valid size arg (guards against a regressed no-icon result).
            big = _safe(lambda: c11n.getBonusIcon("big"), "") or ""
            candidate = big if big.startswith("img://") \
                else (_safe(lambda: c11n.getBonusIcon("small"), "") or candidate)
        icon = candidate if candidate.startswith("img://") else ""
        item_type_id = _safe(lambda: getItemTypeID(custs[0].get("custType")), None)
        if item_type_id is not None:
            title, _desc = PrestigeCustomizationBonusUIPacker.getTextInfoByItemTypeID(item_type_id)
            type_label = title or ""
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return icon, label, type_label
