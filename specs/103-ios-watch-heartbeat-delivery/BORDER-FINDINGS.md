# Border-side findings for the iOS drop investigation

Observed on the Linux/WSL Border host, 2026-08-10 13:38–15:30. Written for the
Mac/Xcode session — this is evidence you cannot see from the phone side.

> **CONFIRMED 16:33 — the race is real, and the settle delay proves it.**
> Row 5 of the queue is the *same message* that timed out at 13:57 when it was
> dispatched 86ms after accept (`attempts=1` recorded that miss). On 2026-08-10
> at 16:33 it was dispatched **3.087s** after accept and delivered in under a
> second, along with four others:
>
> ```
> 16:33:35.870  Accepted edge WS dial-in
> 16:33:38.957  Replaying 5 queued message(s)   ← 3.087s after accept
> 16:33:39.951  AUDIT edge_push/queue_replay → pushed/success gait=f696e3b8fe
> ```
>
> Same message, same client, same method, same socket lifecycle — **failed at
> 86ms, succeeded at 3.087s.** The client drops inbound frames that arrive too
> soon after the WebSocket opens. This is now a measured fact, not a hypothesis.
>
> The Border-side settle delay makes queue replay reliable, but **the client fix
> is still required**: the nonce challenge in `accept_edge_ws()` is sent before
> the channel is even registered, so no server-side delay can protect it. The
> iPhone went a full hour (14:56:22 → 16:33:35) without authenticating while the
> Android authenticated repeatedly over the same network path — consistent with
> the same lost-first-frame defect hitting the challenge.

> **READ THIS FIRST — single root-cause hypothesis (added 15:30).**
> **The Dart client's receive loop starts too late after the WebSocket opens, so
> it misses the first inbound frame(s).** One bug explains every symptom below.
> See §"The convergence" — start there, not at the top.

## The convergence — one race explains all of it

`FederationService.accept_edge_ws()` does this, in this exact order:

```python
ch = EdgeChannel(ws, ...)
ch.nonce = nonce
await ch.notify("n2n/edge/challenge", {"nonce": nonce.hex()})   # ← FIRST frame, immediately
await ch.start()
logger.info("Accepted edge WS dial-in (awaiting device auth)")
```

**The very first thing the Border sends is an inbound notification the client
must already be listening for.** The device cannot authenticate until it receives
`n2n/edge/challenge` and signs the nonce back via `in2n/hello` (or
`in2n/enroll`). If the client's read loop or handler map isn't live the instant
the socket opens, that frame is gone and there is no retransmit — the connection
then sits in `awaiting device auth` forever and eventually disappears.

This single defect predicts all four observed symptoms:

| Symptom | Explanation |
|---|---|
| Connection stuck in `awaiting device auth`, no `auth_failure_bucket` row (15:23:51) | Missed the challenge frame. Never *failed* verification — never *attempted* it. |
| Queue replay timed out 30s after being dispatched 86ms post-accept (13:57:10) | Missed an early inbound `n2n/edge/message`. |
| Ordinary pushes on that *same* connection succeeded at 14:26 and 14:44 | Read loop was live by then. |
| Replay succeeded at 13:38:37 | Won the race that time. It is intermittent, not deterministic. |

**Where to look**: between "WebSocket open" and "read loop / handler map live" in
`edge_client.dart`. Anything `await`ed between those two points — secure-storage
reads for the enrollment key, `mobile_scanner` teardown, a `Future` chain before
subscribing to the socket stream — is a frame you can lose. The fix is to
subscribe to the inbound stream *before* anything else, and buffer whatever
arrives until handlers are ready.

**Empirical confirmation available**: `auth_failure_bucket` is **empty**. If the
client were sending a malformed or wrongly-signed `in2n/hello`, there would be a
row. There is no row, on any attempt. It is not an auth-credential problem.

### Border-side mitigation already shipped (does not remove the need for the fix)

`_flush_edge_queue()` now waits `N2N_EDGE_REPLAY_SETTLE_S` (default **3.0s**)
after channel registration before dispatching, and retries once after the same
delay before giving up. That covers the *replay* half of the race. It **cannot**
cover the auth half — the nonce challenge is sent before the channel is even
registered, so the client genuinely must listen first. Commit: see git log for
`fix(103)`.

## TL;DR — three things that should change your instrumentation

1. **The close reason is `keepalive ping timeout`, not a network drop.** The TCP
   connection stays open while the app stops answering. Instrument the event
   loop / app lifecycle, not the socket.
2. **"Dies in 18–57s" was wrong** — my earlier figure, over-generalized from two
   samples. It held **~30 minutes** on 2026-08-10 14:26→14:55 with two
   successful live pushes. Long holds happen.
3. **Some of the short drops I attributed to the iPhone were the Android device**
   (`risk/1785267858182`). Don't chase iOS-specific causes for those.

## US1 (queue replay) is validated — stop testing it

```
13:38:37,495  Accepted edge WS dial-in (awaiting device auth)
13:38:37,533  Replaying 2 queued message(s) to edge node risk/1785078347014
13:38:37,601  AUDIT[in2n] outbound edge_push/queue_replay → pushed/success gait=1b6ff92ba1
```

Both rows marked `delivered_at`. The Border half works end-to-end. Any later
non-zero queue count is **re-accumulation**, not failure — see the counting trap
below.

## The failure signature

```
14:26:10  AUDIT edge_push/text → pushed/success gait=95ac7c1fb5   ← live delivery
14:44:08  AUDIT edge_push/text → pushed/success gait=17fc4e3f7b   ← live delivery
14:54:48  WARNING risk/1785078347014: heartbeat failed (n2n/edge/heartbeat timed out)
14:55:48  WARNING risk/1785078347014: heartbeat failed (n2n/edge/heartbeat timed out)
14:55:50  Edge channel closed: sent 1011 (internal error) keepalive ping timeout;
          no close frame received
14:55:50  Edge node risk/1785078347014 channel closed — deregistered
```

Read that carefully: the app stopped answering **both** our application-level
`n2n/edge/heartbeat` *and* the `websockets` library's own protocol-level ping,
while the TCP connection remained established. A network drop or an OS-killed
socket would tear down the connection outright. This is the app's event loop
stopping — suspension, a blocked isolate, or a wedged read loop — with the
kernel socket outliving it. `1011` and the ping timeout are the **server**
giving up, not the client closing.

## A second, sharper instance: auth alive, dispatch dead

```
13:57:10,566  Accepted edge WS dial-in (awaiting device auth)
13:57:10,652  Replaying 1 queued message(s) to edge node risk/1785078347014
13:57:40,663  WARNING Queued replay failed (n2n/edge/message timed out)
              — 1 message(s) stay queued
```

86ms from TCP accept to authenticated + queue-replay dispatch — so the WS
handshake and the `in2n/hello` pinned-key proof both completed fine. Then the
very next JSON-RPC request got no answer for the full 30s timeout, **on a
brand-new connection**. That rules out "it was suspended earlier and the socket
went stale."

**This is the highest-value place for your `debugPrint`s**: straddle the boundary
between handshake/auth completion and the first inbound method dispatch. Whatever
services `in2n/hello` is working; whatever should service `n2n/edge/message`
isn't. Candidates worth checking: the receive loop not being restarted after
auth, a handler map registered too late, or the auth path being handled inline
while subsequent dispatch awaits something never completed.

Queue row 5 carries `attempts=1` — that failed replay is recorded, and it will be
retried on the next connect rather than lost.

## Relevant Border-side constants

| Thing | Value | Source |
|---|---|---|
| Edge WS port | `8443`, bound `0.0.0.0` | `N2N_EDGE_WS_PORT` |
| `n2n/edge/message` timeout | 30s | `service.py` `push_to_edge` / `_flush_edge_queue` |
| `n2n/edge/heartbeat` timeout | 30s | `service.py` `_edge_heartbeat_once` |
| Liveness interval / miss limit | 30s × 3 | `NCFED_HEARTBEAT_INTERVAL` / `_MISS_LIMIT` |
| Device heartbeat cadence | 30m | `netclaw-edge-heartbeat.timer` |
| Phone member | `risk/1785078347014` (`push_platform` NULL) | `federation.db` |
| Android (comparison) | `risk/1785267858182` (`fcm`) | `federation.db` |

## The queue-counting trap

`select count(*) from edge_message_queue` **cannot** tell you whether a drain
succeeded, because:

- delivered rows are pruned on the next enqueue (the queue is a delivery buffer,
  not an audit log — the audit trail is `remote_invocation_record` / GAIT), and
- a new heartbeat enqueues every 30 minutes while the phone is away.

Example: at 14:59 the count was `2` (rows 5 and 6, enqueued 13:56 and 14:56)
**even though** the 13:38 replay succeeded and the 14:26 heartbeat delivered live
and was pruned. Count alone would have read as total failure.

Query with timestamps instead:

```sql
select queue_id, attempts,
       datetime(enqueued_at,'unixepoch','localtime') as enqueued,
       coalesce(datetime(delivered_at,'unixepoch','localtime'),'PENDING') as delivered
from edge_message_queue where member_id='risk/1785078347014' order by queue_id;
```

For ground truth on delivery, use the audit trail, not the queue:
`journalctl --user -u netclaw-mesh | grep 'edge_push'`.

## Corrected copy-paste checks

The `grep -A5 '"1785078347014"'` in the earlier request never matches — the JSON
value is `"risk/1785078347014"`, so the leading quote breaks it (it exits 1
silently, which reads as "no such device"). Use:

```bash
curl -s http://127.0.0.1:8179/n2n/health | python3 -c "
import json,sys
for e in json.load(sys.stdin).get('edge_nodes',[]):
    print(f\"{e['member_id']}  connected={e['connected']}  state={e['state']}  queued={e['queued']}\")"
```

Live event stream while you test:

```bash
journalctl --user -u netclaw-mesh -f | grep -E 'Accepted edge|channel closed|Replay|stay queued|Queued undeliverable|heartbeat failed|edge_push'
```

## Two red herrings — don't waste time on these

- **`n2n.edge[unauthenticated]` in close messages.** The channel logger is never
  relabelled after successful auth, so every close logs as `unauthenticated`
  even when the member was fully authenticated and serving traffic. Cosmetic.
- **Failed handshakes on 8443.** Since ~14:57 there is a steady trickle of
  `InvalidUpgrade: missing Connection header`, `connection rejected (426 Upgrade
  Required)`, and `InvalidMessage: did not receive a valid HTTP request`. Port
  8443 is internet-exposed via the DDNS name, so this is consistent with
  background scanning. It is **not** correlated with a real dial-in (a genuine
  one logs `Accepted edge WS dial-in`). Source-IP capture is running on the
  Border to confirm; assume noise until told otherwise.

## Current state as of 15:05

- Phone `risk/1785078347014`: not connected, 2 pending (rows 5, 6). Last real
  dial-in 14:56:22; nothing since.
- Android `risk/1785267858182`: not connected, 0 pending, FCM push works.
- Every Border service active; Slack delivery healthy (0 failures since 13:27).
- **No dial-in attempts at all since 14:56**, so as of now the app is either not
  running or not reaching the Border.

## What would most help from the Mac side

1. Timestamped `debugPrint` at: WS open, handshake complete, `in2n/hello`
   sent/ack'd, receive-loop start, and **each inbound method dispatch by name**.
   The gap between `in2n/hello` ack and the first `n2n/edge/message` dispatch is
   the suspect.
2. Whether the app was foregrounded, backgrounded, or being redeployed during
   `14:54:48–14:55:50` — that distinguishes iOS suspension from a client bug.
3. Anything in the iOS console about the app being terminated, jetsammed, or
   its watchdog firing near those timestamps.
