# Tasks: Mobile Pre-Release Hardening & Expansion Sweep

**Input**: Design documents from `/specs/099-mobile-prerelease-sweep/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — the spec itself requires closing real test-coverage gaps (FR-011, CI enforcement, Story 6 verification), so test tasks are in scope, not optional add-ons.

**Organization**: Tasks are grouped by user story (P1-P8 from spec.md) so each is independently implementable, testable, and shippable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Maps to spec.md's US1-US8
- All file paths are relative to the repo root

---

## Phase 1: Setup

**Purpose**: Establish a clean baseline before touching anything.

- [ ] T001 Run `flutter test` and `flutter analyze` in `mobile/netclaw-mobile/` and confirm both pass cleanly — this is the pre-change baseline every later story's changes are compared against
- [ ] T002 Record the current Xcode target list, `IPHONEOS_DEPLOYMENT_TARGET`/`WATCHOS_DEPLOYMENT_TARGET` values, and signing configuration from `mobile/netclaw-mobile/ios/Runner.xcodeproj/project.pbxproj` as a reference point, since Stories US7 and US8 both add new targets to this same file

---

## Phase 2: Foundational

**Purpose**: Cross-story blocking prerequisites.

**None identified.** Every story in this spec (US1-US8) reads existing, already-correct application state (research.md R9) and touches its own files; the only shared file multiple stories touch is `project.pbxproj` (US7, US8), and those two stories add distinct, independent targets to it — sequencing is handled by doing US7 before US8 (see Dependencies below), not by a separate foundational phase. Proceed directly to user story phases once Phase 1 is done.

---

## Phase 3: User Story 1 - Notification badge always reflects reality (Priority: P1) 🎯 MVP

**Goal**: The home-screen badge count is reconciled to the true unread/pending count on every app launch and every foreground-resume, not just reactively.

**Independent Test**: Force a stale OS badge (receive a push while fully closed), then launch or foreground-resume the app without touching any unread item — the badge must self-correct.

### Implementation for User Story 1

- [x] T004 [US1] Add a launch-time call to the existing `_recomputeBadge()` at the end of `initState`'s async initialization in `mobile/netclaw-mobile/lib/main.dart` (FR-001)
- [x] T005 [US1] Extract `BadgeLifecycleObserver` (a `WidgetsBindingObserver` calling `_recomputeBadge` on `AppLifecycleState.resumed`) into `mobile/netclaw-mobile/lib/ncfed/badge_lifecycle.dart` and wire it in `_HomeShellState` — extracted rather than implemented inline because `_HomeShellState` can't be constructed in a test (its `EdgeClient` dependency only exposes real-I/O static factories, so no existing test mounts `HomeShell`); this mirrors why `confirmAndResolve` was pulled out of `approvals_screen.dart` in 073 (FR-002, SC-001; depends on T004)

### Tests for User Story 1

- [x] T003 [P] [US1] Write `mobile/netclaw-mobile/test/badge_lifecycle_test.dart` covering: recomputes on `resumed` (FR-002), does not recompute on any other lifecycle state, recomputes again on a second resume (superseded scope — see T005's note on why this targets `BadgeLifecycleObserver` directly rather than a `main_badge_lifecycle_test.dart` mounting `HomeShell`)
- [ ] T006 [US1] Manually verify Story 1's acceptance scenarios on a real device per `specs/099-mobile-prerelease-sweep/quickstart.md` §"Story 1"

**Checkpoint**: Badge behavior is now correct and independently shippable — this is the MVP slice.

---

## Phase 4: User Story 2 - App passes automated App Store submission checks (Priority: P2)

**Goal**: Close every App Store Connect submission blocker that does NOT require a paid Apple Developer account.

**Independent Test**: Archive and run Xcode Organizer's "Validate App" — no failures for privacy manifest, usage strings, or encryption declaration.

### Implementation for User Story 2

- [x] T007 [US2] Create `mobile/netclaw-mobile/ios/Runner/PrivacyInfo.xcprivacy` declaring required-reason API categories for UserDefaults and file-timestamp APIs used transitively by `flutter_secure_storage`, `path_provider`, and the Firebase SDKs (FR-003)
- [x] T008 [US2] Register `PrivacyInfo.xcprivacy` in the Runner target's "Copy Bundle Resources" build phase in `mobile/netclaw-mobile/ios/Runner.xcodeproj/project.pbxproj` (depends on T007)
- [x] T009 [P] [US2] Checked: `capture_client.dart`/`capture_screen.dart` and the rest of `lib/` never write to the Photo Library (no `image_gallery_saver`/`photo_manager`/platform Photos API usage anywhere) — `NSPhotoLibraryUsageDescription` is confirmed **not** needed, not added (FR-004)
- [x] T010 [P] [US2] Added `NSLocalNetworkUsageDescription` to `mobile/netclaw-mobile/ios/Runner/Info.plist` for the `wss://<clawDomain>` Border connection (066/067), which routinely resolves to a local/private address; no `NSBonjourServices` added since the app has no Bonjour/mDNS service discovery of its own (confirmed by inspection) (FR-004)
- [x] T011 [P] [US2] Set `ITSAppUsesNonExemptEncryption` to `false` in `mobile/netclaw-mobile/ios/Runner/Info.plist`, having confirmed the app uses only standard TLS/HTTPS (X.509/TLS usage per specs 060/066) with no custom encryption implementation (FR-005)
- [ ] T012 [US2] Manually validate the archive via Xcode Organizer's "Validate App" per `quickstart.md` §"Story 2" (SC-002; depends on T007-T011)

**Checkpoint**: The app can be archived and passes automated submission checks that don't need the paid account, independent of US1 and US3.

---

## Phase 5: User Story 3 - Push and store submission work once the paid account is active (Priority: P3)

**Goal**: Everything needed for push + real submission is prepared and documented, without touching the signing state that currently makes free-team builds work (FR-007).

**Independent Test**: With a paid account and signing identity, code signing can be enabled and a distribution build produced by following the documented process — with no rediscovery.

### Implementation for User Story 3

- [x] T013 [US3] Add `UIBackgroundModes` (`remote-notification`) to `mobile/netclaw-mobile/ios/Runner/Info.plist` — safe to add now; inert until the push entitlement is actually signed
- [x] T014 [US3] Create `mobile/netclaw-mobile/ExportOptions.plist` (`method: app-store`) with a placeholder `teamID` and inline comments marking what must be filled in once the paid account exists
- [x] T015 [US3] Create `scripts/mobile-release-archive.sh` wrapping `xcodebuild archive` and `xcodebuild -exportArchive` against `ExportOptions.plist`, with a preflight check that fails with a clear message if `DEVELOPMENT_TEAM` in the project is still the current free/Personal team ID — verified: running it today correctly refuses with the free-team error
- [x] T016 [US3] Create `docs/MOBILE-RELEASE.md` documenting the complete once-paid-account checklist (FR-006, FR-008, SC-003)
- [x] T017 [US3] Confirmed today's free/Personal-team debug build still builds successfully after T013-T016 (`flutter build ios --simulator` succeeded post-change) (FR-007)

> **Do NOT wire `CODE_SIGN_ENTITLEMENTS` in `project.pbxproj` as part of this task list.** The entitlements file is deliberately disconnected from the build today because the free/Personal team cannot sign the Push capability; flipping this switch before the paid account exists would break today's working free-team build, directly violating FR-007. This is intentionally the one manual step left in `docs/MOBILE-RELEASE.md` for the developer to perform once the paid account is active.

**Checkpoint**: All paid-account-dependent groundwork is staged; today's build is provably unaffected.

---

## Phase 6: User Story 4 - Regressions are caught before merge (Priority: P4)

**Goal**: A CI gate runs tests, analysis, and builds on every relevant PR.

**Independent Test**: A PR that breaks a test, an analyzer rule, or either build fails the check; a clean PR passes.

### Implementation for User Story 4

- [x] T018 [US4] Create `.github/workflows/mobile-ci.yml` per `specs/099-mobile-prerelease-sweep/contracts/mobile-ci-workflow.md` — both `xcodebuild` steps verified with `CODE_SIGNING_ALLOWED=NO` from a **completely fresh DerivedData** (matching a cold CI runner exactly), which is how a real, pre-existing latent bug was caught: see the `MinimumOSVersion` fix in `ios/Flutter/AppFrameworkInfo.plist` below — without it, this CI gate would have failed on its very first real run, on the pre-099 codebase too, for reasons unrelated to any of this feature's own stories
- [x] T019 [P] [US4] Extracted `WatchRelayMessage` (pure functions, no `WCSession`/`FlutterMethodChannel` dependency) from `WatchRelayPlugin.swift`, and added `mobile/netclaw-mobile/ios/RunnerTests/WatchRelayPluginTests.swift` — 7 tests, all passing on-device via `xcodebuild test` (FR-011)
- [ ] T020 [US4] Manually verify the CI gate per `quickstart.md` §"Story 4" (SC-004) — requires opening throwaway PRs against this branch; needs developer coordination/permission before pushing anything

**Checkpoint**: CI enforcement exists and is proven to actually block bad merges, independent of every other story.

---

## Phase 7: User Story 5 - At-a-glance federation status on a Dashboard (Priority: P5)

**Goal**: A new Dashboard tab, and the app's default landing tab, surfaces Border health, identity, and unread/pending counts.

**Independent Test**: Open the app — Dashboard shows first, with accurate live data and clear disconnected/not-enrolled states.

### Implementation for User Story 5

- [x] T021 [P] [US5] Create `mobile/netclaw-mobile/lib/ncfed/dashboard_data.dart` aggregating a `UnreadPendingSnapshot` and `FederationIdentitySnapshot` purely from existing `FeedStore`/`ConversationStore`/`ApprovalClient`/`StoredEnrollment`/`_connected` state — no new network calls (FR-012)
- [x] T022 [US5] Checked: `lastSeenAt`/uptime is not tracked anywhere today; not added — no story acceptance scenario actually requires it (FR-012's "at minimum" list is satisfied without it), so no new tracking was added per research.md R9's "smallest addition" preference
- [x] T023 [US5] Create `mobile/netclaw-mobile/lib/screens/dashboard_screen.dart` rendering connection health, identity, and unread/pending counts, with explicit disconnected and not-yet-enrolled empty states (FR-012, FR-013, SC-005; depends on T021)
- [x] T024 [US5] Make Dashboard the default landing tab (index 0) in `mobile/netclaw-mobile/lib/main.dart`'s bottom navigation — required renumbering every other `_tab` index reference in the file (Chat 0→1, Feed 1→2, Approvals/Settings shift too)
- [x] T025 [P] [US5] Add `mobile/netclaw-mobile/test/dashboard_screen_test.dart` (+ `dashboard_data_test.dart`) covering healthy, disconnected, and not-yet-enrolled states plus count display — all 7 pass; full suite verified regression-free (203/203) and iOS Simulator build succeeds

**Checkpoint**: Dashboard ships as a real, data-accurate landing screen, independent of US6-US8.

---

## Phase 8: User Story 6 - Approve or deny directly from a notification (Priority: P6)

**Goal**: Verify and close test gaps on functionality Phase 0 research found is **already fully implemented** (research.md R1) — `local_notifications.dart`'s authenticated `approval` category, `main.dart`'s `_handleNotificationResponse`, and `approval_confirmation.dart`'s shared `confirmAndResolve` path.

**Independent Test**: Approve/deny directly from a notification banner; confirm Face ID gating and correct stale-approval handling, with no new code path introduced.

### Implementation for User Story 6

- [x] T026 [P] [US6] Add `mobile/netclaw-mobile/test/approval_confirmation_test.dart` — 6 tests: successful confirm+resolve, cancelled/failed auth, `authenticate()` throwing, already-resolved reply, `resolve()` throwing, watch `confirmationMethod` passthrough (FR-015, FR-016)
- [x] T027 [US6] Extracted `_handleNotificationResponse` out of `_HomeShellState` into a top-level `handleNotificationResponse` in `lib/ncfed/notification_deep_link.dart` (it never touched instance state, so this cost nothing) with an injectable `authenticate` parameter mirroring `confirmAndResolve`'s own; added `mobile/netclaw-mobile/test/notification_response_routing_test.dart` — 4 tests, including one that discriminates "correctly routed, failed auth" from "never routed" (the default-authenticate version couldn't)
- [ ] T028 [US6] Manually verify Story 6's acceptance scenarios per `quickstart.md` §"Story 6" (SC-006) — expect **no** further application-code changes; if verification finds a real defect, file it as a new task rather than silently patching around this plan

**Checkpoint**: Story 6 is verified, not rebuilt — test coverage gap closed, existing behavior confirmed correct.

---

## Phase 9: User Story 7 - Pending approval visible without unlocking the phone (Priority: P7)

**Goal**: A Live Activity shows pending-approval status on the Lock Screen without exposing sensitive content.

**Independent Test**: Trigger a pending approval, lock the phone — a Live Activity appears and clears on resolution from any surface.

### Implementation for User Story 7

- [x] T029 [US7] Bump `IPHONEOS_DEPLOYMENT_TARGET` from 15.0 to **16.2** (corrected from the originally planned 16.1 once implementation found `.end(_:dismissalPolicy:)`'s `ActivityContent`-based overload isn't available below 16.2 in the current SDK — research.md R2) across Runner AND the new LiveActivityWidget target's build configurations
- [x] T030 [US7] Added the "LiveActivityWidget" Widget Extension target to `project.pbxproj` (`com.apple.product-type.app-extension`, embedded via a new "Embed Foundation Extensions" copy-files phase) — populated `PBXProject.attributes.TargetAttributes` from the start (verified present: `74BA3BA4675CE8A523ED938C = { CreatedOnToolsVersion = 1510; }`), avoiding spec-072's exact omission (research.md R5); verified via `xcodebuild -list` showing the target/scheme and a successful isolated `xcodebuild build -scheme LiveActivityWidget`
- [x] T031 [P] [US7] Implemented `mobile/netclaw-mobile/ios/LiveActivityWidget/PendingApprovalActivityAttributes.swift` — a member of BOTH the `Runner` and `LiveActivityWidget` targets (two `PBXBuildFile` entries, one `PBXFileReference`), since ActivityKit requires the same concrete type on both sides of the app/extension boundary
- [x] T032 [P] [US7] Implemented `mobile/netclaw-mobile/ios/LiveActivityWidget/PendingApprovalLiveActivityView.swift` (Lock Screen + Dynamic Island presentations) showing only `targetName` and pending status — no sensitive approval content (FR-017)
- [x] T033 [US7] Implemented `mobile/netclaw-mobile/ios/Runner/LiveActivityBridge.swift` (registered in `AppDelegate.swift` alongside `WatchRelayPlugin`) plus `mobile/netclaw-mobile/lib/ncfed/live_activity.dart` and a `main.dart` subscription to `approvalClient.pending` — starts on the first pending approval, ends when the list empties, reacting identically regardless of whether the phone, a notification action, or the watch (via `WatchRelay`, which resolves through this SAME `ApprovalClient` instance) caused the change (FR-018, SC-007; analyze finding U1 resolved — this is the data-driven pattern the finding called for, not a `confirmAndResolve`-return trigger)
- [x] T034 [US7] Verified end-to-end via `xcodebuild build` for both the `LiveActivityWidget` and full `Runner` schemes (extension embeds correctly — confirmed `Runner.app/PlugIns/LiveActivityWidget.appex` present in the build output), `WatchApp` scheme confirmed unaffected, and `flutter test` (4 new `live_activity_test.dart` tests, 217/217 total passing) — remaining acceptance-scenario verification (an actual Lock Screen appearing on a real/simulated device) needs the developer, per `quickstart.md` §"Story 7"

**Checkpoint**: Lock Screen glanceability works end-to-end, independent of US8.

---

## Phase 10: User Story 8 - Pending approval count on the watch face (Priority: P8)

**Goal**: A watch complication shows the live pending-approval count.

**Independent Test**: Add the complication to a watch face; count updates as approvals are created/resolved.

### Implementation for User Story 8

- [x] T035 [US8] Added the "WatchComplication" WidgetKit extension target embedded in `WatchApp` (own "Embed Foundation Extensions" phase, `watchos`/`watchsimulator` `SUPPORTED_PLATFORMS` set explicitly from the start, `TargetAttributes` populated — verified: `0B6028294AE52A99799DC8CE` present) (research.md R5); also added an App Group entitlement (`group.ca.automateyournetwork.netclaw.mobile`, supported on a free/Personal team, unlike Push) shared between `WatchApp` and `WatchComplication`, needed because a widget extension runs in its own process and can't read `WatchDataStore`'s in-memory state directly — a design detail research.md hadn't anticipated, now recorded there
- [x] T036 [P] [US8] Implemented `PendingApprovalCountStore.swift` (shared, App-Group-backed, member of both `WatchApp` and `WatchComplication` targets) and the complication's `TimelineProvider`/accessory views in `mobile/netclaw-mobile/ios/WatchComplication/PendingApprovalComplication.swift` (FR-019) — reads the shared count, not `WatchDataStore` directly (impossible cross-process)
- [x] T037 [US8] `WatchDataStore.refreshApprovals()` now writes the shared count and calls `WidgetCenter.shared.reloadAllTimelines()` on every refresh (SC-007) — same trigger point that already runs after every approval push/resolve via the existing `WatchConnectivitySession` relay
- [x] T038 [US8] Verified via `xcodebuild build` for `WatchComplication` alone and the full `WatchApp` scheme (extension embeds correctly — confirmed `WatchApp.app/PlugIns/WatchComplication.appex`), plus `Runner`/`LiveActivityWidget` regression builds and `flutter test` (217/217) — an actual watch-face complication appearing and updating live needs the developer's real/simulated watch, per `quickstart.md` §"Story 8"

**Checkpoint**: All 8 user stories are independently functional.

---

## Phase 11: Polish & Cross-Cutting Concerns

- [x] T039 [P] Updated `mobile/netclaw-mobile/README.md`'s screen/tab list and `main.dart` comment to include Dashboard as the default landing tab
- [x] T040 Ran the full local verification sweep from a **completely fresh DerivedData** (`rm -rf DerivedData/Runner-*`, matching a cold CI runner) — `flutter analyze` (clean), `flutter test` (217/217), `xcodebuild` for `Runner` (iOS Simulator) and `WatchApp` (watchOS Simulator) both `BUILD SUCCEEDED`, confirming all 8 stories coexist with zero regression to enrollment/chat/feed/approvals/capture (FR-020). This sweep caught a real pre-existing bug unrelated to any of this feature's 8 stories: Flutter's generated `FlutterGeneratedPluginSwiftPackage/Package.swift` hardcoded an iOS 13.0 platform floor (Xcode's SPM resolver only enforces this on a fully fresh package-graph resolution — a persisted DerivedData/SPM cache, which every build earlier in this implementation had, masks it entirely), conflicting with `firebase_core`/`firebase_messaging`'s real minimum of iOS 15 — reproduced identically on the pre-099 baseline via `git stash`, confirming it predates this feature. Fixed by adding `MinimumOSVersion` to `mobile/netclaw-mobile/ios/Flutter/AppFrameworkInfo.plist` (the standard, documented Flutter mechanism for this), which was necessary for T018's CI gate to actually pass on a real (always-cold) CI runner — without it, `mobile-ci.yml` would have failed on its first real run for reasons having nothing to do with this feature's own stories.
- [x] T041 Drafted `docs/blog/2026-08-06-mobile-prerelease-sweep.md` per constitution Principle XVII — presented to the developer for review, not published
- [x] T042 GAIT summary commit per constitution Principle IV (analyze finding C1) — committed as `aae0c7a` on `099-mobile-prerelease-sweep` after explicit developer go-ahead

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies, run first
- **Foundational (Phase 2)**: Empty — see note above
- **User Stories (Phases 3-10)**: All depend only on Phase 1. US1-US6 touch entirely disjoint files and can proceed in any order or in parallel. **US7 and US8 both edit `project.pbxproj` and should be sequenced one after the other (US7 before US8, matching priority order) rather than run concurrently**, to avoid two people/agents editing the same project file at once.
- **Polish (Phase 11)**: Depends on however many of US1-US8 are in scope for a given delivery slice

### Within Each User Story

- Tests before implementation where a test task is listed
- US7/US8: target-registration task before the Swift files that live in that target
- Story complete before its checkpoint is declared

### Parallel Opportunities

- T003 (US1 tests) can run while T007-T012 (US2) proceed — different files
- Once US1-US6 foundations exist, T021/T025 (US5), T026 (US6), T031/T032 (US7), T036 (US8) are each independently parallelizable within their own story
- US1, US2, US3, US4, US5, US6 have zero file overlap and can be fully parallelized across multiple contributors/agents; only US7→US8 needs sequencing

---

## Implementation Strategy

### MVP First

1. Phase 1 (Setup)
2. Phase 3 (US1 — badge fix)
3. **STOP and VALIDATE**: quickstart.md Story 1
4. This alone is a shippable, real bug fix

### Incremental Delivery

Setup → US1 (MVP) → US2 → US3 → US4 → US5 → US6 (verification) → US7 → US8 → Polish, validating each story's checkpoint before moving on. Given zero cross-story file overlap outside US7/US8, stories can also be delivered out of this order or in parallel if multiple contributors are available.
