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
from wgmod_research.domain.constants import Category
from wgmod_research._compat import LOG_CURRENT_EXCEPTION

# kind values
TECHTREE = "techtree"
FIELDMOD = "fieldmod"
SKILLTREE = "skilltree"

# veh_int_cd -> record dict (the single marker currently shown for that vehicle).
_done = {}
# The last optimistic click, awaiting confirmation on the next reconciled snapshot.
_pending = None
# How many decorate() calls the current pending has survived without promotion; a
# cancelled/failed click never confirms, so a stale pending is dropped after N
# reconciles rather than lingering forever. Count-based (no wall clock) to stay
# engine-free and deterministic in tests.
_pending_reconciles = 0
_PENDING_MAX_RECONCILES = 5

# Modes whose views actually render ticks (main tick loop) -- the elite modes use a
# separate render path and complete/hidden draw no ticks, so a done tick isn't shown
# there. Chips (tier-XI) render only in skill_tree.
_TICK_MODES = (t.Mode.TECH_TREE, t.Mode.FIELD_MODS, t.Mode.SKILL_TREE)


def record(kind, veh_int_cd, item_id, name="", icon="", category="",
           level=0, effect="", xp_cost=0, kind_label="", done_count=0):
    """Optimistically stash the item just clicked. Display fields are captured now
    because a researched item vanishes from every snapshot source afterwards.

    `done_count` is the snapshot's `skilltree_done` AT CLICK TIME (skill-tree only) --
    kept as positive confirmation evidence: a later snapshot whose done-count GREW means
    a node was received, so the click succeeded even when the frontier collapsed to empty
    (which the absence test alone can't confirm). 0/ignored for non-skill-tree kinds."""
    global _pending, _pending_reconciles
    try:
        veh = int(veh_int_cd or 0)
        if not veh:
            # A failing/unknown vehicle would share the sentinel key 0 with every
            # other; never record it (avoids cross-vehicle marker bleed).
            return
        _pending = {
            "kind": kind,
            "veh_int_cd": veh,
            "item_id": int(item_id or 0),
            "name": name or "",
            "icon": icon or "",
            "category": category or "",
            "level": int(level or 0),
            "effect": effect or "",
            "xp_cost": int(xp_cost or 0),
            "kind_label": kind_label or "",
            "done_count": int(done_count or 0),
        }
        _pending_reconciles = 0
    except Exception:
        LOG_CURRENT_EXCEPTION()
        _pending = None


def clear():
    """Drop all markers (used by tests; not wired to a game event)."""
    global _pending
    _pending = None
    _done.clear()


def clear_fieldmod(veh_int_cd):
    """Drop this vehicle's marker iff it's a field-mod marker. Called after a click on a
    field-mod done tick opens the Field Modifications page -- clicking the tick IS the
    visit, so the marker is cleared "after visiting". Guarded + kind-scoped: a tech-tree
    or tier-XI marker (or no marker) is left untouched."""
    try:
        veh = int(veh_int_cd or 0)
        rec = _done.get(veh)
        if rec is not None and rec.get("kind") == FIELDMOD:
            del _done[veh]
    except Exception:
        LOG_CURRENT_EXCEPTION()


def decorate(model, snapshot):
    """Promote a confirmed pending click to this vehicle's marker, then inject that
    vehicle's marker into the built model. Mutates `model` in place; guarded so any
    failure leaves the model untouched."""
    global _pending, _pending_reconciles
    try:
        if snapshot is None or model is None:
            return
        veh = int(getattr(snapshot, "vehicle_int_cd", 0) or 0)
        if not veh:
            # Never key markers on the sentinel 0 (see record()).
            return

        # 1) Promote a pending record IF it belongs to this vehicle and is now done.
        #    A pending that never confirms (cancelled/failed click) is dropped after
        #    _PENDING_MAX_RECONCILES reconciles so it doesn't linger and false-promote.
        if _pending is not None and _pending["veh_int_cd"] == veh:
            if _is_done(_pending, snapshot):
                _done[veh] = _pending
                _pending = None
                _pending_reconciles = 0
            else:
                _pending_reconciles += 1
                if _pending_reconciles > _PENDING_MAX_RECONCILES:
                    _pending = None
                    _pending_reconciles = 0

        # 2) Retire a marker whose follow-up action is now complete. A tech-tree module
        #    marker self-clears once the module is owned (bought + mounted via the "buy +
        #    mount" click); everything else is retired elsewhere (field-mods on page-open,
        #    tier-XI never auto-retire). Degrade-safe: unreadable ownership keeps the marker.
        rec = _done.get(veh)
        if rec is not None and _is_retired(rec, snapshot):
            del _done[veh]
            rec = None

        # 3) Inject this vehicle's marker (if any) into the model.
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
            # Positive evidence: a researched item STAYS in tech_unlocks with
            # researched=True, so match by presence + flag. A degraded/empty read
            # leaves the loop un-run and returns False (defers -- never false-promotes
            # on missing data).
            for u in (snap.tech_unlocks or []):
                if u.int_cd == item_id:
                    return bool(getattr(u, "researched", False))
            return False
        if kind == FIELDMOD:
            for s in (snap.field_mod_steps or []):
                if getattr(s, "step_id", None) == item_id:
                    return bool(getattr(s, "unlocked", False))
            return False
        if kind == SKILLTREE:
            # Two independent confirmations, EITHER suffices (each guards its own degraded
            # read, so neither false-promotes on missing data):
            #   1) Positive count evidence: skilltree_done grew since the click -> a node
            #      was received. This is the ONLY confirmation when unlocking the node
            #      collapses the frontier to empty while the tree is still incomplete
            #      (the absence test can't confirm an empty list).
            #   2) Absence (legacy): the node left a NON-EMPTY frontier. Still valid for
            #      the common case and covers a degraded done-count read.
            done_now = int(getattr(snap, "skilltree_done", 0) or 0)
            if done_now > int(rec.get("done_count", 0) or 0):
                return True
            avail = [getattr(s, "step_id", None) for s in (snap.skilltree_available or [])]
            return bool(avail) and (item_id not in avail)
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return False


# --- retirement: is a confirmed marker's follow-up action now complete? ------

def _is_retired(rec, snap):
    """True if this marker should be dropped because its follow-up completed. Only a
    tech-tree MODULE marker self-retires here -- once the module is owned (the "buy +
    mount" click bought it). Vehicle markers keep opening Research (you can't mount a
    tank), field-mod markers are retired on page-open (clear_fieldmod), and tier-XI chips
    never auto-retire. Degrade-safe: a missing/unreadable ownership read returns False so
    the marker persists rather than vanishing on bad data (mirrors _is_done)."""
    try:
        if rec.get("kind") != TECHTREE or rec.get("category") != Category.MODULE:
            return False
        item_id = rec["item_id"]
        for u in (snap.tech_unlocks or []):
            if u.int_cd == item_id:
                return bool(getattr(u, "owned", False))
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return False


# --- synthetic view objects (reuse domain shapes so the bridge marshal is unchanged) ---

def _make_tick(rec):
    """A done tech-tree / field-mod tick: pinned to xp_position 0, marked done,
    always shown bright (it's completed). The `.done` attribute drives the JS
    checkmark + open-screen click; it is read via getattr in the marshal."""
    # done drives the JS checkmark + open-screen click; int_cd lets the (engine-bound)
    # bridge look up the item's live credits buy price + ownership at marshal time
    # (kept a plain int so this module stays engine-free and unit-testable).
    # action_id is the id the JS "buy + mount" click needs: only a MODULE done tick
    # uses it (WGModResearch.js gates the buyMount branch on it); field-mod/vehicle
    # done ticks open a screen and ignore it, so keep theirs 0.
    is_module = rec["category"] == Category.MODULE
    return t.Tick(
        xp_position=0, category=rec["category"], icon=rec["icon"], name=rec["name"],
        xp_gained=0, xp_required=0, affordable=True, completed=True,
        locked=False, level=rec["level"], effect=rec["effect"],
        kind_label=rec["kind_label"], done=True, int_cd=rec["item_id"],
        action_id=rec["item_id"] if is_module else 0)


def _make_chip(rec):
    """A done tier-XI chip: a ProgressionStep marked done, prepended so it sorts
    first in the next-available row."""
    return t.ProgressionStep(
        step_id=rec["item_id"], name=rec["name"], icon=rec["icon"],
        xp_cost=rec["xp_cost"], unlocked=True, description=rec["effect"],
        category=rec["category"], done=True)
