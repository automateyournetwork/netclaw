#!/usr/bin/env python3
"""Administrator tooling for the Cisco IQ remote MCP integration (spec 191).

Stdlib only. Registers Cisco IQ through NetClaw's native remote MCP support
(url + headers), manages the credential in the private runtime .env, and
diagnoses the connection. No Cisco IQ tool name or schema is assumed anywhere.

Contract source: GitHub issue #346 (the official guide could not be fetched
automatically; see specs/191-cisco-iq-mcp/spec.md, "Contract Provenance").

Secrets: the API key is only ever read from stdin or a no-echo prompt, written
only to the private .env, and every printed string passes through redact().
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SERVER_KEY = "cisco-iq-mcp"
KEY_VAR = "CISCO_IQ_API_KEY"
REGION_VAR = "CISCO_IQ_REGION"
AUTH_TEMPLATE = "Bearer ${" + KEY_VAR + "}"

# Single source of truth for regional endpoints (issue #346). Mirrored in docs,
# catalog and the skill; tests assert they agree.
REGIONS = {
    "emea": "https://eu-central-1.iq.cisco.com/mcp",
    "us": "https://us-west-2.iq.cisco.com/mcp",
    "apjc": "https://ap-southeast-2.iq.cisco.com/mcp",
}

FINDINGS = ("NOT_ENABLED", "KEY_UNSET", "ENV_PERMISSIONS", "TRANSPORT_FAILURE",
            "AUTH_FAILURE", "ZERO_TOOLS", "OK")

SECRET_FLAG = re.compile(r"^--?(key|api-?key|token|secret|password|bearer|authorization)(=|$)", re.I)
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO_ROOT / "config" / "cisco-iq-policy.json"

ASSIGNMENT = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


class AdminError(Exception):
    """Operational failure with a message that is safe to print."""

    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


# ----------------------------------------------------------------- redaction
_known_secrets: set[str] = set()


def register_secret(value: str | None) -> None:
    if value and len(value) >= 4:
        _known_secrets.add(value)


def redact(text) -> str:
    """Remove any registered secret, Bearer token or Authorization value."""
    out = str(text)
    for secret in sorted(_known_secrets, key=len, reverse=True):
        out = out.replace(secret, "[REDACTED]")
    out = re.sub(r"(?i)(bearer\s+)(?!\$\{)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", out)
    out = re.sub(r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?)(?!Bearer \$\{)[^\s,'\"}]+(\s+[^\s,'\"}]+)?",
                 lambda m: m.group(1) + "[REDACTED]" if "${" not in m.group(0) else m.group(0), out)
    return out


def say(message="", stream=None):
    print(redact(message), file=stream or sys.stdout)


# ------------------------------------------------------------------- region
def validate_region(value: str | None) -> str:
    if not value:
        raise AdminError("Region is required. Choose one of: " + ", ".join(REGIONS)
                         + ". It is never inferred from this host.", 2)
    region = value.strip().lower()
    if region not in REGIONS:
        raise AdminError("Unknown region. Choose one of: " + ", ".join(REGIONS), 2)
    return region


def check_endpoint(url: str, allow_loopback_http: bool = False) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == "https":
        return url
    if parsed.scheme == "http" and allow_loopback_http and parsed.hostname in LOOPBACK:
        return url
    raise AdminError("Refusing non-HTTPS endpoint (plain HTTP is allowed only for loopback test overrides).", 2)


# ------------------------------------------------------------- paths + files
def runtime_home(home: str | None) -> Path:
    return Path(home or os.environ.get("OPENCLAW_HOME") or Path.home() / ".openclaw").expanduser()


def env_path(home: Path) -> Path:
    return home / ".env"


def config_path(home: Path) -> Path:
    """Detect the runtime config (F1): prefer an existing file; both known
    locations are supported; otherwise default to <home>/openclaw.json."""
    override = os.environ.get("OPENCLAW_CONFIG_PATH")
    if override:
        return Path(override)
    for candidate in (home / "openclaw.json", home / "config" / "openclaw.json"):
        if candidate.exists():
            return candidate
    return home / "openclaw.json"


def _regular(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not stat.S_ISREG(path.stat().st_mode)):
        raise AdminError(f"{path.name} must be a regular file, not a symlink.")


def write_private(path: Path, data: str) -> None:
    _regular(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix=".netclaw-config-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def dotenv_quote(value: str) -> str:
    if any(c in value for c in ("\r", "\n", "\0")):
        raise AdminError("Values must be single-line text.", 2)
    if re.fullmatch(r"[A-Za-z0-9_@%+=:,./-]+", value):
        return value
    return json.dumps(value, ensure_ascii=False)


def dotenv_get(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    _regular(path)
    found = None
    for line in path.read_text().splitlines():
        m = ASSIGNMENT.match(line.strip())
        if m and m[1] == key:
            raw = m[2].strip()
            if raw.startswith('"'):
                try:
                    found = json.loads(raw)
                    continue
                except ValueError:
                    pass
            found = raw.strip("'\"")
    return found


def dotenv_set(path: Path, key: str, value: str | None) -> None:
    """Set (or, when value is None, remove) one assignment, keeping the rest."""
    _regular(path)
    original = path.read_text() if path.exists() else ""
    pattern = re.compile(r"^\s*(?:export\s+)?" + re.escape(key) + r"\s*=")
    lines = [l for l in original.splitlines() if not pattern.match(l)]
    if value is not None:
        lines.append(f"{key}={dotenv_quote(value)}")
    write_private(path, ("\n".join(lines) + "\n") if lines else "")


def backup(path: Path) -> Path | None:
    """Private 0600 backup plus a digest-only journal (never values)."""
    if not path.exists():
        return None
    stamp = time.strftime("%Y%m%dT%H%M%S")
    dest = path.with_name(f"{path.name}.cisco-iq-{stamp}.bak")
    n = 0
    while dest.exists():
        n += 1
        dest = path.with_name(f"{path.name}.cisco-iq-{stamp}-{n}.bak")
    data = path.read_text()
    write_private(dest, data)
    journal = dest.with_name(dest.name + ".state.json")
    write_private(journal, json.dumps({"backup_sha256": hashlib.sha256(data.encode()).hexdigest(),
                                       "source": path.name}) + "\n")
    return dest


def load_config(path: Path) -> dict:
    _regular(path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except ValueError:
        raise AdminError(f"{path.name} is not valid JSON; refusing to modify it.")
    if not isinstance(data, dict):
        raise AdminError(f"{path.name} has an unexpected shape; refusing to modify it.")
    return data


def registration(region: str) -> dict:
    return {
        "url": REGIONS[region],
        "headers": {"Authorization": AUTH_TEMPLATE},
        "env": {KEY_VAR: "${" + KEY_VAR + "}"},
    }


# ----------------------------------------------------------------- key input
def read_key(args) -> str | None:
    if getattr(args, "key_stdin", False):
        key = sys.stdin.read().strip("\r\n")
    elif sys.stdin.isatty() and getattr(args, "need_key_prompt", False):
        key = getpass.getpass("Cisco IQ API key (hidden): ").strip()
    else:
        return None
    if not key:
        raise AdminError("No API key supplied.", 2)
    if any(c in key for c in ("\r", "\n", "\0")):
        raise AdminError("API key must be single-line text.", 2)
    register_secret(key)
    return key


def reject_secret_args(argv: list[str]) -> None:
    for token in argv:
        if SECRET_FLAG.match(token):
            raise AdminError("Secrets are never accepted as arguments. Use --key-stdin or the hidden prompt.", 2)


# ------------------------------------------------------------------ commands
def state(home: Path) -> dict:
    cfg_path = config_path(home)
    cfg = load_config(cfg_path)
    reg = (cfg.get("mcpServers") or {}).get(SERVER_KEY)
    env = env_path(home)
    mode = None
    if env.exists() and not env.is_symlink():
        mode = stat.S_IMODE(env.stat().st_mode)
    key = dotenv_get(env, KEY_VAR)
    register_secret(key)
    return {
        "config_path": str(cfg_path), "env_path": str(env), "registered": reg is not None,
        "registration": reg, "region": dotenv_get(env, REGION_VAR),
        "key_set": bool(key), "env_mode": mode,
    }


def region_of_url(url: str | None) -> str | None:
    for name, endpoint in REGIONS.items():
        if url == endpoint:
            return name
    return None


def cmd_enable(args) -> int:
    region = validate_region(args.region)
    home = runtime_home(args.home)
    env, cfgp = env_path(home), config_path(home)
    args.need_key_prompt = not args.dry_run and dotenv_get(env, KEY_VAR) is None
    key = read_key(args)
    cfg = load_config(cfgp)
    if cfgp.exists() and "mcpServers" not in cfg:
        raise AdminError(f"{cfgp.name} has no mcpServers container; refusing to guess its layout.")
    reg = registration(region)
    say(f"Cisco IQ enable (region={region})")
    say(f"  endpoint : {REGIONS[region]}")
    say(f"  header   : Authorization: {AUTH_TEMPLATE}   (resolved at runtime, never written)")
    say(f"  env file : {env}  ({KEY_VAR}: {'will be set' if key else 'unchanged/unset'}, {REGION_VAR}={region})")
    say(f"  config   : {cfgp}")
    if args.dry_run:
        say("Dry run: nothing written.")
        return 0
    if key is None and dotenv_get(env, KEY_VAR) is None:
        say("WARNING: no API key stored yet. Run: printf '%s' \"$KEY\" | scripts/cisco-iq-enable.sh rotate --key-stdin")
    if key is not None:
        backup(env)
        dotenv_set(env, KEY_VAR, key)
    dotenv_set(env, REGION_VAR, region)
    cfg.setdefault("mcpServers", {})[SERVER_KEY] = reg
    write_private(cfgp, json.dumps(cfg, indent=2) + "\n")
    say("Enabled. Reload the OpenClaw MCP runtime, then run: scripts/cisco-iq-enable.sh diagnose")
    say("Reminder: the key must be owned by a user principal (service-account keys expose no tools).")
    return 0


def cmd_update(args) -> int:
    home = runtime_home(args.home)
    st = state(home)
    region = validate_region(args.region or st["region"])
    previous = st["region"] or region_of_url((st["registration"] or {}).get("url"))
    say(f"Cisco IQ update: {previous or 'none'} -> {region}")
    if args.dry_run:
        say("Dry run: nothing written.")
        return 0
    cfgp = config_path(home)
    cfg = load_config(cfgp)
    cfg.setdefault("mcpServers", {})[SERVER_KEY] = registration(region)
    write_private(cfgp, json.dumps(cfg, indent=2) + "\n")
    dotenv_set(env_path(home), REGION_VAR, region)
    say("Updated registration (key untouched).")
    return 0


def cmd_rotate(args) -> int:
    home = runtime_home(args.home)
    env = env_path(home)
    args.need_key_prompt = True
    key = read_key(args)
    if key is None:
        raise AdminError("Provide the new key with --key-stdin or run interactively.", 2)
    if args.dry_run:
        say("Dry run: key would be replaced; registration untouched.")
        return 0
    bak = backup(env)
    dotenv_set(env, KEY_VAR, key)
    say("Credential rotated (value not shown). Registration unchanged."
        + (f" Private backup: {bak.name}" if bak else ""))
    return 0


def cmd_disable(args) -> int:
    home = runtime_home(args.home)
    cfgp = config_path(home)
    cfg = load_config(cfgp)
    present = SERVER_KEY in (cfg.get("mcpServers") or {})
    if args.dry_run:
        say(f"Dry run: would remove registration ({'present' if present else 'absent'})"
            + (" and purge credential." if args.purge_credential else "; credential kept."))
        return 0
    if present:
        del cfg["mcpServers"][SERVER_KEY]
        write_private(cfgp, json.dumps(cfg, indent=2) + "\n")
        say("Registration removed.")
    else:
        say("Registration already absent (no change).")
    env = env_path(home)
    if args.purge_credential:
        if dotenv_get(env, KEY_VAR) is not None or dotenv_get(env, REGION_VAR) is not None:
            backup(env)
            dotenv_set(env, KEY_VAR, None)
            dotenv_set(env, REGION_VAR, None)
        say("Credential and region purged from the private env file.")
    else:
        say("Credential kept (use --purge-credential to remove it).")
    return 0


def cmd_status(args) -> int:
    st = state(runtime_home(args.home))
    out = {
        "registered": st["registered"],
        "region": st["region"],
        "endpoint": (st["registration"] or {}).get("url"),
        "key_set": st["key_set"],
        "env_mode": oct(st["env_mode"]) if st["env_mode"] is not None else None,
        "config_path": st["config_path"], "env_path": st["env_path"],
    }
    if args.json:
        say(json.dumps(out, indent=2))
    else:
        for k, v in out.items():
            say(f"{k:12}: {v}")
    return 0


# ------------------------------------------------------------------ transport
def _parse_body(raw: bytes, content_type: str):
    text = raw.decode("utf-8", "replace")
    if "text/event-stream" in content_type:
        for line in text.splitlines():
            if line.startswith("data:"):
                try:
                    return json.loads(line[5:].strip())
                except ValueError:
                    continue
        return None
    try:
        return json.loads(text) if text.strip() else None
    except ValueError:
        return None


def rpc(url: str, key: str, payload: dict, session: str | None, timeout: float = 10.0):
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream",
               "Authorization": "Bearer " + key}
    if session:
        headers["Mcp-Session-Id"] = session
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return (_parse_body(resp.read(), resp.headers.get("Content-Type", "")),
                resp.headers.get("Mcp-Session-Id") or session)


def list_tools(url: str, key: str) -> list[dict]:
    """MCP initialize then tools/list. Raises urllib errors for the caller to classify."""
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "netclaw-cisco-iq-diagnose", "version": "1"}}}
    _, session = rpc(url, key, init, None)
    try:
        rpc(url, key, {"jsonrpc": "2.0", "method": "notifications/initialized"}, session)
    except urllib.error.HTTPError as err:
        if err.code not in (202, 400, 404, 405):
            raise
    body, _ = rpc(url, key, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, session)
    tools = ((body or {}).get("result") or {}).get("tools")
    return tools if isinstance(tools, list) else []


def finding(status: str, detail: str, hints=None) -> dict:
    assert status in FINDINGS
    return {"status": status, "detail": redact(detail), "hints": [redact(h) for h in (hints or [])]}


def diagnose_state(args) -> tuple[dict, dict, str | None, str | None]:
    home = runtime_home(args.home)
    st = state(home)
    key = dotenv_get(env_path(home), KEY_VAR)
    url = (st["registration"] or {}).get("url")
    if args.endpoint_override:
        url = check_endpoint(args.endpoint_override, allow_loopback_http=True)
    return st, {}, key, url


def cmd_diagnose(args) -> int:
    st, _, key, url = diagnose_state(args)
    result = None
    mode = st["env_mode"]
    if not st["registered"]:
        result = finding("NOT_ENABLED", "No cisco-iq-mcp registration found.",
                         ["Run: scripts/cisco-iq-enable.sh enable --region <emea|us|apjc>"])
    elif not key:
        result = finding("KEY_UNSET", f"{KEY_VAR} is not set in the private env file.",
                         ["Run: printf '%s' \"$KEY\" | scripts/cisco-iq-enable.sh rotate --key-stdin"])
    elif mode is not None and mode & 0o077:
        result = finding("ENV_PERMISSIONS", f"Env file mode is {oct(mode)}; expected 0600.",
                         [f"chmod 600 {st['env_path']}"])
    elif st["registered"] and region_of_url(url) is None and not args.endpoint_override:
        result = finding("NOT_ENABLED", "Registered URL is not one of the three known regional endpoints.",
                         ["Run enable/update with an explicit region."])
    elif not args.live:
        result = finding("OK", "Offline checks passed (registration, key present, permissions). "
                               "No network check was performed; use --live.")
    else:
        try:
            tools = list_tools(url, key)
            if tools:
                result = finding("OK", f"Connected; server lists {len(tools)} tool(s).")
            else:
                result = finding("ZERO_TOOLS", "Authenticated but the server lists no tools.",
                                 ["A service-account-owned key receives no tools; use a key owned by a user principal.",
                                  "The key owner's permissions may be insufficient."])
        except urllib.error.HTTPError as err:
            if err.code in (401, 403):
                result = finding("AUTH_FAILURE", f"HTTP {err.code} from the endpoint.",
                                 ["Possible causes (not confirmed): expired or revoked key, "
                                  "account is in a different region, key lacks permission.",
                                  "Other regions: " + ", ".join(r for r in REGIONS if r != region_of_url(url))
                                  + " (never switched automatically)."])
            else:
                result = finding("TRANSPORT_FAILURE", f"HTTP {err.code} from the endpoint.")
        except (urllib.error.URLError, OSError, TimeoutError) as err:
            result = finding("TRANSPORT_FAILURE", f"Cannot reach endpoint: {type(err).__name__}.")
    report = {"region": st["region"] or region_of_url(url), "endpoint": url, **result}
    if args.json:
        say(json.dumps(report, indent=2))
    else:
        say(f"status : {report['status']}")
        say(f"region : {report['region']}")
        say(f"detail : {report['detail']}")
        for h in report["hints"]:
            say(f"  hint : {h}")
    return 0 if report["status"] == "OK" else 1


# --------------------------------------------------------------------- policy
def load_policy(path: Path = POLICY_PATH) -> dict:
    policy = json.loads(path.read_text())
    if (policy.get("mode") != "deny-by-default" or policy.get("read_only") is not True
            or not isinstance(policy.get("allow"), list) or not isinstance(policy.get("deny_patterns"), list)):
        raise AdminError("Policy file does not satisfy the deny-by-default read-only schema.")
    return policy


def classify(names: list[str], policy: dict) -> dict:
    allow = {e["name"] for e in policy["allow"]}
    deny = [re.compile(p, re.I) for p in policy["deny_patterns"]]
    out = {"allowed": [], "denied": [], "unlisted": []}
    for name in names:
        if any(p.search(name) for p in deny):
            out["denied"].append(name)          # deny patterns win over the allowlist
        elif name in allow:
            out["allowed"].append(name)
        else:
            out["unlisted"].append(name)        # deny by default until an admin allowlists it
    return out


def cmd_policy_check(args) -> int:
    policy = load_policy(Path(args.policy) if args.policy else POLICY_PATH)
    if args.tools_file:
        data = json.loads(Path(args.tools_file).read_text())
        data = data.get("tools", data) if isinstance(data, dict) else data
        names = [t["name"] if isinstance(t, dict) else str(t) for t in data]
    elif args.live:
        st, _, key, url = diagnose_state(args)
        if not key or not url:
            raise AdminError("Not enabled or key unset; cannot list tools.")
        try:
            names = [t.get("name", "") for t in list_tools(url, key)]
        except (urllib.error.URLError, OSError) as err:
            raise AdminError(f"Cannot list tools: {type(err).__name__}")
    else:
        raise AdminError("Provide --tools-file FILE or --live.", 2)
    result = classify(names, policy)
    if args.json:
        say(json.dumps(result, indent=2))
    else:
        for bucket in ("allowed", "denied", "unlisted"):
            say(f"{bucket}: {', '.join(result[bucket]) or '-'}")
        blocked = result["denied"] + result["unlisted"]
        if blocked:
            say("If DefenseClaw is enabled, block anything not allowlisted:")
            for name in blocked:
                say(f"  defenseclaw tool block {name}")
        say("Note: without DefenseClaw this policy is enforced by agent instructions, not a hard per-tool gate.")
    return 0


# ------------------------------------------------------------------------ cli
def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--home", help="runtime home (default ~/.openclaw)")
    common.add_argument("--dry-run", action="store_true", help="preview only; write nothing")
    common.add_argument("--json", action="store_true")
    p = argparse.ArgumentParser(prog="cisco-iq-enable.sh", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("enable", parents=[common]); s.add_argument("--region"); s.add_argument("--key-stdin", action="store_true"); s.set_defaults(fn=cmd_enable)
    s = sub.add_parser("update", parents=[common]); s.add_argument("--region"); s.set_defaults(fn=cmd_update)
    s = sub.add_parser("rotate", parents=[common]); s.add_argument("--key-stdin", action="store_true"); s.set_defaults(fn=cmd_rotate)
    s = sub.add_parser("disable", parents=[common]); s.add_argument("--purge-credential", action="store_true"); s.set_defaults(fn=cmd_disable)
    s = sub.add_parser("status", parents=[common]); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("diagnose", parents=[common]); s.add_argument("--live", action="store_true"); s.add_argument("--endpoint-override", help="loopback http(s) URL for tests"); s.set_defaults(fn=cmd_diagnose)
    s = sub.add_parser("policy-check", parents=[common]); s.add_argument("--tools-file"); s.add_argument("--live", action="store_true"); s.add_argument("--policy"); s.add_argument("--endpoint-override"); s.set_defaults(fn=cmd_policy_check)
    return p


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        reject_secret_args(argv)
        args = build_parser().parse_args(argv)
        return args.fn(args)
    except AdminError as err:
        say("ERROR: " + str(err), sys.stderr)
        return err.code
    except SystemExit:
        raise
    except Exception as err:  # never leak values through tracebacks
        say(f"ERROR: unexpected {type(err).__name__}", sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
