# Research: Purchase price (credits) on "done" tick tooltips

_Submitted: "Add purchase price for 'done' ticks' tooltips. Use the same design as xp." · Status: open_

## Summary
A "done" tick (an item researched via the bar this session — green check, opens the
native screen on click) currently shows **no footer** in its tooltip. Since a
researched item still costs **credits to buy**, show that purchase price in the
done tooltip, styled exactly like the existing XP cost line.

## Findings

### The XP footer design to mirror (widget JS)
`src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.js`:
- `XP_ICON = "img://gui/maps/icons/vehicle_hub/research_purchase/total_experience.png"`
  and `xpIco(url)` builds the inline currency glyph as a `background-image` span
  (Gameface clips `<img>`) with class `.wg-tip-xp-ico`.
- `xpFracHtml(have, need, iconUrl, vehHave)` is the "foot" cost builder: a
  `.wg-tip-xp` headline row (cost figure + glyph), turning `.wg-tip-xp wg-tip-short`
  when unaffordable, with an optional `.wg-tip-xp-rem` shortfall sub-line. It
  **early-returns `""` when `need <= 0`** — handy: a 0 price naturally renders
  nothing.
- `fmtXp(n)` formats with a space thousands-separator.
- `tooltipHtml(t, spendableXp, fillVehicle)` assembles the footer. The critical
  hook: **the done branch forces the footer empty** —
  ```js
  if (t.done) { foot = ""; }          // ~js:469-471  <-- inject the credits line here
  else if (t.locked) { ... }
  else { foot = xpFracHtml(spendableXp, t.position, XP_ICON, fillVehicle); }
  return joinSections([tipMain(tickIconHtml(t), text), foot]);
  ```
- Chip tooltips do the same in `renderNextAvailable(...)`:
  `const cFoot = u.done ? "" : xpFracHtml(...)`.

### The CSS to clone
`src/res/gui/gameface/mods/14th_ua/WGModResearch/WGModResearch.css`:
- `.wg-tip-xp` — flex row, `font-size:16rem`, `font-weight:700`, `color:#ecca9d`
  (currency tan). `.wg-tip-xp-ico` — 14rem square, `background-size:contain`.
- Mirror these into `.wg-tip-credits` / reuse `.wg-tip-xp-ico` geometry with a
  credits glyph. (Simplest: reuse `xpIco`/`.wg-tip-xp` as-is and just pass the
  credits icon URL — a distinct tint is optional. Match the game's credit tone,
  a pale gold ~`#f2d16f`, only if you want the two lines visually distinguished.)

### The credits icon asset (verified present in the game packages)
Best match for the XP tooltip glyph (same size/context):
**`img://gui/maps/icons/components/tooltip/credits.png` = 16×16** (confirmed in
`res/packages/gui-part*.pkg`). Alternatives: `library/currency/credits_16x16.png`
(16×16), `library/CreditsIcon-1.png` (16×16). Use the `components/tooltip/` one for
parity with how the XP glyph reads in tooltips.

### Data flow — where to add a `price` field
End-to-end chain the value must travel (done ticks are synthesized at click-time,
so the price has to be captured then and threaded through the recent store):

1. **Adapter reads price** — `adapter/engine_adapter.py:_read_tech_unlocks` (`:141-187`).
   The GUI item is already fetched at `:151` (`item = cache.items.getItemByCD(int_cd)`).
   Read the credits buy-price here and pass it into the `UnlockItem(...)` ctor
   (`:178-183`). Expected WoT API (verify — see Open questions):
   ```py
   def _credits_price(item):
       try:
           from gui.shared.money import Currency
           return int(item.buyPrices.itemPrice.price.getSignValue(Currency.CREDITS) or 0)
       except Exception:
           return 0
   ```
2. **`UnlockItem`** — `domain/types.py:85-101`: add a `credits_price=0` field.
3. **Capture at click-time** — `bridge/gameface_bridge.py:_record_click` (`:359-397`)
   reads the fresh snapshot's `UnlockItem` just before research fires and calls
   `recent.record(..., xp_cost=getattr(u,"xp_cost",0))` (`:373-375`). Add
   `credits_price=getattr(u,"credits_price",0)`.
4. **Recent store** — `adapter/recent.py`: `record(...)` (`:50-67`) stores a dict;
   add `credits_price`. `_make_tick(rec)` (`:138-148`) synthesizes the done tick;
   set `tick.credits_price = rec["credits_price"]` (mirrors how `tick.done = True`
   is attached at `:147`).
5. **`Tick`** — `domain/types.py:32-82`: add a `credits_price=0` field (or leave it
   monkey-patched like `done` — match whichever pattern the implementer prefers;
   `done` is attached dynamically, `xp_cost` etc. are ctor fields).
6. **Bridge marshal** — `bridge/gameface_bridge.py` `TickVM` (`:493-562`): bump
   `properties=16` → `17`, add `self._addNumberProperty("price", 0)  # 16` in
   `_initialize` + a `setPrice` setter, and in the tick marshal loop (`:796-814`,
   next to `tv.setDone(...)` at `:813`) add
   `tv.setPrice(getattr(t, "credits_price", 0) or 0)`.
7. **JS reads `t.price`** and, in the done branch (~`js:469`), builds the credits
   line instead of `""`.

### "Done" semantics (the gate)
- `Tick.done` = researched **this session via the bar**, not necessarily purchased.
  Attached in `recent.py:147`; marshaled via `getattr` at `gameface_bridge.py:813`;
  gates the empty footer at `WGModResearch.js:469-471`. This is exactly the state
  where a credits purchase price is meaningful (unlocked → now costs credits to buy).
- `UnlockItem.researched` (`types.py:87`, set at `engine_adapter.py:181`) is the
  account-persistent state; the techtree resolver drops researched items
  (`techtree.py:8`), so they never become normal ticks — only the session done
  marker surfaces them. So the credits line lives strictly in the `t.done` branch.

## Suggested approach
1. Adapter: add `_credits_price(item)` and populate `UnlockItem.credits_price`
   (guarded, `_safe`-style). Works for both module and next-vehicle unlocks.
2. Thread it through `_record_click` → `recent.record` → `_make_tick` → `Tick`.
3. Bridge: add the `price` VM property (bump count, add setter, marshal it).
4. JS: in the done branch of `tooltipHtml` (and the chip equivalent), when
   `t.price > 0` emit a credits line built like `xpFracHtml` but with the credits
   glyph — simplest is a tiny `creditsHtml(price)` that reuses `.wg-tip-xp` +
   `xpIco(CREDITS_ICON)`. A 0 price renders nothing (design already early-returns).
5. CSS: reuse `.wg-tip-xp`/`.wg-tip-xp-ico`; add a credits tint only if desired.

## Touch points
- `adapter/engine_adapter.py:151,178-183` — read + pass credits price.
- `domain/types.py` — `UnlockItem` (and maybe `Tick`) new `credits_price` field.
- `bridge/gameface_bridge.py:373-375` (`_record_click` capture), `:493-514` +
  `:796-814` (`TickVM` property + marshal).
- `adapter/recent.py:50-67` (`record`), `:138-148` (`_make_tick`).
- `WGModResearch.js` — `xpIco`/`xpFracHtml` neighbors + the `t.done` branch of
  `tooltipHtml` and `renderNextAvailable`; add `CREDITS_ICON` const.
- `WGModResearch.css` — `.wg-tip-xp`/`.wg-tip-xp-ico` (reuse or clone).

## Verification
- REPL (wgmod-debug-repl): on a researched-but-unowned module/vehicle item, confirm
  the `item.buyPrices.itemPrice.price.getSignValue(Currency.CREDITS)` chain returns
  a sane credits figure; confirm `img://gui/maps/icons/components/tooltip/credits.png`
  loads.
- In-game (relaunch — overlay loads at launch): research an item via the bar so it
  becomes a done tick, hover it, confirm the credits price shows under a divider in
  the XP-line style.
- No pytest for the adapter path (needs live GUI items); the recent-store threading
  (`record`/`_make_tick` carrying the new field) IS unit-testable — extend
  `tests/test_recent.py`.

## Open questions
- **Confirm the buy-price API** — is it `item.buyPrices.itemPrice.price` /
  `Currency.CREDITS`, or `item.getBuyPrice(...)`? The decompiled EU 2.3 sources are
  not local and `game-api.md` doesn't document buy prices — verify via REPL before
  wiring it in.
- **Suppress once owned?** The done tick's price is captured at click-time, so it
  would keep showing even after the player buys the module in the same session. If
  that's unwanted, either (a) set `credits_price=0` in the adapter when the item is
  already owned (`item.isInInventory`/`inventoryCount` — verify), or (b) re-read the
  price on each sync in `decorate()` rather than trusting the click-time capture.
  Decide desired behavior with the user.
- Should the line show for **next-vehicle** done ticks too, or **modules only**?
  (Both have credit prices; vehicles are pricier.)
