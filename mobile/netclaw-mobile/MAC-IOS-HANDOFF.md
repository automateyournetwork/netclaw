# NetClaw Mobile — Mac / iOS Handoff

**Read this first on the Mac.** It replaces the throwaway kickoff prompt from the
2026-07-23 Android session (which was written to a scratchpad and lost — hence
this file lives in the repo now).

Last updated: **2026-07-25**, at the end of the Android verification pass.

---

## Where things stand

The Android/Dart/Python side of specs **066** (NCFED edge node), **067**
(mobile command channel) and **068** (biometrics/capture) is done, merged, and
— as of 2026-07-25 — **verified against the real production Border with a real
round trip from an emulated phone**.

Merged: **#159, #161, #162, #163** (the 066→067→068 stack), **#164**
(branding/icon, persisted reconnect, first real end-to-end proof, HUD phone
glyph), **#166** (heartbeat, stale-answer recovery, session-key fix, manual
enrollment fallback, HUD edge-node liveness), **#170** (orphaned-task cancel).

Pull `main` and confirm **#170** is merged before starting.

### Proof the stack works end to end

From 2026-07-25 13:04–13:06 local, a question typed on the emulated phone
("check the CML lab R1 interfaces, test them and report back") produced:

| Time | Event |
|---|---|
| 13:04:33 | Edge WS accepts the ask, capability negotiate (proto 053) |
| 13:04:46 | `cml-lab-lifecycle` → member `johns-risk/cml` completed |
| 13:04:59 | Router picks `pyats-health-check` → `johns-risk/pyats`, GAIT logged |
| 13:06:10 | pyATS returns `in_scope/success` |
| 13:06:46 | 1583-byte answer delivered to the handset — **2m13s end to end** |

Enrollment, edge WS transport, delegation, routing, GAIT audit, and result
delivery are all real. iOS is the only unproven platform.

---

## What's already built (verify/wire up on iOS — do not rebuild)

Everything under `mobile/netclaw-mobile/`:

- **`EdgeIdentity`** (`lib/ncfed/edge_identity.dart`) — platform-channel
  interface. iOS native side is `ios/Runner/EdgeIdentityPlugin.swift` (Secure
  Enclave keygen/signing) and `ios/Runner/X509SelfSigned.swift` (manual
  self-signed cert builder — iOS has no equivalent of AndroidKeyStore's cert
  convenience). **Both were written without a Mac and are entirely unverified.**
  This is the actual iOS work: get them compiling, generate a real Secure
  Enclave key, sign real challenge nonces, build a real X.509 cert from it.
  The Secure Enclave does not exist on the Simulator — you need a real device
  for keygen/signing. Simulator is fine for build + UI sanity.
  - Android's working equivalent is
    `android/app/src/main/kotlin/.../MainActivity.kt` — read it as the
    reference implementation. It is confirmed to link and run on a real
    emulator, so its shape is trustworthy.
- **`AppDelegate`/`SceneDelegate`** — Android needed `FlutterActivity` →
  `FlutterFragmentActivity` for `local_auth`. Confirm whether iOS needs an
  analogous change (it likely does not).
- **Everything else is pure Dart** and should behave identically on iOS:
  enrollment (QR *and* manual), ask/chat, approvals, capture UI, capability
  registration, heartbeat, persisted reconnect.
- **App icon/splash** via `flutter_launcher_icons`/`flutter_native_splash` from
  `assets/icon/icon.png`. The generator targets both platforms, but the iOS
  icon has never been eyeballed on a device. See `ASSETS.md`.

---

## Corrections to the old draft — these are now FIXED, don't go hunting

The 2026-07-23 prompt listed three gaps. Two are closed:

1. ~~Session-key bug: `n2n-edge-{member_id}` breaks on `/`~~ — **FIXED.**
   `bgp/federation/service.py:1289` now does
   `"n2n-edge-" + member_id.replace("/", "_")`. Shipped in #166.
2. ~~Enrollment is QR-scan-only with no manual fallback~~ — **FIXED.**
   `lib/screens/manual_enrollment_screen.dart` exists; `enrollment_screen.dart`
   offers "Can't scan? Enter manually" (domain/port/token fields). Shipped in
   #166. **This matters for you specifically** — it's the clean way past
   enrollment on the iOS Simulator, which has no usable camera. You no longer
   need the `integration_test/enrollment_and_ask_test.dart` trick.
3. **Face ID / `NSFaceIDUsageDescription`** — still open, still unverified.
   The key is in `ios/Runner/Info.plist` but no real Face ID prompt has ever
   fired. Confirm on a real device.

---

## Known defects — pre-existing, not yours

If you hit these on iOS, they are not iOS bugs and not something you introduced.

- **Empty result payloads survive a crash as a clean "completed".** Two
  independent holes, both found 2026-07-25:
  - `bgp/federation/audit.py:30-38` `store_result()` writes results
    non-atomically (no temp+`os.replace`+`fsync`), and returns the path even
    when the write raised. A host reboot inside the ext4 delayed-allocation
    window leaves a **0-byte** result file. Confirmed twice on this box
    (2026-07-24 14:14 and 2026-07-25 11:47, each ~12s before a reboot).
  - `bgp/federation/tasks.py:139-146` `result()` swallows the resulting JSON
    parse failure with a bare `except: pass`, returning
    `{"state": "completed"}` with no `output_text`, no `error`, and no log
    line. A lost payload is indistinguishable from a skill that returned
    nothing. `service.py:1593` then re-caches that empty reply over the
    Border's own good copy.
  - Also on that line: `resp.get("completed_at")` is always `None` because
    `TaskManager.result()` never returns the field — every outbound task row
    has `completed_at=NULL`.
  - Fourth path: `gateway.py:123-125` returns `("", 0)` when the agent CLI
    emits no stdout at all, bypassing the `"(no reply text…)"` fallback at
    `gateway.py:184`; `tasks.py:65-68` records that as `completed`.
- **Operator-side cancel doesn't notify the phone.** #170 fixed the phone's own
  Cancel button (`invocation.py:232-254` pushes `n2n/edge/ask_result` with
  `state:"cancelled"`), but the HTTP route `bgp-daemon-v2.py:422-423` returns
  `{"cancelled": …}` without the push. Cancel a stuck `edge_ask` from the
  HUD/CLI and the phone sits on "Working…" forever.
- **`ReconnectSupervisor` ignores revocation.** `reconnect_supervisor.dart:55`
  is a bare `catch (_)` that backs off forever, so a device revoked *while
  running* retries a dead enrollment indefinitely instead of returning to the
  enrollment gate. `isRevokedByBorder()` (`edge_client.dart:22-31`, added in
  #170) exists but is only consulted on cold-start reconnect.
- **`NotificationDeepLink` is orphaned code.** `lib/ncfed/notification_deep_link.dart`
  wires `onMessageOpenedApp` + `getInitialMessage()` to open the matching feed
  message, but nothing ever instantiates it — repo-wide grep finds only its own
  definition. **This bites APNs on iOS exactly as it bites FCM on Android**:
  tapping a push notification will not deep-link. Fix it once, both platforms
  benefit.

---

## Push notifications — read before doing APNs

Push is **wired in Dart, dead at runtime, on both platforms**:

- `firebase_messaging: ^16.4.3` + `firebase_core: ^4.12.1` are in `pubspec.yaml`.
- `lib/ncfed/push_registration.dart` does `requestPermission()` → `getToken()` →
  `n2n/edge/register_push` (`platform: 'apns'` on iOS).
- `main.dart:272-279` `_tryRegisterPush()` wraps `Firebase.initializeApp()` in a
  `try/catch` that **swallows failure to a `debugPrint`** — so a missing Firebase
  config produces silence, not an error. Don't be fooled by "no crash".
- Android has no `google-services.json` and no `com.google.gms.google-services`
  Gradle plugin. iOS will need the equivalent `GoogleService-Info.plist`, an
  APNs auth key uploaded to Firebase, and the Push Notifications + Background
  Modes capabilities in Xcode.

Treat push as a **separate work item**, not part of the iOS port. The core
product (enrollment → ask → answer) works without it.

---

## How to verify for real

Match the rigor of the Android pass — actually run it, don't just green the tests.

1. `flutter analyze` / `flutter test` clean (platform-agnostic, should already pass).
2. Xcode build → Simulator (UI/layout, manual enrollment path) → **real device**
   (Secure Enclave, Face ID, camera).
3. Enroll against the operator's real Border: **`N2N_EDGE_WS_PORT=8443` is
   permanently live** and confirmed serving as of 2026-07-25 13:00
   (`Edge WS listener on 0.0.0.0:8443`, risk `johns-risk`). You should not need
   to enable anything. For an isolated run instead, follow the throwaway-Border
   pattern in `specs/068-ncfed-mobile-biometrics-capture/quickstart.md`.
4. Close out the two remaining manual-verification tasks if iOS is the platform
   you do them on:
   - `specs/066-netclaw-mobile-ncfed-edge/tasks.md:121` — **T045**, full
     `quickstart.md` walkthrough steps 1–10 against a live Border.
   - `specs/067-ncfed-mobile-command-channel/tasks.md:72` — **T017**, confirm a
     federated-peer request is attributed to the external peer in the
     conversation. Note: the three eN2N peers (`as65007`, `as65008`, `as65099`)
     have been connection-refused all week — you need a reachable peer first.
5. Update `README.md`'s iOS section and 066 T044's iOS note once verified. Be
   honest about verified vs. still-assumed, the way the Android section is.

---

## Environment gotchas learned the hard way

- **`JAVA_HOME` must point at JDK 17.** The Gradle/AGP/Kotlin combination in
  this project (Gradle 9.1.0, AGP 9.0.1, Kotlin 2.3.20, `JvmTarget.JVM_17`)
  fails confusingly on newer JDKs. On the Mac, expect the same class of
  problem and pin JDK 17 for Android builds. (Irrelevant for the iOS target
  itself, relevant the moment you build Android from the Mac.)
- `mobile/netclaw-mobile/build` reaches **2.2 GB** and `.dart_tool` **334 MB**.
  Both are gitignored; don't copy them to the Mac, just `flutter pub get`.
- The repo is a **shared checkout** — other agents switch branches in it. Verify
  the branch before committing.

---

## Store-release status (Android, applies to iOS App Store too)

The user intends to publish. Current Android release config is **not
shippable**, and the same discipline will apply to the App Store:

- `android/app/build.gradle.kts:32` — release is **signed with the debug
  keystore** (`signingConfig = signingConfigs.getByName("debug")`). Play rejects
  this. No keystore exists in the repo (correctly gitignored).
- **R8/minify is off** — no `isMinifyEnabled`, no ProGuard rules file.
- Resolved SDK levels: `compileSdk 36`, `targetSdk 36`, `minSdk 24` (from the
  Flutter SDK defaults). **API 36 is already correct** for Google's
  2026-08-31 deadline — no change needed.
- `pubspec.yaml:19` — `version: 1.0.0+1` → `versionName 1.0.0`, `versionCode 1`.
- **`applicationId` is permanent once published.** See `PLAY-STORE-ROADMAP.md`.

Full path to publication, timelines, and the account-type decision (which gates
everything and cannot be changed later) are in
[`PLAY-STORE-ROADMAP.md`](PLAY-STORE-ROADMAP.md).

---

Work through this the same way the Android pass did: implement, test for real,
be honest in the docs about what's verified vs. still assumed, and open a PR
when done.
