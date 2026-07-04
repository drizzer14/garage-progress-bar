# Ideas Backlog

Recorded ideas for the mod. Entries are deleted once implemented. Each entry links
to a deeper research note under `IDEAS/` for the implementer.

## Open

### wgmods.net release .zip (mod + dependencies + bilingual readme)
Mod is approved on wgmods.net. Add a new release deliverable alongside the unchanged
GitHub release: a `.zip` bundling the mod `.wotmod` + required dependency payload(s)
(OpenWG GameFace + ModsSettingsAPI — both already vendored under `installer/vendor/`;
approved on wgmods.net bundled in the archive) + a short `readme.txt` with install
instructions in **English and Ukrainian**. Process/packaging change only (update the
`wgmod-release` skill §3 + commit a bilingual readme template).
→ Research: IDEAS/wgmods-net-release-zip.md

### Dev/release tooling gaps (shadowing + version-check coverage)
Five confirmed small gaps: deploy leaves .pyc shadows and never warns about the
gameface overlay; build_debug_wotmod has no Py2.7 guard; the installer's cleanup glob
eats the _debug.wotmod; check_version.py can't see dist/INSTALL.txt or prose refs.
→ Research: IDEAS/build-tooling-gaps.md

### Post-refactor dead-code & stale-comment sweep (cleanup batch)
Confirmed-dead wire fields (eliteMaxLevel/eliteSub), dead CSS rules, vestigial
classes, and half a dozen false comments/docstrings left behind by shipped features
and the refactor. Zero runtime impact; batch-fix to remove drift traps.
→ Research: IDEAS/post-refactor-dead-code-sweep.md
