# -*- coding: utf-8 -*-
"""Localize the mod's OWN text through the game's own resource strings.

WoT's ``gui.impl.backport.text(resId)`` returns a string in the client's *active*
language, so mapping each mod-owned label to an existing WG resource id makes it
follow the player's language with **zero translation tables** -- a Ukrainian client
shows Ukrainian, a German client German, etc. (Game-provided data -- skill/field-mod
names, KPI effect text, prerequisite names -- is already localized this way in
``engine_adapter``; this module covers the labels the mod itself invents.)

Live-only, like the rest of the adapter: ``backport``/``R`` are imported lazily and
every lookup is wrapped so a missing or renamed id degrades to the English fallback
(today's text) instead of blanking the bar or raising into the widget.

Only labels with a **confirmed** matching WG resource are wired to an accessor below.
The rest keep an English-only fallback -- either the game has no equivalent (by
design: see the widget's mod-invented captions) or the id is not yet confirmed. The
resolver never guesses: an unwired key is simply English until its id is verified via
the debug REPL and added here.
"""
from debug_utils import LOG_CURRENT_EXCEPTION

# DIAGNOSTIC: prefix any text that is NOT localized (an English fallback -- because the
# game has no equivalent, an id isn't confirmed yet, or a lookup failed) with an
# underscore, so it's obvious in-client which text still leaks English. Off for ship;
# flip to True to audit for English leaks after a change.
MARK_UNTRANSLATED = False


def _mark(s):
    """Tag an untranslated (English-fallback) string so it stands out in-client."""
    return (u"_" + s) if (MARK_UNTRANSLATED and s) else s


def _cap_first(s):
    """Uppercase only the FIRST character (language-safe: unlike str.capitalize() it
    doesn't lowercase the rest, and it's a no-op on scripts without case)."""
    return (s[:1].upper() + s[1:]) if s else s


def _text(accessor, fallback):
    """Localized text for ``accessor`` (a 0-arg callable returning a resource id from
    ``R.strings``), or the (underscore-marked) ``fallback`` on any failure. ``accessor``
    is a *thunk* so a missing/renamed ``R`` path fails INSIDE the guard (degrading to
    English) rather than at the call site -- the same fail-safe posture as the
    engine_adapter reads."""
    try:
        from gui.impl import backport
        return backport.text(accessor()) or _mark(fallback)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return _mark(fallback)


# English fallbacks for every mod-owned widget label. Also the value SHOWN when the
# game has no equivalent string (keys with no accessor in widget_labels(), by design).
_FALLBACK = {
    # Bar headers (per mode).
    "headerResearch": u"Research",
    "headerFieldMods": u"Field Modifications",
    "headerSkillTree": u"Upgrades",
    "headerElite": u"Elite System",
    "headerEliteRewards": u"Elite Rewards",
    # Tooltip type captions.
    "capFieldMod": u"Field Modification",
    "capEliteLevel": u"Elite Levels",
    # Tooltip status / row labels.
    "requires": u"Required:",
    "prereqNotMet": u"Prerequisites not met",
    # Field-mod choice-variant separator ("... or ...").
    "sepOr": u"or",
}

# Keys with NO wired accessor -- always English. Marked untranslated in the bundle so
# they're spottable in-client. (Currently none: every visible label is wired below.)
_ENGLISH_ONLY = ()


def widget_labels():
    """The resolved label bundle handed to the widget JS via the ``labels`` VM field.

    Keys with a confirmed WG resource are localized to the client's language; the rest
    stay English (the game has no equivalent, or the id is not yet confirmed) and are
    underscore-marked (see MARK_UNTRANSLATED). Returns plain ``unicode`` values --
    json.dumps in the bridge escapes non-ASCII for JS."""
    out = dict(_FALLBACK)
    for k in _ENGLISH_ONLY:
        out[k] = _mark(out[k])

    # Each label resolves INDEPENDENTLY: the full R.strings traversal lives inside the
    # thunk so _text catches a wrong/absent path and degrades just that one label to its
    # (marked) English fallback -- never raising out of here and aborting the push.
    def _S():
        from gui.impl.gen import R
        return R.strings

    # Bar-mode headers -> the game's OWN feature titles (all confirmed live):
    #  tech-tree "Research"       = veh_skill_tree.footer.button.label
    #  field-mods "Field Modification" = veh_post_progression.tooltips.entry_point.header
    #  tier-XI "Upgrades"         = veh_skill_tree.intro.progression.title
    #  elite "Elite System"       = prestige.entryPoint.header
    #  elite rewards "Elite Rewards" = veh_skill_tree.intro.vanity.title
    out["headerResearch"] = _text(
        lambda: _S().veh_skill_tree.footer.button.label(), _FALLBACK["headerResearch"])
    out["headerFieldMods"] = _text(
        lambda: _S().veh_post_progression.tooltips.entry_point.header(), _FALLBACK["headerFieldMods"])
    out["headerSkillTree"] = _text(
        lambda: _S().veh_skill_tree.intro.progression.title(), _FALLBACK["headerSkillTree"])
    out["headerElite"] = _text(
        lambda: _S().prestige.entryPoint.header(), _FALLBACK["headerElite"])
    out["headerEliteRewards"] = _text(
        lambda: _S().veh_skill_tree.intro.vanity.title(), _FALLBACK["headerEliteRewards"])
    # Field-mod per-tick caption reuses the field-mods header (its roman numeral already
    # rides the hexagon glyph, so it's not repeated in the caption).
    out["capFieldMod"] = out["headerFieldMods"]
    # Elite tick caption -> the game's "Elite Levels" label; JS appends the level number.
    out["capEliteLevel"] = _text(
        lambda: _S().prestige.tooltip.grades.header(), _FALLBACK["capEliteLevel"])
    # Locked-prerequisite label -> the game's own "required:" (the prereq NAMES are
    # already localized game item names). Capitalized to open a tooltip line.
    out["requires"] = _cap_first(_text(
        lambda: _S().veh_post_progression.tooltips.priceBlock.notEnough(), _FALLBACK["requires"]))
    # Locked tick with no readable prereq names -> the game's own "must research the
    # prerequisites first" sentence (skill-tree wording, but the right meaning).
    out["prereqNotMet"] = _text(
        lambda: _S().veh_skill_tree.tooltips.large.perksResearchRequired(), _FALLBACK["prereqNotMet"])
    # The localized "or" the game itself puts between mutually exclusive choices.
    out["sepOr"] = _text(
        lambda: _S().tooltips.vehicle.textDelimiter.c_or(), _FALLBACK["sepOr"])

    # NOT YET WIRED (left English): headerComplete, headerElite, headerEliteRewards,
    # requires. No WG resource confirmed for these; confirm rendered text via the debug
    # REPL, then add an accessor here. Candidate leads to probe:
    #   veh_skill_tree.footer.description.text.allResearched  (id 59197)
    #   prestige.profile.header / prestige.entryPoint.header / prestige.prestigeRewardView.title.*
    return out


def skilltree_category(cat_key):
    """Localized skill-node sub-heading = the game's OWN perk category for the node
    (from action.getCategories(), a single key). Maps 1:1 to
    veh_skill_tree.tooltips.perk.category.<key>:
      firepower/survivability/mobility/spotting/concealment -> "Category: <X>",
      mechanics -> "Mechanic Upgrade", special -> "Special Upgrade".
    Empty key or an unresolved category -> "" (the caller then shows the localized
    "Upgrades" section label instead of a bare English word)."""
    if not cat_key:
        return u""

    def _acc():
        from gui.impl.gen import R
        return getattr(R.strings.veh_skill_tree.tooltips.perk.category, cat_key)()

    return _text(_acc, u"")


def tier_label(roman):
    """"Tier IX" in the client language: the game's own "Tier" name label
    (``tooltips.vehicle.level``) followed by the language-neutral roman numeral. Empty
    roman -> empty caption (no tier to show)."""
    if not roman:
        return u""

    def _acc():
        from gui.impl.gen import R
        return R.strings.tooltips.vehicle.level()

    return _text(_acc, u"Tier") + u" " + roman
