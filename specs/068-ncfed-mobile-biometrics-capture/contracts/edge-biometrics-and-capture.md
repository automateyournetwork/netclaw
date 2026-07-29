# Contract: Biometric Approvals + Capture

Three new wire methods, plus reuse/extension of two existing ones from 066/067.

## 1. `n2n/edge/register_capabilities` — phone tells the Border its enabled capture types

**Request** (phone → Border, at connect time and whenever a Settings toggle changes):

```json
{ "capabilities": ["camera.capture", "audio.record"] }
```

**Result**: `{ "registered": true }`

**Rules**: Replaces the phone's capture-related `scope` entries with exactly this list (research
D1) — a type omitted here is not just refused, it's invisible to `RiskRouter` (FR-007a).

## 2. `n2n/edge/capture` — Border requests a capture (US3)

**Request** (Border → phone, over `self.edge_channels[member_id]`, mirroring `push_to_edge`):

```json
{ "capability": "camera.capture" }
```

**Result** (phone → Border):

```json
{ "decision": "captured", "content_type": "image", "content": "<base64>" }
```
or
```json
{ "decision": "declined", "reason": "permission_denied" }
```

**Rules**: Triggered by an ordinary `n2n_delegate(target_name="camera.capture", ...)` call —
`route_and_delegate()` resolves the phone as the target member (research D1/D2) exactly as it
would resolve any agent member, then `delegate_to_member()` branches on `node_type='edge'` to
call this method instead of `n2n/tasks/submit`, still tracked via the existing `TaskManager`
(same `n2n_task_status`/`result`/`cancel` surface 067 already established). A declined/cancelled
capture is `decision: "declined"`, never a silent empty result or a hang (FR-009).

## 3. `n2n/edge/approval_resolve` — phone resolves a pushed approval via biometric (US1)

**Request** (phone → Border, sent ONLY after local biometric authentication succeeds):

```json
{ "approval_id": 42, "action": "approve" }
```

**Result**: `{ "approval_id": 42, "resolved": true }`

**Rules**: Calls `Authorizer.resolve_approval(approval_id, action, via="biometric")`
unchanged (research D6) — no biometric proof travels over the wire; the Border trusts the
phone's report the same way it trusts any other edge-node action (research D7). A failed/
cancelled/unavailable biometric attempt on the phone means this method is simply never called
— the approval stays pending (FR-002).

## 4. `n2n/edge/ask` gains an optional `attachment` (US2, no new method)

```json
{ "text": "what am I looking at?", "attachment": { "content_type": "image", "content": "<base64>" } }
```

`text` may be empty when the capture stands alone (FR-005's "no accompanying text" case) —
`attachment` alone is a valid request. `_edge_on_ask` folds a present attachment into the
agent-turn prompt before calling `gateway.run_agent_turn()`; no new dispatch path.

## 5. `n2n/edge/message` gains `content_type="approval"` (US1 push, no new method)

See data-model.md's Approval Push Payload — delivered via the EXISTING `push_to_edge()`
(066/US2), including its EXISTING disconnected-device FCM/APNs fallback (066/US3), with no new
Border-side push code (research D5). `notify_approval()` calls this for every connected edge
channel, in addition to its existing (never-wired) `approval_notifier` callback, which is
untouched.

---

**Note (spec 072)**: `n2n/edge/approval_resolve` (§3 above) gained an optional
`confirmation_method` field in `072-apple-watch-companion` — the Apple Watch companion app has
no Face ID/Touch ID sensor, so a watch-resolved approval sends `confirmation_method:
"watch_passcode"` instead of the implicit `"biometric"` this spec defines. See
`specs/072-apple-watch-companion/contracts/watch-relay.md` §5 for the full field definition.
