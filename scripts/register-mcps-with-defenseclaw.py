#!/usr/bin/env python3
"""Register NetClaw MCP servers with DefenseClaw.

Reads MCP server configurations from openclaw.json and registers them
with DefenseClaw using 'defenseclaw mcp set'.

Usage:
    python3 scripts/register-mcps-with-defenseclaw.py [--dry-run] [--skip-scan]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def load_openclaw_config() -> dict:
    """Load openclaw.json configuration."""
    config_paths = [
        Path.home() / ".openclaw" / "config" / "openclaw.json",
        Path("config/openclaw.json"),
    ]

    for path in config_paths:
        if path.exists():
            with open(path) as f:
                return json.load(f)

    raise FileNotFoundError("openclaw.json not found")


def build_command(name: str, config: dict, skip_scan: bool) -> list[str]:
    """Build defenseclaw mcp set command for a server."""
    cmd = ["defenseclaw", "mcp", "set", name]

    if "command" in config:
        cmd.extend(["--command", config["command"]])

        if "args" in config:
            args = config["args"]
            if isinstance(args, list):
                cmd.extend(["--args", json.dumps(args)])
            else:
                cmd.extend(["--args", str(args)])

    if "url" in config:
        cmd.extend(["--url", config["url"]])

    # Add env vars (skip secrets - just note they're needed)
    if "env" in config:
        for key, value in config["env"].items():
            # Skip vars that reference environment variables
            if value.startswith("${"):
                continue
            cmd.extend(["--env", f"{key}={value}"])

    if skip_scan:
        cmd.append("--skip-scan")

    return cmd


def main():
    parser = argparse.ArgumentParser(description="Register MCPs with DefenseClaw")
    parser.add_argument("--dry-run", action="store_true", help="Show commands without executing")
    parser.add_argument("--skip-scan", action="store_true", help="Skip security scan when registering")
    parser.add_argument("--filter", help="Only register MCPs matching this prefix")
    args = parser.parse_args()

    try:
        config = load_openclaw_config()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    mcp_servers = config.get("mcpServers", {})

    if not mcp_servers:
        print("No MCP servers found in openclaw.json")
        sys.exit(0)

    print(f"Found {len(mcp_servers)} MCP servers in openclaw.json")
    print()

    success = 0
    failed = 0
    skipped = 0

    for name, server_config in sorted(mcp_servers.items()):
        if args.filter and not name.startswith(args.filter):
            continue

        # Skip remote MCP servers (url-only without command)
        if "url" in server_config and "command" not in server_config:
            if server_config["url"].startswith("mcp://"):
                print(f"  SKIP: {name} - remote MCP (mcp:// URL)")
                skipped += 1
                continue

        cmd = build_command(name, server_config, args.skip_scan)

        if args.dry_run:
            print(f"  WOULD RUN: {' '.join(cmd)}")
            success += 1
        else:
            print(f"  Registering: {name}...", end=" ", flush=True)
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    print("OK")
                    success += 1
                else:
                    print(f"FAILED")
                    print(f"    {result.stderr.strip()}")
                    failed += 1
            except subprocess.TimeoutExpired:
                print("TIMEOUT")
                failed += 1
            except Exception as e:
                print(f"ERROR: {e}")
                failed += 1

    print()
    print(f"Summary: {success} registered, {failed} failed, {skipped} skipped")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
