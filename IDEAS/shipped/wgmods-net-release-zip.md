# Research: wgmods.net release .zip (mod + dependencies + bilingual readme)

_Submitted: "Mod was approved on wgmods.net, need to update release process. GitHub stays
as-is, but alongside it I need a .zip with the mod file + any required dependencies +
short readme.txt with install instructions in English and Ukrainian" · Status: open_

## Summary
Add ONE new deliverable to the release process: a wgmods.net-oriented `.zip` bundling
the mod `.wotmod`, its required dependency payload(s), and a short bilingual (EN + UA)
`readme.txt`. The GitHub release is unchanged — it keeps its three assets (Setup `.exe`,
bare `.wotmod`, and the existing GitHub consumer zip `Research-Progress-Bar_X.Y.Z.zip`).
This is a **process/packaging** change (the `wgmod-release` skill + a build step), not a
code change to the mod itself.

## What exists today
- Release process lives in the **`wgmod-release`** skill (`.claude/skills/wgmod-release/
  SKILL.md`). §3 already hand-assembles a consumer zip via `Compress-Archive` (flat root:
  the `.wotmod` + `dist\INSTALL.txt`), with **no committed generator**.
- The current consumer readme is `dist\INSTALL.txt` — English-only, ASCII-box style,
  version strings baked in. `dist/` is gitignored, so that text is **not version-
  controlled** (hand-maintained each release). Good model for tone/structure — see it for
  the WHAT/REQUIREMENTS/INSTALL/VERIFY/TROUBLESHOOTING/UNINSTALL layout.
- Dependency payloads already vendored for the installer:
  - `installer\vendor\net.openwg.gameface_1.1.6.wotmod` — **REQUIRED** (bar won't appear
    without it).
  - `installer\vendor\izeberg.modssettingsapi_1.7.0.wotmod` — **optional** (adds the
    in-game settings window; bar works without it).
- `INSTALL.md` (repo root) is the long-form English install guide — source material to
  condense for the readme.

## Bundling decision (settled)
The mod was **approved on wgmods.net with BOTH dependencies shipped inside the archive**
alongside the mod. So the zip bundles all three payloads — no linking-out, no licensing
blocker. Contents:
- `com.14th_ua.garageprogressbar_X.Y.Z.wotmod` (the mod)
- `net.openwg.gameface_1.1.6.wotmod` (required dep)
- `izeberg.modssettingsapi_1.7.0.wotmod` (optional dep, bundled anyway)
- `readme.txt` (EN + UA)

All three `.wotmod`s already live under `installer\vendor\` (GameFace + MSA) and `dist\`
(the mod) at release time — no new sourcing.

## Suggested approach
1. **Assemble the four files above** into the staging tree.
2. **Zip layout** — recommend a `mods\2.3.0.1\`-shaped folder inside the zip so the user
   extracts straight into `<World of Tanks>\` (drag-and-drop, no guessing the version
   folder), with `readme.txt` at the zip root. Confirm against wgmods.net's expected
   package shape.
3. **Author `readme.txt`** — short, bilingual. English block then a `====` divider then a
   Ukrainian block (or side-by-side sections). Cover: what it does (1–2 lines),
   requirement (GameFace, bundled here), the 2-step install (extract into WoT folder /
   drop the `.wotmod`s into `mods\<version>\`, restart), and a one-line uninstall.
   Condense from `dist\INSTALL.txt` + `INSTALL.md`. Keep the UA copy-style rules in mind
   (player-facing, no filler).
4. **Commit a template** so the bilingual readme isn't lost like `INSTALL.txt` is:
   put `installer\readme.wgmods.txt` (or a small generator) under version control with a
   `{VERSION}` placeholder; the release step stamps the version into `dist\readme.txt`.
5. **Add the build step to `wgmod-release` §3**, e.g.:
   ```powershell
   Compress-Archive -Path <staged tree> -DestinationPath dist\GarageProgressBar-wgmods_X.Y.Z.zip
   ```
   Name it distinctly from the GitHub consumer zip (`Research-Progress-Bar_X.Y.Z.zip`) to
   avoid confusion. This zip is **uploaded to wgmods.net manually**, NOT attached to the
   GitHub release (unless you also want it there).
6. **Version-bump wiring**: `readme.txt`/its template carries version + dep-version
   strings, so add it to the skill's "bump in ALL files" list. Consider whether
   `check_version.py` should also assert the readme's mod-version line.

## Touch points
- Edit: `.claude/skills/wgmod-release/SKILL.md` (new §3 sub-step + mention the manual
  wgmods.net upload; add the readme to the version-bump list).
- New (committed): `installer\readme.wgmods.txt` template (EN + UA) — or a tiny
  `build\build_wgmods_zip.py` that stamps version + assembles the zip (nicer than
  hand-assembly, mirrors `build_wotmod.py`).
- Reuses: `installer\vendor\*.wotmod`, `dist\INSTALL.txt` (tone), `INSTALL.md` (content).
- Optional: `build\check_version.py` (assert the readme version line).

## Open questions
- **Zip internal layout** — `mods\<version>\`-shaped (extract-into-WoT) vs. flat files.
  Match whatever wgmods.net downloaders expect / what its uploader UI wants.
- **UA readme** — machine-condense from existing English or have the user (native UA)
  supply/verify the Ukrainian copy. Recommend the latter for the player-facing text.
- Should this zip ALSO be attached to the GitHub release, or wgmods.net-only? (User said
  "alongside" GitHub — read as a separate channel, GitHub unchanged.)

## Verification
- After building: unzip into a scratch dir and confirm the tree matches the chosen layout,
  the `.wotmod` filename carries the new version, and any bundled dep versions match
  `installer\vendor\`. Open `readme.txt` and eyeball both language blocks + version
  strings. Do a real extract-into-a-clean-WoT test if using the folder-shaped layout.
- No pytest impact (packaging only) unless `check_version.py` gains a readme assertion —
  then run `python build\check_version.py`.
