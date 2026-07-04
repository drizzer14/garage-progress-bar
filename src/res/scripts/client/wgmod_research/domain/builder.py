# -*- coding: utf-8 -*-
"""Mode state machine for the EU 2.3 model.

Per selected vehicle:
- not elite (something left to unlock) -> TECH_TREE (modules + next vehicles).
- elite (fully researched) with remaining field-mod steps -> FIELD_MODS.
- elite + prestige + tier-exclusive rewards still to earn -> ELITE_REWARDS
  (the reward roadmap shown first).
- elite + prestige (rewards all earned / none) -> ELITE (grade-band progression).
- elite, no prestige data -> COMPLETE ("fully researched" badge fallback).

Fill is the player's spendable XP shown as two stacked segments: vehicle XP
first, then global free XP. The view treats a scale_min == scale_max range as
100% (guard divide-by-zero). The ELITE/ELITE_REWARDS modes reuse the same
scale/ticks/fill axis with a single segment (fill_free = 0).
"""
from wgmod_research.domain import types as t
from wgmod_research.domain.resolvers import techtree, fieldmods, elite, skilltree


def _max_pos(ticks, default):
    return max([tk.xp_position for tk in ticks]) if ticks else default


def _on(enabled, mode):
    """Whether `mode` is enabled. `enabled` is a set of Mode strings the user has
    left ON; None means "all on" (the default, so callers/tests that pass no toggle
    set behave exactly as before). A mode absent from a non-None set is OFF."""
    return enabled is None or mode in enabled


def bar_visible(overlay_closed, hide_always, hide_when_complete, mode, in_garage):
    """Whether the bar should render, combining the engine state (a tank-setup
    overlay open -> overlay_closed is False; the plain garage is mounted ->
    in_garage is True) with the two user settings. Pure and engine-free so it
    unit-tests on plain inputs.

    - hide_always: master switch -> never show.
    - Mode.HIDDEN: the vehicle's resolved mode is turned off by a per-mode user
      toggle (see build_model) -> never show.
    - in_garage: show ONLY in the plain garage view (fail-closed allowlist -- any
      other lobby view, or an unreadable view signal, hides the bar).
    - hide_when_complete: hide only on fully-progressed vehicles (Mode.COMPLETE).
    - otherwise follow the overlay state (hidden while a setup overlay is open)."""
    if hide_always:
        return False
    if mode == t.Mode.HIDDEN:
        return False
    if not in_garage:
        return False
    if hide_when_complete and mode == t.Mode.COMPLETE:
        return False
    return overlay_closed


def build_model(snapshot, enabled=None):
    """`enabled` is the set of Mode strings the user has left ON (None = all on).
    The mode is resolved by the usual priority chain; if the resolved mode is OFF,
    the bar is HIDDEN -- there is NO fall-through to a lower-priority mode, and
    COMPLETE is reached only when the vehicle is genuinely done (no branch matched)."""
    fill_vehicle = snapshot.vehicle_xp
    fill_free = snapshot.free_xp
    # Total spendable XP, set on every model below so the view can show per-item
    # affordability in any mode (skill_tree fill is a node count, not XP).
    spendable = fill_vehicle + fill_free
    # Historical avg combat XP/battle, carried onto every model so the view can
    # estimate "battles remaining" beside a tooltip's XP shortfall (0 hides it).
    avg_xp = snapshot.avg_battle_xp
    fm_done = snapshot.fieldmods_done
    fm_total = snapshot.fieldmods_total
    veh_class = snapshot.vehicle_class

    def _hidden():
        # The vehicle's resolved mode is toggled off: a placeholder model whose only
        # job is to carry Mode.HIDDEN so bar_visible() hides the bar (the view never
        # renders it). Carries the shared fill/counter fields for consistency.
        return t.ResearchProgressModel(
            mode=t.Mode.HIDDEN, scale_min=0, scale_max=0,
            fill_vehicle=fill_vehicle, fill_free=fill_free, ticks=[],
            fieldmods_done=fm_done, fieldmods_total=fm_total, vehicle_class=veh_class,
            spendable_xp=spendable, avg_battle_xp=avg_xp)

    def _emit(mode, model):
        # Honor the per-mode user toggle: a mode this vehicle RESOLVED to but which the
        # user turned off hides the bar -- there is NO fall-through to a lower-priority
        # mode (see build_model's docstring). Otherwise emit the resolved model.
        return model if _on(enabled, mode) else _hidden()

    # Research takes priority: while ANY tech unlock (module or next vehicle) is
    # still unresearched, show the tech tree -- even on a vehicle the account
    # already counts as elite. veh.isElite is merely eliteVehicles membership and
    # can be True while modules remain unresearched; only isFullyElite means
    # nothing is left (Vehicle.py:304-305). Gating on is_elite wrongly showed
    # Field Modifications for still-researchable elite tanks (e.g. Leopard 1).
    # techtree.resolve already returns remaining-only ticks, so its emptiness is
    # the exact "nothing left to research" signal.
    ticks = techtree.resolve(snapshot)
    if ticks:
        return _emit(t.Mode.TECH_TREE, t.ResearchProgressModel(
            mode=t.Mode.TECH_TREE, scale_min=0, scale_max=_max_pos(ticks, 0),
            fill_vehicle=fill_vehicle, fill_free=fill_free, ticks=ticks,
            vehicle_class=veh_class, spendable_xp=spendable, avg_battle_xp=avg_xp))

    # Tier-XI "vehicle skill tree" upgrade: a branching post-progression tree, so
    # the linear FIELD_MODS reader doesn't apply. The tree is non-linear, so the bar
    # is a COUNT readout: axis = total upgrade nodes, fill = nodes unlocked (a SINGLE
    # segment riding the vehicle slot, free slot empty -- like the elite modes), with
    # one tick per node and the signature 'final' upgrade flagged at the end.
    # resolve() returns None once fully upgraded, so the bar then falls through to
    # the prestige / COMPLETE branches like any other elite vehicle.
    if snapshot.is_skill_tree:
        st = skilltree.resolve(snapshot)
        if st is not None:
            return _emit(t.Mode.SKILL_TREE, t.ResearchProgressModel(
                mode=t.Mode.SKILL_TREE, scale_min=st["scale_min"],
                scale_max=st["scale_max"], fill_vehicle=st["fill"],
                fill_free=0, ticks=st["ticks"],
                fieldmods_done=st["done"], fieldmods_total=st["total"],
                vehicle_class=veh_class, spendable_xp=spendable, avg_battle_xp=avg_xp,
                avail_upgrades=st.get("avail_upgrades", [])))

    # Nothing left to research: show remaining Field Modifications, plus the
    # researched/total field-mod-level counter in the header.
    fm_ticks = fieldmods.resolve(snapshot)
    if fm_ticks:
        return _emit(t.Mode.FIELD_MODS, t.ResearchProgressModel(
            mode=t.Mode.FIELD_MODS, scale_min=0, scale_max=_max_pos(fm_ticks, 0),
            fill_vehicle=fill_vehicle, fill_free=fill_free, ticks=fm_ticks,
            fieldmods_done=fm_done, fieldmods_total=fm_total, vehicle_class=veh_class,
            spendable_xp=spendable, avg_battle_xp=avg_xp))

    # Fully researched. If the vehicle has Elite-Levels (prestige) data, show
    # the prestige progression instead of the static "fully researched" badge.
    if snapshot.has_prestige:
        # Tier-exclusive reward roadmap takes priority while any reward is
        # unearned; once all are earned, fall through to the grade band.
        reward = elite.resolve_reward_track(snapshot)
        if reward is not None and reward["any_unearned"]:
            return _emit(t.Mode.ELITE_REWARDS,
                         _elite_model(t.Mode.ELITE_REWARDS, reward, snapshot))
        band = elite.resolve_grade_band(snapshot)
        if band is not None:
            return _emit(t.Mode.ELITE, _elite_model(t.Mode.ELITE, band, snapshot))

    # nothing left to research and no prestige data: COMPLETE (elite badge).
    return t.ResearchProgressModel(
        mode=t.Mode.COMPLETE, scale_min=0, scale_max=0,
        fill_vehicle=fill_vehicle, fill_free=fill_free, ticks=[],
        fieldmods_done=fm_done, fieldmods_total=fm_total, vehicle_class=veh_class,
        spendable_xp=spendable, avg_battle_xp=avg_xp)


def _elite_model(mode, res, snapshot):
    """Build an ELITE / ELITE_REWARDS model from a resolver result dict. The
    band uses a single fill segment (vehicle slot) so fill_free stays 0; the
    readout is cumulative combat XP."""
    # The prestige/Elite-Levels system tracks the vehicle's CUMULATIVE combat XP
    # (total earned toward Elite Levels), NOT the unspent research XP (vehicle_xp).
    # Reconstruct it from the snapshot: cumulative XP to reach the current level
    # (elite_level_xp[level]) + progress within that level (elite_current_xp). The
    # latter uses -1 as a "no data" sentinel, so floor it at 0. This feeds both the
    # header readout and the per-tick "<have> / <need> XP" tooltip, whose need is
    # the cumulative combat XP to reach each grade.
    level_xp = snapshot.elite_level_xp or {}
    progress = snapshot.elite_current_xp or 0
    if progress < 0:
        progress = 0
    combat = int(level_xp.get(snapshot.elite_level, 0) or 0) + progress
    return t.ResearchProgressModel(
        mode=mode, scale_min=res["scale_min"], scale_max=res["scale_max"],
        fill_vehicle=res["fill"], fill_free=0, ticks=res["ticks"],
        vehicle_class=snapshot.vehicle_class,
        elite_level=res["level"], elite_max_level=res["max_level"],
        elite_grade=res.get("grade", ""), elite_sub=res.get("sub", 0),
        elite_current_icon=elite.current_grade_icon(snapshot),
        combat_xp=combat,
        spendable_xp=snapshot.vehicle_xp + snapshot.free_xp,
        avg_battle_xp=snapshot.avg_battle_xp)
