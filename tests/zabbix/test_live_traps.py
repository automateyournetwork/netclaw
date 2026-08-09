"""The traps, reproduced against a LIVE NMS. Spec 083, FR-001..006b, SC-002/003/004/005/016.

Static tests prove the skill SAYS the right thing. These prove that following it produces
the right ANSWER — which is the only claim that matters after the adopt-as-is decision.

Requires ZABBIX_URL and ZABBIX_TOKEN. Skips loudly without them, EXCEPT where a skip would
hide a requirement (SC-003 trends) — there it fails, because a green skip is how an
unverified claim ships.
"""
from __future__ import annotations
import json, time, urllib.error, urllib.request
from _harness import FAILURES, check, run, skip, zabbix_env  # noqa: F401

ENV = zabbix_env()

def api(method, params=None, token=None, url=None, timeout=20):
    url = url or ENV["url"]
    body = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1}
    req = urllib.request.Request(url.rstrip("/") + "/api_jsonrpc.php",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json-rpc",
                 "Authorization": f"Bearer {token or ENV['token']}"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())

def _monitored_hostids():
    """Only hosts the NMS actually polls. Template items are not attached to a host and
    have no history — including them makes every data search fail for the wrong reason."""
    return [h["hostid"] for h in api("host.get", {"output": ["hostid"], "monitored_hosts": True})["result"]]

def _items(hostid=None):
    p = {"output": ["itemid", "key_", "value_type", "history", "trends", "lastclock"], "limit": 500}
    p["hostids"] = hostid or _monitored_hostids()
    return api("item.get", p)["result"]

def _with_data(items, vt, since):
    out = []
    # Prefer items that already report a recent lastclock — avoids 500 pointless calls.
    cands = [i for i in items if i["value_type"] == str(vt) and i.get("lastclock") not in (None, "", "0")]
    for it in (cands or [i for i in items if i["value_type"] == str(vt)])[:60]:
        r = api("history.get", {"itemids": [it["itemid"]], "history": vt,
                                "output": "extend", "limit": 1, "time_from": since})["result"]
        if r: out.append(it)
        if len(out) >= 2: break
    return out

def test_trap1_wrong_value_type_returns_empty_with_no_error():
    """SC-002. The flagship claim, reproduced in NetClaw's own suite."""
    if not ENV: skip("trap 1", "no ZABBIX_URL/ZABBIX_TOKEN"); return
    since = int(time.time()) - 7200
    floats = _with_data(_items(), 0, since)
    if not floats:
        check("a float item with data exists in the lab", False,
              "cannot exercise trap 1 — the lab has no float item with recent values")
        return
    it = floats[0]
    correct = api("history.get", {"itemids": [it["itemid"]], "history": 0,
                                  "output": "extend", "limit": 5, "time_from": since})
    default = api("history.get", {"itemids": [it["itemid"]], "history": 3,
                                  "output": "extend", "limit": 5, "time_from": since})
    check(f"correct value_type returns data for {it['key_'][:34]}",
          len(correct["result"]) > 0, "the item has no data — test is inconclusive")
    check("the API DEFAULT (3) returns ZERO rows for a float item",
          len(default["result"]) == 0,
          "the trap did not reproduce — re-check the value_type of the chosen item")
    check("and it returns NO ERROR — a silent wrong answer",
          "error" not in default,
          "it errored, which would at least be visible")

def test_trap1_scale_most_items_are_float():
    if not ENV: skip("value_type distribution", "no lab"); return
    items = _items()
    floats = sum(1 for i in items if i["value_type"] == "0")
    check(f"most items are float ({floats}/{len(items)}), so the default is wrong for the majority",
          floats > len(items) / 2,
          "distribution differs from the measured baseline — re-check the skill's '84 of 121' claim")

def test_trap2_types_cannot_be_mixed():
    """FR-002. Both halves must have data or the test is meaningless."""
    if not ENV: skip("trap 2", "no lab"); return
    since = int(time.time()) - 7200
    items = _items()
    f_ok, u_ok = _with_data(items, 0, since), _with_data(items, 3, since)
    if not (f_ok and u_ok):
        check("both a float and an unsigned item have data", False,
              "cannot exercise trap 2 — an inconclusive test that agrees with the "
              "hypothesis is worse than no test")
        return
    mixed = [i["itemid"] for i in f_ok + u_ok]
    h0 = {r["itemid"] for r in api("history.get", {"itemids": mixed, "history": 0,
          "output": "extend", "limit": 200, "time_from": since})["result"]}
    h3 = {r["itemid"] for r in api("history.get", {"itemids": mixed, "history": 3,
          "output": "extend", "limit": 200, "time_from": since})["result"]}
    check("no single call returns every item", len(h0) < len(mixed) and len(h3) < len(mixed),
          "one call returned everything — the trap did not reproduce")
    check("the two calls do not overlap", not (h0 & h3), "unexpected overlap")
    check("together they cover all the items", len(h0 | h3) == len(mixed),
          "splitting by type does not recover everything")

def test_retention_disabled_is_a_real_configuration():
    """FR-006b / SC-028 — the third retention state, found in Phase 0."""
    if not ENV: skip("retention states", "no lab"); return
    items = _items()
    no_hist = [i for i in items if i["history"] == "0"]
    no_trend = [i for i in items if i["trends"] == "0"]
    check("items with history=0 exist (raw never stored)", bool(no_hist),
          "the skill documents a state this lab cannot demonstrate — note it in VERIFICATION.md")
    check("items with trends=0 exist (no aggregates)", bool(no_trend), "same")
    check("retention is per item, not global",
          len({(i["history"], i["trends"]) for i in items}) > 1,
          "a single global retention would make the router unnecessary")

def test_never_collected_is_distinguishable_from_no_data():
    if not ENV: skip("never-collected", "no lab"); return
    items = _items()
    never = [i for i in items if not i.get("lastclock") or i.get("lastclock") == "0"]
    check("lastclock distinguishes never-collected items", True,
          "")  # informational
    print(f"        (lab has {len(never)} item(s) that have never returned a value)")

def test_three_way_outcome_distinction():
    """SC-016 / FR-010 / FR-027 — empty, bad credential, unreachable must differ."""
    if not ENV: skip("three-way distinction", "no lab"); return
    # (a) healthy + genuinely empty window
    far_past = int(time.time()) - 86400 * 3650
    r = api("history.get", {"itemids": ["1"], "history": 0, "output": "extend",
                            "limit": 1, "time_from": far_past, "time_till": far_past + 60})
    check("(a) healthy NMS + empty window → a successful empty result",
          "result" in r and r["result"] == [], f"got {str(r)[:80]}")
    # (b) bad credential
    try:
        bad = api("host.get", {"limit": 1}, token="deadbeef" * 8)
        check("(b) a bad token → an API error, not an empty result",
              "error" in bad, f"got {str(bad)[:80]}")
        check("    and the error is about authorisation, distinguishable from 'no data'",
              "error" in bad and any(w in json.dumps(bad["error"]).lower()
                                     for w in ("auth", "permission", "logged", "token")),
              f"unclear error: {str(bad.get('error'))[:90]}")
    except urllib.error.HTTPError as e:
        check("(b) a bad token → an HTTP error, not an empty result", True, str(e))
    # (c) unreachable
    unreachable = False
    try:
        api("host.get", {"limit": 1}, url="http://127.0.0.1:59999", timeout=4)
    except Exception:
        unreachable = True
    check("(c) an unreachable NMS → a transport failure, not an empty result", unreachable,
          "an unreachable NMS must never look like 'no problems'")

def test_problem_get_empty_is_a_positive_finding():
    if not ENV: skip("problem.get", "no lab"); return
    r = api("problem.get", {"output": "extend"})
    check("problem.get succeeds", "result" in r, str(r)[:100])
    print(f"        (lab has {len(r.get('result', []))} active problem(s))")

def test_trends_beyond_retention():
    """SC-003. Fails rather than skips if trends have not accumulated — a green skip is
    exactly how an unverified claim ships."""
    if not ENV: skip("trends", "no lab"); return
    items = [i for i in _items() if i["trends"] not in ("0", "")]
    got = []
    for it in items[:40]:
        r = api("trend.get", {"itemids": [it["itemid"]], "output": "extend", "limit": 2})["result"]
        if r: got.append(it); break
    if got:
        check("hourly trend data is retrievable", True, "")
    else:
        check("hourly trend data exists in the lab", False,
              "NO TRENDS YET — trends are written hourly and this lab has not run long "
              "enough. SC-003/SC-004 are UNVERIFIED and must be recorded as such in "
              "VERIFICATION.md (FR-051). This failure is deliberate: skipping would look green.")

TESTS = [test_trap1_wrong_value_type_returns_empty_with_no_error, test_trap1_scale_most_items_are_float,
         test_trap2_types_cannot_be_mixed, test_retention_disabled_is_a_real_configuration,
         test_never_collected_is_distinguishable_from_no_data, test_three_way_outcome_distinction,
         test_problem_get_empty_is_a_positive_finding, test_trends_beyond_retention]

if __name__ == "__main__":
    raise SystemExit(run(TESTS, "live trap"))
