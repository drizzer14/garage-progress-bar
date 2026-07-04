---
name: wgmod-debug-repl
description: Live in-client introspection for the Garage Progress Bar WoT mod via its debug TCP REPL, plus dev-loop troubleshooting (the bar not showing, stale assets, finding game symbols in the decompiled client). Use whenever you need to inspect live game state from the running client, probe BigWorld/WG APIs interactively, figure out why the bar isn't loading or updating in-game, or locate the right game method/symbol against the decompiled source.
---

# Live introspection & dev-loop troubleshooting

## The debug REPL
A separate debug package runs a TCP REPL on **127.0.0.1:2223** inside the client.
```sh
# Build/deploy the debug package (Py 2.7, client CLOSED)
& "C:\Python27\python.exe" tools/dev/build_debug_wotmod.py "D:\Games\World_of_Tanks_EU" 2.3.0.1
# Drive it from the host (Py 3.13, client RUNNING, in Garage)
& "<py3>" tools/dev/repl_client.py "<expr>"
& "<py3>" tools/dev/repl_client.py --file cmds.txt
```
- One command per line; state is shared only WITHIN one run, so put interdependent
  commands in a single `--file`. For multi-line code, write a `.py` and send
  `execfile(r'<abs path>')` as one command.
- Keep the debug package SLIM (only `mod_wgmod_debug.pyc`). If it also ships
  `wgmod_research` it conflicts with the real mod and the client ignores BOTH.

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

# probe an unknown game API: the client is compiled .pyc, so inspect.getsource
# raises IOError -- read arg names off the bytecode instead.
f = obj.someMethod
code = f.im_func.func_code if hasattr(f, "im_func") else f.func_code
echo(list(code.co_varnames[:code.co_argcount]))   # -> ['self', 'vehicleCD', ...]
# then just CALL it with live values to learn the return shape (namedtuples expose
# _fields; e.g. UnlockProps._fields, BlueprintsRequester.getFragmentDiscountAndCost).
```
- The deployed `wgmod_research` the REPL imports is the LAST BUILT one — a source edit
  you haven't `deploy_wotmod`'d + relaunched is NOT reflected. To sanity-check new pure
  logic against LIVE data without a redeploy, read inputs via the deployed adapter, then
  apply the new formula inline in the probe (how Bug 6/7 pricing was verified pre-deploy).

## "The bar isn't loading / not updating"
1. **Shadowing** — a loose `res_mods/<ver>/` copy outranks the `.wotmod`. Confirm you
   deployed via `deploy_wotmod.py` and that no stale `sync_gameface.py` overlay lingers
   (see the wgmod-build-deploy skill).
2. **Listener dropped after a battle** — the bar stops updating only after entering/
   exiting a battle → a listener didn't re-arm. See the re-arming convention in the
   wgmod-architecture skill; check `python.log` for the `[wgmod] ... (re)armed` and
   `[wgmod] push ...` LOG_NOTE markers the bridge emits.
3. **OpenWG missing** — the entry point raises if `openwg_gameface` is absent; confirm
   the dependency `.wotmod` is in the same `mods/<version>/`.
4. **Special/event hangars** don't expose the params sub-view, so the bar won't mount
   there — expected.

## Finding game symbols (decompiled client)
Re-clone the decompiled source matching the client's region/branch (EU = `2.3`); it's
NOT in the repo. Cross-check module names against the live `res/packages/scripts.pkg`
since the repo's default branch may be a different regional client. Exact clone
command + caveats: `tools/dev/README.md`.
