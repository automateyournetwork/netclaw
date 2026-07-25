# NetClaw Mobile — Google Play publication roadmap

Captured 2026-07-25 so the plan survives the session. Sequenced against **this
repo's actual build config**, not a generic checklist.

> **Provenance:** the Google policy facts below (fees, deadlines, tester rules,
> review windows) come from the operator's own research pass, not from
> verification by this repo's tooling. Re-check them against Google's own docs
> before acting — Play policy shifts year to year. Everything under "our
> current state" *was* verified directly against the files cited.

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

**Recommendation:** if a business entity is available or obtainable, the
organization route removes the single biggest schedule risk. Decide this before
paying the fee.

---

## Phase 2 — Make the build shippable

This is the part that is **our work**, and it is currently incomplete.

| # | Item | Current state | File |
|---|---|---|---|
| 1 | **Final `applicationId`** | `ca.automateyournetwork.netclaw.netclaw_mobile` — raw Flutter template default (`<org>.<project>`), carries an underscore and an ugly suffix | `android/app/build.gradle.kts:19` (+ `namespace`, line 8) |
| 2 | **Release signing key** | ❌ release signs with the **debug keystore** | `android/app/build.gradle.kts:30-32` |
| 3 | **R8 / minify** | ❌ off; no `isMinifyEnabled`, no ProGuard rules file | `android/app/build.gradle.kts:29-33` |
| 4 | **AAB not APK** | not yet produced — `./gradlew bundleRelease` | — |
| 5 | **`INTERNET` permission** | ⚠️ absent from the release manifest; arrives only as a merge side-effect of `firebase_messaging` | `android/app/src/main/AndroidManifest.xml` |
| 6 | **App description** | ❌ still `"A new Flutter project."` | `pubspec.yaml:2` |
| 7 | **Version** | `1.0.0+1` | `pubspec.yaml:19` |

### Item 1 is irreversible — decide it before the first upload

`ca.automateyournetwork.netclaw.netclaw_mobile` is what the Flutter template
generated. Once an AAB with a given `applicationId` is published, that string is
permanent for the life of the listing; changing it means a brand-new listing
with zero install base. Candidates: `ca.automateyournetwork.netclaw` or
`ca.automateyournetwork.netclaw.mobile`.

Changing it means updating `applicationId` **and** `namespace`
(`build.gradle.kts:8,19`) and the Kotlin package path under
`android/app/src/main/kotlin/`.

### Item 2 — the biggest irreversible risk overall

Losing the upload keystore means you can never update the app again, only
publish a fresh listing. Generate it, then back it up in **two** places off this
machine. `key.properties`, `*.jks` and `*.keystore` are already gitignored
(`android/.gitignore:12-14`) — verified nothing of the sort is tracked. Enroll
in Play App Signing.

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

### Decide before submitting: does push ship in v1?

Push is currently **dead code with live dependencies** — `firebase_messaging`
and `firebase_core` are in `pubspec.yaml`, but there is no
`google-services.json` and no Google Services Gradle plugin, so
`Firebase.initializeApp()` throws into a swallowed `catch`
(`lib/main.dart:272-279`). `NotificationDeepLink` is never instantiated at all.

Shipping it in this state means declaring an FCM dependency that does nothing.
Either finish it (Firebase project + config + wire the deep-link handler) or
strip the dependencies for v1. Don't ship it half-wired.

---

## Phase 4 — The testing gate (personal accounts only)

Closed test with **≥12 testers opted in continuously for 14 days**, then apply
for production access.

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

1. **Now, before anything else:** decide the final `applicationId` and the
   account type. Both are permanent.
2. Generate and back up the release keystore; wire a real signing config.
3. Enable R8, add a ProGuard rules file, declare `INTERNET` explicitly, fix the
   `pubspec.yaml` description.
4. Resolve the push question (finish or strip).
5. Build a release AAB and smoke-test it on the emulator — a minified release
   build is where reflection/serialization breakage surfaces, and we have never
   built one.
6. Register the developer account (in parallel with 2–5; if organization, start
   the D-U-N-S request *first* since it's the long pole).
7. Listing assets + compliance forms.
8. Internal testing → closed testing (if personal) → production.
