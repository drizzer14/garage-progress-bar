# -*- coding: utf-8 -*-
"""PC-only reader for the linear (field-modifications) post-progression subsystem (EU 2.3).

Extracted from engine_adapter.py (Tier 3g): reads an elite vehicle's leveled field
mods into (field_mod_steps, fm_done, fm_total). engine_adapter.build_snapshot() calls
read_post_progression (imported there under its old private alias _read_post_progression).
Shares the KPI-effect formatters with the other readers via adapter._read_common, and
calls skill_tree_read.is_skill_tree to bail on tier-XI vehicles (read separately there).
Fully guarded. Game symbols verified against the EU 2.3 decompiled client.
"""
from wgmod_research._compat import LOG_CURRENT_EXCEPTION, _safe, _safe_int
from wgmod_research.adapter._read_common import _kpi_lines, _action_effect
from wgmod_research.adapter.skill_tree_read import is_skill_tree as _is_skill_tree
from wgmod_research.domain import types as t
from wgmod_research.domain.resolvers.fieldmods import max_level


def read_post_progression(veh):
    """Read the vehicle's post-progression into (field_mod_steps, fm_done,
    fm_total), all clamped to the tier's level cap (the engine lists greyed
    levels above the cap; skip them). Verified in-game:

      - LEVELED field modifications (FeatureModItem / SimpleModItem /
        RoleSlotModItem): cost XP (price.xp), one per level -> bar hexagons, with
        getLevel() driving the roman numeral.
      - Multi-mod choice slots (MultiModsItem): cost no XP -> NOT on the bar.

    The counter (fm_done / fm_total) spans the LEVELED field mods within the cap
    (one per level, so fm_total == the tier cap) -- received vs total. Multi-mod
    choice slots are not counted. Only meaningful for elite vehicles with
    post-progression."""
    steps = []
    fm_done = 0
    fm_total = 0
    try:
        if not veh.isElite or not veh.isPostProgressionExists:
            return steps, 0, 0
        # Tier-XI vehicles use a branching skill tree, not the linear field-mod
        # ladder this reader assumes -- iterOrderedSteps() there yields tree nodes
        # whose getLevel()/MultiModsItem structure doesn't map to leveled hexagons,
        # so feeding them in here would render a garbled FIELD_MODS bar. They are
        # read separately by _read_skill_tree(); bail so FIELD_MODS never triggers.
        if _is_skill_tree(veh):
            return steps, 0, 0
        cap = max_level(_safe_int(lambda: veh.level, 0))
        pp = veh.postProgression
        # Each level pairs a leveled step (the XP-paid base mod) with a free
        # MultiModsItem holding two SELECTABLE VARIANTS, attached as that step's
        # child (parent = the leveled step's id). Collect those variant pairs
        # first, keyed by parent step id, so we can hang them on the leveled
        # tick's tooltip. (The leveled step's own name is a generic base mod and
        # repeats across levels; the pair is what distinguishes a level.)
        all_steps = list(pp.iterOrderedSteps())
        pairs_by_parent = {}
        for step in all_steps:
            try:
                if type(step.action).__name__ != "MultiModsItem":
                    continue
                parent = _safe(lambda: step.getParentStepID(), None)
                if parent is None:
                    continue
                pairs_by_parent[parent] = _pair_options(step.action)
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
        for step in all_steps:
            try:
                level = int(_safe(lambda: step.getLevel(), 0))
                if level and level > cap:
                    continue  # level not unlockable at this tier (greyed in-game)
                received = bool(step.isReceived())
                # multi-mod choice slots are not "field mod levels": neither bar
                # hexagons nor part of the researched/total counter.
                if type(step.action).__name__ == "MultiModsItem":
                    continue
                # counter spans the leveled field mods within the cap
                fm_total += 1
                if received:
                    fm_done += 1
                price = step.getPrice()
                xp_cost = int(getattr(price, "xp", 0) or 0)
                if xp_cost <= 0:
                    continue  # non-XP leveled step (rare) -> not on the bar
                name, icon = _step_label(step)
                pair = pairs_by_parent.get(step.stepID, [])
                steps.append(t.ProgressionStep(
                    step_id=step.stepID, name=name, icon=icon,
                    xp_cost=xp_cost, unlocked=received,
                    level=level,
                    options=[p[0] for p in pair],
                    option_effects=[p[1] for p in pair],
                    description=_action_effect(step.action)))
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
        return steps, fm_done, fm_total
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return steps, fm_done, fm_total


def _pair_options(action):
    """[(variant_name, inline_effect), ...] for a MultiModsItem's selectable
    variants, e.g. [("Reinforced Suspension", "+30% to suspension durability\n
    -5% to hull traverse speed"), ...]. Each `modification` resolves its name the
    same way a step action does (getLocNameRes -> DynAccessor -> backport.text) and
    carries its OWN KPI buffs (one per line, TAB-joined here -- the view renders one
    row each) -- so a choice level shows BOTH variants and ALL their buffs, not just
    the base mod's. TAB (not newline) because the VM joins the per-variant strings
    with newline; the view splits variants on \n, then buffs on \t. Best-effort;
    returns [] on failure, ("name", "") when a variant has no readable KPI."""
    out = []
    try:
        from gui.impl import backport
        for mod in (getattr(action, "modifications", None) or []):
            try:
                acc = mod.getLocNameRes()
                res_id = acc() if callable(acc) else acc
                name = backport.text(res_id) or ""
                if not name:
                    continue
                out.append((name, u"\t".join(_kpi_lines(mod))))
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return out


def _step_label(step):
    """Display name + icon for a field-mod step via its action model.

    The name is a *resource*, not a plain attribute (verified live, EU 2.3):
    `action.getLocNameRes()` returns a wulf `DynAccessor` which must be CALLED to
    yield the int resource id, which `backport.text()` then resolves to the
    localized string (e.g. "Friction Couplers Replacement (Type 1)").
    `getLocName()` alone is only the raw loc KEY ("clutches_replace_1") -- the
    earlier `action.locName`/`.name` attribute reads didn't exist, so names came
    back empty. Falls back to the raw key, then the step id."""
    name, icon = "", ""
    try:
        action = getattr(step, "action", None)
        if action is None:
            return ("step %s" % getattr(step, "stepID", "?")), ""
        try:
            icon = action.getImageName() or ""
        except Exception:
            icon = ""
        try:
            from gui.impl import backport
            acc = action.getLocNameRes()
            res_id = acc() if callable(acc) else acc
            name = backport.text(res_id) or ""
        except Exception:
            # resource lookup failed -> fall back to the raw loc key.
            try:
                name = action.getLocName() or ""
            except Exception:
                name = ""
        if name:
            return name, icon
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return ("step %s" % getattr(step, "stepID", "?")), icon
