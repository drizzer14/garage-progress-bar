# Contributing / developer notes

Developer documentation for **Garage Progress Bar** (`com.14th_ua.garageprogressbar`).
Player-facing docs live in [`README.md`](./README.md) and [`INSTALL.md`](./INSTALL.md).

> For the day-to-day dev loop, debug REPL, and notes on re-cloning the decompiled
> client source, see [`tools/dev/README.md`](./tools/dev/README.md).

## Layout

```
src/
  meta.xml                                         # .wotmod metadata (id, version, name, description)
  res/scripts/client/gui/mods/mod_wgmod.py         # entry point: patches the hangar presenter
  res/scripts/client/wgmod_research/               # domain (engine-free) + adapter + bridge
  res/gui/gameface/mods/14th_ua/WGModResearch/     # widget JS + CSS (rendered via OpenWG GameFace)
build/
  build_wotmod.py    # compile (.py->.pyc) + package -> dist/<id>_<version>.wotmod   (Python 2.7!)
  deploy_wotmod.py   # clean + build + copy the .wotmod into a WoT install            (Python 2.7!)
  deploy_dev.py      # DEPRECATED — loose res_mods scripts do NOT load in WoT 2.3; use deploy_wotmod.py
installer/
  wgmod-setup.iss      # Inno Setup script -> dist/GarageProgressBar-Setup-<version>.exe
  build_installer.ps1  # locate ISCC + compile the installer
  vendor/              # bundled OpenWG GameFace + ModsSettingsAPI .wotmods (installed only if missing)
tests/               # pytest (run with Python 3.13) for the domain layer
tools/dev/           # debug REPL server/client (NOT shipped) + dev notes
dist/                # build output (gitignored)
```

## Build a distributable package (Python 2.7.18)

```sh
python build/build_wotmod.py        # -> dist/com.14th_ua.garageprogressbar_<version>.wotmod
```

## Build + deploy into a local WoT install (Python 2.7.18, client CLOSED)

```sh
python build/deploy_wotmod.py "D:/Games/World_of_Tanks_EU" 2.3.0.1
# or create deploy.local.json (gitignored): { "wot_path": "...", "version": "2.3.0.1" }
python build/deploy_wotmod.py
```

`deploy_wotmod.py` removes old `<id>_*.wotmod` and any loose `res_mods` leftovers
(which would otherwise shadow the package) before building and copying the fresh
`.wotmod` in. Fully restart the client afterwards.

## Run the tests (Python 3.13)

```sh
python -m pytest -q
```

## JS/CSS-only changes (hot reload, no relaunch)

```sh
python tools/dev/sync_gameface.py "<install>" 2.3.0.1
# then in-game: switch to another screen and back to the Garage
```

## Important constraints

- **`.pyc` must be built with Python 2.7.18.** Bytecode is version-locked (not
  OS-locked). Python 3 bytecode will not load in the client. Tests run on Python 3.13.
- `.wotmod` is a **stored (uncompressed) ZIP** with `meta.xml` at the root —
  `build_wotmod.py` handles this.
- **WoT 2.3 loads mods only from `.wotmod` in `mods/<version>/`.** `res_mods/<version>/`
  outranks `.wotmod`, so a stale loose copy silently shadows the package — always
  deploy via `deploy_wotmod.py` and keep `res_mods` clean for ship verification.
- Built for the **Wargaming EU/global** client (version 2.3.0.1) only.

## Releasing

Bumping the version touches several files (meta, entry point, INSTALL, installer,
build strings) and then tags, builds the installer, and publishes the GitHub
release. Follow the `wgmod-release` skill for the exact steps.

## Renaming the mod

Change `<id>`, `<version>`, `<name>`, `<description>` in `src/meta.xml`, and update
`MOD_NAME`/`MOD_VERSION` in `src/res/scripts/client/gui/mods/mod_wgmod.py`. Changing
`<id>` also changes the output `.wotmod` filename and the cleanup glob in
`deploy_wotmod.py`.
