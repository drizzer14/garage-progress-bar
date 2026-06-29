# -*- coding: utf-8 -*-
from wgmod_research.domain import types as t
from wgmod_research.domain.resolvers import skilltree


def _snap(is_skill_tree=True, total_xp=325000, spent_xp=130000, done=10,
          total=26, vehicle_xp=40000, free_xp=5000):
    return t.VehicleSnapshot(
        tier=10, is_elite=True, vehicle_xp=vehicle_xp, free_xp=free_xp,
        is_skill_tree=is_skill_tree, skilltree_total_xp=total_xp,
        skilltree_spent_xp=spent_xp, skilltree_done=done, skilltree_total=total)


def test_not_skill_tree_returns_none():
    assert skilltree.resolve(_snap(is_skill_tree=False)) is None


def test_no_priced_nodes_returns_none():
    # A tree with no priced upgrade nodes -> nothing to show.
    assert skilltree.resolve(_snap(total=0)) is None


def test_fully_upgraded_returns_none():
    # Every node unlocked -> let the builder fall through to ELITE / COMPLETE.
    assert skilltree.resolve(_snap(done=26, total=26)) is None


def test_fixed_total_drives_scale_and_counts():
    res = skilltree.resolve(_snap(total_xp=325000, spent_xp=130000, done=10,
                                  total=26))
    assert res["scale_min"] == 0
    assert res["scale_max"] == 325000          # axis = fixed full-upgrade cost
    assert res["done"] == 10
    assert res["total"] == 26


def test_fill_is_cumulative_invested_xp():
    # fill = XP already invested in unlocked nodes (NOT the player's wallet); a
    # single segment, independent of banked vehicle/free XP.
    res = skilltree.resolve(_snap(spent_xp=130000, vehicle_xp=40000,
                                  free_xp=5000))
    assert res["fill"] == 130000
