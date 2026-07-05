---
name: wgmod-build-deploy
description: Build, deploy, test, and hot-reload the Garage Progress Bar WoT mod locally — the exact scripts, install path, client version, and overlay path for THIS mod. Use whenever building the .wotmod package, deploying into a local World of Tanks install, running the pytest suite, hot-reloading JS/CSS changes, or verifying a change in-game. (For the generic packaging/deploy/hot-reload pattern behind these commands, see the wotmod-build-deploy harness skill; for live in-client REPL introspection, see wgmod-debug-repl.)
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
& "C:\Python27\python.exe" build/deploy_wotmod.py "D:/Games/World_of_Tanks_EU" 2.3.0.1
& "C:\Python27\python.exe" build/deploy_wotmod.py          # uses deploy.local.json (gitignored)

# Domain-layer tests (Py 3.13) — engine-free, no game needed
& "<py3>" -m pytest -q
& "<py3>" -m pytest tests/test_resolver_techtree.py -q     # single file

# Hot-reload JS/CSS ONLY, no relaunch (Py 3.13) — then switch screens in-game to refresh
& "<py3>" tools/dev/sync_gameface.py "D:/Games/World_of_Tanks_EU" 2.3.0.1
```
`<py3>` = `%LOCALAPPDATA%\Programs\Python\Python313\python.exe`.

## This mod's specifics
- **Package:** `dist/com.14th_ua.garageprogressbar_<version>.wotmod`. Build with Py 2.7 ONLY.
- **Overlay path** (hot-reload): `res_mods/<ver>/gui/gameface/mods/14th_ua/WGModResearch/`.
  `deploy_wotmod.py` cleans both `mods/` and `res_mods/` before building; it WARNS when the
  overlay is present and takes `--clean-overlay` to remove it as part of the deploy. After
  every `deploy_wotmod.py`, re-run `sync_gameface.py` (else the stale overlay shadows the
  fresh package); before a clean ship-verification, REMOVE the overlay so you test the
  packaged assets. Only `WGModResearch.js`/`.css` hot-reload — Python (mount/data) changes
  need build + deploy + full relaunch.
- **Target:** EU/global `2.3.0.1` only.
- **Dependencies (same `mods/<version>/`):** OpenWG GameFace is a **hard** dependency; the
  bar itself renders without ModsSettingsAPI (`izeberg.modssettingsapi`), but the settings
  panel, per-mode toggles, and drag-position persistence need it.

## Verifying a change actually works
Build+deploy+relaunch (or hot-reload for JS/CSS), open the Garage, select a vehicle with
research/field-mods/elite remaining, confirm the bar renders, hover/click ticks, switch
vehicles to confirm live update. For live introspection while verifying, use the
**wgmod-debug-repl** skill.
