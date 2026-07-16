---
name: gpb-debug-repl
description: Live in-client introspection for the Garage Progress Bar WoT mod via its debug TCP REPL — the specific debug package, tools, and probe snippets for THIS mod. Use whenever you need to inspect live game state, force a widget refresh, or debug why the bar isn't loading/updating in the running client. (For the generic probe technique and decompiled-source navigation, see the wotmod-debug-repl harness skill.)
---

# Live introspection for the wgmod

Generic technique (bytecode arg-name probing, slim debug package, decompiled-source
navigation, the general "isn't loading" checklist): see the **wotmod-debug-repl** harness
skill. This skill is this mod's concrete REPL + snippets.

## The debug REPL
A separate debug package runs a TCP REPL on **127.0.0.1:2223** inside the client (the sibling
MoE Calculator's debug REPL uses **2224**, so both mods' debug servers can run simultaneously).
```sh
# Build/deploy the debug package (Py 2.7, client CLOSED)
& "C:\Python27\python.exe" tools/dev/build_debug_wotmod.py "D:\Games\World_of_Tanks_EU" 2.3.1.0
# Drive it from the host (Py 3.13, client RUNNING, in Garage)
& "<py3>" tools/dev/repl_client.py "<expr>"
& "<py3>" tools/dev/repl_client.py --file cmds.txt
```
- One command per line; state is shared only WITHIN one run, so put interdependent commands
  in a single `--file`. For multi-line code, write a `.py` and send `execfile(r'<abs path>')`.
- Keep the debug package SLIM (only `mod_wgmod_debug.pyc`). If it also ships `wgmod_research`
  it conflicts with the real mod and the client ignores BOTH.

### Handy snippets
```python
# current vehicle -> snapshot -> model
from CurrentVehicle import g_currentVehicle
from wgmod_research.adapter import engine_adapter
from wgmod_research.domain.builder import build_model
m = build_model(engine_adapter.build_snapshot())
(m.mode, m.scale_min, m.scale_max, m.fill_vehicle, m.fill_free, len(m.ticks))

# force a refresh of the mounted widget
from wgmod_research.bridge import gameface_bridge as B
B.refresh()
```
The deployed `wgmod_research` the REPL imports is the LAST BUILT one — a source edit you
haven't `deploy_wotmod`'d + relaunched is NOT reflected. To sanity-check new pure logic
against LIVE data without a redeploy, read inputs via the deployed adapter, then apply the
new formula inline in the probe.

## "The bar isn't loading / not updating" — this mod's specifics
Beyond the generic checklist in the harness skill:
1. **Listener dropped after a battle** — the bar stops updating only after entering/exiting a
   battle → a listener didn't re-arm. See the re-arming convention in **gpb-architecture**;
   check `python.log` for the `[wgmod] ... (re)armed` and `[wgmod] push ...` LOG_NOTE markers
   the bridge emits.
2. **OpenWG missing** — the entry point raises if `openwg_gameface` is absent; confirm the
   dependency `.wotmod` is in the same `mods/<version>/`.
3. **Special/event hangars** don't expose the params sub-view, so the bar won't mount there
   — expected.

The decompiled source for locating symbols: EU = the `2.3`-series branch; cross-check against
the live `res/packages/scripts.pkg`. Exact clone command + caveats: `tools/dev/README.md`.
