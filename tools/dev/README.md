# Dev tools (WoT 2.3 EU)

In-game introspection + the real dev loop for this mod. **Not shipped** with the mod.

## Environment (this PC)
- WoT install: `D:\Games\World_of_Tanks_EU`, version **2.4.0.1**. OpenWG Gameface installed (`mods\2.4.0.1\net.openwg`).
- **Python 2.7.18** at `C:\Python27\python.exe` — packaging only (compiles `.pyc`; bytecode is 2.7-locked).
- **Python 3.13** at `%LOCALAPPDATA%\Programs\Python\Python313\python.exe` — runs pytest + the REPL client.
- Git at `C:\Program Files\Git\cmd\git.exe`, `core.longpaths=true` (needed for decompiled clones).

## The dev loop (WoT 2.3 loads ONLY `.wotmod`)
Loose `res_mods\<version>\scripts` does **not** load in 2.3, and `res_mods` outranks `.wotmod`
(a stale loose copy SHADOWS the package → client ignores the mod). So always:

```
# 1) close the WoT client (file locks); then build+deploy the real mod:
& "C:\Python27\python.exe" build\deploy_wotmod.py "D:\Games\World_of_Tanks_EU" 2.4.0.1
# 2) relaunch the client. (OpenWG may auto-restart once when res_map changes.)
```
`deploy_wotmod.py` auto-cleans old `com.14th_ua.garageprogressbar_[0-9]*.wotmod` and loose leftovers.

### Hot-reload loop for JS/CSS-only changes (NO relaunch)
`coui://gui/...` resolves through a merged FS where `res_mods/<version>/` outranks
the `.wotmod`, and the hangar sub-view re-fetches our assets each time its document
is rebuilt. So for **visual-only** (WGModResearch.js/.css) iteration:
```
# client may stay running:
& "<py3>" tools\dev\sync_gameface.py "D:\Games\World_of_Tanks_EU" 2.4.0.1
# then in-game: switch to another screen (e.g. Tech Tree) and back to the Garage.
```
This is ONLY for front-end assets. Python (mount/data) changes still need
build+deploy+relaunch. **Caveats:** after every `deploy_wotmod.py`, re-run
`sync_gameface.py` (else the stale overlay shadows the fresh package); and **remove
the overlay** (`res_mods\2.4.0.1\gui\gameface\mods\14th_ua\`) before a clean
ship-verification so you're testing the packaged assets.

Unit tests (engine-free domain layer, Python 3):
```
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -m pytest -q   # expect green
```

## Debug REPL (live introspection)
This mod's own debug REPL package has been retired. Live in-client introspection now goes
through ONE harness-owned REPL shared across all 14th_ua mods:
`wotmod-harness/plugins/wotmod/tools/debug-repl/` (package id `com.wotmod_harness.debug_repl`,
port **2223**, client `repl_client.py` there). See the **wotmod:debug-repl** harness skill for
build/deploy/drive commands, and this repo's **gpb-debug-repl** skill for this mod's probe
snippets.

## Decompiled source (re-clone as needed; not in repo)
Match the client's branch/region — use the **EU** branch of `IzeBerg/wot-src` (live 2.4.0.1):
```
& $git clone --depth 1 --branch EU --single-branch https://github.com/IzeBerg/wot-src.git wot-src-eu
```
(The repo's default branch is a different regional client — cross-check against
the live `res/packages/scripts.pkg` by listing module filenames.)
