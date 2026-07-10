# Isolated Gameface Views Conversion — Implementation Plan

> **⚠️ SUPERSEDED (2026-07-07).** This plan's own-view/window conversion was implemented and
> then abandoned after a live input spike (a full-screen lobby window steals all mouse input;
> CSS `pointer-events` does not pass through to the hangar). What shipped instead: keep
> `gf_mod_inject`, move the research bar onto a different hangar sub-view (`CrewPresenter`);
> MoE keeps the params sub-view. See the "Resolution" section in the spec
> (`docs/superpowers/specs/2026-07-07-isolated-gameface-view-design.md`) and commit `ce642c6`.
> Tasks 2–9 below are obsolete. Still-relevant: Task 10 (debug-REPL port split) and Task 12
> (harness-skill note about one `ModInjectModel` per sub-view).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert both 14th_ua garage bars (this repo's Garage Progress Bar and the sibling MoE Calculator) from a shared `gf_mod_inject` sub-view attachment to standalone OpenWG-registered Gameface own-view windows, so they no longer blank each other (or any third-party mod), split their clashing debug-REPL port, and redeploy + verify both together.

**Architecture:** Each widget registers its **own** Gameface view (a `res_map` config JSON → a `ViewImpl` + `WindowImpl` + a root `ModelObserver`), exactly like the MoE **battle** overlay already does (`moe_calculator/bridge/battle_view.py` + `mods/configs/res_map/MoEBattleView.json`). The domain and adapter layers are unchanged; only the binding surface (bridge/view/config/entry/JS/CSS) changes. The root ViewModel of each view is the mod's existing data VM (`ResearchVM` / `MoEVM`); the JS observes the view's own root model instead of a nested `wgResearch`/`moeData` property hung on a shared sub-view.

**Tech Stack:** Python 2.7.18 (packaging/runtime, BigWorld) · Python 3.13 (pytest only) · Wulf/OpenWG Gameface · HTML/CSS/JS (Coherent). No npm/linter/CI; builds are plain Python scripts.

## Global Constraints

- **Bytecode is version-locked:** package `.wotmod` with **Python 2.7.18** (`C:\Python27\python.exe`). Python 3 bytecode will NOT load in-client. Tests run on **Python 3.13**.
- **`bridge/research_view.py` and the modified bridge import live Wulf/OpenWG symbols → NOT `pytest`-importable.** They are verified in-client only (debug REPL + in-game). The domain/adapter pytest suite is the model-correctness gate and MUST stay green.
- **OpenWG GameFace is a hard dependency**; entry points import `openwg_gameface` and fail-soft if absent.
- **One-time client restart:** the first launch after a new `res_map` config JSON is added triggers OpenWG's `ResMapManager` to rebuild `res_map.json`; `layoutID` is unresolved (`< 0`) until that restart. Handle fail-soft (log once, no-op), same as `MoEBattleView`.
- **Copy/naming:** "Tier XI" (no hyphen). `.wg-*` classes for this mod, `.moe-*` for MoE (already disjoint).
- **Client / install:** WoT EU **2.3.0.1** at `D:/Games/World_of_Tanks_EU`. This repo id `com.14th_ua.garageprogressbar`; MoE id `com.14th_ua.moecalculator`.
- **Fail-soft everywhere:** window open/close and push failures log via `LOG_CURRENT_EXCEPTION` and never crash the hangar; `push()` with no open window is a no-op.
- **`git` workflow:** commit straight to `main` in each repo; do NOT branch/PR. Push only when the user asks.

## ⚠️ In-client work is the human partner's

Claude cannot launch World of Tanks. Every task marked **[IN-CLIENT]** is executed by the user, who runs the exact commands/steps given and reports the observed result back. Claude writes the code; the user runs the spike, the REPL probes, and the in-game verification. Do not mark an **[IN-CLIENT]** task complete on Claude's assertion — only on the user's reported observation.

## Spike gates the windowing choice (A vs B)

Two windowing options exist; **Task 1 (the live input spike) picks one** and that choice determines the body of Task 5 (`research_view.py` window flags) and Task 7 (CSS). Both variants are written out in full in those tasks — implement only the branch the spike selected. Do not guess; wait for the spike result.

- **Option A — full-screen, input-transparent-except-the-bar.** `show(focus=False)`; lobby `WindowLayer` **below** modal dialogs; root document `pointer-events:none`, only the bar container (`.wg-hot` / chips / `#moe-root`) `pointer-events:auto`. Clean UX (unconstrained drag range + tooltip overflow), depends on Gameface honouring window-level `pointer-events:none` so clicks/hover pass through the transparent area to the hangar underneath.
- **Option B — window sized to the bar's bounding box.** Physically covers only the bar rectangle → structurally incapable of interfering outside it. Costs: the window must track the bar on Ctrl-drag, and be padded so hover tooltips are not clipped.

**Decision rule:** prefer whichever passes the strict non-interference check; if both pass, prefer A for UX. If A cannot *guarantee* non-interference, use B.

---

## File Structure

**This repo (`wgmod-research-progress`):**
- **Create** `src/res/mods/configs/res_map/WGModResearchView.json` — res_map Layout registration (`itemID: WGModResearchView` → the HTML bundle). Packaged automatically (build walks all of `src/res/`).
- **Create** `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearchView.html` — full-screen root document hosting the bar; empty body (JS builds the markup).
- **Create** `src/res/scripts/client/wgmod_research/bridge/research_view.py` — `WGModResearchView(ViewImpl)` + `WGModResearchWindow(WindowImpl)` + `open_window()` / `close_window()` / `active_view()` singleton. In-client only.
- **Modify** `src/res/scripts/client/wgmod_research/bridge/gameface_bridge.py` — remove `attach`/`gf_mod_inject`/`_addViewModelProperty`; `refresh()`/`push()` target the open window's root VM; keep all listeners; drop the `host_vm` nudge.
- **Modify** `src/res/scripts/client/gui/mods/mod_wgmod.py` — presenter patch opens the window + re-arms listeners (idempotent); add a battle-entry close hook.
- **Modify** `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js` — root `ModelObserver()`; read root model instead of `model.wgResearch`.
- **Modify** `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.css` — root-document passthrough (Option A) or bbox sizing (Option B).

**MoE repo (`14th_ua-moe-calculator`), all mirrors of the above:**
- **Create** `src/res/mods/configs/res_map/MoECalculatorView.json`, `.../MoECalculator/MoECalculatorView.html`, `moe_calculator/bridge/garage_view.py`.
- **Modify** `moe_calculator/bridge/gameface_bridge.py`, `gui/mods/mod_moe_calculator.py`, `.../MoECalculator/MoECalculator.js`, `.../MoECalculator/MoECalculator.css`.
- **Modify (port fix)** `tools/dev/mod_moe_calculator_debug.py`, `tools/dev/repl_client.py`, `tools/dev/build_debug_wotmod.py`, `tools/dev/README.md`, and MoE `TASKS/*.md` references: `2223` → `2224`.

**Docs/skills (Task 12):** `wotmod-gameface-widget` + `wotmod-architecture` harness skills; this repo's `gpb-debug-repl` skill / `tools/dev/README.md` / `CONTRIBUTING.md` port note.

---

## Task 1: Live input spike — pick Option A or B [IN-CLIENT]

**Goal:** Decide the windowing option from evidence, not guesswork. This is the FIRST step and gates Tasks 5 and 7.

**Files:** none created — this is a live probe using a temporary registered view. Reuse the proven `MoEBattleView` machinery as the probe harness (it is already installed and registered in the running client via the MoE mod), OR stand up a throwaway registered full-screen window from the debug REPL.

**Approach (cheapest first):** The MoE **battle** overlay already proves a full-screen `pointer-events:none` registered window is input-transparent *in battle*. The open question is specifically the **garage/lobby layer** with an **interactive** sub-region. Probe that directly.

- [ ] **Step 1: Establish the dev overlay + relaunch** (per `gpb-build-deploy` / the "hot-reload needs overlay-at-launch" memory). The `res_mods` overlay must exist WHEN the client launches. Deploy the current build once and relaunch so the REPL + overlay are live.

- [ ] **Step 2: From the debug REPL, open a full-screen input-transparent registered probe window in the garage.** Use the MoE battle view class as a ready-made registered full-screen `pointer-events:none` window (its layoutID resolves once registered), opened while sitting in the plain garage:

```python
# repl: is a full-screen registered window input-transparent in the LOBBY?
from moe_calculator.bridge import battle_view as bv
v = bv.open_window()          # full-screen, show(focus=False), pointer-events:none
print("layout=", bv.MoEBattleView._layoutID())
# Now, IN-GAME (user observes): with this overlay open in the garage, do the
# hangar buttons / carousel / vehicle tiles / tooltips / Ctrl-drag still work
# EXACTLY as without it? Open the Esc menu + a modal dialog — is input starved?
```

- [ ] **Step 3: Record the Option-A pass/fail.** Option A passes iff, with the full-screen input-transparent window open over the garage: (a) hangar controls under/around it behave exactly as with it absent (click, hover, tooltip, drag); (b) the Esc/in-game menu and any modal dialog open and take input normally (no starved keyboard/mouse). Close the probe: `bv.close_window()`.

- [ ] **Step 4: If Option A passed, additionally confirm an interactive sub-region can still receive its own clicks** while the rest passes through. Quick check: the existing widget already layers `#wgmod-root { pointer-events:none }` + `.wg-hot { pointer-events:auto }` and reliably received clicks when injected into the hangar document — so a `pointer-events:auto` sub-region inside an otherwise-transparent window is the same mechanism one layer up. Confirm in Task 6's in-game check; for the spike, Step 3's passthrough result is the deciding evidence.

- [ ] **Step 5: Decide and record.** Write the chosen option (A or B) and the observed evidence into this plan file under Task 1, and into the spec's status line. **If A passed → implement the "Option A" branches in Tasks 5 & 7. If A failed → implement the "Option B" branches.**

**Decision recorded here:** _(fill in: A or B + one-line evidence)_

---

## Task 2: `res_map` config registration (this repo)

**Files:**
- Create: `src/res/mods/configs/res_map/WGModResearchView.json`

**Interfaces:**
- Produces: res_map `itemID` `"WGModResearchView"`, consumed by `research_view.py`'s `ModDynAccessor("WGModResearchView")` (Task 5) and pointing at the HTML from Task 3.

- [ ] **Step 1: Create the config JSON** (mirrors `MoEBattleView.json`; `entrance` MUST equal the itemID):

```json
[
    {
        "type": "Layout",
        "path": "coui://gui/gameface/mods/14th_ua/WGModResearch/WGModResearchView.html",
        "parameters": {
            "extension": "",
            "entrance": "WGModResearchView",
            "impl": "gameface"
        },
        "itemID": "WGModResearchView"
    }
]
```

- [ ] **Step 2: Confirm the build packages it.** `build/build_wotmod.py` `_compile_tree(RES, ...)` walks all of `src/res/` and copies non-`.py` files verbatim, so `src/res/mods/configs/res_map/WGModResearchView.json` lands at `res/mods/configs/res_map/WGModResearchView.json`. No build-script change needed.

Run: `python build/build_wotmod.py` (Python 2.7) and confirm the JSON appears in the built tree:
```bash
python -c "import zipfile; z=zipfile.ZipFile([f for f in __import__('glob').glob('dist/*.wotmod')][0]); print([n for n in z.namelist() if 'res_map' in n])"
```
Expected: a list containing `res/mods/configs/res_map/WGModResearchView.json`.

- [ ] **Step 3: Commit**

```bash
git add src/res/mods/configs/res_map/WGModResearchView.json
git commit -m "feat(view): register WGModResearchView res_map layout"
```

---

## Task 3: Full-screen root HTML document (this repo)

**Files:**
- Create: `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearchView.html`

**Interfaces:**
- Consumes: the CSS/JS bundle files (`WGModResearch.css`, `WGModResearch.js`) that already exist in the same folder.
- Produces: the document `WGModResearchView` loads when the window opens (Task 5).

- [ ] **Step 1: Create the HTML** (mirrors `MoEBattleView.html`; empty body — the JS builds `#wgmod-root`):

```html
<!doctype html>
<html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>WGModResearchView</title>
        <link rel="stylesheet" crossorigin href="WGModResearch.css" defer />
    </head>
    <body>
        <!-- Registered OpenWG Gameface view opened as a hangar-layer window (see
             bridge/research_view.py). The bar root (#wgmod-root) is created + populated by
             WGModResearch.js, which reads THIS view's own root ViewModel (ResearchVM) via a
             root ModelObserver(). Body intentionally empty so the JS builds the full markup. -->
        <script type="module" crossorigin src="WGModResearch.js" defer></script>
    </body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearchView.html
git commit -m "feat(view): add WGModResearchView root document"
```

---

## Task 4: JS root-observer switch (this repo)

**Files:**
- Modify: `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js` (3 sites: observer construction ~line 33, `invokeCommand` ~line 705, `render` ~line 1267)

**Interfaces:**
- Consumes: the view's own root ViewModel (`ResearchVM`) — now `observer.model` IS the `ResearchVM`, not a host sub-view carrying a `wgResearch` property.
- Produces: unchanged render output; only the model access path changes.

- [ ] **Step 1: Switch to a root observer.** Change the observer construction (currently line 33):

```js
// OLD:
const observer = ModelObserver("WGModResearch");
// NEW: registered view -> our ResearchVM IS the view's own root model (no feature name).
const observer = ModelObserver();
```

- [ ] **Step 2: Read the root model in `render`.** Change the data extraction (currently line 1267):

```js
// OLD:
    const data = unwrap(model && model.wgResearch);
// NEW: the observed model IS our ResearchVM root -- read it directly (still unwrap the proxy).
    const data = unwrap(model);
```

- [ ] **Step 3: Target the root VM in `invokeCommand`.** Change the command host lookup (currently line 705):

```js
// OLD:
        const vm = observer.model && observer.model.wgResearch;
// NEW: commands live on the view's own root model now.
        const vm = observer.model;
```

- [ ] **Step 4: Update the file header comment** (lines 2–3) to say the model is the view's own root VM read via a root `ModelObserver()`, not a `wgResearch` property on a hangar sub-view. (Keep it one edit; wording per surrounding style.)

- [ ] **Step 5: Sanity — no other `wgResearch` references remain.**

Run: `grep -n "wgResearch\|ModelObserver(\"" src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js`
Expected: no `wgResearch` matches; the only `ModelObserver(` is the no-arg root observer.

- [ ] **Step 6: Commit**

```bash
git add src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js
git commit -m "refactor(widget): observe the view's own root model, not wgResearch"
```

---

## Task 5: `research_view.py` — the registered view + window (this repo)

**Files:**
- Create: `src/res/scripts/client/wgmod_research/bridge/research_view.py`

**Interfaces:**
- Consumes: `ResearchVM` (from `bridge.view_models`), `ModDynAccessor("WGModResearchView")` (Task 2 itemID), and `gameface_bridge._connect_commands` + `gameface_bridge.refresh` (Task 6, lazy-imported to avoid a cycle).
- Produces: `open_window() -> WGModResearchView | None`, `close_window()`, `active_view() -> WGModResearchView | None`. `active_view().viewModel` is the `ResearchVM` that `gameface_bridge.push` writes into.

- [ ] **Step 1: Write `research_view.py`** (mirrors `battle_view.py`; root VM is `ResearchVM`; `_onLoading` wires the reverse-channel commands once per open and does the initial push).

**Common code (both options):**

```python
# -*- coding: utf-8 -*-
"""Host the Garage Progress Bar as a standalone OpenWG-registered Gameface WINDOW in the
lobby, over the hangar.

Why an own view and not a garage sub-view inject: OpenWG's gf_mod_inject adds a SINGLE
`ModInjectModel` property to the target sub-view's ViewModel, and the JS injector reads
exactly one per sub-view. Two mods injecting onto the same sub-view
(HangarVehicleParamsPresenter) share that one property -- the last attacher wins and the
other's assets are never injected (its Python still runs and push() returns ok=True, so it
cannot tell its JS is absent). So we register our OWN Gameface view
(mods/configs/res_map/WGModResearchView.json -> WGModResearchView.html) and open it as a
lobby window. Nothing is shared -> nothing can collide. Mirrors moe_calculator's
bridge/battle_view.py.

The window content view's OWN root ViewModel IS our ResearchVM; the JS reads it with a
root ModelObserver() and gameface_bridge pushes into `view.viewModel`.

NOTE: adding the res_map entry triggers a ONE-TIME client restart the first time OpenWG's
ResMapManager rebuilds res_map.json with our layout. PC-only (needs the live client); not
imported under pytest. Python 2.7 runtime.
"""
from wgmod_research._compat import LOG_CURRENT_EXCEPTION, LOG_NOTE

from frameworks.wulf import ViewSettings, ViewFlags, WindowFlags, WindowLayer
from gui.impl.pub import ViewImpl, WindowImpl
from openwg_gameface import ModDynAccessor

from wgmod_research.bridge.view_models import ResearchVM

# itemID registered in mods/configs/res_map/WGModResearchView.json -- keep in lockstep.
RES_MAP_ITEM_ID = "WGModResearchView"


class WGModResearchView(ViewImpl):
    """The registered Gameface view; its root ViewModel is our ResearchVM."""

    _layoutID = ModDynAccessor(RES_MAP_ITEM_ID)

    def __init__(self):
        settings = ViewSettings(self._layoutID(), ViewFlags.VIEW, ResearchVM())
        super(WGModResearchView, self).__init__(settings)

    @property
    def viewModel(self):
        return super(WGModResearchView, self).getViewModel()

    def _onLoading(self, *args, **kwargs):
        super(WGModResearchView, self)._onLoading(*args, **kwargs)
        # Wire the reverse-channel commands to this view's OWN ResearchVM (a fresh VM per
        # open, so no double-subscription), then push once so the bar paints immediately.
        # Lazy import avoids a research_view <-> gameface_bridge import cycle.
        try:
            from wgmod_research.bridge import gameface_bridge
            gameface_bridge._connect_commands(self.viewModel)
            gameface_bridge.refresh()
        except Exception:
            LOG_CURRENT_EXCEPTION()
```

**Option A window class (full-screen, input-transparent) — use if the spike picked A:**

```python
class WGModResearchWindow(WindowImpl):
    """Full-screen, input-transparent lobby window hosting WGModResearchView over the hangar.

    Layer = WINDOW (below modal dialogs / the Esc menu at TOP_WINDOW): a full-screen window
    ABOVE a modal window becomes the keyboard sink and starves it of input (the trap
    documented in moe_calculator's MoEBattleView). Sitting below the menu layer lets its
    modality gate input away from our overlay while we still render above the hangar views.
    The document is pointer-events:none except the bar container (.wg-hot / chips), so all
    input outside the bar passes through to the hangar. show(focus=False) so we never grab
    lobby focus."""

    def __init__(self, content):
        super(WGModResearchWindow, self).__init__(
            WindowFlags.WINDOW | WindowFlags.WINDOW_FULLSCREEN,
            content=content, layer=WindowLayer.WINDOW)

    def _onReady(self):
        self.show(focus=False)
```

**Option B window class (sized to the bar box) — use if the spike picked B:**

```python
class WGModResearchWindow(WindowImpl):
    """Window physically sized to the bar's bounding box, so it is structurally incapable of
    interfering with input outside that rectangle. Layer = WINDOW (below modal dialogs).
    The window rect is padded for hover-tooltip overflow and re-positioned on Ctrl-drag (see
    reposition()). show(focus=False) so we never grab lobby focus.

    NOTE: the exact WindowFlags for a non-fullscreen sized window + the rect-setting API
    (setViewSize / setPosition on the window's decorator) are confirmed in Task 5a in-client;
    fill BAR_RECT from the measured bar box + tooltip padding."""

    def __init__(self, content):
        super(WGModResearchWindow, self).__init__(
            WindowFlags.WINDOW, content=content, layer=WindowLayer.WINDOW)

    def _onReady(self):
        self.show(focus=False)
        # reposition() sets the window rect to the bar box (+ tooltip padding). Wired to
        # setPosition drags via gameface_bridge; see Task 5a for the confirmed rect API.
```

**Common singleton + lifecycle (both options):**

```python
# Singleton (window, view) for the currently-open bar (None when closed).
_active = None


def open_window():
    """Idempotently open the bar window. Returns its WGModResearchView (read `.viewModel`
    to push into), or None on failure / res_map not yet registered."""
    global _active
    if _active is not None:
        return _active[1]
    try:
        layout = WGModResearchView._layoutID()
        if layout is None or layout < 0:
            LOG_NOTE("[wgmod] res_map layout '%s' unresolved -- a one-time client restart "
                     "is needed for OpenWG to register it." % RES_MAP_ITEM_ID)
            return None
        view = WGModResearchView()
        window = WGModResearchWindow(view)
        # Publish BEFORE load() so the view's _onLoading initial push (which calls back
        # through gameface_bridge.refresh() -> active_view()) sees us.
        _active = (window, view)
        window.load()
        LOG_NOTE("[wgmod] bar window opened (layoutID=%s)" % layout)
        return view
    except Exception:
        LOG_CURRENT_EXCEPTION()
        _active = None
        return None


def close_window():
    """Destroy the bar window if open."""
    global _active
    if _active is None:
        return
    window = _active[0]
    _active = None
    try:
        window.destroy()
        LOG_NOTE("[wgmod] bar window destroyed")
    except Exception:
        LOG_CURRENT_EXCEPTION()


def active_view():
    """The currently-open WGModResearchView, or None."""
    return None if _active is None else _active[1]
```

- [ ] **Step 2: Confirm it imports cleanly under Python 2.7 syntax** (cannot run in pytest — Wulf/OpenWG absent). Byte-compile check only:

Run: `C:\Python27\python.exe -m py_compile src/res/scripts/client/wgmod_research/bridge/research_view.py`
Expected: exits 0 (no syntax error). Runtime import is verified in Task 6.

- [ ] **Step 3: Commit**

```bash
git add src/res/scripts/client/wgmod_research/bridge/research_view.py
git commit -m "feat(bridge): add WGModResearchView registered own-view window"
```

---

## Task 6: Rewire `gameface_bridge.py` + `mod_wgmod.py` to the own-view lifecycle (this repo)

**Files:**
- Modify: `src/res/scripts/client/wgmod_research/bridge/gameface_bridge.py` (remove `attach`; retarget `refresh`/`push`; drop `host_vm`)
- Modify: `src/res/scripts/client/gui/mods/mod_wgmod.py` (presenter patch opens window + re-arms; add battle-entry close)

**Interfaces:**
- Consumes: `research_view.open_window()`, `research_view.close_window()`, `research_view.active_view()`.
- Produces: `refresh() -> bool` (pushes into the open window's root VM), `push(rvm)` (now single-arg; no `host_vm`), `_connect_commands(rvm)` (unchanged signature, called from `research_view._onLoading`).

- [ ] **Step 1: In `gameface_bridge.py`, delete the `attach()` function** (lines 432–452) and the `openwg_gameface` import (line 33) and the now-unused `WIDGET_NAME` / `DATA_PROP` / `COUI` constants (lines 35–37). The `gf_mod_inject` sub-view mechanism is gone.

- [ ] **Step 2: Retarget `refresh()`** to the open window's view model:

```python
# OLD:
def refresh():
    """Re-push the current vehicle's model into the mounted widget."""
    if _active is None:
        LOG_NOTE("[wgmod] refresh: no active widget")
        return False
    push(_active[1], host_vm=_active[0])
    return True
# NEW:
def refresh():
    """Re-push the current vehicle's model into the open bar window's root VM."""
    from wgmod_research.bridge import research_view
    view = research_view.active_view()
    if view is None:
        LOG_NOTE("[wgmod] refresh: no open bar window")
        return False
    push(view.viewModel)
    return True
```

- [ ] **Step 3: Drop the `host_vm` param + nudge from `push()`.** Change the signature (line 490) and delete the trailing host-sub-view nudge (lines 587–594):

```python
# OLD:
def push(rvm, host_vm=None):
    """Recompute the model for the selected vehicle and write it into rvm."""
# NEW:
def push(rvm):
    """Recompute the model for the selected vehicle and write it into the view's root VM."""
```
And delete this block at the end of `push` (the nested-model bubble nudge is unnecessary for a root VM):
```python
        # Nudge the host sub-view so its data re-syncs to JS (nested-model
        # updates may not bubble a data-changed event on their own).
        if host_vm is not None:
            try:
                with host_vm.transaction() as _h:
                    pass
            except Exception:
                pass
```

- [ ] **Step 4: Remove the stale `_active` module global + its comment in `gameface_bridge.py`** (lines 39–41 and the reference in the block comment near line 46 that names `_active`). The open-window singleton now lives in `research_view._active`. Update the `_LISTENERS`/re-arm block comment to reference `research_view` for the active-view state.

- [ ] **Step 5: Rewrite `mod_wgmod.py`'s presenter patch** to open the window + re-arm listeners (no `attach`), and add a battle-entry close hook so the full-screen lobby window never bleeds into battle:

```python
def _install():
    import openwg_gameface  # noqa: F401  (hard dependency; raises if absent)
    from gui.impl.lobby.hangar.presenters.hangar_vehicle_params_presenter import (
        HangarVehicleParamsPresenter as P)
    from wgmod_research.bridge import gameface_bridge as bridge
    from wgmod_research.bridge import research_view
    from wgmod_research.bridge import mod_settings

    mod_settings.init()

    if getattr(P, "_wgmod_patched", False):
        return

    _orig_onLoading = P._onLoading

    def _onLoading(self, *args, **kwargs):
        _orig_onLoading(self, *args, **kwargs)
        try:
            # Re-arm every mount (battle-exit teardown drops our hangar-scoped delegates),
            # then open our OWN registered view window (idempotent). The bar's data model is
            # this window's root VM -- nothing is shared with any other mod's sub-view inject.
            bridge.install_all_listeners()
            research_view.open_window()
        except Exception:
            LOG_CURRENT_EXCEPTION()

    P._onLoading = _onLoading
    P._wgmod_patched = True

    # Close the lobby window on battle entry so a full-screen lobby-layer window can't bleed
    # into the battle HUD; the next hangar mount re-opens it. Guarded + idempotent.
    _arm_battle_close(research_view)

    bridge.install_all_listeners()
    research_view.open_window()  # for the install that happens while already in the hangar
    LOG_NOTE("[%s] v%s installed (registered own-view window)" % (MOD_NAME, MOD_VERSION))


def _arm_battle_close(research_view):
    """Close the bar window when a battle avatar becomes ready. PlayerEvents persist across
    battles (unlike per-battle controllers), so this fires reliably; membership-checked so
    it is idempotent across re-installs/hot-reloads."""
    try:
        from PlayerEvents import g_playerEvents

        def _on_avatar_ready(*args, **kwargs):
            try:
                research_view.close_window()
            except Exception:
                LOG_CURRENT_EXCEPTION()

        ev = g_playerEvents.onAvatarReady
        if _on_avatar_ready not in ev:
            ev += _on_avatar_ready
            g_playerEvents.onAvatarReady = ev
    except Exception:
        LOG_CURRENT_EXCEPTION()
```

> Note: `_on_avatar_ready` is defined inside `_arm_battle_close`, so a fresh closure identity is created per call — the membership check dedupes within a single install, and `_wgmod_patched` prevents re-install. This is acceptable (install runs once per session). If a hot-reload re-runs `_install`, the `_wgmod_patched` guard returns early before re-arming.

- [ ] **Step 6: Byte-compile check (Python 2.7 syntax).**

Run:
```bash
C:\Python27\python.exe -m py_compile \
  src/res/scripts/client/wgmod_research/bridge/gameface_bridge.py \
  src/res/scripts/client/gui/mods/mod_wgmod.py
```
Expected: exits 0.

- [ ] **Step 7: Run the pytest suite — the domain/adapter model gate MUST stay green.**

Run: `python -m pytest -q` (Python 3.13)
Expected: all tests pass (bridge files are not imported by the suite; this confirms nothing in domain/adapter regressed).

- [ ] **Step 8: Commit**

```bash
git add src/res/scripts/client/wgmod_research/bridge/gameface_bridge.py \
        src/res/scripts/client/gui/mods/mod_wgmod.py
git commit -m "refactor(bridge): drive the bar via its own registered window, not gf_mod_inject"
```

---

## Task 7: CSS for the own-view document (this repo) — GATED on Task 1

**Files:**
- Modify: `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.css` (root document rules; ~lines 1–27)

**Interfaces:** none new — pure styling. The existing `#wgmod-root { pointer-events:none }` + `.wg-hot { pointer-events:auto }` layering is preserved in both options.

- [ ] **Step 1 — Option A (if the spike picked A): make the root document itself transparent to input.** Add `html, body` passthrough at the top of the file, above `#wgmod-root`:

```css
/* Registered own-view document: the window fills the screen but must be input-transparent
   everywhere except the bar. html/body pass through; #wgmod-root keeps pointer-events:none
   (already set below) and only .wg-hot / chips are pointer-events:auto. */
html, body {
    margin: 0;
    width: 100%;
    height: 100%;
    background: transparent;
    pointer-events: none;
    overflow: hidden;
}
```
Leave `#wgmod-root` and `.wg-hot` unchanged (root already `pointer-events:none`; `.wg-hot` already `auto`). No other change needed — the bar keeps `position:fixed` and its `top:17.6vh` anchor within the full-screen document.

- [ ] **Step 1 — Option B (if the spike picked B): the window is the bar box.** The document is sized to the window rect, so `html, body` fill it and the bar is positioned at the box origin instead of `position:fixed`/`17.6vh`:

```css
/* Registered own-view document sized to the bar's bounding box (window rect tracks the bar).
   The bar fills the document; tooltip overflow is absorbed by the window's padding. */
html, body {
    margin: 0;
    width: 100%;
    height: 100%;
    background: transparent;
    pointer-events: none;
    overflow: visible;   /* let hover tooltips draw into the window's padding */
}
```
And change `#wgmod-root` positioning from screen-fixed to box-relative:
```css
/* OLD: position: fixed; left: 50%; top: 17.6vh; transform: translateX(-50%); */
/* NEW (Option B): the window is placed at the bar location; the bar fills the box. */
#wgmod-root {
    position: absolute;
    left: 0;
    top: 0;
    /* width unchanged (520rem); transform removed -- the window rect is the anchor */
}
```
> Option B also requires the window-rect tracking wiring in Task 5's Option B `reposition()` and a Task 5a in-client confirmation of the rect API. Do NOT implement Option B CSS unless the spike selected B.

- [ ] **Step 2: Commit**

```bash
git add src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.css
git commit -m "style(widget): root-document input passthrough for the own-view window"
```

---

## Task 8: Build, clean-deploy, and verify this repo solo [IN-CLIENT]

**Files:** none — build/deploy/verify.

- [ ] **Step 1: Build with Python 2.7.**

Run: `C:\Python27\python.exe build/build_wotmod.py`
Expected: `dist/com.14th_ua.garageprogressbar_<version>.wotmod` written; JSON/HTML/JS/CSS + `.pyc` (no `.py`) inside.

- [ ] **Step 2: Clean-deploy — remove any stale `res_mods` overlay first** (per `gpb-build-deploy` + the "hot-reload needs overlay-at-launch" memory). Deploy the packaged `.wotmod` into `D:/Games/World_of_Tanks_EU/mods/2.3.0.1/`, deleting the prior `com.14th_ua.garageprogressbar_*.wotmod` and any `res_mods` overlay for this mod.

Run: `python build/deploy_wotmod.py --clean-overlay` (per the deploy script's flags).

- [ ] **Step 3: One-time restart for res_map.** Launch the client once so OpenWG's `ResMapManager` rebuilds `res_map.json` with `WGModResearchView`; the bar may not appear on this first launch (`layoutID` unresolved → logged no-op). Relaunch.

- [ ] **Step 4: In-game verify (this mod only installed).** In the plain garage:
  - Bar renders (all six modes as the selected vehicle dictates).
  - A clickable tick fires its command (research/unlock; watch the REPL log `[wgmod] researchUnlock ...`).
  - Ctrl-drag repositions the bar; Reset returns it.
  - Vehicle switch live-updates the bar.
  - Hover tooltips show and are not clipped.
  - **Passthrough (the spike criterion, re-confirmed in real use):** hangar buttons/carousel/tiles under and around the bar behave exactly as normal; the Esc menu and a modal dialog open and take input normally.

- [ ] **Step 5: Record the result.** If any check fails, STOP and debug via the REPL (`gpb-debug-repl`) before proceeding to MoE. Do not convert MoE on top of an unverified conversion.

---

## Task 9: Convert the MoE Calculator garage bar (sibling repo) — mirror Tasks 2–7

**Files (in `C:/Users/Dmytro Vasylkivskyi/14th_ua-moe-calculator`):**
- Create: `src/res/mods/configs/res_map/MoECalculatorView.json`
- Create: `src/res/gui/gameface/mods/14th_ua/MoECalculator/MoECalculatorView.html`
- Create: `src/res/scripts/client/moe_calculator/bridge/garage_view.py`
- Modify: `src/res/scripts/client/moe_calculator/bridge/gameface_bridge.py`
- Modify: `src/res/scripts/client/gui/mods/mod_moe_calculator.py`
- Modify: `src/res/gui/gameface/mods/14th_ua/MoECalculator/MoECalculator.js`
- Modify: `src/res/gui/gameface/mods/14th_ua/MoECalculator/MoECalculator.css`

**Interfaces:**
- Consumes: `MoEVM` (root VM), `ModDynAccessor("MoECalculatorView")`.
- Produces: `garage_view.open_window()/close_window()/active_view()`; `gameface_bridge.refresh()/push(rvm)`.
- Reuse the **windowing option chosen by Task 1** (proven on this repo first). The MoE **battle** overlay (`battle_view.py` / `MoEBattleView.json`) is UNTOUCHED.

- [ ] **Step 1: res_map config** — `src/res/mods/configs/res_map/MoECalculatorView.json`:

```json
[
    {
        "type": "Layout",
        "path": "coui://gui/gameface/mods/14th_ua/MoECalculator/MoECalculatorView.html",
        "parameters": {
            "extension": "",
            "entrance": "MoECalculatorView",
            "impl": "gameface"
        },
        "itemID": "MoECalculatorView"
    }
]
```

- [ ] **Step 2: Root HTML** — `MoECalculatorView.html` (mirrors `MoEBattleView.html`; loads `MoECalculator.css` + `MoECalculator.js`, empty body):

```html
<!doctype html>
<html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>MoECalculatorView</title>
        <link rel="stylesheet" crossorigin href="MoECalculator.css" defer />
    </head>
    <body>
        <script type="module" crossorigin src="MoECalculator.js" defer></script>
    </body>
</html>
```

- [ ] **Step 3: `garage_view.py`** — mirror this repo's `research_view.py` (Task 5), substituting `moe_calculator` / `MoEVM` / `MoECalculatorView` / `_layoutID = ModDynAccessor("MoECalculatorView")`. The MoE garage VM has **no reverse-channel commands** (no `_connect_commands`), so `_onLoading` only does the initial push:

```python
    def _onLoading(self, *args, **kwargs):
        super(MoECalculatorView, self)._onLoading(*args, **kwargs)
        try:
            from moe_calculator.bridge import gameface_bridge
            gameface_bridge.refresh()
        except Exception:
            LOG_CURRENT_EXCEPTION()
```
Use the same Option A / Option B window class the spike picked. `open_window/close_window/active_view` are identical in shape to `research_view`.

- [ ] **Step 4: `gameface_bridge.py`** — remove `attach()`/`gf_mod_inject`/`_addViewModelProperty`/`WIDGET_NAME`/`DATA_PROP`/`COUI`/`openwg_gameface` import and the `_active` global; retarget `refresh()` to `garage_view.active_view().viewModel`; drop `host_vm` from `push()` and delete its trailing host-nudge block. **Keep** `moe_data.start()` — move its kick from the old `attach()` into `install_all_listeners()` (it is already armed there via the ready listener; add the `moe_data.start()` call alongside so the fetch still kicks without `attach`).

```python
# refresh() NEW:
def refresh():
    from moe_calculator.bridge import garage_view
    view = garage_view.active_view()
    if view is None:
        LOG_NOTE("[moe] refresh: no open bar window")
        return False
    push(view.viewModel)
    return True
```

- [ ] **Step 5: `mod_moe_calculator.py`** — rewrite `_install()`'s presenter patch to `install_all_listeners()` + `garage_view.open_window()` (no `attach`), and add the same `_arm_battle_close(garage_view)` battle-entry close hook as this repo (Task 6 Step 5). `_install_battle()` is UNCHANGED (the battle overlay already uses its own window).

- [ ] **Step 6: `MoECalculator.js`** — `ModelObserver("MoECalculator")` → `ModelObserver()`; replace `model.moeData` reads with the root `model`; update the header comment. (MoE has no reverse-channel commands, so there is no `invokeCommand` VM-host change.)

Run: `grep -n "moeData\|ModelObserver(\"" src/res/gui/gameface/mods/14th_ua/MoECalculator/MoECalculator.js`
Expected: no `moeData` matches; only the no-arg root `ModelObserver(`.

- [ ] **Step 7: `MoECalculator.css`** — apply the same Option A / B root-document rules as Task 7. Note `#moe-root` is `pointer-events:auto` on the whole panel box (not `none` like `#wgmod-root`); under Option A add `html, body { pointer-events:none }` above it so only the panel box captures input and the rest passes through. The MoE bar anchors to the carousel via `bottom` (`.moe-rows2 { bottom:28vh }`) — keep that; only add the document passthrough.

- [ ] **Step 8: Byte-compile (Py 2.7) + MoE pytest suite green.**

Run:
```bash
C:\Python27\python.exe -m py_compile \
  src/res/scripts/client/moe_calculator/bridge/garage_view.py \
  src/res/scripts/client/moe_calculator/bridge/gameface_bridge.py \
  src/res/scripts/client/gui/mods/mod_moe_calculator.py
python -m pytest -q
```
Expected: py_compile exits 0; pytest all pass.

- [ ] **Step 9: Commit (MoE repo)**

```bash
git -C "C:/Users/Dmytro Vasylkivskyi/14th_ua-moe-calculator" add -A
git -C "C:/Users/Dmytro Vasylkivskyi/14th_ua-moe-calculator" \
  commit -m "refactor(bridge): convert the garage bar to a registered own-view window"
```

---

## Task 10: Fix the debug-REPL port clash (MoE moves 2223 → 2224)

**Files (MoE repo only — this repo keeps 2223, no value change):**
- Modify: `tools/dev/mod_moe_calculator_debug.py` (`PORT = 2223` → `2224`, and the two docstring `2223` mentions)
- Modify: `tools/dev/repl_client.py` (`HOST, PORT = "127.0.0.1", 2223` → `2224`, and the docstring)
- Modify: `tools/dev/build_debug_wotmod.py` (meta `<description>` `2223` → `2224`, and the connection-refused hint text)
- Modify: `tools/dev/README.md` + `TASKS/in-battle-moe-handoff.md` + `TASKS/in-battle-moe-mount-rework.md` (any `2223` → `2224`)

**Interfaces:** dev-only, not shipped. Garage Progress Bar = 2223; MoE = 2224.

- [ ] **Step 1: Change the MoE debug server port.** In `mod_moe_calculator_debug.py`: `PORT = 2224`; update the `Listens on 127.0.0.1:2223` docstring line to `2224`.

- [ ] **Step 2: Change the MoE REPL client port.** In `repl_client.py`: `HOST, PORT = "127.0.0.1", 2224`; update the docstring `2223` → `2224`.

- [ ] **Step 3: Change the MoE debug meta + hint.** In `build_debug_wotmod.py`: `<description>DEV-ONLY: TCP REPL on 127.0.0.1:2224. ...` and the `"...REPL port 2223)"` hint → `2224`.

- [ ] **Step 4: Update MoE docs.** Replace remaining `2223` with `2224` in `tools/dev/README.md` and the two `TASKS/*.md` files.

Run (MoE repo): `grep -rn "2223" tools/ TASKS/`
Expected: no matches remain (all moved to 2224).

- [ ] **Step 5: Update THIS repo's docs to note the split (no port value change).** In `tools/dev/README.md`, `CONTRIBUTING.md`, and `.claude/skills/gpb-debug-repl/SKILL.md`, add a one-line note that Garage Progress Bar uses **2223** and the sibling MoE Calculator uses **2224** so both debug REPLs can run simultaneously.

- [ ] **Step 6: Commit both repos**

```bash
git -C "C:/Users/Dmytro Vasylkivskyi/14th_ua-moe-calculator" add -A
git -C "C:/Users/Dmytro Vasylkivskyi/14th_ua-moe-calculator" \
  commit -m "chore(dev): move debug REPL to port 2224 (avoid clash with the research bar)"
git add tools/dev/README.md CONTRIBUTING.md .claude/skills/gpb-debug-repl/SKILL.md
git commit -m "docs(dev): note the 2223/2224 debug-REPL port split between the two mods"
```

---

## Task 11: Redeploy both + verify TOGETHER [IN-CLIENT]

**Files:** none — build/deploy/verify both mods installed at once.

- [ ] **Step 1: Build MoE with Python 2.7** (`C:\Python27\python.exe build/build_wotmod.py` in the MoE repo). Confirm `MoECalculatorView.json` + `MoECalculatorView.html` are in the package.

- [ ] **Step 2: Clean-deploy BOTH mods** into `D:/Games/World_of_Tanks_EU/mods/2.3.0.1/`, removing every stale `res_mods` overlay for both (this also clears this repo's stale 0.5.0 package). Include the OpenWG GameFace dependency `.wotmod` as usual.

- [ ] **Step 3: One-time restart** so OpenWG registers BOTH new `res_map` layouts (`WGModResearchView`, `MoECalculatorView`). Relaunch.

- [ ] **Step 4: Verify both bars together in the plain garage.** Acceptance criteria (all required):
  - **Rendering non-interference:** BOTH bars render simultaneously (the original bug — MoE blanked the research bar — is gone). Neither restyles the other.
  - **Both interactive:** the research bar's ticks/chips fire commands and Ctrl-drag works; the MoE bar shows its marks/tooltips.
  - **Input non-interference (hard criterion):** with both bars open, the hangar, carousel, vehicle tiles, the Esc/in-game menu, and any modal dialog all behave EXACTLY as with no mods — no starved keyboard/mouse, no swallowed clicks, no blocked hover.
  - **Battle round-trip:** enter a battle and return — both bars close on battle entry and re-open on hangar return (the `_arm_battle_close` hook), and nothing leaks into the battle HUD.

- [ ] **Step 5: Record the result.** If any criterion fails, debug via the two REPLs (2223 = research bar, 2224 = MoE) before declaring done.

---

## Task 12: Capture the reusable rule in the harness skills

**Files (in the installed `wotmod-harness` plugin skills):**
- Modify: `wotmod-gameface-widget` SKILL.md — add the standalone-view rule + interactive-lobby-window notes.
- Modify: `wotmod-architecture` SKILL.md — cross-reference the rule from the binding-surface section.

**Interfaces:** documentation only.

- [ ] **Step 1: Add the rule to `wotmod-gameface-widget`** (verbatim from the spec's "Harness update" section):

> A standalone mod widget must register its **own** view (res_map config JSON +
> `ViewImpl`/`WindowImpl` + root `ModelObserver`). Use `gf_mod_inject` **only** to
> deliberately augment an existing WG view — never for a standalone widget: every mod that
> injects onto the same sub-view shares one `ModInjectModel` and the last writer wins, so
> two such mods silently blank each other.

- [ ] **Step 2: Add the interactive-lobby-window notes:** layer choice **below** modal dialogs (`WindowLayer.WINDOW`, never TOP_WINDOW/OVERLAY — the keyboard-sink trap), `show(focus=False)`, `pointer-events:none` root document + `pointer-events:auto` interactive sub-region for click passthrough, and the A-vs-B windowing decision rule (input non-interference is the deciding criterion). Reference the working examples: `moe_calculator/bridge/battle_view.py` (info-only, full-screen) and this conversion's `research_view.py` (interactive).

- [ ] **Step 3: Cross-reference from `wotmod-architecture`** in the binding-surface / "listeners re-arm every mount" area: point to the `wotmod-gameface-widget` standalone-view rule as the correct binding surface for a mod-owned widget.

- [ ] **Step 4: Commit the harness plugin** (its own repo; commit locally, push only if asked — mirrors the existing harness-handoff state).

---

## Self-Review

**1. Spec coverage:**
- Convert this repo to own-view → Tasks 2–8. ✓
- Convert MoE → Task 9. ✓
- Debug-REPL port clash → Task 10. ✓
- Clean redeploy + verify both together → Tasks 8 (solo) + 11 (together). ✓
- Harness skills update → Task 12. ✓
- Spike-first, A-vs-B decision → Task 1 gates Tasks 5 & 7. ✓
- Sequencing (spike → this mod → MoE → port → joint verify → harness) → Task order matches. ✓
- Domain/adapter unchanged, pytest stays green → Tasks 6/9 include the pytest gate. ✓
- Input non-interference as a hard, choice-gating criterion → Task 1 + Tasks 8/11 acceptance. ✓

**2. Placeholder scan:** The only deliberately-deferred items are (a) Task 1's recorded A/B decision (it is the spike's output, not a plan gap) and (b) Task 5 Option B's exact window-rect API + `BAR_RECT` values, explicitly flagged as a Task 5a in-client confirmation because they are only reachable by live probing — and only if the spike selects B. All code steps that can be written now are written in full.

**3. Type/name consistency:** `WGModResearchView` (itemID = entrance = class = `_layoutID` accessor arg) consistent across Tasks 2/3/5. `research_view.open_window/close_window/active_view` used identically in Tasks 5/6. `push(rvm)` single-arg after Task 6 Step 3 — matched in `refresh()` Step 2 and `research_view._onLoading`. MoE mirrors: `MoECalculatorView` + `garage_view.*` consistent across Task 9.

---

## Execution Handoff

Because Tasks 1, 8, and 11 are **[IN-CLIENT]** (only the user can launch WoT), this plan is best run **inline** so Claude writes each code task and hands the in-client tasks to the user at the natural checkpoints, rather than dispatching blind subagents across an unrunnable boundary.
