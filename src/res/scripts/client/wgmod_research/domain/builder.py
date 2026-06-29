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


def build_model(snapshot):
    fill_vehicle = snapshot.vehicle_xp
    fill_free = snapshot.free_xp
    fm_done = snapshot.fieldmods_done
    fm_total = snapshot.fieldmods_total
    veh_class = snapshot.vehicle_class

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
        return t.ResearchProgressModel(
            mode=t.Mode.TECH_TREE, scale_min=0, scale_max=_max_pos(ticks, 0),
            fill_vehicle=fill_vehicle, fill_free=fill_free, ticks=ticks,
            vehicle_class=veh_class)

    # Tier-XI "vehicle skill tree" upgrade: a branching post-progression tree, so
    # the linear FIELD_MODS reader doesn't apply (the adapter reads it as an
    # aggregate instead). Show the cumulative "% upgraded" readout: axis = the fixed
    # full-upgrade cost, fill = the XP already invested (a SINGLE segment, so it
    # rides the vehicle slot with the free slot empty -- like the elite modes).
    # resolve() returns None once fully upgraded, so the bar then falls through to
    # the prestige / COMPLETE branches like any other elite vehicle.
    if snapshot.is_skill_tree:
        st = skilltree.resolve(snapshot)
        if st is not None:
            return t.ResearchProgressModel(
                mode=t.Mode.SKILL_TREE, scale_min=st["scale_min"],
                scale_max=st["scale_max"], fill_vehicle=st["fill"],
                fill_free=0, ticks=[],
                fieldmods_done=st["done"], fieldmods_total=st["total"],
                vehicle_class=veh_class)

    # Nothing left to research: show remaining Field Modifications, plus the
    # researched/total field-mod-level counter in the header.
    fm_ticks = fieldmods.resolve(snapshot)
    if fm_ticks:
        return t.ResearchProgressModel(
            mode=t.Mode.FIELD_MODS, scale_min=0, scale_max=_max_pos(fm_ticks, 0),
            fill_vehicle=fill_vehicle, fill_free=fill_free, ticks=fm_ticks,
            fieldmods_done=fm_done, fieldmods_total=fm_total, vehicle_class=veh_class)

    # Fully researched. If the vehicle has Elite-Levels (prestige) data, show
    # the prestige progression instead of the static "fully researched" badge.
    if snapshot.has_prestige:
        # Tier-exclusive reward roadmap takes priority while any reward is
        # unearned; once all are earned, fall through to the grade band.
        reward = elite.resolve_reward_track(snapshot)
        if reward is not None and reward["any_unearned"]:
            return _elite_model(t.Mode.ELITE_REWARDS, reward, snapshot)
        band = elite.resolve_grade_band(snapshot)
        if band is not None:
            return _elite_model(t.Mode.ELITE, band, snapshot)

    # nothing left to research and no prestige data: COMPLETE (elite badge).
    return t.ResearchProgressModel(
        mode=t.Mode.COMPLETE, scale_min=0, scale_max=0,
        fill_vehicle=fill_vehicle, fill_free=fill_free, ticks=[],
        fieldmods_done=fm_done, fieldmods_total=fm_total, vehicle_class=veh_class)


def _elite_model(mode, res, snapshot):
    """Build an ELITE / ELITE_REWARDS model from a resolver result dict. The
    band uses a single fill segment (vehicle slot) so fill_free stays 0; the
    readout is cumulative combat XP."""
    return t.ResearchProgressModel(
        mode=mode, scale_min=res["scale_min"], scale_max=res["scale_max"],
        fill_vehicle=res["fill"], fill_free=0, ticks=res["ticks"],
        vehicle_class=snapshot.vehicle_class,
        elite_level=res["level"], elite_max_level=res["max_level"],
        elite_grade=res.get("grade", ""), elite_sub=res.get("sub", 0),
        combat_xp=snapshot.vehicle_xp)
