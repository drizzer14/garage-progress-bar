# -*- coding: utf-8 -*-
"""
Deploy src/res/ into a WoT install's res_mods/<version>/ as plain .py for fast,
compile-free iteration. Run this on the PC where WoT is installed.

  python build/deploy_dev.py "C:/Games/World_of_Tanks" 2.3.0.1
  python build/deploy_dev.py --config deploy.local.json

Or create deploy.local.json (gitignored) so you can just run it bare:
  { "wot_path": "C:/Games/World_of_Tanks", "version": "2.3.0.1" }

Plain .py works in res_mods/ (the game compiles on the fly); no build step.
Runs under Python 2 or 3 — it only copies files.
"""
from __future__ import print_function

import os
import sys
import json
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_RES = os.path.join(ROOT, "src", "res")


def _resolve_args(argv):
    if "--config" in argv:
        cfg_path = argv[argv.index("--config") + 1]
        with open(cfg_path) as f:
            cfg = json.load(f)
        return cfg["wot_path"], cfg["version"]
    default_cfg = os.path.join(ROOT, "deploy.local.json")
    if len(argv) >= 3:
        return argv[1], argv[2]
    if os.path.exists(default_cfg):
        with open(default_cfg) as f:
            cfg = json.load(f)
        return cfg["wot_path"], cfg["version"]
    print("Usage: python build/deploy_dev.py <wot_path> <version>")
    print("   or: python build/deploy_dev.py --config deploy.local.json")
    sys.exit(1)


def main():
    wot_path, version = _resolve_args(sys.argv)
    target = os.path.join(wot_path, "res_mods", version)

    if not os.path.isdir(wot_path):
        print("WoT path not found: {0}".format(wot_path))
        sys.exit(1)

    copied = 0
    for dirpath, _dirs, files in os.walk(SRC_RES):
        rel = os.path.relpath(dirpath, SRC_RES)
        dest_dir = os.path.join(target, rel) if rel != "." else target
        if not os.path.isdir(dest_dir):
            os.makedirs(dest_dir)
        for name in files:
            shutil.copy2(os.path.join(dirpath, name),
                         os.path.join(dest_dir, name))
            copied += 1

    print("Deployed {0} file(s) to {1}".format(copied, target))
    print("Restart the WoT client to load changes.")


if __name__ == "__main__":
    main()
