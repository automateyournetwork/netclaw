# Research: Apple Watch Companion App for NetClaw Mobile

## D1: How a native watch app talks to Flutter's Dart-side Border logic

**Decision**: A new native Swift `WatchRelayPlugin` (WatchConnectivity's `WCSessionDelegate`) on the
iOS side receives requests from the watch and calls **into** the existing Flutter engine via a
`FlutterMethodChannel` (the same primitive `EdgeIdentityPlugin` already uses, just invoked in the
opposite direction — native calling Dart, not Dart calling native, which `FlutterMethodChannel`
supports symmetrically). A new, small Dart module (`lib/ncfed/watch_relay.dart`) registers a
handler on that channel and answers using the SAME already-constructed `ApprovalClient`,
`EdgeAskClient`, and `MessageFeedStore` instances `HomeShell` already builds — no second Border
connection, no duplicate identity, nothing new on the wire between the phone and the Border at all.

**Rationale**: `EdgeClient`, `ApprovalClient`, `EdgeAskClient`, and `MessageFeedStore` are Dart
classes with no Swift equivalent, and the spec's own constraint (relay-through-phone, FR-011) rules
out giving the watch (or any new Swift code) its own connection. The only two ways to reach that
existing Dart-side state from watch-originated Swift code are (a) call into the Flutter engine via
a method channel, or (b) reimplement the relevant slice of `ApprovalClient`/`EdgeAskClient` natively
in Swift and have it maintain a second WebSocket to the Border — which is exactly the standalone
architecture the operator already rejected. (a) is a few dozen lines of channel plumbing reusing
four already-built, already-tested Dart classes; (b) would duplicate real protocol logic for no
benefit.

**Alternatives considered**: A native Swift NCFED client reachable from the watch relay without
going through Dart — rejected, this is the standalone-identity architecture already rejected in
favor of relay-through-phone.

## D2: Message transport between watch and phone (WatchConnectivity API choice)

**Decision**: Use `WCSession.sendMessage(_:replyHandler:errorHandler:)` for all three capabilities
(Approvals list fetch + resolve, Feed fetch, Ask submit + poll) — a live, one-shot request/reply
call that requires both devices reachable *right now*, which is exactly what FR-012's "explicit
not-connected state" requirement wants: if `sendMessage` fails (phone unreachable, app not running
to receive it), that failure is the not-connected signal, mapped directly to a UI state.
`updateApplicationContext`/`transferUserInfo` (WatchConnectivity's background-tolerant, queued
delivery APIs) are NOT used for this feature's request/response actions — they exist for
best-effort background sync, which would blur exactly the reachability signal FR-012 needs to stay
sharp. (Complications, called out in the spec as an optional stretch, would be the one place a
background-delivered snapshot might make sense later — out of scope for this feature per the
spec's own Assumptions.)

**Rationale**: `sendMessage` requires `WCSession.isReachable == true` and fails immediately and
explicitly when it isn't (or when the counterpart app isn't running to receive it) — this failure
*is* FR-012's "not connected" state, not something to detect separately. Using a queued/background
API instead would mean a request could sit unresolved for an indeterminate time with no clean
"it failed" signal, which is precisely the "silent failure / indefinite spinner" FR-012 forbids.

**Alternatives considered**: `transferUserInfo` for approval/feed sync — rejected for the reason
above; reconsider only if/when a complication is built, since a complication genuinely does want a
best-effort cached snapshot rather than a live round trip.

## D3: Watch-side approval confirmation (per Clarifications)

**Decision**: `LAContext().evaluatePolicy(.deviceOwnerAuthentication, localizedReason: ..., reply:)`
on the watch, called fresh immediately before every single approve/deny action — never cached,
never skipped because the watch is already unlocked. `LAPolicy.deviceOwnerAuthentication` (not
`.deviceOwnerAuthenticationWithBiometrics`) is the correct policy: watchOS has no biometric sensor,
so this policy resolves to a passcode prompt, which is exactly the confirmed answer to the
Clarifications question.

**Rationale**: Directly implements the clarified requirement (FR-003/FR-004) — an explicit,
per-action passcode re-check, not an ambient unlock-state check. `.deviceOwnerAuthentication`'s
passcode-first behavior is watchOS's documented behavior for devices without biometric hardware, so
no biometric APIs are invoked or even attempted, keeping the resolution-method attribution
(FR-004) truthful without needing extra logic to detect which modality actually fired.

**Alternatives considered**: `.deviceOwnerAuthenticationWithBiometrics` — rejected outright, would
simply fail on every watchOS device (no sensor exists) since this policy has no passcode fallback.

## D4: What "resolved_via" the Border/phone records for a watch approval

**Decision**: Confirmed by direct inspection of the actual Border code (not just the phone side):
`Authorizer.resolve_approval(approval_id, action, via="cli")`
(`bgp/federation/authorization.py:149`) already accepts an arbitrary `via` string — but
`_edge_on_approval_resolve` (`bgp/federation/service.py:1288-1304`), the handler for
`n2n/edge/approval_resolve`, currently **hardcodes `via="biometric"` unconditionally** for every
edge/phone-originated resolution, with no `via`/method field read from the wire request at all. Two
small, additive changes close this precisely:
1. `EdgeAskClient`/`ApprovalClient`'s wire call gains an optional `confirmation_method` field in the
   `n2n/edge/approval_resolve` request (e.g. `"biometric"` for the existing phone path,
   `"watch_passcode"` for the new watch-relayed path).
2. `_edge_on_approval_resolve` reads that field (defaulting to `"biometric"` if absent, so the
   existing phone flow's wire behavior is byte-for-byte unchanged) and passes it through to
   `resolve_approval(..., via=<that value>)` instead of the current hardcoded literal.

**Rationale**: This is the minimal, fully backward-compatible change that makes FR-004 true at the
source of truth (the Border's own audit record via `Authorizer.resolve_approval`'s existing `via`
parameter) rather than only in the phone/watch UI's own display — `resolve_approval` already has
the exact extensibility point needed; nothing about its own logic needs to change, only who calls
it with what string.

**Alternatives considered**: Leaving `_edge_on_approval_resolve` hardcoded and only changing what
the *phone UI* displays for a watch-relayed approval — rejected; FR-004 requires the record itself
(what the Border persists and could be audited/queried later) to be accurate, not just what a
screen happens to show at the moment of resolution.

## D5: Dictation input on watchOS

**Decision**: A SwiftUI `TextField` bound to dictation-first input — watchOS's system text input
sheet (triggered by tapping the field) already defaults to offering Dictation as the primary input
method for short text, alongside Scribble/emoji as system-provided alternatives outside this app's
control. No custom speech-recognition code is written; the system dictation pipeline is used as-is
via the standard text input presentation, matching the spec's "quick voice ask" framing without
requiring a bespoke `SFSpeechRecognizer` integration (which would duplicate what the system control
already provides for free and consistently across watchOS).

**Rationale**: watchOS does not let an app suppress the system's other input methods (Scribble,
emoji) from its own text-input sheet — "dictation only" in the spec's plain-language framing means
*this app's primary, designed-for interaction is dictation*, not a technical requirement to disable
system-provided alternatives, which isn't achievable through public API anyway.

**Alternatives considered**: A custom `SFSpeechRecognizer`-based capture UI — rejected as needless
duplication of a system capability already exposed through the standard text field, and it would
require its own microphone-permission story separate from the phone's already-solved one.

## D6: Environment — real watch reachability unconfirmed via CLI

**Decision**: Task list treats real-device verification as best-effort, matching spec 071's own
precedent (research D7/D8 there): Simulator-based build/run verification is the baseline
deliverable; a real, physical watch paired to the already-used iPhone is attempted opportunistically
and its outcome documented (verified / blocked-with-reason) rather than assumed.

**Rationale**: `xcrun devicectl list devices` and `xcrun xctrace list devices` both list only the
phone as a directly-tethered device — a paired watch is not enumerable this way; Apple's own
tooling surfaces a paired watch as a run destination only inside Xcode's GUI (Devices and
Simulators window, or the scheme destination picker) once the phone itself is connected and
trusted. This was independently re-confirmed for this feature (same commands, same result as spec
071's environment).

**Alternatives considered**: Blocking this feature on a positive real-watch confirmation before any
work starts — rejected; the watchOS Simulators are fully capable of exercising every capability in
this spec except the confirmation step's actual passcode hardware prompt (Simulator supports a
simulated passcode too, so even that is exercisable, just not on real Secure Enclave-backed
hardware).
