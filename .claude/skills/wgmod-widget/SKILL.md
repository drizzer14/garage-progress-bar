---
name: wgmod-widget
description: Front-end (Gameface HTML/CSS/JS) conventions for the Garage Progress Bar WoT mod's widget — the DOM structure, the img:// game-icon URL maps, the pointer-events layering, the unified tick-render loop and per-mode specs, lane de-crowding, hover/click hit-testing, done markers, Ctrl+drag, and Gameface CSS quirks. Use whenever editing WGModResearch.js or WGModResearch.css, changing how the bar/ticks/tooltips/chips look or behave, fixing a glyph or icon, adjusting hover/click behavior, or wiring a new tick category into the renderer.
---

# wgmod widget (front-end) conventions

The widget is `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.{js,css}`,
injected into the hangar document by OpenWG. It reads the Python data model (exposed as
`wgResearch`) via `ModelObserver("WGModResearch")` and renders a single-axis XP bar.
For the Python side that produces that model, see the **wgmod-architecture** skill.

## Wire-contract constants (top of the JS — edit HERE, not inline)
`MODE` / `CAT` / `CMD` / `GRADE` at the top of WGModResearch.js mirror
`domain/types.py Mode`, `domain/constants.py Category`/`GradeFamily`, and the
`bridge/view_models.py` command names **verbatim**. Every render branch, click
resolver, and CSS-class builder switches on these constants — never a raw string
literal (a drifted literal fails SILENTLY: wrong glyph, no-op click). When the
Python side gains a value, add it here in the same commit. (`MODE.HIDDEN` exists
for completeness only: the HIDDEN placeholder model arrives with `visible=false`,
which `render` honors before ever branching on mode.)

## Lifecycle
`engine.whenReady` → `observer.onUpdate(render)` → `observer.subscribe()` →
`render(observer.model)`. In `render`, read the model with `unwrap(model.wgResearch)`
(Wulf wraps values; `unwrap` peels the proxy). Each render calls
`refreshLabels(data)` (parses the `labels` JSON pushed from `adapter/i18n.py` into
`LBL`; `L(key, fallback)` never blanks a caption on a missing key), `cbClass(data)`
(toggles `wg-colorblind` on the root from the `colorBlind` field), and
`applyPosition(root, data)` (positions the bar from `posX`/`posY`; 0 = CSS default —
on first run it measures the default position and seeds it back via
`CMD.SET_POSITION` with `{x, y, seed: 1}`). `data.visible === false` → hide the
root and bail (Python computes visibility: overlay open, off-garage view, per-mode
toggle → HIDDEN, hide-always/complete settings).

## DOM structure
```
#wgmod-root (pointer-events:none)
  .wg-head   .wg-cat-icon | .wg-head-left(.wg-label,.wg-upgrades)
             | .wg-xp(.wg-xp-val,.wg-xp-ico,.wg-xp2-val,.wg-xp2-ico)
  .wg-track  .wg-fill-veh + .wg-fill-free (stacked) | .wg-ticks(.wg-tick…)
             | .wg-cur | .wg-hot | .wg-tooltip
  .wg-next   .wg-chip…   (skill_tree only; no caption element)
```
- `.wg-xp2-*` is the second readout pair: skill_tree shows the node counter in
  `.wg-xp-*` AND the total-XP figure in `.wg-xp2-*`; other modes leave xp2 empty.
- `.wg-cur` is the current-position glow marker, placed at the fill edge in BOTH
  `render` (linear modes) and `renderElite`.
- Mode is applied as a root class (`wg-complete`, `wg-elite`, `wg-elite-rewards`, …)
  that CSS keys off for per-mode fill colors and icon sizing; `wg-colorblind` is a
  sibling root class overriding the palette.

## pointer-events layering (don't break this)
`#wgmod-root` is `pointer-events:none` so it never steals the hangar's drag-to-rotate.
The ONLY re-enabled layer is **`.wg-hot`** (`pointer-events:auto`, `z-index:3`, topmost)
— a transparent overlay spanning the bar AND the glyph strip below it (it extends past
the left edge so 0%-anchored done markers stay hoverable). Ticks, chips, and the
tooltip stay `pointer-events:none`. So ALL hover/click is driven from the `.wg-hot`
handlers in JS, not CSS `:hover`; the clickable cue is a JS-set pointer cursor, not a
`:hover` rule. The tooltip is `z-index:4` (above `.wg-hot`) but non-interactive.

## Icon URL conventions (img:// into game art)
Defined as constants at the top of the JS; reuse the in-game art so the bar matches WG's
own screens:
- `CAT_ICON[mode]` — header glyph per mode (`vehicleMenu/large/{research,fieldModification,vehSkillTree}.png`).
- `XP_ICON` (`vehicle_hub/research_purchase/total_experience.png`) — Total-XP readout; the
  game's `_elite` variant is lower-quality art, so the base glyph is used everywhere.
- `COMBAT_XP_ICON` (`library/xpIcon_23x22.png`) — elite mode only (cumulative combat XP).
- `SKILL_COUNTER_ICON` — the unlocked/total node counter glyph (skill_tree).
- `DONE_ICON` (`library/GreenCheck_1.png`) — the green-check badge on session "done"
  markers; `CREDITS_ICON` (`library/CreditsIcon-3.png`) — the done-tick credits footer.
- `eliteIcon(vehClass)` — COMPLETE badge; class ids use `-`, files use `_`
  (`AT-SPG` → `AT_SPG_elite.png`).
- **Elite grade badges**: `ELITE_CAT_ICON_STYLE = "tab"` (shipped) renders the battle
  team-HP arrowhead "tab" badge (`prestige/tab/<family>/<size>/<grade>.png`,
  `gradeTabUrl()` rewrites the emblem URL, `fillTabBadge()` composes badge + level
  number via `tabNumber()`, `GRADE_COLOR` tints the numeral) — falling back to the
  hexagon emblem when tab art doesn't resolve. The emblem path arrives on the tick as
  `t.icon` (`prestige/emblem/<size>/<family>/<sub>.png`); `gradeFamily()` parses
  `<family>`; emblem level digits are `emblemFont/<family>/<digit>.png` glyph divs
  (NOT CSS text), `enamel` → `gold` fallback, the `1` glyph is narrower
  (`wg-emblem-digit-one`). The MAX (lvl 350) badge is the numberless prestige hexagon
  inside the arrowhead (`ELITE_TAB_FORCE_MAX` to test without a lvl-350 vehicle).

## The unified tick-render loop
`renderTicks(ticksEl, ticks, n, spec)` is ONE loop shared by the linear path
(`render`: tech_tree / field_mods / skill_tree) and `renderElite(root, data,
isRewards)`. Each caller passes a `spec(t, i)` callback returning
`{className, leftPct, tip, body, cmd, arg, glyph, lane}`; renderTicks builds the
tick divs and returns `{tickMeta, clickMeta}` which the caller stores on
`hotEl._wgTickMeta` / `._wgClickMeta` for hit-testing. Glyph builders:
`linearGlyph(t, mode)` (done check / field-mod hexagon+roman / skill-tree final
framed perk chip / tech-tree module-vehicle art) and `eliteGlyph(t, isRewards)`
(reward thumbnail / tab badge / pip when icon-less).

**Lane de-crowding**: `computeLanes(ticks, n, pct, mode, hotEl, reserves)` measures
glyph footprints (`glyphFootprintRem`), `assignLanes` stacks overlapping glyphs into
vertical lanes, and `applyLane(mark, glyphEl, lane)` offsets the glyph + draws a stem
back to the tick (lane 0 = no-op). Done markers always keep lane 0 (they're
custom-positioned at the left edge; a lane transform would displace them).

## Per-mode specifics
- **tech_tree / field_mods** — linear: ticks at `pct(t.position)`; state classes
  `wg-locked` (dim) / `wg-aff` (bright).
- **skill_tree** — count axis; ticks carry no per-node metadata (no tooltips except
  the final tick), the FINAL tick carries the framed perk glyph, and
  `renderNextAvailable()` draws clickable chips below the bar (`wg-chip-major` for
  ≥20k XP nodes, else `wg-chip-minor`; no caption row). `upgradesSig()` lets `render`
  skip rebuilding identical chips (a rebuild would destroy the hovered chip's tooltip).
  The `onlyFinal` capstone case (all nodes done except the final): the final tick is
  forced bright and the chip row is suppressed. Header shows counter + total-XP
  (`.wg-xp2-*`). The final tick is `locked` on the COUNT axis but IS clickable, so
  `tooltipHtml` has a dedicated branch — `t.category === CAT.UPGRADE && t.icon &&
  t.xpRequired`, placed BEFORE the `t.locked` check — that shows its name + real XP
  cost (`xpFracHtml(spendableXp, t.xpRequired, XP_ICON)`) in every state, instead of
  falling into the generic "Prerequisites not met" locked branch or footering off
  `t.position` (a node index, not a cost). Chip cost lines use
  `xpFracHtml(spendableXp, xp, XP_ICON)` with **no** `fillVehicle` arg: `xp` is a node
  count-cost, not a two-currency XP figure, so a vehicle-XP "-<n>" sub-line would be
  bogus (that sub-line only makes sense when free XP moves a real combat-XP number).
- **elite** — grade-band ticks with the tab badge (above). The vehicle fill is
  **grade-colored** via inline `GRADE_COLOR[gradeFamily(curEmblem)]`, gated
  `!isRewards && !data.colorBlind` (an inline background would beat the
  `.wg-colorblind` CSS override), and ALWAYS reset first (`vehEl.style.background = ""`)
  — the fill element persists across renders, so a stale inline color leaks into
  other modes.
- **elite_rewards** — reward-thumbnail ticks; `t.state` (`achieved`/`next`/`upcoming`)
  drives the pip/thumbnail coloring via `wg-state-*` classes; keeps rarity purple fill.
- **complete** — no ticks; full green bar + class elite badge.

## Done markers (session "done" ticks/chips)
A tick/chip with `t.done`/`u.done` renders the green-check treatment (`wg-done` class,
`doneGlyph()` for the bar tick, `doneBadge()` bottom-right on a chip). Done ticks ride
the bar's LEFT EDGE (`leftPct = 0`, regardless of position). Their tooltip shows a
credits price footer when the model's `price` field is non-zero (`creditsHtml`,
`CREDITS_ICON`). Clicking a done marker never re-researches — it opens the native
screen: `CMD.OPEN_FIELD_MODS` for field-mod ticks, `CMD.OPEN_RESEARCH` otherwise;
a done chip fires `CMD.OPEN_SKILL_TREE`.

## Hover & click hit-testing
- **Hover** is two-tier: the exact element under the cursor (read `_wgBody` off the
  ancestor `.wg-tick`) when Gameface deep-targets, else nearest tick by cursor-x over
  the `tickMeta` list. skill_tree has only the final-tick tooltip, gated by proximity
  (`bestD <= 6`) so it doesn't show across the empty bar. Tooltips are edge-aware
  (clamped inside the screen) and use the reserved-column layout: `tipMain(iconHtml,
  titleHtml, bodyHtml)` renders the text block with a right-side, top-pinned icon
  column (`wg-tip-main-*`), sections joined by `joinSections` (dividers).
- **Click** (`.wg-hot` click handler): try `chipAt()` (exact chip box) first, else
  `nearestClick()` (nearest CLICKABLE tick within `CLICK_HIT_PCT`). Then `invokeCommand()`.
  NOTE the asymmetry: `renderTicks` only pushes a tick into `clickMeta` when it has a
  cmd (`if (s.cmd)`), so `nearestClick` never returns a non-clickable tick — but
  `chipAt` returns ANY chip under the cursor regardless of cmd, so the handler must
  guard `if (chip.cmd) invokeCommand(...)` (an unaffordable chip carries `cmd: null`;
  `invokeCommand(null)` would otherwise just log "command missing").
- **Clickability → command** (in the linear spec): done → open-screen commands
  (above); skill_tree → only the final (icon) tick → `CMD.OPEN_SKILL_TREE`;
  field-mod → only the NEXT (first remaining) tick, if affordable →
  `CMD.UNLOCK_FIELD_MOD` (arg `actionId`; a choice-pair level opens the screen since
  a click can't pick a variant); tech-tree (`vehicle`/`module`) → affordable &&
  !locked && actionId → `CMD.RESEARCH_UNLOCK`. Chips: done → `OPEN_SKILL_TREE`, else
  `UNLOCK_FIELD_MOD` with the node's `actionId` **only when affordable**
  (`spendableXp >= xpRequired`), else `cmd: null` (matches the bar ticks' affordability
  gate — skill-tree nodes share the field-mod purchase path).
- **Ctrl+drag repositions the bar**: mousedown on `.wg-hot` with `e.ctrlKey` starts a
  drag (plain clicks with Ctrl held are suppressed from hit-testing); on release the
  new center-x/top px are sent via `CMD.SET_POSITION` `{x, y}` and persisted by
  Python (ModsSettingsAPI). **`y` is floored at 1, never 0**: `y=0` is the
  "auto/unseeded" sentinel that the next model push re-seeds from, so a flush-to-top
  drag stored as 0 would be silently discarded — the `onMove` clamp and the `onUp`
  send both use `Math.max(1, …)`, and the bridge's `_on_set_position` drops any
  non-seed write with `x<=0 or y<=0`. `invokeCommand(name, arg)` wraps a scalar id as
  **`{value: arg}`** (a bare scalar is rejected by Gameface as "not a map"); no-arg
  commands (`openSkillTree`, `openResearch`, `openFieldMods`) are called bare.

## Gameface quirks (the usual culprits)
- Gameface clips `<img>` — render glyphs as `background-image` divs with
  `background-size: contain`.
- A CSS declaration is dropped WHOLE if a `var()` doesn't resolve (the fallback hex is
  ignored too) — so colors are hard-coded hex, not custom properties.
- Setting `display:inline-block` via the CSSOM setter is REJECTED (use `block`).
- box-shadow renders only when the element has a background fill; transforms need
  explicit dimensions; `:not()` selectors are unreliable; transform transitions need
  matching transform-function lists in both states (see the gameface-css-gotchas
  memory for war stories).
- Sizes are in `rem`; the engine scales the root font, so `rem` keeps the bar
  resolution-stable.
