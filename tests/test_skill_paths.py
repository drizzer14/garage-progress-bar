import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_REF = re.compile(r"\b(?:tools/dev|build)/[\w.-]+\.py\b")


def test_skill_script_paths_exist():
    missing = []
    for skill in sorted((ROOT / ".claude" / "skills").glob("**/SKILL.md")):
        lines = skill.read_text(encoding="utf-8").splitlines()
        for n, line in enumerate(lines, 1):
            if "retired" in line.lower():
                continue
            for ref in _REF.findall(line):
                if not (ROOT / ref).is_file():
                    missing.append("%s:%d %s" % (skill.relative_to(ROOT), n, ref))
    assert not missing, "\n".join(missing)
