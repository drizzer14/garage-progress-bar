---
name: gpb-architecture
description: Architecture of the Garage Progress Bar WoT mod specifically — its concrete wgmod_research file tree, the seven bar modes + priority order (including the opt-in POTENTIAL_TIER_XI speculative bar), the resolvers, per-item tech-tree pricing, blueprint discount, done-marker reconcile, and the ResearchVM/TickVM/UpgradeVM shapes. Use when editing or extending THIS mod's Python, adding a bar mode, tracing a click→research action, or debugging why the bar doesn't update. (For the reusable engine-free domain/adapter/bridge discipline and the conventions that bite, see the wotmod:architecture harness skill; for the JS/CSS widget, gpb-widget; for the ModsSettingsAPI panel's mechanics, wotmod:msa-settings; for the settings-panel localization pattern, wotmod:i18n-settings; for live game symbols, references/game-api.md.)
---

# wgmod architecture (this mod's specifics)

The reusable pattern — engine-free `domain/` vs `adapter/` (reads+writes) vs `bridge/`
(Wulf/Gameface), and the conventions that bite (listeners re-arm every mount, Wulf MAP-arg,
fail-soft reads, `_compat.py` shim, hand-numbered VM indices, import≠ready) — lives in the
**wotmod:architecture** harness skill, and the MSA settings panel's mechanics
(register/migrate lifecycle, replace-not-merge + `saveState`, guards, bump rules) in
**wotmod:msa-settings**. This skill is how the Garage Progress Bar realizes them.

```
src/res/scripts/client/
  gui/mods/mod_wgmod.py               # ENTRY POINT — monkey-patches a hangar sub-view
  wgmod_research/
    _compat.py                        # engine shims: LOG_* fallbacks + _safe/_safe_int guards
                                       #   owns the two log tiers (LOG_NOTE dev-gated / LOG_PROD
                                       #   always-on) + auto-path-scrubbed LOG_CURRENT_EXCEPTION
                                       #   -- full pattern in the wotmod:logger harness skill
    adapter/engine_adapter.py         # READ orchestrator: build_snapshot() composes the readers
    adapter/tech_read.py              #   reader: tech-tree modules + next vehicles
    adapter/post_progression_read.py  #   reader: linear field modifications
    adapter/skill_tree_read.py        #   reader: tier-XI skill tree (+ is_skill_tree)
    adapter/prestige_read.py          #   reader: Elite Levels ("prestige")
    adapter/pricing_read.py           #   reader: done-tick credits purchase price
    adapter/_read_common.py           #   shared read helpers (items-cache accessor, KPI text)
    adapter/actions.py                # WRITE-ONLY: invoke WG's research/unlock APIs
    adapter/format.py                 # pure formatting helpers (roman, icons, KPI) — tested
    adapter/i18n.py                   # widget labels from the game's OWN resource strings
    adapter/recent.py                 # session "done" markers (optimistic record + reconcile) — tested
    bridge/gameface_bridge.py         # listeners, refresh scheduling, click handlers, push/marshal
    bridge/view_models.py             # Wulf VMs: ResearchVM/TickVM/UpgradeVM (hand-numbered indices)
    bridge/wulf_args.py               # engine-free MAP-arg parsing (cmd_int_arg/cmd_xy_arg/cmd_wh_arg) — tested
    bridge/mod_settings.py            # ModsSettingsAPI panel: per-mode toggles, auto-hide, position (+ capture viewport posW/posH)
    domain/types.py                   # engine-free data types (2/3 compatible) + Mode
    domain/constants.py               # Category / GradeFamily string ids — the JS wire contract
    domain/builder.py                 # MODE STATE MACHINE (build_model + bar_visible)
    domain/resolvers/{techtree,fieldmods,skilltree,elite,potential}.py  # pure snapshot -> ticks
    domain/resolvers/complete.py      #   the COMPLETE gate: snapshot -> finished categories
src/res/gui/gameface/mods/14th_ua/WGModResearch/
  WGModResearch.{js,css}              # widget (see gpb-widget skill)
```

Refactor lineage: `engine_adapter.py` was a 593-LOC monolith; reads were carved into the
per-subsystem `*_read.py` modules, which engine_adapter re-imports under its old private
aliases (`_read_tech_unlocks`, `_read_prestige`, …) so `build_snapshot()` call sites are
unchanged. `read_purchase_price` is re-exported for the bridge. Similarly the VMs moved from
gameface_bridge into `view_models.py`, arg parsing into `wulf_args.py` (bridge re-imports as
`_cmd_int_arg` etc.).

## Forward flow (game → bar)
`mod_wgmod._install()` patches `HangarVehicleParamsPresenter._onLoading`. On each mount it
injects JS/CSS via `openwg_gameface.gf_mod_inject`, hangs a `ResearchVM` on the sub-view model
(property `wgResearch`), then `bridge.push()`: `engine_adapter.build_snapshot()` →
`builder.build_model(snapshot, enabled=mod_settings.enabled_modes())` (picks a `Mode`, calls
the matching resolver) → the bridge writes the `ResearchProgressModel` into `ResearchVM` in a
Wulf `transaction()`, plus channel fields: `labels` (JSON from `i18n.widget_labels()`),
`colorBlind`, `posX`/`posY` (+ `posW`/`posH`, the viewport a pinned position was captured at,
for resolution-aware rescale), `eliteCurrentIcon`, `spendableXp`, done-tick `price`. JS
`ModelObserver("WGModResearch")` re-renders.

## Reverse flow (clicks → research)
JS `invokeCommand()` calls a Wulf command on `wgResearch`. Six commands (`view_models.py`):
`researchUnlock` (tech-tree int_cd) / `unlockFieldMod` (field-mod or skill-tree step_id) /
`openSkillTree` / `openResearch` / `openFieldMods` (no arg — done-marker clicks open the
native screen) / `setPosition` ({x, y[, w, h]} px; w/h = capture viewport; `0/0` = auto). Handlers
parse args via `wulf_args.cmd_int_arg` / `cmd_xy_arg` / `cmd_wh_arg` and delegate to `actions.py`
or `mod_settings.set_position`. Before a research
action the bridge calls `_record_click()` → `recent.record(...)` so the item can render as a
"done" marker after it vanishes (optimistic-record; reconciled next sync). Handlers do NOT
refresh — the game's `onSyncCompleted` does.

## Mode state machine (`builder.build_model`, priority order)
TECH_TREE (any unlock remaining) → SKILL_TREE (tier-XI branching tree, count-based) →
FIELD_MODS → POTENTIAL_TIER_XI (opt-in speculative bar; entry-gated on `enabled` membership,
only for a Tier-X tank with NO real Tier XI — `builder._b_potential`) → ELITE_REWARDS (unearned
tier-XI milestone rewards) → ELITE (prestige grade band) → COMPLETE. This is the `_BUILDERS`
tuple order (`_b_tech, _b_skill, _b_field, _b_potential, _b_elite_rewards, _b_elite`); there are
SEVEN real modes plus HIDDEN. COMPLETE has NO builder of its own — see the next section.
`build_model` takes `enabled` (Mode strings left ON; None = all). If a vehicle
RESOLVES to a mode toggled off, `_emit()` returns a `Mode.HIDDEN` placeholder — **no
fall-through** to a lower-priority mode. `bar_visible(overlay_closed, hide_always,
hide_when_complete, mode, in_garage)` combines that with the master hide switch, the
hide-when-complete option, the tank-setup-overlay state, and the fail-closed garage allowlist
(`in_garage` = only the plain `hangar/{root}` view). `mod_settings.enabled_modes()` is the
settings→builder seam — it maps the six per-mode checkbox settings to the `Mode` set
`build_model` consumes; builder tests pass a `Mode` set in directly, so a wrong/collapsed
toggle→Mode mapping regression here hides behind a green builder suite and has its own guard in
`test_enabled_modes_*` (`tests/test_mod_settings_template.py`).

### Onslaught garage is `hangar/{root}` too — `_in_garage()` doesn't exclude it
Confirmed live via the debug REPL on client 2.4.0.0, both garages read side by side. The
"Onslaught" mode is internally named **Comp7**: prebattle entity class `Comp7Entity`
(module `comp7.gui.prb_control.entities.pre_queue.entity`), `getModeFlags()` = `536870912`
= `FUNCTIONAL_FLAG.COMP7`, `getQueueType()` = `29`, lobby state id
`subScope/subLayer/comp7/hangar/{root}`. The plain garage: entity `RandomEntity`, flags
`32768` = `FUNCTIONAL_FLAG.RANDOM`, state id `subScope/subLayer/hangar/{root}`. Because the
Onslaught state id still ENDS with `hangar/{root}`, `_in_garage()`'s allowlist matches it and
the bar renders there too — Onslaught is a prebattle queue/functional mode reusing the
default hangar view, not a distinct lobby leaf state.

To detect the current prebattle mode: `g_prbLoader.getDispatcher().getEntity().getModeFlags()`
(`g_prbLoader` from `gui.prb_control.dispatcher`; `FUNCTIONAL_FLAG` from
`gui.prb_control.settings`). **`g_prbLoader.getEntity()` does NOT exist** — it's always
`.getDispatcher().getEntity()`. `FUNCTIONAL_FLAG.MAPBOX` (bit 26) is a different flag, unset
in both garages tested — it is NOT Onslaught. Two valid discriminators: `getModeFlags() &
FUNCTIONAL_FLAG.COMP7`, or the substring `comp7` in the lobby state id.

Used in `adapter/prb_read.py`'s `is_onslaught_garage()`, consumed by
`bridge/gameface_bridge.py` to pick a per-mode position: the Onslaught (Comp7) garage has its
OWN independent X and Y (`onslaughtPosX`/`onslaughtPosY` vs the plain garage's `posX`/`posY`),
set by their own numeric steppers and Ctrl+drag; `posW`/`posH` (the capture-viewport size for
rescale) stay shared across both garages. `onslaughtPosX` was added and `onslaughtPosY`
promoted to a user-facing stepper in the `settingsVersion` 14->15 bump above.

- **The Onslaught-vs-regular WIRE is mode-blind — the field name `onslaughtPosX`/`onslaughtPosY`
  never crosses to JS, and a build-integrity grep for it in the packaged/minified widget WILL
  find nothing.** Python is the only layer that knows which garage it is: the bridge branches on
  `is_onslaught_garage()` to pick `mod_settings.onslaught_pos_x()/y()` vs `pos_x()/y()`, then
  pushes the chosen value through the SAME generic wire field, `data.posX`/`data.posY` (also
  `posW`/`posH`), consumed by the ONE `applyPosition()` in the widget (gpb-widget → "Position is
  viewport-aware"). The Python setting-key spelling `onslaughtPosX` appears only in a JS source
  comment and is stripped by the build minifier — it is not a real DOM/wire token. **A presence
  check for this feature must grep `applyPosition` + `prb_read.py`'s `is_onslaught_garage` branch
  in `gameface_bridge.py`, never the built/minified JS for `onslaughtPosX`.**

## COMPLETE ("Fully Progressed") — the gate, not a builder
Shipped in `e0ae891`. **The gate is "every category that APPLIES to this vehicle is finished"** —
NOT, as it was before, "no builder returned a candidate". The old `not cands` gate was almost
unreachable in practice: `_b_elite` returns a grade band even at the max elite level, so any
prestige vehicle kept showing the ELITE bar forever. (Behaviour change users see: a maxed-elite
tank now shows Fully Progressed instead of the Elite bar.)
- **Resolution order in `build_model`**: explicit per-vehicle `override` (if still available) →
  **COMPLETE** (`done_cats` non-empty AND `POTENTIAL_TIER_XI not in by_mode`) → the old
  `not cands` no-data COMPLETE `_placeholder` → priority winner (or HIDDEN if its toggle is off).
  `POTENTIAL_TIER_XI` still wins when it applies + is opted in: it is a speculative goal AHEAD of
  the vehicle, never a category it has finished (and so it is deliberately absent from
  `complete._CATEGORIES`). COMPLETE has no per-mode user toggle — `bar_visible`'s
  `show_when_complete` governs it.
- **`domain/resolvers/complete.py` is pure**: `resolve(snapshot) -> [(Mode string, raw total XP)]`,
  one entry per applicable category in bar-priority order, or `[]` while anything is unfinished /
  nothing applies. It adds NO engine reads — every applies/done/price fact is already on the
  snapshot. Applies/done matrix:

  | category | applies when | done when | total XP |
  |---|---|---|---|
  | TECH_TREE | `tech_unlocks` non-empty | every entry `researched` | Σ `xp_cost` of the OUTGOING unlock graph |
  | SKILL_TREE | `is_skill_tree` | `skilltree_done >= skilltree_total` | `skilltree_total_xp` |
  | FIELD_MODS | `fieldmods_total > 0` | `fieldmods_done == fieldmods_total` | Σ step `xp_cost` up to `fieldmods.max_level(tier)` |
  | ELITE_REWARDS | `elite_rewards` non-empty | every reward `achieved` | `elite_level_xp[last reward level]` |
  | ELITE | `has_prestige and elite_grades` | `elite_level >= elite_max_level` | `elite_level_xp[elite_max_level]` |

  **FIELD_MODS and SKILL_TREE are mutually exclusive** (a tier-XI vehicle reads field mods 0/0), so
  a real row can hold at most FOUR categories — the widget's 5-entry dev preview is an impossible
  state.
- **Totals are RAW `xp_cost`, never `xp_cost_effective`.** A blueprint discount is a one-off
  per-player rebate; reporting it would misstate what the category itself cost. (The opposite of
  the tech-tree TICK rule below — different question, different price.) A total that can't be
  derived degrades to 0 and the tooltip simply shows no cost line.
- **The Research total means "researchable FROM this vehicle", and that is intentional** (docstring
  confirmed, not a bug): `unlocksDescrs` is the OUTGOING unlock graph — modules + child vehicles —
  and a vehicle's own purchase price lives on its PARENT node. Default/stock modules never appear
  there at all. See `references/game-api.md` for the full semantics and the corpus counts.
- **Wire: NO view-model or marshal change.** The finished categories ride the existing
  `avail_upgrades` / `UpgradeVM` array (already marshalled unconditionally), one `ProgressionStep`
  each carrying `category` + its total as `xp_cost` + `done=True`. `_complete_model` is a REAL bar
  (`scale_min=0, scale_max=1, fill_vehicle=1`) — the old `_placeholder`'s 0/0 scale drew nothing,
  which is why COMPLETE used to be invisible. `progress_current` = the summed total (the header's
  upper-right figure), `progress_required` = 0 (so the widget's `current / required` + `%` readouts
  fall back to the current-only figure — they are gated on `required > 0`). It also pushes
  `elite_current_icon` and `elite_max_level` for the elite box's badge.
- **The header title comes from the SETTINGS PANEL's table, via a new seam.** The game ships no
  "Fully Progressed" string, but `settings_i18n`'s `showWhenComplete` label is exactly that text,
  already translated for all 11 languages. `settings_i18n.label(key, lang=None)` (pure given
  `lang`) exposes ONE such label; `i18n._complete_label()` calls it behind a guard and
  `widget_labels()["headerComplete"]` publishes it. The import is **LAZY** — `settings_i18n`
  imports `i18n`, so a top-level import would be circular. **Convention:** a widget string with no
  WG equivalent that the settings panel already ships comes from the panel tables through
  `settings_i18n.label()` — never a second translation table.
- Render side (golden gradient, `done_big.png`, the `.wg-chip` category row, the `FORCE_COMPLETE`
  dev flag): gpb-widget → "COMPLETE".
- **"Allow Fallthrough" (`allowFallthrough`, default off) replaced "Exclude Elite System".**
  It changes TWO things in `build_model`, both gated on the same flag:
  - The COMPLETE gate is normally **toggle-BLIND**: `complete.resolve(snapshot, enabled=...)`
    (`domain/builder.py:408`, gate at `:413` -- `done_cats and Mode.POTENTIAL_TIER_XI not in
    by_mode`) receives `enabled=None` by default, and `complete.resolve` (`resolvers/complete.py:86`)
    returns `[]` unless EVERY *applicable* category is done -- so a category still in progress
    (e.g. Elite Rewards) vetoes Fully Progressed for the whole vehicle even if the player
    disabled that mode's bar. Under Allow Fallthrough, `build_model` passes the real `enabled`
    set instead: `complete.py:100` then skips a disabled-mode category from BOTH the all-done
    check and the returned list, so a disabled-but-unfinished category no longer vetoes -- only
    the enabled, completed categories show. `enabled=None` (flag off) is byte-identical to
    before.
  - The final resolution branch (`builder.py:420-423`) stops hiding a disabled top-priority
    winner: instead of `_placeholder(Mode.HIDDEN)`, it takes the next enabled candidate in
    priority order -- `by_mode[avail[0]] if avail else HIDDEN` (`avail` is already the
    priority-ordered enabled subset of `cands`, so no rescan is needed).
  - The membership test in `complete.py` is inlined rather than importing `builder._on` --
    importing it would be circular (`builder` imports `complete`).
  - settingsVersion bumped 13->14 for the varName swap. Shipped + deployed on client 2.3.1.2,
    feature verified in-client 2026-08-18.

## Conventions specific to this mod
- **A GATE resolver must fail CLOSED — the repo-wide fail-soft rule INVERTS into a bug here.**
  "Every engine read fails soft to empty" (the harness `wotmod:architecture` convention) is right
  for a resolver that *displays* data: one bad read degrades one category. It is **wrong** wherever
  the value gates a *claim*. Live bug, caught by qa before `e0ae891` shipped: `complete.resolve`
  originally wrapped applicability+doneness in one `try`, so a category whose probe raised was
  DROPPED — `resolve()` then returned non-empty and an UNFINISHED vehicle rendered "Fully
  Progressed". Real repro: `tier=None` made `fieldmods.max_level()` raise while field mods stood at
  3/8. Fix = **probe applicability separately from doneness** (`_CATEGORIES` holds
  `(mode, applies, probe)`), so an applicable-but-unreadable category is kept and counted as NOT
  done and still vetoes; only a category we can't even tell applies is skipped (there, an
  exception is indistinguishable from "not applicable", since the readers already degrade to
  empty). Rule of thumb: **fail soft when the answer is "what to show", fail closed when the answer
  is "is it finished / allowed / paid".** *(Generic — propagate a terse version to the harness
  `wotmod:architecture` fail-soft bullet. Not edited there.)*
- **Tech-tree ticks are priced PER ITEM, not cumulatively.** `techtree.py` places each tick at
  its own cost (`xp_position = cost`, `affordable = cost <= spendable`) — items are
  independently researchable. Field mods are the exception (`fieldmods.py` stays cumulative —
  they unlock in sequence). Cost is `getattr(u, "xp_cost_effective", u.xp_cost)`:
  `xp_cost_effective` carries the blueprint-fragment-discounted price for a next-VEHICLE unlock
  (set in `tech_read` via `_read_common.blueprint_effective_cost`; modules keep raw cost — WG's
  validator rejects a module unlocked at a differing cost), and `actions._do_research` mirrors
  it into `UnlockProps` (discounted xpCost + discount% + raw xpFullCost).
- **Done-marker reconcile uses POSITIVE evidence, and expires.** `recent._is_done` confirms a
  click by presence + a truthy flag (tech-tree: still in `tech_unlocks` with `researched=True`),
  NOT by absence — the readers deliberately degrade to `[]` on failure, so an absence test would
  turn one bad read into a permanent false check. Skill-tree has no per-node flag so it keeps
  the absence test but guards the empty list. A pending that never confirms is dropped after
  `_PENDING_MAX_RECONCILES` (~5, count-based/testable); `veh_int_cd == 0` is rejected in both
  `record()` and `decorate()`.
- **A synthetic done tick must carry EVERY tooltip-bearing field a live tick has.** The done
  marker's `recent._make_tick` builds a `Tick` from the recorded dict, so any field it omits
  defaults to empty and the widget silently falls back to a less-specific tooltip branch. This
  bit field mods: `_make_tick` dropped `options`/`option_effects` (the A/B variant pair), so the
  done tick took `tooltipHtml`'s base `name`+`effect` branch — and those base strings are generic
  and repeat across levels (`post_progression_read.py`), reading as the WRONG field mod. Fix
  threaded the pair through the whole optimistic chain: `_record_click` (capture off the snapshot
  step) → `recent.record()` params → the `_pending` dict → `_make_tick`. The bridge marshal
  already forwards `options`/`optionEffects` for every tick, so no VM/JS change was needed. Rule
  of thumb: when adding a tooltip field to a live resolver tick, mirror it in the `recent` chain.
- **Buff/KPI tooltip lines are enriched records, not plain text.** `_read_common._kpi_lines`
  emits one `format.kpi_record` per KPI (`icon \x1f cls \x1f value \x1f desc`) so the widget can
  render the game's native perk-tooltip look. Three resolutions, all live-verified (EU 2.3):
  **color** = `KPI.isDebuff` (NOT the number's sign — a beneficial reduction like a −25% fire
  chance is `isDebuff=False` → green); **unit** (`add` KPIs only) = `items_parameters.formatters
  .measureUnitsForParameter(<param>)` → `#menu:tank_params/*` key → `helpers.i18n.makeString` →
  `format.strip_unit` drops the parens (`avgDamage`→`HP`, `aimingTime`→`s`, …); **icon** =
  `R.images.gui.maps.icons.vehParams.small.dyn(<param>).isValid()` → `backport.image`. The
  KPI name → vehParams param basename remap is `format.KPI_PARAM_ICON` (ported from the client's
  perk-tooltip bundle; unknown names used verbatim, unresolved → no icon/unit, never a broken
  box). `format.py` holds the pure helpers (unit-tested); the game-symbol lookups live in
  `_read_common` (live-only).
  - **`isDebuff` color GOTCHA — key it on the MAPPED param name, not the raw KPI name.** The game
    derives `KPI.isDebuff` by testing the **raw KPI name** (e.g. `vehicleGunAimSpeed`) against
    `gui.shared.items_parameters.comparator.BACKWARD_QUALITY_PARAMS` (its "lower is better" set).
    But that set keys several params ONLY under their **vehParams param name** (e.g. `aimingTime`),
    NOT the KPI name — so a lower-is-better KPI whose KPI-name diverges from its param-name (aim
    speed at minimum) is mis-colored: a beneficial `-0.1s` aim reduction wrongly takes the
    red/debuff (`neg`) branch. The KPI→param remap the mod already holds in `format.KPI_PARAM_ICON`
    (accessor `format.param_icon_name`) is the correct membership key for the COLOR decision too, not
    just icons/units. Fix (shipped): pure `format.resolve_is_debuff(raw_is_debuff,
    kpi_name_backward, param_name_backward)` flips the flag when the mapped param name is in
    `BACKWARD_QUALITY_PARAMS` but the raw KPI name is not; `_read_common` computes the two
    membership booleans against the game set (fail-soft — falls back to raw `KPI.isDebuff` if the
    import fails) and defers to the pure helper, which then feeds `format.kpi_record`
    (`neg`=red / `pos`=green).
  - **The game keeps TWO separate "lower is better" tables, not one — check both before
    concluding no signal exists.** `gui.shared.items_parameters.comparator` exports the flat
    `BACKWARD_QUALITY_PARAMS` set above AND a second, compound `_CUSTOM_QUALITY_PARAMS` table
    (per-component tuples; currently `pitchLimits`, `clipFireRate`, `burstFireRate`,
    `turboshaftBurstFireRate`). `KPI.isDebuff` (`gui/shared/gui_items/__init__.py:463-465`)
    consults ONLY the flat set, so a KPI that is "lower is better" solely via the compound table
    computes the WRONG `isDebuff` at the source — e.g. `gunDepression` (backward via
    `pitchLimits` component 0) and `reloadTimeInClip` (via `clipFireRate`). Fix:
    `format.KPI_BACKWARD_OVERRIDE = frozenset(["gunDepression", "reloadTimeInClip"])`, ORed into
    `_resolve_is_debuff`'s param-backward branch. **Key it by the RAW KPI name, not the mapped
    param name** — `pitchLimits` is compound (component 0 depression = backward, component 1
    elevation = not), so `gunDepression` belongs in the override but `gunElevation` (same param,
    other component) must NOT — adding it would invert an already-correct read.
  - **Signature "mechanic" perks (`KPI.Name.VALUE`, raw name `'value'`) have NO reliable
    direction signal anywhere** — not in either quality table, not in WG's own skill-tree
    tooltip (which renders these neutral too). Convention: a `name == 'value'` line renders
    NEUTRAL (`cls="neu"`, `is_debuff=None`) — match WG, don't invent a direction for it.
  - **Tier-XI description templates INDEX their value slots: `{<kpi.name><0-based index>}`, with
    the index OMITTED when the node has exactly ONE KPI.** So a single-KPI node reads `{value}`
    while a multi-KPI node reads `{value0}`/`{value1}` — a plain `{value}`-only substitution leaves
    the indexed spellings as raw literal text in the tooltip (the symptom on the tier-XI French TD
    Fauteur's final node). The substituted text is **magnitude only** — unsigned, no unit:
    `abs(100*(v-1))` for `kpi.type == "mul"`, else `abs(v)`, trailing zeros dropped
    (`format.kpi_magnitude`; the loop that walks the ordered KPI list and accepts both spellings is
    `format.fill_kpi_placeholders`, whose `filled` return tells `_skilltree_effect` the sentence
    already carries its numbers so the KPI lines must NOT also be appended). Source of truth for
    the index+magnitude rule is the LIVE client's
    `mono/vehicle_hub/views/tooltips/perk_tooltip/.../bundle.js` `descriptionValues` transform —
    it is NOT in the decompiled Python, so don't look for it there. Only 3 templates in
    `res/text/lc_messages/veh_skill_tree.mo` are indexed at all: `f143_mechanic_0` (2 values),
    `f143_mechanic_3` (2 — Fauteur's final node, the confirmed case), `r230_mechanic_3` (3, still
    unverified in-game).
  - **A KPI record with neither an icon nor a desc must never become a tooltip line.** It renders
    as a naked green number with nothing naming it. These arise when `kpi.name == "value"` (the
    generic mechanic-perk KPI), for which `format._param_icon`/`param_icon_name` correctly resolves
    to `""` — the resolution isn't broken, the record is just unlabelable. `format.kpi_record_labeled`
    is the predicate; `skill_tree_read._skilltree_effect:213` filters `_kpi_number_lines` through it.
  - **WG suppresses a skill-tree node's ENTIRE KPI/param list purely on `categories[0] ==
    "mechanics"`** — same bundle: `[Common,Major,Final].includes(type) && category !== "mechanics"`.
    Our own read already has `getCategories()` in hand at `skill_tree_read.py:153`, so matching WG
    is a category test, not new plumbing. Note branching on `getType() == "final"` alone would MISS
    the mechanic *major* nodes.
  - **Caveat: `action._descriptor.kpi` (what the mod reads) can diverge from `action.getKpi(vehicle)`
    (what WG uses)** when a KPI carries `vehicleTypes` or is `AGGREGATE_MUL` — WG's accessor filters
    and aggregates. The mod reads the descriptor deliberately: base `getKpi` returns `[]` while the
    node is unpurchased, which is exactly when we need the numbers. Since the indexed slots key off
    LIST ORDER, a divergence would mis-assign values; order was confirmed correct for
    `f143_mechanic_3` against the live in-game tooltip.
  - Widget rendering: see gpb-widget "Buff lines".
- **Progress readout scalars (`progress_current` / `progress_required`) are per-mode; the two
  elite axes differ from each other.** Every emitted `ResearchProgressModel` carries two
  unified scalars the widget renders as `current / required` (+ an optional `%`); each mode
  builder sets them differently and the rule is load-bearing:
  - **XP-fill modes** (TECH_TREE / FIELD_MODS / POTENTIAL_TIER_XI): `progress_current` =
    `spendable_xp` (vehicle + free XP), `progress_required` = `scale_max` — because for these
    the bar axis genuinely IS an XP amount.
  - **SKILL_TREE**: `progress_current` = `spendable_xp`; `progress_required` =
    `max(0, snapshot.skilltree_total_xp - snapshot.skilltree_spent_xp)`. The skill-tree BAR is a
    node-COUNT axis (`scale_max` = node count), so the readout denominator can't be `scale_max` —
    it's the XP still needed to fully upgrade. These two snapshot fields were previously read but
    DROPPED by `_b_skill`; this readout is their first consumer (`builder._b_skill`).
  - **ELITE (grade band)**: a genuine WITHIN-BAND XP axis — the bar fill width EQUALS the readout
    %. `elite.resolve_grade_band` sets `scale_min = level_xp[band_min]`, `scale_max =
    level_xp[band_max]`, `fill = combat_xp − scale_min` (combat_xp = `level_xp[level] +
    max(0, elite_current_xp)`, reconstructed in `_elite_model`); readout `progress_current =
    max(0, combat_xp − scale_min)`, `progress_required = span (= scale_max − scale_min)`, and it
    PROMOTES both scalars so `_elite_model` uses them verbatim (`res.get("progress_current",
    combat)`). At a terminal MAX grade the span is ≤ 0 → BOTH scalars 0 (widget falls back to a
    current-only readout, `%` hidden; `renderElite` still clamps the fill to a full bar).
  - **ELITE_REWARDS (reward track)**: still LEVEL-based (NOT an XP axis) — do NOT conflate it with
    the grade band. `progress_current` = `combat_xp` (the resolver promotes NO `progress_current`,
    so `_elite_model` falls back to reconstructed cumulative `combat`); `progress_required` = the
    resolver-PROMOTED trailing-tick cumulative XP (`resolve_reward_track` → last reward level's
    cumulative XP, promoted to a scalar so the builder needn't walk ticks).
  - **COMPLETE**: `progress_current` = the SUM of the finished categories' totals (the header's
    upper-right figure), `progress_required` = **0** — nothing is left to require, so the widget
    falls back to the current-only readout and hides the `%`. **HIDDEN**: neither scalar is set (0).
  - **THE TRAP:** for ELITE_REWARDS and SKILL_TREE, `scale_max` is a LEVEL or NODE COUNT, not an
    XP amount — the per-XP denominator lives per-tick as `Tick.xp_required` (from
    `snapshot.elite_level_xp`). A naive `spendable_xp / scale_max` for those two modes is WRONG.
    (ELITE grade band is the exception — its `scale_min`/`scale_max` ARE cumulative-XP bounds now,
    so its fill == its readout %.) Anyone adding an XP-based readout must take `progress_required`
    from the builder/resolver, never divide by a level/count `scale_max`.
- **There is NO compact numbered "Elite Level <N>" string in the client (EU 2.3.1.0)** — a
  "required level N" caption cannot be composed from game resources. The only semantic match,
  `veh_skill_tree:vanity/reward/level/tooltip` = "Elite Level required for reward"
  (`R.strings.veh_skill_tree.vanity.reward.level.tooltip()`, declared
  `<decompiled>/res/scripts/client/gui/impl/gen/resources/strings.py:126571`), is **macro-less** —
  no number slot. `prestige:tooltip/eliteLevel/title` is "Elite System" (already wired as
  `headerElite`), `prestige:tooltip/grades/header` the plural "Elite Levels" (already
  `capEliteLevel`); the only numbered form anywhere is a whole sentence
  (`messenger:serviceChannelMessages/invoiceReceived/prestigeSet/justLevel`, "The %(vehicleName)s
  received Elite Level %(level)s."). **Convention:** render a required level as the existing
  plural `capEliteLevel` label plus the NUMBER painted over the grade emblem — the pattern the
  ELITE grade-band tooltip already uses (gpb-widget → `eliteTipIconHtml`). Verified by parsing
  every `.mo` under `res/text/lc_messages` (no msgstr matches `^Elite Level$`) — that parse is how
  you answer "does this string exist / does it take a macro" with the client CLOSED.
- **Settings-panel localization — read `wotmod:i18n-settings` FIRST.** The reusable MSA-panel
  pattern (lang-major tables with English master + per-key fallback + untranslated-leak diagnostic,
  `getClientLanguage`/`_norm` incl. `ua`→`uk`, `{HEADER}/{BODY}` tooltip assembly, and THE gotcha —
  MSA caches a COPY of the template text at registration, so a text-only change never reaches an
  existing install without walking the stored template in place, and needs NO `settingsVersion`
  bump) lives in the **wotmod:i18n-settings** harness skill. This mod's *concretes* only
  (`adapter/settings_i18n.py` + `bridge/mod_settings.py`):
  - **Panel shape: three `Label`-headed categories over TWO columns, no master checkbox.**
    column1 = "Modes" (the seven per-mode toggles, all STANDALONE — the old `showBar` master
    was removed in the v10 restructure, so turning all seven off is what hides the bar).
    column2 = "Formatting" (`ignoreFreeXp`, `showPercent`, `progressMode`) then an
    `{"type": "Empty", "height": 20}` spacer then "Layout" (`scale`, a "Position" sub-label,
    `posX`, `posY`). **"Layout" deliberately shares column2 instead of declaring `column3`** —
    a third declared column only renders side-by-side while the USER's global MSA
    `multiColumnMode` toolbar toggle is on (default OFF); with it off Aslain folds the declared
    columns round-robin (`i % columnCount`, columnCount=2) and `column3` would stack UNDER
    column1. Full mechanism + caveats: wotmod:msa-settings → columns.
  - **DON'T bump `settingsVersion` for a layout change** — the bump rules (what is structural to
    Aslain's `(varName, type, domain)` signature and what isn't, and why every bump costs a wipe
    `init()` then migrates back) are wotmod:msa-settings; the same correction is inlined in
    `mod_settings._template()`. This mod's 8->9 bump (a pure column move of `showPercent`) was
    gratuitous and wiped users' settings for nothing.
    Honest bump history: 4->5 (modes inverted into the then-`showBar` master — *the layout half
    of that was not the reason; the `varName`/polarity change was*), 5->6 (`ignoreFreeXp`
    de-nested — **unnecessary**), 6->7 (`scale` Dropdown added — required), 7->8
    (`progressMode` + `showPercent` added — required), 8->9 (`showPercent` moved column1→column2
    — **unnecessary**), 9->10 (three-category restructure — required *only* because it REMOVED
    the `showBar` varName), 10->11 (`scale` + `progressMode` re-typed from `Dropdown` to inline
    `RadioButtonGroup` — a `type` change, genuinely structural), 11->12 (two more `Empty`
    spacers added to column2, a row-count change), 12->13 (the `excludeEliteSystem` child
    CheckBox added under `showWhenComplete`), 13->14 (`excludeEliteSystem` replaced by the
    standalone `allowFallthrough` checkbox — see "Allow Fallthrough" above), 14->15 (the
    Onslaught garage got its own X axis: `onslaughtPosX` added and `onslaughtPosY` promoted
    from an internal-only key to a user-facing stepper — see "Bar position is
    resolution-aware" below for the Onslaught X/Y split). Current `settingsVersion` =
    **15**. (varName-less `Label`/`Empty` rows are NOT collected into
    `_settingsStructure` — resolved in wotmod:msa-settings.)
  - **`settings_i18n.COL1_KEYS`/`COL2_KEYS` must stay in lockstep with `_template()` wire order,
    POSITIONALLY — textless rows included.** `_sync_template_text` zips the key tuples against
    the STORED template's component list, so **every textless row (a `Label` header, an `Empty`
    spacer) must still occupy a slot** or every key after it shifts by one and the panel
    silently relabels itself on a client-language change (no crash). The repo uses a
    `SPACER = None` sentinel for those slots (`settings_i18n.py:69`); `_sync_template_text`
    tolerates it via `t.get(key)` → `None` → continue, but **`render_panel` needs an explicit
    `key is SPACER` skip** (`settings_i18n.py:373`) — without it the walk raised
    `KeyError: None`. Guard: the positional-alignment tests in
    `tests/test_mod_settings_template.py`.
  - **Only the panel LABELS are localized** — NOT tooltips, NOT anything outside the panel.
  - **The `scale` control is an inline `RadioButtonGroup`** (column2, ABOVE the Bar position
    controls; a `Dropdown` before v11) — the
    Default/Large bar-size selector. Its Aslain descriptor uses `value` = the current 0-based
    index (`_clamp_scale` coerces a bad/out-of-range read to `0`) and `options` =
    `[{"label": …}]`. `settings_i18n` keeps the two option-label strings (Default / Large) in a
    SEPARATE `_SCALE_OPTIONS` table, NOT `_LABELS` — options aren't label/tooltip rows, and
    folding them in would break the positional `COL*_KEYS` / `_sync_template_text` partition
    (its tests enforce this). `render_panel` resolves them (same `_norm` + English fallback) and
    attaches the localized pair onto `t["scale"]["options"]`; `_template()` drops it into the
    descriptor. `COL2_KEYS` = `(formatting, ignoreFreeXp, showPercent, progressMode, SPACER,
    layout, scale, position, posX, posY)` — the three category `Label`s and the `Empty` spacer
    each own a slot (see the lockstep bullet above). Adding it bumped
    `settingsVersion` 6->7 (option-set change — see wotmod:i18n-settings "Option-bearing
    controls"). `mod_settings.scale()` reads the index back; `bridge.push` writes it to
    `ResearchVM.scale` (prop 33); the widget folds `.wg-large` when it's `1` — the VISUAL
    mechanism (asymmetric width x2.0 / rest x1.5 via an explicit override class) is gpb-widget.
    - **The whole scale path FAILS SAFE to Default(0) on every layer**, so a "cold mount paints
      Large" symptom is a runtime value-DELIVERY problem, NOT a static large-default/inversion —
      don't re-hunt the source for a large default. The layers: JS strict `data.scale === 1`
      (WGModResearch.js); Python DEFAULTS `scale: 0` + `_clamp_scale` coerces any bad/out-of-range
      read to `0`; VM index 33 default `0`; CSS base `520rem` with `.wg-large 1040rem` as an
      ADDITIVE override. Large can only appear if the mod's runtime read genuinely receives
      `scale=1` at that mount. Confirmed diagnosis of one such case (post-update cold launch on
      4K): the bridge push and disk value were both `0` yet the bar painted Large — a temporal
      divergence at cold mount, traced to `mod_settings.init()`'s settingsVersion-mismatch branch
      reading a STALE stored value (see `TASKS/scale-large-after-update-cold-launch.md`; leading
      hypothesis, not yet fully confirmed). Same reasoning applies to `progressMode` (also a
      fail-safe-to-0 Dropdown index).
    - **On a `settingsVersion` bump the reset-to-defaults direction CANNOT produce Large** — the
      bump branch resets every stored value to the template's `value` (scale → `0` = small), so it
      explains a wiped pinned position after an update but never a Large bar. The bump/migrate
      mechanics themselves (`setModTemplate` self-persisting, the `old_raw` overlay landing as one
      debounced write — shipped in `0fc07fc`) are wotmod:msa-settings.
  - **The int-index keys need their own `_apply()` branch ABOVE the `bool()` fallthrough** —
    `scale` → `_clamp_index`, `progressMode` → `_clamp_index`, position keys → `clamp_pos`,
    `modeOverrides` → verbatim string; everything else is a bool. Any new index-valued control
    needs its own clamp + branch. Why the generic `bool()` destroys an index: wotmod:msa-settings.
  - **A new persisted key needs its `_apply()` branch in the SAME change that adds it** —
    confirmed bug: `onslaughtPosY` was added to `DEFAULTS` and to `set_position()`'s write, but
    not to the `("posX","posY","posW","posH")` position branch. `set_position()` calls
    `g.updateModSettings(...)` then `g.saveState()`, and `saveState()` synchronously fires MSA's
    global `onSettingsChanged` back into this mod's own `_on_changed` → `_apply(new_settings)`
    **before `set_position()` returns** — so `_apply()` re-ingests the just-written dict
    immediately. Missing from the position branch, `onslaughtPosY` fell through to the generic
    `else: _settings[key] = bool(settings[key])`, turning a valid Y like `300` into `True`, pushed
    to the widget as `int(True) == 1` — the bar snapped to the very top of the screen. Fixed by
    adding `onslaughtPosY` to the position branch; `onslaught_pos_y()` also now rejects a
    bool/non-numeric stored value explicitly (`isinstance(True, int)` is `True`, so bool must be
    checked before the numeric check) and falls back to `pos_y()`. Rule: any `g.updateModSettings`
    + `g.saveState()` writer round-trips synchronously through the mod's own `onSettingsChanged`
    before it returns — so every new persisted key's `_apply()` coercion must land alongside the
    key itself, not as a follow-up.
  - **Don't stack a third read-time guard on top of those two layers.** `_apply()`'s coercion
    branch (`clamp_pos` on every ingest) plus the settings migration already guarantee a clean
    number at read time for a persisted position key — a bool-rejecting check in the accessor is
    unreachable dead code, and wouldn't even catch the realistic case anyway (`clamp_pos(True) ==
    1`, a valid int). Two-layer defense for a new key: `_apply()` coercion + migrate its
    pre-existing stored form; the read accessor stays a plain `value or fallback`.
  - **Two label sources.** (1) **WG feature names** (Research, Upgrades, Field Modifications,
    Elite System, Elite Rewards, Tier XI) reuse WG's OWN localized strings via
    `i18n.widget_labels()` — `FEATURE_WG` maps each checkbox → its widget-labels key, so they match
    the game exactly. NEVER hand-translate a term the game already ships (that's how "модифікації"
    vs the correct "модернізація" / an un-localized "Elite" slip in); "Show"+noun composition is
    impossible (grammar/case), so the label just IS the WG noun. (2) **Mod-invented labels** (the
    two hide toggles, the "Bar modes"/"Bar position" labels, the two position steppers) use
    lang-major `_LABELS` tables.
  - **Tooltips are FIXED ENGLISH** for every control (`_TOOLTIPS_EN`, header+body) — never routed
    through i18n.
  - `render_panel(wg_labels, lang)` is pure (testable with a fake label dict); `panel_text()` feeds
    it `i18n.widget_labels()`; `client_language()` is the one guarded `getClientLanguage()` read.
    Ships `cs de en es fr hu it pl ru tr uk`; verify exact client codes live (gpb-debug-repl).
  - The propagate-to-existing-installs step is `_sync_template_text(api)`, called unconditionally
    per candidate api in `init()` (walks the STORED template and rewrites its label text in place).
    **It also rewrites `scale`/`progressMode`'s stored `options[i]["label"]`, positionally,
    guarded by a length match** — the second axis of the caching gotcha (options are cached
    separately from `text`/`tooltip`, so a text/tooltip-only rewrite loop leaves them frozen in
    whatever language the panel first registered with; a fresh install hides the bug because its
    template was already written in the current language). Still text-only, no `settingsVersion`
    bump. Full mechanism in **wotmod:i18n-settings** → "THE gotcha"; regression test
    `test_sync_template_text_relabels_stale_radio_options` (`tests/test_position.py`).
  - **The `<b>` bold-header wrap MUST live inside `render_panel()`, not `_template()`** — the
    single function both the initial build and `_sync_template_text` source their text from.
    `HEADER_KEYS` (frozenset of the three category `Label` keys) gates the wrap in
    `render_panel()`. Applying it a layer higher would make the sync compare stored (wrapped) vs
    freshly-rendered (unwrapped) text on every launch, strip the wrap back out, and
    `saveState()` on every init — see wotmod:i18n-settings "A display transform belongs in ONE
    function" for the mechanism. Guard: `test_sync_template_text_is_idempotent_over_the_bold_headers`
    (a DOUBLE sync asserting zero writes on the second pass — a single "is it bold" assertion
    would miss this). `bridge/mod_settings.py`'s `_label()` sets `useHTML: True` on the Label
    descriptor but does NOT itself wrap — it just declares the descriptor as HTML-capable.
  - **`scale` and `progressMode` ARE inline `RadioButtonGroup`s as of `settingsVersion` 11** —
    swapped from `Dropdown` with zero coercion changes (same 0-based-index value shape; only the
    descriptor `type` + `inline: True` moved), at the cost of the bump a `type` change forces.
    `inline` is emitted as a plain KEY, not through the vendor kwarg — see wotmod:msa-settings.
- **Bar position is resolution-aware, and the recompute lives in the WIDGET, not Python.**
  `posX`/`posY` are px, `0/0` = auto (the resolution-relative CSS default position — centered,
  ~17.6vh). The two position steppers (`posX` "Horizontal (center X)", `posY` "Vertical (top Y)")
  carry PLAIN base labels — no dynamic default suffix. When a coordinate is `0` the widget clears
  its inline `left`/`top` so the bar falls back to the CSS default; a nonzero value pins it. The
  widget never sends any auto measurement; `_on_reset` forces `0/0`. A *pinned* position also
  stores `posW`/`posH` — the Gameface viewport it was captured at — so the JS can rescale it
  proportionally after a resolution / UI-scale change (auto just re-derives the CSS default).
  Python's role is only to (a) persist `posW`/`posH` in `set_position(x, y, w, h)`
  and push them, and (b) TRIGGER a recompute when the viewport changes, via two added signals in
  the bridge: a `gui.g_guiResetters` callback (`_arm_gui_resetters`, a set — not the `+=`/`setattr`
  Event pattern; set-add is idempotent so re-arm-per-mount is safe) and a broadened
  `_on_settings_changed` (COLOR_BLIND **or** any geometry key from `_geometry_setting_keys()`).
  The JS `window` `resize` listener is the primary self-heal; these are the backstop. See gpb-widget
  for the JS `applyPosition` rescale/adopt logic.

## Skill-tree "next skills" chain (locked successors one hop past the frontier)
- **The engine's post-progression GRAPH API is now USED by this mod**:
  `PostProgressionStepItem.getNextStepIDs()` (→ successor step ids, backed by
  `descriptor.unlocks`) and `getParentStepID()`/`getParentStepIDs()` (→
  `descriptor.requiredUnlocks`). `adapter/skill_tree_read.py` does a SECOND pass over the
  available frontier: for each available step it calls `getNextStepIDs()`, loads each successor
  via `pp.getStep(next_id)`, keeps only the STILL-LOCKED ones, and dedupes a shared
  (convergent) successor down to one node that accumulates its `parent_ids`. A "next" node uses
  an **OR unlock rule** — one parent unlocking it is enough to make it available next.
- **New wire shapes.** `NextUpgradeVM` (`actionId=0, icon, name, xpRequired, effect, category,
  done=False, stepId, parentIds`), carried on `ResearchVM.nextUpgrades`; the existing available
  `UpgradeVM` gained a `stepId` field too. **Deliberate `stepId`-vs-`actionId` split**:
  `actionId` legitimately reads `0` for non-clickable rows (COMPLETE's finished-category
  breakdown, and now the next chips), so `stepId` is the stable link key used to connect a next
  node back to its parent(s) — never repurpose `actionId` for that. `parentIds` is a
  **comma-joined string** (`"1023"` or `"1023,1044"`), the same packed-string idiom already used
  for `availModes`.
- **Testability boundary, unchanged**: the bridge VM layer (`bridge/view_models.py` Wulf VM
  classes + `bridge/gameface_bridge.py` marshal loop) is NOT unit-testable in this repo —
  `frameworks.wulf`/`BigWorld` are never stubbed. Domain tests can reach
  `ResearchProgressModel`/`skill_tree_read` output, but NOT the actual VM property push or the
  `parentIds` comma-join — those need in-client (prober) verification.

## Key data types
`VehicleSnapshot` (adapter output / domain input), `ResearchProgressModel` (builder output →
bridge writes into `ResearchVM`), `Tick` (`category` drives glyph + clickability; `action_id`
= tech-tree int_cd / field-mod step_id, 0 = not clickable) — all in `domain/types.py`. The
`ResearchVM`/`TickVM`/`UpgradeVM` Wulf shapes live in `bridge/view_models.py`; their numeric
property indices are hand-maintained and must match `_addXProperty` registration order. The JS
reads by NAME, and the mode/category/grade/command string values are mirrored in the JS
`MODE`/`CAT`/`CMD`/`GRADE` constants — keep `domain/types.py Mode`, `domain/constants.py`, and
the `view_models.py` command names in lockstep (see gpb-widget).

## Adding a new read or write?
The concrete WoT/BigWorld symbols this mod uses — and which reader/action each lives in — are
in `references/game-api.md`. The full generic symbol catalogue is the **wotmod:architecture**
harness skill's `references/game-api.md`. Read before adding a `*_read.py` or an `actions.py` path.
