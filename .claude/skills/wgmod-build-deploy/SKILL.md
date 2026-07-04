---
name: wgmod-build-deploy
description: Build, deploy, test, and hot-reload the Garage Progress Bar WoT mod locally. Use whenever building the .wotmod package, deploying into a local World of Tanks install, running the pytest suite, hot-reloading JS/CSS changes, or verifying a change in-game — anything about getting a change running and observed in the game. Covers the Python 2.7-vs-3.13 split and the mods/ vs res_mods/ shadowing trap that silently hides your build. (For live in-client REPL introspection, see the wgmod-debug-repl skill.)
---

# Building, deploying & testing the wgmod

## Two Pythons (don't mix them)
- **Python 2.7.18** `C:\Python27\python.exe` — packaging ONLY. The client runs the
  `.pyc`, and bytecode magic numbers are version-locked. Python 3 `.pyc` won't load.
- **Python 3.13** `%LOCALAPPDATA%\Programs\Python\Python313\python.exe` — pytest + dev tools.

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

## The shadowing trap (why your change "isn't loading")
WoT 2.3 loads mods ONLY from `.wotmod` in `mods/<version>/`. Loose files in
`res_mods/<version>/` OUTRANK `.wotmod`, so a stale loose copy silently shadows the
package. `deploy_wotmod.py` exists precisely to clean both before building — always
deploy through it, never hand-copy.

`sync_gameface.py` writes a `res_mods` overlay for hot-reload. Consequences:
- After EVERY `deploy_wotmod.py`, re-run `sync_gameface.py` (else the stale overlay
  shadows the fresh package).
- Before a clean ship-verification, REMOVE the overlay
  (`res_mods/<ver>/gui/gameface/mods/14th_ua/`) so you test the packaged assets.
  `deploy_wotmod.py` WARNS when the overlay is present; pass `--clean-overlay` to
  have it removed as part of the deploy.
- Only `WGModResearch.js`/`.css` hot-reload. Python (mount/data) changes need
  build + deploy + full client relaunch.

Other constraints: `.wotmod` is a STORED (uncompressed) ZIP with `meta.xml` at the
root (the build script handles this); EU/global 2.3.0.1 only; OpenWG GameFace must
be installed in the same `mods/<version>/` (hard dependency), and ModsSettingsAPI
(`izeberg.modssettingsapi`) should be too — the settings panel, per-mode toggles,
and drag-position persistence need it (the bar itself still renders without it).

## Verifying a change actually works
Build+deploy+relaunch (or hot-reload for JS/CSS), open the Garage, select a vehicle
with research/field-mods/elite remaining, confirm the bar renders, hover/click ticks,
switch vehicles to confirm live update. For live introspection while verifying, use
the **wgmod-debug-repl** skill.
