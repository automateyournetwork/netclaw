import skill_limits as sl
from conftest import make_skills, write_policy


def _policy(tmp_path, **limits):
    return sl.load_policy(write_policy(tmp_path / "p.json", **limits))


def test_candidates_below_count_fails(tmp_path):
    skills = sl.shipped_skills(make_skills(tmp_path / "s", 10))
    got = {f["limit"]: f for f in sl.evaluate(_policy(tmp_path, maxSkillsLoadedPerSource=8, maxCandidatesPerRoot=9,
                                                      maxSkillsInPrompt=9), skills)}
    assert got["maxSkillsLoadedPerSource"]["level"] == "fail" and got["maxSkillsLoadedPerSource"]["needed"] == 10
    assert got["maxCandidatesPerRoot"]["level"] == "fail"
    assert got["maxSkillsInPrompt"]["level"] == "fail"


def test_char_budget_overflow_names_limit_and_amount(tmp_path):
    skills = sl.shipped_skills(make_skills(tmp_path / "s", 10, "d" * 100))
    policy = _policy(tmp_path, maxSkillsPromptChars=1000)
    (fail,) = [f for f in sl.evaluate(policy, skills) if f["level"] == "fail"]
    assert fail["limit"] == "maxSkillsPromptChars"
    assert fail["needed"] - fail["configured"] == sl.measure_prompt_chars(skills, policy) - 1000


def test_warning_threshold_applies_to_every_limit(tmp_path):
    skills = sl.shipped_skills(make_skills(tmp_path / "s", 9))
    findings = sl.evaluate(_policy(tmp_path, maxSkillsLoadedPerSource=10, maxCandidatesPerRoot=10,
                                   maxSkillsInPrompt=10, maxSkillsPromptChars=10**6), skills)
    assert {f["limit"] for f in findings if f["level"] == "warn"} == {
        "maxSkillsLoadedPerSource", "maxCandidatesPerRoot", "maxSkillsInPrompt"}
    assert not [f for f in findings if f["level"] == "fail"]


def test_shipped_repo_has_no_prompt_overflow():
    policy, skills = sl.load_policy(), sl.shipped_skills()
    assert not [f for f in sl.evaluate(policy, skills) if f["level"] == "fail"]
    assert sl.measure_prompt_chars(skills, policy) <= policy["limits"]["maxSkillsPromptChars"]
