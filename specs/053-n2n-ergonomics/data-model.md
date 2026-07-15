# Data Model: N2N Ergonomics & Reliability

**Feature**: 053-n2n-ergonomics | **Date**: 2026-07-11
**Store**: extends 052's SQLite `~/.openclaw/n2n/federation.db` + in-memory
service state. Only ADDITIVE changes (052 tables/columns unchanged, FR-022).

## New table: delegated_task (US1, persisted for FR-004)

| Field | Type | Notes |
|---|---|---|
| task_id | TEXT PK | UUID |
| direction | TEXT | `inbound` (we run it for a peer) \| `outbound` (peer runs it for us) |
| peer_identity | TEXT | `as<AS>-<router-id>` |
| target_type | TEXT | `skill` \| `tool` |
| target_name | TEXT | e.g. `cml-lab-lifecycle` |
| input_text | TEXT | request input (no secrets) |
| state | TEXT | `submitted` \| `working` \| `completed` \| `failed` \| `cancelled` |
| progress | TEXT | free-text/step counter (e.g. "3/10 nodes") |
| result_ref | TEXT | path to stored result payload (reuses audit result store) |
| tokens_used | INTEGER | for budget accounting |
| created_at / updated_at / completed_at | TEXT | ISO 8601 |
| retention_until | TEXT | created_at + `N2N_TASK_RETENTION_S`; swept after |

**State transitions**:
```
submitted → working → completed
                    → failed
submitted|working → cancelled   (via n2n/tasks/cancel)
```
- Rows survive channel drop/reconnect and daemon restart → result retrievable
  after transient loss (FR-004). Swept when now > retention_until.
- Inbound tasks debit the peer's existing budget (052 BudgetCounter) on
  completion — unchanged accounting.

## Extended: federation_peer (US3 — columns already exist in 052)

`endpoint_host` / `endpoint_port` are now actively updated by an authenticated
`n2n/endpoint_update` (FR-011); add `endpoint_updated_at` (TEXT) for freshness
display (US6). No other schema change.

## In-memory: ChannelHealth (US2, per live channel — not persisted)

| Field | Notes |
|---|---|
| peer_identity | |
| last_heartbeat_at | updated on any inbound frame/heartbeat |
| consecutive_misses | incremented by the heartbeat loop; ≥ limit → close+dereg |
| state | `up` \| `reconnecting` \| `unreachable` |
| reconnect_attempts | drives bounded backoff (5s→60s) |
| next_retry_at | |

Rebuilt from scratch on daemon start; consent (persisted) drives which peers the
reconnect supervisor watches.

## In-memory / exchanged: CapabilityDescriptor (US4)

Sent inside `n2n/hello` params and stored on the channel + `federation_peer`:
```json
{
  "proto_version": "053",
  "features": ["async_tasks", "endpoint_reannounce", "negotiate"],
  "agent_invoke": "session-id",          // flag this peer's CLI supports
  "reply_shapes": ["finalAssistantVisibleText", "payloads"]
}
```
- Absent descriptor ⇒ peer treated as `proto_version="052"`, features empty →
  graceful degrade (FR-016): no async tasks (fall back to synchronous skill call
  with the 052 behavior), no auto-endpoint-update.
- Local descriptor built by `negotiate.py` probing `openclaw agent --help`.

## Relationships

```
FederationPeer (052) 1—N DelegatedTask        (by peer_identity)
FederationPeer (052) 1—1 CapabilityDescriptor (latest from hello)
FederationPeer (052) 1—1 ChannelHealth        (in-memory, while known)
DelegatedTask —0..1 RemoteInvocationRecord(052)  (audit link on completion)
```

All new state is additive; 052 entities (FederationPeer, ConsentRecord,
CapabilityInventory, InvocationGrant, BudgetCounter, RemoteInvocationRecord,
ApprovalRequest, N2NChatSession) are unchanged.
