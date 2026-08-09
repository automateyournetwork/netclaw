"""The dedicated venv, and proof it does not disturb the system interpreter.
Spec 083, FR-037a/b/c, SC-026/027.

This is not hygiene. The vendored server requires fastmcp 3.x; FIVE NetClaw servers pin
fastmcp<3. A shared install breaks all five — spec 076's cryptography incident verbatim.
"""
from __future__ import annotations
import json, os, re, subprocess
from _harness import FAILURES, check, read, repo, run, skip  # noqa: F401

PINNED_BELOW_3 = ["netbox-mcp-server", "CiscoFMC-MCP-server-community",
                  "Wikipedia_MCP", "rag-mcp", "ISE_MCP"]
VENV_PY = repo("mcp-servers", "zabbix-mcp", ".venv", "bin", "python")

def _version(python_exe: str, dist: str) -> str | None:
    out = subprocess.run([python_exe, "-c",
        f"import importlib.metadata as m;print(m.version({dist!r}))"],
        capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else None

def test_venv_exists_and_holds_fastmcp_3():
    if not os.path.exists(VENV_PY):
        skip("venv checks", "venv not built — run the installer")
        return
    v = _version(VENV_PY, "fastmcp")
    check("the venv resolves fastmcp 3.x", bool(v) and v.startswith("3."), f"got {v}")
    check("the venv has the vendored package installed",
          _version(VENV_PY, "zabbix-mcp-server") is not None, "not installed")

def test_system_interpreter_is_untouched():
    import importlib.metadata as md
    try:
        sysv = md.version("fastmcp")
    except Exception:
        skip("system fastmcp check", "fastmcp not installed system-wide")
        return
    check("the SYSTEM interpreter still resolves fastmcp 2.x", sysv.startswith("2."),
          f"got {sysv} — installing the Zabbix server leaked into the shared interpreter, "
          f"which breaks {', '.join(PINNED_BELOW_3)}")

def test_the_five_pinned_servers_are_still_satisfied():
    import importlib.metadata as md
    try:
        sysv = md.version("fastmcp")
    except Exception:
        skip("pinned-server check", "fastmcp not installed system-wide")
        return
    major = int(sysv.split(".")[0])
    for server in PINNED_BELOW_3:
        found = False
        for fn in ("pyproject.toml", "requirements.txt"):
            p = repo("mcp-servers", server, fn)
            if os.path.exists(p):
                if re.search(r"fastmcp[^\n]*<\s*3", open(p, encoding="utf-8").read()):
                    found = True
        check(f"{server} still declares fastmcp<3", found,
              "its pin vanished — either it was relaxed, or this list is stale")
    check(f"the installed system fastmcp ({sysv}) satisfies <3", major < 3,
          "all five pinned servers are now unsatisfiable")

def test_installer_never_uses_bare_venv():
    steps = read("scripts", "lib", "install-steps.sh")
    fn = steps[steps.index("component_install_zabbix()"):]
    fn = fn[:fn.index("\n}\n")]
    # Line-aware, not string-aware: this function deliberately MENTIONS bare venv in a
    # comment and in a log_warn that tells the operator not to use it. Matching the raw
    # string would flag the warning as the offence it warns about.
    offenders = []
    for line in fn.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("log_warn") or stripped.startswith("echo"):
            continue
        if "python3 -m venv" in stripped:
            offenders.append(stripped)
    check("no executable line calls bare `python3 -m venv`", not offenders,
          f"bare venv fails on hosts without ensurepip (spec 077 hazard #3, hit live in "
          f"Phase 0). Offending line(s): {offenders}")
    check("the installer uses netclaw_venv_create or uv",
          "netclaw_venv_create" in fn or "uv venv" in fn, "no supported venv creation path")
    check("the installer explains why the venv exists",
          "fastmcp" in fn and ("<3" in fn or "3.x" in fn),
          "without the rationale a maintainer will 'simplify' it away")

def test_registration_points_at_the_venv():
    cfg = json.loads(read("config", "openclaw.json"))["mcpServers"]["zabbix-mcp"]
    check("the registered command is the venv interpreter",
          ".venv/bin/python" in cfg["command"],
          f"got {cfg['command']!r} — a system python would resolve the wrong fastmcp")
    check("the command path is repo-relative", not cfg["command"].startswith("/"),
          "an absolute path breaks on every other machine")

def test_venv_is_gitignored():
    out = subprocess.run(["git", "check-ignore", "-v",
                          "mcp-servers/zabbix-mcp/.venv/pyvenv.cfg"],
                         capture_output=True, text=True, cwd=repo())
    check("the venv is git-ignored", out.returncode == 0,
          "the negation !mcp-servers/zabbix-mcp/ re-includes everything beneath it — "
          "without an explicit re-ignore the whole virtualenv gets committed")
    check("the vendored source is NOT ignored",
          subprocess.run(["git", "check-ignore",
                          "mcp-servers/zabbix-mcp/vendor/zabbix-mcp-server/pyproject.toml"],
                         capture_output=True, cwd=repo()).returncode != 0,
          "the vendored tree is invisible to git")

TESTS = [test_venv_exists_and_holds_fastmcp_3, test_system_interpreter_is_untouched,
         test_the_five_pinned_servers_are_still_satisfied, test_installer_never_uses_bare_venv,
         test_registration_points_at_the_venv, test_venv_is_gitignored]

if __name__ == "__main__":
    raise SystemExit(run(TESTS, "venv isolation"))
