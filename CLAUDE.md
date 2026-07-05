# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

World of Tanks **EU 2.3.0.1** Garage mod (`com.14th_ua.garageprogressbar`) — a progress bar
showing the selected vehicle's tech-tree research, Field Modifications, tier-XI
skill-tree upgrades, and Elite Levels (prestige). Hard dependency: **OpenWG
GameFace**. Player-facing docs: `README.md`, `INSTALL.md`. Generic WoT-modding
background lives in the **wotmod harness** plugin (skill `wotmod-basics`); this repo's
`RESEARCH.md` keeps only the resolved scope for this mod.

## The one rule that bites everywhere

The game runs compiled `.pyc`, and **bytecode is version-locked**: package with
**Python 2.7.18** (`C:\Python27\python.exe`) — Python 3 bytecode will NOT load.
Tests and dev tools run on **Python 3.13**. There is no npm/linter/CI; builds are
plain Python scripts.

## Task-scoped skills

Detailed, situational guidance lives in skills (loaded on demand to keep context
tight) — do not duplicate it here. Guidance is split in two layers:

**Generic WoT-modding — the installed `wotmod` harness plugin** (reusable across mods;
dev dependency, installed via the local `wotmod-harness` marketplace):
`wotmod-basics` (stack, file structure, load model, Fair Play, resources) ·
`wotmod-architecture` (engine-free domain/adapter/bridge discipline + `references/game-api.md`) ·
`wotmod-build-deploy` · `wotmod-debug-repl` · `wotmod-gameface-widget` · `wotmod-release` ·
`wotmod-planner`.

**This mod's specifics — the in-repo `wgmod-*` skills** (each references its `wotmod-*`
counterpart for the shared pattern):
- **wgmod-build-deploy** — this mod's exact build/deploy/test/hot-reload commands + paths.
- **wgmod-release** — the exact 7 files to bump, artifact names, vendor payloads.
- **wgmod-architecture** — the `wgmod_research` tree, the six modes, resolvers, done-marker reconcile (+ `references/game-api.md` usage map).
- **wgmod-widget** — the `WGModResearch` widget: DOM, icon URLs, render branches, hover/click.
- **wgmod-debug-repl** — this mod's debug REPL package + probe snippets.
- **wgmod-planner** — the `TASKS.md`/`TASKS/` backlog workflow + cross-session sync hooks.
