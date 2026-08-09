# k8s-mcp — Kubernetes read-only coverage

**Spec 084 / roadmap R14.** 7 tools, stdio, **strictly read-only**, Secrets denied.
Manifest measured **1,643 / 5,000 tokens**.

`kubeshark-traffic` sees packets inside a cluster. This reads the objects: pods, services, ingresses,
EndpointSlices and **NetworkPolicies** — the hard floor for any container-networking work.

## Adopted, not authored

See [NOTICE.md](./NOTICE.md). `containers/kubernetes-mcp-server` **v0.0.66**, **Apache-2.0**, a pinned
statically-linked Go binary verified against a recorded SHA-256. Not committed — 75 MB, fetched at install.

### Why, with the numbers

Measured by building and running each candidate and issuing a real `tools/list`:

| Candidate / config | Tools | Tokens | Outcome |
|---|---|---|---|
| **this, `read_only + core + disabled`** | **7** | **1,643** | **adopted** |
| this, `--read-only` defaults | 15 | 4,049 | passes, more than needed |
| **this, DEFAULT config** | 21 | 5,716 | **busts the ceiling** |
| this, all 8 toolsets | 51 | 18,236 | far over |
| `Flux159/mcp-server-kubernetes` read-only | 8 | 1,686 | fallback, with a caution |
| `Flux159` DEFAULT | 23 | 6,312 | busts the ceiling |
| `rohitg00/kubectl-mcp-server` | **313** | — | rejected |
| `patrickdappollonio/mcp-kubernetes-ro` | 10 | 2,140 | good design, 23★, single maintainer |

**Both leading candidates bust the ceiling in their default configuration.** Trimming is what makes
adoption possible, not merely tidier.

Three properties decided it:

1. **Apache-2.0** — identical to NetClaw's own, so unlike spec 083 there is no vendoring-posture question.
2. **Statically linked Go** (`ldd` → *not a dynamic executable*). Zero runtime dependencies, so it
   **cannot** collide with the `fastmcp<3` pins carried by five NetClaw servers. Structural, not careful.
3. **Read-only enforced at registration time** (`isToolApplicable`, `pkg/mcp/mcp.go:69`) — filtered tools
   are never registered and cannot be invoked.

**Rejections, recorded so they are not revisited:**

- **`rohitg00` — disqualified twice**: 313 tools, *and* it pins `fastmcp>=3.0.0b1`, spec 083's blocker
  reproduced exactly.
- **`Flux159` — the caution**: five published advisories, including **GHSA-cr22-wjx7-2w6m (High)**,
  *"Tool Access Control Bypass: Presentation-Layer Filtering Without Execution-Layer Enforcement"* — tools
  hidden from `tools/list` were **still callable**. That is precisely the mechanism we would depend on to
  fit the ceiling. Fixed now; the pattern is the warning. Its `kubectl_context` also accepts
  `operation: "set"`, letting a model switch clusters mid-session while still counting as read-only.

**There is no official Kubernetes or CNCF MCP server.** `org:kubernetes mcp` → 0 repos; `org:cncf mcp` → 0.

## ⚠ The upstream behaviour this integration exists to contain

Given a credential **without** cluster-wide list permission, the server does not return an error. It
rewrites your cluster-wide query to a single namespace and returns that as the answer.

Reproduced live, same credential, same question:

```
raw kubectl  →  Error from server (Forbidden): cannot list networkpolicies at the cluster scope
this server  →  success, 1 policy                    ← the cluster had 2
```

`pkg/kubernetes/resources.go:34-38` runs a SelfSubjectAccessReview and on denial narrows the query — and
`canIUse` is `allowed, _ := CanI(...)`, so **the permission error is discarded** and an API blip is
indistinguishable from a denial. The namespace fallback resolves to `"default"`.

For NetworkPolicy review that is an **audit lie**: *"no policy restricts this pod"* when the truth is
*"I could not see them"*.

**Two layers answer it**, and the first is mechanical rather than advisory:

1. **A mandated cluster-wide-read ServiceAccount.** With it, `canIUse` returns true and the narrowing
   branch never executes. Verified: `can-i list networkpolicies -A` → `yes`, and the server returns 2 of 2.
2. **A skill preflight.** `k8s-network-policy` requires `can-i` before trusting any empty result, catching
   a misconfigured deployment.

## Configuration NetClaw forces

| Setting | Why |
|---|---|
| `read_only = true` | Never inherited |
| `toolsets = ["core"]` + 6 `disabled_tools` | The default busts the ceiling |
| `denied_resources` → `Secret` | **Upstream defaults this to empty — Secrets are readable.** Its README shows the snippet and does not apply it |
| explicit `--kubeconfig` | Every candidate otherwise uses the ambient `current-context`, which may be **production** |

The ServiceAccount's RBAC also denies Secrets, so that is two independent layers
(`can-i get secrets` → `no`, verified).

## Setup

```bash
kubectl create serviceaccount netclaw-ro -n default
kubectl create clusterrole netclaw-view \
  --verb=get,list,watch \
  --resource=pods,services,ingresses,networkpolicies,endpointslices,namespaces,events
kubectl create clusterrolebinding netclaw-ro-b \
  --clusterrole=netclaw-view --serviceaccount=default:netclaw-ro
```

Then build a **token-only** kubeconfig from `kubectl create token netclaw-ro`. It must be token-only: a
kubeconfig that also carries a client certificate **silently ignores the token** and authenticates as the
certificate's identity. That mistake invalidated the first attempt at verifying this feature's central
claim, and `kubectl auth whoami` is how to catch it.

## Limitations

- **No per-call GAIT audit.** The binary exposes `--log-file`/`--log-level`, but measured at level 4 the log
  contains lifecycle only — no tool calls, no arguments. Operational logging, not an audit trail. Acceptable
  only because this is strictly read-only. (Whether level 9 records calls is untested.)
- **Trust-on-first-use checksum.** Upstream publishes none — 15 release assets, zero `sha` files. The
  recorded hash detects a re-tagged or altered asset; it is not upstream attestation.
- **Cluster-scoped CRD policies** (Cilium, Calico) are readable as objects but their **semantics** are not
  interpreted. A follow-on.

## Skills

`k8s-network-policy` (the preflight lives here) · `k8s-service-path` · `k8s-workload-inventory`

## Tests

```bash
bash tests/k8s/run-tests.sh                                    # static
K8S_TEST_KUBECONFIG=... K8S_TEST_LIMITED_KUBECONFIG=... \
  bash tests/k8s/run-tests.sh                                  # + live
```

104 assertions. The live suite **reproduces the silent narrowing** rather than citing it.
