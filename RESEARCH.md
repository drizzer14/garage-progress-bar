# World of Tanks Mod Development — Research Notes

_Last updated: 2026-06-28. Game baseline: WoT 2.x (Gameface UI era)._

## 1. The stack at a glance

| Layer | Technology | Notes |
|-------|-----------|-------|
| Engine | BigWorld (Core engine) | Exposed to mods via the `BigWorld` Python module |
| Scripting | **Python 2.7.18** | Yes — still 2.7 in 2026. Use the python.org 2.7.18 build to compile `.pyc`. |
| Legacy UI | Flash / ActionScript 3 | `gui/flash/` — being phased out |
| Modern UI | **Gameface** (HTML/CSS/JS-based) | WoT 2.0+. Lives under `gui/unbound/`. |
| Config | XML | Game data, vehicle defs, etc. |

## 2. Game file structure

Top-level install folders:
- `res/` — base game resources. **Read-only, never modify.**
- `res_mods/<version>/` — unpacked overrides; files here override their `res/` equivalents. **Dev workflow.**
- `mods/<version>/` — packaged `.wotmod` archives. **Distribution.**
- `replays/`, `win64/` (engine binaries)
- Root config: `version.xml`, `paths.xml`, `game_info.xml`

The `<version>` folder must match the client version exactly (e.g. `2.3.0.1/`) and is updated each patch.

### Python script locations
- `res_mods/<version>/scripts/client/mods/` — main mod entry point
- `res_mods/<version>/scripts/client/gui/mods/` — GUI-related Python, loaded **alphabetically** (use ordering prefixes)
- `mods/configs/` — community convention for config files

### UI asset locations
- `res_mods/<version>/gui/flash/` — legacy Flash/AS3 overrides
- `res_mods/<version>/gui/unbound/` — modern Gameface UI (WoT 2.0+)
- `res_mods/<version>/spaces/` — per-map overrides

## 3. Two workflows

**Development (`res_mods/`)** — drop plain `.py` files directly in; instant testing, no compile step. Fastest iteration.

**Distribution (`.wotmod`)** — a ZIP archive whose internal path mirrors `res/`. Python **must** be compiled to `.pyc` (plain `.py` does not execute from packages). `.wotmod` has *lower* load priority than `res_mods/`.

```
my_mod.wotmod (ZIP)
└── res/scripts/client/gui/mods/mod_example.pyc
```

## 4. How mods load & hook the game

- Loader scans `scripts/client/mods/` and `scripts/client/gui/mods/` and loads every `.pyc` at runtime.
- Standard technique is **monkey-patching** (method reassignment):
  ```python
  def new_function(self, *a, **kw):
      result = old_function(self, *a, **kw)  # call original
      # custom logic
      return result
  old_function = OriginalClass.method
  OriginalClass.method = new_function
  ```
- Engine access via `import BigWorld` — e.g. `BigWorld.player()`. Other engine modules: `Vehicle`, `Avatar`.

## 5. Modern dependency stack (WoT 2.0+)

Many current mods depend on a shared infra installed as `.wotmod` files:
- **Gameface** (OpenWG) — modern UI runtime/bridge
- **ModsList** — mod registry/menu
- **ModsSettings API** — standardized in-game settings panel

OpenWG maintains a Gameface GitLab repo with releases for WoT 2.0.

## 6. Key resources

- **Official Wargaming Modding Hub** — https://wgmods.dev/docs (Getting Started, API, decompiled source analysis, Fair Play guidelines)
- **Community docs (wotstat)** — https://docs.wotstat.info/en/ (env setup, tutorials: Fast Equipment Demount, Armor Pen Calculator)
- **Official mod portal** — https://wgmods.net/
- **Wargaming Developer API** (account/stats data) — https://developers.wargaming.net/
- **Korean Random forum** — central modding community hub (much content in Russian)
- **wot-debugserver** (juho-p) — TCP REPL into the live BigWorld engine for experimentation
- Example repos: `PolyacovYury/PYmods`, `jstar88/wotmods`, `OpenMods-WoT/core`
- Decompiled client source — referenced from wgmods.dev for locating target methods

## 7. Fair play / compliance

Wargaming publishes Fair Play guidelines. Allowed: UI, info, cosmetic, QoL mods. Forbidden: anything granting unfair advantage (auto-aim/bots, tundra/foliage removal, illegal laser sights, etc.). Check the Fair Play policy before designing features.

## 8. Resolved scope (this mod)
- **Target client:** WoT EU `2.3.0.1` (`mods/2.3.0.1/`).
- **UI:** Gameface (HTML/CSS/JS widget) driven by a Python data model; no Flash.
- **Config UI:** in-game settings via **ModsSettingsAPI** (optional, soft dependency —
  guarded so the mod runs without it). Hard dependency on **OpenWG GameFace**.
- **Distribution:** packaged `.wotmod` (+ Inno Setup installer). Loose `res_mods`
  does NOT load in 2.3 and is used only as a dev hot-reload overlay.

See `CLAUDE.md` and the `.claude/skills/wgmod-*` skills for build/deploy,
architecture, and release specifics.
