# Tasks: Cloud eN2N Federation Parity

**Input**: spec.md, plan.md, research.md, data-model.md and contracts/.
**Tests**: Required by spec; actual cloud/native-client acceptance is separate from fixtures.
**State**: Complete for the approved retained-delivery scope; checkboxes map to actual evidence in verification.md. Scheduled retirement is future work within the fixed lifetime, not a claim of already removed resources.

## Phase 1: Setup

- [x] T001 Record owner decisions, branch/base, contract analysis and private evidence root in specs/177-external-en2n-federation/verification.md. (FR-001,FR-016)
- [x] T002 Verify isolated environments, focused existing federation/protected baseline and ignore boundaries; record commands in specs/177-external-en2n-federation/verification.md. (FR-015,FR-016)

## Phase 2: Foundations

- [x] T003 Add selected-home, modern/legacy registration, foreign-config sentinel and subprocess-timeout behavior tests in tests/n2n/test_selected_tool_runtime_177.py. (FR-002,FR-003,FR-009)
- [x] T004 Correct selected MCP config/environment/cwd and owned subprocess cleanup in mcp-servers/protocol-mcp/bgp/federation/invocation.py; retain Hermes contracts. (FR-002,FR-003,FR-009)
- [x] T005 Verify native external-agent restrictions and add locally selected external profile support only where needed in mcp-servers/protocol-mcp/bgp/federation/gateway.py and tests/n2n/test_external_agent_177.py. (FR-007,FR-008,FR-009)

## Phase 3: US1 — Three independent organizations

Independent test: three strict TLS participants establish every pair and support requests in all six directions.

- [x] T006 [US1] Add three-peer strict direct TCP/identity/consent fixture in tests/n2n/test_cloud_triangle_177.py, including local outbound-only connection order and simultaneous pair isolation. (FR-001,FR-003,FR-004,SC-001)
- [x] T007 [US1] Resolve only reproduced registry/listener interoperability defects in mcp-servers/protocol-mcp/bgp/federation/service.py or record verified no-change disposition in specs/177-external-en2n-federation/verification.md. (FR-002,FR-004,FR-015)

## Phase 4: US2 — Existing complete workflows

Independent test: permitted inventory, two-turn peer chat, native tool and async skill/result work in each direction.

- [x] T008 [US2] Extend native workflow matrix and selected-runtime assertions in tests/n2n/test_cloud_workflows_177.py, with independent peer contexts and real MCP execution. (FR-006,SC-002)
- [x] T009 [US2] Preserve original task/request identity and truthful failed/unknown outcomes; add focused loss/retrieval tests in tests/n2n/test_cloud_workflows_177.py and correct only demonstrated defects in mcp-servers/protocol-mcp/bgp/federation/tasks.py or invocation.py. (FR-010,FR-013,SC-005)
- [x] T010 [US2] Define native external result provenance from actual outgoing calls in mcp-servers/protocol-mcp/bgp/federation/invocation.py and tasks.py, without deriving trust from model text. (FR-007,FR-013)

## Phase 5: US3 — Existing trust boundaries

Independent test: wrong identity/consent/scope/budget/transit cannot cause unauthorized execution.

- [x] T011 [US3] Add refusal/effect assertions for all selected trust, grant, visibility, budget and external-agent scope cases in tests/n2n/test_cloud_boundaries_177.py. (FR-004,FR-005,FR-007,FR-008,SC-003)
- [x] T012 [US3] Exercise protected-profile preservation and non-cloud compatibility in tests/n2n/test_protected_role_172.py and existing federation suites; record actual outcomes in specs/177-external-en2n-federation/verification.md. (FR-009,FR-015,SC-006)

## Phase 6: US4 — HUD and VS Code

Independent test: ordinary cloud runtime is discovered truthfully and existing peer views/chat operate on the selected installation.

- [x] T013 [US4] Add ordinary-versus-protected cloud config/capability and route/origin/identity refusal tests in ui/netclaw-visual/src/hud-server/cloud-federation.test.js. (FR-003,FR-009,FR-011)
- [x] T014 [US4] Add explicit ordinary-cloud workspace support using ui/netclaw-visual/src/hud-server/protected-server.js and remote-hud.js (or a small adjacent helper), keeping protected validation unchanged and admin/operation routes private. (FR-009,FR-011)
- [x] T015 [US4] Restore bounded peer inventory/chat route and aligned deadlines in ui/netclaw-visual/src/hud-server/remote-hud.js and ui/netclaw-visual/server.js; test source/session binding and no retry. (FR-006,FR-010,FR-011,FR-013)
- [x] T016 [US4] Update extensions/netclaw-vscode/src/client/owner.ts, remote-hud.ts and affected views for explicit ordinary discovery, existing openPeerChat and unavailable protected controls; extend test/remote-hud.test.mjs and connection tests. (FR-011,FR-015)
- [x] T017 [US4] Run affected HUD/editor regressions and builds; record results and native journey preparation in specs/177-external-en2n-federation/verification.md. (FR-011,FR-015)

## Phase 7: US5 — Mobile

Independent test: ordinary cloud QR/Ask Border/external result and original-request recovery preserve enrolled-device identity.

- [x] T018 [US5] Add ordinary cloud-origin QR issuance/WSS endpoint tests in ui/netclaw-visual/src/hud-server/mobile-enrollment.test.js and tests/n2n/test_mobile_enrollment_175.py; preserve protected mode refusal. (FR-012,FR-015)
- [x] T019 [US5] Integrate exact ordinary-cloud enrollment origin/endpoint into existing ui/netclaw-visual/src/hud-server/mobile-enrollment.js and federation/mobile_enrollment.py as needed; no scanner/login replacement. (FR-012)
- [x] T020 [US5] Propagate bounded native external provenance through mcp-servers/protocol-mcp/bgp/federation/service.py task push/status/result and mobile/netclaw-mobile/lib/ncfed/edge_ask_client.dart plus conversation_store.dart. (FR-007,FR-012,FR-013)
- [x] T021 [US5] Render/persist source in mobile/netclaw-mobile/lib/screens/chat_screen.dart; test cold/reconnect compatibility in conversation_store_test.dart and turn_reconciler_test.dart. (FR-010,FR-012,SC-004)
- [x] T022 [US5] Run affected/full Flutter tests and analyzer and prepare actual simulator driver reuse; record commands in specs/177-external-en2n-federation/verification.md. (FR-012,FR-015)

## Phase 8: US6 — Cloud deployment and actual acceptance

Independent test: fresh cloud/local deployment produces actual six-direction/native-client evidence with finite lifecycle and preserved owner resources.

- [x] T023 [US6] Build fresh R06 IaC foundations/activation variables in labs/cloud/gcp/r06/main.tf and variables.tf; test no cross-org privilege/peering and fixed expiry. (FR-001,FR-003,FR-014)
- [x] T024 [US6] Add exact saved-plan/one-use execution/unknown-state review controls in labs/cloud/gcp/r06/review_plan.py and run_plan.py with tests/cloud-r06/. (FR-014)
- [x] T025 [US6] Prepare fresh host/runtime/secret/network/source packages via labs/cloud/gcp/r06/render_host.py and private R06 artifacts; verify source hashes and ordinary external-agent restrictions. (FR-003,FR-009,FR-014)
- [x] T026 [US6] Prepare current cost, resource/DNS/HTTPS/WSS/provider-use/expiry/teardown packet in specs/177-external-en2n-federation/deployment-review.md with exact private plan references. Record actual scoped authorization before activation. (FR-014)
- [x] T027 [US6] Execute authorized fresh foundation/runtime/client ingress once and verify baseline→apply→observed state; record actual identities/source/resource outcomes in specs/177-external-en2n-federation/verification.md. (FR-001,FR-003,FR-004,FR-014)
- [x] T028 [US6] Complete actual all-six-direction inventory/contextual chat/native tool/async skill matrix in specs/177-external-en2n-federation/parity-matrix.md with correlated private native/provider evidence. (FR-006,FR-013,SC-001,SC-002)
- [x] T029 [US6] Complete actual identity/consent/scope/budget/member/admin/transit refusal and owned-peer/lost-response recovery in specs/177-external-en2n-federation/verification.md, preserving failures/unknowns and effect counts. (FR-005,FR-007,FR-008,FR-010,SC-003,SC-005)
- [x] T030 [US6] Complete actual browser and Mac VS Code cloud peer journeys, including original-result restart recovery, in specs/177-external-en2n-federation/verification.md. (FR-011,SC-004)
- [x] T031 [US6] Complete actual native iPhone simulator QR/Ask Border/external attribution/cold recovery against cloud in specs/177-external-en2n-federation/verification.md. (FR-012,SC-004)
- [x] T032 [US6] Export private evidence; implement and verify exact owned disposable cleanup/retained-delivery lifetime and residue accounting with labs/cloud/gcp/r06/retire.py; preserve R01/R05. (FR-014,SC-006)

## Phase 9: Coherence and closeout

- [x] T033 Reconcile affected source/environment/skill/catalog/agent artifacts and maintain roadmap hold; run required declaration/catalog and affected compatibility checks, documenting dispositions in specs/177-external-en2n-federation/verification.md. (FR-015,FR-016)
- [x] T034 Verify full FR/SC/task/evidence coverage and honest qualification limits in specs/177-external-en2n-federation/verification.md and parity-matrix.md; no open required acceptance task at100%. (FR-013,FR-016,SC-006)
- [x] T035 Update USER.md, TOOLS.md, AGENTS.md and memory/2026-11-06.md, record GAIT summary/log and provide acceptance handoff in specs/177-external-en2n-federation/resume.md. (FR-013,FR-016)

## Dependencies and implementation strategy

T001–T005 precede runtime workflows. T006–T012 establish source federation behavior. UI T013–T017 and Mobile T018–T022 depend on the agreed ordinary-cloud/provenance contracts; edits to shared files are sequential. T023–T026 may be prepared after contracts while source work proceeds; T027 requires source/package verification and actual scoped activation authorization. T028/T029 precede native acceptance T030/T031. T032 follows export; T033–T035 require actual evidence reconciliation. Transport-only MVP is T006/T007 but does not complete the owner request.

Parallel opportunities are independent test execution and read-only research (already completed under plan skill); no implementation-agent delegation is implied. Within US1, registry/identity fixtures can run independently of runtime fixtures. Within US2/US3, scope/refusal tests can run after shared runtime fixes. HUD/editor test processes and Flutter tests can run independently after their changes. Cloud read-only plan preparation does not bypass mutation dependencies.

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001 | T001,T006,T023,T027 |
| FR-002 | T003,T004,T007 |
| FR-003 | T003,T004,T006,T013,T023,T025,T027 |
| FR-004 | T006,T007,T011,T027 |
| FR-005 | T011,T029 |
| FR-006 | T008,T015,T028 |
| FR-007 | T005,T010,T011,T020,T029 |
| FR-008 | T005,T011,T029 |
| FR-009 | T003,T004,T005,T012,T013,T014,T025 |
| FR-010 | T009,T015,T021,T029 |
| FR-011 | T013–T017,T030 |
| FR-012 | T018–T022,T031 |
| FR-013 | T009,T010,T015,T020,T028,T034,T035 |
| FR-014 | T023–T027,T032 |
| FR-015 | T002,T007,T012,T016–T018,T022,T033 |
| FR-016 | T001,T002,T033–T035 |
| SC-001/002 | T006,T008,T028 |
| SC-003 | T011,T029 |
| SC-004 | T021,T030,T031 |
| SC-005 | T009,T029 |
| SC-006 | T012,T032,T034 |
