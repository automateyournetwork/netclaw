# Feature Specification: Kubernetes read-only coverage

**Feature Branch**: `084-k8s-readonly`
**Created**: 2026-08-03
**Status**: Draft
**Roadmap**: R14, Tier 3

## Overview

`kubeshark-traffic` gives NetClaw packet-level visibility inside a cluster. It cannot read a **pod**, a
**service**, an **ingress**, or a **NetworkPolicy**.

That is the hard floor for any container-networking work. NetClaw can watch traffic flow between two pods
and cannot answer the first question anyone asks about it:

- *What is supposed to be allowed to talk to this pod?*
- *Why is this service getting no traffic — no endpoints, or no policy?*
- *Which ingress routes to this backend?*
- *Is anything at all restricting this namespace?*

This feature adds read-only Kubernetes API coverage: workloads, services, ingresses, endpoints and network
policies.

## The distinction this feature exists to protect

### An empty list is not evidence of absence

Every feature since 078 has protected one distinction. This one is the same shape as R11's — an empty result
that means something other than "nothing is there" — but with a consequence the others did not have:
**NetworkPolicy review is a security task, and a false negative here is an audit lie.**

Saying *"no NetworkPolicy restricts this pod"* when the truth is *"I could not see them"* is not a degraded
answer. It is the opposite of the right one, delivered with confidence, about a control someone is relying
on.

Measured on a live cluster (Kubernetes v1.35.0):

| Ask | Result |
|---|---|
| List in a **namespace that does not exist** | **0 items, HTTP 200** — not a 404 |
| **Typo a label selector** (`app=wbe` for `app=web`) | **0 pods, HTTP 200** — identical to "none match" |
| **Omit the all-namespaces flag** | **0 policies** in `default` — while **1** existed cluster-wide |

None of those is an error. All three return success.

### And the sharper half: the API is honest, the adopted layer is not

This was mis-tested first, and the correction matters.

An initial attempt appeared to show a restricted account happily listing cluster-wide. `auth whoami`
revealed why: **`kubernetes-admin` via X509** — the kubeconfig's client certificate had silently overridden
the `--token`. Re-run with a token-only kubeconfig and a genuine restricted identity:

```
identity: system:serviceaccount:app1:limited
can-i list networkpolicies -A  →  no
get netpol -A                  →  Error from server (Forbidden):
                                  cannot list resource "networkpolicies" at the cluster scope
```

**The Kubernetes API returns a correct 403.** It does not silently narrow. It tells the truth.

The silent narrowing is **the adopted server's behaviour**. `pkg/kubernetes/resources.go:34-38`:

```go
isNamespaced, _ := c.isNamespaced(gvk)
if isNamespaced && !c.canIUse(ctx, gvr, namespace, "list") && namespace == "" {
    namespace = c.NamespaceOrDefault("")
}
```

On denial it **rewrites a cluster-wide query to a single namespace** and returns those results as though
they were the whole cluster. And `canIUse` is `allowed, _ := CanI(...)` — **the permission error is
discarded**, so an API blip is indistinguishable from a denial and triggers the same narrowing. The
namespace fallback resolves to **`"default"`**.

So the shape of this feature is unusual and worth stating plainly: **the upstream API is trustworthy, and
the layer being adopted launders a 403 into a plausible short list.** Everything NetClaw builds here exists
to stop that reaching a user unqualified.

*Status*: **both halves are now verified live** — see Clarifications. The API's honest 403 and the server's
silent narrowing were reproduced side by side with the same credential against the same cluster. FR-043 is
satisfied, not pending.

### Third distinction: reachable is not permitted

`kubeshark` can show that traffic flowed. A NetworkPolicy says what is *allowed*. These answer different
questions and are routinely confused — "it works" is not "it is permitted", and a cluster with no policies
at all permits everything while looking perfectly healthy.

## Build vs adopt — adopt, and this time the licence agrees

Measured by building and running each candidate and issuing a real `tools/list`, not read off READMEs:

| Configuration | Tools | Tokens | vs 5,000 ceiling |
|---|---|---|---|
| **`containers/kubernetes-mcp-server`** `read_only + core + disabled` | **7** | **2,301** | **PASS — 54% under** |
| same, `--read-only` default toolsets | 15 | 4,049 | PASS |
| same, **default config** | 21 | 5,716 | **FAIL** |
| same, all 8 toolsets | 51 | 18,236 | FAIL |
| `Flux159/mcp-server-kubernetes` read-only | 8 | 1,686 | PASS |
| `Flux159` **default config** | 23 | 6,312 | **FAIL** |
| `rohitg00/kubectl-mcp-server` | **313** | — | FAIL by ~6× |
| `patrickdappollonio/mcp-kubernetes-ro` | 10 | 2,140 | PASS |

**Both leading candidates bust the ceiling in their default configuration.** Read-only is not merely the
safer posture here — it is what makes adoption possible at all.

**`containers/kubernetes-mcp-server`** is Red Hat's (originally `manusa/`, donated to the `containers` org;
`openshift/openshift-mcp-server` is the downstream product build). Three properties make it the choice:

- **Apache-2.0** — licence-identical to NetClaw. Unlike R11's GPL-3.0 there is no vendoring-posture question
  at all.
- **A Go static binary.** Zero Python or Node runtime dependencies, so it **structurally cannot** collide
  with the `fastmcp<3` pins that blocked R11's first candidate. Dependency conflict is impossible by
  construction, not by care.
- **Read-only enforced at registration time** (`isToolApplicable`, `pkg/mcp/mcp.go:69`) — filtered tools are
  never registered with the SDK and cannot be invoked.

Two rejections worth recording so they are not revisited:

- **`rohitg00` is disqualified twice over**: 313 tools, *and* it pins `fastmcp>=3.0.0b1` — R11's blocker
  reproduced exactly.
- **`Flux159` is the fallback, with a caution.** Five published advisories, the most relevant being
  **GHSA-cr22-wjx7-2w6m (High)** — *"Tool Access Control Bypass: Presentation-Layer Filtering Without
  Execution-Layer Enforcement"*: tools hidden from `tools/list` were **still callable**. That is precisely
  the mechanism we would depend on to fit the ceiling. Fixed now; the pattern is the warning. Separately its
  `kubectl_context` tool accepts `operation: "set"`, so **the model can switch clusters mid-session** — and
  it counts as read-only, because switching context is not a cluster write.

**There is no official Kubernetes or CNCF MCP server.** `org:kubernetes mcp` → 0 repos; `org:cncf mcp` → 0.
`kubernetes-sigs/mcp-lifecycle-operator` is the inverse — an operator for deploying MCP servers *onto*
Kubernetes.

## Two risks that come with any candidate

**Ambient-context risk.** Every candidate defaults to `~/.kube/config` and its `current-context`. A server
started with no arguments talks to whatever cluster the operator last used — **including production**. On
this machine `kubectl config get-contexts` already lists multiple contexts.

**Secrets are readable by default.** `denied_resources` defaults to `[]`. The upstream README shows a
Secret-denial snippet and does not apply it.

## The infrastructure is real and running

A `kind` cluster, **Kubernetes v1.35.0**, two nodes, with NetworkPolicies, Services and namespaces created
for verification, plus a restricted ServiceAccount. Every capability this feature claims can be exercised
against it. Nothing is blocked on a VM or a licence.

## Clarifications

### Session 2026-08-03

- Q: Where does scope-confirmation live, given the adopted server actively converts a 403 into a plausible short list? → A: **Both layers.** (1) Mandate a **dedicated cluster-wide-read ServiceAccount**, which removes the trap at the root — `canIUse` returns true so the narrowing branch never executes. (2) **Also** require the skill to run a permission preflight and refuse to report absence without confirmed scope. R11's forced-read-only + deny-list already proved the second layer earns its keep.
- Q: How much tool surface? → A: **`read_only + core + disabled_tools`.** Measured live: **7 tools, 1,643 tokens** (33% of ceiling). Generic `resources_list`/`resources_get` already reach NetworkPolicy, Service, Ingress and EndpointSlice. Logs and metrics belong to `kubeshark` and `prometheus`.
- Q: How is a Go binary vendored? → A: **Pinned release binary downloaded at install, verified against a recorded SHA-256.** Not `@latest` — that is exactly how a 7-tool surface silently becomes 21 and busts the ceiling. Not source-build — no Go toolchain is assumed present.
- Q: (raised during verification) **Upstream publishes no checksums.** The release has 15 assets and zero `sha`/`checksum` files, so "pinned release + checksum" was only half available as recommended. → A: **NetClaw records its own SHA-256** of the pinned artifact and verifies every install against it. This is trust-on-first-use rather than upstream attestation — weaker, and stated as such — but it still detects a re-tagged or altered asset.

### Verified during clarification, not merely designed

| Claim | Result |
|---|---|
| Pinned binary exists for linux/amd64 | **v0.0.66**, published 2026-07-31 |
| Statically linked, no runtime deps | `not a dynamic executable` — the dependency-conflict-impossible claim holds |
| Recorded SHA-256 | `692a7b283a96140311fd46f13b8373657b2e9bfe660a36bb6434e8c42d899dbc` |
| Tool count and manifest | **7 tools, 1,643 tokens** — better than the 2,301 predicted |
| Secret denial | `resource not allowed: /v1, Kind=Secret` — **works** |
| **FR-043: the silent narrowing** | **REPRODUCED** — see below |
| Cluster-wide-read SA avoids narrowing | `can-i list netpol -A` = yes; raw count 2 of 2 policies |

**FR-043 is no longer code inspection.** Same credential, same question, side by side:

```
raw kubectl  →  Error from server (Forbidden): ... cannot list ... at the cluster scope
MCP server   →  err=False,  app1/policy-app1        ← one namespace, no caveat
```

The cluster holds **two** policies. `kubectl` refuses honestly. The server returns **one**, with no error and
no indication that scope was narrowed. That is the failure this feature exists to prevent, demonstrated.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — What is allowed to reach this pod? (Priority: P1)

A security reviewer wants to know what NetworkPolicies apply to a workload, and whether the answer is
trustworthy.

**Why this priority**: It is the roadmap's headline ask, and the one place where a wrong answer is a
security finding rather than an inconvenience. Nothing else here is worth shipping if this one can lie.

**Independent Test**: query policies for a pod in a namespace that has them, one that does not, and with a
credential that cannot see them — and confirm all three answers differ.

**Acceptance Scenarios**:

1. **Given** a namespace with a NetworkPolicy, **When** policies are queried, **Then** they are returned
   with their pod selectors, policy types and ingress/egress rules.
2. **Given** a namespace with **no** policies, **Then** the answer says **no policy exists — and therefore
   all traffic is permitted**, because in Kubernetes an absence of policy is permissive, not restrictive.
   Reporting "no policies" without that consequence is a half-answer.
3. **Given** a credential that cannot list cluster-wide, **Then** the answer states the scope could not be
   established. It **MUST NOT** return a namespace-scoped list as though it were cluster-wide.
4. **Given** a namespace that does not exist, **Then** that is stated — not reported as "no policies".
5. **Given** a label selector that matches nothing, **Then** the answer distinguishes *nothing matched* from
   *the selector may be wrong*, and shows the selector used.
6. **Given** any policy answer, **Then** the **scope actually queried** is stated alongside it.

---

### User Story 2 — Why is this service getting no traffic? (Priority: P1)

An engineer has a Service that appears dead and needs to know where the path breaks: no endpoints, no
matching pods, a policy blocking it, or an ingress not routing to it.

**Why this priority**: The most common real Kubernetes networking question, and independently valuable. It
is also where the pieces have to join up — a Service with no EndpointSlice and a Service blocked by policy
look identical from outside.

**Independent Test**: build a Service with no matching pods and one with healthy endpoints; confirm the two
are distinguishable and the reason is named.

**Acceptance Scenarios**:

1. **Given** a Service, **Then** its selector, ports, type and **backing EndpointSlices** are retrievable.
2. **Given** a Service whose selector matches no pods, **Then** the answer says **the selector matches no
   pods** — not merely that there are no endpoints.
3. **Given** a Service with endpoints that are not ready, **Then** ready and not-ready are distinguished.
4. **Given** an Ingress, **Then** its rules, paths and backend services are retrievable, and a backend that
   names a non-existent Service is called out.
5. **Given** a path trace request, **Then** the answer states which links were checked and **which were
   not** — a partial trace presented as complete is the failure mode here.

---

### User Story 3 — What is actually running, and where? (Priority: P2)

An engineer wants the workload inventory: pods, their nodes, their status, their namespaces.

**Why this priority**: The enabling capability behind the other two, and genuinely useful alone — but it is
the least likely to mislead, because a missing pod is usually obvious.

**Independent Test**: list workloads across namespaces and confirm the result matches the cluster.

**Acceptance Scenarios**:

1. **Given** a cluster, **Then** pods are listable with namespace, node, phase and readiness.
2. **Given** a namespace filter, **Then** the filter is applied and **stated in the answer**.
3. **Given** no namespace filter, **Then** the answer states whether it covered all namespaces or defaulted
   to one — never leaves it ambiguous.
4. **Given** a pod that is not running, **Then** its phase and reason are given rather than it being omitted.

---

### Edge Cases

- **The cluster is unreachable.** Reported as unreachable — never as "no resources".
- **The credential is expired or invalid.** Distinct from unreachable, and from empty.
- **The context points somewhere unexpected.** The cluster actually being talked to must be identifiable in
  the answer, because an ambient `current-context` may be production.
- **A CRD is not installed** (asking for a Cilium policy on a cluster without Cilium). This is a real error
  at GVK resolution and is distinguishable — say so rather than reporting no policies.
- **A very large cluster.** Bounded, with the bound stated, and the caller told how to narrow.
- **Secrets.** Must not be readable. A monitoring integration has no business reading Secret material.
- **A namespace exists but is empty** vs **a namespace that does not exist** — different answers.

## Requirements *(mandatory)*

### Functional Requirements

#### The empty-list distinction

- **FR-001**: An empty result MUST NOT be reported as absence unless the **scope was established**. Where
  scope could not be established, the answer MUST say so.
- **FR-002**: Every answer MUST state the **scope actually queried** — cluster-wide or which namespace(s).
- **FR-003**: **Insufficient permission MUST be a distinct outcome** from an empty result. If the adopted
  server narrows a cluster-wide query on denial, NetClaw MUST detect and surface that rather than pass the
  narrowed result through.
- **FR-004**: A **non-existent namespace** MUST be distinguished from an existing but empty one.
- **FR-005**: Where a **label or field selector** was used, it MUST appear in the answer, so a typo is
  visible rather than indistinguishable from "nothing matched".
- **FR-006**: An **unreachable cluster** and an **invalid credential** MUST each be distinct from an empty
  result and from each other.
- **FR-007**: A **missing CRD** MUST be reported as not-installed, never as "no such resources".

#### NetworkPolicy semantics

- **FR-008**: **No NetworkPolicy means all traffic is permitted.** Any answer reporting an absence of
  policies MUST state that consequence. An absence of policy is permissive in Kubernetes, and reporting it
  neutrally invites the opposite conclusion.
- **FR-009**: Policy answers MUST include pod selectors, policy types and rules — enough to reason about
  what is permitted, not merely that a policy exists.
- **FR-010**: A policy answer MUST NOT be presented as a complete picture of what can reach a workload
  unless cluster-wide scope was confirmed, since policies in other namespaces and cluster-scoped CRD
  policies can also apply.
- **FR-011**: **"Traffic was observed" is not "traffic is permitted."** Where this composes with
  `kubeshark-traffic`, the two MUST be reported as different kinds of evidence.

#### Service and ingress path

- **FR-012**: Services MUST be retrievable with selector, ports, type and backing EndpointSlices.
- **FR-013**: **A selector matching no pods MUST be named as such**, distinct from a Service having no
  endpoints for another reason.
- **FR-014**: Ready and not-ready endpoints MUST be distinguished.
- **FR-015**: Ingresses MUST be retrievable with rules, paths and backends; a backend naming a non-existent
  Service MUST be called out.
- **FR-016**: A path trace MUST state which links were checked **and which were not**.

#### Workload inventory

- **FR-017**: Pods MUST be listable with namespace, node, phase and readiness.
- **FR-018**: Non-running pods MUST be reported with phase and reason, never omitted.

#### Read-only and scope safety

- **FR-019**: The integration MUST be **strictly read-only**. No write path is exposed.
- **FR-020**: Read-only MUST be **forced by NetClaw's own configuration**, never inherited from a default,
  and MUST be enforced at **tool-registration time** so filtered tools cannot be invoked.
- **FR-021**: **Secrets MUST be denied** at the resource level. The upstream default is to allow them.
- **FR-022**: The **kubeconfig and context MUST be explicit**. NetClaw MUST NOT rely on the ambient
  `current-context`, which may be production.
- **FR-023**: The **cluster actually connected to** MUST be identifiable from NetClaw's configuration and
  surfaced in answers where it affects interpretation.
- **FR-024**: No tool that switches cluster context may be exposed. Context selection is an operator
  decision, not a model decision.
- **FR-025**: A dedicated **read-only credential** MUST be documented as the supported way to run this —
  both to avoid the production-context default and because a credential with genuine cluster-wide read never
  triggers the narrowing path.

#### Adoption and licence

- **FR-026**: The build-vs-adopt decision MUST be recorded with **measured** tool counts and licences for
  every candidate evaluated.
- **FR-027**: The adopted licence (Apache-2.0) MUST be recorded, along with the vendoring posture.
- **FR-028**: The adopted server MUST be **tested against a live cluster before adoption**, not after.
- **FR-029**: The rejected candidates' reasons MUST be recorded — `rohitg00`'s 313 tools and
  `fastmcp>=3.0.0b1`, and `Flux159`'s bypassable-filtering advisory — so they are not re-evaluated.
- **FR-030**: That **no official Kubernetes or CNCF MCP server exists** MUST be recorded.

#### Dependencies

- **FR-031**: Installation MUST use the repository's helpers, never a bare `pip`/`pip3` (spec 077), and
  never bare `python3 -m venv` (fails on this host).
- **FR-032**: No shared dependency version may be moved (spec 076). The Go binary makes this structurally
  safe and that MUST be recorded as the reason it was chosen.

#### Audit

- **FR-033**: Whether per-call GAIT audit exists MUST be determined and stated. If the adopted server has no
  audit concept, that is an inherited limitation to record — acceptable only because this is read-only.

#### Artifact coherence (Principle XI)

- **FR-034**: All surfaces MUST be updated: registration or an `EXTERNAL_INTEGRATIONS` entry with a reason;
  `catalog.sh` entry **and curated profile membership**; `install-steps.sh` install function; **both** HUD
  entries; `README.md` and `SOUL.md` including counts **and** a SOUL capability section; skills;
  `.env.example`; `TOOLS.md`; a server `README.md`; `.gitignore` handling for any vendored tree.
- **FR-035**: `python3 scripts/reconcile-mcp.py` MUST exit 0 across all four surfaces.
- **FR-036**: `python3 scripts/verify-inventory-counts.py` MUST exit 0 with updated counts.
- **FR-037**: The tool manifest MUST measure **≤ 5,000 tokens**, with the figure recorded.

#### Boundaries

- **FR-038**: The boundary against `kubeshark-traffic` MUST be stated: that shows **observed traffic**; this
  shows **declared configuration**. Reachability is not permission.
- **FR-039**: The boundary against `prometheus`/`grafana` MUST be stated: metrics about workloads, not the
  Kubernetes object model.
- **FR-040**: The boundary against `containerlab`/`gns3`/`cml` MUST be stated: those build labs; this reads a
  cluster.
- **FR-041**: Cluster **mutation of any kind** is out of scope and MUST NOT be reachable.

#### Honest verification

- **FR-042**: On completion, the feature MUST state per capability what was **exercised against the live
  cluster** versus what merely ran.
- **FR-043**: The server's silent-narrowing behaviour — currently **code inspection only** — MUST be
  **reproduced against the running server** or recorded as unverified.
- **FR-044**: Anything not exercised MUST be marked unverified or cut.

### Key Entities

- **Scope** — cluster-wide or a named namespace set, plus whether it was **confirmed**. A result without a
  confirmed scope is not an absence.
- **Resource query** — a kind, a scope, and any selector, all of which must be visible in the answer.
- **Absence** — a first-class outcome with distinguishable causes: no such namespace, empty namespace,
  selector matched nothing, permission insufficient, CRD not installed, cluster unreachable.
- **NetworkPolicy** — selectors, policy types and rules. **Its absence is permissive**, which is a property
  of the entity, not a footnote.
- **Service path** — Service → selector → pods → EndpointSlices → readiness, with each link either checked
  or explicitly not checked.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: NetworkPolicies for a real namespace are retrieved with selectors, types and rules.
- **SC-002**: A namespace with no policies produces an answer that **states all traffic is permitted**.
- **SC-003**: A restricted credential produces an answer stating scope could not be established — **not** a
  narrowed list presented as complete. Verified with a real restricted ServiceAccount.
- **SC-004**: A non-existent namespace, an empty namespace, and a non-matching selector produce **three
  different answers**, verified by wording.
- **SC-005**: Every answer states the scope actually queried.
- **SC-006**: A used selector appears in the answer.
- **SC-007**: Unreachable cluster, invalid credential and empty result are three distinguishable outcomes.
- **SC-008**: A missing CRD is reported as not-installed.
- **SC-009**: A Service with a selector matching no pods is reported as such, distinct from other
  no-endpoint causes.
- **SC-010**: Ready and not-ready endpoints are distinguished.
- **SC-011**: An Ingress backend naming a non-existent Service is called out.
- **SC-012**: A path trace states which links were not checked.
- **SC-013**: Pods list with namespace, node, phase and readiness; non-running pods appear with a reason.
- **SC-014**: A write is refused, and read-only is verifiably forced by NetClaw rather than inherited.
- **SC-015**: **Secrets are denied** — an attempt to read one fails, verified live.
- **SC-016**: No exposed tool can switch cluster context.
- **SC-017**: The kubeconfig and context in use are explicit in NetClaw's configuration.
- **SC-018**: The manifest measures ≤ 5,000 tokens, with the figure recorded.
- **SC-019**: `reconcile-mcp.py` exits 0; `verify-inventory-counts.py` exits 0 with updated counts;
  `trace-skill.py` resolves for every skill added.
- **SC-020**: `SOUL.md` gains a capability section covering the empty-list distinction and the permissive
  meaning of no-policy — not merely an incremented count.
- **SC-021**: The candidate table with **measured** tool counts and licences is recorded in a shipped
  artifact, along with why `rohitg00` and `Flux159` were rejected and that no official server exists.
- **SC-022**: The silent-narrowing behaviour is either **reproduced live** or recorded as unverified.
- **SC-023**: A per-capability verification table distinguishes **exercised against the live cluster** from
  **executed without error**.

## Assumptions

- **`containers/kubernetes-mcp-server` is the adoption target**, in a read-only, trimmed-toolset
  configuration measured at 7 tools / 2,301 tokens. Its Go static binary makes dependency conflict
  structurally impossible, which is why it is preferred over the Node and Python alternatives.
- **The kind cluster is the verification environment.** Kubernetes v1.35.0, two nodes, with namespaces,
  NetworkPolicies and a restricted ServiceAccount already created.
- **Read-only means read-only.** No write path is exposed in this feature, so no approval or change-record
  gate is designed. Adding one later would require a NetClaw-owned layer.
- **A dedicated read-only credential is the supported deployment**, not the operator's ambient kubeconfig.
- **No new persistent state.** The cluster holds everything.

## Out of Scope

- **Any cluster mutation** — apply, scale, patch, rollout, delete, exec, port-forward, Helm install. Not
  exposed, not gated, not reachable (FR-041).
- **Reading Secrets** — explicitly denied (FR-021).
- **Helm** — the adopted server's Helm toolset is not enabled.
- **Traffic observation** — `kubeshark-traffic` owns that. This shows declared configuration.
- **Metrics** — `prometheus`, `grafana`. This is the object model, not time series.
- **Building labs** — `containerlab`, `gns3`, `cml`.
- **CNI-specific tooling** (Cilium/Calico policy semantics, eBPF introspection) — a credible follow-on;
  generic CRD reads cover the objects, not the vendor semantics.
- **Multi-cluster** — one explicitly configured cluster. Context switching is deliberately unreachable.
- **Service-mesh** (Istio/Kiali) and **NetObserv** toolsets — real and on-roadmap for CNI health, but each
  costs manifest budget and needs its operator installed. Deferred.
