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
    # ── Surfaced 2026-08-03 by spec 082, which taught this check to read
    # pyproject.toml (rag-mcp had none, so it had never been scanned) and added a
    # distribution→module alias map (pymupdf→fitz and friends never matched).
    #
    # Every finding below is REAL and of exactly the class this check exists to catch.
    # They are excepted for one specific reason: these directories are UNTRACKED
    # third-party clones (`git ls-files` returns nothing for them). An edit there is not
    # committable, evaporates on the next re-clone, and would leave a fixed-looking
    # check guarding nothing — which is worse than an honest exception.
    #
    # Closing them needs an upstream pin or a vendoring-policy change, not a local edit.
    # Recorded in specs/082-document-generation/VERIFICATION.md as found-not-fixed.
    # If any of these is ever vendored INTO the repo, delete its line here — the
    # exception is about the file being untracked, not about the hazard being acceptable.
    "AAP-Enterprise-MCP-Server:mcp": "untracked upstream clone — a local pin is not committable",
    "gait_mcp:mcp": "untracked upstream clone — a local pin is not committable",
    "infrahub-mcp:infrahub-sdk": "untracked upstream clone — a local pin is not committable",
    "junos-mcp-server:mcp": "untracked upstream clone — a local pin is not committable",
    "junos-mcp-server:starlette": "untracked upstream clone — a local pin is not committable",
    "mcp-nautobot:mcp": "untracked upstream clone — a local pin is not committable",
    "mcp-nvd:mcp": "untracked upstream clone — a local pin is not committable",
    "mcp-nvd:starlette": "untracked upstream clone — a local pin is not committable",
    "meraki-magic-mcp-community:mcp": "untracked upstream clone — a local pin is not committable",
    "servicenow-mcp:requests": "untracked upstream clone — a local pin is not committable",
    "servicenow-mcp:starlette": "untracked upstream clone — a local pin is not committable",
}
BARE_PIP_EXCEPTIONS: dict[str, str] = {}

# Scripts that create venvs correctly and must not be flagged.
VENV_OK_PATTERNS = ("uv venv", "virtualenv ", "netclaw_venv_create")


# Distribution name -> module name, where they differ. Spec 082 (2026-08-03).
#
# The submodule scan compares a DISTRIBUTION name from a requirements file against a
# MODULE name from an import statement. When they differ the two never meet, so the
# check silently passes. `pymupdf` is imported as `fitz`; `python-docx` as `docx`;
# `beautifulsoup4` as `bs4`. rag-mcp declared all three unbounded while importing
# submodules/attributes of them, and this check reported PASS.
#
# Deliberately small and specific. A large speculative table would rot the way
# EXTERNAL_INTEGRATIONS did (the lesson in this file's own docstring); these are the
# renames actually present in this repository, verified by grep.
DIST_TO_MODULE: dict[str, str] = {
    "pymupdf": "fitz",
    "python-docx": "docx",
    "python-pptx": "pptx",
    "beautifulsoup4": "bs4",
    "python-dotenv": "dotenv",
    "pyyaml": "yaml",
    "pillow": "pil",
    "msgraph-sdk": "msgraph",
    "azure-identity": "azure",
    "google-api-python-client": "googleapiclient",
    "protobuf": "google",
    "grpcio": "grpc",
    "grpcio-tools": "grpc-tools",
    "attrs": "attr",
    "scikit-learn": "sklearn",
    "sentence-transformers": "sentence-transformers",
}


def _module_for(dist_name: str) -> str:
    """The module name a distribution installs, normalised the same way imports are."""
    return DIST_TO_MODULE.get(dist_name, dist_name).lower().replace("_", "-")


def _requirements(server_dir: str) -> list[str]:
    """Declared dependencies, from requirements.txt AND pyproject.toml.

    pyproject.toml support added by spec 082. Before it, this function read
    requirements.txt only — and rag-mcp has none, declaring its dependencies in
    pyproject.toml instead. So rag-mcp was never scanned at all, and this script's
    PASS was an artefact of the file being invisible rather than of it being correct.
    """
    lines: list[str] = []

    path = os.path.join(server_dir, "requirements.txt")
    if os.path.isfile(path):
        lines += [
            ln.strip() for ln in open(path) if ln.strip() and not ln.strip().startswith("#")
        ]

    lines += _pyproject_dependencies(server_dir)
    return lines


def _pyproject_dependencies(server_dir: str) -> list[str]:
    """[project].dependencies from pyproject.toml.

    tomllib is stdlib from 3.11; below that this falls back to a narrow regex over the
    dependencies array. The fallback is deliberately conservative — it reads only
    quoted strings inside `dependencies = [...]` and gives up on anything else, because
    a wrong parse here produces false findings, and a noisy check is worse than no check
    (this file's own conclusion about FR-006c).
    """
    path = os.path.join(server_dir, "pyproject.toml")
    if not os.path.isfile(path):
        return []

    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

    if tomllib is not None:
        try:
            with open(path, "rb") as fh:
                data = tomllib.load(fh)
        except (OSError, ValueError):
            return []
        deps = (data.get("project") or {}).get("dependencies") or []
        return [str(d).strip() for d in deps if str(d).strip()]

    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return []
    m = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.S | re.M)
    if not m:
        return []
    return [d.strip() for d in re.findall(r'"([^"]+)"|\'([^\']+)\'', m.group(1)) for d in d if d]


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
            module = _module_for(name)
            if module in submodule and not _is_bounded(spec):
                rename = f" (imported as {module!r})" if module != name else ""
                failures.append(
                    f"pins: {entry}: {name!r}{rename} is pinned {spec or '(unpinned)'!r} with no "
                    f"upper bound, but the code imports a SUBMODULE of it — a new major can "
                    f"remove that submodule (as mcp 2.0.0 removed mcp.server.fastmcp)"
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
