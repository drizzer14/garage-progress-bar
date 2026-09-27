# -*- coding: utf-8 -*-
"""Every module must import LOG_NOTE/LOG_PROD/LOG_CURRENT_EXCEPTION from
wgmod_research._compat -- never straight from debug_utils. _compat is the ONE place
that scrubs the player's absolute install path out of a logged traceback (see the
logger skill); a direct `from debug_utils import ...` anywhere else silently bypasses
that scrub and leaks the path."""
import os
import re

_SRC_ROOT = os.path.join(os.path.dirname(__file__), "..", "src", "res", "scripts", "client")
_COMPAT_PATH = os.path.join(_SRC_ROOT, "wgmod_research", "_compat.py")
_DEBUG_UTILS_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+debug_utils\b", re.MULTILINE)


def _py_files():
    for dirpath, _dirs, files in os.walk(_SRC_ROOT):
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def test_only_compat_imports_debug_utils():
    offenders = []
    for path in _py_files():
        if os.path.abspath(path) == os.path.abspath(_COMPAT_PATH):
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        if _DEBUG_UTILS_IMPORT_RE.search(text):
            offenders.append(os.path.relpath(path, _SRC_ROOT))
    assert not offenders, (
        "these modules import debug_utils directly instead of going through "
        "wgmod_research._compat (path-scrub bypass): %s" % offenders
    )
