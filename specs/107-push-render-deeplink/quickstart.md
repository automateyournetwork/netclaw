# Quickstart: verifying spec 107

**Feature**: 107-push-render-deeplink
**Date**: 2026-08-13

How to see the bug, and how to confirm each story fixed it. Written so a device
session — which on iOS costs a TestFlight round trip — is spent only on what
genuinely needs one.

---

## Reproduce the bug first (before any code changes)

Requires a Border on spec 106 or later and an enrolled phone.

```bash
# 1. Confirm the phone is disconnected, so the push takes the wake-signal path.
curl -s http://127.0.0.1:8179/n2n/health | python3 -c "
import json,sys
for e in json.load(sys.stdin).get('edge_nodes',[]):
    print(e['member_id'], 'connected=', e['connected'], 'queued=', e['queued'])"

# 2. With the app FULLY CLOSED, push a message.
curl -s -H 'Content-Type: application/json' \
  -d '{"member_id":"<member_id>","content_type":"text","content":"spec 107 repro"}' \
  http://127.0.0.1:8179/n2n/edge/push
#    Expect: "in_app_delivery": "pending_replay", "queued": true
```

3. **Tap the notification** on the phone.

**Current (broken) behavior**: the app opens to whatever screen it was last on.
The message appears in the Feed tab a few seconds later, but you were not taken
to it. That gap is Story 1.

Watch it from the Border side:

```bash
journalctl --user -u netclaw-mesh --since "2 min ago" | \
  grep -E 'authenticated|Replaying'
# Edge node … authenticated (source=…, 1 queued)
# Replaying 1 queued message(s) …          ← ~3s after auth; the tap already lost
```

That ~3s gap between auth and replay is precisely why a single store read at tap
time cannot succeed.

---

## Story 3 — no duplicates (P1, do this first)

Fully verifiable in the Dart suite; no device needed.

```bash
cd mobile/netclaw-mobile
flutter test test/message_feed_test.dart
```

Confirms: a second append with the same `pushed_at` is declined; the stored
entry's `read` state is untouched; two distinct messages both store; and
`wireMessageFeed` remains the only `n2n/edge/message` registration site.

> Do this before Story 2. Story 2 adds a second writer, and without dedup every
> message it persists will double when replay arrives.

---

## Story 1 — the tap opens the message (P1)

Most of it is verifiable without a device:

```bash
flutter test test/notification_deep_link_test.dart test/pending_open_intent_test.dart
```

Confirms: an intent resolves when the message arrives *after* the tap (the actual
bug); resolves immediately when already stored; expires within the bound and
falls back to the feed; opening the app without a tap forces nothing open.

**Then on a device** — this part cannot be faked:

1. Close the app fully. Push a message (commands above).
2. Tap the notification.
3. **Expect**: the app opens *to that message*.
4. Repeat with the app backgrounded rather than closed.

---

## Story 2 — renders without a live connection (P2)

```bash
flutter test test/push_message_ingest_test.dart
```

Confirms: a fully stringified payload reconstructs; a payload with a missing or
unparseable `pushed_at` is rejected without corrupting the store;
`content_type: 'approval'` routes to approvals and never the feed.

**On a device**, the case worth the trip is *no connectivity*:

1. Block the phone's route to the Border (airplane mode with wifi only, or a
   firewall rule dropping `:8443` from that address).
2. Push a message. The banner should still arrive — it comes via the push
   service, not the Border channel.
3. Open the app. **Expect**: the message is readable even though no live
   connection can be established.
4. Restore connectivity. **Expect**: exactly one copy of it, after replay
   delivers the same message again. This is the check that proves dedup and
   ingest work together, and it is the single most valuable device test in this
   feature.

---

## Whole-feature regression

```bash
cd mobile/netclaw-mobile
flutter test            # all suites
flutter analyze
```

And on the Border, confirm nothing regressed in delivery:

```bash
cd /path/to/netclaw
python3 -m pytest tests/n2n/ -q      # expect 445+ passed
```

That last one should be untouched — this feature makes no Border change. If it
moves, something is out of scope.

---

## What "done" looks like

| Story | Signal |
|---|---|
| 3 | 50 mixed-path messages → 50 feed entries, no duplicates (SC-005) |
| 1 | Tap opens the named message ≥95% of attempts, zero manual navigation (SC-001, SC-002) |
| 2 | Message readable with no Border connectivity at all (SC-004), within 2s of the app becoming interactive (SC-003) |
| all | No message the Border delivered is missing from the feed (SC-006) |
