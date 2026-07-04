# Research: Blueprint discounts ignored for the next-vehicle tick (wrong affordability + silent failure)
_Submitted: full-codebase bug sweep (2026-07-04) · Status: open_

## Summary
When the player holds blueprint fragments for the next vehicle, the bar prices the
vehicle tick at the UNDISCOUNTED cost: affordability shading understates what they
can buy, and clicking in the between-costs window ends in WG's exchange-XP dialog or
a **silent** post-confirm failure. Modules are NOT affected — for them the raw cost
is byte-identical to WG's own context-menu handler and required by the validator.
Verified against the local decompiled EU client source (`C:\Users\Dmytro
Vasylkivskyi\wot-eu\source`).

## Findings
- Mod side: `adapter/actions.py:123-126` builds
  `UnlockProps(veh.intCD, unlockIdx, xp_cost, required, 0, xp_cost)` from the raw
  `getUnlocksDescrs()` row; domain affordability uses the same raw cost
  (`domain/resolvers/techtree.py:9-19`); the bar includes next vehicles
  (`adapter/tech_read.py:33-41`).
- Blueprint discounts exist ONLY for vehicle nodes:
  `blueprints_requester.py:109-118` (`getBlueprintDiscount` returns 0 for non-vehicle
  CDs). WG folds them in via `techtree_dp.py:141-161` / `getUnlockProps` (:254-256).
- Module path is CORRECT as-is: WG's own cm-handler builds identical props
  (`research_cm_handlers.py:38-40`), and the module validator REJECTS a cost that
  differs from the raw graph cost (`techtree/unlock.py:105-111`,
  `xp_cost_invalid`) — "folding the discount in" for modules would be a new bug.
- Vehicle-path consequences with raw cost:
  - `items_actions/actions.py:333-336` gates on the props' cost → a player between
    discounted and full cost is routed into `ExchangeXpMeta` (`:373-377`) instead of
    a direct unlock (and may convert more free XP than needed — user-confirmed but
    mispriced).
  - Vehicle validator `unlock.py:115-117` blocks with the raw cost — and its
    `makeError()` carries an EMPTY userMsg, and `_UnlockItem._showResult`
    (`items_actions/actions.py:344-350`) only shows `result.userMsg` → confirm
    dialog appears, then NOTHING (silent failure).
  - The confirm dialog itself shows the undiscounted price (`unlock.py:43-56`,
    `makeCostCtx` :18-25 ignores the discount field).
  - No wrong spend is possible: the server computes the real cost
    (`unlock.py:131-133` sends only `vehTypeCD, unlockIdx`).
- Verifier also settled the related "async failures = dead click" sweep claim:
  mostly REFUTED — WG's confirm dialog is the first async link and field-mod/tech
  errors surface as system messages; the one silent case is exactly this empty-
  userMsg XP failure. (Doc nit: `actions.py:6-8` overclaims "everything degrades to
  opening the native screen" — async-phase failures bypass the except.)

## Root cause
`_find_unlock_row`/`_do_research` price the vehicle unlock from the raw descriptor
row; neither the domain affordability nor the UnlockProps consult
`IBlueprintsRequester`/`techtree_dp` discount data.

## Suggested approach
Vehicle ticks only: read the discounted cost via the game's own path — either
`techtree_dp.getUnlockProps`-equivalent or
`blueprints_requester.getBlueprintDiscountData` — in `tech_read.py` (a new
`xp_cost_discounted` on the vehicle UnlockItem, feeding tooltip + affordability) and
in `actions.py` (build UnlockProps with `(newCost, topIDs, discount, xpFullCost)`
like `techtree_dp.py:151-154`). Leave module rows untouched. Symbols need live REPL
confirmation before implementing (the decompiled source is authoritative for shape,
not availability).

## Touch points
- `src/res/scripts/client/wgmod_research/adapter/tech_read.py:33-41`
- `src/res/scripts/client/wgmod_research/adapter/actions.py:111-127`
- `src/res/scripts/client/wgmod_research/domain/resolvers/techtree.py` (if a
  discounted-cost field is added to the tick)
- `.claude/skills/wgmod-architecture/references/game-api.md` (record the new symbols)

## Verification
Live only (needs an account state with fragments): hold blueprint fragments on a
next vehicle, spendable XP between discounted and full cost → tick must show
affordable + discounted cost; click → direct unlock confirm at the discounted price.
REPL: `dependency.instance(IBlueprintsRequester).getBlueprintDiscount(vehCD, ...)`.

## Open questions
- Whether to ALSO show the discount on the tooltip ("~~50 000~~ 40 000 XP") or just
  use the effective number.
- REPL-confirm `IBlueprintsRequester` skeleton name + `getBlueprintDiscountData`
  signature in EU 2.3 before coding.
