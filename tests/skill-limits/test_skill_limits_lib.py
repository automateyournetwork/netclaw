import copy
import json
from pathlib import Path

import pytest

import skill_limits as sl
from conftest import ROOT, make_skills, write_policy


def test_repo_policy_loads_and_covers_shipped_skills():
    policy = sl.load_policy()
    skills = sl.shipped_skills()
    assert len(skills) >= 240
    assert [f for f in sl.evaluate(policy, skills) if f["level"] == "fail"] == []
    # headroom: policy must exceed the default OpenClaw ceilings that caused issue #326
    assert policy["limits"]["maxSkillsLoadedPerSource"] > 240


@pytest.mark.parametrize("change,message", [
    ({"maxSkillsLoadedPerSource": 0}, "positive integer"),
    ({"maxSkillsLoadedPerSource": True}, "positive integer"),
    ({"maxSkillsLoadedPerSource": "400"}, "positive integer"),
    ({"maxSkillsLoadedPerSource": 500}, "must not exceed maxCandidatesPerRoot"),
    ({"maxSkillsInPrompt": 100}, "must cover"),
])
def test_policy_validation(tmp_path, change, message):
    with pytest.raises(ValueError, match=message):
        sl.load_policy(write_policy(tmp_path / "p.json", **change))


def test_policy_missing_or_bad_json(tmp_path):
    with pytest.raises(ValueError):
        sl.load_policy(tmp_path / "none.json")
    (tmp_path / "bad.json").write_text("{")
    with pytest.raises(ValueError):
        sl.load_policy(tmp_path / "bad.json")


def test_shipped_skills_counts_only_dirs_with_skill_md(tmp_path):
    make_skills(tmp_path, 3)
    (tmp_path / "no-skill-md").mkdir()
    (tmp_path / "stray.txt").write_text("x")
    assert [n for n, _ in sl.shipped_skills(tmp_path)] == ["skill-0000", "skill-0001", "skill-0002"]


def test_description_parsing_variants(tmp_path):
    for name, body in {"a": 'description: "quoted one"', "b": "description: plain text",
                       "c": "description: >\n  folded\n  text", "d": "other: 1"}.items():
        (tmp_path / name).mkdir()
        (tmp_path / name / "SKILL.md").write_text(f"---\nname: {name}\n{body}\n---\n")
    got = dict(sl.shipped_skills(tmp_path))
    assert got == {"a": "quoted one", "b": "plain text", "c": "folded text", "d": ""}


def test_measurement_uses_default_for_missing_description(tmp_path):
    policy = sl.load_policy(write_policy(tmp_path / "p.json"))
    assert sl.measure_prompt_chars([("ab", "xyz")], policy) == 2 + 3 + 120
    assert sl.measure_prompt_chars([("ab", "")], policy) == 2 + 200 + 120


def test_raise_limits_fresh_config():
    config = {}
    assert sl.raise_limits(config) is True
    assert config["skills"]["limits"] == sl.policy_limits()


def test_raise_limits_is_raise_only_and_preserves_other_keys():
    policy = sl.load_policy()
    config = {"gateway": {"mode": "local"},
              "skills": {"entries": {"x": {"enabled": False}}, "workshop": {"a": 1},
                         "limits": {"maxSkillsLoadedPerSource": 9999, "maxSkillsInPrompt": 5,
                                    "maxCandidatesPerRoot": "bad", "extra": 7}}}
    assert sl.raise_limits(config, policy) is True
    limits = config["skills"]["limits"]
    assert limits["maxSkillsLoadedPerSource"] == 9999          # operator higher value kept
    assert limits["maxSkillsInPrompt"] == policy["limits"]["maxSkillsInPrompt"]  # lower raised
    assert limits["maxCandidatesPerRoot"] == policy["limits"]["maxCandidatesPerRoot"]  # invalid replaced
    assert limits["extra"] == 7
    assert config["skills"]["entries"] == {"x": {"enabled": False}}
    assert config["skills"]["workshop"] == {"a": 1} and config["gateway"] == {"mode": "local"}


def test_raise_limits_idempotent_and_non_dict_skills():
    config = {"skills": "oops"}
    assert sl.raise_limits(config) is True
    snapshot = copy.deepcopy(config)
    assert sl.raise_limits(config) is False
    assert config == snapshot


def test_bool_existing_value_replaced():
    config = {"skills": {"limits": {"maxSkillsLoadedPerSource": True}}}
    sl.raise_limits(config)
    assert config["skills"]["limits"]["maxSkillsLoadedPerSource"] == sl.policy_limits()["maxSkillsLoadedPerSource"]
