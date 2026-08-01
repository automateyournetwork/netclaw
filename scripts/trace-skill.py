#!/usr/bin/env python3
"""Trace a skill to the integration backing it, and report that integration's
recorded state.

Contract: specs/075-mcp-config-reconciliation/contracts/reconcile-cli.md (FR-025, FR-026)

With 199 skills, "why did this skill just fail?" is a frequent question. The
answer is usually one of: the backing integration is registered and fine; it is
an intentional on-demand install that this machine has not installed; or the
chain is genuinely broken. Those three look identical from a failure message,
which is what this tool fixes.

Critically, an integration that is "external and not installed" is reported as an
EXPECTED state, not a fault (FR-026). Sixty of NetClaw's 149 integrations are
deliberately installed on demand; treating them as broken would make the tool
useless.

Diagnostic only -- deliberately NOT part of the CI gate, because a skill may
legitimately reference an integration a given install has not enabled.

No third-party dependencies.
"""

import argparse
import importlib.util
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO_ROOT, "workspace", "skills")
CONFIG = os.path.join(REPO_ROOT, "config", "openclaw.json")
COVERAGE = os.path.join(REPO_ROOT, "scripts", "verify-catalog-coverage.py")

EXIT_OK, EXIT_BROKEN, EXIT_NO_SKILL = 0, 1, 2


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("skill", help="skill directory name under workspace/skills/")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    skill_dir = os.path.join(SKILLS_DIR, args.skill)
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        print(f"ERROR: no such skill '{args.skill}' (expected {skill_md})", file=sys.stderr)
        return EXIT_NO_SKILL

    with open(skill_md) as f:
        text = f.read()

    cov = _load(COVERAGE, "verify_catalog_coverage")
    with open(CONFIG) as f:
        registered = sorted(json.load(f).get("mcpServers", {}).keys())
    external = cov.load_external_integrations()
    catalog_ids = set(cov.load_catalog_ids())

    # Skills name their tools as mcp__<server>__<tool>, and/or mention the
    # server key in prose. Both are worth harvesting -- prose-only references
    # are common in older skills.
    found = set(re.findall(r"mcp__([a-z0-9_-]+)__", text))
    lowered = text.lower()
    for key in registered:
        if key.lower() in lowered or key.replace("-mcp", "").lower() in lowered:
            found.add(key)

    chain = []
    reg_norm = {cov._norm(k): k for k in registered}
    for token in sorted(found):
        key = reg_norm.get(cov._norm(token))
        if key:
            catalog_id = (cov.GROUPED_CONFIG_EXACT.get(key)
                          or next((cid for pre, cid in cov.GROUPED_CONFIG_PREFIXES.items()
                                   if key.startswith(pre)), None)
                          or cov.strip_mcp_suffix(key))
            ok = catalog_id in catalog_ids
            chain.append({
                "token": token, "integration": key, "state": "registered",
                "catalog_id": catalog_id if ok else None,
                "status": "ok" if ok else "broken",
                "detail": "registered and installable" if ok else
                          f"registered but catalog id '{catalog_id}' not found",
            })
            continue

        ext = next((n for n in external if cov._norm(n) and cov._norm(n) in cov._norm(token)
                    or cov._norm(token) and cov._norm(token) in cov._norm(n)), None)
        if ext:
            chain.append({
                "token": token, "integration": ext, "state": "external",
                "catalog_id": None, "status": "ok",
                "detail": "intentionally external — installed on demand; "
                          "absence from this machine is expected, not a fault",
            })
            continue

        chain.append({
            "token": token, "integration": None, "state": "unknown",
            "catalog_id": None, "status": "unresolved",
            "detail": "no backing integration found — may be a built-in tool or a naming mismatch",
        })

    broken = [c for c in chain if c["status"] == "broken"]

    if args.as_json:
        print(json.dumps({"skill": args.skill, "chain": chain,
                          "overall": "broken" if broken else "ok"}, indent=2))
    else:
        print(f"Skill: {args.skill}")
        if not chain:
            print("  (no backing integration references found in SKILL.md)")
        for c in chain:
            mark = {"ok": "ok", "broken": "BROKEN", "unresolved": "?"}[c["status"]]
            print(f"  [{mark:>6}] {c['token']}")
            print(f"           integration: {c['integration'] or '—'}  state: {c['state']}")
            if c["catalog_id"]:
                print(f"           installer component: {c['catalog_id']}")
            print(f"           {c['detail']}")

    return EXIT_BROKEN if broken else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
