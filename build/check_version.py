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

New references written in any of these forms are picked up automatically, so the
check needs no per-file list to maintain.

Runs on Python 2.7 or 3.x (release tooling is 2.7; CI is 3.13).
"""
from __future__ import print_function

import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = os.path.join(ROOT, "src", "meta.xml")

# Directories not worth scanning (build output, VCS, vendored binaries, editor cfg).
_SKIP_DIRS = {".git", "dist", "__pycache__", "node_modules", ".idea", ".vscode",
              "vendor", "assets"}
# Only these extensions hold version references.
_SCAN_EXT = (".md", ".py", ".xml", ".iss", ".ps1", ".txt")

# Each pattern captures a semver in group 1 that must equal the meta version.
_PATTERNS = [
    re.compile(r"com\.14th_ua\.garageprogressbar_(\d+\.\d+\.\d+)\.wotmod"),
    re.compile(r"GarageProgressBar-Setup-(\d+\.\d+\.\d+)\.exe"),
    re.compile(r'MOD_VERSION\s*=\s*"(\d+\.\d+\.\d+)"'),
    re.compile(r'#define\s+ModVersion\s+"(\d+\.\d+\.\d+)"'),
]


def _meta_version():
    return ET.parse(META).getroot().findtext("version").strip()


def _iter_files():
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for name in files:
            if name.endswith(_SCAN_EXT):
                yield os.path.join(dirpath, name)


def main():
    expected = _meta_version()
    mismatches = []
    found_any = False
    for path in _iter_files():
        try:
            with open(path, "rb") as fh:
                text = fh.read().decode("utf-8", "replace")
        except (IOError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for pat in _PATTERNS:
                for m in pat.finditer(line):
                    found_any = True
                    if m.group(1) != expected:
                        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
                        mismatches.append((rel, lineno, m.group(1), line.strip()))

    if mismatches:
        print("Version mismatch (src/meta.xml says %s):" % expected)
        for rel, lineno, got, line in mismatches:
            print("  %s:%d  found %s  ->  %s" % (rel, lineno, got, line))
        return 1
    if not found_any:
        print("WARNING: no version references matched any pattern -- "
              "check_version.py may be stale.")
        return 1
    print("OK: all version references match src/meta.xml (%s)." % expected)
    return 0


if __name__ == "__main__":
    sys.exit(main())
