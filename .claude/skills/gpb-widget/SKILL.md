---
name: gpb-widget
description: Front-end specifics of the Garage Progress Bar widget (WGModResearch.js/.css) — its #wgmod-root DOM tree, wire-contract constants, the unified tick-render loop, per-mode render branches, elite grade badges, done markers, lane de-crowding, hover/click hit-testing, and the Ctrl+drag y-floor sentinel. Use when editing this mod's widget, changing how the bar/ticks/tooltips/chips look or behave, or wiring a new tick category. (For the generic Gameface/Wulf front-end conventions and CSS quirks, see the wotmod-gameface-widget harness skill; for the Python side, gpb-architecture.)
---

# wgmod widget (this mod's front-end)

Generic Gameface/Wulf conventions (the `ModelObserver`+`unwrap` lifecycle, wire-contract
discipline, `pointer-events` layering, `invokeCommand` MAP-wrapping, `img://` art, the CSS
quirks) live in the **wotmod-gameface-widget** harness skill. This skill is the Garage
Progress Bar's concrete widget: `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.{js,css}`,
which reads `wgResearch` and renders a single-axis XP bar.

## Wire-contract constants
`MODE` / `CAT` / `CMD` / `GRADE` at the top of the JS mirror `domain/types.py Mode`,
`domain/constants.py Category`/`GradeFamily`, and the `bridge/view_models.py` command names
verbatim. Every branch/resolver/class-builder switches on these — never a raw literal (drift
fails silently). `MODE.HIDDEN` exists for completeness only: the HIDDEN model arrives
`visible=false`, which `render` honors before branching on mode.

## DOM structure
```
#wgmod-root (pointer-events:none)
  .wg-head   .wg-cat-icon | .wg-head-left(.wg-label,.wg-upgrades)
             | .wg-xp(.wg-xp-val,.wg-xp-ico,.wg-xp2-val,.wg-xp2-ico)
  .wg-track  .wg-fill-veh + .wg-fill-free (stacked) | .wg-ticks(.wg-tick…)
             | .wg-cur | .wg-hot | .wg-tooltip
  .wg-next   .wg-chip…   (skill_tree only; no caption element)
```
- `.wg-xp2-*` is the second readout pair: skill_tree shows the node counter in `.wg-xp-*` AND
  the total-XP figure in `.wg-xp2-*`; other modes leave xp2 empty.
- `.wg-cur` is the current-position glow marker, placed at the fill edge in BOTH `render`
  (linear modes) and `renderElite`.
- Mode is applied as a root class (`wg-complete`, `wg-elite`, `wg-elite-rewards`, …) that CSS
  keys off for per-mode fill colors/icon sizing; `wg-colorblind` is a sibling root class.
- Per `render`: `refreshLabels(data)` (parses `labels` JSON → `LBL`; `L(key, fallback)` never
  blanks a caption), `cbClass(data)` (toggles `wg-colorblind`), `applyPosition(root, data)`
  (positions from `posX`/`posY`; 0 = CSS default — first run measures + seeds via
  `CMD.SET_POSITION` `{x, y, seed:1}`). The ONE re-enabled pointer layer is `.wg-hot`
  (`z-index:3`), spanning the bar + the glyph strip below it (extends past the left edge so
  0%-anchored done markers stay hoverable); tooltip is `z-index:4` but non-interactive.

## Icon URLs (this mod's map)
`CAT_ICON[mode]` (`vehicleMenu/large/{research,fieldModification,vehSkillTree}.png`), `XP_ICON`
(`vehicle_hub/research_purchase/total_experience.png` — base glyph used everywhere; `_elite`
variant is lower quality), `COMBAT_XP_ICON` (`library/xpIcon_23x22.png`, elite only),
`SKILL_COUNTER_ICON`, `DONE_ICON` (`library/GreenCheck_1.png`), `CREDITS_ICON`
(`library/CreditsIcon-3.png`), `eliteIcon(vehClass)` (COMPLETE badge; `AT-SPG`→`AT_SPG_elite.png`).
**Elite grade badges:** `ELITE_CAT_ICON_STYLE="tab"` renders the arrowhead "tab" badge
(`prestige/tab/<family>/<size>/<grade>.png`; `gradeTabUrl()`, `fillTabBadge()`, `tabNumber()`,
`GRADE_COLOR` tints the numeral), falling back to the hexagon emblem when tab art doesn't
resolve. Emblem path arrives as `t.icon` (`prestige/emblem/<size>/<family>/<sub>.png`);
`gradeFamily()` parses `<family>`; level digits are `emblemFont/<family>/<digit>.png` glyph divs
(NOT CSS text), `enamel`→`gold` fallback, `1` glyph narrower (`wg-emblem-digit-one`). MAX (lvl
350) = numberless prestige hexagon inside the arrowhead (`ELITE_TAB_FORCE_MAX` to test).

## The unified tick-render loop
`renderTicks(ticksEl, ticks, n, spec)` is ONE loop shared by the linear path (`render`:
tech_tree/field_mods/skill_tree) and `renderElite(root, data, isRewards)`. Each caller passes a
`spec(t, i)` → `{className, leftPct, tip, body, cmd, arg, glyph, lane}`; renderTicks builds the
divs and returns `{tickMeta, clickMeta}` stored on `hotEl._wgTickMeta`/`._wgClickMeta`. Glyph
builders: `linearGlyph(t, mode)` (done check / field-mod hexagon+roman / skill-tree final framed
perk chip / tech-tree module-vehicle art) and `eliteGlyph(t, isRewards)` (reward thumbnail / tab
badge / pip). **Lane de-crowding:** `computeLanes(...)` measures `glyphFootprintRem`,
`assignLanes` stacks overlaps into vertical lanes, `applyLane` offsets + draws a stem (lane 0 =
no-op; done markers always keep lane 0 — custom-positioned at the left edge).

## Per-mode specifics
- **tech_tree / field_mods** — linear: ticks at `pct(t.position)`; `wg-locked` (dim) / `wg-aff` (bright).
- **skill_tree** — count axis; ticks carry no per-node metadata (no tooltips except the final
  tick), the FINAL tick carries the framed perk glyph, `renderNextAvailable()` draws clickable
  chips below the bar (`wg-chip-major` ≥20k XP, else `wg-chip-minor`; no caption). `upgradesSig()`
  lets `render` skip rebuilding identical chips (a rebuild destroys a hovered chip's tooltip). The
  `onlyFinal` capstone case: final tick forced bright, chip row suppressed. Header shows counter +
  total-XP (`.wg-xp2-*`). The final tick is `locked` on the COUNT axis but IS clickable, so
  `tooltipHtml` has a dedicated branch (`t.category === CAT.UPGRADE && t.icon && t.xpRequired`,
  BEFORE the `t.locked` check) showing name + real XP cost. Chip cost lines use `xpFracHtml(...)`
  with **no** `fillVehicle` arg (a node count-cost, not a two-currency XP figure). In the
  `onlyFinal` state the lone available node is reachable ONLY via the bar tick's `OPEN_SKILL_TREE`
  (screen) — the direct one-click `UNLOCK_FIELD_MOD` affordance is deliberately NOT restored on
  the final tick (owner decision 2026-07-05: keep it screen-only). Don't "fix" this.
- **potential_tier_xi** — opt-in speculative bar; ONE non-clickable tick pinned at 100%. Like
  skill_tree's final tick it's a single far-from-left milestone, so the hover proximity gate
  (below) covers `POTENTIAL_TIER_XI` too, else hovering the empty left half pops the tooltip.
- **elite** — grade-band ticks with the tab badge. Vehicle fill grade-colored via inline
  `GRADE_COLOR[gradeFamily(curEmblem)]`, gated `!isRewards && !data.colorBlind`, and ALWAYS reset
  first (`vehEl.style.background = ""`) — the fill element persists across renders.
- **elite_rewards** — reward-thumbnail ticks; `t.state` (`achieved`/`next`/`upcoming`) drives pip
  coloring via `wg-state-*`; keeps rarity purple fill.
- **complete** — no ticks; full green bar + class elite badge.

## Buff lines (tooltip KPI rows)
Each buff/KPI line in `effect` / `optionEffects` is an ENRICHED RECORD from Python
(`icon \x1f cls \x1f value \x1f desc`, `cls` = `pos`/`neg`) so a tooltip buff renders like the
game's native perk tooltip: the vehParams param icon, the value+unit colored green (buff) / red
(nerf), then the dim phrase — e.g. `[icon] +50 HP  to vehicle hit points`. `buffLineHtml(line,
baseCls)` splits on `\x1f`; `<4` fields → plain `.wg-tip-effect` fallback (non-KPI text).
`effectHtml` and `variantsHtml` both route through it. The row is **FLEXBOX**
(`.wg-tip-buff`): Coherent stacks bare inline/inline-block spans, so a flex row is the only way
to keep icon + value + phrase on one line (icon `flex:0 0 auto`; `.wg-tip-buff-desc`
`flex:1 1 auto; min-width:0` wraps internally). Colors: `.wg-buff-pos #64ba21` / `.wg-buff-neg
#f31201` (native tokens), color-blind `#wgmod-root.wg-colorblind .wg-buff-neg` → orange
`#ffaa4c`. Title↔description and inter-buff spacing share one value: `.wg-tip-effect` /
`.wg-tip-variant-eff` `margin-top` (every line, incl. the first, carries it). The Python side
that builds the record is `adapter/_read_common._kpi_lines` (see gpb-architecture).

## Done markers
A tick/chip with `t.done`/`u.done` renders the green-check treatment (`wg-done`, `doneGlyph()` /
`doneBadge()`). Done ticks ride the bar's LEFT EDGE (`leftPct=0`). Tooltip shows a credits price
footer when `price` is non-zero (`creditsHtml`, `CREDITS_ICON`). Clicking a done marker opens the
native screen: `CMD.OPEN_FIELD_MODS` for field-mod ticks, `CMD.OPEN_RESEARCH` otherwise; a done
chip fires `CMD.OPEN_SKILL_TREE`.

## Hover & click hit-testing
- **Hover** two-tier: exact element under cursor (`_wgBody` off ancestor `.wg-tick`) when Gameface
  deep-targets, else nearest tick by cursor-x over `tickMeta`. Single-milestone modes (skill_tree's
  final tick AND potential_tier_xi's 100% tick) gate the fallback by proximity (`near.dist <= 6`)
  so a lone far-right tick doesn't pop across the empty bar; dense modes stay nearest-anywhere.
  Tooltips edge-aware; reserved-column layout via `tipMain(...)` (right-side, top-pinned icon
  column), sections joined by `joinSections`.
- **Hover perf / stale-tooltip:** `show()` early-returns when the same body/left/lane is already
  shown (skips the per-mousemove innerHTML+clampTip churn); `barRect()` is read once per mousemove
  and threaded into `nearestByX`/`nearestClick` as an optional `rect`. `render()`/`renderElite()`
  call `hideStaleTooltip(hotEl, tipEl, data)` — a `dataSig(data)` diff that HIDES a tooltip left
  over from the previous vehicle on a genuine change, while leaving it alone on a repeat push (so a
  still cursor keeps its tooltip). NB `render()` must never blanket-hide the tooltip — that made it
  vanish whenever the cursor stopped. (The `renderTicks` skip-rebuild optimization is NOT done yet.)
- **Click** (`.wg-hot`): `chipAt()` (exact chip box) first, else `nearestClick()` (nearest
  CLICKABLE tick within `CLICK_HIT_PCT`). `renderTicks` only pushes into `clickMeta` when a tick
  has a cmd, so `nearestClick` never returns a dead tick — but `chipAt` returns ANY chip, so guard
  `if (chip.cmd) invokeCommand(...)`.
- **Clickability → command** (linear spec): done → open-screen; skill_tree → only the final (icon)
  tick → `OPEN_SKILL_TREE`; field-mod → only the NEXT affordable tick → `UNLOCK_FIELD_MOD` (a
  choice-pair level opens the screen); tech-tree → affordable && !locked && actionId →
  `RESEARCH_UNLOCK`. Chips: done → `OPEN_SKILL_TREE`, else `UNLOCK_FIELD_MOD` **only when
  affordable** (`spendableXp >= xpRequired`), else `cmd:null`.
- **Ctrl+drag repositions**: mousedown on `.wg-hot` with `e.ctrlKey`; on release the new center-x/
  top px go via `CMD.SET_POSITION` `{x, y}`. **`y` is floored at 1, never 0**: `y=0` is the
  auto/unseeded sentinel the next push re-seeds from, so a flush-to-top drag stored as 0 is
  silently discarded — `onMove` clamp and `onUp` send both `Math.max(1, …)`, and the bridge drops
  any non-seed write with `x<=0 or y<=0`.
