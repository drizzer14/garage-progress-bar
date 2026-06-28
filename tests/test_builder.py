# -*- coding: utf-8 -*-
from wgmod_research.domain import types as t
from wgmod_research.domain.builder import build_model


def _u(cd, cost, researched=False, kind="module"):
    return t.UnlockItem(cd, "u%d" % cd, "u%d.png" % cd, cost, kind, researched, True)


def _step(sid, cost, unlocked=False):
    return t.ProgressionStep(sid, "fm%d" % sid, "fm%d.png" % sid, cost, unlocked)


def test_not_elite_is_tech_tree():
    snap = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=500, free_xp=0,
                             tech_unlocks=[_u(1, 1000), _u(2, 500)])
    m = build_model(snap)
    assert m.mode == t.Mode.TECH_TREE
    assert m.scale_min == 0
    assert m.scale_max == 1500          # cumulative max
    assert m.fill_vehicle == 500
    assert m.fill_free == 0
    assert [tk.xp_position for tk in m.ticks] == [500, 1500]
    assert all(tk.category == "techtree" for tk in m.ticks)


def test_tech_tree_includes_tier_xi_vehicle_unlock():
    # Tier XI is an ordinary tech-tree vehicle unlock researched with XP.
    snap = t.VehicleSnapshot(
        tier=10, is_elite=False, vehicle_xp=0, free_xp=0,
        tech_unlocks=[_u(1, 5000, kind="module"),
                      _u(99, 325000, kind="vehicle")])  # the Tier XI successor
    m = build_model(snap)
    assert m.mode == t.Mode.TECH_TREE
    assert [tk.xp_position for tk in m.ticks] == [5000, 330000]
    assert m.scale_max == 330000


def test_tech_tree_fill_is_two_segments():
    snap = t.VehicleSnapshot(tier=5, is_elite=False, vehicle_xp=800, free_xp=300,
                             tech_unlocks=[_u(1, 600), _u(2, 5000)])
    m = build_model(snap)
    # spendable = 1100 affords the 600 tick, not the 5600 tick
    assert m.fill_vehicle == 800
    assert m.fill_free == 300
    assert [tk.affordable for tk in m.ticks] == [True, False]


def test_elite_with_field_mods_is_field_mods_mode():
    snap = t.VehicleSnapshot(
        tier=10, is_elite=True, vehicle_xp=1000, free_xp=200,
        field_mod_steps=[_step(1, 2000), _step(2, 4000)])
    m = build_model(snap)
    assert m.mode == t.Mode.FIELD_MODS
    assert [tk.category for tk in m.ticks] == ["fieldmod", "fieldmod"]
    assert [tk.xp_position for tk in m.ticks] == [2000, 6000]
    assert m.scale_min == 0
    assert m.scale_max == 6000
    assert m.fill_vehicle == 1000
    assert m.fill_free == 200


def test_elite_partial_field_mods_skips_unlocked():
    snap = t.VehicleSnapshot(
        tier=10, is_elite=True, vehicle_xp=0, free_xp=0,
        field_mod_steps=[_step(1, 1000, unlocked=True),   # done, skip
                         _step(2, 3000)])
    m = build_model(snap)
    assert m.mode == t.Mode.FIELD_MODS
    assert [tk.xp_position for tk in m.ticks] == [3000]
    assert m.scale_max == 3000


def test_elite_field_mods_all_done_is_complete():
    snap = t.VehicleSnapshot(
        tier=9, is_elite=True, vehicle_xp=0, free_xp=0,
        field_mod_steps=[_step(1, 2000, unlocked=True)])  # done
    m = build_model(snap)
    assert m.mode == t.Mode.COMPLETE
    assert m.ticks == []
    assert m.scale_min == m.scale_max     # zero-width range -> view renders 100%


def test_elite_with_no_field_mods_is_complete():
    snap = t.VehicleSnapshot(tier=8, is_elite=True, vehicle_xp=0, free_xp=0)
    m = build_model(snap)
    assert m.mode == t.Mode.COMPLETE
    assert m.ticks == []
