#!/usr/bin/env python3
"""Minimal stdio MCP server used only as an eN2N invocation target in the
two-Border evidence run. Stdlib only. No tool touches the filesystem or network.
  echo_info      read-only: returns host label + UTC time + the arguments it got
  approval_info  read-only: same output; granted with requires_approval
  touch_marker   annotated as a write tool; it performs no write (returns a string)
"""
import json, sys, time, socket

TOOLS = [
    {"name": "echo_info", "description": "Return host label, UTC time and the given arguments.",
     "inputSchema": {"type": "object", "properties": {"note": {"type": "string"}}},
     "annotations": {"readOnlyHint": True}},
    {"name": "approval_info", "description": "Same as echo_info; used for the approval path.",
     "inputSchema": {"type": "object", "properties": {"note": {"type": "string"}}},
     "annotations": {"readOnlyHint": True}},
    {"name": "touch_marker", "description": "Classified as a write tool for access-class tests (performs no write).",
     "inputSchema": {"type": "object", "properties": {}},
     "annotations": {"readOnlyHint": False}},
]

def reply(i, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": i}
    msg.update({"error": error} if error else {"result": result})
    sys.stdout.write(json.dumps(msg) + "\n"); sys.stdout.flush()

for line in sys.stdin:
    try:
        req = json.loads(line)
    except Exception:
        continue
    m, i = req.get("method"), req.get("id")
    if i is None:
        continue
    if m == "initialize":
        reply(i, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                  "serverInfo": {"name": "ncfed-probe", "version": "1.0"}})
    elif m == "tools/list":
        reply(i, {"tools": TOOLS})
    elif m == "tools/call":
        name = (req.get("params") or {}).get("name")
        args = (req.get("params") or {}).get("arguments") or {}
        if name in ("echo_info", "approval_info", "touch_marker"):
            body = {"tool": name, "host": socket.gethostname(),
                    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "arguments": args}
            reply(i, {"content": [{"type": "text", "text": json.dumps(body)}], "isError": False})
        else:
            reply(i, error={"code": -32602, "message": "unknown tool"})
    else:
        reply(i, error={"code": -32601, "message": "method not found"})
