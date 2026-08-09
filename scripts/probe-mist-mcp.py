#!/usr/bin/env python3
"""Re-run spec 095's ceiling check against Juniper's remote Mist MCP server.

Reads MIST_API_TOKEN, MIST_API_HOST and MIST_ORG_ID from the environment
(`set -a; source ~/.openclaw/.env; set +a`).

    python3 scripts/probe-mist-mcp.py            # initialize + tools/list, chars/4 sizing
    python3 scripts/probe-mist-mcp.py --count    # exact token count (needs ANTHROPIC_API_KEY)

Spec 095 measured 11,783 tokens against a 5,000 ceiling. A materially different
number means Juniper changed the manifest and the adoption decision is stale.
"""
import json
import os
import sys
import urllib.error
import urllib.request

ENDPOINT = os.environ.get("MIST_MCP_URL", "https://mcp.ai.juniper.net/mcp/mist")
CEILING = 5000
SPEC_095_TOTAL = 11783
COUNT_MODEL = "claude-opus-4-5-20251101"

_session_id = None


def rpc(method, params=None, notify=False):
    """One JSON-RPC call over MCP streamable HTTP. Returns the decoded message."""
    global _session_id
    body = {"jsonrpc": "2.0", "method": method}
    if not notify:
        body["id"] = 1
    if params is not None:
        body["params"] = params

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        # The MCP server accepts Bearer only — the REST API's `Token` scheme is refused.
        "Authorization": f"Bearer {os.environ['MIST_API_TOKEN']}",
        # Without this the server defaults to api.mist.com and a regional token 401s.
        "X-Mist-Base-URL": f"https://{os.environ.get('MIST_API_HOST', 'api.mist.com')}",
    }
    if os.environ.get("MIST_ORG_ID"):
        headers["X-Mist-Org-ID"] = os.environ["MIST_ORG_ID"]
    if _session_id:
        headers["Mcp-Session-Id"] = _session_id

    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(body).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            sid = r.headers.get("Mcp-Session-Id")
            if sid:
                _session_id = sid
            raw = r.read().decode("utf-8", "replace")
            ctype = r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raw, ctype = e.read().decode("utf-8", "replace"), ""

    if "event-stream" in ctype:
        for line in raw.splitlines():
            if line.startswith("data:"):
                try:
                    return json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
        return {"raw": raw[:400]}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw[:400]}


def count_tokens(tools, instructions):
    """Exact count via the Anthropic count_tokens endpoint, as a delta over baseline."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ANTHROPIC_API_KEY not set — cannot count exactly", file=sys.stderr)
        return None

    def _count(payload):
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages/count_tokens",
            data=json.dumps(payload).encode(),
            headers={
                "content-type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)["input_tokens"]

    msg = [{"role": "user", "content": "hi"}]
    baseline = _count({"model": COUNT_MODEL, "messages": msg})
    as_tools = [
        {
            "name": t["name"],
            "description": t.get("description", ""),
            "input_schema": t.get("inputSchema", {"type": "object"}),
        }
        for t in tools
    ]

    print("\nper-tool cost:")
    for t in as_tools:
        c = _count({"model": COUNT_MODEL, "messages": msg, "tools": [t]}) - baseline
        print(f"  {t['name']:<22} {c:>6}")

    manifest = _count({"model": COUNT_MODEL, "messages": msg, "tools": as_tools}) - baseline
    instr = 0
    if instructions:
        instr = _count({"model": COUNT_MODEL, "messages": [{"role": "user", "content": instructions}]}) - baseline
    return manifest, instr


def main():
    if not os.environ.get("MIST_API_TOKEN"):
        print("MIST_API_TOKEN not set. source ~/.openclaw/.env first.", file=sys.stderr)
        return 2

    init = rpc(
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "netclaw-probe", "version": "0.1"},
        },
    )
    if "result" not in init:
        print("initialize failed:", json.dumps(init)[:400], file=sys.stderr)
        return 1

    res = init["result"]
    instructions = res.get("instructions") or ""
    print(f"server      : {json.dumps(res.get('serverInfo', {}))}")
    print(f"protocol    : {res.get('protocolVersion')}")
    print(f"instructions: {len(instructions)} chars")

    rpc("notifications/initialized", notify=True)

    listed = rpc("tools/list")
    if "result" not in listed:
        print("tools/list failed:", json.dumps(listed)[:400], file=sys.stderr)
        return 1
    tools = listed["result"].get("tools", [])
    print(f"tools       : {len(tools)}")

    chars = len(json.dumps(tools)) + len(instructions)
    print(f"\nchars/4 estimate : ~{chars // 4} tokens")
    print("  (spec 095: this convention under-reported by 17% here — estimate only)")

    total = None
    if "--count" in sys.argv:
        counted = count_tokens(tools, instructions)
        if counted:
            manifest, instr = counted
            total = manifest + instr
            print(f"\nmanifest     : {manifest}")
            print(f"instructions : {instr}")
            print(f"TOTAL        : {total}  (ceiling {CEILING})")

    verdict = total if total is not None else chars // 4
    print(f"\nvs ceiling   : {verdict / CEILING:.2f}x")
    if total is not None and abs(total - SPEC_095_TOTAL) > 500:
        print(
            f"CHANGED: spec 095 measured {SPEC_095_TOTAL}; now {total}. "
            "Re-check the adoption decision."
        )
    return 0 if verdict <= CEILING else 1


if __name__ == "__main__":
    sys.exit(main())
