# Dev tools (WoT 2.3 EU)

In-game introspection + the real dev loop for this mod. **Not shipped** with the mod.

## Environment (this PC)
- WoT install: `D:\Games\World_of_Tanks_EU`, version **2.3.1.0**. OpenWG Gameface installed (`mods\2.3.1.0\net.openwg`).
- **Python 2.7.18** at `C:\Python27\python.exe` — packaging only (compiles `.pyc`; bytecode is 2.7-locked).
- **Python 3.13** at `%LOCALAPPDATA%\Programs\Python\Python313\python.exe` — runs pytest + the REPL client.
- Git at `C:\Program Files\Git\cmd\git.exe`, `core.longpaths=true` (needed for decompiled clones).

## The dev loop (WoT 2.3 loads ONLY `.wotmod`)
Loose `res_mods\<version>\scripts` does **not** load in 2.3, and `res_mods` outranks `.wotmod`
(a stale loose copy SHADOWS the package → client ignores the mod). So always:

```
# 1) close the WoT client (file locks); then build+deploy the real mod:
& "C:\Python27\python.exe" build\deploy_wotmod.py "D:\Games\World_of_Tanks_EU" 2.3.1.0
# 2) relaunch the client. (OpenWG may auto-restart once when res_map changes.)
```
`deploy_wotmod.py` auto-cleans old `com.14th_ua.garageprogressbar_[0-9]*.wotmod` and loose leftovers.

### Hot-reload loop for JS/CSS-only changes (NO relaunch)
`coui://gui/...` resolves through a merged FS where `res_mods/<version>/` outranks
the `.wotmod`, and the hangar sub-view re-fetches our assets each time its document
is rebuilt. So for **visual-only** (WGModResearch.js/.css) iteration:
```
# client may stay running:
& "<py3>" tools\dev\sync_gameface.py "D:\Games\World_of_Tanks_EU" 2.3.1.0
# then in-game: switch to another screen (e.g. Tech Tree) and back to the Garage.
```
This is ONLY for front-end assets. Python (mount/data) changes still need
build+deploy+relaunch. **Caveats:** after every `deploy_wotmod.py`, re-run
`sync_gameface.py` (else the stale overlay shadows the fresh package); and **remove
the overlay** (`res_mods\2.3.1.0\gui\gameface\mods\14th_ua\`) before a clean
ship-verification so you're testing the packaged assets.

Unit tests (engine-free domain layer, Python 3):
```
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -m pytest -q   # expect green
```

## Debug REPL (live introspection)
`com.14th_ua.garageprogressbar_debug.wotmod` runs a TCP REPL on **127.0.0.1:2223** in the client
(the sibling MoE Calculator's debug REPL uses **2224**, so both can run at once).
- Build/deploy it (client closed):
  `& "C:\Python27\python.exe" tools\dev\build_debug_wotmod.py "D:\Games\World_of_Tanks_EU" 2.3.1.0`
- Drive it from the host (client running, in Garage):
  `& "<py3>" tools\dev\repl_client.py "<expr>"` or `--file cmds.txt`
- One command per line; state shared only within one run → put interdependent
  commands in one `--file`. For multi-line code: write a `.py` and send
  `execfile(r'<abs path>')` as one command.
- Keep the debug package SLIM (only `mod_wgmod_debug.pyc`). If it also ships
  `wgmod_research`, it conflicts with the real mod and WoT ignores it.

### Handy REPL snippets
The canonical probe snippets (current-vehicle → snapshot → model; force a widget refresh)
live in the **gpb-debug-repl** skill's "Handy snippets" section — kept there so the two
copies can't drift. See `.claude/skills/gpb-debug-repl/SKILL.md`.

## Decompiled source (re-clone as needed; not in repo)
Match the client's branch/region — use the **EU** branch (`2.3`):
```
& $git clone --depth 1 --branch 2.3 --single-branch https://github.com/StranikS-Scan/WorldOfTanks-Decompiled.git wot-eu
```
(The repo's default branch is a different regional client — cross-check against
the live `res/packages/scripts.pkg` by listing module filenames.)
