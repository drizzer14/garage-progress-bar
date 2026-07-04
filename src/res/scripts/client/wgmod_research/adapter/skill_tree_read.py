# -*- coding: utf-8 -*-
"""PC-only reader for the tier-XI "vehicle skill tree" subsystem (EU 2.3).

Extracted from engine_adapter.py (Tier 3g): reads a branching post-progression
(tree id >= VEH_SKILL_TREE_ID_OFFSET) into the count-based skill-tree fields +
the clickable "Upgrades Available:" frontier. engine_adapter.build_snapshot() calls
read_skill_tree / is_skill_tree (imported there under their old private aliases
_read_skill_tree / _is_skill_tree); post_progression_read also calls is_skill_tree to
bail so the linear FIELD_MODS reader never runs on a skill-tree vehicle. Shares only the
KPI-number formatter with the other readers, via adapter._read_common. Fully guarded.
Game symbols verified against the EU 2.3 decompiled client.
"""
import re

from wgmod_research._compat import LOG_CURRENT_EXCEPTION, _safe
from wgmod_research.adapter import i18n
from wgmod_research.adapter._read_common import _kpi_number_lines
from wgmod_research.adapter.format import (
    skilltree_icon as _skilltree_icon, humanize as _humanize,
    skilltree_value as _skilltree_value)
from wgmod_research.domain import types as t


# Localized names a skill-tree node may carry that are too generic to show, and the
# shape of ID-like image names (vehicle-specific 'mechanic' nodes, incl. the final).
_ST_GENERIC_NAMES = frozenset((u"Modification",))
_ST_ID_RE = re.compile(r"(^s\d+_|mechanic|_\d+$)", re.I)


def _skilltree_title(image_name):
    """The node's real localized title from
    R.strings.veh_skill_tree.tooltips.title.dyn(<imageName>) -- the same source the
    Upgrades screen uses (verified live: 's36_mechanic_3' -> 'Hydraulic-Driven
    Rammer', 'invisibilityWhenShooting' -> 'Concealment After Firing'). "" if absent."""
    if not image_name:
        return u""
    try:
        from gui.impl.gen import R
        from gui.impl import backport
        acc = R.strings.veh_skill_tree.tooltips.title.dyn(image_name)
        if acc is not None and acc.isValid():
            return backport.text(acc()) or u""
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return u""


def _skilltree_name(action, node_type):
    """Best readable name for a skill-tree node's tooltip. Tiered, since no single
    source covers every node type (verified live):
      1) the localized tooltips.title keyed by image name -- authoritative, covers
         perks AND signature 'mechanic' nodes;
      2) else a meaningful action loc name -- slot/config nodes give a real one
         ('Alternate Configuration: Auxiliary Loadout');
      3) else the humanized image id for a real perk; else a clean generic."""
    image_name = _safe(lambda: action.getImageName(), "") or ""
    title = _skilltree_title(image_name)
    if title:
        return title
    loc = u""
    try:
        from gui.impl import backport
        acc = action.getLocNameRes()
        loc = (backport.text(acc() if callable(acc) else acc) or u"").strip()
    except Exception:
        loc = u""
    if loc and loc not in _ST_GENERIC_NAMES:
        return loc
    if image_name and not _ST_ID_RE.search(image_name):
        return _humanize(image_name)
    return "Final Upgrade" if node_type == "final" else "Vehicle Upgrade"


def is_skill_tree(veh):
    """True for a tier-XI "vehicle skill tree" upgrade vehicle (branching
    post-progression, tree id >= VEH_SKILL_TREE_ID_OFFSET=10000). Best-effort:
    any failure -> False, so the vehicle is treated as an ordinary (linear
    field-mod) post-progression vehicle. Verified: gui_items Vehicle exposes
    .postProgression, whose model has isVehSkillTree()."""
    try:
        if not veh.isPostProgressionExists:
            return False
        return bool(veh.postProgression.isVehSkillTree())
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return False


def read_skill_tree(veh):
    """Aggregate the branching skill tree into
    (total_xp, spent_xp, done, total, final_icon, available). The bar stays a COUNT
    readout (owner directive: non-linear tree), but `available` carries the frontier
    nodes (not received, prerequisites met) as [ProgressionStep] for the clickable
    "Upgrades Available:" chips. done/total
    are the priced, non-ghost nodes unlocked vs. available; final_icon is the
    'final' node's art (img:// URL) for the rightmost tick. total_xp/spent_xp are
    retained for completeness but no longer drive the (count-based) bar.

    Steps come from the same veh.postProgression.iterOrderedSteps() the linear
    reader uses, but here each is a tree node: getPrice().xp, isReceived(),
    getType() ('major'/'special'/'final'/'common'/'ghost'). 'ghost' nodes are
    layout placeholders and zero-price nodes aren't purchasable, so neither counts.
    The 'final' node carries the tank's signature upgrade; its icon comes off the
    action model the same way field mods read theirs (action.getImageName()).

    CRITICAL: the skill tree is a DAG, so iterOrderedSteps() visits a node ONCE PER
    incoming parent edge -- a node with two parents is yielded twice (verified live:
    Hirschkaefer yields 32 steps for 26 unique nodes). We dedupe by stepID, else
    both the cost and the N/M count are inflated. Fully guarded -> (0,...,"") on
    any failure (bar falls back to COMPLETE)."""
    total_xp = 0
    spent_xp = 0
    done = 0
    total = 0
    final_icon = ""
    final_name = ""
    final_xp = 0
    final_effect = ""
    available = []
    seen = set()
    try:
        pp = veh.postProgression
        for step in pp.iterOrderedSteps():
            try:
                step_id = getattr(step, "stepID", None)
                if step_id in seen:
                    continue  # DAG: shared node already counted via another parent
                seen.add(step_id)
                node_type = _safe(lambda: step.getType(), "") or ""
                if node_type == "ghost":
                    continue
                price = step.getPrice()
                xp_cost = int(getattr(price, "xp", 0) or 0)
                if xp_cost <= 0:
                    continue  # not a purchasable upgrade node
                total += 1
                total_xp += xp_cost
                if bool(step.isReceived()):
                    done += 1
                    spent_xp += xp_cost
                elif _safe(lambda: step.isUnlocked(), False):
                    # AVAILABLE FRONTIER: not received but prerequisites met
                    # (isUnlocked() resolves the DAG parent rule). These become the
                    # clickable "Upgrades Available:" chips. isLocked() is its inverse
                    # (prereqs not met) -- verified live: only reachable nodes are
                    # isUnlocked. getImageName() is the perk basename -> full URL via
                    # _skilltree_icon; the localized name is generic, so humanize it.
                    image_name = _safe(lambda: step.action.getImageName(), "") or ""
                    # The node's OWN category (single key from getCategories()) -> its
                    # localized Upgrades-screen sub-heading (e.g. "Category: Firepower",
                    # "Mechanic Upgrade", "Special Upgrade").
                    cat_key = _safe(lambda: sorted(step.action.getCategories())[0], "") or ""
                    available.append(t.ProgressionStep(
                        step_id=step_id, name=_skilltree_name(step.action, node_type),
                        icon=_skilltree_icon(node_type, image_name),
                        xp_cost=xp_cost, unlocked=False,
                        description=_skilltree_effect(step.action),
                        category=i18n.skilltree_category(cat_key)))
                # the signature 'final' upgrade -> its icon + name + cost for the end
                # tick (which carries a tooltip like the available chips).
                if node_type == "final" and not final_icon:
                    action = getattr(step, "action", None)
                    if action is not None:
                        image_name = _safe(lambda: action.getImageName(), "") or ""
                        final_icon = _skilltree_icon("final", image_name)
                        final_name = _skilltree_name(action, "final")
                        final_xp = xp_cost
                        final_effect = _skilltree_effect(action)
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
        return (total_xp, spent_xp, done, total, final_icon, final_name, final_xp,
                final_effect, available)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return 0, 0, 0, 0, "", "", 0, "", []


def _skilltree_effect(action):
    """Effect/bonus text for a tier-XI skill-tree node.

    Signature 'mechanic' perks (major/final) describe themselves in a localized
    SENTENCE template keyed by image name:
    R.strings.veh_skill_tree.tooltips.description.dyn(<imageName>), e.g. "Reduces gun
    reload time by {value}% in Pillbox mode." We fill {value} with the node's KPI
    magnitude (_skilltree_value) and strip the {colorTagOpen/Close} markup.

    Most nodes' templates are QUALITATIVE with no magnitude slot (e.g. "Reduces gun
    dispersion when your gun is damaged.") -- the number lives only in the KPI. For
    those we append the KPI's signed magnitude line(s) via _kpi_number_lines, e.g.
    "...\n-20% to dispersion of a damaged gun", so the buff shows a figure. Ordinary
    stat perks with NO template fall back to those KPI lines alone ("+10% to hull
    elevation speed"). Feature/role slots (and negligible ~zero deltas) carry no
    numbered KPI line -> "" (unchanged). Verified live (EU 2.3). Never raises."""
    try:
        from gui.impl import backport
        from gui.impl.gen import R
        image_name = _safe(lambda: action.getImageName(), "") or ""
        tmpl = ""
        if image_name:
            rid = R.strings.veh_skill_tree.tooltips.description.dyn(image_name)
            tmpl = backport.text(rid() if callable(rid) else rid) or ""
        kpi_lines = "\n".join(_kpi_number_lines(action))
        if not tmpl or tmpl.startswith("#"):
            return kpi_lines  # no sentence template -> KPI-derived line(s) only
        value = _skilltree_value(action)
        filled = (tmpl.replace("{value}", value)
                      .replace("{colorTagOpen}", "")
                      .replace("{colorTagClose}", "").strip())
        if "{value}" in tmpl:
            # Template embeds its own magnitude slot (signature 'mechanic' perks).
            # If we couldn't classify the KPI (defensive, not seen on EU 2.3), prefer
            # the KPI-derived line so a numberless "by %" doesn't reach the tooltip.
            return filled if value else (kpi_lines or filled)
        # Qualitative sentence, no magnitude slot: append the KPI's signed number(s).
        return (filled + "\n" + kpi_lines) if (filled and kpi_lines) else (filled or kpi_lines)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return ""
