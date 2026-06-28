# WGMod

A World of Tanks mod. Authored on macOS, tested/installed on a Windows PC.

> See [`RESEARCH.md`](./RESEARCH.md) for WoT modding background (engine, file
> structure, hooking, packaging, compliance).

## Layout

```
src/
  meta.xml                                  # .wotmod metadata (id, version, name)
  res/scripts/client/gui/mods/mod_wgmod.py  # mod entry point (loaded at startup)
build/
  build_wotmod.py    # compile + package -> dist/<id>_<version>.wotmod  (Python 2.7!)
  deploy_dev.py      # copy src/res into a WoT res_mods/<version> for live testing
dist/                # build output (gitignored)
```

`src/res/` mirrors the game's `res/` tree, so the same source feeds both the
dev deploy and the packaged build.

## Workflow

**Author (macOS):** edit `src/`, commit, push to the private GitHub repo.

**Test (Windows PC):**
```sh
git pull
python build/deploy_dev.py "C:/Games/World_of_Tanks" <client-version>
# launch WoT; plain .py runs from res_mods/ — no compile step
```
Tip: create `deploy.local.json` (gitignored) so you can run `deploy_dev.py` with
no args:
```json
{ "wot_path": "C:/Games/World_of_Tanks", "version": "2.3.0.1" }
```

**Package for distribution (Windows PC, Python 2.7.18):**
```sh
python build/build_wotmod.py        # -> dist/com.drizzer14.wgmod_0.1.0.wotmod
```
Copy the `.wotmod` into `World_of_Tanks/mods/<client-version>/` to install, or
upload to wgmods.net.

## Important constraints

- **WoT is Windows-only** — the Mac is authoring only; all testing is on the PC.
- **`.pyc` must be built with Python 2.7.18.** Bytecode is version-locked (not
  OS-locked), so building on the PC's 2.7 is the safe path. Python 3 bytecode
  will not load.
- `.wotmod` is a **stored (uncompressed) ZIP** with `meta.xml` at the root —
  `build_wotmod.py` handles this.

## Renaming the mod

Change the `<id>`, `<version>`, `<name>` in `src/meta.xml`, rename
`mod_wgmod.py`, and update `MOD_NAME`/`MOD_VERSION` inside it.
