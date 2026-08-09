# Phase 0 Research: Mobile Pre-Release Hardening & Expansion Sweep

## R1: Story 6 (rich notification actions) is already implemented

**Decision**: Re-scope Story 6 from "build" to "verify + close test gaps."

**Rationale**: Direct code inspection found spec 073 already delivered this exact capability:
- `mobile/netclaw-mobile/lib/ncfed/local_notifications.dart:11-13,71-91` registers an `approval` notification category with `approve`/`deny` `DarwinNotificationActionOption.authenticationRequired` actions (iOS enforces device authentication before invoking the action at the OS level) and Android equivalents.
- `mobile/netclaw-mobile/lib/main.dart:376-405` (`_handleNotificationResponse`) routes both actions through `confirmAndResolve` — the exact same function the in-app Approve/Deny buttons in `approvals_screen.dart:44` call.
- `mobile/netclaw-mobile/lib/ncfed/approval_confirmation.dart:19-46` (`confirmAndResolve`) is documented as "the app's one place biometric code exists," performs a fresh `local_auth` challenge before ever calling `ApprovalClient.resolve()`, and already returns `'Already resolved'` (not a silent no-op or error) when the approval was resolved elsewhere first — this already satisfies FR-016's stale-approval requirement too.

**Alternatives considered**: Building a parallel/new notification-action pathway was never seriously on the table once this was found — doing so would violate the "don't rebuild what exists" principle and risks *diverging* from the already-correct shared confirmation path, which is a regression risk (FR-020), not a safe addition.

**Remaining real gap**: no test file exercises `approval_confirmation.dart` end-to-end (no `approval_confirmation_test.dart` exists among the ~25 Dart test files) or the notification-response routing in `main.dart`. Story 6's tasks are therefore: add that missing test coverage, and manually verify FR-014/015/016 acceptance scenarios still hold (they should, unchanged) — no application code changes anticipated unless verification surfaces a real defect.

## R2: iOS deployment target bump for ActivityKit

**Decision**: Raise `IPHONEOS_DEPLOYMENT_TARGET` from 15.0 to **16.2** (not 16.1) across all Runner and LiveActivityWidget build configurations (Debug/Release/Profile).

**Rationale**: ActivityKit's Live Activities feature itself shipped in iOS 16.1, but the `ActivityContent<T>` wrapper (`Activity.request(attributes:content:)`, `activity.content`, `activity.end(_:dismissalPolicy:)`) — the API this app's `LiveActivityBridge.swift` uses — is gated to iOS 16.2+ in the SDK this project builds against (confirmed directly: building against a 16.1 floor with the pre-16.2 raw-`ContentState` API compiled `Activity.request(attributes:contentState:pushType:)` fine but failed on `activity.end(_:dismissalPolicy:)`, which only has the `ActivityContent`-based overload available). Bumping to 16.2 lets the widget use the current, non-deprecated API uniformly. Same "no existing users to strand" rationale as before — 16.2 shipped weeks after 16.1, in October 2022.

**Alternatives considered**: Staying on 16.1 and using the older raw-`ContentState` `Activity.request`/`.end` overloads — rejected once discovered mid-implementation that `.end(_:dismissalPolicy:)`'s non-`ActivityContent` overload isn't available in the current Xcode SDK regardless of deployment target, making 16.1 a dead end for the `end` call specifically. Conditionally compiling behind `if #available` — still rejected per the original rationale (no compatibility need to preserve).

## R3: Live Activity vs. static Lock Screen widget for Story 7

**Decision**: Implement Story 7 as a single ActivityKit Live Activity (started when a pending approval notification is posted, ended when resolved), not a separate always-on static WidgetKit widget.

**Rationale**: A pending approval is inherently a bounded-lifetime event (starts, resolves) — exactly what Apple designed Live Activities for, including automatic Lock Screen presentation with no separate widget-gallery configuration step required from the user. FR-017 in the spec already says "widget and/or Live Activity," so one mechanism satisfies it. A parallel static widget showing the same content would be redundant UI surface for no added value (the app has no pending-approval state worth showing at rest between activities — a resolved state has nothing to display).

**Alternatives considered**: Static `WidgetKit` Lock Screen widget with a `TimelineProvider` polling approval state — rejected because it requires the user to manually add the widget from the widget gallery (extra onboarding friction) and polls rather than reflects real-time state the way a Live Activity does.

## R4: Watch complications use WidgetKit, not the deprecated ClockKit

**Decision**: Add a WidgetKit-based complication (`.complicationset` asset catalog, `AccessoryCircular`/`AccessoryRectangular` families as appropriate) inside a new Complication extension embedded in the existing `WatchApp` target.

**Rationale**: `WATCHOS_DEPLOYMENT_TARGET` is already 10.0 (confirmed in `project.pbxproj`), well past watchOS 9's WidgetKit-for-complications transition — ClockKit's `CLKComplicationDataSource` is deprecated for anything targeting watchOS 9+. No deployment-target change needed for this story, unlike Story 7.

**Alternatives considered**: None seriously — targeting a deprecated API on an already-modern deployment target would be actively wrong, not a legitimate alternative.

## R5: Adding two new Xcode extension targets — repeat spec 072's mistakes deliberately avoided

**Decision**: When hand-editing `project.pbxproj` to add the `LiveActivityWidget` and `WatchComplication` extension targets, explicitly mirror the corrected `WatchApp` target configuration (not its first-draft form), and add both `PBXProject.attributes.TargetAttributes` entries at creation time.

**Rationale**: The prior watch-app addition (spec 072) shipped a real, since-fixed bug where `WatchApp` inherited the project's default `iphoneos` `SUPPORTED_PLATFORMS` instead of `watchos watchsimulator` (documented as found-and-fixed 2026-07-29 in the mobile app's own `README.md:274-285`), and its `TargetAttributes` entry was never populated at all (still absent as of this writing — confirmed by inspection, `PBXProject.attributes.TargetAttributes` only lists `RunnerTests` and `Runner`), which leaves Xcode's Signing & Capabilities UI treating the watch target as unmanaged until a human manually touches it once. Both new targets in this spec are extension targets embedded in an app target (same structural pattern as `WatchApp` embedded in `Runner`), so the same two mistakes are the most likely to recur if the pbxproj is edited the same way. This research item exists specifically so tasks.md includes an explicit verification step for both.

**Alternatives considered**: Doing this work interactively in Xcode's GUI instead of scripting the pbxproj edit — the safer option in principle (Xcode writes correct `TargetAttributes`/`SUPPORTED_PLATFORMS` itself), but not available to an automated implementation pass; noted as a fallback the developer can use if the scripted edit proves fragile.

## R6: No fastlane — plain `xcodebuild`/`ExportOptions.plist` for Story 3's submission scaffold

**Decision**: Story 3's "repeatable archiving process" is a committed `ExportOptions.plist` plus a thin `scripts/mobile-release-archive.sh` wrapper around `xcodebuild archive` / `xcodebuild -exportArchive`, not a new fastlane dependency.

**Rationale**: No fastlane installation exists anywhere in the repo today (confirmed by search). Every prior mobile spec (066-073) explicitly favored zero or minimal new third-party dependencies; a Ruby toolchain + Fastfile + plugin ecosystem is a disproportionately heavy addition for "make the archive command repeatable," which plain `xcodebuild` flags already achieve. Matches the existing `scripts/*.sh` convention used throughout the repo for installation/automation glue.

**Alternatives considered**: fastlane — rejected per above; a manual, undocumented Xcode GUI archive — rejected as not meeting FR-008's "repeatable, documented process" bar.

## R7: CI runner and scope

**Decision**: New `.github/workflows/mobile-ci.yml` runs on `macos-14` (or newer GitHub-hosted macOS runner available at implementation time), triggered on pull requests touching `mobile/netclaw-mobile/**`. Steps: `flutter pub get` → `flutter analyze` → `flutter test` → `xcodebuild build` for the `Runner` scheme targeting the iOS Simulator destination → `xcodebuild build` for the `WatchApp` scheme targeting the watchOS Simulator destination. Both `xcodebuild` steps build for Simulator (not device), so no signing identity or secrets are required in CI — keeping the paid-account dependency (Story 3) fully decoupled from the CI gate (Story 4).

**Rationale**: Simulator builds prove compileability/link-ability of all targets (including the two new extension targets from Stories 7/8) without needing any provisioning profile or team secret in CI, satisfying FR-009/FR-010 without coupling CI to Story 3's external dependency.

**Alternatives considered**: Device/distribution builds in CI — rejected, would require storing a distribution certificate and provisioning profile as CI secrets before the paid account even exists, which is a real security-surface increase for no verification benefit Simulator builds don't already provide.

## R8: Native test target for the watch-relay logic

**Decision**: Add `WatchRelayPluginTests.swift` to the existing (currently placeholder-only) `RunnerTests` target, testing `WatchRelayPlugin.swift`'s message encode/decode and dispatch logic with a fake/mock `WCSession` rather than a real device/simulator watch pairing.

**Rationale**: `RunnerTests` already exists as a unit-test target on the `Runner` (phone) side, where `WatchRelayPlugin.swift` itself lives — no new test target is needed, just real content in the one that exists. A mock `WCSession` (protocol-conforming fake) keeps the test hermetic and fast in CI (R7), rather than requiring a paired watch/simulator which GitHub-hosted CI runners don't provide.

**Alternatives considered**: A new dedicated `WatchAppTests` target for the watch-side Swift files (`ConnectionState`, `WatchDataStore`, etc.) — reasonable follow-up but out of scope for FR-011, which specifically calls out the watch-relay *message-passing* logic; only `WatchRelayPluginTests.swift` is required to satisfy it.

## R9: Dashboard data sourcing

**Decision**: `dashboard_data.dart` is a thin aggregator over already-existing service objects already constructed in `main.dart`'s app-shell state (edge/heartbeat connection state, the persisted enrollment/identity store, `FeedStore`/`ConversationStore`/`ApprovalClient` unread/pending counts) — no new Border-side RPC, no new local storage.

**Rationale**: Spec Assumptions section already commits to this ("no new Border-side data surface is assumed necessary unless implementation discovers a genuine gap"); every data point FR-012 requires (Border connection health, device identity/enrollment status, unread/pending counts) is already computed somewhere in the existing app for other screens' use — Dashboard is a new *view* over existing state, not a new data path.

**Alternatives considered**: A new `dashboard_service.dart` calling the Border directly for a purpose-built summary payload — rejected as premature; only pursue if implementation finds a real gap (e.g., "uptime" isn't currently tracked anywhere), at which point the smallest addition to the existing heartbeat/edge client is preferred over a new subsystem.

## R10: FR-004 usage-string coverage is deliberately partial (analyze finding G1)

**Decision**: tasks.md only adds `NSPhotoLibraryUsageDescription` and `NSLocalNetworkUsageDescription`/`NSBonjourServices` (Story 2). No task touches camera, microphone, speech-recognition, or Face ID usage strings.

**Rationale**: The pre-spec release-readiness sweep that motivated this feature directly inspected `mobile/netclaw-mobile/ios/Runner/Info.plist` and confirmed `NSCameraUsageDescription`, `NSMicrophoneUsageDescription`, `NSSpeechRecognitionUsageDescription`, and `NSFaceIDUsageDescription` are already present, specific, and correctly scoped to specs 067/068's actual capture/voice/biometric flows — only photo library and local network were found missing. FR-004 lists all six resource categories for completeness against the general App Store requirement, not because all six needed new work.

**Alternatives considered**: None — re-auditing these four now would just re-confirm the prior finding at extra cost; recorded here instead so a reader of only plan.md/tasks.md doesn't mistake partial task coverage for an accidental gap.

## R11: Watch complication needs an App Group (discovered during Story 8 implementation)

**Decision**: Added a shared App Group entitlement (`group.ca.automateyournetwork.netclaw.mobile`) to both the `WatchApp` and `WatchComplication` targets, plus `PendingApprovalCountStore.swift` (a shared file, member of both targets, mirroring the `PendingApprovalActivityAttributes.swift` sharing pattern from Story 7) wrapping `UserDefaults(suiteName:)` reads/writes.

**Rationale**: R4 assumed the complication could read `pendingApprovalCount` "from the existing WatchDataStore," but a WidgetKit extension runs in its own separate process — it has no access to another process's in-memory `@Published` state. The standard, Apple-documented bridge for this exact situation is an App Group-backed shared container: the app writes on every data change, the extension reads on every timeline request, and the app calls `WidgetCenter.shared.reloadAllTimelines()` right after writing so the change is reflected promptly rather than on WidgetKit's own opportunistic refresh schedule. App Groups (unlike Push Notifications, which blocked Runner's entitlement — see `Runner.entitlements`) are supported on a free/Personal Apple Developer team, so this doesn't introduce a new paid-account dependency.

**Alternatives considered**: Direct `WatchConnectivitySession` calls from within the widget extension itself — rejected as unreliable; WidgetKit extensions get very limited, infrequent background execution time, unsuited to an interactive phone round-trip. A push-driven complication (APNs updates delivered straight to the widget) — rejected as premature; that's the same paid-account-gated push infrastructure Story 3 explicitly defers, and the local App Group bridge already satisfies FR-019 without it.

## R12: Pre-existing latent CI-blocking bug found and fixed during T040's fresh-state regression sweep

**Decision**: Added `MinimumOSVersion = 16.2` to `mobile/netclaw-mobile/ios/Flutter/AppFrameworkInfo.plist`.

**Rationale**: T040's local verification sweep deliberately wiped DerivedData first, to match what a real (always-cold) CI runner sees — and only then did `xcodebuild build -scheme Runner` fail with `firebase-core requires minimum platform version 15.0... but this target supports 13.0 (in target 'FlutterGeneratedPluginSwiftPackage')`. Investigation traced this to Flutter's generated `Package.swift` hardcoding an `iOS("13.0")` platform floor whenever `AppFrameworkInfo.plist` has no `MinimumOSVersion` key (true of this project before this fix) — a floor incompatible with the pinned `firebase_core`/`firebase_messaging` versions' real iOS 15 minimum. Xcode's SPM resolver only enforces this on a genuinely fresh package-graph resolution; every build performed earlier in this feature's implementation reused a persisted DerivedData/SPM cache that masked it. **Reproduced identically on the pre-099 baseline** via `git stash` + a DerivedData wipe, confirming this predates spec 099 entirely — it is not a regression introduced by any of the 8 stories, but it WOULD have silently broken Story 4's CI gate (`mobile-ci.yml`) on its very first real run, since GitHub Actions runners always start cold. Fixed via `MinimumOSVersion`, the standard Flutter-documented mechanism for controlling this — confirmed by rebuilding via `flutter build ios` (which regenerates `Package.swift` from this key) and seeing the floor correctly become `iOS("16.2")`, then re-verifying both `Runner` and `WatchApp` schemes build successfully from a fully fresh DerivedData afterward.

**Alternatives considered**: Downgrading `firebase_core`/`firebase_messaging` to versions compatible with an iOS 13 floor — rejected as a much larger, riskier change (unknown API surface differences, and push is already best-effort/optional per FR-007) for a problem `MinimumOSVersion` fixes in one line. Leaving it undiscovered — rejected outright; SC-004 (the CI gate reliably blocks broken builds) would have been silently false from day one.

## R13: Two more real-device-only bugs found during the actual phone/watch install (post-merge)

**Bug 1 — extension Info.plists had an unresolvable version variable.** `LiveActivityWidget/Info.plist` and `WatchComplication/Info.plist` referenced `$(FLUTTER_BUILD_NUMBER)`/`$(FLUTTER_BUILD_NAME)` (copied from Runner's own Info.plist), but those variables are only defined via Flutter's Generated.xcconfig chain, which only Runner's build configurations include — neither extension target's `XCBuildConfiguration` has a `baseConfigurationReference` to it (R2's static `CURRENT_PROJECT_VERSION`/`MARKETING_VERSION` build-setting fix was necessary but not sufficient by itself, since the *plist* never referenced those build settings in the first place). Simulator installs never validate this strictly; a real-device `devicectl install` does, and failed with `does not have a CFBundleVersion key with a non-zero length string value`. **Fixed** by pointing both plists at `$(CURRENT_PROJECT_VERSION)`/`$(MARKETING_VERSION)` instead of the Flutter-only variables — confirmed via `plutil -p` on the built `.appex` showing real values (`CFBundleVersion => "1"`), then a successful `devicectl device install app`.

**Bug 2 — the WatchComplication App Group cannot be provisioned on a free/Personal team at all, confirmed empirically twice.** The real-device phone install failed with `Failed Registering Bundle Identifier: ... cannot be registered to your development team because it is not available` for `ca.automateyournetwork.netclaw.mobile.watchapp.watchcomplication` specifically (Runner, WatchApp, and LiveActivityWidget's IDs all registered fine in the same build). The developer then confirmed directly in the Apple Developer portal that a free/Personal-team account has no Certificates/App Groups management UI at all — that section is gated behind actual Program enrollment, not just automatic on-the-fly registration through Xcode. This means R11's "App Groups are supported on a free/Personal team" was **wrong** — App Groups specifically require paid Program enrollment, the same gate as Push (though for a different underlying reason: Push is blocked by capability restriction, App Groups are blocked by no portal access to create the group at all). **Mitigated for tonight's install** by temporarily detaching `WatchComplication`'s embed phase/dependency from `WatchApp` in a local, uncommitted working-tree change, installing everything else, then restoring the full wiring before committing — main's committed state keeps the complete feature (Simulator/CI builds are unaffected, since they never hit real provisioning). Recorded in `docs/MOBILE-RELEASE.md` as a second paid-account-gated item alongside Push.

**Alternatives considered** (Bug 2): Removing the App Group requirement entirely and finding another cross-process data-sharing mechanism for the complication — rejected; App Groups are still the correct, standard mechanism once the paid account exists, and this is a temporary account-status blocker, not a design flaw to re-architect around. Leaving `WatchComplication` permanently detached from the committed project — rejected; that would silently regress Story 8 out of the codebase for every future contributor, not just work around tonight's specific device limitation.
