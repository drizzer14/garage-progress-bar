# -*- coding: utf-8 -*-
from wgmod_research.domain import types as t
from wgmod_research.domain.resolvers import elite


def _grade(level, grade, sub, main=False):
    return t.EliteGrade(level=level, grade=grade, sub=sub, main=main)


def _reward(level, achieved, icon="i.png", label="R", type_label="2D Style"):
    return t.EliteReward(level=level, achieved=achieved, icon=icon,
                         label=label, type_label=type_label)


# A compact synthetic grade scale: two real families + the synthetic MAX entry.
def _grades():
    return [
        _grade(1, "iron", 1, True), _grade(3, "iron", 2),
        _grade(5, "iron", 3), _grade(7, "iron", 4),
        _grade(10, "bronze", 1, True), _grade(13, "bronze", 2),
        _grade(16, "bronze", 3), _grade(19, "bronze", 4),
        _grade(20, "prestige", -1, True),  # synthetic MAX at the cap
    ]


def _snap(level, grades=None, rewards=None, current_xp=0, next_xp=0, max_level=20,
          level_xp=None):
    return t.VehicleSnapshot(
        tier=11, is_elite=True, vehicle_xp=12345, free_xp=0,
        has_prestige=True, elite_level=level, elite_max_level=max_level,
        elite_current_xp=current_xp, elite_next_xp=next_xp,
        elite_grades=grades if grades is not None else _grades(),
        elite_rewards=rewards or [], elite_level_xp=level_xp or {})


# --- grade band ----------------------------------------------------------

def test_grade_band_picks_current_family():
    res = elite.resolve_grade_band(_snap(12))
    assert res["grade"] == "bronze"
    assert res["scale_min"] == 10        # bronze sub1
    assert res["scale_max"] == 20        # next family (prestige/MAX) start
    # the 4 bronze sub-grades + one extra tick for the next grade's first level
    assert [tk.xp_position for tk in res["ticks"]] == [10, 13, 16, 19, 20]
    assert res["sub"] == 1               # only sub1 (@10) reached at level 12


def test_grade_band_ticks_carry_emblem_urls():
    res = elite.resolve_grade_band(_snap(12))
    icons = [tk.icon for tk in res["ticks"]]
    assert icons[0] == "img://gui/maps/icons/prestige/emblem/72x72/bronze/1.png"
    assert icons[3] == "img://gui/maps/icons/prestige/emblem/72x72/bronze/4.png"
    # the trailing next-grade tick is the synthetic MAX ("prestige") emblem
    assert icons[4] == "img://gui/maps/icons/prestige/emblem/72x72/prestige.png"


def test_grade_band_ticks_carry_xp_cost():
    xp = {10: 500000, 13: 700000, 16: 950000, 19: 1200000, 20: 1300000}
    res = elite.resolve_grade_band(_snap(12, level_xp=xp))
    assert [tk.xp_required for tk in res["ticks"]] == [
        500000, 700000, 950000, 1200000, 1300000]


def test_reward_track_ticks_carry_xp_cost():
    rewards = [_reward(50, True), _reward(100, False)]
    xp = {50: 2000000, 100: 5000000}
    res = elite.resolve_reward_track(_snap(60, rewards=rewards, level_xp=xp))
    assert [tk.xp_required for tk in res["ticks"]] == [2000000, 5000000]


def test_grade_band_tick_states_and_completed():
    res = elite.resolve_grade_band(_snap(13))
    states = [(tk.xp_position, tk.state, tk.completed) for tk in res["ticks"]]
    assert states == [
        (10, "achieved", True),   # 13 >= 10
        (13, "achieved", True),   # 13 >= 13
        (16, "next", False),      # first unreached
        (19, "upcoming", False),
        (20, "upcoming", False),  # next grade's first level (the extra tick)
    ]


def test_grade_band_trailing_tick_is_next_when_band_fully_reached():
    # A band whose every sub-grade is reached but the next family isn't: the
    # trailing next-family tick must carry the "next" highlight (the in-band loop
    # marks nothing "next" once all sub-grades are achieved).
    grades = [
        _grade(1, "iron", 1, True), _grade(3, "iron", 2),
        _grade(5, "iron", 3), _grade(7, "iron", 4),
        _grade(10, "bronze", 1, True),
    ]
    res = elite.resolve_grade_band(_snap(8, grades=grades, max_level=10))
    states = [(tk.xp_position, tk.state) for tk in res["ticks"]]
    assert states == [
        (1, "achieved"), (3, "achieved"), (5, "achieved"), (7, "achieved"),
        (10, "next"),  # next family's first level -> "next" now the band is done
    ]


def test_grade_band_fill_offset_includes_fraction():
    # level 12 in band [10,20], halfway to level 13 -> position 12.5, offset 2.5
    res = elite.resolve_grade_band(_snap(12, current_xp=50, next_xp=100))
    assert abs(res["fill"] - 2.5) < 1e-9
    assert res["scale_min"] == 10


def test_grade_band_no_data_sentinel_gives_zero_fraction():
    res = elite.resolve_grade_band(_snap(12, current_xp=-1, next_xp=-1))
    assert res["fill"] == 2              # exactly on the level, no fraction


def test_grade_band_below_first_threshold_uses_first_family():
    res = elite.resolve_grade_band(_snap(0))
    assert res["grade"] == "iron"
    assert res["scale_min"] == 1
    assert res["sub"] == 0               # nothing reached yet


def test_grade_band_max_is_full_bar():
    res = elite.resolve_grade_band(_snap(20, max_level=20))
    assert res["grade"] == "prestige"
    # band falls back to the last real family (bronze) and fills fully
    assert res["scale_max"] == 20
    assert res["fill"] == res["scale_max"] - res["scale_min"]


def test_grade_band_empty_returns_none():
    assert elite.resolve_grade_band(_snap(0, grades=[])) is None


# --- current grade icon (category-icon emblem, shared by both elite modes) ----

def test_current_grade_icon_is_highest_reached():
    # level 12 -> highest grade reached is bronze sub1 (@10); bronze2 (@13) not yet.
    assert elite.current_grade_icon(_snap(12)) == \
        "img://gui/maps/icons/prestige/emblem/72x72/bronze/1.png"


def test_current_grade_icon_below_first_threshold_is_empty():
    assert elite.current_grade_icon(_snap(0)) == ""


def test_current_grade_icon_at_max_is_prestige():
    assert elite.current_grade_icon(_snap(20, max_level=20)) == \
        "img://gui/maps/icons/prestige/emblem/72x72/prestige.png"


def test_current_grade_icon_no_grades_is_empty():
    assert elite.current_grade_icon(_snap(5, grades=[])) == ""


# --- reward track --------------------------------------------------------

def test_reward_track_states_and_span():
    rewards = [_reward(50, True), _reward(100, True),
               _reward(150, False), _reward(200, False)]
    res = elite.resolve_reward_track(_snap(170, rewards=rewards, max_level=350))
    assert res["scale_min"] == 0
    assert res["scale_max"] == 200
    assert [(tk.xp_position, tk.state) for tk in res["ticks"]] == [
        (50, "achieved"), (100, "achieved"),
        (150, "next"), (200, "upcoming")]
    assert res["any_unearned"] is True
    assert res["fill"] == 170


def test_reward_track_carries_icon_and_type_label():
    rewards = [_reward(50, False, icon="style_42.png",
                       label="Arctic", type_label="2D Style")]
    res = elite.resolve_reward_track(_snap(10, rewards=rewards))
    tk = res["ticks"][0]
    assert tk.icon == "style_42.png"
    assert tk.name == "Arctic"
    assert tk.options == ["2D Style"]
    assert tk.completed is False


def test_reward_track_all_earned_has_no_unearned():
    rewards = [_reward(50, True), _reward(100, True)]
    res = elite.resolve_reward_track(_snap(120, rewards=rewards))
    assert res["any_unearned"] is False
    assert all(tk.state == "achieved" for tk in res["ticks"])


def test_reward_track_empty_returns_none():
    assert elite.resolve_reward_track(_snap(0, rewards=[])) is None


def test_reward_track_fill_clamps_to_span():
    rewards = [_reward(50, True), _reward(100, True)]
    res = elite.resolve_reward_track(_snap(300, rewards=rewards))
    assert res["fill"] == 100            # clamped to last reward level
