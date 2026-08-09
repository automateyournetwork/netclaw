---
name: k8s-workload-inventory
description: "List Kubernetes workloads and namespaces — pods with their node, phase and readiness, plus events. Use when asked what is running, where it is running, what is failing, or for a general inventory of a cluster."
version: 1.0.0
license: Apache-2.0
tags: [kubernetes, k8s, pods, inventory, namespaces, events, troubleshooting]
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["kubectl"], "env": ["K8S_MCP_CMD", "K8S_KUBECONFIG"] } } }
---

# Kubernetes Workload Inventory

## Server

`k8s-mcp` — vendored third-party, read-only, 7 tools: `pods_list`, `pods_list_in_namespace`, `pods_get`,
`namespaces_list`, `events_list`, `resources_list`, `resources_get`. See
[k8s-network-policy](../k8s-network-policy/SKILL.md) for the shared preflight.

## Always say which scope you covered

`pods_list` is cluster-wide; `pods_list_in_namespace` is not. **State which you used.** Leaving it ambiguous
is how "12 pods" gets read as the whole cluster when it was one namespace.

And **say which cluster answered** — an operator with several must never have to guess.

## Report failures, never omit them

A pod that is not Running is **the interesting one**. Give its phase and reason:

| Phase / reason | Means |
|---|---|
| `Pending` + `Unschedulable` | no node satisfies its requests or affinity |
| `Pending` + `ContainerCreating` | image pull or volume mount in progress |
| `ImagePullBackOff` / `ErrImagePull` | wrong image, wrong tag, or missing pull secret |
| `CrashLoopBackOff` | starts and dies repeatedly — check `events_list` |
| `Running` but **not Ready** | readiness probe failing. **It is not serving traffic** |
| `Evicted` | node pressure |

**`Running` is not `Ready`.** A pod can be Running and serving nothing. Report both, and never summarise a
set of pods as "healthy" on phase alone.

## Events give the why

`events_list` explains what a pod status only names. Events are **time-limited** (typically one hour) — an
empty event list for an old problem means the events aged out, **not** that nothing happened. That is
another empty-result trap: say *"no events in the retention window"*, not *"no events"*.

## Empty results

The six-cause table in `k8s-network-policy` applies. Most relevant here: a **non-existent namespace** and an
**empty namespace** both return zero pods. Check `namespaces_list` before concluding.

## Boundaries

| Want to… | Use |
|---|---|
| Pod CPU/memory over time | `prometheus`, `grafana` — this is the object model, not metrics |
| Actual traffic | `kubeshark-traffic` |
| Whether traffic is permitted | `k8s-network-policy` |
| Why a service has no endpoints | `k8s-service-path` |
| Build a lab | `containerlab`, `gns3`, `cml` |
| Change anything | **nothing here.** Read-only; Secrets are denied |

## Rules

1. **State the scope** — cluster-wide or which namespace.
2. **State which cluster.**
3. **Never omit non-running pods.** They are the point.
4. **Running ≠ Ready.**
5. **No events in the window ≠ nothing happened.**
6. **Read-only.**
