# Quickstart: iOS Port Verification and App Store Roadmap for NetClaw Mobile

## Prerequisite: environment setup

This machine had only Xcode Command Line Tools and no Flutter SDK at planning time (research D7).
Before any step below:

1. Install Xcode from the App Store (full app, not just Command Line Tools); `xcode-select -s
   /Applications/Xcode.app/Contents/Developer` once installed.
2. Install the Flutter SDK; run `flutter doctor` and resolve everything under "Xcode - develop for
   iOS" until it shows no errors.
3. `cd mobile/netclaw-mobile && flutter pub get`.
4. Open `ios/Runner.xcworkspace` (not `.xcodeproj`) in Xcode. Under Signing & Capabilities, select
   a Personal Team (any Apple ID) for automatic signing — no paid enrollment needed yet (D1).
5. Connect a real iPhone via cable, trust the Mac on the device, select it as the run destination.

## Manual walkthrough

1. **Build**: build `Runner` for the connected real device in Xcode. Record the first-attempt
   result verbatim (FR-001) — this code has never compiled before; a clean build on the first try
   would itself be notable, and errors are the expected/normal starting point to work through.
2. **Fresh enrollment via QR**: on the real device, scan a Border-issued enrollment QR. Confirm the
   app generates a device identity and completes enrollment (US1, FR-002/FR-003/FR-004).
3. **Fresh enrollment via manual entry**: on the Simulator (no usable camera), use "Can't scan?
   Enter manually" with the same domain/port/token. Confirm it reaches the identical enrolled state
   as step 2 (US1 acceptance scenario 2).
4. **Ask/answer round trip**: from the enrolled real device, ask a question; confirm an answer is
   delivered (US1 acceptance scenario 3) — the iOS equivalent of Android's 2m13s proof.
5. **Reconnect**: toggle the device's network off/on mid-session; confirm the app redials without
   requiring re-enrollment (US1 acceptance scenario 4).
6. **Secure Enclave signing**: with the Border, trigger a re-authentication challenge on the
   already-enrolled real device; confirm the Border accepts the signature (US2 acceptance
   scenario 2).
7. **Face ID approval — success path**: trigger a Border-side approval; on the real device (Face ID
   enrolled), confirm a genuine system Face ID prompt appears and a successful scan resolves the
   approval (US2 acceptance scenario 3).
8. **Face ID approval — failure path**: trigger another approval; fail or cancel the Face ID prompt;
   confirm the approval remains unresolved, not falsely approved (US2 acceptance scenario 4).
9. **Camera capture, both directions**: attach a photo to an outgoing question; separately, fulfill
   a Border-requested capture. Confirm both round-trip (US3 acceptance scenarios 1–2).
10. **Permission-denied path**: deny camera/mic permission, attempt a capture, confirm a clear
    message and no crash (US3 acceptance scenario 3).
11. **AppDelegate check (FR-008/D3)**: confirm step 7 worked with the stock `FlutterAppDelegate` —
    if a Face ID prompt never appears at all (not just fails), investigate whether an
    `AppDelegate`/`SceneDelegate` change is actually required before concluding D3 holds.
12. **Revocation edge case**: revoke the device from the Border mid-session; confirm the app returns
    to the enrollment gate (Edge Cases). If it retries a dead connection indefinitely instead
    (the known cross-platform `ReconnectSupervisor` defect), apply a fix only if it is genuinely a
    one-line/obvious change (FR-015); otherwise document it and move on.
13. **Outstanding 066/067 manual tasks (FR-009)**: attempt 066's `quickstart.md` steps 1–10 (T045)
    and 067's federated-peer attribution check (T017) using this iOS device. Record closed or
    blocked-with-reason either way.

## Automated checks

```bash
cd mobile/netclaw-mobile
flutter analyze
flutter test
```

No new automated iOS-specific tests are added (research D2) — `RunnerTests` stays a stub, since
Secure Enclave/Face ID cannot be meaningfully unit-tested without a real device.

## Success signals (from spec)

- SC-001: steps 2 or 3 → step 4 completes in one sitting with no undocumented workaround.
- SC-002: step 1 build succeeds and steps 2/4/6 show zero silent non-hardware-backed fallbacks.
- SC-003: steps 7 and 8 both observed with a real Face ID prompt.
- SC-004: step 9 completes in both directions at least once.
- SC-005: the README rewrite (a separate task) cites specific steps above as evidence for every
  "Verified" claim — no claim without a matching Verification Record row.
- SC-006/SC-007: `APP-STORE-ROADMAP.md` (a separate task) is checked against
  `PLAY-STORE-ROADMAP.md`'s structure per research D5/D6.
