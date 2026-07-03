# Research: Release 0.4.0 (gated on all other open items)

_Submitted: "Release 0.4.0 must be done when all other items are resolved" · Status: open_

## Summary
Cut the **0.4.0** release once every other open backlog item is *shipped* — not
merely code-complete, but verified in-game and committed. This entry is the gate /
reminder; the release mechanics themselves are the `wgmod-release` skill's job.

## Findings
- Current version is **0.3.0**, unreleased (per the memory handoffs). The batch of
  open ideas is code-complete + built against 0.3.0 but NOT deployed/verified/
  committed, so nothing is shipped yet.
- The release procedure is fully specified in the **`wgmod-release`** skill: bump
  the version across all 7 files, commit + tag, build the `.wotmod` + Windows
  installer + consumer zip, publish the GitHub release. Do not duplicate those
  steps here — invoke that skill when the gate opens.

## Gate — all of these must be shipped (verified in-game + committed) first
1. Shift current-position glow marker left onto the fill — `IDEAS/current-glow-marker-offset.md`
2. Max-width cap for tooltips — `IDEAS/tooltip-max-width.md`
3. Tech-tree / tier-XI-reward tooltip icons too tall — `IDEAS/tooltip-icons-too-tall.md`
4. Tooltip icons — use highest-quality assets — `IDEAS/tooltip-icon-quality.md`
5. Purchase price (credits) on "done" tick tooltips — `IDEAS/done-tick-purchase-price.md`
6. Bar disappears completely on a mode transition — `IDEAS/mode-transition-bar-disappears.md`

(Whether 0.4.0 vs 0.3.0 is the right number is the maintainer's call — this note
just tracks "release when the rest are done." Adjust the version if a 0.3.0 release
is cut first.)

## Suggested approach
When the last gating item is verified + committed, run the `wgmod-release` skill for
0.4.0. Before publishing, confirm each item above is genuinely shipped (the memory
handoffs and git log are the record) and prune each from `IDEAS.md`.

## Touch points
- The 7 version files (enumerated in `wgmod-release`).
- `IDEAS.md` — prune the six entries above as they ship; delete this entry once the
  release is published.

## Verification
- The `wgmod-release` skill's own checklist (build artifacts, tag, GH release Latest).
- Sanity: a clean packaged build deployed + relaunched in-client before tagging.

## Open questions
- Version number: 0.4.0 as stated, or 0.3.0 if no 0.3.0 release ships first?
- Do all six gate the release, or would the maintainer ship a subset and defer the
  rest (e.g. release the polish items, hold the mode-transition bug if it needs a
  repro)?
