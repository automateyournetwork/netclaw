# Mac / Xcode handoff — spec 103

Paste the prompt at the bottom into Claude Code on the Mac. Everything above it
is context you may want to skim first.

---

## Where things stand

**Branch**: `103-ios-watch-heartbeat-delivery` (pushed). The Border/Linux half is
done and running on the WSL host. The iOS/watchOS half is untouched — that's your
side.

**The constraint that shapes everything**: there is no Apple Developer Program
membership, so **APNs is unavailable**. Not a config gap — a licensing one. iOS
suspends a backgrounded app's WebSocket and only a push can wake it, so *nothing*
can deliver to a backgrounded iPhone in real time. The Border side is already
built around this: undeliverable pushes persist and replay on reconnect. Don't
spend time trying to make APNs work; if you think you've found a way, that's
almost certainly the free-provisioning-profile trap (the free personal team does
not grant the Push Notifications capability).

**What already works, verified:**
- Slack heartbeat delivery — was dead ~15h, fixed, confirmed with a real send.
- The queue — undeliverable pushes persist, bounded, replay oldest-first.
- The 30m device heartbeat — delivers to Android via FCM, queues for iOS.
- Cross-channel alarm — the device heartbeat warns when Slack delivery is failing.

**What is NOT proven:**
- `defenseclaw-slack-watch.service` has not yet faced a real wipe. The wipe
  happens at **host boot**, and the restart that installed the watcher didn't
  trigger re-extraction. First reboot is the test. Check with
  `journalctl --user -u defenseclaw-slack-watch | grep -i wipe`.
- **The queue replay has never completed end-to-end.** There are pending rows for
  `risk/1785078347014` waiting for that phone to connect. Draining them is the
  first thing worth doing on the Mac, because it validates the whole Border half.

## The actual iOS problem

The phone holds its edge WebSocket for **18–57 seconds** and dies with
`no close frame received or sent` — an abrupt transport loss, not a clean close
and not a heartbeat-miss timeout (that would take 90s: 30s interval × 3 misses).

Observed twice:
```
13:22:17 Accepted edge WS dial-in (awaiting device auth)
13:22:35 Edge channel closed: no close frame received or sent   ← 18s
13:06:40 Accepted edge WS dial-in
13:07:37 Edge channel closed: no close frame received or sent    ← 57s
```

This has been happening long enough to be treated as normal — there's a comment
in `service.py` recording *94 dial-ins and 82 deregistrations in one day*. It may
be plain iOS backgrounding, but 18 seconds is short for that, and nobody has ever
looked at it with a debugger attached. That's what the Mac unlocks.

Note the log label is `n2n.edge[unauthenticated]` at close even though the Border
resolved the member ID — the channel logger just never gets relabelled after auth.
Cosmetic, but don't let it mislead you into thinking auth failed.

## Border-side facts you'll need

- Edge WS listener: port **8443**, `N2N_EDGE_WS_PORT` in `~/.openclaw/mesh.systemd.env`
- Liveness: `n2n/edge/heartbeat` every **30s**, closes after **3** misses
  (`NCFED_HEARTBEAT_INTERVAL` / `_MISS_LIMIT` in `bgp/constants.py`)
- Your phone's member: `risk/1785078347014` (`node_type='edge'`,
  `push_platform` NULL — that NULL is what routes to the queue)
- Android, for regression comparison: `risk/1785267858182` (`fcm`, delivers fine)
- Abandoned enrollment to ignore: `risk/1785077389894` (last seen Jul 28).
  Re-enrolling mints a **new** member_id, which is why six stale rows exist.

Useful commands on the Linux host:
```bash
curl -s http://127.0.0.1:8179/n2n/health | python3 -m json.tool   # edge_nodes[] has queue depth
sqlite3 ~/.openclaw/n2n/federation.db "select * from edge_message_queue;"
journalctl --user -u netclaw-mesh -f | grep -E 'edge|Replay|Queued'
python3 scripts/edge-heartbeat.py --dry-run                        # compose without sending
python3 scripts/edge-heartbeat.py --member risk/1785078347014      # push to just the phone
```

## Suggested order of work

1. **Drain the queue.** Build to a device from Xcode, foreground the app, watch
   `Replaying N queued message(s)` on the Linux host. This proves US1 end-to-end
   and is the cheapest possible win.
2. **Diagnose the 18s drop** with the console attached. This is the highest-value
   item — everything about the phone feeling "live" depends on it.
3. **Background refresh** (`BGAppRefreshTask`) → reconnect, drain, local
   notification. Explicitly best-effort; don't oversell it.
4. **Watch surface.** Only after the phone reliably has content to relay.

Don't start at 3 or 4. Without 1 and 2 they're decoration.

## One open question in the spec

US2 scenario 3 has a `[NEEDS CLARIFICATION]`: what's the target reconnect budget
after a drop — 5s or 30s? Worth deciding once you've seen how fast the reconnect
supervisor actually is in practice.

---

## Prompt to paste into Claude Code on the Mac

> I'm picking up spec `103-ios-watch-heartbeat-delivery` on my Mac — the iOS and
> watchOS half. The Linux/Border half is already done, running, and pushed on
> that branch; read `specs/103-ios-watch-heartbeat-delivery/spec.md` and
> `MAC-HANDOFF.md` in the same directory before doing anything, because they
> record findings that aren't obvious from the code.
>
> The hard constraint: **I have no Apple Developer Program membership, so APNs is
> off the table.** Please don't design around push notifications or suggest I buy
> a membership — the Border already implements a store-and-forward queue that
> replays to the phone on reconnect, and that's the delivery model.
>
> The app is Flutter at `mobile/netclaw-mobile/` with an iOS runner and an
> existing `WatchApp` watchOS target (specs 066–073, 099 built these — reuse
> `MessageFeedStore`, `ConversationStore`, `local_notifications.dart`,
> `reconnect_supervisor.dart`, don't rewrite them).
>
> Two things first, in this order:
>
> 1. Get the app running on my physical iPhone from Xcode and drain the queued
>    heartbeats waiting on the Border for member `risk/1785078347014`. I want to
>    see the replay land — that validates the whole Border half.
> 2. Then diagnose why the edge WebSocket dies after 18–57 seconds with
>    `no close frame received or sent`. It's been happening for months (94
>    dial-ins in one day is in the code comments as if it were normal) and nobody
>    has ever attached a debugger. I want to know whether that's iOS
>    backgrounding or a real bug in our client.
>
> The Border host is a separate Linux/WSL machine, so you can't reach its
> journal or database directly — tell me what to run there and I'll paste output
> back. I'm working with another Claude Code session on that side, so we can go
> back and forth.
>
> Ask me questions before writing code if the spec leaves something genuinely
> ambiguous.
