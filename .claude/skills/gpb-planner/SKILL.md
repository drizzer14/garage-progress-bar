---
name: gpb-planner
description: Backlog keeper for the Garage Progress Bar mod — this repo's TASKS.md/TASKS/ workflow plus its cross-session task-list sync hooks. Use whenever someone hands you an idea or bug to "record"/"save"/"note for later", asks you to be the "planner", wants to scan the repo for unrecorded ideas, or says an idea has shipped and should be pruned. (For the generic capture→research→note→prune workflow and the research-note structure, see the wotmod-planner harness skill.)
---

# Planner for the wgmod

The reusable workflow — the two artifacts (`TASKS.md` backlog + `TASKS/<slug>.md` note), the
note structure, how to research a submission, and how to prune a shipped idea — lives in the
**wotmod-planner** harness skill. This skill adds this repo's concrete wiring: the sibling
skills to lean on, the Task-list mirror, and the cross-session sync hooks.

When researching a submission, lean on the sibling skills for the map: **gpb-architecture**
for the Python data flow, **gpb-widget** for the JS/CSS widget, **gpb-debug-repl** for
locating live game symbols. (These reference the `wotmod-*` harness skills for the shared pattern.)

## On activation: mirror the backlog into the Task list
1. Read `TASKS.md`'s `## Open` section.
2. Create one task per `### entry` via `TaskCreate` — title = entry title; detail = the
   one-line blurb + the `TASKS/<slug>.md` note path. (Settings entries: one task each.)
3. The list is a *mirror* of `TASKS.md` (source of truth), rebuilt from it each time. Keep it
   in sync: add a task when you capture, complete/remove it when you prune. Don't duplicate if
   it already matches this session.
4. **Register as the planner session:** run `bash .claude/hooks/plan-saver-register.sh`.
   This records this session's id in `.git/.plan-saver-session` so that when *another* session
   prunes a shipped idea, you (and only you) get nudged to reconcile. Most recently activated
   planner owns the role; re-registering is cheap and idempotent.

## Cross-session sync (this repo's hooks)
Both keep per-repo state under `.git/` (never committed):
- **`.claude/hooks/sync-ideas.sh`** (`UserPromptSubmit`, every turn/session): stashes the
  session id to `.git/.current-session`; on any content change to `TASKS.md` appends a
  session-tagged **ping** to `.git/.plan-saver-pings`. When the *registered* planner session
  next takes a turn with pings pending, it prints a reconcile nudge and clears the queue.
- **`.claude/hooks/plan-saver-register.sh`**: run on activation (step 4) to claim the role.

Consequences to rely on: you don't manually ping (any session editing `TASKS.md` auto-pings by
virtue of the change); self-edits don't nudge; pings survive an absent planner (queued until
the next session registers); sync is turn-level ("next prompt"), not instantaneous.

## This repo's TASKS layout
- `TASKS.md` (root) — the scannable backlog (`## Open`; `### Title` + blurb + `→ Research:` pointer).
- `TASKS/<slug>.md` — the research note. Shipped notes move to `TASKS/shipped/` with `Status: shipped`.

## Scanning for unrecorded ideas
Sweep with an `Explore` agent for: code TODO/FIXME/"later"/"for now"; doc notes phrased as
planned/wishlist/known-limitation; and "NEXT:"/"optional"/"outstanding" notes in the memory
handoff files. Record only genuine pending ones — research each before it earns a note.

## Conventions
- This role edits `TASKS.md` and files under `TASKS/` (and this skill). No mod code changes.
- Cross-session state (`.plan-saver-session`, `.current-session`, `.plan-saver-pings`,
  `.ideas-md-hash`) lives under `.git/` — never committed, nothing to `.gitignore`. (The hook
  script filenames and these `.git/` state filenames keep their historical names.)
