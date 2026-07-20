# -*- coding: utf-8 -*-
"""Value-migration tests for the settings shim (``bridge/mod_settings.init``).

The bug this locks: Aslain MSA's ``setModTemplate`` resets every saved value to the
template defaults whenever the template's ``settingsVersion`` exceeds the stored one, and
``getModSettings`` reports ``None`` on that bump -- so ``init()`` fell into its
``setModTemplate`` else-branch and lost the user's settings on nearly every feature
release. The shim reads the raw previously-stored dict (still at
``api.state['settings'][LINKAGE]`` before ``setModTemplate`` runs), overlays the surviving
values onto the fresh defaults, and persists once, so the wipe never lands on disk.

mod_settings imports the game's ``debug_utils`` at module load, so stub it first (as the
sibling tests do); ``init()`` resolves its api through ``_primary_api()`` -> a faked
``gui.aslainMenu`` module injected per test."""
import sys
import types

import pytest

if "debug_utils" not in sys.modules:
    _dbg = types.ModuleType("debug_utils")
    _dbg.LOG_CURRENT_EXCEPTION = lambda *a, **k: None
    _dbg.LOG_NOTE = lambda *a, **k: None
    sys.modules["debug_utils"] = _dbg

from wgmod_research.bridge import mod_settings as M


class _FakeMsaApi(object):
    """Models Aslain MSA's settingsVersion-bump behavior for the migration shim.

    - ``getModSettings`` returns ``None`` while the template's settingsVersion exceeds the
      stored one (the wipe path init()'s else-branch reacts to); once setModTemplate has
      recorded the new version, it returns the current stored dict.
    - ``setModTemplate`` resets the stored dict to the template's varName defaults (the
      host-owned ``enabled`` toggle is preserved across the reset), records the new version,
      and returns the fresh defaults.
    - The raw previously-stored values live at ``.state['settings'][LINKAGE]`` until
      setModTemplate overwrites them.
    """

    def __init__(self, stored=None, stored_version=0):
        settings = {M.LINKAGE: dict(stored)} if stored is not None else {}
        self.state = {"settings": settings, "templates": {}}
        self._stored_version = stored_version
        self.saved = 0
        self.updated = 0
        self.registered_cb = None
        self.template_cb = None

    @staticmethod
    def _defaults_from_template(template):
        d = {}
        for col in ("column1", "column2"):
            for c in template.get(col, []):
                if "varName" in c:
                    d[c["varName"]] = c.get("value")
        d["enabled"] = template.get("enabled", True)
        return d

    def getModSettings(self, linkage, template=None):
        cur = (self.state.get("settings") or {}).get(linkage)
        if cur is None:
            return None
        if template is not None and template.get("settingsVersion", 0) > self._stored_version:
            # Version bump not yet applied -> host reports None (values about to be wiped).
            return None
        return cur

    def setModTemplate(self, linkage, template, callback):
        self.template_cb = callback
        defaults = self._defaults_from_template(template)
        prev = (self.state.get("settings") or {}).get(linkage) or {}
        if "enabled" in prev:                      # host toggle survives a template reset
            defaults["enabled"] = prev["enabled"]
        self.state.setdefault("settings", {})[linkage] = defaults
        self._stored_version = template.get("settingsVersion", 0)
        return defaults

    def registerCallback(self, linkage, callback):
        self.registered_cb = callback

    def updateModSettings(self, linkage, data):
        self.updated += 1
        self.state.setdefault("settings", {})[linkage] = dict(data)

    def saveState(self):
        self.saved += 1


@pytest.fixture(autouse=True)
def _restore_module_state():
    """Restore mod_settings' shared globals + the injected fake modules AFTER each test, so
    a migration run's dirty _settings / _registered can't leak into the rest of the suite.
    Runs post-assertion, so the test body reads the live post-init _settings."""
    yield
    M._registered = False
    M._settings = dict(M.DEFAULTS)
    M._reset_hooked = set()
    sys.modules.pop("gui.aslainMenu", None)
    gui = sys.modules.get("gui")
    if gui is not None and hasattr(gui, "aslainMenu"):
        del gui.aslainMenu


def _run_init_with(api):
    """Reset mod_settings' module state, wire a faked gui.aslainMenu exposing `api`, and run
    init() against it. Returns after init; the caller inspects `api` + M._settings (the
    autouse fixture restores the module afterwards)."""
    # Fresh module state so shared globals don't leak into this run.
    M._registered = False
    M._settings = dict(M.DEFAULTS)
    M._reset_hooked = set()
    # Inject a fake gui.aslainMenu so _primary_api() resolves to our fake.
    gui = sys.modules.setdefault("gui", types.ModuleType("gui"))
    aslain = types.ModuleType("gui.aslainMenu")
    aslain.g_modsSettingsApi = api
    gui.aslainMenu = aslain
    sys.modules["gui.aslainMenu"] = aslain
    # Make sure a stray izeberg module never shadows the primary.
    sys.modules.pop("gui.modsSettingsApi", None)
    M.init()


# --- migration (settingsVersion bump) ---------------------------------------

def test_migration_preserves_user_values_drops_removed_key_and_seeds_new_default():
    # A stored dict at an OLD settingsVersion with non-default user values, one legacy key
    # that no longer exists in the template, and NO 'progressMode' (a key that only exists
    # in the newer template) -- so migration must keep the survivors, drop the legacy key,
    # and leave progressMode at its fresh default.
    old = {
        "enabled": True,
        "showBar": True,
        "showWhenComplete": True,
        "scale": 1,
        "ignoreFreeXp": True,
        "showPercent": True,
        "posX": 640, "posY": 190, "posW": 1920, "posH": 1080,
        "showTechTree": False,          # a per-mode toggle the user turned off
        "legacyGoneVarName": 7,         # a key removed from DEFAULTS -> must be dropped
    }
    api = _FakeMsaApi(stored=old, stored_version=8)   # older than the template's version
    _run_init_with(api)

    # Surviving user values restored + clamped.
    assert M.scale() == 1
    assert M.ignore_free_xp() is True
    assert M.show_percent() is True
    assert M.pos_x() == 640 and M.pos_y() == 190
    assert M._settings["showTechTree"] is False
    # A key only in the NEW template (not in the old dict) takes its fresh default.
    assert M.progress_mode() == M.DEFAULTS["progressMode"]
    # The removed legacy key is gone (never leaks into our cache).
    assert "legacyGoneVarName" not in M._settings
    # Persisted exactly once (the reset + overlay coalesce into one debounced write).
    assert api.updated == 1
    assert api.saved == 1
    # The written dict carries the migrated survivors + the host 'enabled' key.
    written = api.state["settings"][M.LINKAGE]
    assert written["scale"] == 1
    assert written["ignoreFreeXp"] is True
    assert written["posX"] == 640
    assert "enabled" in written and written["enabled"] is True
    assert "legacyGoneVarName" not in written


def test_migration_preserves_host_enabled_false():
    # If the user disabled the mod via Aslain's host 'enabled' toggle, migration must not
    # silently re-enable it -- the host key survives the template reset and the re-write.
    old = {"enabled": False, "showBar": True, "scale": 1}
    api = _FakeMsaApi(stored=old, stored_version=8)
    _run_init_with(api)
    assert api.state["settings"][M.LINKAGE]["enabled"] is False


# --- fresh install ----------------------------------------------------------

def test_fresh_install_yields_defaults_without_spurious_persist():
    # No stored settings at all (state has no linkage entry) -> old_raw is empty, so the
    # migration overlay is skipped entirely: defaults everywhere, and NO updateModSettings /
    # saveState (nothing to migrate).
    api = _FakeMsaApi(stored=None, stored_version=0)
    _run_init_with(api)
    assert M.scale() == M.DEFAULTS["scale"]
    assert M.ignore_free_xp() is M.DEFAULTS["ignoreFreeXp"]
    assert M.pos_x() == 0 and M.pos_y() == 0
    assert api.updated == 0
    assert api.saved == 0
    # The template was registered (fresh install path), and its callback wired.
    assert api.template_cb is M._on_changed


# --- same-version path (unchanged) ------------------------------------------

def test_same_version_path_applies_stored_and_does_not_migrate():
    # getModSettings returns the stored dict (version matches) -> the saved-truthy branch
    # runs: _apply(saved) + registerCallback, and the migration/setModTemplate else-branch
    # is never entered (no template reset, no migration write).
    stored = {"enabled": True, "showBar": True, "scale": 1, "ignoreFreeXp": True,
              "posX": 700, "posY": 300}
    api = _FakeMsaApi(stored=stored, stored_version=M._template()["settingsVersion"])
    _run_init_with(api)
    assert M.scale() == 1
    assert M.ignore_free_xp() is True
    assert M.pos_x() == 700 and M.pos_y() == 300
    # Same-version path registers the live callback and performs no migration write
    # (the stored dict already has 'enabled', so no repair write either).
    assert api.registered_cb is M._on_changed
    assert api.template_cb is None
    assert api.updated == 0
    assert api.saved == 0
