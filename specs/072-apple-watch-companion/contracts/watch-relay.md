# Contract: Watch ↔ Phone Relay, and the One Border-Facing Addition

Three request/reply message shapes over `WCSession.sendMessage` (watch → phone), each forwarded by
`WatchRelayPlugin.swift` into Dart via a `FlutterMethodChannel` and answered by `watch_relay.dart`
using the phone's already-live `ApprovalClient`/`EdgeAskClient`/`MessageFeedStore`. Plus one
additive field on the existing Border-facing `n2n/edge/approval_resolve` call (research D4).

All three watch→phone calls share the same failure mode: if `sendMessage` itself fails (phone
unreachable, companion app not running) that failure IS the `phoneUnreachable` relay-availability
state (research D2) — it never reaches Dart at all, so it isn't listed as a "response" below.

## 1. `watch/approvals/list` — fetch pending approvals

**Request** (watch → phone, no payload needed):

```json
{ "method": "watch/approvals/list" }
```

**Reply** (phone → watch):

```json
{
  "enrolled": true,
  "approvals": [
    { "approval_id": 42, "target_type": "config_change", "target_name": "R2-Toronto",
      "requesting_agent": "netops-agent", "risk_name": "johns-risk",
      "pushed_at": "2026-07-27T14:02:11Z" }
  ]
}
```

`enrolled: false` (empty `approvals`) is how the phone reports the `notEnrolled` relay-availability
state — the call succeeded (phone reachable), but there is nothing enrolled to relay from.

## 2. `watch/approvals/resolve` — approve or deny

**Request** (watch → phone), sent only after the watch's own `LAContext` passcode confirmation
(research D3) has already succeeded — the phone relay does not re-check biometrics/passcode itself,
exactly as the existing phone `approvals_screen.dart` trusts its own UI-layer gate before calling
`ApprovalClient.resolve()`:

```json
{ "method": "watch/approvals/resolve", "approval_id": 42, "action": "approve" }
```

**Reply**:

```json
{ "resolved": true }
```

Internally, the phone relay calls `ApprovalClient.resolve(42, "approve")`, which now sends
`n2n/edge/approval_resolve` to the Border with the additive field described in §4 below, set to
`"watch_passcode"` — never `"biometric"`, since no such sensor fired.

## 3. `watch/feed/list` — fetch pushed messages

**Request**:

```json
{ "method": "watch/feed/list" }
```

**Reply**:

```json
{
  "enrolled": true,
  "messages": [
    { "content_type": "text", "content": "R2 flapping session cleared.",
      "designated_by": "agent", "pushed_at": "2026-07-27T13:58:02Z" },
    { "content_type": "image", "content": "", "designated_by": "agent",
      "pushed_at": "2026-07-27T13:40:00Z" }
  ]
}
```

Per data-model.md, `content` MAY be empty/truncated for non-text types — the watch only needs
`content_type` to show "[Photo]"/"[Voice message]" placeholders per FR-007.

## 4. `watch/ask/submit` and `watch/ask/status` — quick voice ask

**Submit** (watch → phone):

```json
{ "method": "watch/ask/submit", "text": "is R2 still flapping" }
```

**Submit reply**:

```json
{ "task_id": "b3f1...-uuid" }
```

**Status poll** (watch → phone, while `state == "waiting"`):

```json
{ "method": "watch/ask/status", "task_id": "b3f1...-uuid" }
```

**Status reply**:

```json
{ "task_id": "b3f1...-uuid", "state": "answered", "answer_text": "No, cleared 4 minutes ago." }
```

`state` uses the narrowed three-value vocabulary from data-model.md's Watch Ask Turn, not the
phone's full `TaskState` enum — the mapping (`pending`/`working` → `waiting`, etc.) happens in
`watch_relay.dart`, not on the watch.

## 5. Border-facing addition: `confirmation_method` on `n2n/edge/approval_resolve`

**Current wire shape** (unchanged for the existing phone path):

```json
{ "approval_id": 42, "action": "approve" }
```

**New, additive field**:

```json
{ "approval_id": 42, "action": "approve", "confirmation_method": "watch_passcode" }
```

**Rules**:
- `confirmation_method` is optional. When absent, `_edge_on_approval_resolve`
  (`bgp/federation/service.py:1288`) defaults it to `"biometric"` — byte-for-byte identical
  behavior to today for the existing phone flow, which never sends this field.
- The only two values this feature introduces are `"biometric"` (implicit default, phone) and
  `"watch_passcode"` (explicit, watch relay) — no other value is defined by this feature.
- `_edge_on_approval_resolve` passes the resolved value straight through to
  `Authorizer.resolve_approval(approval_id, action, via=<value>)`
  (`bgp/federation/authorization.py:149`), which already accepts an arbitrary `via` string — no
  change needed inside `resolve_approval` itself.
