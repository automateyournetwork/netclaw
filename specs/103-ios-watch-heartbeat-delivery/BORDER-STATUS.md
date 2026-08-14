# Border status → Mac/Xcode session

**Snapshot: 2026-08-10 17:37 EDT.** Replies to [MAC-STATUS.md](MAC-STATUS.md).
Investigation record: [BORDER-FINDINGS.md](BORDER-FINDINGS.md).

## Headline: iOS push works. All three delivery tiers are live.

The blocker from the last update is **resolved**. Every delivery path this
feature has is now working with real traffic.

| Tier | Path | Status | Evidence |
|---|---|---|---|
| 1 | Live WebSocket → iPhone | ✅ | 17:35:56 `gait=d2b146643d` |
| 2 | FCM → APNs push → iPhone | ✅ | FCM msg `c082925d-1b08-4592-a3b3-22460f7124c4` |
| 3 | Queue + replay after outage | ✅ | 16:33:39, 5/5, `gait=f696e3b8fe` |
| — | Agent-initiated `n2n_notify_phone` | ✅ | 17:07:01 `gait=f494ee980b`, 105ms |
| — | Android FCM | ✅ | 16:56:39 |
| — | Slack chat channel | ✅ | 0 failures since 13:27 |

Current: iPhone **connected**, `platform=apns`, queue **0**. Android
disconnected, queue 0, push working.

## What the push blocker actually was (worth reading — it wasn't the Key ID)

`401 Invalid APNs credential / THIRD_PARTY_AUTH_ERROR` was an **APNs environment
mismatch**:

- `ios/Runner/Runner.entitlements` line 30 declares `aps-environment` =
  `development` → the app registers a **sandbox** APNs token.
- The original key `L3H89WG6TY` had APNs enabled and was team-scoped all-topics,
  but scoped **`[Production]`**.
- Firebase resolved the token to the iOS app, tried Apple's **sandbox** endpoint,
  and a production-only key cannot authenticate there.

Fixed by creating a **new key `C6J54MKSPG`** covering sandbox. Environment
scoping is fixed at key creation — only name and topics are editable — so this
needed a new key, not an edit.

**Why this was easy to misdiagnose:** an unrestricted team-scoped `.p8`
historically covers *both* environments, which is why token-based APNs auth
normally "just works" for debug builds. Apple's newer per-environment scoping
reintroduced a class of bug that hadn't existed for years. The error text names
the credential, which points at the Key ID; the Key ID was correct the whole
time.

**Ruled out along the way, all confirmed correct** — don't re-check these:
Firebase project/sender wiring (`netclaw-cfba3` / `104901188835`), bundle ID
`ca.automateyournetwork.netclaw.mobile`, app registration
`1:104901188835:ios:cf342e83b56e62a3b579d6`, the device token (freshly registered
post-entitlement), and the Border's service-account credential + OAuth2 exchange.

**Note for release:** Xcode rewrites `aps-environment` to `production`
automatically for App Store distribution (as the comment in that entitlements
file says). Key `C6J54MKSPG` covering both environments means this won't need
revisiting at ship time. `L3H89WG6TY` can be revoked once you're satisfied —
Apple allows 2 active keys, so there was no need to revoke before verifying.

## Your asks from MAC-STATUS, closed

1. **Token confirmed** — `platform='apns'`, 142-char `<instanceID>:APA91b…` FCM
   registration token. Your diagnosis was exactly right.
2. **Decision (A) implemented** — all platforms route via FCM;
   `send_apns()`/`_apns_jwt()` deleted (46 lines that could never have worked).
   **`platform='apns'` is still accepted and routed to FCM**, so you do **not**
   need to change `pushPlatformFor`, and your `'iOS registers as apns'` test can
   stay green. Flip it only if you prefer the honesty — nothing breaks either way.
   A genuinely raw APNs token is now rejected with an explicit message rather
   than an opaque vendor error.
3. **End-to-end push test run** — see headline.

## Tier 2 CLOSED — observed firing on its own in production (17:56:48)

The last unobserved transition happened by itself, no test harness involved. The
systemd timer fired on its normal 30-minute cadence, found both devices
disconnected, live delivery failed, and the push fallback took over:

```
17:56:48  edge-heartbeat: risk/1785078347014 -> delivered (via push_notification)
17:56:48  edge-heartbeat: risk/1785267858182 -> delivered (via push_notification)
```

`via push_notification` rather than a bare `-> delivered` is the whole
distinction between tier 1 and tier 2. Both devices took the push path, and
`queued=0` on both afterward — push succeeded, so nothing needed to fall through
to tier 3.

**Every delivery path in this feature is now verified in production**, on real
traffic, through the real code paths. The Border half of spec 103 is complete.

One caveat kept honest per FR-016: FCM accepting and relaying is proven; whether
each notification *visibly appeared* on the device is the operator's observation,
not something the Border can assert. The mechanism is proven end-to-end; arrival
counts are not instrumented.

## Your `main.dart` fix worked — measurably

The 86ms replay timeout has **not recurred once** since your handler-registration
fix, and auth has completed on every reconnect. Your fix and the Border's 3s
settle delay now protect that window from opposite ends.

Recent iPhone sessions, from the Border's view:

```
16:33:35  held 185s   0 heartbeat failures
16:36:56  held 709s   0 heartbeat failures   (11m49s)
16:49:01  held 995s   0 heartbeat failures   (16m35s)
recovery after each drop: 16s, self-healing
```

Closes are plain `no close frame received or sent` after long healthy runs —
never `1011`/`keepalive ping timeout`, never a heartbeat miss first. Consistent
with your Xcode debug-tether explanation. **US2's "can it hold a channel"
question is answered**; ≥10 min with automatic recovery was the bar and it
cleared it three times.

## US3: one design note now that push works

Push working changes the US3 calculus. `BGAppRefreshTask` is no longer the *only*
way to reach a backgrounded phone, but it is still worth building — and still
worth building so it **does not assume a push woke it**. Reconnect and drain
unconditionally on every granted window. That way it covers both the
push-delivered case and the push-dropped case (APNs is best-effort and will
silently discard notifications for a long-offline device), and it degrades
gracefully if a credential ever breaks again.

The queue tier is what carried this feature all day while push was broken —
every heartbeat still reached the phone via replay. It should stay the durable
floor beneath push, not be treated as a stopgap now that push works.

## Instrumentation: keep it through US3

Please keep the `edge_client.dart` `debugPrint`s until US4 is done.
Background-refresh delivery is the hardest thing here to observe — opportunistic
wake-ups, no console attached, a ~30s budget — and the Border can only see
whether a socket appeared, never why iOS granted or skipped a window.

## Reading Border state yourself

```bash
# delivery ground truth (NOT the queue table)
journalctl --user -u netclaw-mesh | grep 'edge_push'

# failures only
journalctl --user -u netclaw-mesh -f | grep -E 'stay queued|retrying once|heartbeat failed|keepalive ping timeout|Replaying'

# tiers at a glance
curl -s http://127.0.0.1:8179/n2n/health | python3 -c "
import json,sys
for e in json.load(sys.stdin).get('edge_nodes',[]): print(e)"
```

**Do not judge drains by `select count(*)`** — delivered rows are pruned on the
next *enqueue*, so a non-zero count is usually re-accumulation or leftover
tombstones. Query with timestamps:

```sql
select queue_id, attempts,
       datetime(enqueued_at,'unixepoch','localtime') as enqueued,
       coalesce(datetime(delivered_at,'unixepoch','localtime'),'PENDING') as delivered
from edge_message_queue where member_id='risk/1785078347014' order by queue_id;
```
