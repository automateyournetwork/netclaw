# Research: iPhone / Apple Watch heartbeat delivery

**Branch**: `103-ios-watch-heartbeat-delivery` | **Spec**: [spec.md](./spec.md)

> **Written retrospectively, 2026-08-11.** This feature began as incident
> response — "I haven't got a heartbeat in a while" — not as a planned feature,
> so Phase 0 happened *as* live diagnosis rather than before implementation. The
> findings below are the real ones, each traceable to a measurement or log line
> from 2026-08-10/11, not reconstructed guesses. Recorded because several are
> non-obvious, cost hours, and will otherwise be rediscovered the hard way.

## R1 — Why the existing DefenseClaw Slack guard could never work

**Question**: a known one-line fix (`slack.com` in `KNOWN_SAFE_DOMAINS`) had an
idempotent `ExecStartPre` guard re-asserting it. Why was Slack dead for ~15h?

**Finding**: the guard is structurally incapable of winning. Measured:

| Time | Event |
|---|---|
| `10:55:35.x` | guard patches the file, greps to confirm, logs success |
| `10:55:36.87` | DefenseClaw re-extracts its **entire** vendored extension dir |

`dist/`, `node_modules/` and `package.json` all share that mtime, so it is a full
re-extract, and it happens *after* `ExecStartPre` by design. Compounding it: the
gateway imports `fetch-interceptor.js` **once** (`LLM fetch interceptor active`,
~16s into startup) and never re-reads it — so patching a running gateway does
nothing until the next restart, which is also when the wipe happens. That
circularity is the whole trap.

**Also established**: the wipe correlates with **host boot**, not every gateway
restart. A `systemctl restart` at 13:27 did *not* re-extract (mtime unchanged).

**Decision**: a polling watcher ordered `Before=` the gateway, tight (0.2s) for
the first 180s then 5s forever. Wins because the wipe lands ~1.4s in and the
import is ~16s in — a ~14s window. `inotifywait` is not installed on this host,
hence polling.

**Rejected — `chattr +i`** (the operator's initial preference): since the wipe is
part of extraction *at boot*, an immutable file makes that extraction fail during
boot; if that aborts the plugin install the entire DefenseClaw security layer is
lost at the worst possible moment. Also needs sudo. The watcher cannot break
extraction. **Validated in production 2026-08-11 06:49:25** — caught a real wipe
2s into boot and repaired it 27s before the gateway loaded the file.

**Also ruled out, do not retry**: `guardrail.allow_unknown_llm_domains: true` is
*already set* and the sidecar was started after that config was written, yet it
still logs `BLOCKED passthrough to unknown domain`. The setting looks like the
fix and is not. And there is no local extraction source to patch instead —
nothing under `~/.defenseclaw/`, the Python package, or the openclaw npm install
contains `KNOWN_SAFE_DOMAINS`.

## R2 — The edge channel's lost-first-frame race

**Question**: the phone reported connected while `federation.db` said
`unreachable`, and a queue replay timed out on a freshly-authenticated socket.

**Finding**: `FederationService.accept_edge_ws()` sends the nonce challenge as
the **first frame, before `ch.start()`**, with no retransmit:

```python
await ch.notify("n2n/edge/challenge", {"nonce": nonce.hex()})   # first frame
await ch.start()                                               # read loop AFTER
```

A client whose read loop isn't live at socket-open misses it, never sends
`in2n/hello`, and hangs in `awaiting device auth` forever. Corroborated by
`auth_failure_bucket` being **empty** on every attempt — it never *failed* auth,
it never *attempted* it, which rules out a credential problem.

**The measurement that settled it** — same queued message, same client, same
method, same socket lifecycle:

| Dispatch delay after accept | Outcome |
|---|---|
| 86ms | `n2n/edge/message` timed out at the full 30s |
| 3.087s | delivered in under a second, with 4 others |

**Decision**: `N2N_EDGE_REPLAY_SETTLE_S` (default 3s) before dispatching a
replay, plus one retry — abandoning the whole backlog on a single miss is how a
phone connected for an hour still received nothing. This covers replay but
**cannot** cover auth, since the challenge precedes channel registration; the
client fix (moving handler registration ahead of an `await` on a permission
dialog) was required and landed on the Mac side.

## R3 — It was never iOS suspension

**Question**: drops with `no close frame received or sent`, and once
`1011 keepalive ping timeout`, suggested iOS freezing a backgrounded app.

**Finding**: **wrong.** The Android flaps identically (10s–96s holds, same close
reason) on the same Flutter codebase. And the iPhone is capable of long holds —
observed distribution: `18s, 57s, 84s, 185s, 709s, 995s, 3520s`, with zero
heartbeat failures on the long ones and consistent 16s self-recovery. An early
"dies in 18–57s" claim was two samples over-generalized.

**Lesson recorded**: a second device on the same codebase is the cheapest
possible control. It falsified a platform-specific theory in one observation.

## R4 — iOS push: token types, and why direct-to-APNs was dead code

**Question**: `push_notify.send_apns()` existed and was wired. Once a paid
membership appeared, would it work?

**Finding**: no — **unusable by construction**, independent of credentials. It
POSTs to `https://api.push.apple.com/3/device/{token}`, which requires the raw
APNs device token (64 hex chars, 160 on newer). The client registers
`FirebaseMessaging.instance.getToken()` — an **FCM registration token**. Confirmed
empirically: the enrolled iPhone row held `push_platform='apns'` with a 142-char
`<instanceID>:APA91b…` value. That combination can only ever return
`BadDeviceToken`.

**Decision (A)**: route every platform through FCM; Firebase relays to APNs using
the `.p8` uploaded to the project. Chosen over keeping the direct path because
either option needs a valid APNs credential — (A) inside Firebase, (B) on the
Border — and (A) needed no new Border config, moved no secrets between machines,
and let ~60 lines of never-executed ES256/JWT code be deleted rather than
promoted to production. `platform='apns'` is still accepted and routed to FCM so
enrolled devices need no re-registration.

## R5 — A membership is not a working push channel

**Question**: with the membership active and the `.p8` uploaded, push still
returned `401`.

**Finding**: an **APNs environment mismatch**. `Runner.entitlements` declares
`aps-environment=development`, so debug builds register a **sandbox** token,
while the first key was scoped `[Production]`. Firebase resolved the token to the
app, tried Apple's sandbox endpoint, and could not authenticate.

**The diagnostic that mattered — read the error *code*, not the text.**
`THIRD_PARTY_AUTH_ERROR` rather than `SENDER_ID_MISMATCH` / `UNREGISTERED` /
`INVALID_ARGUMENT` proves FCM resolved the device token → the registered iOS app
→ *then* tried APNs and was refused. That single fact eliminated project wiring,
sender ID, bundle ID, app registration, the device token, and the Border's
service-account credential in one step. The error *text* says "credential", which
points at the Key ID — correct the whole time.

**Environment scoping is fixed at key creation** (only name and topics are
editable), so the fix is a new key. Apple permits 2 active keys, so the old one
need not be revoked before verifying. Historically an unrestricted team-scoped
`.p8` covered both environments — which is why token auth "just works" for debug
builds — so Apple's newer per-environment scoping reintroduced a bug class that
had not existed for years.

## R6 — Observability traps found while building the status summary

- **`/n2n/faults` counts edge nodes as members.** A naive summary read "3 members
  down" when all four real members were up. Compose agent-member health from
  `/n2n/members` (carries `node_type`, `live`, `heartbeat_age_s`) — but it does
  **not** carry `push_platform`, which only `/n2n/health`'s `edge_nodes[]` has.
  Both endpoints are needed to decide whether a device is worth pushing to.
- **`member.state` alone is misleading on a phone.** Written on
  connect/disconnect, and a phone reconnects constantly, so two reads seconds
  apart can honestly disagree. Heartbeat *age* distinguishes "between sockets"
  from "gone".
- **Queue `count(*)` cannot indicate drain success.** Delivered rows are pruned
  on the next *enqueue*, and a heartbeat lands every 30m, so a non-zero count is
  usually re-accumulation or leftover tombstones. Ground truth is the audit trail
  (`grep 'edge_push'`), not the queue table.
- **Re-enrolling mints a new `member_id`.** Nine `node_type='edge'` rows
  accumulated. This is what motivated FR-017.
- **`n2n.edge[unauthenticated]` appears in every close line**, including fully
  authenticated sessions — the channel logger is never relabelled after auth.
  Purely cosmetic, but it reads as an auth failure.

## R7 — Outbound-only failure is invisible to every health surface

**Finding**: through the entire ~15h Slack outage, `openclaw channels status`
reported `connected, health:healthy` because **inbound Socket Mode was fine**.
The agent kept running and composing correct heartbeats; only delivery 403'd.
Nothing retried and nothing alerted. Two real findings (a BGP peer down since
Aug 4, a stopped CML lab) sat undelivered inside blocked payloads.

**Decision**: because the device heartbeat rides a completely different
transport, it is the natural place to notice — it reports recent chat-channel
delivery failures, and vice versa. Neither channel can now go silent unobserved.

**Corollary for verification**: absence of interception logs proves nothing
without traffic. Steps like "grep for 0 interceptions" passed for hours while
delivery was broken, because nothing had tried to send. **A real send returning a
message ID is the only proof that counts** — which is why the fix was confirmed
with an actual Slack message, not a clean log.
