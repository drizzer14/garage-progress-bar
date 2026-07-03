# -*- coding: utf-8 -*-
"""Pure resolver for the tier-XI "vehicle skill tree" upgrade. Engine-free, tested.

A tier-XI vehicle is reached by upgrading a tier-X through a branching skill tree
(post-progression with a tree id >= 10000), NOT the linear field-modification
ladder. Per the owner's directive the bar shows this as a COUNT readout -- the
tree is non-linear, so an XP axis is meaningless. Every tier-XI tree has a FIXED
set of upgrades, so the axis is that node count and the fill is how many nodes are
unlocked. One tick is placed per node (evenly spaced, no per-node metadata since
ordering is non-linear); the rightmost tick flags the signature 'final' upgrade
and carries its icon. A header counter shows unlocked / total nodes.

resolve() returns a plain dict the builder maps onto ResearchProgressModel (the
same contract as elite.py), or None when this isn't a skill-tree vehicle or the
tree is already fully upgraded (so the builder falls through to ELITE / COMPLETE).
"""
from wgmod_research.domain import types as t
from wgmod_research.domain.constants import Category


def resolve(snapshot):
    """Count-based skill-tree upgrade progress, or None to fall through.

    None when the vehicle isn't a skill-tree vehicle, has no priced upgrade nodes,
    or its tree is fully upgraded (every node unlocked) -- in those cases the
    builder continues to the elite / complete branches.
    """
    if not snapshot.is_skill_tree:
        return None
    total = int(snapshot.skilltree_total or 0)
    done = int(snapshot.skilltree_done or 0)
    if total <= 0 or done >= total:
        return None  # no upgrades / fully upgraded -> fall through to ELITE/COMPLETE

    # One tick per node, evenly spaced on a 0..total axis (tick i sits at i). Ticks
    # within the fill (i <= done) are unlocked -> render bright (affordable); the
    # rest are locked -> render dim. No names/options/tooltips (non-linear tree).
    # Only the last tick (the signature 'final' upgrade) carries an icon.
    ticks = []
    for i in range(1, total + 1):
        is_final = (i == total)
        # Only the final tick carries an icon + name + cost (-> its end-tick tooltip,
        # reusing the Tick name/xp_required fields). The plain count ticks stay bare.
        ticks.append(t.Tick(
            xp_position=i, category=Category.UPGRADE,
            icon=(snapshot.skilltree_final_icon if is_final else ""),
            name=(snapshot.skilltree_final_name if is_final else ""),
            xp_gained=0,
            xp_required=(snapshot.skilltree_final_xp if is_final else 0),
            affordable=(i <= done), completed=(i <= done),
            locked=(i > done),
            effect=(snapshot.skilltree_final_effect if is_final else "")))

    return {
        "scale_min": 0,
        "scale_max": total,     # axis = total upgrade nodes (count, not XP)
        "fill": done,           # fill = nodes unlocked (single segment)
        "done": done,
        "total": total,
        "ticks": ticks,
        # frontier nodes (not received, prereqs met) -> clickable header chips.
        "avail_upgrades": list(snapshot.skilltree_available or []),
    }
