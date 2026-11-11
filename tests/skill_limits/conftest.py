import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))


def make_skills(directory, count, description="Does a thing."):
    for i in range(count):
        d = Path(directory) / f"skill-{i:04d}"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f'---\nname: skill-{i:04d}\ndescription: "{description}"\n---\nbody\n')
    return Path(directory)


def write_policy(path, **limits):
    base = {"maxSkillsLoadedPerSource": 400, "maxCandidatesPerRoot": 400,
            "maxSkillsInPrompt": 400, "maxSkillsPromptChars": 122000}
    base.update(limits)
    Path(path).write_text(json.dumps({"version": 1, "limits": base}))
    return Path(path)


@pytest.fixture
def helpers():
    return make_skills, write_policy
