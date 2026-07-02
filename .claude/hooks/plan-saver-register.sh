#!/usr/bin/env bash
# Register THIS session as the active plan-saver session.
#
# Run by the wgmod-plan-saver skill when it activates. It copies the current
# session id (stashed by sync-ideas.sh into .git/.current-session on this same
# turn — UserPromptSubmit hooks run before the model) into
# .git/.plan-saver-session. From then on, sync-ideas.sh will nudge only this
# session when another session pings by editing IDEAS.md during cleanup.
#
# Overwrites any stale registration (previous plan-saver session), so the most
# recently activated plan saver owns the role. On registering, it reports any
# pending pings so the freshly activated plan saver knows to reconcile.
set -uo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
current="$repo_root/.git/.current-session"
registered_file="$repo_root/.git/.plan-saver-session"
pings="$repo_root/.git/.plan-saver-pings"

if [ ! -f "$current" ]; then
  echo "No session id recorded yet (sync-ideas.sh has not run this session). Send a prompt first, then re-run."
  exit 0
fi

sid="$(head -1 "$current" 2>/dev/null || true)"
if [ -z "$sid" ]; then
  echo "Could not read current session id from $current."
  exit 0
fi

printf '%s\n' "$sid" > "$registered_file" 2>/dev/null || true
echo "Registered plan-saver session: $sid"

if [ -s "$pings" ]; then
  n="$(wc -l < "$pings" 2>/dev/null | tr -d ' ')"
  echo "Pending pings from other sessions: ${n:-?} — reconcile the task list against IDEAS.md now."
fi
exit 0
