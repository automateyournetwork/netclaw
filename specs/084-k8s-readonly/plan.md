# Implementation Plan + Tasks: Kubernetes read-only coverage

**Branch**: `084-k8s-readonly` | **Date**: 2026-08-03 | **Spec**: [spec.md](./spec.md)
**Roadmap**: R14, Tier 3

> **Note on form.** Plan and tasks are combined in one document for this feature. Phase 0 research and
> clarification did an unusual amount of the design work *by measurement* — the tool count, the manifest
> size, the Secret denial and the silent-narrowing reproduction are all settled facts rather than open
> questions — so a separate tasks file would mostly restate them. Nothing is omitted; the task list is below
> with the same rigour, and traceability is verified mechanically at the end.

## Summary

`kubeshark-traffic` sees packets inside a cluster and cannot read a pod, service, ingress or NetworkPolicy.
This adds read-only Kubernetes API coverage.

**Adopt `containers/kubernetes-mcp-server`** — Red Hat's, **Apache-2.0** (licence-identical to NetClaw, so
none of R11's vendoring question), a **statically linked Go binary** (`not a dynamic executable`, verified)
so dependency conflict with the `fastmcp<3` pins is impossible by construction. Pinned at **v0.0.66**,
downloaded at install and verified against a NetClaw-recorded SHA-256.

**Measured live at 7 tools / 1,643 tokens** — 67% under the ceiling.

**The feature exists because the adopted server lies.** Given a credential without cluster-wide list
permission it converts the API's honest 403 into a one-namespace answer with no error and no caveat. That was
reproduced during clarification. Two layers answer it: a mandated cluster-wide-read ServiceAccount (removes
the trap at the root) *and* a skill-level preflight (catches a misconfigured deployment).

## Technical Context

**Language/Version**: none authored. A Go binary plus NetClaw-authored skills and tests (Python, stdlib).

**Dependencies**: **zero runtime dependencies.** Statically linked. This is the reason it was chosen over the
Node and Python candidates.

**Storage**: none. The cluster holds everything.

**Testing**: `tests/k8s/run-tests.sh` — static (config forces read-only? Secrets denied? skill has a
preflight procedure?) plus live against the kind cluster (does the narrowing reproduce? are the five
absences distinguishable?).

**Constraints**: manifest ≤ 5,000 (**measured 1,643**); strictly read-only; Secrets denied; explicit
kubeconfig; no context-switching tool.

## Constitution Check

| Principle | Status | How |
|---|---|---|
| **I. Safety-First** | ✅ | Strictly read-only; Secrets denied at two layers (server `denied_resources` **and** the ServiceAccount's RBAC — `can-i get secrets` → no, verified) |
| **II. Read-Before-Write** | ✅ n/a | No write exists |
| **III. ITSM-Gated Changes** | ✅ n/a | No changes to gate. Recorded as a scope decision |
| **IV. Immutable Audit Trail** | ⚠️ **partial, knowingly** | No per-call GAIT — a Go binary with no audit concept, and no platform-level MCP audit. Same inherited posture as R11, acceptable only because read-only. See Complexity Tracking |
| **V. MCP-Native** | ✅ | stdio |
| **VI. Multi-Vendor Neutrality** | ✅ | Kubernetes is the vendor-neutral layer |
| **VII. Skill Modularity** | ✅ | FR-038–041: boundaries against kubeshark, prometheus/grafana, lab builders |
| **VIII. Verify After Change** | ✅ | Live cluster; FR-042–044 require stating what was not exercised |
| **IX. Security by Default** | ✅ | Read-only forced, Secrets denied, explicit kubeconfig, no context switching |
| **X. Observability** | ✅ | FR-002: every answer states the scope actually queried |
| **XI. Artifact Coherence** | ✅ | FR-034–037 |
| **XII. Documentation-as-Code** | ✅ | spec, notes, plan, skills, server README, TOOLS.md, VERIFICATION.md |
| **XIII. Credential Safety** | ✅ | Token in a dedicated kubeconfig outside the repo; never in output |
| **XIV. External Comms** | ✅ | Reads only |
| **XV. Backwards Compatibility** | ✅ | **Structurally guaranteed** — a static binary touches no shared interpreter |
| **XVI. Spec-Driven** | ✅ | specify → clarify (4 Q) → plan/tasks → analyze → implement |
| **XVII. Blog** | ⏭️ waived | Standing operator decision |

## Complexity Tracking

| Deviation | Why | Alternative rejected because |
|---|---|---|
| **Principle IV partial** — no per-call GAIT | **Established by T007b, not assumed.** The binary *does* expose `--log-file` and `--log-level`, so it is not audit-free in the way spec 083's candidate was. But measured at level 4 the log contains **lifecycle only** — startup, config path, feature gates, session begin/end, watcher shutdown — and **no tool calls and no arguments**. So there is operational logging but no per-call audit trail, and no platform-level MCP audit either. | A NetClaw wrapper would add audit but reintroduce the code surface adoption avoids. Mitigated: strictly read-only, so there is no operation to record; `--log-file` is still worth enabling for operational forensics; any future write path must carry real audit and gates. *Whether log level 9 records calls is untested — recorded as unverified.* |
| **Distinctions partly guidance-level** | Same as R11 — no NetClaw code in the call path. | Unlike R11 this is **not** guidance alone: the mandated cluster-wide-read credential removes the trap mechanically. Guidance is the *second* layer, not the only one. That is a genuine improvement on R11's position. |
| **Trust-on-first-use checksum** | Upstream publishes **no** checksums — 15 release assets, zero `sha`/`checksum` files (verified). | Upstream attestation is unavailable. Recording our own SHA-256 still detects a re-tagged or altered asset, which is strictly better than nothing, and the limitation is stated rather than implied. |

## Tasks

### Phase 1 — Vendor the binary and isolate (BLOCKING)

- [X] T001 Create `mcp-servers/k8s-mcp/` with `NOTICE.md` recording upstream, **Apache-2.0**, pinned **v0.0.66**, and that NetClaw does not modify it
- [X] T002 Record the pinned SHA-256 `692a7b283a96140311fd46f13b8373657b2e9bfe660a36bb6434e8c42d899dbc` in a `CHECKSUMS` file, with a comment stating **upstream publishes no checksums** so this is trust-on-first-use, not attestation (FR-027)
- [X] T003 Create `mcp-servers/k8s-mcp/config.toml`: `read_only = true`, `toolsets = ["core"]`, the six `disabled_tools`, and the `denied_resources` Secret block (FR-019, FR-020, FR-021)
- [X] T004 `.gitignore`: negate `mcp-servers/k8s-mcp/` but **re-ignore the downloaded binary** — it is 75 MB and must never be committed. Prove with `git check-ignore`
- [X] T005 Add `component_install_k8s()` to `scripts/lib/install-steps.sh`: download the pinned release, **verify the SHA-256 and refuse to install on mismatch**, `chmod +x`. Never bare `pip`/`python3 -m venv` (FR-031)
- [X] T006 Register `k8s-mcp` in `config/openclaw.json` pointing at the binary with `--config` and an explicit `--kubeconfig` from `${K8S_KUBECONFIG}` (FR-022)
- [X] T007 Verify no context-switching tool is exposed — the 7-tool surface contains none (FR-024, SC-016)
- [X] T007a Record that the server was **tested against a live cluster before adoption** (done in clarification: 7 tools, 1,643 tokens, Secret denied, narrowing reproduced) rather than after (FR-028)
- [X] T007b **Establish** whether the binary has any audit concept — `strings`/`--help` for audit/log flags — and record the finding rather than assuming it. Complexity Tracking asserts there is none; this proves it (FR-033)
- [X] T007c Record that the static Go binary is *why* no shared dependency version can move, as the reason it was chosen (FR-032)

### Phase 2 — The read-only ServiceAccount (BLOCKING, this is layer 1)

- [X] T008 Document and script a **dedicated cluster-wide-read ServiceAccount**: ClusterRole with `get,list,watch` on pods, services, ingresses, networkpolicies, endpointslices, namespaces, events — and **no secrets** (FR-025)
- [X] T009 Document generating a token-only kubeconfig from it, and **why it must be token-only**: a kubeconfig carrying a client certificate silently overrides `--token`, which invalidated the first attempt at this feature's central test
- [X] T010 State in the docs that this credential is what makes the narrowing trap unreachable — `canIUse` returns true, so the branch never executes (verified)

### Phase 3 — US1 skill: NetworkPolicy review (P1) 🎯 MVP

- [X] T011 [P] Create `workspace/skills/k8s-network-policy/SKILL.md` with the standard frontmatter
- [X] T012 Write the **preflight procedure** as numbered steps: confirm cluster-wide list permission *before* trusting any empty result (FR-001, FR-003)
- [X] T013 State the headline rule: **no NetworkPolicy means all traffic is permitted** — an absence is permissive, and reporting it neutrally invites the opposite conclusion (FR-008, SC-002)
- [X] T013a Require policy answers to carry **pod selectors, policy types and rules** — enough to reason about what is permitted, not merely that a policy exists (FR-009, SC-001)
- [X] T014 Require every answer to state the **scope actually queried** (FR-002, SC-005)
- [X] T014a Require the **cluster actually connected to** to be surfaced wherever it affects interpretation — an operator with several clusters must never have to guess which one an answer describes (FR-023)
- [X] T015 Write the **six absences** as a lookup table: no such namespace · empty namespace · selector matched nothing · permission insufficient · CRD not installed · cluster unreachable (FR-004, FR-005, FR-006, FR-007, SC-004)
- [X] T016 Require the **selector used** to appear in the answer so a typo is visible (FR-005, SC-006)
- [X] T017 State that a policy answer is not a complete picture unless cluster-wide scope was confirmed — other namespaces and cluster-scoped CRD policies also apply (FR-010)
- [X] T018 State **"traffic was observed" ≠ "traffic is permitted"** and the `kubeshark` boundary (FR-011, FR-038)

### Phase 4 — US2 skill: service path tracing (P1)

- [X] T019 [P] Create `workspace/skills/k8s-service-path/SKILL.md`
- [X] T020 Document the path: Service → selector → pods → EndpointSlices → readiness, and require each link to be marked **checked or not checked** (FR-012, FR-016, SC-012)
- [X] T021 Require **"the selector matches no pods"** as a distinct diagnosis from "no endpoints" (FR-013, SC-009)
- [X] T022 Require ready vs not-ready endpoints to be distinguished (FR-014, SC-010)
- [X] T023 Require an Ingress backend naming a non-existent Service to be called out (FR-015, SC-011)

### Phase 5 — US3 skill: workload inventory (P2)

- [X] T024 [P] Create `workspace/skills/k8s-workload-inventory/SKILL.md`
- [X] T025 Require namespace, node, phase and readiness; **non-running pods reported with a reason, never omitted** (FR-017, FR-018, SC-013)
- [X] T026 Require the answer to state whether it covered all namespaces or one (FR-002)
- [X] T027 Add all boundaries to all three skills (FR-038, FR-039, FR-040) and state read-only + no-mutation (FR-041)

### Phase 6 — Tests

- [X] T028 [P] `tests/k8s/_harness.py` following `tests/zabbix/_harness.py`
- [X] T029 [P] `tests/k8s/test_config_forced.py` — static: read-only forced in NetClaw's config; Secret denial present; six `disabled_tools`; deny-list non-vacuous; kubeconfig explicit not ambient (FR-019–022, SC-014, SC-017)
- [X] T030 [P] `tests/k8s/test_skill_procedure.py` — static: each skill has a numbered preflight; the no-policy-means-permitted rule; six absences; five boundaries; no unqualified absence claims (FR-006a-equivalents, SC-020)
- [X] T031 [P] `tests/k8s/test_live_k8s.py` — **live**: reproduce the narrowing side by side (restricted credential vs raw kubectl); prove the cluster-wide-read SA avoids it; Secret denial; non-existent vs empty namespace; typo'd selector; missing CRD; a real NetworkPolicy read with selectors/types/rules; a Service whose selector matches nothing; ready vs not-ready endpoints (SC-001, SC-002, SC-003, SC-004, SC-007, SC-008, SC-009, SC-010, SC-015, SC-022)
- [X] T032 [P] `tests/k8s/test_manifest_size.py` — manifest ≤ 5,000 and **exactly 7 tools**, so an upstream bump that inflates the surface fails loudly (FR-037, SC-018)
- [X] T033 `tests/k8s/run-tests.sh` wiring all four, static-only without a cluster

### Phase 7 — Artifact coherence

- [X] T034 `catalog.sh` entry + `PROFILE_OBSERVABILITY` membership (FR-034)
- [X] T035 **Both** HUD entries in `ui/netclaw-visual/server.js`
- [X] T036 `.env.example` block: `K8S_MCP_CMD`, `K8S_KUBECONFIG`, with the read-only-SA rationale
- [X] T037 `TOOLS.md` section: measured 1,643 tokens, the narrowing finding, the two layers, five boundaries
- [X] T038 `mcp-servers/k8s-mcp/README.md` — NetClaw-authored, with the **measured candidate table** and why `rohitg00` and `Flux159` were rejected, and that no official server exists (FR-026, FR-029, FR-030, SC-021)
- [X] T039 `SOUL.md` capability section — the empty-list distinction, no-policy-is-permissive, reachable≠permitted (SC-020) + both count sites
- [X] T040 `README.md` MCP table row, skill rows, four count sites → **157 / 215**
- [X] T041 `docs/COVERAGE-ROADMAP.md` — R14 status, the measured candidate table, and the CNI-specific follow-on note

### Phase 8 — Honest verification

- [X] T042 `bash tests/k8s/run-tests.sh` passes
- [X] T043 `reconcile-mcp.py` exit 0; `verify-inventory-counts.py` exit 0; `trace-skill.py` × 3 (FR-035, FR-036, SC-019)
- [X] T044 Regression: document, zabbix, bgp-intel, fortinet, reconcile suites still pass
- [X] T045 `VERIFICATION.md` — per-capability exercised-vs-executed table (FR-042, SC-023)
- [X] T046 In `VERIFICATION.md`: record that **FR-043's narrowing was reproduced**, with the side-by-side output (SC-022)
- [X] T047 In `VERIFICATION.md`: record the no-per-call-GAIT limitation, the trust-on-first-use checksum limitation, and the iN2N decision
- [X] T048 In `VERIFICATION.md`: state anything unverified or cut (FR-044)
- [X] T049 Secret-scan the diff; confirm no token or kubeconfig content committed
- [X] T050 GAIT session log

## Dependencies

```
Phase 1 (vendor) ─┬─▶ Phase 2 (read-only SA) ── BLOCKING ──┬─▶ Phase 3 (US1) 🎯
                  │                                        ├─▶ Phase 4 (US2)
                  │                                        └─▶ Phase 5 (US3)
                  └─────────────────────────────────────────────▶ Phase 6 (tests)
                                                                      │
                                                          Phase 7 (artifacts)
                                                                      │
                                                          Phase 8 (verification)
```

**MVP** = Phases 1–3. US1 is the security-relevant capability and the reason R14 exists.

## Analyze remediation (2026-08-03)

Traceability was 16 keys short on first pass. Three were genuine gaps, not just missing tags:

| Gap | Fix |
|---|---|
| **FR-028** — test before adopting | Satisfied in clarification but nothing recorded it. T007a |
| **FR-033** — determine whether audit exists | Complexity Tracking *asserted* there is none; nothing *established* it. T007b now proves it rather than assuming |
| **FR-023** — surface which cluster answered | No skill task required it. T014a. An operator with several clusters must never guess which one an answer describes |

The other 13 were covered by inference and are now tagged. **Post-remediation: 44 FRs, 23 SCs, 55 tasks,
zero untagged, zero dangling.**

**Next**: implement.
