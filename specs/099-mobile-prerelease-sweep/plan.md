# Implementation Plan: Mobile Pre-Release Hardening & Expansion Sweep

**Branch**: `099-mobile-prerelease-sweep` | **Date**: 2026-08-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/099-mobile-prerelease-sweep/spec.md`

## Summary

Eight-story pre-release sweep of the NetClaw mobile app (Flutter phone app + Swift watch app). Fixes a real defect (stuck notification badge never reconciled on launch/resume), closes App Store submission blockers not gated on the developer's pending paid Apple Developer account, wires the paid-account-gated push/signing/submission-scaffold work so it activates cleanly once that account exists, adds a CI gate for a codebase that currently has none, and adds four new experience surfaces (Dashboard as the new default landing tab, Lock Screen Live Activity, watch complication) — **except rich notification actions (Story 6), which Phase 0 research found are already fully implemented** in spec 073's `local_notifications.dart`/`approval_confirmation.dart`/`main.dart` (biometric-gated Approve/Deny notification actions routed through the same `confirmAndResolve` path as the in-app buttons). That story's tasks are re-scoped to verification and test-coverage closure, not new implementation.

## Technical Context

**Language/Version**: Dart 3.x / Flutter (SDK constraint `^3.12.2`, matching `mobile/netclaw-mobile/pubspec.yaml`); Swift 5.0 (existing `ios/Runner/*.swift`, `ios/WatchApp Watch App/*.swift`); Bash (CI workflow is declarative YAML, no new scripting language)
**Primary Dependencies**: No new Dart packages — reuses `flutter_local_notifications`, `firebase_messaging`, `firebase_core`, `local_auth`, `app_links`, `web_socket_channel`, `flutter_secure_storage` already in `pubspec.yaml`. New native-only surface: Apple's **ActivityKit** (Live Activity, Story 7) and **WidgetKit** (watchOS complication, Story 8) — both system frameworks, zero new third-party dependencies, consistent with every prior mobile spec (066-073) adding no new packages beyond what a given story strictly needs.
**Storage**: N/A — reuses existing on-device stores (`MessageFeedStore`, `ConversationStore`, `ApprovalClient` in-memory state, `flutter_secure_storage` for enrollment) for Dashboard data; no new persistence introduced.
**Testing**: `flutter_test` + `integration_test` (existing, ~25 files); XCTest (native — currently only the unmodified Xcode placeholder in `ios/RunnerTests/RunnerTests.swift`, this spec adds the first real native test)
**Target Platform**: iOS (bumping `IPHONEOS_DEPLOYMENT_TARGET` from the current 15.0 to **16.2** — the `ActivityContent`-based ActivityKit API this app uses is gated there in the current SDK, discovered mid-implementation; see research.md R2 — acceptable pre-release since there are no existing users on older iOS to strand); watchOS 10.0 (unchanged — already WidgetKit-based, sufficient for complications)
**Project Type**: Mobile app (existing `mobile/netclaw-mobile/` Flutter project with iOS native `ios/Runner/` + `ios/WatchApp Watch App/` targets) — this spec extends that single project, it does not introduce a new project
**Performance Goals**: Badge/Dashboard/complication reconciliation must complete within a few seconds of the triggering event (launch, resume, sync) — matches spec SC-001/SC-005, no new numeric target beyond what's already implied by "at a glance"
**Constraints**: No regression to existing enrollment/chat/feed/approvals/capture flows (spec FR-020); paid-account-gated work (Story 3) must not block or degrade current free/Personal-team builds (FR-007); CI must run on GitHub-hosted `macos-14` runners (needed for any Xcode build step) — noted as a real per-minute cost consideration, not a blocker
**Scale/Scope**: 8 user stories, ~4 modified Dart files (badge lifecycle), ~6 new/modified native config files (entitlements, Info.plist, privacy manifest, ExportOptions.plist), 2 new Xcode targets (Widget Extension for Live Activity, watch Complication extension), 1 new CI workflow file, 1 new top-level screen (Dashboard)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

This feature does not add an MCP server, skill, or network-device-facing integration, so the constitution's device-automation gates (I, II, III, VIII, IX) and the MCP-specific gates (V, VI, XI's catalog/install-steps/HUD touchpoints) are **not applicable** — there is no `catalog.sh` entry, `install-steps.sh` function, or Three.js HUD node for a mobile-app UI change. Applicable principles:

- **XVI (Spec-Driven Development)** — ✅ satisfied: this plan follows specify → plan → tasks → analyze → implement, spec is ratified with no open `[NEEDS CLARIFICATION]` markers.
- **XV (Backwards Compatibility)** — ✅ addressed directly by FR-020 and the "no new third-party packages" constraint above; re-verified in Phase 1 design below.
- **XIII (Credential Safety)** — ✅ no new secrets introduced; signing identity/entitlements are Xcode project configuration, not application secrets, and nothing here touches `.env`.
- **IV (Immutable Audit Trail)** — N/A as a design gate for this feature's artifacts (no device/GAIT-relevant operations performed by the mobile app itself); the development *session* producing this work still owes a GAIT summary commit per standing practice — tracked explicitly as tasks.md T042 rather than left as an unverified assumption (analyze finding C1).
- **XVII (Milestone Documentation)** — deferred to post-implementation: a WordPress blog post draft is owed once `/speckit.implement` completes, tracked as a final task, not a design gate.

No violations requiring the Complexity Tracking table below.

## Project Structure

### Documentation (this feature)

```text
specs/099-mobile-prerelease-sweep/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── notification-actions.md
│   └── mobile-ci-workflow.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
mobile/netclaw-mobile/
├── lib/
│   ├── main.dart                       # MODIFY (Story 1): add lifecycle-observer badge recompute on launch/resume
│   ├── screens/
│   │   ├── dashboard_screen.dart       # NEW (Story 5): Border health, identity, unread/pending counts
│   │   ├── settings_screen.dart        # unchanged (existing "notifications unavailable" state is correct behavior, not a bug — see research.md)
│   │   └── ...                         # existing screens (chat/feed/approvals/capture/enrollment) unchanged
│   └── ncfed/
│       ├── local_notifications.dart    # unchanged (Story 6 already implemented here — verification only)
│       ├── approval_confirmation.dart  # unchanged (Story 6 already implemented here — verification only)
│       ├── notification_deep_link.dart # MODIFY (Story 6): adds top-level handleNotificationResponse(), extracted from _HomeShellState (never touched instance state) for testability
│       ├── badge_lifecycle.dart        # NEW (Story 1): BadgeLifecycleObserver, extracted from _HomeShellState for testability (same rationale as approval_confirmation.dart)
│       ├── live_activity.dart          # NEW (Story 7): MethodChannel wrapper for LiveActivityBridge.swift
│       └── dashboard_data.dart         # NEW (Story 5): aggregates existing service state, no new backend calls
├── ios/
│   ├── Runner/
│   │   ├── Runner.entitlements         # UNCHANGED by this feature's tasks — aps-environment wiring is the one deliberately deferred step, left for the developer once the paid account exists (see tasks.md Story 3 warning)
│   │   ├── Info.plist                  # MODIFY (Story 2): missing usage strings, ITSAppUsesNonExemptEncryption
│   │   └── PrivacyInfo.xcprivacy       # NEW (Story 2)
│   ├── RunnerTests/
│   │   └── WatchRelayPluginTests.swift # NEW (Story 4): first real native test, covers WatchRelayPlugin.swift
│   ├── LiveActivityWidget/             # NEW target (Story 7): ActivityKit Live Activity + Lock Screen widget extension
│   ├── WatchApp Watch App/             # existing (spec 072) — MODIFY (Story 8): WatchDataStore.swift writes the shared count; NEW WatchApp.entitlements (App Group, research.md R11)
│   ├── WatchComplication/              # NEW target embedded in WatchApp (Story 8): WidgetKit complication + shared PendingApprovalCountStore.swift + WatchComplication.entitlements
│   ├── Runner.xcodeproj/project.pbxproj  # MODIFY: register both new extension targets, mirroring the WatchApp target's structure (research.md documents the spec-072 pitfalls to avoid: missing TargetAttributes, SUPPORTED_PLATFORMS cross-SDK mismatch)
│   └── Flutter/AppFrameworkInfo.plist  # MODIFY: MinimumOSVersion, fixes a pre-existing latent CI-blocking bug found during T040 (research.md R12) — unrelated to any of this feature's own stories
├── ExportOptions.plist                 # NEW (Story 3): distribution export config, usable once paid team exists
└── test/
    └── dashboard_screen_test.dart      # NEW (Story 5)
    └── badge_lifecycle_test.dart       # NEW (Story 1)

.github/workflows/
└── mobile-ci.yml                       # NEW (Story 4): flutter test + analyze + iOS/watch simulator build gate

scripts/
└── mobile-release-archive.sh           # NEW (Story 3): documented, repeatable archive process for once the paid account exists (Bash, matches repo's existing scripts/*.sh convention)
```

**Structure Decision**: Everything extends the existing single Flutter+iOS mobile project at `mobile/netclaw-mobile/`; no new top-level project is created. The two genuinely new pieces of Xcode project structure (a Widget Extension target for Story 7, a Complication extension embedded in the existing WatchApp for Story 8) follow the same target-addition pattern spec 072 already established for `WatchApp` itself, and Phase 0 research explicitly captures the pitfalls that surfaced during that prior addition so they aren't repeated.

## Complexity Tracking

*No constitution violations requiring justification — table intentionally omitted.*
