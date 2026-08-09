# Live Baseline (T001) — captured before any change

**Feature**: 100-federation-log-observability
**Captured**: 2026-08-06 19:09 EDT, host `DESKTOP`, `netclaw-mesh.service`
**Purpose**: SC-003 requires a ≥90% reduction in dead-peer log volume. That is
unmeasurable without a recorded before, so this file is a prerequisite, not a courtesy.

## Measured counts

| Signal | 7 days | Today | Last 10 min |
|---|---|---|---|
| `open_channel to … failed` (US2 target) | **23,366** | 772 | **0** |
| `Connection failed to …` (BGP FSM — out of scope) | — | 241 | 5 |
| `Error in _handle_incoming_connection` (US3 target) | 2 | 1 | 0 |
| `eof_received` (FR-030 target) | 12 | 2 | 0 |
| `Invalid N-magic` (FR-018 — must be preserved) | — | 0 | 0 |
| `AUDIT[` (US1 — already working, regression guard) | — | 28 | — |

## The dial storm, characterized

Today's 772 failures resolve to **exactly 193 per peer** across four peers:

| Peer | Failures today |
|---|---|
| `as65100-10.0.0.1` (Carapace) | 193 |
| `as65099-10.255.255.1` (Byrn) | 193 |
| `as65008-8.8.8.8` (Hermes) | 193 |
| `as65007-7.7.7.7` (Nicholas) | 193 |

Per-hour: 212 (11:00), 236 (12:00), 236 (13:00), 88 (14:00, partial).

**236/hour ÷ 4 peers ≈ 59 attempts/peer/hour — one attempt per peer every 60 seconds,
flat.** This is direct confirmation of research R3: `min(_backoff_min * 2**min(attempts,6),
_backoff_max)` saturates at `_backoff_max=60` and stays there forever. The uniformity
across four unrelated peers is the signature of a ceiling, not of peer behavior.

**FR-016 evidence**: volume scaled linearly with peer count (4 peers → 4× the lines).
Nothing bounds it as unreachable peers accumulate.

**FR-015 evidence**: the cause strings carry variably-ordered multi-address lists —

```
open_channel to as65099-10.255.255.1 failed: Multiple exceptions:
  [Errno 111] Connect call failed ('52.9.84.44', 24781),
  [Errno 111] Connect call failed ('13.52.204.76', 24781), … (6 addresses)
```

confirming that verbatim cause comparison would report a changed cause on nearly every
attempt and defeat collapsing. The normalized `OSError:111` signature
([data-model.md](./data-model.md) §1.3) is required, not a refinement.

## ⚠️ The defect is currently dormant — SC-003 needs a synthetic peer

The storm **stopped at 14:22:10 today** and the last-10-minutes count is `0`. This is
not a fix: it is the manual `UPDATE federation_peer SET endpoint_host='',
endpoint_port=NULL, endpoint_updated_at=NULL` performed while resolving the original
incident (research R7). Clearing the endpoints removed the *trigger*, because
`service.py:738-739` skips any peer without one.

Only one peer can be dialled at all right now:

| identity | state | endpoint | endpoint_updated_at |
|---|---|---|---|
| `as65006-6.6.6.6` (Nate) | federated | `netclaw.thirdlevel.ai:1179` | 2026-08-06T20:12:08Z |

…and it is healthy, so it never enters the failure path.

**Consequence for verification**: SC-003 cannot be demonstrated against the current live
state, because the live rate is already zero for reasons unrelated to this feature.
Verifying it requires **reintroducing a dead peer with a stale endpoint** as a
deliberate, reversible test — registering a bogus endpoint on an already-severed or
test identity, measuring, then forgetting it via the very `n2n_forget_endpoint` tool
US4 adds.

This also means the honest SC-003 comparison is **236 lines/hour/4-peers → target
≤23 lines/hour**, taken from the 11:00–14:00 window when the defect was active, not
from a post-clear window that would show a meaningless 0→0.

## Out-of-scope noise still present

`Connection failed to fd00:ee::0` continues at 5 per 10 minutes (241 today). This is
the BGP FSM dialling a configured peer with nothing listening — **configuration, not
code**, and explicitly excluded (spec.md Out of Scope). It is recorded here so it is
not mistaken for a US2 regression after the fix lands: US2's grep pattern
(`open_channel to … failed`) does not match it.

T047 must answer whether the dampening principle established here should also govern
BGP session retry reporting, since this is the identical defect shape.
