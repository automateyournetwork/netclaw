# Quickstart: NCFED Edge Node Foundation + Border-to-Phone Push Channel

Prove enrollment and push end-to-end, then the automated checks.

## Manual walkthrough

1. **Confirm domain-verified cert is live.** On the Border, confirm feature 060's
   domain-verified certificate is active (`netclaw.automateyournetwork.ca` or equivalent) —
   this feature reuses it as-is; it does not provision one.
2. **Issue an edge enrollment QR.** Run the enrollment CLI with the new `--edge` flag; confirm
   a QR code renders (terminal ASCII, and/or a saved PNG) rather than a plain-text token.
3. **Enroll the phone.** From NetClaw Mobile's first-launch screen, scan the QR. Confirm the
   app refuses to proceed if it deliberately points at a Border whose certified domain doesn't
   match the QR's `claw_domain` (test this by pointing the QR at a mismatched host, expect a
   hard abort, not a warning-and-continue).
4. **Confirm the member row.** On the Border, list members and confirm the new row has
   `node_type=edge`, a pinned key, and a fingerprint — indistinguishable in kind from any
   other member's pinning, just a new `node_type` value.
5. **Confirm heartbeat.** Disconnect the phone (airplane mode) and confirm the Border's health
   view marks it unhealthy/disconnected within the configured heartbeat-miss window (T010's
   implementation sets this; verify against whatever interval it actually uses, not a guess),
   without any skill having been delivered to it.
6. **Push a message.** From Slack (or the TUI/HUD), ask the agent to notify the phone with a
   short text message (`n2n_notify_phone`). Confirm it arrives in the app's message feed.
   Repeat with a voice clip and an image.
7. **Confirm no mirroring.** Send an ordinary message through the same Slack conversation
   *without* asking it to be pushed to the phone. Confirm it does NOT appear on the phone.
8. **Confirm backgrounded delivery.** Background the app (or lock the phone), push another
   message, and confirm a platform push notification arrives and opens directly to it.
9. **Confirm reconnect.** Toggle airplane mode off and on while the app is foregrounded;
   confirm the connection re-establishes automatically, with backoff, and a message pushed
   immediately after reconnection is delivered normally.
10. **Confirm revocation.** Remove/quarantine the edge member using the existing operator
    action for removing any member; confirm the phone can no longer connect and no further
    pushes are attempted to it.

## Automated checks (pytest + flutter test)

```bash
cd ~/netclaw
python3 -m pytest tests/n2n/test_edge_enrollment.py tests/n2n/test_edge_push.py \
                   tests/n2n/test_edge_heartbeat.py -q

cd mobile/netclaw-mobile
flutter test
```

Expected coverage:
- Enrollment refuses on domain/certificate mismatch before any token exchange is attempted.
- Token is single-use; a second enrollment attempt with the same token fails.
- `node_type='edge'` rows satisfy `BASE_FLOOR` via heartbeat/self-status responses alone, with
  no skill delivery.
- A pushed message reaches a connected phone; an un-designated message never does (explicit
  push, not mirroring).
- A push to a disconnected edge node falls back to a notification-delivery path rather than
  being dropped.
- The Dart reconnect backoff matches the ported pattern's bounds (5s→60s) and actually
  reconnects after a simulated drop.

## Success signals (from spec)

- SC-001: QR-to-enrolled in under two minutes, zero manual token copy-paste, zero successful
  enrollments against a mismatched certificate.
- SC-002: 100% of explicitly-designated messages reach the phone; 0% of non-designated
  traffic does.
- SC-003: automatic reconnect after a connectivity loss, no operator action.
- SC-004: a backgrounded push notification opens directly to the pushed content.
- SC-005: revocation via the existing member-removal action fully blocks further delivery.
- SC-006: heartbeat gives the Border the same health-monitoring guarantee `BASE_FLOOR` gives
  an agent member.

## T043: automated coverage as of implementation — mapped to SC-001…SC-006

`python3 -m pytest tests/n2n -q` → 249 passed, 0 regressions (was 237 before this feature).

| SC | Covered by | Notes |
|----|------------|-------|
| SC-001 | `test_edge_enrollment.py::test_qr_enrollment_creates_edge_member_single_use`, `::test_domain_mismatch_aborts_before_token_exchange` | The "under two minutes" wall-clock claim and the real QR-scan step are not automatable — need step 2 of the manual walkthrough on a real device. Zero-mismatched-cert-success and single-use-token ARE fully automated. |
| SC-002 | `test_edge_push.py::test_push_to_edge_delivers_explicit_message_only`, `::test_n2n_edge_message_has_no_inbound_handler`, `::test_all_content_types_round_trip` | Explicit-push-only and all 3 content types verified end-to-end over a real WebSocket. |
| SC-003 | `reconnect_supervisor_test.dart` (backoff bounds + reset-on-success) | The Dart reconnect supervisor's *logic* is unit-tested; an actual airplane-mode reconnect needs step 9 of the manual walkthrough on a real device. |
| SC-004 | `notification_deep_link_test.dart::findMessageForNotificationData` | Only the tap-matching logic is testable here — real FCM/APNs delivery and app-backgrounding behavior are unverified (no real Firebase/Apple credentials or device in this environment); needs step 8 on a real device. |
| SC-005 | `test_edge_enrollment.py::test_revoked_edge_member_blocks_further_delivery`, `test_edge_push.py::test_push_to_edge_on_disconnected_member_fails_cleanly_not_hangs` | Fully automated: removal blocks both a valid-signature reconnect attempt and subsequent push/heartbeat. |
| SC-006 | `test_edge_heartbeat.py::test_disconnected_edge_node_reflects_unreachable`, `::test_connected_heartbeating_edge_node_with_zero_skills_passes_base_floor` | Both the negative (disconnected → unreachable) and positive (connected, zero skills, still healthy) cases are covered. |

### T045 status — partially exercised against a throwaway Border, not a full walkthrough

A debug APK was built, installed, and launched on an Android emulator against a fully
isolated throwaway Border (separate `HOME`, SQLite DB, and ports — never the live
production daemon): steps 1-4 of the walkthrough above (domain-verified cert, QR
enrollment, the app refusing a mismatched domain, and the resulting member row showing
`node_type=edge` with a pinned key) were confirmed for real this way, and a full
`n2n/edge/ask` handshake (feature 067) round-tripped over the same connection — proving
the transport, enrollment, and pinned-key trust model work end-to-end on real Android,
not just in unit tests.

Steps 6-9 remain genuinely unexercised here, not because of the production-daemon
restriction (a throwaway daemon covers that) but because they need infrastructure this
environment doesn't have: step 6/7 (push via `n2n_notify_phone`, no-mirroring) needs a
live Slack/TUI conversation actually asking the agent to push, which wasn't set up
against the throwaway daemon; step 8 needs real FCM/APNs credentials (`.env.example`'s
`FCM_SERVICE_ACCOUNT_JSON`/`APNS_*`), which don't exist in this repo; step 9 needs a
real network-connectivity drop (airplane mode) on physical or real emulator networking,
not exercised this pass. Step 10 (revocation) IS fully covered, but only by the
automated `test_revoked_edge_member_blocks_further_delivery` test above, not manually.

iOS Secure Enclave key generation/signing (`EdgeIdentityPlugin.swift`) remains entirely
unexercised — that requires Xcode, which only runs on macOS, per T044's own note.

T045's checkbox stays unchecked: a genuine end-to-end 10-step walkthrough needs live
push credentials and a Slack conversation wired to the throwaway/real Border, which is
follow-up work, not something this pass silently declared done.
