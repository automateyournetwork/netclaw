# Tasks: NCFED Mobile Command Channel

**Input**: Design documents from `/specs/067-ncfed-mobile-command-channel/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included, matching the repo's test-driven convention (`tests/n2n/`, `flutter test`).

**Organization**: By user story (US1/US2 P1, US3/US4/US5 P2).

## Path Conventions

Federation daemon: `mcp-servers/protocol-mcp/bgp/federation/`. Mobile app: extends
`mobile/netclaw-mobile/` (066). Tests: `tests/n2n/`, `mobile/netclaw-mobile/test/`.

---

## Phase 1: Setup

- [X] T001 [P] Create `tests/n2n/test_edge_ask.py` (empty scaffold, reusing the shared `conftest.py` manager fixture and the `_FakePhone`/`_border`/`_serve`/`_enroll` helpers already established in `test_edge_enrollment.py` — import or duplicate minimally, whichever keeps the test file self-contained).

**Checkpoint**: Nothing yet depends on implementation.

---

## Phase 2: Foundational (blocking prerequisites)

- [X] T002 Add `n2n/edge/ask`, `n2n/edge/ask_result`, `n2n/tasks/status`, `n2n/tasks/result`, `n2n/tasks/cancel` to `EDGE_METHODS` in `mcp-servers/protocol-mcp/bgp/federation/edge.py` (contract §1-5; task-status/result/cancel are reused method NAMES from the existing iN2N surface — this only widens which methods an `EdgeChannel` handler map may register, not new logic in edge.py itself).
- [X] T003 Register `n2n/tasks/status`/`n2n/tasks/result`/`n2n/tasks/cancel` in `service.py`'s `_edge_border_handlers` pointing at the EXISTING `self.invoker.handle_task_status`/`handle_task_result`/`handle_task_cancel` (`invocation.py:224-235`) — do NOT write new handler functions; these are already fully generic over `channel.peer_identity` (research D4).
- [X] T004 Implement `_edge_on_ask(self, channel, params)` in `service.py`, mirroring `_in2n_member_submit`'s task-creation shape (`service.py:1451-1490`) but calling `gateway.run_agent_turn(text, session_key=f"n2n-edge-{member_id}", untrusted=False)` (research D2/D4) instead of the member's local/embedded mode. Register it as `n2n/edge/ask` in `_edge_border_handlers`. On task completion, best-effort push `ch.notify("n2n/edge/ask_result", {...})` if the channel is still open (contract §2).

**Checkpoint**: The wire methods exist and are unit-testable without a real phone.

---

## Phase 3: User Story 1 — Ask the Border a question from the phone (Priority: P1)

**Goal**: A text request from an enrolled phone reaches the Border and gets answered via a real agent turn.
**Independent test**: Submit a text request from an enrolled, connected phone; confirm a real composed answer returns to the same conversation.

- [X] T005 [US1] Implement `mobile/netclaw-mobile/lib/ncfed/edge_ask_client.dart`: `ask(text) -> taskId`, listens for `n2n/edge/ask_result`, exposes a `Stream<TaskUpdate>` the Chat screen can subscribe to.
- [X] T006 [US1] Implement `mobile/netclaw-mobile/lib/ncfed/conversation_store.dart`: per-device JSON-Lines persisted history (mirrors 066's `MessageFeedStore`, data-model.md).
- [X] T007 [US1] Implement `mobile/netclaw-mobile/lib/screens/chat_screen.dart`: text input, request/answer history from `ConversationStore`, in-progress state while a task is pending.
- [X] T008 [P] [US1] Test in `tests/n2n/test_edge_ask.py`: `n2n/edge/ask` creates a `delegated_task` row (`target_type='edge_ask'`) and returns a `task_id` immediately (mock/stub `gateway.run_agent_turn` so the test doesn't need a real `openclaw agent` binary — patch it to return a canned `(text, tokens)` tuple).
- [X] T009 [P] [US1] Test in `tests/n2n/test_edge_ask.py`: the completed task's answer is pushed via `n2n/edge/ask_result` to the connected phone.
- [X] T010 [P] [US1] Test in `tests/n2n/test_edge_ask.py`: an unauthorized request (simulate a `run_agent_turn` refusal) surfaces as a failed task, not a hang — confirms FR-010.
- [X] T011 [P] [US1] `flutter test` for `conversation_store.dart`: appended turns persist across a simulated app restart (same pattern as 066's `message_feed_test.dart`).

**Checkpoint**: US1 independently demonstrable.

---

## Phase 4: User Story 2 — The Border delegates a phone request to an iN2N member (Priority: P1)

**Goal**: A phone request requiring a member's expertise is delegated and answered with clear attribution; in-progress and cancellable.
**Independent test**: Submit a request only a specific member can fulfill; confirm delegation (reusing existing task submission) and correct attribution; cancel an in-progress request and confirm it's reflected as cancelled.

- [X] T012 [US2] Implement cancel support in `chat_screen.dart`: a cancel action on an in-progress turn calls `n2n/tasks/cancel` (via `edge_ask_client.dart`) and updates `ConversationStore`'s state to `cancelled`.
- [X] T013 [P] [US2] Test in `tests/n2n/test_edge_ask.py`: an edge-ask task's `task_id` is cancellable via `n2n/tasks/cancel`, reusing `TaskManager.cancel()` — confirm the SAME code path member-delegation already exercises, not a new one (grep-verified: `Invoker.handle_task_cancel` is the only implementation).
- [X] T014 [P] [US2] Test in `tests/n2n/test_edge_ask.py`: a task cancelled after it has already completed is a no-op on the finished result (never both "cancelled" and "completed" — the edge case from spec.md).
- [X] T015 [P] [US2] `flutter test` for `chat_screen.dart`: an in-progress turn shows a distinct visual state from a completed one; cancelling updates it to cancelled, not failed.

**Checkpoint**: US2 independently demonstrable — delegation and cancellation both hold. NOTE: this story needs no NEW Border-side delegation code (research D3) — its "independent test" is really testing that D3's premise holds, i.e. that the agent, given a member-specific question, actually calls `n2n_delegate` on its own. If it does not, that is an AGENT PROMPTING/BEHAVIOR issue outside this spec's code, not a bug to fix here — flag it rather than build a parallel delegation path.

---

## Phase 5: User Story 3 — The Border reaches an external claw on the operator's behalf (Priority: P2)

**Goal**: A phone request needing a federated peer is routed over eN2N, subject to the exact same grant/audit model.
**Independent test**: Submit a request requiring an eN2N-authorized peer; confirm refusal without a grant and correct external attribution with one.

- [X] T016 [P] [US3] Test in `tests/n2n/test_edge_ask.py`: an edge-ask task whose agent turn attempts (mocked) an eN2N-crossing tool call without a grant is refused/audited identically to a non-mobile equivalent — this is exercising the EXISTING authorization.py grant model, not new edge-specific gating (confirms FR-004's "MUST NOT be restricted or specially gated merely because the request originated from a phone" by testing that no edge-specific check exists to accidentally add one to).
- [ ] T017 [US3] Manual verification only (no new code expected): with a real federated peer configured, submit a phone request that requires it and confirm attribution in the conversation names the external peer. Record the result in quickstart.md.
      - **2026-07-25 (iOS, spec `071-ios-mobile-port`)**: attempted from the iOS side, still blocked — same Xcode/Flutter gap as 066's T045 (no iOS build possible yet from this Mac). Separately, per `MAC-IOS-HANDOFF.md`, the three eN2N peers (`as65007`, `as65008`, `as65099`) have been connection-refused all week, so this would be double-blocked even once the app builds. Not closed by this pass.

**Checkpoint**: US3 demonstrable given a federated peer exists; no Border-side code changes anticipated for this story per research D3.

---

## Phase 6: User Story 4 — Ask a question by voice (Priority: P2)

**Goal**: A recorded voice message produces the same answer a typed equivalent would.
**Independent test**: Record and send a voice message that would trigger delegation if typed; confirm identical answer/attribution behavior.

- [X] T018 [US4] Add an on-device speech-to-text package to `mobile/netclaw-mobile/pubspec.yaml` (research D7) and implement `mobile/netclaw-mobile/lib/ncfed/voice_transcription.dart`: record → transcribe → hand the resulting text to the SAME `edge_ask_client.dart.ask()` path as a typed request (no separate wire method, contract's client-side-shortcuts section).
- [X] T019 [US4] Add a voice-record button to `chat_screen.dart`, wired to `voice_transcription.dart`.
- [X] T020 [P] [US4] `flutter test` for `voice_transcription.dart`: a transcribed voice input produces the exact same request shape (`{"text": ...}`) a typed one would — asserted at the `edge_ask_client` call boundary (mock the STT engine; this is not a speech-recognition-accuracy test).

**Checkpoint**: US4 demonstrable — voice is provably just a different input method into the same US1 path.

---

## Phase 7: User Story 5 — Scan equipment to jump to its status (Priority: P2)

**Goal**: A QR code or `netclaw://device/<id>` deep link submits a device-status request with no typing.
**Independent test**: Scan/open a link encoding a known identifier; confirm an automatic device-status request and answer; an unknown identifier fails explicitly.

- [X] T021 [US5] Implement `mobile/netclaw-mobile/lib/ncfed/device_deep_link.dart`: parses `netclaw://device/<id>` (register the URI scheme via a deep-link package, research/plan's Primary Dependencies) and a QR payload of the same shape, both resolving to `edge_ask_client.dart.ask("What is the current status of device <id>?")` (contract's client-side-shortcuts section).
- [X] T022 [US5] Wire `device_deep_link.dart` into the app's routing so a cold-start-from-link and a foreground-tap both land on `chat_screen.dart` with the auto-submitted request visible.
- [X] T023 [P] [US5] `flutter test` for `device_deep_link.dart`: a known-shape identifier produces the exact templated request text; confirm no separate "unknown device" client-side error path exists — that failure surfaces from the SAME agent-turn failure path US1's T010 already tests (grep-verified: no new error code invented, research D8).

**Checkpoint**: US5 demonstrable — the deep link is provably just a request-submission shortcut, not a new mechanism.

---

## Phase 8: Polish & Cross-Cutting

- [X] T024 [P] Update `workspace/skills/n2n-federation/SKILL.md` with the phone-command-channel slice (ask/delegate/route/cancel from a phone) — this spec only; capture/biometrics is 068's.
- [X] T025 [P] Update `README.md`/`TOOLS.md`/`SOUL.md` — no new MCP tool is introduced (research D3), so these updates are capability-description only, not a tool-count bump.
- [X] T026 [P] Update `mobile/netclaw-mobile/README.md` with the Chat screen / voice / deep-link additions.
- [X] T027 Run the full n2n suite (`python3 -m pytest tests/n2n -q`) and confirm zero regressions; map passing tests to SC-001…SC-006.
- [X] T028 [P] Run `flutter analyze` and `flutter test` in `mobile/netclaw-mobile/`; confirm an actual Android build/run against a local emulator (unlike 066, this environment should have the Android SDK by the time this task runs).
- [X] T029 [P] Run the `quickstart.md` manual walkthrough end-to-end against a throwaway (non-production) Border instance + the Android emulator; record the result including US3's manual-only verification (T017).

---

## Dependencies

- **Setup (T001)** → **Foundational (T002-T004)** blocks everything below.
- US1 (T005-T011) is the base path every other story's request travels through.
- US2 (T012-T015) depends on US1's task-tracking plumbing (same `n2n/edge/ask`/task_id shape).
- US3 (T016-T017) depends on US1/US2's plumbing existing; no new code expected.
- US4 (T018-T020) depends only on US1's `ask()` entry point.
- US5 (T021-T023) depends only on US1's `ask()` entry point.
- Polish (T024-T029) depends on all stories above.

## Notes

- The single biggest risk in this spec is NOT writing new delegation/routing code where none
  is needed (research D3) — if a "US2 doesn't work" test failure shows up, the fix is almost
  certainly a prompt/context issue in how `_edge_on_ask` frames the request to the agent, not a
  missing Border-side delegation mechanism. Do not build a parallel `n2n_delegate`-equivalent
  call inside `_edge_on_ask`.
- Do NOT reuse `n2n/edge/message` for the phone→Border direction — it is documented
  Border-initiated-push-only (066, FR-008/FR-009). Use the new `n2n/edge/ask`/`ask_result` pair.
