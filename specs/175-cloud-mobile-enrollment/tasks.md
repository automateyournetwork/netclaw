# Tasks: R04b Mobile QR enrollment

## Phase 1 — Setup

- [x] T001 Record owner scope and quality checklist in specs/175-cloud-mobile-enrollment/spec.md and checklists/requirements.md.
- [x] T002 Create separate backend, surfaces and Mobile worktrees; record architecture in specs/175-cloud-mobile-enrollment/plan.md.
- [x] T003 Freeze enrollment and protected-device contracts in specs/175-cloud-mobile-enrollment/contracts/ and research.md.
- [x] T004 Capture current pilot/authority and tooling baseline in specs/175-cloud-mobile-enrollment/verification.md with private receipts.

## Phase 2 — Foundational authority

- [x] T005 Add bounded durable issuance and mobile-only token purpose in mcp-servers/protocol-mcp/bgp/federation/ and tests/n2n/.
- [x] T006 Add device-derived protected authority, scoped access and unchanged historical principal verification in mcp-servers/protocol-mcp/bgp/federation/ and tests/n2n/.
- [x] T007 Add explicit protected loopback WSS role/listener and ingress validation in scripts/lib/protected_role.py and mcp-servers/protocol-mcp/bgp-daemon-v2.py.

## Phase 3 — US1: HUD to phone enrollment

Goal: one visible action generates a genuine bounded QR in local/cloud HUD; existing scanner and retained key enroll/reconnect. Independent test: actual image decode on native simulator, one registration, same-key hello.

- [x] T008 [US1] Test issuance/replay/purpose/expiry/wrong binding in tests/n2n/ and HUD route tests.
- [x] T009 [P] [US1] Implement narrow shared enrollment HTTP handler/local adapter and protected mount in ui/netclaw-visual/src/hud-server/ and server.js.
- [x] T010 [P] [US1] Implement Mobile enrollment card, visible entry and transient QR lifecycle in ui/netclaw-visual/src/.
- [x] T011 [P] [US1] Add additive QR installation/path and pending same-key enrollment recovery in mobile/netclaw-mobile/lib/ncfed/ and existing native identity plugins.
- [x] T012 [US1] Test production enrollment lost reply, wrong key/domain/installation, token absence in storage and legacy compatibility in mobile/netclaw-mobile/test/.
- [x] T013 [US1] Add separate simulator-native actual QR decoding/key harness importing production enrollment UI in mobile/netclaw-mobile/integration_test/ and ios/.

## Phase 4 — US2: VS Code Mobile generation

Goal: local/cloud selected Mobile view displays real QR and status. Independent test: actual native editor generates QR consumed by simulator, with selection/expiry handling.

- [x] T014 [P] [US2] Add exact selected-connection enrollment client methods and capability gating in extensions/netclaw-vscode/src/.
- [x] T015 [US2] Add dedicated Mobile view with QR, expiry, retained nonsecret nonce and explicit replacement in extensions/netclaw-vscode/src/.
- [x] T016 [US2] Verify no shell routing/token persistence, unknown issuance recovery and local/cloud selection in extensions/netclaw-vscode/test/.

## Phase 5 — US3: protected operation and recovery

Goal: enrolled device sees exact protected catalog/review/decision/result/ACK; recovery adds no effects. Independent test: one bounded native read then actual process/background restart.

- [x] T017 [US3] Dispatch five scoped authenticated WSS protected RPCs with refusal tests in mcp-servers/protocol-mcp/bgp/federation/ and tests/n2n/.
- [x] T018 [P] [US3] Implement strict device descriptor, WSS adapter and separate device retention in mobile/netclaw-mobile/lib/.
- [x] T019 [US3] Reuse complete review/decision/result UI in device mode and gate legacy HomeShell/headless paths in mobile/netclaw-mobile/lib/.
- [x] T020 [US3] Test exact review, lost prepare/decision, cross-device reference refusal and no-repeat recovery in mobile/netclaw-mobile/test/ and tests/n2n/.

## Phase 6 — Native acceptance and preservation

- [x] T021 Integrate local commits and run targeted combined checks/builds; record in specs/175-cloud-mobile-enrollment/verification.md.
- [x] T022 Prepare and independently review exact pilot update/rollback/ingress and owned local test setup in specs/175-cloud-mobile-enrollment/deployment.md with private packet hashes.
- [x] T023 Apply reviewed bounded development-pilot changes and verify confinement/preservation in specs/175-cloud-mobile-enrollment/verification.md.
- [x] T024 Verify actual local HUD and native VS Code Mobile QR generation to simulator with real decode/enroll/reconnect in specs/175-cloud-mobile-enrollment/verification.md.
- [x] T025 Verify actual cloud HUD and native VS Code Mobile QR generation to simulator with trusted TLS and refusal cases in specs/175-cloud-mobile-enrollment/verification.md.
- [ ] T026 Review and approve one bounded read on enrolled simulator, verify signed result/durable ACK/effect counts in specs/175-cloud-mobile-enrollment/verification.md.
- [x] T027 Verify native background/process restart and same-reference recovery with unchanged effects/history in specs/175-cloud-mobile-enrollment/verification.md.
- [x] T028 Export evidence, retire only disposable owned fixtures, preserve usable owner pilot and inventory leftovers in specs/175-cloud-mobile-enrollment/verification.md.
- [x] T029 Record coverage limits, maintainer handoff and product entry steps in specs/175-cloud-mobile-enrollment/resume.md; update TOOLS.md, USER.md, AGENTS.md and memory/2026-11-04.md; final GAIT log.
- [ ] T030 Obtain separate human stage acceptance before R05 in specs/175-cloud-mobile-enrollment/resume.md.

## Dependencies and parallel execution

T001–T003 precede implementation; T004 precedes deployment. T005–T007 provide authority and transport, with frozen contracts allowing independent T009–T016 client work. US1 (T008–T013) precedes actual enrollment; US2 (T014–T016) depends on the shared issuer contract; US3 (T017–T020) depends on device authority and authenticated enrollment. T021 integrates all lanes before T022–T028 live acceptance. T029 is additive throughout; T030 is owner acceptance and cannot be self-certified.

Backend owns Python/federation/protected-server mount, surfaces owns shared HTTP handlers/HUD/editor, Mobile owns Dart/native harness. Communicate shared-file edits before merging. Root owns deployment and integration. Example parallel batches: T005/T009/T011; T007/T014/T013; T017/T016/T018. One bounded feature pass; no automatic loop. The native test matrix deliberately distinguishes local and cloud, HUD and editor, and image decode versus camera hardware.

## Implementation strategy

Deliver the common issuer and genuine QR path first, then editor parity and protected operations, integrate once and qualify the actual product. Tests target meaningful authorization/replay/state transitions. Stop dependent mutation on unknown outcome and inspect retained state. Native acceptance remains unchecked until observed; publication/later-stage work is excluded.


## November 5 acceptance checkpoint

All four actual QR/enrollment paths, native refusals and no-repeat recovery passed.
T026 remains open for a successful data read: the one approved native attempt
returned a signed, acknowledged HTTP403 failure using the unchanged Nov4 demo
credential. A current owner-provided read-only token is required; preserve that
failed operation and use a separately reviewed new reference. T030 remains the
separate human acceptance gate. The owner explicitly requires a full stop before
R05; neither technical progress nor a supplied credential starts the next stage.
