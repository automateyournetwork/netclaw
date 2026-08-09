---
name: k8s-network-policy
description: "Review Kubernetes NetworkPolicies — what is actually permitted to reach a workload, and whether the answer can be trusted. Use when asked what can talk to a pod, whether a namespace is restricted, why traffic is being blocked, or for any security review of cluster network segmentation."
version: 1.0.0
license: Apache-2.0
tags: [kubernetes, k8s, networkpolicy, security, segmentation, audit, cni]
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["kubectl"], "env": ["K8S_MCP_CMD", "K8S_KUBECONFIG"] } } }
---

# Kubernetes NetworkPolicy Review

## Server

`k8s-mcp` — vendored third-party (`containers/kubernetes-mcp-server` v0.0.66, **Apache-2.0**), a pinned
static Go binary. **7 tools, strictly read-only, Secrets denied.**

## ⚠ Two rules before anything else

### 1. No NetworkPolicy means ALL traffic is permitted

Kubernetes is default-allow. A namespace with **zero** policies permits everything, in both directions.

So *"no policies found"* is not a neutral observation — it is a **finding**, and reporting it without the
consequence invites exactly the wrong conclusion. Someone reading "no policies" while thinking about
security will hear "nothing to worry about". The opposite is true.

**Always say the consequence:** *"No NetworkPolicy applies to this workload, so all ingress and egress
traffic is permitted."*

### 2. An empty result may mean you could not see, not that nothing exists

**This is the one that gets people, and this server makes it worse.**

Given a credential without cluster-wide list permission, the adopted server does **not** return an error.
It silently rewrites your cluster-wide query to a single namespace and hands back that result with no
caveat. Reproduced against a live cluster:

```
raw kubectl  →  Forbidden: cannot list networkpolicies at the cluster scope
this server  →  success, one policy          ← the cluster actually had two
```

For a security review that is an **audit lie**: *"no policy restricts this pod"* when the truth is *"I could
not see them"*.

## The procedure — do this every time

**Step 1 — confirm scope before you trust anything.**

```
kubectl --kubeconfig $K8S_KUBECONFIG auth can-i list networkpolicies --all-namespaces
```

- `yes` → cluster-wide answers are trustworthy. Proceed.
- `no` → **stop treating empty results as absence.** Any answer you give is namespace-scoped at best, and
  you must say so explicitly.

The supported deployment uses a dedicated cluster-wide-read ServiceAccount precisely so this returns `yes`
and the narrowing branch never executes. If it returns `no`, the deployment is misconfigured — say that
rather than working around it.

**Step 2 — list the policies.**

```jsonc
resources_list({"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy"})
resources_list({"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy", "namespace": "app1"})
```

**Step 3 — report selectors, policy types and rules**, not merely that a policy exists. "There is a policy"
tells a reviewer nothing about what is permitted. Give the `podSelector`, the `policyTypes`
(Ingress/Egress), and the actual `from`/`to` rules.

**Step 4 — state the scope you actually queried**, and **which cluster answered**. An operator with several
clusters must never have to guess.

## The six reasons you get nothing back

| Cause | How to tell | How to say it |
|---|---|---|
| **Permission insufficient** | Step 1 returned `no` | *"Scope could not be established — this is not evidence that no policies exist"* |
| **Namespace does not exist** | `namespaces_list` does not contain it | *"No such namespace"* — not "no policies" |
| **Namespace exists but is empty** | it is in `namespaces_list` | *"No policies in this namespace, so all traffic there is permitted"* |
| **Selector matched nothing** | you passed a label selector | *"No match for `<selector>`"* — and **show the selector**, so a typo is visible |
| **CRD not installed** | GVK resolution error | *"Cilium/Calico policies are not installed on this cluster"* — a real error, distinguishable |
| **Cluster unreachable** | transport failure | *"The cluster could not be reached"* — never "no policies" |

A typo'd selector and a genuine non-match are **identical over the wire** — both return HTTP 200 with an
empty list. Showing the selector you used is the only thing that lets a reader spot the difference.

## Completeness caveat

A namespace-scoped policy list is **not** a complete picture of what can reach a workload. Policies in other
namespaces, and cluster-scoped CRD policies (Cilium `CiliumClusterwideNetworkPolicy`, Calico
`GlobalNetworkPolicy`), also apply. Say so unless cluster-wide scope was confirmed and CRDs were checked.

## Traffic observed is not traffic permitted

`kubeshark-traffic` shows packets that **flowed**. This shows what is **declared**. They answer different
questions and are constantly confused:

- Traffic flowing does **not** prove a policy permits it — the policy may have been added after.
- No traffic does **not** prove a policy blocks it — nothing may have tried.

When both are used, report them as **two kinds of evidence**, never as one conclusion.

## Boundaries

| Want to… | Use |
|---|---|
| See actual packets | `kubeshark-traffic` — observed traffic, not declared config |
| Workload metrics | `prometheus`, `grafana` |
| Build a lab | `containerlab`, `gns3`, `cml` |
| Service/ingress path | `k8s-service-path` |
| Pod inventory | `k8s-workload-inventory` |
| Change anything | **nothing here.** Strictly read-only; no mutation is reachable |

## Rules

1. **Run the Step 1 preflight.** An empty result without confirmed scope is not an absence.
2. **Never report "no policies" without "therefore all traffic is permitted."**
3. **Show the selector and the scope** in every answer.
4. **Say which cluster answered.**
5. **Read-only.** Secrets are denied and no mutation exists.
