# -*- coding: utf-8 -*-
"""Session-scoped "done" markers for items researched via the progress bar.

When the player researches / unlocks something by clicking the bar, that item is
recorded here. On the next model push it is surfaced as a "done" marker: a tech-tree
or field-mod item becomes the very first tick (xp_position 0) with a green checkmark;
a tier-XI upgrade becomes a chip sorted first in the "next available" row. Clicking a
done marker opens the relevant native screen (handled JS-side), it never re-researches.

Lifecycle -- REPLACE, latest only, PER VEHICLE:
  * `record()` stashes the click OPTIMISTICALLY (the async confirm dialog has no
    synchronous success signal, and a cancel fires no onSyncCompleted).
  * `decorate()` only PROMOTES a pending record to the shown marker once a fresh
    snapshot confirms the item is actually done -- so a cancelled confirm never
    surfaces a marker and never clobbers the previous one.
  * Promotion overwrites that vehicle's single marker -> the next via-bar research
    replaces the last. Records are keyed by vehicle intCD; only the current vehicle's
    marker is ever injected.
  * The store is module-global and in-memory (mirrors the bridge's listener state);
    it clears naturally on client restart. No garage-reload hook is needed since
    "replace on next research" is the only clear path.

Engine-free: imports only domain.types, so it unit-tests on plain snapshots.
Every entry point is guarded -- a failure here must never blank the bar.
"""
from wgmod_research.domain import types as t

try:
    from debug_utils import LOG_CURRENT_EXCEPTION
except Exception:
    def LOG_CURRENT_EXCEPTION():
        pass

# kind values
TECHTREE = "techtree"
FIELDMOD = "fieldmod"
SKILLTREE = "skilltree"

# veh_int_cd -> record dict (the single marker currently shown for that vehicle).
_done = {}
# The last optimistic click, awaiting confirmation on the next reconciled snapshot.
_pending = None

# Modes whose views actually render ticks (main tick loop) -- the elite modes use a
# separate render path and complete/hidden draw no ticks, so a done tick isn't shown
# there. Chips (tier-XI) render only in skill_tree.
_TICK_MODES = (t.Mode.TECH_TREE, t.Mode.FIELD_MODS, t.Mode.SKILL_TREE)


def record(kind, veh_int_cd, item_id, name="", icon="", category="",
           level=0, effect="", xp_cost=0, kind_label=""):
    """Optimistically stash the item just clicked. Display fields are captured now
    because a researched item vanishes from every snapshot source afterwards."""
    global _pending
    try:
        _pending = {
            "kind": kind,
            "veh_int_cd": int(veh_int_cd or 0),
            "item_id": int(item_id or 0),
            "name": name or "",
            "icon": icon or "",
            "category": category or "",
            "level": int(level or 0),
            "effect": effect or "",
            "xp_cost": int(xp_cost or 0),
            "kind_label": kind_label or "",
        }
    except Exception:
        LOG_CURRENT_EXCEPTION()
        _pending = None


def clear():
    """Drop all markers (used by tests; not wired to a game event)."""
    global _pending
    _pending = None
    _done.clear()


def decorate(model, snapshot):
    """Promote a confirmed pending click to this vehicle's marker, then inject that
    vehicle's marker into the built model. Mutates `model` in place; guarded so any
    failure leaves the model untouched."""
    global _pending
    try:
        if snapshot is None or model is None:
            return
        veh = int(getattr(snapshot, "vehicle_int_cd", 0) or 0)

        # 1) Promote a pending record IF it belongs to this vehicle and is now done.
        if _pending is not None and _pending["veh_int_cd"] == veh:
            if _is_done(_pending, snapshot):
                _done[veh] = _pending
                _pending = None

        # 2) Inject this vehicle's marker (if any) into the model.
        rec = _done.get(veh)
        if not rec:
            return
        if rec["kind"] == SKILLTREE:
            if model.mode == t.Mode.SKILL_TREE:
                model.avail_upgrades = [_make_chip(rec)] + list(model.avail_upgrades or [])
        elif model.mode in _TICK_MODES:
            tick = _make_tick(rec)
            if model.ticks is None:
                model.ticks = []
            model.ticks.append(tick)
    except Exception:
        LOG_CURRENT_EXCEPTION()


# --- reconciliation: is the recorded item actually done now? -----------------

def _is_done(rec, snap):
    try:
        kind = rec["kind"]
        item_id = rec["item_id"]
        if kind == TECHTREE:
            # No longer among the remaining (unresearched) tech-tree unlocks.
            remaining = [u.int_cd for u in (snap.tech_unlocks or [])
                         if not getattr(u, "researched", False)]
            return item_id not in remaining
        if kind == FIELDMOD:
            for s in (snap.field_mod_steps or []):
                if getattr(s, "step_id", None) == item_id:
                    return bool(getattr(s, "unlocked", False))
            return False
        if kind == SKILLTREE:
            avail = [getattr(s, "step_id", None) for s in (snap.skilltree_available or [])]
            return item_id not in avail
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return False


# --- synthetic view objects (reuse domain shapes so the bridge marshal is unchanged) ---

def _make_tick(rec):
    """A done tech-tree / field-mod tick: pinned to xp_position 0, marked done,
    always shown bright (it's completed). The `.done` attribute drives the JS
    checkmark + open-screen click; it is read via getattr in the marshal."""
    tick = t.Tick(
        xp_position=0, category=rec["category"], icon=rec["icon"], name=rec["name"],
        xp_gained=0, xp_required=0, affordable=True, completed=True,
        locked=False, level=rec["level"], effect=rec["effect"],
        kind_label=rec["kind_label"])
    tick.done = True
    return tick


def _make_chip(rec):
    """A done tier-XI chip: a ProgressionStep marked done, prepended so it sorts
    first in the next-available row."""
    step = t.ProgressionStep(
        step_id=rec["item_id"], name=rec["name"], icon=rec["icon"],
        xp_cost=rec["xp_cost"], unlocked=True, description=rec["effect"],
        category=rec["category"])
    step.done = True
    return step
