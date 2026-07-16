# README screenshots

Per-language captures, one folder each — the root `README.md` embeds the English
section from `en/` and the Ukrainian section from `ua/`. Use these **exact
filenames** in both folders.

| Filename | State to capture | Where it's used |
|----------|------------------|-----------------|
| `research.png` | A **partially-researched** vehicle — research ticks + Total-XP readout, with a tooltip visible. | Hero image (top of the language section). |
| `field-mods.png` | The bar in **Field Modifications** mode, with a tooltip. | "Every progression type". |
| `elite.png` | An **Elite Levels (prestige)** vehicle — grade-band progression, with a tooltip. | "Every progression type". |
| `elite-rewards.png` | A tier-XI vehicle showing the **exclusive-rewards** milestone roadmap, with a tooltip. | "Every progression type". |
| `skill-tree.png` | A **tier-XI** vehicle — skill-tree upgrade progress, with a tooltip. | "Every progression type". |
| `potential-tier-xi.png` | A fully-researched, field-mods-done **tier-X** tank with no real tier XI, with **"Show potential Tier XI"** enabled — the speculative Tier XI bar (banked XP vs. the fixed unlock cost) above Elite Levels, with the milestone tooltip visible. | "Every progression type". |

Capture in-game in the Garage (WoT EU 2.3.1.0) with the client language set to match
the folder (`en/` = English UI, `ua/` = Ukrainian UI). `research.png` is the hero, so
make it the strongest shot.

Cropping recipe (matches the current set): captured at 3840×2160, cropped bar-centered
to exclude the right-hand battle-pass panel and normalized to 1260px wide, e.g.

```sh
magick shot.png -crop 1250x754+1295+203  +repage -resize 1260x en/research.png   # short tooltips
magick shot.png -crop 1250x1067+1295+203 +repage -resize 1260x en/field-mods.png # tall tooltip
```
