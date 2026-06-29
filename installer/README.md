# Windows installer

A one-double-click `setup.exe` (built with [Inno Setup](https://jrsoftware.org/isinfo.php)) that
installs the Research Progress Bar mod and its **OpenWG GameFace** dependency.

## What the installer does for end users

1. **Finds World of Tanks** — checks the Windows registry and common install
   locations, then shows the detected folder for the user to confirm or change.
   The chosen folder must contain `version.xml` (the installer validates this).
2. **Targets the right version** — reads the client version from `version.xml`
   (e.g. `2.3.0.1`) and installs into `mods\<version>\`.
3. **Installs OpenWG only if missing** — recursively checks `mods\<version>\` for
   `net.openwg.gameface*.wotmod` (so it won't duplicate a copy the user already has
   via ModsList, Aslain, etc.). If absent, it copies the bundled
   `net.openwg.gameface_1.1.6.wotmod` in.
4. **Cleans + installs the mod** — removes older `com.drizzer14.wgmod_*.wotmod`
   builds (and stale loose `res_mods\<version>\` leftovers that would shadow the
   package), then installs the current `.wotmod`.
5. **Reminds** the user to fully restart the client.

The installer refuses to run while `WorldOfTanks.exe` is open (file locks). On
uninstall it removes the mod but **leaves OpenWG in place** (other mods may use it).

## Bundled dependency

`vendor/net.openwg.gameface_1.1.6.wotmod` is the official OpenWG GameFace build
(from <https://gitlab.com/openwg/wot.gameface>), bundled because its GitLab release
asset is not directly downloadable by an automated client (login/Cloudflare gated).
OpenWG is open source and is routinely redistributed in WoT mod packs.

To update it: download the newer `.wotmod` from the OpenWG releases page, replace the
file in `vendor/`, and bump the `OpenWgWotmod` define in `wgmod-setup.iss`.

## Building the installer

```powershell
# 1. Build the mod package (Python 2.7 — bytecode is version-locked):
& "C:\Python27\python.exe" build\build_wotmod.py        # -> dist\com.drizzer14.wgmod_0.1.1.wotmod

# 2. Install Inno Setup once (provides ISCC.exe):
winget install -e --id JRSoftware.InnoSetup

# 3. Compile:
pwsh installer\build_installer.ps1                      # -> dist\ResearchProgressBar-Setup-0.1.1.exe
```

`build_installer.ps1` locates `ISCC.exe`, verifies the mod package and bundled
dependency exist, and runs the compiler. The `.iss` `OutputDir` is `..\dist`.
