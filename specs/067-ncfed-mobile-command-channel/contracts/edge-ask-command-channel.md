# Contract: Phone-to-Border Command Channel

One new wire method pair, plus reuse of three existing ones, all over the edge WebSocket
connection feature 066 established.

## 1. `n2n/edge/ask` — phone asks the Border something

**Request** (phone → Border):

```json
{ "text": "check every core router for BGP problems" }
```

**Result** (Border → phone, immediate — does NOT block on the answer):

```json
{ "task_id": "b3f1...-uuid" }
```

**Rules**
- Creates a `delegated_task` row (`direction=inbound`, `target_type=edge_ask`,
  `peer_identity=<member_id>`) via the existing `TaskManager.create()` (feature 053) and spawns
  a background worker calling `gateway.run_agent_turn(text, session_key=f"n2n-edge-{member_id}",
  untrusted=False)` (research D2/D4) — returns immediately, never blocks the RPC.
- `session_key` is per-device (`member_id`), giving each enrolled phone its own independent
  agent session (FR-007) — no cross-device state.
- The agent's own reasoning decides whether to answer directly, delegate to an in-risk member
  (`n2n_delegate`), or route to an eN2N peer (`n2n_route`/`n2n_invoke`) — no Border-side
  branching logic exists for this; see research D3.

## 2. `n2n/edge/ask_result` — Border pushes the finished answer

**Notification** (Border → phone, once the background task completes):

```json
{
  "task_id": "b3f1...-uuid",
  "state": "completed",
  "output_text": "Checked all 4 core routers — R2-Toronto has 1 flapping BGP session with...",
  "tokens_used": 842
}
```

**Rules**
- Best-effort push over the still-open connection — if the phone disconnected before
  completion, this notify simply has nowhere to go; the phone recovers via `n2n/tasks/status`/
  `result` on reconnect (edge case: app killed mid-request).
- `state` is one of `completed` | `failed` | `cancelled` (mirrors `TaskManager`'s existing
  states exactly — no new state vocabulary).

## 3-5. Reused as-is: `n2n/tasks/status`, `n2n/tasks/result`, `n2n/tasks/cancel`

Identical request/response shapes to the existing iN2N member-facing versions
(`Invoker.handle_task_status`/`handle_task_result`/`handle_task_cancel`,
`invocation.py:224-235`) — registered under the SAME method names in the edge channel's
handler map. `owner` binding is `channel.peer_identity` (the phone's `member_id`), exactly as
for a member channel — a task_id belonging to a different device is answered as "unknown",
never leaked (NCFED -00 §9.2/§14.6, unchanged).

```json
// n2n/tasks/status request/result
{ "task_id": "b3f1...-uuid" } → { "task_id": "...", "state": "working", "progress": "..." }

// n2n/tasks/cancel request/result
{ "task_id": "b3f1...-uuid" } → { "task_id": "...", "cancelled": true }
```

## Client-side shortcuts (no new wire surface)

- **Voice (US4)**: transcribed on-device to text; sent as an ordinary `n2n/edge/ask` — the
  Border never sees a difference between a typed and a spoken request (research D7).
- **Device deep link (US5)**: `netclaw://device/<id>` or its QR form resolves locally into
  `n2n/edge/ask` with `{"text": "What is the current status of device <id>?"}` — no new
  Border-side method, no device registry (research D8).
