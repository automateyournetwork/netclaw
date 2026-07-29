# Quickstart: NCFED Mobile Biometrics and Capture

## Manual walkthrough

1. **Register capture capabilities**: from the app's Settings, enable photo + audio capture,
   disable video. Confirm the Border's view of the member's `scope` shows only the enabled
   two — video is absent entirely, not present-but-disabled.
2. **Trigger a `requires_approval` grant**: confirm a prompt reaches the phone (foreground) or
   a push notification (backgrounded) with device/change/reason/agent/risk visible.
3. **Approve with biometric**: tap approve, complete Face ID/BiometricPrompt, confirm the
   audit trail shows `resolved_via=biometric`.
4. **Fail the biometric**: cancel/fail authentication; confirm the approval remains pending —
   not approved, not denied.
5. **Resolve via CLI while a phone prompt is pending**: `netclaw` CLI `n2n_approve`; confirm
   the phone reflects it as already resolved rather than staying actionable.
6. **Phone-initiated capture**: take a photo, attach it to a typed question; separately, send
   a bare photo with no text. Confirm both reach the Border and produce a response reflecting
   the image.
7. **Border-requested capture**: submit a request needing a phone-advertised capability;
   confirm the phone's native capture UI activates and the result flows back attributed to
   the phone. Decline the OS permission prompt on a second attempt; confirm an explicit
   failure, not a hang.
8. **Disconnected phone**: with the phone offline, request its capture capability from the
   Border; confirm a clean "capability not available" failure, not a hang.

## Automated checks

```bash
cd ~/netclaw
python3 -m pytest tests/n2n/test_edge_approval.py tests/n2n/test_edge_capture.py -q

cd mobile/netclaw-mobile
flutter test
```

## Success signals (from spec)

- SC-001/SC-002: biometric resolution recorded 100%; 0% resolved without successful local auth.
- SC-003/SC-004: phone-initiated capture reaches the Border 100% (healthy connection);
  Border-requested capture never silently hangs (0%).
- SC-005: no successful biometric auth ever exposes the enrollment key (verified by code
  review — `local_auth` and `EdgeIdentity` share no class/state, see research D7).
- SC-006: declined OS permission produces an explicit failure in both directions.
- SC-007: 100% of captures fit the existing 16 MiB channel bound (capped at capture time).
- SC-008: a disabled capture type is verifiably absent from the Border's view of `scope`.

## T028: automated coverage as of implementation — mapped to SC-001…SC-008

Full n2n suite: `python3 -m pytest tests/n2n -q` → 266 passed, zero regressions
(the 9 new tests below plus every 052–067 test unchanged). Mobile suite:
`flutter test` → 45 passed (13 new for this feature, plus every 066/067 test
unchanged).

| SC | Automated coverage | Notes |
|----|---------------------|-------|
| SC-001/SC-002 | `test_edge_approval.py::test_edge_approval_resolve_calls_existing_resolve_approval_unchanged`, `::test_first_resolution_wins_cli_then_phone`; `approval_client_test.dart`'s "a failed/cancelled biometric attempt never triggers n2n/edge/approval_resolve" (parameterized over every non-`true` return: `false`, an exception, a delayed `false`) | `resolve_approval`'s pre-existing `WHERE status='pending'` clause is what makes "first resolution wins" true regardless of biometric vs CLI order — proven directly, not assumed. Whether a *specific* device's Face ID/fingerprint sensor itself fired is outside what CI can check; the Dart test instead proves the wire call structurally never fires without the `authenticate` callback returning `true`. |
| SC-003/SC-004 | `test_edge_capture.py::test_delegate_resolves_edge_node_and_calls_capture_not_tasks_submit`, `::test_declined_capture_surfaces_as_explicit_failure`; `capture_client_test.dart`'s full "captureAndAsk (US2, phone-initiated)" and "n2n/edge/capture handler (US3, Border-requested)" groups (7 tests) | Both directions' declined/cancelled path returns an explicit `decision: 'declined'`/raises, never an empty success — directly exercised, not inferred. |
| SC-005 | Not independently automated — verified by code review (research D7): `approval_client.dart`/`capture_client.dart`/`approvals_screen.dart` import nothing from `edge_identity.dart`, and `grep -rn EdgeIdentity` across the new 068 files returns no hits. | A negative/absence property; a test asserting "this file doesn't import X" would be weaker than the review already performed. |
| SC-006 | `capture_screen.dart`'s `_init()`/`_shutter()` catch blocks (camera-permission/capture-failure → explicit `_error` state, no silent hang) plus `capture_client_test.dart`'s declined-capture cases on both sides | The real OS permission dialog itself isn't invokable under `flutter test`; T030's manual walkthrough covers the actual dialog. |
| SC-007 | `test_edge_capture.py::test_declined_capture_surfaces_as_explicit_failure` (server-side cap, via `kMaxCaptureBytes`-equivalent check in `delegate_to_edge`'s wire contract), `capture_client_test.dart`'s "a capture exceeding the size cap is refused, never sent" and "an oversized capture is declined server-side too, not just client-side" | Both the phone-side pre-check and the (defense-in-depth) handler-side check are exercised, not just one. |
| SC-008 | `test_edge_capture.py::test_disabled_capability_invisible_to_router`, `::test_set_capture_capabilities_rejects_unknown_name`; `capability_registration_test.dart`'s all 3 cases | Direct coverage — inspects `RiskRouter.candidates()`/`member.scope` itself, not just an attempted request's outcome. |

### T030 — manual-only, deferred

The full numbered walkthrough above needs real biometric hardware (Face ID/
fingerprint sensor) and a real camera — neither exists in this Linux/WSL2
dev environment's Android emulator (the emulator's virtual camera and
`local_auth`'s biometric enrollment both require host-level setup this
session doesn't have). Steps 1, 5, and 8 (capability registration/toggle,
CLI-resolves-while-phone-pending, disconnected-phone capability-not-available)
are fully covered by the automated tests above and don't need to be repeated
manually. Steps 2-4, 6-7 (the actual push arriving, a real biometric
success/failure, and a real photo reaching the Border) require the Mac/iOS
session or a properly provisioned Android device and should be run there.

## Post-implementation hardening (same session, after T001-T030)

A few real gaps surfaced from actually trying to run the app end-to-end, fixed
before wrap-up:

- **App identity**: the app shipped the stock Flutter template icon/splash and
  launcher label (`netclaw_mobile`) on both platforms. Fixed: a real claw-mark
  icon (`assets/icon/icon.png`, generated via `flutter_launcher_icons`/
  `flutter_native_splash`, see `ASSETS.md`), the launcher label changed to
  "NetClaw" (`AndroidManifest.xml`/`Info.plist`), and the `MaterialApp` theme
  seed changed from an arbitrary `Colors.deepPurple` to the icon's own orange
  (`#E65733`). `empty_feed.png`/`empty_approvals.png` illustrations wired into
  `FeedScreen`/`ApprovalsScreen`'s empty states via a new shared `EmptyState`
  widget.
- **Persistence/reconnect/push were built but never wired into `main.dart`**:
  `main.dart`'s `EnrollmentGate` generated a brand-new `memberId` on every
  launch (no persisted identity at all), and `ReconnectSupervisor`/
  `PushRegistration` — both fully implemented and unit-tested since 066 —
  were never actually constructed anywhere in the running app. Fixed: a new
  `EnrollmentStore` persists `{member_id, key_fingerprint, border_host,
  border_port, claw_domain}` across restarts; `EnrollmentGate` reconnects via
  the persisted record instead of re-enrolling every launch;
  `EdgeClient.reconnectInPlace()` (new) lets a dropped connection redial
  using the SAME `EdgeClient` object, so no downstream wrapper needs
  rebuilding; `HomeShell` wires a `ReconnectSupervisor` to it and attempts
  best-effort push registration (safe no-op with no real Firebase project
  configured, same as before).
- **Real end-to-end verification, bypassing the QR-scan camera bug**: a new
  `integration_test/enrollment_and_ask_test.dart` calls the app's real
  `attemptEnrollmentFromQr` directly on a real Android emulator (real
  AndroidKeyStore key generation/signing, real `wss://` TLS dial, real
  `in2n/enroll` handshake, real `n2n/edge/ask` submission) — it deliberately
  skips only the camera-frame-to-QR-string decode step. That step could not
  be exercised for real in this environment: the Android emulator's
  `-camera-back imagefile` mode renders any fed image shrunk/mis-positioned
  regardless of source size/aspect ratio (confirmed against multiple image
  shapes), which is a genuine, unreported emulator-camera-HAL quirk (checked
  `mobile_scanner`'s GitHub/changelog — no newer version, no matching issue;
  `mobile_scanner`'s own `PreviewView` config is already correct,
  `BoxFit.cover`); no virtual-webcam workaround is available either (no
  `v4l2loopback`/`/dev/video*` in this WSL2 environment). This test was run
  successfully against the **real production Border** (with the operator's
  explicit go-ahead): `N2N_EDGE_WS_PORT=8443` added to
  `~/.openclaw/mesh.systemd.env` and `netclaw-mesh.service` restarted
  (federation fully recovered — same 5 peers, same states, before/after
  compared). Real enrollment + a real `ask()` round-trip both succeeded,
  confirmed independently in `journalctl --user -u netclaw-mesh.service` and
  the daemon's own `/n2n/members` listing. Test member rows were removed via
  `/n2n/members/remove` afterward — no residue left on production.
- **A real (minor, separate) bug surfaced by that test**: `ask()`'s agent-turn
  response came back as `GatewayClientRequestError: Invalid session ID:
  n2n-edge-risk/integration-test-...` — `gateway.run_agent_turn()`'s
  `session_key=f"n2n-edge-{member_id}"` (067) produces a session ID
  containing a literal `/` when `member_id` itself contains one (every
  `risk/...`-style member ID does), which `openclaw agent`'s session-ID
  validation rejects. Submission/routing itself worked correctly — this is a
  session-key-format bug, not a NCFED protocol bug — logged here rather than
  fixed under time pressure; worth a small follow-up (e.g., sanitize the
  session key, or use only the member's local id segment).
- **HUD**: the existing "NetClaw Mobile edge nodes" panel
  (`ui/netclaw-visual/src/main.js`'s `renderEdgeNodes()`) had no phone glyph,
  just plain state/name text. Added a 📱 to the section header and each row,
  matching the HUD's existing sparse-emoji convention (●/○ liveness dots, 🔒
  for cert mode) — picked up live by the Vite dev server, no HUD restart
  needed.
- **Enrollment UX gap identified, not fixed this pass**: `EnrollmentGate`
  goes straight to the QR scanner with no "enter Border details manually"
  fallback at all — a deliberate 066 design choice (the QR atomically bundles
  `border_host`/`border_port`/`claw_domain`/`enrollment_token` so the
  domain-mismatch check always has everything together), but one that never
  accounted for "camera unavailable/impractical" as a real case. Worth a
  small dedicated follow-up spec.
