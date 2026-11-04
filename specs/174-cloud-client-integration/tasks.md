# Tasks: R04a cloud clients

## Phase 1 — Setup

- [x] T001 Record authorized scope, startup, pass allowance and requirements in specs/174-cloud-client-integration/spec.md and private GAIT.
- [x] T002 Inspect client/server contracts and document design in specs/174-cloud-client-integration/contracts/owner-client.md.

## Phase 2 — Foundation

- [x] T003 Reproduce current rejection in actual isolated VS Code; record private evidence and specs/174-cloud-client-integration/verification.md.
- [x] T004 Review fresh finite cloud resource/identity/cost scope and native platform availability in specs/174-cloud-client-integration/qualification-plan.md.

## Phase 3 — US1: VS Code (P1)

Independent test: actual editor completes exact approved read and recovers it without replay.

- [x] T005 [P] [US1] Implement explicit cloud profile and HTTPS capability/identity checks; honor the November4 no-login correction in extensions/netclaw-vscode/src/.
- [x] T006 [US1] Implement native catalog/review/decision/results and persistent reference recovery in extensions/netclaw-vscode/src/.
- [x] T007 [US1] Add meaningful negative/recovery/local-compatibility tests and actual editor harness in extensions/netclaw-vscode/test/.
- [x] T008 [US1] Record actual editor/cloud success, attributable result/ACK and no-repeat reconnect evidence in specs/174-cloud-client-integration/verification.md.

## Phase 4 — US2: Mobile (P1)

Independent test: affected native platform completes and recovers an approved cloud read; physical scope explicit.

- [x] T009 [P] [US2] Implement separate cloud-owner profile/session and secure persistence in mobile/netclaw-mobile/lib/.
- [x] T010 [US2] Implement native catalog/review/decision/results and background/restart recovery in mobile/netclaw-mobile/lib/.
- [x] T011 [US2] Add meaningful negative/widget/recovery tests in mobile/netclaw-mobile/test/.
- [x] T012 [US2] Record actual native platform/cloud evidence and physical-device limits in specs/174-cloud-client-integration/verification.md.

## Phase 5 — US3: Boundaries (P1)

Independent test: local and edge regressions pass; cloud owner does not open legacy authority.

- [x] T013 [P] [US3] Correct protected edge capability advertisement with regression in mcp-servers/protocol-mcp/bgp/federation/service.py and tests/.
- [x] T014 [US3] Verify server ingress/auth and client local/edge isolation using existing HUD/federation and client test suites; record in specs/174-cloud-client-integration/verification.md.

## Phase 6 — Closure

- [x] T015 Export actual evidence and remove fresh owned qualification resources; record actual zero-residue inventories in specs/174-cloud-client-integration/verification.md.
- [x] T016 Reconcile reopened owner-delivery scope, actual handoff, memory/GAIT and release/platform limits in specs/174-cloud-client-integration/resume.md and current daily memory.
- [ ] T017 Obtain human evidence acceptance before R05; record in specs/174-cloud-client-integration/verification.md.
- [x] T018 Correct the persistent GCP development deployment after current-state/rollback review, rebuilding the Border image if needed; leave a compatible trusted HTTPS owner endpoint and supported member workload running within the scoped pilot lifetime.
- [x] T019 Install/configure the compatible extension in the owner's actual VS Code, preserve existing profiles, prove live protected read/restart recovery and hand off the usable Name + URL connection with automatically pinned identity and no user sign-in. Do not retire this intended deployment/profile as test cleanup. Native result display and independent member/Border comparisons passed after the real extension-host restart; exact initiating picker-click attribution is not claimed.

## Dependencies and parallel work

T001–T002 precede implementation. T003 establishes actual pre-fix reproduction before client replacement. T005–T007 and T009–T011 run in separate VS Code/Mobile worktrees; root owns T004/T013 and common contracts. T004 gates fresh deployment; source work may proceed independently. T008/T012 depend on client tests and fresh cloud; T014 joins both; T015–T017 close in order. MVP is US1, but closure includes US2 and US3. This is one bounded pass5, not separate passes per lane.


## Owner correction: actual operating interface

The source/live connection checks above did not meet the owner's intended UI scope.
T018/T019 were reopened for the full cloud-backed workspace; no further optional
proof loop on the rejected JSON/read-only client. Preserve completed evidence.

- [x] T020 Reuse normal VS Code panels/navigation with an installation-pinned HTTPS remote HUD transport; cloud connection opens the operating workspace, with JSON only as optional evidence.
- [x] T021 Restore/integrate the existing full cloud HUD/runtime APIs required by Chat, Canvas, RAG and advertised estate/operations/integration views, preserving current identity and protected history and adding no user authentication.
- [x] T022 Verify the actual installed editor's normal cloud workspace and representative real workflows; preserve local controls and report exact feature/platform limits without claiming success from connectivity alone. Native Chat, RAG search/staging and cited Canvas passed; the approved one-file upload used production HudClient after native picker automation failed before submission. All advertised read panels and usage passed after documented docs/log repairs.
