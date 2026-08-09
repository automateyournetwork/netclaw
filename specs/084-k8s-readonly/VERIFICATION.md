# Verification Report — Kubernetes read-only coverage (spec 084 / R14)

**Date**: 2026-08-03 · **FR-042, FR-043, FR-044, SC-023**

**Cluster tested**: `kind` cluster `netclaw-r14`, **Kubernetes v1.35.0**, 2 nodes, with two namespaces,
two NetworkPolicies, a restricted ServiceAccount and a cluster-wide-read ServiceAccount created for the
purpose.

**Server tested**: `containers/kubernetes-mcp-server` **v0.0.66**, SHA-256
`692a7b28…d899dbc`, statically linked.

## The headline: FR-043 was reproduced, not cited

The feature's central claim was code-inspection-only when the spec was written. It is now demonstrated
**inside NetClaw's own test suite** (`tests/k8s/test_live_k8s.py::test_silent_narrowing_reproduces`):

```
cluster ground truth                     2 NetworkPolicies, in 2 namespaces
raw kubectl, limited credential      →   Forbidden: cannot list at the cluster scope
this server, SAME credential         →   success, 1 policy, no error, no caveat
```

The Kubernetes API is **honest**. The adopted server converts that 403 into a plausible short list.
`resources.go:34-38` narrows the query and **discards the permission error**, so an API blip is
indistinguishable from a denial.

For NetworkPolicy review that is an **audit lie** — and it is why this feature exists.

## Per-capability status

| Capability | Exercised live | Evidence |
|---|---|---|
| **Silent narrowing reproduced** | ✅ | 1 of 2 policies returned with no error, side by side with kubectl's 403 |
| **Mandated credential avoids it** | ✅ | `can-i list netpol -A` → `yes`; server returns **2 of 2** |
| Secret denial (server) | ✅ | `resource not allowed: /v1, Kind=Secret` |
| Secret denial (RBAC, 2nd layer) | ✅ | `can-i get secrets -A` → `no` |
| NetworkPolicy content usable | ✅ | selectors and pod-selector data returned, not just names |
| Non-existent ns ≠ empty ns | ✅ | `namespaces_list` establishes existence; the API returns empty, not 404 |
| Typo'd selector | ✅ | HTTP 200, zero rows — identical to a genuine non-match |
| Missing CRD is a real error | ✅ | `cilium.io/v2` errors rather than returning empty |
| Write refused | ✅ | no write tool is registered at all |
| Manifest ≤ 5,000 | ✅ | **1,643** measured via real handshake; exactly 7 tools |
| Checksum matches | ✅ | installed binary hashes to the recorded value |
| Read-only forced by NetClaw | ✅ | asserted against `config.toml` and `openclaw.json` |
| Explicit kubeconfig, not ambient | ✅ | `--kubeconfig` required in the registration |
| No context-switching tool | ✅ | absent from the 7-tool surface |

**104 assertions across 4 suites, exit 0.**

## Unverified, stated plainly

| Item | Why | What would close it |
|---|---|---|
| **Service path tracing end-to-end (US2)** | The skill is written and statically tested, but a Service with a deliberately non-matching selector, an Ingress with a dangling backend, and not-ready endpoints were **not** built in the lab. `resources_list` for Services/Ingresses/EndpointSlices works; the *diagnostic reasoning* is unexercised | Build those three cases in the cluster and run through the skill |
| **Workload inventory against failure states (US3)** | Pods list correctly, but `CrashLoopBackOff`, `ImagePullBackOff` and `Unschedulable` were not induced | Induce them |
| **Log level 9** | `--log-file` at level 4 logs lifecycle only. Whether level 9 records tool calls is untested | Run at level 9 |
| **Cluster-scoped CRD policies** | Cilium/Calico CRDs are readable as objects; their **semantics** are not interpreted. Deliberate scope decision, not an oversight | The CNI follow-on |
| **A cluster with RBAC that denies `namespaces_list`** | The six-cause table assumes namespace existence can be established. A credential that cannot list namespaces would degrade that | A more restricted credential |

## Corrections made during this feature

**My own Complexity Tracking was wrong, and a task I wrote caught it.** I asserted the binary "has no audit
concept". T007b existed to *establish* rather than assume, and found `--log-file` and `--log-level` do
exist. Measured at level 4 the log holds lifecycle only — startup, config path, feature gates, session
begin/end — with **no tool calls and no arguments**. So: operational logging, not a per-call audit trail.
Corrected in place.

**The first attempt at the central test was invalid.** It appeared to show a restricted account listing
cluster-wide successfully. `kubectl auth whoami` showed why: **`kubernetes-admin` via X509** — the
kubeconfig's client certificate silently overrode `--token`. A token-only kubeconfig was required, and that
requirement is now documented in `.env.example` and the server README because anyone reproducing this will
hit it.

**The research's predicted manifest was 2,301 tokens; measured it is 1,643.** Better than predicted, and
recorded as measured rather than carried forward from research.

## Limitations by design

- **No per-call GAIT audit** — inherited; acceptable only because strictly read-only. Any future write path
  must carry real audit and both gates.
- **Trust-on-first-use checksum** — upstream publishes none (15 assets, zero `sha` files). The recorded hash
  detects a re-tagged or altered asset; it is not upstream attestation.
- **Distinctions are partly guidance-level** — but unlike spec 083 this is **not guidance alone**: the
  mandated cluster-wide-read ServiceAccount removes the trap mechanically. Guidance is the second layer.

## iN2N (FR-041-adjacent)

**Not triggered.** A read-only observability integration with a single credential; no member specialisation
justifies the five member artifacts. Recorded as a decision.

## Checks

| Check | Result |
|---|---|
| `bash tests/k8s/run-tests.sh` (with cluster) | ✅ **104 assertions, 4 suites, exit 0** |
| `python3 scripts/reconcile-mcp.py` | ✅ exit 0, all four surfaces |
| `verify-inventory-counts.py` | ✅ **215 skills / 157 integrations** |
| `trace-skill.py` × 3 | ✅ all resolve |
| Regression: document, zabbix, bgp-intel, fortinet, reconcile | ✅ all exit 0 |
| `node --check server.js` · `bash -n catalog.sh` | ✅ |
