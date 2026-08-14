# Contract: `watch/heartbeat/latest` — the device heartbeat, relayed to the watch

One additional request/reply shape over the same `WCSession.sendMessage` → `WatchRelayPlugin.swift`
→ `watch_relay.dart` path spec 072's contract already establishes (see
`specs/072-apple-watch-companion/contracts/watch-relay.md` §0 for the shared failure-mode note: a
`sendMessage` failure never reaches Dart at all, it IS the `phoneUnreachable` state).

## Background: there is no dedicated heartbeat wire format

The Border-composed device status heartbeat (US5/FR-008–FR-010, `scripts/edge-heartbeat.py`) is
pushed to the phone as an ordinary `n2n/edge/message` with `content_type: "text"` — byte-for-byte
the same envelope as any manually-sent text push. There is no structured field marking it as a
heartbeat. `lib/ncfed/device_heartbeat.dart` recognizes one by two textual conventions the Border
side already follows:

- Every heartbeat's `content` begins with the literal prefix `"NetClaw "` (`compose()`'s first line
  is always `f"NetClaw {identity} — {HH:MM %Z}"`).
- An active Slack-delivery-failure alarm (FR-010) appears as a line containing the literal substring
  `"⚠ SLACK HEARTBEAT FAILING"`.

The phone persists only the *latest* one (`DeviceHeartbeatStore`, a single JSON file — older
heartbeats are not retained for this purpose, they're still visible in the ordinary Feed tab like
any other message). This detection runs in two places: `main.dart`'s foreground `onMessage` handler,
and `background_refresh.dart`'s headless `BGAppRefreshTask` entrypoint (spec 103 US3) — a heartbeat
delivered while the app is backgrounded still reaches the watch.

## `watch/heartbeat/latest` — fetch the latest device heartbeat

**Request** (watch → phone, no payload needed):

```json
{ "method": "watch/heartbeat/latest" }
```

**Reply** (phone → watch) — three distinct shapes, deliberately not collapsed into one:

```json
{ "enrolled": false, "has_heartbeat": false }
```
No heartbeat store exists at all — nothing has ever enrolled this device with a Border.

```json
{ "enrolled": true, "has_heartbeat": false }
```
Enrolled, but no heartbeat has been received yet (e.g. a fresh enrollment, before the first 30-minute
tick). Rendered distinctly from "all clear" — a genuinely-empty state must never read as a healthy one.

```json
{
  "enrolled": true,
  "has_heartbeat": true,
  "summary": "⚠ SLACK HEARTBEAT FAILING — 2 delivery failure(s), run `openclaw channels status`",
  "pushed_at": "2026-08-10T16:33:00Z",
  "is_alarm": true
}
```
The latest heartbeat. `summary` is the single line worth showing on a watch-sized screen: the alarm
line verbatim if `is_alarm` is true, otherwise the fixed string `"All systems normal"` — the full
multi-line posture/daemon/peer report the Border composes is available on the phone's Feed tab, not
here. `pushed_at` is the heartbeat's original Border timestamp (ISO-8601, UTC) — the watch computes
its own relative age from this rather than the phone sending a pre-formatted "5m ago" string, so the
age stays accurate for however long the watch view stays open.

## Unlike Approvals/Feed/History: the watch falls back to a cached value

Every other `watch/*/list` call clears its list to empty when the phone is unreachable
(`ConnectionState.phoneUnreachable`) — nothing to show, so nothing is shown. The heartbeat surface is
different by design (US4 acceptance scenario 3: "the phone is unreachable... shows the last-known
status and its age rather than an empty or misleading view"): `WatchDataStore.refreshHeartbeat()`
leaves its last successfully-fetched value in place on failure, backed by `HeartbeatStatusStore` (an
App-Group-shared `UserDefaults`, also what the `HeartbeatComplication` widget reads from) so the
last-known value survives even a watch app relaunch, not just a single failed refresh mid-session.

## Complication data flow (no request of its own)

`HeartbeatComplication.swift` (accessoryCircular/accessoryRectangular/accessoryInline) has no network
call — it reads whatever `HeartbeatStatusStore` currently holds and calls
`WidgetCenter.shared.reloadAllTimelines()` only when `WatchDataStore.refreshHeartbeat()` writes a
genuinely new value, mirroring `PendingApprovalComplication`'s existing pattern (`policy: .never`, no
periodic polling).
