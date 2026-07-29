# Implementation Plan: iOS Port Verification and App Store Roadmap for NetClaw Mobile

**Branch**: `071-ios-mobile-port` | **Date**: 2026-07-25 | **Spec**: `specs/071-ios-mobile-port/spec.md`
**Input**: Feature specification from `/specs/071-ios-mobile-port/spec.md`

## Summary

Verify, on a real Mac + real iPhone, the iOS-native code that specs 066/067/068 already wrote but
could never build or run (no Mac was available at the time): `EdgeIdentityPlugin.swift` (Secure
Enclave keygen/sign) and `X509SelfSigned.swift` (hand-built self-signed cert). The shared Dart/UI
layer is done and out of scope — this feature is a verification + narrow native-fix pass, not new
product development. It closes with an honest README update (mirroring the existing Android
section's evidence-based style) and a new `APP-STORE-ROADMAP.md` structurally mirroring the
existing `PLAY-STORE-ROADMAP.md`.

## Technical Context

**Language/Version**: Swift 5.0 (existing `ios/Runner/*.swift`, `SWIFT_VERSION = 5.0` in
`project.pbxproj`); Dart 3.x / Flutter (SDK `^3.12.2`, unchanged — no shared-layer edits per FR-014)
**Primary Dependencies**: None new. Reuses what's already in `pubspec.yaml`: `local_auth ^3.0.2`
(Face ID), `camera ^0.12.0+2` (capture), `mobile_scanner ^7.4.0` (QR enrollment). Native side uses
only Apple system frameworks already imported (`Security`, `Foundation`) — no third-party iOS pods
introduced.
**Storage**: N/A — Secure Enclave key storage is managed entirely by the Keychain/Secure Enclave
APIs already called in `EdgeIdentityPlugin.swift` (`kSecClassKey` + `kSecAttrTokenIDSecureEnclave`);
nothing for this feature to add.
**Testing**: `flutter analyze` / `flutter test` (platform-agnostic, already passing per the Android
pass); Xcode's `RunnerTests` XCTest target (currently a stub — left as-is, see research D2); manual
on-device verification for everything Secure Enclave/Face ID/camera-related, since none of that is
exercisable in a unit test or on the Simulator.
**Target Platform**: iOS 13.0+ (existing `IPHONEOS_DEPLOYMENT_TARGET`), verified on iOS Simulator
(build sanity, UI, manual-enrollment fallback) and a real, physical iPhone (Secure Enclave, Face
ID, camera/mic — confirmed available per Clarifications).
**Project Type**: Mobile app — extends the existing `mobile/netclaw-mobile/` Flutter project's `ios/`
target. No new top-level project, no new Xcode target beyond what already exists (`Runner`,
`RunnerTests`).
**Performance Goals**: None new. SC-001's "single sitting" round trip is qualitative — the
quantitative bar already exists from the Android pass (2026-07-25: enroll → ask → answer in
2m13s) and this feature does not need to beat or formally re-benchmark it, only demonstrate the
same shape of success on iOS.
**Constraints**: FR-014 — no changes to the shared Dart layer's behavior; the Secure Enclave
private key MUST NEVER be exportable (already true — `EdgeIdentityPlugin.swift` exposes only
`ensureKeyPair` returning a cert and `sign`, never raw key bytes — this plan must not add an export
path); FR-013 — push notifications (APNs/Firebase) untouched; FR-015 — defect fixes limited to
one-line/obvious changes, anything larger documented and deferred.
**Scale/Scope**: One platform (iOS), two native Swift files to get compiling and verified, zero new
wire methods (the protocol is already fully specified by 066/067/068 and proven on Android), one
new roadmap document, one README section rewrite.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| IV. Immutable Audit Trail | No change to any GAIT-audited path (enrollment/delegation/audit logic lives server-side in `bgp/federation/*`, untouched by this feature) | PASS (N/A) |
| V. MCP-Native Integration | No new MCP server or tool; this is a mobile-client-only verification feature | PASS (N/A) |
| VI. Multi-Vendor Neutrality | N/A — mobile client, not a vendor integration | PASS (N/A) |
| IX. Security by Default | Verifies (does not weaken) the existing no-export Secure Enclave design (FR-002/FR-003); any native code change must preserve "private key never leaves the plugin" | PASS — re-verify at Phase 1 |
| XI. Full-Stack Artifact Coherence | Not a new capability (MCP server/skill/integration) — the checklist's catalog/install-steps/HUD/SKILL.md items do not apply. Only `mobile/netclaw-mobile/README.md` (FR-010) is in scope, which this plan's tasks cover | PASS (scoped) |
| XII. Documentation-as-Code | README update (FR-010) and the new roadmap doc (FR-011) land in the same PR as the verification work, not a follow-up | PASS |
| XIII. Credential Safety | No new credentials. Any signing certificate/provisioning profile used for real-device builds stays local to Xcode's keychain/developer account, never committed (mirrors the existing `*.jks`/`key.properties` `.gitignore` pattern on Android) | PASS |
| XV. Backwards Compatibility | No wire-protocol or shared-layer changes (FR-014); Android is unaffected | PASS |
| XVI. Spec-Driven Development | This plan follows `/speckit.specify` → `/speckit.clarify` → `/speckit.plan` | PASS |
| XVII. Milestone Documentation | Deferred to post-`/speckit.implement`, per the standard SDD lifecycle — noted here, not a Phase 0/1 gate | N/A (later) |

No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/071-ios-mobile-port/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output (lightweight — see rationale in the file itself)
├── quickstart.md         # Phase 1 output — the actual Xcode/device verification walkthrough
└── tasks.md              # Phase 2 output (/speckit.tasks command — NOT created by /speckit.plan)
```

No `contracts/` directory: this feature introduces zero new wire methods, message shapes, or
external interfaces. The enrollment/challenge/capture/approval contracts it verifies against are
already fully specified in `specs/066-netclaw-mobile-ncfed-edge/contracts/`,
`specs/067-ncfed-mobile-command-channel/contracts/`, and
`specs/068-ncfed-mobile-biometrics-capture/contracts/edge-biometrics-and-capture.md` — this feature
does not change or extend them.

### Source Code (repository root)

```text
mobile/netclaw-mobile/
├── ios/Runner/
│   ├── EdgeIdentityPlugin.swift   # get compiling + verified on real device (FR-001/002/003)
│   ├── X509SelfSigned.swift        # get compiling + verified on real device (FR-001/002/003)
│   ├── AppDelegate.swift           # confirm no FlutterFragmentActivity-equivalent change needed (FR-008)
│   └── Info.plist                  # already declares NSFaceIDUsageDescription/camera/mic keys — no change expected
├── README.md                       # iOS section rewritten with verified-vs-assumed evidence (FR-010)
├── APP-STORE-ROADMAP.md            # NEW — companion to PLAY-STORE-ROADMAP.md (FR-011/012)
└── PLAY-STORE-ROADMAP.md           # read-only reference for structural parity, not modified

specs/066-netclaw-mobile-ncfed-edge/tasks.md   # mark T045 closed/blocked (FR-009)
specs/067-ncfed-mobile-command-channel/tasks.md # mark T017 closed/blocked (FR-009)
```

**Structure Decision**: Extends the existing `mobile/netclaw-mobile/` Flutter project's iOS target
only. No new top-level project, no new Xcode target, no changes outside `ios/Runner/` and the
mobile app's top-level docs. This mirrors how 066/067/068 scoped their Android-side native work to
`android/app/src/main/kotlin/.../MainActivity.kt` plus docs.

## Complexity Tracking

*No entries — Constitution Check has no violations to justify.*
