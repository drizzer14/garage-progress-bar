# -*- coding: utf-8 -*-
from wgmod_research.domain import types as t
from wgmod_research.domain.builder import build_model


def _u(cd, cost, researched=False, kind="module"):
    return t.UnlockItem(cd, "u%d" % cd, "u%d.png" % cd, cost, kind, researched, True)


def _step(sid, cost, unlocked=False, level=0):
    return t.ProgressionStep(sid, "fm%d" % sid, "fm%d.png" % sid, cost, unlocked, level)


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
    # tech-tree ticks carry the unlock kind as their category
    assert all(tk.category == "module" for tk in m.ticks)


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


def test_elite_with_remaining_unlocks_is_tech_tree():
    # Regression: veh.isElite can be True (eliteVehicles membership) while modules
    # are still unresearched (e.g. Leopard 1). Research must win over field mods.
    snap = t.VehicleSnapshot(
        tier=10, is_elite=True, vehicle_xp=0, free_xp=0,
        tech_unlocks=[_u(1, 5000)],                 # still something to research
        field_mod_steps=[_step(1, 2000)])           # field mods also available
    m = build_model(snap)
    assert m.mode == t.Mode.TECH_TREE
    assert [tk.xp_position for tk in m.ticks] == [5000]


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


def test_fieldmods_counter_and_class_pass_through_to_model():
    snap = t.VehicleSnapshot(
        tier=10, is_elite=True, vehicle_xp=0, free_xp=0,
        field_mod_steps=[_step(1, 2000, level=1)],
        fieldmods_done=2, fieldmods_total=8, vehicle_class="lightTank")
    m = build_model(snap)
    assert m.mode == t.Mode.FIELD_MODS
    assert (m.fieldmods_done, m.fieldmods_total) == (2, 8)
    assert m.vehicle_class == "lightTank"


def test_complete_carries_fieldmods_counter_and_class():
    snap = t.VehicleSnapshot(
        tier=9, is_elite=True, vehicle_xp=0, free_xp=0,
        field_mod_steps=[_step(1, 2000, unlocked=True)],  # all done -> complete
        fieldmods_done=7, fieldmods_total=7, vehicle_class="heavyTank")
    m = build_model(snap)
    assert m.mode == t.Mode.COMPLETE
    assert (m.fieldmods_done, m.fieldmods_total) == (7, 7)
    assert m.vehicle_class == "heavyTank"


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


# --- Tier-XI skill-tree (upgrade) mode ------------------------------------

def _skill_snap(total_xp=325000, spent_xp=130000, done=10, total=26,
                vehicle_xp=40000, free_xp=5000, **kw):
    return t.VehicleSnapshot(
        tier=10, is_elite=True, vehicle_xp=vehicle_xp, free_xp=free_xp,
        is_skill_tree=True, skilltree_total_xp=total_xp,
        skilltree_spent_xp=spent_xp, skilltree_done=done, skilltree_total=total,
        vehicle_class="heavyTank", **kw)


def test_skill_tree_mode_when_upgrade_remaining():
    m = build_model(_skill_snap(total_xp=325000, spent_xp=130000, done=10,
                                total=26))
    assert m.mode == t.Mode.SKILL_TREE
    assert m.scale_min == 0
    assert m.scale_max == 325000             # axis = fixed full-upgrade cost
    assert m.fill_vehicle == 130000          # single segment = cumulative invested
    assert m.fill_free == 0                  # free slot unused in this mode
    assert m.ticks == []                     # aggregate readout, no per-node ticks
    # node counter rides the existing field-mod counter fields
    assert (m.fieldmods_done, m.fieldmods_total) == (10, 26)
    assert m.vehicle_class == "heavyTank"


def test_skill_tree_takes_priority_over_field_mods():
    # Defensive: even if linear field-mod steps were somehow present, a skill-tree
    # vehicle shows the upgrade readout (the adapter also zeroes the linear read).
    m = build_model(_skill_snap(field_mod_steps=[_step(1, 2000)]))
    assert m.mode == t.Mode.SKILL_TREE


def test_tech_tree_still_wins_over_skill_tree():
    # Unresearched modules must still show the tech tree first.
    m = build_model(_skill_snap(tech_unlocks=[_u(1, 5000)]))
    assert m.mode == t.Mode.TECH_TREE


def test_fully_upgraded_skill_tree_with_prestige_is_elite():
    m = build_model(_skill_snap(done=26, total=26, has_prestige=True,
                                elite_level=12, elite_max_level=20,
                                elite_grades=_grades()))
    assert m.mode == t.Mode.ELITE


def test_fully_upgraded_skill_tree_no_prestige_is_complete():
    m = build_model(_skill_snap(done=26, total=26))
    assert m.mode == t.Mode.COMPLETE


# --- Elite Levels (prestige) modes ---------------------------------------

def _grades():
    return [t.EliteGrade(1, "iron", 1, True), t.EliteGrade(5, "iron", 2),
            t.EliteGrade(10, "bronze", 1, True), t.EliteGrade(20, "prestige", -1, True)]


def _elite_snap(rewards=None, grades=None, level=12):
    return t.VehicleSnapshot(
        tier=11, is_elite=True, vehicle_xp=99999, free_xp=500,
        has_prestige=True, elite_level=level, elite_max_level=20,
        elite_grades=grades if grades is not None else _grades(),
        elite_rewards=rewards or [])


def test_elite_rewards_mode_when_rewards_unearned():
    snap = _elite_snap(rewards=[t.EliteReward(50, True), t.EliteReward(100, False)])
    m = build_model(snap)
    assert m.mode == t.Mode.ELITE_REWARDS
    assert m.elite_level == 12
    assert m.elite_max_level == 20
    assert m.fill_free == 0                 # single segment in elite modes
    assert m.combat_xp == 99999             # cumulative combat XP, not +free


def test_elite_grade_mode_when_all_rewards_earned():
    snap = _elite_snap(rewards=[t.EliteReward(50, True), t.EliteReward(100, True)])
    m = build_model(snap)
    assert m.mode == t.Mode.ELITE
    assert m.elite_grade == "bronze"


def test_elite_grade_mode_when_no_rewards():
    snap = _elite_snap(rewards=[])
    m = build_model(snap)
    assert m.mode == t.Mode.ELITE
    assert m.elite_grade == "bronze"


def test_no_prestige_data_falls_back_to_complete():
    snap = t.VehicleSnapshot(tier=10, is_elite=True, vehicle_xp=0, free_xp=0,
                             has_prestige=False)
    m = build_model(snap)
    assert m.mode == t.Mode.COMPLETE


def test_field_mods_take_priority_over_prestige():
    # remaining field mods must win even when prestige data is present.
    snap = t.VehicleSnapshot(
        tier=10, is_elite=True, vehicle_xp=0, free_xp=0,
        field_mod_steps=[_step(1, 2000)],
        has_prestige=True, elite_level=5, elite_max_level=20,
        elite_grades=_grades(),
        elite_rewards=[t.EliteReward(50, False)])
    m = build_model(snap)
    assert m.mode == t.Mode.FIELD_MODS
