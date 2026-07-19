---
name: gpb-widget
description: Front-end specifics of the Garage Progress Bar widget (WGModResearch.js/.css) — its #wgmod-root DOM tree, wire-contract constants, the unified tick-render loop, per-mode render branches, elite grade badges, done markers, lane de-crowding, hover/click hit-testing, the Ctrl+drag y-floor sentinel, the cold-mount self-heal render poll (the fix for the bar frozen-until-camera-moves after a tank/mode switch), and the resolution/UI-scale-aware position rescale. Use when editing this mod's widget, changing how the bar/ticks/tooltips/chips look or behave, wiring a new tick category, or debugging "bar frozen after switch" / "bar position after resolution change". (For the generic Gameface/Wulf front-end conventions and CSS quirks, see the wotmod-gameface-widget harness skill; for the Python side, gpb-architecture. Widget text is localized by reusing WG's own strings via Python `i18n.widget_labels()` — see gpb-architecture; the mod's own MSA settings-PANEL prose is a separate concern owned by the wotmod-i18n-settings harness skill.)
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

## Render lifecycle & cold-mount self-heal
`engine.whenReady` wires `observer.onUpdate(renderAndTrack)`, `observer.subscribe()`, a DIRECT
initial `renderAndTrack(observer.model)`, and `window.__wgPoll = setInterval(pollForChanges, 250)`
(cleared first, so it re-arms per mount and never stacks). The poll is this mod's fix for OpenWG's
**cold-mount dormant `viewEnv.onDataChanged`** event (the generic finding lives in
wotmod-gameface-widget → Lifecycle): on a freshly-mounted sub-view the engine withholds the
data-changed event until the view next composites, so after a mode/tank switch in an idle garage
the observer never fires and the bar looked **frozen until the camera moved** (the first paint
survived only because it's the direct call, not observer-driven). `revOf(model)` reads
`unwrap(model.wgResearch).rev` — a monotonic counter Python bumps every push (`ResearchVM` prop 32
`rev`/`setRev` in `view_models.py`; module global `_push_seq` in `bridge/gameface_bridge.py`,
written as the FIRST `tx.setRev(_push_seq)` inside `push()`'s `rvm.transaction()`). `pollForChanges`
re-renders (via `renderAndTrack`, which records `_lastRev`) only when `rev` actually moved — idle
cost is a shallow read + compare, a real render only on a genuine change (no spurious tick
rebuilds). Verified in-game with camera-on-cursor DISABLED (rules out incidental composites): both
the header mode-switch AND a REPL-driven tank switch self-heal within ~250ms. Do NOT remove the
poll to "simplify" — the direct-call + observer path alone leaves the cold-mount freeze.

## DOM structure
```
#wgmod-root (pointer-events:none)
  .wg-head   .wg-cat-icon | .wg-head-left(.wg-label,.wg-upgrades)
             | .wg-xp(.wg-xp-pct,.wg-xp-val,.wg-xp-ico,.wg-xp2-val,.wg-xp2-ico)
  .wg-track  .wg-fill-veh + .wg-fill-free (stacked) | .wg-ticks(.wg-tick…)
             | .wg-cur | .wg-hot | .wg-tooltip
  .wg-next   .wg-chip…   (skill_tree only; no caption element)
```
- `.wg-xp2-*` is the second readout pair: skill_tree shows the node counter in `.wg-xp-*` AND
  the total-XP figure in `.wg-xp2-*`; other modes leave xp2 empty.
- `.wg-xp-pct` is the optional leading progress-% span (view-only). Two independent settings
  drive the readout, latched per `render()`/`renderElite()` into module globals from
  `data.progressMode` / `data.showPercent` / `data.progressCurrent` / `data.progressRequired`:
  `PROGRESS_MODE === 1` makes `xpReadoutText(cur)` return `"current / required"` (from the unified
  scalars, plain `/`) instead of the mode's own single figure; `SHOW_PERCENT` fills `.wg-xp-pct`
  via `setXpPct()`. Both are gated on `PROGRESS_REQ > 0` — a mode with no denominator (COMPLETE,
  or `required <= 0`) falls back to the current-only figure and the `%` span stays empty +
  `display:none` (takes no space). The percent is computed IN JS as
  `min(100, round(cur/req*100))` on purpose: Wulf's int-truncating number setter would lose
  precision if it were pushed as a fraction from Python. The Python scalars behind
  `progressCurrent`/`progressRequired` are per-mode — see gpb-architecture.
- **`current / required` is ONE text node.** `xpReadoutText(cur)` (~124-129) returns the plain
  string `"current / required"` (or the single figure), written straight into `.wg-xp-val`'s
  `textContent` — Python pushes only the numeric scalars (`progressCurrent`/`progressRequired`),
  never markup. So any request to style the "total"/denominator on its own (e.g. dim the
  `/ required` half) is a **JS change** — split `xpReadoutText` into `<span>`s — NOT a CSS-only
  tweak: there's no separate element to target today.
- `.wg-cur` is the current-position glow marker, placed at the fill edge in BOTH `render`
  (linear modes) and `renderElite`.
- Mode is applied as a root class (`wg-complete`, `wg-elite`, `wg-elite-rewards`, …) that CSS
  keys off for per-mode fill colors/icon sizing; `wg-colorblind` is a sibling root class.
- Per `render`: `refreshLabels(data)` (parses `labels` JSON → `LBL`; `L(key, fallback)` never
  blanks a caption), `cbClass(data)` (toggles `wg-colorblind`), `applyPosition(root, data)`
  (positions from `posX`/`posY`; 0 = CSS default — first run measures + seeds via
  `CMD.SET_POSITION` `{x, y, seed:1}`). `render` stashes `root._wgLastData = data` so the
  resize handler can reposition without a re-push. The ONE re-enabled pointer layer is `.wg-hot`
  (`z-index:3`), spanning the bar + the glyph strip below it (extends past the left edge so
  0%-anchored done markers stay hoverable); tooltip is `z-index:4` but non-interactive.

## Bar scale (the "Large" setting)
`data.scale` (0 = Default, 1 = Large; `ResearchVM.scale`, pushed from `mod_settings.scale()` —
Python side in gpb-architecture) is latched into the module global `SCALE_LARGE` at the top of
BOTH `render()` and `renderElite()` (`SCALE_LARGE = data.scale === 1`) and folded onto
`#wgmod-root` as a `wg-large` class in the same root-class expression that carries
`wg-colorblind` / `wg-ignore-free`. Large is an **explicit CSS override class**
(`#wgmod-root.wg-large …`), deliberately NOT `transform: scale()` and NOT `calc()`/vars: the
scaling is **asymmetric** — bar WIDTH x2.0 but track heights, all fonts, all icons/glyphs and
the whole tooltip x1.5 — which a single transform can't express without distorting text, and a
separate override block keeps the Default path byte-for-byte untouched so all risk is isolated
to the override. The bar width is ONE CSS constant (`#wgmod-root` `520rem` → `.wg-large`
`1040rem`) that MUST switch in lockstep with the JS tick-geometry constant: `TICKS_WIDTH_REM`
516 (Default) / `TICKS_WIDTH_REM_LARGE` 1034 (Large = the scaled width minus the scaled 2×3rem
track borders), read via `ticksWidthRem()` off the `SCALE_LARGE` latch. rem is the engine root
font (not settable per-widget), so every `*rem` dimension scales together and the override just
restates the enlarged values exactly (13→19.5rem, 36→54rem, …). Do NOT try to collapse it into
`transform:scale` — the width/rest ratio differs, and the tooltip would blur/reflow.

**Restatement rule:** because Large is a font-size/dimension OVERRIDE (not a transform), any new
element added to the `.wg-xp` header region — or anywhere that carries a `*rem` size — MUST ALSO
be restated in the `#wgmod-root.wg-large` block, or it silently keeps its Default size in Large
mode. Precedent: the `.wg-xp-pct` span needed its own `#wgmod-root.wg-large .wg-xp-pct` rule
(x1.5 font/spacing/margin); the base rule stays byte-for-byte untouched.

Buff-line icon vertical alignment lives on `.wg-tip-buff-ico` (`align-self: flex-start`,
top-aligning the vehParams icon to the FIRST line of the buff text in BOTH scale modes — the
`.wg-large` block deliberately does NOT restate `align-self`, so Large inherits it); the row is
`.wg-tip-buff` (`display:flex; align-items: baseline`). (Was `center` — swapped to `flex-start`
in v1.2.0 so multi-line field-mod / Tier XI buff icons top-align.)

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
- **The grade-tick badge NUMBER rides on `t.level`, NOT `t.position`.** `t.level` (= `g.level`,
  the elite level number like 10/13/16 — matching WoT's own prestige-tab badge) is the numeral;
  `t.position` (= `xp_position`) is now the cumulative-XP PLACEMENT on the axis, a different
  quantity. `eliteGlyph`'s tab-badge numeral (via `tabNumber(t.level)`) and `eliteTooltipHtml`'s
  icon overlay both read `t.level | 0`. Do NOT source the badge from `t.position` — that would
  render the raw XP figure instead of the milestone level. (Reuses the existing `Tick.level` wire
  field; no wire widening. Python side: `elite.resolve_grade_band` — see gpb-architecture.)

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

## Header mode switch (`.wg-switch`)
When a vehicle qualifies for ≥2 bar modes, Python pushes the ordered `availModes` (comma-joined);
the widget shows the NEXT mode's title dimmed beside the current heading, click swaps the bar to it
(`selectMode`, persisted per-vehicle), and the previously-active title becomes the new switch
(A↔B with 2 modes, forward-cycle with 3+). `modeTitle(mode)`, `switchHit(el,x,y)` (live-rect hit-test),
`setSwitchHot(el,hot)`, `renderModeSwitch(root,data)`/`hideSwitch(root)`. The title is **rendered
only** — it lives in the header, which the root's `pointer-events:none` covers.
- **Header input routing (the hard part).** The switch title sits in the HEADER, above the bar.
  Input there is delivered by **extending the bar's `.wg-hot` layer UP over the header** (`top:-26rem`)
  — `.wg-hot` is the one proven-interactive layer. `ensureHover`'s `mousemove`/`click`/`mouseleave`
  handlers hit-test the title's own rect (`switchHit`) BEFORE the chip/tick logic, and gate the bar's
  tick tooltip/affordance/click by cursor-y (`e.clientY < barRect.top` = header band → skip). Measured
  live: motion events AND clicks DO reach `.wg-hot` over the header — an earlier belief that the header
  region was input-blocked was wrong. What failed was a body-level sibling overlay AND a nested
  `.wg-head-hot`; the working answer is the single extended `.wg-hot`.
- **Dim↔bright is a COLOR swap, inline, driven by `setSwitchHot`** (`#dce0e0` ↔ `#ede6d9`; the
  JS constants `SWITCH_COLOR`/`SWITCH_COLOR_HOT`) with
  `transition:color` for the fade — NOT opacity and NOT a `.wg-switch-hot` class. The dim/inactive
  tone is `#dce0e0` to match the `.wg-xp-val` XP-readout total (it was `#8e867d` before v1.2.x); the
  hover-bright `#ede6d9` is unchanged. NB the other `#8e867d` uses (locked/status/tick grays) are
  unrelated and stay as-is. In this Coherent
  build a dynamic **opacity** change (with `transition`) never repaints, and a toggled **class** never
  restyles, but a dynamic inline **color** write does. (Add to the CSS-quirks list alongside
  `:hover`/`:not()` unreliability.)
- **render must NOT reset the hover color on repeat pushes** (same bug as the tooltip): `hideSwitch`
  (top of `render`) only sets `display:none`, and `renderModeSwitch` re-applies the dim resting color
  ONLY when the target changes (`prevTarget !== target`). Otherwise a push while the cursor rests on
  the title dims it, and — no mousemove to re-brighten — it stays dim until the mouse moves ("hover
  only works while moving"). Python side (`availModes`/`selectMode`/`modeOverrides`): see gpb-architecture.

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
  top px go via `CMD.SET_POSITION` `{x, y, w, h}` (`w/h` = the current viewport, see below).
  **`y` is floored at 1, never 0**: `y=0` is the auto/unseeded sentinel the next push re-seeds
  from, so a flush-to-top drag stored as 0 is silently discarded — `onMove` clamp and `onUp`
  send both `Math.max(1, …)`, and the bridge drops any non-seed write with `x<=0 or y<=0`.
- **Position is viewport-aware (tracks resolution / UI-scale changes).** A resolution or
  UI-scale change resizes the Gameface viewport but does NOT re-push the model, so a `window`
  `resize` listener (added once, rAF-coalesced) re-runs `applyPosition(getRoot(),
  root._wgLastData)`. `applyPosition` keys off `currentVP()` = `{innerWidth, innerHeight}`:
  - **auto** (`posX/posY == 0`): clears inline `left/top` so the resolution-relative CSS
    default (`left:50%; top:17.6vh`) re-derives, and re-fires the default-label seed ONCE PER
    viewport size (`root._wgSeededVP = "WxH"` guard) so a new resolution re-measures the panel's
    "default N" label instead of showing the old one.
  - **pinned** (`posX/posY > 0`): the px were captured at `posW`×`posH` (pushed from Python).
    If the current viewport differs, rescale proportionally (`x*vp.w/rw`, `y*vp.h/rh`) and echo
    the rescaled px + new capture size back via `CMD.SET_POSITION` so the steppers track it and
    the next push (now matching) doesn't re-rescale (converges). A pinned px with NO capture size
    (typed into a stepper, or a pre-fix save) ADOPTS the current viewport as its ref on first
    sight (applied unchanged that once) so a later change can rescale it. Verified live 4K→1440p
    →1080p→4K: horizontal stays centered, vertical scales exactly and round-trips with no drift.
    (Python side: `g_guiResetters` + a broadened `onSettingsChanged` also refresh — see gpb-architecture.)
