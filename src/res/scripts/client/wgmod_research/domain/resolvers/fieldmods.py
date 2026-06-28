# -*- coding: utf-8 -*-
from wgmod_research.domain import types as t


def resolve(snapshot, start_position=0):
    """Field-mod ticks, cumulative from start_position (remaining only).

    Field-mod steps are ordered by their natural step sequence (list order),
    not re-sorted by cost.
    """
    spendable = snapshot.vehicle_xp + snapshot.free_xp
    ticks = []
    running = start_position
    for step in snapshot.field_mod_steps:
        if step.unlocked:
            continue
        running += step.xp_cost
        # Field-mod steps carry no prerequisite info in the snapshot, so locked
        # stays at its default (False); only tech-tree ticks can be locked.
        ticks.append(t.Tick(
            xp_position=running, category="fieldmod", icon=step.icon, name=step.name,
            xp_gained=0, xp_required=step.xp_cost,
            affordable=(running <= spendable), completed=False))
    return ticks
