# NetClaw Mobile — Google Play publication roadmap

Captured 2026-07-25, **corrected 2026-07-26**. Sequenced against **this repo's
actual build config**, not a generic checklist.

> **Provenance:** the Google policy facts below (fees, deadlines, tester rules,
> review windows) come from the operator's own research pass, not from
> verification by this repo's tooling. Re-check them against Google's own docs
> before acting — Play policy shifts year to year. Everything under "our
> current state" *was* verified directly against the files cited.

> **2026-07-26 correction.** The Phase 2 table in the 2026-07-25 version of this
> document listed four items as outstanding that had already shipped — the
> `applicationId`, R8/ProGuard, the explicit `INTERNET` permission, and the
> `pubspec.yaml` description. `APP-STORE-ROADMAP.md` flagged the first of these;
> all four are now corrected below against the files as they actually stand.
> **Phase 2 is nearly finished, not barely started.**

---

## The deadline that shapes the schedule

Per the operator's research: from **2026-08-31**, new apps and updates must
target **Android 16 (API 36)** or higher to be submitted to Play. That is
roughly five weeks out and shorter than the process below takes.

**Good news — we already comply.** Flutter's SDK defaults resolve this project
to `compileSdk 36` / `targetSdk 36` / `minSdk 24`
(`android/app/build.gradle.kts:9,22-23` delegating to `flutter.*`, resolved in
the Flutter SDK's `FlutterExtension.kt`). No migration work needed. Do **not**
pin these lower.

---

## Phase 1 — Developer account (gates everything; start first)

$25 USD one-time registration. The consequential part is the account type,
**which cannot be changed later**:

| | Personal | Organization |
|---|---|---|
| Extra prerequisite | none | D-U-N-S number (days–weeks to obtain) |
| Closed-testing gate | **12 testers × 14 continuous days** | **exempt** |
| Realistic time to live | ~4–6 weeks | ~1–3 weeks |

Identity verification (document upload, sometimes a selfie) takes hours to two
business days; the name on the ID must match the name on the payment card.

### Decided 2026-07-26: **Personal**

No D-U-N-S dependency, so nothing blocks registering immediately — but this
**accepts the 12-testers × 14-continuous-days closed-testing gate** as the long
pole of the whole Android schedule, and that gate now shapes everything below.

What that concretely commits us to:

- **Twelve real people with real Google accounts**, opted in and keeping the app
  installed for fourteen *continuous* days. The clock starts only once the
  release is approved **and** the twelfth tester has actually opted in — not
  when you add their email addresses.
- Recruiting those twelve is now a **scheduling dependency, not an
  afterthought**. Start collecting names before the build is even ready; the
  14-day clock cannot begin until they exist.
- **Emulators and fake accounts risk permanent account suspension.** The
  `netclaw_test` AVD is fine for our own verification and must never be used to
  pad the count.
- Because sideloading is how those twelve get the app in the first place,
  [`SIDELOAD.md`](SIDELOAD.md) and [`TESTER-INSTRUCTIONS.md`](TESTER-INSTRUCTIONS.md)
  are on the critical path for Play, not just a convenience.

Apple is a separate decision — the Personal choice here does **not** bind
`APP-STORE-ROADMAP.md`'s Individual-vs-Organization choice, though picking
Individual there too keeps both free of D-U-N-S.

---

## Phase 2 — Make the build shippable

This is the part that is **our work**. As of 2026-07-26 most of it is done;
what remains is two items, one of them purely an operator action.

| # | Item | Current state | File |
|---|---|---|---|
| 1 | **Final `applicationId`** | ✅ **done** — `ca.automateyournetwork.netclaw.mobile`, matching the iOS bundle ID exactly. `namespace` and the Kotlin package path agree. | `android/app/build.gradle.kts:22,33` |
| 2 | **Release signing key** | ⚠️ **half done** — the Gradle plumbing is wired (reads `android/key.properties`, falls back to the debug key with a warning if absent), but **no keystore has ever been generated**, so every build to date is debug-signed. | `android/app/build.gradle.kts:15-19,42-63` |
| 3 | **R8 / minify** | ✅ **done** — `isMinifyEnabled` and `isShrinkResources` both on, with a real hand-written keep-rules file. | `android/app/build.gradle.kts:64-69`; `android/app/proguard-rules.pro` |
| 4 | **AAB not APK** | ❌ still not produced — `flutter build appbundle` | — |
| 5 | **`INTERNET` permission** | ✅ **done** — declared explicitly in the main manifest, no longer a merge side-effect. `RECORD_AUDIO` was fixed the same way, and `<queries>` for `android.speech.RecognitionService` was added after a real tester reported the mic dead on Android 11+. | `android/app/src/main/AndroidManifest.xml` |
| 6 | **App description** | ✅ **done** — real description, no longer the Flutter template default. | `pubspec.yaml:2` |
| 7 | **Version** | `1.0.0+1` → `versionName 1.0.0`, `versionCode 1` | `pubspec.yaml:19` |

### Item 1 — settled, and now permanent

`ca.automateyournetwork.netclaw.mobile` is the final answer and is already in
the tree. **The moment an AAB with that `applicationId` is published it is fixed
for the life of the listing** — changing it later means a brand-new listing with
zero install base. Do not touch it. iOS uses the identical string as its bundle
identifier (`APP-STORE-ROADMAP.md` Phase 2 item 1), which is deliberate.

### Item 2 — the only genuinely irreversible risk left

The build machinery is ready; the keystore itself is not. Generate it:

```bash
keytool -genkey -v -keystore ~/netclaw-upload-keystore.jks \
  -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

then copy [`android/key.properties.example`](android/key.properties.example) to
`android/key.properties` and fill it in.

**Losing the upload keystore means you can never update the app again**, only
publish a fresh listing. Back it up in **two** places off this machine before
the first upload, and enroll in Play App Signing. `key.properties`, `*.jks` and
`*.keystore` are gitignored (`android/.gitignore:12-14`) — verified nothing of
the sort is tracked.

### Item 4 — build the AAB and actually run it

```bash
flutter build appbundle          # build/app/outputs/bundle/release/app-release.aab
```

A minified release build is where reflection and serialization breakage
surfaces, and R8 has only ever been exercised by `flutter build apk --release`.
Install the bundle's output on a real device (`bundletool`, or a
`--split-per-abi` release APK as a proxy) and complete a real enrollment before
trusting it.

---

## Phase 3 — Listing and compliance paperwork

One sitting, but larger than people expect:

- 512×512 icon, 1024×500 feature graphic, ≥2 screenshots per form factor
  (we have brand assets already — see `ASSETS.md`)
- Short description (80 chars), full description (4000 chars)
- **Privacy policy at a public HTTPS URL** — mandatory, no exceptions
- **Data safety form** — must match actual app behavior or it's a rejection
- Content rating questionnaire (IARC)
- Declarations: ads, target audience, government/financial/health flags

### Where NetClaw Mobile specifically will draw scrutiny

These are ours, and they are not the generic ones:

- **Camera, microphone, and biometric** permissions (spec 068) all need
  justification in the Data safety form. Biometric auth via `local_auth` is
  local-only and never leaves the device — say so explicitly.
- **Photo/video/audio capture** (068) is user-initiated and transmitted to the
  operator's own Border. That is a data *transfer*, and must be declared.
- The app is effectively a **remote-administration client for network
  infrastructure**. Expect questions about target audience — it is unambiguously
  not for children; answer the audience questions accordingly.
- **Push**: if `firebase_messaging` ships (see below), FCM token collection is
  declarable data collection even though the token is only sent to our Border.

### Decided 2026-07-26: push **ships in v1** — finish it, don't strip it

Push was dead at runtime with live dependencies: `firebase_messaging` and
`firebase_core` in `pubspec.yaml`, but no `google-services.json`, no Google
Services Gradle plugin, and `Firebase.initializeApp()` throwing into a swallowed
`catch`.

> Earlier versions of this document (and `MAC-IOS-HANDOFF.md`) also claimed
> `NotificationDeepLink` was orphaned code that nothing instantiated. **That is
> no longer true** — `lib/main.dart:310` wires it from `_tryRegisterPush()`'s
> success path. The Dart side of push is complete.

**Done 2026-07-26** (everything that does not require the operator's own
credentials):

- The Google Services Gradle plugin is declared and applied **conditionally** —
  only when `android/app/google-services.json` is present. The plugin aborts the
  build outright when that file is missing, so an unconditional apply would
  break every fresh clone. Same conditional shape already used for
  `key.properties`.
- `POST_NOTIFICATIONS` is now declared explicitly in the manifest. Android 13+
  will not show a notification without it, and it had been arriving only as a
  merge side-effect of `firebase_messaging` — the third instance of that same
  accidental-dependency bug, after `INTERNET` and `RECORD_AUDIO`.
- The swallowed `catch` is gone. Failures are classified into
  *not-configured* / *permission-denied* / *genuinely-failed*, reported through
  `FlutterError.reportError` when real, and surfaced to the user on the Settings
  tab — push previously failed invisibly, which is how it stayed broken.
- `google-services.json`, `GoogleService-Info.plist` and `firebase_options.dart`
  are gitignored.

**Remaining, and only the operator can do it:** create the Firebase project,
download `google-services.json` (Android) and `GoogleService-Info.plist` (iOS),
upload an APNs auth key to Firebase, and add the Push Notifications +
Background Modes capabilities in Xcode (see `ios/Runner/Runner.entitlements`,
deliberately not yet referenced by the build).

Consequences for this phase:

- **FCM token collection becomes declarable data collection** in the Data
  safety form — declare it, even though the token only ever goes to the
  operator's own Border and to Google's FCM service. Same on Apple's side for
  APNs.
- The Firebase project, `google-services.json`, and (for iOS) the APNs auth key
  are **operator actions requiring the maintainer's own Google and Apple
  credentials** — they cannot be produced from the repo. Config files carrying
  project identifiers must not be committed.
- Because push crosses both platforms, do it **once, consistently**, rather
  than shipping it finished on one store and half-wired on the other.

Until the Firebase project exists, the app behaves exactly as before: push
registration fails and the app works normally without it.

---

## Phase 4 — The testing gate (**applies to us** — Personal account chosen)

Closed test with **≥12 testers opted in continuously for 14 days**, then apply
for production access. Per the Phase 1 decision this is on our critical path,
and at ~2 weeks minimum it is the longest single stretch in the schedule.

Getting the app to those twelve people is a sideloading problem — see
[`SIDELOAD.md`](SIDELOAD.md) for the build-and-install path and
[`TESTER-INSTRUCTIONS.md`](TESTER-INSTRUCTIONS.md) for the handout. Each tester
also needs their own single-use enrollment token
([`MOBILE-ONBOARDING.md`](MOBILE-ONBOARDING.md)); twelve testers means twelve
tokens and twelve member rows to verify and eventually revoke.

- The 14-day clock starts only once the release is approved **and** 12 testers
  have actually opted in — not when you add their emails.
- Testers must genuinely open and use the app; dropping below 12 can reset it.
- **Emulators and fake accounts risk permanent account suspension.** Our
  `netclaw_test` AVD is fine for our own verification; it must not be used to
  pad the tester count.

Use **internal testing** (up to 100 testers, no waiting period) first to shake
out crashes, then start the closed-test clock with a build you trust.

---

## Phase 5 — Production review

Typically ≤7 days, sometimes longer; first submissions from new accounts skew
long.

---

## Suggested order of work

Both permanent decisions are now made — `applicationId`
(`ca.automateyournetwork.netclaw.mobile`) and account type (**Personal**) — so
the remaining sequence is:

1. **Register the Personal developer account now.** No D-U-N-S dependency means
   nothing gates it, and identity verification runs in the background while the
   rest proceeds. Everything downstream waits on this.
2. **Start recruiting the twelve testers immediately, in parallel.** With a
   Personal account this is the schedule's long pole, and it is the one item
   that cannot be compressed by working harder. Hand them
   [`SIDELOAD.md`](SIDELOAD.md) + [`TESTER-INSTRUCTIONS.md`](TESTER-INSTRUCTIONS.md).
3. Generate and back up the release keystore (Phase 2 item 2) — the last
   irreversible technical step.
4. Finish push — the code side is done; what's left is the Firebase project,
   `google-services.json` / `GoogleService-Info.plist`, and the APNs key.
5. Build a release AAB and smoke-test it on a real device — R8 is on and has
   never been exercised through a bundle.
6. Listing assets + compliance forms, including FCM token collection in the Data
   safety form.
7. Internal testing (100 testers, no waiting period) to shake out crashes →
   closed testing (the 12 × 14-day clock) → production.

~~Decide the final `applicationId` and account type~~ — done.
~~Enable R8, add ProGuard rules, declare `INTERNET`, fix the description~~ —
done, see the Phase 2 table.
