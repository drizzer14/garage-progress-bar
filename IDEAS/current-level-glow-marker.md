# Research: Brighter, glowing marker at the current progress position

_Submitted: "On current progress level show brighter blurred tick. Consult battlepass progress bar inside the selected chapter." · Status: open_

## Summary
Add a brighter, blurred/glowing marker at the bar's **current progress position**
(where the fill currently ends — the player's current level), modeled on how WoT's
Battle Pass bar highlights the current level inside a selected chapter. Feasible via
a filled marker + glow (`box-shadow`/`drop-shadow`), matching the mod's existing
glow vocabulary. A literal `filter: blur()` is **not safe** in this Gameface build —
simulate the blur with a soft glow instead.

## Findings
All refs in `src/res/gui/gameface/mods/14th_ua/WGModResearch/`.

### The current-progress position is a single computed percentage
The fill's right edge = current progress. In `render()`:
- Inputs `WGModResearch.js:855-861`: `spendableXp`, `scaleMin`/`scaleMax`, `fillVehicle`
  (`fv`), `fillFree` (`ff`), `span`, and `pct(xp) = ((xp - sMin)/span)*100` clamped 0-100.
- Fill applied `WGModResearch.js:949-954`: `vehW = pct(sMin + fv)`, free stacked to
  `pct(sMin + fv + ff)`. So the **current level x-position is `pct(sMin + fv + ff)`**
  — the combined fill edge. This is NOT a tick index; ticks are milestones at
  `t.position`, independent of the fill.
- Fill CSS `WGModResearch.css:236-257` (`transition: left/width 0.3s ease` at :242).

### Ticks today — no current-position marker exists
- Ticks built in the loop `WGModResearch.js:982-994`, each a `.wg-tick` positioned by
  `mark.style.left = pct(t.position) + "%"`.
- State classes: `.wg-tick` base `WGModResearch.css:412-421` (`box-shadow:0 0 1rem #888`),
  `.wg-tick.wg-aff` `:425-431` (`box-shadow:0 0 4rem rgba(255,255,255,0.7)`),
  `.wg-tick.wg-locked` `:436-442`, `.wg-tick.wg-clickable` `:996-998`
  (`box-shadow:0 0 4rem rgba(255,244,200,0.6)`).
- **No "current"/"active" tick class and no marker at the fill edge exist today.** The
  new marker is a NEW element at `pct(sMin + fv + ff)`, distinct from milestone ticks.
- `.wg-ticks` layer is `z-index:2` above the notch overlay; fills are below. Fill
  elements are re-fetched each render (`:875-876`, `:1118-1119`), so the pattern is:
  append a marker div once to `.wg-track`, reposition it per-render (like the tooltip).

### Existing glow/blur vocabulary to match
- Root halo is a painted `radial-gradient`, NOT a box-shadow — `WGModResearch.css:29-52`,
  with an explicit note (`:30-37`) that **box-shadow on a transparent box does not render
  in Gameface**; the halo had to be a gradient.
- Track lift `:178-181` (`inset` glow + drop shadow). Affordable-tick white glow `:430`.
  Clickable warm glow `:997`. Steel-blue skill fill `:262-265` (`#5a8fc4`).
- Closest existing "current milestone" highlight: elite **next pip** `:595-598`
  (`drop-shadow(0 0 4rem rgba(255,255,255,0.8))`) and next emblem `:684-690`
  (`drop-shadow(0 0 4rem rgba(255,255,255,0.9))`). Gold achieved halo `:676-683`.
- → A new current-position marker should reuse the **white-glow language** of `wg-aff`
  / `wg-state-next` on a *filled* element.

### Per-mode current position (all reduce to the fill edge)
| Mode | Where | Current-pos formula | Note |
|---|---|---|---|
| tech_tree / field_mods | `render()` :949-954 | `pct(sMin + fv + ff)` | XP-based, two-tone |
| skill_tree | `render()` :942/866-873/949-954 | `pct(sMin + fv)` | **count-based**, `ff=0`; marker sits on a node boundary |
| elite / elite_rewards | `renderElite()` :1182-1202 | `pct(sMin + fillVehicle)` | single-segment; **early-returns via :841-844** — marker must be added here too |
| complete | :932-935 | bar hidden | no marker |

A shared helper computing `pct(sMin + fv + ff)` hooks the marker into all modes; mind
that skill_tree is count-based (`ff=0`) and elite is built in its own function.

### Battle Pass reference — structure confirmed, art not decompilable
The decompiled EU 2.3 client **is** present at `C:\Users\Dmytro Vasylkivskyi\wot-eu`
(branch 2.3), but it contains **only decompiled Python — no Gameface HTML/CSS/SCSS and
no battle-pass textures** (the bar's art is baked into the packaged Gameface bundle).
What the Python confirms about the in-chapter bar:
- View/presenter `gui/impl/lobby/battle_pass/battle_pass_progressions_view.py`
  (`ProgressionPresenter`, alias `R.aliases.battle_pass.Progression()`), view model
  `.../battle_pass_progressions_view_model.py`, per-level `.../reward_level_model.py`.
- Current-level data: `currentPointsInLevel`/`previousPointsInLevel` (partial fill
  inside the active level), `currentLevel`, per-level `state`
  (`DISABLED/NOT_REACHED/REACHED/NOT_CHOSEN`, `reward_level_model.py:9-12`), and
  `showLevelsAnimations` (animated-highlight trigger). Presenter computes the live
  current level from points at `battle_pass_progressions_view.py:391-419`.
- Mechanism (from WoT UI knowledge, since art isn't in source): a segmented bar where
  the **current level is the fill front** — a partial-fill segment marked by a
  **brighter glowing knob/leading edge with a soft bloom** (additive glow sprite / soft
  shadow behind a bright node, optionally pulsing via `showLevelsAnimations`) — i.e.
  exactly the "brighter blurred tick" the user wants. It's a **glow/bloom, not a CSS
  `blur()`**. No reusable `img://` asset path is recoverable — imitate, don't reuse.

### Gameface feasibility (Part C)
- **`box-shadow` glow — WORKS, but only on a filled element** (`:30-37` documents
  box-shadow on transparent boxes not rendering; all working glows are on filled
  elements). ✅ Give the marker a solid background.
- **`filter: drop-shadow()` — WORKS** (glyph halos `:497/597/687`). ✅
- **`filter: blur()` — RISKY/UNVERIFIED.** Not used anywhere; the file documents that
  `grayscale()` silently does NOT render in this build (`:447-448/674-675/707-709`), so
  `blur()` can't be assumed. **Recommend simulating the blur with a soft glow, not
  `filter: blur()`.**
- **`radial-gradient` — WORKS** (root halo) — a painted bloom behind the marker is the
  safest fallback.
- **`transition` — WORKS** (`:242`). A **`@keyframes` pulse is unused → unverified**;
  attempt only with a static fallback.
- Other gotchas: `var()` drops the declaration (hard-code hex); `<img>` is clipped (use
  `background-image` divs); size in `rem`; `transform` needs explicit dims.

## Suggested approach
1. Add a single `.wg-cur` (current-position) marker div to `.wg-track` in `ensureRoot()`
   (`WGModResearch.js:521-527`), a filled bright sliver/knob.
2. A shared helper returns the current fill-edge percentage; position the marker with
   `left = pct(sMin + fv + ff)` (skill_tree: `fv` only; elite: `sMin + fillVehicle`).
   Update it in BOTH `render()` (`:949-954`) and `renderElite()` (`:1182-1202`); hide it
   in `complete` mode.
3. Style `.wg-cur` with a solid bright fill + `box-shadow: 0 0 Nrem rgba(255,255,255,…)`
   (and/or `drop-shadow`) to match `wg-aff`/`wg-state-next`. For the "blurred" look use a
   layered soft glow / `radial-gradient` bloom — NOT `filter: blur()`.
4. Optionally add a subtle `@keyframes` pulse, but only with a static fallback (support
   unverified). Reuse the `0.3s ease` transition so the marker glides with the fill.

Feasibility: high for a static glowing marker (CSS + a few JS lines, no Python). The
only uncertain bits — `filter: blur()` and `@keyframes` pulse — are explicitly flagged;
default to the confirmed glow techniques.

## Touch points
- `WGModResearch.js`: `ensureRoot()` (`:521-527`) add the marker; `render()` (`:949-954`)
  and `renderElite()` (`:1182-1202`) position it; a shared pct helper (`:860`).
- `WGModResearch.css`: new `.wg-cur` rule modeled on `.wg-tick.wg-aff` (`:425-431`) /
  `wg-state-next` (`:595-598`); mind the transparent-box box-shadow rule (`:30-37`).
- No Python / domain / bridge changes — the position derives from existing
  `fillVehicle`/`fillFree`/`scaleMin`/`scaleMax` VM fields.

## Verification
- Hot-reload JS/CSS (`wgmod-build-deploy`; overlay must exist at client launch per
  `dev-loop-no-midsession-overlay`) and check the marker sits exactly at the fill edge
  in every mode (tech_tree, field_mods, skill_tree count-based, both elite modes) and is
  hidden in complete mode.
- Confirm the glow renders (filled element) and glides with the fill's `0.3s` transition.
- If trying `filter: blur()` or a `@keyframes` pulse, verify in-client that they actually
  render (both are unproven in this Gameface build) and fall back to a static soft glow
  if not.
- `pytest` unaffected (frontend-only).

## Open questions
- Marker shape: a thin bright vertical sliver at the fill edge, or a small knob/dot? (BP
  uses a knob-like leading edge.)
- Include the pulse animation, or static glow only? (Static is the safe default.)
- In skill_tree (count-based) the fill edge lands on a node boundary — should the marker
  snap to the node or sit at the raw fill edge? Decide during live testing.
