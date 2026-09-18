# -*- coding: utf-8 -*-
"""Unit tests for the settings-panel text resolver (engine-free).

Scope under test: the panel LABELS (WG feature names + mod-invented label tables), the
radio OPTION labels, and the TOOLTIPS -- all three localized into the same 11 codes with
English as the per-key fallback. settings_i18n imports cleanly under pytest because
_compat guards debug_utils and i18n.widget_labels() fails soft to English."""
import sys
import types

from wgmod_research.adapter import settings_i18n as S
from wgmod_research.adapter import i18n

_MOD_KEYS = set(S._LABELS[u"en"].keys())          # hand-translated labels
_FEATURE_KEYS = set(S.FEATURE_WG.keys())          # WG-labelled per-mode checkboxes
# The SPACER sentinel names no control -- render_panel skips it, so it is not a key.
_ALL_KEYS = (set(S.COL1_KEYS) | set(S.COL2_KEYS)) - {S.SPACER}
_HEADER_KEYS = set(S.HEADER_KEYS)   # inert captions -- bold, no tooltip
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
    # Every control has a tooltip EXCEPT the three inert category headers.
    assert set(S._TOOLTIPS[u"en"].keys()) == _ALL_KEYS - _HEADER_KEYS


def test_category_headers_render_without_a_tooltip():
    # Section captions, not settings -- they get a localized label and no tooltip key at
    # all (rather than invented filler prose). _sync_template_text skips a missing one.
    for code in (u"en", u"de", u"uk"):
        r = S.render_panel(_FAKE_WL, lang=code)
        for key in _HEADER_KEYS:
            assert r[key][u"text"]
            assert u"tooltip" not in r[key]


def test_category_headers_render_bold():
    # MSA Labels render HTML, so the three category captions come out bold. The wrap is
    # applied HERE (render_panel), never in the _LABELS tables -- translation data stays
    # markup-free -- and never in mod_settings._template().
    en = S.render_panel(_FAKE_WL, lang=u"en")
    assert en[u"modes"][u"text"] == u"<b>Modes</b>"
    assert en[u"formatting"][u"text"] == u"<b>Formatting</b>"
    assert en[u"layout"][u"text"] == u"<b>Layout</b>"
    # The translation tables themselves stay plain.
    for code in S._LABELS:
        for key in _HEADER_KEYS:
            assert u"<b>" not in S._LABELS[code][key]


def test_only_category_headers_are_bold():
    # The "position" sub-header sits a level below the categories -- bolding it too would
    # flatten the hierarchy. No varName-bearing label is bold either.
    en = S.render_panel(_FAKE_WL, lang=u"en")
    for key, entry in en.items():
        want_bold = key in _HEADER_KEYS
        assert entry[u"text"].startswith(u"<b>") is want_bold, key
    assert en[u"position"][u"text"] == u"Position (px)"


def test_bold_survives_a_language_switch():
    # The wrapper goes around the TRANSLATED word, not a hardcoded English one.
    de = S.render_panel(_FAKE_WL, lang=u"de")
    assert de[u"formatting"][u"text"] == u"<b>Formatierung</b>"
    uk = S.render_panel(_FAKE_WL, lang=u"uk")
    assert uk[u"modes"][u"text"] == u"<b>Режими</b>"


def test_uk_layout_and_position_captions_differ():
    # Both would naturally translate to "Розташування"; the sub-header takes "Позиція" so
    # the two stacked captions don't read as a duplicated row.
    uk = S.render_panel(_FAKE_WL, lang=u"uk")
    assert uk[u"layout"][u"text"] == u"<b>Розташування</b>"
    assert uk[u"position"][u"text"] == u"Позиція (px)"


def test_every_shipped_language_covers_all_mod_labels():
    # EN_ONLY_KEYS are deliberately English-until-scheduled-translation, so a non-en block
    # is allowed to omit them (render_panel falls back to the English master per key).
    required = _MOD_KEYS - set(S.EN_ONLY_KEYS)
    for code in _SHIPPED:
        assert required <= set(S._LABELS[code].keys()), (
            u"lang %s missing labels: %s" % (code, required - set(S._LABELS[code])))
        # and it must not carry a key outside the English master's full set.
        assert set(S._LABELS[code].keys()) <= _MOD_KEYS


def test_en_only_keys_are_english_master_only():
    # The pending-translation keys live in the en master (so the fallback has a source) and
    # are absent from every shipped non-en block until translations are scheduled.
    for key in S.EN_ONLY_KEYS:
        assert key in S._LABELS[u"en"]
        for code in _SHIPPED:
            assert key not in S._LABELS[code]


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
    assert en[u"ignoreFreeXp"][u"text"] == u"Ignore Free XP"
    assert uk[u"ignoreFreeXp"][u"text"] == u"Ігнорувати вільний досвід"
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


# --- progressMode dropdown option labels ------------------------------------

def test_progress_mode_options_localized_with_english_fallback():
    en = S.render_panel(_FAKE_WL, lang=u"en")
    assert en[u"progressMode"][u"options"] == [u"Current", u"Current / Required"]
    de = S.render_panel(_FAKE_WL, lang=u"de")
    assert de[u"progressMode"][u"options"] == [u"Aktuell", u"Aktuell / Benötigt"]
    xx = S.render_panel(_FAKE_WL, lang=u"xx")   # unknown code -> English options
    assert xx[u"progressMode"][u"options"] == [u"Current", u"Current / Required"]


def test_progress_mode_options_cover_every_shipped_language():
    # The option table ships the same languages as the label table.
    assert set(S._PROGRESS_OPTIONS.keys()) == set(S._LABELS.keys())
    for code, opts in S._PROGRESS_OPTIONS.items():
        assert len(opts) == 2, u"lang %s must have exactly 2 progressMode options" % code


def test_show_percent_and_progress_mode_have_labels_and_tooltips():
    # Both new controls must carry a label + tooltip in every language.
    for code in (u"en", u"de", u"uk"):
        r = S.render_panel(_FAKE_WL, lang=code)
        for key in (u"showPercent", u"progressMode"):
            assert r[key][u"text"]
            assert r[key][u"tooltip"].startswith(u"{HEADER}")


# --- tooltips are LOCALIZED (same 11 codes as the labels) -------------------

def test_every_shipped_language_covers_all_tooltips():
    # THE dropped-key guard: each of the 11 blocks must carry all 15 tooltip keys, each
    # with a non-empty header AND body. A missing key would silently render English.
    en_keys = set(S._TOOLTIPS[u"en"].keys())
    # EN_ONLY_KEYS are English-until-scheduled-translation, so the non-en blocks may omit
    # their tooltips (render_panel falls back per key). The en master still carries them.
    required = en_keys - set(S.EN_ONLY_KEYS)
    assert set(S._TOOLTIPS.keys()) == set(S._LABELS.keys())      # same shipped languages
    for code, block in S._TOOLTIPS.items():
        want = en_keys if code == u"en" else required
        assert set(block.keys()) == want, (
            u"lang %s tooltip keys differ: missing %s / extra %s"
            % (code, want - set(block), set(block) - want))
        for key, entry in block.items():
            assert len(entry) == 2, u"%s/%s must be a (header, body) pair" % (code, key)
            header, body = entry
            assert header and header.strip(), u"%s/%s has an empty header" % (code, key)
            assert body and body.strip(), u"%s/%s has an empty body" % (code, key)


def test_tooltips_are_localized_not_english():
    en = S.render_panel(_FAKE_WL, lang=u"en")
    # EN_ONLY_KEYS are intentionally English in every language (translations pending), so
    # they legitimately match the English string -- exclude them from the "not English" guard.
    checked = _ALL_KEYS - _HEADER_KEYS - set(S.EN_ONLY_KEYS)
    for code in _SHIPPED:
        r = S.render_panel(_FAKE_WL, lang=code)
        for key in checked:
            assert r[key][u"tooltip"] != en[key][u"tooltip"], (
                u"tooltip for %s is still the English string in %s" % (key, code))


def test_tooltip_bodies_keep_the_english_tokens():
    # Placeholders / markup-ish tokens must ride across untranslated: the scale body's
    # em-dash substitute " - " (the client renders a real em-dash as "--"), the "/" in the
    # progressMode option name, the "%" in showPercent's header, and the "+" in the
    # Tier XI banked-XP sum.
    for code in S._TOOLTIPS:
        tips = S._TOOLTIPS[code]
        assert u" - " in tips[u"scale"][1], code
        assert u" / " in tips[u"progressMode"][1], code
        assert u"%" in tips[u"showPercent"][0], code
        assert u" + " in tips[u"showPotentialTierXI"][1], code


def test_tooltip_markup_shape():
    # Assembled ONCE in render_panel, so no translation string carries the markup.
    for code in S._TOOLTIPS:
        assert not any(u"{HEADER}" in s for e in S._TOOLTIPS[code].values() for s in e)
    r = S.render_panel(_FAKE_WL, lang=u"en")
    tip = r[u"showWhenComplete"][u"tooltip"]
    assert tip == (u"{HEADER}Fully Progressed{/HEADER}"
                   u"{BODY}Keeps the bar visible on vehicles with nothing left to "
                   u"research, upgrade, or unlock. Uncheck to hide the bar once a "
                   u"vehicle is fully progressed.{/BODY}")
    de = S.render_panel(_FAKE_WL, lang=u"de")[u"posX"][u"tooltip"]
    assert de == (u"{HEADER}Horizontale Position{/HEADER}"
                  u"{BODY}Die MITTE der Leiste, in Pixeln vom linken "
                  u"Bildschirmrand.{/BODY}")


def test_partial_language_falls_back_per_tooltip_key(monkeypatch):
    # A language that translated one tooltip keeps English for the other fourteen.
    monkeypatch.setitem(S._TOOLTIPS, u"zz", {u"posX": (u"ZZ-H", u"ZZ-B")})
    monkeypatch.setitem(S._LABELS, u"zz", dict(S._LABELS[u"en"]))
    r = S.render_panel(_FAKE_WL, lang=u"zz")
    assert r[u"posX"][u"tooltip"] == u"{HEADER}ZZ-H{/HEADER}{BODY}ZZ-B{/BODY}"
    assert r[u"posY"][u"tooltip"] == S.render_panel(_FAKE_WL, lang=u"en")[u"posY"][u"tooltip"]


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
    monkeypatch.setitem(S._LABELS, u"zz", {u"modes": u"ZZ"})   # partial language
    r = S.render_panel(_FAKE_WL, lang=u"zz")
    assert not r[u"modes"][u"text"].startswith(u"_")         # translated label
    assert r[u"position"][u"text"].startswith(u"_")       # fell back -> marked
    # Feature labels aren't re-marked here (i18n owns them); tooltips never marked.
    assert r[u"showFieldMods"][u"text"] == u"WG-FieldMods"
    assert not r[u"position"][u"tooltip"].startswith(u"_")


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


# --- label(): one mod-invented label, reused by the WIDGET ------------------
# i18n.headerComplete ("Fully Progressed") sources the COMPLETE bar's header from this
# table instead of duplicating the translations.

def test_label_english_master_is_unmarked(monkeypatch):
    monkeypatch.setattr(i18n, u"MARK_UNTRANSLATED", True)
    assert S.label(u"showWhenComplete", lang=u"en") == u"Fully Progressed"


def test_label_localized_per_language():
    assert S.label(u"showWhenComplete", lang=u"uk") == u"Повністю пройдено"
    assert S.label(u"showWhenComplete", lang=u"de") == u"Vollständig fortgeschritten"


def test_label_unknown_language_falls_back_to_marked_english(monkeypatch):
    monkeypatch.setattr(i18n, u"MARK_UNTRANSLATED", True)
    assert S.label(u"showWhenComplete", lang=u"xx") == u"_Fully Progressed"


def test_label_unknown_key_is_empty(monkeypatch):
    monkeypatch.setattr(i18n, u"MARK_UNTRANSLATED", True)
    assert S.label(u"noSuchKey", lang=u"en") == u""      # no mark on an empty string


def test_label_defaults_to_the_client_language(monkeypatch):
    # How the widget actually calls it (no lang arg) -> client language, en fallback.
    monkeypatch.delitem(sys.modules, u"helpers", raising=False)
    assert S.label(u"showWhenComplete") == u"Fully Progressed"


def test_panel_text_labels_and_english_tooltips(monkeypatch):
    monkeypatch.delitem(sys.modules, u"helpers", raising=False)   # -> en, WG English
    t = S.panel_text()
    assert t[u"modes"][u"text"] == u"<b>Modes</b>"
    assert t[u"showFieldMods"][u"text"] == u"Field Modifications"
    assert t[u"showFieldMods"][u"tooltip"].startswith(u"{HEADER}Field Modifications{/HEADER}")
