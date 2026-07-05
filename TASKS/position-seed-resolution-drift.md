# Research: First-run position seed pins the bar to px — drifts after a resolution change

_Submitted: bug hunt (2026-07-05) · Status: open_

## Summary
On the very first garage mount the widget measures its CSS-default spot (a
resolution-relative `top: 17.6vh`-style placement) and seeds it to Python as fixed pixel
coordinates. From then on `posX/posY > 0`, so the bar is pinned to those pixels forever —
the resolution-independent CSS default never applies again, and the recorded "reset
target" is the OLD resolution's pixels. Change the game resolution (or move to another
monitor) and both the bar and the settings-panel Reset land off-header. Confidence:
medium-high for the mechanism (verified end-to-end in code); severity low-medium (users
who never change resolution never see it).

## Findings
- Seed path: `applyPosition` clears inline position when unseeded, then measures and
  sends `{x, y, seed: 1}` exactly once — `WGModResearch.js:1050-1075` (guarded by
  `_wgSeedPending`; the comment at `js:1070-1072` says seed:1 marks the DEFAULT position
  so reset repaints to real default coords).
- Python persists the seed like a user position: `bridge/mod_settings.py` `set_position`
  writes `_settings.posX/posY` + `saveState()` (`mod_settings.py:493-509`), so every
  later mount takes the `x > 0 && y > 0` pinned branch (`js:1050-1056`).
- The CSS default is deliberately resolution-relative (`WGModResearch.css:10-20`), so the
  pre-seed placement adapts to any resolution — the seed freezes one sample of it.
- Related dead-fallback nit (fold in or ignore): `js:1064` `requestAnimationFrame ||
  function (f) { f(); }` — the sync fallback would re-enter render() re-entrantly via the
  Python echo; only safe because Gameface provides rAF. Low.

## Root cause
The seed exists so the settings panel's X/Y steppers and Reset show real numbers instead
of 0/0 — but persisting it into the same posX/posY slot as a user drag makes "never
positioned" indistinguishable from "user chose this spot", and px is the wrong unit for
"the default".

## Suggested approach
Options, smallest first (owner picks):
1. Don't persist the seed as a position: keep the panel's displayed default in a separate
   non-authoritative field (or compute it JS-side on panel open), leaving posX/posY = 0
   (auto) until a real drag/stepper edit. Wire note: the 0-sentinel semantics are already
   baked in everywhere (`clamp_pos`, `applyPosition`, drag floor at 1 from the previous
   sweep) — this option leans INTO them.
2. Keep the seed but re-seed on viewport-size change: JS compares
   `window.innerWidth/Height` to a stored seed-time size and re-sends `seed:1` when they
   differ AND the user has never dragged (needs a "user-set" flag next to posX/posY —
   settingsVersion bump 2→3 + migration).
3. Store resolution-relative coords (fractions of viewport) instead of px — biggest
   change, touches steppers' px semantics; probably not worth it.
Recommend option 1; it also simplifies `applyPosition`.

## Touch points
- `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js:1050-1075`
- `src/res/scripts/client/wgmod_research/bridge/mod_settings.py:493-509` (+ template
  version/migration if a flag is added)
- `tests/test_position.py` — seed-vs-user-write semantics.

## Verification
In-game: fresh settings (delete the MSA entry) → bar at CSS default; change resolution →
bar still header-anchored (pre-fix it drifts); Ctrl+drag → position persists across
relaunch; panel Reset → returns to the CURRENT resolution's default. Python change needs
build+deploy+relaunch; JS half hot-reloads.

## Open questions
- Which option — 1 (don't persist seed) vs 2 (re-seed on resize)? MSA panel UX for
  "auto" X/Y display needs a look under option 1 (what do the steppers show before any
  drag?).
