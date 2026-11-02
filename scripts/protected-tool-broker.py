#!/usr/bin/env python3
"""Private one-operation MCP child for the protected execute-once pyATS read.

Only stdio is exposed. Trusted parent supplies immutable arguments through a
private file and records the effect claim before starting this child.
"""
import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from protected_pyats import execute_once, validate_arguments, validate_document


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--upstream-sha256", required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--endpoint-sha256", required=True)
    parser.add_argument("--approved", type=Path, required=True)
    parser.add_argument("--logfile", type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.upstream.read_bytes()).hexdigest() != args.upstream_sha256:
        raise ValueError("upstream_revision_changed")
    manifest = json.loads(args.source_manifest.read_text())
    if set(manifest) != {"pyats_mcp_server.py", "pyats_testbed_builder.py", "pyats_tasks.py"}:
        raise ValueError("source_closure_required")
    for name, digest in manifest.items():
        if hashlib.sha256((args.upstream.parent / name).read_bytes()).hexdigest() != digest:
            raise ValueError("source_closure_changed")
    approved = json.loads(args.approved.read_text())
    validate_arguments(approved)
    import yaml
    validate_document(yaml.safe_load(Path(os.environ["PYATS_TESTBED_PATH"]).read_text()), approved["device_name"])
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    os.environ["PYATS_MCP_CONN_CACHE_TTL"] = "0"
    sys.path.insert(0, str(args.upstream.parent))
    spec = importlib.util.spec_from_file_location("protected_pyats_upstream", args.upstream)
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)
    from mcp.server.mcpserver import MCPServer
    server = MCPServer("NetClaw protected pyATS", version="171")
    spent = False

    async def pyats_run_show_command(device_name: str, command: str, timeout: int, retries: int) -> dict:
        nonlocal spent
        candidate = dict(device_name=device_name, command=command, timeout=timeout, retries=retries)
        validate_arguments(candidate)
        if candidate != approved or spent:
            raise ValueError("approved_call_spent_or_changed")
        spent = True
        return await asyncio.to_thread(execute_once, upstream, candidate, logfile=args.logfile,
                                       endpoint_sha256=args.endpoint_sha256)

    server.add_tool(pyats_run_show_command,
                    description="Execute the exact approved show version once; parse captured output.")
    server.run(transport="stdio")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Protected pyATS child refused; inspect private evidence.", file=sys.stderr)
        raise SystemExit(1)
