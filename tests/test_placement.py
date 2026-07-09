# -*- coding: utf-8 -*-
from wgmod_research.domain.placement import choose_placement, INJECT, WAIT, BLOCKED

# ViewModels are opaque to the pure decision; represent them as sentinel strings and
# mark the "already claimed by another mod" ones via a set the predicate closes over.
def _pred(occupied):
    return lambda vm: vm in occupied


def test_preferred_free_injects_preferred():
    vms = {"crew": "crewVM", "loadout": "loadoutVM"}
    assert choose_placement(["crew", "loadout"], vms, _pred(set())) == (INJECT, "crew")


def test_preferred_unmounted_waits():
    assert choose_placement(["crew", "loadout"], {}, _pred(set())) == (WAIT, None)


def test_fallback_free_but_preferred_pending_still_waits():
    # loadout is free, but crew hasn't mounted yet -> do NOT commit to the fallback;
    # wait so we always prefer the higher-priority sub-view when it arrives.
    vms = {"loadout": "loadoutVM"}
    assert choose_placement(["crew", "loadout"], vms, _pred(set())) == (WAIT, None)


def test_preferred_foreign_falls_back_when_fallback_free():
    vms = {"crew": "crewVM", "loadout": "loadoutVM"}
    assert choose_placement(["crew", "loadout"], vms, _pred({"crewVM"})) == (INJECT, "loadout")


def test_preferred_foreign_fallback_unmounted_waits():
    vms = {"crew": "crewVM"}
    assert choose_placement(["crew", "loadout"], vms, _pred({"crewVM"})) == (WAIT, None)


def test_all_candidates_foreign_blocked():
    vms = {"crew": "crewVM", "loadout": "loadoutVM"}
    assert choose_placement(
        ["crew", "loadout"], vms, _pred({"crewVM", "loadoutVM"})) == (BLOCKED, None)


def test_single_candidate_free():
    assert choose_placement(["crew"], {"crew": "c"}, _pred(set())) == (INJECT, "crew")


def test_single_candidate_foreign_blocked():
    assert choose_placement(["crew"], {"crew": "c"}, _pred({"c"})) == (BLOCKED, None)


def test_none_valued_vm_treated_as_unmounted():
    # An explicit None (not just a missing key) also means "not mounted yet".
    assert choose_placement(["crew", "loadout"], {"crew": None}, _pred(set())) == (WAIT, None)
