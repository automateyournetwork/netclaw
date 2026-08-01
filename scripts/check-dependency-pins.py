#!/usr/bin/env python3
"""Catch dependency breakage that only affects FRESH installs.

Spec 077 (roadmap R0a). Contract: FR-006 through FR-014.

Three classes of breakage were found in this repository, and none was visible to
any existing check, because all three break only *new* installs:

  1. An unbounded pin on a package whose SUBMODULE the code imports. `mcp 2.0.0`
     removed `mcp.server.fastmcp`, so eight sites resolved a breaking major.
  2. A bare `pip`/`pip3` invocation, where `pip3` and `python3` may be different
     interpreters — packages land where the server cannot import them.
  3. `python3 -m venv` where `ensurepip` is unavailable, which fails outright.

Detection is derived from the SOURCE, not from a hand-maintained list of risky
packages. That is deliberate: R0 found `EXTERNAL_INTEGRATIONS` had gone stale
("Verified ... as of 2026-07-07"), and a list of dangerous packages would rot the
same way. A static scan cannot.

Known technique limitation (FR-006b): a submodule scan cannot see breakage from
*top-level* API drift — a package changing what `from X import Y` yields. That
limit is real but has NO instance in this repository: all eight sites import a
submodule. It is documented rather than closed with a curated list that would only
make this check look thorough.

No third-party dependencies. No network. Paths resolve from this file's location.
"""

import argparse
import ast
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVERS_DIR = os.path.join(REPO_ROOT, "mcp-servers")
INSTALL_STEPS = os.path.join(REPO_ROOT, "scripts", "lib", "install-steps.sh")

# Recorded exceptions, each with a reason (FR-010). Same discipline R0 applies to
# intentionally-external integrations: the only way to silence a finding is to say
# why, which is human knowledge a scan cannot infer.
PIN_EXCEPTIONS: dict[str, str] = {
    # Fully unpinned with no known breaking major, so any upper bound would be a
    # guess. Bounding on speculation is worse than leaving it: it blocks legitimate
    # upgrades and teaches maintainers that the bounds here are arbitrary.
    "ISE_MCP:aiocache": "unpinned, no known breaking major — bounding would be a guess",
    "pyATS_MCP:pyats": "unpinned; pyATS versions by date, not semver, so <N+1 is meaningless",
    "twilio-voice-mcp:twilio": "second declaration; the bounded one above governs",
}
BARE_PIP_EXCEPTIONS: dict[str, str] = {}

# Scripts that create venvs correctly and must not be flagged.
VENV_OK_PATTERNS = ("uv venv", "virtualenv ", "netclaw_venv_create")


def _requirements(server_dir: str) -> list[str]:
    path = os.path.join(server_dir, "requirements.txt")
    if not os.path.isfile(path):
        return []
    return [ln.strip() for ln in open(path) if ln.strip() and not ln.strip().startswith("#")]


def _parse_pin(line: str) -> tuple[str, str] | None:
    m = re.match(r"^([A-Za-z0-9_.\-\[\]]+)\s*(.*)$", line)
    if not m:
        return None
    name = re.sub(r"\[.*\]", "", m.group(1)).strip().lower().replace("_", "-")
    return name, m.group(2).strip()


def _is_bounded(spec: str) -> bool:
    """Whether a version spec cannot drift into a new major.

    `==`, `<`, `<=`, `~=` all bound above. A bare `>=` does not.
    """
    return bool(re.search(r"(==|<=?|~=)", spec))


def _imported_modules(server_dir: str) -> tuple[set[str], set[str]]:
    """Return (top_level_imports, packages_whose_submodule_is_imported)."""
    top: set[str] = set()
    submodule: set[str] = set()
    for root, _dirs, files in os.walk(server_dir):
        if ".venv" in root or "__pycache__" in root or "/tests" in root:
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            try:
                tree = ast.parse(open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read())
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    parts = node.module.split(".")
                    top.add(parts[0].lower().replace("_", "-"))
                    if len(parts) > 1:
                        submodule.add(parts[0].lower().replace("_", "-"))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        parts = alias.name.split(".")
                        top.add(parts[0].lower().replace("_", "-"))
                        if len(parts) > 1:
                            submodule.add(parts[0].lower().replace("_", "-"))
    return top, submodule


def scan_pins() -> tuple[list[str], list[str]]:
    """Scan 1 + 4: unbounded submodule-imported pins, and unused declarations."""
    failures: list[str] = []
    warnings: list[str] = []
    if not os.path.isdir(SERVERS_DIR):
        return failures, warnings
    for entry in sorted(os.listdir(SERVERS_DIR)):
        sdir = os.path.join(SERVERS_DIR, entry)
        if not os.path.isdir(sdir):
            continue
        reqs = _requirements(sdir)
        if not reqs:
            continue  # FR-014: no declarations is not a gap
        top, submodule = _imported_modules(sdir)
        for line in reqs:
            parsed = _parse_pin(line)
            if not parsed:
                continue
            name, spec = parsed
            key = f"{entry}:{name}"
            if key in PIN_EXCEPTIONS:
                continue
            if name in submodule and not _is_bounded(spec):
                failures.append(
                    f"pins: {entry}: {name!r} is pinned {spec or '(unpinned)'!r} with no upper "
                    f"bound, but the code imports a SUBMODULE of it — a new major can remove "
                    f"that submodule (as mcp 2.0.0 removed mcp.server.fastmcp)"
                )
            # FR-006c (unused-declaration detection) is DROPPED as unimplementable
            # reliably here. A distribution name is not a module name --
            # python-dotenv imports as `dotenv`, pyyaml as `yaml`, and so on -- and
            # resolving the mapping needs importlib.metadata against INSTALLED
            # packages, which this check cannot assume. A first implementation
            # produced 187 findings, nearly all false, which would have trained
            # maintainers to ignore this check entirely. A noisy check is worse than
            # no check. Recorded in the spec rather than shipped.
    return failures, warnings


def scan_bare_pip() -> list[str]:
    """Scan 2: bare pip in install steps, excluding comments and log strings."""
    failures: list[str] = []
    if not os.path.isfile(INSTALL_STEPS):
        return failures
    for lineno, line in enumerate(open(INSTALL_STEPS), 1):
        if not re.search(r"\bpip3?\s+install\b", line):
            continue
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.match(r"^(log_\w+|echo)\s", stripped):
            continue
        if re.search(r'(log_\w+|echo)\s+"[^"]*pip3?\s+install', line):
            continue
        if re.search(r"/bin/(python|pip)|python3?\s+-m\s+pip", line):
            continue
        if f"install-steps.sh:{lineno}" in BARE_PIP_EXCEPTIONS:
            continue
        failures.append(
            f"bare-pip: scripts/lib/install-steps.sh:{lineno}: bare pip invocation — use "
            f"netclaw_pip_install so packages land in the interpreter the server runs under"
        )
    return failures


def scan_venv() -> list[str]:
    """Scan 3: venv creation that depends on ensurepip."""
    failures: list[str] = []
    scripts_dir = os.path.join(REPO_ROOT, "scripts")
    for root, _dirs, files in os.walk(scripts_dir):
        for fn in files:
            if not fn.endswith(".sh"):
                continue
            path = os.path.join(root, fn)
            for lineno, line in enumerate(open(path, errors="ignore"), 1):
                if not re.search(r"python[0-9.]*\s+-m\s+venv", line):
                    continue
                stripped = line.strip()
                if stripped.startswith("#") or re.match(r"^(log_\w+|echo)\s", stripped):
                    continue
                if any(ok in line for ok in VENV_OK_PATTERNS):
                    continue
                rel = os.path.relpath(path, REPO_ROOT)
                failures.append(
                    f"venv: {rel}:{lineno}: 'python -m venv' needs ensurepip, which is absent "
                    f"on some hosts — use netclaw_venv_create (virtualenv/uv fallback)"
                )
    return failures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--warn-only", action="store_true")
    args = ap.parse_args()

    pin_fail, pin_warn = scan_pins()
    pip_fail = scan_bare_pip()
    venv_fail = scan_venv()
    failures = pin_fail + pip_fail + venv_fail

    if args.as_json:
        print(json.dumps({
            "surface": "dependencies",
            "status": "fail" if failures else ("flagged" if pin_warn else "pass"),
            "failures": failures,
            "warnings": pin_warn,
        }, indent=2))
    else:
        print(f"Servers scanned: {len([d for d in os.listdir(SERVERS_DIR) if os.path.isdir(os.path.join(SERVERS_DIR, d))])}")
        print()
        if failures:
            print("Dependency check: FAIL")
            for f in failures:
                print(f"  {f}")
        else:
            print("Dependency check: PASS")
        for w in pin_warn:
            print(f"  flagged: {w}")

    if failures and not args.warn_only:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
