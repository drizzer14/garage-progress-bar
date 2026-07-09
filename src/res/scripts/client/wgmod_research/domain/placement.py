# -*- coding: utf-8 -*-
"""Engine-free placement decision for collision-aware widget injection.

OpenWG stores exactly ONE `ModInjectModel` per hangar sub-view (last-writer-wins),
so two mods that inject onto the same sub-view overwrite each other's assets. Rather
than clobber whoever got there first, we inject onto the highest-priority sub-view
that is still FREE. This module holds only the pure decision; the bridge supplies the
live ViewModels and the "is this VM already claimed" predicate (see
gameface_bridge.note_mount / has_inject_model)."""

WAIT = "wait"
INJECT = "inject"
BLOCKED = "blocked"


def choose_placement(order, vms, has_inject):
    """Decide where to first place the widget (caller has no existing commitment yet).

    order       -- list of candidate sub-view names, PREFERRED FIRST.
    vms         -- dict name -> ViewModel; a name missing / mapped to None means that
                   sub-view has not mounted yet.
    has_inject  -- predicate(vm) -> True if `vm` already carries a ModInjectModel from
                   another mod (that sub-view is claimed).

    Returns (action, name):
      (INJECT, name)  -- inject onto vms[name], the highest-priority FREE sub-view.
      (WAIT, None)    -- a higher-priority candidate has not mounted yet; defer, so we
                         never commit to a fallback while the preferred one is pending.
      (BLOCKED, None) -- every candidate has mounted and each is foreign-occupied.

    Walking in priority order: a foreign candidate is skipped to try the next; the
    first not-yet-mounted candidate forces a WAIT (its slot is still undecided)."""
    for name in order:
        vm = vms.get(name)
        if vm is None:
            return (WAIT, None)
        if has_inject(vm):
            continue
        return (INJECT, name)
    return (BLOCKED, None)
