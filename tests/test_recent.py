# -*- coding: utf-8 -*-
"""Session "done" marker store: optimistic record + reconcile-on-decorate.

recent.py is engine-free (debug_utils import degrades to a no-op), so it imports and
runs in the Python 3.13 test env against fabricated snapshots -- unlike the adapter
proper, which needs the live client."""
from wgmod_research.adapter import recent
from wgmod_research.domain import types as t


def _unlock(int_cd, researched=False):
    return t.UnlockItem(int_cd=int_cd, name="u%d" % int_cd, icon="u%d.png" % int_cd,
                        xp_cost=1000, kind="module", researched=researched,
                        prereqs_met=True)


def _step(sid, unlocked=False):
    return t.ProgressionStep(step_id=sid, name="s%d" % sid, icon="s%d.png" % sid,
                             xp_cost=2000, unlocked=unlocked)


def _snap(veh_int_cd, tech_unlocks=None, field_mod_steps=None, skilltree_available=None,
          is_skill_tree=False):
    return t.VehicleSnapshot(
        tier=9, is_elite=False, vehicle_xp=0, free_xp=0,
        tech_unlocks=tech_unlocks, field_mod_steps=field_mod_steps,
        is_skill_tree=is_skill_tree, skilltree_available=skilltree_available,
        vehicle_int_cd=veh_int_cd)


def _model(mode=t.Mode.TECH_TREE, ticks=None, avail=None):
    return t.ResearchProgressModel(
        mode=mode, scale_min=0, scale_max=0, fill_vehicle=0, fill_free=0,
        ticks=ticks if ticks is not None else [], avail_upgrades=avail or [])


def setup_function(_):
    recent.clear()


def test_techtree_confirmed_surfaces_done_tick():
    recent.record(recent.TECHTREE, 100, 5, name="Gun", icon="g.png", category="module")
    # item 5 is now researched -> no longer among remaining unlocks.
    snap = _snap(100, tech_unlocks=[_unlock(5, researched=True)])
    model = _model(ticks=[])
    recent.decorate(model, snap)
    assert len(model.ticks) == 1
    tick = model.ticks[0]
    assert tick.done is True
    assert tick.xp_position == 0
    assert tick.category == "module"
    assert tick.name == "Gun"


def test_cancel_leaves_no_marker():
    recent.record(recent.TECHTREE, 100, 5, name="Gun", icon="g.png", category="module")
    # Confirm was cancelled: item 5 still pending (not researched) -> nothing surfaces.
    snap = _snap(100, tech_unlocks=[_unlock(5, researched=False)])
    model = _model(ticks=[])
    recent.decorate(model, snap)
    assert model.ticks == []


def test_pending_scoped_to_its_vehicle():
    recent.record(recent.TECHTREE, 100, 5, name="Gun", icon="g.png", category="module")
    # A different vehicle is selected before the sync -> pending is not promoted.
    snap = _snap(200, tech_unlocks=[_unlock(5, researched=True)])
    model = _model(ticks=[])
    recent.decorate(model, snap)
    assert model.ticks == []


def test_marker_shows_only_on_its_vehicle():
    recent.record(recent.TECHTREE, 100, 5, name="Gun", icon="g.png", category="module")
    recent.decorate(_model(ticks=[]), _snap(100, tech_unlocks=[_unlock(5, researched=True)]))
    # Now viewing another vehicle: no marker of veh 100 bleeds onto veh 300.
    model = _model(ticks=[])
    recent.decorate(model, _snap(300, tech_unlocks=[_unlock(9)]))
    assert model.ticks == []


def test_replace_latest_only_per_vehicle():
    recent.record(recent.TECHTREE, 100, 5, name="Gun", icon="g.png", category="module")
    recent.decorate(_model(ticks=[]), _snap(100, tech_unlocks=[_unlock(5, researched=True)]))
    # Research a second item on the same vehicle -> it replaces the first marker.
    recent.record(recent.TECHTREE, 100, 6, name="Turret", icon="t.png", category="module")
    snap = _snap(100, tech_unlocks=[_unlock(5, researched=True), _unlock(6, researched=True)])
    model = _model(ticks=[])
    recent.decorate(model, snap)
    assert len(model.ticks) == 1
    assert model.ticks[0].name == "Turret"


def test_fieldmod_confirmed_surfaces_done_tick():
    recent.record(recent.FIELDMOD, 100, 7, name="FM", icon="fm", category="fieldmod", level=3)
    snap = _snap(100, field_mod_steps=[_step(7, unlocked=True)])
    model = _model(mode=t.Mode.FIELD_MODS, ticks=[])
    recent.decorate(model, snap)
    assert len(model.ticks) == 1
    assert model.ticks[0].done is True
    assert model.ticks[0].level == 3
    assert model.ticks[0].category == "fieldmod"


def test_skilltree_confirmed_prepends_done_chip():
    recent.record(recent.SKILLTREE, 100, 42, name="Perk", icon="p.png", category="Mechanic")
    # Node 42 no longer available (it was unlocked); node 43 still is.
    snap = _snap(100, is_skill_tree=True, skilltree_available=[_step(43)])
    existing = t.ProgressionStep(step_id=43, name="next", icon="n.png", xp_cost=10000,
                                 unlocked=False)
    model = _model(mode=t.Mode.SKILL_TREE, avail=[existing])
    recent.decorate(model, snap)
    assert len(model.avail_upgrades) == 2
    assert model.avail_upgrades[0].done is True     # done chip sorted FIRST
    assert model.avail_upgrades[0].step_id == 42
    assert model.avail_upgrades[1].step_id == 43


def test_marker_not_injected_outside_tick_modes():
    recent.record(recent.TECHTREE, 100, 5, name="Gun", icon="g.png", category="module")
    snap = _snap(100, tech_unlocks=[_unlock(5, researched=True)])
    model = _model(mode=t.Mode.COMPLETE, ticks=[])
    recent.decorate(model, snap)
    assert model.ticks == []
