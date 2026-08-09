"""Against live Catalyst Center. Spec 087, SC-001..SC-008.

The centrepiece is test_two_appliances_differ. This feature exists because an empty
inventory reads identically to an empty network, and the DevNet sandboxes hand us a free,
real instance of that trap: two hosts, same credentials, one with 4 devices and one with
none. Verifying against only the populated one would prove nothing about the distinction.

Needs CATC_TEST_HOST (populated). CATC_TEST_EMPTY_HOST enables the centrepiece.
"""
from __future__ import annotations
import asyncio, json, os, sys
from _harness import FAILURES, check, repo, run, skip  # noqa: F401

SRV = repo("mcp-servers", "catc-mcp", "server.py")
U, P = os.environ.get("CATC_TEST_USER"), os.environ.get("CATC_TEST_PASS")

async def _call(host, tool, args):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    env = dict(os.environ)
    env.update({"CATALYST_CENTER_HOST": host, "CATALYST_CENTER_USERNAME": U or "",
                "CATALYST_CENTER_PASSWORD": P or "", "CATALYST_CENTER_VERIFY_SSL": "false"})
    p = StdioServerParameters(command=sys.executable, args=["-u", SRV], env=env)
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool(tool, args)
            return json.loads(res.content[0].text) if res.content else {}

def call(host, tool, args): return asyncio.run(_call(host, tool, args))

def _ready():
    if not (os.environ.get("CATC_TEST_HOST") and U and P):
        skip("live tests", "CATC_TEST_HOST / CATC_TEST_USER / CATC_TEST_PASS not set"); return False
    return True

def test_find_then_dispatch():
    """SC-001 — operation names are generated, so discovery must work before dispatch."""
    if not _ready(): return
    h = os.environ["CATC_TEST_HOST"]
    d = call(h, "catc_find", {"query": "sites", "limit": 5})
    check("catc_find returns operations", d["outcome"] == "ok" and d["data"], str(d)[:150])
    check("find does not contact the appliance (local catalogue)",
          any("does not contact" in c for c in d["caveats"]), str(d["caveats"])[:120])
    r = call(h, "catc_sites", {"operation": "api_getSites"})
    check("dispatch returns real site data", r["outcome"] == "ok" and r.get("data"), str(r)[:150])
    check("the response names the appliance", r["appliance"] == h, r.get("appliance"))
    check("the response carries an observed_at", bool(r.get("observed_at")), str(r)[:100])

def test_two_appliances_differ():
    """SC-002 — THE test. Same credentials, same call, two appliances, two answers."""
    if not _ready(): return
    empty = os.environ.get("CATC_TEST_EMPTY_HOST")
    if not empty:
        check("an empty appliance is available to prove the distinction", False,
              "CATC_TEST_EMPTY_HOST unset — the central claim of this feature is UNVERIFIED")
        return
    pop = os.environ["CATC_TEST_HOST"]
    a = call(pop,  "catc_devices", {"operation": "api_getDeviceConfigCount"})
    b = call(empty,"catc_devices", {"operation": "api_getDeviceConfigCount"})
    check("populated appliance reports records", a["outcome"] == "ok" and a["data"], str(a)[:120])
    check("empty appliance reports outcome=empty", b["outcome"] == "empty",
          f"got {b['outcome']} — a zero count was not flagged as an absence")
    check("the empty answer carries an explicit caveat",
          any("NOT that the network has none" in c for c in b["caveats"]),
          str(b["caveats"])[:160])
    check("the two answers name different appliances", a["appliance"] != b["appliance"])
    check("neither answer claims the network is empty",
          not any("network has none" in c and "NOT" not in c for c in a["caveats"]+b["caveats"]))

def test_unreachable_is_not_empty():
    """SC-003 — three distinguishable outcomes."""
    if not _ready(): return
    d = call("https://127.0.0.1:59999", "catc_sites", {"operation": "api_getSites"})
    check("an unreachable appliance is outcome=unreachable", d["outcome"] == "unreachable",
          f"got {d['outcome']}")
    check("and says so explicitly", "NOT AN EMPTY RESULT" in (d.get("message") or "").upper(),
          str(d.get("message"))[:140])
    b = call(os.environ["CATC_TEST_HOST"], "catc_sites", {"operation": "api_getSites"})
    check("unreachable differs from a real answer", d["outcome"] != b["outcome"])

def test_bad_credentials_are_not_empty():
    if not _ready(): return
    import copy
    old = os.environ.get("CATC_TEST_PASS")
    globals()["P"] = "definitely-not-the-password"
    try:
        d = call(os.environ["CATC_TEST_HOST"], "catc_sites", {"operation": "api_getSites"})
        check("bad credentials give auth_failed, not empty", d["outcome"] == "auth_failed",
              f"got {d['outcome']}")
        check("and state that the controller's state is unknown",
              "unknown" in (d.get("message") or "").lower(), str(d.get("message"))[:130])
    finally:
        globals()["P"] = old

def test_unknown_operation_is_refused_helpfully():
    """SC-012 — a refusal must name what IS available."""
    if not _ready(): return
    d = call(os.environ["CATC_TEST_HOST"], "catc_devices", {"operation": "getDeviceList"})
    check("an unknown operation is refused", d["outcome"] == "refused", f"got {d['outcome']}")
    check("the refusal points at catc_find", "catc_find" in (d.get("message") or ""),
          str(d.get("message"))[:140])

def test_describe_gives_a_schema():
    if not _ready(): return
    d = call(os.environ["CATC_TEST_HOST"], "catc_describe_operation", {"operation": "api_getSites"})
    check("describe returns a schema", d["outcome"] == "ok" and d["data"].get("uri"), str(d)[:130])
    check("it names the HTTP method", d["data"].get("method") == "GET", str(d["data"])[:100])

TESTS = [test_find_then_dispatch, test_two_appliances_differ, test_unreachable_is_not_empty,
         test_bad_credentials_are_not_empty, test_unknown_operation_is_refused_helpfully,
         test_describe_gives_a_schema]

if __name__ == "__main__":
    raise SystemExit(run(TESTS, "live Catalyst Center"))
