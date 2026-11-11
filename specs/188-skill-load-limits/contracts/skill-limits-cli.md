# Contract: scripts/check-skill-limits.py

`python3 scripts/check-skill-limits.py [--skills-dir DIR] [--policy FILE] [--warn-only] [--json]`

- Exit 0: all limits cover the shipped set. Exit 1: at least one exceeded. Exit 2: policy/dir unreadable or invalid.
- Output: `skill-limits: FAIL maxSkillsLoadedPerSource 400 < 431 shipped skills (over by 31)`; warnings `skill-limits: note ...` at >= 80%.
- Surface `skill-limits` in `scripts/reconcile-mcp.py`.

# Contract: scripts/lib/skill_limits.py
- `load_policy(path=None) -> dict` (validates, raises ValueError)
- `raise_limits(config: dict, policy) -> bool` (mutates, True if changed)
- `shipped_skills(skills_dir) -> list[(name, description)]`
- `evaluate(policy, skills) -> list[finding]`
