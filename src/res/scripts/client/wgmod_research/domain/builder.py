# -*- coding: utf-8 -*-
"""Mode state machine for the EU 2.3 model.

Per selected vehicle:
- not elite (something left to unlock) -> TECH_TREE (modules + next vehicles).
- elite (fully researched) with remaining field-mod steps -> FIELD_MODS.
- elite + prestige + tier-exclusive rewards still to earn -> ELITE_REWARDS
  (the reward roadmap shown first).
- elite + prestige (rewards all earned / none) -> ELITE (grade-band progression).
- elite, no prestige data -> COMPLETE ("fully researched" badge fallback).

Fill is the player's spendable XP shown as two stacked segments: vehicle XP
first, then global free XP. The view treats a scale_min == scale_max range as
100% (guard divide-by-zero). The ELITE/ELITE_REWARDS modes reuse the same
scale/ticks/fill axis with a single segment (fill_free = 0).
"""
import copy

from wgmod_research.domain import types as t
from wgmod_research.domain.constants import Category
from wgmod_research.domain.resolvers import techtree, fieldmods, elite, skilltree, potential


def _has_real_tier_xi(snapshot):
    """True if the vehicle's tech tree carries a real Tier-XI successor vehicle. A
    tier-X's only possible tech-tree VEHICLE unlock is its Tier XI, and a researched one
    STAYS in tech_unlocks (researched=True) -- so any vehicle entry here means the real XI
    exists regardless of researched state (an UNresearched one would already have won
    TECH_TREE higher in the chain). Used to exclude the speculative POTENTIAL bar on lines
    that actually have a Tier XI."""
    return any(getattr(u, "kind", None) == Category.VEHICLE
               for u in (snapshot.tech_unlocks or []))


def _max_pos(ticks, default):
    return max([tk.xp_position for tk in ticks]) if ticks else default


def _on(enabled, mode):
    """Whether `mode` is enabled. `enabled` is a set of Mode strings the user has
    left ON; None means "all on" (the default, so callers/tests that pass no toggle
    set behave exactly as before). A mode absent from a non-None set is OFF."""
    return enabled is None or mode in enabled


def _est(snapshot):
    """The battles-remaining estimate inputs, carried identically onto every emitted
    model so the view can render the "≈ M-N battles" range in any mode (see
    WGModResearch.js). Spread as **_est(snapshot) into ResearchProgressModel."""
    return dict(
        avg_battle_xp=snapshot.avg_battle_xp,
        battle_count=snapshot.battle_count,
        account_avg_battle_xp=snapshot.account_avg_battle_xp,
        reserve_mult=snapshot.reserve_mult,
        daily_double_factor=snapshot.daily_double_factor,
        max_battle_xp=snapshot.max_battle_xp)


def bar_visible(overlay_closed, show_bar, show_when_complete, mode, in_garage):
    """Whether the bar should render, combining the engine state (a tank-setup
    overlay open -> overlay_closed is False; the plain garage is mounted ->
    in_garage is True) with the two user settings. Pure and engine-free so it
    unit-tests on plain inputs.

    show_bar / show_when_complete are the INVERSE polarity of the old hide_always /
    hide_when_complete flags (checkbox default now ON = shown), so the gates test the
    negation -- same net behavior as before.

    - not show_bar: master switch OFF -> never show.
    - Mode.HIDDEN: the vehicle's resolved mode is turned off by a per-mode user
      toggle (see build_model) -> never show.
    - in_garage: show ONLY in the plain garage view (fail-closed allowlist -- any
      other lobby view, or an unreadable view signal, hides the bar).
    - not show_when_complete: hide on fully-progressed vehicles (Mode.COMPLETE).
    - otherwise follow the overlay state (hidden while a setup overlay is open)."""
    if not show_bar:
        return False
    if mode == t.Mode.HIDDEN:
        return False
    if not in_garage:
        return False
    if not show_when_complete and mode == t.Mode.COMPLETE:
        return False
    return overlay_closed


# --- Per-mode candidate builders --------------------------------------------------
# Each returns (Mode, ResearchProgressModel) if the vehicle qualifies for that mode,
# else None. They embody the SAME gate logic the old first-match chain used, but each
# is evaluated independently so build_model can (a) enumerate ALL applicable modes for
# the header switch and (b) re-emit any chosen one. `ctx` carries the shared scalars
# derived once from the snapshot (fill/spendable/est/counters/class). Order in _BUILDERS
# is the historical priority order; the first non-None is the priority winner.


def _b_tech(snapshot, ctx, enabled):
    # Research takes priority: while ANY tech unlock (module or next vehicle) is still
    # unresearched, show the tech tree -- even on a vehicle the account already counts
    # as elite. techtree.resolve returns remaining-only ticks, so its emptiness is the
    # exact "nothing left to research" signal (see the long note kept below).
    ticks = techtree.resolve(snapshot)
    if not ticks:
        return None
    scale_max = _max_pos(ticks, 0)
    return (t.Mode.TECH_TREE, t.ResearchProgressModel(
        mode=t.Mode.TECH_TREE, scale_min=0, scale_max=scale_max,
        fill_vehicle=ctx["fill_vehicle"], fill_free=ctx["fill_free"], ticks=ticks,
        vehicle_class=ctx["veh_class"], spendable_xp=ctx["spendable"],
        progress_current=ctx["spendable"], progress_required=scale_max, **ctx["est"]))


def _b_skill(snapshot, ctx, enabled):
    # Tier-XI "vehicle skill tree": a branching COUNT bar (axis = total nodes). resolve()
    # returns None once fully upgraded, so it then falls through to prestige / COMPLETE.
    if not snapshot.is_skill_tree:
        return None
    st = skilltree.resolve(snapshot)
    if st is None:
        return None
    # The skill-tree bar itself is a node COUNT axis, but the "current / required"
    # readout is the XP figure: XP already invested in the tree vs. the full-upgrade
    # total, so both the "%" and the "current / required" text read researched / total.
    # Both totals ride the snapshot.
    return (t.Mode.SKILL_TREE, t.ResearchProgressModel(
        mode=t.Mode.SKILL_TREE, scale_min=st["scale_min"],
        scale_max=st["scale_max"], fill_vehicle=st["fill"],
        fill_free=0, ticks=st["ticks"],
        fieldmods_done=st["done"], fieldmods_total=st["total"],
        vehicle_class=ctx["veh_class"], spendable_xp=ctx["spendable"],
        avail_upgrades=st.get("avail_upgrades", []),
        progress_current=snapshot.skilltree_spent_xp,
        progress_required=snapshot.skilltree_total_xp, **ctx["est"]))


def _b_field(snapshot, ctx, enabled):
    # Nothing left to research: remaining Field Modifications, plus the researched/total
    # field-mod-level counter in the header.
    fm_ticks = fieldmods.resolve(snapshot)
    if not fm_ticks:
        return None
    scale_max = _max_pos(fm_ticks, 0)
    return (t.Mode.FIELD_MODS, t.ResearchProgressModel(
        mode=t.Mode.FIELD_MODS, scale_min=0, scale_max=scale_max,
        fill_vehicle=ctx["fill_vehicle"], fill_free=ctx["fill_free"], ticks=fm_ticks,
        fieldmods_done=ctx["fm_done"], fieldmods_total=ctx["fm_total"],
        vehicle_class=ctx["veh_class"], spendable_xp=ctx["spendable"],
        progress_current=ctx["spendable"], progress_required=scale_max, **ctx["est"]))


def _b_potential(snapshot, ctx, enabled):
    # Speculative "potential Tier XI" (opt-in, default off): a tier-X tank with NO real
    # tier XI, fully researched + field mods done. Banked spendable XP filling toward the
    # fixed price a real tier XI costs. Sits above prestige so it REPLACES the Elite-Levels
    # bar when enabled. Gated at ENTRY on enabled membership (not the _emit hide path), so
    # OFF falls THROUGH to elite/complete rather than hiding. enabled=None (legacy/tests)
    # never includes this opt-in mode, so existing tests are unchanged. It also must NOT
    # apply to a PREMIUM / gift / reward tank (no research line -> never a Tier XI; e.g. the
    # tier-X premium Dravec). "No real Tier XI" needs the remaining exclusions: not
    # skill-tree, and no tech-tree Tier-XI successor vehicle (which stays in tech_unlocks
    # researched=True -- see _has_real_tier_xi).
    if not (enabled is not None and t.Mode.POTENTIAL_TIER_XI in enabled
            and snapshot.tier == 10 and not snapshot.is_skill_tree
            and not getattr(snapshot, "is_premium", False)
            and not _has_real_tier_xi(snapshot)):
        return None
    # potential.resolve never returns None by contract, so no None-guard.
    pxi = potential.resolve(snapshot)
    return (t.Mode.POTENTIAL_TIER_XI, t.ResearchProgressModel(
        mode=t.Mode.POTENTIAL_TIER_XI, scale_min=pxi["scale_min"],
        scale_max=pxi["scale_max"], fill_vehicle=ctx["fill_vehicle"],
        fill_free=ctx["fill_free"], ticks=pxi["ticks"],
        vehicle_class=ctx["veh_class"], spendable_xp=ctx["spendable"],
        progress_current=ctx["spendable"], progress_required=pxi["scale_max"],
        **ctx["est"]))


def _b_elite_rewards(snapshot, ctx, enabled):
    # Tier-exclusive reward roadmap: available only while a reward is unearned. Once all
    # are earned, resolve returns None / any_unearned False and we fall to the grade band.
    if not snapshot.has_prestige:
        return None
    reward = elite.resolve_reward_track(snapshot)
    if reward is not None and reward["any_unearned"]:
        return (t.Mode.ELITE_REWARDS,
                _elite_model(t.Mode.ELITE_REWARDS, reward, snapshot, ctx["est"], ctx["spendable"]))
    return None


def _b_elite(snapshot, ctx, enabled):
    # Prestige grade-band progression (the fallback prestige view).
    if not snapshot.has_prestige:
        return None
    band = elite.resolve_grade_band(snapshot)
    if band is not None:
        return (t.Mode.ELITE, _elite_model(t.Mode.ELITE, band, snapshot, ctx["est"], ctx["spendable"]))
    return None


# Historical priority order: the first non-None candidate is the mode the bar shows by
# default (unchanged from the old first-match chain).
_BUILDERS = (_b_tech, _b_skill, _b_field, _b_potential, _b_elite_rewards, _b_elite)


def build_model(snapshot, enabled=None, override=None, ignore_free_xp=False):
    """`enabled` is the set of Mode strings the user has left ON (None = all on).

    `ignore_free_xp` (the "Ignore Free XP" setting) makes the bar behave as if the
    account-global free XP were zero -- combat XP only counts toward the fill,
    per-item affordability, and every resolver's own spendable. It is applied ONCE
    here by neutralizing the single source field (snapshot.free_xp) on a shallow copy
    (the snapshot is fresh per push, but copy so a shared test fixture isn't mutated);
    everything downstream -- fill_free/spendable below AND each resolver's affordability
    (techtree/fieldmods/potential) -- reads snapshot.free_xp, so no per-site logic is
    needed. The battles estimate is already combat-XP-only; elite modes already force
    fill_free = 0.

    The default mode is resolved by the usual priority chain (the first applicable mode
    in _BUILDERS); if that resolved mode is OFF, the bar is HIDDEN -- there is NO
    fall-through to a lower-priority mode, and COMPLETE is reached only when the vehicle
    is genuinely done (no branch matched).

    `override` is the player's per-vehicle "mode switch" choice (a Mode string). It is
    honored ONLY when it is among the AVAILABLE modes (applicable AND enabled) -- an
    explicit, still-valid choice by the player, so it wins even if the priority default
    is disabled. A stale/absent override is ignored and the priority default applies.

    The emitted model carries `avail_modes` (the ordered available modes) so the widget
    can render the header switch."""
    if ignore_free_xp:
        snapshot = copy.copy(snapshot)
        snapshot.free_xp = 0
    fill_vehicle = snapshot.vehicle_xp
    fill_free = snapshot.free_xp
    # Total spendable XP, set on every model below so the view can show per-item
    # affordability in any mode (skill_tree fill is a node count, not XP).
    spendable = fill_vehicle + fill_free
    # Battles-remaining estimate inputs, carried onto every model so the view can
    # render the "≈ M-N battles" range beside a tooltip's XP shortfall (see _est).
    est = _est(snapshot)
    fm_done = snapshot.fieldmods_done
    fm_total = snapshot.fieldmods_total
    veh_class = snapshot.vehicle_class
    ctx = {"fill_vehicle": fill_vehicle, "fill_free": fill_free, "spendable": spendable,
           "est": est, "fm_done": fm_done, "fm_total": fm_total, "veh_class": veh_class}

    def _placeholder(mode):
        # A model with no bar of its own, carrying only the shared fill/counter fields:
        # Mode.HIDDEN (resolved mode toggled off -> bar_visible() hides it) or
        # Mode.COMPLETE (nothing left to research -> the elite badge).
        return t.ResearchProgressModel(
            mode=mode, scale_min=0, scale_max=0,
            fill_vehicle=fill_vehicle, fill_free=fill_free, ticks=[],
            fieldmods_done=fm_done, fieldmods_total=fm_total, vehicle_class=veh_class,
            spendable_xp=spendable, **est)

    # Enumerate every applicable mode in priority order (each builder embeds its own gate).
    cands = []
    for build in _BUILDERS:
        r = build(snapshot, ctx, enabled)
        if r is not None:
            cands.append(r)
    # The switch options: applicable AND enabled, priority-ordered (POTENTIAL is already
    # entry-gated on enabled membership, so _on is a safe no-op for it).
    avail = [m for (m, _model) in cands if _on(enabled, m)]

    if not cands:
        # nothing left to research and no prestige data: COMPLETE (elite badge).
        result = _placeholder(t.Mode.COMPLETE)
    else:
        by_mode = dict(cands)
        if override and override in avail:
            # Player's explicit choice among the available modes -- honored even if the
            # priority default is disabled (override is drawn from `avail`, i.e. enabled).
            result = by_mode[override]
        else:
            winner_mode, winner_model = cands[0]
            # Honor the per-mode user toggle for the priority default: a mode this vehicle
            # RESOLVED to but which the user turned off hides the bar -- NO fall-through
            # to a lower-priority mode.
            result = winner_model if _on(enabled, winner_mode) else _placeholder(t.Mode.HIDDEN)

    result.avail_modes = avail
    return result


def _elite_model(mode, res, snapshot, est, spendable):
    """Build an ELITE / ELITE_REWARDS model from a resolver result dict. The
    band uses a single fill segment (vehicle slot) so fill_free stays 0; the
    readout is cumulative combat XP. `est` (the estimate inputs) and `spendable`
    (vehicle + free XP) are threaded in from build_model so they aren't recomputed --
    both equal what the caller already derived from the same snapshot."""
    # The prestige/Elite-Levels system tracks the vehicle's CUMULATIVE combat XP
    # (total earned toward Elite Levels), NOT the unspent research XP (vehicle_xp).
    # Reconstruct it from the snapshot: cumulative XP to reach the current level
    # (elite_level_xp[level]) + progress within that level (elite_current_xp). The
    # latter uses -1 as a "no data" sentinel, so floor it at 0. This feeds both the
    # header readout and the per-tick "<have> / <need> XP" tooltip, whose need is
    # the cumulative combat XP to reach each grade.
    level_xp = snapshot.elite_level_xp or {}
    progress = snapshot.elite_current_xp or 0
    if progress < 0:
        progress = 0
    combat = int(level_xp.get(snapshot.elite_level, 0) or 0) + progress
    return t.ResearchProgressModel(
        mode=mode, scale_min=res["scale_min"], scale_max=res["scale_max"],
        fill_vehicle=res["fill"], fill_free=0, ticks=res["ticks"],
        vehicle_class=snapshot.vehicle_class,
        elite_level=res["level"], elite_max_level=res["max_level"],
        elite_grade=res.get("grade", ""), elite_sub=res.get("sub", 0),
        elite_current_icon=elite.current_grade_icon(snapshot),
        combat_xp=combat,
        spendable_xp=spendable,
        # "current / required" readout, promoted to scalars by the resolver:
        #   ELITE (grade band) -> combat XP earned since the current grade started, out
        #     of the grade's XP span (so the "%" equals the bar fill width exactly).
        #   ELITE_REWARDS      -> total combat XP (no progress_current promoted, so we
        #     fall back to `combat` here) toward the last reward level's cumulative XP.
        progress_current=res.get("progress_current", combat),
        progress_required=res.get("progress_required", 0),
        **est)
