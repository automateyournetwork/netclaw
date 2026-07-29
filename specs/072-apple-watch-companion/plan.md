# Implementation Plan: Apple Watch Companion App for NetClaw Mobile

**Branch**: `072-apple-watch-companion` | **Date**: 2026-07-27 | **Spec**: `specs/072-apple-watch-companion/spec.md`
**Input**: Feature specification from `/specs/072-apple-watch-companion/spec.md`

## Summary

Adds a native watchOS app (Flutter has no watchOS target at all) to the existing
`mobile/netclaw-mobile/ios/` Xcode project, alongside the Flutter `Runner` app. The watch has no
identity, enrollment, or network connection of its own — every capability (Approvals, Feed, Quick
Voice Ask) is relayed live through the already-enrolled iPhone app via WatchConnectivity's
`sendMessage`, which a new native `WatchRelayPlugin` forwards into the existing Flutter engine
through a method channel, answered by the same `ApprovalClient`/`EdgeAskClient`/`MessageFeedStore`
instances `HomeShell` already builds. No new Border-facing wire method except one small, additive
field (D4) so a watch-resolved approval is truthfully attributed, never mislabeled as biometric.

## Technical Context

**Language/Version**: Swift 5.0 (new watch app target + new `WatchRelayPlugin.swift` on the phone
side, matching `ios/Runner`'s existing `SWIFT_VERSION`); Dart 3.x (new `lib/ncfed/watch_relay.dart`
in the existing Flutter app, no version change)
**Primary Dependencies**: `WatchConnectivity` (Apple system framework, phone + watch sides — no new
external package); `LocalAuthentication` (already used by the phone's `approvals_screen.dart`, now
also used watch-side for D3's passcode confirmation); SwiftUI + WatchKit (the watch app's UI, a new
target, no third-party UI library). No new Flutter pub packages — `watch_relay.dart` is pure Dart
wiring against already-imported classes.
**Storage**: N/A on the watch — it holds no persistent state of its own; every view (Approvals,
Feed, Ask) is a live snapshot fetched from the phone on demand, matching D2's request/reply-only
transport decision (no watch-side database, no watch-side conversation/feed store).
**Testing**: `flutter analyze` / `flutter test` for the new `watch_relay.dart` module (mockable
`EdgeRpcSource`-style injection, matching every existing Dart test in this app); Xcode's `xcodebuild
test` / manual verification for the native watch app and `WatchRelayPlugin` (WatchConnectivity has
no meaningful headless/CI-testable surface — the same manual-verification standard specs 066–071
already established for anything requiring real Secure Enclave/biometric/hardware behavior applies
here to real WatchConnectivity message delivery and the passcode prompt).
**Target Platform**: watchOS 26.5 SDK (already installed) targeting a `WKApplication`
(watchOS 10+ single-target app, no separate WatchKit Extension needed on this Xcode/SDK version);
verified first on the watchOS Simulator (5 already installed: SE 3, Series 11, Ultra 3), with a
real physical paired watch attempted opportunistically per research D6.
**Project Type**: Extends the existing `mobile/netclaw-mobile/` Flutter + native-iOS project — no
new top-level project. Adds one new native Xcode target (the watch app) plus one new Swift file on
the existing `Runner` target (`WatchRelayPlugin.swift`) plus one new Dart file in the existing
Flutter `lib/` tree.
**Performance Goals**: None new beyond the existing phone-to-Border latency this feature inherits
by relaying through the same `EdgeAskClient`/`ApprovalClient` calls already in production; SC-001's
"under 15 seconds" bound is a UX/interaction-count target (open app → view → confirm → resolved),
not a new backend throughput requirement.
**Constraints**: FR-011 — the watch MUST NOT gain any independent identity, enrollment, or network
path to the Border, ever, even as an optimization; FR-003 — the passcode confirmation MUST be
re-checked on every single approve/deny action, never cached or skipped for an already-unlocked
watch; D2 — only `sendMessage`'s live request/reply is used for these three capabilities (no
background/queued delivery), so "not connected" is always a direct, immediate signal.
**Scale/Scope**: 3 user stories; 1 new native Xcode target (watch app); 1 new native Swift relay
plugin; 1 new Dart relay module; 1 additive (backward-compatible) field on the existing
`n2n/edge/approval_resolve` call rather than a new wire method; zero new Border-side wire methods.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| IV. Immutable Audit Trail | The one new field (D4) makes a watch-resolved approval's audit record MORE accurate (distinguishes passcode from biometric), not less — no reduction in what's recorded | PASS |
| V. MCP-Native Integration | No new MCP server or tool; mobile-client-only feature exactly like spec 071 | PASS (N/A) |
| VI. Multi-Vendor Neutrality | N/A — mobile client, not a vendor integration | PASS (N/A) |
| IX. Security by Default | FR-003/FR-004 (research D3/D4): every watch approval requires a fresh, explicit, non-cached passcode confirmation, and its record is never mislabeled as biometric — the security bar for watch approvals is documented and no weaker than what it explicitly claims to be | PASS |
| XI. Full-Stack Artifact Coherence | Not a new capability in the MCP-server/skill sense (no catalog/install-steps/HUD entries apply, exactly as spec 071 established) — `README.md`'s mobile section update is the one artifact touchpoint in scope | PASS (scoped) |
| XII. Documentation-as-Code | README update lands in the same PR as the implementation, not a follow-up | PASS |
| XIII. Credential Safety | No new credentials; watch app signing reuses the same Xcode team/signing already configured for `Runner` in spec 071 | PASS |
| XV. Backwards Compatibility | The one new field on `n2n/edge/approval_resolve` is additive (a Border/CLI that ignores it sees identical behavior to today); Android and the existing iPhone approval flow are untouched | PASS |
| XVI. Spec-Driven Development | Follows `/speckit.specify` → `/speckit.clarify` → `/speckit.plan` | PASS |
| XVII. Milestone Documentation | Deferred to post-`/speckit.implement`, per the standard SDD lifecycle | N/A (later) |

No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/072-apple-watch-companion/
├── plan.md              # This file
├── research.md          # Phase 0 output (6 decisions: D1-D6)
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── watch-relay.md    # Phase 1 output — phone<->watch message shapes + the one additive Border field
└── tasks.md              # Phase 2 output (/speckit.tasks command — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
mobile/netclaw-mobile/
├── ios/
│   ├── Runner/
│   │   └── WatchRelayPlugin.swift       # NEW — WCSessionDelegate on the phone; forwards to Dart
│   │                                     #  via FlutterMethodChannel, registered in AppDelegate.swift
│   │                                     #  alongside the existing EdgeIdentityPlugin registration
│   └── WatchApp/                         # NEW native watchOS app target (SwiftUI)
│       ├── WatchApp.swift                # @main WKApplication entry point
│       ├── WatchConnectivitySession.swift # WCSessionDelegate on the watch side; sendMessage() calls
│       ├── ApprovalsView.swift           # US1 — list + approve/deny + LAContext passcode confirm (D3)
│       ├── FeedView.swift                # US2 — read-only scrollable message list
│       ├── AskView.swift                 # US3 — dictation TextField + waiting/answered/failed states
│       └── ConnectionState.swift         # Shared "connected / phone unreachable / not enrolled" enum
│                                          #  surfaced consistently across all three views (FR-012)
├── lib/
│   ├── main.dart                         # HomeShell wires WatchRelay alongside existing clients
│   └── ncfed/
│       └── watch_relay.dart              # NEW — registers the method-channel handler answering
│                                          #  watch requests using the existing ApprovalClient/
│                                          #  EdgeAskClient/MessageFeedStore instances (research D1)
└── test/
    └── watch_relay_test.dart             # NEW — Dart-side relay logic, mocked channel calls

mcp-servers/protocol-mcp/bgp/federation/
└── service.py                            # _edge_on_approval_resolve (line ~1288): reads a new
                                           #  optional confirmation_method field instead of
                                           #  hardcoding via="biometric" (research D4) — additive,
                                           #  defaults to "biometric" when absent so the existing
                                           #  phone flow's wire behavior is unchanged
```

**Structure Decision**: Extends the existing `mobile/netclaw-mobile/` project with one new native
Xcode target (`WatchApp`) and minimal additions to the existing `Runner` target and Flutter `lib/`
tree — no new top-level project, matching how spec 071 scoped its own iOS-only native work.

## Complexity Tracking

*No entries — Constitution Check has no violations to justify.*
