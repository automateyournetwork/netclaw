# Contract: N2N Control Methods — endpoint update & capability negotiation

**Feature**: 053 | **Channel**: NCFED (unchanged framing). Additive methods /
handshake fields only; 052 methods unchanged (FR-022).

## Capability negotiation — extend `n2n/hello` (US4)

`n2n/hello` (exchanged at federate and on every reconnect) gains a
`capabilities` field in params and result:

```json
{
  "identity": "as65001-4.4.4.4",
  "display_name": "John",
  "versions": ["1.0"],
  "capabilities": {
    "proto_version": "053",
    "features": ["async_tasks", "endpoint_reannounce", "negotiate"],
    "agent_invoke": "session-id",
    "reply_shapes": ["finalAssistantVisibleText", "payloads"]
  }
}
```

Rules:
- Each side stores the peer's descriptor and adapts:
  - use `async_tasks` path only if the peer advertises it, else fall back to the
    052 synchronous skill call (graceful degrade, FR-016).
  - responder uses its OWN probed `agent_invoke`/reply-shape locally (it runs
    its own agent) — the descriptor is informational for the requester.
- **Missing `capabilities`** ⇒ peer is pre-053 ⇒ `proto_version="052"`, empty
  features ⇒ 052 behavior only. No breakage (FR-016).
- Negotiation adds no new round trip (rides the existing hello).

## Endpoint re-announce — new `n2n/endpoint_update` (US3)

| Method | Direction | Params | Result |
|---|---|---|---|
| `n2n/endpoint_update` | claw → each federated peer, on local endpoint change | `{identity, endpoint: "host:port"}` | `{accepted: bool}` |

Receiver rules (FR-011, FR-012):
1. Accept ONLY if `identity` matches an already-federated peer AND the update
   arrived over that identity's authenticated NCFED session (bound to the
   established BGP mesh identity — same anchor as 052). Otherwise reject + log.
2. Update `federation_peer.endpoint_host/port` + `endpoint_updated_at`.
3. Trigger the reconnect supervisor to re-dial the new endpoint, preserving the
   lower-AS-initiates role (higher-AS side just updates its record and waits).

The existing BGP mesh-directory exchange (`_send_mesh_directory` /
`_process_mesh_directory` in agent.py) remains the backup carrier for endpoints;
`n2n/endpoint_update` is the fast, explicit path over the federation channel.

## Reconnect behavior (US2 — no new wire method)

Auto-reconnect is local behavior, not a wire method: the service's reconnect
supervisor re-runs the existing `open_channel` (052, which already replaces a
stale channel) with bounded backoff (5 s → 60 s) for any `federated` peer whose
channel is down. `n2n/hello` re-runs on the fresh channel, re-exchanging the
capability descriptor.
