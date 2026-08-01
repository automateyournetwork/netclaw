#!/usr/bin/env python3
"""Verify that every MCP registration in config/openclaw.json is portable --
that is, that it will still resolve on a machine other than the one it was
written on.

Contract: specs/075-mcp-config-reconciliation/contracts/reconcile-cli.md
Data model: specs/075-mcp-config-reconciliation/data-model.md (PathClassification)

Why this exists: three Nautobot registrations shipped with
`/home/ubuntu/netclaw/.venv/bin/python3` hardcoded as their interpreter. That
path exists on nobody's machine -- not even the maintainer's -- so all three
integrations were broken for every single installer until spec 075 found them.
Nothing was checking, because "does this path exist somewhere else" is not a
question any other verifier asks.

The distinction that matters is NOT absolute-vs-relative. `/usr/bin/python3` is
an absolute path and is perfectly portable; `/home/ubuntu/netclaw/...` is not.
Banning all absolute paths would flag every system interpreter and push people
toward suppressions. So paths are classified, and only genuinely
machine-specific ones fail.

No third-party dependencies. Paths resolve relative to this file's location,
not the caller's cwd.
"""

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(REPO_ROOT, "config", "openclaw.json")

# Absolute prefixes that are portable in practice: present at the same location
# on any conventional Linux install.
SYSTEM_PREFIXES = ("/usr/", "/bin/", "/sbin/", "/lib/", "/opt/", "/etc/")

# Absolute prefixes that are inherently specific to one machine and one user.
# This is the class that actually broke, and the reason this script exists.
HOME_PREFIXES = ("/home/", "/Users/", "/root/")

CLASS_REPO_RELATIVE = "repo_relative"
CLASS_SYSTEM_ABSOLUTE = "system_absolute"
CLASS_MACHINE_SPECIFIC = "machine_specific"
CLASS_PACKAGE_SPEC = "package_spec"
CLASS_EMBEDDED_ARGS = "embedded_args"
CLASS_OTHER_ABSOLUTE = "other_absolute"


def classify(value, repo_root):
    """Classify one command / arg / cwd string. See data-model.md."""
    if not isinstance(value, str) or not value:
        return None

    # A command string containing whitespace has arguments packed into it.
    # Whether that launches depends on whether the host splits it, so this is
    # reported for verification rather than failed outright.
    if not value.startswith("/") and " " in value.strip() and not value.startswith("-"):
        if os.path.sep in value.split(" ")[0] or value.split(" ")[0].endswith("python3"):
            return CLASS_EMBEDDED_ARGS

    if value.startswith("/"):
        if " " in value:
            return CLASS_EMBEDDED_ARGS
        if value.startswith(HOME_PREFIXES):
            # Inside the repo root is still machine-specific in the config file,
            # even though normalize-mcp-cwd.py legitimately injects such a path
            # at install time for the installing user's own machine.
            return CLASS_MACHINE_SPECIFIC
        if value.startswith(SYSTEM_PREFIXES):
            return CLASS_SYSTEM_ABSOLUTE
        return CLASS_OTHER_ABSOLUTE

    candidate = os.path.join(repo_root, value)
    if os.path.exists(candidate):
        return CLASS_REPO_RELATIVE

    return CLASS_PACKAGE_SPEC


def check(config_path, repo_root):
    """Return (failures, flags, examined_count)."""
    with open(config_path) as f:
        config = json.load(f)
    servers = config.get("mcpServers", {})

    failures = []
    flags = []
    examined = 0

    for name in sorted(servers):
        entry = servers[name]
        if not isinstance(entry, dict):
            continue

        fields = [("command", entry.get("command")), ("cwd", entry.get("cwd"))]
        args = entry.get("args")
        if isinstance(args, list):
            fields += [(f"args[{i}]", a) for i, a in enumerate(args)]

        for field, value in fields:
            verdict = classify(value, repo_root)
            if verdict is None:
                continue
            examined += 1
            if verdict == CLASS_MACHINE_SPECIFIC:
                failures.append(
                    f"{name}: {field} '{value}' is machine-specific "
                    f"(expected repo-relative or system path)"
                )
            elif verdict == CLASS_EMBEDDED_ARGS:
                flags.append(
                    f"{name}: {field} '{value}' packs arguments into one string "
                    f"(expected separate 'command' and 'args')"
                )

    return failures, flags, examined


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--config", default=DEFAULT_CONFIG,
                        help="path to openclaw.json (default: repo config)")
    parser.add_argument("--repo", default=REPO_ROOT,
                        help="repository root used to resolve relative paths")
    parser.add_argument("--warn-only", action="store_true",
                        help="print findings but always exit 0")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit machine-readable results")
    args = parser.parse_args()

    if not os.path.isfile(args.config):
        print(f"ERROR: could not read {args.config}", file=sys.stderr)
        return 2
    try:
        failures, flags, examined = check(args.config, args.repo)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: could not parse {args.config}: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps({
            "surface": "portability",
            "status": "fail" if failures else ("flagged" if flags else "pass"),
            "failures": failures,
            "flags": flags,
            "paths_examined": examined,
        }, indent=2))
    else:
        print(f"Paths examined: {examined}")
        print()
        if failures:
            print("Portability check: FAIL")
            for item in failures:
                print(f"  portability: {item}")
        else:
            print("Portability check: PASS")
        for item in flags:
            print(f"  flagged: {item}")

    if failures and not args.warn_only:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
