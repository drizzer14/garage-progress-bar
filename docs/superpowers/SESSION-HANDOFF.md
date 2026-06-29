# Session Handoff — Research-Progress Bar (Phase 2, in-game working)

> **RESUME NOTE (session reopened after accidental close):** two commits landed
> after the body of this doc was written and the client closed before they were
> deployed:
> - `cb34f10` — **elite tick-state contrast reworked off grayscale** (addresses
>   OPEN #1 below: brightness/opacity/drop-shadow instead of `grayscale()`, which
>   the owner reported doesn't render). **CSS-only.**
> - `dc004a3` — **hide the bar outside the plain garage** (ammo/tank-setup overlay).
>   **Python (`gameface_bridge.py`, `mod_wgmod.py`) + JS.**
>
> **Now redeployed:** rebuilt + deployed the fresh `.wotmod` (2026-06-29 19:11) so
> both commits' Python is live. 54 pytest green, working tree clean, `main` 2 ahead
> of origin (unpushed). **PENDING: live visual sign-off** of (1) the new tick-state
> contrast and (2) the garage-only visibility — launch the client and verify. The
> skill-tree mode still can't be seen (owner owns no tier-XI). The OPEN/REMAINING
> sections below are otherwise current.

_Updated 2026-06-29 (tier-XI skill-tree DEPLOY+VERIFY session). Read tools/dev/README.md
for the dev loop. **THIS SESSION deployed the prior session's `Mode.SKILL_TREE`, REPL-
verified it live, found+fixed a DAG-dedup bug, and reframed the bar to a cumulative
"% upgraded" readout** (owner directive). Committed at `ce86b90`. See "## Tier-XI
skill-tree mode" below._

**State at handoff: SKILL_TREE code complete + LIVE-VERIFIED, committed `ce86b90`**
(main, unpushed; 19 ahead) — 54 pytest green, 2.7-compiles clean.
- **Live REPL verification (EU 2.3) caught a bug static review missed:**
  `iterOrderedSteps()` visits a node ONCE PER incoming parent edge (the skill tree is a
  **DAG**, not a pure tree). Hirschkaefer yields **32 steps for 26 unique nodes**, which
  inflated both the cost (405000 vs the true 325000) and the N/M counter (32 vs 26). Fix:
  `_read_skill_tree` dedupes by `stepID`. Cross-checked live: unique stepIDs ==
  `getRawTree().steps` == 26.
- **Reframed to a monotonic "% upgraded" bar** (owner picked this over remaining-cost):
  axis = the FIXED full-upgrade cost (sum of all priced nodes), fill = cumulative XP
  already invested (sum of received node prices), single segment like the elite modes.
  Snapshot fields `skilltree_remaining_xp` → `skilltree_total_xp` + `skilltree_spent_xp`;
  resolver falls through to ELITE/COMPLETE once `done >= total`. **JS unchanged** (the
  existing fill_vehicle/fill_free + N/M counter path fits).
- **Decompiled-source assumptions re-confirmed live:** `getType()` returns a bare string
  (`'common'`/`'major'`/`'special'`/`'final'`; no `'ghost'` seen but type is definitively
  str so the skip is valid); skill-tree nodes only cost `xp`
  (`ALLOWED_CURRENCIES_FOR_TREE_STEP={'xp'}`); ghost/zero-price nodes skipped.
- **DEPLOY STATE:** the package deployed this session is still the PRE-FIX `f45d3fb` build
  (the running client has the buggy 3-tuple `_read_skill_tree`). The fix `ce86b90` is NOT
  yet deployed. Redeploying gains no visible behavior right now — **the owner has 0 owned
  tier-XI vehicles** (verified: 0 owned, none partial in the items cache), so no skill-tree
  tank is selectable and the bar can't render in normal play. So the `spent_xp>0`/`done>0`
  path is **unit-tested only**, and **visual sign-off stays deferred** until the owner
  acquires/upgrades a tier-XI. Deploy `ce86b90` at the next natural client restart (Python
  change → close client, `deploy_wotmod.py`, `sync_gameface`, relaunch).

**THE TRANSLUCENCY BUG (root cause, now fixed — KEY LESSON):** the owner's
long-standing "badges look translucent even when achieved" was NOT the asset. The
elite tick's container `.wg-elite-tick` (the `mark`) had `opacity: 0.65` (intended
only to keep the thin tick LINE subtle). **CSS opacity on a parent establishes a
stacking context that CAPS the whole subtree** — so the badge child could never
exceed 65% opacity no matter its own `opacity: 1`. Every elite badge (chevron AND
emblem) rendered at 0.65 → translucent; this is also why last session's 13×
`stackedBg` chevron stacking never looked fully solid. Fix: keep the tick line
subtle via a translucent **background color** `rgba(178,175,171,0.65)` and set the
mark's own `opacity: 1`. (Lesson: never use element `opacity` on an ancestor of art
you want opaque — use rgba/background alpha instead.)

**ALSO this session:** measured the prestige emblem PNGs — the **hexagon `emblem`
art is SOLID** (~245/255 mean alpha over the shape, both 48x48 and 72x72; verified by
decoding + viewing the PNGs). The prior "emblems are translucent-by-design / mesh
interior" note was a MISDIAGNOSIS — the genuinely translucent art is the *chevron
`tab`* set (~76/255, 1% opaque), which is why only IT needed stacking. So the emblem
is drawn ONCE, no stacking.

**OPEN (owner-set, NEXT):**
1. **Tick STATE MACHINE (owner will revisit, deferred by owner).** Owner reports
   **`grayscale()` desaturation "doesn't work — looks perfectly normal"** in their
   client (contradicts the old handoff claim that grayscale renders — TRUST THE LIVE
   OBSERVATION). So the achieved/next/upcoming/locked contrast needs reworking with
   levers that DO render: **brightness + opacity** (both confirmed) and light/dark
   `drop-shadow` glows. Don't rely on grayscale. (The stale "grayscale confirmed to
   render" comment in WGModResearch.css is now suspect.)
2. **TIER-XI UPGRADES ("vehicle skill tree") progression** — the longstanding next
   feature (research pre-collected in "Tier-XI upgrades"; owner can't visually verify
   yet — develop vs decompiled source + REPL, defer sign-off)._

## Tier-XI skill-tree mode (THIS SESSION — code complete, not yet deployed)
Tier-XI vehicles are reached by **upgrading** a tier-X via a branching **vehicle
skill tree** (post-progression tree id ≥ `VEH_SKILL_TREE_ID_OFFSET`=10000), NOT the
linear field-mod ladder. They previously rendered as a garbled/empty FIELD_MODS bar
because `_read_post_progression` assumes leveled steps. New `Mode.SKILL_TREE` fixes
that. **Owner directive: show an XP readout, NO per-node detail** (owner picked no
option in the framing question, noting "xp readout, no need to keep per-node detail"
— so the rich per-node-tick option was dropped).

**What it does (current, reframed `ce86b90`):** the 2-D tree is projected to the bar as
an **aggregate, monotonic "% upgraded"** readout — axis = the **FIXED full-upgrade cost**
(deduped sum of ALL priced nodes), fill = **cumulative XP already invested** (deduped sum
of RECEIVED node prices), a **single segment** (rides the vehicle slot, free slot empty,
like the elite modes), header = **"Vehicle Upgrades N/M"** node counter + the existing
Total-XP readout (which now shows the invested figure). **No ticks** (single fill bar).
The fill only grows as nodes are unlocked. Once fully upgraded (`done >= total`),
`skilltree.resolve()` returns None and the bar falls through to ELITE_REWARDS → ELITE →
COMPLETE (a skill-tree vehicle still has prestige afterward). _(The original `f45d3fb`
used a remaining-cost framing — axis=remaining, fill=banked wallet XP — superseded.)_

**Builder precedence:** TECH_TREE (modules unresearched) → **SKILL_TREE** (if
`is_skill_tree` and remaining XP > 0) → FIELD_MODS (linear; non-skill-tree elites) →
ELITE_REWARDS → ELITE → COMPLETE. SKILL_TREE replaces FIELD_MODS only for skill-tree
vehicles.

**Code (mirrors the ELITE structure):**
- `domain/types.py`: `Mode.SKILL_TREE`; snapshot fields `is_skill_tree`,
  `skilltree_total_xp`, `skilltree_spent_xp`, `skilltree_done`, `skilltree_total`. The
  node counter REUSES the model's existing `fieldmods_done/total` fields (so no new
  bridge/JS plumbing — the bridge already pushes those + `mode`).
- `domain/resolvers/skilltree.py` (pure): `resolve(snapshot)` → dict
  `{scale_min, scale_max=total_xp, fill=spent_xp, done, total}`, or **None** when not a
  skill-tree vehicle / no priced nodes / `done >= total` (fully upgraded).
- `domain/builder.py`: SKILL_TREE branch after TECH_TREE, before FIELD_MODS; maps
  `st["fill"]` → `fill_vehicle`, `fill_free=0` (single segment).
- `adapter/engine_adapter.py`: `_is_skill_tree(veh)` =
  `veh.postProgression.isVehSkillTree()` (guarded); `_read_skill_tree(veh)` iterates
  `iterOrderedSteps()`, **dedupes by `stepID`** (DAG — see header), skips
  `getType()=="ghost"` and zero-price nodes, returns
  `(total_xp=Σ all prices, spent_xp=Σ received prices, done, total)`;
  `_read_post_progression` early-returns empties for skill-tree vehicles so FIELD_MODS
  never triggers. New fields wired into BOTH the read site AND the `VehicleSnapshot(...)`
  call (the `elite_level_xp` KeyError trap).
- `WGModResearch.js`: `skill_tree` → label "Vehicle Upgrades", `CAT_ICON` reuses the
  fieldModification glyph (swap if a dedicated post-progression icon is wanted),
  `root.className="wg-skill"` hook. Empty `ticks[]` → the existing tick loop draws
  nothing. No CSS change required (default combat-XP fill tone).
- Tests: `tests/test_resolver_skilltree.py` (5: not-skill-tree, no-priced-nodes,
  fully-upgraded, fixed-total scale/counts, fill=invested) + 5 builder tests (mode,
  priority over field mods, tech-tree still wins, fully-upgraded → ELITE / COMPLETE).
  54 green.

**Verified data shapes (decompiled EU `C:\Users\…\wot-eu`, branch 2.3):** detect via
`veh.postProgression.isVehSkillTree()`. Steps from `iterOrderedSteps()` =
`PostProgressionStepItem`: `stepID`, `getPrice().xp`, `isReceived()`, `getType()`
(`major/special/final/common/ghost`), `getParentStepIDs()`, `action`. Whole-tree:
`len(getState().unlocks)` / `len(getRawTree().steps)` (we instead count via the
iterator), `getCompletion()`→`EMPTY/PARTIAL/FULL`, `getCheapestAvailablePerk(veh)`.

**REMAINING (next session):**
1. **Deploy `ce86b90`** at the next client restart — the package on disk is still the
   pre-fix `f45d3fb`. Python change → close client, `deploy_wotmod.py` (Py2.7),
   `sync_gameface`, relaunch. (No urgency: no owned tier-XI tank is selectable, so the
   bar can't render yet.) Confirm the `python.log` `push mode=skill_tree …` line once a
   skill-tree vehicle is selectable.
2. **`spent_xp>0` / `done>0` path is unit-tested only** — there is no owned or partially-
   upgraded skill-tree vehicle in the items cache (verified: 0 owned). When the owner
   eventually owns/partially-upgrades a tier-XI, REPL-dump
   `engine_adapter._read_skill_tree(veh)` and confirm `spent_xp` == Σ received prices and
   the bar fills proportionally.
3. **Visual sign-off deferred** — owner has no tier-XI tank.
4. Pick a fill tone / dedicated header icon for the upgrade bar if the default reads
   wrong once seen live (all hot-reloadable JS/CSS; `wg-skill` class is the hook).

## Bug-fix session (deployed; fixes 1-3 owner-CONFIRMED in-game)
Diverted from tier-XI to fix owner-reported bugs.
- **Elite vehicle with research left showed Field Mods, not Research (CONFIRMED
  fixed — "Leopard 1" case).** `builder.build_model` gated TECH_TREE on
  `not snapshot.is_elite`, but `veh.isElite` is merely account `eliteVehicles`
  membership and goes True while modules are still unresearched (only `isFullyElite`
  = all `unlocksDescrs` researched means nothing's left — `Vehicle.py:304-305,660-665`).
  Fix: build_model now shows TECH_TREE whenever `techtree.resolve(snapshot)` returns
  any (remaining-only) ticks, regardless of is_elite — research wins over field mods.
  Regression test `test_elite_with_remaining_unlocks_is_tech_tree`.
- **Research-state bar never updated (the big one).** Selecting a non-elite tank
  left the bar showing the previous vehicle. Root cause found via the client log:
  `engine_adapter.build_snapshot()` raised **`KeyError('elite_level_xp')`** and
  `push()` swallowed it, so nothing was written. `_prestige_defaults()` was missing
  the `elite_level_xp` key; every early-return path in `_read_prestige` returns that
  dict, and a non-elite vehicle takes the `hasVehiclePrestige(checkElite=True)
  → False → return out` path. Elite vehicles hit the success path (which sets the
  key), so only research tanks broke. **Exactly the "wire a new field into BOTH the
  defaults dict AND the `VehicleSnapshot(...)` call" trap noted in the Elite session
  — the defaults dict was the half that got missed.** Fix: added `elite_level_xp={}`
  to `_prestige_defaults()` + made the constructor read it via
  `prestige.get("elite_level_xp", {})` so a future missing key degrades to a
  graceful render instead of blanking the bar. (Investigation ruled OUT a
  `g_currentVehicle.onChanged` timing/staleness cause: onChanged fires reliably
  ~200ms post-switch with fresh data — verified in `currentvehicle.py`.)
- **Elite combat-XP icon too small.** The elite modes' combat star
  (`xpIcon_23x22.png`) has more transparent padding than the Total-XP glyph, so
  `background-size:contain` in the shared 16rem `.wg-xp-ico` box rendered it smaller.
  Fix: `#wgmod-root.wg-elite .wg-xp-ico { background-size: 130%; }` (tune live).
- **Elite grade-emblem state/transparency look — NOT FIXED (next focus).** See the
  dedicated section below.
- **Diagnosis technique worth reusing:** the mod logs `push mode=… ticks=…` and
  `onChanged -> refresh ok=…` to `python.log`. A standalone `onChanged -> refresh
  ok=True` with NO preceding `push mode=…` means `build_snapshot` returned None/raised
  (push bailed). Grepping the live log pinpointed the crash without the REPL. Also
  the live REPL (`tools/dev/repl_client.py --file …`; build a `RESULT` string,
  `execfile` a script) dumps the live model's per-tick icon/state — used it to
  confirm exactly which emblem URLs/states were being produced.

## Carousel-tooltip hexagon emblems (THIS SESSION — owner-verified in-game)
Owner directive: make the ELITE grade ticks look **exactly like the prestige badge
in the hangar carousel vehicle tooltip**, and **not translucent when achieved**. The
chevron-badge detour from last session is fully retired. All JS/CSS; data was already
on the tick (no Python change). The translucency was the `.wg-elite-tick` opacity-cap
bug above (NOT the asset).

**Ground truth (verified by extracting the game's own bundle from
`res/packages/gui-part*.pkg`):** the carousel tooltip badge is the game component
`PrestigeProgressSymbol` (`gui/gameface/_dist/production/lobby/prestige/
sharedComponents/PrestigeProgressSymbol/PrestigeProgressSymbol.css`). It is dead
simple — a single hexagon-emblem PNG as `background: no-repeat center / contain`,
**no backing, no glow, no `mix-blend-mode`, no stacking.** The level number is the
sibling `PrestigeProgressLabel`: a row of grade-colored **emblemFont** digit-glyph
PNGs. (Agent guesswork about a `mix-blend-mode: screen` solidity trick was WRONG —
that was the full-screen `elite_window` celebration popup with animated rays, a
different context.)

**What the bar does now (matches the tooltip):**
- grade tick → the solid hexagon emblem `img://gui/maps/icons/prestige/emblem/72x72/
  <family>/<sub>.png` (already on the tick as `t.icon` from `elite.py` `_EMBLEM_BASE`),
  drawn ONCE via `.wg-tick-emblem` `background-image` (no `stackedBg`).
- level number → `emblemNumber(level, family)` builds a flex row of
  **`.wg-emblem-digit`** divs, each backed by `img://gui/maps/icons/prestige/
  emblemFont/16x33/<fam>/<digit>.png` (the game's own grade-colored digit glyphs).
  Family map: `emblemFontFamily()` sends **enamel → gold** (emblemFont ships
  iron/bronze/gold/silver only — no enamel; matches the old amber tint). Digit box
  `5.5rem × 11rem`, the `"1"` glyph narrowed to `4rem` (`.wg-emblem-digit-one`,
  mirrors the game's `letter__s1`). A drop-shadow keeps the soft glyph edges legible.
- **MAX ("prestige")** tick → `…/emblem/72x72/prestige.png` (gold hexagon), shown
  numberless — its icon has no grade family, so `gradeFamily()` returns "" and
  `emblemNumber` is skipped. Matches the in-game MAX badge.
- Retired: `tabChevronUrl`, `isPrestigeEmblem`, `PRESTIGE_TAB_URL`, `stackedBg`,
  `BADGE_OPACITY_LAYERS`, and all `.wg-tick-badge*` / `.wg-grade-* .wg-tick-badge-num`
  CSS. `gradeFamily()` + `GRADE_FAMILIES` are KEPT (now used for the emblemFont
  family + a `wg-grade-<fam>` class hook).

**Dark tech-tree + reward icons "lift off" the dark background (owner request, NO
plates):** the vehicle tech-tree node renders and the tier-XI reward thumbnails are
dark realistic art that blended into the dark area below the bar. **Owner explicitly
rejected backing plates** (rounded `background-color` rects — do NOT add them). Fix =
swap the base DARK `drop-shadow` for a **LIGHT glow that hugs the silhouette**:
`#wgmod-root .wg-cat-vehicle .wg-tick-img { filter: drop-shadow(0 0 2.5rem
rgba(245,240,232,0.85)) drop-shadow(0 1rem 2rem rgba(0,0,0,0.55)); }` and the same on
`.wg-state-upcoming .wg-tick-reward`. Owner CONFIRMED "icons stand out." (Module
glyphs were left alone — flat symbolic icons, and their 96rem-wide box would make a
plate/treatment look like a bar.)

**Owner verdict:** badges now match the tooltip and are solid; digit size tuned down
to match; dark icons stand out. Signed off in-game. Remaining = the tick state
machine (see OPEN #1) and tier-XI.

## Elite emblem look (was UNRESOLVED — chevron-badge approach now in progress)
SUPERSEDED by the battle score-panel CHEVRON BADGE work below; kept for context.
The owner is unhappy with the per-level grade emblems on the ELITE bar: earned
levels "don't change state" / look faded/transparent. **Code is correct** —
`elite.resolve_grade_band` tags each tick `state=achieved/next/upcoming` and JS
applies `wg-state-*`; verified live via REPL. The problem is purely visual.

Dead-ends tried this session (all reverted to a clean baseline — single
`.wg-tick-emblem` bg-image div + number, `.wg-state-*` filters):
- Stronger CSS glow / saturate / brightness, then hard-darken "upcoming". Didn't
  read — the emblem ART brightness (dark bronze vs bright silver) dominated.
- Switched emblem source `48x48` → **`72x72`** (KEPT — higher-res, crisper; URL in
  `elite._EMBLEM_BASE`). Did NOT fix it: the badges have a **translucent mesh
  interior by design**, so they look see-through over the bright hangar at any size.
- A dark "coin" backing behind each emblem — owner: "looks bad".
- A soft dark radial-vignette disk (JS wraps art in `.wg-tick-emblem-art` over a
  `.wg-tick-emblem` disk) — owner: "still shitty". Reverted.
- Tried the skill-tree state set `skillTree/prestige/emblem/{available,current,
  disable}.png` (purpose-built for state) — also translucent white hexagons.
Root finding (decompiled source): there is **NO solid standalone emblem PNG**. All
prestige emblems are translucent overlays; the game makes them look solid via its
own gameface COMPONENT + dark panel context. The battle player panel uses
`gui/impl/gen/view_models/common/battle_player.py` → `PrestigeEmblemModel`
(type+grade only, no image path), rendered by the React component
`res/.../gui/gameface/_dist/production/lobby/prestige/sharedComponents/
PrestigeProgressSymbol/*` (minified). Backing art exists but is layout-scale
(`skillTree/prestige/vanity_bg`, `rays`, `prestige/emblem/emblemGlow.png`).

**NEXT-SESSION leads for "battle score-panel badges":**
1. **Look at the OTHER mod** the owner saw using battle score-panel badges — its
   source will show the exact asset path / compositing it uses. Best starting point.
2. Battle consumers of the emblem: `gui/impl/gen/view_models/views/battle/
   battle_page/player_list_model.py` and `gui/impl/battle/battle_page/tab_view.py`.
3. **`emblemFont/<size>/<grade>/<digit>.png`** (sizes 6x12 … 77x176) — SOLID,
   grade-COLORED digit glyphs (the styled level number). The battle panel may show
   the prestige level as these colored digits rather than the hexagon badge; could
   be the clean "solid" look the owner wants. View them first.
4. If a backing is unavoidable, the owner rejected flat/soft dark disks — so prefer
   a solid asset (emblemFont) or replicating the game component's exact treatment,
   not another home-grown backing.

## Elite System (DONE this session — deployed, owner verifying in-game)
The "EU dropped elite/Paragons" note was WRONG (it conflated EU's Elite Levels
with Lesta's RU "Paragon"). EU 2.3 ships WG's global **Elite Levels** feature
(internal codename **"prestige"**, update 1.22.1): cosmetic per-vehicle 0→350
levels via combat XP after a vehicle is elite. The `COMPLETE` "fully researched"
fallback is now replaced by two new modes (precedence: TECH_TREE → FIELD_MODS →
**ELITE_REWARDS** → **ELITE** → COMPLETE):
- **ELITE** (any elite vehicle with prestige): the CURRENT grade band. Shows the
  current complex grade's sub-grade milestones as the real **team-HP-bar emblems**
  (`img://gui/maps/icons/prestige/emblem/48x48/<family>/<sub>.png`; MAX =
  `…/48x48/prestige.png`), each **overlaid with the elite level it's reached at**
  (the badge art ships numberless; `.wg-tick-emblem-num` renders it), plus ONE
  extra tick for the next grade's first level. Gold fill. Label "Elite System
  {Grade}". Tooltip: **capitalized** title ("Silver 2"/"Prestige") + **cumulative
  combat-XP cost to reach that level** + "Elite Level N".
- **ELITE_REWARDS** (tier-XI vehicles with unearned milestone rewards, shown
  FIRST, then falls back to ELITE once all earned): the tier-exclusive reward
  roadmap. Each milestone tick is the **real reward thumbnail** (style/attachment
  art via `c11nItem.icon`/`.iconUrl` → `img://`), state-treated (earned gold-glow /
  next white-glow / upcoming faded). Fill = **epic-attachment purple `#9160d0`**.
- Both elite modes: single-segment fill; readout = **cumulative combat XP**
  (vehicle XP, no free XP) with the gray combat star
  `img://gui/maps/icons/library/xpIcon_23x22.png` (not the gold total-XP star).
- Code: domain `resolvers/elite.py` (`resolve_grade_band` / `resolve_reward_track`,
  pure, 20 tests) + `Mode.ELITE`/`ELITE_REWARDS` in `builder.py`; adapter
  `engine_adapter._read_prestige`/`_read_elite_grades`/`_read_elite_rewards`/
  `_read_reward_art`/`_read_level_xp` (all best-effort, guarded → COMPLETE
  fallback); bridge VM props (`eliteLevel/Max/Grade/Sub/combatXp`, tick `state`);
  JS `renderElite` + `.wg-tick-emblem`/`.wg-tick-reward` CSS. 43 pytest green;
  2.7-compiles; img:// thumbnails confirmed rendering in-game.
- **APIs (gui.prestige.prestige_helpers, deps auto-inject):** `hasVehiclePrestige
  (cd, checkElite=True)`, `getVehiclePrestige(cd)`→`(level, remainingPts)`,
  `getCurrentProgress(cd,lvl,pts)`→`(curXP,nextXP)` (sentinels (-1,-1)/(1,1)),
  `getSortedGrades(cd)`+`mapGradeIDToUI(markID)`→`(family,sub)`, `getMilestones`/
  `getVehicleAchievedMilestones`, reward bonus via veh_skill_tree `utils
  .getPrestigeBonus`+`PrestigeBonusContext`. XP-cost = cumulative of the prestige
  config's per-vehicle points array (`prestigeConfig.getVehiclePoints(cd)`,
  `points[L-1]`=level cost, `points[0]`=0) via `prestigePointsToXP`.
- **All owner-verified in-game (2026-06-29):** emblems + overlaid level numbers,
  next-grade tick, "Elite System {Grade}" label, capitalized tooltip titles, and
  the **XP-cost numbers are correct** (cross-checked against the game's own
  prestige screen). Reward thumbnails (img://) render. Watch-out fixed mid-session:
  a new snapshot field must be wired into BOTH `_read_prestige`'s out-dict AND the
  `VehicleSnapshot(...)` call in `build_snapshot` — `elite_level_xp` was computed
  but not passed, so all XP read as 0 until the constructor arg was added.

## Tier-XI upgrades ("vehicle skill tree") — NEXT FOCUS (research pre-collected)
Tier-XI vehicles are reached by **upgrading** a tier-X via a branching **vehicle
skill tree** (NOT the linear field-mod ladder our FIELD_MODS mode reads). A
vehicle is `eliteByProgression` (so field-mods/prestige unlock) when its
`typeDescr.postProgressionTree >= VEH_SKILL_TREE_ID_OFFSET` (=10000; see
`items/vehicles.py:2053` and `common/post_progression_common.py:33`). The current
`engine_adapter._read_post_progression` assumes leveled steps (levels 1..8 +
multi-mod pairs) clamped to a tier cap — that model does NOT fit a skill tree, so
tier-XI upgrade vehicles likely render wrong/empty in FIELD_MODS today. Goal: a
dedicated representation of the skill-tree upgrade progress.
- **Data**: same entry `veh.postProgression.iterOrderedSteps()`, but the steps form
  a branching tree. Per-step (see `…/veh_skill_tree/utils.py:fillNodeModel`):
  `step.getPosition()`→(x,y), `step.getType()`→node `Type`
  (major/special/final/common/ghost), `step.action.getImageName()`/`getLocName()`,
  `step.getPrice().xp`, `step.isReceived()`, `step.getNextStepIDs()`,
  `step.action.isFeatureAction()`/`actionID`. Node `Status` =
  researched/selected/default (`…/veh_skill_tree/node_model.py`).
- **Whole-tree state**: `post_progression_common.VehicleState` (unlocks/pairs/
  features; `isResearchedTree(tree)`). Helpers in veh_skill_tree `utils.py`:
  `getFullProgressionState(vehicle)`, `getCheapestAvailablePerk(vehicle)` (walks
  the tree from `getRawTree().rootStep` via `getNextStepIDs`).
- **Design question for next session (clarify w/ owner):** a skill tree is 2-D /
  branching; our bar is a single XP axis. Options: (a) collapse to a linear
  "researched perks / total + XP toward the cheapest next perk" progress; (b) a
  distinct "upgrade %" readout; (c) something else. Pick the bar-friendly framing
  first, then build a new `Mode` + resolver + adapter read, mirroring how
  ELITE/FIELD_MODS are structured.
- **Verification constraint:** owner has no un-upgraded tier-XI tank right now.
  Develop + unit-test the domain logic, introspect a real skill-tree vehicle's
  steps via the REPL (`tools/dev/repl_client.py`, dump `iterOrderedSteps()` shapes)
  to confirm the reads, but the final visual sign-off waits for a suitable tank.

## TL;DR — where we are
The mod **works in-game** on WoT **EU 2.3.0.1**. The Garage bar renders from live
data in all modes (tech-tree / field-mods / "Fully researched"), refreshes on
tank-switch (listener self-heals across the battle-exit cycle — see gotchas), and
now uses **real in-game icons**:
- **tech-tree module ticks** → the generic module-type glyph (chassis/engine/
  tower/gun/radio), **vehicle ticks** → the framed tech-tree-node tank icon.
- **field-mod ticks** → a hexagon with the level **roman numeral** (clip-path).
- **header category icon** (outboard left of the bar) → Research / Field
  Modifications icons from the in-game Vehicle-management menu.
- **field-mod counter** in the header → "FIELD MODIFICATIONS N/M" = researched /
  total field-mod LEVELS, clamped to the tier cap.
- **COMPLETE state** → class+elite badge (e.g. `mediumTank_elite.png`).

Branch `main`, unpushed. Tests green (23, py3), 2.7-compiles clean.

**DONE THIS SESSION (visual polish 2 — all JS/CSS, hot-reloaded, owner-verified
in-game):**
- **Tooltips restyled to the native garage look** (`.wg-tooltip`): the panel is
  the client's own 9-slice frame `img://gui/maps/icons/tooltip/background_with_border.png`
  (border-image, slice 4 fill / 4rem round) + native deep shadow, with a solid
  dark fallback behind it. Layout reordered to **title → XP → divider + variant
  description**, where the `img://gui/maps/icons/tooltip/divider.png` rule + the
  field-mod variant names appear ONLY when options exist. Native type tokens
  (17rem title #ede6d9, 15rem body, currency-tan XP).
- **Unified "Total XP" readout** (replaced the old two-pool combat+free readout):
  one figure = `fillVehicle + fillFree` (vehicle combat XP + global free XP, the
  same sum the research screen's `getVehTotalXP` shows), value then icon, pinned
  so the **icon centers on the bar's right edge**. Icon = the Research screen's
  own Total-XP-row glyph **`img://gui/maps/icons/vehicle_hub/research_purchase/total_experience.png`**
  (found via `gui/impl/gen/resources/images.py` → `_research_purchase.total_experience`;
  NOT a `library/currency` star). The `_elite` sibling exists but its 16x16 art is
  drawn smaller + offset low, so we use the clean base glyph in every mode.
  Counter is comma-separated (`fmtXp(n, ",")`); tooltip XP keeps native spaces.
  Font matches the label/counter: 13rem / 700 / letter-spacing 1rem.
- **Category header icon**: now centered on the bar's **left edge** (was outboard
  −35rem); label group pushed right 14rem to clear it; base icons bumped to 36rem
  (+2); **elite badge shrunk to 30rem** to match proportions; non-elite category
  icons nudged up 1px (`margin-top:-1rem`, elite resets to 0).
- **Ticks**: thinner (base 1rem / affordable 2rem / locked 1.5rem). **Locked**
  ticks made visible (opacity 0.45→0.9, cool gray, dark halo) + locked glyphs
  partially desaturated. **Field-mod hexagons** restyled to the menu look: dark
  fill `#15181a` + thin light-tan border ring (two layered clip-path hexagons,
  inner shrunk via `transform: scale(0.9)`), tan roman numeral.

**Gameface notes learned this session (don't relearn):** `border-image` with an
`img://` URL WORKS (slice/fill/width/round) — used for the native tooltip frame;
keep a solid `background` behind it as a fallback. `transform: scale()` on a
`::before` works (the hex border ring). Small currency/star PNGs have size-variant
art that differs (the 24px elite star loses the split the 48px has) — VIEW the
actual PNG before trusting a path. Flex `margin-left:auto` did NOT right-align in
the header; use `justify-content: space-between` (or absolute positioning) instead.

**DONE THIS SESSION — TOOLTIPS + field-mod names (both verified in-game):**
- Real hover **tooltips** on ticks (name + XP), confirmed working. Implementation
  (all in `WGModResearch.js`/`.css`): a transparent **`.wg-hot` overlay** is the
  ONLY element with `pointer-events:auto` (root stays `none` so it never steals
  hangar drag-to-rotate); it's sized to span the bar AND the glyph strip below,
  so hovering an icon counts. A `mousemove` handler resolves the hovered tick
  (exact element via an `e.target` climb, else nearest-by-`clientX`) and shows a
  `.wg-tooltip` positioned BELOW the icons. See gotchas for the Gameface quirks.
- **Empty field-mod names FIXED** (`engine_adapter._step_label`): the action name
  is a *resource*, not an attribute — `action.getLocNameRes()` returns a wulf
  `DynAccessor` you must CALL to get the int id, then `backport.text(id)`. The old
  `action.locName`/`.name` reads didn't exist → empty.
- **Field-mod tooltips list the two SELECTABLE VARIANTS** of each level's paired
  choice ("A or B"), e.g. VII → *Anti-Reflective Optics Coating / External Vision
  System*. See the field-mods section: each level = a leveled XP step (generic
  base-mod name, repeats across levels) + a free `MultiModsItem` child holding the
  two variants (`action.modifications[*].getLocNameRes()`); `_pair_options()` reads
  them, keyed by the multi-mod's `getParentStepID()`. New plumbing: `Tick.options`
  / `ProgressionStep.options` (domain) → `TickVM.options` (a `\n`-joined string) →
  JS splits + renders.

**STILL-OPEN SIDE ITEM (not next focus):**
- **Tier XI field-mod level cap is UNKNOWN and currently guessed.** `max_level()`
  in `domain/resolvers/fieldmods.py` maps tier≥10→8, so tier **XI also gets 8**,
  which is unverified. Owner has no non-fully-upgraded tier-XI tank to read it live;
  get the real cap from the EU **decompiled** post-progression config (re-clone
  branch `2.3`) or the WoT wiki. Confirmed caps so far: **VI–VII=5, VIII=6, IX=7,
  X=8**.

**CONFIRMED IN-GAME THIS SESSION (were open, now done):**
- ✅ **Elite badge** renders correctly on a fully-maxed tank (COMPLETE state,
  `img://gui/maps/icons/vehicleTypes/md/<class>_elite.png`).
- ✅ **Field-mod counter** reads correctly (N/8 at tier 10, N/5 at tier 6).

## Architecture (as built, EU 2.3)
- **Domain (engine-free, tested):** `wgmod_research/domain` — `VehicleSnapshot` →
  `build_model` → `ResearchProgressModel` with modes `TECH_TREE` / `FIELD_MODS` /
  `COMPLETE`, two-segment fill (`fill_vehicle`, `fill_free`), `ticks[]`. 15 pytest
  tests (`python3 -m pytest -q`).
- **Adapter (`wgmod_research/adapter/engine_adapter.py`):** live client →
  `VehicleSnapshot`. Tech unlocks via `vehicle.getUnlocksDescrs()` →
  `(idx, xpCost, intCD, prereqs)`; module vs vehicle via
  `getTypeOfCompactDescr/GUI_ITEM_TYPE.VEHICLE`; field mods via
  `vehicle.postProgression.iterOrderedSteps()` (`getPrice().xp`, `isReceived()`).
  Uses `dependency.instance(IItemsCache)`. Each read guarded → safe default.
- **Mount (the tricky part):** WoT 2.3 loads only `.wotmod`. OpenWG's JS injector
  (`gui/gameface/js/index.js`) injects a mod's assets only for hangar **sub-views**
  carrying a `ModInjectModel`. So `mod_wgmod.py` patches
  `HangarVehicleParamsPresenter._onLoading` and calls
  `gameface_bridge.attach(host_vm)` →
  `openwg_gameface.gf_mod_inject(host_vm, "WGModResearch", styles=[…], modules=[…])`
  (loads our JS into the hangar document) and
  `host_vm._addViewModelProperty("wgResearch", ResearchVM())` (our data model).
- **Data → JS:** `WGModResearch.js` (ES module) reads the model via
  `ModelObserver("WGModResearch")` → `model.wgResearch` (+ `ticks[]`, elements as
  `item.value.*`) and renders the bar. Updates: `gameface_bridge.push()` writes via
  `rvm.transaction()` and nudges the host sub-view; subscription lives in the bridge
  (`install_vehicle_listener`) with a **strong global ref** (WG `Event` is weak-ref).

### Key files
```
src/res/scripts/client/gui/mods/mod_wgmod.py                 # entry: patch presenter
src/res/scripts/client/wgmod_research/adapter/engine_adapter.py
src/res/scripts/client/wgmod_research/bridge/gameface_bridge.py   # ViewModels + attach/push/refresh/listener
src/res/scripts/client/wgmod_research/domain/{types,builder,resolvers/*}.py
src/res/gui/gameface/mods/drizzer14/WGModResearch/{WGModResearch.js,.css}
build/deploy_wotmod.py        # clean build+deploy (Python 2.7, client CLOSED)
tools/dev/                    # debug REPL server + client + README (NOT shipped)
docs/superpowers/research/decompiled-findings.md   # verified EU symbols
```

## Remaining v1 work
1. **Tier XI field-mod cap** (see TL;DR #1) + **elite-badge visual verify** (#2) +
   **counter confirm** (#3).
2. **Visual polish** — DONE (icons session + the 2026-06-29 restyle; all
   hot-reloadable for further tuning; see the dev loop). The 2026-06-29 restyle
   (commit `9b1c6ac`) made the bar match WoT's own bar visual language, verified
   against the client's `EditableProgress` / `Status` / `VehicleExperience` CSS:
   - **flat fills** (the native bars use a plain `background-color`, NOT a
     gradient — owner rejected the glossy sheen). Vehicle XP now uses its true
     **combat-experience currency color `#dce0e0`** (not the old green); free XP
     stays tan `#ecca9d`; COMPLETE stays `#64ba21` green.
   - **two-tone frame**: a 2rem translucent-black outer border
     (`rgba(0,0,0,0.75)`) + a 1rem inner border. The inner border AND the dense
     segment notches are ONE `::after` overlay, `#888` with
     **`mix-blend-mode: color-burn`** so they burn into the fill colors; the empty
     channel is set to the same `rgba(0,0,0,0.75)` as the outer border, so over
     unfilled zones color-burn collapses the notches/inner-border to black → one
     seamless black frame.
   - **dense notches** via a SINGLE tiled gradient (`background-size: 3rem 100%` +
     `background-repeat: repeat`), the native VehicleExperience period — NOT
     `repeating-linear-gradient` (its per-period rounding drifted). Pattern offset
     by one gap so the first notch isn't glued to the inner border.
   - lighter category title (`#ede6d9`); **drop-shadows** on the header icon and
     tick glyphs; elite badge keeps only its baked-in shadow (filter disabled in
     `.wg-complete`).
   - DONE: locked (prereqs-unmet) tech-tree ticks (gray). Field mods carry no
     prereq info so stay unlocked.
   - DONE: colors. Uses **literal hex** from `research/gameface-design-tokens.md`
     (NOT `var(--color-*)` — Gameface drops the whole declaration on an
     unresolved var, which is what made the bar render black; see gotcha). Tick
     color is state-driven (affordable / locked / idle).
   - DONE: **real in-game icons** (img:// loads in our injected doc). Module &
     vehicle ticks, header category icon, field-mod roman-numeral hexagons, elite
     badge. Icon paths + sizing in the "Icons" section below.
   - DONE: **field-mod level tier cap** + **researched/total counter**.
   - Owner DROPPED the "stable full-scale / completed-base bar" idea; keep the
     remaining-only view. Don't revisit unless re-raised.
   - DONE: real hover **tooltips** (name + XP + field-mod pair variants), via the
     `.wg-hot` overlay + `mousemove` (see TL;DR + gotchas). Empty field-mod names
     also fixed.
   - DONE: general visual polish — two sessions of position/size/styling tuning
     against the live hangar (icons, tooltips, the unified Total-XP readout, tick
     + hexagon restyle). All owner-verified. Further small tweaks are still
     hot-reloadable JS/CSS if raised.
3a. **NEW FEATURE (next focus): elite system progression** — replace the
   `COMPLETE` "Fully researched" fallback with a real elite-progression view. See
   the header note: first define what the elite system is in EU 2.3 (the prior
   "EU dropped Paragons/elite milestones" finding may be stale or may mean a
   different mechanic — verify). This is a domain+adapter change (likely a new
   `Mode` + builder branch + new adapter reads), so Python build+deploy+relaunch,
   plus a new JS render path for that mode.
3. **Finalize packaging & docs** (Task): remove the loose `res_mods` gameface
   overlay before a clean ship verification (it shadows the packaged assets — see
   gotcha); `meta.xml` name/id (consider
   `com.drizzer14.research_progress` / "Research Progress"); declare OpenWG Gameface
   as a required dependency in README; deprecate `build/deploy_dev.py` (loose
   res_mods does not load in 2.3) pointing to `deploy_wotmod.py`; document the debug
   mod; build the distributable.

## Icons & field-mods (this session — verified in-game)
Data flow: `engine_adapter` reads icon URLs + field-mod levels → domain `Tick`
(`icon`, `level`, `category`) and `ResearchProgressModel` (`fieldmods_done/total`,
`vehicle_class`) → `TickVM`/`ResearchVM` → JS renders.

- **Tech-tree tick `category` carries the unlock kind** (`"vehicle"` | `"module"`),
  not a generic `"techtree"`. JS adds `wg-cat-<category>`.
- **Icon URLs (img://), read off the live item objects:**
  - module unlock → `item.icon` = generic module-type glyph,
    `img://gui/maps/icons/modules/{chassis,engine,tower,gun,radio}.png` (48×48).
  - vehicle unlock → `item.icon` = framed tech-tree-node icon (~160×100). **NOT
    `iconSmall`** (124×31 carousel contour — cropped edge-to-edge, looks "cut off").
  - header category → `img://gui/maps/icons/hangar/vehicleMenu/large/{research,
    fieldModification}.png` (64×64), keyed by mode in JS (`CAT_ICON`).
  - elite badge (COMPLETE) → `img://gui/maps/icons/vehicleTypes/md/<class>_elite.png`
    — pre-composed class+elite art; map `veh.type` '-'→'_' (`AT-SPG`→`AT_SPG`).
- **Render icons as `background-image` + `background-size:contain`** on a div, NOT
  `<img>` — Gameface ignores `object-fit` and CLIPS an `<img>` to its box (and
  `width:auto` collapses to 0). background-size:contain scales aspect-correct.
- **Field mods (post-progression), read via `veh.postProgression.iterOrderedSteps()`:**
  each step has `getLevel()` (1..N → roman numeral), `isReceived()`, `getPrice().xp`,
  and a typed `action`. Two kinds: **leveled mods** (`FeatureModItem`/`SimpleModItem`/
  `RoleSlotModItem`, cost `price.xp`, one per level → hexagon ticks) and **multi-mod
  choice slots** (`MultiModsItem`, `price.xp==0` → excluded from bar AND counter).
  The tree always lists **8 levels + 5 multi-mods regardless of tier**; only the
  per-level XP scales (T6 3500 / T8 11500 / T10 28000). Clamp to the tier cap:
  `max_level(tier)` (VI–VII=5, VIII=6, IX=7, X+=8 — **XI unverified**).
- **Per-level pair structure (verified in-game, drives the tooltip variants):** a
  level's leveled XP step and its free `MultiModsItem` are SEPARATE steps — the
  multi-mod hangs off the leveled step as a child (`MultiModsItem.getParentStepID()`
  == the leveled step's `stepID`). The leveled step's own name is a generic base
  mod that REPEATS across levels (e.g. "Additional Armor Plating (Type 2)" at both
  L7 and L8 — confirmed it's exactly what WoT's own field-mods grid shows). The two
  *distinct* selectable variants live in the multi-mod's `action.modifications`
  (always 2), each named via `mod.getLocNameRes()`. `_pair_options()` reads them
  and `_read_post_progression` keys them by parent stepID onto the leveled tick's
  `options` → tooltip "A or B".
- **Counter** = researched / total LEVELED field mods within the cap (`fieldmods_done
  / fieldmods_total`); multi-mods are not counted.

## Gotchas / lessons (don't relearn these)
- **Gameface drops a whole CSS declaration on an unresolved `var()`** — it does NOT
  honor the hex fallback in `var(--x, #hex)`. Every color was a `var()`, so the bar
  rendered black. Fix: literal hex only. Custom properties are effectively unusable
  in our injected document.
- **Gameface CSS that DOES work (used in the restyle):** `mix-blend-mode`
  (`color-burn`, `multiply` — the client itself uses `additive`); `filter:
  drop-shadow(...)` (chainable; use it instead of `box-shadow` for alpha/clip-path
  shapes so the shadow hugs the silhouette); multi-stop `linear-gradient` /
  `radial-gradient` + multiple backgrounds; `clip-path: polygon()`; `::before` /
  `::after` pseudo-elements; `box-sizing: border-box`.
- **For dense even tick/notch patterns, tile a SINGLE `linear-gradient` via
  `background-size` + `background-repeat: repeat` — NOT `repeating-linear-gradient`**,
  whose per-period rounding makes the spacing visibly drift across the bar. A tiled
  single gradient snaps every tile pixel-identically.
- **Native WoT bars are FLAT** (`EditableProgress_line` = plain `background-color`),
  with a segmented pattern overlaid on top (`EditableProgress` / `VehicleExperience`
  use period **3rem**). The green "done" tone is `#64ba21` (= `rgba(100,186,33)`,
  from `lib.css` `Status`). Combat-XP currency = `#dce0e0`, free-XP = `#ecca9d`. To
  re-extract more: unzip `res/packages/gui-part{1..4}.pkg` and grep the CSS under
  `gui/gameface/_dist/production/**` (the team-HP battle bar is Flash/Scaleform, NOT
  in the gameface bundles).
- **Gameface ignores `object-fit` and clips `<img>` to its box; `width:auto`→0.**
  Use a div with `background-size:contain`. `clip-path: polygon(...)` DOES work
  (the field-mod hexagons use it).
- **Hot-reload loop for JS/CSS-only changes (no relaunch):** `tools/dev/
  sync_gameface.py "<install>" 2.3.0.1` copies the gameface assets into the
  `res_mods` overlay, then in-game switch to another screen and back to the Garage —
  the hangar sub-view document re-fetches them. Python (mount/data) changes still
  need build+deploy+relaunch via `deploy_wotmod.py`. **After every `deploy_wotmod`,
  re-run `sync_gameface`** or the (now stale) overlay shadows the fresh package.
  **Remove the overlay before a clean ship-verification** (`res_mods/2.3.0.1/gui/
  gameface/mods/drizzer14/`).
- **Wrong client trap:** the StranikS-Scan default branch is **MirTankov/Lesta RU**,
  a different client (it has "Paragons", lacks `RandomHangar`). Use branch **`2.3`**
  (EU). "Paragons / elite milestones / level-150" do **not** exist in EU — the elite
  feature was dropped; v1 is the XP-driven bar.
- **WoT 2.3 loads only `.wotmod`** from `mods/<version>/`; `res_mods` outranks it, so
  a stale loose copy SHADOWS the package and the client silently ignores the mod.
  Always deploy via `deploy_wotmod.py` (auto-cleans), with the **client closed**.
- **`g_currentVehicle.onChanged` is a STRONG-ref delegate `list`** (not a weak-ref
  Event — the earlier `1e11b90` theory was wrong). The real trap: WoT tears down and
  rebuilds the hangar space on **battle exit**, repopulating that list with WG's own
  presenters while dropping any handler that doesn't re-subscribe. WG presenters
  re-add themselves on each hangar load; so must we. `install_vehicle_listener()` is
  self-healing (re-adds iff not in the list) and is called from the patched
  `_onLoading` on every mount. Don't go back to a once-only subscription.
- **Gameface hover/tooltip quirks (learned this session):** (1) Gameface only
  hit-tests within an element's OWN box — children painted OUTSIDE it (our glyphs
  hang below the bar) are NOT hovered via the parent, so a hover region must be a
  box that actually covers them (the `.wg-hot` overlay). (2) `mouseenter` on tiny
  marks is unreliable; `mousemove` on a covering region works. (3) `e.offsetX` is
  NOT populated (came back `undefined`) — use `clientX - getBoundingClientRect().left`.
  (4) `e.target` is usually the listener's element / the layer, NOT the deep glyph,
  so per-element hit detection can't be relied on — resolve the tick by nearest
  `clientX` (keep an `e.target` climb as a bonus). (5) `render()` runs on every
  model update (can fire while the cursor is still) — do NOT hide the tooltip in
  `render()` or it blinks out whenever the cursor stops; let the hover handler own
  visibility. (6) No native `title` tooltip — must build our own DOM element.
- **Field-mod action NAME is a resource, not an attribute (FIXED):** use
  `action.getLocNameRes()` → it's a wulf `DynAccessor`, CALL it for the int id →
  `backport.text(id)`. `getLocName()` alone is just the raw key
  (`clutches_replace_1`); `action.locName`/`.name` don't exist. Same call resolves
  each variant in `action.modifications` for the pair tooltip.
- **Special "7×7" tanks** (T57 Heavy 7×7, etc.) use a hangar without
  `HangarVehicleParamsPresenter`, so the bar won't mount there. If that matters,
  pick a more universally-present sub-view as the inject host (or accept the gap).
- Mod module isn't importable as `mod_wgmod` (loader namespace); the bridge module
  IS importable (`wgmod_research.bridge.gameface_bridge`) — use it for REPL pokes.
- The session **scratchpad is ephemeral**; durable dev tools now live in `tools/dev/`.
  Re-clone the EU decompiled source when needed (see tools/dev/README.md).
