"""Skill load/prompt limits for OpenClaw (spec 188, issue #326).

OpenClaw loads at most 200 skills per source and injects at most 150 skills / 18000
characters of skill descriptions into the model prompt. NetClaw ships more than that, so
the excess was silently never loaded. `config/skill-limits.json` is the single source of
truth; this module applies it raise-only to a runtime config and measures the shipped
skills against it. Stdlib only.
"""
import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO / "config" / "skill-limits.json"
SKILLS_DIR = REPO / "workspace" / "skills"
LIMIT_KEYS = ("maxSkillsLoadedPerSource", "maxCandidatesPerRoot",
              "maxSkillsInPrompt", "maxSkillsPromptChars")


def _is_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def load_policy(path=None):
    """Read and validate the policy; ValueError on any problem."""
    path = Path(path) if path else POLICY_PATH
    try:
        policy = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot read skill limits policy {path}: {exc}")
    limits = policy.get("limits") if isinstance(policy, dict) else None
    if not isinstance(limits, dict):
        raise ValueError("policy needs a 'limits' object")
    for key in LIMIT_KEYS:
        if not _is_count(limits.get(key)):
            raise ValueError(f"policy limits.{key} must be a positive integer")
    if limits["maxSkillsLoadedPerSource"] > limits["maxCandidatesPerRoot"]:
        raise ValueError("maxSkillsLoadedPerSource must not exceed maxCandidatesPerRoot")
    if limits["maxSkillsInPrompt"] < limits["maxSkillsLoadedPerSource"]:
        raise ValueError("maxSkillsInPrompt must cover maxSkillsLoadedPerSource")
    measurement = policy.setdefault("measurement", {})
    measurement.setdefault("perSkillOverheadChars", 120)
    measurement.setdefault("missingDescriptionChars", 200)
    fraction = policy.setdefault("warnAtFraction", 0.8)
    if not isinstance(fraction, (int, float)) or isinstance(fraction, bool) or not 0 < fraction <= 1:
        raise ValueError("warnAtFraction must be in (0, 1]")
    return policy


def policy_limits(policy=None):
    return dict((policy or load_policy())["limits"])


def raise_limits(config, policy=None):
    """Raise-only: set config['skills']['limits'][key] = max(existing valid int, policy).
    Invalid existing values are replaced; every other key is untouched. Returns True if
    the config changed."""
    limits = policy_limits(policy)
    skills = config.get("skills")
    if not isinstance(skills, dict):
        skills = config["skills"] = {}
    current = skills.get("limits")
    if not isinstance(current, dict):
        current = skills["limits"] = {}
        changed = True
    else:
        changed = False
    for key, want in limits.items():
        have = current.get(key)
        new = max(have, want) if _is_count(have) else want
        if current.get(key) != new:
            current[key] = new
            changed = True
    return changed


def _description(text):
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not match:
        return ""
    lines = match.group(1).splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^description:\s*(.*)$", line)
        if not m:
            continue
        value = m.group(1).strip()
        if value in (">", "|", ">-", "|-", ">+", "|+"):
            parts = []
            for follow in lines[i + 1:]:
                if follow[:1] in (" ", "\t") or not follow.strip():
                    parts.append(follow.strip())
                else:
                    break
            return " ".join(p for p in parts if p)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value
    return ""


def shipped_skills(skills_dir=None):
    """[(name, description)] for each directory holding a SKILL.md."""
    root = Path(skills_dir) if skills_dir else SKILLS_DIR
    found = []
    for entry in sorted(root.iterdir()):
        skill = entry / "SKILL.md"
        if entry.is_dir() and skill.is_file():
            found.append((entry.name, _description(skill.read_text(errors="replace"))))
    return found


def measure_prompt_chars(skills, policy=None):
    m = (policy or load_policy())["measurement"]
    total = 0
    for name, description in skills:
        total += len(name) + (len(description) or m["missingDescriptionChars"]) + m["perSkillOverheadChars"]
    return total


def recommended_char_budget(skills, policy=None, headroom=1.25):
    return int(math.ceil(measure_prompt_chars(skills, policy) * headroom / 1000.0)) * 1000


def evaluate(policy, skills):
    """Findings [{limit, configured, needed, level}] where level is 'fail' (shipped set
    exceeds the limit) or 'warn' (at or above warnAtFraction of it)."""
    limits, count = policy["limits"], len(skills)
    needs = {
        "maxSkillsLoadedPerSource": count,
        "maxCandidatesPerRoot": count,
        "maxSkillsInPrompt": count,
        "maxSkillsPromptChars": measure_prompt_chars(skills, policy),
    }
    fraction, findings = policy["warnAtFraction"], []
    for key in LIMIT_KEYS:
        configured, needed = limits[key], needs[key]
        if needed > configured:
            findings.append({"limit": key, "configured": configured, "needed": needed, "level": "fail"})
        elif needed >= configured * fraction:
            findings.append({"limit": key, "configured": configured, "needed": needed, "level": "warn"})
    return findings
