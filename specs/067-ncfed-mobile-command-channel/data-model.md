# Phase 1 Data Model: NCFED Mobile Command Channel

No new Border-side persistent schema (research D6) — this feature reuses the existing
`delegated_task` table (feature 053) and adds no columns to it or to `member`.

## Entities

### Phone-Originated Request (ephemeral, Border-side)

Represented as a normal `delegated_task` row (feature 053's existing table), created by
`_edge_on_ask` exactly as `_in2n_member_submit` already creates one for member-delegated
skill execution:

| Field | Value for an edge-ask task |
|-------|------------------------------|
| `direction` | `inbound` |
| `peer_identity` | the edge node's `member_id` (owner-binding, reused unchanged from 053) |
| `target_type` | `edge_ask` (new discriminator value; existing column, no migration) |
| `target_name` | `ask` (constant — there's only one kind of edge-ask task) |
| `input_text` | the phone's request text (post-transcription if it was voice, D7) |
| `state` / `progress` / `result_ref` / `tokens_used` | unchanged semantics — `TaskManager` already manages these |

### Answer Attribution

Not a new column or table — it is text within the agent's own composed reply (`output_text`
in the task's `result_ref` JSON), because the agent itself is what decides whether it answered
directly, delegated, or routed externally, and it already names the source when it does
(research D3). No Border-side structured attribution field is introduced.

### Device Deep Link (client-side only)

Not a Border-side entity at all — a URI (`netclaw://device/<id>`) or QR payload the phone
parses locally into a fixed-template `n2n/edge/ask` request. No Border-side registry, no new
table (research D8).

### Conversation (app-local, one per device — FR-007)

```dart
class ConversationTurn {
  final String requestText;
  final String? answerText;       // null while in-progress
  final String state;              // 'pending' | 'completed' | 'failed' | 'cancelled'
  final String? taskId;
  final DateTime submittedAt;
}
```

Persisted as JSON Lines under the app's documents directory (mirrors 066's `MessageFeedStore`
— `ConversationStore`), one file per installation (already inherently per-device — no
cross-device sync mechanism exists to build or omit).
