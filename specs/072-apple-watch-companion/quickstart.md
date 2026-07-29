# Quickstart: Apple Watch Companion App for NetClaw Mobile

## Prerequisite

Builds on spec 071's already-verified state: Xcode 26.6 + Flutter 3.44.8 installed, the phone app
building/running/enrolled against a live Border on a real iPhone. Nothing here re-does that setup.

## Manual walkthrough

1. **Add the watch target**: in Xcode, add a new watchOS App target (`WatchApp`) to
   `ios/Runner.xcodeproj`, embedded in `Runner` as its companion. Confirm the existing `Runner`
   scheme is untouched and a new `WatchApp` scheme appears.
2. **Wire the relay, phone side**: add `WatchRelayPlugin.swift` (WCSessionDelegate), register it in
   `AppDelegate.swift` alongside the existing `EdgeIdentityPlugin` registration. Add
   `lib/ncfed/watch_relay.dart`, wire it in `HomeShell.initState()` using the already-constructed
   `askClient`/`approvalClient`/`feedStore`.
3. **Build for Simulator first**: `WatchApp` on a watchOS Simulator, paired with `Runner` on an
   iOS Simulator (Xcode pairs Simulators automatically when both are booted) — confirms the
   WatchConnectivity session activates and the method channel forwards correctly, with zero
   dependency on real hardware.
4. **Approvals, Simulator**: trigger a Border-side approval (same mechanism as spec 068's
   quickstart); confirm it appears in the watch Simulator's Approvals view; approve it; confirm the
   Simulator's own passcode-simulation prompt appears (Simulator supports a simulated device
   passcode for `LAContext` testing); confirm the Border's audit record shows
   `via="watch_passcode"`, not `"biometric"`.
5. **Feed, Simulator**: push a text and an image message from the Border; confirm both appear in
   the watch Simulator's Feed view, the image showing a type indicator rather than the image itself.
6. **Quick ask, Simulator**: the Simulator can't dictate for real, but can accept typed text into
   the same `TextField` — confirm submit → waiting → answered flow completes end to end.
7. **Not-connected states**: force-quit the phone's Flutter app (or stop the iOS Simulator) while
   the watch app is open; confirm all three views show an explicit not-connected state, not a
   silent failure or indefinite spinner (FR-012).
8. **Real hardware, best-effort** (research D6): if the paired physical Apple Watch is confirmed
   reachable as a run destination in Xcode's Devices and Simulators window, repeat steps 4-7 on it;
   record the outcome (verified, or blocked-with-reason) either way — do not assume success without
   evidence, matching spec 071's own standard.

## Automated checks

```bash
cd mobile/netclaw-mobile
flutter analyze
flutter test test/watch_relay_test.dart
flutter test   # full suite — zero regressions in existing phone-only tests
```

No automated test exists (or is expected) for `WatchRelayPlugin.swift`/the watch app's SwiftUI
views — WatchConnectivity and `LAContext` passcode prompts have no meaningful headless-test surface,
matching the same standard already applied to `EdgeIdentityPlugin.swift`/Face ID in spec 071.

## Success signals (from spec)

- SC-001: steps 4 (or its real-device repeat) complete well under 15 seconds end to end.
- SC-002: step 4's Border audit check — zero `"biometric"` records for a watch-originated
  resolution, ever.
- SC-003: step 5 — full text readable on the watch with the phone untouched.
- SC-004: step 6 — the ask reaches `answered` or `failed`, never stuck on `waiting`.
- SC-005: step 7 — every capability's not-connected state appears within a few seconds.
- SC-006: a code review confirms no enrollment/QR/capture/settings code exists anywhere under the
  new `WatchApp` target.
