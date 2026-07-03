# Research: Verify tooltip icons use the highest-quality assets

_Submitted: "Verify tooltip icons use the most high quality assets possible" · Status: shipped_

## Summary
Audit of every icon rendered in a tooltip to confirm each pulls the largest
resolution variant the game ships, so nothing looks blurry when displayed in the
52rem tooltip icon box (and upscaled further on 4K). Verdict: **two real gaps** —
(1) tech-tree **module** glyphs have an 80×80 `Big` variant the mod isn't using
(the plain 48×48 is upscaled in the box; the tech-tree screen itself uses `Big`),
and (2) the reward-thumbnail fallback uses the `"small"` bonus icon. Grade emblems,
vehicle nodes, and skill perks are already on the largest variant that ships.

> Reassessment note: the original audit claimed modules ship nothing larger than
> 48×48. That was **wrong** — see the module row below. Corrected after the user
> reported clearly higher-quality module art in the tech tree.

## Findings

Tooltip icons all flow to JS as `t.icon` / `u.icon` and are painted as a
`background-image` by `bgIconHtml()` (`WGModResearch.js:350-352`) into a fixed
**52rem × 52rem** box — `.wg-tip-icon` (`WGModResearch.css:862-877`,
`background-size: contain`). The grade-emblem variant `.wg-tip-icon-elite` is
44rem (`css:881-886`). No size params ride in the URLs; sizing is 100% CSS, so the
only quality lever is which source asset Python hands over.

Category-by-category (source native res → 52rem box):

- **Grade emblems (elite)** — `img://…/prestige/emblem/72x72/<family>/<sub>.png`,
  built in `domain/resolvers/elite.py:28-36`. **72×72**, downscaled into the box.
  Already consciously maximized: `elite.py:24-27` documents the deliberate upgrade
  from 48×48 (which "renders see-through/grey when scaled up") to 72×72. ✅ optimal.
- **Vehicle / Tier-XI node icons** — `item.icon` from the GUI item
  (`adapter/engine_adapter.py:153-160`), ~160×100. The code explicitly *rejects*
  the smaller `iconSmall` carousel strip in favor of the larger `icon`
  (comment at `engine_adapter.py:157-159`). ✅ optimal.
- **Skill-tree perks** — `img://…/skillTree/tree/perks/<type>/skills/large/<name>.png`,
  built in `engine_adapter.py:190-201`. Hardcodes the `large` (40×40) segment; the
  docstring notes only small(32)/large(40) exist. `large` is the max variant, so
  40×40 in a 52rem box is a slight upscale but there is **nothing higher to
  switch to**. ✅ best available.
- **Modules** (gun/turret/engine/chassis/radio) — `item.icon` →
  `img://gui/maps/icons/modules/<type>.png`, ~48×48 (`engine_adapter.py:153-160`).
  ⚠️ **actionable gap.** The generic module-TYPE glyphs ship in the *same directory*
  in two sizes (verified in `res/packages/gui-part*.pkg`):
  - `gui/maps/icons/modules/gun.png` = **48×48** (what `item.icon` returns)
  - `gui/maps/icons/modules/gunBig.png` = **80×80** (the higher-quality variant)
  Confirmed pairs: `gun`/`gunBig`, `tower`/`towerBig`, `chassis`/`chassisBig`,
  `engine`/`engineBig`, `radio`/`radioBig`, `wheeledChassis`/`wheeledChassisBig` —
  all 48×48 → 80×80. The tech-tree research screen uses the `Big` set, which is the
  higher-quality art the user sees; the mod uses the plain 48×48, so it upscales in
  the 52rem box. (There's also 64×64 `hangarTutorial/modules/*.png` and huge
  1124×780 `manual/backgrounds/*.png`, but those are different glyphs / render art,
  not the tech-tree type icon — `Big` at 80×80 is the right target.)
- **Currency glyphs** — Total-XP `total_experience.png` 16×16 shown at 14rem
  (`js:44`, `css:999-1007`); combat-XP `xpIcon_23x22.png` 23×22 (`js:50`). Both
  downscaled or 1:1. ✅ fine.
- **Reward thumbnails (elite_rewards)** — `_read_reward_art`
  (`engine_adapter.py:577-611`). Prefers `c11n.icon` (style previewIcon, img://),
  then `c11n.iconUrl` (`getTextureLinkByID`, high-res), then **falls back to
  `c11n.getBonusIcon("small")` at `engine_adapter.py:603`**. That `"small"` asset
  is then displayed at **30rem on the tick and 52rem in the tooltip** — a small
  asset shown large. ⚠️ **the one actionable gap.** Only bites reward types that
  fall through both preferred branches.

## Root cause (of the two gaps)
- **Modules:** `engine_adapter.py:160` takes `item.icon` verbatim, which resolves
  to the 48×48 `img://gui/maps/icons/modules/<type>.png`. The 80×80 `Big` sibling
  in the same directory (what the tech-tree screen uses) is never requested, so a
  48×48 glyph upscales into the 52rem box.
- **Rewards:** `engine_adapter.py:603` requests the `"small"` size from
  `c11n.getBonusIcon(size)`. Larger variants exist; `"small"` caps the fallback
  thumbnail at the smallest raster, which then upscales in the 30–52rem boxes.

## Suggested approach
1. **Modules → `Big` (recommended, high value):** upgrade the module icon to the
   80×80 variant. Cleanest spot is the adapter, right after `icon = item.icon`
   (`engine_adapter.py:160`) — for the module kind, rewrite the trailing
   `<type>.png` → `<type>Big.png` (e.g. a regex/`str.replace` on
   `"gui/maps/icons/modules/"` filenames), and only keep the swap if the `Big`
   asset actually exists (fall back to the plain path otherwise). Confirm
   `item.icon`'s exact returned string first (see Open questions) so the swap
   targets the real filename. This gets an 80×80 asset into the 52rem box — no more
   upscaling — and matches what the tech tree shows. Do NOT apply the swap to the
   vehicle kind (its `item.icon` is a different, already-large node art).
2. **Rewards → larger `getBonusIcon`:** swap `getBonusIcon("small")` → the largest
   size the API accepts (likely `"big"`, but confirm the valid arg strings — see
   Open questions). Guard the same way (`_safe`, must still `startswith("img://")`).
   One-line win for the fallback path only.
3. Leave grade emblems, vehicle nodes, and skill perks as-is — already on the
   largest ships-with-the-game variant. (Skill perks' `large` = 40×40 is the max
   the game ships; if its upscale is ever objectionable, the only lever is
   shrinking the tooltip icon box for that category — cosmetic, low priority.)

## Touch points
- `src/res/scripts/client/wgmod_research/adapter/engine_adapter.py:160` — module
  icon; add the `<type>` → `<type>Big` swap for the module kind (the high-value
  change).
- `src/res/scripts/client/wgmod_research/adapter/engine_adapter.py:603` — the
  `getBonusIcon("small")` reward fallback.
- (Only if pursuing the perk box-shrink idea) `WGModResearch.css:862-877`
  (`.wg-tip-icon`) + a per-category class hook.

## Verification
- REPL (wgmod-debug-repl): for a module unlock item, print `item.icon` to confirm
  the exact `img://gui/maps/icons/modules/<type>.png` string and that the `Big`
  sibling loads (`gunBig.png` etc. verified present in `gui-part*.pkg`). For
  rewards, resolve a `c11n` bonus item that falls through to the bonus-icon branch
  and call `getBonusIcon("big")` vs `("small")`.
- In-game (relaunch — overlay loads at launch): hover a tech-tree module tick,
  confirm the glyph is crisp (80×80 source, not the upscaled 48×48); hover a
  non-style elite reward tick, confirm a crisper thumbnail.
- No pytest coverage — the icon paths need live GUI items (adapter unimportable
  under pytest).

## Open questions
- **Confirm `item.icon`'s exact string for a module** — is it literally
  `img://gui/maps/icons/modules/gun.png` (so a filename swap to `gunBig.png` works),
  or does the module GUI item expose a `Big`/large getter directly? Check via REPL
  or the decompiled `gui.shared.gui_items` module-icon property (EU 2.3 sources not
  local — re-clone per `tools/dev/README.md`).
- **Exact valid size args for `c11n.getBonusIcon(size)`** — `"big"`, a dimension
  string, or an enum? Confirm before changing the literal.
- Is the reward-fallback branch even reached in practice, or do real elite rewards
  always resolve via `c11n.icon`/`c11n.iconUrl`? If effectively dead, that half is
  a no-op-in-practice cleanup — the module `Big` swap is the higher-value change.
