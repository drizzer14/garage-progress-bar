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
    assert m.scale_max == 1000          # max own cost (per-item, not cumulative)
    assert m.fill_vehicle == 500
    assert m.fill_free == 0
    assert [tk.xp_position for tk in m.ticks] == [500, 1000]
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
    assert [tk.xp_position for tk in m.ticks] == [5000, 325000]
    assert m.scale_max == 325000


def test_tech_tree_fill_is_two_segments():
    snap = t.VehicleSnapshot(tier=5, is_elite=False, vehicle_xp=800, free_xp=300,
                             tech_unlocks=[_u(1, 600), _u(2, 5000)])
    m = build_model(snap)
    # spendable = 1100 affords the 600 tick, not the 5600 tick
    assert m.fill_vehicle == 800
    assert m.fill_free == 300
    assert [tk.affordable for tk in m.ticks] == [True, False]


def test_spendable_xp_is_vehicle_plus_free_xp():
    # spendable_xp (vehicle combat XP + global free XP) is set on the model in
    # every mode, so the view can show per-item affordability. Tech-tree here;
    # field-mods below confirm a second mode.
    snap = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=800, free_xp=300,
                             tech_unlocks=[_u(1, 1000)])
    m = build_model(snap)
    assert m.mode == t.Mode.TECH_TREE
    assert m.spendable_xp == 1100

    fm = t.VehicleSnapshot(tier=10, is_elite=True, vehicle_xp=1000, free_xp=200,
                           field_mod_steps=[_step(1, 2000)])
    mfm = build_model(fm)
    assert mfm.mode == t.Mode.FIELD_MODS
    assert mfm.spendable_xp == 1200


# --- "Ignore Free XP" setting (build_model ignore_free_xp) ----------------
# When on, the account-global free XP is neutralized at the single source
# (snapshot.free_xp) so the fill, model spendable, AND each resolver's own
# affordability all count combat XP only. Default (off) is unchanged.

def test_ignore_free_xp_zeroes_fill_and_spendable():
    # A tick priced between combat XP (800) and combat+free (1100): affordable only
    # because free XP covers the rest -- exactly the case the setting removes.
    snap = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=800, free_xp=300,
                             tech_unlocks=[_u(1, 1000)])
    off = build_model(snap, ignore_free_xp=False)
    assert off.fill_vehicle == 800
    assert off.fill_free == 300
    assert off.spendable_xp == 1100
    assert [tk.affordable for tk in off.ticks] == [True]     # free XP affords it

    on = build_model(snap, ignore_free_xp=True)
    assert on.fill_vehicle == 800
    assert on.fill_free == 0                                 # free segment gone
    assert on.spendable_xp == 800                            # combat XP only
    assert [tk.affordable for tk in on.ticks] == [False]     # combat alone falls short


def test_ignore_free_xp_does_not_mutate_the_snapshot():
    # build_model must copy before zeroing -- a shared fixture (or the caller's snapshot)
    # keeps its free XP so a later off-build still counts it.
    snap = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=800, free_xp=300,
                             tech_unlocks=[_u(1, 1000)])
    build_model(snap, ignore_free_xp=True)
    assert snap.free_xp == 300
    assert build_model(snap, ignore_free_xp=False).spendable_xp == 1100


def test_ignore_free_xp_affects_field_mod_affordability():
    # The fieldmods resolver recomputes its own spendable from snapshot.free_xp, so it
    # must see the neutralized value too.
    snap = t.VehicleSnapshot(tier=10, is_elite=True, vehicle_xp=1000, free_xp=1500,
                             field_mod_steps=[_step(1, 2000)])
    assert [tk.affordable for tk in build_model(snap, ignore_free_xp=False).ticks] == [True]
    assert [tk.affordable for tk in build_model(snap, ignore_free_xp=True).ticks] == [False]


def test_ignore_free_xp_affects_potential_mode_spendable():
    # The potential resolver also derives spendable from snapshot.free_xp.
    on = build_model(_done_tier_x(vehicle_xp=100000, free_xp=50000), _WITH_PXI,
                     ignore_free_xp=True)
    assert on.mode == t.Mode.POTENTIAL_TIER_XI
    assert on.fill_free == 0
    assert on.spendable_xp == 100000


def test_avg_battle_xp_carries_onto_model():
    # The snapshot's avg combat XP/battle rides every model so the view can estimate
    # "battles remaining"; 0 when unread stays 0 (view then hides the estimate).
    snap = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=800, free_xp=300,
                             tech_unlocks=[_u(1, 1000)], avg_battle_xp=740)
    m = build_model(snap)
    assert m.mode == t.Mode.TECH_TREE
    assert m.avg_battle_xp == 740

    fm = t.VehicleSnapshot(tier=10, is_elite=True, vehicle_xp=1000, free_xp=200,
                           field_mod_steps=[_step(1, 2000)], avg_battle_xp=1234)
    mfm = build_model(fm)
    assert mfm.mode == t.Mode.FIELD_MODS
    assert mfm.avg_battle_xp == 1234

    bare = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=0, free_xp=0,
                             tech_unlocks=[_u(1, 1000)])
    assert build_model(bare).avg_battle_xp == 0


def test_estimate_inputs_carry_onto_model():
    # The rest of the "battles remaining" estimate inputs (sample size, account-wide
    # fallback avg, and the optimistic-bound bonuses) ride every model like avg_battle_xp.
    snap = t.VehicleSnapshot(
        tier=6, is_elite=False, vehicle_xp=800, free_xp=300,
        tech_unlocks=[_u(1, 1000)], avg_battle_xp=740, battle_count=42,
        account_avg_battle_xp=560, reserve_mult=200, daily_double_factor=200,
        max_battle_xp=1900)
    m = build_model(snap)
    assert (m.battle_count, m.account_avg_battle_xp, m.reserve_mult,
            m.daily_double_factor, m.max_battle_xp) == (42, 560, 200, 200, 1900)

    # An elite/prestige model routes through _elite_model -- inputs must survive there too.
    fm = t.VehicleSnapshot(
        tier=10, is_elite=True, vehicle_xp=1000, free_xp=200,
        field_mod_steps=[_step(1, 2000)], battle_count=7,
        account_avg_battle_xp=610, reserve_mult=150, daily_double_factor=100)
    mfm = build_model(fm)
    assert mfm.mode == t.Mode.FIELD_MODS
    assert (mfm.battle_count, mfm.account_avg_battle_xp,
            mfm.reserve_mult, mfm.daily_double_factor) == (7, 610, 150, 100)


def test_estimate_inputs_default_to_no_bonus():
    # Unread reads default to neutral: multipliers 100 (x1.0), counts/avg 0 -> the view
    # renders today's single-number estimate with no range widening.
    bare = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=0, free_xp=0,
                             tech_unlocks=[_u(1, 1000)])
    m = build_model(bare)
    assert (m.battle_count, m.account_avg_battle_xp, m.max_battle_xp) == (0, 0, 0)
    assert (m.reserve_mult, m.daily_double_factor) == (100, 100)


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
                vehicle_xp=40000, free_xp=5000, final_icon="img://final.png", **kw):
    return t.VehicleSnapshot(
        tier=10, is_elite=True, vehicle_xp=vehicle_xp, free_xp=free_xp,
        is_skill_tree=True, skilltree_total_xp=total_xp,
        skilltree_spent_xp=spent_xp, skilltree_done=done, skilltree_total=total,
        skilltree_final_icon=final_icon, vehicle_class="heavyTank", **kw)


def test_skill_tree_mode_when_upgrade_remaining():
    m = build_model(_skill_snap(done=10, total=26))
    assert m.mode == t.Mode.SKILL_TREE
    assert m.scale_min == 0
    assert m.scale_max == 26                  # axis = total upgrade NODES (count)
    assert m.fill_vehicle == 10               # single segment = nodes unlocked
    assert m.fill_free == 0                   # free slot unused in this mode
    assert len(m.ticks) == 26                 # one tick per node
    assert m.ticks[-1].icon == "img://final.png"  # final upgrade flagged at end
    # node counter rides the existing field-mod counter fields
    assert (m.fieldmods_done, m.fieldmods_total) == (10, 26)
    assert m.vehicle_class == "heavyTank"


def test_skill_tree_carries_available_upgrades():
    # The frontier nodes (available now) flow through to the model as avail_upgrades,
    # preserving identity (step_id), name, icon and cost for the clickable chips.
    avail = [t.ProgressionStep(7, "Reinforced Tracks", "ic7.png", 20000, unlocked=False),
             t.ProgressionStep(3, "Improved Optics", "ic3.png", 10000, unlocked=False)]
    m = build_model(_skill_snap(done=5, total=26, skilltree_available=avail))
    assert m.mode == t.Mode.SKILL_TREE
    assert [u.step_id for u in m.avail_upgrades] == [7, 3]
    assert [u.name for u in m.avail_upgrades] == ["Reinforced Tracks", "Improved Optics"]
    assert [u.xp_cost for u in m.avail_upgrades] == [20000, 10000]


def test_skill_tree_available_defaults_empty():
    # No frontier provided -> empty list, never None (safe for the bridge push loop).
    m = build_model(_skill_snap(done=10, total=26))
    assert m.avail_upgrades == []


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


def _elite_snap(rewards=None, grades=None, level=12, level_xp=None, current_xp=0):
    return t.VehicleSnapshot(
        tier=11, is_elite=True, vehicle_xp=99999, free_xp=500,
        has_prestige=True, elite_level=level, elite_max_level=20,
        elite_grades=grades if grades is not None else _grades(),
        elite_rewards=rewards or [],
        elite_level_xp=level_xp or {}, elite_current_xp=current_xp)


def test_elite_rewards_mode_when_rewards_unearned():
    snap = _elite_snap(rewards=[t.EliteReward(50, True), t.EliteReward(100, False)],
                       level_xp={12: 800000}, current_xp=12345)
    m = build_model(snap)
    assert m.mode == t.Mode.ELITE_REWARDS
    assert m.elite_level == 12
    assert m.elite_max_level == 20
    assert m.fill_free == 0                 # single segment in elite modes
    # cumulative combat XP = XP-to-reach-current-level + progress within it
    # (NOT the unspent research XP / vehicle_xp=99999, the old bug).
    assert m.combat_xp == 812345


def test_elite_combat_xp_is_cumulative_not_research_xp():
    # ELITE band + ELITE_REWARDS both reconstruct cumulative combat XP the same way.
    snap = _elite_snap(rewards=[], level=10, level_xp={10: 650000}, current_xp=4000)
    m = build_model(snap)
    assert m.mode == t.Mode.ELITE
    assert m.combat_xp == 654000
    # the -1 "no progress data" sentinel floors to 0 (no negative drift).
    snap2 = _elite_snap(rewards=[], level=10, level_xp={10: 650000}, current_xp=-1)
    assert build_model(snap2).combat_xp == 650000


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


# --- clickable-tick identity (action_id) ----------------------------------

def test_tech_tree_ticks_carry_int_cd_as_action_id():
    # Each tech-tree tick must carry its unlock int_cd so a click can research it.
    snap = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=0, free_xp=0,
                             tech_unlocks=[_u(1, 1000), _u(2, 500)])
    m = build_model(snap)
    # ticks sort by cost -> cd 2 (500) then cd 1 (1000); action_id == int_cd
    assert [tk.action_id for tk in m.ticks] == [2, 1]


def test_field_mod_ticks_carry_step_id_as_action_id():
    # Each field-mod tick must carry its step_id so a click can unlock the step.
    snap = t.VehicleSnapshot(tier=10, is_elite=True, vehicle_xp=0, free_xp=0,
                             field_mod_steps=[_step(1, 2000), _step(2, 4000)])
    m = build_model(snap)
    assert [tk.action_id for tk in m.ticks] == [1, 2]


def test_skill_tree_ticks_have_no_action_id():
    # Skill-tree nodes are position-only (non-linear DAG) -> not individually
    # actionable, so they carry no action identity.
    m = build_model(_skill_snap(done=10, total=26))
    assert all(tk.action_id == 0 for tk in m.ticks)


# --- per-mode toggles (enabled set) ---------------------------------------
# `enabled` is the set of Mode strings left ON; None = all on. A vehicle whose
# resolved mode is off yields Mode.HIDDEN -- NO fall-through to a lower mode.

_ALL_MODES = {t.Mode.TECH_TREE, t.Mode.SKILL_TREE, t.Mode.FIELD_MODS,
              t.Mode.ELITE_REWARDS, t.Mode.ELITE}


def _without(mode):
    return _ALL_MODES - {mode}


def test_enabled_none_is_unchanged():
    # Default (no toggle set) behaves exactly as before: research shows.
    snap = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=500, free_xp=0,
                             tech_unlocks=[_u(1, 1000)])
    assert build_model(snap).mode == t.Mode.TECH_TREE
    assert build_model(snap, None).mode == t.Mode.TECH_TREE


def test_tech_tree_disabled_hides():
    snap = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=500, free_xp=0,
                             tech_unlocks=[_u(1, 1000)])
    m = build_model(snap, _without(t.Mode.TECH_TREE))
    assert m.mode == t.Mode.HIDDEN
    assert m.ticks == []


def test_skill_tree_disabled_hides():
    m = build_model(_skill_snap(done=10, total=26), _without(t.Mode.SKILL_TREE))
    assert m.mode == t.Mode.HIDDEN


def test_field_mods_disabled_hides():
    snap = t.VehicleSnapshot(tier=10, is_elite=True, vehicle_xp=0, free_xp=0,
                             field_mod_steps=[_step(1, 2000)])
    m = build_model(snap, _without(t.Mode.FIELD_MODS))
    assert m.mode == t.Mode.HIDDEN


def test_elite_rewards_disabled_hides_no_fall_through_to_band():
    # Rewards unearned resolves ELITE_REWARDS; with it off the bar HIDES -- it does
    # NOT drop to the grade band even though ELITE is still enabled.
    snap = _elite_snap(rewards=[t.EliteReward(50, True), t.EliteReward(100, False)])
    m = build_model(snap, _without(t.Mode.ELITE_REWARDS))
    assert m.mode == t.Mode.HIDDEN


def test_elite_disabled_hides():
    # All rewards earned -> resolves to the grade band; with ELITE off, hide.
    snap = _elite_snap(rewards=[t.EliteReward(50, True), t.EliteReward(100, True)])
    m = build_model(snap, _without(t.Mode.ELITE))
    assert m.mode == t.Mode.HIDDEN


def test_disabling_a_non_matching_higher_mode_is_a_no_op():
    # A fully-researched field-mod tank never resolves to tech-tree, so disabling
    # tech-tree leaves FIELD_MODS showing (only the RESOLVED mode's toggle matters).
    snap = t.VehicleSnapshot(tier=10, is_elite=True, vehicle_xp=1000, free_xp=0,
                             field_mod_steps=[_step(1, 2000)])
    m = build_model(snap, _without(t.Mode.TECH_TREE))
    assert m.mode == t.Mode.FIELD_MODS


def test_genuine_complete_unaffected_by_toggles():
    # COMPLETE is the genuine end-state, never toggled: even with every mode off,
    # a fully-done vehicle still shows COMPLETE (not HIDDEN).
    snap = t.VehicleSnapshot(tier=8, is_elite=True, vehicle_xp=0, free_xp=0)
    assert build_model(snap, set()).mode == t.Mode.COMPLETE


# --- potential Tier XI (opt-in speculative mode) --------------------------
# A tier-X tank with no real tier XI, fully done. Gated at ENTRY (only when the
# mode is explicitly in `enabled`), so OFF falls THROUGH to elite/complete rather
# than hiding, and enabled=None (legacy default) never triggers it.

_WITH_PXI = _ALL_MODES | {t.Mode.POTENTIAL_TIER_XI}


def _done_tier_x(vehicle_xp=100000, free_xp=50000, **kw):
    # A tier-X tank with nothing left to research and no field mods -> would be
    # COMPLETE (or ELITE with prestige) today.
    return t.VehicleSnapshot(tier=10, is_elite=True,
                             vehicle_xp=vehicle_xp, free_xp=free_xp, **kw)


def test_potential_mode_when_enabled_on_done_tier_x():
    m = build_model(_done_tier_x(vehicle_xp=100000, free_xp=50000), _WITH_PXI)
    assert m.mode == t.Mode.POTENTIAL_TIER_XI
    assert m.scale_min == 0
    assert m.scale_max == 325000              # fixed tier-XI price
    assert m.fill_vehicle == 100000           # two stacked segments (vehicle + free)
    assert m.fill_free == 50000
    assert m.spendable_xp == 150000
    assert len(m.ticks) == 1                  # single milestone tick
    assert m.ticks[0].xp_position == 325000
    assert m.ticks[0].action_id == 0          # not clickable


def test_potential_replaces_elite_when_enabled():
    # With prestige data present, the potential mode still wins (sits above ELITE).
    snap = _done_tier_x(has_prestige=True, elite_level=10, elite_max_level=20,
                        elite_grades=_grades(), elite_level_xp={10: 650000})
    assert build_model(snap, _WITH_PXI).mode == t.Mode.POTENTIAL_TIER_XI


def test_potential_off_falls_through_to_elite_not_hidden():
    # OFF (mode absent from enabled) must fall THROUGH to the prestige band, NOT hide.
    snap = _done_tier_x(has_prestige=True, elite_level=10, elite_max_level=20,
                        elite_grades=_grades(), elite_level_xp={10: 650000})
    assert build_model(snap, _ALL_MODES).mode == t.Mode.ELITE


def test_potential_off_falls_through_to_complete():
    assert build_model(_done_tier_x(), _ALL_MODES).mode == t.Mode.COMPLETE


def test_potential_enabled_none_does_not_trigger():
    # Legacy/tests default (enabled=None = "all on") never includes this opt-in mode.
    assert build_model(_done_tier_x()).mode == t.Mode.COMPLETE
    assert build_model(_done_tier_x(), None).mode == t.Mode.COMPLETE


def test_potential_not_for_skill_tree_vehicle():
    # A tank with a real (fully-upgraded) tier XI is excluded even when enabled.
    m = build_model(_skill_snap(done=26, total=26), _WITH_PXI)
    assert m.mode == t.Mode.COMPLETE


def test_potential_not_for_non_tier_x():
    # Tier gate: only tier X (level 10) qualifies.
    snap = t.VehicleSnapshot(tier=9, is_elite=True, vehicle_xp=100000, free_xp=0)
    assert build_model(snap, _WITH_PXI).mode == t.Mode.COMPLETE


def test_field_mods_take_priority_over_potential():
    # Remaining field mods win: the speculative bar only shows once everything real
    # is done.
    snap = t.VehicleSnapshot(tier=10, is_elite=True, vehicle_xp=0, free_xp=0,
                             field_mod_steps=[_step(1, 2000)])
    assert build_model(snap, _WITH_PXI).mode == t.Mode.FIELD_MODS


def test_tech_tree_takes_priority_over_potential():
    # Unresearched modules still show the tech tree first.
    snap = t.VehicleSnapshot(tier=10, is_elite=False, vehicle_xp=0, free_xp=0,
                             tech_unlocks=[_u(1, 5000)])
    assert build_model(snap, _WITH_PXI).mode == t.Mode.TECH_TREE


def test_potential_excluded_when_real_tier_xi_researched():
    # A tier-X whose real tech-tree Tier-XI successor is already RESEARCHED keeps that
    # vehicle in tech_unlocks (researched=True, so it makes no tick). The speculative bar
    # must NOT show -- a real Tier XI exists on this line. Falls through to COMPLETE.
    snap = _done_tier_x(tech_unlocks=[_u(99, 325000, researched=True, kind="vehicle")])
    assert build_model(snap, _WITH_PXI).mode == t.Mode.COMPLETE


def test_potential_excluded_when_real_tier_xi_researched_with_prestige():
    # Same exclusion with prestige data present -> falls through to the ELITE band.
    snap = _done_tier_x(tech_unlocks=[_u(99, 325000, researched=True, kind="vehicle")],
                        has_prestige=True, elite_level=10, elite_max_level=20,
                        elite_grades=_grades(), elite_level_xp={10: 650000})
    assert build_model(snap, _WITH_PXI).mode == t.Mode.ELITE


def test_potential_excluded_for_premium_tank():
    # A premium / gift / reward tier-X (e.g. Dravec) has no research line -> the
    # speculative bar must NOT apply, even when enabled. Falls through to COMPLETE.
    snap = _done_tier_x(is_premium=True)
    assert build_model(snap, _WITH_PXI).mode == t.Mode.COMPLETE


def test_potential_excluded_for_premium_tank_with_prestige():
    # Same premium exclusion with prestige -> falls through to ELITE, and POTENTIAL is
    # NOT offered as a switch option.
    snap = _done_tier_x(is_premium=True, has_prestige=True, elite_level=10,
                        elite_max_level=20, elite_grades=_grades(),
                        elite_level_xp={10: 650000})
    m = build_model(snap, _WITH_PXI)
    assert m.mode == t.Mode.ELITE
    assert t.Mode.POTENTIAL_TIER_XI not in m.avail_modes


def test_potential_still_shows_with_researched_module_in_unlocks():
    # A researched MODULE left in tech_unlocks is NOT a successor vehicle -> only a
    # VEHICLE entry signals a real Tier XI, so the speculative bar still applies.
    snap = _done_tier_x(tech_unlocks=[_u(5, 1000, researched=True, kind="module")])
    assert build_model(snap, _WITH_PXI).mode == t.Mode.POTENTIAL_TIER_XI


def test_potential_model_carries_estimate_inputs_and_class():
    # The POTENTIAL model must carry the same estimate inputs + vehicle_class every other
    # mode does, so the tooltip's "~ M-N battles" range and the class badge render.
    snap = _done_tier_x(vehicle_class="mediumTank", avg_battle_xp=740, battle_count=42,
                        account_avg_battle_xp=560, reserve_mult=200,
                        daily_double_factor=200, max_battle_xp=1900)
    m = build_model(snap, _WITH_PXI)
    assert m.mode == t.Mode.POTENTIAL_TIER_XI
    assert m.vehicle_class == "mediumTank"
    assert (m.avg_battle_xp, m.battle_count, m.account_avg_battle_xp,
            m.reserve_mult, m.daily_double_factor, m.max_battle_xp) == (
        740, 42, 560, 200, 200, 1900)


# --- avail_modes + override (the header "mode switch") --------------------
# avail_modes lists every mode the vehicle qualifies for AND that is enabled, in
# priority order. override re-emits any of those; a stale/absent override is ignored.

def test_avail_modes_single_mode_has_one_entry():
    # A plain tech-tree vehicle qualifies for exactly one mode -> no switch (len 1).
    snap = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=500, free_xp=0,
                             tech_unlocks=[_u(1, 1000)])
    m = build_model(snap)
    assert m.mode == t.Mode.TECH_TREE
    assert m.avail_modes == [t.Mode.TECH_TREE]


def test_avail_modes_elite_and_rewards_coexist():
    # A prestige vehicle with an unearned reward qualifies for BOTH elite_rewards and
    # the grade band -> two switch options, priority order (rewards first).
    snap = _elite_snap(rewards=[t.EliteReward(50, True), t.EliteReward(100, False)])
    m = build_model(snap)
    assert m.mode == t.Mode.ELITE_REWARDS
    assert m.avail_modes == [t.Mode.ELITE_REWARDS, t.Mode.ELITE]


def test_avail_modes_all_rewards_earned_is_elite_only():
    # No unearned reward -> elite_rewards is NOT available; only the band remains.
    snap = _elite_snap(rewards=[t.EliteReward(50, True), t.EliteReward(100, True)])
    m = build_model(snap)
    assert m.avail_modes == [t.Mode.ELITE]


def test_avail_modes_excludes_disabled_modes():
    # A disabled mode is not a switch option even when the vehicle qualifies for it.
    snap = _elite_snap(rewards=[t.EliteReward(50, True), t.EliteReward(100, False)])
    m = build_model(snap, _without(t.Mode.ELITE))
    # ELITE filtered out; ELITE_REWARDS (the priority winner) still shows.
    assert m.mode == t.Mode.ELITE_REWARDS
    assert m.avail_modes == [t.Mode.ELITE_REWARDS]


def test_override_selects_a_lower_priority_available_mode():
    # override to the grade band on a vehicle whose default is elite_rewards.
    snap = _elite_snap(rewards=[t.EliteReward(50, True), t.EliteReward(100, False)],
                       level=10, level_xp={10: 650000})
    m = build_model(snap, _ALL_MODES, override=t.Mode.ELITE)
    assert m.mode == t.Mode.ELITE
    # avail_modes is unchanged by the override -- it's still the full switch menu.
    assert m.avail_modes == [t.Mode.ELITE_REWARDS, t.Mode.ELITE]


def test_override_ignored_when_mode_not_available():
    # A stale override (mode the vehicle no longer qualifies for) is ignored -> the
    # priority default shows.
    snap = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=500, free_xp=0,
                             tech_unlocks=[_u(1, 1000)])
    m = build_model(snap, _ALL_MODES, override=t.Mode.ELITE)
    assert m.mode == t.Mode.TECH_TREE


def test_override_ignored_when_mode_disabled():
    # override names a mode the vehicle qualifies for but the user disabled -> not in
    # avail, so ignored; the enabled priority default shows.
    snap = _elite_snap(rewards=[t.EliteReward(50, True), t.EliteReward(100, False)])
    m = build_model(snap, _without(t.Mode.ELITE), override=t.Mode.ELITE)
    assert m.mode == t.Mode.ELITE_REWARDS


def test_override_none_is_priority_default():
    snap = _elite_snap(rewards=[t.EliteReward(50, True), t.EliteReward(100, False)])
    assert build_model(snap, _ALL_MODES, override=None).mode == t.Mode.ELITE_REWARDS


def test_complete_has_empty_avail_modes():
    snap = t.VehicleSnapshot(tier=8, is_elite=True, vehicle_xp=0, free_xp=0)
    m = build_model(snap)
    assert m.mode == t.Mode.COMPLETE
    assert m.avail_modes == []


def test_hidden_model_still_reports_avail_modes():
    # The priority winner is disabled -> HIDDEN, but avail_modes still lists the enabled
    # options (so an override to an enabled mode could later show the bar).
    snap = _elite_snap(rewards=[t.EliteReward(50, True), t.EliteReward(100, False)])
    m = build_model(snap, _without(t.Mode.ELITE_REWARDS))
    assert m.mode == t.Mode.HIDDEN
    assert m.avail_modes == [t.Mode.ELITE]


def test_override_honored_even_when_priority_default_disabled():
    # If the priority winner is off but the player explicitly picked an enabled mode,
    # honor it (the switch only offers enabled modes, so this is the player asking).
    snap = _elite_snap(rewards=[t.EliteReward(50, True), t.EliteReward(100, False)],
                       level=10, level_xp={10: 650000})
    m = build_model(snap, _without(t.Mode.ELITE_REWARDS), override=t.Mode.ELITE)
    assert m.mode == t.Mode.ELITE


# --- progress_current / progress_required (the "current / required" readout) --
# Populated per mode so the widget can render "current / required" (progressMode) and
# a derived percentage (showPercent). XP-fill modes read spendable / scale_max; skill
# reads spendable / remaining-full-upgrade-cost; elite modes read cumulative combat XP /
# the trailing milestone's cumulative XP; COMPLETE carries 0 / 0.

def test_progress_readout_tech_tree_is_spendable_over_scale_max():
    snap = t.VehicleSnapshot(tier=6, is_elite=False, vehicle_xp=500, free_xp=200,
                             tech_unlocks=[_u(1, 1000), _u(2, 500)])
    m = build_model(snap)
    assert m.mode == t.Mode.TECH_TREE
    assert m.progress_current == 700          # spendable = vehicle + free
    assert m.progress_current == m.spendable_xp
    assert m.progress_required == 1000        # == scale_max (max per-item cost)
    assert m.progress_required == m.scale_max


def test_progress_readout_field_mods_is_spendable_over_scale_max():
    snap = t.VehicleSnapshot(tier=10, is_elite=True, vehicle_xp=1000, free_xp=200,
                             field_mod_steps=[_step(1, 2000), _step(2, 4000)])
    m = build_model(snap)
    assert m.mode == t.Mode.FIELD_MODS
    assert m.progress_current == 1200         # spendable
    assert m.progress_required == 6000        # cumulative scale_max
    assert m.progress_required == m.scale_max


def test_progress_readout_potential_is_spendable_over_price():
    m = build_model(_done_tier_x(vehicle_xp=100000, free_xp=50000), _WITH_PXI)
    assert m.mode == t.Mode.POTENTIAL_TIER_XI
    assert m.progress_current == 150000       # spendable
    assert m.progress_required == 325000      # the fixed tier-XI price == scale_max
    assert m.progress_required == m.scale_max


def test_progress_readout_skill_tree_is_spent_over_total_xp():
    # readout = XP already invested in the tree (skilltree_spent_xp) / the full-upgrade
    # total (skilltree_total_xp) -- both ride the snapshot, so the "%" and the
    # "current / required" text read spent / total (NOT spendable, NOT a derived remaining).
    m = build_model(_skill_snap(total_xp=325000, spent_xp=130000,
                                vehicle_xp=40000, free_xp=5000, done=10, total=26))
    assert m.mode == t.Mode.SKILL_TREE
    assert m.progress_current == 130000       # skilltree_spent_xp (invested so far)
    assert m.progress_required == 325000      # skilltree_total_xp (full-upgrade total)


def test_progress_readout_skill_tree_reads_spent_and_total_verbatim():
    # spent_xp / total_xp are read straight off the snapshot -- even a spent >= total
    # figure passes through unchanged (no derived remaining, no flooring).
    m = build_model(_skill_snap(total_xp=200000, spent_xp=250000,
                                vehicle_xp=40000, free_xp=5000, done=10, total=26))
    assert m.mode == t.Mode.SKILL_TREE
    assert m.progress_current == 250000       # skilltree_spent_xp verbatim
    assert m.progress_required == 200000      # skilltree_total_xp verbatim


def test_progress_readout_elite_is_within_band_combat_xp():
    # NEW within-band axis: progress_current is the combat XP earned SINCE the current
    # grade band started (combat_xp - scale_min = level_xp[band_min]), out of the band's
    # XP span -- so the readout "%" equals the bar fill width exactly. combat_xp itself
    # stays the cumulative total (unchanged).
    snap = _elite_snap(rewards=[], level=10, level_xp={10: 650000, 20: 900000},
                       current_xp=4000)
    m = build_model(snap)
    assert m.mode == t.Mode.ELITE
    assert m.combat_xp == 654000              # cumulative combat XP (unchanged)
    assert m.progress_current == 4000         # combat_xp - scale_min (within-band offset)
    assert m.progress_current == m.fill_vehicle   # fill width == readout numerator
    assert m.progress_required == 250000      # band XP span (900000 - 650000)


def test_progress_readout_elite_rewards_is_combat_xp_over_last_reward_level():
    # required = cumulative XP of the trailing tick = the LAST reward level.
    snap = _elite_snap(rewards=[t.EliteReward(50, True), t.EliteReward(100, False)],
                       level=12, level_xp={12: 800000, 100: 2000000}, current_xp=12345)
    m = build_model(snap)
    assert m.mode == t.Mode.ELITE_REWARDS
    assert m.progress_current == 812345       # == combat_xp
    assert m.progress_current == m.combat_xp
    assert m.progress_required == 2000000     # cumulative XP to the last reward (level 100)


def test_progress_readout_complete_is_zero_over_zero():
    snap = t.VehicleSnapshot(tier=8, is_elite=True, vehicle_xp=0, free_xp=0)
    m = build_model(snap)
    assert m.mode == t.Mode.COMPLETE
    assert m.progress_current == 0
    assert m.progress_required == 0
