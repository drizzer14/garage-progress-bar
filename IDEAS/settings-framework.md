# Research: Candidate settings — the shared substrate + recipe

_Submitted: the "Candidate settings (for the settings system in progress)" cluster · Status: open_

## Summary
The cluster is a list of hardcoded values that should become MSA (ModsSettingsAPI)
user settings. The settings system already ships and is battle-tested (per-mode
toggles + draggable position), so each candidate is an application of one recipe,
not new architecture. This note documents the recipe and classifies each candidate
so items can be ticked off individually.

## Current state (settingsVersion = 2)
`bridge/mod_settings.py` owns the settings. Already wired end-to-end:
- **Per-mode "Show X" toggles** — `showTechTree/showSkillTree/showFieldMods/
  showEliteRewards/showElite` (DEFAULTS ~50; template ~118–162; `enabled_modes()`
  ~498–514; gated in `domain/builder.py` via `_on()` ~25). Tested in
  `tests/test_builder.py`.
- **Draggable position** — `posX/posY` NumericSteppers (~173–198) with a
  seed+reset flow; tested in `tests/test_position.py`. Elaborate and
  position-specific — **do not copy it as the template for simple settings.**

Key functions: `_template()` (~77–200, the MSA panel), `_apply()` (~203–214,
merges MSA settings into the `_settings` cache with per-key coercion), `DEFAULTS`
(~46), `settingsVersion` (~91), `_on_changed()` (~278, calls `B.refresh()`).

## The recipe (add one setting)
1. **Add the key** to `DEFAULTS` and to `_template()` (matching `varName`, a
   control `type`, `value`, `tooltip`).
2. **Bump `settingsVersion`** (~91) *only if a `varName` was added/renamed/removed*
   — not for tooltip/label text. (Bumping resets stored user values.)
3. **Coerce in `_apply()`** (~203) — the generic path does `bool(...)`; numeric/
   float keys need explicit `float()` + clamp (mirror `clamp_pos` ~54). ⚠ Without
   this, a float setting is silently turned into a bool.
4. **Add a getter** (e.g. `def bar_width_scale(): return _settings[...]`).
5. **If JS-bound:** add a ResearchVM property + setter in `gameface_bridge.py` and
   push it in `push()` (~672–681: `tx.setXxx(mod_settings.xxx())`). ⚠ Wulf VM
   properties are index-based — **always add new props at the END**, never reorder.
6. **If Python-gated:** put the logic in `bar_visible()` or `build_model()`.
7. **JS:** read `data.xxx` in `render()` and apply — either a render conditional,
   an inline style, or set a CSS custom property (`root.style.setProperty('--x',v)`)
   that the CSS then reads via `var(--x)`.
8. Unit-test the Python coercion/clamp; manual in-game test (toggle → live change →
   restart persists → reset reverts).

## Classification of the candidates
**Front-end only (JS/CSS — no domain logic):**
- Bar width/scale (`WGModResearch.css` `width:520rem`) → CSS var / inline width.
- Fill colors + fill opacity (CSS ~219–299) → CSS vars set from JS.
- Icon drop-shadow / track shadow intensity+toggle (CSS ~62/151).
- z-index (CSS:23).
- Element visibility: category icon (`setCatIcon` ~303), XP readout (`setXp` ~329),
  field-mod counter (`setUpgrades` ~316), upgrade chips (`renderNextAvailable`
  ~434), tooltips on/off (hover handler). Each is an independent JS `if (data.showX)`
  gate.
- Custom/shortened mode labels; click hit tolerance (`CLICK_HIT_PCT`) + hover
  proximity — niche JS tuning.

**Python/domain-gated:**
- Mode toggles — DONE (reference implementation).
- Visibility override (force always/never) → new branch in `bar_visible()`.
- Click-to-research toggle (view-only) → gate the reverse click commands in
  `gameface_bridge.py` before `invokeCommand`/unlock.

## Gotchas (from the substrate)
- MSA `updateModSettings()` **replaces** the whole stored dict — read-overlay-write
  the full dict (the `posX/posY` path already does this) or you drop other mods'
  keys and lose persistence.
- Gameface CSS drops an unresolved `var()` — set the custom property from JS first.
- `_apply()` bool-coerces unknown keys: `"0"` becomes `True`. Numeric keys MUST get
  their own coercion branch.

## Splitting recommendation
Recommend splitting the single cluster into individually-tickable entries so each
can ship on its own:
1. **Styling settings** — width/scale, fill colors, fill opacity, shadows, z-index
   (pure CSS/JS, low risk).
2. **Element visibility toggles** — icon / XP readout / counter / chips / tooltips
   (pure JS gates, low risk, ship one at a time).
3. **Advanced modes** — visibility override, click-to-research, custom labels,
   hit-tolerance tuning (some touch domain logic / are niche — medium risk).
(Deferred to the user — IDEAS.md still holds the grouped cluster until they decide.)

## Verification
- Python: unit-test `_apply()` coercion + clamp for each new key.
- In-game: open the MSA panel, change the control, confirm the bar updates live;
  restart to confirm persistence; use the reset to confirm it reverts to default.
