# Garage Progress Bar — Installation Guide

A World of Tanks mod that adds a progress bar to the Garage showing the selected
vehicle's progression at a glance:

- **Tech-tree research** — modules and the next vehicle to unlock.
- **Field Modifications** — the post-progression upgrade ladder.
- **Elite Levels (prestige)** — current grade band and the Tier XI reward track.
- **Tier XI vehicle skill tree** — how many skill-tree upgrades are unlocked out of the total.

It uses the game's own icons and hover tooltips, and refreshes live whenever you
switch vehicles.

---

## Requirements

| Requirement | Detail |
|-------------|--------|
| **Game** | World of Tanks **EU (Wargaming)** client, version **2.3.0.1**. Built and tested against this version. |
| **Dependency** | **OpenWG GameFace** (required). The installer sets this up for you; for a manual install you add it yourself. |
| **Optional** | **ModsSettingsAPI** — adds the mod's options to its in-game Modification list window. The installer adds it if missing; without it the bar simply shows everywhere with no options. |

This build targets the Wargaming EU/global client (version 2.3.0.1).

---

## Install with the installer (recommended)

1. Close World of Tanks completely (exit the Game Center launcher too).
2. Run **`GarageProgressBar-Setup-0.6.1.exe`**.
3. Confirm your World of Tanks folder when the installer shows it — the folder that
   contains `version.xml`. The installer detects it automatically in most cases.
4. If a newer version is available on GitHub, the installer offers to download and
   run the latest installer for you — accept to always get the newest build.
5. The installer adds OpenWG GameFace and ModsSettingsAPI when your client doesn't
   already have them, then installs the mod into `mods\<version>\`.
6. Start the game and go to the Garage. Adjust the bar from the **Modification list**
   window (added by ModsSettingsAPI) if you like.

To remove the mod later, use its entry in Windows **Apps & features**, or re-run the
installer. OpenWG GameFace and ModsSettingsAPI stay in place for other mods that use them.

---

## Manual install

1. Get **OpenWG GameFace** from the official WG mod portal (**wgmods.net**) or the
   OpenWG project's GitLab releases, and install its `.wotmod` into your game's
   `mods\<version>\` folder. If you already run other GameFace mods you likely have it.
   Optionally also install **ModsSettingsAPI** (izeberg) the same way for the in-game
   settings panel — most modpacks (e.g. Aslain's) already include it.
2. Open your World of Tanks folder and the version-matched mods folder inside it:

   ```
   <World of Tanks>\mods\2.3.0.1\
   ```

   The folder name matches your installed client version. After a game update the
   version changes and you move the mod into the new version folder.

3. Copy **`com.14th_ua.garageprogressbar_0.6.1.wotmod`** into that folder.
4. Delete any older version of this mod from the same folder first. **If you used a
   release before the rename, also delete the old `com.drizzer14.wgmod_*.wotmod`** —
   otherwise both load and you get two bars.
5. Fully restart the game client: exit completely and relaunch.

The `mods\2.3.0.1\` folder then holds the OpenWG GameFace `.wotmod` and
`com.14th_ua.garageprogressbar_0.6.1.wotmod`.

---

## Verifying it works

1. Launch the game and go to the **Garage**.
2. Select a vehicle that still has research, field modifications, or elite levels
   remaining.
3. A progress bar appears in the vehicle-parameters area, with the matching header
   icon and a Total-XP readout.
4. Hover the ticks/icons to see tooltips. Switch vehicles and the bar updates.

---

## Troubleshooting

**The bar doesn't show up.**
- Confirm OpenWG GameFace is installed in the same `mods\<version>\` folder.
- Confirm the `.wotmod` is in the folder matching your client version (for example
  `mods\2.3.0.1\`).
- Check that no loose copy of the mod sits under `res_mods\<version>\scripts\client\`,
  which would override the packaged mod. Keep only the `.wotmod` in `mods\<version>\`.
- Fully restart the client after installing.

**No settings appear for the mod.**
- The mod's options need **ModsSettingsAPI** in the same `mods\<version>\` folder
  (the installer adds it if missing). Without it the bar still works — it just shows
  everywhere with no toggles.
- If the bar is hidden and you want it back, open the **Modification list** window
  (added by ModsSettingsAPI), find **Garage Progress Bar**, and uncheck the hide options.

**A game update stopped it from working.**
- Game updates change the version folder. Move the `.wotmod` from the old
  `mods\<old-version>\` into the new `mods\<new-version>\`. A new client version may
  also need a rebuilt mod — check for an updated release.

**Special "7×7" / event hangars.**
- Some special battle-mode hangars don't expose the panel the bar attaches to, so the
  bar won't appear there. It returns in the normal Garage.

---

## Uninstalling

Remove the mod through its Windows **Apps & features** entry, or delete
`com.14th_ua.garageprogressbar_0.6.1.wotmod` from `mods\<version>\`, then restart the client.

---

*Mod by 14th_ua. Built for WoT EU 2.3.0.1.*
