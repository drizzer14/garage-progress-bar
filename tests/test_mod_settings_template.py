# -*- coding: utf-8 -*-
"""Structure tests for the MSA settings-panel template (``bridge/mod_settings.py``).

Locks the Aslain master/child structure: ``showBar`` is the master, the six per-mode
toggles + ``showWhenComplete`` are its children (each carrying ``masterVarName == "showBar"``,
in the exact spec order), and ``ignoreFreeXp`` is the single STANDALONE checkbox last in
column1 (NOT bound to the master -- no ``masterVarName``). ``showPercent`` now lives in
column2, directly beneath the ``progressMode`` Dropdown (also standalone). The old "Bar
modes" Label is gone, and the polarity/position defaults are unchanged.

``_template()`` itself is a pure dict, engine-free once imported. (The game's
``debug_utils`` is stubbed once in conftest.py.)"""
from wgmod_research.bridge import mod_settings as M

# The seven children of the showBar master, in the exact spec order (ignoreFreeXp and
# showPercent are NOT here -- they're standalone controls after the group, see below).
_CHILD_ORDER = [
    "showTechTree",
    "showFieldMods",
    "showPotentialTierXI",
    "showSkillTree",
    "showEliteRewards",
    "showElite",
    "showWhenComplete",
]


def _col1():
    return M._template()["column1"]


# --- version ----------------------------------------------------------------

def test_settings_version_is_9():
    # Bumped 8 -> 9 when showPercent was MOVED from column1 to column2 (directly under the
    # progressMode Dropdown) -- re-parenting a control between columns is a layout change,
    # so MSA must re-register for an existing install to see the move.
    assert M._template()["settingsVersion"] == 9


# --- master / children ------------------------------------------------------

def test_showbar_is_the_master():
    master = _col1()[0]
    assert master["varName"] == "showBar"
    assert master["type"] == "CheckBox"
    # The master itself is NOT a child of anything.
    assert "masterVarName" not in master
    assert master["value"] is True


def test_children_order_matches_spec():
    # The master group is master + 7 children; ignoreFreeXp is the single standalone LAST
    # entry, so the children are col1[1:-1]. .get (not []) so a stray Label row -- which
    # carries no varName -- yields a clean order mismatch not a KeyError.
    assert [c.get("varName") for c in _col1()[1:-1]] == _CHILD_ORDER


def test_all_seven_children_are_bound_to_showbar():
    children = _col1()[1:-1]   # exclude master (0) and the single standalone control (last)
    assert len(children) == 7
    for c in children:
        assert c["type"] == "CheckBox"
        assert c["masterVarName"] == "showBar", (
            "child %s not bound to showBar master" % c.get("varName"))


def test_ignore_free_xp_is_standalone_last_not_bound_to_master():
    # ignoreFreeXp changes WHICH XP counts, not whether the bar shows, so it is a plain
    # standalone checkbox last in column1 -- with NO masterVarName binding. (showPercent used
    # to sit after it here, but has moved to column2 under progressMode.)
    c = _col1()[-1]
    assert c["varName"] == "ignoreFreeXp"
    assert c["type"] == "CheckBox"
    assert "masterVarName" not in c
    assert c["value"] is False


def test_show_percent_is_in_column2_under_progress_mode_not_bound_to_master():
    # showPercent is a display tweak (prepends a % to the readout), not a visibility gate.
    # It now lives in column2 directly beneath the progressMode Dropdown -- a standalone
    # CheckBox with NO masterVarName binding, and absent from column1.
    assert "showPercent" not in [c.get("varName") for c in _col1()]
    col2 = M._template()["column2"]
    sp = col2[2]
    assert sp["varName"] == "showPercent"
    assert sp["type"] == "CheckBox"
    assert "masterVarName" not in sp
    assert sp["value"] is False
    assert col2[1]["varName"] == "progressMode"   # sits directly under progressMode


def test_column1_has_master_plus_seven_children_plus_one_standalone():
    # master (1) + 7 group children + 1 standalone (ignoreFreeXp) = 9 controls
    # (showPercent moved to column2).
    assert len(_col1()) == 9


# --- the removed "Bar modes" label ------------------------------------------

def test_no_bar_modes_label_leftover():
    # The old "Bar modes" section Label was removed in the restructure; column1 is now a
    # flat [master, ...children] list with no Label rows at all.
    for col in ("column1", "column2"):
        for comp in M._template()[col]:
            text = (comp.get("text") or "")
            assert "Bar modes" not in text
    assert not any(c.get("type") == "Label" for c in _col1())


# --- defaults (polarity + opt-in + position) --------------------------------

def test_show_polarity_defaults_on():
    # Inverted flags default to shown (True) so net behavior is unchanged.
    assert M.DEFAULTS["showBar"] is True
    assert M.DEFAULTS["showWhenComplete"] is True


def test_potential_tier_xi_stays_opt_in():
    assert M.DEFAULTS["showPotentialTierXI"] is False


def test_position_defaults_are_auto():
    assert M.DEFAULTS["posX"] == 0
    assert M.DEFAULTS["posY"] == 0


def test_no_legacy_hide_flags_remain():
    # The old hide-polarity varNames must be gone from both defaults and the template.
    assert "hideAlways" not in M.DEFAULTS
    assert "hideWhenComplete" not in M.DEFAULTS
    var_names = {c.get("varName") for col in ("column1", "column2")
                 for c in M._template()[col]}
    assert "hideAlways" not in var_names
    assert "hideWhenComplete" not in var_names


def test_child_values_track_defaults():
    # Each child checkbox's seeded value mirrors its DEFAULTS entry (so a fresh install
    # renders with the right ticks -- notably potentialTierXI unticked).
    for c in _col1()[1:]:
        var = c["varName"]
        assert c["value"] == M.DEFAULTS[var], (
            "child %s value %r != default %r" % (var, c["value"], M.DEFAULTS[var]))


# --- template <-> i18n column-key lockstep ----------------------------------

def test_col1_keys_match_template_wire_order():
    # settings_i18n.COL1_KEYS is walked in lockstep with the stored template
    # (_sync_template_text). It must match the template's actual order.
    from wgmod_research.adapter import settings_i18n as S
    assert list(S.COL1_KEYS) == [c["varName"] for c in _col1()]


# --- scale dropdown (column2) -----------------------------------------------

def _col2():
    return M._template()["column2"]


def test_scale_default_is_zero():
    assert M.DEFAULTS["scale"] == 0


def test_clamp_scale_coerces_to_known_index():
    # Aslain returns a 0-based int; a bad / out-of-range value guards back to 0.
    assert M._clamp_index(0) == 0
    assert M._clamp_index(1) == 1
    assert M._clamp_index(2) == 0
    assert M._clamp_index(-1) == 0
    assert M._clamp_index(u"1") == 1
    assert M._clamp_index(None) == 0
    assert M._clamp_index(u"nope") == 0


def test_scale_dropdown_is_first_in_column2_above_bar_position():
    dd = _col2()[0]
    assert dd["type"] == "Dropdown"
    assert dd["varName"] == "scale"
    assert dd["value"] == 0
    assert len(dd["options"]) == 2                     # Default / Large
    assert all(o.get("label") for o in dd["options"])  # both option labels present
    # The progressMode Dropdown follows scale, then the showPercent CheckBox (moved here
    # from column1), then the Bar position Label (lockstep with COL2_KEYS below).
    assert _col2()[1]["type"] == "Dropdown"
    assert _col2()[1]["varName"] == "progressMode"
    assert _col2()[2]["type"] == "CheckBox"
    assert _col2()[2]["varName"] == "showPercent"
    assert _col2()[3]["type"] == "Label"


def test_progress_mode_dropdown_follows_scale_with_two_options():
    dd = _col2()[1]
    assert dd["type"] == "Dropdown"
    assert dd["varName"] == "progressMode"
    assert dd["value"] == 0
    assert len(dd["options"]) == 2                     # Current / Current-Required
    assert all(o.get("label") for o in dd["options"])  # both option labels present


def test_col2_keys_match_template_wire_order():
    # settings_i18n.COL2_KEYS is walked in lockstep with the stored template; the
    # Label carries no varName, so pair positionally (scale, progressMode, showPercent,
    # barPosition, posX, posY).
    from wgmod_research.adapter import settings_i18n as S
    col2 = _col2()
    assert list(S.COL2_KEYS) == [
        "scale", "progressMode", "showPercent", "barPosition", "posX", "posY"]
    assert len(col2) == len(S.COL2_KEYS)
    assert col2[0].get("varName") == "scale"
    assert col2[1].get("varName") == "progressMode"
    assert col2[2].get("varName") == "showPercent"
    assert col2[3].get("varName") is None          # barPosition Label -- no varName
    assert col2[4].get("varName") == "posX"
    assert col2[5].get("varName") == "posY"


def test_scale_reads_back_stored_int():
    # scale() defaults to 0 and reads back a stored int index through _apply.
    assert M.scale() == 0
    M._apply({"scale": 1})
    try:
        assert M.scale() == 1
        assert isinstance(M.scale(), int)
    finally:
        M._apply({"scale": 0})   # restore default for other tests


# --- progressMode dropdown (column2) ----------------------------------------

def test_progress_mode_default_is_zero():
    assert M.DEFAULTS["progressMode"] == 0


def test_clamp_progress_mode_coerces_to_known_index():
    # Aslain returns a 0-based int; a bad / out-of-range value guards back to 0 (Current).
    assert M._clamp_index(0) == 0
    assert M._clamp_index(1) == 1
    assert M._clamp_index(2) == 0
    assert M._clamp_index(-1) == 0
    assert M._clamp_index(u"1") == 1
    assert M._clamp_index(None) == 0
    assert M._clamp_index(u"nope") == 0


def test_progress_mode_reads_back_stored_int_not_coerced_to_bool():
    # The dropdown index must round-trip as an INT through _apply -- the non-bool clamp
    # branch keeps index 1 as 1, never the generic bool() branch that would turn it True.
    assert M.progress_mode() == 0
    M._apply({"progressMode": 1})
    try:
        assert M.progress_mode() == 1
        assert isinstance(M.progress_mode(), int)
        assert M.progress_mode() is not True   # not clobbered to a bool
    finally:
        M._apply({"progressMode": 0})   # restore default for other tests


def test_progress_mode_out_of_range_apply_guards_to_zero():
    M._apply({"progressMode": 5})
    try:
        assert M.progress_mode() == 0
    finally:
        M._apply({"progressMode": 0})


# --- showPercent checkbox (column2, under progressMode) ---------------------

def test_show_percent_default_is_false():
    assert M.DEFAULTS["showPercent"] is False


def test_show_percent_reads_back_bool():
    assert M.show_percent() is False
    M._apply({"showPercent": True})
    try:
        assert M.show_percent() is True
    finally:
        M._apply({"showPercent": False})   # restore default for other tests


# --- enabled_modes: the per-mode-toggle -> builder `enabled` set mapping -----
# enabled_modes() is the SEAM between the six per-mode checkboxes and
# build_model's `enabled` gate. Every builder test passes a Mode set directly, so
# a wrong toggle->Mode mapping HERE (e.g. showElite feeding ELITE_REWARDS, or two
# toggles collapsing onto one Mode) would pass the whole builder suite yet silently
# break which vehicles show the bar. Lock the exact 1:1 mapping.

# showTechTree..showPotentialTierXI (the six settings enabled_modes reads) -> Mode.
_TOGGLE_MODE = None  # filled lazily below to keep types import local to the tests


def _toggle_mode_map():
    from wgmod_research.domain import types as t
    return {
        "showTechTree": t.Mode.TECH_TREE,
        "showSkillTree": t.Mode.SKILL_TREE,
        "showFieldMods": t.Mode.FIELD_MODS,
        "showEliteRewards": t.Mode.ELITE_REWARDS,
        "showElite": t.Mode.ELITE,
        "showPotentialTierXI": t.Mode.POTENTIAL_TIER_XI,
    }


def test_enabled_modes_all_on_yields_exactly_the_six_modes():
    mapping = _toggle_mode_map()
    saved = {k: M._settings[k] for k in mapping}
    try:
        for k in mapping:
            M._settings[k] = True
        assert M.enabled_modes() == set(mapping.values())
    finally:
        M._settings.update(saved)


def test_enabled_modes_each_toggle_controls_exactly_its_own_mode():
    # Turning ONE toggle off must drop exactly that toggle's Mode and no other -- this
    # catches both a wrong mapping (drops the wrong Mode) and a shared/duplicate mapping
    # (dropping one collaterally drops another).
    mapping = _toggle_mode_map()
    saved = {k: M._settings[k] for k in mapping}
    try:
        for off in mapping:
            for k in mapping:
                M._settings[k] = True
            M._settings[off] = False
            modes = M.enabled_modes()
            assert mapping[off] not in modes, (
                "%s off must drop %s" % (off, mapping[off]))
            for k, mode in mapping.items():
                if k != off:
                    assert mode in modes, (
                        "%s off wrongly dropped %s" % (off, mode))
    finally:
        M._settings.update(saved)


def test_enabled_modes_all_off_is_empty():
    mapping = _toggle_mode_map()
    saved = {k: M._settings[k] for k in mapping}
    try:
        for k in mapping:
            M._settings[k] = False
        assert M.enabled_modes() == set()
    finally:
        M._settings.update(saved)
