# Session Handoff — Research-Progress Bar (Phase 2, in-game working)

_Date: 2026-06-28. Supersedes the original PHASE2-HANDOFF.md, which predates the
EU-vs-RU client correction. Read tools/dev/README.md for the dev loop._

## TL;DR — where we are
The mod **works in-game** on WoT **EU 2.3.0.1**. A research-progress bar renders in
the Garage from live data: tech-tree (green vehicle-XP fill + yellow ticks),
field-modifications (purple ticks), and a "Fully researched" complete state — all
verified via the debug REPL + visually.

**Live refresh is now VERIFIED** (incl. the battle-exit cycle): garage → switch
tanks → play a battle → exit → switch tanks again, all firing `[wgmod] onChanged
-> refresh ok=True`. (Current HEAD: `c54ac37`.) The next step is the remaining v1
work below — start with the owner-requested locked/prereqs-unmet ticks (item 2).

## Architecture (as built, EU 2.3)
- **Domain (engine-free, tested):** `wgmod_research/domain` — `VehicleSnapshot` →
  `build_model` → `ResearchProgressModel` with modes `TECH_TREE` / `FIELD_MODS` /
  `COMPLETE`, two-segment fill (`fill_vehicle`, `fill_free`), `ticks[]`. 15 pytest
  tests (`python3 -m pytest -q`).
- **Adapter (`wgmod_research/adapter/engine_adapter.py`):** live client →
  `VehicleSnapshot`. Tech unlocks via `vehicle.getUnlocksDescrs()` →
  `(idx, xpCost, intCD, prereqs)`; module vs vehicle via
  `getTypeOfCompactDescr/GUI_ITEM_TYPE.VEHICLE`; field mods via
  `vehicle.postProgression.iterOrderedSteps()` (`getPrice().xp`, `isReceived()`).
  Uses `dependency.instance(IItemsCache)`. Each read guarded → safe default.
- **Mount (the tricky part):** WoT 2.3 loads only `.wotmod`. OpenWG's JS injector
  (`gui/gameface/js/index.js`) injects a mod's assets only for hangar **sub-views**
  carrying a `ModInjectModel`. So `mod_wgmod.py` patches
  `HangarVehicleParamsPresenter._onLoading` and calls
  `gameface_bridge.attach(host_vm)` →
  `openwg_gameface.gf_mod_inject(host_vm, "WGModResearch", styles=[…], modules=[…])`
  (loads our JS into the hangar document) and
  `host_vm._addViewModelProperty("wgResearch", ResearchVM())` (our data model).
- **Data → JS:** `WGModResearch.js` (ES module) reads the model via
  `ModelObserver("WGModResearch")` → `model.wgResearch` (+ `ticks[]`, elements as
  `item.value.*`) and renders the bar. Updates: `gameface_bridge.push()` writes via
  `rvm.transaction()` and nudges the host sub-view; subscription lives in the bridge
  (`install_vehicle_listener`) with a **strong global ref** (WG `Event` is weak-ref).

### Key files
```
src/res/scripts/client/gui/mods/mod_wgmod.py                 # entry: patch presenter
src/res/scripts/client/wgmod_research/adapter/engine_adapter.py
src/res/scripts/client/wgmod_research/bridge/gameface_bridge.py   # ViewModels + attach/push/refresh/listener
src/res/scripts/client/wgmod_research/domain/{types,builder,resolvers/*}.py
src/res/gui/gameface/mods/drizzer14/WGModResearch/{WGModResearch.js,.css}
build/deploy_wotmod.py        # clean build+deploy (Python 2.7, client CLOSED)
tools/dev/                    # debug REPL server + client + README (NOT shipped)
docs/superpowers/research/decompiled-findings.md   # verified EU symbols
```

## Remaining v1 work
1. **Verify live refresh** (immediate, above) and the full mode matrix (graceful
   degradation if a read fails).
2. **Visual polish** (Task: design system): game Gameface fonts/colors; real hover
   **tooltips** (name + XP); category **icons**; position/size. Owner decision:
   ticks should **also show locked (prereqs-unmet)** items, not just affordability —
   so propagate `UnlockItem.prereqs_met` → `Tick` → `TickVM` → JS and style locked
   ticks distinctly (currently `Tick` has no `prereqs_met` field; the techtree
   resolver drops it).
3. **Finalize packaging & docs** (Task): `meta.xml` name/id (consider
   `com.drizzer14.research_progress` / "Research Progress"); declare OpenWG Gameface
   as a required dependency in README; deprecate `build/deploy_dev.py` (loose
   res_mods does not load in 2.3) pointing to `deploy_wotmod.py`; document the debug
   mod; build the distributable.

## Gotchas / lessons (don't relearn these)
- **Wrong client trap:** the StranikS-Scan default branch is **MirTankov/Lesta RU**,
  a different client (it has "Paragons", lacks `RandomHangar`). Use branch **`2.3`**
  (EU). "Paragons / elite milestones / level-150" do **not** exist in EU — the elite
  feature was dropped; v1 is the XP-driven bar.
- **WoT 2.3 loads only `.wotmod`** from `mods/<version>/`; `res_mods` outranks it, so
  a stale loose copy SHADOWS the package and the client silently ignores the mod.
  Always deploy via `deploy_wotmod.py` (auto-cleans), with the **client closed**.
- **`g_currentVehicle.onChanged` is a STRONG-ref delegate `list`** (not a weak-ref
  Event — the earlier `1e11b90` theory was wrong). The real trap: WoT tears down and
  rebuilds the hangar space on **battle exit**, repopulating that list with WG's own
  presenters while dropping any handler that doesn't re-subscribe. WG presenters
  re-add themselves on each hangar load; so must we. `install_vehicle_listener()` is
  self-healing (re-adds iff not in the list) and is called from the patched
  `_onLoading` on every mount. Don't go back to a once-only subscription.
- **Field-mod tick names are empty** — the `step.action` label lookup in
  `engine_adapter._step_label` doesn't resolve; fix when wiring tooltips.
- **Special "7×7" tanks** (T57 Heavy 7×7, etc.) use a hangar without
  `HangarVehicleParamsPresenter`, so the bar won't mount there. If that matters,
  pick a more universally-present sub-view as the inject host (or accept the gap).
- Mod module isn't importable as `mod_wgmod` (loader namespace); the bridge module
  IS importable (`wgmod_research.bridge.gameface_bridge`) — use it for REPL pokes.
- The session **scratchpad is ephemeral**; durable dev tools now live in `tools/dev/`.
  Re-clone the EU decompiled source when needed (see tools/dev/README.md).
