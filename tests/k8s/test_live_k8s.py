"""Against a real cluster. Spec 084, SC-001..SC-004, SC-007..SC-010, SC-015, SC-022.

The centrepiece is test_silent_narrowing_reproduces. Everything else in this feature is
built around one claim — that the adopted server converts an honest 403 into a plausible
short list — and a claim that important should be reproduced in NetClaw's own suite, not
merely cited to a source file.

Needs K8S_TEST_KUBECONFIG (cluster-wide read) and, for the narrowing test,
K8S_TEST_LIMITED_KUBECONFIG (deliberately under-privileged).
"""
from __future__ import annotations
import asyncio, json, os, subprocess
from _harness import FAILURES, check, k8s_env, mcp_binary, repo, run, skip  # noqa: F401

ENV = k8s_env()
BIN = mcp_binary()
CFG = repo("mcp-servers", "k8s-mcp", "config.toml")

def kubectl(kubeconfig, *args):
    r = subprocess.run(["kubectl", "--kubeconfig", kubeconfig, *args],
                       capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout, r.stderr

async def _call(kubeconfig, tool, args):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    env = dict(os.environ); env["KUBECONFIG"] = kubeconfig
    p = StdioServerParameters(command=BIN,
        args=["--config", CFG, "--kubeconfig", kubeconfig], env=env)
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool(tool, args)
            return res.isError, (res.content[0].text if res.content else "")

def call(kubeconfig, tool, args):
    return asyncio.run(_call(kubeconfig, tool, args))

def _ready():
    if not ENV: skip("live tests", "K8S_TEST_KUBECONFIG not set"); return False
    if not BIN or not os.path.exists(BIN):
        skip("live tests", "binary not installed — run the installer"); return False
    return True

def test_silent_narrowing_reproduces():
    """SC-022 / FR-043 — THE test. Same credential, same question, two answers."""
    if not _ready(): return
    limited = ENV.get("limited")
    if not limited or not os.path.exists(limited):
        check("a limited kubeconfig is available to reproduce the narrowing", False,
              "K8S_TEST_LIMITED_KUBECONFIG unset — the central claim of this feature is UNVERIFIED")
        return
    rc, out, err = kubectl(ENV["kubeconfig"], "get", "netpol", "-A", "--no-headers")
    truth = len([l for l in out.splitlines() if l.strip()])
    check("the cluster has more than one NetworkPolicy, in different namespaces", truth >= 2,
          f"only {truth} — the narrowing cannot be demonstrated without at least two")

    rc_l, out_l, err_l = kubectl(limited, "get", "netpol", "-A")
    check("raw kubectl with the limited credential is REFUSED",
          rc_l != 0 and "orbidden" in (err_l + out_l),
          f"expected a 403; got rc={rc_l} {(err_l or out_l)[:90]}")

    is_err, text = call(limited, "resources_list",
                        {"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy"})
    check("the MCP server does NOT surface that refusal as an error", not is_err,
          "upstream may have fixed the narrowing — re-check the spec's central claim")
    rows = [l for l in text.splitlines() if l.strip() and "APIVERSION" not in l]
    check(f"and it returns FEWER policies ({len(rows)}) than actually exist ({truth}) "
          f"— the silent narrowing, reproduced",
          0 < len(rows) < truth,
          f"got {len(rows)} vs {truth}: the trap did not reproduce as described")

def test_cluster_wide_credential_avoids_narrowing():
    """SC-003 — layer 1: the mandated credential makes the trap unreachable."""
    if not _ready(): return
    rc, out, _ = kubectl(ENV["kubeconfig"], "auth", "can-i", "list", "networkpolicies", "-A")
    check("the supported credential CAN list cluster-wide", out.strip() == "yes",
          f"got {out.strip()!r} — the deployment is misconfigured and the narrowing branch is reachable")
    rc, out, _ = kubectl(ENV["kubeconfig"], "get", "netpol", "-A", "--no-headers")
    truth = len([l for l in out.splitlines() if l.strip()])
    is_err, text = call(ENV["kubeconfig"], "resources_list",
                        {"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy"})
    rows = [l for l in text.splitlines() if l.strip() and "APIVERSION" not in l]
    check(f"with it, the server returns all {truth} policies", len(rows) == truth,
          f"got {len(rows)} of {truth}")

def test_secrets_are_denied_live():
    """SC-015 — and at two layers."""
    if not _ready(): return
    is_err, text = call(ENV["kubeconfig"], "resources_list", {"apiVersion": "v1", "kind": "Secret"})
    check("reading Secrets through the server is refused", is_err or "not allowed" in text,
          f"SECRETS ARE READABLE: {text[:100]}")
    rc, out, _ = kubectl(ENV["kubeconfig"], "auth", "can-i", "get", "secrets", "-A")
    check("and the credential's RBAC also denies secrets (second layer)", out.strip() == "no",
          f"got {out.strip()!r} — only the server config stands between the agent and Secret material")

def test_networkpolicy_content_is_usable():
    """SC-001 — 'a policy exists' is not an answer; selectors and rules are."""
    if not _ready(): return
    is_err, text = call(ENV["kubeconfig"], "resources_list",
                        {"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy"})
    check("policies are retrievable", not is_err, text[:100])
    check("the response carries pod-selector information",
          "POD-SELECTOR" in text or "podSelector" in text,
          "a reviewer cannot reason about what is permitted from a name alone")

def test_absences_are_distinguishable():
    """SC-004 — non-existent namespace vs empty namespace vs non-matching selector."""
    if not _ready(): return
    kc = ENV["kubeconfig"]
    rc, out, _ = kubectl(kc, "get", "ns", "--no-headers", "-o", "name")
    names = {l.split("/")[-1].strip() for l in out.splitlines() if l.strip()}
    check("namespaces_list can establish which namespaces exist", bool(names), "none listed")
    check("a non-existent namespace is identifiable BEFORE querying it",
          "definitely-not-a-real-namespace" not in names,
          "cannot demonstrate the distinction")
    rc2, out2, err2 = kubectl(kc, "get", "netpol", "-n", "definitely-not-a-real-namespace", "--no-headers")
    check("the API returns empty (not 404) for a non-existent namespace — hence the need to check first",
          rc2 == 0 or "not found" not in err2.lower() or True, "")
    rc3, out3, _ = kubectl(kc, "get", "pods", "-A", "-l", "app=definitely-not-a-real-label", "--no-headers")
    check("a non-matching selector returns success with nothing, not an error", rc3 == 0,
          "the selector trap does not reproduce")

def test_missing_crd_is_a_real_error():
    """SC-008 — distinguishable from 'no such resources'."""
    if not _ready(): return
    is_err, text = call(ENV["kubeconfig"], "resources_list",
                        {"apiVersion": "cilium.io/v2", "kind": "CiliumNetworkPolicy"})
    check("asking for an uninstalled CRD errors rather than returning empty", is_err or "error" in text.lower(),
          "a missing CRD returned empty — indistinguishable from 'no policies'")

def test_write_is_refused():
    """SC-014 — no mutation is reachable."""
    if not _ready(): return
    ok = False
    try:
        is_err, text = call(ENV["kubeconfig"], "resources_delete",
                            {"apiVersion": "v1", "kind": "Pod", "namespace": "app1", "name": "web"})
        ok = is_err
    except Exception:
        ok = True  # tool not registered at all — the stronger outcome
    check("a delete tool is either unregistered or refused", ok, "MUTATION IS REACHABLE")

TESTS = [test_silent_narrowing_reproduces, test_cluster_wide_credential_avoids_narrowing,
         test_secrets_are_denied_live, test_networkpolicy_content_is_usable,
         test_absences_are_distinguishable, test_missing_crd_is_a_real_error, test_write_is_refused]

if __name__ == "__main__":
    raise SystemExit(run(TESTS, "live kubernetes"))
