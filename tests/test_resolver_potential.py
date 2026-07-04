# -*- coding: utf-8 -*-
from wgmod_research.domain import types as t
from wgmod_research.domain.resolvers import potential


def _snap(vehicle_xp=100000, free_xp=50000):
    return t.VehicleSnapshot(tier=10, is_elite=True,
                             vehicle_xp=vehicle_xp, free_xp=free_xp)


def test_axis_is_zero_to_fixed_tier_xi_price():
    res = potential.resolve(_snap())
    assert res["scale_min"] == 0
    assert res["scale_max"] == potential.POTENTIAL_TIER_XI_XP == 325000


def test_single_milestone_tick_at_target():
    res = potential.resolve(_snap())
    assert len(res["ticks"]) == 1
    tk = res["ticks"][0]
    assert tk.xp_position == 325000
    assert tk.xp_required == 325000
    # name/icon/caption are widget-owned presentation (set in JS), not domain.
    assert tk.name == ""
    assert tk.icon == ""
    assert tk.category == "vehicle"


def test_milestone_tick_is_not_clickable():
    # No real item to research -> action_id 0 keeps the JS from wiring a command.
    assert potential.resolve(_snap())["ticks"][0].action_id == 0


def test_affordable_when_banked_xp_reaches_target():
    # spendable = vehicle_xp + free_xp; >= target -> affordable (bright milestone).
    assert potential.resolve(_snap(vehicle_xp=300000, free_xp=25000))["ticks"][0].affordable is True
    assert potential.resolve(_snap(vehicle_xp=300000, free_xp=24999))["ticks"][0].affordable is False


def test_none_xp_fields_coerce_to_zero():
    # Defensive: a snapshot with None XP must not raise (fails soft to not-affordable).
    snap = t.VehicleSnapshot(tier=10, is_elite=True, vehicle_xp=None, free_xp=None)
    tk = potential.resolve(snap)["ticks"][0]
    assert tk.affordable is False
