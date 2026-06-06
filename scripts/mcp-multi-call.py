#!/usr/bin/env python3
"""Run multiple MCP tool calls in one server session (for BGP flap demos)."""
import json
import os
import select
import shlex
import subprocess
import sys
import time


def send(proc, msg):
    proc.stdin.write((json.dumps(msg) + "\n").encode())
    proc.stdin.flush()


def recv(proc, timeout=30, expected_id=None):
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
            continue
        if expected_id is not None and msg.get("id") != expected_id:
            continue
        return msg
    return None


def call_tool(proc, req_id, name, arguments=None):
    send(proc, {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    })
    return recv(proc, timeout=60, expected_id=req_id)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} '<server-command>' tool1 [json1] tool2 [json2] ...", file=sys.stderr)
        sys.exit(1)

    parts = shlex.split(sys.argv[1])
    env = os.environ.copy()
    cmd = []
    for part in parts:
        if not cmd and "=" in part:
            k, v = part.split("=", 1)
            if k and all(c.isalnum() or c == "_" for c in k):
                env[k] = v
                continue
        cmd.append(part)

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    send(proc, {
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "netclaw", "version": "1.0"}},
    })
    if not recv(proc, expected_id=0):
        print("initialize failed", file=sys.stderr)
        sys.exit(1)
    send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
    time.sleep(0.5)

    req_id = 1
    i = 2
    while i < len(sys.argv):
        tool = sys.argv[i]
        args = {}
        if i + 1 < len(sys.argv) and sys.argv[i + 1].startswith("{"):
            args = json.loads(sys.argv[i + 1])
            i += 2
        else:
            i += 1
        resp = call_tool(proc, req_id, tool, args)
        print(f"\n=== {tool} ===")
        print(json.dumps(resp.get("result", resp) if resp else {"error": "timeout"}, indent=2))
        req_id += 1
        time.sleep(0.2)

    proc.terminate()


if __name__ == "__main__":
    main()