# -*- coding: utf-8 -*-
"""Structure tests for the MSA settings-panel template (``bridge/mod_settings.py``).

Locks the Aslain master/child structure: ``showBar`` is the master, the six per-mode
toggles + ``showWhenComplete`` are its children (each carrying ``masterVarName == "showBar"``,
in the exact spec order), and ``ignoreFreeXp`` is a STANDALONE checkbox last in column1 (NOT
bound to the master -- no ``masterVarName``). The old "Bar modes" Label is gone, and the
polarity/position defaults are unchanged.

mod_settings imports the game's ``debug_utils`` at module load, so stub it first (as
test_position does); ``_template()`` itself is a pure dict, engine-free once imported."""
import sys
import types

if "debug_utils" not in sys.modules:
    _dbg = types.ModuleType("debug_utils")
    _dbg.LOG_CURRENT_EXCEPTION = lambda *a, **k: None
    _dbg.LOG_NOTE = lambda *a, **k: None
    sys.modules["debug_utils"] = _dbg

from wgmod_research.bridge import mod_settings as M

# The seven children of the showBar master, in the exact spec order (ignoreFreeXp is NOT
# here -- it's a standalone control after the group, see the tests below).
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

def test_settings_version_is_6():
    assert M._template()["settingsVersion"] == 6


# --- master / children ------------------------------------------------------

def test_showbar_is_the_master():
    master = _col1()[0]
    assert master["varName"] == "showBar"
    assert master["type"] == "CheckBox"
    # The master itself is NOT a child of anything.
    assert "masterVarName" not in master
    assert master["value"] is True


def test_children_order_matches_spec():
    # The master group is master + 7 children; ignoreFreeXp is the standalone LAST entry,
    # so the children are col1[1:-1]. .get (not []) so a stray Label row -- which carries no
    # varName -- yields a clean order mismatch rather than a KeyError.
    assert [c.get("varName") for c in _col1()[1:-1]] == _CHILD_ORDER


def test_all_seven_children_are_bound_to_showbar():
    children = _col1()[1:-1]   # exclude master (0) and the standalone ignoreFreeXp (last)
    assert len(children) == 7
    for c in children:
        assert c["type"] == "CheckBox"
        assert c["masterVarName"] == "showBar", (
            "child %s not bound to showBar master" % c.get("varName"))


def test_ignore_free_xp_is_standalone_last_not_bound_to_master():
    # ignoreFreeXp changes WHICH XP counts, not whether the bar shows, so it is a plain
    # standalone checkbox at the end of column1 -- with NO masterVarName binding.
    last = _col1()[-1]
    assert last["varName"] == "ignoreFreeXp"
    assert last["type"] == "CheckBox"
    assert "masterVarName" not in last
    assert last["value"] is False


def test_column1_has_master_plus_seven_children_plus_standalone():
    # master (1) + 7 group children + 1 standalone (ignoreFreeXp) = 9 controls.
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
