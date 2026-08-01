#!/usr/bin/env python3
"""Single entry point for NetClaw's MCP reconciliation checks.

Contract: specs/075-mcp-config-reconciliation/contracts/reconcile-cli.md

The goal these checks serve: **every integration NetClaw claims to ship must be
genuinely obtainable by someone installing their own risk.** Not "present in a
config file on the maintainer's laptop" -- obtainable, by a stranger, on their
own machine.

Why this wrapper exists: the underlying checks already existed and already
failed correctly. What was missing was anything that *ran* them. Before spec
075, `.github/workflows/` contained only skill-review.yml and no script, hook or
workflow invoked any verifier -- so they reported real problems into a void for
as long as they had existed. This script is what CI and maintainers call, so
there is exactly one way to ask "is the repository reconciled?" and one answer.

Surfaces checked:

  catalog      every registered server maps to an installer component, every
               external integration is covered, every vendored directory has a
               recorded state
  docs         documented skill/MCP counts match the computed truth, and every
               expected claim is still locatable
  portability  no registration depends on a path that only resolves on one
               machine

No third-party dependencies. Read-only: never writes a repository file. Requires
no running agent, no network, and no credentials, so it works in a bare CI
container and on a fresh clone.
"""

import argparse
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO_ROOT, "scripts")

# surface name -> (script filename, human summary noun)
SURFACES = {
    "catalog": ("verify-catalog-coverage.py", "installer coverage and vendored state"),
    "docs": ("verify-inventory-counts.py", "documented counts"),
    "portability": ("check-mcp-portability.py", "registration portability"),
    # Added by spec 077 (R0a): dependency breakage that only affects FRESH
    # installs — unbounded pins on packages whose submodules are imported, bare
    # pip invocations, and ensurepip-dependent venv creation.
    "dependencies": ("check-dependency-pins.py", "dependency pins and install paths"),
}

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_CANNOT_RUN = 2


def run_surface(name, warn_only):
    """Run one surface check. Returns (exit_code, output_lines)."""
    script, _ = SURFACES[name]
    path = os.path.join(SCRIPTS, script)
    if not os.path.isfile(path):
        return EXIT_CANNOT_RUN, [f"{name}: check script missing at {path}"]

    cmd = [sys.executable, path]
    if warn_only:
        # Only pass the flag to scripts that accept it; the two older verifiers
        # predate it. Probing --help would be slower and no more reliable than
        # simply not forwarding it, since this wrapper enforces warn-only itself.
        if script in ("check-mcp-portability.py", "check-dependency-pins.py"):
            cmd.append("--warn-only")

    proc = subprocess.run(cmd, capture_output=True, text=True)
    output = (proc.stdout + proc.stderr).splitlines()
    return proc.returncode, output


def extract_findings(output):
    """Pull the actionable lines out of a surface's output.

    Each underlying check already formats findings as indented detail lines, so
    the wrapper surfaces those verbatim rather than re-deriving them -- keeping
    one source of truth for wording.
    """
    findings = []
    for line in output:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            findings.append(stripped[2:])
        elif stripped.startswith(("portability:", "unlocatable:", "flagged:", "note:",
                                  "ERROR:", "pins:", "bare-pip:", "venv:")):
            findings.append(stripped)
        elif line.startswith("  ") and (
            "claims" in stripped or "no matching" in stripped or "no recorded state" in stripped
        ):
            findings.append(stripped)
    return findings


def main():
    parser = argparse.ArgumentParser(
        description="Reconcile NetClaw's MCP registration surfaces.",
        epilog="Exit 0 = reconciled, 1 = inconsistent, 2 = check could not run.",
    )
    parser.add_argument("--surface", action="append", choices=sorted(SURFACES),
                        help="run only this surface (repeatable; default: all)")
    parser.add_argument("--warn-only", action="store_true",
                        help="print findings but always exit 0 (never use in CI)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit machine-readable results")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress passing surfaces; print findings only")
    args = parser.parse_args()

    selected = args.surface or sorted(SURFACES)
    results = {}
    cannot_run = False
    any_failed = False

    for name in selected:
        code, output = run_surface(name, args.warn_only)
        findings = extract_findings(output)
        if code == EXIT_CANNOT_RUN:
            status = "cannot_run"
            cannot_run = True
        elif code != EXIT_OK:
            status = "fail"
            any_failed = True
        else:
            status = "flagged" if any(f.startswith("flagged:") for f in findings) else "pass"
        results[name] = {"status": status, "exit_code": code, "findings": findings}

    if args.as_json:
        overall = "cannot_run" if cannot_run else ("fail" if any_failed else "pass")
        print(json.dumps({"overall": overall, "surfaces": results}, indent=2))
    else:
        overall = "CANNOT RUN" if cannot_run else ("FAIL" if any_failed else "PASS")
        print(f"Reconciliation: {overall}")
        for name in selected:
            r = results[name]
            label = {"pass": "pass", "fail": "FAIL",
                     "flagged": "pass*", "cannot_run": "ERROR"}[r["status"]]
            _, noun = SURFACES[name]
            if args.quiet and r["status"] in ("pass", "flagged"):
                continue
            print(f"  {name:<12} {label:<6} {noun}")
            for finding in r["findings"]:
                print(f"      {finding}")
        if not args.quiet and any(r["status"] == "flagged" for r in results.values()):
            print("\n  * passed with advisory findings (see 'flagged:' lines)")

    if cannot_run:
        return EXIT_CANNOT_RUN
    if any_failed and not args.warn_only:
        return EXIT_FAIL
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
