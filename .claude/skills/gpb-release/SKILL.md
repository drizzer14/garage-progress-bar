---
name: gpb-release
description: Cut a release of the Garage Progress Bar WoT mod — the exact 6 files to bump, the concrete build scripts, artifact filenames, and vendor payloads for THIS mod. Use whenever bumping the version, building the Setup .exe installer, assembling the wgmods.net bundle, or publishing the GitHub release. (For the generic release shape and traps, see the wotmod-release harness skill.)
---

# Releasing the wgmod

Generic shape (canonical version mirrored, annotated tag + `gh release`, installer + zips
with bundled vendor deps, the don't-rename-the-.exe trap): see the **wotmod-release** harness
skill. This skill is this mod's concrete file list and commands. `gh` CLI and Inno Setup are
installed on this machine (paths at the bottom).

## 1. Bump the version in ALL 6 files
`src/meta.xml` is canonical (`<version>`). Mirror the new `X.Y.Z` into:
1. `src/meta.xml` — `<version>`
2. `src/res/scripts/client/gui/mods/mod_wgmod.py` — `MOD_VERSION`
3. `installer/wgmod-setup.iss` — `#define ModVersion` AND `#define ModWotmod`
4. `installer/build_installer.ps1` — `$ModWotmod` path
5. `INSTALL.md` (multiple refs)
6. `installer/README.md`

`README.md` is deliberately NOT in this list — the consumer restructure removed its mod-version
ref by design (it carries only the client + dependency versions), so `check_version.py` neither
scans nor requires one. At release time also bump `dist\INSTALL.txt` (the consumer-zip readme,
step 3).

Then verify: `python build\check_version.py` (either Python) — fails on any reference that
drifted from `src/meta.xml`. It matches five mod-version patterns (packaged filename, Setup
filename, `MOD_VERSION`, `#define ModVersion`, prose `version <v>`), scans `dist\INSTALL.txt`
explicitly, and fails a required file that has LOST its reference. It ALSO checks the 4-part
CLIENT version (canonical: `build_wgmods_zip.CLIENT_VERSION`) across the shipping/instruction
files, failing on drift. It can't see arbitrary prose, so ALSO `grep -rn "<old version>"`.
Changing `<id>` would also change the output filename + the cleanup glob in `deploy_wotmod.py`.

## 2. Commit & tag
Conventional commits, landing directly on `main` (no branch). Fixes as their own `fix(...)`
commits first, then `chore(release): X.Y.Z`. Annotated tag `vX.Y.Z`. Push `main` + tag.
`dist/` is gitignored — binaries are NEVER committed.

## 3. Build the artifacts (into gitignored dist/)
```powershell
python build\clean_dist.py            # tidy dist/ to one release's files; --dry-run to preview
& "C:\Python27\python.exe" build\build_wotmod.py    # -> dist\com.14th_ua.garageprogressbar_X.Y.Z.wotmod
pwsh installer\build_installer.ps1                   # -> dist\GarageProgressBar-Setup-X.Y.Z.exe
```
The installer needs the `.wotmod` already built and BOTH vendor payloads present
(`build_installer.ps1` throws if either is missing):
`installer\vendor\net.openwg.gameface_1.1.6.wotmod` and
`installer\vendor\izeberg.modssettingsapi_1.7.0.wotmod`.

Consumer zip (no committed generator — hand-assemble): bump `dist\INSTALL.txt` version, then
```powershell
Compress-Archive -Path dist\com.14th_ua.garageprogressbar_X.Y.Z.wotmod,dist\INSTALL.txt `
  -DestinationPath dist\Research-Progress-Bar_X.Y.Z.zip          # flat root, 2 files
```

**wgmods.net bundle zip** (uploaded to wgmods.net BY HAND, NOT attached to the GitHub release):
```powershell
python build\build_wgmods_zip.py       # -> dist\GarageProgressBar_X.Y.Z.zip
```
Runs on either Python (only zips already-built files). Needs the `.wotmod` + both
`installer\vendor\*.wotmod`; bundles mod + vendor deps under `mods\2.3.0.1\` plus a bilingual
`readme.txt` (generated from `installer\readme.wgmods.txt`, `{VERSION}` auto-stamped). The
`2.3.0.1` folder is `CLIENT_VERSION` in the generator; bump when the supported client changes.

## 4. Publish the GitHub Release (all 3 assets)
```powershell
gh release create vX.Y.Z --title "Garage Progress Bar vX.Y.Z" --notes-file <body.md> `
  dist\GarageProgressBar-Setup-X.Y.Z.exe `
  dist\com.14th_ua.garageprogressbar_X.Y.Z.wotmod `
  dist\Research-Progress-Bar_X.Y.Z.zip
```
Body: intro + `### What's new in X.Y.Z` + Requirements + Install (recommended, .exe) + Manual
install (.wotmod).

**Do not rename the setup .exe asset.** The installer's self-update builds the download URL
from the tag + the fixed name `GarageProgressBar-Setup-<version>.exe`
(`SetupBaseName`/`OutputBaseFilename` in `wgmod-setup.iss`). Keep the tag `vX.Y.Z` and this
filename, or older installers can't fetch the new build.

## Machine state
- `gh` at `C:\Program Files\GitHub CLI\gh`, authed as 14th_ua.
- `ISCC.exe` at `%LOCALAPPDATA%\Programs\Inno Setup 6\` (Find-ISCC checks there).

For build/deploy/verify mechanics see the **gpb-build-deploy** skill.
