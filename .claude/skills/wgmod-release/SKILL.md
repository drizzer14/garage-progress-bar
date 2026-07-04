---
name: wgmod-release
description: Cut a release of the Garage Progress Bar WoT mod — bump the version across all 7 files, commit and tag, build the .wotmod + Windows installer + consumer zip, and publish the GitHub release. Use whenever the user wants to bump the version, ship/release/publish a new version, build the Setup .exe installer, or create a GitHub release for this mod.
---

# Releasing the wgmod

Pattern established by the 0.1.1 / 0.1.2 releases. `gh` CLI and Inno Setup are
installed on this machine (see paths at the bottom).

## 1. Bump the version in ALL 7 files
`src/meta.xml` is canonical (`<version>`). Mirror the new `X.Y.Z` into:
1. `src/meta.xml` — `<version>`
2. `src/res/scripts/client/gui/mods/mod_wgmod.py` — `MOD_VERSION`
3. `installer/wgmod-setup.iss` — `#define ModVersion` AND `#define ModWotmod`
4. `installer/build_installer.ps1` — `$ModWotmod` path
5. `README.md`
6. `INSTALL.md` (multiple refs)
7. `installer/README.md`

Then verify: `python build\check_version.py` (either Python) — fails on any
reference that drifted from `src/meta.xml`. It matches five patterns (packaged
filename, Setup filename, `MOD_VERSION`, `#define ModVersion`, and prose `version
<v>`), scans `dist\INSTALL.txt` explicitly (built the consumer zip yet? bump it
first), and fails a required file that has LOST its reference. It still can't see
arbitrary prose, so ALSO `grep -rn "<old version>"` to catch bare refs (note:
`README.md` deliberately carries no version ref). Changing `<id>` would also change
the output filename + the cleanup glob in `deploy_wotmod.py`.

## 2. Commit & tag
Conventional commits, landing directly on `main` (no branch). Land fixes as their own
`fix(...)` commits first, then the release commit `chore(release): X.Y.Z`. Create an
**annotated** tag `vX.Y.Z`. Push `main` + the tag. `dist/` is gitignored — binaries
are NEVER committed.

## 3. Build the artifacts (into gitignored dist/)
```powershell
& "C:\Python27\python.exe" build\build_wotmod.py        # -> dist\com.14th_ua.garageprogressbar_X.Y.Z.wotmod
pwsh installer\build_installer.ps1                       # -> dist\GarageProgressBar-Setup-X.Y.Z.exe
```
The installer needs the `.wotmod` already built and BOTH vendor payloads present
(`build_installer.ps1` throws if either is missing):
`installer\vendor\net.openwg.gameface_1.1.6.wotmod` and
`installer\vendor\izeberg.modssettingsapi_1.7.0.wotmod`.

Consumer zip has NO committed generator — hand-assemble: bump version strings in
`dist\INSTALL.txt`, then
```powershell
Compress-Archive -Path dist\com.14th_ua.garageprogressbar_X.Y.Z.wotmod,dist\INSTALL.txt `
  -DestinationPath dist\Research-Progress-Bar_X.Y.Z.zip          # flat root, 2 files
```

**wgmods.net bundle zip** (the extra deliverable, uploaded to wgmods.net BY HAND):
```powershell
python build\build_wgmods_zip.py       # -> dist\GarageProgressBar-wgmods_X.Y.Z.zip
```
Runs on either Python — it only zips already-built files (no bytecode). It needs
the `.wotmod` built (step above) and both `installer\vendor\*.wotmod` deps present;
it bundles the mod + every vendor `.wotmod` under `mods\2.3.0.1\` plus a bilingual
`readme.txt` at the zip root, so the player extracts straight into `<WoT>\`. The
readme is generated from the committed `installer\readme.wgmods.txt` template
(`{VERSION}` auto-stamped, so it can't drift — nothing to bump). The `2.3.0.1`
folder is `CLIENT_VERSION` in the generator; bump it when the supported client
changes. This zip is **uploaded to wgmods.net manually** and is **NOT** attached
to the GitHub release (GitHub keeps its 3 assets — see §4).

## 4. Publish the GitHub Release (every version gets a full release, not just a tag)
All 3 assets:
```powershell
gh release create vX.Y.Z --title "Garage Progress Bar vX.Y.Z" --notes-file <body.md> `
  dist\GarageProgressBar-Setup-X.Y.Z.exe `
  dist\com.14th_ua.garageprogressbar_X.Y.Z.wotmod `
  dist\Research-Progress-Bar_X.Y.Z.zip
```
Body: intro blurb + `### What's new in X.Y.Z` + Requirements + Install (recommended,
.exe) + Manual install (.wotmod).

**Do not rename the setup .exe asset.** The installer's self-update check builds the
download URL from the tag + the fixed name `GarageProgressBar-Setup-<version>.exe`
(`SetupBaseName`/`OutputBaseFilename` in `wgmod-setup.iss`). Keep the tag `vX.Y.Z` and
this asset filename convention, or older installers can't fetch the new build.

## Machine state
- `gh` at `C:\Program Files\GitHub CLI\gh`, authed as 14th_ua.
- `ISCC.exe` at `%LOCALAPPDATA%\Programs\Inno Setup 6\` (Find-ISCC checks there).

For building/deploying/verifying mechanics see the **wgmod-build-deploy** skill.
