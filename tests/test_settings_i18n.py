# -*- coding: utf-8 -*-
"""Unit tests for the settings-panel LABEL resolver (engine-free).

Scope under test: only the panel LABELS are localized (WG feature names + mod-invented
label tables); tooltips are fixed English. settings_i18n imports cleanly under pytest
because _compat guards debug_utils and i18n.widget_labels() fails soft to English."""
import sys
import types

from wgmod_research.adapter import settings_i18n as S
from wgmod_research.adapter import i18n

_MOD_KEYS = set(S._LABELS[u"en"].keys())          # hand-translated labels
_FEATURE_KEYS = set(S.FEATURE_WG.keys())          # WG-labelled per-mode checkboxes
_ALL_KEYS = set(S.COL1_KEYS) | set(S.COL2_KEYS)
_SHIPPED = [c for c in S._LABELS if c != u"en"]

_FAKE_WL = {
    u"headerResearch": u"WG-Research",
    u"headerSkillTree": u"WG-Upgrades",
    u"headerFieldMods": u"WG-FieldMods",
    u"headerEliteRewards": u"WG-EliteRewards",
    u"headerElite": u"WG-EliteSystem",
    u"capTierXI": u"WG-TierXI",
}


# --- key coverage -----------------------------------------------------------

def test_keys_partition_all_controls():
    assert _MOD_KEYS | _FEATURE_KEYS == _ALL_KEYS
    assert _MOD_KEYS & _FEATURE_KEYS == set()
    # Every control has a fixed English tooltip.
    assert set(S._TOOLTIPS_EN.keys()) == _ALL_KEYS


def test_every_shipped_language_covers_all_mod_labels():
    for code in _SHIPPED:
        assert set(S._LABELS[code].keys()) == _MOD_KEYS, (
            u"lang %s missing labels: %s" % (code, _MOD_KEYS - set(S._LABELS[code])))


# --- feature labels come from WG --------------------------------------------

def test_feature_labels_come_from_wg():
    r = S.render_panel(_FAKE_WL, lang=u"en")
    assert r[u"showFieldMods"][u"text"] == u"WG-FieldMods"
    assert r[u"showElite"][u"text"] == u"WG-EliteSystem"
    assert r[u"showTechTree"][u"text"] == u"WG-Research"


def test_feature_label_english_fallback_when_wg_missing():
    r = S.render_panel({}, lang=u"uk")   # widget_labels gave nothing
    assert r[u"showFieldMods"][u"text"] == u"Field Modifications"
    assert r[u"showElite"][u"text"] == u"Elite System"


# --- mod-invented labels are localized --------------------------------------

def test_mod_invented_labels_localized():
    en = S.render_panel(_FAKE_WL, lang=u"en")
    uk = S.render_panel(_FAKE_WL, lang=u"uk")
    assert en[u"showBar"][u"text"] == u"Show Progress Bar"
    assert uk[u"showBar"][u"text"] == u"Показувати смугу прогресу"
    assert uk[u"showWhenComplete"][u"text"] == u"Повністю пройдено"


def test_unknown_language_labels_are_english():
    xx = S.render_panel(_FAKE_WL, lang=u"xx")
    en = S.render_panel(_FAKE_WL, lang=u"en")
    assert xx == en


# --- scale dropdown option labels -------------------------------------------

def test_scale_options_localized_with_english_fallback():
    en = S.render_panel(_FAKE_WL, lang=u"en")
    assert en[u"scale"][u"options"] == [u"Default", u"Large"]
    de = S.render_panel(_FAKE_WL, lang=u"de")
    assert de[u"scale"][u"options"] == [u"Standard", u"Groß"]
    xx = S.render_panel(_FAKE_WL, lang=u"xx")   # unknown code -> English options
    assert xx[u"scale"][u"options"] == [u"Default", u"Large"]


def test_scale_options_cover_every_shipped_language():
    # The option table ships the same languages as the label table.
    assert set(S._SCALE_OPTIONS.keys()) == set(S._LABELS.keys())
    for code, opts in S._SCALE_OPTIONS.items():
        assert len(opts) == 2, u"lang %s must have exactly 2 scale options" % code


# --- tooltips are FIXED ENGLISH, never translated ---------------------------

def test_tooltips_are_english_in_every_language():
    en = S.render_panel(_FAKE_WL, lang=u"en")
    for code in _SHIPPED:
        r = S.render_panel(_FAKE_WL, lang=code)
        for key in _ALL_KEYS:
            assert r[key][u"tooltip"] == en[key][u"tooltip"], (
                u"tooltip for %s differs in %s -- must stay English" % (key, code))


def test_tooltip_markup_shape():
    r = S.render_panel(_FAKE_WL, lang=u"de")
    tip = r[u"showWhenComplete"][u"tooltip"]
    assert tip == (u"{HEADER}Fully Progressed{/HEADER}"
                   u"{BODY}Keeps the bar visible on vehicles with nothing left to "
                   u"research, upgrade, or unlock. Uncheck to hide the bar once a "
                   u"vehicle is fully progressed.{/BODY}")


# --- _norm ------------------------------------------------------------------

def test_norm_cases():
    assert S._norm(u"en") == u"en"
    assert S._norm(u"EN") == u"en"
    assert S._norm(u"en-US") == u"en"
    assert S._norm(u"pt_BR") == u"pt"
    assert S._norm(u"ua") == u"uk"
    assert S._norm(u"UA") == u"uk"
    assert S._norm(None) == u""
    assert S._norm(u"") == u""


# --- marking ----------------------------------------------------------------

def test_marks_only_mod_invented_label_fallbacks(monkeypatch):
    monkeypatch.setattr(i18n, u"MARK_UNTRANSLATED", True)
    monkeypatch.setitem(S._LABELS, u"zz", {u"showBar": u"ZZ"})   # partial language
    r = S.render_panel(_FAKE_WL, lang=u"zz")
    assert not r[u"showBar"][u"text"].startswith(u"_")       # translated label
    assert r[u"barPosition"][u"text"].startswith(u"_")       # fell back -> marked
    # Feature labels aren't re-marked here (i18n owns them); tooltips never marked.
    assert r[u"showFieldMods"][u"text"] == u"WG-FieldMods"
    assert not r[u"barPosition"][u"tooltip"].startswith(u"_")


def test_english_client_never_marks(monkeypatch):
    monkeypatch.setattr(i18n, u"MARK_UNTRANSLATED", True)
    r = S.render_panel(_FAKE_WL, lang=u"en")
    for entry in r.values():
        assert not entry[u"text"].startswith(u"_")


# --- client_language guard + panel_text -------------------------------------

def test_client_language_reads_helpers(monkeypatch):
    fake = types.ModuleType(u"helpers")
    fake.getClientLanguage = lambda: u"de"
    monkeypatch.setitem(sys.modules, u"helpers", fake)
    assert S.client_language() == u"de"


def test_client_language_normalizes_ua_alias(monkeypatch):
    fake = types.ModuleType(u"helpers")
    fake.getClientLanguage = lambda: u"ua"
    monkeypatch.setitem(sys.modules, u"helpers", fake)
    assert S.client_language() == u"uk"


def test_client_language_falls_back_on_error(monkeypatch):
    fake = types.ModuleType(u"helpers")

    def _boom():
        raise RuntimeError(u"no client")

    fake.getClientLanguage = _boom
    monkeypatch.setitem(sys.modules, u"helpers", fake)
    assert S.client_language() == u"en"


def test_panel_text_labels_and_english_tooltips(monkeypatch):
    monkeypatch.delitem(sys.modules, u"helpers", raising=False)   # -> en, WG English
    t = S.panel_text()
    assert t[u"showBar"][u"text"] == u"Show Progress Bar"
    assert t[u"showFieldMods"][u"text"] == u"Field Modifications"
    assert t[u"showFieldMods"][u"tooltip"].startswith(u"{HEADER}Field Modifications{/HEADER}")
