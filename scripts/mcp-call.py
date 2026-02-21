#!/usr/bin/env python3
"""mcp-call.py — Send a single MCP tool call with proper protocol handshake.

Usage:
    python3 mcp-call.py <server-command> <tool-name> [arguments-json]

Examples:
    python3 mcp-call.py "python3 -u /path/to/pyats_mcp_server.py" pyats_list_devices
    python3 mcp-call.py "npx -y @drawio/mcp" open_drawio_mermaid '{"content":"graph TD; A-->B"}'
    python3 mcp-call.py "node /path/to/markmap/dist/index.js" create_markmap '{"content":"# Root"}'
"""

import json
import select
import shlex
import subprocess
import sys
import time


def send(proc, msg):
    """Send a JSON-RPC message to the MCP server via stdin."""
    proc.stdin.write((json.dumps(msg) + "\n").encode())
    proc.stdin.flush()


def recv(proc, timeout=30):
    """Read a JSON-RPC response from the MCP server via stdout."""
    if select.select([proc.stdout], [], [], timeout)[0]:
        line = proc.stdout.readline().decode().strip()
        if line:
            return json.loads(line)
    return None


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <server-command> <tool-name> [arguments-json]", file=sys.stderr)
        sys.exit(1)

    server_cmd = sys.argv[1]
    tool_name = sys.argv[2]
    args_json = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}

    cmd_parts = shlex.split(server_cmd)
    proc = subprocess.Popen(
        cmd_parts,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    try:
        # Step 1: Initialize
        send(proc, {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "netclaw", "version": "1.0"},
            },
        })
        init_resp = recv(proc, timeout=10)
        if not init_resp:
            print("Error: No response to initialize", file=sys.stderr)
            sys.exit(1)

        # Step 2: Initialized notification
        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        time.sleep(0.1)

        # Step 3: Tool call
        send(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args_json},
        })
        resp = recv(proc, timeout=30)
        if resp:
            print(json.dumps(resp.get("result", resp), indent=2))
        else:
            print("Error: No response to tool call", file=sys.stderr)
            sys.exit(1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
