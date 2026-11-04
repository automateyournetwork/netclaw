# Tasks: R04a cloud clients

## Phase 1 — Setup

- [x] T001 Record authorized scope, startup, pass allowance and requirements in specs/174-cloud-client-integration/spec.md and private GAIT.
- [x] T002 Inspect client/server contracts and document design in specs/174-cloud-client-integration/contracts/owner-client.md.

## Phase 2 — Foundation

- [x] T003 Reproduce current rejection in actual isolated VS Code; record private evidence and specs/174-cloud-client-integration/verification.md.
- [ ] T004 Review fresh finite cloud resource/identity/cost scope and native platform availability in specs/174-cloud-client-integration/qualification-plan.md.

## Phase 3 — US1: VS Code (P1)

Independent test: actual editor completes exact approved read and recovers it without replay.

- [ ] T005 [P] [US1] Implement explicit cloud profile, HTTPS owner session and capability/identity checks in extensions/netclaw-vscode/src/.
- [ ] T006 [US1] Implement native catalog/review/decision/results and persistent reference recovery in extensions/netclaw-vscode/src/.
- [ ] T007 [US1] Add meaningful negative/recovery/local-compatibility tests and actual editor harness in extensions/netclaw-vscode/test/.
- [ ] T008 [US1] Record actual editor/cloud success, attributable result/ACK and no-repeat reconnect evidence in specs/174-cloud-client-integration/verification.md.

## Phase 4 — US2: Mobile (P1)

Independent test: affected native platform completes and recovers an approved cloud read; physical scope explicit.

- [ ] T009 [P] [US2] Implement separate cloud-owner profile/session and secure persistence in mobile/netclaw-mobile/lib/.
- [ ] T010 [US2] Implement native catalog/review/decision/results and background/restart recovery in mobile/netclaw-mobile/lib/.
- [ ] T011 [US2] Add meaningful negative/widget/recovery tests in mobile/netclaw-mobile/test/.
- [ ] T012 [US2] Record actual native platform/cloud evidence and physical-device limits in specs/174-cloud-client-integration/verification.md.

## Phase 5 — US3: Boundaries (P1)

Independent test: local and edge regressions pass; cloud owner does not open legacy authority.

- [x] T013 [P] [US3] Correct protected edge capability advertisement with regression in mcp-servers/protocol-mcp/bgp/federation/service.py and tests/.
- [ ] T014 [US3] Verify server ingress/auth and client local/edge isolation using existing HUD/federation and client test suites; record in specs/174-cloud-client-integration/verification.md.

## Phase 6 — Closure

- [ ] T015 Export actual evidence and remove fresh owned qualification resources; record actual zero-residue inventories in specs/174-cloud-client-integration/verification.md.
- [ ] T016 Reconcile tasks, maintainer handoff, memory/GAIT and release/platform limits in specs/174-cloud-client-integration/resume.md and memory/2026-11-03.md.
- [ ] T017 Obtain human evidence acceptance before R05; record in specs/174-cloud-client-integration/verification.md.

## Dependencies and parallel work

T001–T002 precede implementation. T003 establishes actual pre-fix reproduction before client replacement. T005–T007 and T009–T011 run in separate VS Code/Mobile worktrees; root owns T004/T013 and common contracts. T004 gates fresh deployment; source work may proceed independently. T008/T012 depend on client tests and fresh cloud; T014 joins both; T015–T017 close in order. MVP is US1, but closure includes US2 and US3. This is one bounded pass5, not separate passes per lane.
