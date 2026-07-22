#!/usr/bin/env python3
"""Translate NetClaw's OpenClaw MCP registrations into Hermes config.yaml.

NetClaw's canonical MCP list lives in config/openclaw.json under the
``mcpServers`` key, where each entry is ``{command, args, env}`` — structurally
identical to what Hermes expects under ``mcp_servers`` in ~/.hermes/config.yaml.
This script performs that JSON→YAML port so a Hermes-based NetClaw install gets
the same network tooling an OpenClaw install would.

Two NetClaw-isms are normalised for Hermes, which runs from its own cwd and may
not share OpenClaw's ``${VAR}`` expansion semantics:

  * relative ``mcp-servers/...`` command/args paths are made absolute against
    the NetClaw repo root, and
  * ``${VAR}`` / ``${VAR:-default}`` env values are resolved against the shared
    .env (+ process env). A bare ``${VAR}`` with no value and no default is left
    as a literal placeholder so it's easy to grep and fill in later.

Merge is non-destructive: if the target config.yaml has no ``mcp_servers:`` block
the generated block is appended; if one already exists, the block is written to a
sidecar file and the user is told to merge it (we never rewrite existing YAML).

Usage:
    openclaw-to-hermes-mcp.py \
        --source   config/openclaw.json \
        --repo     /path/to/netclaw \
        --env      ~/.hermes/.env \
        --config   ~/.hermes/config.yaml \
        --sidecar  ~/.hermes/netclaw-mcp-servers.yaml

Stdlib only — no PyYAML dependency (the YAML we emit is a fixed, simple shape).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}")


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a KEY=VALUE .env file. Missing file -> empty dict."""
    env: dict[str, str] = {}
    if not path or not path.is_file():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            env[key] = val
    return env


def expand(value: str, env: dict[str, str]) -> str:
    """Resolve ${VAR} / ${VAR:-default} against env. Unresolved bare vars
    keep their literal ${VAR} form as an obvious placeholder."""

    def repl(m: re.Match) -> str:
        name, has_default, default = m.group(1), m.group(2), m.group(3)
        if name in env and env[name] != "":
            return env[name]
        if has_default:
            return default if default is not None else ""
        return m.group(0)  # leave ${VAR} literal

    return _VAR_RE.sub(repl, value)


def abspath_arg(token: str, repo: Path) -> str:
    """Make a relative NetClaw path (mcp-servers/...) absolute; leave bare
    commands (python3, npx, ...) and already-absolute paths untouched."""
    if token.startswith("mcp-servers/") or token.startswith("scripts/") or token.startswith("src/"):
        return str((repo / token).resolve())
    return token


def yaml_scalar(s: str) -> str:
    """Double-quote a scalar with minimal escaping (safe for our value set)."""
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def companion_env(env_block: dict, env_file_vars: dict[str, str]) -> dict[str, str]:
    """Return .env vars that belong to a server's own namespace but are absent
    from its explicit env block.

    OpenClaw sources the shared ~/.openclaw/.env into its own process, so every
    MCP subprocess inherits it in full — a server can read e.g. CML_VERIFY_SSL
    even though it never appears in that server's openclaw.json ``env`` block.
    Hermes, by contrast, passes ONLY the explicit block to the subprocess, so any
    such implicitly-inherited var silently disappears in the port. The concrete
    fallout: cml-mcp then verifies a self-signed cert and crashes at import, and
    the client sits forever on "connecting".

    We reproduce the inheritance *scoped to the server's own prefix* — the token
    before the first underscore of a key it already declares (``CML`` from
    ``CML_URL``). That materialises CML_VERIFY_SSL for cml-mcp while deliberately
    NOT dragging CHKP_* into a Check Point server whose block keys are generic
    (``MANAGEMENT_HOST``, ``API_KEY``), since those share no prefix. Only the
    parsed .env file is a source — never the porting shell's ambient environment
    — so the output stays reproducible and free of unrelated host vars."""
    prefixes = {k.split("_", 1)[0] for k in env_block if "_" in k}
    return {
        k: v
        for k, v in env_file_vars.items()
        if k not in env_block and "_" in k and k.split("_", 1)[0] in prefixes
    }


def is_configured(spec: dict, repo: Path, env: dict[str, str]) -> bool:
    """A server is 'configured' when none of its command/args/url/header/env
    values still holds an unresolved ``${VAR}`` placeholder after .env
    expansion. Unconfigured servers (missing required creds) are emitted
    ``enabled: false`` so Hermes never launches them — no failed connect, no
    reconnect-park churn, no shutdown-teardown noise. Fill the creds in .env
    and re-run the port (or flip ``enabled: true``) to bring one online."""
    probe: list[str] = []
    command = spec.get("command")
    url = spec.get("url")
    if command:
        probe.append(abspath_arg(str(command), repo))
        for a in (spec.get("args") or []):
            probe.append(abspath_arg(expand(str(a), env), repo))
    elif url:
        probe.append(expand(str(url), env))
    for hv in (spec.get("headers") or {}).values():
        probe.append(expand(str(hv), env))
    for ev in (spec.get("env") or {}).values():
        probe.append(expand(str(ev), env))
    return not any("${" in p for p in probe)


def emit_yaml(
    servers: dict[str, dict],
    repo: Path,
    env: dict[str, str],
    env_file_vars: dict[str, str],
) -> str:
    lines = ["mcp_servers:"]
    for name, spec in servers.items():
        lines.append(f"  {name}:")
        command = spec.get("command")
        url = spec.get("url")
        if command:
            lines.append(f"    command: {yaml_scalar(abspath_arg(str(command), repo))}")
            args = spec.get("args") or []
            if args:
                lines.append("    args:")
                for a in args:
                    lines.append(f"      - {yaml_scalar(abspath_arg(expand(str(a), env), repo))}")
        elif url:
            lines.append(f"    url: {yaml_scalar(expand(str(url), env))}")
            headers = spec.get("headers") or {}
            if headers:
                lines.append("    headers:")
                for hk, hv in headers.items():
                    lines.append(f"      {hk}: {yaml_scalar(expand(str(hv), env))}")
        env_block = spec.get("env") or {}
        companions = companion_env(env_block, env_file_vars)
        if env_block or companions:
            lines.append("    env:")
            for ek, ev in env_block.items():
                lines.append(f"      {ek}: {yaml_scalar(expand(str(ev), env))}")
            for ek, ev in companions.items():
                lines.append(f"      {ek}: {yaml_scalar(ev)}  # inherited from .env (implicit under OpenClaw)")
        enabled = "true" if is_configured(spec, repo, env) else "false"
        lines.append(f"    enabled: {enabled}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, help="path to config/openclaw.json")
    ap.add_argument("--repo", required=True, help="NetClaw repo root (for absolute paths)")
    ap.add_argument("--env", default="", help="shared .env for ${VAR} resolution")
    ap.add_argument("--config", required=True, help="target ~/.hermes/config.yaml")
    ap.add_argument("--sidecar", default="", help="fallback file if config.yaml already has mcp_servers")
    args = ap.parse_args()

    source = Path(args.source)
    if not source.is_file():
        print(f"[ERROR] source not found: {source}", file=sys.stderr)
        return 1

    try:
        servers = json.loads(source.read_text()).get("mcpServers", {})
    except (json.JSONDecodeError, OSError) as e:
        print(f"[ERROR] could not read {source}: {e}", file=sys.stderr)
        return 1

    if not servers:
        print("[WARN] no mcpServers found in source — nothing to translate")
        return 0

    repo = Path(args.repo).resolve()
    env_file_vars = parse_env_file(Path(args.env)) if args.env else {}
    env = dict(os.environ)
    env.update(env_file_vars)

    injected = sum(
        len(companion_env(s.get("env") or {}, env_file_vars)) for s in servers.values()
    )
    if injected:
        print(f"[INFO] materialised {injected} .env var(s) implicitly inherited under "
              f"OpenClaw into their server env blocks (e.g. CML_VERIFY_SSL).")

    block = emit_yaml(servers, repo, env, env_file_vars)
    config = Path(args.config)
    config.parent.mkdir(parents=True, exist_ok=True)

    existing = config.read_text() if config.is_file() else ""
    has_block = bool(re.search(r"(?m)^mcp_servers:\s*$", existing))

    disabled = sum(1 for s in servers.values() if not is_configured(s, repo, env))
    if disabled:
        print(f"[INFO] {disabled}/{len(servers)} servers have unresolved required "
              f"env → emitted enabled:false (fill creds in .env + re-run to enable).")

    if not has_block:
        with config.open("a") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write("\n# ── NetClaw MCP servers (generated by openclaw-to-hermes-mcp.py) ──\n")
            f.write(block)
        print(f"[INFO] wrote {len(servers)} MCP servers into {config}")
        return 0

    # config.yaml already declares mcp_servers — don't rewrite the user's YAML.
    sidecar = Path(args.sidecar) if args.sidecar else config.with_name("netclaw-mcp-servers.yaml")
    sidecar.write_text(block)
    print(f"[WARN] {config} already has an mcp_servers block — not modifying it.")
    print(f"[WARN] Generated {len(servers)} servers to {sidecar} — merge them under mcp_servers manually,")
    print(f"[WARN] or run 'hermes config edit' and paste them in.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
