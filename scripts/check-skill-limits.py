#!/usr/bin/env python3
"""Fail when the shipped workspace skills exceed the configured OpenClaw skill limits.

Spec 188 / issue #326. Contract: specs/188-skill-load-limits/contracts/skill-limits-cli.md
Exit 0 covered, 1 exceeded, 2 policy or skills directory unreadable. Read-only, stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import skill_limits as sl


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--warn-only", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    try:
        policy = sl.load_policy(args.policy)
        skills = sl.shipped_skills(args.skills_dir)
    except (ValueError, OSError) as exc:
        print(f"skill-limits: ERROR {exc}")
        return 2
    findings = sl.evaluate(policy, skills)
    failed = [f for f in findings if f["level"] == "fail"]
    if args.as_json:
        print(json.dumps({"skills": len(skills), "findings": findings}, indent=2))
    else:
        for f in findings:
            if f["level"] == "fail":
                print(f"skill-limits: FAIL {f['limit']} {f['configured']} < {f['needed']} needed "
                      f"for {len(skills)} shipped skills (over by {f['needed'] - f['configured']}); "
                      f"raise it in config/skill-limits.json")
            else:
                print(f"skill-limits: note {f['limit']} {f['configured']} is at "
                      f"{f['needed'] * 100 // f['configured']}% use ({f['needed']}); plan a bump")
        if not failed:
            print(f"skill-limits: ok, {len(skills)} shipped skills covered by the configured limits")
    return 0 if (not failed or args.warn_only) else 1


if __name__ == "__main__":
    sys.exit(main())
