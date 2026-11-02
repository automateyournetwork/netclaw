# Tasks: R02 execution parity

Roadmap R02; implementation may begin only after analysis has no CRITICAL/HIGH
finding. Every live claim needs actual evidence; fixture checks alone do not
complete acceptance. Shared contracts are authoritative. No release/version bump.

## Phase 1 — Specification and independent architecture

- [x] T001 Record owner scope, budget, parallel-team decision and loop cap in specs/171-execution-parity/spec.md and resume.md.
- [x] T002 Audit reusable and missing controls into specs/171-execution-parity/research.md and contracts/execution.md.
- [x] T003 Define owner UI, signed wire and durable state in specs/171-execution-parity/contracts/ and data-model.md.
- [x] T004 Independently analyze spec/plan/tasks/contracts and resolve all CRITICAL/HIGH findings in specs/171-execution-parity/analysis.md before implementation.

## Phase 2 — Foundations

- [x] T005 Implement strict canonical signed approval/result/ACK schemas and pinned-key validation in mcp-servers/protocol-mcp/bgp/federation/protected_contract.py.
- [x] T006 Implement additive SQLite ledger, atomic claims and retained spent authority in mcp-servers/protocol-mcp/bgp/federation/protected_store.py.
- [x] T007 Add enrollment generations and attested Border authority bindings in mcp-servers/protocol-mcp/bgp/federation/risk.py and service.py without reenrolling existing members.
- [x] T008 Implement private one-use owner tickets/session authority and native CLI in mcp-servers/protocol-mcp/bgp/federation/protected_owner.py and scripts/protected-owner.py.
- [x] T009 Define fixed authenticated private bridge and opt-in lifecycle in mcp-servers/protocol-mcp/bgp/federation/protected_service.py and service.py.
- [x] T010 [P] Add independent canonical/signature and separate-process atomic-claim tests in tests/n2n/test_protected_contract_171.py and test_protected_claims_171.py.

## Phase 3 — US1 exact owner-approved read

- [x] T011 [US1] Freeze catalog, candidate idempotency, review and exact signed decisions in mcp-servers/protocol-mcp/bgp/federation/protected_service.py.
- [x] T012 [US1] Add authenticated protected submit and stable operation lookup over existing iN2N in mcp-servers/protocol-mcp/bgp/federation/service.py.
- [x] T013 [P] [US1] Implement strict owner Origin/CSRF/cookie routes and fixed bridge client in ui/netclaw-visual/src/hud-server/protected-operations.js and protected-client.js.
- [x] T014 [P] [US1] Add OwnerSessionGate and ApprovedOperationsView in ui/netclaw-visual/src/dashboard/ with capability-gated server.js/Dashboard.jsx wiring.
- [x] T015 [P] [US1] Test approval tamper/expiry/replay/principal and owner-session/origin/CSRF refusals in tests/n2n/test_protected_approvals_171.py and HUD protected-operations.test.js.

## Phase 4 — US2 guarded credential-owning execution

- [x] T016 [US2] Implement trusted executor/effect-gate adapter and refusal of every legacy execution bypass for protected members in protected_runtime.py and service.py.
- [x] T017 [US2] Add operation-scoped inference facade with pinned routing and durable two-call limit in scripts/protected-inference.py and protected_runtime.py, with SDK retry deduplication in scripts/lib/protected_provider.py.
- [x] T018 [US2] Add exact approved MCP broker forwarding and execute-once/parse-captured-output pyATS adapter in scripts/protected-tool-broker.py and scripts/lib/protected_pyats.py. Pass2 corrected implicit native discovery; fresh full transcripts independently show only the approved command.
- [x] T019 [US2] Prepare pinned official OpenClaw and Hermes runtimes with DefenseClaw in fresh Docker topologies and honest containment verification in specs/171-execution-parity/qualification/ and protected_docker.py.
- [x] T020 [P] [US2] Add runtime/argument/profile/bypass tests in tests/n2n/test_protected_runtime_171.py; no test may fake live production posture as acceptance.

## Phase 5 — US3 durable result and no-replay recovery

- [x] T021 [US3] Persist executor/effect claims before their effects and preserve uncertainty on timeout/cancel/restart in protected_store.py and protected_service.py.
- [x] T022 [US3] Sign member receipts, verify bindings and atomically persist Border receipt/ACK before completion in protected_contract.py and protected_service.py.
- [x] T023 [US3] Implement authenticated operation reconciliation and idempotent ACK delivery without submit replay in protected_service.py and service.py.
- [x] T024 [P] [US3] Add independently owned crash/lost-ACK/conflicting-result/retention tests in tests/n2n/test_protected_recovery_171.py.
- [x] T025 [P] [US3] Add browser refresh/uncertain decision/reconcile behavior and tests in ui/netclaw-visual/src/dashboard/ApprovedOperationsView.jsx and its test harness.

## Phase 6 — US4 attributable audit

- [x] T026 [US4] Extend existing GAIT with structured principal/correlation and process-safe required protected emission in mcp-servers/protocol-mcp/bgp/federation/gait.py and audit.py.
- [x] T027 [US4] Enforce required pre-boundary audit and post-effect pending-audit recovery in protected_service.py.
- [x] T028 [P] [US4] Test unavailable/concurrent audit and principal attribution in tests/n2n/test_protected_audit_171.py.

## Phase 7 — US5 integration and actual qualification

- [x] T029 [US5] Integrate separate worker commits and review shared boundaries; record bounded implementation passes in specs/171-execution-parity/verification.md.
- [x] T030 [US5] Prepare exact fresh local activation/verification packet with pins, homes, model limits, baseline, device scope, preservation and stop procedure in specs/171-execution-parity/runtime-review.md.
- [x] T031 [US5] Verify actual fresh runtime containment/guard readiness and credential absence, preserving private receipts and sanitized specs/171-execution-parity/verification.md.
- [x] T032 [US5] Execute actual browser-approved pyATS show version for both OpenClaw and Hermes, with principal/approval/attempt/tool/result/ACK/GAIT correlation and independently checked parsed output in specs/171-execution-parity/verification.md.
- [x] T033 [US5] Run actual approved refusal/bypass and lost-ACK recovery drills with one real show effect; record evidence in specs/171-execution-parity/verification.md.
- [x] T034 [US5] Verify existing relevant federation/HUD/installer contracts, HUD build and platform limits in specs/171-execution-parity/verification.md.
- [x] T035 [US5] Independent final security/evidence review and required fixes in specs/171-execution-parity/analysis.md; no self-certified fixture-only completion.
- [ ] T036 [US5] Complete parity matrix and human R02 evidence gate in specs/171-execution-parity/verification.md before R03 begins.

## Dependencies and parallel work

T001–T004 precede all implementation. T005–T009 freeze foundations; HUD T013–T014
and independent tests T010/T015 can proceed in separate worktrees once the shared
contracts are agreed. Backend owns protocol/service/risk/gait/owner CLI; HUD owns
Node/React; coordinator owns runtime/facade/tool broker/pyATS adapter/qualification;
verifier owns new independent test files and review. No concurrent edits to another
owner's files. T016–T023 require shared foundations; UI can use explicit fixtures
while backend integrates, never label these as live results. T029 integrates before
T030–T033 actual qualification. T034–T036 conclude R02; R03 requires human review.

## Requirement coverage

FR001:T008,T011,T013,T026; FR002:T011,T014,T015; FR003:T005,T007,T011,T015;
FR004:T006,T010,T015,T021; FR005:T016,T018,T020; FR006:T017,T018,T019,T031;
FR007:T016,T017,T019,T020,T033; FR008:T021,T024; FR009:T005,T022,T024;
FR010:T023,T024,T025,T033; FR011:T026,T027,T028; FR012:T030,T032,T033;
FR013:T008,T009,T013,T015; FR014:T002,T035,T036; FR015:T007,T019,T034;
FR016:T001,T030,T036. SC001–SC007:T031–T036 plus independent tests above.

Maximum five optional implementation/test/review passes across R02–R05, not five
per agent. Zero used before implementation. Passing the cap is not completion;
never silently replay unknown live operations to improve a test result.
