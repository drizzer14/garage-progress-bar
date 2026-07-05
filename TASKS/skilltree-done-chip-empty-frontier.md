# Research: Skill-tree done chip never promotes when the unlock empties the frontier

_Submitted: bug hunt (2026-07-05) · Status: open_

## Summary
A tier-XI node unlocked via the bar becomes a "done" chip only after `recent._is_done`
confirms it. For skill-tree records the confirmation is "the node left the available
list" — but guarded by `bool(avail)`, so if unlocking that node leaves the frontier EMPTY
while the tree is NOT yet complete (every remaining node still prereq-locked), the pending
record can never confirm and silently expires after 5 reconciles: no done chip, no error.
Confidence: low-medium — the mechanism is verified; the trigger needs a DAG shape whose
frontier collapses to empty mid-tree, which may not exist in live tier-XI trees. (If the
unlock COMPLETES the tree, the mode leaves SKILL_TREE anyway and no chip would render —
that case is fine.)

## Findings
- The guard: `adapter/recent.py:173-177` — `return bool(avail) and (item_id not in
  avail)`. The comment says exactly why: a degraded `[]` read must NOT read as "done"
  (the readers fail soft to empty lists), so absence alone is untrustworthy.
- Expiry: an unconfirmed pending is dropped after `_PENDING_MAX_RECONCILES = 5`
  (`recent.py:44,124-127`) — correct behavior for a cancelled click, silent-loss behavior
  here.
- Chip injection only happens in SKILL_TREE mode (`recent.py:141-143`), so the
  tree-completed case is moot by design.
- Contrast: tech-tree/field-mod records confirm by POSITIVE evidence (presence + flag,
  `recent.py:159-171`) because their snapshots retain done items; the skill-tree snapshot
  has no per-node researched flag (`skilltree_available` is frontier-only,
  `types.py:240-243`).

## Root cause
No positive per-node evidence in the skill-tree snapshot forces an absence test, and the
degraded-read guard (correct on its own) makes "legitimately empty frontier" and "failed
read" indistinguishable.

## Suggested approach
Add positive evidence instead of loosening the guard: `record()` for SKILLTREE captures
the snapshot's current `skilltree_done` count; `_is_done` confirms when a fresh snapshot
shows `skilltree_done` strictly greater (count grew ⇒ a node was received ⇒ the recorded
click succeeded — per-vehicle keying already scopes it). Keep the absence test as a
secondary condition if extra strictness is wanted. Engine-free, fully unit-testable.

## Touch points
- `src/res/scripts/client/wgmod_research/adapter/recent.py:52-74 (record), 155-180
  (_is_done)`
- `tests/test_recent.py` — cases: frontier empties + done-count grows → promotes;
  degraded `[]` read with unchanged count → defers; cancelled click (count unchanged) →
  expires as today.

## Verification
Unit tests above (pure domain). In-game spot-check optional: on a tier-XI tank, unlock a
node whose siblings are all locked and watch for the done chip.

## Open questions
- Does any live tier-XI tree actually have a frontier-collapsing shape? (REPL probe of
  the tree DAG would settle severity; the count-based fix is strictly more robust either
  way.)
