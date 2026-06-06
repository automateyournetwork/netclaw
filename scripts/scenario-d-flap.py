#!/usr/bin/env python3
"""Scenario D: 5x inject/withdraw via single Protocol MCP session."""
import json
import os
import select
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = [
    "/home/ubuntu/netclaw/.venv/bin/python3", "-u",
    os.path.join(ROOT, "mcp-servers/protocol-mcp/server.py"),
]
ENV = {
    **os.environ,
    "NETCLAW_ROUTER_ID": "10.255.255.1",
    "NETCLAW_LOCAL_AS": "65099",
    "NETCLAW_BGP_PEERS": '[{"ip":"10.255.255.2","as":65000}]',
    "PROTOCOL_METRICS_ENABLED": "true",
    "BGP_LISTEN_PORT": "1179",
}
PREFIX = os.environ.get("FLAP_PREFIX", "192.168.99.0/24")
CYCLES = int(os.environ.get("FLAP_CYCLES", "5"))
WAIT = int(os.environ.get("FLAP_WAIT_SEC", "8"))


def send(proc, msg):
    proc.stdin.write((json.dumps(msg) + "\n").encode())
    proc.stdin.flush()


def recv(proc, timeout=60, expected_id=None):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not select.select([proc.stdout], [], [], max(0, deadline - time.monotonic()))[0]:
            break
        line = proc.stdout.readline().decode(errors="replace").strip()
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


def call(proc, rid, name, args=None):
    send(proc, {"jsonrpc": "2.0", "id": rid, "method": "tools/call", "params": {"name": name, "arguments": args or {}}})
    return recv(proc, expected_id=rid)


def text_result(resp):
    if not resp:
        return "(no response)"
    result = resp.get("result", resp)
    content = result.get("content", [])
    if content and isinstance(content, list):
        return content[0].get("text", json.dumps(result, indent=2))
    return json.dumps(result, indent=2)


def main():
    proc = subprocess.Popen(SERVER, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV)
    send(proc, {
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "scenario-d", "version": "1.0"}},
    })
    if not recv(proc, expected_id=0):
        print("MCP initialize failed", file=sys.stderr)
        sys.exit(1)
    send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
    time.sleep(1)

    rid = 1
    print("=== BGP Route Stability Watch — Scenario D ===\n")
    print(f"Prefix: {PREFIX}  Cycles: {CYCLES}  Wait: {WAIT}s\n")

    print("--- Step 1: Wait for BGP + baseline ---")
    for attempt in range(20):
        r = call(proc, rid, "bgp_get_peers")
        rid += 1
        body = text_result(r)
        if "Established" in body or "established" in body:
            print(body[:800])
            break
        print(f"  attempt {attempt + 1}: waiting for Established...")
        time.sleep(3)
    else:
        print(text_result(r))

    r = call(proc, rid, "protocol_summary")
    rid += 1
    print("\nprotocol_summary:\n", text_result(r)[:600])

    print("\n--- Step 2: Injection loop ---")
    for i in range(1, CYCLES + 1):
        print(f"\nCycle {i}/{CYCLES}: inject → wait {WAIT}s → withdraw")
        r = call(proc, rid, "bgp_inject_route", {"network": PREFIX})
        rid += 1
        print("  inject:", text_result(r)[:200])
        time.sleep(WAIT)
        r = call(proc, rid, "bgp_withdraw_route", {"network": PREFIX})
        rid += 1
        print("  withdraw:", text_result(r)[:200])
        time.sleep(WAIT)

    print("\n--- Step 3: Post-flap state ---")
    r = call(proc, rid, "protocol_summary")
    rid += 1
    print("protocol_summary:\n", text_result(r))
    r = call(proc, rid, "bgp_get_rib", {"prefix": PREFIX})
    rid += 1
    print("\nbgp_get_rib:\n", text_result(r)[:500])

    proc.terminate()
    print("\n--- Step 4: Metrics (:9179) ---")
    os.system("curl -sf http://localhost:9179/metrics | grep -E 'bgp_route_|bgp_rib|bgp_peer' || true")


if __name__ == "__main__":
    main()