# NetClaw Mobile — Apple App Store publication roadmap

Companion to [`PLAY-STORE-ROADMAP.md`](PLAY-STORE-ROADMAP.md), same structure, mapped to Apple's
process (spec `071-ios-mobile-port`, research decision D5). Written from the repo's actual current
iOS build config as of 2026-07-25 — re-check before acting, since Apple policy and this repo's own
config both shift over time.

> **Provenance**: Apple's own account/review-timeline facts below are the maintainer's general
> knowledge of the App Store process, not independently re-verified against Apple's current
> developer documentation for this session — re-check against `developer.apple.com` before acting,
> the same caveat `PLAY-STORE-ROADMAP.md` applies to its Google Play facts. Everything under "our
> current state" *was* verified directly against the files cited.

---

## Phase 1 — Apple Developer Program enrollment (gates everything; start first)

$99 USD/year, renews annually (unlike Play's $25 one-time fee). The consequential part is the same
choice Android's roadmap flags — **account type, which shapes the rest of the timeline**:

| | Individual | Organization |
|---|---|---|
| Extra prerequisite | none | D-U-N-S number (days–weeks to obtain, same requirement as Play) |
| External TestFlight review | Required (Apple reviews the build once before external testers can install it — typically 24–48h, much lighter than Play's 12-tester/14-day closed-testing gate) | Same requirement |
| Realistic time to live | ~1–2 weeks | ~2–4 weeks (D-U-N-S is the long pole, same as Android) |

Identity verification is generally faster than Google Play's for Individual accounts, but
Organization accounts carry the same D-U-N-S bottleneck Android's roadmap already flags — if an
Organization Play listing is planned, this can and should be requested once for both stores.

**Recommendation**: same as Android — if a business entity is available, decide the account type
before paying either platform's fee, since both gate on the same D-U-N-S dependency.

> **Still open as of 2026-07-26.** Google Play's account type was decided (**Personal** — see
> `PLAY-STORE-ROADMAP.md` Phase 1), but that choice does **not** bind Apple's. Picking Individual
> here too keeps both stores free of the D-U-N-S bottleneck. The asymmetry worth knowing: on Play,
> Personal costs you the 12-tester × 14-continuous-day gate, whereas on Apple, Individual costs you
> nothing extra — TestFlight's external-tester Beta App Review applies to Individual and
> Organization alike. **There is no testing-gate penalty for choosing Individual on Apple.**

Development/testing on a real device (everything `specs/071-ios-mobile-port/tasks.md`'s Setup and
Foundational phases need) does **not** require this enrollment — Xcode's free "Personal Team"
automatic signing is sufficient for on-device debugging (research D1). Enrollment is only required
starting at TestFlight external testing / App Store submission.

---

## Phase 2 — Make the build shippable

| # | Item | Current state | File |
|---|---|---|---|
| 1 | **Final bundle identifier** | `ca.automateyournetwork.netclaw.mobile` — already clean, no template artifacts | `ios/Runner.xcodeproj/project.pbxproj:385` |
| 2 | **Code signing** | ✅ **updated 2026-07-26** — `CODE_SIGN_STYLE = Automatic` and `DEVELOPMENT_TEAM = A49777FMJG` is now committed, which is what let the app build to a real iPhone. **This being in git is a hazard for anyone else cloning the repo** — their build cannot sign until they replace it with their own team. Called out in [`SIDELOAD.md`](SIDELOAD.md). | `ios/Runner.xcodeproj/project.pbxproj:387,567,590` |
| 3 | **Distribution certificate + provisioning profile** | ❌ Not yet created — required only once Phase 1 enrollment is complete and a distribution (not debug) build is needed | Created in Xcode/App Store Connect, not stored in this repo |
| 4 | **Archive/IPA, not a debug build** | ❌ Not yet produced — `flutter build ipa` (requires Phase 1 signing) | — |
| 5 | **`NSCameraUsageDescription`/`NSMicrophoneUsageDescription`/`NSFaceIDUsageDescription`/`NSSpeechRecognitionUsageDescription`** | ✅ Already present and worded appropriately | `ios/Runner/Info.plist` |
| 6 | **App description** | Set via `pubspec.yaml`'s `description` field — real (not the Flutter template default, unlike the same field's history on Android) | `pubspec.yaml:2` |
| 7 | **Version** | `1.0.0+1` → `CFBundleShortVersionString=1.0.0`, `CFBundleVersion=1` (shared with Android via the same `pubspec.yaml`) | `pubspec.yaml:19` |
| 8 | **Push notifications (`firebase_messaging`/`firebase_core`)** | 🔨 **Decided 2026-07-26: finish it, don't strip it.** Needs a real Firebase project, `GoogleService-Info.plist`, an **APNs auth key** uploaded to Firebase, and the **Push Notifications + Background Modes** capabilities in Xcode. APNs token collection then becomes declarable data collection in the App Privacy questionnaire. Note the free Personal Team **cannot** do push — this route requires the paid program. | `pubspec.yaml:40,46`; `lib/main.dart` |

### Item 1 — already decided, unlike Android's original state

Android's `applicationId` started as the raw Flutter template default
(`ca.automateyournetwork.netclaw.netclaw_mobile`) per `PLAY-STORE-ROADMAP.md`'s Phase 2 — that
decision has since been made in this repo (`android/app/build.gradle.kts:33`, now
`ca.automateyournetwork.netclaw.mobile`, matching iOS's bundle ID exactly). ~~`PLAY-STORE-ROADMAP.md`
itself has not been updated to reflect this~~ — **fixed 2026-07-26**; that document's Phase 2 table
now reflects reality (three further stale rows were corrected at the same time). For iOS
specifically: the bundle ID is already clean and
already matches Android's, so there is no open decision here — only the standard warning that,
like Android's `applicationId`, **it becomes permanent the moment the first build is submitted to
App Store Connect.**

### Item 2/3 — the biggest irreversible risk overall (same shape as Android's keystore risk)

Losing the distribution certificate's private key or the provisioning profile is recoverable
(Apple lets you revoke and regenerate certificates, unlike losing an Android upload keystore
outright) but **do** enroll in App Store Connect's automatic Xcode-managed signing to avoid manual
certificate/profile juggling, and keep the associated Apple ID's credentials backed up the same way
Android's `key.properties`/`*.jks` are (never committed — this repo's `.gitignore` conventions
already cover `ios/Podfile.lock`-adjacent secrets patterns; no signing material should ever land in
git for either platform).

---

## Phase 3 — Listing and compliance paperwork

Similar shape to Play's Phase 3, same underlying facts about this app's own surface area:

- 1024×1024 App Store icon (no alpha channel — Apple rejects icons with transparency, a stricter
  rule than Play's), plus screenshots per required device size class (we have brand assets
  already — see `ASSETS.md`)
- Promotional text (170 chars), description (4000 chars, same limit as Play)
- **Privacy policy at a public HTTPS URL** — mandatory, same as Play
- **App Privacy "nutrition label" questionnaire** (App Store Connect's equivalent of Play's Data
  Safety form) — must match actual app behavior or risks rejection, identical stakes to Play
- Age rating questionnaire (Apple's own format, not IARC, but asks the same substantive questions)
- Export compliance declaration (Apple-specific — this app's use of Secure Enclave/TLS crypto is
  typically exempt under the standard encryption exemption, but the questionnaire must still be
  answered on first submission)

### Where NetClaw Mobile specifically will draw scrutiny (same substance as the Play roadmap)

- **Camera, microphone, and biometric (Face ID)** permissions all need justification in the App
  Privacy questionnaire. Face ID auth via `local_auth` is local-only and never leaves the device —
  say so explicitly, exactly as planned for Play's Data Safety form.
- **Photo/video/audio capture** is user-initiated and transmitted to the operator's own Border —
  a data *transfer*, must be declared, same as Android.
- Same "remote-administration client for network infrastructure" framing applies to the age-rating
  and target-audience questions.
- **Push**: if `firebase_messaging` ships, APNs token collection is declarable data collection,
  same as FCM on Android.

---

## Phase 4 — TestFlight (materially lighter than Play's testing gate)

- **Internal testing**: up to 100 testers (App Store Connect users on the team), available
  immediately after a build is uploaded and passes automated processing — no external review
  needed, comparable to Play's internal testing track.
- **External testing**: up to 10,000 testers, but the **first build requires a Beta App Review**
  (typically 24–48h, sometimes longer for first-time submitters) — there is no Play-style
  "12 testers × 14 continuous days" clock at all. This is the single biggest schedule advantage
  iOS has over Android's Personal-account path.
- Builds expire after 90 days on TestFlight — re-upload periodically during an extended beta.

---

## Phase 5 — App Store Review

Typically faster than Google Play's for an established category (often 24–48h, sometimes longer),
but — same caveat as the Play roadmap — first submissions from new accounts and apps in sensitive
categories (network/remote-administration tooling, biometric use) commonly see longer and more
scrutinized review cycles. Budget for at least one rejection-and-resubmission cycle on a first
submission, the same prudent assumption Android's roadmap implicitly makes.

---

## Suggested order of work

1. **Now, before anything else**: decide the Apple Developer Program account type (Individual vs
   Organization) — ideally the same decision made for Play, since both gate on D-U-N-S if
   Organization is chosen. The bundle identifier itself needs no new decision (already clean,
   already shared with Android).
2. Get the iOS build actually compiling and verified on a real device first
   (`specs/071-ios-mobile-port/tasks.md` Phases 1–5) — App Store readiness is moot until the app
   works at all on iOS.
3. Select a real signing team in Xcode; once Phase 1 enrollment completes, generate the
   distribution certificate + provisioning profile via Xcode-managed (automatic) signing.
4. Resolve the push question (finish or strip) — do this once, consistently, for both platforms'
   roadmaps rather than shipping it half-wired on either.
5. Produce a release archive (`flutter build ipa`) and smoke-test it via TestFlight internal
   testing before spending a Beta App Review cycle on external testers.
6. Register the Apple Developer Program account (in parallel with 2–4; if Organization, start the
   D-U-N-S request first, exactly as Android's roadmap recommends).
7. Listing assets + App Privacy / compliance forms.
8. Internal TestFlight → external TestFlight (Beta App Review) → App Store submission (Phase 5
   review).
