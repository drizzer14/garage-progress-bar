# -*- coding: utf-8 -*-
from wgmod_research.domain import types as t


def test_mode_constants_are_distinct():
    modes = {t.Mode.TECH_TREE, t.Mode.FIELD_MODS, t.Mode.COMPLETE}
    assert len(modes) == 3


def test_tick_holds_fields():
    tick = t.Tick(xp_position=1500, category="techtree", icon="gun.png",
                  name="Gun X", xp_gained=0, xp_required=1500,
                  affordable=False, completed=False)
    assert tick.xp_position == 1500
    assert tick.category == "techtree"
    assert tick.affordable is False
    assert tick.locked is False  # defaults to unlocked


def test_tick_locked_field():
    tick = t.Tick(xp_position=0, category="techtree", icon="", name="",
                  xp_gained=0, xp_required=0, affordable=True, completed=False,
                  locked=True)
    assert tick.locked is True


def test_model_defaults_empty_ticks():
    m = t.ResearchProgressModel(mode=t.Mode.TECH_TREE, scale_min=0, scale_max=0,
                                fill_vehicle=0, fill_free=0, ticks=[])
    assert m.ticks == []
    assert m.mode == t.Mode.TECH_TREE
    assert m.fill_vehicle == 0
    assert m.fill_free == 0


def test_snapshot_list_defaults_are_independent():
    a = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=0, free_xp=0)
    b = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=0, free_xp=0)
    assert a.tech_unlocks == []
    assert a.field_mod_steps == []
    # distinct instances must not share the same default list object
    a.tech_unlocks.append("x")
    assert b.tech_unlocks == []
