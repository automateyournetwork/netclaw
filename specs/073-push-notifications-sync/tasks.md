# Tasks: Push Notifications, Unread Tracking & Cross-Device Sync for NetClaw Mobile

**Input**: Design documents from `/specs/073-push-notifications-sync/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/watch-relay-extensions.md, quickstart.md

**Tests**: Included for everything with a meaningful headless-test surface (Dart store/relay logic,
Python Border-side handler), matching spec 072's precedent. Native `AVSpeechSynthesizer`, OS
notification permission/badge/mirroring, and `LAContext` passcode UI have none — manually verified
instead (quickstart.md).

**Organization**: Setup + Foundational (the shared store/relay/notification plumbing every story
needs) come first, then one phase per user story in priority order (US1 Notifications+Badge P1,
US2 Unread/Acknowledge/Delete P2, US3 Watch-chat-history fix P3, US4 Voice playback P4), then
Polish.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [X] T001 Add `flutter_local_notifications` to `mobile/netclaw-mobile/pubspec.yaml`; run
      `flutter pub get`; confirm the app still builds for both iOS and Android with no new
      permission-declaration errors (Android already declares `POST_NOTIFICATIONS` per research;
      confirm no NEW Info.plist keys are required beyond what `flutter_local_notifications`'
      own setup needs — add any it does require to `ios/Runner/Info.plist`).
- [X] T002 [P] Confirm `flutter analyze` and the full existing `flutter test` suite still pass with
      the new dependency added and nothing else changed yet — a clean baseline before any
      feature code lands.

**Checkpoint**: The new dependency is present and the existing app is unaffected.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The store/relay/Border plumbing every user story below depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 `mobile/netclaw-mobile/lib/ncfed/message_feed.dart`: add a `bool acknowledged` field to
      `EdgeMessage` (default `false` for new instances); `toJson()` gains `'acknowledged'`;
      `fromJson()` MUST default a **missing** `acknowledged` key to `true` (research D5 — getting
      this backwards makes every pre-existing message appear unread after upgrade). Add
      `acknowledge(DateTime pushedAt)`, `delete(DateTime pushedAt)`, and a derived
      `int get unreadCount` (messages where `acknowledged == false`) to `MessageFeedStore`.
- [X] T004 [P] `mobile/netclaw-mobile/lib/ncfed/conversation_store.dart`: add `bool acknowledged`
      (default `false`, same missing-key-defaults-to-`true` migration rule) and
      `String origin` (`"phone"` | `"watch"`, default `"phone"`, missing key also defaults to
      `"phone"`) to `ConversationTurn`. Add `acknowledge(String taskId)`, `delete(String taskId)`,
      and a derived `int get unreadCount` (terminal-state turns where `acknowledged == false`) to
      `ConversationStore`.
- [X] T005 [P] Create `mobile/netclaw-mobile/lib/ncfed/local_notifications.dart` — initializes
      `flutter_local_notifications`, exposes a function to post a notification (title, body,
      payload JSON per contracts/watch-relay-extensions.md §4, optional Darwin actions with
      `authenticationRequired` for approvals), and a function to set the iOS/watch-mirrored app
      badge to an explicit combined count (research D3). No caller wiring yet — this task is pure
      infrastructure.
- [X] T006 `mobile/netclaw-mobile/lib/ncfed/watch_relay.dart`: add four new relay methods —
      `watch/feed/acknowledge`, `watch/feed/delete` (calling `MessageFeedStore.acknowledge()`/
      `.delete()` from T003), `watch/history/acknowledge`, `watch/history/delete` (calling
      `ConversationStore.acknowledge()`/`.delete()` from T004) — per
      contracts/watch-relay-extensions.md §1-2. Also add the `acknowledged` field to the existing
      `watch/feed/list` and `watch/history/list` replies (§3).
- [X] T007 [P] `mcp-servers/protocol-mcp/bgp/federation/authorization.py`: extend
      `resolve_approval()` (~line 149) to report whether its `UPDATE ... WHERE status='pending'`
      actually affected a row (e.g. inspect the cursor's row count) rather than unconditionally
      returning `True` — research D6. Keep the existing always-`True`-on-success contract for any
      caller that only checks a boolean; add the new information as an additional return value.
- [X] T008 `mcp-servers/protocol-mcp/bgp/federation/service.py`'s `_edge_on_approval_resolve`
      (~line 1288): thread T007's new information through as an additive `already_resolved: bool`
      field on the `n2n/edge/approval_resolve` reply, per contracts/watch-relay-extensions.md §5.

**Checkpoint**: Stores support acknowledge/delete/unread-count; the watch relay has the four new
methods; the Border reports `already_resolved`. Nothing user-visible yet — verified by unit tests
in each user story phase below, not here.

---

## Phase 3: User Story 1 - Get notified the moment the Border pushes something (Priority: P1) 🎯 MVP

**Goal**: Real local notifications for Feed/Chat/Approvals, an authenticated inline Approve/Deny
on approval banners, deep-linking on tap, and the combined app-icon badge.

**Independent Test**: With the app running (foreground or backgrounded), trigger a Feed push, a
completed chat answer, and a new approval in turn; confirm a distinct correctly-worded banner for
each, badge increments for Feed/Chat only, and the watch mirrors each banner (including its own
home-screen icon badge).

### Tests for User Story 1

- [X] T009 [P] [US1] `mobile/netclaw-mobile/test/local_notifications_test.dart` (new): the badge
      helper from T005 computes the combined count correctly from given Feed/Chat unread counts,
      including the zero case.
- [X] T010 [P] [US1] `tests/n2n/test_edge_approval.py`: a second `resolve` call for an
      already-resolved `approval_id` returns `already_resolved: true` on the wire reply; the first
      call for a still-pending approval returns `already_resolved: false` (T007/T008).
- [X] T011 [P] [US1] `mobile/netclaw-mobile/test/local_notifications_test.dart`: the dedup guard
      (T020 below) never posts a second notification for an identifier it has already posted one
      for, even across repeated calls with identical Feed/Chat/approval identifiers (FR-007).
- [X] T012 [P] [US1] `mobile/netclaw-mobile/test/notification_deep_link_test.dart` (extend): the
      generalized dispatcher (T017 below) correctly routes a local-notification payload
      (`{"type":"feed"/"chat","identifier":...}`) to the right message/turn, in addition to its
      existing Firebase-remote-tap coverage — both payload sources feed the same dispatch logic
      (research D4).

### Implementation for User Story 1

- [X] T013 [US1] `mobile/netclaw-mobile/lib/main.dart`: in `wireMessageFeed`'s existing `onMessage`
      callback, post a local notification (T005) for each new Feed message — one-line content
      preview, payload `{"type":"feed","identifier":"<pushedAt ISO>"}`.
- [X] T014 [US1] `lib/main.dart`/`lib/ncfed/conversation_store.dart`: when `updateState()` moves a
      turn to a terminal `completed` state, post a local notification for that answer — payload
      `{"type":"chat","identifier":"<taskId>"}`.
- [X] T015 [US1] `lib/main.dart`: in `ApprovalClient.receiveApproval`'s call site, post a local
      notification for each new approval with two `DarwinNotificationAction`s (`approve`/`deny`),
      each with `authenticationRequired` set (research D2) — payload
      `{"type":"approval","identifier":"<approval_id>"}`. This notification MUST NOT affect the
      badge (Approvals excluded, spec Assumptions).
- [X] T016 [US1] `lib/ncfed/approval_client.dart` (or a new small handler wired in `main.dart`):
      the notification-action callback (`onDidReceiveNotificationResponse`) for `approve`/`deny`
      MUST route through the exact same biometric-confirmation-then-`resolve()` path the in-app
      Approve/Deny buttons already use — never a direct `resolve()` call bypassing that gate
      (FR-004). On an `already_resolved: true` reply, surface a clear "already resolved" outcome
      (FR-005) instead of treating it as a fresh success.
- [X] T017 [US1] `mobile/netclaw-mobile/lib/ncfed/notification_deep_link.dart`: generalize
      `NotificationDeepLink` into a shared dispatcher consuming BOTH the existing Firebase
      `onMessageOpenedApp`/`getInitialMessage()` taps AND the new local-notification tap callback's
      payload (`type`/`identifier`) — Feed taps open that specific message, chat taps open that
      specific answer (FR-006).
- [X] T018 [US1] `lib/main.dart`: wire the badge helper (T005) to be recomputed and set (a) every
      time a new Feed/Chat notification posts (T013/T014) and (b) — anticipating User Story 2 —
      expose it as a function other call sites can invoke, since acknowledge/delete actions will
      also need to trigger it.
- [X] T019 [US1] `lib/main.dart`: check notification-permission status at startup; if denied, set a
      discoverable (non-nagging, e.g. a small persistent indicator, not a repeated dialog) flag —
      every other capability MUST continue working normally regardless (FR-020).
- [X] T020 [US1] Add a dedup guard (in `local_notifications.dart` or the call sites) so a
      reconnect-triggered replay of an already-notified Feed message/chat answer/approval never
      posts a second notification for the same item (FR-007) — keyed by the same identifier used
      in the notification payload.
- [ ] T021 [US1] Manual verification: quickstart.md steps 1-5 and 11 (permission prompt and
      graceful denial, Feed/Chat/Approval banners with correct badge behavior on BOTH the phone's
      and the watch's own home-screen icon per FR-009, authenticated inline actions,
      already-resolved race, burst-produces-individual-notifications) on the real iPhone + Apple
      Watch pair from spec 072.

**Checkpoint**: User Story 1 is fully functional and independently demonstrable — this is the MVP.

---

## Phase 4: User Story 2 - See at a glance what's new, and clear it when done (Priority: P2)

**Goal**: Per-item unread indicators and acknowledge/delete actions on both phone and watch,
correctly reflected across devices and in the badge.

**Independent Test**: Push several items; confirm unread indicators on both phone and watch;
acknowledge one from the watch and confirm the phone/badge reflect it on next view; delete one from
the phone and confirm it's gone from the watch's next refresh.

### Tests for User Story 2

- [X] T022 [P] [US2] `mobile/netclaw-mobile/test/message_feed_test.dart`: `acknowledge()`,
      `delete()`, `unreadCount`, and the missing-key-defaults-to-`true` migration behavior (T003)
      are all covered.
- [X] T023 [P] [US2] `mobile/netclaw-mobile/test/conversation_store_test.dart`: same coverage for
      `ConversationStore` (T004), plus the `origin` field's default.
- [X] T024 [P] [US2] `mobile/netclaw-mobile/test/watch_relay_test.dart`: the four new relay methods
      (T006) call through to the right store method and return the documented reply shape.

### Implementation for User Story 2

- [X] T025 [US2] `mobile/netclaw-mobile/lib/screens/feed_screen.dart`: visually distinguish
      unacknowledged messages (e.g. bold/dot); add an acknowledge action and a per-message delete
      action (distinct from the existing whole-history clear-all).
- [X] T026 [US2] `mobile/netclaw-mobile/lib/screens/chat_screen.dart`: same treatment for chat
      turns — unread indicator, acknowledge action, per-turn delete action.
- [X] T027 [US2] `mobile/netclaw-mobile/ios/WatchApp Watch App/FeedView.swift`: unread indicator
      per message; acknowledge/delete controls calling the new `watch/feed/acknowledge`/
      `watch/feed/delete` relay methods (T006).
- [X] T028 [US2] `mobile/netclaw-mobile/ios/WatchApp Watch App/HistoryView.swift`: unread indicator
      per turn; acknowledge/delete controls calling `watch/history/acknowledge`/
      `watch/history/delete`.
- [X] T029 [US2] Wire T018's badge-recompute call into every acknowledge/delete action from BOTH
      the phone UI (T025/T026) and the watch relay (T006) — the badge must never drift stale after
      an action that didn't also involve a new notification (FR-008).
- [X] T030 [US2] Confirm (and fix if needed) that an acknowledge/delete attempted from the watch
      while the phone is unreachable surfaces the existing `phoneUnreachable`/"can't reach iPhone"
      state (already established in `WatchDataStore`'s pattern) rather than silently failing
      (FR-015).
- [ ] T031 [US2] Manual verification: quickstart.md steps 6-8 (unread indicators on both devices,
      watch-acknowledge reflected on phone, phone-delete reflected on watch, watch-unreachable
      action handling).

**Checkpoint**: User Stories 1 and 2 both independently functional.

---

## Phase 5: User Story 3 - A question asked from the watch shows up in chat history everywhere (Priority: P3)

**Goal**: Fix the existing defect where watch-submitted Ask turns never reach the shared
conversation history.

**Independent Test**: Ask a question from the watch; confirm it appears in the phone's Chat tab and
the watch's own History tab once answered.

### Tests for User Story 3

- [X] T032 [P] [US3] `mobile/netclaw-mobile/test/watch_relay_test.dart`: `watch/ask/submit` now
      calls `ConversationStore.addPending()` (currently it only calls `EdgeAskClient.ask()`); the
      created turn's `origin` is `"watch"`. `watch/ask/status` now calls
      `ConversationStore.updateState()` when the Border's answer arrives (currently it only
      narrows and returns state to the watch, never persists it).

### Implementation for User Story 3

- [X] T033 [US3] `mobile/netclaw-mobile/lib/ncfed/watch_relay.dart`'s `_submitAsk`: after calling
      `EdgeAskClient.ask()`, also call the already-available `conversationStore.addPending(taskId,
      text)` (the `conversationStore` field already exists on `WatchRelay` from the History-tab
      work — it is simply never called from `_submitAsk` today) and set the new turn's `origin` to
      `"watch"`.
- [X] T034 [US3] `watch_relay.dart`'s `_askStatus`: after calling `EdgeAskClient.result()`, also
      call `conversationStore.updateState(taskId, ...)` with the resolved state/answer so the turn
      persists correctly, not just what's returned to the watch in that one reply.
- [ ] T035 [US3] Manual verification: quickstart.md step 9 (a watch-asked question appears in the
      phone's Chat tab and the watch's own History tab, indistinguishable in form from a
      phone-submitted question).

**Checkpoint**: User Stories 1-3 all independently functional.

---

## Phase 6: User Story 4 - Have the watch read a message aloud (Priority: P4)

**Goal**: An explicit, on-demand "read aloud" control on the watch's Feed/History/Ask views.

**Independent Test**: Tap "read aloud" on a text message and a photo message; confirm speech and a
content-type description respectively; confirm nothing is ever spoken without that tap.

### Implementation for User Story 4

*(No automated tests — `AVSpeechSynthesizer` has no meaningful headless-test surface, matching this
project's established precedent for native platform capabilities.)*

- [X] T036 [US4] Create `mobile/netclaw-mobile/ios/WatchApp Watch App/SpeechPlayback.swift` — a
      small wrapper exposing `speak(_ text: String)` using `AVSpeechSynthesizer`. Register this new
      file in `Runner.xcodeproj`'s `WatchApp` target Sources build phase via the `xcodeproj` Ruby
      gem (set `path` to just the filename, not a nested path — this exact mistake caused a build
      failure twice in spec 072's implementation).
- [X] T037 [US4] `ios/WatchApp Watch App/FeedView.swift`: add a "read aloud" control per message —
      text messages call `SpeechPlayback.speak(content)`; photo/voice messages speak a description
      of the content type instead (FR-019) — never automatically, only on explicit tap (FR-018).
- [X] T038 [US4] `ios/WatchApp Watch App/HistoryView.swift`: add a "read aloud" control per turn's
      answer text, same rules.
- [X] T039 [US4] `ios/WatchApp Watch App/AskView.swift`: add a "read aloud" control on the answered
      state's answer display, same rules.
- [ ] T040 [US4] Manual verification: quickstart.md step 10 (read-aloud works on a tap, photo
      content speaks a description, nothing is ever spoken unprompted).

**Checkpoint**: All four user stories independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T041 [P] Update `mobile/netclaw-mobile/README.md` with a new section documenting this
      feature's real-hardware-verified status (or blocked-with-reason), at the same specificity
      level as the existing iOS/Android/watchOS sections.
- [X] T042 [P] Code-review confirmation that FR-010's constraint holds: grep the `WatchApp` target
      for any new background-delivery/push-registration code — there must be none; the watch's
      notification/badge behavior must come entirely from standard OS mirroring, not new watch-side
      code.
- [X] T043 Run `flutter analyze` and `flutter test` (full suite) in `mobile/netclaw-mobile/`, and
      `python3 -m pytest tests/n2n -q`, confirming zero regressions in every existing test.
- [ ] T044 Walk through `specs/073-push-notifications-sync/quickstart.md` end to end as a final
      self-check that every success signal listed there is satisfied.

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → **Foundational (Phase 2)**: strictly sequential; Foundational needs the new
  dependency from Setup.
- **Foundational (Phase 2)** BLOCKS all four user stories — none of the store/relay/Border changes
  they depend on exist until T003-T008 are done.
- **User Story 1 (Phase 3)** is the MVP and should be done first. **User Story 2 (Phase 4)**
  depends on US1's badge-helper wiring (T018), so US2 is not fully independent of US1 the way
  spec 072's user stories were of each other — build US1 first.
- **User Story 3 (Phase 5)** is independent of US1/US2 — it only touches `watch_relay.dart`'s ask
  methods and can be built/tested in any order relative to them.
- **User Story 4 (Phase 6)** is independent of all other stories — purely additive watch-native UI
  with no relay/store dependency beyond data already fetched by US2's views.
- **Polish (Phase 7)**: T041/T042 are independent of each other; T043/T044 run last.

### Parallel Opportunities

- T001/T002 (Setup) are sequential (T002 verifies T001's result).
- T003/T004/T005 (Foundational) touch different files and can run in parallel; T007 (Python) is
  independent of all Dart foundational work.
- T009/T010/T011/T012 (US1 tests) can all be written in parallel with each other and with US1
  implementation.
- T022/T023/T024 (US2 tests) can all run in parallel.
- User Story 3 (Phase 5) and User Story 4 (Phase 6) can be built in parallel with each other and,
  once Foundational is done, in parallel with User Story 1/2 work if staffed separately — they
  touch entirely different files.
- T041/T042 (Polish) are independent of each other.

## Implementation Strategy

1. Setup + Foundational — get the new dependency, store fields, relay methods, and Border addition
   in place before building anything user-visible.
2. User Story 1 (Notifications + Badge) — the MVP; stop and validate independently before
   continuing.
3. User Story 2 (Unread/Acknowledge/Delete) — builds on US1's badge wiring; adds the other half of
   "like a normal app."
4. User Story 3 (Watch chat history fix) — independent defect fix, can slot in anytime after
   Foundational.
5. User Story 4 (Voice playback) — independent, lowest-risk, purely additive.
6. Polish — documentation, negative-requirement code review, full regression pass, final
   quickstart walkthrough.
