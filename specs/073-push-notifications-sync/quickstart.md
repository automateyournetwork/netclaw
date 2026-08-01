# Quickstart: Push Notifications, Unread Tracking & Cross-Device Sync

## Prerequisite

Builds on spec 072's already-verified state: the phone app and watch companion both build/run/enroll against a live Border on real hardware (a physical iPhone + Apple Watch pair). Nothing here re-does that setup.

## Manual walkthrough

1. **Notification permission**: fresh install, first launch — confirm the OS notification-permission prompt appears once; grant it. Confirm every other capability (Feed, Chat, Approvals, History) still works exactly as before if this step is instead denied (FR-020).
2. **Feed push notification**: push a text Feed message from the Border while the app is backgrounded (not terminated). Confirm a banner appears with a one-line content preview (respecting the device's lock-screen "Show Previews" setting, FR-021), the phone's home-screen app icon badge increments by one, and — with the watch's screen not showing the NetClaw app — the same banner mirrors to the watch. Separately, look at the watch's own home screen (press the Digital Crown) and confirm the NetClaw watch app icon shows that same badge number (FR-009) — this is the one badge check this feature explicitly assumes works via standard OS behavior rather than custom code, so it must be checked on real hardware, not assumed.
3. **Chat answer notification**: submit a chat question, background the app, wait for the Border's answer. Confirm the notification banner appears, the badge increments, and tapping the banner opens directly to that answer (FR-006), not just the Chat tab.
4. **Approval notification with inline actions**: trigger a Border-side approval while backgrounded. Confirm the banner shows inline Approve/Deny buttons and does NOT affect the badge count (Approvals are excluded, per spec Assumptions). Tap Approve; confirm the device requires on-device authentication (Face ID/passcode) before the approval actually resolves (FR-004) — a cancelled authentication must leave it pending. Confirm the Border's audit record shows the resolution.
5. **Already-resolved race**: resolve the same approval from inside the app first, then tap the (now-stale) notification's Approve/Deny button. Confirm a clear "already resolved" outcome (FR-005), not a crash or a confusing second resolution attempt.
6. **Unread indicators and acknowledge**: with several unacknowledged Feed messages and chat answers present, confirm both are visually distinguished from acknowledged items on the phone's Feed/Chat tabs AND the watch's Feed/History tabs. Acknowledge one item from the watch; confirm it clears from the badge count and no longer shows as unread on the phone's next view, with no explicit "sync" action taken (FR-014).
7. **Delete**: delete one Feed message and one chat turn from the phone. Confirm both are gone from the watch's Feed/History on its next refresh.
8. **Watch unreachable during an action**: put the phone out of Bluetooth/Wi-Fi range of the watch (or force-quit the phone app); attempt to acknowledge/delete from the watch. Confirm the existing "can't reach iPhone" state appears (FR-015), not a silent failure.
9. **Watch-originated chat history (the defect fix)**: submit a question from the watch's Ask tab; wait for the answer. Confirm it appears in the phone's Chat tab AND the watch's own History tab (FR-016) — this is the one item in this feature that is a correctness fix for existing, already-shipped behavior, not new capability.
10. **Voice playback**: on the watch, open a text Feed message and tap "read aloud" (FR-017); confirm it's spoken. Open a photo-content Feed message and tap "read aloud"; confirm it describes the content type rather than failing (FR-019). Confirm nothing is ever spoken without that explicit tap — not on a push arriving, not on opening a tab (FR-018).
11. **Notification burst**: trigger several Feed messages/approvals in quick succession from the Border. Confirm each gets its own individual notification (FR-007a) — no collapsed summary — and no duplicate notification for any single item (FR-007).
12. **Real hardware verification**: repeat steps 2-11 on the real iPhone + Apple Watch pair already used in spec 072's verification, not just in Debug/Simulator — record the outcome (verified, or blocked-with-reason) either way, matching this project's established "verify on real hardware, don't assume" standard.

## Automated checks

```bash
cd mobile/netclaw-mobile
flutter analyze
flutter test test/watch_relay_test.dart
flutter test test/message_feed_test.dart      # extended: acknowledge/delete, unreadCount, migration default
flutter test test/conversation_store_test.dart # extended: acknowledge/delete, unreadCount, migration default, origin field
flutter test test/notification_deep_link_test.dart  # extended dispatcher covering both Firebase and local-notification payloads
flutter test   # full suite — zero regressions in existing tests

cd /Users/john.capobianco/netclaw
python3 -m pytest tests/n2n/test_edge_approval.py -q   # extended: already_resolved field
```

No automated test exists (or is expected) for the watch's native "read aloud" `AVSpeechSynthesizer` wiring or the OS-level notification permission/badge/mirroring behavior itself — matching this project's established precedent (spec 072) that native platform UI/OS-behavior surfaces with no meaningful headless-test hook are verified manually instead.

## Success signals (from spec)

- SC-001: steps 2-4 — a banner appears within a few seconds on whichever device the operator is near.
- SC-002: step 4 — a routine approval resolved entirely from the banner, authentication included, no app-open required.
- SC-003: step 6 — unread vs. acknowledged is visually obvious on both devices without re-reading anything.
- SC-004: step 9 — zero watch-originated questions missing from the phone's chat history.
- SC-005: steps 6-7 — an action on either device is correctly reflected on the other with no manual sync step.
- SC-006: step 10 — read-aloud works with a single deliberate tap, never triggers unprompted.
