# Research: Build-tooling hardening batch

_Submitted: bug hunt (2026-07-05) · Status: open_

## Summary
Five small, independent hardenings in the build/deploy scripts. All latent (nothing is
broken today — the new -OO + minify pipeline itself audited CLEAN: no assert/`__doc__`
reliance in src/, no rjsmin/rcssmin hazards in the current JS/CSS). Each is a cheap guard
against a future footgun. Confidence: high on mechanisms (all verified by direct read);
severity low.

## Findings
1. **No OS-cruft filter in the package copy.** `build/build_wotmod.py:87-104`
   (`_compile_tree`) filters only `.py`/`.pyc`/`__pycache__`; any stray `Thumbs.db`,
   `.DS_Store`, or editor swap file under `src/res/` would ship verbatim inside the
   `.wotmod`. None present today.
2. **Deploy deletes before it builds.** `build/deploy_wotmod.py:114-116` — `_clean()`
   removes the installed package from the WoT `mods/` dir, THEN `build_wotmod.main()`
   runs; a build failure (e.g. missing minifier vendor file) leaves the install
   mod-less until rerun. Build into `dist/` first, copy on success.
3. **clean_dist can sweep a debug package.** `build/clean_dist.py:56` — the pattern
   `^<mod_id>_.+\.wotmod$` matches the debug REPL package's filename too; it's not in
   `_keep_names`, so a debug `.wotmod` that ever lands in `dist/` is deleted by a routine
   clean. (The debug builder normally writes straight into WoT `mods/`, hence latent.)
4. **Minifier import is lazy per-file.** `build/build_wotmod.py:71-84`
   (`_minify_or_copy`) imports `build/vendor/rjsmin.py`/`rcssmin.py` on first use — a
   missing/broken vendor file fails mid-build with `dist/_build/` half-populated. A
   startup preflight import fails fast.
5. **Debug bytecode diverges from release.** `tools/dev/build_debug_wotmod.py:54`
   compiles without `-OO` while the release build strips docstrings/asserts — invisible
   today, but debug-vs-shipped bytecode differ if ever compared. Align (or document why
   not).

## Root cause
Each script grew for the happy path; failure ordering and cross-script consistency were
never revisited after the 88f8433 minify pipeline landed.

## Suggested approach
One small PR-sized batch: add an exclusion set (`Thumbs.db`, `.DS_Store`, `*.swp`,
`*.orig`, `desktop.ini`) to `_compile_tree`'s copy branch; reorder deploy to
build→verify-artifact-exists→clean→copy; add the debug filename to `_keep_names` (or
exclude `_debug` from the pattern); preflight-import both minifiers at build start; pass
`-OO` in the debug builder. Re-run a full build+deploy+wgmods-zip afterwards to confirm
byte-identical artifacts (except the debug .pyc, which shrinks).

## Touch points
- `build/build_wotmod.py:71-84, 87-104`
- `build/deploy_wotmod.py:104-125`
- `build/clean_dist.py:40-60`
- `tools/dev/build_debug_wotmod.py:54`

## Verification
`python build/build_wotmod.py` output unchanged (compare zip listing before/after); drop
a dummy `Thumbs.db` under `src/res/` → not in the package; rename a vendor minifier →
build fails BEFORE `_clean` touches the install and before `dist/_build` is created;
`clean_dist --dry-run` with a debug wotmod in dist/ → kept.

## Open questions
- None; all mechanical. (Skipped as not worth doing, for the record: wgmods readme UTF-8
  BOM — only pre-1903 Notepad misrenders; installer ps1 printing an empty path on a
  no-match success; vendor-glob double-dep bundling — the update instructions already say
  "replace".)
