# -*- coding: utf-8 -*-
"""Pure resolvers for the Elite Levels ("prestige") system. Engine-free, tested.

Two views, both reusing the bar's scale/ticks/fill axis (so the JS renders them
with the same pct(scale_min..scale_max) math as the other modes):

- resolve_grade_band: the CURRENT complex-grade band (e.g. all of SILVER's four
  sub-grades), with one milestone tick per sub-grade and the fill running to the
  current elite level. The axis spans [band_min, band_max).
- resolve_reward_track: the tier-exclusive milestone-REWARD roadmap -- one tick
  per reward (with its img:// thumbnail + earned/next/upcoming state), the axis
  spanning [0, last reward level], fill to the current level.

Each returns a plain dict the builder maps onto ResearchProgressModel. `fill` is
the position OFFSET from scale_min (scale_min + fill == current position).
"""
from wgmod_research.domain import types as t
from wgmod_research.domain.constants import Category, GradeFamily

# The in-game elite-level grade emblems -- the same hexagonal badges the battle
# team-HP bars show next to a player's vehicle. 48x48 set; families iron/bronze/
# silver/gold/enamel carry sub-grades 1..4, and the terminal MAX grade is a single
# "prestige" badge. Built here (deterministic from family+sub) so each grade tick
# carries its emblem img:// URL like the other ticks carry theirs.
# Use the 72x72 set, NOT 48x48: the 48x48 art is a sparse downscale that renders
# see-through/grey when scaled up on the bar; 72x72 is the solid, detailed badge
# (full color + laurel) that reads correctly at our render size. Same family/sub
# layout + a terminal prestige.png.
_EMBLEM_BASE = "img://gui/maps/icons/prestige/emblem/72x72/"


def _emblem_url(family, sub):
    if family == GradeFamily.PRESTIGE:
        return _EMBLEM_BASE + "prestige.png"
    if family and 1 <= sub <= 4:
        return _EMBLEM_BASE + "%s/%d.png" % (family, sub)
    return ""


def _grade_title(family, sub):
    """Capitalized tooltip title, e.g. 'Silver 2' / 'Prestige'."""
    name = (family or "").capitalize()
    return "%s %d" % (name, sub) if sub > 0 else name


def _fill_fraction(current_xp, next_xp):
    """Within-level progress 0..1. Zero on the no-data (-1) / maxed (equal)
    sentinels or any degenerate input -- the bar then sits exactly on the level
    boundary."""
    try:
        if next_xp and next_xp > 0 and 0 <= current_xp <= next_xp:
            return float(current_xp) / float(next_xp)
    except (TypeError, ValueError):
        pass
    return 0.0


def _families_in_order(grades):
    """Ordered, de-duplicated complex-grade family ids, in level order (grades
    arrive sorted by level, so families appear iron->...->prestige)."""
    families = []
    for g in grades:
        if g.grade not in families:
            families.append(g.grade)
    return families


def _clamp(value, low, high):
    if high < low:
        return low
    return max(low, min(high, value))


def _mark_states(entries, reached):
    """Yield (entry, state) for a milestone sequence: 'achieved' where reached(entry)
    is true, 'next' for the first not-yet-reached entry, 'upcoming' for the rest.
    Shared by the grade-band and reward-track tick loops."""
    next_marked = False
    for e in entries:
        if reached(e):
            state = "achieved"
        elif not next_marked:
            state = "next"
            next_marked = True
        else:
            state = "upcoming"
        yield e, state


def _current_grade(grades, level):
    """The last (sub-)grade whose threshold has been reached (level <= elite level),
    or None below the very first threshold. ``grades`` must be sorted by level."""
    current = None
    for g in grades:
        if g.level <= level:
            current = g
        else:
            break
    return current


def current_grade_icon(snapshot):
    """Emblem URL for the highest grade the player has currently REACHED (the
    last (sub-)grade whose level <= the current elite level). "" below the first
    threshold or with no grades. MAX ("prestige") -> the terminal prestige badge.
    Shared by both elite modes so the category icon shows the current-grade chevron
    regardless of whether the bar is the grade band or the reward roadmap."""
    grades = sorted(snapshot.elite_grades, key=lambda g: g.level)
    if not grades:
        return ""
    level = snapshot.elite_level
    current = _current_grade(grades, level)
    if current is None:
        return ""
    return _emblem_url(current.grade, current.sub)


def resolve_grade_band(snapshot):
    """The current grade band. Returns None if there are no grades to show."""
    grades = sorted(snapshot.elite_grades, key=lambda g: g.level)
    if not grades:
        return None
    level = snapshot.elite_level
    max_level = snapshot.elite_max_level or (grades[-1].level if grades else 0)
    families = _families_in_order(grades)

    # Current grade = the last (sub-)grade whose threshold has been reached;
    # None when below the very first threshold (treat as the first family).
    current_grade = _current_grade(grades, level)
    current_family = current_grade.grade if current_grade is not None else families[0]

    # At MAX ("prestige", a single synthetic entry at max_level): show the last
    # real complex band, full, badged as the max grade.
    if current_family == GradeFamily.PRESTIGE:
        real = [f for f in families if f != GradeFamily.PRESTIGE]
        band_family = real[-1] if real else current_family
    else:
        band_family = current_family

    band_grades = [g for g in grades if g.grade == band_family]
    if not band_grades:
        return None
    band_min = min(g.level for g in band_grades)
    # band_max = first level of the next family, else the overall cap.
    idx = families.index(band_family)
    next_families = families[idx + 1:]
    if next_families:
        nxt = next_families[0]
        band_max = min(g.level for g in grades if g.grade == nxt)
    else:
        band_max = max_level

    level_xp = snapshot.elite_level_xp or {}

    # Sub-grade milestone ticks (each carrying its grade emblem + the cumulative
    # XP to reach it). The first not-yet-reached sub-grade is "next".
    # NB PLACEMENT vs LABEL: `xp_position` places the pip on the cumulative-XP axis
    # (level_xp[g.level]); the tick's on-screen badge NUMBER is the elite LEVEL and
    # rides on `level` (the widget's numeric-glyph field). Do NOT source the badge
    # from xp_position -- that renders the raw XP figure instead of the milestone.
    ticks = []
    for g, state in _mark_states(band_grades, lambda g: level >= g.level):
        ticks.append(t.Tick(
            xp_position=level_xp.get(g.level, 0), category=Category.ELITE,
            icon=_emblem_url(band_family, g.sub),
            name=_grade_title(band_family, g.sub),
            xp_gained=0, xp_required=level_xp.get(g.level, 0), affordable=False,
            completed=(level >= g.level), level=g.level, state=state))

    # One extra tick at the band's end = the NEXT grade's first level, so the bar
    # always shows what you're climbing toward. Sits at scale_max (the right edge).
    # When the whole current band is achieved but this next-family tick isn't yet
    # reached, it is the "next" milestone (the in-band loop only marks a tick "next"
    # while sub-grades remain, so a fully-achieved band would otherwise show none).
    if next_families:
        nxt = next_families[0]
        nxt_grades = [g for g in grades if g.grade == nxt]
        if nxt_grades:
            ng = min(nxt_grades, key=lambda g: g.level)
            band_all_reached = all(level >= g.level for g in band_grades)
            trailing_state = ("achieved" if level >= ng.level
                              else ("next" if band_all_reached else "upcoming"))
            ticks.append(t.Tick(
                xp_position=level_xp.get(ng.level, 0), category=Category.ELITE,
                icon=_emblem_url(nxt, ng.sub),
                name=_grade_title(nxt, ng.sub),
                xp_gained=0, xp_required=level_xp.get(ng.level, 0), affordable=False,
                completed=(level >= ng.level), level=ng.level,
                state=trailing_state))

    if current_family == GradeFamily.PRESTIGE:
        sub = 0
    else:
        achieved = [g for g in band_grades if g.level <= level]
        sub = max([g.sub for g in achieved]) if achieved else 0

    # Re-express the bar AND the readout on cumulative combat XP WITHIN the current
    # band, so the fill width equals the readout % exactly (both XP-based). The axis
    # spans [level_xp[band_min] .. level_xp[band_max]]; the fill segment feeds
    # data.fillVehicle, and renderElite computes fillPos = scale_min + fill = combat_xp,
    # width = (combat_xp - scale_min) / (scale_max - scale_min) = readout %.
    combat = int(level_xp.get(level, 0) or 0) + max(0, snapshot.elite_current_xp or 0)
    scale_min = level_xp.get(band_min, 0)
    scale_max = level_xp.get(band_max, 0)
    # Readout scalars: XP earned since the current grade started vs. the grade's XP
    # span. At the terminal MAX grade (no next band) the span is <= 0 -- leave both 0
    # so the widget falls back to a current-only readout + hidden "%". The bar geometry
    # still holds (renderElite clamps fillPos, showing a full bar at max).
    span = scale_max - scale_min
    if span > 0:
        progress_current = max(0, combat - scale_min)
        progress_required = span
    else:
        progress_current = 0
        progress_required = 0

    return {
        "scale_min": scale_min,
        "scale_max": scale_max,
        "fill": combat - scale_min,
        "ticks": ticks,
        "grade": current_family,
        "sub": sub,
        "level": level,
        "max_level": max_level,
        "progress_current": progress_current,
        "progress_required": progress_required,
    }


def resolve_reward_track(snapshot):
    """The tier-exclusive milestone-reward roadmap. Returns None if no rewards."""
    rewards = sorted(snapshot.elite_rewards, key=lambda r: r.level)
    if not rewards:
        return None
    level = snapshot.elite_level
    max_level = snapshot.elite_max_level or rewards[-1].level
    scale_max = max(r.level for r in rewards)
    level_xp = snapshot.elite_level_xp or {}

    ticks = []
    for r, state in _mark_states(rewards, lambda r: r.achieved):
        # type label rides along in `options` so the JS tooltip can show it.
        opts = [r.type_label] if r.type_label else []
        ticks.append(t.Tick(
            xp_position=r.level, category=Category.REWARD, icon=r.icon,
            name=r.label, xp_gained=0, xp_required=level_xp.get(r.level, 0),
            affordable=False, completed=r.achieved, state=state, options=opts))

    frac = _fill_fraction(snapshot.elite_current_xp, snapshot.elite_next_xp)
    position = _clamp(level + frac, 0, scale_max)
    # Cumulative combat XP required to reach the LAST reward level (the trailing tick).
    # Promoted to a scalar so the builder can feed the header "current / required"
    # readout without walking the ticks.
    progress_required = level_xp.get(rewards[-1].level, 0)
    return {
        "scale_min": 0,
        "scale_max": scale_max,
        "fill": position,
        "ticks": ticks,
        "level": level,
        "max_level": max_level,
        "any_unearned": any(not r.achieved for r in rewards),
        "progress_required": progress_required,
    }
