# -*- coding: utf-8 -*-
"""Unit tests for the draggable bar-position storage (clamp + defaults).

mod_settings imports the game's `debug_utils` at module load, so stub it before
importing -- clamp_pos itself is pure and engine-free."""
import sys
import types

if "debug_utils" not in sys.modules:
    _dbg = types.ModuleType("debug_utils")
    _dbg.LOG_CURRENT_EXCEPTION = lambda *a, **k: None
    _dbg.LOG_NOTE = lambda *a, **k: None
    sys.modules["debug_utils"] = _dbg

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
    # Bug 4: y=0 is the "auto/unseeded" sentinel (re-seeded on the next push), so a
    # flush-to-top drag must land at 1, not 0. clamp_pos itself keeps 0 mapping to 0
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
    stored = {"enabled": False, "showBar": True, "showWhenComplete": True,
              "posX": 5, "posY": 6}
    out = mod_settings._full_settings_for_write(_FakeApi(stored))
    assert out["enabled"] is False          # host toggle preserved, not clobbered
    assert out["posX"] == 111 and out["posY"] == 222   # our live values overlaid
    # every managed varName is present (updateModSettings replaces the whole dict)
    for k in ("showBar", "showWhenComplete", "posX", "posY", "enabled"):
        assert k in out


def test_full_settings_defaults_enabled_when_missing():
    # Repairs a corrupted stored dict (no 'enabled') -> defaults to True so the host
    # renderer never KeyErrors.
    out = mod_settings._full_settings_for_write(_FakeApi({"showBar": True}))
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
    for k in ("showBar", "showWhenComplete", "posX", "posY"):
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


# --- position-seed drift fix (Option 1: never persist the seed as a position) --------

def test_seed_does_not_persist_as_position():
    # The widget's SEED (is_default=True) records the panel's default target / stepper
    # label only -- it must NOT pin posX/posY. Leaving them 0 (auto) keeps the
    # resolution-relative CSS default in force, so the bar never drifts when the game
    # resolution changes. (MSA calls inside set_position degrade to no-ops in the test env.)
    mod_settings._settings["posX"] = 0
    mod_settings._settings["posY"] = 0
    mod_settings.set_position(960, 190, is_default=True)
    assert mod_settings._settings["posX"] == 0
    assert mod_settings._settings["posY"] == 0


def test_real_drag_persists_as_position():
    # A real drag / stepper edit (is_default=False) DOES pin the chosen px.
    mod_settings._settings["posX"] = 0
    mod_settings._settings["posY"] = 0
    mod_settings.set_position(700, 300, is_default=False)
    assert mod_settings._settings["posX"] == 700
    assert mod_settings._settings["posY"] == 300


# --- capture viewport (posW/posH) for resolution-aware rescale -----------------------

def test_real_drag_stores_capture_viewport():
    # A real drag records the viewport (posW/posH) the px were captured at, so the widget
    # can rescale the pin proportionally after a resolution / UI-scale change.
    mod_settings._settings["posW"] = 0
    mod_settings._settings["posH"] = 0
    mod_settings.set_position(700, 300, is_default=False, w=3840, h=2160)
    assert mod_settings._settings["posW"] == 3840
    assert mod_settings._settings["posH"] == 2160
    assert mod_settings.pos_w() == 3840 and mod_settings.pos_h() == 2160


def test_capture_viewport_is_clamped():
    # w/h go through the same clamp as posX/posY (non-numeric / negative -> 0).
    mod_settings.set_position(700, 300, is_default=False, w=-5, h="nope")
    assert mod_settings._settings["posW"] == 0
    assert mod_settings._settings["posH"] == 0


def test_seed_does_not_store_capture_viewport():
    # The seed (is_default=True) doesn't pin px, so it must not record a capture viewport
    # either (posW/posH stay as-is / auto).
    mod_settings._settings["posW"] = 0
    mod_settings._settings["posH"] = 0
    mod_settings.set_position(960, 190, is_default=True, w=3840, h=2160)
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
_VARNAMES = {"showBar", "showWhenComplete", "ignoreFreeXp", "showTechTree",
             "showSkillTree", "showFieldMods", "showEliteRewards", "showElite",
             "showPotentialTierXI", "posX", "posY"}

# The seven controls nested under the showBar master (greyed while it's off). ignoreFreeXp
# is NOT here -- it's a standalone control after the group (see below).
_CHILDREN = {"showTechTree", "showFieldMods", "showPotentialTierXI", "showSkillTree",
             "showEliteRewards", "showElite", "showWhenComplete"}


def test_template_structure_and_english_text():
    tpl = mod_settings._template()
    # Structure the host owns is language-independent.
    assert tpl["settingsVersion"] == 6           # bumped for ignoreFreeXp -> standalone
    assert tpl["modDisplayName"] == "Garage Progress Bar"   # brand, never translated
    varnames = [c["varName"] for col in ("column1", "column2")
                for c in tpl[col] if "varName" in c]
    assert set(varnames) == _VARNAMES
    assert len(varnames) == len(_VARNAMES)                  # no dupes / drops
    # Every visible control carries text + tooltip (no Label rows remain in column1).
    for col in ("column1", "column2"):
        for c in tpl[col]:
            assert c.get("text")
            assert c.get("tooltip")
    # showBar is the MASTER (first control, no masterVarName); the seven group controls are
    # its children (createControlsGroup's masterVarName key). ignoreFreeXp is the STANDALONE
    # last control -- not bound to the master.
    col1 = tpl["column1"]
    assert col1[0]["varName"] == "showBar"
    assert "masterVarName" not in col1[0]
    children = [c for c in col1[1:-1]]            # exclude master and the standalone last
    assert {c["varName"] for c in children} == _CHILDREN
    for c in children:
        assert c["masterVarName"] == "showBar"
        assert "masterIndent" not in c            # default indent = visual nest
    # Child order per spec.
    assert [c["varName"] for c in children] == [
        "showTechTree", "showFieldMods", "showPotentialTierXI", "showSkillTree",
        "showEliteRewards", "showElite", "showWhenComplete"]
    # ignoreFreeXp: standalone last control in column1, NOT bound to the master.
    assert col1[-1]["varName"] == "ignoreFreeXp"
    assert "masterVarName" not in col1[-1]
    # Mod-invented text comes from the tables (English in the test env).
    assert col1[0]["text"] == u"Show Progress Bar"                   # showBar master
    assert tpl["column2"][0]["text"] == u"Bar position (px)"         # barPosition Label
    # Per-mode checkbox labels come from WG's own strings (i18n.widget_labels(), which
    # fails soft to English feature names here).
    assert col1[1]["text"] == u"Research"                            # showTechTree
    assert col1[6]["text"] == u"Elite System"                        # showElite
    # showWhenComplete / ignoreFreeXp are mod-invented children.
    assert col1[7]["text"] == u"Fully Progressed"                    # showWhenComplete
    assert col1[8]["text"] == u"Ignore Free XP"                      # ignoreFreeXp


class _FakeStateApi(object):
    """Stand-in for an MSA api that stores a template + counts saveState() calls."""
    def __init__(self, template):
        self.state = {"templates": {mod_settings.LINKAGE: template}}
        self.saved = 0

    def saveState(self):
        self.saved += 1


def test_sync_template_text_rewrites_stale_and_saves():
    fresh = mod_settings._template()         # correct (English) text
    good_text = fresh["column1"][0]["text"]
    good_tip = fresh["column1"][0]["tooltip"]
    fresh["column1"][0]["text"] = u"STALE LABEL"
    fresh["column1"][0]["tooltip"] = u"STALE TIP"
    api = _FakeStateApi(fresh)
    mod_settings._sync_template_text(api)
    assert fresh["column1"][0]["text"] == good_text
    assert fresh["column1"][0]["tooltip"] == good_tip
    assert api.saved == 1                    # changed -> persisted once


def test_sync_template_text_noop_when_current():
    api = _FakeStateApi(mod_settings._template())
    mod_settings._sync_template_text(api)
    assert api.saved == 0                    # already current -> no write


def test_sync_template_text_guards_missing_template():
    # No stored template for our linkage -> silent no-op, never raises.
    api = _FakeStateApi(None)
    api.state = {"templates": {}}
    mod_settings._sync_template_text(api)
    assert api.saved == 0
