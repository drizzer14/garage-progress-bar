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
    stored = {"enabled": False, "hideAlways": True, "hideWhenComplete": False,
              "posX": 5, "posY": 6}
    out = mod_settings._full_settings_for_write(_FakeApi(stored))
    assert out["enabled"] is False          # host toggle preserved, not clobbered
    assert out["posX"] == 111 and out["posY"] == 222   # our live values overlaid
    # every managed varName is present (updateModSettings replaces the whole dict)
    for k in ("hideAlways", "hideWhenComplete", "posX", "posY", "enabled"):
        assert k in out


def test_full_settings_defaults_enabled_when_missing():
    # Repairs a corrupted stored dict (no 'enabled') -> defaults to True so the host
    # renderer never KeyErrors.
    out = mod_settings._full_settings_for_write(_FakeApi({"hideAlways": False}))
    assert out["enabled"] is True


def test_full_settings_handles_no_stored():
    # No stored settings (fresh / template mismatch) -> still a complete dict.
    out = mod_settings._full_settings_for_write(_FakeApi(None))
    assert out["enabled"] is True
    for k in ("hideAlways", "hideWhenComplete", "posX", "posY"):
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


def test_reset_returns_to_auto_not_seeded_px():
    # Reset -> AUTO (0/0) so the resolution-relative CSS default applies, even when the
    # host's stored 'defaults' snapshot still carries a seeded px. (Pre-fix this pinned
    # the stale seeded pixels, which is exactly the drift being removed.)
    mod_settings._settings["posX"] = 700
    mod_settings._settings["posY"] = 300
    mod_settings._on_reset(mod_settings.LINKAGE, {"posX": 960, "posY": 190})
    assert mod_settings._settings["posX"] == 0
    assert mod_settings._settings["posY"] == 0
