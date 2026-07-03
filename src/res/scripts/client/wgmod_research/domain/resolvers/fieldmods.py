# -*- coding: utf-8 -*-
from wgmod_research.domain import types as t
from wgmod_research.domain.constants import Category


def max_level(tier):
    """Number of field-modification levels actually unlockable at a given tier
    (EU 2.3). The post-progression tree always exposes all 8 levels -- the
    unavailable ones are shown greyed in-game -- so we clamp to the tier cap.
    Field mods don't exist below tier 6, so the floor is 5."""
    if tier >= 10:
        return 8
    if tier == 9:
        return 7
    if tier == 8:
        return 6
    return 5  # tiers 6-7


def resolve(snapshot, start_position=0):
    """Field-mod ticks, cumulative from start_position (remaining only).

    Field-mod steps are ordered by their natural step sequence (list order),
    not re-sorted by cost. Levels beyond the tier cap are skipped (the engine
    lists them but they aren't unlockable at this tier).
    """
    spendable = snapshot.vehicle_xp + snapshot.free_xp
    cap = max_level(snapshot.tier)
    ticks = []
    running = start_position
    for step in snapshot.field_mod_steps:
        if step.unlocked:
            continue
        if step.level and step.level > cap:
            continue
        running += step.xp_cost
        # Field-mod steps carry no prerequisite info in the snapshot, so locked
        # stays at its default (False); only tech-tree ticks can be locked.
        # level -> the roman numeral the view shows in the hexagon glyph.
        ticks.append(t.Tick(
            xp_position=running, category=Category.FIELDMOD, icon=step.icon, name=step.name,
            xp_gained=0, xp_required=step.xp_cost,
            affordable=(running <= spendable), completed=False,
            level=step.level, options=step.options, action_id=step.step_id,
            effect=step.description, option_effects=step.option_effects))
    return ticks
