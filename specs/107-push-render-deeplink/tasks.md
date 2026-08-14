---

description: "Task list for 107-push-render-deeplink"
---

# Tasks: Notification tap opens the message it names

**Input**: Design documents from `/specs/107-push-render-deeplink/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/notification-intent.md, quickstart.md

**Tests**: Test tasks ARE included. The spec's own Success Criteria are behavioral
and the plan carries an explicit requirement→verification map; spec 106 also
demonstrated the cost of shipping this area untested — its route tiering had no
coverage at all, which is exactly why the bug reached production.

**Organization**: Grouped by user story. Note the one hard cross-story dependency
below — it is the whole reason the phases are ordered this way.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 / US2 / US3 from spec.md
- **🔌 DEVICE**: requires real hardware; cannot be verified in the Dart suite
- All paths are relative to repo root

## Path Conventions

Flutter single package at `mobile/netclaw-mobile/` — `lib/ncfed/` for edge-node
modules, `test/` for the suite. Per plan.md's Structure Decision.

---

## ⚠️ The one ordering rule that matters

**Phase 4 (US3, dedup) MUST fully complete before Phase 5 (US2, instant render).**

US2 adds a second writer to the feed store. Without dedup in place, every message
it persists will appear **twice** the moment the Border's replay delivers the same
message — converting a fixed bug into a more visible one. This is FR-008, and it
is enforced here by phase ordering rather than by a runtime assertion, so that it
stays testable.

US1 is independent of both and may run fully in parallel with US3.

---

## Phase 1: Setup

No project initialization needed — this feature adds no dependency and no new
package. Two orientation tasks only.

- [ ] T001 Reproduce the bug on a device following `specs/107-push-render-deeplink/quickstart.md` §"Reproduce the bug first", and record the observed auth→replay gap from the Border journal 🔌 DEVICE
- [x] T002 [P] Confirm the baseline suite is green before any change: `cd mobile/netclaw-mobile && flutter test && flutter analyze`

---

## Phase 2: Foundational

Blocking prerequisite for US1 and US2. The intent mechanism is shared by both tap
paths, so it lands once, before either story consumes it.

- [x] T003 Create `PendingOpenIntent` in `mobile/netclaw-mobile/lib/ncfed/pending_open_intent.dart` — records one identifier with its creation time, exposes record / resolve-if-present / expire, holds at most one intent (a second record discards the first), and does not persist across launches. Implements contract §1.1–1.7 and data-model's PendingOpenIntent lifecycle
- [x] T004 [P] Create `test/pending_open_intent_test.dart` covering: resolves immediately when the message is already present (§1.3); resolves when it arrives later (§1.4); expires within the bound and does not fire the open callback (§1.5, §1.6); a second record discards the first (§1.2); open callback fires exactly once (§1.6)

**Checkpoint**: intent mechanism exists and is unit-tested against the contract.

---

## Phase 3: User Story 1 — Tapping a notification opens that message (P1)

**Goal**: The tap opens the named message whether the app was closed,
backgrounded, or already open — including when the message arrives seconds after
launch.

**Independent test**: Push a message with the app closed, tap the notification,
the message opens. Verifiable without US2 or US3.

- [x] T005 [US1] Rewrite `NotificationDeepLink._handleRemote` in `mobile/netclaw-mobile/lib/ncfed/notification_deep_link.dart` to record a `PendingOpenIntent` from the notification data instead of performing a single `store.load()` + `findMessageForNotificationData` read that cannot win the race (research R1)
- [x] T006 [US1] Converge `handleLocalNotificationTap` in `mobile/netclaw-mobile/lib/ncfed/notification_deep_link.dart` onto the shared intent, so the remote and local paths are one mechanism rather than two (research R6, contract §5.4). The local path's existing correct behavior must be preserved
- [x] T007 [US1] Wire intent resolution to the feed's existing change signal in `mobile/netclaw-mobile/lib/main.dart` — `wireMessageFeed`'s `onMessage` callback already fires after every append, so no polling is introduced (research R1)
- [x] T008 [P] [US1] Extend `test/notification_deep_link_test.dart`: message arrives AFTER the tap and the intent resolves (the actual production bug); message already stored resolves with no wait; intent expires and the feed is shown (FR-003); opening the app with no tap forces nothing open (FR-011)
- [x] T009 [P] [US1] Extend `test/notification_response_routing_test.dart` to confirm the local-notification tap path still deep-links after converging on the intent (regression guard for T006)
- [ ] T010 [US1] Verify on hardware: app fully closed → push → tap → the named message opens; then repeat backgrounded (SC-001, SC-002) 🔌 DEVICE

**Checkpoint**: US1 delivers standalone value. Shippable without US2 or US3.

---

## Phase 4: User Story 3 — No duplicates (P1) — **BLOCKS PHASE 5**

**Goal**: The feed shows each message exactly once, regardless of delivery path.

**Independent test**: Deliver the same message twice by different paths; one entry
appears.

- [x] T011 [US3] Add identity-based dedup to the append path in `mobile/netclaw-mobile/lib/ncfed/message_feed.dart`, keyed on `pushedAt` (research R2, R3). Enforce inside the store, NOT at call sites, so a future writer inherits it
- [x] T012 [US3] Make append in `mobile/netclaw-mobile/lib/ncfed/message_feed.dart` report whether it stored or declined, per contract §2.3 — without this, a declined duplicate would still fire an unread badge and the double-entry bug becomes a double-notification bug one layer up
- [x] T013 [US3] In `mobile/netclaw-mobile/lib/ncfed/message_feed.dart`, ensure a declined duplicate leaves the stored entry byte-for-byte unchanged including `read` state (FR-006, contract §2.2)
- [x] T014 [US3] In `mobile/netclaw-mobile/lib/ncfed/message_feed.dart`, reject rather than default a Message whose `pushedAt` is missing or unparseable, per data-model's validation rule — defaulting to "now" would mint a fresh identity per attempt and silently defeat dedup entirely
- [x] T015 [P] [US3] Extend `test/message_feed_test.dart`: duplicate `pushedAt` declined (FR-004, FR-005); read state preserved on re-delivery (FR-006); two distinct messages both stored; unparseable `pushedAt` rejected without corrupting the store
- [x] T016 [P] [US3] Add a structural test to `test/message_feed_test.dart` asserting `wireMessageFeed` is the ONLY registration site for `n2n/edge/message` (contract §4). `EdgeClient.on()` keeps only the LAST handler per method, so a second registration would silently disable live delivery with no error — highest-severity failure mode in this feature, cheapest to guard

**Checkpoint**: dedup enforced at the chokepoint. **Phase 5 is now unblocked.**

---

## Phase 5: User Story 2 — Renders without a live connection (P2)

**⛔ Do not start until Phase 4 is complete.** See the ordering rule above.

**Goal**: A pushed message is readable immediately, even with no connection to the
Border at all.

**Independent test**: With the device unable to reach the Border, push a message
and open the app — the message is visible.

- [x] T017 [US2] Create `mobile/netclaw-mobile/lib/ncfed/push_message_ingest.dart` that reconstructs a Message from the push data payload through the SAME wire parser the live channel uses — a second parser is forbidden (contract §3.5)
- [x] T018 [US2] In `mobile/netclaw-mobile/lib/ncfed/push_message_ingest.dart`, tolerate fully stringified values (contract §3.1). The sender emits `data: {k: str(v) for k, v in content.items()}`, so no field survives with its original type — the most likely source of a silent parse failure
- [x] T019 [US2] In `mobile/netclaw-mobile/lib/ncfed/push_message_ingest.dart`, route `content_type: 'approval'` to the approvals path and never to the feed (FR-009, contract §3.2)
- [x] T020 [US2] In `mobile/netclaw-mobile/lib/ncfed/push_message_ingest.dart`, reject malformed payloads without corrupting or truncating the stored feed (FR-010, contract §3.4); falling back to spec 106's replay is the correct outcome
- [x] T021 [US2] Register the **foreground** push handler in `mobile/netclaw-mobile/lib/main.dart`, routing through the ingest path. Must NOT register a channel handler (contract §4.2). **Background handler deliberately NOT implemented** — research R5 establishes that background execution for a data-carrying push is at the OS's discretion, so treating it as a delivery path would reintroduce the silent-loss class spec 106 removed. A push arriving while backgrounded still reaches the feed via replay, and US1 makes its tap open the message. Revisit only with real-device evidence that the OS runs the handler reliably
- [x] T022 [P] [US2] Create `test/push_message_ingest_test.dart`: fully stringified payload reconstructs; missing/unparseable `pushed_at` rejected; `approval` routes to approvals not the feed; malformed payload leaves the store intact
- [ ] T023 [US2] Verify on hardware — the single most valuable device test in this feature: block the phone's route to the Border, push, open the app, confirm the message is readable (SC-004); then restore connectivity and confirm **exactly one** copy survives replay (proves dedup + ingest work together) 🔌 DEVICE

**Checkpoint**: all three stories complete.

---

## Phase 6: Polish & Cross-Cutting

- [x] T024 Update the known-rough-edges table in `mobile/netclaw-mobile/TESTER-INSTRUCTIONS.md` — it currently advertises "Tapping a notification doesn't deep-link" as a known issue. Constitution XII requires this in the same PR, not as a follow-up
- [x] T025 [P] Update `mobile/netclaw-mobile/README.md` if it documents notification behavior
- [x] T026 [P] Confirm no Border regression: `python3 -m pytest tests/n2n/ -q` (expect 445+ passed, unchanged — this feature makes no Border change, so any movement means scope leaked)
- [x] T027 Full suite and analyzer: `cd mobile/netclaw-mobile && flutter test && flutter analyze`
- [x] T028 Run `python3 scripts/verify-spec-artifacts.py` and confirm exit 0 for this spec (CI-enforced, Principle XVI)
- [ ] T029 Walk `specs/107-push-render-deeplink/quickstart.md` end to end and confirm every "What done looks like" row 🔌 DEVICE

---

## Dependencies

```
Phase 1 (Setup)
      │
      ▼
Phase 2 (Foundational — PendingOpenIntent)
      │
      ├─────────────────────┬──────────────────────
      ▼                     ▼
Phase 3 (US1, P1)     Phase 4 (US3, P1)
 tap opens message     dedup  ── BLOCKS ──┐
      │                     │              │
      │                     ▼              │
      │              Phase 5 (US2, P2) ◀───┘
      │               instant render
      └─────────────────────┬──────────────
                            ▼
                    Phase 6 (Polish)
```

**Story completion order**: US1 and US3 in parallel → US2 → polish.

**The only hard cross-story dependency**: US3 → US2 (FR-008). US1 depends on
nothing but the foundational phase.

## Parallel execution examples

**After Phase 2, two developers:**

- Developer A: Phase 3 (T005–T010, US1)
- Developer B: Phase 4 (T011–T016, US3)

They touch disjoint files — `notification_deep_link.dart` + `main.dart` wiring vs
`message_feed.dart` — with the one exception that both eventually edit
`main.dart` (T007 and T021). Sequence those two.

**Within phases**, `[P]`-marked test tasks parallelize freely: T004, T008, T009,
T015, T016, T022 all live in separate files.

## Implementation strategy

**MVP is US1 alone.** It is P1, independently shippable, and fixes the thing the
operator actually notices — spec 106 already guarantees the message arrives, so
the remaining complaint is "I tapped it and it didn't take me there." US1 makes
the tap work while still relying on replay for the content.

**Then US3.** Also P1, and it is pure invariant-strengthening with no
user-visible change on its own — which makes it low-risk to land and a
prerequisite worth having regardless of whether US2 ever ships.

**US2 last**, and only after US3. It is the largest change, the only one that
touches OS background execution, and the one whose benefit (seconds of latency,
plus poor-connectivity resilience) is smallest relative to its risk. If schedule
pressure appears, US2 is the story to defer — spec 106 means deferring it loses
immediacy, never a message.

**Device budget.** Four tasks are marked 🔌 DEVICE (T001, T010, T023, T029).
iOS verification costs a TestFlight round trip, so batch them: reproduce once at
the start (T001), then verify all stories in one session at the end (T010, T023,
T029) rather than per-story.


---

## Status — 2026-08-13

**Implemented and verified in CI: 25 of 29 tasks.** All four outstanding tasks
are the 🔌 DEVICE ones (T001, T010, T023, T029); everything verifiable without
hardware is done and green.

| Gate | Result |
|---|---|
| `flutter test` | **280 passed** (was 234; +46 for this feature) |
| `flutter analyze` | No issues found |
| `pytest tests/n2n/` | **445 passed**, unchanged — confirms no Border-side scope leak |
| `verify-spec-artifacts.py` | exit 0 |
| `reconcile-mcp.py` | exit 0 |

**One deliberate scope reduction**, recorded in T021: the background push handler
was not implemented. Foreground ingest ships; background delivery is OS-discretionary
(research R5), so building on it would reintroduce silent loss. Nothing is lost —
a backgrounded push still reaches the feed via the Border's replay, and US1 makes
its tap open the message on arrival.

**Remaining device verification**, best done in one TestFlight session:

- T010 — app closed → push → tap → the named message opens; repeat backgrounded
- T023 — with the phone unable to reach the Border, push, open, message readable;
  then restore connectivity and confirm exactly one copy survives replay
- T029 — walk `quickstart.md`'s "What done looks like" table
