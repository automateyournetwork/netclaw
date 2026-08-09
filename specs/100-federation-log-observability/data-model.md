# Phase 1 Data Model: Federation Inbound-Call Observability

**Feature**: 100-federation-log-observability
**Date**: 2026-08-06
**Input**: [spec.md](./spec.md) Key Entities · [research.md](./research.md) R3, R7

**No database schema change.** Every persistent column this feature touches already
exists (`federation_peer.endpoint_host`, `endpoint_port`, `endpoint_updated_at`) and is
*cleared*, never added to. All new state is in-memory, consistent with how peer health
is held today.

---

## 1. Peer dial health — `FederationService.health[identity]`

The existing in-memory dict, extended. Today's shape (`service.py:82`) is:

```python
{"state": str, "attempts": int, "next_retry_at": float, "last_seen": float}
```

### Extended shape

| Field | Type | New? | Meaning |
|---|---|---|---|
| `state` | `str` | existing | `reconnecting` \| `up` \| `unreachable`. Unchanged vocabulary — the HUD already reads it (FR-014). |
| `attempts` | `int` | existing | Consecutive dial failures. **Reset semantics change** — see §1.2. |
| `next_retry_at` | `float` | existing | Epoch seconds; supervisor skips the peer until then. |
| `last_seen` | `float` | existing | Epoch seconds of last successful dial. |
| `connected_since` | `float` \| `None` | **new** | Epoch seconds the current channel came up, or `None` when down. Required by FR-031 — distinguishing "connected" from "connected and stayed up". |
| `cause_sig` | `str` \| `None` | **new** | Normalized signature of the most recent failure cause (§1.3). A change means log immediately rather than summarize (FR-015). |
| `suppressed` | `int` | **new** | Failures collapsed into the pending summary since `summary_at`. Reported by the summary, then zeroed (FR-009). |
| `summary_at` | `float` | **new** | Epoch seconds the last summary was emitted. `0` means none yet. |
| `dampened` | `bool` | **new** | Whether this peer is currently on the escalated ceiling. Exposed to the operator (FR-014). |

`state`, `attempts`, `next_retry_at` and `last_seen` keep their names and meanings so
`/n2n/health` and the HUD keep working untouched (FR-014, FR-027).

### 1.2 Reset semantics (FR-031) — the behavioral change

Today `open_channel` success overwrites health wholesale (`service.py:709-710`),
setting `attempts = 0` on *any* successful connect. Research R3 identified this as
what makes flapping defeat dampening entirely: a peer that connects and immediately
drops never accumulates failures.

New rule:

- On successful dial: set `state="up"`, `last_seen=now`, `connected_since=now`.
  **Do not clear `attempts`, `suppressed`, or `dampened`.**
- Dampening state is cleared only once the channel has been continuously up for
  `N2N_RECONNECT_STABLE_AFTER_S` — evaluated by the supervisor on a live channel,
  not at connect time.
- On endpoint change (FR-013): clear `attempts`, `dampened`, `next_retry_at`
  immediately, regardless of history. Detected by comparing the peer row's
  `endpoint_updated_at` against the value seen on the previous iteration.

This is the highest-risk change in the feature (plan.md "Primary implementation
risk") because it is the one that alters dial scheduling.

### 1.3 Failure cause signature (FR-015)

Raw cause strings are unstable — research R4 recorded live examples such as:

```
Multiple exceptions: [Errno 111] Connect call failed ('3.12.245.36', 15091), ...
```

whose IP ordering varies between attempts, so verbatim comparison would report a
"changed cause" on every attempt and defeat collapsing entirely.

`cause_sig` is therefore derived, not stored raw:

```
f"{type(exc).__name__}:{errno_or_empty}"
```

- Exception class name, plus the numeric `errno` when the exception carries one.
- No addresses, no ports, no message text — so ordering churn cannot change it.
- Deliberately coarse: `OSError:111` covers every "connection refused" regardless of
  which address in a multi-homed list refused first.

A different signature is treated as a materially different cause: log it at once and
restart the summary window.

---

## 2. Endpoint freshness — `federation_peer.endpoint_updated_at`

Existing column, no change. This feature adds two *readers* and one *clearer*.

| Consumer | Use |
|---|---|
| Dampening eligibility (FR-011) | A peer qualifies for the escalated ceiling only when `attempts >= N2N_RECONNECT_DEAD_AFTER` **and** `now - endpoint_updated_at > N2N_RECONNECT_ENDPOINT_STALE_S`. Two signals, per the spec's resolution of FR-010 vs FR-012. |
| Backoff reset (FR-013) | A change in this value resets backoff immediately. |
| `forget_peer_endpoint` (FR-021) | Set to `NULL` together with host and port. |

**Absent endpoint is already terminal for dialling.** `service.py:738-739` skips any
peer without `endpoint_host` or `endpoint_port`, which is the pre-existing mechanism
FR-023 relies on — clearing the endpoint stops dialling with no new code path.

**Null-handling rule**: a peer with an endpoint but `endpoint_updated_at IS NULL`
(possible for rows predating feature 063) is treated as **stale**, since the absence
of a freshness marker cannot demonstrate freshness.

---

## 3. Inbound invocation log event

Not a stored entity — the correlated sequence of operator-visible lines for one call.
The audit *row* is unchanged (FR-027); only what reaches the journal changes.

| Event | Emitter | Level | Trigger |
|---|---|---|---|
| **arrival** | `invocation.py` handler entry | `info` | Inbound call received, before authorization. New (FR-033) — makes a hung or abandoned call visible. |
| **decision + outcome** | `Auditor.record()` | `info` \| `warning` | Existing single line (`audit.py:77-79`), enriched. `warning` when `outcome == "denied"` (FR-003), `info` otherwise. |

Total per call: **two** lines — one arrival, one terminal. FR-032 forbids a third:
the decision line is enriched *in place*, never duplicated.

### 3.1 Denial severity mapping (FR-003)

Severity keys off `outcome`, not `decision`. Live taxonomy across
`bgp/federation/*.py`:

| `outcome` | Level | Count in source |
|---|---|---|
| `denied` | **`warning`** | 13 |
| `timeout` | **`warning`** | 3 |
| `error` | **`warning`** | 1 |
| `success` | `info` | 11 |
| `pending` | `info` | 7 |
| `submitted` | `info` | 3 |

`decision` is the wrong key: `not_allowlisted`, `approval_required`, `not_found`,
`out_of_scope` and `guardrail_blocked` all describe *why*, and all already resolve to
`outcome="denied"`. Keying off `outcome` needs one rule instead of a growing
denial-decision list that would drift as branches are added.

**FR-003 also forbids dampening denials.** Dampening in this feature is confined to
the reconnect supervisor and the inbound-accept path; the audit logger is never
dampened, so this holds structurally rather than by a guard.

---

## 4. Failure summary

Transient value, assembled at emit time from §1 and immediately discarded.

| Field | Source |
|---|---|
| peer identity | health key |
| suppressed count | `suppressed` (FR-009) |
| period covered | `now - summary_at` (FR-009) |
| current cause | `cause_sig` |
| consecutive failures | `attempts` |
| dampened / ceiling | `dampened` |

**Bounded volume as peers grow (FR-016)**: the summary is per-peer with a per-peer
`summary_at`, so N unreachable peers produce at most N lines per
`N2N_RECONNECT_SUMMARY_INTERVAL_S` — linear in peers, not in attempts, and each line
still names its own peer so "multiple peers affected" stays visible.

---

## 5. Probe dampening — `BGPAgent._probe_health[source_ip]`

New in-memory dict for FR-038. The edge listener is internet-reachable, so probe
volume is unbounded and continuous; per-connection logging cannot be bounded by
severity alone.

```python
{"count": int, "summary_at": float, "reason_sig": str}
```

Keyed by source IP, holding the same collapse-and-summarize shape as §1 with the same
`N2N_RECONNECT_SUMMARY_INTERVAL_S` cadence.

**Must stay distinguishable from a real edge failure (FR-038).** Enrolled-device
connection failures reach the daemon through a different path — the WebSocket edge
listener with an authenticated member — and are logged by `n2n.service`, not by the
BGP agent's protocol discrimination. Keeping probe summarization inside the agent's
pre-handshake path means it structurally cannot swallow an enrolled device's failure.

**Unbounded-key risk, accepted with a bound**: a scanner rotating source addresses
would grow this dict without limit. Capped at 512 entries, evicting the oldest
`summary_at` when exceeded — a scan is summarized either way, and the cap keeps a
log-noise fix from becoming a memory leak.

---

## 6. State transitions

```
                    ┌─────────────────────────────────────────┐
                    │  no endpoint  →  supervisor skips peer   │  FR-023
                    └─────────────────────────────────────────┘
                            ▲                        │
        forget_peer_endpoint│                        │endpoint recorded (FR-024)
                            │                        ▼
   ┌────────────┐  dial ok        ┌──────────┐  fails   ┌───────────────┐
   │reconnecting├────────────────►│    up    ├─────────►│ reconnecting  │
   └─────┬──────┘                 └────┬─────┘          └───────┬───────┘
         │                             │                        │
         │ attempts >= unreachable_after│ up >= STABLE_AFTER_S   │
         ▼                             ▼  → clear dampening      │
   ┌─────────────┐               (FR-031: NOT on connect)        │
   │ unreachable │◄────────────────────────────────────────────┘
   └──────┬──────┘
          │ attempts >= DEAD_AFTER  AND  endpoint stale   (FR-010/011)
          ▼
   ┌──────────────────────────┐
   │ unreachable + dampened   │  retry ceiling 900s, summary every 300s
   └──────────┬───────────────┘
              │ endpoint_updated_at changes  → immediate reset (FR-013)
              ▼
        reconnecting (attempts=0)
```

`up` and `unreachable` remain the only states the HUD and `/n2n/health` observe;
`dampened` is an additional flag on the same record, not a new state, so no existing
consumer needs to learn a new value (FR-014, FR-027).
