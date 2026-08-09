---
name: k8s-service-path
description: "Trace the Kubernetes service path — Service to selector to pods to EndpointSlices to readiness, plus Ingress routing. Use when a service is getting no traffic, an ingress is not routing, or someone asks why a workload is unreachable inside a cluster."
version: 1.0.0
license: Apache-2.0
tags: [kubernetes, k8s, service, ingress, endpoints, endpointslice, troubleshooting]
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["kubectl"], "env": ["K8S_MCP_CMD", "K8S_KUBECONFIG"] } } }
---

# Kubernetes Service Path Tracing

## Server

`k8s-mcp` — vendored third-party, read-only, 7 tools. See
[k8s-network-policy](../k8s-network-policy/SKILL.md) for the shared preflight and the empty-result cautions,
which apply here identically.

## The path, and the rule about it

```
Ingress → Service → selector → Pods → EndpointSlice → readiness
```

**Mark every link checked or not checked.** A partial trace presented as complete is the failure mode of
this skill — "the service is fine" after checking two of five links is worse than saying nothing, because it
sends the next person somewhere else.

## Walking it

```jsonc
resources_list({"apiVersion":"networking.k8s.io/v1","kind":"Ingress"})
resources_get ({"apiVersion":"v1","kind":"Service","namespace":"app1","name":"web"})
pods_list_in_namespace({"namespace":"app1"})            // then match against the Service selector
resources_list({"apiVersion":"discovery.k8s.io/v1","kind":"EndpointSlice","namespace":"app1"})
```

## Diagnoses that look identical and are not

| Symptom | Actual cause | How to say it |
|---|---|---|
| No endpoints | **Selector matches no pods** | *"The Service selector `app=web` matches no pods"* — the selector is wrong or the pods are gone |
| No endpoints | Pods exist but **none are ready** | *"3 pods match but none are Ready"* — a readiness-probe problem, not a wiring problem |
| No endpoints | Pods ready, **port mismatch** | *"Pods are ready but no container exposes the target port"* |
| Traffic blocked | A **NetworkPolicy** denies it | hand off to `k8s-network-policy` — this skill does not evaluate policy |
| Ingress not routing | Backend names a **non-existent Service** | *"Ingress `web` routes to Service `web-v2`, which does not exist"* — call this out loudly, it is a common and silent misconfiguration |

**"No endpoints" is a symptom, never a diagnosis.** Always name which of these it is.

## Ready is not the same as existing

An EndpointSlice lists both ready and not-ready addresses. A Service with five not-ready endpoints has
**zero** serving capacity but is not empty. Report the two counts separately — collapsing them hides an
outage.

## Empty results

Everything in `k8s-network-policy`'s six-cause table applies. In particular:

- A Service in a **non-existent namespace** returns nothing, not a 404.
- A **typo'd selector** returns zero pods with HTTP 200 — show the selector.
- Without confirmed cluster-wide scope, a cross-namespace Ingress trace may be **silently incomplete**.

## Boundaries

| Want to… | Use |
|---|---|
| Whether traffic is **permitted** | `k8s-network-policy` — this traces wiring, not policy |
| Whether packets actually **flowed** | `kubeshark-traffic` |
| Latency / error rates | `prometheus`, `grafana` |
| Pod inventory and status | `k8s-workload-inventory` |
| Change anything | **nothing here.** Read-only |

## Rules

1. **State which links you checked and which you did not.**
2. **"No endpoints" is a symptom** — name the cause.
3. **Separate ready from not-ready.**
4. **Call out an Ingress backend that does not exist.**
5. **Show selectors and scope.** Read-only.
