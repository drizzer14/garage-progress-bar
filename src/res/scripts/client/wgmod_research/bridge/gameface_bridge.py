# -*- coding: utf-8 -*-
"""Bridge: attach our Gameface widget to a hangar sub-view and push the model.

OpenWG's JS injector (gui/gameface/js/index.js) scans hangar SUB-views for a
`ModInjectModel` and loads the listed assets into the hangar document. So we
inject onto a sub-view's ViewModel (HangarVehicleParamsPresenter) and also hang
our own data model on it (property `wgResearch`), which the widget JS reads via
ModelObserver("WGModResearch").

ViewModel API (string/number/array, transaction, addViewModel, _addViewModelProperty)
was verified live in the EU 2.3 client.
"""
import json

import BigWorld
from CurrentVehicle import g_currentVehicle
from helpers import dependency
from skeletons.gui.game_control import ILoadoutController
from skeletons.gui.shared import IItemsCache

from wgmod_research._compat import LOG_CURRENT_EXCEPTION, LOG_NOTE
from wgmod_research.adapter import engine_adapter
from wgmod_research.adapter import actions
from wgmod_research.adapter import i18n
from wgmod_research.adapter import recent
from wgmod_research.domain.builder import build_model, bar_visible
from wgmod_research.domain.constants import Category
from wgmod_research.bridge import mod_settings
from wgmod_research.bridge.view_models import ResearchVM, TickVM, UpgradeVM
from wgmod_research.bridge.wulf_args import (
    map_get as _map_get, cmd_int_arg as _cmd_int_arg, cmd_xy_arg as _cmd_xy_arg)
import openwg_gameface

WIDGET_NAME = "WGModResearch"
DATA_PROP = "wgResearch"
COUI = "coui://gui/gameface/mods/14th_ua/WGModResearch"

# (host_vm, rvm) for the currently-mounted widget. Importable so the entry point
# and the dev REPL can drive refreshes without poking module-private state.
_active = None

# Engine events we subscribe to. WoT's Events store STRONG refs to their delegates,
# but the battle entry/exit teardown rebuilds the hangar space -- repopulating the
# vehicle/loadout/lobby event lists with WG's own presenters while dropping ours. So
# subscribing once is not enough: install_all_listeners() re-arms on every hangar
# mount, membership-checked (not a 'did we subscribe' flag -- the flag stayed set
# while the event had silently lost our handler). The stats + colorblind events are
# long-lived DI singletons NOT torn down on battle exit, so re-arming them is
# unnecessary but harmless; kept for symmetry and hot-reload safety. Our handlers are
# module-level functions, so their identity is already stable across re-arms -- the
# membership check needs no extra caching. See _LISTENERS / install_all_listeners.

# Set while a coalesced refresh is already queued for the next tick, so a burst of
# onSyncCompleted fires (one server action often triggers several) collapses to a
# single deferred refresh(). See _schedule_refresh.
_refresh_pending = False

# Items-cache sync reasons the bar can safely IGNORE -- pure account/economy noise
# that never changes the XP state, fill, or ticks. Everything else (inventory,
# vehicle, stats, init, and any unknown/future reason) refreshes the bar. Matched
# as strings and FAIL-OPEN, so we couple to no fragile reason-constant imports and
# only ever skip the clearly-irrelevant syncs.
_IGNORED_SYNC_REASONS = frozenset(("shop", "clan"))


def _on_vehicle_changed(*args, **kwargs):
    try:
        ok = refresh()
        LOG_NOTE("[wgmod] onChanged -> refresh ok=%s" % ok)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_interactor_updated(*args, **kwargs):
    # The loadout interactor was set (tank-setup / ammo overlay opened) or cleared
    # (back to the plain garage). Re-push so the bar hides / shows accordingly.
    try:
        refresh()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_lobby_state_changed(*args, **kwargs):
    # The visible lobby view changed (garage <-> playlists / other views). A view
    # change does not necessarily re-mount the sub-view, so re-push here so the bar
    # hides when we leave the plain garage and shows again when we return.
    try:
        refresh()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_settings_changed(diff):
    # settingsCore.onSettingsChanged(diff): a dict of the settings that changed. Only
    # re-push when the color-blind flag is among them, so we don't refresh on every
    # unrelated settings tweak. Guarded and fail-open (refresh if the diff is
    # unreadable) so a settings-API shape change can't silently freeze the palette.
    try:
        from account_helpers.settings_core.settings_constants import GRAPHICS
        if diff is None or GRAPHICS.COLOR_BLIND in diff:
            refresh()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _reason_affects_bar(reason):
    """True if this items-cache sync reason can change what the bar shows. Refreshes
    for everything except the known-irrelevant reasons (_IGNORED_SYNC_REASONS),
    FAIL-OPEN on unknown/empty so a new or unrecognized reason still refreshes."""
    try:
        if not reason:
            return True
        return str(reason) not in _IGNORED_SYNC_REASONS
    except Exception:
        return True


def _on_sync_completed(*args, **kwargs):
    # IItemsCache.onSyncCompleted(updateReason, invalidItems). Use *args so any
    # live-arity drift can't raise. Skip clearly-irrelevant reasons, then coalesce.
    try:
        reason = args[0] if args else ""
        if not _reason_affects_bar(reason):
            return
        _schedule_refresh()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _schedule_refresh():
    """Coalesce a refresh onto the next tick. A single server action often fires
    onSyncCompleted several times; the pending flag collapses them to one push.
    Deferring also fixes ordering: CurrentVehicle rebuilds g_currentVehicle.item
    in its OWN onSyncCompleted handler, so reading next tick guarantees veh.xp is
    fresh (not one event behind freeXP). BigWorld.callback runs on the main thread,
    so the push transaction is safe -- never use a timer thread here."""
    global _refresh_pending
    if _refresh_pending:
        return
    _refresh_pending = True
    try:
        BigWorld.callback(0.0, _do_scheduled_refresh)
    except Exception:
        # Couldn't schedule -> clear the flag and refresh inline as a fallback.
        _refresh_pending = False
        LOG_CURRENT_EXCEPTION()
        try:
            refresh()
        except Exception:
            LOG_CURRENT_EXCEPTION()


def _do_scheduled_refresh():
    global _refresh_pending
    _refresh_pending = False
    try:
        refresh()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _bar_visible():
    """True only in the plain garage. The tank-setup overlays (shells/ammo,
    consumables, equipment, optional devices) keep the vehicle-params panel mounted
    to show stat changes, so the bar must be hidden explicitly while one is open.
    A live loadout interactor is exactly that 'a setup overlay is open' signal.
    Guarded -> True (fail open: show the bar) if the controller is unreadable."""
    try:
        return dependency.instance(ILoadoutController).interactor is None
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return True


def _in_garage():
    """True only when the plain garage view is the visible lobby state. The
    vehicle-params sub-view we inject into stays mounted on other lobby views
    (notably the playlists / battle-type selection screen), so the bar must be
    hidden explicitly there. The lobby state machine's visible leaf state carries
    a hierarchical id; the plain garage is the DefaultHangarState, whose id ends in
    'hangar/{root}' (verified live: 'subScope/subLayer/hangar/{root}'). '{root}' is
    defined exactly once in the client -- the sole default child of the hangar
    state -- so this uniquely identifies the plain garage and excludes the full
    'All Vehicles' browser ('.../hangar/allVehicles'), the playlists screen
    ('.../editVehiclePlaylists'), and every other view.

    Guarded -> False (FAIL CLOSED: show ONLY in the confirmed garage) if the state
    machine is missing or unreadable. This is the opposite default from
    _bar_visible() by design -- a positive garage confirmation is required."""
    try:
        from gui.Scaleform.lobby_entry import getLobbyStateMachine
        machine = getLobbyStateMachine()
        if machine is None:
            return False
        state = machine.visibleState
        if state is None:
            return False
        state_id = state.getStateID() or ""
        return state_id.endswith("hangar/{root}")
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return False


# --- engine event subscriptions -------------------------------------------------
# Each entry names the HOLDER object that owns the Event (resolved lazily each mount,
# so a not-yet-ready provider just skips and is retried) and the attribute the Event
# lives on. Handlers are the stable module-level functions above. install_all_listeners
# arms them all; see the block comment near _active for the re-arm rationale.
#
# We subscribe via getattr/+=/setattr (i.e. `holder.attr += handler`), NOT `event +=
# handler` on a local: WoT's Event augmented-add does not reliably mutate the shared
# object in place, so the result MUST be stored back onto the attribute or the
# subscription is silently lost (the bar then never updates).

def _vehicle_holder():
    return g_currentVehicle


def _loadout_holder():
    return dependency.instance(ILoadoutController)


def _lobby_holder():
    from gui.Scaleform.lobby_entry import getLobbyStateMachine
    return getLobbyStateMachine()  # None until the lobby state machine exists


def _stats_holder():
    return dependency.instance(IItemsCache)


def _colorblind_holder():
    from skeletons.account_helpers.settings_core import ISettingsCore
    return dependency.instance(ISettingsCore)


# (label, holder-getter, event-attribute, handler) -- what the bar listens to.
#   vehicle : vehicle-selection changes
#   loadout : tank-setup (ammo) overlay open/close -> hide/show the bar
#   lobby   : garage <-> other lobby views -> hide off the plain garage
#   stats   : items-cache syncs (free-XP convert, research/field-mod buys, XP, prestige)
#   colorblind : WoT's color-blind toggle -> re-color live
_LISTENERS = (
    ("vehicle", _vehicle_holder, "onChanged", _on_vehicle_changed),
    ("loadout", _loadout_holder, "onInteractorUpdated", _on_interactor_updated),
    ("lobby state", _lobby_holder, "onVisibleRouteChanged", _on_lobby_state_changed),
    ("stats", _stats_holder, "onSyncCompleted", _on_sync_completed),
    ("colorblind", _colorblind_holder, "onSettingsChanged", _on_settings_changed),
)


def _arm(label, get_holder, attr, handler):
    """Subscribe `handler` to holder.<attr> iff not already present, storing the
    augmented Event back onto the attribute (see the note above). Self-healing +
    idempotent; guarded so a not-yet-ready holder just skips (retried next mount)."""
    try:
        holder = get_holder()
        if holder is None:
            return
        event = getattr(holder, attr)
        if event is not None and handler not in event:
            event += handler
            setattr(holder, attr, event)
            LOG_NOTE("[wgmod] %s listener (re)armed" % label)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def install_all_listeners():
    """(Re)arm every engine listener. Safe to call on every hangar mount -- the battle
    exit teardown drops the hangar-scoped delegates and this restores them."""
    for entry in _LISTENERS:
        _arm(*entry)


# --- Reverse channel: handlers for JS click commands -------------------------
# The widget JS invokes the ResearchVM commands when a clickable tick is clicked.
# Each handler reads the tick identity Wulf delivered and delegates to the
# write-side `actions` module (which touches the game's research / unlock APIs).
# After a successful action the game fires onSyncCompleted, which the stats
# listener already turns into a bar refresh -- so handlers do not refresh here.

def _record_click(int_cd):
    """Capture the item just clicked for the session "done" marker BEFORE the async
    research fires (a researched item vanishes from the snapshot afterwards). Reads a
    fresh snapshot, classifies by what the id actually is, and stashes display data.
    Guarded: a failure here must never block the actual research action."""
    try:
        snap = engine_adapter.build_snapshot()
        if snap is None:
            return
        veh = getattr(snap, "vehicle_int_cd", 0) or 0
        # Tech-tree unlock (global int_cd)?
        for u in (snap.tech_unlocks or []):
            if getattr(u, "int_cd", None) == int_cd and not getattr(u, "researched", False):
                recent.record(recent.TECHTREE, veh, int_cd,
                              name=u.name, icon=u.icon, category=u.kind,
                              kind_label=getattr(u, "kind_label", ""),
                              xp_cost=getattr(u, "xp_cost", 0))
                return
        # Tier-XI upgrade node (frontier chip; per-vehicle step_id)?
        if getattr(snap, "is_skill_tree", False):
            for s in (snap.skilltree_available or []):
                if getattr(s, "step_id", None) == int_cd:
                    recent.record(recent.SKILLTREE, veh, int_cd,
                                  name=s.name, icon=s.icon,
                                  category=getattr(s, "category", ""),
                                  effect=getattr(s, "description", ""),
                                  xp_cost=getattr(s, "xp_cost", 0))
                    return
        # Field-mod step (per-vehicle step_id).
        for s in (snap.field_mod_steps or []):
            if getattr(s, "step_id", None) == int_cd and not getattr(s, "unlocked", False):
                recent.record(recent.FIELDMOD, veh, int_cd,
                              name=s.name, icon=s.icon, category=Category.FIELDMOD,
                              level=getattr(s, "level", 0),
                              effect=getattr(s, "description", ""),
                              xp_cost=getattr(s, "xp_cost", 0))
                return
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_research_unlock(*args):
    try:
        int_cd = _cmd_int_arg(args)
        LOG_NOTE("[wgmod] researchUnlock intCD=%s" % int_cd)
        if int_cd:
            _record_click(int_cd)
            actions.research_unlock(int_cd)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_unlock_field_mod(*args):
    try:
        step_id = _cmd_int_arg(args)
        LOG_NOTE("[wgmod] unlockFieldMod stepID=%s" % step_id)
        if step_id:
            _record_click(step_id)
            actions.unlock_field_mod(step_id)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_open_skill_tree(*args):
    try:
        LOG_NOTE("[wgmod] openSkillTree")
        actions.open_skill_tree()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_open_research(*args):
    try:
        LOG_NOTE("[wgmod] openResearch")
        actions.open_research()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_buy_mount(*args):
    # Click on a "done" tech-tree MODULE marker: buy + mount the module. No _record_click
    # -- the marker already exists; the buy completes it and recent's removal phase retires
    # it once it reads as owned on the next sync.
    try:
        int_cd = _cmd_int_arg(args)
        LOG_NOTE("[wgmod] buyMount intCD=%s" % int_cd)
        if int_cd:
            actions.buy_and_mount(int_cd)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_open_field_mods(*args):
    try:
        LOG_NOTE("[wgmod] openFieldMods")
        actions.open_field_mods()
        # Clicking the field-mod done tick IS the visit -> drop its marker now. Guarded +
        # kind-scoped (a no-op for any other marker). Read the current vehicle intCD the
        # same way the read layer does.
        try:
            if g_currentVehicle.isPresent():
                recent.clear_fieldmod(g_currentVehicle.item.intCD)
        except Exception:
            LOG_CURRENT_EXCEPTION()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_set_position(*args):
    try:
        x, y = _cmd_xy_arg(args)
        # The widget marks its default-position SEED with seed=1 (measured while the bar
        # sits at its CSS default). That value becomes the reset target; a plain drag omits
        # it. See mod_settings.set_position / _store_default_position.
        is_seed = bool(_map_get(args[0], "seed")) if args else False
        LOG_NOTE("[wgmod] setPosition x=%s y=%s seed=%s" % (x, y, is_seed))
        # A non-seed drag with a coord <= 0 is not a real placement: 0 is the
        # auto/unseeded sentinel, and the _cmd_xy_arg failure signature is (0, 0).
        # Dropping it keeps a bad measurement from clobbering the stored position.
        # Seed writes are always allowed -- they carry real measured default coords.
        if not is_seed and (x <= 0 or y <= 0):
            return
        mod_settings.set_position(x, y, is_default=is_seed)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _connect_commands(rvm):
    """Wire the reverse-channel commands to their handlers. The command objects
    are Wulf events that support +=. A fresh ResearchVM is created per attach(),
    so there's no double-subscription to guard against."""
    try:
        rvm.researchUnlock += _on_research_unlock
        rvm.unlockFieldMod += _on_unlock_field_mod
        rvm.openSkillTree += _on_open_skill_tree
        rvm.openResearch += _on_open_research
        rvm.openFieldMods += _on_open_field_mods
        rvm.buyMount += _on_buy_mount
        rvm.setPosition += _on_set_position
    except Exception:
        LOG_CURRENT_EXCEPTION()


# TickVM / UpgradeVM / ResearchVM live in bridge/view_models.py (imported above).


def attach(host_vm):
    """Load assets into the hangar doc + expose our data model on the sub-view.
    Returns the ResearchVM instance to push into, or None on failure."""
    global _active
    try:
        openwg_gameface.gf_mod_inject(
            host_vm, WIDGET_NAME,
            styles=[COUI + "/WGModResearch.css"],
            modules=[COUI + "/WGModResearch.js"])
        rvm = ResearchVM()
        _connect_commands(rvm)
        # Retry settings registration here: by the first hangar mount every mod
        # (including ModsSettingsAPI) is loaded, so the import that may have failed
        # at entry-point install time now succeeds. Idempotent once registered.
        mod_settings.init()
        host_vm._addViewModelProperty(DATA_PROP, rvm)
        _active = (host_vm, rvm)
        return rvm
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return None


def refresh():
    """Re-push the current vehicle's model into the mounted widget."""
    if _active is None:
        LOG_NOTE("[wgmod] refresh: no active widget")
        return False
    push(_active[1], host_vm=_active[0])
    return True


def push(rvm, host_vm=None):
    """Recompute the model for the selected vehicle and write it into rvm."""
    if rvm is None:
        return
    try:
        snap = engine_adapter.build_snapshot()
        if snap is None:
            return
        model = build_model(snap, mod_settings.enabled_modes())
        # Session "done" markers: promote a confirmed click and inject the current
        # vehicle's marker (a first tick / first chip). Engine-free + guarded.
        recent.decorate(model, snap)
        LOG_NOTE("[wgmod] push mode=%s ticks=%d fillV=%d fillF=%d" % (
            model.mode, len(model.ticks), model.fill_vehicle, model.fill_free))
        # Resolve localized labels OUTSIDE the transaction: a bad resource id must never
        # abort the model write (a rolled-back transaction blanks the whole bar).
        try:
            labels_json = json.dumps(i18n.widget_labels(), ensure_ascii=True)
        except Exception:
            LOG_CURRENT_EXCEPTION()
            labels_json = "{}"
        with rvm.transaction() as tx:
            tx.setVisible(bar_visible(_bar_visible(), mod_settings.hide_always(),
                                      mod_settings.hide_when_complete(), model.mode,
                                      _in_garage()))
            tx.setColorBlind(engine_adapter.is_color_blind())
            # Localized widget labels (client-language, sourced from WG's own strings);
            # JSON so the whole bundle rides one field. ensure_ascii escapes non-ASCII
            # (e.g. Cyrillic) to \uXXXX, which JS JSON.parse decodes back.
            tx.setLabels(labels_json)
            tx.setPosX(mod_settings.pos_x())
            tx.setPosY(mod_settings.pos_y())
            tx.setMode(model.mode)
            tx.setScaleMin(model.scale_min)
            tx.setScaleMax(model.scale_max)
            tx.setFillVehicle(model.fill_vehicle)
            tx.setFillFree(model.fill_free)
            tx.setFieldModsDone(model.fieldmods_done)
            tx.setFieldModsTotal(model.fieldmods_total)
            tx.setVehicleClass(model.vehicle_class or "")
            tx.setEliteLevel(model.elite_level or 0)
            tx.setEliteMaxLevel(model.elite_max_level or 0)
            tx.setEliteGrade(model.elite_grade or "")
            tx.setEliteSub(model.elite_sub or 0)
            tx.setEliteCurrentIcon(getattr(model, "elite_current_icon", "") or "")
            tx.setCombatXp(model.combat_xp or 0)
            tx.setSpendableXp(model.spendable_xp or 0)
            tx.setAvgBattleXp(getattr(model, "avg_battle_xp", 0) or 0)
            arr = tx.getTicks()
            arr.clear()
            for t in model.ticks:
                tv = TickVM()
                tv.setPosition(t.xp_position)
                tv.setXpRequired(t.xp_required)
                tv.setCategory(t.category)
                tv.setName(t.name or "")
                tv.setAffordable(bool(t.affordable))
                tv.setLocked(bool(t.locked))
                tv.setIcon(t.icon or "")
                tv.setLevel(t.level or 0)
                tv.setOptions("\n".join(t.options or []))
                tv.setState(t.state or "")
                tv.setActionId(t.action_id or 0)
                tv.setKindLabel(getattr(t, "kind_label", "") or "")
                tv.setPrereqNames("\n".join(getattr(t, "prereq_names", None) or []))
                tv.setEffect(getattr(t, "effect", "") or "")
                tv.setOptionEffects("\n".join(getattr(t, "option_effects", None) or []))
                is_done = bool(getattr(t, "done", False))
                tv.setDone(is_done)
                # Done ticks: current credits buy price for the researched item, read
                # fresh (hides once owned). 0 for every other tick -> JS shows no footer.
                tv.setPrice(engine_adapter.read_purchase_price(
                    getattr(t, "int_cd", 0), t.category,
                    getattr(snap, "vehicle_int_cd", 0)) if is_done else 0)
                arr.addViewModel(tv)
            arr.invalidate()
            # Available tier-XI upgrade nodes -> the clickable header chips.
            ua = tx.getAvailUpgrades()
            ua.clear()
            for up in model.avail_upgrades:
                uv = UpgradeVM()
                uv.setActionId(getattr(up, "step_id", 0) or 0)
                uv.setIcon(getattr(up, "icon", "") or "")
                uv.setName(getattr(up, "name", "") or "")
                uv.setXpRequired(getattr(up, "xp_cost", 0) or 0)
                uv.setEffect(getattr(up, "description", "") or "")
                uv.setCategory(getattr(up, "category", "") or "")
                uv.setDone(bool(getattr(up, "done", False)))
                ua.addViewModel(uv)
            ua.invalidate()
        # Nudge the host sub-view so its data re-syncs to JS (nested-model
        # updates may not bubble a data-changed event on their own).
        if host_vm is not None:
            try:
                with host_vm.transaction() as _h:
                    pass
            except Exception:
                pass
    except Exception:
        LOG_CURRENT_EXCEPTION()
