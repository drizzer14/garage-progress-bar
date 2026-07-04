# -*- coding: utf-8 -*-
"""Pure resolver for the speculative "potential Tier XI" bar. Engine-free, tested.

Most Tier-X tanks never got a real Tier XI (the branching vehicle skill tree that a
few lines received -- see skilltree.py). This opt-in mode gives those tanks something
aspirational to grind toward once they're fully researched and their field mods are
done: a bar tracking the player's BANKED SPENDABLE XP (unspent vehicle XP + global
free XP) filling toward the fixed price every real Tier XI costs to unlock
(POTENTIAL_TIER_XI_XP). The bar is a plain XP axis with a single milestone tick at
the target; the tick is NOT clickable (there is no real item to research), it only
carries the "have / need" + "~ M-N battles" tooltip via the shared view estimator.

resolve() returns a plain dict the builder maps onto ResearchProgressModel (the
builder supplies the two-segment fill from the snapshot's vehicle + free XP, exactly
like the tech-tree / field-mods modes). It never returns None -- the builder owns the
applicability gate (tier == X, not a skill-tree vehicle, opt-in toggle on).
"""
from wgmod_research.domain import types as t
from wgmod_research.domain.constants import Category

# The fixed XP price every real Tier XI costs to unlock. Used as the representative
# target for the speculative bar on tanks that don't have one. A code constant (not a
# user setting) by the owner's decision -- trivially tunable here if it ever changes.
POTENTIAL_TIER_XI_XP = 325000


def resolve(snapshot):
    """A single-milestone XP bar toward POTENTIAL_TIER_XI_XP.

    The lone tick sits at the target with the cost so the view's "have / need" +
    "~ M-N battles" tooltip renders; action_id == 0 keeps it non-clickable (nothing
    real to research). The tick carries NO name/icon/caption -- those are presentation
    the widget owns (the "undefined tank" glyph + the localized "Tier XI" caption are
    set in WGModResearch.js, since the domain is engine-free and can't localize or
    know asset URLs). The builder fills the bar from the snapshot's vehicle + free XP
    (two stacked segments), so the fill isn't computed here -- only the axis + tick.
    """
    spendable = int(snapshot.vehicle_xp or 0) + int(snapshot.free_xp or 0)
    tick = t.Tick(
        xp_position=POTENTIAL_TIER_XI_XP, category=Category.VEHICLE,
        icon="", name="",
        xp_gained=0, xp_required=POTENTIAL_TIER_XI_XP,
        affordable=(spendable >= POTENTIAL_TIER_XI_XP), completed=False,
        locked=False, action_id=0)
    return {
        "scale_min": 0,
        "scale_max": POTENTIAL_TIER_XI_XP,
        "ticks": [tick],
    }
