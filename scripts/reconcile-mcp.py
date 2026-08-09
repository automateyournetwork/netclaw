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
    # Added by spec 088: a registered server that cannot START. Every other surface here
    # validates that things are DECLARED consistently; none of them ran anything. Found
    # by launching all 98 registered servers: seven could not start, one had no server
    # file at all, and 22 skills routed to them — while this script exited 0.
    #
    # Runs --warn-only until the seven are resolved, because they need four different
    # fixes (two SDKs are not publicly distributable, one server has no entry point, one
    # is a uv-env issue, three are blocked by PEP 668 on this host). Flipping it to
    # hard-fail is the follow-up, and the reason it is not hard-fail today is written
    # down rather than left as a mystery.
    "startup": ("check-server-startup.py", "registered servers can actually start"),
    # Added by spec 089. Vendor-specific, deliberately: the five Meraki skills cited 80
    # method names of which 54 DID NOT EXIST in the Meraki API, and the docs surface passed
    # throughout because it compares counts, never the truth of a documented call. Validates
    # skill text against Cisco's own OpenAPI spec, vendored offline. Same lesson as 088 --
    # declarations checked against each other cannot catch one that is uniformly wrong.
    "meraki-ids": ("check-meraki-capability-ids.py", "Meraki capability IDs cited in skills"),
    # Added by spec 093. Skills invoke packages on demand via npx/uvx; those references are
    # neither counted by the docs surface nor launched by the startup surface, so nothing
    # verified they exist. @anthropic-ai/microsoft-graph-mcp did not -- 404 on npm -- and three
    # skills documented 14 tool names against it. Offline against a vendored manifest, with a
    # separate --refresh mode that hits the registries, because this gate has no network by
    # design (SC-013) and spec 090 already learned what ignoring that costs.
    "packages": ("check-package-references.py", "npx/uvx packages skills invoke exist"),
    # Added by spec 077 (R0a): dependency breakage that only affects FRESH
    # installs — unbounded pins on packages whose submodules are imported, bare
    # pip invocations, and ensurepip-dependent venv creation.
    "dependencies": ("check-dependency-pins.py", "dependency pins and install paths"),
}

EXIT_OK = 0
# Surfaces that report findings but never fail the build, regardless of --warn-only.
# A surface belongs here only with a written reason and an exit condition -- otherwise it
# becomes a permanent way to ignore real breakage, which is the failure mode spec 088 was
# written to fix in the first place.
ALWAYS_WARN: set[str] = {
    # Empty. Spec 088 put "startup" here because seven registered servers could not start
    # and it was believed two needed non-distributable SDKs, so nobody could make it green.
    # Spec 090 fixed six of the seven and excepted the one that is genuinely unobtainable
    # (RADKit, code-signed wheels outside PyPI), so the surface is now a hard gate: a
    # registered server that cannot start FAILS the build.
    #
    # Add a surface here only with a written reason and an exit condition, as 088 did.
    # Without both it becomes a permanent way to ignore real breakage.
}

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
        if script in ("check-mcp-portability.py", "check-dependency-pins.py",
                      "check-meraki-capability-ids.py", "check-package-references.py"):
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
                                  "ERROR:", "pins:", "bare-pip:", "venv:",
                                  "startup:", "meraki-ids:", "packages:")):
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
        always_warn = name in ALWAYS_WARN
        # Deliberately NOT passing warn_only for an ALWAYS_WARN surface: the check should
        # still report its true exit code, and this wrapper downgrades it below. Silencing
        # it at the source would make the finding invisible here too.
        code, output = run_surface(name, args.warn_only and not always_warn)
        findings = extract_findings(output)
        if code == EXIT_CANNOT_RUN:
            status = "cannot_run"
            cannot_run = True
        elif code != EXIT_OK:
            # An ALWAYS_WARN surface reports but does not fail the build. It is still
            # rendered distinctly ("warn"), so a reader can never mistake it for a pass.
            status = "warn" if always_warn else "fail"
            any_failed = any_failed or not always_warn
        else:
            status = "flagged" if any(f.startswith("flagged:") for f in findings) else "pass"
        results[name] = {"status": status, "exit_code": code, "findings": findings}

    if args.as_json:
        any_warn = any(r["status"] == "warn" for r in results.values())
        overall = ("cannot_run" if cannot_run else "fail" if any_failed
                   else "pass_with_warnings" if any_warn else "pass")
        print(json.dumps({"overall": overall, "surfaces": results}, indent=2))
    else:
        # A WARN surface must not render as a bare PASS. The whole point of spec 088 is
        # that a green summary concealed seven dead servers.
        any_warn = any(r["status"] == "warn" for r in results.values())
        overall = ("CANNOT RUN" if cannot_run else "FAIL" if any_failed
                   else "PASS (with warnings)" if any_warn else "PASS")
        print(f"Reconciliation: {overall}")
        for name in selected:
            r = results[name]
            label = {"pass": "pass", "fail": "FAIL", "warn": "WARN",
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
