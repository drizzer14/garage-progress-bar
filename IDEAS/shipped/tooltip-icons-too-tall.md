# Research: Tech-tree / tier-XI-reward tooltip icons are too tall

_Submitted: "Some tooltip icons are too tall (confirmed tech tree and tier xi exclusive rewards)" · Status: shipped_

## Summary
The title-block icon in tech-tree (research) tooltips and tier-XI exclusive-reward
tooltips reads as too tall / elongated vertically. Both categories route through
the same fixed **52rem × 52rem square** icon box, which doesn't match the natural
aspect of those particular assets the way the (smaller, per-category) below-bar
tick glyphs do.

## Findings
Every tooltip title icon is built by `bgIconHtml(url)` (`WGModResearch.js:361-363`),
which emits a single `<div class="wg-tip-icon">` with the art as a
`background-image`. The kind-specific modifier picked in `tipMain`
(`js:398-400`) is only `-hex` (field mod) / `-elite` (grade emblem) / else
`-icon` — so **tech-tree modules, the next-vehicle node, AND reward thumbnails all
fall into the same `.wg-tip-main-icon` / `.wg-tip-icon` bucket** (`js:376`,
`js:400`; reward path via `tipMain` at `js:1225`, tick path at `js:485`).

That box is a hardcoded square:
- `WGModResearch.css:888-903` — `.wg-tip-icon`: `width:52rem; height:52rem;`
  `background-size: contain; background-position: center top;` positioned
  `absolute` top-right.
- `WGModResearch.css:880` — `.wg-tip-main-icon { padding-right:64rem;
  min-height:52rem; }` reserves a 52rem-tall right-hand column so short-text
  tooltips still clear the icon.

Contrast the below-bar ticks, which already give each category its own
(smaller, non-square) box and look fine:
- `.wg-tick-img` 96×24rem (`css:524-538`), `.wg-cat-vehicle .wg-tick-img` 45×28rem
  (`css:553-558`), `.wg-tick-reward` 30×30rem (`css:679-691`).

Icon sources (from the asset audit — see `IDEAS/tooltip-icon-quality.md`):
- Tech-tree **module** glyph `img://gui/maps/icons/modules/…` ≈ 48×48 (square).
- Tech-tree **vehicle node** `item.icon` ≈ 160×100 (wide).
- Tier-XI **reward** thumbnail — a customization preview (`_read_reward_art`,
  `adapter/engine_adapter.py:577-611`); style/2D previews are frequently
  **portrait / non-square**.

## Root cause
Two failure modes feed the same "too tall" complaint, both from forcing every
title icon into the 52rem square:

1. **Portrait art (tier-XI rewards):** `background-size: contain` on a
   taller-than-wide source scales it to the full **52rem height** while leaving it
   narrow — so the reward thumbnail is visibly elongated. (`css:899`)
2. **Reserved height (tech tree):** `.wg-tip-main-icon { min-height:52rem }`
   (`css:880`) forces the header block to be at least 52rem tall even when the
   module/vehicle art and its short text (caption + name + a "Requires:" line)
   need less — so the icon column dominates the tooltip vertically.

The below-bar ticks avoid both by sizing per category; the tooltip does not.

## Suggested approach
Give the tooltip title icon category-aware dimensions instead of one 52rem square
— mirror what the ticks already do. Options, least → most invasive:

1. **Shrink the box** globally: drop `.wg-tip-icon` to something like 40rem tall
   and cap width, and lower the matching `.wg-tip-main-icon` `min-height`. Simplest;
   helps every category but may make wide vehicle art small.
2. **Per-category modifier (recommended):** have JS add a category class to the
   icon (the tick's `t.category` is available in `tickIconHtml`, `js:371`), e.g.
   `wg-tip-icon-veh` / `wg-tip-icon-reward`, and in CSS give each a box matching
   its natural aspect (wide+short for vehicle, ~square-but-shorter for reward),
   plus a matching `.wg-tip-main-*` reservation. This is the clean fix and keeps
   the square for genuinely-square module glyphs.
3. Cap **height only** via `max-height` on `.wg-tip-icon` (e.g. 40rem) while
   leaving width, so portrait art can't run to full 52rem. Cheap partial fix for
   the reward case; doesn't address the tech-tree reserved-height case.

Keep it CSS-first if possible; option 2 needs a one-line JS class addition in
`bgIconHtml`/`tickIconHtml` plus the reward call site (`js:1225` area).

## Touch points
- `WGModResearch.css:888-903` (`.wg-tip-icon`) and `:880` (`.wg-tip-main-icon`).
- `WGModResearch.js:361-363` (`bgIconHtml`), `:371-378` (`tickIconHtml` — has
  `t.category`), `:398-400` (`tipMain` modifier), reward call site near `:1225`.

## Verification
- In-game (needs overlay-at-launch relaunch per the dev-loop note): hover a
  tech-tree module/next-vehicle tick and a tier-XI exclusive-reward tick; confirm
  the icon is no longer elongated and the header isn't taller than its text needs.
- Compare against a field-mod tooltip (hexagon) and an elite grade tooltip — those
  use `-hex`/`-elite` and must be unaffected by the change.
- No pytest surface (pure widget CSS/JS).

## Open questions
- **Confirm the exact aspect ratios** of the offending assets with a screenshot or
  REPL (resolve the reward `c11n` preview icon and the tech-tree `item.icon` and
  read their pixel dims) — this decides whether the fix is width-cap, height-cap,
  or per-category boxes. The "tech tree" case in particular is ambiguous: is the
  complaint the *art* being tall, or the 52rem *reserved column* dwarfing short
  text? A screenshot settles it.
- Should module glyphs (already square, fine) keep the current box while only
  vehicle + reward get new dimensions? (Argues for option 2.)
