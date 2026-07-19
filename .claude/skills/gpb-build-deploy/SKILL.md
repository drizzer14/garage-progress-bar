---
name: gpb-build-deploy
description: Build, deploy, test, and hot-reload the Garage Progress Bar WoT mod locally — the exact scripts, install path, client version, and overlay path for THIS mod. Use whenever building the .wotmod package, deploying into a local World of Tanks install, running the pytest suite, hot-reloading JS/CSS changes, or verifying a change in-game. (For the generic packaging/deploy/hot-reload pattern behind these commands, see the wotmod-build-deploy harness skill; for live in-client REPL introspection, see gpb-debug-repl.)
---

# Building, deploying & testing the wgmod

Generic mechanics (two Pythons, `.wotmod` stored-ZIP + `meta.xml`, the `res_mods` shadowing
trap, the hot-reload overlay loop): see the **wotmod-build-deploy** harness skill. This
skill is the concrete wiring for the Garage Progress Bar.

## Commands
```sh
# Build the package (Py 2.7) -> dist/com.14th_ua.garageprogressbar_<version>.wotmod
& "C:\Python27\python.exe" build/build_wotmod.py

# Clean-build-and-deploy into a local install (Py 2.7, CLIENT CLOSED — file locks)
& "C:\Python27\python.exe" build/deploy_wotmod.py "D:/Games/World_of_Tanks_EU" 2.3.1.0
& "C:\Python27\python.exe" build/deploy_wotmod.py          # uses deploy.local.json (gitignored)

# Domain-layer tests (Py 3.13) — engine-free, no game needed
& "<py3>" -m pytest -q
& "<py3>" -m pytest tests/test_resolver_techtree.py -q     # single file

# Hot-reload JS/CSS ONLY, no relaunch (Py 3.13) — then switch screens in-game to refresh
& "<py3>" tools/dev/sync_gameface.py "D:/Games/World_of_Tanks_EU" 2.3.1.0
```
`<py3>` = `%LOCALAPPDATA%\Programs\Python\Python313\python.exe`.

## This mod's specifics
- **Package:** `dist/com.14th_ua.garageprogressbar_<version>.wotmod`. Build with Py 2.7 ONLY.
- **The packaged build is size-optimized (behaviour/UI unchanged).** `build_wotmod.py`
  self-re-execs under `-OO` (strips `.pyc` docstrings) and minifies `WGModResearch.js`/`.css`
  through the vendored `build/vendor/rjsmin.py` / `rcssmin.py` (comment + whitespace only,
  no name mangling). Source stays commented; **`sync_gameface.py` deploys the RAW assets**
  for readable in-client debugging. Net effect: ~357 KB → ~199 KB. If a JS edit ever renders
  differently packaged-vs-hot-reloaded, suspect the minifier and syntax-check the packaged
  file (`node --check` on the extracted `.js` as a `.mjs`).
- **Overlay path** (hot-reload): `res_mods/<ver>/gui/gameface/mods/14th_ua/WGModResearch/`.
  `deploy_wotmod.py` cleans both `mods/` and `res_mods/` before building; it WARNS when the
  overlay is present and takes `--clean-overlay` to remove it as part of the deploy. After
  every `deploy_wotmod.py`, re-run `sync_gameface.py` (else the stale overlay shadows the
  fresh package); before a clean ship-verification, REMOVE the overlay so you test the
  packaged assets. Only `WGModResearch.js`/`.css` hot-reload — Python (mount/data) changes
  need build + deploy + full relaunch.
- **Deploying an ALREADY-released `dist\` artifact as-is (NO rebuild):** do NOT use
  `deploy_wotmod.py` — it calls `build_wotmod.main()` and re-packages from source every run, so
  you'd ship a fresh size-optimized/minified rebuild, not the released bytes. When the point is
  to land the exact tested/published artifact (e.g. a QA-gate + deploy of the released
  v1.3.0 `.wotmod`), copy the precise
  `dist\com.14th_ua.garageprogressbar_<ver>.wotmod` by hand into `mods\<client-version>\`
  (e.g. `mods\2.3.1.0\`) with the CLIENT CLOSED — a running client locks the stale
  `..._<oldver>.wotmod` (`Device or resource busy` on delete), so the old-copy cleanup can't
  finish while it's open. (Same-`<id>` highest-version-wins and scan-only-at-launch mechanics:
  see **wotmod-build-deploy**.) Reserve `deploy_wotmod.py` for the normal build-and-deploy loop.
- **Target:** EU/global `2.3.1.0` only (the current `deploy.local.json` client version — the
  literal above is only an example; a client bump is run via **wotmod-upgrade-analyzer** /
  **wotmod-upgrade-implementer**, not hand-edited here).
- **Dependencies (same `mods/<version>/`):** OpenWG GameFace is a **hard** dependency; the
  bar itself renders without ModsSettingsAPI (`izeberg.modssettingsapi`), but the settings
  panel, per-mode toggles, and drag-position persistence need it.

## What's unit-testable vs in-game-only (plan verification around this)
`pytest` (Py 3.13, no client) covers the ENGINE-FREE code only: everything under `domain/`
(builder, resolvers, types) plus `adapter/recent.py`, `adapter/format.py`, `bridge/wulf_args.py`,
and `bridge/mod_settings.py` (the test stubs `debug_utils`; MSA calls inside degrade to no-ops, so
`clamp_pos`/`set_position`/`_on_reset`/`_full_settings_for_write` ARE testable). Everything that
imports live game symbols is NOT pytest-importable and can only be checked in-client (debug REPL):
`adapter/engine_adapter.py`, the `*_read.py` readers, `adapter/_read_common.py`, `adapter/actions.py`,
`bridge/gameface_bridge.py`. ALL of `WGModResearch.js`/`.css` and the MSA settings PANEL (stepper
labels/values, reset button) are in-game-only too. A packaged JS build can at least be
syntax-checked headless: `node --check` the raw `.js` as a `.mjs`, and extract+`node --check` the
minified copy from the built `.wotmod` (Py2 on Windows can't write to Git Bash `/tmp` — use a
repo-relative path when extracting). So: a domain/adapter-recent/mod_settings fix ships behind
green tests; a reader/bridge/JS/CSS/MSA change is code-complete only until an in-game pass.

These same gates run in CI (`.github/workflows/ci.yml`) on every push/PR — `check_version.py`,
`ruff check .`, `pytest -q` (Python 3.13; CI does NOT build the `.wotmod`). Run them locally
before pushing a release so a version drift, ruff error, or red test doesn't fail CI after the fact.

## Verifying a change actually works
Build+deploy+relaunch (or hot-reload for JS/CSS), open the Garage, select a vehicle with
research/field-mods/elite remaining, confirm the bar renders, hover/click ticks, switch
vehicles to confirm live update. For live introspection while verifying, use the
**gpb-debug-repl** skill.
