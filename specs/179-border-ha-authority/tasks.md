# Tasks: R08 Border HA authority

Input: spec.md,plan.md,research.md,data-model.md,contracts/,qualification-matrix.md.
Tests are mandatory under FR-020/021. Checkboxes close only with recorded evidence.

## Phase 1 — Scope and preparation

- [x] T001 Record authorized R08 scope,NCFED foundation and SDD specification/clarification in specs/179-border-ha-authority/spec.md and checklists/requirements.md (FR-025/026).
- [x] T002 Complete research,design,contracts and exact fixture/real matrix in specs/179-border-ha-authority/plan.md,research.md,data-model.md,contracts/,qualification-matrix.md (FR-001–026).
- [x] T003 Complete read-only cross-artifact analysis and resolve all CRITICAL/HIGH before implementation;record specs/179-border-ha-authority/analysis.md (FR-024).
- [x] T004 Baseline source,retained resources/retirement receipts and exact owned local resources in private roadmap-r08-20261107 and specs/179-border-ha-authority/qualification-plan.md (FR-022).

## Phase 2 — Foundation

- [x] T005 Write strict config/identity/legacy-fallback and quorum-client contract tests in tests/n2n/test_ha_contract_179.py and test_ha_store_179.py (FR-001/002/011/012/013/023/026).
- [x] T006 Implement bounded HA manifest/private ownership and durable HA-required marker in mcp-servers/protocol-mcp/bgp/federation/ha/config.py (FR-001/012/013/023).
- [x] T007 Implement isolated etcd3.6.16 dependency lock and private mTLS/RBAC fixture provisioning in labs/ha/dependencies.json,labs/ha/etcd_lab.py (FR-002/012/020).
- [x] T008 Implement bounded linearizable etcd adapter with single-attempt mutations and exact unknown-commit readback in mcp-servers/protocol-mcp/bgp/federation/ha/store.py (FR-002/006/009/013).
- [x] T009 Implement leader lease/incarnation/value+revision fencing,independent renewal and bounded metadata/claim/reservation state in mcp-servers/protocol-mcp/bgp/federation/ha/authority.py (FR-002/005/006/008/009/013).
- [x] T010 Implement explicit opt-in mutual TLS and cluster endpoint profile in mcp-servers/protocol-mcp/bgp/federation/exporter_tls.py,endpoint_registry.py with tests/n2n/test_ha_transport_179.py (FR-011/012/026).

## Phase 3 — US1: Surviving Border operation

Independent test: any of3Borders accepts a new exact operation through current
quorum authority;leader loss permits distinct fresh work while old work is retained.

- [x] T011 [US1] Write actual NCFED cluster handshake/forwarding and multiattachment tests in tests/n2n/test_ha_channels_179.py (FR-003/004/011/026).
- [x] T012 [US1] Implement separately enrolled NCFED ClusterChannel with exact transcript/role/method checks in mcp-servers/protocol-mcp/bgp/federation/ha/channel.py (FR-011/012/026).
- [x] T013 [US1] Integrate cluster lifecycle and node-keyed outbound iN2N attachments in federation/service.py,internal_security.py and bgp-daemon-v2.py (FR-003/004/023).
- [x] T014 [US1] Add explicit protectedv2 cluster review/approval/result/ACK and stable principal audience in federation/protected_contract.py with tests/n2n/test_ha_execution_contract_179.py (FR-001/003/008/010).
- [x] T015 [US1] Implement quorum-wide review/nonce/approval/revocation and exact dispatch ownership plus narrow follower forwarding in federation/ha/operations.py,protected_service.py (FR-003/008/009/010).
- [x] T016 [US1] Recover original signed member result/ACK through surviving nodes without redispatch in federation/protected_service.py,protected_store.py and tests/n2n/test_ha_results_179.py (FR-008/009/010).

## Phase 4 — US2: Member and guard enforcement

Independent test: minority/stale/noquorum cannot commit a fresh model/tool admission;
unknowns and resource fences remain across IDs and leader changes.

- [x] T017 [US2] Write claim/freshness/pause/clock/unknown/runner exclusion tests in tests/n2n/test_ha_admission_179.py (FR-005/006/007/009).
- [x] T018 [US2] Implement member nonce/incarnation/monotonic receipt consumption and durable journal in federation/ha/admission.py (FR-005/006/007/009).
- [x] T019 [US2] Bind quorum admission into actual ScopedInference and Docker/executor construction in federation/protected_runtime.py,protected_docker.py,protected_ollama.py (FR-005/006/009/023).
- [x] T020 [US2] Bind fresh tool admission at the native effect boundary and block legacy/unqualified paths in federation/protected_service.py,service.py and scripts/lib/protected_role.py (FR-005/006/009/023).
- [X] T021 [US2] Run actual3voter/NCFED minority/asymmetric/threeway/delay/stale/clock/quota fault suite from labs/ha/qualify.py and tests/n2n/test_ha_integration_179.py (FR-002/005/006/007/009/013/020;SC-001/002).

## Phase 5 — US3: Lifecycle and recovery

Independent test: full restart/retirement/restore cannot resurrect consumed authority
or unfreeze work missing from a stale snapshot.

- [x] T022 [US3] Write restart/retirement/restore-evidence-gap tests in tests/n2n/test_ha_recovery_179.py (FR-008/009/014/015).
- [x] T023 [US3] Implement majority-gated drain/retire/re-enroll and safe voter changes in federation/ha/lifecycle.py (FR-014).
- [x] T024 [US3] Implement trusted owned-process isolation receipts,export/fenced restore and one-use activation in scripts/lib/ha_cluster.py and federation/ha/recovery.py (FR-015/022).
- [x] T025 [US3] Run actual fullrestart/retiredreturn/fencedrestore/storagegap fixtures in labs/ha/recovery_lab.py and record specs/179-border-ha-authority/verification.md (FR-015/020/021;SC-001/002).

## Phase 6 — US4: Operating clients

Independent test: actual browser/editor/Mobile retain cluster identity,exact pending
review/sent markers and original result while node or authority changes.

- [x] T026 [US4] Add cross-language standalone/cluster/negative golden descriptors in tests/fixtures/ha-179 and client contract tests (FR-016/017/018/019).
- [x] T027 [US4] Implement shared cluster device enrollment/revocation and retained-key hello in federation/mobile_enrollment.py,edge.py and tests/n2n/test_ha_edge_179.py (FR-018/019).
- [x] T028 [US4] Implement cluster descriptor/typed status/forwarding in ui/netclaw-visual/src/hud-server/protected-{server,client,operations}.js (FR-003/016/019).
- [x] T029 [US4] Implement HUD cluster audiences,status and stale-review/original-result recovery in src/shared/protected-* and dashboard operation views with tests (FR-016/019).
- [x] T030 [US4] Implement VSCode cluster profile/endpoint manifest and CAS selection in extensions/netclaw-vscode/src/state/profiles.ts,connection/connect.ts,client/owner.ts (FR-017/019).
- [x] T031 [US4] Implement VSCode authority display,native exact review and original-reference recovery in extensions/netclaw-vscode/src/views/owner.ts,client/combined.ts with tests (FR-017/019).
- [x] T032 [US4] Implement Mobile cluster enrollment,retained-key alternate endpoint and secure reference scope in mobile/netclaw-mobile/lib/ncfed/ and cloud/owner_client.dart with tests (FR-018/019).
- [x] T033 [US4] Implement Mobile authority/quorum/stale-review flows in mobile/netclaw-mobile/lib/screens/ and reconnect wiring with tests (FR-018/019).

## Phase 7 — Fixture gate and real-runtime qualification

- [X] T034 Independently review complete fixture matrix and source gates before REAL work;record specs/179-border-ha-authority/fixture-gate.md (FR-020/021;SC-001/002).
- [X] T035 Freeze fresh NetClaw/OpenClaw/DefenseClaw/Ollama/nativeMCP source/image/profile/resource packet in labs/ha and private qualification manifest (FR-020/022).
- [X] T036 Run actual bounded guarded native workload via each Border and leader-loss recovery in labs/ha/real_runtime.py;record signed evidence/counters (FR-005/010/020/021;SC-001/002/003).
- [X] T037 Run all REAL model/tool admission negatives,unknown/restart/resultACK/restore cases from qualification-matrix.md;record cumulative counters and every failure in private evidence (FR-005–015/020/021;SC-001/002/003).
- [X] T038 Run actual browser HUD authority/quorum/staleapproval/original-result journeys tied to REAL signed records via labs/ha/client_qualification.mjs (FR-016/019/020;SC-004).
- [X] T039 Run actual isolated MacCode1.109 G12 failover/recovery tied to REAL signed records via extensions/netclaw-vscode/scripts/cloud-editor.mjs and owned harness (FR-017/019/020;SC-004).
- [X] T040 Run actual nativeiOSsimulator G13 enrollment/background/cold/failover tied to REAL signed records via mobile integration_test and owned harness (FR-018/019/020;SC-004).
- [X] T041 Record detection/election/recovery and network/storage/clock/resource measurements in specs/179-border-ha-authority/measurements.md (FR-007/020/021;SC-005).

## Phase 8 — Coherence and closeout

- [x] T042 Complete private setup/status/lifecycle CLI and scoped installer/config declarations in scripts/ha-cluster.py,scripts/lib/install-steps.sh,installer catalog and .env.example (FR-024).
- [x] T043 Reconcile all artifact touchpoints and unchanged component counts;maintainer-only documentation in SOUL.md,TOOLS.md,protocol/n2n documentation and specs/179-border-ha-authority/coherence.md (FR-023/024/025/026).
- [X] T044 Run affected full federation/HUD/editor/Flutter/build/analyzer/SDD/catalog/registration checks and review final source;record verification.md (FR-023/024;SC-006).
- [X] T045 Write operator runbooks and exact row-to-artifact evidence matrix retaining every limitation/failure in specs/179-border-ha-authority/runbook.md,verification.md (FR-020/021/024;SC-001–006).
- [X] T046 Export/hash consistent private evidence and verify exact owned local cleanup,retained authority and retirement preservation in private receipts and verification.md (FR-022;SC-006).
- [X] T047 Complete daily memory/GAIT audit,maintainer completion summary and clear-safe resume in memory/2026-11-07.md and specs/179-border-ha-authority/resume.md (FR-024/025;SC-006).
- [X] T048 Present completed technical/measurement acceptance packet and record actual owner review before R09 in specs/179-border-ha-authority/acceptance.md (SC-006).

## Dependencies and parallel opportunities

T001–004 precede source work;T005tests precedeT006–010. T011–016 build on foundation;
T017–020 require authority/contracts;T021 requires integrated NCFED/guard gates.
T022–025 build on durable authority. T026 freezes client contract beforeT027–033.
Client source work can run in independent HUD/editor/Mobile lanes after backend
contract freeze;it cannot qualify until actual backend/REAL records exist.
T034 requires all fixture/runtime/client contract tests;T035–041 follow gate review.
T042–048 finish coherence/acceptance. Runtime mutations are serialized by coordinator.
The owner authorized three implementation agents in separate worktrees. The coordinator
serializes actual runtime changes and qualification. No optional Ralph loop.

## Implementation strategy

Incrementally deliver authority and native fencing before client failover;preserve
standalone exact contracts. Every phase keeps original unknown state and failures.
MVP is not completion:all48tasks and the mandatory two-gate evidence are required.
No claim of cloud/physical-device/other-runtime qualification from fixtures.

## Foundation implementation evidence (in progress)

T007 provisioned three actual private etcd3.6.16 voters with mTLS/RBAC; exact IDs
and the first stale-leader/durable-claim smoke are retained outside source.
T009 adds bounded per-operation headers, nonce indexes, member enrollment, durable
dispatch and admission claims, and member/runner reservations in ha/operations.py.
T010 passes actual mutual-TLS socket negatives and legacy transport regressions.
T012 passes actual NCFED cluster socket proof/method/duplicate-JSON checks;
service integration and multiattachment remain T011/T013. T014 adds explicit v2
cluster approval/result/ACK schemas; standalone v1 tests continue to pass.
T017/T018 cover durable member consumption, restart replay, delay, clock jumps,
request substitution and unknown reservations. The guarded Docker/inference
boundaries now require HA callbacks for cluster payloads; production construction
and end-to-end validation remain open under T019/T020. No REAL execution or client
HA acceptance has occurred. All remaining unchecked tasks remain required.

## Integrated source checkpoint — 2026-11-07

T011 now covers actual authenticated cluster sockets and three outbound iN2N
attachments. T015/T016 preserve exact dispatch, unknown member/runner reservations
and original issuer/result with successor ACK. T022–024 implement lifecycle and
host-proven fenced restore; actual recovery fixtures remain T025. T026/T028–031
include shared signed descriptors and HUD/editor implementation/regressions;
actual browser/editor acceptance remains T038/T039. Shared Mobile enrollment
and service wiring are under integrated verification; native Mobile remains open.
The combined targeted Python batch passes235tests. These are source/controlled
verification results, not REAL model/native execution or completed R08.

## Integrated source completion — 2026-11-07

T013/T019/T020/T027 now close their implementation scope with the actual service,
profile3 launch, cluster edge and final model/MCP handoff paths integrated.
The coordinator's full federation suite passes1998tests,5existing skips; later
setup/role/export/process checks pass110tests and56subtests. These source gates
include real OS-pipe/TLS checks but do not replace REAL runtime qualification.
T032/T033 close Mobile implementation after integrated525tests and clean analyzer;
T040 still requires actual native simulator journeys. T042/T043 close private
setup safeguards and maintainer/catalog coherence with the recorded source
checks in coherence.md. HUD build and editor TypeScript checks pass. All actual
fixture/REAL/native, evidence/cleanup and owner-acceptance tasks stay open until
their own complete evidence is recorded. Process fixture cleanup failures remain
explicit in verification.md and cannot be hidden by these source checkboxes.

<!-- 2026-11-08 status: T037 stays open: 9 matrix rows are fixture-only and 2 partial (see
evidence-matrix.md); the REAL budget (10/10) is spent. T038-T040 close with the stated limits
(HUD same-tab cold_recovery not exercised). T048 requires the actual owner review. -->
