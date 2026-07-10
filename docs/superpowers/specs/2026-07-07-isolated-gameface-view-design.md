# Isolated Gameface view for the Garage Progress Bar

**Date:** 2026-07-07
**Status:** SUPERSEDED (2026-07-07) — the own-view/window approach below was implemented and
then abandoned after a live spike. See "Resolution" immediately below.

## Resolution (what actually shipped)

The own-view registered-window approach (the bulk of this doc) was built and tested live,
then **abandoned**. Two findings from the spike:

1. Opening the window inside the hangar presenter's `_onLoading` left the view stuck at
   `ViewStatus.CREATED` (never loaded); it only loaded when opened a tick later. (Fixable
   with a deferred `BigWorld.callback` open.)
2. **Fatal:** a full-screen lobby `WindowImpl` **steals all mouse input** — CSS
   `pointer-events:none` on the document does NOT let events fall through to the hangar
   beneath the window, and there is no window-level input-transparency `WindowFlags` bit.
   (Battle composites differently, which is why the MoE **battle** overlay is input-
   transparent there.) Any own-view window therefore creates an input dead-zone over the
   hangar; Option B (bbox window) only shrinks the dead-zone at the cost of a
   dead-patch-over-the-vehicle + tooltip-clipping + drag-tracking rework.

**What shipped instead (commit `ce642c6`):** keep the proven `gf_mod_inject` model, but move
this bar onto a **different always-mounted hangar sub-view** — the crew panel
(`CrewPresenter`) — while the sibling MoE Calculator keeps `HangarVehicleParamsPresenter`.
OpenWG stores one `ModInjectModel` **per sub-view VM**, so two mods on *different* sub-views
no longer collide; both still inject into the shared hangar document, and each widget's JS
self-locates its data by feature name across sub-views (OpenWG `model.js`), so no JS/CSS
change was needed. In-game verified: both bars render together, hangar input unaffected.

Trade-off accepted: this is robust for the two 14th_ua mods but not immune to a hypothetical
third mod that also picks `CrewPresenter` (the "any third-party mod" ideal below is not met).
Still-open follow-ups: the debug-REPL port split (2223/2224) and the harness-skill note.

---

_Original design (superseded) follows._

**Original Status:** Approved (design) — pending implementation plan
**Scope (all folded into one plan):**
1. Convert the **Garage Progress Bar** (this repo) to an isolated own-view widget.
2. Convert the **MoE Calculator** garage bar (sibling repo
   `C:/Users/Dmytro Vasylkivskyi/14th_ua-moe-calculator`) to the same pattern.
3. Resolve the duplicate **debug-REPL port 2223** clash (both mods hardcode it).
4. **Redeploy** both mods clean (this repo is stale at 0.5.0 vs 0.6.2) and verify in-game.
5. Capture the reusable rule in the `wotmod-*` **harness skills**.

## Problem

The bar is installed and its Python is fully alive (listeners arm, `push … ok=True`),
but it renders nothing once the sibling **MoE Calculator** mod is also installed. It
was visible before MoE existed.

### Root cause (confirmed, live + static)

Both mods attach their widget to the **same** hangar sub-view,
`HangarVehicleParamsPresenter`, via `openwg_gameface.gf_mod_inject(host_vm, …)`.

- Live REPL probe: both bridges' `_active[0]` point at the **same** ViewModel object
  (`wg_host_id == moe_host_id == 4656310088`, `same_host_object: true`).
- OpenWG's injector (decompiled `openwg_gameface.pyc` + `res/gui/gameface/js/index.js`):
  `gf_mod_inject` adds a **single** property named `ModInjectModel` to the target
  ViewModel; the JS injector reads exactly one `model?.ModInjectModel` per sub-view and
  injects it **once** (guarded by an `injectedResIds` Set). The `name` argument is only a
  JS-side label — it does **not** namespace the property.
- Therefore two mods on one sub-view cannot coexist: the second `gf_mod_inject` overwrites
  the first's `ModInjectModel`, so only the last attacher's assets are injected. The loser's
  Python still runs and `push()` returns `ok=True` (it set `_active` and cannot tell the JS
  is absent), which is exactly the observed symptom.

Ruled out along the way: the `res_mods` overlay / MoE dev workflow, the OpenWG-generated
`res_map.json` (the bar never used res_map), CSS/class collision (`.wg-*` vs `.moe-*`,
disjoint), saved position (`posX:1920` is screen-centre at 4K), and the stale 0.5.0 deploy.

### Requirement

Both mods must be **fully isolated** — non-interfering with each other **and with any
third-party mod**. This applies to **two** surfaces:

1. **Rendering** — a widget must never blank or restyle another. Since `gf_mod_inject`
   shares one `ModInjectModel` per sub-view, sharing any sub-view can never satisfy this;
   each widget must own its own Gameface view.
2. **Input** — the bar may receive its own clicks / Ctrl-drag / hover, but must be
   **provably incapable** of blocking or stealing pointer or keyboard input from the hangar
   or any other mod/window. This is a hard acceptance criterion, not best-effort, and it
   **gates the windowing choice** (below).

## Approach (chosen)

**Standalone registered hangar-overlay window per mod** (OpenWG res_map registration —
"mechanism B"). Proven in-repo: the MoE **battle** overlay already uses it
(`moe_calculator/bridge/battle_view.py` + `mods/configs/res_map/MoEBattleView.json`).

Each widget registers its own view: a unique res_map `itemID` → `layoutID` (via
`ModDynAccessor`) → its own Gameface **document** and **root ViewModel**. Nothing is
shared, so nothing can collide.

Rejected alternatives:
- **Dedicated per-mod sub-view via `gf_mod_inject`** — no OpenWG API to create a
  mod-owned sub-view; the surface is only `gf_mod_inject` (shared) + res_map registration.
- **Different existing game sub-views per mod** — fails the "any mod" requirement (a third
  mod on the same sub-view still collides) and depends on finding a second always-mounted
  sub-view.

## Architecture & components

Domain and adapter layers are **unchanged**. Only the binding surface changes.

| Layer | File | Change |
|---|---|---|
| domain/ | builder, resolvers, types | Unchanged; still `pytest`-covered |
| adapter/ | `engine_adapter`, `*_read`, `format`, `recent`, `i18n` | Unchanged |
| bridge | `bridge/research_view.py` | **NEW** — `WGModResearchView(ViewImpl)` with `_layoutID = ModDynAccessor("WGModResearchView")`, root VM = `ResearchVM`; `WGModResearchWindow(WindowImpl)` full-screen lobby-layer window, `show(focus=False)`; `open_window()` / `close_window()` singleton. Mirrors `MoEBattleView`. In-client only. |
| bridge | `bridge/gameface_bridge.py` | **MODIFIED** — remove `attach(host_vm)` / `gf_mod_inject` / `_addViewModelProperty`. Keep listeners (vehicle / loadout / stats / colorblind / lobby-state / settings). Lifecycle → `open_window()` / `close_window()` driven by the existing garage allowlist. `push()` writes into `view.viewModel` (root VM) instead of the injected sub-view property. |
| bridge | `bridge/view_models.py` | Minor — `ResearchVM` becomes the view's **root** VM (shape unchanged). |
| config | `src/res/mods/configs/res_map/WGModResearchView.json` | **NEW** — `Layout` itemID `WGModResearchView` → `coui://gui/gameface/mods/14th_ua/WGModResearch/WGModResearchView.html`. |
| front-end | `WGModResearchView.html` | **NEW** — full-screen root document hosting the bar markup. |
| front-end | `WGModResearch.js` | **MODIFIED** — root `ModelObserver()` instead of the sub-view-property observer. **Render logic unchanged.** |
| front-end | `WGModResearch.css` | **MODIFIED** — root `pointer-events:none`; bar container `pointer-events:auto`; same visual styling / px positioning. |
| entry | `mod_wgmod.py` | **MODIFIED** — no longer patches `HangarVehicleParamsPresenter`; arms the open/close lifecycle on hangar enter/exit. |

## Data flow

`vehicle / settings / stats change` → existing listener → `engine_adapter.build_snapshot()`
→ `domain.builder.build_model()` → `push()` into the **open window's root VM** → JS root
`ModelObserver` re-renders. Identical to today except the VM write target is the view's root
VM rather than a property hung on a shared sub-view.

## Lifecycle

- Enter the plain garage (allowlist leaf `hangar/{root}`) → `open_window()` → initial `push()`.
- Leave garage / open tank-setup / ammo overlay → `close_window()`.
- Vehicle / stats / colorblind / settings change while open → `push()`.
- `layoutID` unresolved on first launch (res_map not yet rebuilt) → log once, no-op until
  the one-time OpenWG restart resolves it (accepted). Same handling as `MoEBattleView`.

## Input handling (primary risk)

The battle overlay is info-only (`pointer-events:none` throughout); the garage bar is
**interactive** (click ticks/chips → `invokeCommand({value:…})`; Ctrl-drag reposition;
hover tooltips). The bar must take *its own* input while being provably incapable of
interfering with anything else (see requirement 2 above).

**Non-interference is the deciding criterion, not UX convenience.** Two windowing options,
chosen by the spike below:

- **Option A — full-screen, input-transparent-except-the-bar.** `show(focus=False)`, lobby
  `WindowLayer` **below** modal dialogs (never the keyboard/mouse sink — the trap documented
  in `MoEBattleView`); root document `pointer-events:none`, only the bar container
  `pointer-events:auto`. Cleaner UX (drag range and tooltip overflow are unconstrained), but
  depends on Gameface honouring `pointer-events:none` at the window level so clicks/hover
  pass through the transparent area to the hangar.
- **Option B — window sized to the bar's bounding box.** Physically covers only the bar's
  rectangle, so it is *structurally incapable* of interfering outside it — the strongest
  non-interference guarantee. Cost: the window must track the bar on Ctrl-drag, and be
  padded so hover tooltips are not clipped.

**Decision rule:** prefer whichever passes the strict non-interference check; if both pass,
prefer A for UX. If A cannot *guarantee* non-interference, use B — physical isolation wins
over convenience.

**Validation-first:** the implementation plan's FIRST step is a live spike. Pass criteria
(all required): (a) a button inside the bar receives a click and fires its command;
(b) with the bar open, hangar controls under/around it behave **exactly** as with the bar
absent — clicks, hover, tooltips, and drag all unaffected; (c) opening the Esc/in-game menu
and any modal dialog is fully unaffected (no starved keyboard/mouse). The choice between A
and B is made from this evidence, not guessed.

## Error handling

Fail-soft throughout (existing convention): unresolved `layoutID` → log + no-op; window
open/close failure → log via `LOG_CURRENT_EXCEPTION`, never crash the hangar; `push()` with
no open window → no-op.

## Testing

- **Automated:** domain/adapter unchanged → existing `pytest` suite stays green as the model
  correctness gate.
- **In-client (REPL + in-game):** `research_view.py` and the modified bridge import live
  Wulf/OpenWG symbols → not `pytest`-importable. Verify via the debug REPL + garage: window
  opens, bar renders, tick click fires its command, drag repositions, vehicle switch
  live-updates, and the passthrough check from the spike.

## Harness update (reusable lesson)

Add to `wotmod-gameface-widget` (referenced from `wotmod-architecture`):

> A standalone mod widget must register its **own** view (res_map config JSON +
> `ViewImpl`/`WindowImpl` + root `ModelObserver`). Use `gf_mod_inject` **only** to
> deliberately augment an existing WG view — never for a standalone widget: every mod that
> injects onto the same sub-view shares one `ModInjectModel` and the last writer wins, so
> two such mods silently blank each other.

Include the interactive-lobby-window notes (layer choice below modal dialogs,
`show(focus=False)`, `pointer-events` layering for click passthrough).

## Also in scope (folded in)

### MoE Calculator conversion (sibling repo)

Apply the identical own-view pattern to the MoE **garage** bar
(`moe_calculator/bridge/gameface_bridge.py`, which today `gf_mod_inject`s onto the same
`HangarVehicleParamsPresenter`): new `mods/configs/res_map/MoECalculatorView.json`, a
`MoECalculatorView(ViewImpl)` + window (mirroring its own `MoEBattleView`), root VM =
`moeData`'s VM, JS switched to a root `ModelObserver`, lifecycle open/close on the garage
allowlist. The MoE **battle** overlay already uses mechanism B and is untouched. Same input
non-interference requirement and windowing decision (A vs B) apply. This repo's conversion
is completed and validated first; MoE reuses the proven choice.

### Debug-REPL port clash

Both `mod_wgmod_debug` and `mod_moe_calculator_debug` bind `127.0.0.1:2223`, so only one can
start when both are installed. Assign distinct ports — Garage Progress Bar keeps **2223**,
MoE moves to **2224** — updating each repo's `tools/dev/mod_*_debug.py` (`PORT`),
`repl_client.py` (`PORT`), the debug `meta.xml` description, and any skill/docs references.
Dev-only; not shipped.

### Clean redeploy + in-game verification

After each mod's conversion, build (Py 2.7) and deploy clean into
`D:/Games/World_of_Tanks_EU` `2.3.0.1`, removing any stale `res_mods` overlay, then verify
in-game **with both mods installed together**: both bars render, both are interactive, and
neither interferes with the other, the hangar, or the Esc/modal menus. This also clears the
stale 0.5.0 package (this repo is at 0.6.2). Version bump handled per `gpb-release` when
shipping.

## Sequencing

1. Input spike (this repo) → pick windowing Option A or B.
2. Convert this repo; verify in-game solo.
3. Convert MoE (reuse the chosen option); verify in-game solo.
4. Fix the debug-REPL port clash in both repos.
5. Redeploy both; verify **together** (rendering + input non-interference).
6. Update the `wotmod-*` harness skills with the rule + input notes.
