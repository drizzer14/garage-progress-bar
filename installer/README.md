# Windows installer

A one-double-click `setup.exe` (built with [Inno Setup](https://jrsoftware.org/isinfo.php)) that
installs the Garage Progress Bar mod and its dependencies — **OpenWG GameFace**
(required) and **ModsSettingsAPI** (for the in-game settings panel).

## What the installer does for end users

1. **Finds World of Tanks** — checks the Windows registry and common install
   locations, then shows the detected folder for the user to confirm or change.
   The chosen folder must contain `version.xml` (the installer validates this).
2. **Targets the right version** — reads the client version from `version.xml`
   (e.g. `2.3.1.0`) and installs into `mods\<version>\`.
3. **Installs OpenWG only if missing** — recursively checks `mods\<version>\` for
   `net.openwg.gameface*.wotmod` (so it won't duplicate a copy the user already has
   via ModsList, Aslain, etc.). If absent, it copies the bundled
   `net.openwg.gameface_1.1.6.wotmod` in.
4. **Installs ModsSettingsAPI only if missing** — recursively checks for any
   `*modssettingsapi*.wotmod` (matches the izeberg or Aslain builds many packs
   already ship). If absent, it copies the bundled
   `izeberg.modssettingsapi_1.7.0.wotmod` in. This powers the in-game settings panel;
   the bar still works without it (it just falls back to its default visibility).
5. **Cleans + installs the mod** — removes older `com.14th_ua.garageprogressbar_*.wotmod`
   builds (and stale loose `res_mods\<version>\` leftovers that would shadow the
   package), then installs the current `.wotmod`.
6. **Reminds** the user to fully restart the client.

The installer refuses to run while `WorldOfTanks.exe` is open (file locks). On
uninstall it removes the mod but **leaves OpenWG and ModsSettingsAPI in place**
(other mods may use them).

## Update check

After you confirm the WoT folder, the installer makes one best-effort call to the
GitHub releases Atom feed
(`https://github.com/drizzer14/garage-research-progress/releases.atom`) and compares
the latest published version against the higher of *this installer's bundled version*
and *any already-installed mod build* under `mods\<version>\`. If GitHub has a newer
release, it offers to **download and launch that installer** for you, then closes
itself so you continue with the current version.

It's entirely best-effort: no internet, a changed feed, or a failed download all fall
back silently to installing the bundled version. Pass **`/SKIPUPDATECHECK`** on the
command line to skip the check (useful offline or for testing).

The self-update relies on the release-asset filename convention
`GarageProgressBar-Setup-<version>.exe` (driven by `SetupBaseName` +
`OutputBaseFilename` in `wgmod-setup.iss`) — **don't rename the setup asset** without
updating that define, or the updater won't find the new build.

## Bundled dependencies

`vendor/net.openwg.gameface_1.1.6.wotmod` is the official OpenWG GameFace build
(from <https://gitlab.com/openwg/wot.gameface>), bundled because its GitLab release
asset is not directly downloadable by an automated client (login/Cloudflare gated).
OpenWG is open source and is routinely redistributed in WoT mod packs.

`vendor/izeberg.modssettingsapi_1.7.0.wotmod` is the ModsSettingsAPI library mod
(izeberg), the de-facto standard in-game settings framework, also bundled in modpacks
like Aslain's. It is redistributed the same way.

To update either: download the newer `.wotmod`, replace the file in `vendor/`, and
bump the matching `OpenWgWotmod` / `MsaWotmod` define in `wgmod-setup.iss`
(and the `$Msa` path in `build_installer.ps1` if its filename changed).

## Building the installer

```powershell
# 1. Build the mod package (Python 2.7 — bytecode is version-locked):
& "C:\Python27\python.exe" build\build_wotmod.py        # -> dist\com.14th_ua.garageprogressbar_1.1.0.wotmod

# 2. Install Inno Setup once (provides ISCC.exe):
winget install -e --id JRSoftware.InnoSetup

# 3. Compile:
pwsh installer\build_installer.ps1                      # -> dist\GarageProgressBar-Setup-1.1.0.exe
```

`build_installer.ps1` locates `ISCC.exe`, verifies the mod package and bundled
dependency exist, and runs the compiler. The `.iss` `OutputDir` is `..\dist`.
