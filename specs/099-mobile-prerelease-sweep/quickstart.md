# Quickstart: Verifying the Mobile Pre-Release Sweep

Manual, on-device verification steps per story — mirrors the acceptance scenarios in spec.md. Run after `/speckit.implement` completes.

## Story 1 — Badge reconciliation

1. Force a nonzero OS badge: send yourself a Feed message via the Border while the app is fully force-quit, wait for the push, don't open the app.
2. Launch the app fresh. Badge must correct to the true unread count within 5 seconds.
3. Background the app (don't force-quit), trigger another message from another device/session, then bring the app to the foreground without touching the new item. Badge must reflect the true count on resume.
4. Read everything. Confirm badge reaches exactly 0, not negative, not stuck.

## Story 2 — Non-gated App Store readiness

1. Archive the app (`Product > Archive` in Xcode, or the new `scripts/mobile-release-archive.sh` once it exists).
2. Validate the archive via Xcode Organizer's "Validate App" (works without a paid account for the checks this story covers: privacy manifest, usage strings, encryption declaration).
3. Confirm no validation errors reference `PrivacyInfo.xcprivacy`, missing usage descriptions, or `ITSAppUsesNonExemptEncryption`.

## Story 3 — Paid-account-gated work (run only once the paid account is active)

1. Confirm `CODE_SIGN_ENTITLEMENTS` is wired and the archive signs with the push entitlement.
2. Send a real push notification to a distribution-signed build; confirm delivery.
3. Run `scripts/mobile-release-archive.sh` end-to-end and confirm it produces an uploadable `.ipa`.
4. Confirm today's free/Personal-team debug build still runs unaffected (FR-007) — this MUST still work identically to before this story's changes.

## Story 4 — CI gate

1. Open a throwaway PR that breaks one existing Dart test — confirm `mobile-ci.yml` fails and blocks merge.
2. Revert that break, instead introduce an analyzer violation — confirm the analyze step fails.
3. Revert that, instead break `WatchRelayPlugin.swift`'s build — confirm the watch-scheme `xcodebuild` step fails.
4. Open a clean PR — confirm all steps pass.

## Story 5 — Dashboard

1. With an enrolled, connected device, open the app — Dashboard must be the first thing shown (default landing tab).
2. Confirm it shows: Border connection health, this device's identity/enrollment scope, unread message count, pending approval count.
3. Turn off networking / stop the Border — confirm the Dashboard shows a clear disconnected state, not stale "last known good" data presented as current.
4. On a fresh, never-enrolled install, confirm the Dashboard shows a clear "not yet enrolled" state, not blank or errored.

## Story 6 — Notification actions (verification, not new build — see research.md R1)

1. Trigger a pending-approval notification, tap Approve directly on the banner without opening the app — confirm Face ID prompt appears, then the approval resolves and is reflected in-app, on watch, and at the Border.
2. Repeat for Deny.
3. Resolve the same approval from the in-app Approvals screen first, then tap Approve on a (now stale) queued notification for it — confirm the app reports it's already resolved rather than double-applying.

## Story 7 — Live Activity / Lock Screen

1. Trigger a pending approval, lock the phone — confirm a Live Activity appears on the Lock Screen showing that a pending approval exists, without exposing approval details.
2. Resolve the approval from any surface (phone, watch, or notification) — confirm the Live Activity clears/ends promptly.

## Story 8 — Watch complication

1. Add the NetClaw complication to a watch face.
2. Trigger one or more pending approvals — confirm the complication shows the current count.
3. Resolve all pending approvals — confirm the complication returns to zero/no-pending state.
