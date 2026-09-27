# -*- coding: utf-8 -*-
"""Assert the mod version is consistent everywhere.

  python build/check_version.py

`src/meta.xml` <version> is the source of truth. This scans the repo for every
version reference that must track it and fails (exit 1) on any mismatch, printing
each offending file:line. It exists because the version is hand-edited in several
places at release time (see the gpb-release skill) and drift has slipped through
before (a stale CONTRIBUTING.md filename).

To avoid false positives on the *other* version numbers in the repo (the target
client 2.3.1.0, bundled ModsSettingsAPI 1.6.4 / OpenWG GameFace 1.1.6, etc.) this
matches only patterns that unambiguously carry THIS mod's version:

  * com.14th_ua.garageprogressbar_<v>.wotmod   (the packaged filename)
  * GarageProgressBar-Setup-<v>.exe            (the installer filename)
  * MOD_VERSION = "<v>"                          (mod_wgmod.py)
  * #define ModVersion "<v>"                     (wgmod-setup.iss)
  * version <v>                                  (prose header, e.g. dist/INSTALL.txt)

The last (prose) pattern has a negative lookahead so it matches THIS mod's 3-part
version only, never the 4-part client version ("version 2.3.1.0").

New references written in any of these forms are picked up automatically. On top of
that, a small REQUIRED list names files that must carry at least one reference, so a
file silently LOSING its version reference also fails the check.

The hand-bumped consumer readme (dist/INSTALL.txt) lives under gitignored dist/,
which is otherwise skipped; it is scanned explicitly when present.

It ALSO checks the supported CLIENT version (4-part, e.g. 2.3.1.0) -- a separate value
from the mod version. The single canonical source is build_wgmods_zip.CLIENT_VERSION;
a fixed set of shipping/instruction files (_CLIENT_REQUIRED) must each carry it and must
not carry a differing 4-part client token, so a client patch that misses one file fails.
IP-shaped tokens (the debug REPL's 127.0.0.1) are excluded so they never false-fail.

`.claude/skills/**/*.md` + `CLAUDE.md` are prose nothing else greps, so they silently
rot after a release or client upgrade. The core check above already covers old-MOD-
version drift there (`.claude` isn't skipped, `.md` is in `_SCAN_EXT`, same _PATTERNS)
-- so on top of that, this file ALSO prints a fix-list (file:line + what's stale) for
three narrower signals the core check can't see: an old bundled vendor .wotmod name
(compares against installer/vendor/*.wotmod, id-only so a version-only bump isn't a
false positive), an old settingsVersion/SETTINGS_VERSION value (compares against the
mod's own source), and old atlas WxH dimensions (compares against the mod's own atlas
PNG, read via IHDR, only on lines mentioning "atlas"). Every one of these is fail-soft:
a mod without a vendor dep / settings panel / atlas just emits no rows for that
category, never an error.

Run `python check_version.py --selfcheck` to exercise the stale-doc scan logic against
fixtures (no repo state needed).

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
# bundle extracts into). We import it (it has no import-time side effects) and verify the
# shipping/instruction files agree, so a client patch can't leave a straggler.
sys.path.insert(0, os.path.join(ROOT, "build"))
from build_wgmods_zip import CLIENT_VERSION

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
# version but never the 4-part client version ("version 2.3.1.0").
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


# --- client version (4-part, e.g. 2.3.1.0) -----------------------------------
# Canonical source: build_wgmods_zip.CLIENT_VERSION (imported above).
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


# --- stale-doc scan: .claude/skills/**/*.md + CLAUDE.md ----------------------
# Project skills and CLAUDE.md go stale after every release/client-upgrade because
# nothing else greps them. This reuses the mod-version core check above for old-
# VERSION drift, plus three more narrow, unambiguous signals, to print a fix-list
# (advisory, not per-file required like _REQUIRED -- this is prose, not code).

_VENDOR_WOTMOD_RE = re.compile(r"\b([A-Za-z0-9_.]+?)_(\d+(?:\.\d+)*)\.wotmod\b")
_SETTINGS_VERSION_SRC_RE = re.compile(r'(?:SETTINGS_VERSION|settingsVersion)\s*"?\s*[:=]\s*(\d+)')
_SETTINGS_VERSION_DOC_RE = re.compile(r"(?:SETTINGS_VERSION|settingsVersion)\D{0,10}?(\d+)")
_ATLAS_DIMS_DOC_RE = re.compile(r"\b(\d{2,5})\s*[xX]\s*(\d{2,5})\b")
_OWN_WOTMOD_RE = re.compile(r"com\.14th_ua\.garageprogressbar_\d+\.\d+\.\d+\.wotmod")


def _read_text(path):
    try:
        with open(path, "rb") as fh:
            return fh.read().decode("utf-8", "replace")
    except (IOError, OSError):
        return None


def _iter_doc_files():
    claude_md = os.path.join(ROOT, "CLAUDE.md")
    if os.path.isfile(claude_md):
        yield claude_md
    skills_dir = os.path.join(ROOT, ".claude", "skills")
    for dirpath, _dirs, files in os.walk(skills_dir):
        for name in files:
            if name.endswith(".md"):
                yield os.path.join(dirpath, name)


def _shipped_vendor_ids():
    """Vendor package ids actually bundled (installer/vendor/*.wotmod), keyed without
    their version so a plain version bump isn't mistaken for a package swap.
    Fail-soft: empty set if the mod bundles no vendor .wotmods."""
    vendor_dir = os.path.join(ROOT, "installer", "vendor")
    ids = set()
    if os.path.isdir(vendor_dir):
        for name in os.listdir(vendor_dir):
            m = _VENDOR_WOTMOD_RE.match(name)
            if m:
                ids.add(m.group(1))
    return ids


def _current_settings_version():
    """SETTINGS_VERSION / settingsVersion currently defined in the mod's own source.
    Fail-soft: None if the mod has no MSA settings panel."""
    src_dir = os.path.join(ROOT, "src")
    if not os.path.isdir(src_dir):
        return None
    for dirpath, _dirs, files in os.walk(src_dir):
        for name in files:
            if not name.endswith(".py"):
                continue
            text = _read_text(os.path.join(dirpath, name))
            m = text and _SETTINGS_VERSION_SRC_RE.search(text)
            if m:
                return int(m.group(1))
    return None


def _current_atlas_dims():
    """(width, height) of the mod's own atlas PNG, read off the IHDR chunk directly
    (no Pillow dependency). Fail-soft: None if the mod has no atlas."""
    src_dir = os.path.join(ROOT, "src")
    if not os.path.isdir(src_dir):
        return None
    for dirpath, _dirs, files in os.walk(src_dir):
        for name in files:
            if "atlas" in name.lower() and name.lower().endswith(".png"):
                try:
                    with open(os.path.join(dirpath, name), "rb") as fh:
                        header = fh.read(24)
                except (IOError, OSError):
                    continue
                if len(header) == 24 and header[12:16] == b"IHDR":
                    import struct
                    return struct.unpack(">II", header[16:24])
    return None


def _scan_line(line, vendor_ids, settings_version, atlas_dims):
    """Pure per-line check: returns a list of human-readable "what's stale" strings
    for one prose line. No disk I/O -- kept separate so demo() can exercise it with
    a fixture string.

    NOTE: old-MOD-version detection is NOT duplicated here -- main()'s existing
    _iter_files()/_PATTERNS pass already recursively scans .claude/skills/**/*.md +
    CLAUDE.md (`.claude` isn't in _SKIP_DIRS, `.md` is in _SCAN_EXT) and fails on a
    stale version there before this scan ever runs."""
    findings = []
    if vendor_ids:
        for m in _VENDOR_WOTMOD_RE.finditer(line):
            if _OWN_WOTMOD_RE.search(line):
                continue
            if m.group(1) not in vendor_ids:
                findings.append(
                    "unrecognized vendor wotmod '%s' (shipped: %s)"
                    % (m.group(0), ", ".join(sorted(vendor_ids))))
    if settings_version is not None:
        m = _SETTINGS_VERSION_DOC_RE.search(line)
        if m and int(m.group(1)) != settings_version:
            findings.append("settingsVersion %s (current %s)" % (m.group(1), settings_version))
    if atlas_dims is not None and "atlas" in line.lower():
        for m in _ATLAS_DIMS_DOC_RE.finditer(line):
            dims = (int(m.group(1)), int(m.group(2)))
            if dims != atlas_dims:
                findings.append("atlas dims %dx%d (current %dx%d)"
                                 % (dims[0], dims[1], atlas_dims[0], atlas_dims[1]))
    return findings


def _scan_stale_docs():
    """Fix-list rows (file, line, what) for every stale reference found in
    .claude/skills/**/*.md + CLAUDE.md. (Old-MOD-version drift in these same files
    is already caught by main()'s core _PATTERNS pass -- not duplicated here.)"""
    vendor_ids = _shipped_vendor_ids()
    settings_version = _current_settings_version()
    atlas_dims = _current_atlas_dims()
    rows = []
    for path in _iter_doc_files():
        text = _read_text(path)
        if text is None:
            continue
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        for lineno, line in enumerate(text.splitlines(), 1):
            for what in _scan_line(line, vendor_ids, settings_version, atlas_dims):
                rows.append((rel, lineno, what))
    return rows


def _check_client_version():
    """Return a list of client-version problems (empty = OK). Scoped to _CLIENT_REQUIRED so
    it never false-fails on prose that merely mentions a version (this file's own examples,
    skill docs, TASKS notes)."""
    problems = []
    client = CLIENT_VERSION
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
    stale_docs = _scan_stale_docs()

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
    if stale_docs:
        # Advisory only: the settingsVersion/vendor/atlas regexes can't tell a
        # "current value" claim from changelog prose narrating a past bump (e.g.
        # "settingsVersion 13 -> 14" history in gpb-architecture), so this must
        # never fail CI -- print the fix-list but don't gate on it.
        print("Stale docs -- review these:")
        for rel, lineno, what in stale_docs:
            print("  %s:%d  %s" % (rel, lineno, what))
    if rc == 0:
        print("OK: mod version %s consistent everywhere; client %s consistent."
              % (expected, client))
    return rc


def demo():
    """Self-check for _scan_line -- run with `python check_version.py --selfcheck`.
    Asserts a known-old vendor wotmod name and a known-old settingsVersion/atlas dims
    each show up in the fix-list, and that a clean line (matching current values)
    produces nothing. (Old-MOD-version detection is main()'s core _PATTERNS pass,
    not _scan_line's -- see the note on _scan_line -- so it isn't re-tested here.)

    Fixtures are built by concatenation, not literal inline text, so this file's OWN
    source never contains a contiguous substring that the real scan (run over this
    very file as part of the repo) would flag against itself."""
    stale_vendor_line = "Depends on " + "aslain.modssettingsapi_1.7.1" + ".wotmod for settings."
    settings_line = "settingsVersion" + " 11 is what ships today."
    atlas_line = "The atlas is " + "4096x5152" + " at build time."
    clean_line = "See MOD_VERSION" + " = \"2.0.0\" in the mod entry point."

    found = _scan_line(stale_vendor_line, {"aslain.modmenu"}, None, None)
    assert any("aslain.modssettingsapi_1.7.1.wotmod" in f for f in found), found

    found = _scan_line(settings_line, set(), 15, None)
    assert any("11" in f for f in found), found

    found = _scan_line(atlas_line, set(), None, (4096, 5076))
    assert any("4096x5152" in f for f in found), found

    found = _scan_line(clean_line, set(), None, None)
    assert found == [], found

    # fail-soft: missing category data -> never flags, never errors.
    assert _scan_line(stale_vendor_line, set(), None, None) == []
    assert _scan_line(settings_line, set(), None, None) == []
    assert _scan_line(atlas_line, set(), None, None) == []

    print("demo(): OK -- stale-doc scan flags known-old values, "
          "skips categories the mod doesn't have.")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv[1:]:
        demo()
        sys.exit(0)
    sys.exit(main())
