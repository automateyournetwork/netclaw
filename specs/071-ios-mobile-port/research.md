# Research: iOS Port Verification and App Store Roadmap for NetClaw Mobile

All Technical Context fields in `plan.md` were resolvable directly from the existing codebase
(`ios/Runner/*`, `pubspec.yaml`, `project.pbxproj`) — no `NEEDS CLARIFICATION` markers remained
after Phase 0 investigation. This file records the decisions that shape the task breakdown.

## D1: Code-signing approach for real-device builds

**Decision**: Use Xcode's automatic signing with a free "Personal Team" (any Apple ID, no paid
Apple Developer Program enrollment) for the verification work in this feature. Paid enrollment is
only required later, for TestFlight/App Store submission — captured as its own line item in
`APP-STORE-ROADMAP.md`, not a prerequisite for verification.

**Rationale**: FR-002/FR-003/SC-002 only require running the app on a real device to exercise the
Secure Enclave and Face ID — Apple has allowed free-account on-device debugging (7-day
re-signing window) since Xcode 7. Blocking this feature on Apple Developer Program enrollment
(a multi-day, $99/year process per `PLAY-STORE-ROADMAP.md`'s Android account-type discussion)
would be scope creep the spec's Assumptions already reject ("actually enrolling in the Apple
Developer Program... is out of scope for this feature").

**Alternatives considered**: Requiring a paid account upfront — rejected as unnecessary for
verification and premature given publication timing is undecided (User Story 4 is planning-only).

## D2: `RunnerTests` (XCTest) scope

**Decision**: Leave `RunnerTests.swift` as its current stub. Do not write new XCTest unit tests for
`EdgeIdentityPlugin`/`X509SelfSigned` as part of this feature.

**Rationale**: Both files are fundamentally hardware-dependent (Secure Enclave has no software
fallback and does not exist in the Simulator or in an XCTest host process's sandbox in a
consistently testable way). The Android side reached the same conclusion — the equivalent
`MainActivity.kt`/AndroidKeyStore plugin was verified through manual, evidence-logged runs (logcat
output, a real emulator round trip), not unit tests. This feature follows the same evidence
standard: Xcode console output + a real enrollment/ask/answer transcript, documented in the README
update (FR-010), not a new automated test suite. Consistent with FR-014 (no shared-layer rework)
and the constitution's Documentation-as-Code principle, which asks for accurate documentation, not
a specific test framework.

**Alternatives considered**: Adding host-app XCTest cases that call into `EdgeIdentityPlugin`
directly — rejected; running on the XCTest host process still requires a real device for Secure
Enclave and gains little over manual verification for a one-time port-verification pass.

## D3: `AppDelegate`/`SceneDelegate` — FlutterFragmentActivity-equivalent question (FR-008)

**Decision**: No structural change is expected. Document this finding rather than pre-emptively
changing `AppDelegate.swift`.

**Rationale**: Android's `MainActivity` had to become `FlutterFragmentActivity` because
`local_auth`'s Android implementation requires a `FragmentActivity` host to show the
`BiometricPrompt` dialog. iOS's `local_auth` implementation calls `LAContext.evaluatePolicy`
directly against the system, with no requirement on the hosting `UIViewController`/`AppDelegate`
type — `FlutterAppDelegate` (already in use here) is sufficient. This is a documented characteristic
of the `local_auth` plugin's iOS implementation, not something specific to this app. The task list
still includes a verification step (attempt a Face ID prompt on the stock `AppDelegate` first) so
this is confirmed empirically, not just asserted from platform docs, before the README is updated.

**Alternatives considered**: Pre-emptively restructuring `AppDelegate` "to be safe" — rejected;
unnecessary code churn ahead of empirical confirmation, and risks violating FR-014's spirit of
minimal-footprint native changes.

## D4: Camera/mic plugin iOS wiring (FR-006/FR-007)

**Decision**: No new native iOS wiring expected beyond what's already in `Info.plist`
(`NSCameraUsageDescription`, `NSMicrophoneUsageDescription`, already present). `camera` and
`mobile_scanner` are both actively maintained Flutter plugins with standard CocoaPods-based iOS
implementations that self-register via `GeneratedPluginRegistrant` — no manual Podfile edits are
anticipated beyond `pod install`/`flutter pub get` doing their normal job.

**Rationale**: This mirrors Android, where the equivalent permissions merged automatically via
Gradle manifest merging with zero manual `AndroidManifest.xml` edits (per `README.md`'s existing
Android section). The task list keeps a verification step to confirm this holds for iOS instead of
assuming it silently.

**Alternatives considered**: None — this is a low-risk, well-trodden path for both plugins.

## D5: App Store roadmap structure (FR-011/FR-012)

**Decision**: Mirror `PLAY-STORE-ROADMAP.md`'s five-phase structure, re-mapped to Apple's process:

| Play Store phase | App Store equivalent |
|---|---|
| Phase 1 — Developer account (Personal vs Organization, gates everything) | Phase 1 — Apple Developer Program enrollment (Individual vs Organization/D-U-N-S), which similarly gates App Store Connect access |
| Phase 2 — Make the build shippable (applicationId, signing, R8, AAB) | Phase 2 — Make the build shippable (bundle identifier, distribution certificate + provisioning profile, versioning, `flutter build ipa`) |
| Phase 3 — Listing and compliance paperwork | Phase 3 — App Store Connect listing + compliance (privacy policy URL, App Privacy "nutrition label" questionnaire, age rating, screenshots) |
| Phase 4 — Testing gate (12 testers × 14 days for Personal accounts) | Phase 4 — TestFlight (internal testing immediate; external testing requires a Beta App Review, materially lighter than Play's closed-testing gate) |
| Phase 5 — Production review | Phase 5 — App Store Review (typically faster than Google's for established categories, but first-submission variance applies to both) |

**Rationale**: The user explicitly asked for a document "structurally comparable to
`PLAY-STORE-ROADMAP.md`" (FR-011) — reusing its phase skeleton keeps the two documents easy to
compare side by side and reuses a structure already proven useful for this exact audience (the
same operator, publishing the same app).

**Alternatives considered**: A generic App Store submission checklist sourced independently —
rejected; would not honor FR-012's requirement to sequence against *this repo's actual current iOS
build config*, and would lose the deliberate parallel structure FR-011 asks for.

## D6: Bundle identifier — no decision needed, just documentation

**Decision**: Document the current bundle identifier (`ca.automateyournetwork.netclaw.mobile`,
confirmed in `project.pbxproj`) as already reasonable and *not* carrying Android's
`applicationId` problem (Android's is `ca.automateyournetwork.netclaw.netclaw_mobile` — the raw
Flutter template default with an ugly redundant suffix, flagged as needing a decision in
`PLAY-STORE-ROADMAP.md`). The iOS bundle ID has no such defect.

**Rationale**: Direct inspection of `ios/Runner.xcodeproj/project.pbxproj:385` shows a clean,
already-decided identifier. The roadmap should still flag it as *permanent once published*
(App Store Connect ties a bundle ID to a listing exactly as Play does to an `applicationId`) but
does not need to present it as an open decision the way the Android roadmap did.

**Alternatives considered**: None — this is a factual finding, not a choice.

## D7: Development environment gap (Xcode / Flutter SDK not installed)

**Decision**: Task list must include an explicit environment-setup task (install Xcode from the
App Store, install the Flutter SDK, `flutter doctor` clean) as a prerequisite before any
build/run/verify task, and every hardware-dependent verification task must be written so its
outcome (done / blocked-with-reason) is honestly recorded rather than assumed.

**Rationale**: Direct inspection of this machine found `xcode-select -p` pointing at Command Line
Tools only (no `Xcode.app`), and no `flutter` binary on `PATH` or in common install locations.
Neither tool can be installed non-interactively by an agent (Xcode requires an interactive App
Store / Apple ID sign-in and is a multi-GB download; Flutter's installer is scriptable but its
first `flutter doctor` run still needs Xcode present to detect the iOS toolchain). This is an
environment fact discovered during planning, not a spec ambiguity — the spec's Assumptions already
require "a Mac with a working Xcode installation," which does not yet hold on this machine.

**Alternatives considered**: Silently assuming Xcode/Flutter would be present by implementation
time — rejected; would produce a task list whose first real task fails immediately with no
recorded reason, violating FR-009/FR-010's "document the outcome either way" standard applied
consistently across this feature.

## D8: First real build attempt — two genuine blockers found and fixed (2026-07-26)

Once Xcode 26.6 and Flutter 3.44.8 were actually installed (Xcode via the App Store, interactively
by the operator; Flutter via `brew install --cask flutter`, non-interactively), the first-ever
`flutter build ios --debug --simulator` attempt surfaced two real, previously-undiscoverable
issues (D1–D7 were all findable by reading files; these needed an actual compiler run):

1. **Deployment target too low for Firebase's SPM packages.** `firebase-core`/`firebase-messaging`
   (both already in `pubspec.yaml` for the out-of-scope push feature) declare a minimum iOS
   platform version of 15.0 via Swift Package Manager, but `IPHONEOS_DEPLOYMENT_TARGET` was still
   13.0 (the Flutter template default, never revisited because no iOS build had ever been
   attempted). **Fix**: bumped all three `IPHONEOS_DEPLOYMENT_TARGET` occurrences in
   `ios/Runner.xcodeproj/project.pbxproj` from `13.0` to `15.0`. This is a build-configuration
   change, not a change to `EdgeIdentityPlugin.swift`/`X509SelfSigned.swift` or the shared Dart
   layer (FR-014 unaffected) — iOS 13/14 device share is negligible by 2026, and Firebase itself
   (already a declared, if unfinished, dependency) requires this floor regardless of anything this
   feature does.
2. **`EdgeIdentityPlugin.swift`/`X509SelfSigned.swift` were never added to the Xcode project at
   all.** Both files existed on disk under `ios/Runner/` (written without Xcode access, per
   `MAC-IOS-HANDOFF.md`), but `project.pbxproj` had zero references to either — no
   `PBXFileReference`, no `PBXBuildFile`, no `PBXSourcesBuildPhase` entry. The build failed with
   `Cannot find 'EdgeIdentityPlugin' in scope` at `AppDelegate.swift:16`, confirming this file had
   genuinely never compiled, exactly as the handoff doc warned. **Fix**: used the `xcodeproj` Ruby
   gem (installed alongside CocoaPods) to add both files to the `Runner` group and the target's
   Sources build phase programmatically — equivalent to dragging both files into Xcode and
   checking "Add to target," just scripted. This is squarely within T006's scope (get the iOS
   build compiling) and touches only project configuration, not the two files' own code.

**Result**: `flutter build ios --debug --simulator` now succeeds
(`✓ Built build/ios/iphonesimulator/Runner.app`), and the app installs and launches cleanly on the
iOS Simulator (`xcrun simctl install`/`launch`) — no crash, Dart VM service starts, and it correctly
lands on the "Scan Border QR Code" enrollment screen with a real system camera-permission dialog
showing the exact `NSCameraUsageDescription` text from `Info.plist`. This is strong evidence
`EdgeIdentityPlugin.register(with:)` runs at launch without crashing, though the Secure Enclave
itself remains unverified (unavailable on Simulator — still needs T004/T005/T008 on a real,
signed, physically connected device).

**Alternatives considered**: Hand-editing `project.pbxproj`'s XML-adjacent plist format directly —
rejected as needlessly fragile and error-prone (24-hex-char ID generation, keeping four separate
sections in sync) compared to the purpose-built `xcodeproj` gem already available for free via the
CocoaPods install this feature already needed.
