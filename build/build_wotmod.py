# -*- coding: utf-8 -*-
"""
Build a distributable .wotmod package from src/.

  python build/build_wotmod.py

What it does:
  1. Reads <id> and <version> from src/meta.xml.
  2. Compiles every .py under src/res/ to .pyc bytecode, with docstrings stripped
     (the build re-execs itself under -OO — see below).
  3. Minifies WGModResearch.js / .css (vendored rjsmin / rcssmin: comment +
     whitespace removal only, NO name mangling) so the packaged assets are ~1/3
     their source size. Source stays commented; hot-reload ships the raw files.
  4. Zips meta.xml + res/ (with .pyc, NOT .py) into dist/<id>_<version>.wotmod
     using ZIP_STORED (no compression) — WoT rejects compressed archives.

All three are packaging-only transforms: they change NOTHING about the mod's
behaviour or UI, only the byte size of the shipped .wotmod.

IMPORTANT: run this with **Python 2.7.18**. The game executes the .pyc, and
bytecode is tied to the Python version (magic number). Compiling under Python 3
produces bytecode the WoT client cannot load. OS does not matter — 2.7 .pyc is
portable across macOS/Windows/Linux — only the Python *version* matters.

The build re-execs itself under -OO so every shipped .pyc has its docstrings
stripped (~1/3 of the bytecode). The .pyc magic number is identical for
optimized bytecode, so the (non-optimized) client loads it unchanged; the source
has no asserts and no runtime __doc__ use, so stripping is behaviour-neutral.
"""
from __future__ import print_function

import os
import sys
import shutil
import zipfile
import py_compile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
RES = os.path.join(SRC, "res")
META = os.path.join(SRC, "meta.xml")
DIST = os.path.join(ROOT, "dist")
# Vendored pure-Python minifiers (rjsmin / rcssmin, Apache-2.0).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))


def _preflight_minifiers():
    """Fail fast if a vendored minifier is missing/broken BEFORE any build output is
    written -- otherwise a lazy per-file import blows up mid-build with dist/_build/
    half-populated (build_wotmod docstring / build-tooling hardening)."""
    import rjsmin  # noqa: F401
    import rcssmin  # noqa: F401


def _check_python():
    if sys.version_info[0] != 2 or sys.version_info[1] != 7:
        sys.exit("ERROR: build_wotmod must run under Python 2.7 (got {0}.{1}). "
                 "The game executes the .pyc and bytecode is version-locked, so a "
                 "package built under any other version will NOT load in the WoT "
                 "client. Re-run with C:\\Python27\\python.exe."
                 .format(sys.version_info[0], sys.version_info[1]))


def _read_meta():
    root = ET.parse(META).getroot()
    mod_id = root.findtext("id").strip()
    version = root.findtext("version").strip()
    return mod_id, version


def _minify_or_copy(src_file, target_file):
    """Copy a non-Python asset, minifying .js/.css on the way (packaging only).

    rjsmin / rcssmin strip comments and redundant whitespace but never rename
    identifiers or alter string literals, so the Python<->JS wire contract and the
    ES-module `import` statements survive verbatim. Everything else is copied as-is.
    """
    if src_file.endswith(".js"):
        import rjsmin
        with open(src_file, "rb") as fh:
            data = fh.read()
        with open(target_file, "wb") as fh:
            fh.write(rjsmin.jsmin(data))
    elif src_file.endswith(".css"):
        import rcssmin
        with open(src_file, "rb") as fh:
            data = fh.read()
        with open(target_file, "wb") as fh:
            fh.write(rcssmin.cssmin(data))
    else:
        shutil.copy2(src_file, target_file)


def _compile_tree(src_root, out_root):
    """Copy res/ to out_root, compiling .py -> .pyc and dropping the .py."""
    for dirpath, dirs, files in os.walk(src_root):
        # Never ship dev/build artifacts: Python 3 __pycache__ from pytest, etc.
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        rel = os.path.relpath(dirpath, src_root)
        target_dir = os.path.join(out_root, rel) if rel != "." else out_root
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)
        for name in files:
            src_file = os.path.join(dirpath, name)
            if name.endswith(".py"):
                pyc = os.path.join(target_dir, name + "c")  # foo.py -> foo.pyc
                py_compile.compile(src_file, cfile=pyc, doraise=True)
            elif name.endswith(".pyc"):
                continue  # skip stray/foreign bytecode; we compile fresh from .py
            else:
                _minify_or_copy(src_file, os.path.join(target_dir, name))


def main():
    _check_python()
    if sys.flags.optimize < 2:
        # The .pyc must be compiled under -OO so docstrings are stripped (~1/3
        # smaller bytecode). We can't toggle the optimize flag mid-process, so run
        # THIS build in an -OO child, then return so any caller (e.g. deploy, which
        # imports and calls main()) proceeds normally. Target build_wotmod.py
        # explicitly (not sys.argv) so it works whether run directly or imported.
        # A child process (not os.execv, which detaches stdio on Windows) keeps the
        # "Built:" line visible.
        import subprocess
        rc = subprocess.call([sys.executable, "-OO", os.path.abspath(__file__)])
        if rc != 0:
            raise SystemExit(rc)
        return
    _preflight_minifiers()  # fail fast before writing any build output
    mod_id, version = _read_meta()

    build_dir = os.path.join(DIST, "_build")
    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)

    # meta.xml at archive root
    shutil.copy2(META, os.path.join(build_dir, "meta.xml"))
    # compiled res/ tree
    _compile_tree(RES, os.path.join(build_dir, "res"))

    if not os.path.isdir(DIST):
        os.makedirs(DIST)
    out_path = os.path.join(DIST, "{0}_{1}.wotmod".format(mod_id, version))
    if os.path.exists(out_path):
        os.remove(out_path)

    # ZIP_STORED = no compression (required by WoT)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as zf:
        for dirpath, _dirs, files in os.walk(build_dir):
            for name in files:
                full = os.path.join(dirpath, name)
                arc = os.path.relpath(full, build_dir).replace(os.sep, "/")
                zf.write(full, arc)

    shutil.rmtree(build_dir)
    print("Built: {0} ({1:,} bytes)".format(out_path, os.path.getsize(out_path)))


if __name__ == "__main__":
    main()
