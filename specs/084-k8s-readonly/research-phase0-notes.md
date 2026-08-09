# Phase 0 field notes — captured before the spec (spec 084 / R14)

**Date**: 2026-08-03. Written first and deliberately, so measured findings survive independently of
any later narrative. Everything here is either **measured on this machine** or a **code citation**.

## Lab

`kind` cluster `netclaw-r14`, **Kubernetes v1.35.0**, 2 nodes (control-plane + worker).
NetworkPolicy, Ingress and EndpointSlice all present as API resources.

> Environment note: Docker died mid-session and came back under Docker Desktop's WSL integration at
> `/run/docker.sock` (server 29.7.1). The first kind cluster was lost with it; this is the rebuild.
> Unrelated `clab-mandible-*` containers are running in this checkout — **another agent may be active
> here**, so branch state should be re-checked before any commit.

## Candidate landscape — MEASURED, not read off READMEs

The research agent built and ran each server, issued a real `tools/list`, and tokenised the manifest.

| Configuration | Tools | Tokens | vs 5,000 ceiling |
|---|---|---|---|
| **`containers/kubernetes-mcp-server`** `read_only + core + disabled_tools` | **7** | **2,301** | **PASS (54% under)** |
| `containers-k8s` `--read-only`, default toolsets | 15 | 4,049 | PASS |
| `containers-k8s` default | 21 | 5,716 | **FAIL** |
| `containers-k8s` all 8 toolsets | 51 | 18,236 | FAIL |
| `Flux159/mcp-server-kubernetes` read-only | 8 | 1,686 | PASS |
| `Flux159` default | 23 | 6,312 | **FAIL** |
| `rohitg00/kubectl-mcp-server` | **313** | — | FAIL by ~6× |
| `patrickdappollonio/mcp-kubernetes-ro` | 10 | 2,140 | PASS |

**Both main candidates bust the ceiling in their default configuration.** Read-only mode is not merely a
security preference here — it is what makes adoption possible at all.

## The recommendation, and why

**`containers/kubernetes-mcp-server`** — this *is* Red Hat's server (originally `manusa/`, donated to the
`containers` org; `openshift/openshift-mcp-server` is the downstream product build).

- **Apache-2.0** — licence-identical to NetClaw. Unlike R11's GPL-3.0, no vendoring-posture question at all.
- **Go static binary.** Zero Python/Node runtime dependencies, so it **cannot** collide with the
  `fastmcp<3` pins that blocked R11. Dependency conflict is structurally impossible.
- 1,876★, commits landing the same day as this research.
- **Read-only enforced at registration time** (`isToolApplicable`, `pkg/mcp/mcp.go:69`) — filtered tools are
  never registered with the SDK and cannot be invoked.
- Generic `resources_list`/`resources_get` take arbitrary `apiVersion`+`kind`, so NetworkPolicy, Service,
  Ingress and EndpointSlice are all covered by two read-only tools. CRDs (Cilium/Calico) too.

**`rohitg00` is disqualified twice over**: 313 tools, and it pins `fastmcp>=3.0.0b1` — R11's blocker,
reproduced exactly.

**`Flux159` is the fallback, with a caution.** Five published advisories, the most relevant being
**GHSA-cr22-wjx7-2w6m (High)**: *"Tool Access Control Bypass: Presentation-Layer Filtering Without
Execution-Layer Enforcement"* — tools hidden from `tools/list` were **still callable**. That is precisely
the mechanism we would be depending on to fit the ceiling. Fixed now, but the pattern is the caution.
Also: its `kubectl_context` tool supports `operation: "set"`, so **the model can switch clusters mid-session**
— and it counts as read-only, because switching context is not a cluster write.

**There is no official Kubernetes or CNCF MCP server.** `org:kubernetes mcp` → 0 repos; `org:cncf mcp` → 0.
`kubernetes-sigs/mcp-lifecycle-operator` is the *inverse* — an operator for deploying MCP servers onto
Kubernetes.

## The distinction this feature must protect

**An empty list from the Kubernetes API is not evidence of absence.** Measured on the live cluster:

| Trap | Measured result |
|---|---|
| List in a **non-existent namespace** | **0 items, HTTP 200** — not a 404 |
| **Typo'd label selector** (`app=wbe` vs `app=web`) | **0 pods, HTTP 200** — indistinguishable from "none match" |
| **Omitting `-A`** | **0 policies** in `default`, vs **1** cluster-wide |

For NetworkPolicy review this is a **security false negative**: reporting *"no policy restricts this pod"*
when the truth is *"I could not see them"* is the difference between an audit pass and an audit lie.

### And the sharper finding: the API tells the truth; the server hides it

I initially mis-tested this. My first attempt appeared to show a restricted account listing cluster-wide
successfully — but `auth whoami` returned **`kubernetes-admin` via X509**: the kubeconfig's client
certificate had silently overridden `--token`. Re-run with a token-only kubeconfig and a genuine identity:

```
identity: system:serviceaccount:app1:limited
can-i list netpol -A        → no
get netpol -A               → Error from server (Forbidden): ... cannot list ... at the cluster scope
```

**The Kubernetes API correctly returns 403.** It does *not* silently narrow.

The silent narrowing is therefore **entirely the adopted server's behaviour**
(`pkg/kubernetes/resources.go:34-38`):

```go
isNamespaced, _ := c.isNamespaced(gvk)
if isNamespaced && !c.canIUse(ctx, gvr, namespace, "list") && namespace == "" {
    namespace = c.NamespaceOrDefault("")
}
```

It runs a SelfSubjectAccessReview, and on denial **rewrites a cluster-wide query to a single namespace**,
returning those results as though they were the whole cluster. Worse, `canIUse` is `allowed, _ := CanI(...)`
— **the error is discarded**, so an API blip is indistinguishable from a denial and triggers the same
narrowing. And the namespace fallback resolves to **`"default"`** when the context sets none.

**Status of this finding**: the API behaviour is **verified by me on the live cluster**; the server's
narrowing is **code-inspection only** and MUST be reproduced against the running server during
implementation before it is claimed as verified.

That inversion is the whole feature: *the API is honest and the adopted layer launders a 403 into a
plausible short list.* Nothing NetClaw ships should let that reach a user unqualified.

## Two more risks worth carrying into the spec

- **Ambient-context risk.** Every candidate defaults to `~/.kube/config` and its `current-context`. If a
  developer's current context is production, a server started with no arguments talks to production. On this
  machine `kubectl config get-contexts` already lists two contexts with **none marked current**.
- **Secrets are readable by default.** `containers-k8s`'s `denied_resources` defaults to `[]`. Its README
  shows a Secret-denial snippet but does not apply it.

## Suggested starting configuration (measured: 7 tools, 2,301 tokens)

```toml
read_only = true
toolsets = ["core"]
disabled_tools = ["nodes_log","nodes_stats_summary","nodes_top","pods_top","pods_log","projects_list"]

[[denied_resources]]
group = ""
version = "v1"
kind = "Secret"
```

Run with `--kubeconfig` pointed at a **dedicated file holding a read-only ServiceAccount** — not the
developer's ambient config — which addresses the prod-context default and the silent-narrowing trap at once,
because a token with genuine cluster-wide read never triggers the narrowing path.
