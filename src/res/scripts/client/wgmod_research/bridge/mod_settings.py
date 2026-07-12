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
(centered, 17.6vh, resolution-relative). posX/posY stay 0 until the user actually
DRAGS the bar (or edits a stepper): a real drag pins the chosen px, but the widget's
one-time SEED does NOT (is_default=True in set_position) -- it only feeds the panel's
"default N" stepper label. This is deliberate: pixels have no resolution-independent
meaning, so persisting the seeded px would freeze one resolution's layout and the bar
would drift off-header after any resolution change. Leaving posX/posY at 0 keeps the
CSS default live, so it re-derives correctly at every resolution. Reset returns to auto.
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
from wgmod_research._compat import LOG_CURRENT_EXCEPTION, LOG_NOTE
from wgmod_research.adapter import settings_i18n

# Our mod's reverse-domain id, reused as the MSA "linkage" (panel identity / storage key).
LINKAGE = "com.14th_ua.garageprogressbar"

# 2/3-safe string check (basestring on Py2.7 in-game; str under a Py3 import).
try:
    _STR_TYPES = basestring
except NameError:
    _STR_TYPES = str

# Sanity ceiling for a stored pixel coordinate (well past any real screen size); a
# typed/echoed value is clamped into [0, POS_MAX], with 0 meaning "auto / unseeded".
POS_MAX = 20000

DEFAULTS = {"hideAlways": False, "hideWhenComplete": False, "posX": 0, "posY": 0,
            # Viewport (px) a custom posX/posY was captured at, so the widget can rescale
            # the pinned position proportionally after a resolution / UI-scale change (see
            # applyPosition in WGModResearch.js). 0 = unknown (auto position, or a pre-fix
            # saved pin -- the widget then adopts the current viewport on first sight).
            # Not user-facing (no stepper); written only via set_position.
            "posW": 0, "posH": 0,
            # Per-mode toggles, all default True (every mode shown). When a mode is
            # off, a vehicle that resolves to it hides the bar -- no fall-through
            # (see domain.builder.build_model / enabled_modes below).
            "showTechTree": True, "showSkillTree": True, "showFieldMods": True,
            "showEliteRewards": True, "showElite": True,
            # Speculative "potential Tier XI" mode -- opt-in (default off): on a tier-X
            # tank with no real tier XI, tracks banked XP toward a hypothetical one and
            # REPLACES the Elite-Levels bar. Unlike the toggles above, off does not hide
            # the bar -- it falls through to the normal Elite/COMPLETE behavior.
            "showPotentialTierXI": False,
            # Per-vehicle "mode switch" selection: a JSON-string map {intCD: Mode} of the
            # non-default mode the player picked in the header switch for each vehicle. Not
            # a user-facing control (absent from _template, so no settingsVersion bump), but
            # persisted like posW/posH via _full_settings_for_write + saveState. Honored by
            # build_model only while the chosen mode is still available (self-healing).
            "modeOverrides": "{}"}


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
    so there is no custom reset control here.

    Every visible label/tooltip is pulled from settings_i18n.panel_text() at the CLIENT's
    active language (English fallback per key). The control STRUCTURE (types, varNames,
    values, min/max, settingsVersion) is language-independent and unchanged; only text
    follows the language. `modDisplayName` stays the literal English brand."""
    t = settings_i18n.panel_text()
    return {
        "modDisplayName": "Garage Progress Bar",
        "enabled": True,
        # settingsVersion lets the panel preserve the user's saved values across cosmetic
        # template edits (tooltip/label tweaks -- including this localization): with it
        # set, the host only wipes stored settings to defaults when this number is BUMPED.
        # Bump it whenever the set of varNames / control layout changes (not for text-only
        # edits; localizing the text is text-only, so it stays 3). Verified against the
        # Aslain 1.3.2 + izeberg 1.7.0 compareTemplates bytecode.
        "settingsVersion": 3,
        "column1": [
            {
                "type": "CheckBox",
                "text": t["hideAlways"]["text"],
                "value": DEFAULTS["hideAlways"],
                "tooltip": t["hideAlways"]["tooltip"],
                "varName": "hideAlways",
            },
            {
                "type": "CheckBox",
                "text": t["hideWhenComplete"]["text"],
                "value": DEFAULTS["hideWhenComplete"],
                "tooltip": t["hideWhenComplete"]["tooltip"],
                "varName": "hideWhenComplete",
            },
            {
                "type": "Label",
                "text": t["barModes"]["text"],
                "tooltip": t["barModes"]["tooltip"],
            },
            {
                "type": "CheckBox",
                "text": t["showTechTree"]["text"],
                "value": DEFAULTS["showTechTree"],
                "tooltip": t["showTechTree"]["tooltip"],
                "varName": "showTechTree",
            },
            {
                "type": "CheckBox",
                "text": t["showSkillTree"]["text"],
                "value": DEFAULTS["showSkillTree"],
                "tooltip": t["showSkillTree"]["tooltip"],
                "varName": "showSkillTree",
            },
            {
                "type": "CheckBox",
                "text": t["showFieldMods"]["text"],
                "value": DEFAULTS["showFieldMods"],
                "tooltip": t["showFieldMods"]["tooltip"],
                "varName": "showFieldMods",
            },
            {
                "type": "CheckBox",
                "text": t["showEliteRewards"]["text"],
                "value": DEFAULTS["showEliteRewards"],
                "tooltip": t["showEliteRewards"]["tooltip"],
                "varName": "showEliteRewards",
            },
            {
                "type": "CheckBox",
                "text": t["showElite"]["text"],
                "value": DEFAULTS["showElite"],
                "tooltip": t["showElite"]["tooltip"],
                "varName": "showElite",
            },
            {
                "type": "CheckBox",
                "text": t["showPotentialTierXI"]["text"],
                "value": DEFAULTS["showPotentialTierXI"],
                "tooltip": t["showPotentialTierXI"]["tooltip"],
                "varName": "showPotentialTierXI",
            },
        ],
        "column2": [
            {
                "type": "Label",
                "text": t["barPosition"]["text"],
                "tooltip": t["barPosition"]["tooltip"],
            },
            {
                "type": "NumericStepper",
                "text": t["posX"]["text"],
                "value": DEFAULTS["posX"],
                "minimum": 0,
                "maximum": POS_MAX,
                "snapInterval": 1,
                "canManualInput": True,
                "tooltip": t["posX"]["tooltip"],
                "varName": "posX",
            },
            {
                "type": "NumericStepper",
                "text": t["posY"]["text"],
                "value": DEFAULTS["posY"],
                "minimum": 0,
                "maximum": POS_MAX,
                "snapInterval": 1,
                "canManualInput": True,
                "tooltip": t["posY"]["tooltip"],
                "varName": "posY",
            },
        ],
    }


def _sync_template_text(api):
    """Refresh a stored template's label/tooltip text to the client's active language.

    MSA stores a COPY of the template text at registration and renders from it (deep-
    copied on each open); on an EXISTING install init() takes the saved-truthy branch and
    never re-applies the template text, so a language change (or this feature landing over
    an English install) would otherwise never show. This walks the stored template in
    lockstep with settings_i18n's column key order (Labels carry no varName) and overwrites
    each entry's text/tooltip from panel_text(), saving only if something changed.
    Idempotent: a no-op on a fresh install (text already matches). Guarded; all changes are
    text-only so no settingsVersion bump is involved."""
    try:
        tmpl = (getattr(api, "state", None) or {}).get("templates", {}).get(LINKAGE)
        if not isinstance(tmpl, dict):
            return
        t = settings_i18n.panel_text()
        changed = False
        for col, keys in (("column1", settings_i18n.COL1_KEYS),
                          ("column2", settings_i18n.COL2_KEYS)):
            for comp, key in zip(tmpl.get(col) or [], keys):
                rendered = t.get(key) if isinstance(comp, dict) else None
                if not rendered:
                    continue
                if comp.get("text") != rendered["text"]:
                    comp["text"] = rendered["text"]
                    changed = True
                tip = rendered.get("tooltip")
                if tip is not None and comp.get("tooltip") != tip:
                    comp["tooltip"] = tip
                    changed = True
        if changed and hasattr(api, "saveState"):
            api.saveState()
            LOG_NOTE("[wgmod] synced settings template text to client language")
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _apply(settings):
    """Merge an MSA settings dict into our cache, ignoring unknown/missing keys.
    Per-key typed: the hide flags are bools, the position fields are clamped ints."""
    if not settings:
        return
    for key in DEFAULTS:
        if key not in settings:
            continue
        if key in ("posX", "posY", "posW", "posH"):
            _settings[key] = clamp_pos(settings[key])
        elif key == "modeOverrides":
            # A JSON string (per-vehicle mode switch map); keep it verbatim, guarding a
            # non-string / missing value back to the empty map.
            v = settings[key]
            _settings[key] = v if isinstance(v, _STR_TYPES) else "{}"
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
        # Refresh the stored template text to the client's active language. Required for
        # EXISTING installs: the saved-truthy branch above re-uses the stored (possibly
        # stale-language) template, so without this a language change never reaches the
        # panel. No-op on a fresh install (setModTemplate just stored the localized text).
        for _api in _candidate_apis():
            _sync_template_text(_api)
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


def _label_defaults(api, dx, dy):
    """Show the DEFAULT position in the stepper labels (so the panel displays the reset
    target, not the currently-applied value). Patches the stored template's posX/posY label
    text in place -- the panel deep-copies the template on each open, so the new label shows
    next time it's opened. Guarded; no-op if the template/coords aren't available.

    The base label AND the "default N" suffix are localized: the base comes from
    settings_i18n.panel_text() (the same source _sync_template_text uses, already marked if
    it fell back to English) and settings_i18n.default_label appends the localized suffix --
    e.g. EN "Horizontal (center X) — default 1920", DE "... — Standard 1920"."""
    if not dx or not dy:
        return
    try:
        tmpl = (getattr(api, "state", None) or {}).get("templates", {}).get(LINKAGE)
        if not isinstance(tmpl, dict):
            return
        t = settings_i18n.panel_text()
        wanted = {"posX": settings_i18n.default_label(t["posX"]["text"], dx),
                  "posY": settings_i18n.default_label(t["posY"]["text"], dy)}
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
    button move our bar. `defaults` is the host's stored snapshot (hide flags + per-mode
    toggles); we apply it, then force the position back to AUTO (0/0). Under the drift fix
    the default position IS auto -- the resolution-relative CSS default, re-measured live --
    so reset never pins a stale seeded px and is resolution-independent. The widget re-seeds
    the panel's default label on the next mount. Guarded + linkage-scoped (the event is
    global across every mod)."""
    try:
        if linkage != LINKAGE:
            return
        _apply(defaults if defaults else DEFAULTS)
        # Position always resets to auto (CSS default), regardless of any seeded px the
        # host snapshot may still carry -- see the Option 1 drift fix in set_position.
        _settings["posX"] = 0
        _settings["posY"] = 0
        _settings["posW"] = 0
        _settings["posH"] = 0
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
    data.update(_settings)             # our varNames (hide flags, per-mode toggles, posX/posY)
    return data


def set_position(x, y, is_default=False, w=0, h=0):
    """Persist a new bar position (px) and re-push it to the widget. Called from the JS
    `setPosition` reverse command.

    `is_default` is True for the widget's SEED -- the px it measures while the bar sits at
    its CSS default. Under the drift fix (Option 1) the seed is NOT stored as the applied
    position: it only records the panel's default-target label (see _store_default_position),
    leaving posX/posY at 0 (auto). Keeping them 0 means the resolution-relative CSS default
    stays in force, so the bar never drifts to stale pixels when the game resolution changes.
    Only a real drag / stepper edit (is_default=False) pins posX/posY to the chosen px.

    `w`/`h` are the Gameface viewport size the px were captured at. For a real pin we store
    them (posW/posH) so the widget can rescale the pinned position proportionally after a
    resolution / UI-scale change (see applyPosition in WGModResearch.js). The seed doesn't
    pin px, so its w/h are ignored here.

    Writes the FULL settings through ModsSettingsAPI so the panel's numeric fields track the
    position; guarded so a missing/broken MSA never breaks the bar. updateModSettings only
    mutates in-memory state, so saveState() flushes it to disk (survives a client restart)."""
    x = clamp_pos(x)
    y = clamp_pos(y)
    if not is_default:
        # A real drag/stepper edit pins the chosen px; the seed leaves posX/posY at auto.
        _settings["posX"] = x
        _settings["posY"] = y
        # Record the viewport the pin was captured at (for later proportional rescale).
        _settings["posW"] = clamp_pos(w)
        _settings["posH"] = clamp_pos(h)
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


def pos_w():
    return _settings["posW"]


def pos_h():
    return _settings["posH"]


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
    if _settings["showPotentialTierXI"]:
        modes.add(t.Mode.POTENTIAL_TIER_XI)
    return modes


def _mode_overrides():
    """Parse the per-vehicle mode-switch map from the JSON-string setting. Guarded: bad
    JSON / non-dict -> empty map, so a corrupt value never breaks the push."""
    import json
    try:
        m = json.loads(_settings.get("modeOverrides", "{}") or "{}")
        return m if isinstance(m, dict) else {}
    except Exception:
        return {}


def mode_override(int_cd):
    """The player's chosen (non-default) bar mode for this vehicle, or None. Keyed by
    intCD (stored as a JSON string key). intCD 0 (no vehicle) -> None."""
    try:
        int_cd = int(int_cd or 0)
    except (TypeError, ValueError):
        return None
    if not int_cd:
        return None
    return _mode_overrides().get(str(int_cd)) or None


def set_mode_override(int_cd, mode):
    """Persist the player's header mode-switch choice for `int_cd` and re-push so the bar
    repaints in that mode. Stored in the JSON-string map (survives a client restart, like
    a pinned position). intCD 0 is rejected. build_model applies it only while the chosen
    mode is still available, so a stale entry is harmless."""
    try:
        int_cd = int(int_cd or 0)
    except (TypeError, ValueError):
        return
    if not int_cd or not mode:
        return
    import json
    m = _mode_overrides()
    m[str(int_cd)] = mode
    try:
        _settings["modeOverrides"] = json.dumps(m)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return
    try:
        from gui.modsSettingsApi import g_modsSettingsApi
        g_modsSettingsApi.updateModSettings(LINKAGE, _full_settings_for_write(g_modsSettingsApi))
        try:
            g_modsSettingsApi.saveState()
        except Exception:
            LOG_CURRENT_EXCEPTION()
    except ImportError:
        pass  # MSA absent -> selection applies this session, just not persisted
    except Exception:
        LOG_CURRENT_EXCEPTION()
    # Re-push so the chosen mode reaches the widget immediately (Class-B local-state
    # command: the game fires no sync, so we must refresh -- like set_position).
    try:
        from wgmod_research.bridge import gameface_bridge as B
        B.refresh()
    except Exception:
        LOG_CURRENT_EXCEPTION()
