# Phase 1 Contracts: Federation Inbound-Call Observability

**Feature**: 100-federation-log-observability
**Date**: 2026-08-06
**Input**: [spec.md](../spec.md) · [research.md](../research.md) R7, R8 · [data-model.md](../data-model.md)

Three contract surfaces: configuration (env vars), the operator-facing tool and its
daemon route, and the log line formats an operator reads. All three are the *stable*
part of this feature — thresholds are tunable, but these shapes are what tests and
operators depend on.

---

## 1. Configuration — new environment variables

Named on the existing `N2N_RECONNECT_*` prefix (`service.py:83-85`, research R8).
**Every default preserves today's observable behavior except where the spec mandates
a change** (FR-010's escalated ceiling, FR-031's reset rule).

| Variable | Default | Unit | Governs |
|---|---|---|---|
| `N2N_RECONNECT_DAMPEN` | `1` | bool (`0` disables) | Master switch (FR-028). `0` restores per-attempt `WARNING` logging and the flat 60 s ceiling — today's exact behavior. |
| `N2N_RECONNECT_DEAD_CEILING_S` | `900` | seconds | Escalated retry ceiling for a durably-dead peer (FR-010, ≈15 min per clarification). |
| `N2N_RECONNECT_DEAD_AFTER` | `20` | count | Consecutive failures before a peer is *eligible* for escalation (FR-010). At the existing 60 s ceiling, 20 failures ≈ 18 min of continuous failure. |
| `N2N_RECONNECT_ENDPOINT_STALE_S` | `86400` | seconds | Endpoint-freshness horizon; older than this counts as stale (FR-011). |
| `N2N_RECONNECT_SUMMARY_INTERVAL_S` | `300` | seconds | Cadence of the collapsed failure summary (FR-008/009) and of probe summaries (FR-038). |
| `N2N_RECONNECT_STABLE_AFTER_S` | `120` | seconds | Continuous uptime required before dampening clears (FR-031). Prevents a flapping peer resetting its history. |

### 1.1 Invariants

- **Both signals required** (FR-011): escalation needs `attempts >= DEAD_AFTER`
  **and** endpoint staler than `ENDPOINT_STALE_S`. Either alone keeps the 60 s ceiling.
- **`DAMPEN=0` is a true bypass** (FR-028/SC-010): no suppression, no summaries, no
  escalated ceiling, no probe collapsing. Verbatim pre-feature behavior.
- **Denials are never dampened** (FR-003): these variables govern the reconnect
  supervisor and the inbound-accept path only. They are not read by `Auditor.record()`.
- **Malformed values fall back to the default** rather than raising — a typo in an env
  file must not prevent the daemon from starting.

All six documented in `.env.example` with no values (Constitution XI/XIII).

---

## 2. Registry operation — `FederationManager.forget_peer_endpoint`

```python
def forget_peer_endpoint(self, identity: str) -> dict:
    """Clear a peer's dial endpoint (FR-021).

    Sets endpoint_host, endpoint_port and endpoint_updated_at to NULL together,
    leaving federated state, trust material, chat enablement and audit history
    untouched (FR-022). Returns the prior endpoint so the operation is reversible
    by hand and reportable.
    """
```

**Return shape**

```json
{
  "identity": "as65099-10.255.255.1",
  "forgotten": true,
  "previous": { "host": "1.2.3.4", "port": 1179, "updated_at": "2026-07-25T16:53:04Z" }
}
```

- `forgotten: false` with `previous: null` when the peer already had no endpoint —
  **idempotent, not an error**.
- Unknown identity raises `KeyError`; the route maps it to HTTP 404.

**Why a distinct method** (research R7): `upsert_peer` treats `None` as "leave
unchanged" (`manager.py:298-299`), so clearing through it is impossible, and adding a
sentinel would make every existing caller's semantics ambiguous. Resolving the live
incident on 2026-08-06 required raw SQL against the running database — precisely what
FR-026 forbids.

**Not a channel teardown** (research R7 open item, resolved): the endpoint is consulted
only for *dialling*. A live channel is unaffected and is deliberately left running —
tearing it down would turn a cleanup action into an outage.

**Attribution** (FR-025): recorded through the existing `Auditor.record()` GAIT path
with `event="endpoint-forgotten"` and `actor`, satisfying Constitution IV. No new trail.

---

## 3. Daemon route

```
POST /n2n/peers/forget-endpoint
```

Follows the existing `if path == ... and method == ...` dispatch style
(`bgp-daemon-v2.py:464`).

**Request**

```json
{ "peer": "as65099-10.255.255.1", "actor": "operator" }
```

| Field | Required | Notes |
|---|---|---|
| `peer` | yes | `as<AS>-<router-id>`. Missing → `400`. |
| `actor` | no | Recorded for attribution; defaults to `"operator"`. |

**Responses**

| Code | Body |
|---|---|
| `200` | the §2 return shape |
| `400` | `{"error": "missing required field 'peer'"}` |
| `404` | `{"error": "unknown peer <identity>"}` |

Deliberately **not** `DELETE` on a peer sub-resource: the peer is not being deleted,
only one attribute cleared, and the spec's Out of Scope explicitly excludes retiring
peer records. A `POST` verb-style route makes that distinction legible.

---

## 4. MCP tool — `n2n_forget_endpoint`

Added to the already-registered `n2n-mcp` server. Brings its tool count **38 → 39**
(Constitution XII — `TOOLS.md` and any stated README count must match).

```python
@mcp.tool()
async def n2n_forget_endpoint(peer: str, actor: str = "operator") -> str:
    """Retire a peer's stale dial endpoint so the reconnect supervisor stops
    dialling a dead address (feature 100, FR-021).

    Use when a peer's recorded endpoint is known-wrong — it moved, its tunnel
    rotated, or it will not return — and the log shows repeated dial failures
    against it. The peer stays federated and keeps its trust material, chat
    setting and audit history; only the dial address is cleared. It reconnects
    automatically with no further action the moment it re-registers an endpoint
    by contacting this Border.

    Idempotent: forgetting an endpoint that is already absent succeeds.
    """
```

Returns the §2 shape via the existing `_gcf_dumps` serializer, matching all 38
existing tools.

**Why a tool and not a script** (FR-021/FR-026): the stale endpoint must be retirable
conversationally, without shell access or a database write.

---

## 5. Log line formats

The operator-facing contract. Line *shapes* are stable; thresholds are not.

### 5.1 Inbound arrival (new — FR-033)

```
[n2n.invocation] INFO  inbound n2n/tools/call from as65006-6.6.6.6 req=a1b2c3d4e5
```

Emitted at handler entry, before authorization. Carries the request identifier so a
call that never reaches a decision is still attributable (FR-033, FR-005).

### 5.2 Audit decision line (existing, enriched — FR-003/005/032)

Before (`audit.py:77-79`):

```
[n2n.audit] INFO  AUDIT[en2n] inbound as65006-6.6.6.6 skill/foo → allowlisted/success gait=3e19ac3098
```

After — same single line, `req=` added, level keyed to `outcome`:

```
[n2n.audit] INFO     AUDIT[en2n] inbound as65006-6.6.6.6 skill/foo → allowlisted/success req=a1b2c3d4e5 gait=3e19ac3098
[n2n.audit] WARNING  AUDIT[en2n] inbound as65099-10.255.255.1 skill/bar → not_allowlisted/denied req=f6g7h8i9j0 gait=7c21bd44f1
```

- Field order and existing tokens unchanged — anything grepping `AUDIT[` keeps working.
- `req=` omitted entirely when `request_id` is `None` (as `gait=` already is).
- `request_id` truncated to 10 characters, matching the existing `gait_ref[:10]`.
- **Exactly one line per audit write** (FR-032). No parallel logger.

### 5.3 Dead-peer failure summary (FR-008/009)

First failure of a new cause — logged immediately at `WARNING`, as today:

```
[n2n.service] WARNING  open_channel to as65099-10.255.255.1 failed: [Errno 111] Connect call failed
```

Subsequent identical failures collapse; every `SUMMARY_INTERVAL_S`:

```
[n2n.service] WARNING  as65099-10.255.255.1 unreachable: 14 failures in 5m0s (OSError:111), attempts=34, retry in 15m0s [dampened]
```

Carries attempt count and covered period (FR-009), current cause, and whether the
escalated ceiling is active (FR-014). One line per peer per interval (FR-016).

### 5.4 Benign pre-handshake disconnect (FR-017)

Before — a ~10-line `ERROR` traceback from the catch-all (`agent.py:498`). After, one
line, no traceback:

```
[bgp.agent] DEBUG  pre-handshake disconnect from 127.0.0.1: IncompleteReadError (0 bytes)
```

`DEBUG` because a zero-byte probe is never actionable (FR-020). A *complete but
invalid* magic value keeps its existing one-line `WARNING` (`agent.py:307`, FR-018),
and unexpected faults keep reaching the catch-all with a traceback (FR-019).

### 5.5 Probe summary (FR-038)

```
[bgp.agent] INFO  probe traffic: 47 non-protocol connections in 5m0s from 12 sources
```

Bounded regardless of scan volume. Structurally cannot mask an enrolled-device failure,
which is logged by `n2n.service` on a different path (data-model §5).

### 5.6 Suppressed stdlib warning (FR-030)

```
[asyncio] WARNING  returning true from eof_received() has no effect when using ssl
```

Dropped by a filter matching **this message only** (research R5). All other `asyncio`
warnings pass through unchanged — the filter matches on message text, never on level
or logger alone.

---

## 6. Backwards compatibility (Constitution XV)

| Surface | Guarantee |
|---|---|
| `N2N_RECONNECT_BACKOFF_MIN_S` / `_MAX_S` / `_UNREACHABLE_AFTER` | Unchanged meaning; still govern the non-dampened path. |
| `/n2n/health`, `/n2n/status` | Response shape unchanged. `dampened` is additive; existing fields keep names and types (FR-014). |
| HUD `/api/n2n` | No change required. Peer posture renders as today (research R9, Principle X deviation). |
| Existing 38 MCP tools | Untouched. One added, none altered. |
| `remote_invocation_record` | No schema change; no column's meaning changes (FR-027). |
| Wire protocol | Untouched (FR-029). No handshake, framing or trust change. |
