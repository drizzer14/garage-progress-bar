# -*- coding: utf-8 -*-
from wgmod_research.domain import types as t
from wgmod_research.domain.resolvers import techtree


def _unlock(cd, cost, researched=False, prereqs_met=True):
    return t.UnlockItem(int_cd=cd, name="i%d" % cd, icon="i%d.png" % cd,
                        xp_cost=cost, kind="module",
                        researched=researched, prereqs_met=prereqs_met)


def test_skips_researched_and_orders_cumulatively():
    snap = t.VehicleSnapshot(
        tier=5, is_elite=False, vehicle_xp=1000, free_xp=500,
        tech_unlocks=[_unlock(1, 800, researched=True),
                      _unlock(2, 2000),
                      _unlock(3, 600)])
    ticks = techtree.resolve(snap)
    # researched item excluded; remaining ordered by cost: 600 then 2000
    assert [tk.xp_required for tk in ticks] == [600, 2000]
    # cumulative positions: 600, then 2600
    assert [tk.xp_position for tk in ticks] == [600, 2600]


def test_affordable_against_spendable():
    snap = t.VehicleSnapshot(
        tier=5, is_elite=False, vehicle_xp=1000, free_xp=500,  # spendable = 1500
        tech_unlocks=[_unlock(3, 600), _unlock(2, 2000)])
    ticks = techtree.resolve(snap)
    # 600 affordable (<=1500), 2600 not
    assert [tk.affordable for tk in ticks] == [True, False]
    assert all(tk.category == "techtree" for tk in ticks)


def test_locked_reflects_prereqs_met():
    snap = t.VehicleSnapshot(
        tier=5, is_elite=False, vehicle_xp=1000, free_xp=500,
        tech_unlocks=[_unlock(3, 600, prereqs_met=True),
                      _unlock(2, 2000, prereqs_met=False)])
    ticks = techtree.resolve(snap)
    # ordered by cost: 600 (prereqs met -> not locked), 2000 (unmet -> locked)
    assert [tk.locked for tk in ticks] == [False, True]
