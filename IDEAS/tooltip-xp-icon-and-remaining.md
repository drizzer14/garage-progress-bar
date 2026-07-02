# Research: Tooltip "N/M XP" — swap "XP" for the total-XP icon + show XP remaining

_Submitted: "In tooltips where N/M XP is shown: replace XP with total XP icon, show how much XP left (and without free XP too)" · Status: open_

## Summary
The cost footer in the ticks/chips/elite tooltips currently reads `have / need XP`
as plain text. Two changes wanted:
1. Replace the literal `" XP"` with the game's **total-XP icon** (the freeXP+vehXP
   glyph already used in the header readout).
2. Also surface **how much XP is left** to reach the target — and additionally a
   **"without free XP"** variant (i.e. remaining if only the vehicle's own XP
   counted, ignoring the global free-XP pool).

## Findings
The whole "N/M XP" string comes from one JS helper — everything below is in
`src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js` unless noted.

- **`xpFracHtml(have, need)` — lines 238-244** is the single source of the footer:
  ```js
  function xpFracHtml(have, need) {
      need = need | 0;
      if (need <= 0) return "";
      have = have | 0;   // shown as-is, NOT capped to need (surplus XP visible)
      const cls = have >= need ? "wg-tip-xp" : "wg-tip-xp wg-tip-short";
      return '<div class="' + cls + '">' + fmtXp(have) + " / " + fmtXp(need) + " XP</div>";
  }
  ```
  Line **243** emits the literal `" XP"` and the `have / need` formatting. This is
  the one function to edit for both requests. `fmtXp(n)` (lines 206-209) does
  thousand-separator formatting.

- Called from **three** tooltip builders, each passing a different `have`/`need`:
  - `tooltipHtml(t, spendableXp)` **line 353** — tech-tree / field-mod ticks;
    `have = spendableXp`, `need = t.position` (cumulative bar position, not
    `t.xpRequired`).
  - `renderNextAvailable(...)` **line 526** — Tier-XI upgrade chips;
    `have = spendableXp`, `need = u.xpRequired` (per-node cost, line 502).
  - `eliteTooltipHtml(t, isRewards, combatXp)` **line 1038** — `have = combatXp`
    (cumulative combat XP), `need = t.xpRequired` (grade/reward cumulative combat
    XP). NB: elite uses **combat XP**, not spendable/free XP — the "without free XP"
    variant is meaningless here (there is no free-XP component), so it should be
    skipped for the elite path.

- CSS for the row: `.wg-tip-xp` (tan `#ecca9d`) and shortfall `.wg-tip-short`
  (red `#d96e5a`) — `WGModResearch.css` lines **885-905**. The red tint when
  `have < need` is currently the *only* expression of a shortfall; a numeric
  "left" figure would cleanly reintroduce the old verbose "Need N more"/"Ready"
  pair that was deliberately removed (see comment lines 236-237) — this time as a
  compact number.

### The total-XP icon already exists
- **`XP_ICON` — line 44**: `img://gui/maps/icons/vehicle_hub/research_purchase/total_experience.png`
  — exactly the requested icon (research screen's "Total XP" = freeXP+vehXP glyph).
  Already used only in the header via `setXp()` (lines 386-391) → `.wg-xp-ico`
  background-image (`WGModResearch.css` lines 155-175).
- Gameface quirk (see lines 282, 998-1004): icons must be **background-image divs,
  not `<img>`** — Gameface clips `<img>` but honors `background-size:contain` on a
  div. `bgIconHtml(url)` (lines 282-284) is the existing helper that returns such a
  div; for an inline row-glyph a small `<span>` with `style="background-image:url(...)"`
  is the pattern.
- No tooltip-scoped XP-icon CSS class exists yet — add one (e.g. `.wg-tip-xp-ico`,
  model after `.wg-xp-ico`).

### Free-XP split already flows all the way down
No Python changes are strictly required — vehicle XP and free XP are already
separate fields end to end:
- `domain/types.py`: `VehicleSnapshot.vehicle_xp` (line 174) + `free_xp` (line 176);
  `ResearchProgressModel.spendable_xp` (line 235, = vehicle+free), `fill_vehicle`
  (line 228), `fill_free` (line 229).
- `domain/builder.py` line 65: `spendable = fill_vehicle + fill_free`.
- `bridge/gameface_bridge.py`: VM props `spendableXp` (line 554), `fillVehicle`
  (line 541), `fillFree` (line 542) — all pushed to JS.
- In JS `render()` **lines 796-797** both `data.fillVehicle` and `data.fillFree`
  are already in scope.

So **"spendable without free XP" == `fillVehicle`** (vehicle XP alone), with no new
plumbing. `xpFracHtml` today only receives the combined `spendableXp`, so to compute
the "without free XP" remaining you must also pass `fillVehicle` into the two
non-elite call sites (lines 353, 526).

### There is no pre-computed "remaining" anywhere
Affordability is a bool only (`techtree.py:19`, `fieldmods.py:42`, `skilltree.py:49`;
elite ticks `affordable=False`). "Remaining" is trivially `Math.max(0, need - have)`
computed client-side inside `xpFracHtml`, where both values already exist.

## Suggested approach
All work is in the JS helper + a bit of CSS + optional i18n. Roughly:

1. **Icon swap (easy, low-risk).** In `xpFracHtml`, replace the trailing `" XP"`
   with an inline XP-icon span using `XP_ICON` (line 44) as a background-image, and
   add a `.wg-tip-xp-ico` class in CSS. Keep `fmtXp(have) / fmtXp(need)` before it.

2. **"XP left" figure.** Compute `left = Math.max(0, need - have)` and render it,
   e.g. a second muted line/segment "· N left" — only when `left > 0` (hide when
   already affordable). Decide whether it reads better appended to the same row or
   as a small sub-line; the row is currently single-line.

3. **"Without free XP" variant (non-elite only).** Thread `fillVehicle` into
   `tooltipHtml` (line 353) and `renderNextAvailable` (line 526) — for the tech-tree
   path `need = t.position` and `have = spendableXp`, so the vehicle-only remaining
   is `Math.max(0, need - fillVehicle)`. Show it as a secondary figure, e.g.
   "N left (M without Free XP)". Skip entirely for the elite path (combat XP has no
   free-XP component). Only show the extra figure when the player actually has free
   XP contributing (`fillFree > 0`) and it changes the number — otherwise it's noise.

Feasibility: high — the data is all present, no domain/bridge changes needed. The
main open design question is layout (one dense line vs. a small stacked block) and
avoiding clutter when the two "remaining" numbers are equal.

## Touch points
- `WGModResearch.js`:
  - `xpFracHtml` (238-244) — icon swap + remaining figure.
  - Call sites `tooltipHtml` (353), `renderNextAvailable` (526), `eliteTooltipHtml`
    (1038) — pass `fillVehicle` to the first two for the "without free XP" figure.
  - `XP_ICON` (44), `bgIconHtml`/inline-bg pattern (282-284) for the glyph.
- `WGModResearch.css`:
  - New `.wg-tip-xp-ico` (model after `.wg-xp-ico`, 155-175); tweak `.wg-tip-xp`
    (885-905) for the icon/extra-figure layout.
- `adapter/i18n.py` (optional): if a "left"/"without Free XP" caption is added,
  register it in `_FALLBACK` (57-72) + wire it in `widget_labels()` (79-136). WG's
  `veh_post_progression.tooltips.priceBlock.*` namespace (already used for
  `requires`, i18n.py:121) likely has a native "you need N more" / free-XP string
  worth probing via the debug REPL before hardcoding English.

## Verification
- `pytest` for the Python suite (should stay green — no domain changes expected).
- Hot-reload JS/CSS (see `wgmod-build-deploy`) and hover ticks/chips in-garage:
  - Icon replaces "XP" and renders sharp (not clipped — confirm the bg-div, not
    `<img>`, approach).
  - "N left" appears only when the item is unaffordable and disappears at/after
    affordability.
  - On a vehicle where free XP contributes, the "without free XP" figure is larger
    than the plain remaining; equal figures collapse to one.
- Check the elite tooltip still shows just the combat-XP fraction (no free-XP figure).

## Open questions
- Layout: single dense line vs. a small stacked block for two remaining figures?
- Should "left" show only when unaffordable, or always (0 when done)? (Recommend
  only when > 0.)
- Native WG string for "without Free XP" / "need N more" — confirm id via REPL, or
  ship an English fallback and localize later (per the localization handoff, headers
  still awaiting id-confirmation).
