# -*- coding: utf-8 -*-
from wgmod_research.domain import types as t
from wgmod_research.domain.resolvers import techtree


def _unlock(cd, cost, researched=False, prereqs_met=True, kind="module",
            kind_label="", prereq_names=None):
    return t.UnlockItem(int_cd=cd, name="i%d" % cd, icon="i%d.png" % cd,
                        xp_cost=cost, kind=kind,
                        researched=researched, prereqs_met=prereqs_met,
                        kind_label=kind_label, prereq_names=prereq_names)


def test_skips_researched_and_orders_by_cost():
    snap = t.VehicleSnapshot(
        tier=5, is_elite=False, vehicle_xp=1000, free_xp=500,
        tech_unlocks=[_unlock(1, 800, researched=True),
                      _unlock(2, 2000),
                      _unlock(3, 600)])
    ticks = techtree.resolve(snap)
    # researched item excluded; remaining ordered by cost: 600 then 2000
    assert [tk.xp_required for tk in ticks] == [600, 2000]
    # each tick sits at its OWN cost (not a cumulative running total)
    assert [tk.xp_position for tk in ticks] == [600, 2000]


def test_affordable_against_spendable():
    snap = t.VehicleSnapshot(
        tier=5, is_elite=False, vehicle_xp=1000, free_xp=500,  # spendable = 1500
        tech_unlocks=[_unlock(3, 600), _unlock(2, 2000)])
    ticks = techtree.resolve(snap)
    # 600 affordable (<=1500), 2000 not
    assert [tk.affordable for tk in ticks] == [True, False]


def test_effective_cost_used_for_position_and_affordability():
    # A next-vehicle unlock discounted by blueprint fragments: raw 2000, effective 1200.
    # Position, affordability and the tooltip cost all follow the effective cost.
    disc = t.UnlockItem(int_cd=9, name="Next", icon="n.png", xp_cost=2000,
                        kind="vehicle", researched=False, prereqs_met=True,
                        xp_cost_effective=1200)
    snap = t.VehicleSnapshot(
        tier=9, is_elite=False, vehicle_xp=1000, free_xp=500,  # spendable = 1500
        tech_unlocks=[disc])
    ticks = techtree.resolve(snap)
    assert ticks[0].xp_position == 1200
    assert ticks[0].xp_required == 1200
    assert ticks[0].affordable is True   # 1200 <= 1500 (raw 2000 would be unaffordable)


def test_per_item_pricing_not_cumulative():
    # Two independently-researchable modules whose costs each fit the budget but
    # whose SUM does not. The old cumulative model placed the second at 1700 and
    # marked it unaffordable; per-item pricing keeps both affordable at own cost.
    snap = t.VehicleSnapshot(
        tier=5, is_elite=False, vehicle_xp=1000, free_xp=500,  # spendable = 1500
        tech_unlocks=[_unlock(1, 800), _unlock(2, 900)])
    ticks = techtree.resolve(snap)
    assert [tk.xp_position for tk in ticks] == [800, 900]
    assert [tk.affordable for tk in ticks] == [True, True]


def test_category_reflects_unlock_kind():
    snap = t.VehicleSnapshot(
        tier=10, is_elite=False, vehicle_xp=0, free_xp=0,
        tech_unlocks=[_unlock(1, 600, kind="module"),
                      _unlock(2, 2000, kind="vehicle")])  # next-tank unlock
    ticks = techtree.resolve(snap)
    # ordered by cost: module tick first, vehicle tick second
    assert [tk.category for tk in ticks] == ["module", "vehicle"]


def test_locked_reflects_prereqs_met():
    snap = t.VehicleSnapshot(
        tier=5, is_elite=False, vehicle_xp=1000, free_xp=500,
        tech_unlocks=[_unlock(3, 600, prereqs_met=True),
                      _unlock(2, 2000, prereqs_met=False)])
    ticks = techtree.resolve(snap)
    # ordered by cost: 600 (prereqs met -> not locked), 2000 (unmet -> locked)
    assert [tk.locked for tk in ticks] == [False, True]


def test_kind_label_and_prereq_names_pass_through_to_ticks():
    snap = t.VehicleSnapshot(
        tier=10, is_elite=False, vehicle_xp=0, free_xp=0,
        tech_unlocks=[
            _unlock(1, 600, kind="module", kind_label="Gun"),
            _unlock(2, 2000, kind="vehicle", kind_label="Tier IX",
                    prereqs_met=False, prereq_names=["Some Engine", "Some Turret"])])
    ticks = techtree.resolve(snap)  # ordered by cost: module (600), vehicle (2000)
    assert [tk.kind_label for tk in ticks] == ["Gun", "Tier IX"]
    assert ticks[0].prereq_names == []
    assert ticks[1].prereq_names == ["Some Engine", "Some Turret"]
