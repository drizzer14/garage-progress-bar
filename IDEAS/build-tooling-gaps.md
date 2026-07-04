# Research: Build/deploy/installer tooling gaps (shadowing + version-check coverage)
_Submitted: full-codebase bug sweep (2026-07-04) · Status: open_

## Summary
Five confirmed dev/release tooling gaps, all inspection-verified. None affect the
shipped mod's runtime; all can burn dev or release time. Grouped because the fixes
are small and adjacent.

## Findings
1. **`deploy_wotmod.py` leaves `.pyc` shadows** — `build/deploy_wotmod.py:63` cleans
   only `mod_wgmod.py`/`mod_wgmod_debug.py`; the byte-compiled `.pyc` siblings
   survive in `res_mods/<v>/scripts/client/gui/mods/` and outrank the packaged
   entry point forever after. The installer knows better — `wgmod-setup.iss`
   explicitly deletes the `.pyc`s (~:549-550).
2. **`deploy_wotmod.py` neither cleans nor warns about the gameface overlay** —
   `_clean` (`:51-71`) never touches
   `res_mods/<v>/gui/gameface/mods/14th_ua/`, the hot-reload overlay planted by
   `sync_gameface.py`, which shadows the packaged JS/CSS. Leaving it is intentional
   for the dev loop, but the script prints only "Restart the WoT client" — a
   detection + warning line ("overlay present, packaged assets shadowed") would
   have prevented the repeatedly-recurring "clean redeploy + overlay removal" chore
   noted across several release handoffs.
3. **`tools/dev/build_debug_wotmod.py` has no Python-2.7 guard** — unlike
   `build_wotmod._check_python()`; run under Py3 it silently emits Py3 bytecode
   and the REPL mod never loads (symptom: connection refused on 2223).
4. **The installer's upgrade cleanup eats the dev debug mod** —
   `installer/wgmod-setup.iss:543` `DelTree('{#ModId}_*.wotmod')` matches
   `com.14th_ua.garageprogressbar_debug.wotmod`; `deploy_wotmod.py:55` deliberately
   uses `_[0-9]*` to avoid exactly this. (`:374` FindFirst uses the same broad
   pattern for install detection — the debug mod alone would read as an install.)
5. **`build/check_version.py` blind spots** — pattern-based only (`:43-48`):
   (a) `dist/` is in `_SKIP_DIRS` (`:37`), so the hand-bumped consumer-zip
   `dist\INSTALL.txt` is permanently unchecked; (b) README.md currently has no
   pattern-matchable version reference, so a prose "v0.4.0" reintroduced there
   passes silently; (c) no required-file list, so a file LOSING its reference also
   passes. Failure shape: ship a 0.5.0 zip whose INSTALL.txt says 0.4.0.

## Root cause
Each is a coverage gap in a guard that exists precisely to prevent that class of
mistake (the shadowing traps and version drift are this repo's two documented
recurring footguns).

## Suggested approach
1. Add the `.pyc` names to the `_clean` loop (same tuple, `+ ".pyc"` variants, or
   glob `mod_wgmod*.py?`).
2. In `deploy_wotmod.main()`, detect
   `res_mods/<v>/gui/gameface/mods/14th_ua/` and print a loud warning (or add a
   `--clean-overlay` flag that removes it).
3. Copy `_check_python()` (or import it from `build_wotmod`) into
   `build_debug_wotmod.py`.
4. Change the `.iss` globs (`:374`, `:543`) to `{#ModId}_[0-9]*.wotmod`-equivalent
   (Inno's DelTree accepts wildcards but not char classes — may need a FindFirst
   loop that skips names containing `_debug`).
5. `check_version.py`: scan `dist/INSTALL.txt` explicitly when present, and add a
   small required-references list (file → expected pattern count ≥ 1) for the 7
   release files.

## Touch points
- `build/deploy_wotmod.py:51-71`
- `tools/dev/build_debug_wotmod.py`
- `installer/wgmod-setup.iss:374, 543`
- `build/check_version.py:36-48`

## Verification
1/2: plant a fake `.pyc` + overlay, run deploy, confirm clean/warn. 3: run under
Py3 → must abort. 4: place a `_debug.wotmod`, run the installer's uninstall/upgrade
logic in a sandbox (or code-review the FindFirst loop). 5: seed a stale
`dist\INSTALL.txt` → check must fail.

## Open questions
- Overlay handling preference: warn-only (keeps the dev loop) vs `--clean-overlay`
  flag vs always-clean (would break mid-development hot-reload) — recommend warn +
  flag.
