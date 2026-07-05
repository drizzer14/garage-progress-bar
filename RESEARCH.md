# Research Notes — Garage Progress Bar

_Game baseline: WoT 2.x (Gameface UI era)._

Generic World of Tanks modding background — the stack (BigWorld / Python 2.7.18 /
Gameface / Wulf / Scaleform / XML), the `res/` · `res_mods/` · `mods/` file structure,
the dev-vs-`.wotmod` workflows, how mods load and monkey-patch the game, the modern
dependency stack (OpenWG / ModsList / ModsSettingsAPI), the key community resources
(`modding.wot-tools.dev`, `wgmods.dev`, `wgmods.net`), and the current Fair Play rules —
now lives in the **wotmod harness** plugin, skill **`wotmod-basics`** (reusable across
mods, kept current there). This file keeps only what's specific to this mod.

## Resolved scope (this mod)
- **Target client:** WoT EU `2.3.0.1` (`mods/2.3.0.1/`).
- **UI:** Gameface (HTML/CSS/JS widget) driven by a Python data model; no Flash.
- **Config UI:** in-game settings via **ModsSettingsAPI** (optional, soft dependency —
  guarded so the mod runs without it). Hard dependency on **OpenWG GameFace**.
- **Distribution:** packaged `.wotmod` (+ Inno Setup installer). Loose `res_mods` does
  NOT load in 2.3 and is used only as a dev hot-reload overlay.

See `CLAUDE.md` and the `.claude/skills/wgmod-*` skills for this mod's build/deploy,
architecture, widget, and release specifics.
