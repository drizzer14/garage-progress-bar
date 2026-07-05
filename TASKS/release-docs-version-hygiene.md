# Research: Release/docs version-reference hygiene

_Submitted: bug hunt (2026-07-05) · Status: open_

## Summary
Three documentation/process drifts around versioning, found while auditing the release
tooling. None affects the shipped mod; all three make the NEXT release or client-version
bump error-prone. Confidence: high (each verified by direct read).

## Findings
1. **The release skill contradicts itself about README.md.**
   `.claude/skills/wgmod-release/SKILL.md` step 1 lists `README.md` as bump-file #5 of
   "ALL 7 files", but the same section's endnote says "`README.md` deliberately carries
   no version ref", and `build/check_version.py` doesn't scan it. Grep confirms README.md
   contains no mod-version string (only client `2.3.0.1` and dep versions). The file list
   is wrong — it's 6 files + INSTALL.md's multiple refs, or the numbering needs redoing.
   A release agent following step 1 literally will hunt for a nonexistent ref.
2. **The supported CLIENT version `2.3.0.1` is duplicated with zero check coverage.**
   Hardcoded in `build/build_wgmods_zip.py:41` (`CLIENT_VERSION`, drives the zip's
   `mods/<ver>/` folder), `installer/readme.wgmods.txt` (multiple), `README.md`,
   `INSTALL.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `tools/dev/README.md` — and
   `check_version.py` intentionally checks only the MOD version. On the next client
   patch these can silently disagree (e.g. a wgmods bundle whose folder no longer
   matches its own readme's instructions).
3. **CONTRIBUTING.md's repo-layout listing is stale.** It omits everything the last two
   releases added: `build/check_version.py`, `build/clean_dist.py`,
   `build/build_wgmods_zip.py`, `build/vendor/` (minify pipeline), and under
   `tools/dev/`: `sync_gameface.py`, `build_debug_wotmod.py`.

## Root cause
Version knowledge lives in prose across many files; check_version.py covers the mod
version well but was never extended to the client version, and docs/skill lists weren't
updated as tooling grew.

## Suggested approach
- Fix the wgmod-release SKILL.md file list (drop README.md or renumber; keep the
  no-version-ref note — verify against the tree at fix time).
- Teach `check_version.py` a second check: read a canonical client version (either
  `build_wgmods_zip.CLIENT_VERSION` or a new single-source constant) and verify the
  known files agree; fail on drift like the mod-version checks do. Keep the required-ref
  semantics (a file that LOSES its ref fails).
- Refresh CONTRIBUTING.md's layout section.

## Touch points
- `.claude/skills/wgmod-release/SKILL.md` (step-1 list)
- `build/check_version.py`, `build/build_wgmods_zip.py:41`
- `CONTRIBUTING.md`; the client-version prose files listed above.

## Verification
`python build/check_version.py` passes on the current tree; temporarily editing one
client-version ref makes it fail; a dry release-skill walkthrough no longer stumbles on
README.md.

## Open questions
- Where should the canonical client version live? (Recommend: keep it in
  build_wgmods_zip.py and have check_version import/parse it — one source, no new file.)
