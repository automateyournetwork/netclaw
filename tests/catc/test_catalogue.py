"""The catalogue and the manifest. Spec 087, FR-001..FR-006, SC-009..SC-013.

The whole feature is a size problem: inlining Cisco's 515 generated tools measures 64,420
tokens against a 5,000 ceiling. These assertions are what stop that regressing — a
careless catalogue addition or an upstream regeneration must fail here, loudly, rather
than quietly consuming the context budget.
"""
from __future__ import annotations
import glob, json, os
from _harness import FAILURES, check, repo, run  # noqa: F401

CAT = repo("mcp-servers", "catc-mcp", "catalog")
GROUPS = ["devices","sites","wireless","health","compliance","software","events","other"]
CEILING = 5000

def _ops():
    out = {}
    for g in GROUPS:
        out[g] = json.load(open(os.path.join(CAT, f"{g}.json"), encoding="utf-8"))
    return out

def test_all_eight_groups_exist():
    o = _ops()
    for g in GROUPS:
        check(f"group '{g}' exists and is non-empty", bool(o[g]), "missing or empty")

def test_every_operation_is_readonly():
    """FR-004 / SC-010 — the single upstream POST must be absent."""
    o = _ops()
    bad = [(g, x["name"], x["method"]) for g in GROUPS for x in o[g] if x["method"] != "GET"]
    check("every catalogued operation is GET", not bad, f"non-GET present: {bad}")
    names = {x["name"] for g in GROUPS for x in o[g]}
    check("the upstream mutating operation is excluded",
          "api_complianceRemediation" not in names,
          "complianceRemediation is present — this catalogue is no longer read-only")

def test_operation_count_is_pinned():
    """SC-011 — growth must fail here, not surface as a bigger manifest later."""
    o = _ops()
    total = sum(len(o[g]) for g in GROUPS)
    print(f"        catalogued operations: {total}")
    check("catalogue holds 514 read-only operations", total == 514,
          f"got {total}; upstream bundle was 515 with 1 POST excluded. If upstream "
          f"regenerated, re-derive the catalogue and update this number deliberately")

def test_every_operation_is_dispatchable():
    """A definition without uri or method cannot be called — it would fail at runtime."""
    o = _ops()
    for g in GROUPS:
        bad = [x.get("name") for x in o[g] if not x.get("uri") or not x.get("method")]
        check(f"{g}: every operation has uri and method", not bad, f"undispatchable: {bad[:4]}")

def test_no_duplicate_operations_across_groups():
    o = _ops()
    seen, dupes = set(), []
    for g in GROUPS:
        for x in o[g]:
            if x["name"] in seen: dupes.append(x["name"])
            seen.add(x["name"])
    check("no operation appears in two groups", not dupes,
          f"duplicated: {dupes[:5]} — a dispatcher would shadow the other")

def test_manifest_under_ceiling():
    """SC-009 — measured via a real handshake, not estimated from source."""
    import asyncio, subprocess, sys
    probe = r'''
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def main():
    env=dict(os.environ); env.setdefault("CATALYST_CENTER_HOST","")
    p=StdioServerParameters(command=sys.executable,args=["-u",sys.argv[1]],env=env)
    async with stdio_client(p) as (r,w):
        async with ClientSession(r,w) as s:
            await s.initialize()
            t=(await s.list_tools()).tools
            m="\n".join(f"{x.name}\n{x.description or ''}\n{x.inputSchema}" for x in t)
            print(json.dumps({"n":len(t),"names":[x.name for x in t],
                              "chars":len(m),"lines":m.count("\n")}))
asyncio.run(main())
'''
    out = subprocess.run([sys.executable, "-c", probe,
                          repo("mcp-servers","catc-mcp","server.py")],
                         capture_output=True, text=True, timeout=120)
    line = next((l for l in reversed(out.stdout.strip().splitlines()) if l.startswith("{")), None)
    if not line:
        check("manifest could be measured", False, out.stderr[-200:]); return
    d = json.loads(line)
    tokens = d["chars"]//4 + d["lines"]
    print(f"        manifest: {tokens} / {CEILING} tokens ({d['chars']} chars), {d['n']} tools")
    check(f"manifest <= {CEILING} tokens", tokens <= CEILING, f"measured {tokens}")
    check("exactly 10 tools exposed", d["n"] == 10, f"got {d['n']}: {d['names']}")
    check("8 group dispatchers plus find and describe",
          set(d["names"]) == {f"catc_{g}" for g in GROUPS} | {"catc_find","catc_describe_operation"},
          f"surface changed: {sorted(d['names'])}")
    check("no write-shaped tool name", not [n for n in d["names"] if any(
          v in n for v in ("create","update","delete","set_","apply","remediat"))], str(d["names"]))

TESTS = [test_all_eight_groups_exist, test_every_operation_is_readonly,
         test_operation_count_is_pinned, test_every_operation_is_dispatchable,
         test_no_duplicate_operations_across_groups, test_manifest_under_ceiling]

if __name__ == "__main__":
    raise SystemExit(run(TESTS, "catalogue and manifest"))
