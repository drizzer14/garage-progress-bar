---
name: gpb-widget
description: Front-end specifics of the Garage Progress Bar widget (WGModResearch.js/.css) — its #wgmod-root DOM tree, wire-contract constants, the unified tick-render loop, per-mode render branches, elite grade badges, the COMPLETE ("Fully Progressed") golden bar + finished-category row, icon-family size normalization, done markers, lane de-crowding, hover/click hit-testing, the Ctrl+drag y-floor sentinel, the cold-mount self-heal render poll (the fix for the bar frozen-until-camera-moves after a tank/mode switch), and the resolution/UI-scale-aware position rescale. Use when editing this mod's widget, changing how the bar/ticks/tooltips/chips look or behave, wiring a new tick category, or debugging "bar frozen after switch" / "bar position after resolution change". (For the generic Gameface/Wulf front-end conventions and CSS quirks, see the wotmod:gameface-widget harness skill; for the Python side, gpb-architecture. Widget text is localized by reusing WG's own strings via Python `i18n.widget_labels()` — see gpb-architecture; the mod's own MSA settings-PANEL prose is a separate concern owned by the wotmod:i18n-settings harness skill.)
---

# wgmod widget (this mod's front-end)

Generic Gameface/Wulf conventions (the `ModelObserver`+`unwrap` lifecycle, wire-contract
discipline, `pointer-events` layering, `invokeCommand` MAP-wrapping, `img://` art, the CSS
quirks) live in the **wotmod:gameface-widget** harness skill. This skill is the Garage
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
wotmod:gameface-widget → Lifecycle): on a freshly-mounted sub-view the engine withholds the
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

**The widget sets NO root font-size and does NO DPR/resolution-based SIZING.** Every element
dimension is pure `rem`, delegated to the engine's `interfaceScale` (the WoT settings' UI scale /
its power-of-two Auto gating), which scales WG's OWN chrome identically. The only resolution reads
in the JS (`currentVP()`, `innerWidth`/`innerHeight`) are for bar POSITION/drag, never sizing;
the root carries only `translateX(-50%)`, no `transform: scale`. Consequence for triage: any
"everything is uniformly ~2x bigger on a 4K display" report is the ENGINE interface-scale, NOT a
mod scaling race and NOT the "Large" Scale setting — the two are orthogonal (verified while
diagnosing a Large-after-cold-launch bug: the uniform enlargement was engine scale, while the
Scale setting's `.wg-large` is asymmetric x2.0/x1.5). Don't hunt for a mod-side DPR/rem race.

**Restatement rule:** because Large is a font-size/dimension OVERRIDE (not a transform), any new
element added to the `.wg-xp` header region — or anywhere that carries a `*rem` size — MUST ALSO
be restated in the `#wgmod-root.wg-large` block, or it silently keeps its Default size in Large
mode. Precedent: the `.wg-xp-pct` span needed its own `#wgmod-root.wg-large .wg-xp-pct` rule
(x1.5 font/spacing/margin); the base rule stays byte-for-byte untouched. `em` appears **zero**
times in this widget's CSS — the house pattern is rem-only, delegated to the engine root font — so a
new rule that must scale carries an explicit `.wg-large` restatement rather than reaching for `em`.

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
(`library/CreditsIcon-3.png`), `eliteIcon(vehClass)`, `CAT_ICON[MODE.COMPLETE]`
(`personal_missions_30/common/card/done_big.png`), `PRESTIGE_EMBLEM`
(`prestige/emblem/72x72/prestige.png`).
**Elite grade badges:** `ELITE_CAT_ICON_STYLE="tab"` renders the arrowhead "tab" badge
(`prestige/tab/<family>/<size>/<grade>.png`; `gradeTabUrl()`, `fillTabBadge()`, `tabNumber()`,
`GRADE_COLOR` tints the numeral), falling back to the hexagon emblem when tab art doesn't
resolve. Emblem path arrives as `t.icon` (`prestige/emblem/<size>/<family>/<sub>.png`);
`gradeFamily()` parses `<family>`; level digits are `emblemFont/<family>/<digit>.png` glyph divs
(NOT CSS text), `enamel`→`gold` fallback, `1` glyph narrower (`wg-emblem-digit-one`). MAX (lvl
350) = numberless prestige hexagon inside the arrowhead. **There is NO force-MAX testing hook**
in this widget (an earlier version of this skill claimed an `ELITE_TAB_FORCE_MAX` constant — no
such symbol has ever existed; the only dev flag is `FORCE_COMPLETE`, below). To see MAX, drive a
maxed vehicle or edit the model in the REPL.
- **Two emblem-number builders, pick by host type.** `emblemNumber(level, family)` returns a
  **DOM** `<span class="wg-tick-emblem-num">` of digit glyphs; `emblemNumberHtml(level, family)`
  is its innerHTML-**string** sibling; `eliteTipIconHtml(url, level, extraCls, famOverride)` wraps
  the string form in a `.wg-tip-icon.wg-tip-icon-elite` box. `famOverride` also **opts a
  family-less emblem INTO the number** (the generic `prestige.png` a category badge uses) — grade
  ticks pass nothing, so their MAX badge stays numberless. Adding a third implementation is the
  wrong move; one of these three already fits.
- **`eliteTipIconHtml()` is hard-coded for the tooltip's MAIN icon slot** — its markup arrives
  `position:absolute; top:0; right:0`, 55rem square. Reusing it anywhere in normal flow (e.g. a
  tooltip FOOTER row) needs an override to `position:relative` — **not `static`**, the box must stay
  the positioning context for the `.wg-tip-icon-num` digit overlay — plus an explicit box size. Cheap
  size to reuse: the below-bar tick emblem's 30rem (Large 45rem), because the existing digit-glyph
  rules already fit a 3-digit level in that box, so the overlay needs no new rules at all. Precedent
  + the reasoning inline: `.wg-tip-foot .wg-tip-icon-elite` (WGModResearch.css ~1093-1111).
  Any OTHER box size also breaks the `.wg-tip-icon-num` digit overlay in two ways that must BOTH be
  fixed: (a) the overlay's `top: 2rem` (Large `3rem`) centering nudge is ~4% of a 55rem box but ~1/8
  of a 16-24rem one, so the number sits visibly low → reset to `top: 0`; (b) the digit glyphs
  (`8.125 × 16.25rem`, Large `12.1875 × 24.375rem`) overflow a small box entirely → rescale, keeping
  the below-bar tick emblem's proven ~56% fill for 3 digits (a level can reach 350). As shipped on
  the ELITE_REWARDS cost row: a 24rem badge (Large 36rem) takes 4.5 × 9rem digits (Large
  6.75 × 13.5rem) — `WGModResearch.css:1876-1917`. NB when the reuse site can supply its own
  positioning context, KEEPING the inherited `position:absolute` is preferable — that's what pins the
  badge via `right: 0` — and an absolutely positioned box is a containing block for the digit overlay
  just as a relative one is.
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
- **complete** ("Fully Progressed") — no ticks; a **GOLDEN** full bar plus a below-bar row of the
  vehicle's FINISHED categories. See the dedicated section below. (An earlier version of this
  skill described this as "full green bar + class elite badge" — that was never implemented and
  the colour is gold, not green; the whole render path landed in `e0ae891`.)

## COMPLETE ("Fully Progressed") — the golden bar + finished-category row
Shipped in `e0ae891`. The Python gate/wire is in gpb-architecture; this is the front end.
- **The bar is GOLD, not green.** `#wgmod-root.wg-complete .wg-fill-veh` is the widget's ONE
  gradient — a single non-tiling `linear-gradient(90deg, #d9a441, #ecbe6e, #e8b84b)` (Coherent
  renders non-repeating linear gradients reliably; repeating/conic ones it does not), lifted from
  the prestige gold family (`#d9a441` IS the flat `.wg-elite` fill) with a lighter mid so a
  100%-filled bar doesn't read flat. Colour-blind substitutes the same flat `#ffaa4c` the elite
  fill uses (`WGModResearch.css` ~389-396, ~415-419).
- **Header tick art is `personal_missions_30/common/card/done_big.png`, NOT `library/GreenCheck_1.png`.**
  GreenCheck_1 is natively **16x16** — it would upscale 2.25-4.5x in the 36/54rem `.wg-cat-icon`
  box; done_big is 110x110. GreenCheck_1 stays correct for the small 12rem corner `doneBadge()`.
  done_big's checkmark fills its canvas edge to edge, so `.wg-complete .wg-cat-icon` trims it to
  24rem and drops the base optical up-nudge (`WGModResearch.css:102-109`).
- **Header title** = `L("headerComplete", "Fully Progressed")` via the normal `modeTitle()` path
  (`WGModResearch.js:1912`). Python sources that label from the MSA settings panel's own
  translations — see gpb-architecture.
- **The category row is `renderCompleteCats(nextEl, arr, curEmblem, eliteLevel, hotEl)`**
  (`WGModResearch.js:1122`), reusing the skill-tree chip machinery **verbatim**: each box carries
  `.wg-chip` (size/spacing + the nested `.wg-chip-tip` frame + the `.wg-large` restatement, all
  free), the shared `doneBadge()` corner check, and `hotEl._wgChips` hit-testing (`chipAt` /
  `setActiveChip`). Boxes are VISUAL ONLY — `cmd: null` on every one. Tooltip = `tipMain(icon,
  name)` with `modeTitle(u.category)` as the title, plus `xpTotalHtml(u.xpRequired)` — a bare
  total shaped like `creditsHtml`, deliberately NOT `xpFracHtml` (nothing is left to afford, so no
  have/need fraction and no battles estimate; `0`/absent renders nothing).
- **The level numeral rides the ELITE box ONLY.** The lever is `renderCompleteCats`' `eliteCat`
  (`u.category === MODE.ELITE`): `ELITE_REWARDS` is a reward **track**, not a grade, so a numeral
  over its generic prestige emblem read as a claim about a grade it doesn't represent. The same
  `badgeFam` decides the badge at BOTH sites the icon appears (row box via `emblemNumber`, tooltip
  via `eliteTipIconHtml(url, level, fam, badgeFam)`) so family resolution has one truth.
- **A real row holds AT MOST 4 boxes.** Field Mods and Skill Tree are mutually exclusive (a tier-XI
  vehicle reads field mods 0/0), so the 5-entry `FAKE_CATS` dev preview is an **impossible state** —
  don't tune layout for five boxes.

### Icon-family size normalization — use a background-size PERCENTAGE
Two icon families share one box in this row, and they fill their canvases very differently
(alpha bounding boxes measured off the packed art): the `hangar/vehicleMenu/large/*` white line-art
PNGs span only **0.50-0.56** of their 64x64 (research 32x17, fieldModification 35x19, vehSkillTree
36x26), while all 21 `prestige/emblem/72x72/**` emblems fill **0.93-0.96** of 72x72 — a ~1.8x
linear / ~4x AREA mismatch at a shared `background-size: contain`. Fix: per-family
`background-size` **percentages** — `.wg-cat-fam-white` 170% (row box 158%, `wg-cat-m-skill_tree`
128% since its line art has the widest fill), `.wg-cat-fam-emblem` 88%. Blowing white past 100%
crops its transparent margin (all three glyphs are canvas-centred, so a centred crop keeps them
whole) and lands it at 0.85-0.96 of the box; the emblem is held just under `contain` at 0.82-0.84
on purpose — a solid hexagon reads heavier than line art at equal extent.
**Why a percentage and not rem:** it is a RATIO OF THE BOX, so it self-scales into `.wg-large` with
**no restatement** — the one exception to this widget's rem-only + restate-in-`.wg-large` rule
(`WGModResearch.css` ~1427-1451, 1503-1515). Note these rules tie on specificity with
`.wg-tip-icon`/`.wg-cat-done-ico`, so **source order decides** — family rules must come after, and
the skill-tree trim last.

### The canonical elite-badge proportion (digit height = 0.365 x the RENDERED emblem)
The invariant to copy when painting a level number over an emblem in a new host box comes from the
shipped ELITE header badge (`#wgmod-root.wg-elite .wg-cat-icon`): a 23rem box at
`background-size: contain` carries **4.2 x 8.4rem** digits and a **3rem "1"** — digit height
**0.3652** of the emblem's extent, width exactly half the height, `"1"` **0.1304**. Its `.wg-large`
restatement (34.5rem box, 6.3 x 12.6, 4.5) holds the identical ratio, which is what makes it the
invariant rather than a one-off.
**THE TRAP: apply it to the RENDERED extent, not the box.** Where the family normalization above
renders the emblem at 88%, the ratio applies to `0.88 x box` → digit height = **0.3214 x box**. A
box-based calculation comes out visibly too big; the two live hosts also inherit unscoped rules
sized for a different box, which is the other half of the error:
- tooltip icon, 32rem box → emblem 28.16 → **5.15 x 10.3rem**, `"1"` 3.7rem (left alone it inherits
  `.wg-tip-icon-num`'s 8.125 x 16.25, sized for the 55rem grade-tick box — **~58% too big**), and
  `top: 0` drops that rule's 2rem centring nudge.
- row box, 30rem `.wg-chip` → emblem 26.4 → **4.8 x 9.6rem**, `"1"` 3.4rem (left alone it inherits
  the tick emblem's 5.5 x 11 — **~15% too big**).
Corollary on the `.wg-chip` reuse: the 30rem (Large 45rem) chip box is **dimensionally identical to
the below-bar tick emblem**, which is why `emblemNumber` drops into a `.wg-cat-done-ico` with no new
*box* geometry — but the 88% normalization still forces a digit-size rule **plus** its `.wg-large`
1.5x restatement (`WGModResearch.css` ~1517-1528, ~1807-1817). Dimensional identity buys the box,
not the digits.

### `FORCE_COMPLETE` — the dev flag, and why it needs `FAKE_CATS`
`const FORCE_COMPLETE = false;` (`WGModResearch.js:37`, **must stay false in shipped builds** —
same hand-flipped convention as `_compat._DEBUG` on the Python side) forces the COMPLETE render
path on EVERY vehicle, so the mode can be inspected without owning a fully-progressed tank (they
are rare by construction — see the handoff memory).
The flag alone previews only the bar GEOMETRY, and needs three companions because a
not-genuinely-complete vehicle carries contradicting real data:
- a fake **0..1 filled scale** (`sMin/sMax/fv`), else the vehicle's own real scale + ticks draw a
  partial bar;
- **`FAKE_CATS`** — `availUpgrades` is EMPTY outside skill-tree mode (only the real COMPLETE model
  populates it), so the row would render zero boxes and hide itself. Only `category` +
  `xpRequired` are read. Its figures are REAL magnitudes sourced from the client's own XML (each
  category's total differs by an order of magnitude in-game, so five similar numbers would
  misrepresent the readout) — see the inline comment block for the provenance of each;
- **`FAKE_CATS_TOTAL`** overriding `PROGRESS_CUR` (and `PROGRESS_REQ = 0`), else the header's
  upper-right figure keeps the real mode's value and contradicts the tooltips;
- **`FAKE_ELITE_MAX_LEVEL = 350`** (the EU 2.3 cap) for the badge, else a non-complete vehicle
  pushes its own lower `eliteMaxLevel` and understates it.

## Skill-tree "next skills" chain — chip connectors
**Visually confirmed in-client 2026-08-15 (user "LGTM")** — every finding below (mask tint,
two-color state model, ring-inset connectors, fan-out column, below-node hover) is shipped
render behavior, not a plan.
- **The existing COMPLETE-mode connector doesn't fit.** The field-mod tooltip connector
  (`completeHexRowHtml`, `.wg-tick-stem`/`.wg-tip-item-stem`) is a VERTICAL, single-stem-per-row,
  filled-`<div>` primitive with NO branching — it cannot draw a two-parent fork, so the
  skill-tree next-chain needed new markup rather than reusing it.
- **New pattern: a HORIZONTAL in-flow flex connector, `.wg-chip-link`** — a filled `16rem x 2rem`
  div (`rgba(178,175,171,0.45)`, drop-shadow; `.wg-large` restatement `24rem x 3rem`). Simpler
  than the absolutely-positioned `.wg-tick-stem` because `.wg-next` is already `display:flex;
  align-items:center`, so the connector just drops inline between chips.
- **Mask tint CONFIRMED WORKING — supersedes any earlier "perk art can't be recolored" note.**
  The locked next-chip icon renders as a flat gray silhouette via `-webkit-mask-image`/
  `mask-image` (set to the perk-art URL, same as the color icon) + `background-color: #8C8C7E`
  on `#wgmod-root .wg-chip-locked .wg-chip-ico`, with `mask-repeat:no-repeat;
  mask-position:center; mask-size:contain`. In JS, `fillChipGlyph(box, iconUrl, masked)` sets
  `mask-image` instead of `background-image` when `masked` is truthy; `buildNextChip` passes
  `true`. So CSS `mask` DOES render in this Coherent build — there was **no precedent either
  way** before this (the earlier `grayscale()`-doesn't-render finding was about a filter, not a
  mask, and doesn't generalize to "recoloring is impossible"). A commented `filter:
  brightness(0.45); opacity:0.75` dimming fallback sits below the mask rule in source, unused.
- **Two-color state model** — the chip background is identical in both states; state reads only
  via color. Available = gold `#FFDD99` ring (icon art stays full-color); next/locked = gray
  `#8C8C7E` on the ring + the icon silhouette + the connectors. Ring/border thickness is `1rem`
  (Large `1.5rem`), matching WG's own researched-node ring treatment.
- **Ring-inset connector rule — every connector needs negative margins to reach the ring.** The
  ring sits ~`2rem` inside the `30rem` `.wg-chip` box (minor ring `26rem`; Large `3rem` inside
  `45rem`), so a connector drawn edge-to-edge of the box would visibly gap from the ring on both
  ends. Fix on both axes: horizontal `.wg-chip-link` gets `margin-left:-10rem;
  margin-right:-2rem` (Large `-15rem`/`-3rem`); vertical `.wg-chip-link-down` gets
  `margin-top:-2rem; margin-bottom:-2rem` (Large `-3rem`). A diamond/major chip has only ~`1rem`
  inset, so its connector may tuck ~`1rem` under the disc edge — accepted as-is, don't chase it
  further.
- **Fan-out column (one available node, two locked successors).** One successor renders to the
  RIGHT via the horizontal `.wg-chip-link`; the second renders BELOW, inside a `.wg-chip-col`
  (a flex column: parent chip → vertical `.wg-chip-link-down` → below chip). Left alone, the
  taller column re-centers the whole `.wg-next` row vertically. Fix: `.wg-next` uses
  `align-items:flex-start` (not `center`) plus a compensating `margin-top:14rem` (Large
  `21rem`) on the thin horizontal `.wg-chip-link` so its row still sits on the same centerline
  as the rest of the fan-out.
- **Fan-out ceiling raised to 3 (`fan3`, commit 094ac7d, visually confirmed in-client) — a
  T-branch.** One available parent with THREE locked successors: two render inline either side
  of the parent (left/right `.wg-chip-link`s) and the third below via `.wg-chip-col`/
  `.wg-chip-link-down`, reusing `appendAvailColumn` for the parent+below cell — no new CSS.
  Fires only when `queue.length === 3`, every entry is `kind === "single"`, and the parent slot
  is free (`!appended[i]`), mirroring the 2-child `fanOut` guard; 4+ children or any tangled/
  shared-parent case still falls back to the single-connector escape hatch.
  **Gotcha (unresolved, re-check per vehicle):** the resolver's `getNextStepIDs` queue order
  does NOT match the Upgrades window's above→right→below reading order. `fan3`'s slot mapping
  (`queue[2]`→left, `queue[0]`→below, `queue[1]`→right) was FITTED to one vehicle's observed
  in-client layout, not derived from a stable key — no known sort key reproduces the window's
  order from resolver data. A different 3-child vehicle may render its three children in the
  wrong slots; verify in-client before trusting a new one.
- **`.wg-hot` coverage assumption — below-node content needs its own hover hookup.** The single
  transparent hit-test overlay (`pointer-events:auto`, hit-tests chips via a live
  `getBoundingClientRect`) only extends ~`39rem` below the bar, sized for ONE horizontal chip
  row. The fan-out's below-node chip sits ~`76rem` down, outside that band, so it never gets a
  `mousemove` and never hovers. Fix pattern used here: re-enable `pointer-events:auto` on that
  one chip specifically (`.wg-chip-col-hot`) with its own `mouseenter`/`mouseleave` routed into
  the existing `setActiveChip`, rather than growing `.wg-hot` itself (which would punch a dead
  zone over the hangar UI below the bar).
- **Two-parent placement (`<>-[]-<>`)**: when both of a next chip's parents resolve to adjacent
  available-chip indices, `renderNextAvailable` (`WGModResearch.js`) emits
  parentA-link-nextchip-link-parentB. Tangled / non-adjacent / 3+-parent cases fall back to a
  single connector off the first parent (ponytail-commented in the source; an SVG-overlay
  upgrade path is noted there for a real multi-parent fork if ever needed).
- `renderNextAvailable` owns this whole render; the rebuild-skip signature `upgradesSig` now
  folds `data.nextUpgrades` too, so a next-chain-only change still triggers a chip rebuild.

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

### Getting WG `{tag}` markup through as styled HTML — the sentinel handoff
The general recipe (control chars, not markup): **Python replaces the markup with sentinel
control chars, JS substitutes them into spans AFTER escaping.** Never before escaping — the
model text is game-supplied, so injecting spans first and escaping second is an injection hole,
and escaping first then re-writing raw markup can't work because the escaper eats it. Live case:
`{colorTagOpen}…{colorTagClose}` (the highlighted figure, sometimes figure + unit) →
`format.mark_color_tags` → `HL_OPEN`/`HL_CLOSE` → JS `escapeHl()` (~535) emits
`.wg-tip-hl` / `.wg-tip-tok` spans; unpaired/stray sentinels are DROPPED so a malformed template
degrades to plain text instead of leaking a control char or a half-open span.
**Claimed control chars — pick a fresh one for any new markup:** `\x1f` (buff-record field sep),
`\t` (variant sep), `\n` (line sep), `\x02`/`\x03` (`HL_OPEN`/`HL_CLOSE`).

### Coherent inline flow is unusable — the per-word flex recipe
This supersedes/extends the "Coherent stacks bare inline spans" note above and in
`WGModResearch.css`, which stops one level too early. Full picture, in the order it bites:
1. A bare span carrying only `color` gets **blockified** — line breaks BEFORE and AFTER it.
2. `display:inline` does **not** rescue it. Don't retry.
3. A wrapping flex row on the CONTAINER is **also not enough**: every flex item is block-level,
   so nothing can sit beside a text item's LAST line. With one item per RUN the highlight is
   pushed to its own line exactly when the preceding text happens to fill the row — which
   presents as the maddening "sometimes it wraps, sometimes it doesn't".
4. **The working recipe: one flex item per WORD**, each token keeping its own trailing space
   INSIDE its span, with `white-space: pre-wrap` on the container (`.wg-tip-effect`:
   `display:flex; flex-wrap:wrap; white-space:pre-wrap`; tokenizer `HL_TOKEN_RE = /\S+\s*/g`).
   Per-word items make flex line-breaking *be* word wrapping. Do NOT substitute a `column-gap`
   em fudge for the in-span space — it drifts between Default and Large scale.
Supporting evidence worth keeping: across all **514** production `_dist` CSS files the client
uses `display:inline-block` **0** times, `inline-flex` **0** times, `display:inline` **3** times —
and WG's own mid-sentence-highlight component (`FormatText`, `mono/vehicle_hub/lib/lib.css`) is
itself a `display:flex; flex-wrap:wrap; white-space:pre-wrap` row. This is the house pattern.
**Corollary — a shared base class must RESTATE `flex-wrap`/`white-space` on its flex-row
variants.** A buff row carries both `.wg-tip-effect` and `.wg-tip-buff`, so it inherited the
description row's wrapping: `.wg-tip-buff` needs explicit `flex-wrap:nowrap; white-space:normal`,
or `wrap` drops the phrase under the value and `pre-wrap` turns the literal space emitted between
the value and desc spans into a visible extra gap.
*(Propagate the two blocks above to the harness `wotmod:gameface-widget` CSS-gotchas list — they
are generic Coherent behaviour, not mod-specific. Not edited here.)*

### Scoping a rule to ONE tooltip variant — `xpFracHtml`'s `tailHtml`
`xpFracHtml(have, need, iconUrl, vehHave, est, tailHtml)` (`WGModResearch.js:436`) takes an optional
trailing `tailHtml`: when non-empty it both appends that markup INSIDE the headline cost row AND adds
a `wg-tip-xp-tail` modifier class to the row (`:447-449`). That modifier is the hook for styling the
cost row of ONE tooltip type without touching the four other call sites (tech-tree/module, field-mod,
skill-tree chips, elite grade band) — they pass no tail, so their markup and computed style stay
byte-identical. This is the house answer to "scope a rule to one tooltip variant": an explicit
JS-applied class, never `:has()`/`:not()` (both documented unreliable here). Live use: hanging the
elite-level badge on the ELITE_REWARDS reward tooltip, with `min-width` (200/300rem) reserving room
and `padding-right` (32/48rem) keeping the in-flow text from sliding under the out-of-flow badge
(`WGModResearch.css:1850-1870`).

### Absolute-position centering — only an explicit `top` moves the box
Vertical centering via `top: 0; bottom: N; margin-top: auto; margin-bottom: auto` on a definite-height
absolutely positioned box is **silently ignored** by Coherent: the engine resolves `top`, treats the
auto margins as `0`, and ignores `bottom` outright. Confirmed the hard way — four successive `bottom`
values (2 → 4 → 6 → 26rem) moved the element **zero pixels** in-client, where the spec says the box
should rise by `bottom/2` independent of container height. A plain explicit `top` IS honoured; use
that (a negative `top` for an upward offset). Recorded in-file with a "don't reach for this idiom"
warning at `.wg-tip-xp-tail .wg-tip-icon-elite` (`WGModResearch.css` ~1876-1888).
**Debugging lesson, because it cost four rounds:** when an in-client observation says "nothing moved",
believe it over the spec-derived reasoning on the FIRST null result. This engine's layout is a subset
of CSS, so "it should work per the spec" is not evidence.
*(Generic Coherent behaviour — propagate to the harness `wotmod:gameface-widget` CSS-gotchas list
alongside "box-shadow needs a fill" / "transform needs explicit dims" / ":not() unreliable".
Propagated — the harness list now carries a terse version of this entry.)*

## Done markers
A tick/chip with `t.done`/`u.done` renders the green-check treatment (`wg-done`, `doneGlyph()` /
`doneBadge()`). Done ticks ride the bar's LEFT EDGE (`leftPct=0`). Tooltip shows a credits price
footer when `price` is non-zero (`creditsHtml`, `CREDITS_ICON`). Clicking a done marker opens the
native screen: `CMD.OPEN_FIELD_MODS` for field-mod ticks, `CMD.OPEN_RESEARCH` otherwise; a done
chip fires `CMD.OPEN_SKILL_TREE`.

## Header mode switch (`.wg-switch`)
When a vehicle qualifies for ≥2 bar modes, Python pushes the ordered `availModes` (comma-joined);
the widget shows an ALTERNATIVE mode's title dimmed beside the current heading, click swaps the bar
to it (`selectMode`, persisted per-vehicle). `modeTitle(mode)`, `switchHit(el,x,y)` (live-rect hit-test),
`setSwitchHot(el,hot)`, `renderModeSwitch(root,data)`/`hideSwitch(root)`. The title is **rendered
only** — it lives in the header, which the root's `pointer-events:none` covers.
- **The alternative is top-priority-other, NOT a forward cycle.** `renderModeSwitch`
  (`WGModResearch.js:1513`) picks `const target = idx === 0 ? avail[1] : avail[0];` — i.e. the
  highest-priority available mode other than the current one, since `avail` is priority-ordered by
  Python `builder._BUILDERS`. With exactly 2 modes this is a plain A↔B toggle. **With 3+ modes only
  the top two are click-reachable** — e.g. `elite` sitting behind both `field_mods` and
  `potential_tier_xi` can never be reached from the switch. Deliberate, user-approved tradeoff
  (predictable two-way toggle beats a cycle that walks you through modes you didn't want); if a
  third mode must become reachable, that needs a real picker, not a tweak here.
- **This is the ONLY mode-selection logic living outside Python** — everything else about mode
  choice (`availModes` ordering, `selectMode`, `modeOverrides`) is Python and covered by pytest.
  The target pick above is JS, so **the Python-only suite cannot catch a regression in it**; verify
  it in-client (switch a vehicle that qualifies for 3+ modes and check the dimmed title).
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
- **The wire is mode-blind by design — `applyPosition` never sees "Onslaught".** Python picks
  which stored position (plain-garage vs Onslaught/Comp7) to send; the JS field is always the
  generic `data.posX`/`data.posY`/`posW`/`posH`. The Python setting name `onslaughtPosX` shows up
  only in a JS comment and is stripped by the minifier, so grepping the packaged JS for it is NOT
  a valid presence check for the per-garage-position feature — check `is_onslaught_garage()` +
  the bridge branch instead (gpb-architecture → Onslaught garage).
