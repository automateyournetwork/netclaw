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
import os
import select
import shlex
import subprocess
import sys
import time


def send(proc, msg):
    """Send a JSON-RPC message to the MCP server via stdin."""
    proc.stdin.write((json.dumps(msg) + "\n").encode())
    proc.stdin.flush()


def recv(proc, timeout=30, expected_id=None):
    """Read JSON-RPC messages from stdout and return the matching response.

    Some MCP servers emit startup logs or notifications before the response we
    care about. This function tolerates non-JSON lines and can optionally wait
    for a specific JSON-RPC id.
    """
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        remaining = max(0, deadline - time.monotonic())
        if not select.select([proc.stdout], [], [], remaining)[0]:
            break

        raw = proc.stdout.readline()
        if not raw:
            continue

        line = raw.decode(errors="replace").strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            # Ignore non-JSON log lines on stdout.
            continue

        if expected_id is not None and msg.get("id") != expected_id:
            continue

        return msg

    return None


def split_server_command(server_cmd):
    """Split a command string and extract leading KEY=VALUE environment assignments."""
    env = os.environ.copy()
    parts = shlex.split(server_cmd)
    cmd_parts = []

    for part in parts:
        if not cmd_parts and "=" in part and not part.startswith("="):
            key, value = part.split("=", 1)
            if key and all(ch.isalnum() or ch == "_" for ch in key):
                env[key] = value
                continue
        cmd_parts.append(part)

    if not cmd_parts:
        raise ValueError(f"Invalid server command: {server_cmd}")

    return cmd_parts, env


def read_stderr(proc):
    """Best-effort read of currently available stderr output."""
    chunks = []
    while True:
        ready, _, _ = select.select([proc.stderr], [], [], 0)
        if not ready:
            break
        data = proc.stderr.readline()
        if not data:
            break
        chunks.append(data.decode(errors="replace"))
    return "".join(chunks).strip()


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <server-command> <tool-name> [arguments-json]", file=sys.stderr)
        sys.exit(1)

    server_cmd = sys.argv[1]
    tool_name = sys.argv[2]

    if len(sys.argv) > 3:
        try:
            args_json = json.loads(sys.argv[3])
        except json.JSONDecodeError as exc:
            print(f"Error: arguments-json must be valid JSON ({exc})", file=sys.stderr)
            sys.exit(1)
    else:
        args_json = {}

    cmd_parts, env = split_server_command(server_cmd)
    proc = subprocess.Popen(
        cmd_parts,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
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
        init_resp = recv(proc, timeout=10, expected_id=0)
        if not init_resp:
            stderr_output = read_stderr(proc)
            if stderr_output:
                print(f"Error: No response to initialize\n{stderr_output}", file=sys.stderr)
            else:
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
        tool_timeout = float(os.environ.get("MCP_CALL_TIMEOUT", "30"))
        resp = recv(proc, timeout=tool_timeout, expected_id=1)
        if resp:
            print(json.dumps(resp.get("result", resp), indent=2))
        else:
            stderr_output = read_stderr(proc)
            if stderr_output:
                print(f"Error: No response to tool call\n{stderr_output}", file=sys.stderr)
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
