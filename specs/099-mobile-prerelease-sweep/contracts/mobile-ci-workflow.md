# Contract: `.github/workflows/mobile-ci.yml`

## Trigger

`pull_request` on paths `mobile/netclaw-mobile/**` (covers both Dart and `ios/` native changes, since the iOS project lives under `mobile/netclaw-mobile/ios/`).

## Jobs / steps (in order, single job, `runs-on: macos-14` or newer available at implementation time)

1. Checkout.
2. Set up Flutter (pinned to the version implied by `pubspec.yaml`'s `sdk: ^3.12.2` constraint).
3. `flutter pub get` in `mobile/netclaw-mobile/`.
4. `flutter analyze` — non-zero exit fails the check.
5. `flutter test` — non-zero exit fails the check.
6. `xcodebuild build -project ios/Runner.xcodeproj -scheme Runner -destination 'generic/platform=iOS Simulator'` — non-zero exit fails the check. No signing required (Simulator destination).
7. `xcodebuild build -project ios/Runner.xcodeproj -scheme WatchApp -destination 'generic/platform=watchOS Simulator'` — non-zero exit fails the check.

## Explicit non-goals

- No device/distribution signing, no secrets — keeps this workflow fully decoupled from Story 3's paid-account dependency (research.md R7).
- No fastlane, no custom GitHub Action beyond the standard `subosito/flutter-action` (or equivalent) — matches the "no new third-party tooling beyond what's strictly needed" pattern used throughout this spec.
- Does not attempt to fix flakiness in the existing 25 Dart test files — if one is flaky, that surfaces as a real CI finding to address separately, not something this workflow's contract papers over.
