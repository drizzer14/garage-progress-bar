# -*- coding: utf-8 -*-
"""Unit tests for the draggable bar-position storage (clamp + defaults).

clamp_pos itself is pure and engine-free; the game's `debug_utils` is stubbed once in
conftest.py."""
from wgmod_research.bridge import mod_settings


def test_clamp_pos_passthrough_in_range():
    assert mod_settings.clamp_pos(0) == 0
    assert mod_settings.clamp_pos(1) == 1
    assert mod_settings.clamp_pos(1920) == 1920
    assert mod_settings.clamp_pos(mod_settings.POS_MAX) == mod_settings.POS_MAX


def test_clamp_pos_negative_becomes_auto():
    # Negative (and any < 0) collapses to 0 == "auto / unseeded".
    assert mod_settings.clamp_pos(-1) == 0
    assert mod_settings.clamp_pos(-9999) == 0


def test_clamp_pos_top_edge_survives_zero_sentinel():
    # Bug 4: y=0 is the "auto" sentinel, so a flush-to-top drag must land at 1, not 0.
    # clamp_pos itself keeps 0 mapping to 0
    # (unchanged) -- the JS drag + bridge guard are what floor the coord at 1; this
    # locks in that 1 is a legal stored placement while 0 stays the sentinel.
    assert mod_settings.clamp_pos(0) == 0    # sentinel preserved (auto)
    assert mod_settings.clamp_pos(1) == 1    # a real top-edge placement is kept


def test_clamp_pos_over_max_is_capped():
    assert mod_settings.clamp_pos(mod_settings.POS_MAX + 1) == mod_settings.POS_MAX
    assert mod_settings.clamp_pos(10 ** 9) == mod_settings.POS_MAX


def test_clamp_pos_non_numeric_becomes_zero():
    assert mod_settings.clamp_pos(None) == 0
    assert mod_settings.clamp_pos("nope") == 0
    assert mod_settings.clamp_pos([1, 2]) == 0


def test_clamp_pos_floats_truncate_to_int():
    assert mod_settings.clamp_pos(12.9) == 12
    assert mod_settings.clamp_pos("37") == 37


def test_defaults_include_auto_position():
    assert mod_settings.DEFAULTS["posX"] == 0
    assert mod_settings.DEFAULTS["posY"] == 0


def test_defaults_include_unknown_capture_viewport():
    # posW/posH default to 0 == "unknown capture viewport" (auto position, or a pre-fix
    # saved pin). The widget adopts the current viewport on first sight.
    assert mod_settings.DEFAULTS["posW"] == 0
    assert mod_settings.DEFAULTS["posH"] == 0


class _FakeApi(object):
    """Minimal stand-in for g_modsSettingsApi.getModSettings."""
    def __init__(self, stored):
        self._stored = stored

    def getModSettings(self, linkage, template):
        return self._stored


def test_full_settings_preserves_host_enabled_key():
    # The bug: updateModSettings REPLACES the stored dict, so a partial write dropped
    # Aslain's 'enabled' toggle and blanked the whole panel. The full-write must keep
    # 'enabled' (and honor its stored value) while overlaying our own varNames.
    mod_settings._settings["posX"] = 111
    mod_settings._settings["posY"] = 222
    stored = {"enabled": False, "showWhenComplete": True, "posX": 5, "posY": 6}
    out = mod_settings._full_settings_for_write(_FakeApi(stored))
    assert out["enabled"] is False          # host toggle preserved, not clobbered
    assert out["posX"] == 111 and out["posY"] == 222   # our live values overlaid
    # every managed varName is present (updateModSettings replaces the whole dict)
    for k in ("showWhenComplete", "showTechTree", "posX", "posY", "enabled"):
        assert k in out


def test_full_settings_defaults_enabled_when_missing():
    # Repairs a corrupted stored dict (no 'enabled') -> defaults to True so the host
    # renderer never KeyErrors.
    out = mod_settings._full_settings_for_write(_FakeApi({"showWhenComplete": True}))
    assert out["enabled"] is True


# --- per-vehicle mode-switch overrides (JSON-string map) --------------------

def test_mode_overrides_defaults_to_empty_map():
    assert mod_settings.DEFAULTS["modeOverrides"] == "{}"


def test_mode_override_round_trip():
    # set_mode_override mutates the in-memory JSON map (MSA + refresh degrade to no-ops in
    # tests); mode_override reads the same vehicle's choice back.
    mod_settings._settings["modeOverrides"] = "{}"
    mod_settings.set_mode_override(1234, "elite")
    assert mod_settings.mode_override(1234) == "elite"
    # a different vehicle is independent / untouched.
    assert mod_settings.mode_override(5678) is None
    mod_settings.set_mode_override(5678, "field_mods")
    assert mod_settings.mode_override(1234) == "elite"
    assert mod_settings.mode_override(5678) == "field_mods"


def test_mode_override_intcd_zero_rejected():
    mod_settings._settings["modeOverrides"] = "{}"
    mod_settings.set_mode_override(0, "elite")
    assert mod_settings.mode_override(0) is None
    assert mod_settings._settings["modeOverrides"] == "{}"


def test_mode_override_bad_json_is_none():
    # A corrupt stored value never raises -> treated as no override.
    mod_settings._settings["modeOverrides"] = "not json"
    assert mod_settings.mode_override(1234) is None


def test_apply_keeps_mode_overrides_string():
    # _apply keeps the JSON string verbatim; a non-string value falls back to "{}".
    mod_settings._settings["modeOverrides"] = "{}"
    mod_settings._apply({"modeOverrides": '{"42": "elite"}'})
    assert mod_settings._settings["modeOverrides"] == '{"42": "elite"}'
    mod_settings._apply({"modeOverrides": 123})
    assert mod_settings._settings["modeOverrides"] == "{}"


def test_full_settings_handles_no_stored():
    # No stored settings (fresh / template mismatch) -> still a complete dict.
    out = mod_settings._full_settings_for_write(_FakeApi(None))
    assert out["enabled"] is True
    for k in ("showWhenComplete", "showTechTree", "posX", "posY"):
        assert k in out


def test_on_reset_ignores_other_mods():
    # onResetMod is a global event across every mod; our handler must only act on our
    # own linkage (else another mod's reset would wipe our position). Foreign linkage
    # returns before any refresh, so this is safe to call in the test env.
    mod_settings._settings["posX"] = 999
    mod_settings._settings["posY"] = 888
    mod_settings._on_reset("some.other.mod", {"posX": 0, "posY": 0})
    assert mod_settings._settings["posX"] == 999
    assert mod_settings._settings["posY"] == 888


# --- bar position: a drag/stepper edit pins the chosen px (auto is never sent) --------

def test_real_drag_persists_as_position():
    # A real drag / stepper edit pins the chosen px. (An auto default -- posX/posY 0 -- is
    # never sent from the widget; it keeps the CSS default. MSA calls inside set_position
    # degrade to no-ops in the test env.)
    mod_settings._settings["posX"] = 0
    mod_settings._settings["posY"] = 0
    mod_settings.set_position(700, 300)
    assert mod_settings._settings["posX"] == 700
    assert mod_settings._settings["posY"] == 300


# --- per-garage X AND Y (Onslaught vs regular garage) --------------------------------

def test_default_onslaught_pos_inherits_regular():
    assert mod_settings.DEFAULTS["onslaughtPosX"] == 0
    assert mod_settings.DEFAULTS["onslaughtPosY"] == 0


def test_set_position_onslaught_writes_both_onslaught_coords_only():
    # onslaught=True routes BOTH x/y into onslaughtPosX/onslaughtPosY, leaves the regular
    # posX/posY untouched, and still writes the SHARED posW/posH.
    mod_settings._settings["posX"] = 111
    mod_settings._settings["posY"] = 222
    mod_settings._settings["onslaughtPosX"] = 0
    mod_settings._settings["onslaughtPosY"] = 0
    mod_settings.set_position(30, 500, w=3840, h=2160, onslaught=True)
    assert mod_settings._settings["onslaughtPosX"] == 30
    assert mod_settings._settings["onslaughtPosY"] == 500
    assert mod_settings._settings["posX"] == 111          # regular X unchanged
    assert mod_settings._settings["posY"] == 222          # regular Y unchanged
    assert mod_settings._settings["posW"] == 3840 and mod_settings._settings["posH"] == 2160


def test_set_position_default_writes_only_regular_coords():
    # Default (onslaught=False) writes posX/posY and leaves the onslaught keys untouched.
    mod_settings._settings["posX"] = 0
    mod_settings._settings["posY"] = 0
    mod_settings._settings["onslaughtPosX"] = 111
    mod_settings._settings["onslaughtPosY"] = 222
    mod_settings.set_position(30, 500)
    assert mod_settings._settings["posX"] == 30
    assert mod_settings._settings["posY"] == 500
    assert mod_settings._settings["onslaughtPosX"] == 111   # onslaught X unchanged
    assert mod_settings._settings["onslaughtPosY"] == 222   # onslaught Y unchanged


def test_onslaught_pos_falls_back_to_regular_when_unset():
    mod_settings._settings["posX"] = 960
    mod_settings._settings["posY"] = 190
    mod_settings._settings["onslaughtPosX"] = 0
    mod_settings._settings["onslaughtPosY"] = 0
    assert mod_settings.onslaught_pos_x() == 960           # 0 -> inherit regular X
    assert mod_settings.onslaught_pos_y() == 190           # 0 -> inherit regular Y


def test_onslaught_pos_uses_pinned_when_set():
    mod_settings._settings["posX"] = 960
    mod_settings._settings["posY"] = 190
    mod_settings._settings["onslaughtPosX"] = 42
    mod_settings._settings["onslaughtPosY"] = 420
    assert mod_settings.onslaught_pos_x() == 42
    assert mod_settings.onslaught_pos_y() == 420


def test_apply_clamps_onslaught_pos_as_a_position_not_a_bool():
    # Root cause: _on_changed re-ingests the FULL settings dict (MSA's global
    # onSettingsChanged broadcast, fired by set_position's own saveState()) through
    # _apply(). Without their own clamp_pos branch, the onslaught keys fell through to the
    # generic bool() coercion -- turning a just-written numeric coord into True.
    mod_settings._apply({"onslaughtPosX": 300, "onslaughtPosY": 500})
    assert mod_settings._settings["onslaughtPosX"] == 300
    assert mod_settings._settings["onslaughtPosX"] is not True
    assert mod_settings._settings["onslaughtPosY"] == 500
    assert mod_settings._settings["onslaughtPosY"] is not True
    # a passed bool coerces to the 0/1 int clamp_pos yields, never stays a bool.
    mod_settings._apply({"onslaughtPosX": True})
    assert mod_settings._settings["onslaughtPosX"] is not True


# --- capture viewport (posW/posH) for resolution-aware rescale -----------------------

def test_real_drag_stores_capture_viewport():
    # A real drag records the viewport (posW/posH) the px were captured at, so the widget
    # can rescale the pin proportionally after a resolution / UI-scale change.
    mod_settings._settings["posW"] = 0
    mod_settings._settings["posH"] = 0
    mod_settings.set_position(700, 300, w=3840, h=2160)
    assert mod_settings._settings["posW"] == 3840
    assert mod_settings._settings["posH"] == 2160
    assert mod_settings.pos_w() == 3840 and mod_settings.pos_h() == 2160


def test_capture_viewport_is_clamped():
    # w/h go through the same clamp as posX/posY (non-numeric / negative -> 0).
    mod_settings.set_position(700, 300, w=-5, h="nope")
    assert mod_settings._settings["posW"] == 0
    assert mod_settings._settings["posH"] == 0


def test_reset_returns_to_auto_not_seeded_px():
    # Reset -> AUTO (0/0) so the resolution-relative CSS default applies, even when the
    # host's stored 'defaults' snapshot still carries a seeded px. (Pre-fix this pinned
    # the stale seeded pixels, which is exactly the drift being removed.)
    mod_settings._settings["posX"] = 700
    mod_settings._settings["posY"] = 300
    mod_settings._settings["posW"] = 3840
    mod_settings._settings["posH"] = 2160
    mod_settings._on_reset(mod_settings.LINKAGE, {"posX": 960, "posY": 190})
    assert mod_settings._settings["posX"] == 0
    assert mod_settings._settings["posY"] == 0
    # the capture viewport is cleared too, so a reset truly returns to auto
    assert mod_settings._settings["posW"] == 0
    assert mod_settings._settings["posH"] == 0


# --- localized settings template (see adapter/settings_i18n) --------------------------

# `helpers` is a game module absent under pytest, so settings_i18n.client_language()
# fails soft to English -- _template() renders the English master here.
_VARNAMES = {"showWhenComplete", "allowFallthrough", "ignoreFreeXp", "showPercent",
             "showTechTree", "showSkillTree", "showFieldMods", "showEliteRewards",
             "showElite", "showPotentialTierXI", "scale", "progressMode", "posX", "posY",
             "onslaughtPosX", "onslaughtPosY"}

_COLUMNS = ("column1", "column2")

# The seven "Modes" checkboxes in column1 -- all standalone now (no master switch).
_MODES = {"showTechTree", "showFieldMods", "showPotentialTierXI", "showSkillTree",
          "showEliteRewards", "showElite", "showWhenComplete"}


def test_template_structure_and_english_text():
    tpl = mod_settings._template()
    # Structure the host owns is language-independent.
    assert tpl["settingsVersion"] == 15          # bumped for the onslaught X/Y steppers
    assert tpl["modDisplayName"] == "Garage Progress Bar"   # brand, never translated
    varnames = [c["varName"] for col in _COLUMNS for c in tpl[col] if "varName" in c]
    assert set(varnames) == _VARNAMES
    assert len(varnames) == len(_VARNAMES)                  # no dupes / drops
    # Every control carries text; every control EXCEPT the three category headers also
    # carries a tooltip (they're inert captions -- no invented filler prose). The Empty
    # spacer is pure layout and carries neither.
    headers = {u"<b>Modes</b>", u"<b>Formatting</b>", u"<b>Layout</b>"}
    for col in _COLUMNS:
        for c in tpl[col]:
            if c["type"] == "Empty":
                assert "text" not in c and "tooltip" not in c
                continue
            assert c.get("text")
            assert bool(c.get("tooltip")) is (c["text"] not in headers)
    # column1 = the "Modes" header + the seven per-mode checkboxes, all STANDALONE (the
    # showBar master is gone, so nothing carries a masterVarName any more) -- plus a
    # spacer and the standalone allowFallthrough checkbox at the end (also no master).
    col1 = tpl["column1"]
    assert col1[0]["type"] == "Label" and col1[0]["text"] == u"<b>Modes</b>"
    assert col1[8] == {"type": "Empty", "height": 20}
    modes = [c for c in col1[1:] if c["type"] != "Empty"]
    assert {c["varName"] for c in modes} == _MODES | {"allowFallthrough"}
    for c in modes:
        assert "masterVarName" not in c
    # Mode order per spec.
    assert [c["varName"] for c in modes] == [
        "showTechTree", "showFieldMods", "showPotentialTierXI", "showSkillTree",
        "showEliteRewards", "showElite", "showWhenComplete", "allowFallthrough"]
    # Mod-invented text comes from the tables (English in the test env).
    # column2 carries BOTH remaining categories, split by Empty spacers.
    col2 = tpl["column2"]
    assert col2[0]["text"] == u"<b>Formatting</b>"                   # category header (bold)
    assert col2[1]["text"] == u"Ignore Free XP"                      # ignoreFreeXp
    assert col2[2]["text"] == u"Show Progress %"                     # showPercent
    assert col2[3]["type"] == "Empty"                                # spacer before progressMode
    assert col2[4]["text"] == u"Progress Mode"                       # progressMode radios
    assert col2[5]["type"] == "Empty"                                # group spacer
    assert col2[6]["text"] == u"<b>Layout</b>"                       # category header (bold)
    assert col2[7]["text"] == u"Scale"                               # scale radios
    assert col2[8]["type"] == "Empty"                                # spacer before Position
    assert col2[9]["text"] == u"Position (px)"                       # sub-header, NOT bold
    assert col2[10]["varName"] == "posX"                             # regular steppers
    assert col2[11]["varName"] == "posY"
    assert col2[12]["varName"] == "onslaughtPosX"                    # Onslaught steppers
    assert col2[12]["text"] == u"Horizontal (Onslaught X)"
    assert col2[13]["varName"] == "onslaughtPosY"
    assert col2[13]["text"] == u"Vertical (Onslaught Y)"
    # Per-mode checkbox labels come from WG's own strings (i18n.widget_labels(), which
    # fails soft to English feature names here).
    assert col1[1]["text"] == u"Research"                            # showTechTree
    assert col1[6]["text"] == u"Elite System"                        # showElite
    # showWhenComplete is mod-invented.
    assert col1[7]["text"] == u"Fully Progressed"                    # showWhenComplete


class _FakeStateApi(object):
    """Stand-in for an MSA api that stores a template + counts saveState() calls."""
    def __init__(self, template):
        self.state = {"templates": {mod_settings.LINKAGE: template}}
        self.saved = 0

    def saveState(self):
        self.saved += 1


def test_sync_template_text_rewrites_stale_and_saves():
    # column1[1] is the first real control (slot 0 is the "Modes" category Label, which
    # carries no tooltip at all).
    fresh = mod_settings._template()         # correct (English) text
    good_text = fresh["column1"][1]["text"]
    good_tip = fresh["column1"][1]["tooltip"]
    fresh["column1"][1]["text"] = u"STALE LABEL"
    fresh["column1"][1]["tooltip"] = u"STALE TIP"
    api = _FakeStateApi(fresh)
    mod_settings._sync_template_text(api)
    assert fresh["column1"][1]["text"] == good_text
    assert fresh["column1"][1]["tooltip"] == good_tip
    assert api.saved == 1                    # changed -> persisted once


def test_sync_template_text_rewrites_a_category_header_past_the_spacer():
    # The Label headers are walked positionally too (they carry no varName), so a stale
    # header caption must still be refreshed -- and its absent tooltip left absent. The
    # "Layout" header sits AFTER an Empty spacer, so this also proves the SPACER sentinel
    # keeps COL2_KEYS aligned: without it this row would be relabelled "Scale".
    fresh = mod_settings._template()
    fresh["column2"][6]["text"] = u"STALE HEADER"
    api = _FakeStateApi(fresh)
    mod_settings._sync_template_text(api)
    assert fresh["column2"][6]["text"] == u"<b>Layout</b>"
    assert "tooltip" not in fresh["column2"][6]
    assert fresh["column2"][7]["text"] == u"Scale"      # neighbours unshifted
    assert fresh["column2"][5] == {"type": "Empty", "height": 20}
    assert api.saved == 1


def test_sync_template_text_is_idempotent_over_the_bold_headers():
    # THE regression guard for the bold category headers. The <b>...</b> wrap lives ONLY in
    # settings_i18n.render_panel, so _template() and _sync_template_text see the SAME
    # string. Had _template() wrapped independently, sync would find a mismatch every init,
    # strip the bold back out, and fire a saveState() on every single launch -- a test that
    # merely asserts "the text is bold" would not catch that. So: sync a FRESH template
    # twice and require zero writes both times, and the bold still intact after.
    fresh = mod_settings._template()
    api = _FakeStateApi(fresh)
    mod_settings._sync_template_text(api)
    assert api.saved == 0                    # pass 1: already current -> no write
    mod_settings._sync_template_text(api)
    assert api.saved == 0                    # pass 2: still no write (not oscillating)
    assert fresh["column1"][0]["text"] == u"<b>Modes</b>"
    assert fresh["column2"][0]["text"] == u"<b>Formatting</b>"
    assert fresh["column2"][6]["text"] == u"<b>Layout</b>"
    assert fresh["column2"][9]["text"] == u"Position (px)"   # sub-header still plain


def test_sync_template_text_noop_when_current():
    api = _FakeStateApi(mod_settings._template())
    mod_settings._sync_template_text(api)
    assert api.saved == 0                    # already current -> no write


def test_sync_template_text_skips_a_length_mismatched_stored_column():
    # THE regression guard: an EXISTING install's stored column2 can be SHORTER than the
    # live COL2_KEYS whenever a row was added without a settingsVersion bump forcing
    # setModTemplate to reshape it (init() only calls setModTemplate on a bump/fresh
    # install -- see the settingsVersion 11->12 changelog in _template()). Walking that
    # shorter list positionally against the longer COL2_KEYS used to relabel every row
    # past the divergence point ("Layout" rendered twice, "Scale" bleeding onto the
    # Layout/Position rows). Simulate the stale stored shape by removing the two new
    # Empty spacers, and require _sync_template_text to leave every remaining row
    # untouched rather than mislabel it.
    stale = mod_settings._template()
    stale_col2 = stale["column2"]
    before = [dict(c) for c in stale_col2]     # snapshot for the untouched-ness check
    del stale_col2[8]   # the spacer before "position"
    del stale_col2[3]   # the spacer before "progressMode"
    assert len(stale_col2) == len(mod_settings.settings_i18n.COL2_KEYS) - 2

    api = _FakeStateApi(stale)
    mod_settings._sync_template_text(api)

    assert api.saved == 0                     # column2 skipped outright -> no write
    # Every surviving row keeps its ORIGINAL text/tooltip -- none of the corruption the
    # live regression produced (no stray "Layout"/"Scale" bleed-through).
    remaining = [c for i, c in enumerate(before) if i not in (3, 8)]
    assert stale_col2 == remaining


def test_sync_template_text_guards_missing_template():
    # No stored template for our linkage -> silent no-op, never raises.
    api = _FakeStateApi(None)
    api.state = {"templates": {}}
    mod_settings._sync_template_text(api)
    assert api.saved == 0


def test_sync_template_text_relabels_stale_radio_options(monkeypatch):
    # THE bug this locks: MSA stores a COPY of the option labels too (not just text/
    # tooltip), so a stored template whose scale options were rendered in English never
    # picks up a later client-language change without this rewrite.
    import sys
    import types
    stale = mod_settings._template()          # built while client_language() == "en"
    scale = stale["column2"][7]
    assert scale["varName"] == "scale"
    assert [o["label"] for o in scale["options"]] == [u"Default", u"Large"]

    fake = types.ModuleType(u"helpers")
    fake.getClientLanguage = lambda: u"de"
    monkeypatch.setitem(sys.modules, u"helpers", fake)

    api = _FakeStateApi(stale)
    mod_settings._sync_template_text(api)     # now runs with "de" active

    assert [o["label"] for o in scale["options"]] == [u"Standard", u"Groß"]
    assert api.saved == 1
