# -*- coding: utf-8 -*-
"""Pure resolver for the tier-XI "vehicle skill tree" upgrade. Engine-free, tested.

A tier-XI vehicle is reached by upgrading a tier-X through a branching skill tree
(post-progression with a tree id >= 10000), NOT the linear field-modification
ladder. Per the owner's directive the bar shows this as an AGGREGATE, monotonic
"% upgraded" readout -- no per-node detail: every tier-XI tree has a FIXED set of
upgrades, so the axis is that fixed full-upgrade cost (sum of all priced nodes) and
the fill is the cumulative XP already invested (sum of the unlocked nodes' prices),
which only grows as nodes are unlocked. A header counter shows unlocked / total
nodes.

resolve() returns a plain dict the builder maps onto ResearchProgressModel (the
same contract as elite.py), or None when this isn't a skill-tree vehicle or the
tree is already fully upgraded (so the builder falls through to ELITE / COMPLETE).
There are no ticks -- this is a single-segment fill bar.
"""


def resolve(snapshot):
    """Aggregate skill-tree upgrade progress, or None to fall through.

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
    return {
        "scale_min": 0,
        # axis = the fixed full-upgrade cost (all priced nodes).
        "scale_max": int(snapshot.skilltree_total_xp or 0),
        # fill = cumulative XP invested so far (single segment; the builder puts it
        # in the vehicle slot and leaves the free slot empty).
        "fill": int(snapshot.skilltree_spent_xp or 0),
        "done": done,
        "total": total,
    }
