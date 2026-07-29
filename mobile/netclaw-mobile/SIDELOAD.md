# NetClaw Mobile — sideloading (Android + iOS)

How to get NetClaw Mobile onto a real phone **before it is on either store**.
This is the AS-IS build-and-install path; it is deliberately honest about what
has actually been done versus what is documented-but-untried.

Installing the app is only half the job — a fresh install is inert until a
Border enrolls it. Do the install from this document, then hand the person
[`TESTER-INSTRUCTIONS.md`](TESTER-INSTRUCTIONS.md) and follow the operator side
in [`MOBILE-ONBOARDING.md`](MOBILE-ONBOARDING.md) to issue their enrollment
token.

| | Android | iOS |
|---|---|---|
| Can you just send a file? | **Yes** — an APK, over anything | **No.** Apple has no APK equivalent |
| Costs money? | No | Only the free 7-day route is free |
| Needs a Mac? | No | **Yes, always** — to produce any build at all |
| Best route for a non-technical tester | Send the APK | TestFlight |

---

## Prerequisites (both platforms)

```bash
git clone https://github.com/automateyournetwork/netclaw.git
cd netclaw/mobile/netclaw-mobile
flutter pub get
```

Flutter **3.44.8** is the version both this repo's Linux box and the operator's
Mac are on. See [`README.md`](README.md) for the wider toolchain notes; the two
that bite hardest are pinned here:

- **Android needs JDK 17.** Gradle 9.1.0 + AGP 9.0.1 + Kotlin 2.3.20 fail
  confusingly on newer JDKs. Pin it for Flutter only, without disturbing a
  system `JAVA_HOME` that other tooling may depend on:
  ```bash
  flutter config --jdk-dir=/usr/lib/jvm/java-17-openjdk-amd64
  ```
- **`ios/Runner.xcodeproj/project.pbxproj` has a committed `DEVELOPMENT_TEAM`**
  (`A49777FMJG`, the maintainer's). If you are not the maintainer, **iOS builds
  will fail to sign until you change it to your own team** — see
  [Building for iOS at all](#building-for-ios-at-all).

---

# Android

## Build the APK

```bash
cd mobile/netclaw-mobile
flutter build apk --release      # build/app/outputs/flutter-apk/app-release.apk
```

`--release` is what you want even for testers: the debug APK is far larger,
slower, and its Dart VM service port is open. The release build has R8
minification and resource shrinking on (`android/app/proguard-rules.pro`).

> **Read this before trusting a release build.** If `android/key.properties` is
> absent, the release APK is **signed with the Android debug key** and Gradle
> prints a warning saying so. That is fine for sideloading and is the current
> state, but such an artifact can never be uploaded to Play. It also means
> every rebuild on a *different machine* produces a differently-signed APK,
> which Android will refuse to install over the existing one — see
> [Troubleshooting](#android-troubleshooting). To sign with a real key, see
> [`README.md`](README.md#building-a-release) and
> [`PLAY-STORE-ROADMAP.md`](PLAY-STORE-ROADMAP.md).

To build a smaller APK per CPU architecture (roughly a third the size each):

```bash
flutter build apk --release --split-per-abi
```

Send `app-arm64-v8a-release.apk` — every phone made in the last several years is
arm64. If you are not sure, send the universal `app-release.apk`.

## Get it onto the phone

**Over a cable** (fastest if the phone is in front of you):

```bash
adb install -r build/app/outputs/flutter-apk/app-release.apk
```

Needs USB debugging enabled on the phone (Settings → About phone → tap *Build
number* seven times → Developer options → USB debugging), and you must accept
the "Allow USB debugging?" prompt on the phone itself.

**Remotely** — just send the `.apk` file. Signal, Drive, Dropbox, email, a web
link, whatever the person can open. There is nothing else to it; the APK is
self-contained.

## What the tester will see

Both of these are expected and neither means anything is wrong:

1. **"For your security, your phone is not allowed to install unknown apps from
   this source."** The permission is per-source, so it must be granted to
   whichever app is doing the opening (Files, Chrome, Gmail…). Tap **Settings**
   → **Allow from this source** → back → **Install**.
2. **Play Protect: "Unsafe app blocked"** or "app scan" prompt. This fires for
   any app not distributed through Play. Tap **More details** → **Install
   anyway**.

There is no way to suppress either warning short of publishing to Play. If a
tester is uneasy, that reaction is reasonable and the honest answer is that
these warnings exist precisely because sideloading bypasses Google's review.

## Android troubleshooting

| Symptom | Cause and fix |
|---|---|
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` / "App not installed" over an existing copy | The new APK is signed with a different key than the installed one — typically a debug-signed build from a different machine. Uninstall the old copy first. Enrollment does not survive this; issue a fresh token. |
| `INSTALL_FAILED_USER_RESTRICTED` on a Xiaomi/Redmi/POCO | MIUI blocks `adb install` separately. Developer options → **Install via USB** must be on, which needs a signed-in Mi account. |
| `adb devices` shows `unauthorized` | The USB-debugging trust prompt was not accepted on the phone. Unplug, replug, accept. |
| App installs but immediately closes | Get the real error: `adb logcat -d \| grep -iE "flutter\|AndroidRuntime"`. A crash only in release and not in debug points at a missing R8 keep rule in `android/app/proguard-rules.pro`. |
| Camera permission dialog never appears | The tester previously chose "Don't ask again". Settings → Apps → NetClaw → Permissions → Camera → Allow. |

---

# iOS

**There is no iOS equivalent of sending someone an APK.** Every route below
requires a Mac with Xcode to *produce* the build, and Apple gates who may
install it. Pick a route by who the tester is:

| Route | Costs | Tester needs | Expires | Apple review |
|---|---|---|---|---|
| **TestFlight** ← use this | $99/yr | Just the TestFlight app + a link | 90 days per build | Once, for external testers (24–48h) |
| **Ad Hoc IPA** | $99/yr | You to register their device UDID first | 1 year | None |
| **Free Personal Team** | Free | **Their own Mac**, cabled | **7 days** | None |

## Building for iOS at all

Before any route, the project must sign as *you*:

1. Open `ios/Runner.xcworkspace` in Xcode (**the workspace, not the
   `.xcodeproj`** — this project uses Swift Package Manager, so there is no
   Podfile).
2. Select the **Runner** target → **Signing & Capabilities** → set **Team** to
   your own. This overwrites the committed
   `DEVELOPMENT_TEAM = A49777FMJG`. Leave **Automatically manage signing**
   ticked.
3. The bundle identifier is `ca.automateyournetwork.netclaw.mobile`. If you are
   not the maintainer you must change it to something in a domain you control —
   two teams cannot both claim the same bundle ID.

Deployment target is **iOS 15.0** (raised from Flutter's default 13.0 because
Firebase's SwiftPM products require it).

### On iOS 16 and later, the device needs Developer Mode

For anything not installed from the App Store or TestFlight, on the *phone*:
Settings → Privacy & Security → **Developer Mode** → on → **reboot**. The toggle
does not appear until the device has been connected to Xcode at least once.
This trips up nearly everyone the first time.

## Route 1 — TestFlight (recommended)

The only route that feels like "send them a link", and the only one a
non-technical tester can complete alone. Requires Apple Developer Program
enrollment ($99/yr).

```bash
flutter build ipa
```

Then upload `build/ios/ipa/*.ipa` via Xcode's Organizer or Transporter.app to
App Store Connect. Once the build finishes processing:

- **Internal testing** — up to 100 testers, but each must be a member of your
  App Store Connect team. Available immediately, **no Apple review**. This is
  where you smoke-test your own builds.
- **External testing** — up to 10,000 testers by email invite or a public link.
  The **first** build requires a one-time **Beta App Review** (typically
  24–48h). Subsequent builds usually go out without re-review.

The tester installs Apple's **TestFlight** app from the App Store, opens your
link, and taps Install. That is the whole tester experience.

Builds expire **90 days** after upload. A long beta means re-uploading
periodically.

## Route 2 — Ad Hoc IPA

No Apple review and a full year of validity, but you must know every device in
advance. Requires the $99 enrollment.

1. Collect each tester's **UDID**. On the device: Settings → General → About →
   tap the serial number to reveal it, or connect to a Mac and read it in
   Finder. (Third-party "get my UDID" web pages exist and work by installing a
   configuration profile — think about whether you want to route a tester
   through one.)
2. Register each UDID in the Apple Developer portal. **Up to 100 devices per
   product type per membership year**, and the list can only be *reset* — not
   individually pruned — at renewal.
3. Create an Ad Hoc provisioning profile including those devices.
4. Build and export:
   ```bash
   flutter build ipa --export-method ad-hoc
   ```
5. Send the `.ipa`. The tester installs it via Apple Configurator on a Mac, or
   you host the `.ipa` alongside a `manifest.plist` on **HTTPS** and send an
   `itms-services://` link they can tap.

Adding one tester later means registering their UDID, regenerating the profile,
and rebuilding. That overhead is the reason TestFlight is recommended instead.

## Route 3 — Free Personal Team

The only genuinely free route, and the one with the sharpest limits. Sign in to
Xcode with any Apple ID; the "Personal Team" appears automatically.

**This is the route that has actually been exercised on this project** — the
current physical-device builds were produced by cabling an iPhone to the Mac and
running from Xcode.

Its constraints make it unusable for anyone but a developer:

- **The signature expires after 7 days.** The app then refuses to launch and
  must be reinstalled from Xcode. There is no way to extend this.
- The tester needs **their own Mac**, cabled, with this repo checked out.
- Maximum **3 sideloaded apps** per device, and **10 App IDs per 7 days** per
  Apple ID.
- **Push notifications are not available to a free Personal Team.** Once push is
  finished, this route cannot exercise it — you need the paid program.

```bash
flutter devices                       # confirm the phone is listed
flutter run --release -d <device-id>
```

## iOS troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Signing for "Runner" requires a development team` | The committed `DEVELOPMENT_TEAM` is not yours. Set your own team in Xcode (see above). |
| "Untrusted Developer" when tapping the app | Settings → General → **VPN & Device Management** → your developer profile → **Trust**. |
| The app launched fine last week, now it won't open | The 7-day free-provisioning signature expired. Reinstall from Xcode. |
| Build fails on a Firebase SwiftPM product | `IPHONEOS_DEPLOYMENT_TARGET` must be **15.0** or higher, in all three places in `project.pbxproj`. |
| Face ID never prompts | Face ID must be enrolled in iOS Settings first; `NSFaceIDUsageDescription` is already present in `ios/Runner/Info.plist`. |
| Secure Enclave key generation fails | The Simulator has no Secure Enclave. Use a real device — enrollment on the Simulator is only reachable via the manual (non-QR) path. |

---

## After the install — enrollment

The app opens on the enrollment screen and can do nothing until a Border
enrolls it.

```bash
./scripts/netclaw risk token --edge <their-name>-<platform>
```

Screenshot the QR it prints and send it with the build. If the camera cannot
focus on the QR, the tester taps **"Can't scan? Enter manually"** and types the
domain, port, and token — this produces exactly the payload a scan would.

Tokens are **single-use** and, by default, **do not expire** — treat an unclaimed
one as live bearer credentials. Full operator procedure, security model, and
revocation are in [`MOBILE-ONBOARDING.md`](MOBILE-ONBOARDING.md).

---

## Where sideloading stops

Sideloading is a bridge, not a destination. Both stores are being pursued:

- [`PLAY-STORE-ROADMAP.md`](PLAY-STORE-ROADMAP.md) — Google Play
- [`APP-STORE-ROADMAP.md`](APP-STORE-ROADMAP.md) — Apple App Store

On Android, sideloading works indefinitely and is a legitimate long-term
distribution channel if you accept the Play Protect friction. **On iOS it is
not** — every route above either expires (7 days, 90 days) or caps out (100
UDIDs), so App Store or TestFlight is the only durable answer.
