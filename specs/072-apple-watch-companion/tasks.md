# Tasks: Apple Watch Companion App for NetClaw Mobile

**Input**: Design documents from `/specs/072-apple-watch-companion/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/watch-relay.md, quickstart.md

**Tests**: Included for everything with a meaningful headless-test surface (Dart relay logic,
Python Border-side handler). Native WatchConnectivity/`LAContext` passcode UI has none, matching
spec 071's precedent for Face ID/Secure Enclave — those are manually verified instead.

**Organization**: Setup + Foundational (the relay plumbing every capability needs) come first,
then one phase per user story in priority order (US1 Approvals P1, US2 Feed P2, US3 Ask P3), then
Polish.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [x] T001 Add a new watchOS App target (`WatchApp`) to
      `mobile/netclaw-mobile/ios/Runner.xcodeproj`, embedded as `Runner`'s companion watch app.
      Confirm the existing `Runner`/`RunnerTests` targets and schemes are untouched.
- [x] T002 [P] Boot a watchOS Simulator paired with an iOS Simulator (Xcode auto-pairs booted
      Simulators of compatible versions); confirm the pairing is recognized before writing any
      relay code.
- [x] T003 [P] Add the `WatchConnectivity` framework to both the `Runner` and `WatchApp` targets,
      and `LocalAuthentication` to `WatchApp` — system frameworks, no new external dependency.

**Checkpoint**: A blank `WatchApp` target builds and installs onto a paired watch Simulator
alongside `Runner`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The watch-to-phone relay plumbing every one of the three user stories depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Create `mobile/netclaw-mobile/ios/Runner/WatchRelayPlugin.swift` — a `WCSessionDelegate`
      that activates a session on launch and, on `session(_:didReceiveMessage:replyHandler:)`,
      forwards the message into Dart via a new `FlutterMethodChannel` (e.g.
      `ca.automateyournetwork.netclaw/watch_relay`, mirroring `EdgeIdentityPlugin`'s channel
      naming). Register it in `AppDelegate.swift`'s `didInitializeImplicitFlutterEngine`, alongside
      the existing `EdgeIdentityPlugin.register` call.
- [x] T005 Create `mobile/netclaw-mobile/lib/ncfed/watch_relay.dart` — sets a
      `MethodChannel.setMethodCallHandler` that dispatches on the method name
      (`watch/approvals/list`, `watch/approvals/resolve`, `watch/feed/list`, `watch/ask/submit`,
      `watch/ask/status` — contracts/watch-relay.md), initially returning `{"enrolled": false}`/
      empty-shaped stubs for all five so the plumbing round-trip can be verified before any real
      capability is wired.
- [x] T006 In `mobile/netclaw-mobile/lib/main.dart`'s `_HomeShellState`, construct the
      `WatchRelay` (or equivalent) once `askClient`/`approvalClient`/`feedStore` are all built, so
      the relay always answers using the SAME live instances the phone's own UI uses — never a
      second set.
- [x] T007 Create `mobile/netclaw-mobile/ios/WatchApp/WatchConnectivitySession.swift` (watch-side
      `WCSessionDelegate` + a `sendMessage`-wrapping async helper) and
      `mobile/netclaw-mobile/ios/WatchApp/ConnectionState.swift` (the `connected` /
      `phoneUnreachable` / `notEnrolled` enum from data-model.md, shared by all three views).
- [x] T008 [P] Build `WatchApp` for the paired Simulator (T002); confirm a trivial round trip
      (e.g. `watch/approvals/list` returning the T005 stub) actually reaches Dart and comes back,
      before building any real UI on top.

**Checkpoint**: A message sent from the watch Simulator reaches Dart and a reply comes back,
proven end to end. All three user stories can now be built in any order.

---

## Phase 3: User Story 1 - Approve or deny a pending request from the wrist (Priority: P1) 🎯 MVP

**Goal**: Resolve a real pending approval entirely from the watch, correctly attributed.

**Independent Test**: Trigger a Border-side approval, resolve it from the watch Simulator, confirm
the Border's own audit record shows `via="watch_passcode"`.

### Tests for User Story 1

- [x] T009 [P] [US1] `mobile/netclaw-mobile/test/watch_relay_test.dart`: `watch/approvals/list`
      returns the current `ApprovalClient.currentPending` list shaped per contracts/watch-relay.md
      §1, and `enrolled: false` when no approval client is available.
- [x] T010 [P] [US1] `watch_relay_test.dart`: `watch/approvals/resolve` calls
      `ApprovalClient.resolve(approval_id, action)` and the underlying wire call carries
      `confirmation_method: "watch_passcode"` (contracts/watch-relay.md §2).
- [x] T011 [P] [US1] `tests/n2n/test_edge_approval.py` (or a new file alongside it): a
      `confirmation_method` field on `n2n/edge/approval_resolve` is passed through to
      `Authorizer.resolve_approval(..., via=<that value>)`; when absent, `via="biometric"` — the
      existing phone flow's behavior is provably unchanged (research D4).

### Implementation for User Story 1

- [x] T012 [US1] `lib/ncfed/watch_relay.dart`: implement `watch/approvals/list` for real, replacing
      the T005 stub.
- [x] T013 [US1] `lib/ncfed/approval_client.dart`: add an optional `confirmationMethod` parameter
      to `resolve()`, defaulting to `"biometric"` (the existing phone call site in
      `approvals_screen.dart` passes nothing, preserving today's exact wire behavior); include it
      in the `n2n/edge/approval_resolve` params only when non-default.
- [x] T014 [US1] `lib/ncfed/watch_relay.dart`: implement `watch/approvals/resolve`, calling
      `ApprovalClient.resolve(approvalId, action, confirmationMethod: "watch_passcode")`.
- [x] T015 [US1] `mcp-servers/protocol-mcp/bgp/federation/service.py`'s
      `_edge_on_approval_resolve` (~line 1288): read `params.get("confirmation_method",
      "biometric")` and pass it to `self.authz.resolve_approval(int(approval_id), action,
      via=<that value>)`, replacing the hardcoded `via="biometric"` literal.
- [x] T016 [US1] `mobile/netclaw-mobile/ios/WatchApp/ApprovalsView.swift`: list view rendering the
      relayed approvals (requester, target, reason), matching `approvals_screen.dart`'s
      information density at watch scale.
- [x] T017 [US1] In `ApprovalsView.swift`, gate every approve/deny action on a fresh
      `LAContext().evaluatePolicy(.deviceOwnerAuthentication, ...)` call (research D3) — called
      immediately before sending, never cached, never skipped. A failed/cancelled confirmation
      leaves the approval untouched (FR-003).
- [x] T018 [US1] Handle the "resolved elsewhere" edge case: on each list refresh, drop any approval
      no longer present in the phone's relayed list rather than leaving a stale, already-resolved
      entry actionable (FR-005).
- [x] T019 [US1] Manual verification: quickstart.md step 4 (Simulator) — trigger a Border approval,
      resolve from the watch, confirm the Border's audit record shows `watch_passcode` not
      `biometric`.

**Checkpoint**: User Story 1 is fully functional and independently demonstrable — this is the MVP.

---

## Phase 4: User Story 2 - Read pushed messages without unlocking the phone (Priority: P2)

**Goal**: A scrollable, read-only Feed view on the watch, sourced from the phone.

**Independent Test**: Push a text and an image message from the Border; confirm both are visible
and scrollable on the watch Simulator with no phone interaction.

### Tests for User Story 2

- [x] T020 [P] [US2] `watch_relay_test.dart`: `watch/feed/list` returns the phone's
      `MessageFeedStore.messages`, and a non-text `content_type` is still present with an empty/
      truncated `content` (contracts/watch-relay.md §3, data-model.md).

### Implementation for User Story 2

- [x] T021 [US2] `lib/ncfed/watch_relay.dart`: implement `watch/feed/list` for real, replacing the
      T005 stub, truncating `content` for `image`/`voice` types before sending.
- [x] T022 [US2] `mobile/netclaw-mobile/ios/WatchApp/FeedView.swift`: scrollable, read-only list;
      text messages show full content, image/voice show a type indicator (FR-007) rather than
      being omitted.
- [x] T023 [US2] Manual verification: quickstart.md step 5 (Simulator).

**Checkpoint**: User Stories 1 and 2 both independently functional.

---

## Phase 5: User Story 3 - Ask a quick question by voice (Priority: P3)

**Goal**: Dictate a question on the watch, submit it exactly like a phone chat message, see the
answer.

**Independent Test**: Submit a dictated (or, on Simulator, typed) question from the watch; confirm
it reaches the Border through the phone and the answer appears on the watch.

### Tests for User Story 3

- [x] T024 [P] [US3] `watch_relay_test.dart`: `watch/ask/submit` calls `EdgeAskClient.ask(text)`
      and returns its `task_id`; `watch/ask/status` narrows `TaskState` to the three-value
      `waiting`/`answered`/`failed` vocabulary from data-model.md (both `pending` and `working`
      collapse to `waiting`; `failed`/`cancelled` collapse to `failed`).
- [x] T025 [P] [US3] `watch_relay_test.dart`: an empty/whitespace-only dictation result never calls
      `EdgeAskClient.ask` at all (FR-010, mirroring `voice_transcription_test.dart`'s existing
      "nothing heard never sends" coverage on the phone side).

### Implementation for User Story 3

- [x] T026 [US3] `lib/ncfed/watch_relay.dart`: implement `watch/ask/submit` and `watch/ask/status`
      for real, replacing the T005 stubs.
- [x] T027 [US3] `mobile/netclaw-mobile/ios/WatchApp/AskView.swift`: a `TextField` (dictation-first
      per research D5) plus waiting/answered/failed state display.
- [x] T028 [US3] In `AskView.swift`, detect empty/whitespace-only dictation output before
      submitting and show a clear "didn't catch that" state instead of calling
      `watch/ask/submit` (FR-010).
- [x] T029 [US3] Manual verification: quickstart.md step 6 (Simulator, typed input standing in for
      dictation since the Simulator cannot dictate for real).

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T030 [P] Verify the `connected`/`phoneUnreachable`/`notEnrolled` state (T007) is surfaced
      consistently and distinguishably across `ApprovalsView`, `FeedView`, and `AskView` — force-
      quit the phone app / stop its Simulator while the watch app is open and confirm every view
      reacts within a few seconds, never an indefinite spinner (FR-012, quickstart.md step 7).
- [x] T031 [P] Attempt real-hardware verification (research D6, quickstart.md step 8): confirm
      whether the paired physical Apple Watch shows up as a run destination in Xcode's Devices and
      Simulators window; if so, repeat T019/T023/T029 on it; document the outcome (verified, or
      blocked-with-reason) either way — do not assume success without evidence.
- [x] T032 Code-review confirmation of FR-011/FR-013/SC-006 (negative/absence requirements — no
      task above directly verifies these): grep the `WatchApp` target and `watch_relay.dart` for
      any enrollment/QR-scanning/camera-capture/settings-toggle code, any `EdgeClient`/WebSocket/
      identity code independent of the relay, and any direct Border network call from the watch
      side. Record the result (a clean negative, or what was found and removed) — do not rely on
      "we never wrote it" being self-evidently true without checking.
- [x] T033 Update `mobile/netclaw-mobile/README.md` with a new watchOS section, stating precisely
      what was verified (Simulator vs. real hardware, per T031's outcome) versus what remains
      assumed, at the same specificity level as the existing iOS/Android sections.
- [x] T034 [P] Add a one-line cross-reference in
      `specs/068-ncfed-mobile-biometrics-capture/contracts/edge-biometrics-and-capture.md` noting
      that `n2n/edge/approval_resolve` gained an optional `confirmation_method` field in spec 072,
      pointing to `specs/072-apple-watch-companion/contracts/watch-relay.md` §5 — keeps the spec
      that originally defined this wire shape from silently going stale.
- [x] T035 Run `flutter analyze` and `flutter test` (full suite) in `mobile/netclaw-mobile/`, and
      `python3 -m pytest tests/n2n -q`, confirming zero regressions in every existing test.
- [x] T036 Walk through `specs/072-apple-watch-companion/quickstart.md` end to end as a final
      self-check that every success signal listed there is satisfied.

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → **Foundational (Phase 2)**: strictly sequential; Foundational needs the
  watch target and Simulator pairing from Setup.
- **Foundational (Phase 2)** BLOCKS all three user stories — none of them have anything to build on
  until the relay round-trip (T008) is proven.
- **User Story 1 (Phase 3)**, **User Story 2 (Phase 4)**, **User Story 3 (Phase 5)**: independent
  of each other once Foundational is done; US1 is the MVP and should be done first, but US2/US3
  don't depend on US1's approval-specific work (they touch different relay methods and different
  watch views entirely).
- **Polish (Phase 6)**: T030 depends on at least one user story's views existing to check (ideally
  all three); T032 depends on all three user stories' code existing to review; T033 depends on
  T019/T023/T029/T031's evidence existing; T034 has no code dependency and can run anytime once
  the contract exists; T035/T036 run last.

### Parallel Opportunities

- T002/T003 (Setup) can run in parallel.
- T009/T010 (US1 tests), T020 (US2 test), T024/T025 (US3 tests) can all be written in parallel
  with each other, and each set can be written before or during its own story's implementation.
- T030/T031 (Polish) are independent of each other.
- US1/US2/US3 implementation phases themselves can proceed in parallel if staffed separately, since
  they touch different watch views and different (non-overlapping) relay methods.

## Implementation Strategy

1. Setup + Foundational — get a proven watch↔phone round trip before building anything real.
2. User Story 1 (Approvals) — the MVP; stop and validate independently before continuing.
3. User Story 2 (Feed) — adds value without touching US1's code.
4. User Story 3 (Quick Ask) — adds value without touching US1/US2's code.
5. Polish — close the loop on not-connected states, real-hardware attempt, and documentation.

## Post-Implementation Notes (real-device testing, 2026-07-27)

- **All three user stories verified on real hardware** (a physical Apple Watch Series 7,
  watchOS 26.6, paired with the spec-071 iPhone), not just the Simulator — the Simulator hit an
  unresolved UI-rendering quirk (backend message exchange succeeded per device logs, but the
  watch UI never visibly progressed past a spinner) and was set aside in favor of hardware.
- **A 4th "History" tab was added beyond the original three-capability scope**, after real-device
  testing showed the operator wanted past chat Q&A (mirroring the phone's `ConversationStore`)
  visible on the wrist, not just new Feed pushes. Read-only, same pattern as Feed
  (`watch/history/list`, capped at 30 turns, newest first). This is additive — FR-011/FR-013's
  negative requirements (no enrollment, no direct network connection, no capture/settings) are
  unaffected and were re-confirmed clean by T032's grep after the addition.
- **A standalone Release build of the phone app was produced**, so the phone no longer needs
  Xcode attached to launch (Flutter debug/JIT builds refuse to run without the tooling attached
  — this was a real, repeatedly-hit blocker during testing). Getting there surfaced a second,
  still-unresolved variant of the cross-SDK platform-bleed problem (see README.md's watchOS
  section for full detail): even at a concrete iPhone `-destination`, Xcode's implicit build of
  the embedded `WatchApp` dependency compiled it against an iOS deployment target. Worked around
  by temporarily detaching `WatchApp`'s target dependency and embed phase from `Runner` for the
  one-off Release build, then restoring both immediately (verified via a clean Debug rebuild
  afterward). **The shipped standalone Release phone build does not embed the watch companion**;
  the watch app remains a separately-installed Debug build, which itself needs no Xcode to launch
  day-to-day (native Swift, not subject to Flutter's JIT restriction). Producing one Release
  archive with both apps properly embedded together is deferred, unresolved follow-up work.
