# Contract: N2N Wire Protocol (NCFED channel)

**Feature**: 052-n2n-federation | **Consumers**: bgp-daemon-v2 federation layer on both peers

## Channel establishment

1. Transport: a dedicated TCP connection to the peer's existing public mesh
   endpoint (the same host:port BGP dials — no new exposure, FR-010).
2. Discrimination handshake (extends bgp/agent.py first-byte peek):
   - Initiator sends: `NCFED` (5 bytes ASCII) + local AS (4 bytes, big-endian)
     + local router-id (4 bytes, IPv4-encoded).
   - Acceptor matches AS+router-id against an Established BGP mesh session and
     a `federated` (or `consent_pending_local`) FederationPeer row; otherwise
     closes immediately. This is the channel-anchored identity check (FR-003).
   - Acceptor replies with its own `NCFED` + AS + router-id; initiator performs
     the same validation.
3. Collision avoidance: the lower-AS side initiates (same rule as NCTUN).
   The higher-AS side never dials; if no channel exists it waits.
4. Reconnect: exponential backoff 5 s → 60 s while both consents remain active.

## Framing

```
[4-byte big-endian payload length][1-byte flags][payload: UTF-8 JSON-RPC 2.0]
```

- `flags` bit 0: continuation (payload is a chunk of a larger message; chunks
  concatenate in order until a frame with bit 0 clear).
- Max payload per frame: 65 536 bytes. Inventories chunk (research R2).
- Heartbeat: empty-payload frame (length 0, flags 0) every 30 s of silence;
  3 missed heartbeats → channel considered down (federation state unchanged;
  reconnect per above).

## JSON-RPC 2.0 methods

All messages are JSON-RPC 2.0 (`"jsonrpc": "2.0"`). Requests carry string ids
prefixed with the sender identity (`as65001-4.4.4.4:17`) for dual-side audit
correlation (FR-015).

### Federation lifecycle

| Method | Direction | Params | Result |
|---|---|---|---|
| `n2n/hello` | both, on channel open | `{identity, display_name, versions: ["1.0"]}` | `{identity, display_name, version: "1.0"}` |
| `n2n/consent_state` | both | `{state}` | `{state}` — used to surface pending/severed transitions |
| `n2n/sever` | either | `{}` | `{acked: true}` — kill switch notification; receiver marks peer severed and closes channel (FR-004) |

### Capability exchange (A2A AgentCard-inspired)

| Method | Direction | Params | Result |
|---|---|---|---|
| `n2n/inventory` | push, on federate + change + interval | full CapabilityInventory document (data-model.md) | `{accepted: true, version}` |
| `n2n/inventory_get` | pull (recovery) | `{min_version?}` | full inventory document |

### Tool invocation (MCP-shaped)

| Method | Direction | Params | Result |
|---|---|---|---|
| `n2n/tools/call` | requester → executor | `{tool: "cml-mcp/list_labs", arguments: {...}, timeout_s}` | MCP `tools/call`-shaped result `{content: [...], isError}` |

Errors use JSON-RPC error objects with reserved codes:
`-32001` not_allowlisted · `-32002` approval_pending · `-32003` approval_expired
· `-32004` budget_exhausted · `-32005` rate_limited · `-32006` execution_timeout
· `-32007` severed · `-32008` guardrail_blocked (DefenseClaw inspection refused
the call — FR-014). Every refusal names its code in `error.message` (FR-012/017).

### Skill delegation (A2A task-lifecycle-inspired)

| Method | Direction | Params / Notes |
|---|---|---|
| `n2n/tasks/submit` | requester → executor | `{skill, input_text, timeout_s}` → `{task_id, status: "submitted"}` |
| `n2n/tasks/status` | executor → requester (notification) | `{task_id, status: submitted\|working\|approval_pending\|completed\|failed\|expired, detail?}` |
| `n2n/tasks/result` | executor → requester | `{task_id, status, output_text, tokens_used}` |
| `n2n/tasks/cancel` | requester → executor | `{task_id}` → `{cancelled: bool}` |

### Chat (A2A message/stream-inspired)

| Method | Direction | Params / Notes |
|---|---|---|
| `n2n/chat/open` | initiator → peer | `{session_id, operator_display}` → `{accepted, reason?}` (refused if chat disabled — FR-018) |
| `n2n/chat/message` | either | `{session_id, seq, text}` — acked `{received: seq}` |
| `n2n/chat/stream` | responder → initiator (notification) | `{session_id, seq, chunk, done}` — incremental response chunks (FR-019 streaming) |
| `n2n/chat/close` | either | `{session_id}` |

## Invariants

- Every inbound method except `n2n/hello` requires `state == federated`.
- Inbound `n2n/tools/call` and `n2n/tasks/submit` debit BudgetCounter before
  execution; refusals are free but rate-limited.
- No payload may contain values sourced from `.env`, credential stores, or
  testbed secrets (FR-007) — enforced at inventory build and result
  serialization, tested by the no-secrets invariant test.
- Requesting side treats all results/outputs as untrusted data (FR-016): they
  are returned to the operator/agent as content, never executed.
