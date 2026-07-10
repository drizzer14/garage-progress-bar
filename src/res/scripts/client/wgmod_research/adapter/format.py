# -*- coding: utf-8 -*-
"""Pure formatting / value helpers for the read-side adapter.

Extracted from engine_adapter.py so they carry NO game-engine imports and can be
unit-tested on plain inputs (Python 3, no client). engine_adapter re-imports these
under their old private names, so its call sites are unchanged. Everything here is
best-effort and side-effect-free (KPI readers use getattr on the passed object, so a
duck-typed stub is enough to test them).

2/3-compatible.
"""
import re

from wgmod_research._compat import LOG_CURRENT_EXCEPTION


_ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]


def roman(n):
    n = int(n or 0)
    if 0 < n < len(_ROMAN):
        return _ROMAN[n]
    return str(n) if n > 0 else ""


_MODULE_ICON_RE = re.compile(r"^(img://gui/maps/icons/modules/[A-Za-z0-9_]+)\.png$")


def module_big_icon(icon):
    """The generic module-TYPE glyphs (gun/tower/chassis/engine/radio/...) ship an
    80x80 `Big` sibling in the same directory (gun.png -> gunBig.png) -- the higher-res
    art the tech-tree screen itself uses. Swap the plain 48x48 for `Big` so it stops
    upscaling in the tooltip icon box. A non-module or already-`Big` path is returned
    unchanged; guarded so a surprise path can never blank the icon."""
    try:
        m = _MODULE_ICON_RE.match(icon or "")
        if m and not m.group(1).endswith("Big"):
            return m.group(1) + "Big.png"
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return icon or ""


def skilltree_icon(node_type, image_name):
    """Full img:// URL for a skill-tree node's perk icon. The client stores them at
    skillTree/tree/perks/<type>/skills/<size>/<imageName>.png (type = getType():
    common|major|special|final) -- verified live. We use the `large` (40x40) variant
    over `small` (32x32) for a sharper glyph in the enlarged tooltip; every `small`
    icon has a matching `large` (verified against res/packages gui-part*.pkg: 178/178
    pairs, zero orphans). Bare getImageName() (e.g. 'invisibilityWhenShooting') is
    just the basename. Empty name -> "" (no icon)."""
    if not image_name:
        return ""
    return ("img://gui/maps/icons/skillTree/tree/perks/%s/skills/large/%s.png"
            % (node_type or "common", image_name))


def humanize(name):
    """camelCase action id -> spaced Title-ish label, e.g. 'invisibilityWhenShooting'
    -> 'Invisibility When Shooting'. Empty -> ""."""
    if not name:
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])([A-Z])", r" \1", name)
    return spaced[:1].upper() + spaced[1:]


def fmt_pct(pct):
    """A KPI 'mul' delta rendered as a signed percent ("+10%", "-1%"). "" if it
    rounds to zero (no meaningful change)."""
    r = round(pct)
    if abs(pct - r) < 0.05:
        n = int(r)
        return "" if n == 0 else ("%+d%%" % n)
    return "%+.1f%%" % pct


def fmt_signed(v):
    """A raw additive KPI delta as a signed magnitude ("+3", "-3", "+2.5", "-0.01").
    No percent/unit suffix -- 'add' KPIs are absolute quantities and the phrase carries
    the stat name. "" only when the value is negligible even at two decimals (rounds to
    0.00).

    'add' deltas span very different scales: +3 km/h top reverse speed, but -0.01 to
    gun dispersion (measured in hundredths). The old integer-rounding treated any
    sub-0.05 value as zero and returned "", so dispersion-scale deltas lost their
    number and the tooltip showed only the qualitative sentence. Now: snap to a clean
    integer only when actually near a NON-zero integer; otherwise render two decimals
    (trailing zeros trimmed) so a -0.01 survives while a genuine ~zero stays empty."""
    r = round(v)
    if r and abs(v - r) < 0.05:
        return "%+d" % int(r)
    s = "%+.2f" % v
    if s in ("+0.00", "-0.00"):
        return ""
    return s.rstrip("0").rstrip(".")


def fmt_num(pct):
    """A bare magnitude for a tier-XI description template's {value} slot: an int
    when it rounds clean to a NON-zero integer, else up to two decimals (trailing
    zeros trimmed). No sign -- the template's wording carries the direction (e.g.
    'Reduces ... by {value}%').

    {value} fills carry absolute magnitudes too (skilltree_value's 'add' path), which
    can be dispersion-scale hundredths; snapping any sub-0.05 value to an int collapsed
    those to "0" ('...by 0'). Keeping two decimals preserves a 0.01. Unlike fmt_signed,
    a true ~zero reads "0" (never empty) -- a filled template always wants a figure."""
    r = round(pct)
    if r and abs(pct - r) < 0.05:
        return str(int(r))
    s = "%.2f" % pct
    if s in ("0.00", "-0.00"):
        return "0"
    return s.rstrip("0").rstrip(".")


def kpi_objs(action):
    """The raw KPI objects on an action's descriptor (action._descriptor.kpi), or []."""
    d = getattr(action, "_descriptor", None)
    return getattr(d, "kpi", None) or []


def kpi_prefix(k):
    """The signed numeric prefix for a KPI, or "" when it carries no usable number.

    'mul' -> percent from (value-1)*100 ("+10%"); 'add' -> the raw signed delta
    ("+3", absolute units, no %). Any other numeric type falls back to the raw signed
    delta (the realistic non-'mul' shape is 'add'; dropping the number is the bug this
    replaces). "" when the value is missing/non-numeric or rounds to a negligible
    ~zero. bool is excluded up front (it's an int subclass). KPI types verified live
    (EU 2.3): 'mul' (Strv 103B et al.) and 'add' (Kranvagn L7 "top reverse speed")."""
    val = getattr(k, "value", None)
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return ""
    val = float(val)
    if (getattr(k, "type", "") or "") == "mul":
        return fmt_pct((val - 1.0) * 100.0)
    return fmt_signed(val)


def skilltree_value(action):
    """The bare {value} magnitude for a tier-XI sentence template, scanned from the
    node's KPI objects: 'mul' -> percent (|value-1|*100), 'add' -> raw magnitude.
    "" when no KPI carries a usable number. Unsigned -- the template's own wording
    carries the direction (e.g. 'Reduces ... by {value}%'). Verified live (EU 2.3):
    the signature 'mechanic' perks' generic 'value' KPI is itself typed 'mul'/'add',
    so it fills here; an unclassifiable type leaves "" for the caller to fall back."""
    for k in kpi_objs(action):
        v = getattr(k, "value", None)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        v = float(v)
        ktype = getattr(k, "type", "") or ""
        if ktype == "mul":
            return fmt_num(abs((v - 1.0) * 100.0))
        if ktype == "add":
            return fmt_num(abs(v))
    return ""
