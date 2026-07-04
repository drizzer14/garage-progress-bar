# -*- coding: utf-8 -*-
from wgmod_research.domain import types as t


def resolve(snapshot):
    """Return tech-tree ticks ordered by XP cost (remaining only).

    Each tick is priced at its OWN cost, not a cumulative running total: tech-tree
    items are independently researchable (each carries its own prereqs + own cost),
    so a cheaper sibling must not inflate another item's position or block its
    affordability. (Field mods differ -- they unlock in sequence -- and keep their
    own cumulative resolver.) `xp_cost_effective` is the discounted cost for a
    next-vehicle unlock holding blueprint fragments, defaulting to the raw cost.
    """
    spendable = snapshot.vehicle_xp + snapshot.free_xp
    remaining = [u for u in snapshot.tech_unlocks if not u.researched]
    remaining.sort(key=lambda u: getattr(u, "xp_cost_effective", u.xp_cost))
    ticks = []
    for u in remaining:
        cost = getattr(u, "xp_cost_effective", u.xp_cost)
        # category carries the unlock kind ('vehicle' | 'module') so the view can
        # draw a distinct glyph for the next-tank tick vs module ticks.
        ticks.append(t.Tick(
            xp_position=cost, category=u.kind, icon=u.icon, name=u.name,
            xp_gained=0, xp_required=cost,
            affordable=(cost <= spendable), completed=False,
            locked=not u.prereqs_met, action_id=u.int_cd,
            kind_label=u.kind_label, prereq_names=u.prereq_names))
    return ticks
