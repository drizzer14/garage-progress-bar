"""installer/vendor/*.wotmod are bundled third-party dependencies with no recorded
origin/licence/hash otherwise -- installer/vendor/manifest.json is the record, and this
guards it from drifting silently when a vendor file is swapped without updating it."""
import hashlib
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
VENDOR_DIR = os.path.join(ROOT, "installer", "vendor")
MANIFEST_PATH = os.path.join(VENDOR_DIR, "manifest.json")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _manifest():
    with open(MANIFEST_PATH) as f:
        data = json.load(f)
    data.pop("_comment", None)
    return data


def _vendor_wotmods():
    return sorted(f for f in os.listdir(VENDOR_DIR) if f.endswith(".wotmod"))


def test_every_vendor_wotmod_is_in_the_manifest():
    manifest = _manifest()
    missing = [f for f in _vendor_wotmods() if f not in manifest]
    assert not missing, "installer/vendor/manifest.json is missing an entry for: %s" % missing


def test_manifest_has_no_orphan_entries():
    manifest = _manifest()
    present = set(_vendor_wotmods())
    orphans = [name for name in manifest if name not in present]
    assert not orphans, "manifest.json references a vendor file that no longer exists: %s" % orphans


def test_manifest_sha256_matches_the_bundled_file():
    manifest = _manifest()
    mismatched = []
    for name, entry in manifest.items():
        actual = _sha256(os.path.join(VENDOR_DIR, name))
        if actual != entry.get("sha256"):
            mismatched.append((name, entry.get("sha256"), actual))
    assert not mismatched, (
        "vendor .wotmod sha256 drifted from manifest.json (name, recorded, actual): %s"
        % mismatched
    )


def test_manifest_entries_have_origin_and_licence():
    manifest = _manifest()
    incomplete = [name for name, entry in manifest.items()
                  if not entry.get("origin") or not entry.get("licence")]
    assert not incomplete, "manifest.json entries missing origin/licence: %s" % incomplete
