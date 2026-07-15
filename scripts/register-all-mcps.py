#!/usr/bin/env python3
"""Register ALL NetClaw MCP servers with DefenseClaw.

Discovers MCP servers from the mcp-servers directory (not just openclaw.json)
and registers them with DefenseClaw.

Usage:
    python3 scripts/register-all-mcps.py [--dry-run] [--skip-scan]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def find_mcp_entry_point(mcp_dir: Path) -> tuple[str, list[str]] | None:
    """Find the main entry point for an MCP server.

    Returns (command, args) tuple or None if not found.
    """
    # Common patterns for MCP server entry points
    patterns = [
        # Python servers
        ("*_mcp_server.py", "python3", ["-u"]),
        ("*_mcp.py", "python3", ["-u"]),
        ("server.py", "python3", ["-u"]),
        ("main.py", "python3", ["-u"]),
        ("mcp_server.py", "python3", ["-u"]),
        # Node servers
        ("index.js", "node", []),
        ("server.js", "node", []),
        # Look in src directory
    ]

    for pattern, command, base_args in patterns:
        matches = list(mcp_dir.glob(pattern))
        if matches:
            # Use relative path from netclaw root
            rel_path = matches[0].relative_to(mcp_dir.parent.parent)
            return command, base_args + [str(rel_path)]

    # Check src subdirectory
    src_dir = mcp_dir / "src"
    if src_dir.exists():
        for pattern, command, base_args in patterns:
            matches = list(src_dir.glob(pattern))
            if matches:
                rel_path = matches[0].relative_to(mcp_dir.parent.parent)
                return command, base_args + [str(rel_path)]

    return None


def load_existing_config() -> dict:
    """Load existing MCP config from openclaw.json."""
    config_path = Path.home() / ".openclaw" / "config" / "openclaw.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f).get("mcpServers", {})
        except:
            pass
    return {}


def main():
    parser = argparse.ArgumentParser(description="Register ALL MCPs with DefenseClaw")
    parser.add_argument("--dry-run", action="store_true", help="Show commands without executing")
    parser.add_argument("--skip-scan", action="store_true", help="Skip security scan when registering")
    parser.add_argument("--mcp-dir", default="mcp-servers", help="MCP servers directory")
    args = parser.parse_args()

    # Find the netclaw root directory
    script_dir = Path(__file__).parent
    netclaw_root = script_dir.parent
    mcp_base = netclaw_root / args.mcp_dir

    if not mcp_base.exists():
        print(f"Error: MCP directory not found: {mcp_base}")
        sys.exit(1)

    # Load existing config
    existing_config = load_existing_config()

    # Find all MCP directories
    mcp_dirs = sorted([d for d in mcp_base.iterdir() if d.is_dir()])

    print(f"Found {len(mcp_dirs)} MCP directories in {mcp_base}")
    print(f"Already configured in openclaw.json: {len(existing_config)}")
    print()

    registered = 0
    skipped = 0
    failed = 0
    no_entry = 0

    for mcp_dir in mcp_dirs:
        name = mcp_dir.name

        # Normalize name for DefenseClaw (lowercase, hyphens)
        dc_name = name.lower().replace("_", "-").replace(" ", "-")

        # Check if already in openclaw.json with different config
        existing = existing_config.get(name) or existing_config.get(dc_name)

        # Find entry point
        entry = find_mcp_entry_point(mcp_dir)

        if entry is None:
            print(f"  SKIP: {name} - no entry point found")
            no_entry += 1
            continue

        command, cmd_args = entry

        # Build defenseclaw mcp set command
        cmd = ["defenseclaw", "mcp", "set", dc_name, "--command", command]
        cmd.extend(["--args", json.dumps(cmd_args)])

        if args.skip_scan:
            cmd.append("--skip-scan")

        if args.dry_run:
            print(f"  WOULD: {dc_name} ({command} {' '.join(cmd_args)})")
            registered += 1
        else:
            print(f"  Registering: {dc_name}...", end=" ", flush=True)
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    print("OK")
                    registered += 1
                else:
                    err = result.stderr.strip()[:60]
                    print(f"FAILED ({err})")
                    failed += 1
            except subprocess.TimeoutExpired:
                print("TIMEOUT")
                failed += 1
            except Exception as e:
                print(f"ERROR: {e}")
                failed += 1

    print()
    print(f"Summary:")
    print(f"  {registered} {'would be ' if args.dry_run else ''}registered")
    print(f"  {no_entry} skipped (no entry point)")
    print(f"  {failed} failed")


if __name__ == "__main__":
    main()
