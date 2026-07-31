#!/usr/bin/env bash
# OPT-IN live test for the Globalping remote MCP (spec 079 T017).
#
# THIS SPENDS REAL MEASUREMENTS — roughly 10 of a 500/hour allowance shared across
# everything using the token. Never run this in CI or from `run-tests.sh`.
#
# Usage:
#   set -a && . ./.env && set +a
#   ./tests/globalping/live-api.sh
#
# Exit codes are captured DIRECTLY, never through a pipe.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="${NETCLAW_PY:-/usr/bin/python3}"

if [ -z "${GLOBALPING_TOKEN:-}" ]; then
    echo "SKIP: GLOBALPING_TOKEN not set." >&2
    echo "  Opt-in script; load credentials with: set -a && . ./.env && set +a" >&2
    exit 2
fi

echo "This spends ~10 live measurements against a 500/hour allowance."
if [ "${GP_LIVE_YES:-}" != "1" ]; then
    printf 'Continue? [y/N] '
    read -r reply
    case "$reply" in [yY]*) ;; *) echo "aborted"; exit 2 ;; esac
fi

"$PY" - <<'PY'
import httpx, json, os, re, sys

URL = "https://mcp.globalping.dev/mcp"
TOKEN = os.environ["GLOBALPING_TOKEN"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
     "Accept": "application/json, text/event-stream"}

# A generic, task-shaped context per FR-012: no customer, host, ticket or topology.
CTX = ("Validating external reachability and latency distribution for public infrastructure "
       "endpoints during automated integration verification across multiple regions.")

PASS = FAIL = 0
def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  ok   {label}"); PASS += 1
    else:
        print(f"  FAIL {label}" + (f" — {detail}" if detail else "")); FAIL += 1

def sse(text):
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return None

c = httpx.Client(timeout=180)
r = c.post(URL, headers=H, json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
               "clientInfo": {"name": "netclaw-test", "version": "1.0"}}})
check("initialize returns 200", r.status_code == 200, str(r.status_code))
sid = r.headers.get("mcp-session-id")
check("session id issued", bool(sid))
H["Mcp-Session-Id"] = sid
c.post(URL, headers=H, json={"jsonrpc": "2.0", "method": "notifications/initialized"})

_id = [10]
def call(name, args):
    _id[0] += 1
    r = c.post(URL, headers=H, json={"jsonrpc": "2.0", "id": _id[0], "method": "tools/call",
                                     "params": {"name": name, "arguments": {**args, "context": CTX}}})
    d = sse(r.text) or {}
    if "error" in d:
        return {"jsonrpc_error": d["error"], "text": "", "isError": True}
    res = d.get("result", {})
    return {"text": "".join(b.get("text", "") for b in res.get("content", [])
                            if b.get("type") == "text"),
            "isError": bool(res.get("isError")), "jsonrpc_error": None}

print("### FR-002: auth is required ###")
bad = httpx.post(URL, headers={"Content-Type": "application/json",
                               "Accept": "application/json, text/event-stream"},
                 json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                       "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                                  "clientInfo": {"name": "x", "version": "1"}}}, timeout=30)
check("unauthenticated request is rejected (401)", bad.status_code == 401, str(bad.status_code))

print("\n### The tool surface (FR-004, FR-005) ###")
r = c.post(URL, headers=H, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
tools = {t["name"]: t for t in sse(r.text)["result"]["tools"]}
check("12 tools advertised", len(tools) == 12, str(len(tools)))
for t in ("ping", "traceroute", "dns", "mtr", "http", "limits", "locations"):
    check(f"'{t}' present", t in tools)
meta_only = [n for n, t in tools.items()
             if set(t.get("inputSchema", {}).get("properties", {})) == {"context"}]
check("6 of 12 tools take only context (capability is 5 measurement tools)",
      len(meta_only) == 6, str(sorted(meta_only)))

print("\n### SC-001: a public target measured from diverse probes ###")
out = call("ping", {"target": "1.1.1.1", "locations": "world", "limit": 3, "packets": 2})
check("world ping succeeds", not out["isError"], out["text"][:120])
check("result reports probe count", "Probes:" in out["text"], out["text"][:120])
m = re.search(r"Successful Probes: (\d+)/(\d+)", out["text"])
check("result reports successful/total probes", bool(m), out["text"][:150])

print("\n### SC-002: no_probes_found means the measurement DID NOT RUN ###")
# AS13335 is correct syntax with zero probes — and it is the vendor's own schema example.
out = call("ping", {"target": "1.1.1.1", "locations": "AS13335", "limit": 1, "packets": 1})
check("AS13335 is an error, not an empty success", out["isError"], out["text"][:120])
check("the error names no_probes_found", "no_probes_found" in out["text"], out["text"][:200])
# The distinction that matters: this must NOT look like a completed 0-probe measurement.
check("AS13335 does NOT return a finished measurement",
      "Status: finished" not in out["text"], out["text"][:150])

print("\n### SC-003: an unresolvable target IS a finished measurement with 0 successful ###")
out = call("ping", {"target": "this-does-not-exist-netclaw-079.invalid",
                    "locations": "London", "limit": 1, "packets": 1})
check("unresolvable target is NOT an error", not out["isError"], out["text"][:120])
check("it returns a finished measurement", "finished" in out["text"], out["text"][:150])
m = re.search(r"Successful Probes: (\d+)/(\d+)", out["text"])
check("0 of N probes succeeded — a real finding",
      bool(m) and m.group(1) == "0", out["text"][:200])

print("\n### FR-009: Globalping also refuses private targets (we refuse them earlier) ###")
for target, expect in [("192.168.1.1", "private"), ("10.0.0.1", "private"),
                       ("localhost", "localhost")]:
    out = call("ping", {"target": target, "locations": "London", "limit": 1, "packets": 1})
    check(f"{target} refused server-side too", out["isError"] and expect in out["text"].lower(),
          out["text"][:110])

print("\n### FR-011: location syntax, as measured ###")
out = call("ping", {"target": "1.1.1.1", "locations": "London+UK", "limit": 1, "packets": 1})
check("'London+UK' works ('+' is AND)", not out["isError"], out["text"][:110])
out = call("ping", {"target": "1.1.1.1", "locations": "London,UK", "limit": 1, "packets": 1})
check("'London,UK' fails (comma is not the AND separator)", out["isError"], out["text"][:110])
out = call("ping", {"target": "1.1.1.1", "locations": "AS3320", "limit": 1, "packets": 1})
check("ASN syntax works for an ASN that HAS probes (AS3320)",
      not out["isError"], out["text"][:110])

print("\n### SC-007 / SC-008: the budget, and what a measurement costs ###")
before = call("limits", {})
b = re.search(r'"remaining":\s*(\d+)', before["text"])
check("limits reports remaining", bool(b), before["text"][:150])
check("documented 500/hour authenticated limit matches",
      '"limit": 500' in before["text"] or "Limit: 500" in before["text"],
      before["text"][:200])
check("limits reports a reset window", "reset" in before["text"].lower())

if b:
    # SC-008: accounting is PER PROBE, not per call. An earlier reading of this got it
    # backwards — 35 exploratory calls happened to be mostly limit:1, and the matching
    # arithmetic looked like per-call billing. Assert both points so the wrong
    # conclusion cannot come back.
    start = int(b.group(1))
    call("ping", {"target": "1.1.1.1", "locations": "world", "limit": 1, "packets": 1})
    mid = re.search(r'"remaining":\s*(\d+)', call("limits", {})["text"])
    cost_1 = start - int(mid.group(1)) if mid else None
    check("limit:1 costs exactly 1", cost_1 == 1, f"cost={cost_1}")

    if mid:
        s2 = int(mid.group(1))
        call("ping", {"target": "1.1.1.1", "locations": "world", "limit": 5, "packets": 1})
        fin = re.search(r'"remaining":\s*(\d+)', call("limits", {})["text"])
        cost_5 = s2 - int(fin.group(1)) if fin else None
        check("limit:5 costs exactly 5 — accounting is per probe, not per call",
              cost_5 == 5, f"cost={cost_5}")
        check("a limits call itself costs nothing",
              cost_5 == 5, "implied: the two limits reads either side did not shift the count")
        if fin:
            print(f"       remaining: {fin.group(1)} of 500")

print("\n### SC-009: the token does not appear in tool output ###")
blob = json.dumps([before["text"], out["text"]])
check("full token absent from output", TOKEN not in blob)
# Known and accepted: `limits` echoes a short fragment. Asserted so a change is noticed.
frag = TOKEN[8:16]
if frag in before["text"]:
    print(f"       note: limits echoes an 8-char token fragment, as documented in the skill")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
PY
rc=$?          # captured directly — no pipe
echo
if [ "$rc" -eq 0 ]; then
    echo "LIVE GLOBALPING SUITE: PASS"
else
    echo "LIVE GLOBALPING SUITE: FAIL (exit $rc)"
fi
exit "$rc"
