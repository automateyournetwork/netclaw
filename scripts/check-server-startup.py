#!/usr/bin/env python3
"""Catch registered MCP servers that cannot start.

Spec 088. The gap this closes, in one sentence: **reconcile validated that servers were
declared consistently, never that they worked.**

Found 2026-08-04 while checking one thing about Meraki. Six of 98 registered servers could
not start — one of them (`aruba-cx-mcp`) had no server file at all — while
`reconcile-mcp.py` exited 0 and reported everything healthy. Twenty skills pointed at
dead servers.

That is the same shape as the two gaps before it:

  * `check-dependency-pins.py` read only `requirements.txt`, so a server declaring deps in
    `pyproject.toml` was never scanned at all (fixed by spec 082).
  * `verify-inventory-counts.py` checks headline arithmetic, not table membership, so the
    README sat two specs behind while every count passed (found by spec 082).

Each time, the check validated a *declaration* rather than a *fact*. This one runs the
thing.

TECHNIQUE, AND ITS LIMIT. Static import analysis was tried first and produced 11 findings,
5 of them false: several servers import a shared module resolved at runtime via sys.path,
which a static scan cannot see. Only *launching* the process gave the truth. So this
launches each server with a short timeout and reads what it says on the way down. That is
slower and it is the only thing that works.

We deliberately do NOT assert a successful MCP handshake — many servers legitimately exit
or block without credentials. The signal is narrower and reliable: a missing module, a
missing entry point, or a syntax error. Those are never correct.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(REPO_ROOT, "config", "openclaw.json")
# A server that is going to fail on import dies in well under a second; one that is
# healthy blocks on stdio forever. So the timeout only needs to be long enough to
# distinguish those, and it is the dominant cost of this check — at 25s across ~35
# servers it took over ten minutes, which is too slow to sit in CI.
TIMEOUT = 6
WORKERS = 8

# Recorded exceptions, each with a reason (the discipline spec 077 established).
# A server here is KNOWN not to start and that is accepted for a stated reason.
STARTUP_EXCEPTIONS: dict[str, str] = {
    # Cisco RADKit is not installable from PyPI. `radkit-client` 404s and
    # `cisco-radkit-client` is a RELOCATION STUB whose build fails with "This package has
    # been relocated!" -- Cisco distributes code-signed wheels from radkit.cisco.com only
    # (https://radkit.cisco.com/docs/security/security_codesign.html#python-wheels).
    #
    # So no install step can make this start, and it is already declared in
    # verify-inventory-counts.py's EXTERNAL_INTEGRATIONS as "Cisco RADKit". Excepted rather
    # than unregistered because the integration is real for operators who have RADKit; the
    # reason is recorded here so nobody spends another afternoon on `pip install`.
    #
    # NOTE for spec 088's record: that spec claimed prisma_sase was also unavailable. That
    # was WRONG -- prisma-sase is on PyPI and installed cleanly (6.8.1b1, spec 090).
    "radkit-mcp": "not on PyPI — Cisco ships code-signed wheels from radkit.cisco.com "
                  "(EXTERNAL_INTEGRATIONS: Cisco RADKit)",
}

# ── The seven found by spec 088, and how spec 090 resolved them ───────────────
#
# 1. FIXED by installing (the helper could not, until spec 090 gave netclaw_pip_install
#    PEP 668 handling): gnmi-mcp (pygnmi 0.8.15), junos-mcp (junos-eznc 2.8.2),
#    prisma-sdwan-mcp (prisma-sase 6.8.1b1). No shared pin moved.
#
#    CORRECTION: spec 088 recorded prisma_sase as "not on PyPI". That was WRONG --
#    pypi.org/prisma-sase returns 200 and it installed cleanly. The original conclusion
#    came from a failed bare `pip install` that had actually died on PEP 668, not on
#    package availability. One error masquerading as another.
#
# 2. FIXED by correcting a registration path: aruba-cx-mcp. Upstream nests its server at
#    mcp-servers/aruba-cx-mcp/ INSIDE its own repo, and the repo is cloned to
#    mcp-servers/aruba-cx-mcp/ -- so the real path carries that level twice. Nothing was
#    missing; the path was wrong.
#
# 3. FIXED by two separate defects: arista-cvp-mcp. Its `uv run --with` list omitted
#    urllib3 and python-dotenv (urllib3 IS installed host-wide, which is irrelevant --
#    `uv run` never sees system site-packages). Underneath that, upstream hardcoded
#    logging to '/home/admin/app.log', a foreign home directory, so it raised
#    FileNotFoundError before starting. Patched at install time because that clone is
#    gitignored and a working-copy edit is lost on the next fresh install.
#
# 4. EXCEPTED, genuinely unobtainable: radkit-mcp -- see STARTUP_EXCEPTIONS below.
#
# junos-mcp also needed a devices.json; jmcp.py exits without one and the repo ships only
# devices-template.json, which carries placeholder credentials and a device whose ip is
# literally "ip". The installer seeds an EMPTY inventory instead, so the server starts and
# honestly reports 0 devices.

STARTUP_EXCEPTIONS: dict[str, str] = {
    # Cisco RADKit is not installable from PyPI. `radkit-client` 404s and
    # `cisco-radkit-client` is a RELOCATION STUB whose build fails with "This package has
    # been relocated!" -- Cisco distributes code-signed wheels from radkit.cisco.com only
    # (https://radkit.cisco.com/docs/security/security_codesign.html#python-wheels).
    #
    # So no install step can make this start, and it is already declared in
    # verify-inventory-counts.py's EXTERNAL_INTEGRATIONS as "Cisco RADKit". Excepted rather
    # than unregistered because the integration is real for operators who have RADKit; the
    # reason is recorded here so nobody spends another afternoon on `pip install`.
    #
    # NOTE for spec 088's record: that spec claimed prisma_sase was also unavailable. That
    # was WRONG -- prisma-sase is on PyPI and installed cleanly (6.8.1b1, spec 090).
    "radkit-mcp": "not on PyPI — Cisco ships code-signed wheels from radkit.cisco.com "
                  "(EXTERNAL_INTEGRATIONS: Cisco RADKit)",
}

# ── The seven found on 2026-08-04, and why each needs a DIFFERENT fix ──────────
#
# Deliberately NOT added to STARTUP_EXCEPTIONS: they are real breakage, and silencing
# them would defeat the check on the day it was written. They are recorded here, and this
# check runs in --warn-only mode from reconcile until they are resolved (spec 088).
#
# 1. GATED SDK — not publicly distributable, so no install can fix it:
#      prisma-sdwan-mcp   missing prisma_sase   (no matching distribution on PyPI)
#      radkit-mcp         missing radkit_client (Cisco RADKit, licensed)
#    These should carry an EXTERNAL_INTEGRATIONS entry or be unregistered. A registered
#    server nobody can install is advertising a capability NetClaw does not have.
#
# 2. NO ENTRY POINT AT ALL:
#      aruba-cx-mcp       mcp-servers/aruba-cx-mcp/aruba_cx_mcp_server.py does not exist
#    4 skills route to it. Either vendor the server or unregister it.
#
# 3. WRONG ENVIRONMENT, not a missing package:
#      arista-cvp-mcp     missing urllib3
#    It launches via `uv run --directory ... --with fastmcp`, i.e. an ephemeral uv
#    environment. urllib3 IS installed system-wide (2.6.3) — it is absent from THAT env.
#    The fix is that server's `--with` list, not a system install. Recorded because the
#    naive reading ("install urllib3") is wrong and would waste someone's afternoon.
#
# 4. INSTALLABLE, BLOCKED BY THE HOST:
#      meraki-magic-mcp   missing meraki      (PyPI: 4.3.1)
#      gnmi-mcp           missing pygnmi      (PyPI: 0.8.15)
#      junos-mcp          missing jnpr        (PyPI: junos-eznc 2.8.2)
#    All three are publicly available and pull NO shared pin (verified by dry-run: none
#    touches fastmcp/mcp/httpx/cryptography/pydantic). But this host's system interpreter
#    is PEP 668 externally-managed, and `netclaw_pip_install` is a bare
#    `"$py" -m pip install "$@"` with no PEP 668 handling — so it cannot install them
#    either. That is a gap in the helper, not in these servers.

# Patterns that mean "this can never work", as opposed to "this needs configuration".
FATAL = [
    (re.compile(r"ModuleNotFoundError: No module named '([^']+)'"),
     "missing Python module {0}"),
    (re.compile(r"can't open file '([^']+)': \[Errno 2\] No such file or directory"),
     "entry point does not exist: {0}"),
    # A FileNotFoundError raised from inside the server -- a config/inventory file it was
    # told to load -- is NOT a missing entry point. Spec 088's generic pattern reported
    # junos-mcp's absent devices.json as "entry point or interpreter not found", which sent
    # me looking for the wrong thing. Ordered before the generic rule so it wins.
    (re.compile(r"FileNotFoundError: \[Errno 2\] No such file or directory: ['\"]([^'\"]+)['\"]"),
     "a file the server loads at startup is missing: {0}"),
    (re.compile(r"No such file or directory"), "entry point or interpreter not found"),
    (re.compile(r"SyntaxError: (.+)"), "syntax error: {0}"),
    (re.compile(r"ImportError: (.+)"), "import error: {0}"),
]


def registered(config: str = CONFIG) -> dict:
    with open(config, encoding="utf-8") as fh:
        return json.load(fh).get("mcpServers", {})


def launchable(name: str, spec: dict) -> tuple[list[str], str] | None:
    """The argv to try, or None with a reason to skip.

    Skips remote/HTTP servers, anything whose interpreter is absent from this host, and
    any component whose vendored directory was never cloned — a missing `node` or an
    uninstalled component is an install gap, not a broken registration, and conflating
    them would make this check noisy enough to ignore (and unusable in CI).
    """
    cmd = spec.get("command")
    if not cmd:
        return None
    if cmd in ("npx", "uvx", "docker", "node", "npm") and not shutil.which(cmd):
        return None
    if cmd not in ("npx", "uvx", "docker", "node", "npm") and not (
        shutil.which(cmd) or os.path.exists(os.path.join(REPO_ROOT, cmd))
    ):
        return None
    argv = [cmd] + list(spec.get("args", []))

    # NOT INSTALLED is not the same as BROKEN, and conflating them made this check
    # unusable as a gate: CI is a fresh checkout where every vendored server clone is
    # absent (they are gitignored runtime clones), so 30+ servers read as "entry point
    # does not exist" on a tree that is perfectly healthy.
    #
    # The distinction that matters: if a server's vendored DIRECTORY is present but the
    # specific file is not, the registration points somewhere wrong -- that is the real
    # aruba-cx-mcp bug and it must still fail. If the directory itself was never cloned,
    # the component simply is not installed here and there is nothing to judge.
    for arg in spec.get("args", []):
        if not isinstance(arg, str) or not arg.startswith("mcp-servers/"):
            continue
        parts = arg.split("/")
        if len(parts) < 2:
            continue
        vendored = os.path.join(REPO_ROOT, parts[0], parts[1])
        if not os.path.isdir(vendored):
            return None  # component not installed on this host
        break

    return argv, ""


def probe(name: str, argv: list[str]) -> str | None:
    """Launch it. Return a failure description, or None if it is not provably broken."""
    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    try:
        p = subprocess.run(argv, cwd=REPO_ROOT, env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        # Blocking on stdio is the CORRECT behaviour for an MCP server. Not a failure.
        return None
    except (OSError, ValueError) as exc:
        return f"could not launch: {exc}"
    blob = (p.stderr or "") + (p.stdout or "")
    for pat, tmpl in FATAL:
        m = pat.search(blob)
        if m:
            return tmpl.format(*m.groups()) if m.groups() else tmpl
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--warn-only", action="store_true",
                    help="report findings but exit 0")
    ap.add_argument("--only", help="check a single server by name")
    # Overridable so this check is testable against fixture servers with known startup
    # behaviour, rather than only against the live repository config.
    ap.add_argument("--config", default=CONFIG,
                    help=f"registration file to read (default: {CONFIG})")
    args = ap.parse_args()

    servers = registered(args.config)
    checked, skipped, failures = 0, [], []

    todo = []
    for name in sorted(servers):
        if args.only and name != args.only:
            continue
        if name in STARTUP_EXCEPTIONS:
            continue
        got = launchable(name, servers[name])
        if got is None:
            skipped.append(name)
            continue
        todo.append((name, got[0]))

    checked = len(todo)
    # Launched in parallel: each probe is dominated by waiting out TIMEOUT, so serial
    # execution made this check unusable in CI.
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for (name, _), why in zip(todo, pool.map(lambda t: probe(*t), todo)):
            if why:
                failures.append((name, why))

    print(f"Servers registered: {len(servers)}")
    print(f"  launched and checked: {checked}")
    print(f"  skipped (remote, interpreter absent, or not installed): {len(skipped)}")
    if STARTUP_EXCEPTIONS:
        print(f"  recorded exceptions: {len(STARTUP_EXCEPTIONS)}")

    if not failures:
        print("\nServer startup check: PASS")
        return 0

    print(f"\nServer startup check: FAIL ({len(failures)})")
    for name, why in failures:
        print(f"  startup: {name}: {why}")
    print("\nA registered server that cannot start is worse than an absent one: it is "
          "advertised in the catalog, counted in the docs, and skills route to it. Either "
          "fix it, unregister it, or record it in STARTUP_EXCEPTIONS with a reason.")
    return 0 if args.warn_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
