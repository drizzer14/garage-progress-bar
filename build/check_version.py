# -*- coding: utf-8 -*-
"""Assert the mod version is consistent everywhere.

  python build/check_version.py

`src/meta.xml` <version> is the source of truth. This scans the repo for every
version reference that must track it and fails (exit 1) on any mismatch, printing
each offending file:line. It exists because the version is hand-edited in several
places at release time (see the wgmod-release skill) and drift has slipped through
before (a stale CONTRIBUTING.md filename).

To avoid false positives on the *other* version numbers in the repo (the target
client 2.3.0.1, bundled ModsSettingsAPI 1.7.0 / OpenWG GameFace 1.1.6, etc.) this
matches only patterns that unambiguously carry THIS mod's version:

  * com.14th_ua.garageprogressbar_<v>.wotmod   (the packaged filename)
  * GarageProgressBar-Setup-<v>.exe            (the installer filename)
  * MOD_VERSION = "<v>"                          (mod_wgmod.py)
  * #define ModVersion "<v>"                     (wgmod-setup.iss)
  * version <v>                                  (prose header, e.g. dist/INSTALL.txt)

The last (prose) pattern has a negative lookahead so it matches THIS mod's 3-part
version only, never the 4-part client version ("version 2.3.0.1").

New references written in any of these forms are picked up automatically. On top of
that, a small REQUIRED list names files that must carry at least one reference, so a
file silently LOSING its version reference also fails the check.

The hand-bumped consumer readme (dist/INSTALL.txt) lives under gitignored dist/,
which is otherwise skipped; it is scanned explicitly when present.

It ALSO checks the supported CLIENT version (4-part, e.g. 2.3.0.1) -- a separate value
from the mod version. The single canonical source is build_wgmods_zip.CLIENT_VERSION;
a fixed set of shipping/instruction files (_CLIENT_REQUIRED) must each carry it and must
not carry a differing 4-part client token, so a client patch that misses one file fails.
IP-shaped tokens (the debug REPL's 127.0.0.1) are excluded so they never false-fail.

Runs on Python 2.7 or 3.x (release tooling is 2.7; CI is 3.13).
"""
from __future__ import print_function

import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = os.path.join(ROOT, "src", "meta.xml")
# build_wgmods_zip.py holds the single canonical CLIENT version (the mods/<ver>/ folder the
# bundle extracts into). check_version parses it (not imports -- no side effects) and
# verifies the shipping/instruction files agree, so a client patch can't leave a straggler.
WGMODS_ZIP = os.path.join(ROOT, "build", "build_wgmods_zip.py")

# Directories not worth scanning (build output, VCS, vendored binaries, editor cfg).
_SKIP_DIRS = {".git", "dist", "__pycache__", "node_modules", ".idea", ".vscode",
              "vendor", "assets"}
# Only these extensions hold version references.
_SCAN_EXT = (".md", ".py", ".xml", ".iss", ".ps1", ".txt")

# Under a _SKIP_DIRS folder but scanned anyway (hand-bumped, drift-prone). Relative
# to ROOT; skipped silently when absent (dist/ is gitignored build output).
_EXTRA_FILES = ("dist/INSTALL.txt",)

# Each pattern captures a semver in group 1 that must equal the meta version.
# The prose "version <v>" pattern uses (?!\.\d) so it matches this mod's 3-part
# version but never the 4-part client version ("version 2.3.0.1").
_PATTERNS = [
    re.compile(r"com\.14th_ua\.garageprogressbar_(\d+\.\d+\.\d+)\.wotmod"),
    re.compile(r"GarageProgressBar-Setup-(\d+\.\d+\.\d+)\.exe"),
    re.compile(r'MOD_VERSION\s*=\s*"(\d+\.\d+\.\d+)"'),
    re.compile(r'#define\s+ModVersion\s+"(\d+\.\d+\.\d+)"'),
    re.compile(r"version\s+(\d+\.\d+\.\d+)(?!\.\d)"),
]

# Files that MUST carry at least one version reference. Catches a file silently
# LOSING its reference (which would otherwise pass). Paths are ROOT-relative,
# forward-slashed. README.md is deliberately absent: the consumer restructure
# removed its version ref by design, so requiring one would false-fail. Entries
# under dist/ are checked only when the file exists (gitignored build output).
_REQUIRED = (
    "src/res/scripts/client/gui/mods/mod_wgmod.py",
    "installer/wgmod-setup.iss",
    "installer/build_installer.ps1",
    "INSTALL.md",
    "installer/README.md",
    "dist/INSTALL.txt",
)


# --- client version (4-part, e.g. 2.3.0.1) -----------------------------------
# Canonical source: build_wgmods_zip.CLIENT_VERSION.
_CLIENT_RE = re.compile(r'CLIENT_VERSION\s*=\s*["\'](\d+\.\d+\.\d+\.\d+)["\']')
# A 4-part version token (the client version's shape). Loopback / IP-shaped tokens that are
# NOT the client version are excluded so an unrelated address (the debug REPL's 127.0.0.1)
# never trips the check.
_CLIENT_TOKEN_RE = re.compile(r"\b\d+\.\d+\.\d+\.\d+\b")
_CLIENT_TOKEN_EXCEPTIONS = frozenset(("127.0.0.1", "0.0.0.0"))
# Files that state the supported CLIENT version as a real target / user instruction (NOT an
# illustrative "e.g." example like wgmod-setup.iss's comments, where the installer resolves
# the real version at runtime). Each MUST carry the canonical client version and must not
# carry a DIFFERENT 4-part client token -- so a client bump that misses one fails here, just
# like the mod-version checks. ROOT-relative, forward-slashed.
_CLIENT_REQUIRED = (
    "build/build_wgmods_zip.py",
    "installer/readme.wgmods.txt",
    "README.md",
    "INSTALL.md",
    "CONTRIBUTING.md",
    "CLAUDE.md",
    "tools/dev/README.md",
)


def _meta_version():
    return ET.parse(META).getroot().findtext("version").strip()


def _client_version():
    try:
        with open(WGMODS_ZIP, "rb") as fh:
            text = fh.read().decode("utf-8", "replace")
    except (IOError, OSError):
        return None
    m = _CLIENT_RE.search(text)
    return m.group(1) if m else None


def _check_client_version():
    """Return a list of client-version problems (empty = OK). Scoped to _CLIENT_REQUIRED so
    it never false-fails on prose that merely mentions a version (this file's own examples,
    skill docs, TASKS notes)."""
    problems = []
    client = _client_version()
    if not client:
        return ["could not parse CLIENT_VERSION from build/build_wgmods_zip.py"], None
    for rel in _CLIENT_REQUIRED:
        path = os.path.join(ROOT, rel.replace("/", os.sep))
        try:
            with open(path, "rb") as fh:
                text = fh.read().decode("utf-8", "replace")
        except (IOError, OSError):
            problems.append("%s: unreadable / missing" % rel)
            continue
        tokens = [tok for tok in _CLIENT_TOKEN_RE.findall(text)
                  if tok not in _CLIENT_TOKEN_EXCEPTIONS]
        if client not in tokens:
            problems.append("%s: missing the %s client reference" % (rel, client))
        drift = sorted(set(tok for tok in tokens if tok != client))
        if drift:
            problems.append("%s: stale client version(s) %s (expected %s)"
                            % (rel, ", ".join(drift), client))
    return problems, client


def _iter_files():
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for name in files:
            if name.endswith(_SCAN_EXT):
                yield os.path.join(dirpath, name)
    # Files under an otherwise-skipped dir that we still want checked.
    for rel in _EXTRA_FILES:
        path = os.path.join(ROOT, rel.replace("/", os.sep))
        if os.path.isfile(path):
            yield path


def main():
    expected = _meta_version()
    mismatches = []
    counts = {}  # rel path -> number of version references found
    found_any = False
    for path in _iter_files():
        try:
            with open(path, "rb") as fh:
                text = fh.read().decode("utf-8", "replace")
        except (IOError, OSError):
            continue
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        for lineno, line in enumerate(text.splitlines(), 1):
            for pat in _PATTERNS:
                for m in pat.finditer(line):
                    found_any = True
                    counts[rel] = counts.get(rel, 0) + 1
                    if m.group(1) != expected:
                        mismatches.append((rel, lineno, m.group(1), line.strip()))

    # A required file that carries NO reference (e.g. an edit dropped it silently).
    # dist/INSTALL.txt is only required when it exists (gitignored build output).
    missing = [rel for rel in _REQUIRED
               if not counts.get(rel)
               and (not rel.startswith("dist/")
                    or os.path.isfile(os.path.join(ROOT, rel.replace("/", os.sep))))]

    client_problems, client = _check_client_version()

    rc = 0
    if mismatches:
        print("Version mismatch (src/meta.xml says %s):" % expected)
        for rel, lineno, got, line in mismatches:
            print("  %s:%d  found %s  ->  %s" % (rel, lineno, got, line))
        rc = 1
    if missing:
        print("Missing version reference (src/meta.xml says %s) in required files:"
              % expected)
        for rel in missing:
            print("  %s  (expected at least one %s reference)" % (rel, expected))
        rc = 1
    if not found_any:
        print("WARNING: no version references matched any pattern -- "
              "check_version.py may be stale.")
        rc = 1
    if client_problems:
        print("Client-version problems (build_wgmods_zip.py says %s):"
              % (client or "?"))
        for p in client_problems:
            print("  " + p)
        rc = 1
    if rc == 0:
        print("OK: mod version %s consistent everywhere; client %s consistent."
              % (expected, client))
    return rc


if __name__ == "__main__":
    sys.exit(main())
