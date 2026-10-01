# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

World of Tanks **EU 2.4.0.2** Garage mod (`com.14th_ua.garageprogressbar`) — a progress bar
showing the selected vehicle's tech-tree research, Field Modifications, tier-XI
skill-tree upgrades, and Elite Levels (prestige). Hard dependency: **OpenWG
GameFace**. Player-facing docs: `README.md`, `INSTALL.md`. Generic WoT-modding
background lives in the **wotmod harness** plugin (skill `wotmod:basics`); this repo's
`RESEARCH.md` keeps only the resolved scope for this mod.

## The one rule that bites everywhere

The game runs compiled `.pyc`, and **bytecode is version-locked**: package with
**Python 2.7.18** (`C:\Python27\python.exe`) — Python 3 bytecode will NOT load.
Tests and dev tools run on **Python 3.13**. Builds are plain Python scripts (no npm).
CI (`.github/workflows/ci.yml`) runs on push/PR: `check_version.py`, `ruff check .`,
and `pytest -q` on Python 3.13 — it does NOT build the `.wotmod` (Py 2.7 is unavailable
on runners), so a green CI does not prove the package builds.

## Never weaken a check

Fix the code when pytest, `ruff`, `py_compile`, or a build check fails — never loosen the
check. No `|| true`, no deleted rule, no skipped test. Every suppression carries a concrete
reason on the same line (`# noqa: F401 -- re-exported for the bridge`).

## Skill drift rule

After every gated iteration, run the retrospect → scribe → commit drift pass (see
`orchestrator` § Skill drift rule).

## Task-scoped skills

Situational guidance lives in the installed **`wotmod`** harness plugin's skills (loaded on
demand by their `description`; dev dependency, installed via the local `wotmod-harness`
marketplace) — do not duplicate it here.

**This mod's specifics — the in-repo `gpb-*` skills** (each references its `wotmod:*`
counterpart for the shared pattern):
- **gpb-build-deploy** — this mod's exact build/deploy/test/hot-reload commands + paths.
- **gpb-release** — the exact 6 files to bump, artifact names, vendor payloads.
- **gpb-architecture** — the `wgmod_research` tree, the seven bar modes, resolvers, done-marker reconcile (+ `references/game-api.md` usage map).
- **gpb-widget** — the `WGModResearch` widget: DOM, icon URLs, render branches, hover/click.
- **gpb-debug-repl** — this mod's debug REPL package + probe snippets.
- **gpb-planner** — the `TASKS.md`/`TASKS/` backlog workflow + cross-session sync hooks.
