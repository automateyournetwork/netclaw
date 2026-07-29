#!/usr/bin/env python3
"""Give every relative-path MCP server entry an explicit cwd.

config/openclaw.json registers most NetClaw servers with repo-relative paths,
e.g. `python3 -u mcp-servers/memory-mcp/memory_mcp_server.py`. The installer
copies that file verbatim to ~/.openclaw/openclaw.json, but the OpenClaw
gateway does not run from the repo — it typically runs from $HOME. Any entry
without a `cwd` then resolves its script path against the wrong directory and
dies at launch with:

    python3: can't open file '/home/<user>/mcp-servers/...': [Errno 2]

Entries that already declare a `cwd` are left alone, as are entries whose
command and args are all absolute paths or plain package names (uvx/npx).

An arg is treated as a repo-relative path only when it actually resolves to an
existing file under the repo root, so package specs that merely contain a slash
(`npx -y @zereight/mcp-gitlab`) are not misread as paths.

Usage:
    normalize-mcp-cwd.py --config <path> --repo <netclaw repo root> [--dry-run]
"""
import argparse
import json
import sys
from pathlib import Path


def needs_cwd(entry: dict, repo: Path) -> bool:
    if entry.get("cwd"):
        return False
    command = entry.get("command")
    if not command:
        return False

    candidates = [command, *entry.get("args", [])]
    for c in candidates:
        if not isinstance(c, str) or c.startswith(("-", "/", "~", "$")):
            continue
        if (repo / c).exists():
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    repo = Path(args.repo).resolve()

    if not cfg_path.is_file():
        print(f"normalize-mcp-cwd: {cfg_path} not found — nothing to do")
        return 0

    cfg = json.loads(cfg_path.read_text())

    # Support both the flat `mcpServers` shape and the nested `mcp.servers`.
    if isinstance(cfg.get("mcpServers"), dict):
        servers = cfg["mcpServers"]
    elif isinstance(cfg.get("mcp"), dict) and isinstance(cfg["mcp"].get("servers"), dict):
        servers = cfg["mcp"]["servers"]
    else:
        print("normalize-mcp-cwd: no MCP server block found — nothing to do")
        return 0

    fixed = []
    for name, entry in servers.items():
        if isinstance(entry, dict) and needs_cwd(entry, repo):
            entry["cwd"] = str(repo)
            fixed.append(name)

    if not fixed:
        print("normalize-mcp-cwd: all MCP entries already resolve correctly")
        return 0

    print(f"normalize-mcp-cwd: set cwd={repo} on {len(fixed)} entries:")
    for name in fixed:
        print(f"  - {name}")

    if args.dry_run:
        print("normalize-mcp-cwd: dry run, not writing")
        return 0

    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"normalize-mcp-cwd: wrote {cfg_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
