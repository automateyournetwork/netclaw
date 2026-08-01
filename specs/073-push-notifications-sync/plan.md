# Implementation Plan: Push Notifications, Unread Tracking & Cross-Device Sync for NetClaw Mobile

**Branch**: `073-push-notifications-sync` | **Date**: 2026-07-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/073-push-notifications-sync/spec.md`

## Summary

Adds real local push notifications (Feed/Chat/Approvals) to the phone app while it's running, with authenticated inline Approve/Deny actions on approval banners; the watch inherits these for free via standard watchOS notification/badge mirroring, with no new watch-side background-delivery code (preserving spec 072's `sendMessage`-only architecture). Adds per-item unread/acknowledge/delete state to the existing `MessageFeedStore`/`ConversationStore`, a combined app-icon badge, four new watch-relay methods for acknowledge/delete, a fix so watch-submitted chat turns are recorded into the shared conversation history (closing a real existing defect), and an on-demand "read aloud" control on the watch using `AVSpeechSynthesizer`.

## Technical Context

**Language/Version**: Dart 3.x / Flutter 3.x (extends `mobile/netclaw-mobile/`, SDK constraint `^3.12.2` per pubspec.yaml); Swift 5.0 (extends the `WatchApp Watch App` target from spec 072); Python 3.10+ (the one Border-side addition, `authorization.py`/`service.py`, matching specs 052-072)
**Primary Dependencies**: `flutter_local_notifications` (new — local notification posting, Darwin/Android notification actions, iOS badge control); existing `firebase_messaging`/`firebase_core` (unchanged, remote-push path stays out of scope per Assumptions); existing `app_links` (extended, not replaced, per research D4); watchOS `AVSpeechSynthesizer` (system framework, no new dependency, watch-side only)
**Storage**: Extends the existing phone-local JSON-Lines `MessageFeedStore` and whole-file JSON `ConversationStore` (both under the app's documents directory) with new fields — no new store, no new database
**Testing**: `flutter test`/`flutter analyze` (existing suite, extended); `python3 -m pytest tests/n2n` (existing suite, extended for the one Border-side addition)
**Target Platform**: iOS 15+ (phone, existing), watchOS 10+ (watch, existing per spec 072's `WATCHOS_DEPLOYMENT_TARGET`)
**Project Type**: Mobile app (Flutter phone app + native watchOS companion) — extends spec 072's structure, no new project
**Performance Goals**: N/A beyond "a notification appears within a few seconds of the triggering event" (SC-001) — no throughput/latency target beyond normal interactive-app responsiveness
**Constraints**: Must not introduce any new watch-side background-delivery/push architecture (FR-010, explicitly preserving spec 072 research D2's `sendMessage`-only decision); notification-action authentication must reuse the existing biometric-confirmation code path, not a new one (FR-004, research D2)
**Scale/Scope**: Single-operator personal-use app (unchanged from every prior mobile spec 066-072) — no concurrency/multi-tenant scale target

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| IV. Immutable Audit Trail | The `already_resolved` addition (D6) makes the Border's approval-resolve response MORE informative, not less; the underlying GAIT-audited `resolve_approval()` call itself is unchanged | PASS |
| V. MCP-Native Integration | No new MCP server or tool; mobile-client-only feature exactly like specs 071/072 | PASS (N/A) |
| VI. Multi-Vendor Neutrality | N/A — mobile client, not a vendor integration | PASS (N/A) |
| IX. Security by Default | FR-004/research D2: notification-action Approve/Deny reuses the exact same fresh, never-cached biometric/passcode confirmation as the in-app flow — a new entry point into existing security logic, not new/weaker logic. FR-005 ensures an already-resolved approval can never be silently double-resolved or misreported. | PASS |
| XI. Full-Stack Artifact Coherence | Not a new capability in the MCP-server/skill sense (no catalog/install-steps/HUD entries apply, exactly as specs 071/072 established) — `README.md`'s mobile section update is the one artifact touchpoint in scope | PASS (scoped) |
| XII. Documentation-as-Code | README update lands in the same PR as the implementation, not a follow-up | PASS |
| XIII. Credential Safety | No new credentials — explicitly out of scope (real Firebase/APNs credentials remain a separate, undone operator prerequisite; this feature only adds local, credential-free notifications) | PASS |
| XV. Backwards Compatibility | `acknowledged`/`origin` fields are additive with safe missing-key defaults (research D5); `already_resolved` is additive and ignorable by existing callers (research D6); no existing field/behavior changes meaning | PASS |
| XVI. Spec-Driven Development | Follows `/speckit.specify` → `/speckit.clarify` → `/speckit.plan` | PASS |
| XVII. Milestone Documentation | Deferred to post-`/speckit.implement`, per the standard SDD lifecycle | N/A (later) |

No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/073-push-notifications-sync/
├── plan.md                          # This file
├── research.md                      # Phase 0 output (D1-D8)
├── data-model.md                    # Phase 1 output
├── quickstart.md                    # Phase 1 output
├── contracts/
│   └── watch-relay-extensions.md    # Phase 1 output — new relay methods, notification payload, Border addition
└── tasks.md                         # Phase 2 output (/speckit.tasks — not created by /speckit.plan)
```

### Source Code (repository root)

```text
mobile/netclaw-mobile/
├── lib/
│   ├── ncfed/
│   │   ├── message_feed.dart              # EXTEND: acknowledged field, acknowledge()/delete()/unreadCount
│   │   ├── conversation_store.dart        # EXTEND: acknowledged/origin fields, acknowledge()/delete()/unreadCount
│   │   ├── watch_relay.dart                # EXTEND: 4 new methods (feed/history acknowledge+delete)
│   │   ├── notification_deep_link.dart     # EXTEND: generalize to a shared dispatcher (local + Firebase taps)
│   │   ├── local_notifications.dart        # NEW: flutter_local_notifications wiring, badge computation
│   │   └── approval_client.dart            # EXTEND: notification-action entry point reuses existing resolve() + biometric gate
│   ├── screens/
│   │   ├── feed_screen.dart                 # EXTEND: unread indicator, acknowledge/delete UI
│   │   └── chat_screen.dart                 # EXTEND: unread indicator, acknowledge/delete UI
│   └── main.dart                            # EXTEND: badge wiring, generalized _unreadFeed→combined badge, notification init
├── test/
│   ├── local_notifications_test.dart        # NEW: badge computation from unread counts
│   ├── message_feed_test.dart               # EXTEND: acknowledge/delete/unreadCount, missing-key migration default
│   ├── conversation_store_test.dart         # EXTEND: acknowledge/delete/unreadCount, origin field, migration default
│   ├── notification_deep_link_test.dart     # EXTEND: dispatcher covers both Firebase and local-notification payloads
│   └── watch_relay_test.dart                 # EXTEND: 4 new acknowledge/delete methods, ask-submit/status now persist to ConversationStore
├── ios/
│   ├── WatchApp Watch App/
│   │   ├── SpeechPlayback.swift            # NEW: AVSpeechSynthesizer wrapper
│   │   ├── FeedView.swift                   # EXTEND: unread indicator, acknowledge/delete/read-aloud controls
│   │   ├── HistoryView.swift                # EXTEND: unread indicator, acknowledge/delete/read-aloud controls
│   │   └── AskView.swift                    # EXTEND: read-aloud control on the answer view
│   └── Runner/Info.plist                    # EXTEND: notification-related entitlements if flutter_local_notifications requires new keys
└── pubspec.yaml                              # EXTEND: add flutter_local_notifications

mcp-servers/protocol-mcp/bgp/federation/
├── authorization.py                          # EXTEND: resolve_approval() reports whether it actually updated a row
└── service.py                                # EXTEND: _edge_on_approval_resolve threads already_resolved through

tests/n2n/test_edge_approval.py               # EXTEND: already_resolved coverage
```

**Structure Decision**: Pure extension of the existing spec-066/067/072 mobile-client structure — no new top-level directory, no new project, no new MCP server. The only cross-cutting new file is `lib/ncfed/local_notifications.dart` (phone-side) and `SpeechPlayback.swift` (watch-side); everything else is additive changes to files this feature's research/data-model docs already name precisely.

## Complexity Tracking

*No entries — Constitution Check has no violations to justify.*
