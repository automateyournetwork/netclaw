# Tasks: iOS Port Verification and App Store Roadmap for NetClaw Mobile

**Status as of 2026-07-26 (third implement pass)**: T001–T007, T021–T026, T028 all complete,
including **T006b — the app now builds, installs, and runs on a real, physical iPhone**
(Team `A49777FMJG`, device trusted, PID 762 confirmed stable). This is the first time
`EdgeIdentityPlugin.swift` has run anywhere a Secure Enclave actually exists. The operator has
begun live interactive testing (enrollment succeeded; ask/chat round trip in progress). Two
cross-platform (Dart-layer) bugs surfaced during that live testing and were fixed at the
operator's explicit direction, exceeding this feature's normal FR-014 boundary (documented, not
silent):
- `lib/screens/chat_screen.dart`: `_send`/`_recordVoice`/`_capturePhoto`/`_cancel` had no error
  handling at all — any RPC failure (timeout, dropped connection) was silently swallowed, looking
  like nothing happened. Now caught and shown in a red banner.
- `lib/ncfed/voice_transcription.dart`: `_defaultListenOnce()` had no `listenFor`/`pauseFor` bound
  and no error surfacing — a session with no natural end-of-speech detection could hang
  indefinitely with zero UI feedback, and a failed `initialize()` (e.g. Speech Recognition
  authorization denied — a separate OS permission from microphone access) returned `null` silently
  instead of throwing a diagnosable error. Now bounded (30s/3s), surfaces `SpeechToText.lastError`,
  and drives a "Listening…" indicator in the chat UI via a new `onListeningChange` callback.
A separate real "stall/fail" symptom during ask/chat was diagnosed as **server-side**: per
`specs/067-ncfed-mobile-command-channel/contracts/edge-ask-command-channel.md`,
`n2n/edge/ask` is spec'd to return immediately and never block the RPC — the phone's 30s call
timeout is not the bottleneck. The actual ceiling is the Border's own agent-turn timeout budget,
too short for multi-minute pyATS calls — being fixed by the operator on the Border host, out of
this spec's scope entirely (not an iOS/mobile-app issue).
Remaining work (T008–T020, T027, T029–T030) is genuinely interactive — tapping through
enrollment, scanning a QR, approving Face ID prompts — and needs the operator physically present
at the device for each step; the agent hands off UI interaction there but continues driving
builds/logs/evidence-capture around it. See
`mobile/netclaw-mobile/README.md`'s iOS section for the full verified-vs-blocked breakdown.

**2026-07-26, quality pass** (operator request, once the core loop was confirmed working end to
end on the real device): two live bugs fixed during interactive use —
1. `_capturePhoto` never read the typed text at all, so a photo could only ever be sent bare
   (no way to ask a question about it). Fixed to send whatever's typed alongside the photo.
2. `ask()` used the same 30s timeout for attachment-bearing requests as plain text — a multi-MB
   base64 photo can legitimately take longer than that just to transfer. Attachment-bearing asks
   now get 120s.
Plus a photo-thumbnail feature (`ConversationTurn.photoPath`, persisted alongside the turn, shown
inline in the chat) since there was no way to see what was actually sent.

Given the app now demonstrably works on real hardware, a full read-through of every remaining
`lib/` file surfaced and fixed five more real, previously-undiscovered bugs (all cross-platform
Dart-layer, all confirmed by direct code inspection, not just live symptoms):
- `ReconnectSupervisor`'s bare `catch (_)` treated Border revocation identically to a transient
  network blip — retried forever instead of returning to the enrollment gate. `isRevokedByBorder`
  was already used at cold-start reconnect but never in the ongoing retry loop. Fixed with a new
  generic `isPermanentFailure`/`onPermanentFailure` hook (the class still knows nothing about NCFED
  specifically) wired in `main.dart` to clear the persisted enrollment and drop back to
  `EnrollmentGate`.
- `ApprovalsScreen._resolve()`, `SettingsScreen`'s capability toggle, `DeviceScanScreen._onDetect()`
  all had the exact same missing-error-handling shape as the original chat bug — an RPC failure
  was silently swallowed with zero user-visible feedback. All now surface a visible error.
- `CapabilityRegistration.setEnabled()` mutated its local toggle state *before* confirming the
  Border accepted the change — a failed `register()` call left local/server state silently
  diverged with no rollback. Now rolls back on failure.
- `_reconcileStaleTurns()` only ever ran once, at ChatScreen's cold start — a turn that finished
  while briefly disconnected (mid-session, not a restart) stayed stuck on "Working…" until the
  next full app relaunch. Now also re-runs on every successful reconnect (`ReconnectSupervisor`'s
  `onConnected`, exposed to `ChatScreen` via a `ValueListenable<int>` tick).
(`NotificationDeepLink`, flagged as orphaned in `MAC-IOS-HANDOFF.md`, turned out to already be
wired in `main.dart` — that finding was stale, not a real gap.)

Quality-of-life additions: **Retry** on a failed turn (resends the original text + photo, read
back from the persisted `photoPath`); **timestamps** on every chat turn; **Clear conversation**
(confirmation dialog, deletes history + every saved photo file — `ConversationStore.clear()`,
new test coverage). `chat_screen.dart`'s `TextEditingController` was also never disposed — fixed
in passing.

64 tests passing (61 → 64: new `ReconnectSupervisor` permanent-failure coverage ×2, new
`ConversationStore.clear()` coverage), `flutter analyze` clean, rebuilt/reinstalled to the real
device after every change.

**2026-07-26, reconciliation with `origin/main`**: before pushing, `origin/main` had moved 7
commits ahead with an independently-built Android-side quality pass on the *same* shared Dart
files (retry, revocation handling, reconnect keepalive, turn reconciliation, clear actions, unread
badge, voice-failure reporting) — all more complete than this session's parallel versions of the
same fixes. Merged, and resolved every conflict by taking `origin/main`'s implementation as the
base (`chat_screen.dart`, `main.dart`, `reconnect_supervisor.dart`, `voice_transcription.dart`),
then re-layering only the genuinely additive iOS-session work on top: photo persistence/thumbnails
(`ConversationTurn.photoPath`, absent upstream — their retry tells the operator to retake a photo
instead), the photo-prompt fix, the attachment-timeout fix (auto-merged cleanly, no overlap), and
every fix to files `origin/main` never touched (`ApprovalsScreen`, `SettingsScreen`,
`DeviceScanScreen`, `CapabilityRegistration`, `DeviceDeepLinkListener`). Two of this session's own
duplicate/superseded pieces were dropped entirely rather than kept alongside upstream's better
version: the custom `ValueListenable`-based reconnect-tick (superseded by upstream's
`turn_reconciler.dart`, decoupled from any widget's lifecycle) and a second, redundant
"Clear conversation" button (upstream's overflow-menu already covers Chat *and* Feed, with an
in-progress-turn warning mine lacked). 98 tests passing post-merge, `flutter analyze` clean,
rebuilt and reinstalled to the real device to confirm the reconciled result still works.

**Input**: Design documents from `/specs/071-ios-mobile-port/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not requested for this feature (research D2) — Secure Enclave/Face ID cannot be
meaningfully unit-tested without a real device; verification is manual and evidence-logged
instead, per the same standard already applied to Android in specs 066–068.

**Organization**: Tasks are grouped by user story per `spec.md`. US1 and US2 are both P1 (the
enroll/ask/answer loop and the security surface it depends on); US3 is P2 (capture); US4 is P3
(App Store roadmap, a documentation-only deliverable independent of the others).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files/devices, no dependencies)
- **[Story]**: Maps to US1–US4 in spec.md
- Every task's evidence (build log, Xcode console output, screenshot, transcript) feeds the
  Verification Record table (data-model.md) consolidated into T028's README rewrite.

---

## Phase 1: Setup

**Purpose**: Get this Mac able to build and run the app at all — confirmed absent at planning
time (research D7).

- [X] T001 Install Xcode (2026-07-26, operator installed via App Store; Xcode 26.6/17F113
      confirmed via `xcodebuild -version`)
- [X] T002 Install the Flutter SDK (2026-07-26, `brew install --cask flutter`, 3.44.8). One
      environment quirk found and fixed: `~/.config` was root-owned (0700), so `flutter doctor`
      couldn't create `~/.config/flutter` — worked around with `XDG_CONFIG_HOME=~/.flutter-config`
      (exported permanently in `~/.zshrc`) rather than requiring `sudo chown` on the operator's
      home directory. Also installed CocoaPods (`brew install cocoapods`) to clear the one
      remaining `flutter doctor` warning under "Xcode - develop for iOS and macOS."
- [X] T003 [P] `cd mobile/netclaw-mobile && flutter pub get` (2026-07-26, succeeded)
- [ ] T004 [P] Open `mobile/netclaw-mobile/ios/Runner.xcworkspace` in Xcode; under Signing &
      Capabilities for the `Runner` target, select a Personal Team for automatic signing
      (research D1 — no paid Apple Developer enrollment needed for this feature). **Blocked**:
      requires the operator's own Apple ID added in Xcode's Accounts preferences — an interactive
      GUI step that can't be scripted or done on the operator's behalf.
- [ ] T005 Connect a real iPhone via cable, trust this Mac on the device, select it as the Xcode
      run destination. **Blocked**: no physical device connected in this environment.

**Checkpoint**: A real device is connected and selectable as a build target in Xcode.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nothing in any user story can be verified until the app actually compiles and runs.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T006a (partial) `flutter build ios --debug --simulator` succeeds and the app installs/launches
      cleanly on the iOS Simulator (2026-07-26) — see research D8 for the two real blockers found
      and fixed (deployment target 13.0→15.0; `EdgeIdentityPlugin.swift`/`X509SelfSigned.swift`
      wired into the Xcode project for the first time). **Not yet done**: a real-device build, which
      needs T004 (select a signing team in Xcode — requires the operator's Apple ID, an interactive
      GUI step) and T005 (a physically connected iPhone) — neither is available in this environment.
- [X] T006b Build the `Runner` scheme for a connected real device in Xcode (2026-07-26). T004
      (Team `A49777FMJG` selected in Signing & Capabilities) and T005 (real iPhone, Developer Mode
      enabled) both completed by the operator. `flutter build ios --debug -d
      00008110-0000649401F3801E` succeeded (`✓ Built build/ios/iphoneos/Runner.app`, 106.9s,
      automatic signing). Installed via `xcrun devicectl device install app` and launched via
      `xcrun devicectl device process launch` — first attempt was refused by the device
      (`invalid code signature... profile has not been explicitly trusted`), resolved by the
      operator trusting the developer profile (Settings → General → VPN & Device Management →
      Trust). Second launch succeeded: PID 762, confirmed still running (same PID) 4s later — no
      crash, no restart loop. **This is the first time `EdgeIdentityPlugin.swift`'s Secure Enclave
      code has ever executed on hardware that actually has a Secure Enclave.**
- [X] T007 [P] Run `flutter analyze` and `flutter test` in `mobile/netclaw-mobile/`; confirm both
      pass with zero regressions relative to the state before this feature (FR-014 — shared-layer
      behavior must be untouched). Result: clean analyze, 61/61 tests pass.

**Checkpoint**: The app builds and launches on the Simulator (✅ 2026-07-26). Real-device build
(T006b) still blocked on T004/T005 — Simulator-only user-story verification (manual enrollment,
UI flows) can proceed now; anything needing Secure Enclave/Face ID/a real camera still needs a
real device.

---

## Phase 3: User Story 1 - Enroll and operate the app on a real iPhone (Priority: P1) 🎯 MVP

**Goal**: Prove the core enroll → ask → answer loop works on iOS, the way it's already proven on
Android.

**Independent Test**: Install on a real iPhone, enroll against a live Border, ask a question,
confirm an answer is delivered.

- [ ] T008 [US1] Enroll a real iPhone against a live Border by scanning a Border-issued QR code;
      confirm the app generates a device identity, signs the challenge, and completes enrollment
      (spec US1 acceptance scenario 1; quickstart step 2)
- [ ] T009 [US1] On the iOS Simulator (no usable camera), enroll via "Can't scan? Enter manually"
      with the same domain/port/token; confirm it reaches the identical enrolled state as T008
      (spec US1 acceptance scenario 2; quickstart step 3)
      - **2026-07-26 (partial)**: launched on Simulator, correctly landed on "Scan Border QR Code"
        (confirms `EnrollmentGate` routing), and the real system camera-permission dialog fired
        with the exact `Info.plist` text. Dismissed without answering (app terminated) rather than
        proceeding — not yet exercised: tapping "Can't scan? Enter manually" and submitting the
        form. No CLI-only tap-injection tool was available/attempted; this needs an actual
        interactive pass (Xcode's UI, XCUITest, or a human tapping the Simulator window).
- [ ] T010 [US1] From the enrolled real device (T008), ask a question and confirm the Border's
      answer is delivered and displayed; record the end-to-end timing the way Android's 2m13s proof
      was recorded (spec US1 acceptance scenario 3; quickstart step 4)
- [ ] T011 [US1] Toggle the enrolled device's network off then on mid-session; confirm the app
      automatically redials and resumes without requiring re-enrollment (spec US1 acceptance
      scenario 4; quickstart step 5)

**Checkpoint**: User Story 1 is fully functional and independently demonstrable — this is the MVP.

---

## Phase 4: User Story 2 - Prove device-native security features actually work (Priority: P1)

**Goal**: Prove Secure Enclave keygen/signing and Face ID are real, not unverified placeholders.

**Independent Test**: On a real iPhone, trigger identity generation and confirm a real Secure
Enclave key signs a challenge; separately, trigger an approval and confirm a real Face ID prompt
gates it correctly on both success and failure.

- [ ] T012 [US2] During T008's enrollment, confirm the generated key is Secure Enclave-backed (not
      a software fallback) — inspect that `EdgeIdentityPlugin.swift`'s `generatePrivateKey()` path
      executed (e.g. via a temporary debug log or Xcode breakpoint — remove any such instrumentation
      before the build is considered done) and that the resulting certificate/signature validate
      against the Border (spec US2 acceptance scenario 1). Repeat with a second, independent
      enrollment (delete the app / reset the Simulator-or-device keychain entry and re-enroll from
      scratch) so SC-002's "100% of attempts" claim rests on more than a single trial.
- [ ] T013 [US2] Trigger a Border-issued re-authentication challenge against the already-enrolled
      device from T008; confirm the Border accepts the Secure-Enclave-signed response (spec US2
      acceptance scenario 2; quickstart step 6)
- [ ] T014 [US2] With Face ID enrolled on the real device, trigger a Border-side approval; confirm
      a genuine system Face ID prompt appears and a successful scan resolves the approval (spec US2
      acceptance scenario 3; quickstart step 7)
- [ ] T015 [US2] Trigger another approval and fail/cancel the Face ID prompt; confirm the approval
      remains unresolved — not falsely approved (spec US2 acceptance scenario 4; quickstart step 8)
- [ ] T016 [US2] Using T014's outcome, confirm research D3 empirically: if a Face ID prompt never
      appeared at all (not just failed) with the stock `FlutterAppDelegate`, apply the minimal
      required change to `mobile/netclaw-mobile/ios/Runner/AppDelegate.swift` and
      `mobile/netclaw-mobile/ios/Runner/SceneDelegate.swift` and retest T014; otherwise record that
      no change was needed (FR-008)
- [ ] T017 [US2] Edge case: on a device/OS combination with no Secure Enclave, confirm enrollment
      fails with a clear, actionable error rather than a silent software-key fallback; on a device
      with no Face ID enrolled at all, confirm the approval flow shows a clear failure/fallback
      rather than hanging (spec Edge Cases)

**Checkpoint**: User Stories 1 AND 2 both verified — the trust model that everything else depends
on is proven real, not assumed.

---

## Phase 5: User Story 3 - Use camera/mic capture on iOS (Priority: P2)

**Goal**: Prove feature 068's bidirectional capture works on iOS.

**Independent Test**: Attach a photo to an outgoing request; separately, fulfill a
Border-requested capture; confirm both round-trip correctly.

- [ ] T018 [P] [US3] With camera permission granted, attach a photo to an outgoing question;
      confirm it is captured, attached, and delivered with the request (spec US3 acceptance
      scenario 1; quickstart step 9)
- [ ] T019 [P] [US3] From the Border, request a capture from the enrolled device; confirm the
      operator is prompted and a successful capture is delivered back (spec US3 acceptance
      scenario 2; quickstart step 9)
- [ ] T020 [US3] Deny camera/microphone permission and attempt a capture in each direction; confirm
      a clear, non-crashing message in both cases (spec US3 acceptance scenario 3; quickstart
      step 10)

**Checkpoint**: User Stories 1–3 all independently verified.

---

## Phase 6: User Story 4 - Publish the app to the App Store (Priority: P3)

**Goal**: Produce a companion App Store roadmap the operator can act on later.

**Independent Test**: Read the roadmap standalone; confirm it identifies every irreversible
pre-publication decision and the current gap to "App Store ready," without needing to touch the
app.

- [X] T021 [US4] Create `mobile/netclaw-mobile/APP-STORE-ROADMAP.md` following the five-phase
      structure mapped in research D5 (Developer Program enrollment → shippable build → App Store
      Connect listing/compliance → TestFlight → App Store Review)
- [X] T022 [US4] In the roadmap, document the bundle identifier finding from research D6
      (`ca.automateyournetwork.netclaw.mobile`, already clean — unlike Android's flagged
      `applicationId` — but still flag it as permanent-once-published per FR-011)
- [X] T023 [US4] Cross-check the roadmap's Phase 2 ("make the build shippable") against this repo's
      actual current iOS build config (`mobile/netclaw-mobile/ios/Runner.xcodeproj/project.pbxproj`,
      `mobile/netclaw-mobile/pubspec.yaml`) — signing/provisioning state, `MARKETING_VERSION`/
      `CFBundleVersion`, and explicitly call out the push-notification dependency as a decision the
      operator must make before v1 — **finish it (real Firebase/APNs config) or strip the
      `firebase_messaging`/`firebase_core` dependencies** — per `PLAY-STORE-ROADMAP.md`'s equivalent
      treatment. Do not phrase this as push itself being required for v1 (FR-012, FR-013)
- [X] T024 [US4] Verify the roadmap sequences irreversible decisions (bundle ID, account type)
      before any reversible task, per SC-006, and that a reader with no prior App Store experience
      can identify the next concrete action without a follow-up question (SC-007)

**Checkpoint**: All four user stories complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Close out the manual-verification carryover, apply/skip the trivial-defect rule, and
write the honest evidence-based documentation this whole feature exists to produce.

- [X] T025 [P] Attempt `specs/066-netclaw-mobile-ncfed-edge/quickstart.md` steps 1–10 (T045) on this
      iOS device against a live Border; update `specs/066-netclaw-mobile-ncfed-edge/tasks.md:121`
      marking T045 closed with evidence, or blocked with a stated reason (FR-009)
- [X] T026 [P] Attempt the federated-peer attribution check (T017) from
      `specs/067-ncfed-mobile-command-channel/tasks.md:72`, network permitting; update that file
      marking it closed with evidence, or blocked with a stated reason (FR-009)
- [ ] T027 Reproduce the revocation-mid-session edge case on iOS (revoke the T008 device from the
      Border mid-session; confirm whether `reconnect_supervisor.dart`'s bare `catch (_)` swallows it
      here too). If a fix is genuinely a one-line/obvious change, apply it in
      `mobile/netclaw-mobile/lib/ncfed/reconnect_supervisor.dart`; otherwise leave it and document
      the reproduction (FR-015)
- [X] T028 Rewrite the iOS section of `mobile/netclaw-mobile/README.md`, stating precisely what
      was verified (citing T008–T020's outcomes) versus what remains assumed or unverified, at the
      same level of specificity as the existing Android section (FR-010, SC-005). Structure the
      evidence using the Verification Record fields defined in `data-model.md` (Capability /
      Status / Evidence / Date) so each claim traces back to a specific task's outcome.
- [ ] T029 Re-run `flutter analyze` and `flutter test` in `mobile/netclaw-mobile/` one final time to
      confirm zero regressions after T016/T027's changes (if any were made)
- [ ] T030 Walk through `specs/071-ios-mobile-port/quickstart.md` end to end as a final self-check
      that every success signal listed there is satisfied

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately. This is the one phase this
  environment cannot currently pass without new installs (research D7).
- **Foundational (Phase 2)**: Depends on Setup. BLOCKS all user stories — nothing in US1-US4's
  device-verification tasks is possible before the app builds and runs.
- **User Story 1 (Phase 3)**: Depends on Foundational only.
- **User Story 2 (Phase 4)**: Depends on Foundational; T012/T013 reuse the T008 enrollment, so in
  practice run after US1, though nothing about US2's scope requires US1 to be "done" first.
- **User Story 3 (Phase 5)**: Depends on Foundational and an enrolled device (reuses T008); no
  dependency on US2.
- **User Story 4 (Phase 6)**: Depends on nothing but Setup/Foundational being informative — it is a
  documentation task and can genuinely run in parallel with US1-US3 if staffed separately.
- **Polish (Phase 7)**: T025/T026 depend on a working enrolled device (US1). T027 depends on US1's
  enrollment. T028 depends on T008-T020's evidence existing. T029/T030 run last.

### Parallel Opportunities

- T003/T004 (Setup) can run in parallel.
- T007 (Foundational) can run alongside nothing else in its phase — it's the only other task.
- T018/T019 (US3) touch different capture directions and can be attempted in either order or
  back-to-back without blocking each other.
- T021-T024 (US4, pure documentation) can be worked on in parallel with all of Phase 3-5, since it
  depends only on already-known repo state, not on live verification outcomes.
- T025/T026 (Polish) are independent of each other.

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 (Setup) — install Xcode/Flutter, this machine currently has neither.
2. Complete Phase 2 (Foundational) — get a clean build on a real device.
3. Complete Phase 3 (US1) — the enroll/ask/answer loop. **This is the MVP**: without it nothing
   else in this feature has a device to run on.
4. Stop and confirm US1's independent test passes before continuing.

### Incremental Delivery

1. Setup + Foundational → a real device can run the app at all.
2. US1 → the core loop works (MVP demo-able).
3. US2 → the security surface behind that loop is proven real, not assumed.
4. US3 → capture parity with Android.
5. US4 → the roadmap deliverable (can run in parallel with 2-4 if staffed separately).
6. Polish → close the loop on carried-over manual tasks, the trivial-defect check, and the
   evidence-based README rewrite that is this feature's actual definition of done.
