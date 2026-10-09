# -*- coding: utf-8 -*-
"""Localize the settings-panel LABELS (see ``bridge/mod_settings.py``).

Scope, deliberately narrow:

* **Only the settings panel is localized** — nothing else. The widget already follows
  the client language by reusing WG's own resource strings (``adapter/i18n.py``).
* **The LABELS are localized** two ways:
  1. **WG feature names** (Research, Upgrades, Field Modifications, Elite System, Elite
     Rewards, Tier XI) — the per-mode checkbox labels reuse WG's own localized strings via
     ``i18n.widget_labels()`` (``FEATURE_WG`` maps each checkbox → its widget-labels key),
     so they match the game exactly in every language and never drift.
  2. **Mod-invented labels** (the three category-header Labels "Modes"/"Formatting"/
     "Layout", the ``showWhenComplete``/``allowFallthrough``/``ignoreFreeXp`` toggles,
     the "Position" section Label, the two position steppers) — bundled
     ``{lang: {key: label}}`` tables here, English master + per-key fallback.
* **Tooltips ARE localized too**, from the lang-major ``_TOOLTIPS`` table (same 11 codes as
  ``_LABELS``, English master + per-key English fallback). Each entry is a plain
  ``(header, body)`` tuple; ``render_panel`` assembles the ``{HEADER}/{BODY}`` markup once.
  The three category headers are the one exception to "every control has a tooltip": they
  are inert section captions, so they carry NO ``_TOOLTIPS`` entry and ``render_panel``
  simply omits the ``tooltip`` key for them (rather than inventing filler prose).

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

# Placeholder for a template row that carries NO text of its own -- the `Empty` spacer
# before the standalone allowFallthrough checkbox in column1, and the three in column2
# (between the Formatting and Layout groups, before the progressMode radio group, and
# before the "Position" sub-header). _sync_template_text zips these key
# tuples against the STORED components POSITIONALLY, so a textless row must still occupy a
# slot: without it every key after the spacer would shift by one and silently relabel the
# wrong controls. A module-level sentinel (not a bare None literal) so the intent reads at
# the call site. Both consumers skip it -- see render_panel below and
# mod_settings._sync_template_text (its ``t.get(key)`` yields None -> continue).
SPACER = None

# The three CATEGORY header Labels. Rendered BOLD (see render_panel) so they read as
# section captions above their controls; the "position" sub-header is deliberately NOT
# here -- it sits a level below the categories, and bolding it too would flatten the
# hierarchy the spacer and headers exist to create.
HEADER_KEYS = frozenset((u"modes", u"formatting", u"layout"))

EN_ONLY_KEYS = frozenset()

# Ordered key lists per column -- the wire order of the controls in ``_template()``. Used
# by mod_settings to walk a stored template in lockstep (Label/Empty rows carry no varName).
# The panel is three named CATEGORIES opened by Label headers ("modes" / "formatting" /
# "layout"), but only TWO columns: Layout is merged into column2 under a spacer, because a
# third column only renders side-by-side when the user's global MSA `multiColumnMode`
# toolbar toggle is ON (default OFF) -- with it off Aslain folds columns round-robin
# (i % columnCount) and column3 would stack UNDER column1 instead. The seven mode
# checkboxes are plain standalone controls (no master switch any more -- see
# mod_settings._template()). The order here MUST match the wire order in _template().
COL1_KEYS = (u"modes", u"showTechTree", u"showFieldMods", u"showPotentialTierXI",
             u"showSkillTree", u"showEliteRewards", u"showElite", u"showWhenComplete",
             SPACER, u"allowFallthrough")
COL2_KEYS = (u"formatting", u"ignoreFreeXp", u"showPercent", SPACER, u"progressMode",
             SPACER, u"layout", u"scale", SPACER, u"position", u"posX", u"posY",
             u"onslaughtPosX", u"onslaughtPosY")


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
# Only labels -- these controls' tooltips live in the parallel _TOOLTIPS table (the three
# category headers carry none at all). The six per-mode checkboxes are NOT here (their
# labels come from WG via FEATURE_WG). "modes"/"formatting"/"layout" are the three category
# header Labels, one per column; "position" is the sub-header above the two steppers.
_LABELS = {
    u"en": {
        u"modes": u"Modes",
        u"formatting": u"Formatting",
        u"layout": u"Layout",
        u"showWhenComplete": u"Fully Progressed",
        u"allowFallthrough": u"Allow Fallthrough",
        u"ignoreFreeXp": u"Ignore Free XP",
        u"showPercent": u"Show Progress %",
        u"progressMode": u"Progress Mode",
        u"scale": u"Scale",
        u"position": u"Position (px)",
        u"posX": u"Horizontal (center X)",
        u"posY": u"Vertical (top Y)",
        # Onslaught garage's own X/Y steppers.
        u"onslaughtPosX": u"Horizontal (Onslaught X)",
        u"onslaughtPosY": u"Vertical (Onslaught Y)",
    },
    u"de": {
        u"modes": u"Modi",
        u"formatting": u"Formatierung",
        u"layout": u"Layout",
        u"showWhenComplete": u"Vollständig fortgeschritten",
        u"allowFallthrough": u"Fallback zulassen",
        u"ignoreFreeXp": u"Freie Erfahrung ignorieren",
        u"showPercent": u"Fortschritt in % anzeigen",
        u"progressMode": u"Fortschrittsmodus",
        u"scale": u"Skalierung",
        u"position": u"Position (px)",
        u"posX": u"Horizontal (Mitte X)",
        u"posY": u"Vertikal (oben Y)",
        u"onslaughtPosX": u"Horizontal (Ansturm X)",
        u"onslaughtPosY": u"Vertikal (Ansturm Y)",
    },
    u"fr": {
        u"modes": u"Modes",
        u"formatting": u"Mise en forme",
        u"layout": u"Disposition",
        u"showWhenComplete": u"Entièrement progressé",
        u"allowFallthrough": u"Autoriser le repli",
        u"ignoreFreeXp": u"Ignorer l'expérience libre",
        u"showPercent": u"Afficher la progression en %",
        u"progressMode": u"Mode de progression",
        u"scale": u"Échelle",
        u"position": u"Position (px)",
        u"posX": u"Horizontale (centre X)",
        u"posY": u"Verticale (haut Y)",
        u"onslaughtPosX": u"Horizontale (Assaut X)",
        u"onslaughtPosY": u"Verticale (Assaut Y)",
    },
    u"es": {
        u"modes": u"Modos",
        u"formatting": u"Formato",
        u"layout": u"Diseño",
        u"showWhenComplete": u"Progreso completo",
        u"allowFallthrough": u"Permitir alternativa",
        u"ignoreFreeXp": u"Ignorar la experiencia libre",
        u"showPercent": u"Mostrar el progreso en %",
        u"progressMode": u"Modo de progreso",
        u"scale": u"Escala",
        u"position": u"Posición (px)",
        u"posX": u"Horizontal (centro X)",
        u"posY": u"Vertical (arriba Y)",
        u"onslaughtPosX": u"Horizontal (Embestida X)",
        u"onslaughtPosY": u"Vertical (Embestida Y)",
    },
    u"it": {
        u"modes": u"Modalità",
        u"formatting": u"Formattazione",
        u"layout": u"Disposizione",
        u"showWhenComplete": u"Completamente progredito",
        u"allowFallthrough": u"Consenti il ripiego",
        u"ignoreFreeXp": u"Ignora l'esperienza libera",
        u"showPercent": u"Mostra l'avanzamento in %",
        u"progressMode": u"Modalità di avanzamento",
        u"scale": u"Scala",
        u"position": u"Posizione (px)",
        u"posX": u"Orizzontale (centro X)",
        u"posY": u"Verticale (alto Y)",
        u"onslaughtPosX": u"Orizzontale (Assalto X)",
        u"onslaughtPosY": u"Verticale (Assalto Y)",
    },
    u"pl": {
        u"modes": u"Tryby",
        u"formatting": u"Formatowanie",
        u"layout": u"Układ",
        u"showWhenComplete": u"W pełni ukończone",
        u"allowFallthrough": u"Zezwól na zastępstwo",
        u"ignoreFreeXp": u"Ignoruj wolne doświadczenie",
        u"showPercent": u"Pokaż postęp w %",
        u"progressMode": u"Tryb postępu",
        u"scale": u"Skala",
        u"position": u"Pozycja (px)",
        u"posX": u"Pozioma (środek X)",
        u"posY": u"Pionowa (góra Y)",
        u"onslaughtPosX": u"Pozioma (Napór X)",
        u"onslaughtPosY": u"Pionowa (Napór Y)",
    },
    u"cs": {
        u"modes": u"Režimy",
        u"formatting": u"Formátování",
        u"layout": u"Rozvržení",
        u"showWhenComplete": u"Plně dokončeno",
        u"allowFallthrough": u"Povolit náhradu",
        u"ignoreFreeXp": u"Ignorovat volné zkušenosti",
        u"showPercent": u"Zobrazit postup v %",
        u"progressMode": u"Režim postupu",
        u"scale": u"Měřítko",
        u"position": u"Pozice (px)",
        u"posX": u"Vodorovná (střed X)",
        u"posY": u"Svislá (nahoře Y)",
        u"onslaughtPosX": u"Vodorovná (Nápor X)",
        u"onslaughtPosY": u"Svislá (Nápor Y)",
    },
    u"ru": {
        u"modes": u"Режимы",
        u"formatting": u"Форматирование",
        u"layout": u"Расположение",
        u"showWhenComplete": u"Полностью пройдено",
        u"allowFallthrough": u"Разрешить запасной режим",
        u"ignoreFreeXp": u"Игнорировать свободный опыт",
        u"showPercent": u"Показывать прогресс в %",
        u"progressMode": u"Режим прогресса",
        u"scale": u"Масштаб",
        u"position": u"Позиция (px)",
        u"posX": u"Горизонтальная (центр X)",
        u"posY": u"Вертикальная (верх Y)",
        u"onslaughtPosX": u"Горизонтальная (Натиск X)",
        u"onslaughtPosY": u"Вертикальная (Натиск Y)",
    },
    u"uk": {
        u"modes": u"Режими",
        u"formatting": u"Форматування",
        u"layout": u"Розташування",
        u"showWhenComplete": u"Повністю пройдено",
        u"allowFallthrough": u"Дозволити резервний режим",
        u"ignoreFreeXp": u"Ігнорувати вільний досвід",
        u"showPercent": u"Показувати прогрес у %",
        u"progressMode": u"Режим прогресу",
        u"scale": u"Масштаб",
        # "Позиція", not "Розташування" -- the latter is the column3 header above it, and
        # two identical captions one under the other read as a duplicated row.
        u"position": u"Позиція (px)",
        u"posX": u"Горизонтальна (центр X)",
        u"posY": u"Вертикальна (верх Y)",
        u"onslaughtPosX": u"Горизонтальна (Натиск X)",
        u"onslaughtPosY": u"Вертикальна (Натиск Y)",
    },
    u"hu": {
        u"modes": u"Módok",
        u"formatting": u"Formázás",
        u"layout": u"Elrendezés",
        u"showWhenComplete": u"Teljesen kész",
        u"allowFallthrough": u"Tartalékmód engedélyezése",
        u"ignoreFreeXp": u"Szabad tapasztalat mellőzése",
        u"showPercent": u"Haladás megjelenítése %-ban",
        u"progressMode": u"Haladási mód",
        u"scale": u"Méretezés",
        u"position": u"Pozíció (px)",
        u"posX": u"Vízszintes (középpont X)",
        u"posY": u"Függőleges (felső Y)",
        u"onslaughtPosX": u"Vízszintes (Roham X)",
        u"onslaughtPosY": u"Függőleges (Roham Y)",
    },
    u"tr": {
        u"modes": u"Modlar",
        u"formatting": u"Biçimlendirme",
        u"layout": u"Yerleşim",
        u"showWhenComplete": u"Tamamen ilerlemiş",
        u"allowFallthrough": u"Yedek moda izin ver",
        u"ignoreFreeXp": u"Serbest deneyimi yok say",
        u"showPercent": u"İlerlemeyi % olarak göster",
        u"progressMode": u"İlerleme modu",
        u"scale": u"Ölçek",
        u"position": u"Konum (px)",
        u"posX": u"Yatay (merkez X)",
        u"posY": u"Dikey (üst Y)",
        u"onslaughtPosX": u"Yatay (Hücum X)",
        u"onslaughtPosY": u"Dikey (Hücum Y)",
    },
}


# --- SCALE DROPDOWN OPTION LABELS (hand-translated) -----------------------------------
# The two option labels for the "scale" radio group: (Default, Large). Kept in their OWN
# table -- NOT in _LABELS -- because options are not per-control label/tooltip rows, so
# folding them into _LABELS would break the label/tooltip key partition (see the
# settings_i18n tests). render_panel attaches the localized pair on t["scale"]["options"];
# English master + per-language fallback (marked on fallback), same policy as _LABELS.
_SCALE_OPTIONS = {
    u"en": (u"Default", u"Large"),
    u"de": (u"Standard", u"Groß"),
    u"fr": (u"Par défaut", u"Grande"),
    u"es": (u"Predeterminada", u"Grande"),
    u"it": (u"Predefinita", u"Grande"),
    u"pl": (u"Domyślna", u"Duża"),
    u"cs": (u"Výchozí", u"Velké"),
    u"ru": (u"По умолчанию", u"Большой"),
    u"uk": (u"За замовчуванням", u"Великий"),
    u"hu": (u"Alapértelmezett", u"Nagy"),
    u"tr": (u"Varsayılan", u"Büyük"),
}


# --- PROGRESS-MODE DROPDOWN OPTION LABELS (hand-translated) ---------------------------
# The two option labels for the "progressMode" radio group: (Current, Current / Required).
# Own table (see _SCALE_OPTIONS rationale). render_panel attaches the localized pair on
# t["progressMode"]["options"]; English master + per-language fallback (marked on
# fallback). Plain "/" only -- never an em-dash (the client renders one as "--").
_PROGRESS_OPTIONS = {
    u"en": (u"Current", u"Current / Required"),
    u"de": (u"Aktuell", u"Aktuell / Benötigt"),
    u"fr": (u"Actuel", u"Actuel / Requis"),
    u"es": (u"Actual", u"Actual / Necesario"),
    u"it": (u"Attuale", u"Attuale / Richiesta"),
    u"pl": (u"Aktualny", u"Aktualny / Wymagany"),
    u"cs": (u"Aktuální", u"Aktuální / Potřebný"),
    u"ru": (u"Текущий", u"Текущий / Требуемый"),
    u"uk": (u"Поточний", u"Поточний / Потрібний"),
    u"hu": (u"Jelenlegi", u"Jelenlegi / Szükséges"),
    u"tr": (u"Mevcut", u"Mevcut / Gerekli"),
}


# --- TOOLTIPS (hand-translated) -------------------------------------------------------
# Lang-major, exactly like _LABELS: {lang: {key: (header, body)}}. 'en' is the always-
# complete MASTER; every other language is overlaid PER KEY, so a key a language hasn't
# translated renders from English rather than blanking (render_panel does the overlay).
# The header mirrors the control's LABEL in that language, the body is the mod's own
# explanatory prose; render_panel assembles the {HEADER}/{BODY} markup once, so no
# translation string carries markup. The three category headers (modes / formatting /
# layout) are inert section captions and carry NO entry here -- render_panel then omits
# their tooltip key entirely.
#
# Translator rules baked into these blocks:
#  * a body that names an OPTION ("Default"/"Large", "Current / Required") must use that
#    language's _SCALE_OPTIONS / _PROGRESS_OPTIONS wording verbatim, and a body that names
#    a feature must use the same noun the LABEL uses (Elite System, Free XP, ...);
#  * game concepts use WoT's OWN per-language wording (uk confirmed against the client's
#    res/text/lc_messages: Дослідження / Модернізація / Польова модернізація / Елітні
#    нагороди / Система «Еліта» / Вільний досвід / "XI рівень"), not an English calque;
#  * gender/case agreement follows each language's noun for "bar" (de Leiste, fr barre,
#    es/it barra, pl pasek, cs lišta, ru полоса, uk смуга, hu sáv, tr çubuk);
#  * NO em-dashes (the client renders one as "--"): the plain " - " in the scale body and
#    the "%", "/", "+" and roman-numeral tokens stay byte-identical to English.
_TOOLTIPS = {
    u"en": {
        u"showWhenComplete": (u"Fully Progressed",
                              u"Keeps the bar visible on vehicles with nothing left to "
                              u"research, upgrade, or unlock. Uncheck to hide the bar once a "
                              u"vehicle is fully progressed."),
        u"allowFallthrough": (u"Allow Fallthrough",
                              u"When on, the bar skips a disabled mode and shows the next "
                              u"available mode in priority order, instead of hiding the bar. "
                              u"Off by default."),
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
        u"scale": (u"Scale",
                   u"Sets the on-screen size of the progress bar. Default keeps the standard "
                   u"size; Large roughly doubles the bar's width and enlarges its text, icons, "
                   u"and tooltip - handy on high-resolution or far-away displays."),
        u"progressMode": (u"Progress Mode",
                          u"Sets what the XP readout shows. Current shows only the XP you "
                          u"have so far; Current / Required shows how much you have out of "
                          u"how much the bar needs."),
        u"showPercent": (u"Show Progress %",
                         u"Adds a progress percentage to the left of the XP readout. Works on "
                         u"its own or alongside Progress Mode. Off by default."),
        u"position": (u"Position",
                      u"Ctrl+drag the bar in the garage to move it, or type exact "
                      u"on-screen pixel coordinates below. Reset returns it to the "
                      u"default position."),
        u"posX": (u"Horizontal position",
                  u"The bar's CENTER, in pixels from the left screen edge."),
        u"posY": (u"Vertical position",
                  u"The bar's TOP, in pixels from the top screen edge."),
        u"onslaughtPosX": (u"Horizontal position (Onslaught)",
                           u"The bar's CENTER in the Onslaught garage, in pixels from the "
                           u"left screen edge. 0 inherits the regular Horizontal position."),
        u"onslaughtPosY": (u"Vertical position (Onslaught)",
                           u"The bar's TOP in the Onslaught garage, in pixels from the top "
                           u"screen edge. 0 inherits the regular Vertical position."),
    },
    u"de": {
        u"showWhenComplete": (u"Vollständig fortgeschritten",
                              u"Hält die Leiste bei Fahrzeugen sichtbar, bei denen nichts mehr "
                              u"zu erforschen, zu modernisieren oder freizuschalten ist. "
                              u"Abwählen, um die Leiste bei vollständig fortgeschrittenen "
                              u"Fahrzeugen auszublenden."),
        u"allowFallthrough": (u"Fallback zulassen",
                              u"Wenn aktiviert, überspringt die Leiste einen deaktivierten "
                              u"Modus und zeigt stattdessen den nächsten verfügbaren Modus in "
                              u"der Prioritätsreihenfolge, statt sich auszublenden. "
                              u"Standardmäßig aus."),
        u"ignoreFreeXp": (u"Freie Erfahrung ignorieren",
                          u"Rechnet nur die Gefechtserfahrung, die du mit dem jeweiligen "
                          u"Fahrzeug verdienst, in seinen Fortschritt ein. Freie Erfahrung "
                          u"bleibt in der Leiste, den Summen und den Tooltips "
                          u"unberücksichtigt. Standardmäßig aus."),
        u"showTechTree": (u"Forschung",
                          u"Der Fortschritt im Forschungsbaum zu den verbleibenden Modulen "
                          u"und Folgefahrzeugen des Fahrzeugs."),
        u"showSkillTree": (u"Modernisierung",
                           u"Der verzweigte Modernisierungsbaum bei Fahrzeugen der Stufe XI."),
        u"showFieldMods": (u"Feldmodifikationen",
                           u"Die Feldmodifikationsstufen, die nach vollständiger Erforschung "
                           u"des Fahrzeugs freigeschaltet werden."),
        u"showEliteRewards": (u"Elite-Belohnungen",
                              u"Der stufenexklusive Fahrplan der Meilenstein-Belohnungen bei "
                              u"Prestige-Fahrzeugen."),
        u"showElite": (u"Elite-System",
                       u"Der Fortschritt über die Stufenspannen der Elite-Stufen bei "
                       u"Prestige-Fahrzeugen."),
        u"showPotentialTierXI": (u"Stufe XI",
                                 u"Bei einem Panzer der Stufe X ohne Stufe XI: sobald er "
                                 u"vollständig erforscht und seine Feldmodifikationen "
                                 u"abgeschlossen sind, wird deine angesparte Erfahrung "
                                 u"(Fahrzeugerfahrung + Freie Erfahrung) am festen Preis "
                                 u"gemessen, den das Freischalten einer Stufe XI kostet. "
                                 u"Ersetzt bei diesen Panzern die Elite-Stufen-Leiste. "
                                 u"Standardmäßig aus."),
        u"scale": (u"Skalierung",
                   u"Legt die Bildschirmgröße der Fortschrittsleiste fest. Standard behält "
                   u"die normale Größe; Groß verdoppelt die Breite der Leiste etwa und "
                   u"vergrößert ihren Text, ihre Symbole und ihren Tooltip - praktisch bei "
                   u"hohen Auflösungen oder weit entfernten Bildschirmen."),
        u"progressMode": (u"Fortschrittsmodus",
                          u"Legt fest, was die Erfahrungsanzeige zeigt. Aktuell zeigt nur die "
                          u"bisher gesammelte Erfahrung; Aktuell / Benötigt zeigt, wie viel du "
                          u"von der benötigten Menge hast."),
        u"showPercent": (u"Fortschritt in % anzeigen",
                         u"Setzt links neben die Erfahrungsanzeige einen Fortschritt in "
                         u"Prozent. Funktioniert allein oder zusammen mit dem "
                         u"Fortschrittsmodus. Standardmäßig aus."),
        u"position": (u"Position",
                      u"Verschiebe die Leiste in der Garage mit Strg+Ziehen, oder gib unten "
                      u"exakte Pixelkoordinaten ein. Das Zurücksetzen stellt die "
                      u"Standardposition wieder her."),
        u"posX": (u"Horizontale Position",
                  u"Die MITTE der Leiste, in Pixeln vom linken Bildschirmrand."),
        u"posY": (u"Vertikale Position",
                  u"Die OBERKANTE der Leiste, in Pixeln vom oberen Bildschirmrand."),
        u"onslaughtPosX": (u"Horizontale Position (Ansturm)",
                           u"Die MITTE der Leiste in der Ansturm-Garage, in Pixeln vom linken "
                           u"Bildschirmrand. 0 übernimmt die normale horizontale Position."),
        u"onslaughtPosY": (u"Vertikale Position (Ansturm)",
                           u"Die OBERKANTE der Leiste in der Ansturm-Garage, in Pixeln vom "
                           u"oberen Bildschirmrand. 0 übernimmt die normale vertikale Position."),
    },
    u"fr": {
        u"showWhenComplete": (u"Entièrement progressé",
                              u"Garde la barre visible sur les véhicules qui n'ont plus rien à "
                              u"rechercher, à moderniser ni à débloquer. Décochez pour masquer "
                              u"la barre dès qu'un véhicule est entièrement progressé."),
        u"allowFallthrough": (u"Autoriser le repli",
                              u"Une fois activé, la barre ignore un mode désactivé et affiche "
                              u"le mode disponible suivant par ordre de priorité, au lieu de se "
                              u"masquer. Désactivé par défaut."),
        u"ignoreFreeXp": (u"Ignorer l'expérience libre",
                          u"Ne compte que l'expérience de combat gagnée sur chaque véhicule "
                          u"dans sa progression. L'expérience libre est exclue de la barre, "
                          u"des totaux et des infobulles. Désactivé par défaut."),
        u"showTechTree": (u"Recherche",
                          u"La progression dans l'arbre technologique vers les modules et les "
                          u"véhicules suivants qu'il reste à débloquer."),
        u"showSkillTree": (u"Modernisation",
                           u"L'arbre de modernisation ramifié des véhicules de rang XI."),
        u"showFieldMods": (u"Modifications de campagne",
                           u"Les paliers de modifications de campagne débloqués une fois le "
                           u"véhicule entièrement recherché."),
        u"showEliteRewards": (u"Récompenses d'élite",
                              u"La feuille de route des récompenses par palier, exclusive au "
                              u"rang, sur les véhicules de prestige."),
        u"showElite": (u"Système Élite",
                       u"La progression par plages de niveaux d'élite sur les véhicules de "
                       u"prestige."),
        u"showPotentialTierXI": (u"Rang XI",
                                 u"Sur un char de rang X sans rang XI, une fois qu'il est "
                                 u"entièrement recherché et ses modifications de campagne "
                                 u"terminées, suit votre expérience accumulée (expérience du "
                                 u"véhicule + expérience libre) par rapport au prix fixe que "
                                 u"coûte le déblocage d'un rang XI. Remplace la barre des "
                                 u"niveaux d'élite sur ces chars. Désactivé par défaut."),
        u"scale": (u"Échelle",
                   u"Définit la taille à l'écran de la barre de progression. Par défaut "
                   u"conserve la taille normale ; Grande double environ la largeur de la barre "
                   u"et agrandit son texte, ses icônes et son infobulle - pratique sur les "
                   u"écrans à haute résolution ou éloignés."),
        u"progressMode": (u"Mode de progression",
                          u"Définit ce qu'affiche le compteur d'expérience. Actuel n'affiche "
                          u"que l'expérience déjà acquise ; Actuel / Requis affiche ce que vous "
                          u"avez sur ce que la barre demande."),
        u"showPercent": (u"Afficher la progression en %",
                         u"Ajoute un pourcentage de progression à gauche du compteur "
                         u"d'expérience. Fonctionne seul ou avec le mode de progression. "
                         u"Désactivé par défaut."),
        u"position": (u"Position",
                      u"Ctrl+glissez la barre dans le garage pour la déplacer, ou saisissez "
                      u"ci-dessous des coordonnées exactes en pixels. La réinitialisation la "
                      u"remet à sa position par défaut."),
        u"posX": (u"Position horizontale",
                  u"Le CENTRE de la barre, en pixels depuis le bord gauche de l'écran."),
        u"posY": (u"Position verticale",
                  u"Le HAUT de la barre, en pixels depuis le bord supérieur de l'écran."),
        u"onslaughtPosX": (u"Position horizontale (Assaut)",
                           u"Le CENTRE de la barre dans le garage Assaut, en pixels depuis le "
                           u"bord gauche de l'écran. 0 reprend la position horizontale "
                           u"habituelle."),
        u"onslaughtPosY": (u"Position verticale (Assaut)",
                           u"Le HAUT de la barre dans le garage Assaut, en pixels depuis le "
                           u"bord supérieur de l'écran. 0 reprend la position verticale "
                           u"habituelle."),
    },
    u"es": {
        u"showWhenComplete": (u"Progreso completo",
                              u"Mantiene la barra visible en los vehículos a los que no les "
                              u"queda nada por investigar, modernizar ni desbloquear. Desmarca "
                              u"para ocultar la barra cuando un vehículo tenga el progreso "
                              u"completo."),
        u"allowFallthrough": (u"Permitir alternativa",
                              u"Cuando está activado, la barra omite un modo desactivado y "
                              u"muestra el siguiente modo disponible por orden de prioridad, en "
                              u"lugar de ocultarse. Desactivado por defecto."),
        u"ignoreFreeXp": (u"Ignorar la experiencia libre",
                          u"Cuenta solo la experiencia de combate que ganas con cada vehículo "
                          u"para su progreso. La experiencia libre queda excluida de la barra, "
                          u"de los totales y de las descripciones. Desactivado por defecto."),
        u"showTechTree": (u"Investigación",
                          u"El progreso en el árbol tecnológico hacia los módulos y los "
                          u"siguientes vehículos que quedan por desbloquear."),
        u"showSkillTree": (u"Modernización",
                           u"El árbol ramificado de modernización de los vehículos de nivel "
                           u"XI."),
        u"showFieldMods": (u"Modificaciones de campo",
                           u"Los pasos de modificaciones de campo que se desbloquean una vez "
                           u"investigado por completo el vehículo."),
        u"showEliteRewards": (u"Recompensas de élite",
                              u"La hoja de ruta de recompensas por hitos, exclusiva del nivel, "
                              u"en los vehículos de prestigio."),
        u"showElite": (u"Sistema Élite",
                       u"El progreso por franjas de niveles de élite en los vehículos de "
                       u"prestigio."),
        u"showPotentialTierXI": (u"Nivel XI",
                                 u"En un tanque de nivel X sin nivel XI, una vez investigado "
                                 u"por completo y terminadas sus modificaciones de campo, "
                                 u"sigue tu experiencia acumulada (experiencia del vehículo + "
                                 u"experiencia libre) frente al precio fijo que cuesta "
                                 u"desbloquear un nivel XI. Sustituye la barra de niveles de "
                                 u"élite en esos tanques. Desactivado por defecto."),
        u"scale": (u"Escala",
                   u"Establece el tamaño en pantalla de la barra de progreso. Predeterminada "
                   u"mantiene el tamaño normal; Grande casi duplica el ancho de la barra y "
                   u"amplía su texto, sus iconos y su descripción - útil en pantallas de alta "
                   u"resolución o alejadas."),
        u"progressMode": (u"Modo de progreso",
                          u"Establece qué muestra el contador de experiencia. Actual muestra "
                          u"solo la experiencia que llevas; Actual / Necesario muestra cuánta "
                          u"tienes de la que necesita la barra."),
        u"showPercent": (u"Mostrar el progreso en %",
                         u"Añade un porcentaje de progreso a la izquierda del contador de "
                         u"experiencia. Funciona por sí solo o junto con el modo de progreso. "
                         u"Desactivado por defecto."),
        u"position": (u"Posición",
                      u"Ctrl+arrastra la barra en el garaje para moverla, o escribe abajo "
                      u"coordenadas exactas en píxeles. El restablecimiento la devuelve a su "
                      u"posición predeterminada."),
        u"posX": (u"Posición horizontal",
                  u"El CENTRO de la barra, en píxeles desde el borde izquierdo de la "
                  u"pantalla."),
        u"posY": (u"Posición vertical",
                  u"La PARTE SUPERIOR de la barra, en píxeles desde el borde superior de la "
                  u"pantalla."),
        u"onslaughtPosX": (u"Posición horizontal (Embestida)",
                           u"El CENTRO de la barra en el garaje de Embestida, en píxeles desde "
                           u"el borde izquierdo de la pantalla. 0 hereda la posición "
                           u"horizontal normal."),
        u"onslaughtPosY": (u"Posición vertical (Embestida)",
                           u"La PARTE SUPERIOR de la barra en el garaje de Embestida, en "
                           u"píxeles desde el borde superior de la pantalla. 0 hereda la "
                           u"posición vertical normal."),
    },
    u"it": {
        u"showWhenComplete": (u"Completamente progredito",
                              u"Mantiene la barra visibile sui veicoli che non hanno più nulla "
                              u"da ricercare, ammodernare o sbloccare. Deseleziona per "
                              u"nascondere la barra quando un veicolo è completamente "
                              u"progredito."),
        u"allowFallthrough": (u"Consenti il ripiego",
                              u"Se attivo, la barra salta una modalità disattivata e mostra la "
                              u"successiva modalità disponibile in ordine di priorità, invece "
                              u"di nascondersi. Disattivato per impostazione predefinita."),
        u"ignoreFreeXp": (u"Ignora l'esperienza libera",
                          u"Conteggia solo l'esperienza di combattimento che guadagni su "
                          u"ciascun veicolo per il suo progresso. L'esperienza libera è esclusa "
                          u"dalla barra, dai totali e dai suggerimenti. Disattivato per "
                          u"impostazione predefinita."),
        u"showTechTree": (u"Ricerca",
                          u"Il progresso nell'albero tecnologico verso i moduli e i veicoli "
                          u"successivi ancora da sbloccare."),
        u"showSkillTree": (u"Ammodernamento",
                           u"L'albero ramificato di ammodernamento dei veicoli di grado XI."),
        u"showFieldMods": (u"Modifiche di campo",
                           u"Le fasi di modifiche di campo che si sbloccano una volta ricercato "
                           u"completamente il veicolo."),
        u"showEliteRewards": (u"Ricompense Elite",
                              u"La tabella di marcia delle ricompense a tappe, esclusiva del "
                              u"grado, sui veicoli prestigio."),
        u"showElite": (u"Sistema Elite",
                       u"Il progresso per fasce di livelli Elite sui veicoli prestigio."),
        u"showPotentialTierXI": (u"Grado XI",
                                 u"Su un carro di grado X senza grado XI, una volta ricercato "
                                 u"completamente e completate le sue modifiche di campo, tiene "
                                 u"traccia della tua esperienza accumulata (esperienza del "
                                 u"veicolo + esperienza libera) rispetto al prezzo fisso che "
                                 u"costa sbloccare un grado XI. Su quei carri sostituisce la "
                                 u"barra dei livelli Elite. Disattivato per impostazione "
                                 u"predefinita."),
        u"scale": (u"Scala",
                   u"Imposta la dimensione a schermo della barra di progresso. Predefinita "
                   u"mantiene la dimensione normale; Grande raddoppia circa la larghezza della "
                   u"barra e ingrandisce il suo testo, le sue icone e il suo suggerimento - "
                   u"utile su schermi ad alta risoluzione o lontani."),
        u"progressMode": (u"Modalità di avanzamento",
                          u"Imposta cosa mostra il contatore dell'esperienza. Attuale mostra "
                          u"solo l'esperienza già ottenuta; Attuale / Richiesta mostra quanta "
                          u"ne hai su quanta serve alla barra."),
        u"showPercent": (u"Mostra l'avanzamento in %",
                         u"Aggiunge una percentuale di avanzamento a sinistra del contatore "
                         u"dell'esperienza. Funziona da sola o insieme alla modalità di "
                         u"avanzamento. Disattivato per impostazione predefinita."),
        u"position": (u"Posizione",
                      u"Ctrl+trascina la barra nel garage per spostarla, oppure inserisci sotto "
                      u"le coordinate esatte in pixel. Il ripristino la riporta alla posizione "
                      u"predefinita."),
        u"posX": (u"Posizione orizzontale",
                  u"Il CENTRO della barra, in pixel dal bordo sinistro dello schermo."),
        u"posY": (u"Posizione verticale",
                  u"La PARTE SUPERIORE della barra, in pixel dal bordo superiore dello "
                  u"schermo."),
        u"onslaughtPosX": (u"Posizione orizzontale (Assalto)",
                           u"Il CENTRO della barra nell'hangar Assalto, in pixel dal bordo "
                           u"sinistro dello schermo. 0 eredita la normale posizione "
                           u"orizzontale."),
        u"onslaughtPosY": (u"Posizione verticale (Assalto)",
                           u"La PARTE SUPERIORE della barra nell'hangar Assalto, in pixel dal "
                           u"bordo superiore dello schermo. 0 eredita la normale posizione "
                           u"verticale."),
    },
    u"pl": {
        u"showWhenComplete": (u"W pełni ukończone",
                              u"Utrzymuje pasek widoczny na pojazdach, w których nie ma już nic "
                              u"do zbadania, zmodernizowania ani odblokowania. Odznacz, aby "
                              u"ukryć pasek, gdy pojazd jest w pełni ukończony."),
        u"allowFallthrough": (u"Zezwól na zastępstwo",
                              u"Gdy włączone, pasek pomija wyłączony tryb i pokazuje kolejny "
                              u"dostępny tryb w kolejności priorytetu, zamiast się ukrywać. "
                              u"Domyślnie wyłączone."),
        u"ignoreFreeXp": (u"Ignoruj wolne doświadczenie",
                          u"Do postępu każdego pojazdu wlicza tylko doświadczenie bojowe na nim "
                          u"zdobyte. Wolne doświadczenie jest pomijane na pasku, w sumach i w "
                          u"podpowiedziach. Domyślnie wyłączone."),
        u"showTechTree": (u"Badania",
                          u"Postęp w drzewku technologicznym w stronę pozostałych modułów i "
                          u"kolejnych pojazdów do odblokowania."),
        u"showSkillTree": (u"Modernizacja",
                           u"Rozgałęzione drzewko modernizacji pojazdów XI poziomu."),
        u"showFieldMods": (u"Modyfikacje polowe",
                           u"Etapy modyfikacji polowych odblokowywane po całkowitym zbadaniu "
                           u"pojazdu."),
        u"showEliteRewards": (u"Nagrody elitarne",
                              u"Ekskluzywna dla poziomu mapa nagród za kolejne etapy na "
                              u"pojazdach prestiżowych."),
        u"showElite": (u"System Elite",
                       u"Postęp w zakresach poziomów Elite na pojazdach prestiżowych."),
        u"showPotentialTierXI": (u"XI poziom",
                                 u"Na czołgu X poziomu bez XI poziomu, gdy jest już w pełni "
                                 u"zbadany, a jego modyfikacje polowe są ukończone, śledzi "
                                 u"zgromadzone doświadczenie (doświadczenie pojazdu + wolne "
                                 u"doświadczenie) w stosunku do stałej ceny odblokowania XI "
                                 u"poziomu. Na tych czołgach zastępuje pasek poziomów Elite. "
                                 u"Domyślnie wyłączone."),
        u"scale": (u"Skala",
                   u"Ustawia rozmiar paska postępu na ekranie. Domyślna zachowuje zwykły "
                   u"rozmiar; Duża zwiększa szerokość paska niemal dwukrotnie i powiększa jego "
                   u"tekst, ikony oraz podpowiedź - przydatne na ekranach o wysokiej "
                   u"rozdzielczości lub oddalonych."),
        u"progressMode": (u"Tryb postępu",
                          u"Ustawia, co pokazuje licznik doświadczenia. Aktualny pokazuje tylko "
                          u"dotychczas zdobyte doświadczenie; Aktualny / Wymagany pokazuje, ile "
                          u"masz z tego, ile potrzebuje pasek."),
        u"showPercent": (u"Pokaż postęp w %",
                         u"Dodaje procent postępu po lewej stronie licznika doświadczenia. "
                         u"Działa samodzielnie lub razem z trybem postępu. Domyślnie "
                         u"wyłączone."),
        u"position": (u"Pozycja",
                      u"Ctrl+przeciągnij pasek w garażu, aby go przenieść, lub wpisz poniżej "
                      u"dokładne współrzędne w pikselach. Zerowanie przywraca go na pozycję "
                      u"domyślną."),
        u"posX": (u"Pozycja pozioma",
                  u"ŚRODEK paska, w pikselach od lewej krawędzi ekranu."),
        u"posY": (u"Pozycja pionowa",
                  u"GÓRA paska, w pikselach od górnej krawędzi ekranu."),
        u"onslaughtPosX": (u"Pozycja pozioma (Napór)",
                           u"ŚRODEK paska w garażu Napór, w pikselach od lewej krawędzi "
                           u"ekranu. 0 przejmuje zwykłą pozycję poziomą."),
        u"onslaughtPosY": (u"Pozycja pionowa (Napór)",
                           u"GÓRA paska w garażu Napór, w pikselach od górnej krawędzi "
                           u"ekranu. 0 przejmuje zwykłą pozycję pionową."),
    },
    u"cs": {
        u"showWhenComplete": (u"Plně dokončeno",
                              u"Nechá lištu zobrazenou u vozidel, u nichž už není co "
                              u"vyzkoumat, modernizovat ani odemknout. Odškrtnutím lištu "
                              u"skryjete, jakmile je vozidlo plně dokončeno."),
        u"allowFallthrough": (u"Povolit náhradu",
                              u"Je-li zapnuto, lišta přeskočí vypnutý režim a zobrazí další "
                              u"dostupný režim podle pořadí priority, místo aby se skryla. Ve "
                              u"výchozím nastavení vypnuto."),
        u"ignoreFreeXp": (u"Ignorovat volné zkušenosti",
                          u"Do postupu každého vozidla počítá jen bojové zkušenosti, které na "
                          u"něm získáte. Volné zkušenosti jsou vynechány z lišty, ze součtů i z "
                          u"popisků. Ve výchozím nastavení vypnuto."),
        u"showTechTree": (u"Výzkum",
                          u"Postup ve výzkumném stromu k modulům a dalším vozidlům, které "
                          u"vozidlu zbývá odemknout."),
        u"showSkillTree": (u"Modernizace",
                           u"Rozvětvený strom modernizace u vozidel XI. úrovně."),
        u"showFieldMods": (u"Polní modifikace",
                           u"Stupně polních modifikací odemčené po plném vyzkoumání vozidla."),
        u"showEliteRewards": (u"Elitní odměny",
                              u"Plán milníkových odměn, exkluzivní pro danou úroveň, u "
                              u"prestižních vozidel."),
        u"showElite": (u"Systém Elite",
                       u"Postup v pásmech elitních úrovní u prestižních vozidel."),
        u"showPotentialTierXI": (u"XI. úroveň",
                                 u"U tanku X. úrovně bez XI. úrovně, jakmile je plně "
                                 u"vyzkoumaný a jeho polní modifikace jsou hotové, sleduje "
                                 u"nastřádané zkušenosti (zkušenosti vozidla + volné "
                                 u"zkušenosti) vůči pevné ceně, kterou odemčení XI. úrovně "
                                 u"stojí. U těchto tanků nahrazuje lištu elitních úrovní. Ve "
                                 u"výchozím nastavení vypnuto."),
        u"scale": (u"Měřítko",
                   u"Nastaví velikost lišty postupu na obrazovce. Výchozí zachová běžnou "
                   u"velikost; Velké zvětší šířku lišty přibližně na dvojnásobek a zvětší její "
                   u"text, ikony i popisek - hodí se na displeje s vysokým rozlišením nebo na "
                   u"vzdálené displeje."),
        u"progressMode": (u"Režim postupu",
                          u"Nastaví, co zobrazuje ukazatel zkušeností. Aktuální zobrazí jen "
                          u"dosud získané zkušenosti; Aktuální / Potřebný zobrazí, kolik máte z "
                          u"toho, co lišta potřebuje."),
        u"showPercent": (u"Zobrazit postup v %",
                         u"Přidá procento postupu vlevo od ukazatele zkušeností. Funguje "
                         u"samostatně i společně s režimem postupu. Ve výchozím nastavení "
                         u"vypnuto."),
        u"position": (u"Pozice",
                      u"Ctrl+tažením přesunete lištu v garáži, nebo níže zadejte přesné "
                      u"souřadnice v pixelech. Obnovení ji vrátí na výchozí pozici."),
        u"posX": (u"Vodorovná pozice",
                  u"STŘED lišty, v pixelech od levého okraje obrazovky."),
        u"posY": (u"Svislá pozice",
                  u"HORNÍ HRANA lišty, v pixelech od horního okraje obrazovky."),
        u"onslaughtPosX": (u"Vodorovná pozice (Nápor)",
                           u"STŘED lišty v garáži Nápor, v pixelech od levého okraje "
                           u"obrazovky. 0 převezme běžnou vodorovnou pozici."),
        u"onslaughtPosY": (u"Svislá pozice (Nápor)",
                           u"HORNÍ HRANA lišty v garáži Nápor, v pixelech od horního okraje "
                           u"obrazovky. 0 převezme běžnou svislou pozici."),
    },
    u"ru": {
        u"showWhenComplete": (u"Полностью пройдено",
                              u"Оставляет полосу на машинах, у которых больше нечего "
                              u"исследовать, модернизировать или открывать. Снимите отметку, "
                              u"чтобы скрывать полосу на полностью пройденных машинах."),
        u"allowFallthrough": (u"Разрешить запасной режим",
                              u"Если включено, полоса пропускает выключенный режим и "
                              u"показывает следующий доступный режим по порядку приоритета, "
                              u"вместо того чтобы скрываться. По умолчанию выключено."),
        u"ignoreFreeXp": (u"Игнорировать свободный опыт",
                          u"В прогресс каждой машины засчитывается только боевой опыт, "
                          u"полученный на ней. Свободный опыт не учитывается ни в полосе, ни в "
                          u"итогах, ни в подсказках. По умолчанию выключено."),
        u"showTechTree": (u"Исследование",
                          u"Прогресс в дереве исследований к оставшимся модулям и следующим "
                          u"машинам."),
        u"showSkillTree": (u"Модернизация",
                           u"Ветвящееся дерево модернизации на машинах XI уровня."),
        u"showFieldMods": (u"Полевая модернизация",
                           u"Этапы полевой модернизации, доступные после полного исследования "
                           u"машины."),
        u"showEliteRewards": (u"Элитные награды",
                              u"Эксклюзивная для уровня карта наград за этапы на престижных "
                              u"машинах."),
        u"showElite": (u"Система «Элита»",
                       u"Прогресс по диапазонам элитных уровней на престижных машинах."),
        u"showPotentialTierXI": (u"XI уровень",
                                 u"На танке X уровня без XI уровня, когда он полностью "
                                 u"исследован и его полевая модернизация завершена, "
                                 u"отслеживает накопленный опыт (опыт машины + свободный опыт) "
                                 u"относительно фиксированной цены открытия XI уровня. Заменяет "
                                 u"полосу элитных уровней на таких танках. По умолчанию "
                                 u"выключено."),
        u"scale": (u"Масштаб",
                   u"Задаёт размер полосы прогресса на экране. По умолчанию сохраняет обычный "
                   u"размер; Большой почти удваивает ширину полосы и увеличивает её текст, "
                   u"значки и подсказку - удобно на экранах с высоким разрешением или "
                   u"удалённых."),
        u"progressMode": (u"Режим прогресса",
                          u"Задаёт, что показывает счётчик опыта. Текущий показывает только "
                          u"уже полученный опыт; Текущий / Требуемый показывает, сколько у вас "
                          u"есть из того, что нужно полосе."),
        u"showPercent": (u"Показывать прогресс в %",
                         u"Добавляет процент прогресса слева от счётчика опыта. Работает сам по "
                         u"себе или вместе с режимом прогресса. По умолчанию выключено."),
        u"position": (u"Позиция",
                      u"Ctrl+перетаскивание перемещает полосу в ангаре, либо укажите ниже "
                      u"точные координаты в пикселях. Сброс возвращает её на позицию по "
                      u"умолчанию."),
        u"posX": (u"Позиция по горизонтали",
                  u"ЦЕНТР полосы, в пикселях от левого края экрана."),
        u"posY": (u"Позиция по вертикали",
                  u"ВЕРХ полосы, в пикселях от верхнего края экрана."),
        u"onslaughtPosX": (u"Позиция по горизонтали (Натиск)",
                           u"ЦЕНТР полосы в ангаре режима «Натиск», в пикселях от левого "
                           u"края экрана. 0 наследует обычную позицию по горизонтали."),
        u"onslaughtPosY": (u"Позиция по вертикали (Натиск)",
                           u"ВЕРХ полосы в ангаре режима «Натиск», в пикселях от верхнего "
                           u"края экрана. 0 наследует обычную позицию по вертикали."),
    },
    u"uk": {
        u"showWhenComplete": (u"Повністю пройдено",
                              u"Залишає смугу на техніці, якій більше нічого досліджувати, "
                              u"модернізувати чи відкривати. Зніміть позначку, щоб ховати смугу "
                              u"на повністю пройденій техніці."),
        u"allowFallthrough": (u"Дозволити резервний режим",
                              u"Якщо увімкнено, смуга пропускає вимкнений режим і показує "
                              u"наступний доступний режим за порядком пріоритету, замість того "
                              u"щоб ховатися. За замовчуванням вимкнено."),
        u"ignoreFreeXp": (u"Ігнорувати вільний досвід",
                          u"У прогрес кожної машини зараховується лише бойовий досвід, здобутий "
                          u"на ній. Вільний досвід не враховується ні в смузі, ні в підсумках, "
                          u"ні в підказках. За замовчуванням вимкнено."),
        u"showTechTree": (u"Дослідження",
                          u"Прогрес у дереві досліджень до модулів і наступної техніки, які "
                          u"залишилося відкрити."),
        u"showSkillTree": (u"Модернізація",
                           u"Розгалужене дерево модернізації на техніці XI рівня."),
        u"showFieldMods": (u"Польова модернізація",
                           u"Етапи польової модернізації, доступні після повного дослідження "
                           u"машини."),
        u"showEliteRewards": (u"Елітні нагороди",
                              u"Ексклюзивна для рівня карта нагород за етапи на престижній "
                              u"техніці."),
        u"showElite": (u"Система «Еліта»",
                       u"Прогрес за діапазонами елітних рівнів на престижній техніці."),
        u"showPotentialTierXI": (u"XI рівень",
                                 u"На танку X рівня без XI рівня, коли він повністю "
                                 u"досліджений і його польову модернізацію завершено, "
                                 u"відслідковує накопичений досвід (досвід машини + вільний "
                                 u"досвід) відносно фіксованої ціни відкриття XI рівня. Замінює "
                                 u"смугу елітних рівнів на таких танках. За замовчуванням "
                                 u"вимкнено."),
        u"scale": (u"Масштаб",
                   u"Задає розмір смуги прогресу на екрані. За замовчуванням зберігає звичайний "
                   u"розмір; Великий майже вдвічі збільшує ширину смуги та збільшує її текст, "
                   u"піктограми й підказку - зручно на екранах із високою роздільною здатністю "
                   u"або віддалених."),
        u"progressMode": (u"Режим прогресу",
                          u"Задає, що показує лічильник досвіду. Поточний показує лише вже "
                          u"здобутий досвід; Поточний / Потрібний показує, скільки у вас є з "
                          u"того, що потрібно смузі."),
        u"showPercent": (u"Показувати прогрес у %",
                         u"Додає відсоток прогресу ліворуч від лічильника досвіду. Працює сам "
                         u"або разом із режимом прогресу. За замовчуванням вимкнено."),
        u"position": (u"Позиція",
                      u"Ctrl+перетягування переміщує смугу в ангарі, або вкажіть нижче точні "
                      u"координати в пікселях. Скидання повертає її на позицію за "
                      u"замовчуванням."),
        u"posX": (u"Позиція по горизонталі",
                  u"ЦЕНТР смуги, у пікселях від лівого краю екрана."),
        u"posY": (u"Позиція по вертикалі",
                  u"ВЕРХ смуги, у пікселях від верхнього краю екрана."),
        u"onslaughtPosX": (u"Позиція по горизонталі (Натиск)",
                           u"ЦЕНТР смуги в ангарі режиму «Натиск», у пікселях від лівого "
                           u"краю екрана. 0 успадковує звичайну позицію по горизонталі."),
        u"onslaughtPosY": (u"Позиція по вертикалі (Натиск)",
                           u"ВЕРХ смуги в ангарі режиму «Натиск», у пікселях від верхнього "
                           u"краю екрана. 0 успадковує звичайну позицію по вертикалі."),
    },
    u"hu": {
        u"showWhenComplete": (u"Teljesen kész",
                              u"A sáv látható marad azokon a harcjárműveken, amelyeken már "
                              u"nincs mit kutatni, korszerűsíteni vagy feloldani. Vedd ki a "
                              u"jelölést, hogy a sáv eltűnjön a teljesen kész "
                              u"harcjárműveken."),
        u"allowFallthrough": (u"Tartalékmód engedélyezése",
                              u"Ha be van kapcsolva, a sáv átugorja a kikapcsolt módot, és a "
                              u"prioritási sorrend szerinti következő elérhető módot jeleníti "
                              u"meg, ahelyett hogy elrejtőzne. Alapértelmezés szerint "
                              u"kikapcsolva."),
        u"ignoreFreeXp": (u"Szabad tapasztalat mellőzése",
                          u"Az egyes harcjárművek haladásába csak a rajtuk szerzett harci "
                          u"tapasztalat számít bele. A szabad tapasztalat kimarad a sávból, az "
                          u"összegzésekből és a súgókból. Alapértelmezés szerint kikapcsolva."),
        u"showTechTree": (u"Kutatás",
                          u"Haladás a kutatási fában a harcjármű hátralévő moduljai és a "
                          u"következő harcjárművek feloldása felé."),
        u"showSkillTree": (u"Korszerűsítés",
                           u"Az elágazó korszerűsítési fa a XI. szintű harcjárműveken."),
        u"showFieldMods": (u"Terepmódosítások",
                           u"A harcjármű teljes kikutatása után feloldódó terepmódosítási "
                           u"szintek."),
        u"showEliteRewards": (u"Elit jutalmak",
                              u"A szintre kizárólagosan jellemző mérföldkő-jutalmak útvonala a "
                              u"presztízs harcjárműveken."),
        u"showElite": (u"Elit rendszer",
                       u"Az elit szintek sávjain végigvezető haladás a presztízs "
                       u"harcjárműveken."),
        u"showPotentialTierXI": (u"XI. szint",
                                 u"Olyan X. szintű harckocsin, amelynek nincs XI. szintje: ha "
                                 u"már teljesen ki van kutatva és a terepmódosításai készen "
                                 u"vannak, a félretett tapasztalatot (harcjármű-tapasztalat + "
                                 u"szabad tapasztalat) követi a XI. szint feloldásának állandó "
                                 u"árához mérve. Ezeken a harckocsikon az elit szintek sávját "
                                 u"váltja fel. Alapértelmezés szerint kikapcsolva."),
        u"scale": (u"Méretezés",
                   u"Beállítja a haladási sáv méretét a képernyőn. Alapértelmezett: a normál "
                   u"méret; Nagy: körülbelül kétszeresére növeli a sáv szélességét, és nagyítja "
                   u"a szövegét, ikonjait és súgóját - hasznos nagy felbontású vagy távoli "
                   u"kijelzőkön."),
        u"progressMode": (u"Haladási mód",
                          u"Beállítja, mit mutat a tapasztalatkijelzés. Jelenlegi: csak az "
                          u"eddig megszerzett tapasztalatot mutatja; Jelenlegi / Szükséges: "
                          u"mennyi van meg abból, amennyi a sávhoz kell."),
        u"showPercent": (u"Haladás megjelenítése %-ban",
                         u"Százalékos haladást tesz a tapasztalatkijelzés bal oldalára. "
                         u"Önmagában és a haladási móddal együtt is működik. Alapértelmezés "
                         u"szerint kikapcsolva."),
        u"position": (u"Pozíció",
                      u"Ctrl+húzással mozgathatod a sávot a garázsban, vagy add meg alább a "
                      u"pontos képpont-koordinátákat. A visszaállítás az alapértelmezett "
                      u"pozícióba teszi."),
        u"posX": (u"Vízszintes pozíció",
                  u"A sáv KÖZEPE, pixelben a képernyő bal szélétől."),
        u"posY": (u"Függőleges pozíció",
                  u"A sáv FELSŐ SZÉLE, pixelben a képernyő felső szélétől."),
        u"onslaughtPosX": (u"Vízszintes pozíció (Roham)",
                           u"A sáv KÖZEPE a Roham hangárban, pixelben a képernyő bal "
                           u"szélétől. A 0 a szokásos vízszintes pozíciót örökli."),
        u"onslaughtPosY": (u"Függőleges pozíció (Roham)",
                           u"A sáv FELSŐ SZÉLE a Roham hangárban, pixelben a képernyő felső "
                           u"szélétől. A 0 a szokásos függőleges pozíciót örökli."),
    },
    u"tr": {
        u"showWhenComplete": (u"Tamamen ilerlemiş",
                              u"Araştırılacak, geliştirilecek veya açılacak bir şeyi kalmayan "
                              u"araçlarda çubuğu görünür tutar. Bir araç tamamen ilerlediğinde "
                              u"çubuğu gizlemek için işareti kaldırın."),
        u"allowFallthrough": (u"Yedek moda izin ver",
                              u"Açıkken, çubuk devre dışı bırakılmış bir modu atlar ve "
                              u"gizlenmek yerine öncelik sırasına göre bir sonraki kullanılabilir "
                              u"modu gösterir. Varsayılan olarak kapalı."),
        u"ignoreFreeXp": (u"Serbest deneyimi yok say",
                          u"Her aracın ilerlemesine yalnızca o araçla kazandığınız savaş "
                          u"deneyimi sayılır. Serbest deneyim çubuğa, toplamlara ve ipuçlarına "
                          u"dahil edilmez. Varsayılan olarak kapalı."),
        u"showTechTree": (u"Araştırma",
                          u"Aracın kalan modülleri ve sonraki araçların açılışına yönelik "
                          u"teknoloji ağacı ilerlemesi."),
        u"showSkillTree": (u"Modernizasyon",
                           u"XI. seviye araçlardaki dallanan modernizasyon ağacı."),
        u"showFieldMods": (u"Saha Modifikasyonları",
                           u"Araç tamamen araştırıldıktan sonra açılan saha modifikasyonu "
                           u"aşamaları."),
        u"showEliteRewards": (u"Elit ödülleri",
                              u"Prestij araçlarındaki, seviyeye özel kilometre taşı ödül yol "
                              u"haritası."),
        u"showElite": (u"Elit Sistemi",
                       u"Prestij araçlarındaki elit seviye aralıklarının ilerlemesi."),
        u"showPotentialTierXI": (u"XI. Seviye",
                                 u"XI. seviyesi olmayan bir X. seviye tankta, tank tamamen "
                                 u"araştırıldığında ve saha modifikasyonları tamamlandığında, "
                                 u"biriktirdiğiniz deneyimi (araç deneyimi + serbest deneyim) "
                                 u"bir XI. seviyenin açılması için gereken sabit fiyata göre "
                                 u"izler. Bu tanklarda elit seviye çubuğunun yerini alır. "
                                 u"Varsayılan olarak kapalı."),
        u"scale": (u"Ölçek",
                   u"İlerleme çubuğunun ekrandaki boyutunu belirler. Varsayılan normal boyutu "
                   u"korur; Büyük çubuğun genişliğini yaklaşık iki katına çıkarır ve metnini, "
                   u"simgelerini ve ipucunu büyütür - yüksek çözünürlüklü veya uzak ekranlarda "
                   u"kullanışlıdır."),
        u"progressMode": (u"İlerleme modu",
                          u"Deneyim göstergesinin ne göstereceğini belirler. Mevcut yalnızca şu "
                          u"ana kadar edindiğiniz deneyimi gösterir; Mevcut / Gerekli ise "
                          u"çubuğun gerektirdiği miktarın ne kadarına sahip olduğunuzu "
                          u"gösterir."),
        u"showPercent": (u"İlerlemeyi % olarak göster",
                         u"Deneyim göstergesinin soluna ilerleme yüzdesi ekler. Tek başına veya "
                         u"İlerleme modu ile birlikte çalışır. Varsayılan olarak kapalı."),
        u"position": (u"Konum",
                      u"Çubuğu garajda taşımak için Ctrl+sürükleyin veya aşağıya tam piksel "
                      u"koordinatlarını girin. Sıfırlama, çubuğu varsayılan konumuna "
                      u"döndürür."),
        u"posX": (u"Yatay konum",
                  u"Çubuğun MERKEZİ, ekranın sol kenarından piksel cinsinden."),
        u"posY": (u"Dikey konum",
                  u"Çubuğun ÜST KENARI, ekranın üst kenarından piksel cinsinden."),
        u"onslaughtPosX": (u"Yatay konum (Hücum)",
                           u"Hücum garajında çubuğun ORTASI, ekranın sol kenarından piksel "
                           u"cinsinden. 0 normal yatay konumu devralır."),
        u"onslaughtPosY": (u"Dikey konum (Hücum)",
                           u"Hücum garajında çubuğun ÜST KENARI, ekranın üst kenarından "
                           u"piksel cinsinden. 0 normal dikey konumu devralır."),
    },
}


def render_panel(wg_labels, lang=None):
    """The full rendered panel text: ``{key: {"text", "tooltip"}}`` for every control
    (PURE given ``wg_labels`` + ``lang``).

    ``text`` (the LABEL) is localized: per-mode checkboxes take WG's own localized name
    from ``wg_labels`` (== ``i18n.widget_labels()``), everything else from the ``_LABELS``
    tables (English-fallback, marked on fallback). ``tooltip`` is localized the same way
    from ``_TOOLTIPS`` (English-fallback PER KEY, never marked -- an underscore in front of
    ``{HEADER}`` would break WG's tooltip markup, and tests/test_settings_i18n.py guards the
    only real leak risk: a language block missing a key) and is OMITTED for the three category
    headers, which have no entry there. The ``SPACER`` sentinel names no control, so skipped
    outright (it has no _LABELS row and would KeyError on the English fallback).
    ``lang`` defaults to the client's language.

    The three ``HEADER_KEYS`` come out wrapped in ``<b>...</b>`` (MSA Labels render HTML).
    The wrap happens HERE and ONLY here -- never in the _LABELS tables (translation data
    stays markup-free) and never in ``mod_settings._template()``. Both consumers of this
    function must see the SAME string: _template() builds the fresh template from it, and
    _sync_template_text() compares a STORED component's text against it. If _template()
    wrapped independently, every init would see a mismatch, strip the bold back out, and
    fire a pointless saveState() -- so one source of truth makes that divergence
    impossible by construction."""
    if lang is None:
        lang = client_language()
    code = _norm(lang)
    labels = _LABELS.get(code) or {}
    en_labels = _LABELS[DEFAULT_LANGUAGE]
    tips = _TOOLTIPS.get(code) or {}
    en_tips = _TOOLTIPS[DEFAULT_LANGUAGE]
    wl = wg_labels or {}
    out = {}
    for key in COL1_KEYS + COL2_KEYS:
        if key is SPACER:
            continue
        if key in FEATURE_WG:
            text = wl.get(FEATURE_WG[key]) or _FEATURE_EN[key]   # WG label; i18n self-marks
        else:
            fb = key not in labels
            text = en_labels[key] if fb else labels[key]
            if fb:
                text = i18n._mark(text)
        if key in HEADER_KEYS:
            # Bold AFTER the fallback mark, so a marked fallback stays visible inside it.
            text = u"<b>%s</b>" % text
        out[key] = {u"text": text}
        # Per-KEY English fallback, same policy as the labels: a language that hasn't
        # translated one tooltip still renders the other fourteen in its own words.
        tip = tips.get(key) or en_tips.get(key)
        if tip is not None:
            out[key][u"tooltip"] = u"{HEADER}%s{/HEADER}{BODY}%s{/BODY}" % tip
        # The two radio groups also carry their localized option labels (see _template()).
        if key == u"scale":
            out[key][u"options"] = _scale_options(code)
        elif key == u"progressMode":
            out[key][u"options"] = _progress_options(code)
    return out


def label(key, lang=None):
    """ONE mod-invented label in the client language -- the same resolution
    ``render_panel`` does for a non-feature control (English master, marked on fallback).
    Exposed because the WIDGET needs one of these strings too: "Fully Progressed"
    (``showWhenComplete``) is also the COMPLETE bar's header, and the game ships no
    equivalent, so ``i18n.headerComplete`` reuses this table instead of duplicating the
    translations. Pure given ``lang``."""
    code = _norm(lang if lang is not None else client_language())
    labels = _LABELS.get(code) or {}
    if key in labels:
        return labels[key]
    return i18n._mark(_LABELS[DEFAULT_LANGUAGE].get(key, u""))


def _scale_options(code):
    """The localized scale radio-group option labels ``[Default, Large]`` for language
    ``code`` (English fallback, marked on fallback -- same policy as the mod-invented
    labels). ``code`` is already a normalized ``_norm()`` key."""
    fb = code not in _SCALE_OPTIONS
    opts = _SCALE_OPTIONS[DEFAULT_LANGUAGE] if fb else _SCALE_OPTIONS[code]
    if fb:
        return [i18n._mark(o) for o in opts]
    return list(opts)


def _progress_options(code):
    """The localized progressMode radio-group option labels ``[Current, Current / Required]``
    for language ``code`` (English fallback, marked on fallback -- same policy as
    _scale_options). ``code`` is already a normalized ``_norm()`` key."""
    fb = code not in _PROGRESS_OPTIONS
    opts = _PROGRESS_OPTIONS[DEFAULT_LANGUAGE] if fb else _PROGRESS_OPTIONS[code]
    if fb:
        return [i18n._mark(o) for o in opts]
    return list(opts)


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
