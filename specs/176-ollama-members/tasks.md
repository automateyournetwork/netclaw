# Tasks: R05 guarded Ollama members

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/).  
**Status**: 26/33 implementation/acceptance tasks complete. SDD preparation is separate.

Tests are required by this feature's acceptance criteria. Port Thermidor's named
behavioral cases first; use actual native runtime evidence for live claims.
Paths below are repository-relative unless explicitly identified as the sibling.

## Phase 1: Reference and shared foundation

- [x] T001 Verify `specs/176-ollama-members/thermidor-reference.json` against the sibling checkout, record adopted source/notices and final-only lessons in `research.md`; exclude dirty HA changes (FR-014).
- [x] T002 Implement immutable local/cloud model profiles and unchanged historical hosted-profile validation in `mcp-servers/protocol-mcp/bgp/federation/protected_ollama.py` with `tests/n2n/test_protected_ollama_176.py`; port profile/latch cases (FR-001, FR-003, FR-006, FR-012).
- [x] T003 Verify selected DefenseClaw capability and implement narrow keyless Ollama admission/fencing in `scripts/lib/protected_ollama.py` and `scripts/protected-guard.py`, including a member/runner-wide busy/uncertain latch that blocks fresh operation IDs, with strict native-route/prompt/header/unknown tests in `tests/n2n/test_protected_ollama_guard_176.py` (FR-005, FR-007).
- [x] T004 Add profile-specific runtime/source bindings, calculator-v4 adaptation and actual container limits in `mcp-servers/protocol-mcp/bgp/federation/protected_docker.py` and `scripts/lib/protected_role.py`; preserve `scripts/lib/protected_provider.py` hosted behavior (FR-003, FR-005, FR-006, FR-012).

## Phase 2: US1 — combined correctly verified calculations (P1)

**Independent test**: prepared parent does no work; two exact approvals produce
two independently correct native-MCP results, each2 inference/1 tool call.

- [x] T005 [US1] Port independent arithmetic/boundary/large-count and compact-result tests to `tests/n2n/test_protected_calculator_176.py`, including actual native-tool schema/result fixtures and refusal of model-only arithmetic (FR-004).
- [x] T006 [US1] Qualify/pin corrected native subnet source or implement `scripts/patches/subnet-calculator-bounded.patch` with `scripts/lib/install-steps.sh` integration, fixing full enumeration, boundary arithmetic and IPv6 in the existing MCP; add explicit summary profiles and actual tool discovery/binding in `mcp-servers/protocol-mcp/bgp/federation/protected_contract.py`, `protected_mcp.py` and `scripts/protected-mcp-profile.py`; preserve old R04 constraints (FR-001, FR-003, FR-004, FR-012).
- [x] T007 [US1] Implement bounded independent result verification in `mcp-servers/protocol-mcp/bgp/federation/protected_calculator.py` and one-text-block delivery in `protected_docker.py`; retain native evidence and actual two-turn wire checks (FR-004).
- [x] T008 [US1] Port Thermidor parent/child approval, changed-authority, duplicate-family and no-dispatch-on-prepare tests into `tests/n2n/test_protected_combined_176.py` (FR-002, FR-003).
- [x] T009 [US1] Add atomic stable parent/child associations and cancellation to `mcp-servers/protocol-mcp/bgp/federation/protected_store.py` and `protected_calculator.py`, reusing existing child authority/expiry without approval-all (FR-002, FR-003, FR-008).
- [x] T010 [US1] Add the combined capability/HTTP and device-WSS allowlisted routes in `mcp-servers/protocol-mcp/bgp/federation/protected_owner.py`, `protected_device.py` and `ui/netclaw-visual/src/hud-server/protected-operations.js` with route-boundary tests (FR-002, FR-010, FR-011, FR-015).
- [x] T011 [US1] Implement exact two-child HUD review, individual decisions and authoritative results in `ui/netclaw-visual/src/dashboard/ApprovedOperationsView.jsx`, with `src/dashboard/protected-operations.test.js` coverage (FR-010).

## Phase 3: US2 — confinement and bounded accounting (P1)

**Independent test**: guard positive control works; all other model access fails;
actual runtime limits and positive usage are observed on both architectures.

- [x] T012 [P] [US2] Port five-role, model-worker exclusion, swap-disabled capacity and component-collision cases to `tests/n2n/test_protected_ollama_deployment_176.py` (FR-005, FR-006).
- [x] T013 [US2] Add reviewed pinned model lock, native guard/UID/worker/readiness probes and profile lifecycle in `labs/ollama/model-lock.json`, `labs/ollama/qualify.py` and `labs/ollama/README.md`; keep MCP/model APIs private (FR-005, FR-006, FR-014).
- [x] T014 [US2] Bind real time/tokens/CPU/memory, zero provider charge, signed result and durable ACK evidence in `mcp-servers/protocol-mcp/bgp/federation/protected_runtime.py` and `protected_docker.py`, with accounting assertions in `tests/n2n/test_protected_ollama_176.py` (FR-009).
- [x] T015 [US2] Prepare an exact owned runtime/resource, headroom/cost, expiry, baseline/rollback and retained-delivery packet in `labs/ollama/README.md` plus private artifacts referenced from `specs/176-ollama-members/verification.md`; resolve existing execution review before activation (FR-006, FR-013, FR-015).

## Phase 4: US3 — one-child failures and no-repeat recovery (P1)

**Independent test**: one completed child survives sibling uncertainty, cancellation,
lost responses and restart with unchanged references/claim/effect counts.

- [x] T016 [P] [US3] Add unknown-provider restart and refusal under a fresh operation ID until verified recovery, lost ACK, duplicate approval, expired review, cancellation, changed binding and foreign-principal cases in `tests/n2n/test_protected_combined_176.py` and `test_protected_ollama_guard_176.py` (FR-007, FR-008).
- [x] T017 [US3] Implement verified owned-process recovery, parent aggregation and bounded yielding status reconciliation in `scripts/lib/protected_ollama.py`, `mcp-servers/protocol-mcp/bgp/federation/protected_calculator.py` and `protected_service.py`; never reissue claims (FR-007, FR-008).
- [x] T018 [US3] Add bounded parent/two-child references persisted before submission and GET-only recovery in `ui/netclaw-visual/src/shared/protected-operations-client.js` and `protected-operation-references.js`, with lost-response/reopen tests (FR-007, FR-008, FR-010).

## Phase 5: US4 — VS Code and Mobile implementation (P2)

**Independent test**: each client supports separate child review/results and safe
recovery with its existing installation/device identity. Actual evidence follows.

- [x] T019 [P] [US4] Extend `extensions/netclaw-vscode/src/client/owner.ts` and `src/views/owner.ts` for combined capability, bounded references, exact separate decisions and partial/unknown results; add tests in `extensions/netclaw-vscode/test/` (FR-010).
- [x] T020 [P] [US4] Extend `mobile/netclaw-mobile/lib/cloud/owner_client.dart`, `lib/ncfed/protected_device_client.dart` and `lib/screens/protected_device_screen.dart` for the same combined contract; test in `test/protected_device_test.dart` and `test/cloud_owner_test.dart` (FR-011).
- [x] T021 [US4] Verify old-server capability absence, profile switching, foreign device/installation, cold/background recovery and no POST replay in both client test suites and `ui/netclaw-visual/src/dashboard/protected-operations.test.js` (FR-007, FR-010, FR-011, FR-012).

## Phase 6: Actual qualification and closeout

- [x] T022 Record artifact coherence in `specs/176-ollama-members/verification.md`; update affected `workspace/skills/subnet-calculator/SKILL.md`, `TOOLS.md` and private setup documentation, with explicit dispositions for README/catalog/install-steps/config/SOUL/env and release-held public material (FR-012, FR-014, FR-015).
- [x] T023 Run focused new and existing protected contract/provider/MCP/recovery and HUD/extension/Mobile checks; record exact commands/source/counts/limits in `specs/176-ollama-members/verification.md` (FR-012, FR-014).
- [x] T024 After T015 execution review, run one real local ARM64 two-turn native subnet summary using `labs/ollama/qualify.py`; verify arithmetic, actual limits, native receipts and no paid calls in `specs/176-ollama-members/verification.md` (FR-001, FR-004, FR-006, FR-009).
- [x] T025 Run real cloud AMD64 and combined browser summaries under separate approvals using `labs/ollama/qualify.py`; record both results, original IDs, durations and signed ACKs in `specs/176-ollama-members/verification.md` (FR-001, FR-002, FR-004, FR-009, FR-010).
- [x] T026 Run both-host admitted-positive and agent/broker/Border/sibling/public-negative isolation probes, real swap/cgroup/OOM checks and eventual model unload via `labs/ollama/qualify.py`; retain evidence in `specs/176-ollama-members/verification.md` (FR-005, FR-006, FR-009).
- [ ] T027 Inject bounded one-child failure, lost response/ACK and actual owned-process restart; compare authorities/claims/effect counts and retained success using `labs/ollama/qualify.py`, with evidence in `specs/176-ollama-members/verification.md` (FR-007, FR-008).
- [ ] T028 [US4] Qualify actual Mac VS Code combined approvals/results and one-child failure/restart through the selected cloud profile; retain G12 receipts in `specs/176-ollama-members/verification.md` (FR-010).
- [ ] T029 [US4] Qualify the native iPhone simulator's two child approvals/results, failure and cold/background reconnect with its existing device key; extend `mobile/netclaw-mobile/integration_test/` and retain G13 receipts in `specs/176-ollama-members/verification.md` (FR-011).
- [ ] T030 Export and verify all private evidence, retire disposable owned resources and compare preserved pilot/identities/history/clients; record actual residue inventory and retained-delivery ownership/expiry in `specs/176-ollama-members/verification.md` (FR-012, FR-013).
- [ ] T031 Review every acceptance row against actual evidence, retain unsuccessful attempts and platform/transport limits, and write a precise handoff in `specs/176-ollama-members/verification.md` (FR-014, FR-015).
- [ ] T032 Append implementation/session lessons to `memory/YYYY-MM-DD.md`, update applicable `TOOLS.md` facts, and record final GAIT/MemPalace outcomes with references in `specs/176-ollama-members/verification.md` (FR-009, FR-014).
- [ ] T033 Record the owner's R05 evidence acceptance in `specs/176-ollama-members/verification.md` before R06/R07; do not infer acceptance or publication from technical completion (FR-015).

## Dependencies and parallel opportunities

T001→T002→T003→T004 establish the frozen profile; T005→T006→T007 establishes native
arithmetic; T008→T009→T010→T011 establishes combined authority/UI. T012 can run after
T004 independently of T008–T011; T013 follows T012 and T014 follows T007. T015 precedes
every live action. T016 follows T009/T003; T017 follows T016; T018 follows T010/T017.
T019 and T020 can run in parallel after T010/T018; T021 follows both. T022/T023 follow
all source work. T024→T025→T026→T027→T028→T029→T030→T031→T032→T033.

Only independently owned test/surface files carry [P]; shared authority/runtime files
stay serialized. [US4] final evidence tasks depend on the real backend qualification.
No optional improvement loop or extra automatic implementation pass is scheduled.

## Implementation strategy and traceability

MVP: US1 on both hosts with US2's compulsory guard/bounds and US3's compulsory
no-repeat behavior. Client acceptance is required before R05 closes.

| Requirement | Tasks |
|---|---|
| FR-001 | T002,T006,T024,T025 |
| FR-002 | T008–T010,T025 |
| FR-003 | T002,T004,T006,T008,T009 |
| FR-004 | T005–T007,T024,T025 |
| FR-005 | T003,T004,T012,T013,T026 |
| FR-006 | T002,T004,T012,T013,T015,T024,T026 |
| FR-007 | T003,T016–T018,T021,T027 |
| FR-008 | T009,T016–T018,T027 |
| FR-009 | T014,T024–T026,T032 |
| FR-010 | T010,T011,T018,T019,T021,T025,T028 |
| FR-011 | T010,T020,T021,T029 |
| FR-012 | T002,T004,T006,T021–T023,T030 |
| FR-013 | T015,T030 |
| FR-014 | T001,T013,T022,T023,T031,T032 |
| FR-015 | T010,T015,T022,T031,T033 |

SC-001:T024–T025; SC-002:T026; SC-003:T014,T024–T026;
SC-004:T027–T029; SC-005:T025,T028,T029; SC-006:T023,T030.
