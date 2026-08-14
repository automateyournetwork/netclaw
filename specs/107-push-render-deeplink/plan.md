# Implementation Plan: Notification tap opens the message it names

**Branch**: `107-push-render-deeplink` | **Date**: 2026-08-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/107-push-render-deeplink/spec.md`

## Summary

Spec 106 made every pushed message survive to the device. This feature makes the
device do the right thing with it: a notification tap opens the message it names
(P1), the feed never shows a message twice (P1), and a pushed message renders
without waiting for a live connection (P2).

The approach is one shared *pending intent* for notification taps — record the
tapped message's identifier, resolve it when that message is present or arrives,
give up after a bounded wait — plus deduplication moved into the feed store's
single append chokepoint so a second writer cannot double-record. The FCM data
payload the Border already sends is then consumed through the existing wire
parser, which is safe only *because* dedup landed first.

No Border change. Entirely within `mobile/netclaw-mobile`.

## Technical Context

**Language/Version**: Dart 3.x / Flutter, SDK constraint `^3.12.2` (from `pubspec.yaml`)
**Primary Dependencies**: No new packages. Reuses `firebase_messaging ^16.4.3`, `firebase_core ^4.12.1`, `flutter_local_notifications ^22.2.0`, all already present. Continues the 066–073 and 099 precedent of adding no dependency a story does not strictly require.
**Storage**: Existing on-device stores, extended not replaced — `MessageFeedStore` (JSON-Lines) and, unchanged, `ConversationStore`. No migration of stored history.
**Testing**: `flutter_test` (30 suites in `test/`, several direct analogues); `integration_test` for the device-only cases
**Target Platform**: iOS 15+ and Android (min SDK 21), matching the existing build config
**Project Type**: Mobile app (Flutter), single package
**Performance Goals**: Pushed message readable within 2s of the app becoming interactive (SC-003); no added latency when the message is already stored
**Constraints**: Must not weaken spec 106's guarantee that no delivered message is absent from the feed (SC-006); ships on the app's release cadence, not a server restart, because the iOS build is TestFlight-gated
**Scale/Scope**: 3 user stories; ~4 existing files touched, 1 new; no new screens

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Applies | Assessment |
|---|---|---|
| **IV. Immutable Audit Trail** | Yes | No operation becomes silent. Delivery is already audited Border-side (`edge_push/queue_replay` recorded per replay, observed in production). This feature changes only device-side rendering of already-audited messages. **A deduplicated message must not suppress an audit record** — dedup is a display/storage concern on the device, and the Border's trail is untouched. |
| **VIII. Verify After Every Change** | Yes | Every FR maps to a test in Phase 1's contract list; R7 partitions what the Dart suite can verify from what needs hardware, so verification is planned rather than assumed. |
| **XI. Full-Stack Artifact Coherence** | Yes | Mobile-only feature: no MCP server, no skill, no catalog entry, no `config/openclaw.json` change. Doc surface is `mobile/netclaw-mobile/README.md` plus the known-rough-edges table in `TESTER-INSTRUCTIONS.md`, which currently lists "Tapping a notification doesn't deep-link" as a known issue — that row must be updated in the same PR. |
| **XII. Documentation-as-Code** | Yes | See above; docs land in the same PR as the code. |
| **XV. Backwards Compatibility** | Yes | Additive. Existing stored feeds remain readable; dedup only ever *declines* a write. No new dependency, so no version conflict surface. The one real hazard is displacing the single `n2n/edge/message` handler registration (R6) — guarded by a structural test. |
| **XVI. Spec-Driven Development** | Yes | This plan completes specify → plan → task. `scripts/verify-spec-artifacts.py` is CI-enforced and requires `plan.md`, `research.md`, and tasks. |
| I, II, III, V, VI, VII, IX, X, XIII, XIV, XVII | No | No device interaction, no config change, no MCP server or skill, no credentials, no external communication. Not a milestone warranting a blog post (a follow-on fix to 106). |

**Gate result**: PASS, no violations. Complexity Tracking section omitted as
unnecessary.

## Project Structure

### Documentation (this feature)

```text
specs/107-push-render-deeplink/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── notification-intent.md
├── checklists/
│   └── requirements.md  # from /speckit.specify
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code

```text
mobile/netclaw-mobile/
├── lib/ncfed/
│   ├── message_feed.dart              # MODIFY — dedup in the append chokepoint (R3);
│   │                                  #   wireMessageFeed stays the ONLY
│   │                                  #   n2n/edge/message registration site (R6)
│   ├── notification_deep_link.dart    # MODIFY — remote + local tap paths converge on
│   │                                  #   the shared pending intent (R1, R6)
│   ├── pending_open_intent.dart       # NEW — record/resolve/expire a tapped identifier
│   └── push_message_ingest.dart       # NEW — reconstruct a message from the FCM data
│                                      #   payload; approval routing preserved (R4)
├── lib/main.dart                      # MODIFY — wire the foreground/background
│                                      #   handlers and the intent into HomeShell
└── test/
    ├── message_feed_test.dart              # EXTEND — dedup, read-state preservation
    ├── notification_deep_link_test.dart    # EXTEND — arrive-after-tap, timeout
    ├── push_message_ingest_test.dart       # NEW — stringified + malformed payloads
    └── pending_open_intent_test.dart       # NEW — resolution ordering, expiry
```

**Structure Decision**: Existing Flutter single-package layout, unchanged. New
code goes in `lib/ncfed/` beside the modules it collaborates with, matching how
066–073 organized every prior edge-node concern. Two new files rather than
growing `notification_deep_link.dart`, because the intent mechanism is used by
both tap paths and the ingest path is a separate concern with its own failure
modes — Principle VII (single well-defined function per unit) argues for the
split.

## Phase 1 Design

### Contract

Interface contract for the intent mechanism and the ingest path is in
[`contracts/notification-intent.md`](contracts/notification-intent.md). The app
exposes no external API, so this is an internal-collaboration contract — the
appropriate form for an application per the plan template's guidance.

### Entities

See [`data-model.md`](data-model.md). Three entities, all already existing in some
form: **Message** (gains an explicit identity rule), **PendingOpenIntent** (new,
in-memory), **Feed** (gains the at-most-once invariant).

### Requirement → verification map

| FR | Verified by | Where |
|---|---|---|
| FR-001, FR-002 | intent resolves when message arrives after tap | `notification_deep_link_test.dart` |
| FR-003 | intent expires, feed shown | `pending_open_intent_test.dart` |
| FR-004, FR-005 | append declines a duplicate `pushed_at` | `message_feed_test.dart` |
| FR-006 | read state preserved on re-delivery | `message_feed_test.dart` |
| FR-007 | message reconstructed from data payload | `push_message_ingest_test.dart` |
| FR-008 | ordering enforced by task phasing, not asserted in code | `tasks.md` |
| FR-009 | `content_type: 'approval'` routes to approvals | `push_message_ingest_test.dart` |
| FR-010 | malformed payload rejected, store intact | `push_message_ingest_test.dart` |
| FR-011 | no forced open without a tap | `notification_deep_link_test.dart` |
| FR-012 | platform parity | device verification (R7) |
| — | single `n2n/edge/message` registration site | structural test, `message_feed_test.dart` |

### Post-design Constitution re-check

**PASS.** The design adds no MCP server, skill, dependency, or credential
surface. Two clarifications the design surfaced:

1. **Dedup must not be mistaken for an audit gap** (Principle IV). The Border's
   trail records every delivery including replays; the device declining a
   duplicate *write* does not erase anything. Recorded in `data-model.md` so an
   implementer does not "fix" it by suppressing the Border-side record.
2. **`TESTER-INSTRUCTIONS.md` currently advertises this bug** as a known rough
   edge. Principle XII requires that row change in the same PR, so it is a task,
   not a follow-up.

## Complexity Tracking

Not applicable — Constitution Check passed with no violations.
