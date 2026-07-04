# Research: Make done tech-tree & field-mod ticks actionable and self-clearing

_Submitted: "Make done tech tree and field mod ticks clickable. Tech tree - purchase and mount, field mods - open field mods page. When tech tree item is purchased and mounted, remove its done tick. Field mod tick must be removed after visiting the field mods page." · Status: shipped (commit 1fae732 "feat: actionable, self-clearing done ticks")_

> Note: recreated by the plan saver after the fact — the original was captured as
> an untracked file and lost when the implementing session pruned the backlog
> entry. The authoritative record of the implementation is commit 1fae732; consult
> its diff for the final shape.

## Summary
Turn the green-check "done" markers from passive navigation into a completing
action, and make them clear themselves once the follow-up is done:
- **Tech-tree done tick** → *purchase and mount* the researched module (one click)
  instead of just opening the research screen. Remove the marker once the item is
  actually bought **and** mounted.
- **Field-mod done tick** → open the Field Modifications page (unchanged action),
  then remove the marker after the visit.

Done markers were already clickable — the change was *what they do* and *when they
disappear*.

## Findings

### Prior done-marker behaviour
Session-scoped, in-memory, one marker per vehicle:
- `adapter/recent.py` — `_done[veh_int_cd]` holds the single marker. `record()`
  (recent.py:51) stashes optimistically on click; `decorate(model, snapshot)`
  (recent.py:87) promotes a confirmed pending into `_done` and injects it each push.
  `_is_done()` (recent.py:132) distinguishes kinds: TECHTREE by presence +
  `researched=True`; FIELDMOD by presence + `unlocked=True`.
- Kind decided at record time in `bridge/gameface_bridge.py` `_record_click` (~:284).
- Domain flag `Tick.done` + `Tick.int_cd` (`domain/types.py:37`); `int_cd` carried
  only on a done marker (for the live price lookup).
- Marshal: `TickVM.done` + `TickVM.price` (view_models.py props 15/16); JS recovers
  tech-tree vs field-mod from the tick's `category`.
- Click previously (`WGModResearch.js` done branch ~:1330): `openResearch` for
  tech-tree, `openFieldMods` for field-mod — both no-arg navigation.

### Action APIs (verified against decompiled EU 2.3 client)
Through WG's items-actions factory `gui.shared.gui_items.items_actions.factory`
(aliased `actions_factory` in `adapter/actions.py`, already used for `UNLOCK_ITEM`
and `PURCHASE_POST_PROGRESSION_STEPS`):
- **Buy + mount a module in one call**:
  `actions_factory.doAction(actions_factory.BUY_AND_INSTALL_AND_SELL_ITEM, module_int_cd, veh.intCD)`
  — the path WoT's own "Buy and equip" menu uses (`research_cm_handlers.py:42`).
  `doAction` is `@adisp_process`, runs its own credits-exchange dialog, never raises.
  (Do NOT use `BUY_AND_INSTALL_ITEM` — not in the factory's `_ACTION_MAP`.)
- **Install-only** (already owned): `INSTALL_ITEM` → `(module_cd, veh.intCD)`.
- **Field-mods page**: already opened via
  `event_dispatcher.showVehPostProgressionView(veh.intCD)` (actions.py:189).

The module int_cd = `rec["item_id"]` (TECHTREE marker's global int_cd), so the buy
handler can read it server-side from `recent._done[veh]` — no new JS arg needed.

## Suggested approach (as captured)
- **A. Tech-tree buy+mount** — new `CMD.BUY_MOUNT` routed from the tech-tree done
  branch; `_on_buy_mount` reads the current vehicle's marker and calls a new
  `actions.buy_and_mount()` → `BUY_AND_INSTALL_AND_SELL_ITEM`, with fall-back to
  `open_research()`.
- **B. Tech-tree removal** — new removal phase in `recent.decorate()` (previously
  inject-only, never retired): drop `_done[veh]` once a module marker is owned+mounted
  (needs an "installed on vehicle" read; owned derivable from `isInInventory`).
  Guarded-degrade: a missing/empty read must not trigger removal.
- **C. Field-mod clear** — clear the FIELDMOD marker on the open-page click
  (clicking is visiting), via a new guarded `recent.clear_fieldmod(veh)`.

## Open questions raised at capture
- **Vehicle done ticks** — a researched next vehicle is also a TECHTREE marker
  (`CAT.VEHICLE`); buy+mount is module-only (can't mount a tank). Recommended
  restricting buy+mount to `CAT.MODULE` ticks.
- "Purchased AND mounted" vs "purchased" as the removal condition.
- Confirm the "installed on vehicle" API live before wiring.

## Outcome
Shipped in commit 1fae732. See the diff for how the open questions were resolved.
