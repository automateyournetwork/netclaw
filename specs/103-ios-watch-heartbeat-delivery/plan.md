# Implementation Plan: iPhone / Apple Watch Heartbeat Delivery

**Branch**: `103-ios-watch-heartbeat-delivery` | **Date**: 2026-08-11 (retrospective)
**Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

> **Written retrospectively.** This feature was not planned before it was built —
> it began as incident response ("I haven't got a heartbeat in a while") and the
> spec itself was written mid-stream, once the shape of the problem was clear.
> This document records the plan the work *actually followed*, including why the
> ordering was forced by circumstance rather than chosen. Recorded honestly
> because a fabricated pre-implementation plan would satisfy Principle XVI's
> checker and inform nobody — the same reasoning `verify-spec-artifacts.py`
> applies when it accepts a combined plan/tasks file.

## Summary

Deliver the periodic NetClaw status heartbeat to an enrolled iPhone and Apple
Watch, on a transport that is independent of the existing Slack channel, and make
it survive a device that is disconnected most of the time.

**Three delivery tiers, tried in order**: live WebSocket → platform push
(FCM, relaying to APNs for iOS) → persistent store-and-forward queue replayed on
reconnect. No tier is load-bearing alone; a device with no working push transport
still loses nothing.

## Technical Context

**Language/Version**: Python 3.10+ (Border: daemon + `bgp/federation/*`,
matching 052–102). Dart 3.x / Flutter and Swift 5.0 on the mobile side
(`mobile/netclaw-mobile/`), extending specs 066–073/099.
**New dependencies**: **none.** Border-side uses stdlib (`sqlite3`, `asyncio`,
`json`, `urllib`) plus `httpx`, already a dependency. Mobile side adds no
packages, consistent with every prior mobile spec.
**Storage**: extends the existing `~/.openclaw/n2n/federation.db` with one table
(`edge_message_queue`); no new datastore.
**Scale**: one operator, two devices, a 30-minute cadence. Bounding the queue
matters far more than throughput.

## Why the order was what it was

The sequencing was **dictated by the incident**, not chosen for engineering
convenience — worth stating plainly since it looks arbitrary otherwise:

1. **Slack first (FR-001).** The reported symptom. Also a hard prerequisite for
   trusting anything else: while the only working notification channel was dead,
   there was no way to observe whether new work helped.
2. **Diagnose the phone (US2) before building for it.** The app claimed to be
   connected and was not. Building delivery on top of an unexamined transport
   would have attributed transport failures to the new code — which is exactly
   what happened for the first hour anyway (see R2).
3. **Queue (US1) before push.** At authoring time APNs was believed impossible,
   so the queue was the *only* mechanism that could work. It shipped first and
   then carried every heartbeat during the ~4 hours push was misconfigured —
   which retroactively justified building it first even though the premise
   changed.
4. **Push last, opportunistically.** It only became possible mid-branch.
5. **FR-017 last of all.** It was a theoretical tidiness requirement until this
   branch's own testing generated nine stale enrollments and the author cleared
   them with `sqlite3` — at which point it became concrete.

## Architecture

### Border side

- **`bgp/federation/edge_queue.py`** — `EdgeQueue`, sharing the
  `FederationManager` sqlite connection exactly as `RiskManager` does. Bounded on
  every enqueue: per-member depth cap (50) and TTL (7d), newest-wins on overflow.
  Deliberately not a general mesh-message queue — it only ever holds content that
  already passed through `/n2n/edge/push`, the single audited Border-to-phone
  path, so queueing cannot become a back door that mirrors channel traffic to a
  device.
- **`FederationService._flush_edge_queue()`** — replays oldest-first on channel
  registration, after a settle delay, with one retry. A mid-replay disconnect
  leaves the remainder queued rather than losing it or double-delivering.
- **`/n2n/edge/push`** — enqueues instead of returning `delivered:false` and
  discarding. **`/n2n/health`** gains `edge_nodes[]` with per-device queue depth,
  so a growing backlog is visible rather than implicit.
- **`scripts/edge-heartbeat.py`** + systemd timer — the device heartbeat, on
  Slack's 30m cadence. Composed deterministically from the daemon's own HTTP
  surface, **not** by the agent choosing to call a tool, and sharing no code path
  with Slack so one channel failing cannot silence the other.
- **`scripts/defenseclaw-slack-watch.sh`** + service — FR-001, per R1.
- **`scripts/edge-enrollments.py`** — FR-017, mutating only via
  `/n2n/members/remove`.

### Mobile side (Mac/Xcode)

Extends the existing app rather than rewriting: `MessageFeedStore`,
`ConversationStore`, `local_notifications.dart`, `reconnect_supervisor.dart` and
the `WatchApp` target are reused. New: `background_refresh.dart`,
`PendingApprovalStore`, `device_heartbeat.dart`, `HeartbeatComplication`, and the
`watch/heartbeat/latest` relay method.

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| Slack patch durability | polling watcher, not `chattr +i` | immutability makes boot-time extraction fail, risking loss of the whole security layer (R1) |
| iOS push transport | all platforms via FCM (decision A) | direct-to-APNs was dead code by token type; A needed no new Border config and deleted ~60 unverified lines (R4) |
| Heartbeat composition | separate deterministic job | the built-in heartbeat depends on the model calling a tool, and rides the transport that was already broken (R7) |
| Queue growth | depth cap + TTL, newest-wins | a phone can be off for weeks; newest status is what matters |
| Retire safety | staleness, not connectedness | a flapping phone reads disconnected while fully live (FR-017c, learned destructively) |

## Tasks

Retrospective, in the order actually executed. All complete.

### Phase 1 — restore the reported symptom (FR-001, FR-002)
- [x] T001 Root-cause the Slack 403; establish that `ExecStartPre` loses to the
      re-extract by ~1.4s and that the interceptor is imported once (R1)
- [x] T002 `scripts/defenseclaw-slack-watch.sh` + `defenseclaw-slack-watch.service`,
      ordered `Before=` the gateway; repo copies of both guard scripts
- [x] T003 Verify by decision function *and* a real send returning a message ID
      (clean logs are not evidence — R7)
- [x] T004 Confirm against a real boot-time wipe — **passed in production
      2026-08-11 06:49:25**, repaired 27s before the gateway loaded the file

### Phase 2 — store-and-forward (US1, FR-003–FR-007)
- [x] T005 `bgp/federation/edge_queue.py` with depth cap, TTL, newest-wins
- [x] T006 Unit-verify overflow behaviour in isolation
- [x] T007 Wire `EdgeQueue` into `FederationService`; `_flush_edge_queue()` with
      mid-replay drop handling
- [x] T008 `/n2n/edge/push` enqueues on failure; report `queued`/`queue_depth`
- [x] T009 `/n2n/health` exposes `edge_nodes[]` incl. queue depth (FR-007)
- [x] T010 Add settle delay + one retry after measuring the 86ms/3.087s race (R2)
- [x] T011 Verify replay end-to-end — 5/5 delivered, `gait=f696e3b8fe`

### Phase 3 — the device heartbeat (FR-008–FR-011)
- [x] T012 `scripts/edge-heartbeat.py` composing from the daemon's own API
- [x] T013 Exclude `node_type='edge'` from agent-member health counts (FR-009, R6)
- [x] T014 Cross-channel Slack-delivery alarm (FR-010, R7)
- [x] T015 Skip stale/unreachable devices so the queue cannot fill for abandoned
      enrollments (FR-011)
- [x] T016 `netclaw-edge-heartbeat.{service,timer}` on Slack's 30m cadence

### Phase 4 — iOS/watchOS (US2, US3, US4) — Mac/Xcode
- [x] T017 Fix the handler-registration race in `main.dart` (US2, R2)
- [x] T018 Confirm foregrounded channel stability — 995s with zero drops
- [x] T019 `BGAppRefreshTask` + headless reconnect-and-drain +
      `PendingApprovalStore` (US3) — unit-tested, **not live-fired**
- [x] T020 `device_heartbeat.dart`, `watch/heartbeat/latest`, watch Status tab,
      `HeartbeatComplication` (US4) — unit-tested, **not screen-confirmed**

### Phase 5 — real push (beyond original scope)
- [x] T021 Diagnose the FCM/APNs token-type mismatch; adopt decision A; delete
      `send_apns()`/`_apns_jwt()` unexecuted (R4)
- [x] T022 Diagnose `THIRD_PARTY_AUTH_ERROR` as an environment mismatch; new key
      covering sandbox (R5)
- [x] T023 Verify push delivering in production — 17:56:48, both devices,
      `via push_notification`

### Phase 6 — enrollment hygiene (FR-017)
- [x] T024 `EdgeQueue.purge_member()`; call it from the removal route (FR-017a)
- [x] T025 Close the channel from `edge_channels` too, not just `member_channels`
      (FR-017b)
- [x] T026 `scripts/edge-enrollments.py` — list / `--retire` / `--retire-stale`
- [x] T027 Replace the connectedness guard with a staleness guard + `--force`
      after it failed destructively (FR-017c)

## Deviations from the plan worth recording

- **Phases 1–3 were built before the spec existed.** The spec's "Already Landed"
  section documents this rather than hiding it.
- **The central assumption inverted mid-branch.** "No Apple Developer membership,
  APNs impossible" became "push works" on the same day. The tiered design
  absorbed it without rework — push slotted in above the queue exactly as the
  original wording anticipated.
- **US3/US4 closed code-complete, not live-fired.** Every last-mile blocker was
  Apple tooling friction (Xcode signing cache, a stuck watch pairing), not
  application defects. Reopen only for a real defect.
- **T027 exists because T026 shipped with a guard that did not work.** A
  `--retire` expected to be refused irreversibly destroyed the then-current
  enrollment because the phone was between sockets. Recorded rather than quietly
  fixed, since the underlying mistake — treating a flapping device's momentary
  disconnection as evidence it is abandoned — is easy to repeat.
