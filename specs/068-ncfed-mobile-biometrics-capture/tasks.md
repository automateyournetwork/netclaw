# Tasks: NCFED Mobile Biometrics and Capture

**Input**: Design documents from `/specs/068-ncfed-mobile-biometrics-capture/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included, matching the repo's test-driven convention.

**Organization**: By user story (US1/US2/US3, all P1).

## Path Conventions

Federation daemon: `mcp-servers/protocol-mcp/bgp/federation/`. Mobile app: extends
`mobile/netclaw-mobile/` (066/067). Tests: `tests/n2n/`, `mobile/netclaw-mobile/test/`.

---

## Phase 1: Setup

- [X] T001 [P] Add `local_auth` and `camera` to `mobile/netclaw-mobile/pubspec.yaml` (research D8); `flutter pub get` and confirm resolution.
- [X] T002 [P] Create empty test scaffolds `tests/n2n/test_edge_approval.py` and `tests/n2n/test_edge_capture.py`.

---

## Phase 2: Foundational (blocking prerequisites)

- [X] T003 Add `n2n/edge/register_capabilities`, `n2n/edge/capture`, `n2n/edge/approval_resolve` to `EDGE_METHODS` in `edge.py` (contract §1-3).
- [X] T004 Implement `_edge_on_register_capabilities(self, channel, params)` in `service.py`: replaces the member's capture-related `scope` entries with exactly the given list (research D1) — must not disturb any non-capture scope entries.
- [X] T005 Implement `_edge_on_approval_resolve(self, channel, params)` in `service.py`: calls `self.authz.resolve_approval(approval_id, action, via="biometric")` unchanged (research D6) — no new logic in `authorization.py` itself.
- [X] T006 Add a `node_type='edge'` branch to `delegate_to_member()` in `service.py`: when the target member is an edge node, call a new `delegate_to_edge(member_id, capability)` helper (`ch.call("n2n/edge/capture", {"capability": capability}, timeout=...)` over `self.edge_channels`) instead of `n2n/tasks/submit` over `self.member_channels` — still tracked via the same `self.tasks` create/run pattern `_edge_on_ask` (067) already established (research D2).
- [X] T007 Extend `notify_approval()` in `service.py` to also call `push_to_edge(member_id, {"content_type": "approval", ...})` for every connected edge channel, alongside the existing (unchanged) `self.approval_notifier` call (research D5) — pull the device/change/reason/agent/risk fields from the same data `create_approval`/`pending_approvals` already expose.
- [X] T008 Extend `_edge_on_ask` in `service.py` to fold an optional `attachment` field into the `run_agent_turn()` prompt (research D3) — `text` may be empty when an attachment stands alone (FR-005).

**Checkpoint**: All new wire methods exist and are unit-testable without a real phone.

---

## Phase 3: User Story 1 — Approve or deny with Face ID (Priority: P1)

- [X] T009 [US1] Implement `mobile/netclaw-mobile/lib/ncfed/approval_client.dart`: receives pushed approvals (both `n2n/edge/message` content_type='approval' while connected, and the existing `notification_deep_link.dart`-style payload while backgrounded), exposes a `Stream<PendingApproval>`.
- [X] T010 [US1] Implement `mobile/netclaw-mobile/lib/screens/approvals_screen.dart`: lists pending approvals (device/change/reason/agent/risk), approve/deny buttons gated by `local_auth.authenticate()` — sends `n2n/edge/approval_resolve` ONLY after a successful biometric result; a failed/cancelled/unavailable biometric attempt sends nothing (FR-002).
- [X] T011 [P] [US1] Test in `tests/n2n/test_edge_approval.py`: `notify_approval()` pushes to every connected edge channel with `content_type='approval'` and the expected fields.
- [X] T012 [P] [US1] Test in `tests/n2n/test_edge_approval.py`: `n2n/edge/approval_resolve` calls the existing `resolve_approval(..., via="biometric")` unchanged — confirm `resolved_via='biometric'` in the DB row, and that `n2n_approve`/`n2n_deny`'s existing HTTP path resolving the SAME approval first makes a second phone resolution attempt a no-op (matches the existing "first resolution wins" behavior, not new logic).
- [X] T013 [P] [US1] `flutter test` for `approval_client.dart`: a mocked failed/cancelled biometric result never triggers an `n2n/edge/approval_resolve` call.

**Checkpoint**: US1 independently demonstrable.

---

## Phase 4: User Story 2 — Send a photo, video, or voice note to the Border (Priority: P1)

- [X] T014 [US2] Implement `mobile/netclaw-mobile/lib/ncfed/capture_client.dart`'s phone-initiated half: captures via `camera`, enforces the size/duration cap at capture time (research D4/FR-005a), and attaches the result to `edge_ask_client.dart.ask()` via the new `attachment` field (contract §4) — supports a bare capture with empty `text`.
- [X] T015 [US2] Add a camera/capture button to `chat_screen.dart` (067), wired to `capture_client.dart`.
- [X] T016 [P] [US2] Test in `tests/n2n/test_edge_ask.py` (067's file, extended): `n2n/edge/ask` with only an `attachment` and empty `text` still reaches `run_agent_turn()` with a non-empty prompt (folds the attachment in, per T008).
- [X] T017 [P] [US2] `flutter test` for `capture_client.dart`: a capture exceeding the configured duration/size budget is refused/truncated at capture time — never sent oversized (FR-005a); a declined OS permission or cancelled capture never calls `ask()` at all (FR-005's acceptance scenarios 3-4).

**Checkpoint**: US2 independently demonstrable.

---

## Phase 5: User Story 3 — The Border asks the phone to capture something (Priority: P1)

- [X] T018 [US3] Implement `capture_client.dart`'s Border-requested half: registers a handler for `n2n/edge/capture`, activates the native capture UI, returns `{"decision": "captured", ...}` or `{"decision": "declined", "reason": ...}` (contract §2) — never a silent empty result.
- [X] T019 [US3] Implement `mobile/netclaw-mobile/lib/ncfed/capability_registration.dart`: sends `n2n/edge/register_capabilities` at connect time and on every Settings toggle change; add the capture-type toggles to a Settings screen (or extend an existing one).
- [X] T020 [P] [US3] Test in `tests/n2n/test_edge_capture.py`: `n2n_delegate(target_name="camera.capture", ...)` against a risk containing only an edge node with that capability resolves to the edge node (via the unmodified `RiskRouter`) and calls `n2n/edge/capture` over its edge channel, not `n2n/tasks/submit`.
- [X] T021 [P] [US3] Test in `tests/n2n/test_edge_capture.py`: a declined/failed capture result flows back as an explicit failure (task state `failed`, not `completed` with an empty payload) — confirms FR-009/SC-004.
- [X] T022 [P] [US3] Test in `tests/n2n/test_edge_capture.py`: delegating to a capability only a DISCONNECTED edge node advertises fails cleanly ("capability not available"/member_unreachable), consistent with how an unreachable agent member is already handled — no new code path, just confirming the existing `ensure_member_up`/unreachable handling covers edge nodes too (it doesn't cold-start a phone, so this should fail fast, not hang).
- [X] T023 [P] [US3] Test in `tests/n2n/test_edge_capture.py`: `n2n/edge/register_capabilities` with a type omitted makes `RiskRouter.candidates()` for that capability NOT include the edge node at all (FR-007a/SC-008 — inspecting `scope` directly, not just observing a request fail).
- [X] T024 [P] [US3] `flutter test` for `capability_registration.dart`: toggling a capture type off and reconnecting sends the updated (shorter) capability list.

**Checkpoint**: US3 independently demonstrable — the phone is a first-class, Border-invocable capability provider, symmetric with any agent member.

---

## Phase 6: Polish & Cross-Cutting

- [X] T025 [P] Update `workspace/skills/n2n-federation/SKILL.md` with the biometric-approval and capture slice.
- [X] T026 [P] Update `README.md`/`TOOLS.md`/`SOUL.md` — no new MCP tool (research D2), capability-description only.
- [X] T027 [P] Update `mobile/netclaw-mobile/README.md` with the Approvals/capture screens and new platform permissions (camera/mic already covered by 066/067's Info.plist keys; confirm no new key needed).
- [X] T028 Run the full n2n suite and confirm zero regressions; map passing tests to SC-001…SC-008.
- [X] T029 [P] Run `flutter analyze` and `flutter test`; confirm an actual Android build/run.
- [X] T030 [P] Run the `quickstart.md` manual walkthrough against a throwaway Border + Android emulator; record the result, noting which steps genuinely need a real device (biometric hardware, real camera) versus what's verifiable here.

---

## Dependencies

- **Setup (T001-T002)** → **Foundational (T003-T008)** blocks everything below.
- US1 (T009-T013), US2 (T014-T017), and US3 (T018-T024) are independent of each other once
  Foundational is done (each depends only on the wire methods, not on each other's UI).
- Polish (T025-T030) depends on all stories above.

## Notes

- The single biggest risk is adding NEW delegation/routing code where D1/D2 already say none is
  needed — if "US3 doesn't route to the phone" fails, the fix is almost certainly in
  `delegate_to_member`'s new branch (T006), not a parallel capability-discovery mechanism.
- Do NOT let `local_auth` or any biometric-related Dart code reference `EdgeIdentity` or the
  Keystore/Secure-Enclave plugins at all (research D7/FR-003) — this is the one hard security
  boundary in this spec, and it's enforced by simply never importing across those files, not by
  a runtime check.
