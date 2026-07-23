# -*- coding: utf-8 -*-
"""Regression: the settings-changed callback must be scoped to OUR linkage.

ModsSettingsAPI fires onSettingsChanged GLOBALLY -- the callback runs for EVERY
mod's settings change and is handed the CHANGING mod's settings dict. A sibling mod
(e.g. 14th_ua's MoE Calculator) stores its own posX/posY/posW/posH under identical
key names, so an unguarded handler would ingest the foreign coordinates and reposition
our bar to the sibling's position. _on_changed must IGNORE any change whose linkage is
not our own LINKAGE (mirroring the linkage guard _on_reset already carries).

The handler paths under test are engine-free (the lazy gameface_bridge.refresh() call
inside the handler degrades to a caught no-op here, exactly as the set_position /
_on_reset tests already rely on); the game's `debug_utils` is stubbed once in
conftest.py."""
from wgmod_research.bridge import mod_settings

# A real sibling mod that ships the SAME posX/posY/posW/posH key names.
_FOREIGN_LINKAGE = "com.14th_ua.moe_calculator"


def test_on_changed_ignores_foreign_linkage():
    # The bug: onSettingsChanged is global, so a SIBLING mod saving its own position
    # (identical key names) must NOT move our bar. Pin a known gpb position, then feed
    # the handler a FOREIGN linkage carrying DIFFERENT coordinates -- our stored position
    # must be untouched (the foreign payload is ignored).
    mod_settings._settings["posX"] = 700
    mod_settings._settings["posY"] = 300
    mod_settings._settings["posW"] = 3840
    mod_settings._settings["posH"] = 2160
    mod_settings._on_changed(_FOREIGN_LINKAGE,
                             {"posX": 111, "posY": 222, "posW": 1920, "posH": 1080})
    assert mod_settings._settings["posX"] == 700
    assert mod_settings._settings["posY"] == 300
    assert mod_settings._settings["posW"] == 3840
    assert mod_settings._settings["posH"] == 2160


def test_on_changed_ignores_foreign_linkage_flags():
    # Same guard for the boolean flags: a sibling mod can't flip our showBar etc.
    mod_settings._settings["showBar"] = True
    mod_settings._on_changed(_FOREIGN_LINKAGE, {"showBar": False})
    assert mod_settings._settings["showBar"] is True


def test_on_changed_applies_own_linkage():
    # The guard must NOT regress legitimate updates: our OWN linkage carrying new
    # coordinates is applied live (the fix can't over-reach and drop real changes).
    mod_settings._settings["posX"] = 700
    mod_settings._settings["posY"] = 300
    mod_settings._on_changed(mod_settings.LINKAGE, {"posX": 111, "posY": 222})
    assert mod_settings._settings["posX"] == 111
    assert mod_settings._settings["posY"] == 222


def test_on_changed_applies_own_linkage_flags():
    # A real flag change on our own linkage still lands.
    mod_settings._settings["showBar"] = True
    mod_settings._on_changed(mod_settings.LINKAGE, {"showBar": False})
    assert mod_settings._settings["showBar"] is False
