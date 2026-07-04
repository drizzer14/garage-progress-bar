# Research: JS mode/category/command constant sweep

_Submitted: "handoff to next session for js sweep" (follow-up to the Tier 3g
engine_adapter carve-up) · Status: open_

## Summary
Behavior-preserving front-end cleanup. The Python side of the mod centralized its
contract strings into enums (Tier 3-era `domain/constants.py` + `domain/types.py`, and
`bridge/view_models.py` for command names), so a typo there is a `NameError`. The
widget JS still hard-codes the SAME strings as bare literals at ~30 call sites. Because
Gameface JS has no compile/lint step here, a drift between the two sides fails
**silently**: a mismatched `category` renders the wrong glyph (or none), a mismatched
`mode` takes the wrong render branch, and a mismatched command name makes a click a
no-op (`callWG` logs `command missing:` at most). Hoist the literals into one
source-of-truth block at the top of `WGModResearch.js` that mirrors the Python enums,
with a comment pointing back to each enum. **No behavior change** — same strings, one
definition.

## The contract (both ends)
All three groups are the Python↔JS wire contract; the JS values MUST equal the Python
values verbatim.

### Mode — `data.mode` (Python `domain/types.py` `Mode`)
`tech_tree`, `field_mods`, `skill_tree`, `elite_rewards`, `elite`, `complete`, `hidden`
(the bar isn't pushed at all for `hidden`, so JS realistically sees the first six).
JS sites (line numbers as of commit `a03ae26`, will drift — grep, don't trust):
`WGModResearch.js` ~824-826, 1124-1125, 1136, 1149, 1201-1203, 1228, 1238-1241, 1263,
1367, 1458.

### Category — `t.category` on each tick (Python `domain/constants.py` `Category`)
`vehicle`, `module`, `fieldmod`, `upgrade`, `elite`, `reward`.
JS sites: ~262, 399, 406-407, 461, 488, 504, 726, 826-827, 1024, 1269, 1280, 1291,
1294, 1299.

### Command — Wulf reverse-channel names (Python `bridge/view_models.py` `_addCommand`,
handlers wired in `bridge/gameface_bridge.py`)
`researchUnlock` (arg: tech-tree int_cd), `unlockFieldMod` (arg: step_id),
`openSkillTree` (no arg), `openResearch` (no arg), `openFieldMods` (no arg).
(`setPosition` also exists but the JS drag code already owns it.)
JS sites: `callWG(...)` invocations + the `cmd = "..."` assignments at ~741-742,
1088, 1291-1301.

### Grade family — `GradeFamily` (Python `domain/constants.py`)
`iron`, `bronze`, `silver`, `gold`, `enamel`, `prestige`, `undefined`. Mirrored in the
JS `GRADE_COLOR` map (from the elite-fill-grade-color work). Include in the sweep for
completeness — same silent-drift risk.

## Suggested approach
1. Add a single block near the top of `WGModResearch.js` (after the file header),
   e.g.:
   ```js
   // Wire contract with the Python side — keep in lockstep with the enums noted.
   var MODE = { TECH_TREE:"tech_tree", FIELD_MODS:"field_mods", SKILL_TREE:"skill_tree",
                ELITE_REWARDS:"elite_rewards", ELITE:"elite", COMPLETE:"complete" }; // domain/types.py Mode
   var CAT  = { VEHICLE:"vehicle", MODULE:"module", FIELDMOD:"fieldmod",
                UPGRADE:"upgrade", ELITE:"elite", REWARD:"reward" };                 // domain/constants.py Category
   var CMD  = { RESEARCH_UNLOCK:"researchUnlock", UNLOCK_FIELD_MOD:"unlockFieldMod",
                OPEN_SKILL_TREE:"openSkillTree", OPEN_RESEARCH:"openResearch",
                OPEN_FIELD_MODS:"openFieldMods" };                                   // bridge/view_models.py
   ```
   (Match the file's existing style — it uses `var`/`function`, ES5-ish Coherent JS,
   not `const`/arrow everywhere; keep it consistent with surrounding code.)
2. Replace each bare literal at the sites above with the constant. Keep replacements
   mechanical — do NOT restructure the render branches.
3. Leave the CSS class strings (`wg-cat-<category>`) as-is unless trivially derived;
   the `"wg-cat-" + (t.category || "x")` concatenation (line ~1280) already works off
   the value, so it needs no change.

## Touch points
- Edit only: `src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js`.
- Read-only references (the Python source of truth, don't edit): `domain/types.py`
  (`Mode`), `domain/constants.py` (`Category`, `GradeFamily`), `bridge/view_models.py`
  (command names), `bridge/gameface_bridge.py` (handler wiring).

## Verification
JS-only change, so NO Python rebuild needed — use the hot-reload loop:
- `python -m pytest -q` still 147 (unaffected; sanity only).
- Hot-reload: `tools/dev/sync_gameface.py "D:/Games/World_of_Tanks_EU" 2.3.0.1`, then
  switch garage screens to refresh (overlay must have existed at client LAUNCH — see
  the dev-loop note; if the client was launched clean, relaunch with the overlay first).
- Exercise EVERY branch, since a typo shows only at runtime: a tech-tree tank (vehicle
  + module ticks, click to research), a field-mod elite tank (click the next tick to
  unlock, click a done marker to open the screen), a Tier-XI skill-tree tank (available
  chips → openSkillTree, final tick), an elite tank (grade band), an elite-rewards tank
  (reward thumbs), and a fully-complete tank (badge). Confirm glyphs, tooltips, and that
  each click still fires its action (watch `python.log` for the `[wgmod] <command>`
  LOG_NOTE lines).

## Open questions
- Worth a tiny dev-time assertion that every `CAT.*`/`MODE.*` the renderer switches on
  is covered? Probably overkill for a 6-value enum; the live sweep is enough.
- The `node --check` syntax gate catches a JS parse error but NOT a wrong string value —
  so live verification is the real safety net here.

_Background: memory note `tier-3d-refactor-handoff.md` (Tier 3g shipped `a03ae26`);
the refactor campaign's last open thread._
