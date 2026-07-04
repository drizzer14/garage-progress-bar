# Research: Screenshot the potential-Tier-XI feature (EN + UA) and add to README
_Submitted: "make a reminder to screenshot potential tier xi feature in both ua and en clients + update the readme with them" · Status: open_

## Summary
The opt-in `POTENTIAL_TIER_XI` bar mode (shipped v0.6.0, [[potential-tier-xi-mode-handoff]])
has no screenshot in the README. Capture it in both the English and Ukrainian
clients and add it to the "Every progression type" gallery, matching the existing
per-language screenshot convention.

## Findings
- The README gallery lives in `README.md`: EN "Every progression type" section at
  lines ~23–39, UA mirror at ~118–132. Each progression type is a bold caption line
  + an `![alt](assets/img/<lang>/<name>.png)` embed. The hero shot is `research.png`
  (README.md:10 EN / :102 UA).
- Screenshot filenames are a fixed contract documented in `assets/img/README.md`
  (a table of `research/field-mods/elite/elite-rewards/skill-tree.png`, used in BOTH
  `en/` and `ua/`). There is **no** entry for potential-Tier-XI yet — a new
  `potential-tier-xi.png` row must be added there too.
- Crop recipe (from `assets/img/README.md`): captured 3840×2160, bar-centered crop
  excluding the right battle-pass panel, resized to 1260px wide. Two variants shown:
  `...+1295+203` at 1250×754 for short tooltips, 1250×1067 for a tall tooltip.
- The feature is **opt-in, default OFF** (setting "Show potential Tier XI",
  `settingsVersion` 3). To make the bar render this mode you must enable that toggle
  in the ModsSettingsAPI "Modification list" window, then select a **tier-X tank with
  NO real tier XI** (not a skill-tree vehicle) that is **fully researched + field mods
  done** — only then does the speculative bar (banked XP → fixed 325000 tier-XI price)
  appear, sitting above Elite Levels. See [[potential-tier-xi-mode-handoff]] and
  [[tier-xi-fixed-unlock-price]].
- The mode shows a Research header glyph, a "Tier XI" header, and a single
  non-clickable milestone tick with an "undefined tank" glyph + the localized vehicle
  class name as the tooltip title — so the tooltip text differs EN vs UA, which is
  exactly why a per-language capture is worth it.

## Suggested approach
1. Set the client language to English; enable "Show potential Tier XI"; pick a
   qualifying fully-done tier-X tank; hover the milestone tick to show the tooltip;
   capture and crop to `assets/img/en/potential-tier-xi.png` per the recipe.
2. Repeat with the Ukrainian client → `assets/img/ua/potential-tier-xi.png`.
3. Add a `potential-tier-xi.png` row to the `assets/img/README.md` table (state to
   capture + where used).
4. Add the caption + embed to the EN and UA "Every progression type" sections in
   `README.md`, in the same style as the neighbouring entries (place near the other
   Tier XI shots, e.g. after `skill-tree.png`). Follow the README copy rules in
   [[readme-copy-style-and-facts]] ("Tier XI", no hyphen; no filler/puns).

## Touch points
- `assets/img/en/potential-tier-xi.png`, `assets/img/ua/potential-tier-xi.png` (new)
- `assets/img/README.md` (new table row)
- `README.md` (EN gallery ~23–39, UA gallery ~118–132)

## Verification
Visual: the two new images render in the README (GitHub preview) under both language
sections, cropped consistently with the existing set. No code/tests involved.

## Open questions
- Which qualifying tier-X tank to feature (needs one that is fully researched + field
  mods done in the live account so the mode actually resolves).
- Whether to also mention the opt-in nature in the caption (it's off by default).
