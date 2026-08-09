"""Manifest ceiling and surface stability. Spec 084, FR-037, SC-018.

The tool-count assertion is load-bearing: upstream's DEFAULT config is 21 tools / 5,716
tokens and busts the ceiling. An upstream bump or a config edit that re-enables a toolset
must fail here rather than silently consume the context budget.
"""
from __future__ import annotations
import asyncio, os, subprocess
from _harness import FAILURES, check, mcp_binary, repo, run, skip  # noqa: F401

CEILING = 5000
EXPECTED = {"events_list", "namespaces_list", "pods_get", "pods_list",
            "pods_list_in_namespace", "resources_get", "resources_list"}
BIN = mcp_binary()
CFG = repo("mcp-servers", "k8s-mcp", "config.toml")

PROBE = r'''
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def main():
    env = dict(os.environ)
    kc = os.environ.get("K8S_TEST_KUBECONFIG", "/dev/null")
    p = StdioServerParameters(command=sys.argv[1],
        args=["--config", sys.argv[2], "--kubeconfig", kc], env=env)
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            t = (await s.list_tools()).tools
            m = "\n".join(f"{x.name}\n{x.description or ''}\n{x.inputSchema}" for x in t)
            print(json.dumps({"names":[x.name for x in t],"chars":len(m),"lines":m.count("\n")}))
asyncio.run(main())
'''
_C = {}

def _d():
    if "d" in _C: return _C["d"]
    if not BIN or not os.path.exists(BIN): _C["d"] = None; return None
    out = subprocess.run(["python3", "-c", PROBE, BIN, CFG], capture_output=True, text=True, timeout=120)
    import json
    for line in reversed(out.stdout.strip().splitlines()):
        if line.startswith("{"): _C["d"] = json.loads(line); return _C["d"]
    _C["d"] = None; return None

def test_under_ceiling():
    d = _d()
    if not d: skip("manifest", "binary not installed"); return
    tokens = d["chars"] // 4 + d["lines"]
    print(f"        measured manifest: {tokens} / {CEILING} tokens ({d['chars']} chars)")
    check(f"manifest <= {CEILING} tokens", tokens <= CEILING, f"measured {tokens}")

def test_surface_is_exactly_seven():
    d = _d()
    if not d: skip("surface", "binary not installed"); return
    names = set(d["names"])
    check("exactly 7 tools", len(names) == 7, f"got {len(names)}: {sorted(names)}")
    check("the surface matches what was verified", names == EXPECTED,
          f"changed: extra={sorted(names-EXPECTED)} missing={sorted(EXPECTED-names)}")

def test_no_write_or_context_tool():
    d = _d()
    if not d: skip("write guard", "binary not installed"); return
    bad = [n for n in d["names"] if any(v in n.lower() for v in
           ("delete", "create", "update", "scale", "apply", "patch", "exec", "run", "helm", "switch"))]
    check("no write-shaped or context-switching tool is exposed", not bad, f"exposed: {bad}")

def test_checksum_recorded():
    import hashlib
    if not BIN or not os.path.exists(BIN): skip("checksum", "binary not installed"); return
    rec = [l.split()[0] for l in open(repo("mcp-servers","k8s-mcp","CHECKSUMS"))
           if l.strip() and not l.startswith("#")]
    actual = hashlib.sha256(open(BIN,"rb").read()).hexdigest()
    check("the installed binary matches the recorded SHA-256", actual in rec,
          f"MISMATCH: {actual} not in {rec} — the pinned artifact changed")

TESTS = [test_under_ceiling, test_surface_is_exactly_seven, test_no_write_or_context_tool,
         test_checksum_recorded]

if __name__ == "__main__":
    raise SystemExit(run(TESTS, "manifest and surface"))
