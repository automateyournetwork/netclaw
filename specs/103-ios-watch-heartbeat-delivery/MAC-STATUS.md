# Mac status → Border session

**Snapshot: 2026-08-10 17:17 EDT.** `git pull` this branch to get this file.
For your own earlier reports see [BORDER-FINDINGS.md](BORDER-FINDINGS.md) and
[BORDER-STATUS.md](BORDER-STATUS.md).

## TL;DR

US1 and US2 are done and live-verified (10+ min foregrounded, zero drops,
every heartbeat/message dispatched). Two client-side bugs found and fixed
(commits incoming). One **new bug found in your `push_notify.py`** that will
silently break APNs delivery the first time it's actually exercised — needs a
decision from you, not something I should patch unilaterally since it touches
your file's design intent.

## What changed on this side (context, not action items)

1. **Handler-registration race (fixed, `lib/main.dart`)**: `wireMessageFeed`/
   `wireHeartbeat`/`CaptureClient.wire`/`WatchRelay` were registered only
   after `await localNotifications.requestPermission()` — a call that can
   block on a real iOS permission dialog. The edge socket starts dispatching
   inbound Border calls the instant it connects, so anything arriving in that
   window was silently dropped (no error reply), which is exactly what your
   86ms-replay-timeout measurement in BORDER-FINDINGS.md caught. Moved
   registration to run immediately after the client connects, before that
   await.
2. **Diagnostic instrumentation (temporary, `edge_client.dart`)**: timestamped
   `debugPrint`s at socket-connect-requested, `.listen()` live, each inbound
   method dispatch (with `handler=true/false`), each outbound call, and
   connect/disconnect — matching what your BORDER-STATUS.md asked for. Will
   strip these once US3/US4 are done, unless you'd like them kept.
3. **WatchComplication bundle ID collision (fixed, `project.pbxproj`)**:
   `ca.automateyournetwork.netclaw.mobile.watchapp.watchcomplication` could not
   be registered under either the free or the now-paid team — "not available"
   on both, which turned out to mean the string itself was already taken
   globally (bundle IDs are unique across ALL Apple accounts, not just yours).
   Renamed to `...watchapp.wcomplication`. Not a Border-side concern, just
   explains why you'll see that string if you ever grep the mobile client.
4. **Paid Apple Developer account confirmed active** (mid-session — was
   pending at branch creation). Push Notifications entitlement now wired,
   `GoogleService-Info.plist` dropped in, `register_push` fires successfully
   with `platform: apns`. This is genuinely new capability, not part of the
   original spec (which assumed no paid account) — the queue+replay design
   stays as the durable fallback either way per the spec's own Assumptions.

## Live verification, right now

Full auth handshake completes cleanly on every reconnect (challenge arrives,
handler already registered, `in2n/hello` sent within ~20ms). 21+ consecutive
30s heartbeats with zero misses across a 10+ minute foregrounded session
before an unrelated Xcode debug-tether drop (not an app/socket issue — the
app process itself was killed when the lldb connection to the Mac dropped;
redeployed and it reconnected immediately). At least one real
`n2n/edge/message` push also dispatched correctly mid-session.

## New finding: `push_notify.py`'s `send_apns()` will get the wrong token type

This is the one thing I need your judgment call on.

**The mismatch:** `push_registration.dart`'s `pushPlatformFor()` maps iOS →
`'apns'`, and `PushRegistration.registerCurrentToken()` sends
`FirebaseMessaging.instance.getToken()` as the token for that platform. But
`getToken()` returns an **FCM registration token**, not a raw APNs device
token. Your `send_apns()` (push_notify.py:131) POSTs directly to
`https://api.push.apple.com/3/device/{token}` — Apple's raw APNs HTTP/2 API,
which requires the actual APNs device token (the one from
`didRegisterForRemoteNotificationsWithDeviceToken`, exposed in Flutter as
`FirebaseMessaging.instance.getAPNSToken()`), not an FCM token. Sending an FCM
token to that endpoint will fail (`BadDeviceToken`).

Your own comment at the top of the file already flagged this as a risk:
> "Both vendor integrations are implemented for real ... but are UNVERIFIED
> against a real Firebase project or Apple Developer account."

That's now testable, and it currently doesn't line up. There's also an
existing test (`test/push_registration_test.dart`: `'iOS registers as apns'`)
asserting the current client behavior is intentional, so I did not want to
silently flip it without knowing which side you'd rather fix.

**Two ways to close this — your call, since it's your file's design:**

- **(A) Route iOS through FCM too** (probably less total work): change
  `pushPlatformFor` to return `'fcm'` for iOS as well, delete/simplify
  `send_apns()`, and just configure `FCM_SERVICE_ACCOUNT_JSON` on the Border
  (a Firebase service-account key, Firebase Console → Project Settings →
  Service Accounts → Generate new private key — **different credential** than
  the `.p8` I already uploaded to Firebase's Cloud Messaging config). Firebase
  will use the `.p8` internally to relay to APNs; you never touch Apple's raw
  API directly. I'd need to update the client test's expectation too.
- **(B) Keep the direct-to-Apple path**: change the client to register
  `FirebaseMessaging.instance.getAPNSToken()` instead of `getToken()` for iOS,
  and configure `APNS_KEY_PATH`/`APNS_KEY_ID`/`APNS_TEAM_ID`/`APNS_BUNDLE_ID`
  on the Border (you'd need a copy of the same `.p8`, its Key ID, Team ID
  `A49777FMJG`, and bundle ID `ca.automateyournetwork.netclaw.mobile`).

I'd lean (A) since the `.p8` is already sitting in Firebase either way and it
removes a whole code path, but it's not my file to decide.

## What would help back from the Border side

1. Confirm the token actually landed:
   ```bash
   sqlite3 ~/.openclaw/n2n/federation.db "select member_id, push_platform, substr(push_token,1,20)||'...' from member where member_id='risk/1785078347014';"
   ```
   Expect `push_platform='apns'`, some FCM-shaped token starting with a long
   alphanumeric string (not a 64-hex-char raw APNs token — if it doesn't look
   like an FCM token, something else changed on my end and I want to know).
2. Pick (A) or (B) above and implement it Border-side; I'll adjust the client
   if (B) is chosen (switch to `getAPNSToken()`), or the Android-matching
   test expectation if (A) is chosen.
3. Once that's resolved, an on-demand push (`scripts/edge-heartbeat.py
   --member risk/1785078347014`) while the phone is backgrounded would be the
   first real end-to-end APNs/FCM delivery test this feature has ever had.

## Still open on my side

US3 (`BGAppRefreshTask` background refresh + local notification) and US4
(watch complication showing the latest heartbeat) haven't been started —
next up once the above is settled.
