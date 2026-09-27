#!/usr/bin/env bash
# PostToolUse hook (Edit|Write|MultiEdit): fast per-file check for shipped Python.
#
# For a src/**/*.py file: compile it under Python 2.7 (the game's interpreter -- a
# py3-only construct like an f-string fails here) and lint it with ruff (the repo's
# pyproject set). On failure print a short block to stderr and exit 2, which Claude
# Code feeds back to the model. Every other file: exit 0 silently. A missing tool is
# a one-line note, never a block.
set -uo pipefail

PY27="C:/Python27/python.exe"

input="$(cat 2>/dev/null || true)"
file="$(printf '%s' "$input" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*"' | head -1 \
  | sed -E 's/^"file_path"[[:space:]]*:[[:space:]]*"(.*)"$/\1/; s#\\\\#/#g')"

case "$file" in
  src/*.py|*/src/*.py) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

fail() {  # $1 = tool, $2 = output
  { printf '[check-fast] %s failed: %s\n' "$1" "$file"; printf '%s\n' "$2" | head -n 12; } >&2
  exit 2
}

# Compile in memory (no .pyc written next to the source).
if [ -x "$PY27" ]; then
  out="$("$PY27" -c 'import sys; compile(open(sys.argv[1], "rU").read(), sys.argv[1], "exec")' "$file" 2>&1)" \
    || fail "py27 compile" "$out"
else
  echo "[check-fast] $PY27 not found; skipped py27 compile" >&2
fi

if ! command -v py >/dev/null 2>&1; then
  echo "[check-fast] py launcher not found; skipped ruff" >&2
  exit 0
fi
out="$(py -3.13 -m ruff check --quiet --force-exclude "$file" 2>&1)" && exit 0
case "$out" in
  *"No module named ruff"*|*"No suitable Python runtime"*)
    echo "[check-fast] ruff (py -3.13 -m ruff) not available; skipped lint" >&2; exit 0 ;;
esac
fail "ruff" "$out"
