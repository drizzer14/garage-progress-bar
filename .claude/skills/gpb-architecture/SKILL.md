---
name: gpb-architecture
description: Architecture of the Garage Progress Bar WoT mod specifically — its concrete wgmod_research file tree, the seven bar modes + priority order (including the opt-in POTENTIAL_TIER_XI speculative bar), the resolvers, per-item tech-tree pricing, blueprint discount, done-marker reconcile, and the ResearchVM/TickVM/UpgradeVM shapes. Use when editing or extending THIS mod's Python, adding a bar mode, tracing a click→research action, or debugging why the bar doesn't update. (For the reusable engine-free domain/adapter/bridge discipline and the conventions that bite, see the wotmod-architecture harness skill; for the JS/CSS widget, gpb-widget; for the settings-panel localization pattern, wotmod-i18n-settings; for live game symbols, references/game-api.md.)
---

# wgmod architecture (this mod's specifics)

The reusable pattern — engine-free `domain/` vs `adapter/` (reads+writes) vs `bridge/`
(Wulf/Gameface), and the conventions that bite (listeners re-arm every mount, Wulf MAP-arg,
fail-soft reads, `_compat.py` shim, ModsSettingsAPI replace+saveState, hand-numbered VM
indices, import≠ready) — lives in the **wotmod-architecture** harness skill. This skill is
how the Garage Progress Bar realizes it.

```
src/res/scripts/client/
  gui/mods/mod_wgmod.py               # ENTRY POINT — monkey-patches a hangar sub-view
  wgmod_research/
    _compat.py                        # engine shims: LOG_* fallbacks + _safe/_safe_int guards
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
    domain/resolvers/{techtree,fieldmods,skilltree,elite}.py  # pure snapshot -> ticks
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
SEVEN real modes plus HIDDEN. `build_model` takes `enabled` (Mode strings left ON; None = all). If a vehicle
RESOLVES to a mode toggled off, `_emit()` returns a `Mode.HIDDEN` placeholder — **no
fall-through** to a lower-priority mode. `bar_visible(overlay_closed, hide_always,
hide_when_complete, mode, in_garage)` combines that with the master hide switch, the
hide-when-complete option, the tank-setup-overlay state, and the fail-closed garage allowlist
(`in_garage` = only the plain `hangar/{root}` view).

## Conventions specific to this mod
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
  - Widget rendering: see gpb-widget "Buff lines".
- **Settings-panel localization — read `wotmod-i18n-settings` FIRST.** The reusable MSA-panel
  pattern (lang-major tables with English master + per-key fallback + untranslated-leak diagnostic,
  `getClientLanguage`/`_norm` incl. `ua`→`uk`, `{HEADER}/{BODY}` tooltip assembly, and THE gotcha —
  MSA caches a COPY of the template text at registration, so a text-only change never reaches an
  existing install without walking the stored template in place, and needs NO `settingsVersion`
  bump) lives in the **wotmod-i18n-settings** harness skill. This mod's *concretes* only
  (`adapter/settings_i18n.py` + `bridge/mod_settings.py`):
  - **`showBar` is a MASTER checkbox with 7 nested children** — the 6 per-mode toggles +
    `showWhenComplete` — bound by a hand-set `"masterVarName": "showBar"` on
    each child in `mod_settings._child()`/`_template()`, NOT via Aslain's `createControlsGroup`
    (keeps `_template()` a pure, unit-testable dict; the key is simply ignored under
    izeberg / pytest). Aslain greys + disables the children while `showBar` is off; no
    `masterIndent` key means they render indented. **`ignoreFreeXp` is a STANDALONE checkbox**
    (no `masterVarName`), placed last in column1 after the `showBar` group.
    **Every structural change here needs a `settingsVersion` bump** — MSA caches the panel
    layout keyed by `settingsVersion` and reuses the STORED template on an existing install
    until you bump, so nesting AND re-parenting a control between groups both require it
    (adding/removing a control does too): bumped 4->5 when the modes were inverted into the
    `showBar` master, then 5->6 when `ignoreFreeXp` was moved OUT of that master to a standalone
    control — no `varName` and no default changed, yet the relocation alone still needed the
    bump (confirmed live: it didn't render standalone until 5->6) — then 6->7 when the `scale`
    Dropdown was added to column2 (a new control + new `varName` + option labels; Aslain folds
    option labels into the template signature, so the bump is mandatory to push it and its
    localized options to an existing install — see the scale bullet below). Text-only label/tooltip
    edits do NOT bump (see the i18n bullet above). (MSA's full nesting toolkit —
    `masterVarName`/`enableWhen`/`visibleWhen`, `column1..column4` — is in
    wotmod-architecture -> ModsSettingsAPI.)
  - **`settings_i18n.COL1_KEYS` must stay in lockstep with `_template()` column1 wire order.**
    `_sync_template_text` walks the STORED template POSITIONALLY against
    `COL1_KEYS`/`COL2_KEYS`, so reordering column1 without updating `COL1_KEYS` silently
    mislabels controls (no crash). Guard test: `test_col1_keys_match_template_wire_order` in
    `tests/test_mod_settings_template.py`.
  - **Only the panel LABELS are localized** — NOT tooltips, NOT anything outside the panel.
    `settingsVersion` is **7** (bump history in the bullet above).
  - **The `scale` control is a `Dropdown`** (column2, ABOVE the Bar position controls) — the
    Default/Large bar-size selector. Its Aslain descriptor uses `value` = the current 0-based
    index (`_clamp_scale` coerces a bad/out-of-range read to `0`) and `options` =
    `[{"label": …}]`. `settings_i18n` keeps the two option-label strings (Default / Large) in a
    SEPARATE `_SCALE_OPTIONS` table, NOT `_LABELS` — options aren't label/tooltip rows, and
    folding them in would break the positional `COL*_KEYS` / `_sync_template_text` partition
    (its tests enforce this). `render_panel` resolves them (same `_norm` + English fallback) and
    attaches the localized pair onto `t["scale"]["options"]`; `_template()` drops it into the
    descriptor. `COL2_KEYS` = `(scale, barPosition, posX, posY)`. Adding it bumped
    `settingsVersion` 6->7 (option-set change — see wotmod-i18n-settings "Option-bearing
    controls"). `mod_settings.scale()` reads the index back; `bridge.push` writes it to
    `ResearchVM.scale` (prop 33); the widget folds `.wg-large` when it's `1` — the VISUAL
    mechanism (asymmetric width x2.0 / rest x1.5 via an explicit override class) is gpb-widget.
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
in `references/game-api.md`. The full generic symbol catalogue is the **wotmod-architecture**
harness skill's `references/game-api.md`. Read before adding a `*_read.py` or an `actions.py` path.
