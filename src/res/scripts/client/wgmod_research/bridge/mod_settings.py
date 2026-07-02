# -*- coding: utf-8 -*-
"""User settings, surfaced through ModsSettingsAPI (the community settings panel).

ModsSettingsAPI (izeberg.modssettingsapi, also shipped by Aslain's modpack) is an
OPTIONAL dependency: we import it guarded, and if it's absent the bar simply uses
the defaults (shown everywhere) with no settings panel -- never a crash. MSA owns
persistence, so there's no config file of our own.

Two independent "hide" checkboxes, both default OFF (bar shown):
- hideAlways       -- hide the whole widget on every vehicle (master switch).
- hideWhenComplete -- hide only on fully-progressed (Mode.COMPLETE) vehicles.

Plus five per-mode "show" checkboxes, all default ON, one per bar mode
(showTechTree / showSkillTree / showFieldMods / showEliteRewards / showElite).
enabled_modes() turns these into the set of enabled Mode strings that build_model
consumes: a vehicle whose resolved mode is off hides the bar (no fall-through).

Plus a draggable bar position, stored as two on-screen PIXEL coordinates:
- posX -- the bar's CENTER-x in px (matches the CSS translateX(-50%) center-anchor).
- posY -- the bar's TOP in px.
Both default to 0, which means "auto" -- the bar keeps its CSS default position
(centered, 17.6vh) and the widget JS seeds these fields once from the live layout so
the numeric inputs always show real coordinates. Pixels have no resolution-independent
default, so resetting just writes 0/0 back (re-seeds at the current resolution).
The position round-trips 1:1: JS reports a dragged position via the `setPosition`
command (see gameface_bridge) -> set_position() persists it here and re-pushes.

Reset uses the settings panel's OWN "reset to defaults" button (Aslain's per-mod
reset), which fires the api's `onResetMod` event -- NOT `onSettingsChanged`. So we
subscribe to onResetMod (_on_reset) and reset the position to auto there. There is no
custom reset control: a control-attached button never fires in Aslain's panel, and a
checkbox is poor UX for a momentary action.

The visibility decision itself is the engine-free `builder.bar_visible`; this module
only owns the settings storage + the live-apply on change.
"""
from debug_utils import LOG_CURRENT_EXCEPTION, LOG_NOTE

from wgmod_research.adapter import i18n

# Our mod's reverse-domain id, reused as the MSA "linkage" (panel identity / storage key).
LINKAGE = "com.14th_ua.garageprogressbar"

# Sanity ceiling for a stored pixel coordinate (well past any real screen size); a
# typed/echoed value is clamped into [0, POS_MAX], with 0 meaning "auto / unseeded".
POS_MAX = 20000

DEFAULTS = {"hideAlways": False, "hideWhenComplete": False, "posX": 0, "posY": 0,
            # Per-mode toggles, all default True (every mode shown). When a mode is
            # off, a vehicle that resolves to it hides the bar -- no fall-through
            # (see domain.builder.build_model / enabled_modes below).
            "showTechTree": True, "showSkillTree": True, "showFieldMods": True,
            "showEliteRewards": True, "showElite": True}


def clamp_pos(v):
    """Coerce a position coordinate to an int in [0, POS_MAX]. 0 = auto/unseeded.
    Pure + engine-free (unit-tested); non-numeric / negative -> 0."""
    try:
        v = int(v)
    except (TypeError, ValueError):
        return 0
    if v < 0:
        return 0
    if v > POS_MAX:
        return POS_MAX
    return v

# Current effective settings. Starts at defaults so accessors are always safe to call,
# even before init() runs or when MSA is absent.
_settings = dict(DEFAULTS)

# True once we've successfully registered with MSA. Kept so init() is idempotent AND
# self-healing: a failed attempt (MSA not loaded yet at our import time) leaves this
# False, so a later init() call (first hangar mount) retries until it sticks.
_registered = False


def _template():
    """The MSA panel descriptor. Two hide checkboxes (both default False so a fresh
    install shows the bar everywhere) plus the draggable-position fields: two numeric
    px steppers. The steppers show 0 until the widget seeds them from the live layout on
    the first hangar mount. Reset is the panel's own per-mod reset button (see _on_reset),
    so there is no custom reset control here."""
    return _mark_untranslated({
        "modDisplayName": "Garage Progress Bar",
        "enabled": True,
        # settingsVersion lets the panel preserve the user's saved values across cosmetic
        # template edits (tooltip/label tweaks): with it set, the host only wipes stored
        # settings to defaults when this number is BUMPED. Bump it whenever the set of
        # varNames / control layout changes (not for text-only edits). Verified against
        # the Aslain 1.3.2 + izeberg 1.7.0 compareTemplates bytecode.
        "settingsVersion": 2,
        "column1": [
            {
                "type": "CheckBox",
                "text": "Hide the bar completely",
                "value": DEFAULTS["hideAlways"],
                "tooltip": ("{HEADER}Hide the bar completely{/HEADER}"
                            "{BODY}Hides the progress bar on every vehicle.{/BODY}"),
                "varName": "hideAlways",
            },
            {
                "type": "CheckBox",
                "text": "Hide when fully progressed",
                "value": DEFAULTS["hideWhenComplete"],
                "tooltip": ("{HEADER}Hide when fully progressed{/HEADER}"
                            "{BODY}Hides the bar only on vehicles with nothing left "
                            "to research, upgrade, or unlock.{/BODY}"),
                "varName": "hideWhenComplete",
            },
            {
                "type": "Label",
                "text": "Bar modes",
                "tooltip": ("{HEADER}Bar modes{/HEADER}"
                            "{BODY}Turn off the bar modes you don't care about. When a "
                            "vehicle's progress falls under a mode you've hidden, the bar "
                            "is hidden for it (it does not switch to another mode).{/BODY}"),
            },
            {
                "type": "CheckBox",
                "text": "Show research (tech tree)",
                "value": DEFAULTS["showTechTree"],
                "tooltip": ("{HEADER}Show research{/HEADER}"
                            "{BODY}The tech-tree progress toward the vehicle's remaining "
                            "module and next-vehicle unlocks.{/BODY}"),
                "varName": "showTechTree",
            },
            {
                "type": "CheckBox",
                "text": "Show tier-XI upgrades",
                "value": DEFAULTS["showSkillTree"],
                "tooltip": ("{HEADER}Show tier-XI upgrades{/HEADER}"
                            "{BODY}The branching upgrade (skill) tree on tier-XI "
                            "vehicles.{/BODY}"),
                "varName": "showSkillTree",
            },
            {
                "type": "CheckBox",
                "text": "Show field modifications",
                "value": DEFAULTS["showFieldMods"],
                "tooltip": ("{HEADER}Show field modifications{/HEADER}"
                            "{BODY}The field-modification steps unlocked once the vehicle "
                            "is fully researched.{/BODY}"),
                "varName": "showFieldMods",
            },
            {
                "type": "CheckBox",
                "text": "Show Elite rewards",
                "value": DEFAULTS["showEliteRewards"],
                "tooltip": ("{HEADER}Show Elite rewards{/HEADER}"
                            "{BODY}The tier-exclusive milestone-reward roadmap on prestige "
                            "vehicles.{/BODY}"),
                "varName": "showEliteRewards",
            },
            {
                "type": "CheckBox",
                "text": "Show Elite progression",
                "value": DEFAULTS["showElite"],
                "tooltip": ("{HEADER}Show Elite progression{/HEADER}"
                            "{BODY}The Elite-Levels grade-band progression on prestige "
                            "vehicles.{/BODY}"),
                "varName": "showElite",
            },
        ],
        "column2": [
            {
                "type": "Label",
                "text": "Bar position (px)",
                "tooltip": ("{HEADER}Bar position{/HEADER}"
                            "{BODY}Ctrl+drag the bar in the garage to move it, or type "
                            "exact on-screen pixel coordinates below. Reset returns it "
                            "to the default position.{/BODY}"),
            },
            {
                "type": "NumericStepper",
                "text": _POSX_LABEL,
                "value": DEFAULTS["posX"],
                "minimum": 0,
                "maximum": POS_MAX,
                "snapInterval": 1,
                "canManualInput": True,
                "tooltip": ("{HEADER}Horizontal position{/HEADER}"
                            "{BODY}The bar's CENTER, in pixels from the left screen "
                            "edge.{/BODY}"),
                "varName": "posX",
            },
            {
                "type": "NumericStepper",
                "text": _POSY_LABEL,
                "value": DEFAULTS["posY"],
                "minimum": 0,
                "maximum": POS_MAX,
                "snapInterval": 1,
                "canManualInput": True,
                "tooltip": ("{HEADER}Vertical position{/HEADER}"
                            "{BODY}The bar's TOP, in pixels from the top screen "
                            "edge.{/BODY}"),
                "varName": "posY",
            },
        ],
    })


def _mark_untranslated(tpl):
    """DIAGNOSTIC: the whole settings panel is intentionally English (mod-invented
    prose with no in-game equivalent), so -- when i18n.MARK_UNTRANSLATED is on -- prefix
    every visible label/tooltip with an underscore, matching the widget's convention for
    untranslated text. The brand `modDisplayName` is left as-is. No-op when the flag is
    off; flip it (in i18n) to clear these before shipping."""
    if not i18n.MARK_UNTRANSLATED:
        return tpl
    for col in ("column1", "column2"):
        for entry in tpl.get(col, ()):
            if entry.get("text"):
                entry["text"] = i18n._mark(entry["text"])
            if entry.get("tooltip"):
                entry["tooltip"] = i18n._mark(entry["tooltip"])
    return tpl


def _apply(settings):
    """Merge an MSA settings dict into our cache, ignoring unknown/missing keys.
    Per-key typed: the hide flags are bools, the position fields are clamped ints."""
    if not settings:
        return
    for key in DEFAULTS:
        if key not in settings:
            continue
        if key in ("posX", "posY"):
            _settings[key] = clamp_pos(settings[key])
        else:
            _settings[key] = bool(settings[key])


def init():
    """Register (or re-load) our settings panel with ModsSettingsAPI.

    Idempotent and self-healing: a no-op once registered; otherwise re-attempts.
    MSA may load after us at startup, so the import can fail on the first call from
    the entry point -- we then retry on the first hangar mount (attach()), by which
    point every mod is loaded. Guarded so it never raises into the mount path."""
    global _registered
    if _registered:
        return
    try:
        from gui.modsSettingsApi import g_modsSettingsApi
    except ImportError:
        LOG_NOTE("[wgmod] ModsSettingsAPI not present -- using default visibility "
                 "(bar shown, no settings panel)")
        return
    try:
        template = _template()
        saved = g_modsSettingsApi.getModSettings(LINKAGE, template)
        if saved:
            _apply(saved)
            g_modsSettingsApi.registerCallback(LINKAGE, _on_changed)
            # Repair a settings dict missing the host-managed 'enabled' key. An earlier
            # build wrote a partial dict via updateModSettings that dropped it, which
            # made Aslain's panel renderer KeyError and blank every mod's settings. This
            # is a no-op for a healthy install (which always has 'enabled').
            if "enabled" not in saved:
                g_modsSettingsApi.updateModSettings(
                    LINKAGE, _full_settings_for_write(g_modsSettingsApi))
                try:
                    g_modsSettingsApi.saveState()
                except Exception:
                    LOG_CURRENT_EXCEPTION()
                LOG_NOTE("[wgmod] repaired settings (re-added 'enabled')")
        else:
            _apply(g_modsSettingsApi.setModTemplate(LINKAGE, template, _on_changed))
        # Wire the panel's "reset to defaults" button. It fires onResetMod (NOT
        # onSettingsChanged), on whichever api actually stores this client's settings.
        # Verified live: with Aslain installed our data lives in Aslain's api
        # (gui.aslainMenu.g_modsSettingsApi) -- a SEPARATE object from the izeberg api we
        # import here, and the one that has onResetMod. So subscribe on BOTH (de-duped,
        # guarded); pure-izeberg installs simply skip the one without onResetMod.
        _subscribe_reset(g_modsSettingsApi)
        try:
            from gui.aslainMenu import g_modsSettingsApi as _aslain_api
            _subscribe_reset(_aslain_api)
        except Exception:
            pass
        # Label the position steppers with the stored default coords (from a prior seed) so
        # the panel shows the default target even when this session won't re-seed (the seed
        # only fires when the position is auto; a saved custom position skips it).
        _dx, _dy = _stored_default()
        if _dx and _dy:
            for _api in _candidate_apis():
                _label_defaults(_api, _dx, _dy)
        _registered = True
        LOG_NOTE("[wgmod] ModsSettingsAPI registered: %s" % (_settings,))
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_changed(linkage, new_settings):
    """MSA callback when the user changes a setting. Update the cache and re-push the bar
    so the change applies live (refresh re-evaluates visibility)."""
    try:
        _apply(new_settings)
        LOG_NOTE("[wgmod] settings changed: %s" % (_settings,))
        # Lazy import to avoid an import cycle (the bridge imports this module).
        from wgmod_research.bridge import gameface_bridge as B
        B.refresh()
    except Exception:
        LOG_CURRENT_EXCEPTION()


# Object ids of api instances we've already hooked onResetMod on, so init() retries
# (entry point + every hangar mount) never stack duplicate handlers.
_reset_hooked = set()


def _subscribe_reset(api):
    """Subscribe _on_reset to an api's onResetMod event (the panel 'reset to defaults'
    button), de-duped by object id. No-op if the api lacks onResetMod (pure izeberg) or is
    already hooked. Guarded so a settings-API shape change can't break registration."""
    try:
        if api is None or not hasattr(api, "onResetMod"):
            return
        if id(api) in _reset_hooked:
            return
        api.onResetMod += _on_reset
        _reset_hooked.add(id(api))
        LOG_NOTE("[wgmod] onResetMod hooked on %s" % (type(api).__module__,))
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _candidate_apis():
    """The settings-api instance(s) this client exposes. With Aslain installed there are
    TWO separate objects (izeberg's gui.modsSettingsApi + Aslain's gui.aslainMenu), and our
    data/defaults live in Aslain's; on a plain install there's just izeberg's. Return
    whichever import(s) succeed so callers can act on all of them, de-duped."""
    apis = []
    try:
        from gui.modsSettingsApi import g_modsSettingsApi as a
        apis.append(a)
    except Exception:
        pass
    try:
        from gui.aslainMenu import g_modsSettingsApi as b
        if b not in apis:
            apis.append(b)
    except Exception:
        pass
    return apis


def _store_default_position(x, y):
    """Record the widget-measured DEFAULT position (px) as the host's stored 'defaults' for
    our mod, so the panel's reset button repaints the X/Y fields to the real default spot
    (centered, near the top) instead of a meaningless 0/0. The widget reports this via the
    `setPosition` seed (fired while the bar sits at its CSS default), see set_position.
    Touches state['defaults'] directly (no public API); guarded, all candidate apis."""
    x = clamp_pos(x)
    y = clamp_pos(y)
    for api in _candidate_apis():
        try:
            defaults = (getattr(api, "state", None) or {}).get("defaults", {}).get(LINKAGE)
            if isinstance(defaults, dict) and (defaults.get("posX") != x or
                                               defaults.get("posY") != y):
                defaults["posX"] = x
                defaults["posY"] = y
                if hasattr(api, "saveState"):
                    api.saveState()
                LOG_NOTE("[wgmod] stored default position for reset: %s,%s" % (x, y))
            _label_defaults(api, x, y)   # show the default in the stepper labels
        except Exception:
            LOG_CURRENT_EXCEPTION()


def _stored_default():
    """The widget-measured default position (px) previously recorded by the seed, read from
    the first candidate api that has it. (None, None) if not seeded yet."""
    for api in _candidate_apis():
        try:
            d = (getattr(api, "state", None) or {}).get("defaults", {}).get(LINKAGE)
            if isinstance(d, dict) and d.get("posX") and d.get("posY"):
                return int(d["posX"]), int(d["posY"])
        except Exception:
            LOG_CURRENT_EXCEPTION()
    return None, None


# Base labels for the position steppers; _label_defaults() appends the default coords once
# the widget has reported them, so the panel reads e.g. "Horizontal (center X) — default 1920".
_POSX_LABEL = "Horizontal (center X)"
_POSY_LABEL = "Vertical (top Y)"


def _label_defaults(api, dx, dy):
    """Show the DEFAULT position in the stepper labels (so the panel displays the reset
    target, not the currently-applied value). Patches the stored template's posX/posY label
    text in place -- the panel deep-copies the template on each open, so the new label shows
    next time it's opened. Guarded; no-op if the template/coords aren't available."""
    if not dx or not dy:
        return
    try:
        tmpl = (getattr(api, "state", None) or {}).get("templates", {}).get(LINKAGE)
        if not isinstance(tmpl, dict):
            return
        # Marked untranslated (underscore) to match the rest of the English-only panel.
        wanted = {"posX": i18n._mark("%s — default %d" % (_POSX_LABEL, dx)),
                  "posY": i18n._mark("%s — default %d" % (_POSY_LABEL, dy))}
        changed = False
        for col in ("column1", "column2"):
            for comp in tmpl.get(col, []) or []:
                if isinstance(comp, dict) and comp.get("varName") in wanted:
                    new_text = wanted[comp["varName"]]
                    if comp.get("text") != new_text:
                        comp["text"] = new_text
                        changed = True
        if changed and hasattr(api, "saveState"):
            api.saveState()
            LOG_NOTE("[wgmod] labelled position steppers with defaults %d,%d" % (dx, dy))
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_reset(linkage, defaults):
    """Panel 'reset to defaults' button. The settings host fires onResetMod (NOT
    onSettingsChanged) when the user resets a mod, so this hook is what makes the reset
    button move our bar. `defaults` is the host's stored snapshot, which -- thanks to the
    seed (see _store_default_position) -- carries the real default position px, so we just
    apply it: posX/posY jump to the default spot and the bar follows. Fallback: if the
    snapshot predates the seed (no posX/posY yet), drop to auto (0/0) so the widget
    re-seeds. Guarded + linkage-scoped (the event is global across every mod)."""
    try:
        if linkage != LINKAGE:
            return
        _apply(defaults if defaults else DEFAULTS)
        if not defaults or "posX" not in defaults or "posY" not in defaults:
            _settings["posX"] = 0   # not seeded yet -> auto; widget re-seeds to default
            _settings["posY"] = 0
        LOG_NOTE("[wgmod] onResetMod -> position reset: %s" % (_settings,))
        from wgmod_research.bridge import gameface_bridge as B
        B.refresh()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _full_settings_for_write(g_modsSettingsApi):
    """Build the COMPLETE settings dict to hand to updateModSettings.

    updateModSettings *replaces* the whole stored per-linkage dict (verified against the
    MSA 1.7.0 AND Aslain 1.3.2 bytecode), so a partial dict silently drops keys the
    settings host owns -- notably Aslain's per-mod 'enabled' toggle, which its renderer
    indexes as settings['enabled'] (a missing key KeyErrors and blanks the ENTIRE panel,
    every mod). So we start from the currently-stored settings (preserving 'enabled' and
    any other host keys), guarantee 'enabled' exists (default True), then overlay our own
    varNames (the hide flags + posX/posY)."""
    data = {}
    try:
        current = g_modsSettingsApi.getModSettings(LINKAGE, _template())
        if current:
            data = dict(current)
    except Exception:
        LOG_CURRENT_EXCEPTION()
    data.setdefault("enabled", True)   # host-managed per-mod toggle; never drop it
    data.update(_settings)             # our varNames (hide flags, posX/posY, resetPos)
    return data


def set_position(x, y, is_default=False):
    """Persist a new bar position (px) and re-push it to the widget. Called from the JS
    `setPosition` reverse command. `is_default` is True for the widget's SEED -- the px it
    measures while the bar sits at its CSS default (fired on first mount and after a reset);
    that value is also recorded as the host's reset 'defaults' (see _store_default_position)
    so the reset button repaints the fields to the real default spot, not 0/0. A normal drag
    passes is_default=False (updates the current position only).

    Writes the FULL settings through ModsSettingsAPI so the panel's numeric fields track the
    position; guarded so a missing/broken MSA never breaks the bar. updateModSettings only
    mutates in-memory state, so saveState() flushes it to disk (survives a client restart)."""
    x = clamp_pos(x)
    y = clamp_pos(y)
    _settings["posX"] = x
    _settings["posY"] = y
    try:
        from gui.modsSettingsApi import g_modsSettingsApi
        g_modsSettingsApi.updateModSettings(LINKAGE, _full_settings_for_write(g_modsSettingsApi))
        try:
            g_modsSettingsApi.saveState()
        except Exception:
            LOG_CURRENT_EXCEPTION()
    except ImportError:
        pass  # MSA absent -> position still applies this session, just not persisted
    except Exception:
        LOG_CURRENT_EXCEPTION()
    if is_default:
        _store_default_position(x, y)
    # Re-push so the (echoed) position reaches the widget immediately, even without MSA.
    try:
        from wgmod_research.bridge import gameface_bridge as B
        B.refresh()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def hide_always():
    return _settings["hideAlways"]


def hide_when_complete():
    return _settings["hideWhenComplete"]


def pos_x():
    return _settings["posX"]


def pos_y():
    return _settings["posY"]


def enabled_modes():
    """The set of bar Mode strings the user has left ON, for domain.builder.build_model
    (a vehicle whose resolved mode is absent hides the bar -- no fall-through). COMPLETE
    is never toggleable here (it's the genuine end-state, governed by hideWhenComplete)."""
    from wgmod_research.domain import types as t
    modes = set()
    if _settings["showTechTree"]:
        modes.add(t.Mode.TECH_TREE)
    if _settings["showSkillTree"]:
        modes.add(t.Mode.SKILL_TREE)
    if _settings["showFieldMods"]:
        modes.add(t.Mode.FIELD_MODS)
    if _settings["showEliteRewards"]:
        modes.add(t.Mode.ELITE_REWARDS)
    if _settings["showElite"]:
        modes.add(t.Mode.ELITE)
    return modes
