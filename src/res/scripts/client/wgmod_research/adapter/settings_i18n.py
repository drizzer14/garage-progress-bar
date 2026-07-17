# -*- coding: utf-8 -*-
"""Localize the settings-panel LABELS (see ``bridge/mod_settings.py``).

Scope, deliberately narrow:

* **Only the settings panel is localized** — nothing else. The widget already follows
  the client language by reusing WG's own resource strings (``adapter/i18n.py``).
* **Only the LABELS are localized**, two ways:
  1. **WG feature names** (Research, Upgrades, Field Modifications, Elite System, Elite
     Rewards, Tier XI) — the per-mode checkbox labels reuse WG's own localized strings via
     ``i18n.widget_labels()`` (``FEATURE_WG`` maps each checkbox → its widget-labels key),
     so they match the game exactly in every language and never drift.
  2. **Mod-invented labels** (the ``showBar`` master toggle, the ``showWhenComplete`` and
     ``ignoreFreeXp`` toggles, the "Bar position" section Label, the two position steppers) —
     bundled ``{lang: {key: label}}`` tables here, English master + per-key fallback.
* **Tooltips are NOT localized.** Every control's tooltip (header + body) is fixed English
  (``_TOOLTIPS_EN``) — it's explanatory help, not a setting, and has no WG string to reuse.
  It is never translated and never routed through i18n.

Everything is PURE except ``client_language()`` (the one guarded
``helpers.getClientLanguage()`` read) and ``panel_text()`` (which pulls the WG labels from
``i18n``). ``render_panel(wg_labels, lang)`` is pure given its args, so it unit-tests with
a fake label dict and the game closed. Ships ``cs de en es fr hu it pl ru tr uk``; unknown
client codes degrade to English (marked when ``i18n.MARK_UNTRANSLATED`` is on).
"""
from wgmod_research._compat import LOG_CURRENT_EXCEPTION
from wgmod_research.adapter import i18n

# The default client language + the value returned when the engine read fails.
DEFAULT_LANGUAGE = u"en"

# getClientLanguage() code quirks -> our table keys. Seeded with the Ukrainian case;
# extend after verifying live codes (Chinese/Portuguese variants, region suffixes).
_ALIASES = {
    u"ua": u"uk",
}

# Per-mode checkbox -> the i18n.widget_labels() key whose WG-localized text is the label.
FEATURE_WG = {
    u"showTechTree": u"headerResearch",         # "Research"
    u"showSkillTree": u"headerSkillTree",        # "Upgrades"
    u"showFieldMods": u"headerFieldMods",        # "Field Modifications"
    u"showEliteRewards": u"headerEliteRewards",   # "Elite Rewards"
    u"showElite": u"headerElite",           # "Elite System"
    u"showPotentialTierXI": u"capTierXI",             # "Tier XI"
}

# English fallback for a feature label, used only if widget_labels() lacks the key.
_FEATURE_EN = {
    u"showTechTree": u"Research",
    u"showSkillTree": u"Upgrades",
    u"showFieldMods": u"Field Modifications",
    u"showEliteRewards": u"Elite Rewards",
    u"showElite": u"Elite System",
    u"showPotentialTierXI": u"Tier XI",
}

# Ordered key lists per column -- the wire order of the controls in ``_template()``. Used
# by mod_settings to walk a stored template in lockstep (Labels carry no varName).
# showBar is the MASTER checkbox; the six per-mode toggles and showWhenComplete are its
# greyed-when-off children, then ignoreFreeXp is a STANDALONE control last in column1 (not
# bound to the master -- see mod_settings._template()). The order here MUST match the wire
# order of the controls in _template() column1 (Aslain's master-group returns a flat
# [master, ...children] list -- no Label rows any more).
COL1_KEYS = (u"showBar", u"showTechTree", u"showFieldMods", u"showPotentialTierXI",
             u"showSkillTree", u"showEliteRewards", u"showElite", u"showWhenComplete",
             u"ignoreFreeXp")
COL2_KEYS = (u"barPosition", u"posX", u"posY")


def _norm(code):
    """Normalize a client language code to a table key (pure, engine-free).

    ``None``/empty -> u"". Otherwise lowercase, ``-`` -> ``_``, apply ``_ALIASES``, and if
    the full code isn't a known block fall back to the primary subtag (``"pt_br"`` ->
    ``"pt"``). Not guaranteed to be a ``_LABELS`` key -- the resolver treats an unknown key
    as "English"."""
    if not code:
        return u""
    c = code.strip().lower().replace(u"-", u"_")
    c = _ALIASES.get(c, c)
    if c in _LABELS:
        return c
    base = c.split(u"_", 1)[0]
    base = _ALIASES.get(base, base)
    return base


# --- MOD-INVENTED LABELS (hand-translated) --------------------------------------------
# Only labels -- these controls' tooltips are the fixed English in _TOOLTIPS_EN. The six
# per-mode checkboxes are NOT here (their labels come from WG via FEATURE_WG).
_LABELS = {
    u"en": {
        u"showBar": u"Show Progress Bar",
        u"showWhenComplete": u"Fully Progressed",
        u"ignoreFreeXp": u"Ignore Free XP",
        u"barPosition": u"Bar position (px)",
        u"posX": u"Horizontal (center X)",
        u"posY": u"Vertical (top Y)",
    },
    u"de": {
        u"showBar": u"Fortschrittsleiste anzeigen",
        u"showWhenComplete": u"Vollständig fortgeschritten",
        u"ignoreFreeXp": u"Freie Erfahrung ignorieren",
        u"barPosition": u"Leistenposition (px)",
        u"posX": u"Horizontal (Mitte X)",
        u"posY": u"Vertikal (oben Y)",
    },
    u"fr": {
        u"showBar": u"Afficher la barre de progression",
        u"showWhenComplete": u"Entièrement progressé",
        u"ignoreFreeXp": u"Ignorer l'expérience libre",
        u"barPosition": u"Position de la barre (px)",
        u"posX": u"Horizontale (centre X)",
        u"posY": u"Verticale (haut Y)",
    },
    u"es": {
        u"showBar": u"Mostrar la barra de progreso",
        u"showWhenComplete": u"Progreso completo",
        u"ignoreFreeXp": u"Ignorar la experiencia libre",
        u"barPosition": u"Posición de la barra (px)",
        u"posX": u"Horizontal (centro X)",
        u"posY": u"Vertical (arriba Y)",
    },
    u"it": {
        u"showBar": u"Mostra la barra di avanzamento",
        u"showWhenComplete": u"Completamente progredito",
        u"ignoreFreeXp": u"Ignora l'esperienza libera",
        u"barPosition": u"Posizione della barra (px)",
        u"posX": u"Orizzontale (centro X)",
        u"posY": u"Verticale (alto Y)",
    },
    u"pl": {
        u"showBar": u"Pokaż pasek postępu",
        u"showWhenComplete": u"W pełni ukończone",
        u"ignoreFreeXp": u"Ignoruj wolne doświadczenie",
        u"barPosition": u"Pozycja paska (px)",
        u"posX": u"Poziomo (środek X)",
        u"posY": u"Pionowo (góra Y)",
    },
    u"cs": {
        u"showBar": u"Zobrazit lištu postupu",
        u"showWhenComplete": u"Plně dokončeno",
        u"ignoreFreeXp": u"Ignorovat volné zkušenosti",
        u"barPosition": u"Pozice lišty (px)",
        u"posX": u"Vodorovně (střed X)",
        u"posY": u"Svisle (nahoře Y)",
    },
    u"ru": {
        u"showBar": u"Показывать полосу прогресса",
        u"showWhenComplete": u"Полностью пройдено",
        u"ignoreFreeXp": u"Игнорировать свободный опыт",
        u"barPosition": u"Положение полосы (px)",
        u"posX": u"По горизонтали (центр X)",
        u"posY": u"По вертикали (верх Y)",
    },
    u"uk": {
        u"showBar": u"Показувати смугу прогресу",
        u"showWhenComplete": u"Повністю пройдено",
        u"ignoreFreeXp": u"Ігнорувати вільний досвід",
        u"barPosition": u"Розташування смуги (px)",
        u"posX": u"По горизонталі (центр X)",
        u"posY": u"По вертикалі (верх Y)",
    },
    u"hu": {
        u"showBar": u"Folyamatjelző sáv megjelenítése",
        u"showWhenComplete": u"Teljesen kész",
        u"ignoreFreeXp": u"Szabad tapasztalat mellőzése",
        u"barPosition": u"A sáv helyzete (px)",
        u"posX": u"Vízszintes (középpont X)",
        u"posY": u"Függőleges (felső Y)",
    },
    u"tr": {
        u"showBar": u"İlerleme çubuğunu göster",
        u"showWhenComplete": u"Tamamen ilerlemiş",
        u"ignoreFreeXp": u"Serbest deneyimi yok say",
        u"barPosition": u"Çubuk konumu (px)",
        u"posX": u"Yatay (merkez X)",
        u"posY": u"Dikey (üst Y)",
    },
}


# --- TOOLTIPS: fixed English for EVERY control (never translated, never i18n) ----------
# (header, body). The header mirrors the control's English name; the body is the mod's
# own explanatory prose. Deliberately English on every client -- see the module docstring.
_TOOLTIPS_EN = {
    u"showBar": (u"Show Progress Bar",
                 u"Master switch: shows the progress bar on the selected vehicle. Uncheck "
                 u"to hide the bar completely on every vehicle. The options below turn its "
                 u"individual modes on or off, and grey out while it's unchecked."),
    u"showWhenComplete": (u"Fully Progressed",
                          u"Keeps the bar visible on vehicles with nothing left to "
                          u"research, upgrade, or unlock. Uncheck to hide the bar once a "
                          u"vehicle is fully progressed."),
    u"ignoreFreeXp": (u"Ignore Free XP",
                      u"Counts only the combat XP you earn on each vehicle toward its "
                      u"progress. Free XP is excluded from the bar, the totals, and the "
                      u"tooltips. Off by default."),
    u"showTechTree": (u"Research",
                      u"The tech-tree progress toward the vehicle's remaining module "
                      u"and next-vehicle unlocks."),
    u"showSkillTree": (u"Upgrades",
                       u"The branching upgrade (skill) tree on Tier XI vehicles."),
    u"showFieldMods": (u"Field Modifications",
                       u"The field-modification steps unlocked once the vehicle is "
                       u"fully researched."),
    u"showEliteRewards": (u"Elite Rewards",
                          u"The tier-exclusive milestone-reward roadmap on prestige "
                          u"vehicles."),
    u"showElite": (u"Elite System",
                   u"The Elite-Levels grade-band progression on prestige vehicles."),
    u"showPotentialTierXI": (u"Tier XI",
                             u"On a Tier X tank that has no Tier XI, once it's fully "
                             u"researched and its field mods are done, track your "
                             u"banked XP (vehicle XP + Free XP) toward the fixed price "
                             u"a Tier XI costs to unlock. Replaces the Elite-Levels bar "
                             u"on those tanks. Off by default."),
    u"barPosition": (u"Bar position",
                     u"Ctrl+drag the bar in the garage to move it, or type exact "
                     u"on-screen pixel coordinates below. Reset returns it to the "
                     u"default position."),
    u"posX": (u"Horizontal position",
              u"The bar's CENTER, in pixels from the left screen edge."),
    u"posY": (u"Vertical position",
              u"The bar's TOP, in pixels from the top screen edge."),
}


def render_panel(wg_labels, lang=None):
    """The full rendered panel text: ``{key: {"text", "tooltip"}}`` for every control
    (PURE given ``wg_labels`` + ``lang``).

    ``text`` (the LABEL) is localized: per-mode checkboxes take WG's own localized name
    from ``wg_labels`` (== ``i18n.widget_labels()``), everything else from the ``_LABELS``
    tables (English-fallback, marked on fallback). ``tooltip`` is the fixed English from
    ``_TOOLTIPS_EN`` -- never translated. ``lang`` defaults to the client's language."""
    if lang is None:
        lang = client_language()
    code = _norm(lang)
    labels = _LABELS.get(code) or {}
    en_labels = _LABELS[DEFAULT_LANGUAGE]
    wl = wg_labels or {}
    out = {}
    for key in COL1_KEYS + COL2_KEYS:
        if key in FEATURE_WG:
            text = wl.get(FEATURE_WG[key]) or _FEATURE_EN[key]   # WG label; i18n self-marks
        else:
            fb = key not in labels
            text = en_labels[key] if fb else labels[key]
            if fb:
                text = i18n._mark(text)
        header, body = _TOOLTIPS_EN[key]
        out[key] = {u"text": text,
                    u"tooltip": u"{HEADER}%s{/HEADER}{BODY}%s{/BODY}" % (header, body)}
    return out


def client_language():
    """The client's active language code, normalized to a table key -- the ONE engine
    read here. Guarded + lazy-imported so the module still imports under pytest and a
    missing/renamed helper degrades to English rather than raising into MSA setup."""
    try:
        import helpers
        return _norm(helpers.getClientLanguage()) or DEFAULT_LANGUAGE
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return DEFAULT_LANGUAGE


def panel_text(lang=None):
    """The rendered panel text for the client's active language (public entry for
    mod_settings). Pulls WG's localized feature names from ``i18n.widget_labels()``."""
    return render_panel(i18n.widget_labels(), lang)
