# Feature Specification: iPhone / Apple Watch Heartbeat Delivery

> Originally titled "…Without APNs". **That premise was overtaken by events on
> the day it was written** — a paid Apple Developer membership went active
> mid-implementation and iOS push now works (see Assumptions). The design is
> unchanged and none of it was wasted: push became the tier *above* the
> store-and-forward queue, exactly as the original wording anticipated, and the
> queue carried every heartbeat to the phone during the ~4 hours push was
> misconfigured. Passages below still argue from "APNs is impossible" — they are
> left intact as the reasoning of record, with amendments marked inline.

**Feature Branch**: `103-ios-watch-heartbeat-delivery`
**Created**: 2026-08-10
**Status**: **COMPLETE.** Border half verified (all three delivery tiers live,
incl. the boot-time Slack-watcher wipe caught in production 2026-08-11
06:49:25). iOS/watchOS half: US1/US2 live-verified; US3/US4 code-complete and
unit-tested, closed without a live-fire/on-screen confirmation (Apple tooling
friction, not a code defect — see "Already Landed"). FR-017 closed 2026-08-11
with three amendments (FR-017a/b/c) found during implementation.
**Input**: User description: "get my NetClaw all up and running and confirmed — I haven't got a heartbeat in a while — I have a mobile netclaw (risk/1785078347014) that SAYS it's connected, is it? Also let's get the HEARTBEATS for the iPhone / Apple Watch working."

## Context: what was actually wrong

Investigated 2026-08-10. Three independent faults, only the first of which was
the reported symptom:

1. **Slack heartbeat dead ~15h** (Aug 9 22:34 → Aug 10 13:27). DefenseClaw's
   fetch-interceptor false-positives `slack.com/api/chat.postMessage` as an LLM
   call (`/api/chat` is an Ollama path suffix matched with `.includes()`), proxies
   it to the guardrail sidecar, and the sidecar 403s it as
   `BLOCKED passthrough to unknown domain`. Known issue with a known one-line
   fix (`KNOWN_SAFE_DOMAINS`), but the existing `ExecStartPre` guard had become
   structurally incapable of applying it — see FR-001. **Fixed and verified.**
2. **The phone was not connected**, despite the app reporting that it was. It
   holds an edge WebSocket for 18–57s and drops with
   `no close frame received or sent`. `state` in `federation.db` was
   `unreachable`.
3. **Heartbeats were never wired to devices at all.** OpenClaw's built-in
   `agents.defaults.heartbeat` (30m) delivers only to the configured chat
   channel. Nothing in the codebase pushed heartbeat content to an enrolled
   edge node, so "get the heartbeats working on iPhone" was new capability, not
   a repair.

**The hard constraint as understood at authoring time** (confirmed with the
operator): there is no Apple Developer Program membership, so APNs cannot be used
— not as a configuration gap but as a licensing one. Since iOS suspends a
backgrounded app's WebSocket and only a push can wake it, no mechanism can
deliver to a backgrounded iPhone in real time. This spec deliberately designs
around that rather than pretending otherwise.

> **AMENDED 2026-08-10 17:35 — the constraint lifted the same day.** A paid
> membership activated mid-implementation and **iOS push now works** (FCM message
> `c082925d-1b08-4592-a3b3-22460f7124c4`). Two corrections to the paragraph
> above, both worth knowing:
>
> 1. `push_notify.send_apns()` did not merely lack credentials — it was
>    **unusable by construction**. It posted to Apple's raw
>    `api.push.apple.com/3/device/{token}`, which needs the APNs device token,
>    while the client registers an FCM registration token. It could only ever
>    have returned `BadDeviceToken`. Deleted unexecuted; iOS now goes through FCM,
>    which relays to APNs (decision A).
> 2. Getting a membership was **not sufficient**. Push stayed broken for hours
>    afterward on an APNs *environment* mismatch: the app declares
>    `aps-environment=development` (sandbox) while the first key was scoped
>    `[Production]`. Fixed by a new key covering sandbox. Hence the FR-016
>    amendment — holding a credential is not evidence of delivery.
>
> The design consequence is nil: the queue was always specified as the durable
> floor with push as a tier above it, and that is what shipped.

## User Scenarios & Testing

### User Story 1 - Heartbeats survive a channel that is usually down (Priority: P1)

The operator's phone is connected for well under a minute at a time. A 30-minute
heartbeat aimed at it will almost always find it gone. Rather than dropping
those pushes (previous behavior: `delivered: false`, content discarded), the
Border persists them and replays them the moment the device reconnects, so
opening the app shows the heartbeats that were missed, oldest first.

**Why this priority**: This is the only delivery path that works at all without
APNs, so everything else in the feature is decoration without it. It also fixes
a silent data-loss bug that existed independently of iOS.

**Independent Test**: Push while the phone is disconnected, confirm the row
lands in `edge_message_queue`, then connect the phone and confirm the content
arrives and the row is marked delivered.

**Acceptance Scenarios**:

1. **Given** an enrolled edge node with no live channel and no usable push
   transport, **When** the Border pushes content to it, **Then** the content is
   persisted with the reason it could not be delivered, and the caller is told
   `queued: true` with the resulting depth rather than a bare failure.
2. **Given** queued messages for a device, **When** that device's channel comes
   up, **Then** every queued message is delivered oldest-first, marked
   `replayed` with its original timestamp, and cleared from the queue.
3. **Given** a device that drops mid-replay, **When** the channel closes, **Then**
   the undelivered remainder stays queued for the next connect and nothing is
   lost or double-delivered.
4. **Given** a device that has been unreachable for weeks, **When** heartbeats
   continue firing, **Then** the queue does not grow without bound (depth cap
   and TTL both enforced) and the newest content is what survives.

---

### User Story 2 - The iPhone holds its channel long enough to be useful (Priority: P1)

The edge WebSocket currently dies after 18–57 seconds with no close frame. The
operator's own code comments record 94 dial-ins and 82 deregistrations in a
single day, so this has been treated as normal — but it is the difference
between "heartbeats arrive when I open the app" and "heartbeats arrive while I
am using the app." **This requires a Mac with Xcode to diagnose**, because the
cause is on the device side and needs the iOS console/debugger to see.

**Why this priority**: Equal-P1 with US1 because US1's replay is only a
consolation prize; a channel that stays up while the app is foregrounded is what
makes the phone feel live. It is separated from US1 because it is independently
testable and lands on different hardware.

**Independent Test**: Run the app from Xcode on a physical device, foreground it,
and confirm the channel survives ≥10 minutes of continuous foreground use with
Border-side heartbeats succeeding throughout.

**Acceptance Scenarios**:

1. **Given** the app is foregrounded on a physical iPhone, **When** it connects
   to the Border, **Then** the channel stays up for at least 10 minutes without
   an unsolicited close.
2. **Given** the app is foregrounded, **When** the Border runs its 30s
   `n2n/edge/heartbeat` liveness call, **Then** the call succeeds and
   `member.health.last_heartbeat` advances.
3. **Given** the channel does drop, **When** the app is still foregrounded,
   **Then** the reconnect supervisor re-establishes it within **30 seconds**
   without operator action. Resolved 2026-08-11 from real observation, not a
   guess: three live foregrounded sessions on the Mac/Xcode build (185s,
   709s, 995s held) each recovered from a drop in 16s, self-healing, via
   `ReconnectSupervisor`'s existing 5s-initial backoff — comfortably inside
   this budget with margin for a slower network.
4. **Given** the app is backgrounded and later foregrounded, **When** it
   resumes, **Then** it reconnects and drains its queue without requiring a
   force-quit or re-enrollment.

---

### User Story 3 - Opportunistic background delivery without APNs (Priority: P2)

Since no push can wake the app, the app itself asks iOS for periodic background
execution, and uses each grant to reconnect briefly, drain the queue, and raise
a *local* notification for anything it collected. Delivery is best-effort and
scheduled at the OS's discretion — minutes to hours, never guaranteed — and the
spec must not claim otherwise.

**Why this priority**: P2 because it is genuinely unreliable by construction. It
converts "you see heartbeats when you open the app" into "you often see them
without opening the app," which is a real improvement but cannot be depended on.

**Independent Test**: With the app backgrounded, trigger a background refresh
from Xcode's debug menu and confirm the queue drains and a local notification
appears.

**Acceptance Scenarios**:

1. **Given** queued messages and a backgrounded app, **When** iOS grants a
   background refresh, **Then** the app connects, drains the queue, posts one
   local notification summarizing what arrived, and returns before its budget
   expires.
2. **Given** the app has no queued messages, **When** a background refresh is
   granted, **Then** it completes without posting a notification and without
   holding the connection open.
3. **Given** iOS never grants a refresh, **When** the operator opens the app,
   **Then** behavior is identical to US1 (full replay on foreground) with no
   duplicate notifications for already-seen content.

---

### User Story 4 - The heartbeat reaches the wrist (Priority: P3)

The Apple Watch companion surfaces the latest heartbeat — status line and any
alarm — without the operator taking out their phone. The watch has no
independent path to the Border; it renders what the phone relays over
WatchConnectivity, consistent with spec 072.

**Why this priority**: P3 because it depends on US1–US3 delivering to the phone
first. Valuable but strictly downstream.

**Independent Test**: With a heartbeat delivered to the phone, confirm the watch
app and complication show the current status without opening the phone app.

**Acceptance Scenarios**:

1. **Given** a heartbeat has arrived on the phone, **When** the operator raises
   their wrist, **Then** the watch shows the latest status summary and its age.
2. **Given** a heartbeat carries the Slack-delivery alarm (FR-010), **When** it
   reaches the phone, **Then** the watch surfaces it distinguishably from a
   routine heartbeat.
3. **Given** the phone is unreachable from the watch, **When** the operator
   opens the watch app, **Then** it shows the last-known status and its age
   rather than an empty or misleading view.

---

### User Story 5 - Neither notification channel can go silent unnoticed (Priority: P2)

The Slack outage was invisible for ~15 hours because the agent stayed healthy,
`openclaw channels status` reported `connected, health:healthy` throughout
(inbound Socket Mode was fine), and only outbound delivery failed. Nothing
retried and nothing alerted. Because the device path is a different transport,
each channel is positioned to report on the other's health.

**Why this priority**: P2 — it prevents recurrence of the exact failure that
prompted this work, and two real findings (a BGP peer down since Aug 4, a
stopped CML lab) sat undelivered inside blocked payloads.

**Independent Test**: Break Slack delivery deliberately, wait for one device
heartbeat, and confirm the phone heartbeat carries the warning.

**Acceptance Scenarios**:

1. **Given** Slack heartbeat deliveries have failed in the recent window,
   **When** the device heartbeat is composed, **Then** it includes an explicit
   warning naming the failure count and the command to diagnose it.
2. **Given** Slack delivery has been healthy for the full window, **When** the
   device heartbeat is composed, **Then** no warning is included.
3. **Given** the DefenseClaw patch is wiped, **When** it is re-applied
   automatically, **Then** the event is recorded in the journal in a way that
   distinguishes "was intact" from "caught a real revert".

### Edge Cases

- **Re-enrollment mints a new `member_id`.** Scanning the QR again creates a new
  row, leaving the old one enrolled forever. Six such rows already exist. Pushes
  must not be queued for abandoned enrollments, and the operator needs a way to
  retire them.
- **`/n2n/faults` reports phones as downed members.** Edge nodes carry no agent
  runtime, so a naive summary read "3 members down" when all four real members
  were up. Any status composition must separate `node_type='edge'` from agent
  members.
- **`state` alone is misleading on a phone.** It is written on connect/disconnect
  and a phone reconnects constantly, so two reads seconds apart can honestly
  disagree. Heartbeat age, not `state`, distinguishes "between sockets" from
  "gone".
- What happens when the same content would be delivered twice — once by a
  background refresh and once by a foreground replay?
- What happens when the queue is replayed to a device whose clock is far off?
- What happens if the operator obtains an Apple Developer account later — does
  the queue become dead code, or the durable fallback beneath APNs?

## Requirements

### Functional Requirements

- **FR-001**: The DefenseClaw Slack passthrough patch MUST be re-asserted by a
  mechanism that runs *after* DefenseClaw re-extracts its vendored extension
  directory. An `ExecStartPre` hook is insufficient and MUST NOT be relied on:
  measured 2026-08-10, the guard patched at `10:55:35` and the file was
  overwritten at `10:55:36.87`, every start, while the guard logged success.
- **FR-002**: The system MUST NOT rely on the running gateway re-reading the
  interceptor file. It is imported once at startup (observed
  `LLM fetch interceptor active` ~16s in) and never re-read, so a patch applied
  after that point has no effect until the next restart.
- **FR-003**: Content pushed to an edge node that can be reached neither live
  nor by platform push MUST be persisted and replayed on next connect, rather
  than discarded.
- **FR-004**: The queue MUST be bounded by both a per-device depth cap and a
  TTL, evaluated on every enqueue, and MUST discard oldest-first on overflow.
- **FR-005**: Replayed content MUST be marked as replayed and carry its original
  enqueue time, so the device can render history as history.
- **FR-006**: A replay interrupted by the device disconnecting MUST leave the
  undelivered remainder queued, and MUST NOT redeliver what already arrived.
- **FR-007**: Queue depth per device MUST be observable from the daemon's HTTP
  surface so a growing backlog is visible rather than implicit.
- **FR-008**: A periodic device heartbeat MUST be delivered on a cadence
  matching the chat-channel heartbeat, composed from the daemon's own state, and
  MUST NOT depend on the agent model choosing to call a tool.
- **FR-009**: Device heartbeat composition MUST exclude `node_type='edge'`
  members from agent-member health counts.
- **FR-010**: The device heartbeat MUST report recent chat-channel delivery
  failures, so an outbound-only outage on the other channel is surfaced.
- **FR-011**: Pushes MUST be skipped for devices that are neither connected nor
  push-capable and have not been seen within a staleness window.
- **FR-012**: The iOS app MUST hold its edge channel for the duration of
  foreground use, and MUST reconnect automatically after a drop without
  operator action.
- **FR-013**: The iOS app MUST request opportunistic background execution and
  use each grant to drain its queue and post a local notification for new
  content.
- **FR-014**: The iOS app MUST NOT post duplicate notifications for content it
  has already surfaced, across background-refresh and foreground-replay paths.
- **FR-015**: The watch companion MUST display the latest heartbeat and its age,
  and MUST visually distinguish an alarm-bearing heartbeat from a routine one.
- **FR-016**: The system MUST NOT claim real-time delivery to a backgrounded
  iOS device until a push has actually been observed arriving on a backgrounded
  device. Amended 2026-08-10: the original wording conditioned this on "while no
  APNs credential exists", which a paid membership satisfied on paper while
  delivery was still broken (`Invalid APNs credential` from FCM). Possessing a
  credential is not evidence of delivery; an observed arrival is.
- **FR-017**: The operator MUST be able to retire an abandoned edge enrollment
  without editing the database by hand. **DONE 2026-08-11** —
  `scripts/edge-enrollments.py` (list / `--retire` / `--retire-stale`), which
  mutates only through the daemon's `/n2n/members/remove` route so channel
  teardown, key unpinning, queue purging and the audit trail all happen the
  normal way. Amended during implementation, having found three real gaps:
  - **FR-017a**: Retiring an enrollment MUST purge its queued messages. Rows are
    keyed by `member_id` and a re-enrolled device gets a new one, so a retired
    device's backlog would otherwise be unclaimable until the TTL reaped it.
    (`EdgeQueue.purge_member()`; before this, clearing it required `sqlite3` —
    precisely what this requirement forbids, and what the author actually did on
    2026-08-10.)
  - **FR-017b**: Retiring an enrollment MUST close its live channel whichever
    registry holds it. `/n2n/members/remove` popped only `member_channels`; an
    edge node's channel lives in `edge_channels` (feature 066), so retiring a
    *connected* phone left it open and serving traffic.
  - **FR-017c**: Retiring a non-abandoned enrollment MUST require an explicit
    override. Removal is irreversible — it NULLs the pinned key and deletes the
    key file, forcing a re-enrol under a new `member_id`. A guard keyed on
    "currently connected" is insufficient: a phone flaps constantly and reads
    disconnected most of the time while being entirely live. **This was learned
    the hard way** — on 2026-08-11 a `--retire` expected to be refused destroyed
    the then-current enrollment `risk/1786470797502`, because it happened to be
    between sockets. Staleness, not connectedness, is the safe test, and
    `--force` is now required for anything inside the staleness window.

### Key Entities

- **Edge message queue entry**: one undeliverable push — target device, the
  exact payload, why it could not be delivered, when it was enqueued, how many
  delivery attempts it has survived, and whether it has been delivered.
- **Edge node (existing, `member` with `node_type='edge'`)**: gains no new
  columns in this feature. Its `push_platform`/`push_token` stay NULL for an
  iPhone with no APNs credential — that NULL is the condition that routes
  delivery to the queue.
- **Device heartbeat**: a composed status summary — identity, posture, peer and
  agent-member counts, notable faults, cross-channel delivery warning, and
  missed-message count. Derived state; never stored.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Zero heartbeat delivery failures to the chat channel over 7
  consecutive days, across at least one host reboot.
- **SC-002**: A wiped interceptor patch is re-applied and confirmed in effect
  within one gateway startup, with the event visible in the journal.
- **SC-003**: No heartbeat content is lost while a device is unreachable —
  every push either delivers, or appears on the device after its next connect.
- **SC-004**: A foregrounded iPhone holds its edge channel ≥10 minutes with
  Border liveness checks succeeding throughout.
- **SC-005**: The operator learns of a chat-channel outbound failure within one
  heartbeat interval (≤30 min), rather than the ~15 hours observed.
- **SC-006**: `edge_message_queue` never exceeds the configured depth cap per
  device, verified with a device offline for ≥7 days.
- **SC-007**: The operator can read current NetClaw status from the watch
  without opening the phone app.

## Assumptions

- ~~**No Apple Developer Program membership, and none is being purchased for
  this feature.** APNs is unavailable.~~ **SUPERSEDED 2026-08-10**: a paid
  membership went active mid-implementation. Push entitlement is wired and the
  device now registers a push token. This does not invalidate the queue design —
  per the original wording, APNs becomes *a tier above the queue rather than a
  replacement for it*, which is exactly how it is implemented. See "Decision A"
  below; iOS pushes are relayed by Firebase rather than sent to Apple directly.
- **iOS push delivery goes through FCM, not Apple's raw API** (decision
  2026-08-10, "Decision A"). The client registers an FCM registration token, not
  a raw APNs device token, so the direct-to-Apple path could only ever have
  returned `BadDeviceToken`; it was removed unexecuted. Firebase relays to APNs
  using the APNs auth key uploaded to the Firebase project.
- ~~**Push is not yet delivering end-to-end.**~~ **RESOLVED 2026-08-10 17:35.** Was
  `401 Invalid APNs credential / THIRD_PARTY_AUTH_ERROR`: an APNs environment mismatch — the app declares `aps-environment=development` (sandbox) while key `L3H89WG6TY` was scoped `[Production]`. Fixed with new key `C6J54MKSPG` covering sandbox. Firebase could not
  authenticate to APNs. This is Firebase Console / Apple Developer portal
  configuration, not code; the Border path is verified up to that boundary.
- A Mac with Xcode is available for the iOS/watchOS half; the Linux Border host
  cannot build or debug the app.
- The existing Flutter app (`mobile/netclaw-mobile/`, specs 066–073, 099) is
  extended, not rewritten. `MessageFeedStore`, `ConversationStore`,
  `local_notifications.dart`, `reconnect_supervisor.dart` and the existing
  `WatchApp` target are reused.
- The Android device (`risk/1785267858182`, FCM registered) already delivers
  successfully and is out of scope except as a regression check.
- The edge WS listener stays on its current port and TLS posture; no transport
  redesign.
- `agents.defaults.heartbeat` stays at 30m and remains Slack's cadence; the
  device heartbeat matches it rather than replacing it.

## Already Landed (uncommitted work folded into this branch)

Implemented and verified on the Border side on 2026-08-10, before this spec was
written — recorded here so the branch is honest about what is already done:

- `bgp/federation/edge_queue.py` — the queue (FR-003–FR-007). Unit-verified
  including newest-wins overflow at the depth cap.
- `bgp/federation/service.py` — `EdgeQueue` wired in; `_flush_edge_queue()`
  replays on reconnect with mid-replay drop handling.
- `bgp-daemon-v2.py` — `/n2n/edge/push` enqueues instead of dropping;
  `/n2n/health` gains `edge_nodes` with per-device queue depth.
- `scripts/edge-heartbeat.py` + `netclaw-edge-heartbeat.{service,timer}` —
  the 30m device heartbeat (FR-008–FR-011) with the cross-channel Slack alarm
  (FR-010). Verified delivering to Android via FCM and queueing for iOS.
- `defenseclaw-slack-watch.{sh,service}` — FR-001. Running, but **not yet
  proven against a real wipe**: the restart that installed it did not trigger
  re-extraction. Proof arrives at the next host reboot.

Implemented and live-verified on the Mac/Xcode side, 2026-08-10/11 — see
MAC-STATUS.md for the full account:

- **US2** — the handler-registration race (`main.dart`) and the FCM/APNs
  token-type mismatch (`push_notify.py`, Border-side, option A) are both
  fixed. Foregrounded channel held 995s/16m35s with zero drops in the longest
  observed session; the `[NEEDS CLARIFICATION]` above is resolved.
- **US3** — `BGAppRefreshTask` registration, a headless `FlutterEngine`
  reconnect-and-drain entrypoint (`lib/ncfed/background_refresh.dart`), and a
  `PendingApprovalStore` durable holding pen (an approval arriving in that
  window has nowhere else to live — `ApprovalClient` is in-memory only).
  Implemented, unit-tested (`background_refresh_test.dart`,
  `pending_approval_store_test.dart`), compiles and deploys cleanly. **Not
  live-fired by a real OS-granted window** — closed as code-complete anyway;
  see the note below on why.
- **US4** — `lib/ncfed/device_heartbeat.dart` (textual heuristic detecting a
  heartbeat push and its FR-010 alarm line — the Border heartbeat has no
  dedicated `content_type`), `watch/heartbeat/latest` relay method
  (contracts/watch-heartbeat.md), a new watch "Status" tab, and a
  `HeartbeatComplication` widget for the literal "raise your wrist" scenario.
  Implemented, unit-tested (`device_heartbeat_test.dart` + 3
  `watch_relay_test.dart` cases), deployed to the phone. **Not visually
  confirmed on the physical watch screen** — the watch itself hit an
  unrelated, one-time pairing/install glitch (its first-ever real-device app
  transfer, right after enabling Developer Mode for the first time) that
  needed a full unpair/re-pair to clear; not a defect in this code. Closed as
  code-complete.
- Real APNs/FCM push (beyond original scope — the paid Apple Developer
  account activated mid-branch): `GoogleService-Info.plist`, the Push
  Notifications entitlement, and `register_push` confirmed working live.

**Why US3/US4 are closed without a live-fire/on-screen confirmation:** every
blocker encountered chasing that last mile was Apple tooling friction
(Xcode's GUI signing/capability cache, a stuck watch pairing state) — none of
it was a defect surfaced in the actual application code, which is unit-tested
everywhere it can be and already runs correctly end-to-end for every other
part of this spec on the same devices. Re-open either User Story if real
usage ever surfaces an actual defect, as distinct from a repeat of this
tooling friction.

**FR-017 closed 2026-08-11** — `scripts/edge-enrollments.py`, plus
`EdgeQueue.purge_member()` and the `edge_channels` teardown fix in
`/n2n/members/remove`. See FR-017a/b/c for the three gaps found while
implementing it, including the irreversible mis-retire of `risk/1786470797502`
that motivated the `--force` guard.

**Nothing in this spec remains open.** Two carried-forward notes for whoever
picks the mobile work up next:

- **US3/US4 were closed as code-complete, not live-fired.** Re-open either only
  if real usage surfaces an actual defect, as distinct from a repeat of the
  Apple tooling friction (Xcode signing cache, watch pairing state) that blocked
  the last mile.
- **The queue is load-bearing, not a stopgap.** It was designed for a world
  where APNs was impossible; that premise lifted the same day, and it still
  earned its place by delivering every heartbeat during the ~4 hours push was
  misconfigured. Keep it as the floor beneath push — APNs is best-effort and
  silently discards for long-offline devices.