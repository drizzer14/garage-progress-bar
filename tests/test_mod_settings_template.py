# -*- coding: utf-8 -*-
"""Structure tests for the MSA settings-panel template (``bridge/mod_settings.py``).

Locks the three-CATEGORY structure, laid out over TWO columns (MSA only renders columns
side-by-side when the user's global ``multiColumnMode`` toggle is on, so a third column
would stack under column1). Each category opens with an inert Label header. column1
"Modes" = the seven per-mode checkboxes, all plain STANDALONE controls (the old
``showBar`` master is gone, so nothing carries a ``masterVarName``); column2 =
"Formatting" (ignoreFreeXp / showPercent / progressMode), an ``Empty`` spacer, then
"Layout" (the scale Dropdown, a "Position" sub-header, and the two steppers). Polarity /
opt-in / position defaults are unchanged.

``_template()`` itself is a pure dict, engine-free once imported. (The game's
``debug_utils`` is stubbed once in conftest.py.)"""
from wgmod_research.bridge import mod_settings as M

# The seven "Modes" checkboxes, in the exact spec order (they follow the column1 header).
_MODE_ORDER = [
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

def test_settings_version_is_15():
    # Bumped 9 -> 10 when the panel was restructured into three named categories and the
    # showBar master was REMOVED (the restructure alone wouldn't need it -- column identity
    # and masterVarName are absent from Aslain's template signature -- but dropping a
    # varName does), then 10 -> 11 when scale/progressMode became inline RadioButtonGroups:
    # a control's `type` IS part of that signature, so without the bump setModTemplate
    # keeps the STORED template and the radios never appear. Then 11 -> 12 when two more
    # `Empty` spacers were added to column2: a row-count change is NOT structural to
    # Aslain's own signature, but our init() only calls setModTemplate (the one thing that
    # can reshape a STORED template) on a bump/fresh install -- without it, an existing
    # install's stored column2 keeps its old (shorter) shape forever, and
    # _sync_template_text's positional zip against the new (longer) COL2_KEYS then
    # mislabels every row past the first new spacer (live regression). Then 12 -> 13 when
    # the "excludeEliteSystem" child CheckBox was added under showWhenComplete -- a new
    # varName, so the bump was mandatory. Then 13 -> 14 when excludeEliteSystem was REMOVED
    # (replaced by the standalone "allowFallthrough" checkbox) -- removing AND adding a
    # varName, so this bump is mandatory too. Then 14 -> 15 when the Onslaught garage got
    # its OWN X/Y: onslaughtPosY became a user-facing stepper and onslaughtPosX was added
    # (two new varNames), so this bump is mandatory too.
    assert M._template()["settingsVersion"] == 15


# --- category headers -------------------------------------------------------

def test_only_two_columns_are_used():
    # A third column would stack UNDER column1 unless the user's global multiColumnMode
    # toolbar toggle is on (default off), so Layout is merged into column2 instead.
    tpl = M._template()
    assert "column3" not in tpl
    assert "column4" not in tpl


def test_each_category_opens_with_a_bold_label_header():
    tpl = M._template()
    # (column, index, text) -- Formatting and Layout share column2, split by the spacer.
    for col, idx, text in (("column1", 0, u"Modes"),
                           ("column2", 0, u"Formatting"),
                           ("column2", 6, u"Layout")):
        head = tpl[col][idx]
        assert head["type"] == "Label"
        # Bold, wrapped by settings_i18n.render_panel (MSA Labels render HTML).
        assert head["text"] == u"<b>%s</b>" % text
        assert head["useHTML"] is True
        assert "varName" not in head
        # Category headers are inert captions -- no tooltip, no invented filler prose.
        assert "tooltip" not in head


def test_position_subheader_stays_plain():
    # A level BELOW the categories: bolding it too would flatten the hierarchy the
    # spacer + headers create. It keeps its plain text AND its tooltip.
    sub = M._template()["column2"][9]
    assert sub["type"] == "Label"
    assert sub["text"] == u"Position (px)"
    assert "<b>" not in sub["text"]
    assert "useHTML" not in sub
    assert sub["tooltip"].startswith(u"{HEADER}")


def test_empty_spacer_splits_the_two_column2_groups():
    # 20px is Aslain's own createEmpty default. It sits between the last Formatting
    # control and the Layout header, and carries neither text nor varName.
    spacer = M._template()["column2"][5]
    assert spacer == {"type": "Empty", "height": 20}


def test_empty_spacers_precede_progress_mode_and_position():
    # Two more breathing-room spacers: immediately before the progressMode radio group,
    # and immediately before the "Position" sub-header.
    col2 = M._template()["column2"]
    assert col2[3] == {"type": "Empty", "height": 20}
    assert col2[4]["varName"] == "progressMode"
    assert col2[8] == {"type": "Empty", "height": 20}
    assert col2[9]["text"] == u"Position (px)"


# --- modes (column1) --------------------------------------------------------

def test_mode_order_matches_spec():
    # The header occupies slot 0; the seven mode checkboxes follow (the excludeElite-
    # System child comes after, see test_all_seven_modes_are_standalone_checkboxes). .get
    # (not []) so a stray Label row -- which carries no varName -- yields a clean mismatch.
    assert [c.get("varName") for c in _col1()[1:8]] == _MODE_ORDER


def test_all_seven_modes_are_standalone_checkboxes():
    modes = _col1()[1:8]
    assert len(modes) == 7
    for c in modes:
        assert c["type"] == "CheckBox"
        # No master switch any more -- nothing is greyed by anything.
        assert "masterVarName" not in c, (
            "mode %s must not be bound to a master" % c.get("varName"))


def test_allow_fallthrough_is_a_standalone_checkbox_after_a_spacer():
    # column1 ends with an Empty spacer then the standalone allowFallthrough checkbox --
    # NOT nested under anything (unlike the old excludeEliteSystem child it replaces).
    col1 = _col1()
    spacer = col1[8]
    assert spacer == {"type": "Empty", "height": 20}
    tail = col1[9]
    assert tail["type"] == "CheckBox"
    assert tail["varName"] == "allowFallthrough"
    assert "masterVarName" not in tail


def test_column1_is_header_plus_seven_modes_plus_spacer_plus_allow_fallthrough():
    assert len(_col1()) == 10


def test_no_show_bar_leftover():
    # The master switch was deleted outright: no varName, no default, no accessor.
    assert "showBar" not in M.DEFAULTS
    assert not hasattr(M, "show_bar")
    var_names = {c.get("varName") for col in ("column1", "column2")
                 for c in M._template()[col]}
    assert "showBar" not in var_names


# --- formatting + layout (column2) ------------------------------------------

def test_formatting_group_order_and_standalone():
    # Per spec: ignoreFreeXp, showPercent, progressMode -- none of them gate visibility.
    # A spacer (no varName) sits between showPercent and progressMode.
    col2 = M._template()["column2"]
    assert [c.get("varName") for c in col2[1:5]] == [
        "ignoreFreeXp", "showPercent", None, "progressMode"]
    assert col2[1]["type"] == "CheckBox" and col2[1]["value"] is False
    assert col2[2]["type"] == "CheckBox" and col2[2]["value"] is False
    assert col2[3]["type"] == "Empty"
    assert col2[4]["type"] == "RadioButtonGroup"
    for c in col2[1:3] + col2[4:5]:
        assert "masterVarName" not in c


# --- the two index selectors (inline RadioButtonGroups) ---------------------
# Converted from Dropdown in the settingsVersion 10 -> 11 bump. A RadioButtonGroup's
# value is the 0-based index into `options`, exactly as a Dropdown's was, so
# _clamp_index / scale() / progress_mode() / the widget wire are all unchanged -- these
# assertions are what keep that contract honest across the type change.

def _selectors():
    col2 = _col2()
    return {"progressMode": col2[4], "scale": col2[7]}


def test_index_selectors_are_inline_radio_button_groups():
    for var, c in _selectors().items():
        assert c["type"] == "RadioButtonGroup", var
        assert c["varName"] == var
        assert c["inline"] is True, "%s must render as one horizontal row" % var
        # `width` is Dropdown-only -- it must not linger on a radio group.
        assert "width" not in c


def test_index_selectors_keep_two_labelled_options_and_zero_default():
    # The 0-based index contract _clamp_index enforces: exactly two options, so only
    # 0 and 1 are valid, and a fresh install starts at 0.
    for var, c in _selectors().items():
        assert len(c["options"]) == 2, var
        for o in c["options"]:
            assert set(o) == {"label"} and o["label"], var
        assert c["value"] == 0
        assert c["value"] == M.DEFAULTS[var]


# --- the removed "Bar modes" label ------------------------------------------

def test_no_bar_modes_label_leftover():
    # The old "Bar modes" section Label was removed long before the category headers
    # landed; make sure the restructure didn't reintroduce the wording.
    for col in ("column1", "column2"):
        for comp in M._template()[col]:
            assert "Bar modes" not in (comp.get("text") or "")


# --- defaults (polarity + opt-in + position) --------------------------------

def test_show_polarity_defaults_on():
    # The inverted flag defaults to shown (True) so net behavior is unchanged.
    assert M.DEFAULTS["showWhenComplete"] is True


def test_potential_tier_xi_stays_opt_in():
    assert M.DEFAULTS["showPotentialTierXI"] is False


def test_allow_fallthrough_defaults_off():
    assert M.DEFAULTS["allowFallthrough"] is False


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


def test_mode_values_track_defaults():
    # Each mode checkbox's seeded value mirrors its DEFAULTS entry (so a fresh install
    # renders with the right ticks -- notably potentialTierXI and allowFallthrough
    # unticked). Skips the Empty spacer, which carries no varName.
    for c in _col1()[1:]:
        if c["type"] == "Empty":
            continue
        var = c["varName"]
        assert c["value"] == M.DEFAULTS[var], (
            "mode %s value %r != default %r" % (var, c["value"], M.DEFAULTS[var]))


# --- template <-> i18n column-key lockstep ----------------------------------
# _sync_template_text walks each stored column POSITIONALLY against these key tuples, so
# a reorder without a matching COL*_KEYS edit silently mislabels controls. Label rows
# carry no varName, hence the .get() pairing.

def test_col1_keys_match_template_wire_order():
    from wgmod_research.adapter import settings_i18n as S
    col1 = _col1()
    assert list(S.COL1_KEYS) == ["modes"] + _MODE_ORDER + [S.SPACER, "allowFallthrough"]
    assert len(col1) == len(S.COL1_KEYS)
    assert col1[0].get("varName") is None            # "modes" header -- no varName
    assert [c.get("varName") for c in col1[1:]] == list(S.COL1_KEYS)[1:]


def test_col2_keys_match_template_wire_order():
    # column2 holds BOTH the Formatting and Layout groups, so its key tuple covers the
    # SPACER sentinels for the three `Empty` rows, plus the two Label headers and the
    # "position" sub-header (which do carry text but no varName).
    from wgmod_research.adapter import settings_i18n as S
    col2 = _col2()
    assert list(S.COL2_KEYS) == [
        "formatting", "ignoreFreeXp", "showPercent", S.SPACER, "progressMode",
        S.SPACER, "layout", "scale", S.SPACER, "position", "posX", "posY",
        "onslaughtPosX", "onslaughtPosY"]
    # THE alignment guard: _sync_template_text zips these two sequences positionally, so
    # a length mismatch or a shifted slot silently relabels the wrong controls.
    assert len(col2) == len(S.COL2_KEYS)
    assert [c.get("varName") for c in col2] == [
        None, "ignoreFreeXp", "showPercent", None, "progressMode",
        None, None, "scale", None, None, "posX", "posY",
        "onslaughtPosX", "onslaughtPosY"]
    assert [c["type"] for c in col2] == [
        "Label", "CheckBox", "CheckBox", "Empty", "RadioButtonGroup",
        "Empty", "Label", "RadioButtonGroup", "Empty", "Label",
        "NumericStepper", "NumericStepper", "NumericStepper", "NumericStepper"]
    # Every SPACER sentinel lines up with an Empty row and nothing else.
    spacer_idxs = [i for i, k in enumerate(S.COL2_KEYS) if k is S.SPACER]
    assert spacer_idxs == [3, 5, 8]
    assert all(col2[i]["type"] == "Empty" for i in spacer_idxs)


def test_columns_stay_structurally_index_aligned_with_col_keys():
    # A STRUCTURAL invariant, deliberately not a hardcoded index list (unlike the tests
    # above): whatever shape _template() and COL1_KEYS/COL2_KEYS take, the two must stay
    # in positional lockstep, because _sync_template_text zips them together on every
    # existing install. This is what a future spacer insertion (or any row add/remove)
    # must keep true, regardless of exactly where the new row lands.
    from wgmod_research.adapter import settings_i18n as S
    tpl = M._template()
    for col, keys in (("column1", S.COL1_KEYS), ("column2", S.COL2_KEYS)):
        comps = tpl[col]
        assert len(comps) == len(keys), (
            "%s has %d rows but %d keys -- _sync_template_text would misalign every "
            "row past the first divergence" % (col, len(comps), len(keys)))
        for i, (comp, key) in enumerate(zip(comps, keys)):
            if key is S.SPACER:
                assert comp["type"] == "Empty", (
                    "%s[%d] should be the Empty spacer, got %r" % (col, i, comp["type"]))
            elif "varName" in comp:
                assert comp["varName"] == key, (
                    "%s[%d] varName %r != key %r" % (col, i, comp["varName"], key))
            else:
                # A varName-less, non-spacer row (a Label header/sub-header): must not
                # itself be an Empty row masquerading as a labelled control.
                assert comp["type"] != "Empty", (
                    "%s[%d] is an untracked Empty -- add a SPACER for it in %s" % (
                        col, i, "COL1_KEYS" if col == "column1" else "COL2_KEYS"))


def test_spacer_sentinel_is_skipped_by_both_consumers():
    # render_panel must NOT emit an entry for it (it has no _LABELS row and would
    # KeyError on the English fallback); _sync_template_text's t.get(key) then yields
    # None for that slot and simply continues.
    from wgmod_research.adapter import settings_i18n as S
    rendered = S.render_panel({}, lang=u"en")
    assert S.SPACER not in rendered
    assert set(rendered) == (set(S.COL1_KEYS) | set(S.COL2_KEYS)) - {S.SPACER}


# --- scale radio group ------------------------------------------------------

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


# (Both selectors' position, type, options and defaults are asserted by
# test_col2_keys_match_template_wire_order + the two index-selector tests above.)

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


# --- showPercent checkbox (column2, above progressMode) ---------------------

def test_show_percent_default_is_false():
    assert M.DEFAULTS["showPercent"] is False


def test_show_percent_reads_back_bool():
    assert M.show_percent() is False
    M._apply({"showPercent": True})
    try:
        assert M.show_percent() is True
    finally:
        M._apply({"showPercent": False})   # restore default for other tests


# --- allowFallthrough checkbox (column1, standalone) ------------------------

def test_allow_fallthrough_reads_back_bool():
    assert M.allow_fallthrough() is False
    M._apply({"allowFallthrough": True})
    try:
        assert M.allow_fallthrough() is True
    finally:
        M._apply({"allowFallthrough": False})   # restore default for other tests


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
