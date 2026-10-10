# NetClaw Mobile

Flutter (iOS + Android, one codebase) client app for the NCFED Edge Node profile.
A thin client — no LLM, no local agent reasoning. Connects outbound to a NetClaw
Border Claw, advertises device-native capabilities (camera, biometric approval,
location, etc.), and renders whatever the Border sends back.

Feature 066 (this repo's `specs/066-netclaw-mobile-ncfed-edge/`) covers the protocol
foundation: enrollment and the Border-to-phone push channel. Feature 067
(`specs/067-ncfed-mobile-command-channel/`) adds the reverse direction — asking the
Border something from the phone (text, voice, or a scanned device QR/deep link).
Feature 068 (`specs/068-ncfed-mobile-biometrics-capture/`) adds two more slices on
top of both: Border-triggered approvals resolved on the phone with device
biometrics (Face ID/fingerprint), and camera/mic capture in either direction
(attach a photo to your own request, or let the Border request one from you).

## Hermes Border — 1.0.3 (build 6)

This is the minimum app version for durable Hermes admission recovery and explicit
unknown/interrupted/cancellation-requested states. Summary shows the Border harness,
model and capabilities; missing metadata stays unknown. Typed and voice-transcribed
Ask Border requests are supported, including Siri voice origin and permitted
federation delegation. Photo/video/audio-file attachments are unavailable with the
protected Hermes runtime and are refused before execution. Existing OpenClaw paths
remain compatible. Never automatically resubmit uncertain work; use Check status.

The signed iOS archive includes the app, Watch app and Live Activity extensions.
Build6 was accepted by App Store Connect for processing; public release was not
submitted. Flutter unit/widget tests and real authenticated backend protocol tests
are distinct from physical iPhone/iPad/Watch/Siri testing. See
[actual evidence and unrun coverage](../../specs/149-hermes-ncfed-federation/verification.md)
and [the compatibility guide](../../docs/HERMES-FEDERATION.md).

## Structure

```
lib/
  ncfed/                     # protocol layer -- no UI
    edge_identity.dart        # platform Keystore/Secure Enclave keygen + sign
    enrollment_qr_payload.dart
    edge_client.dart          # WebSocket JSON-RPC client (mirrors edge.py's EdgeChannel)
    enrollment_flow.dart      # QR -> parse -> domain check -> dial -> outcome
    message_feed.dart         # local persisted store for Border-pushed messages (066)
    enrollment_store.dart     # persisted enrollment, so a restart redials instead of re-enrolling
    reconnect_supervisor.dart # bounded-retry loop; drives the app's auto-redial
    heartbeat.dart            # answers the Border's n2n/edge/heartbeat + self_status probes
    push_registration.dart    # FCM/APNs token registration
    notification_deep_link.dart # notification tap -> jump to that message in the feed
    edge_ask_client.dart      # n2n/edge/ask + task status/result/cancel (067)
    conversation_store.dart   # per-device persisted chat history (067)
    voice_transcription.dart  # on-device speech-to-text -> ask() (067, US4)
    device_deep_link.dart     # netclaw://device/<id> / QR -> ask() (067, US5)
    approval_client.dart      # tracks pushed approvals + approval_resolve (068, US1)
    capability_registration.dart # advertises/toggles capture capabilities (068, US3)
    capture_client.dart       # phone-initiated attach + Border-requested capture handler (068, US2/US3)
    badge_lifecycle.dart      # BadgeLifecycleObserver -- badge recompute on launch/resume (099, Story 1)
    dashboard_data.dart       # Dashboard's snapshot of existing service state, no new backend calls (099, Story 5)
    live_activity.dart        # MethodChannel wrapper for the Lock Screen Live Activity (099, Story 7)
  screens/
    enrollment_screen.dart    # "Scan Border QR Code" + "Can't scan? Enter manually"
    manual_enrollment_screen.dart # domain/port/token typed by hand (no camera needed)
    empty_state.dart          # shared illustrated empty state
    dashboard_screen.dart     # Border health, identity, unread/pending counts -- default landing tab (099, Story 5)
    feed_screen.dart          # renders pushed messages (066)
    chat_screen.dart          # request/answer history, cancel, voice, camera (067/068)
    device_scan_screen.dart   # "Scan Device" -- any time, post-enrollment (067, US5)
    approvals_screen.dart     # pending approvals, Face ID/fingerprint gate (068, US1)
    settings_screen.dart      # per-capture-type enable/disable toggles (068, US3)
    capture_screen.dart       # live camera preview + shutter (068, US2/US3)
  main.dart                   # EnrollmentGate -> HomeShell (Dashboard/Chat/Feed/Approvals/Settings tabs, Dashboard first -- 099)
android/app/src/main/kotlin/.../MainActivity.kt  # FlutterFragmentActivity (local_auth needs a FragmentActivity host) + AndroidKeyStore EdgeIdentity plugin
ios/Runner/EdgeIdentityPlugin.swift               # Secure Enclave EdgeIdentity plugin
ios/Runner/X509SelfSigned.swift                    # manual self-signed cert builder
```

## Running against a local Border

1. On the Border, set `N2N_CLAW_DOMAIN` and `N2N_EDGE_WS_PORT` in `.env` and restart
   the daemon (`mcp-servers/protocol-mcp/bgp-daemon-v2.py`).
2. Issue a QR: `netclaw risk token --edge [label]`.
3. `flutter pub get`, then `flutter run` (Android) to launch the app and scan it.
   No usable camera (emulator, Simulator)? Tap **"Can't scan? Enter manually"** on
   the enrollment screen and type the domain, port, and token instead — it
   synthesizes exactly the payload a scan would produce.

Once enrolled, the app persists the enrollment (`enrollment_store.dart`) and
redials automatically on restart or a dropped connection, so steps 2–3 are
one-time. A Border that revokes the device returns `-32023`, which drops the app
back to the enrollment screen rather than retrying forever.

```bash
flutter analyze
flutter test
```

## Building a release

`flutter build appbundle` reads signing material from `android/key.properties` —
copy [`android/key.properties.example`](android/key.properties.example) and fill
it in:

```properties
storeFile=/absolute/path/to/upload-keystore.jks
storePassword=…
keyAlias=upload
keyPassword=…
```

That file and any `*.jks`/`*.keystore` are gitignored and must never be
committed. **If it's absent the build still succeeds but signs with the debug
key** (Gradle prints a warning) — such an artifact cannot be uploaded to Play.
The release build type has R8 minification and resource shrinking enabled; keep
rules live in `android/app/proguard-rules.pro`.

To put a build on someone's phone rather than a store, see
[`SIDELOAD.md`](SIDELOAD.md).

### What a fresh clone needs

Everything required to build is tracked **except** the things that must not be:

- `android/gradlew`, `android/gradlew.bat` and `gradle/wrapper/gradle-wrapper.jar`
  are gitignored by Flutter's own template. **Build with `flutter build`, not a
  raw `./gradlew`** — the Flutter tool regenerates the wrapper. Running
  `./gradlew` directly in a fresh clone will simply not find it.
- `android/local.properties` is generated by the Flutter tool from your SDK
  paths; never commit it.
- `android/key.properties` and any keystore — see above.
- **`ios/Runner.xcodeproj/project.pbxproj` carries a committed
  `DEVELOPMENT_TEAM` (`A49777FMJG`, the maintainer's).** Anyone else must
  replace it with their own team in Xcode before iOS will sign. iOS uses Swift
  Package Manager, so there is no `Podfile` to install — open
  `ios/Runner.xcworkspace`, not the `.xcodeproj`.

## Push notifications

Push is **decided in scope for v1** and the app-side code is complete: token
registration (`lib/ncfed/push_registration.dart`), notification-tap deep-linking
(`lib/ncfed/notification_deep_link.dart`), failure classification, and a status
row on the Settings tab so a broken push setup is visible rather than silent.

What is **not** in the repo, and never will be, is the Firebase configuration —
it carries per-operator project IDs and API keys. Without it the app builds and
runs completely normally; it just reports "Notifications unavailable" and
answers only arrive while the app is open.

To enable push for your own deployment:

1. Create a Firebase project and register both apps under the bundle ID
   `ca.automateyournetwork.netclaw.mobile` (or your own, if you changed it).
2. **Android** — download `google-services.json` into `android/app/`. The
   `com.google.gms.google-services` Gradle plugin is applied automatically once
   that file exists (it is skipped, with a log line, when it doesn't — the
   plugin hard-fails the build otherwise, which would break every fresh clone).
3. **iOS** — download `GoogleService-Info.plist` into `ios/Runner/`, generate an
   **APNs auth key** (`.p8`) in the Apple Developer portal, and upload it to
   Firebase → Project settings → Cloud Messaging.
4. **iOS capabilities** — in Xcode, Runner target → Signing & Capabilities → add
   **Push Notifications** and **Background Modes → Remote notifications**.
   `ios/Runner/Runner.entitlements` is prepared for this but deliberately not
   yet referenced by the build, because **a free Xcode Personal Team cannot sign
   the Push Notifications capability** and enabling it early breaks device
   builds. This step needs paid Apple Developer Program membership.

All three config files are gitignored.

Toolchain versions this project is known to build with: **Flutter 3.44.8**,
**JDK 17** (Gradle 9.1.0 / AGP 9.0.1 / Kotlin 2.3.20 fail confusingly on newer
JDKs — pin with `flutter config --jdk-dir=…` rather than changing a system-wide
`JAVA_HOME`), Android SDK **platform 36 / build-tools 36.0.0**, and — for iOS —
**Xcode 26.6**.

## Docs

| Doc | What it covers |
|---|---|
| [`MOBILE-ONBOARDING.md`](MOBILE-ONBOARDING.md) | **How to securely enroll a phone against your own Border** — operator side (token/QR) and phone side, plus the security model. Start here. |
| [`SIDELOAD.md`](SIDELOAD.md) | **How to get the app onto a real phone before either store** — Android APK, and all three iOS routes (TestFlight / Ad Hoc / free Personal Team) with their real limits. |
| [`TESTER-INSTRUCTIONS.md`](TESTER-INSTRUCTIONS.md) | Copy-paste handout for sending a build to someone else to test. |
| [`PLAY-STORE-ROADMAP.md`](PLAY-STORE-ROADMAP.md) | Google Play publication path, sequenced against this repo's build config. |
| [`APP-STORE-ROADMAP.md`](APP-STORE-ROADMAP.md) | Apple App Store publication path, sequenced against this repo's build config. |
| [`MAC-IOS-HANDOFF.md`](MAC-IOS-HANDOFF.md) | The original iOS handoff brief. Superseded as the source of truth by `specs/071-ios-mobile-port/` — read that spec's tasks.md for current status. |
| [`ASSETS.md`](ASSETS.md) | Icon/splash regeneration and brand rationale. |

The app ships with no hostnames or credentials — it is a generic NCFED edge
client, bound to whichever Border enrolls it. Any reference to
`netclaw.automateyournetwork.ca` in this repo is the maintainer's own test
Border, not a dependency.

## Platform-specific notes

- **Android**: builds and runs on any Linux/Mac/Windows machine with the Android
  SDK — no macOS required. Verified for real in this repo's own dev environment:
  a debug APK was built (`flutter build apk --debug`), installed and launched on
  an Android emulator (API 34, x86_64, KVM-accelerated), the real
  `mobile_scanner`/`CameraX` camera-permission dialog and a live emulated camera
  preview both rendered correctly inside `EnrollmentScreen`, and a full enrollment
  + `n2n/edge/ask` handshake completed against a real (throwaway, non-production)
  Border daemon over `wss://`. `MainActivity.kt`'s `EdgeIdentityPlugin`
  (AndroidKeyStore-backed) links and runs without crashing; its actual key
  generation/signing behavior has not been separately exercised end-to-end (no QR
  containing a real payload was presented to the emulator's synthetic camera feed).
  Feature 068 was verified the same way: a fresh debug APK (now linking `local_auth`
  and `camera` on top of everything above, and with `MainActivity` changed to
  `FlutterFragmentActivity`) built, installed, and launched cleanly on the same
  emulator — `logcat` showed no Dart/Flutter exception and the activity reached
  `topResumedActivity`, confirming the new native plugins don't crash on startup.
  Biometric approval and a real photo capture were NOT exercised here — this
  emulator has no provisioned fingerprint/Face-unlock enrollment and its virtual
  camera only produces a synthetic test pattern, not a real capture; both need
  either a real device or a properly provisioned emulator, done in a later pass.
  **A full production round trip has since been verified** (2026-07-25): a question
  asked from the emulated phone against the operator's real Border fanned out to
  the `cml` and `pyats` risk members and returned a 1583-byte answer to the handset
  in 2m13s, with GAIT audit records for each delegation. Enrollment, the edge WS
  transport, delegation/routing, and result delivery are all proven end to end.
- **iOS** (status as of spec `071-ios-mobile-port`, 2026-07-26 — see that spec's
  `tasks.md` for the authoritative, evolving record): **the app now builds,
  installs, and launches cleanly on the iOS Simulator.** Xcode 26.6 and Flutter
  3.44.8 were installed on the operator's Mac, and the first-ever
  `flutter build ios --debug --simulator` attempt surfaced (and fixed) two real
  blockers that no amount of code review could have found without an actual
  compiler run — see `specs/071-ios-mobile-port/research.md` D8 for full detail:
  1. `firebase-core`/`firebase-messaging`'s Swift Package Manager products
     require iOS 15.0 minimum; `IPHONEOS_DEPLOYMENT_TARGET` was still the
     Flutter template's `13.0`. Bumped to `15.0` in
     `ios/Runner.xcodeproj/project.pbxproj` (all 3 occurrences) — a
     build-config change only, no app behavior affected.
  2. `EdgeIdentityPlugin.swift` and `X509SelfSigned.swift` — both written
     without Xcode access — had genuinely **never been added to the Xcode
     project at all** (zero `PBXFileReference`/`PBXBuildFile`/Sources-phase
     entries). The build failed with `Cannot find 'EdgeIdentityPlugin' in
     scope`, confirming this file had truly never compiled. Fixed by adding
     both files to the `Runner` target via the `xcodeproj` Ruby gem
     (equivalent to dragging them into Xcode and checking "Add to target").
  After both fixes: `flutter build ios --debug --simulator` succeeds
  (`✓ Built build/ios/iphonesimulator/Runner.app`), and `xcrun simctl
  install`/`launch` confirm the app runs without crashing — the Dart VM
  service starts, and it correctly lands on the "Scan Border QR Code"
  enrollment screen (`EnrollmentGate` routing works) with a real system
  camera-permission dialog showing the exact `NSCameraUsageDescription` text
  from `Info.plist`. This is strong evidence `EdgeIdentityPlugin.register(with:)`
  runs at launch without crashing.
  - **Still unverified — needs a real device**: Secure Enclave key
    generation/signing, Face ID, and a real camera feed are all unavailable on
    the Simulator regardless of tooling. This needs a signing team selected in
    Xcode (requires the operator's own Apple ID — an interactive step no agent
    can do) and a physically connected iPhone. Neither was available as of this
    pass.
  - **Still unverified — needs interactive tapping**: the "Can't scan? Enter
    manually" fallback screen was reached in principle (the enrollment screen
    rendered correctly) but never actually tapped through and submitted — no
    CLI-only UI-automation tool was available/attempted for that.
  - `AppDelegate.swift` uses the stock `FlutterAppDelegate` with no
    `FlutterFragmentActivity`-style change, and the app launched successfully
    with it — consistent with the expectation that iOS's `local_auth` needs no
    such change, though the actual Face ID prompt itself is still unconfirmed
    (needs a real device).
  Remaining work: `specs/071-ios-mobile-port/tasks.md` Phase 1 (T004/T005,
  both requiring the operator's hands) through the rest of the task list.
- **watchOS** (spec `072-apple-watch-companion`, 2026-07-27): a native SwiftUI
  watch companion app (`mobile/netclaw-mobile/ios/WatchApp Watch App/`) that
  relays everything through the paired iPhone's already-running NetClaw Mobile
  app via `WatchConnectivity` — it has no identity, enrollment, or network
  connection of its own (FR-011). **Verified end to end on real hardware**
  (a physical Apple Watch Series 7, watchOS 26.6, paired with the iPhone from
  spec 071's real-device verification) — not just the Simulator, which hit an
  unresolved rendering quirk (backend message exchange succeeded per device
  logs, but the watch UI never visibly progressed past a spinner) and was set
  aside in favor of hardware. All four tabs confirmed working against a real
  Border: Approvals (approve/deny with a fresh on-device passcode confirmation
  per FR-003, correctly attributed as `confirmation_method: "watch_passcode"`
  — never `"biometric"` — on the Border's own audit record), Feed (read-only
  pushed messages), Ask (dictated/typed question through the same
  `n2n/edge/ask` path as the phone's chat), and History (an addition beyond
  the original three-capability scope, added after real-device testing showed
  the operator wanted past chat Q&A visible on the wrist).
  - Getting a real watch discoverable in Xcode at all required unpairing and
    re-trusting the paired iPhone in Xcode's Devices and Simulators window —
    the watch's connection is proxied entirely through the phone's own trust
    relationship with the Mac, not established independently.
  - A cross-SDK build trap cost significant time: `xcodebuild -sdk
    iphonesimulator`/`-sdk iphoneos` as a blunt global flag forces that SDK
    onto every target in the build graph, including the embedded watchOS
    dependency — breaking `WCSessionDelegate` conformance with confusing
    "does not conform to protocol" errors. Fixed by using `-destination
    'id=<device>'` exclusively and never `-sdk`.
  - A Release-configuration build of `Runner` (needed to run the phone app
    without Xcode attached at all — a Flutter debug/JIT build refuses to
    launch without the tooling attached) originally hit a second variant of
    the same platform-bleed problem: even with a concrete `-destination`,
    Xcode's implicit build of the embedded `WatchApp` dependency compiled it
    against an iOS deployment target, breaking watchOS 10+-only APIs
    (`ContentUnavailableView`) and `WCSessionDelegate` conformance
    identically. **Root cause found and fixed (2026-07-29):** the `WatchApp`
    target inherited `SUPPORTED_PLATFORMS = iphoneos` from the project while
    its own `SDKROOT`/`PLATFORM_NAME` were `watchos` — that mismatch is what
    forced the embedded (and even standalone-scheme) build into an iOS
    context. Setting `SUPPORTED_PLATFORMS = "watchos watchsimulator"` on all
    three `WatchApp` build configurations resolves it. `flutter build ios
    --release` now produces one Release archive with **both** apps properly
    embedded (`Runner.app/Watch/WatchApp.app`); installing that phone build
    provisions the watch companion to the paired Apple Watch automatically —
    no more detach/restore workaround, no separately-installed Debug watch
    build. Verified end to end: combined Release build installed to the
    physical iPhone (466) with the watch app embedded, feature `073`.
- **Real local push notifications, unread tracking, and cross-device sync**
  (spec `073-push-notifications-sync`, 2026-07-29): the phone now posts an
  actual local notification (via `flutter_local_notifications`, not the
  credential-blocked remote FCM/APNs path below) for a new Feed message, a
  completed chat answer, or a new approval — while the app process is alive,
  foreground or backgrounded. Approval notifications carry inline
  Approve/Deny actions gated by `DarwinNotificationActionOption
  .authenticationRequired` AND the exact same fresh, never-cached biometric
  confirmation the in-app buttons use (extracted into
  `lib/ncfed/approval_confirmation.dart`, now the one shared entry point for
  both). The watch inherits every notification and the combined app badge
  purely via standard watchOS mirroring — no new watch-side
  background-delivery code was added (confirmed by code review, FR-010).
  `MessageFeedStore`/`ConversationStore` gained per-item `acknowledged` state
  (with a load-bearing migration rule: a message/turn written before this
  feature shipped defaults to *already acknowledged* on load, not unread —
  getting that backwards would have made every pre-existing item appear new
  the moment an operator upgraded) plus `acknowledge()`/`delete()`, exposed
  on both phone screens and the watch's Feed/History tabs (swipe actions),
  and four new watch-relay methods. A real, pre-existing defect is also fixed
  here: `watch_relay.dart`'s `_submitAsk`/`_askStatus` now actually record
  into the shared `ConversationStore` (with `origin: "watch"`) — previously
  a question asked from the watch never appeared in the phone's Chat tab or
  the watch's own History tab at all. The watch's Feed/History/Ask views
  gained an on-demand "read aloud" control (`SpeechPlayback.swift`,
  `AVSpeechSynthesizer`) that only ever speaks on an explicit tap.
  - **Verified**: all Dart-side logic (stores, relay methods, notification
    payload/dedup/badge helpers, the generalized `NotificationDeepLink`
    dispatcher, the Border's `already_resolved` addition) via the automated
    suite — `flutter analyze` clean, full `flutter test` suite passing with
    zero regressions, `python3 -m pytest tests/n2n` passing. All new watchOS
    Swift code (`FeedView.swift`/`HistoryView.swift`/`AskView.swift`/
    `WatchDataStore.swift`/`SpeechPlayback.swift`) compiles cleanly against
    the real, physical Apple Watch from spec 072 (`xcodebuild ... -destination
    'id=<device>' build` succeeded).
  - **Not yet verified**: the actual on-device behavior of every capability
    above (notification banners actually appearing, the watch's own
    home-screen badge mirroring per FR-009, swipe-to-acknowledge/delete on
    real hardware, the notification-tap authenticated-action flow, read-aloud
    audibly speaking) — this needs the operator physically present with both
    devices unlocked and nearby, which wasn't available for this pass. Do
    not assume this works from a clean compile alone; a real-hardware pass
    matching spec 072's own verification standard is the next step before
    this can be marked fully done.
- Push-notification delivery (FCM/APNs, feature 066 US3) needs real Firebase/Apple
  Developer credentials configured on the Border (`.env.example`'s
  `FCM_SERVICE_ACCOUNT_JSON`/`APNS_*` vars) and a real `Firebase.initializeApp()`
  setup in the app (`google-services.json` / `GoogleService-Info.plist`) — neither
  exists in this repo; wire them in with your own project's credentials. Note that
  `main.dart`'s `_tryRegisterPush()` swallows the resulting failure to a
  `debugPrint`, so **push silently does nothing rather than erroring** until those
  credentials exist. Notification-tap deep-linking is wired on the same success
  path: it jumps to the Feed tab and highlights the referenced message. Since
  spec 107 that works even when the message has not arrived yet — the tap records
  a `PendingOpenIntent` (`lib/ncfed/pending_open_intent.dart`) which resolves when
  the message lands, or gives up after 8s. Foreground pushes are also recorded
  straight from their data payload (`lib/ncfed/push_message_ingest.dart`), so a
  pushed message is readable without a live channel; `MessageFeedStore.append`
  deduplicates on `pushed_at`, which is what stops that path and the Border's
  replay from each storing their own copy.
- Voice transcription (`speech_to_text`, feature 067 US4) and the device deep link
  (`app_links`, feature 067 US5) are wired in and pass their unit tests, but — like
  push notifications — haven't been exercised against a real microphone or a real
  tapped/scanned link on either platform.
- Feature 068's `local_auth`/`camera` packages need no manual `AndroidManifest.xml`
  permission entries — both merge their own required permissions (`CAMERA`,
  `RECORD_AUDIO`, `USE_BIOMETRIC`) in automatically via Gradle manifest merging.
  `INTERNET` is the exception and **is** declared explicitly in
  `android/app/src/main/AndroidManifest.xml`: it previously reached release builds
  only as a merge side-effect of `firebase_messaging`, so dropping that dependency
  would have silently broken networking in release with no compile-time error. On
  iOS, `local_auth`'s Face ID needs `NSFaceIDUsageDescription` (Touch ID/Android's
  BiometricPrompt need no key at all) — added to `Info.plist` alongside the
  existing camera/microphone keys, which now also cover the `camera` package's
  photo/video capture use (not exercised on iOS, same Xcode/Mac caveat as above).
- **1.0.1 polish pass** (spec `109-mobile-polish-pass`, 2026-08-15, version bumped
  `1.0.0+1` → `1.0.1+2`): dark mode (a proper dark `ColorScheme`, `themeMode:
  ThemeMode.system`, a repo-hygiene test locking the color-literal sweep in going
  forward), selectable/copyable/shareable Markdown-or-preformatted rendering for
  chat answers and Feed messages (`flutter_markdown_plus` — `flutter_markdown` is
  confirmed discontinued by its own publisher), Time Sensitive approval
  notifications, an operator-adjustable Face ID app-lock gate wrapping the entire
  app root, haptic feedback on six key events (phone + watch), live search/filter
  across Chat and Feed, and a fix for the Dashboard's "Unread"/"Pending approvals"
  rows previously doing nothing on tap.
  - **Verified**: everything above via the automated suite — `flutter analyze`
    clean, full `flutter test` suite passing (360/360, zero regressions, zero
    skipped tests) — consistent with this spec's own scoping to avoid anything
    that could only be proven on a physical device.
  - **Verified via `xcodebuild`, not on real hardware**: the watch-side haptic
    additions (`ApprovalsView.swift`/`WatchDataStore.swift`) compile cleanly
    (`xcodebuild -workspace Runner.xcworkspace -scheme WatchApp -sdk
    watchsimulator` → `BUILD SUCCEEDED`, both before and after the changes).
    Whether they actually *feel* right on a wrist has not been checked.
  - **Not verified — needs a physical device**: (1) the long-answer
    scroll-performance scenario (profiling a ~5000-character answer for dropped
    frames) — Clarifications (2026-08-14) scoped this to a manual/qualitative
    check specifically because it cannot be proven by `flutter test`, and no
    device pass has happened yet; (2) Time Sensitive delivery actually
    surviving a real Focus mode (iOS Focus modes have no meaningful Simulator
    equivalent); (3) the Face ID app-lock's actual biometric prompts — every
    automated test exercises the injected `authenticate` fake, never
    `local_auth`'s real platform channel; (4) all six phone-side haptics'
    actual feel, same caveat as approvals confirmation/device-removal haptics
    elsewhere in this document.
  - One behavior change worth calling out explicitly rather than letting it be
    discovered later: with app-lock enabled, an approval notification's
    Approve/Deny action can no longer resolve until the app itself is
    unlocked, because `HomeShell` — where the notification-response handler is
    wired — does not mount at all until `AppLockGate` authenticates. This is
    the intended, more conservative posture (a locked phone should not be able
    to approve a network change), not a regression, but it is a real change in
    what "tap Approve from the lock screen" does once app-lock is turned on.
- **Siri / App Intents (B1a)** (spec `111-siri-app-intents`, 2026-08-15): three
  native `AppIntent`s — `AskBorderIntent` ("Hey Siri, ask NetClaw [question]",
  headless submit + spoken acknowledgment, real answer arrives later as a
  local notification), `PendingApprovalsIntent`, and `BorderHealthIntent` —
  exposed via one `AppShortcutsProvider` (Siri, the iPhone 15 Pro+ Action
  Button, and Shortcuts automations, with zero manual setup). Each launches a
  headless `FlutterEngine` (the same pattern spec 099's background refresh
  established) rather than opening the app. `PendingApprovalsIntent` required
  one new, narrowly-scoped Border-side RPC (`n2n/edge/approvals_list`) since
  no existing passive/cached source could give a live count without
  under-counting (research.md R3); `BorderHealthIntent` needed zero Border
  changes, since "Border health" in this app has always been a passively
  cached on-device value, not a request/response query (research.md R4).
  - **Verified**: `flutter analyze` clean, full `flutter test` suite passing
    (378/378, zero regressions), the new `tests/n2n/
    test_edge_approvals_list.py` (3/3), the full `tests/n2n` suite
    unaffected (455 passed, the same 14 pre-existing environment-only
    failures — missing `chromadb`, a Python-version-dependent
    `OSError`/`ConnectionRefusedError` string check — present and unaffected
    both before and after this change), **and a full `xcodebuild -workspace
    Runner.xcworkspace -scheme Runner -sdk iphoneos -configuration Debug
    build CODE_SIGNING_ALLOWED=NO` → `BUILD SUCCEEDED`**, compiling and
    linking all three new `AppIntent`s and the `AppShortcutsProvider` into
    `Runner.app` with zero warnings in any of the five new Swift files. The
    first `xcodebuild` attempt during this spec failed on a **stale**
    `ios/Flutter/ephemeral/Packages/FlutterGeneratedPluginSwiftPackage/
    Package.swift` — regenerated with a hardcoded iOS 13 platform floor
    instead of picking up `AppFrameworkInfo.plist`'s `MinimumOSVersion` 16.2
    (the actual fix, already correctly in place, documented in spec 099's own
    blog post). `flutter pub get` alone does not regenerate this file
    correctly; `flutter build ios --config-only --debug` does. Worth noting
    for future specs hitting the same class of failure spec 110 also
    reported: it is a stale-cache artifact, not a genuine unfixable
    limitation — re-running the config-only build resolves it.
  - **Not verified — needs a physical device**: everything Siri/Action-
    Button/Shortcuts-specific in this spec is 🔌 DEVICE-only per its own
    spec.md — real voice invocation, the spoken acknowledgment timing, the
    real-answer notification actually arriving, `ProcessInfo.
    performExpiringActivity`'s actual granted runtime (`AskBorderIntent.
    swift`'s best-effort post-acknowledgment window, research.md R8 — the
    requested 25s budget is a request, not a guarantee, and its real-world
    value is unverified), and the Border-unreachable/not-enrolled spoken
    failure paths for all three intents.
- **Watch Double Tap + corner complication (B4+B5)** (spec
  `112-watch-double-tap-complication`, 2026-08-15): Double Tap on a Series
  9/Ultra 2-or-later watch now triggers the topmost pending approval's
  existing, passcode-gated "Approve" action (never a separate, less-gated
  path — it invokes the identical `Button.action` closure a manual tap
  already uses) and, separately, the "Read aloud" button in the Ask view.
  Both `HeartbeatComplication` and `PendingApprovalComplication` gained
  `.accessoryCorner` support for Infograph watch faces, reusing their
  existing views unchanged. No deployment-target change (Double Tap is
  gated by `if #available(watchOS 11.0, *)`, keeping the 10.0 floor intact
  for older watches, FR-006) and no new Xcode target or entitlement (FR-009).
  - **Verified**: `flutter analyze` clean, full `flutter test` suite passing
    (378/378, zero regressions — this spec touches no Dart code at all), and
    `xcodebuild -workspace Runner.xcworkspace -scheme WatchApp -sdk
    watchsimulator -configuration Debug build CODE_SIGNING_ALLOWED=NO` →
    `BUILD SUCCEEDED`, which embeds and builds `WatchComplication.appex` as
    part of the same scheme (confirming both targets in one build). The four
    modified Swift files parse cleanly via `swiftc -parse` with zero syntax
    errors.
  - **Note on verification method**: a standalone `xcodebuild -scheme
    WatchComplication -sdk watchsimulator` invocation was deliberately not
    used to verify B5 — confirmed via `git stash` that it fails on
    completely unmodified code too, hitting the exact "cross-SDK build trap"
    already documented above for spec 072 (`-sdk` as a blunt flag forces
    every workspace target, including phone-only plugins like
    `mobile_scanner`/`local_auth_darwin` with no watchOS platform support at
    all, onto the watch SDK). The `WatchApp` scheme's build, which correctly
    embeds `WatchComplication.appex`, is the accurate verification vehicle.
  - **Not verified — needs a physical device**: everything in this spec is
    🔌 DEVICE-only per its own spec.md — a real Double Tap gesture (a
    hardware-gated system gesture with no Simulator equivalent), and real
    corner-slot placement/legibility on an actual Infograph watch face.
    Also unverified: backwards-compatibility behavior on a pre-Series-9
    watch or a Series 9/Ultra 2 watch running below watchOS 11 (FR-004) —
    no such device was available during this pass.
- **Interactive and in-flight Live Activity (B3)** (spec
  `113-live-activity-interactive-inflight`, 2026-08-15): the pending-approval
  Live Activity gained Approve/Deny buttons (iOS 17+, `Button(intent:
  ApprovalActionIntent())`) that foreground the app to Approvals — never
  resolving anything directly, since a `LiveActivityIntent` cannot reliably
  present the existing biometric/passcode confirmation from the background,
  and this spec deliberately does not weaken that spec-073 invariant to make
  the button "work." The activity also now dismisses correctly when resolved
  from any surface (in-app, notification, watch), not just a tap on the
  activity itself. Separately, a brand-new in-flight query Live Activity
  starts per submitted question, showing the question and a live elapsed
  timer, updated with the Border's own free-text progress detail — research
  performed before writing this spec found the brief's original
  `respondedMembers`/`expectedMembers` design describes a concept that
  doesn't exist in the Border's actual sequential-delegation model (a
  submitted ask is one agent turn discovering delegated members one at a
  time, confirmed against a real captured trace), so this spec deliberately
  narrowed scope to what the system genuinely knows rather than fabricate a
  member count.
  - **Verified**: `flutter analyze` clean, full `flutter test` suite passing
    (397/397, zero regressions), including new coverage for
    `live_activity.dart`'s start/update/end/startAsk/updateAsk/endAsk call
    sequencing against a fake `MethodChannel` and the new
    `netclaw://approvals`/`netclaw://chat/<taskId>` deep-link parsers. A full
    `xcodebuild -workspace Runner.xcworkspace -scheme Runner -sdk iphoneos`
    → `BUILD SUCCEEDED`, compiling the three new Swift files
    (`ApprovalActionIntent.swift`, `AskActivityAttributes.swift`,
    `AskLiveActivityView.swift`) into their correct target(s) alongside the
    existing `LiveActivityWidget` extension.
  - **A real dual-Xcode-target-membership mistake was caught by the build,
    not assumed correct**: `ApprovalActionIntent.swift` was first added
    `Runner`-only (reasoning it only foregrounds the app), but
    `PendingApprovalLiveActivityView.swift`'s `Button(intent:
    ApprovalActionIntent())` calls are compiled *into* the
    `LiveActivityWidget` extension target, which therefore needs the
    concrete type too — `xcodebuild` failed with `cannot find
    'ApprovalActionIntent' in scope` until fixed. Fixing that, in turn,
    surfaced a second real problem: `UIApplication.shared` (used to open the
    `netclaw://approvals` deep link) is unavailable in application
    extensions, so the same file failed to compile a second way once
    dual-membered. Fixed with a custom `IS_EXTENSION_TARGET`
    `SWIFT_ACTIVE_COMPILATION_CONDITIONS` flag on the `LiveActivityWidget`
    target and an `#if !IS_EXTENSION_TARGET` guard around that one call —
    the extension's copy of `perform()` never actually executes at runtime
    anyway (`openAppWhenRun` always dispatches execution into the app
    process), so this is provably safe, not a workaround masking a real gap.
    Neither problem was caught by `swiftc -parse`/SourceKit single-file
    checks — only a real, full `xcodebuild` run found either, reinforcing
    why this spec's own quickstart.md treats that as mandatory before
    calling any Swift-side task done.
  - **Not verified — needs a physical device**: everything Live-Activity-
    rendering-specific in this spec is 🔌 DEVICE-only per its own spec.md —
    the real interactive Lock Screen button and its foreground behavior, the
    activity dismissing correctly when resolved elsewhere, the in-flight
    activity's real ticking timer and Dynamic Island rendering, and its
    `staleDate` actually taking effect on a genuinely abandoned ask (a
    ~780-second wait, impractical to sit through in one verification pass —
    verified by code review instead that the value mirrors the Border's own
    ask-timeout ceiling, not an arbitrary guess).
- **Home screen, Lock Screen, and Control Center widgets (B1b+B2)** (spec
  `114-widgets-controlwidget`, 2026-08-15, iOS 18+ only — the operator
  explicitly authorized dropping pre-iOS-18 support for this one target):
  a new `NetClawWidgetExtension` target (created by the operator via Xcode's
  own Widget Extension wizard, registered with a new phone-only App Group,
  `group.ca.automateyournetwork.netclaw.mobile.ios`) now shows Border
  health, pending-approval count, and the last heartbeat's age — on the home
  screen (small/medium), the Lock Screen (`.accessoryCircular`/
  `.accessoryRectangular`/`.accessoryInline`), and Control Center. Every
  reading is explicitly timestamped, never implied live; no widget shows any
  per-approval detail, matching the existing Live Activity's identical
  restriction. Tapping any widget deep-links via the same `netclaw://`
  mechanism specs 111/113 already established.
  - **A real, two-part target-setup defect was found and fixed before any
    feature code was written**, caught by a full `xcodebuild` run, not
    assumed correct from the operator's own Xcode wizard output: the new
    target had been embedded under `WatchApp` instead of `Runner` (wrong
    bundle identifier, `ca.automateyournetwork.netclaw.mobile.watchapp
    .NetClawWidget`; wrong, old watch-only App Group in its own
    entitlements; `TARGETED_DEVICE_FAMILY = 4`, the Watch code, instead of
    `1,2` for iPhone/iPad). Fixed via the `xcodeproj` gem: moved the target
    dependency and embed-phase reference from `WatchApp` to `Runner`,
    corrected the bundle identifier to
    `ca.automateyournetwork.netclaw.mobile.netclawwidget`, corrected the
    entitlements to the new phone App Group, and corrected the device
    family. Xcode's own default `ControlWidget` template code also required
    iOS 18 (`buildExpression`) while inheriting the project's 16.2 floor —
    fixed by setting the new target's own deployment target to 18.0,
    explicitly authorized by the operator for this target only (`Runner`'s
    and `WatchApp`'s own floors are unchanged).
  - **The brief's own Control Center design was corrected during planning,
    before implementation**: the source brief described tapping the control
    as invoking `AskBorderIntent` directly, but that intent requires a
    `question: String` parameter Control Center has no text-entry surface to
    collect. The control instead shows the cached pending count and, on tap,
    foregrounds Chat ready to type — reusing the exact `openAppWhenRun` +
    `netclaw://` pattern spec 113's Approve/Deny buttons already
    established, including the same `IS_EXTENSION_TARGET` compile-guard
    technique for its own `UIApplication.shared` call (also newly applied to
    the `NetClawWidgetExtension` target, which didn't have that flag yet).
  - **Verified**: `flutter analyze` clean, full `flutter test` suite passing
    (408/408, zero regressions), including new coverage for
    `widget_data.dart`'s mirror-call wiring and the two new
    `netclaw://dashboard`/`netclaw://chat` deep-link parsers. A full
    `xcodebuild -workspace Runner.xcworkspace -scheme Runner -sdk iphoneos`
    → `BUILD SUCCEEDED`, zero warnings anywhere in the new/changed files,
    compiling all of `NetClawWidget.swift`/`NetClawWidgetControl.swift`/
    `AppIntent.swift`'s real content (no Xcode placeholder "favorite emoji"/
    "timer" template code remains anywhere).
  - **Not verified — needs a physical device**: everything in this spec is
    🔌 DEVICE-only per its own spec.md — real widget placement and rendering
    on an actual home screen/Lock Screen, real refresh timing under iOS's
    own budget, and real Control Center interaction.
