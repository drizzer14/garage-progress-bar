# -*- coding: utf-8 -*-
"""Guard that the packaged .wotmod never bakes the developer's absolute source path into a
shipped .pyc's `co_filename` -- that filename is printed as the frame prefix on EVERY
python.log line (see build/build_wotmod.py's `dfile` handling), so an absolute dev-machine
path there leaks the player's Windows username on every log line, not just a traceback.

Runs the real Python-2.7 build (the game's interpreter) into dist/ and inspects the freshly
built .wotmod's marshalled code objects directly -- no game, no import, just `marshal.load`.
"""
import os
import subprocess
import xml.etree.ElementTree as ET

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_PY27 = r"C:\Python27\python.exe"
_DIST = os.path.join(_ROOT, "dist")
_META = os.path.join(_ROOT, "src", "meta.xml")

# Inspection runs INSIDE the Python-2.7 subprocess: marshal's on-disk format is
# interpreter-version-specific, so a py3 `marshal.loads` on a py2.7 .pyc raises
# "bad marshal data" -- it can't cross the version boundary the way the .pyc
# itself is designed not to (see build-deploy's "bytecode is version-locked").
_INSPECT_PY2 = r"""
import marshal
import sys
import zipfile

def absolute_looking(path):
    if not path:
        return False
    if len(path) >= 2 and path[1:2] == ":":
        return True
    if path.startswith("\\\\") or path.startswith("/"):
        return True
    if "Users" in path or "Dmytro" in path:
        return True
    return False

def iter_code_filenames(code):
    yield code.co_filename
    for const in code.co_consts:
        if hasattr(const, "co_filename"):
            for name in iter_code_filenames(const):
                yield name

wotmod_path = sys.argv[1]
offenders = []
zf = zipfile.ZipFile(wotmod_path)
try:
    for name in zf.namelist():
        if not name.endswith(".pyc"):
            continue
        data = zf.read(name)
        code = marshal.loads(data[8:])  # skip the 4-byte magic + 4-byte mtime header
        for filename in iter_code_filenames(code):
            if absolute_looking(filename):
                offenders.append("%s: co_filename=%r" % (name, filename))
finally:
    zf.close()
for line in offenders:
    print(line)
"""


def _read_meta():
    root = ET.parse(_META).getroot()
    return root.findtext("id").strip(), root.findtext("version").strip()


@pytest.mark.skipif(not os.path.exists(_PY27), reason="Python 2.7.18 not installed on this machine")
def test_built_wotmod_has_no_absolute_co_filename():
    subprocess.check_call([_PY27, os.path.join(_ROOT, "build", "build_wotmod.py")], cwd=_ROOT)

    mod_id, version = _read_meta()
    wotmod_path = os.path.join(_DIST, "%s_%s.wotmod" % (mod_id, version))
    assert os.path.exists(wotmod_path), "build did not produce %s" % wotmod_path

    out = subprocess.check_output([_PY27, "-c", _INSPECT_PY2, wotmod_path]).decode("utf-8", "replace")
    offenders = [line for line in out.splitlines() if line.strip()]
    assert not offenders, "\n".join(offenders)
