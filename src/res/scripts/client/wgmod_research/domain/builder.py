# -*- coding: utf-8 -*-
"""Mode state machine for the EU 2.3 model.

Per selected vehicle:
- not elite (something left to unlock) -> TECH_TREE (modules + next vehicles).
- elite (fully researched) with remaining field-mod steps -> FIELD_MODS.
- elite and no field mods remaining (or none exist) -> COMPLETE (full bar).

Fill is the player's spendable XP shown as two stacked segments: vehicle XP
first, then global free XP. The view treats a scale_min == scale_max range as
100% (guard divide-by-zero).
"""
from wgmod_research.domain import types as t
from wgmod_research.domain.resolvers import techtree, fieldmods


def _max_pos(ticks, default):
    return max([tk.xp_position for tk in ticks]) if ticks else default


def build_model(snapshot):
    fill_vehicle = snapshot.vehicle_xp
    fill_free = snapshot.free_xp

    if not snapshot.is_elite:
        ticks = techtree.resolve(snapshot)
        return t.ResearchProgressModel(
            mode=t.Mode.TECH_TREE, scale_min=0, scale_max=_max_pos(ticks, 0),
            fill_vehicle=fill_vehicle, fill_free=fill_free, ticks=ticks)

    # elite = fully researched: show remaining Field Modifications ("upgrades").
    fm_ticks = fieldmods.resolve(snapshot)
    if fm_ticks:
        return t.ResearchProgressModel(
            mode=t.Mode.FIELD_MODS, scale_min=0, scale_max=_max_pos(fm_ticks, 0),
            fill_vehicle=fill_vehicle, fill_free=fill_free, ticks=fm_ticks)

    # nothing left to research or upgrade.
    return t.ResearchProgressModel(
        mode=t.Mode.COMPLETE, scale_min=0, scale_max=0,
        fill_vehicle=fill_vehicle, fill_free=fill_free, ticks=[])
