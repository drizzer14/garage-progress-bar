# Research: Show total XP near the Tier-XI upgrades counter

_Submitted: "Add total xp to tier xi skill tree progression near the upgrades counter" · Status: open_

## Summary
In skill_tree (Tier-XI upgrades) mode the header shows a count-based readout
("N/M" upgrades + counter glyph) *instead of* the total-XP readout that every other
mode shows. The user wants the vehicle's total spendable XP surfaced near that
counter too. **This is a pure-frontend change** — total XP (`vehicle_xp + free_xp`)
is already computed, set on the skill_tree model, and pushed to the widget as
`data.spendableXp`; it's just never rendered as a header figure in this mode.

## Findings
### The header has one readout slot; skill_tree repurposes it
`.wg-xp` (holding `.wg-xp-val` + `.wg-xp-ico`) is built once in `ensureRoot()`
(`WGModResearch.js:519-522`). Every mode fills it with total XP + `XP_ICON` via
`setXp()`, **except** skill_tree, which swaps in the counter glyph + "N/M":
`WGModResearch.js:866-876`
```js
if (mode === "skill_tree") {
    root.querySelector(".wg-xp-ico").style.backgroundImage =
        "url('" + SKILL_COUNTER_ICON + "')";
    root.querySelector(".wg-xp-val").textContent =
        (data.fieldModsDone || 0) + "/" + (data.fieldModsTotal || 0);
} else {
    setXp(root, data.fillVehicle, data.fillFree);
}
```
- Counter icon: `SKILL_COUNTER_ICON = "img://gui/maps/icons/skillTree/tree/counter.png"`
  (`WGModResearch.js:35`). XP icon: `XP_ICON = ".../total_experience.png"` (`:44`).
- Readout CSS: `.wg-xp`/`.wg-xp-val`/`.wg-xp-ico` at `WGModResearch.css:127-154`;
  header flex `space-between` `.wg-head` at `:54-60`.
- **A spare, currently-hidden header-left text slot `.wg-upgrades` exists**
  (built `WGModResearch.js:517`, hidden via `setUpgrades(el,0,0)` at `:852`, helper
  `:436-445`, CSS `:115-122`). It's a natural host for the *second* figure so counter
  and XP can sit side by side without restructuring `.wg-xp`.

### The XP pattern to mirror — but don't reuse `setXp()` directly
`setXp(root, vehXp, freeXp)` (`WGModResearch.js:448-456`) sums its two args for the
total. In tech-tree/field-mods those args (`fillVehicle`/`fillFree`) *are* the XP
segments, so it works. **In skill_tree `fillVehicle` is a node COUNT and `fillFree`
is 0**, so `setXp()` as-is would show the wrong number. Use `data.spendableXp`
instead (already the correct total in every mode), formatted with `fmtXp(n, ",")`.

### The data is already available to the skill_tree branch
`render()` unwraps at `WGModResearch.js:856-864`: `data.spendableXp` (**= correct
total XP**), `data.fillVehicle` (node count here), `data.fillFree` (0),
`data.fieldModsDone/Total` (the counter), `data.availUpgrades`. `spendableXp` is
already consumed for per-chip affordability (`renderNextAvailable`
`WGModResearch.js:555`, `:590`), proving it's live and correct in this mode.

### Python: total XP is plumbed to skill_tree already (no changes needed)
`builder.py:104-115` builds the skill_tree model with `fill_vehicle=st["fill"]` (node
count), `fill_free=0` (confirms the widget note), **and `spendable_xp=spendable`**.
`spendable` is defined at `builder.py:61-65` as `vehicle_xp + free_xp`. It lives on
`ResearchProgressModel.spendable_xp` (`types.py:224,235`) and is pushed to the VM on
every render as `spendableXp` (`gameface_bridge.py:554`, setter `:622-623`, push
`:718`). So total XP is end-to-end available with no new plumbing.
- Aside: `VehicleSnapshot` also has `skilltree_total_xp` / `skilltree_spent_xp`
  (`types.py:202-203`) — "XP invested / XP to fully upgrade" — but these are
  informational and **not** plumbed to the VM. Only if the user wanted *those*
  (rather than plain spendable XP) would new plumbing be needed. Plain total spendable
  XP does not.

### Is total XP meaningful here? Yes
Tier-XI upgrade nodes are XP-priced (same currency as research): resolver builds ticks
with `xp_required` and `avail_upgrades` carrying per-node `xp_cost`
(`domain/resolvers/skilltree.py:48,60-61`), and chips already compare cost against
`spendableXp` (`WGModResearch.js:590`). The resolver's "XP axis is meaningless"
docstring (`skilltree.py:5-11`) is only about the *bar scale* being non-linear, not
about XP being irrelevant — the total XP readout tells the player how much currency
they have toward the next upgrade, consistent with the per-chip affordability.

### i18n
Not required for an icon + number (mirrors the label-less counter, which is a bare
glyph + "N/M" with no wired caption). Only a *worded* caption (e.g. "XP:") would need
`adapter/i18n.py` (`_FALLBACK` `:57-72` + `widget_labels()` `:79-140`, read via `L()`),
and the WG resource id would need REPL confirmation per the module's no-guess policy.

## Suggested approach
Edit the skill_tree branch of `render()` (`WGModResearch.js:866-876`) to show **both**
the upgrades counter and total XP. Two layout options:
- **(A) Reuse the hidden `.wg-upgrades` slot** for one of the two figures (e.g. counter
  in `.wg-upgrades`, XP in `.wg-xp` via a spendableXp-based setter), so both read
  cleanly on opposite sides of the header. Cleanest; uses an existing slot.
- **(B) Combine into `.wg-xp`** — e.g. counter glyph + "N/M" and then the XP glyph +
  number in the same right-side group. More compact but needs the group to hold two
  icon+value pairs.

Either way, format XP with `fmtXp(data.spendableXp, ",")` and use `XP_ICON` — do NOT
call `setXp()` (it would sum the node-count `fillVehicle`). No Python/VM/i18n changes.

Feasibility: high — a handful of JS lines + minor CSS for the two-figure layout.

## Touch points
- `WGModResearch.js`: skill_tree branch `:866-876`; the `.wg-upgrades` slot helper
  `setUpgrades` `:436-445` (if option A); `fmtXp` `:` for formatting; `XP_ICON` `:44`.
- `WGModResearch.css`: `.wg-xp*` `:127-154`, `.wg-upgrades` `:115-122`, `.wg-head`
  `:54-60` — adjust spacing for the second figure.
- No Python / domain / bridge / i18n changes.

## Verification
- Hot-reload JS/CSS (`wgmod-build-deploy`; overlay at launch per
  `dev-loop-no-midsession-overlay`). Switch to a Tier-XI vehicle in skill_tree mode:
  both the "N/M" counter and total XP appear, XP matches the tech-tree readout for the
  same tank, and the number equals `vehicle_xp + free_xp` (not the node count).
- Confirm other modes' single readout is unchanged.
- `pytest` unaffected (frontend-only).

## Open questions
- Layout: counter and XP on opposite sides (`.wg-upgrades` + `.wg-xp`), or combined in
  one group? Decide during live layout tweaking.
- Worded caption or bare glyph+number? (Bare matches the existing counter; a caption
  adds an i18n/REPL step.)
