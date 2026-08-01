# Contract: New Watch Relay Methods, Local Notifications, and the Border-Facing Addition

Extends `specs/072-apple-watch-companion/contracts/watch-relay.md` — same transport (`WCSession.sendMessage` → `WatchRelayPlugin.swift` → `FlutterMethodChannel` → `watch_relay.dart`), same failure mode (an unreachable phone never reaches Dart at all, it's the `phoneUnreachable` relay-availability state).

## 1. `watch/feed/acknowledge` and `watch/feed/delete`

**Request** (watch → phone):

```json
{ "method": "watch/feed/acknowledge", "pushed_at": "2026-07-27T13:58:02Z" }
```

```json
{ "method": "watch/feed/delete", "pushed_at": "2026-07-27T13:58:02Z" }
```

**Reply** (both):

```json
{ "acknowledged": true }
```
```json
{ "deleted": true }
```

Internally calls `MessageFeedStore.acknowledge(pushedAt)` / `.delete(pushedAt)` (data-model.md) — the SAME store the phone's own Feed screen reads/writes directly, so the change is visible to the phone the next time it reads that store (no separate sync step, per FR-014).

## 2. `watch/history/acknowledge` and `watch/history/delete`

**Request** (watch → phone):

```json
{ "method": "watch/history/acknowledge", "task_id": "b3f1...-uuid" }
```

```json
{ "method": "watch/history/delete", "task_id": "b3f1...-uuid" }
```

**Reply** (both): same shape as §1 (`{"acknowledged": true}` / `{"deleted": true}`).

Internally calls `ConversationStore.acknowledge(taskId)` / `.delete(taskId)`.

## 3. `watch/history/list` gains `acknowledged` per turn (extends spec 072 §—)

The existing `watch/history/list` reply (introduced in spec 072 as an addendum, not in the original contract doc) gains one field per turn:

```json
{
  "enrolled": true,
  "turns": [
    { "task_id": "b3f1...-uuid", "request_text": "is R2 still flapping",
      "answer_text": "No, cleared 4 minutes ago.", "state": "answered",
      "acknowledged": false }
  ]
}
```

`watch/feed/list`'s reply gains the equivalent `acknowledged` field per message.

## 4. Local notification payload shape (phone-internal, not a wire contract with the Border)

Every locally-posted notification (via `flutter_local_notifications`) carries a JSON-encoded `payload` string, consumed by the extended `NotificationDeepLink` dispatcher (research D4) on tap:

```json
{ "type": "feed", "identifier": "2026-07-27T13:58:02Z" }
{ "type": "chat", "identifier": "b3f1...-uuid" }
{ "type": "approval", "identifier": "42" }
```

`type` determines both the notification's content (preview text vs. Approve/Deny actions) and where a tap deep-links. Approval notifications additionally declare two `DarwinNotificationAction`s (`approve`/`deny`), each with `DarwinNotificationActionOption.authenticationRequired` set (research D2) — tapping either still routes through the existing `ApprovalClient`-mediated biometric confirmation before calling resolve, exactly as the in-app buttons do; the OS-level unlock requirement is an additional gate, not a replacement for it.

## 5. Border-facing addition: `already_resolved` on the `n2n/edge/approval_resolve` reply

**Current wire shape** (unchanged request; this is a reply-side addition only):

```json
{ "approval_id": 42, "resolved": true }
```

**New, additive field**:

```json
{ "approval_id": 42, "resolved": true, "already_resolved": false }
```

**Rules**:
- `already_resolved: false` means this call is what actually transitioned the approval out of `pending` (a normal, first-time resolve).
- `already_resolved: true` means the approval was already resolved (by the in-app flow, another device, or a duplicate notification-action tap) — `resolve_approval()`'s `UPDATE ... WHERE status='pending'` matched zero rows (research D6), so this call had no effect, but is still reported as `resolved: true` for backwards compatibility with any caller that only checks that field.
- A caller that ignores `already_resolved` entirely sees byte-for-byte identical behavior to today.
- `_edge_on_approval_resolve` (`bgp/federation/service.py:1288`) is the only handler that needs to change to thread this new value through from `Authorizer.resolve_approval()`'s (`bgp/federation/authorization.py:149`) extended return.
