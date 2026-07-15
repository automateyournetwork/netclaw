# Contract: Daemon HTTP API delta + n2n-mcp tools (053)

**Feature**: 053 | Additive to 052's `/n2n/*` API on `127.0.0.1:8179` and the
`n2n-mcp` server. Existing routes/tools unchanged (FR-022).

## New daemon routes

| Route | Method | Purpose |
|---|---|---|
| `/n2n/tasks` | POST | Submit a delegated task to a peer → `{task_id}` (US1) |
| `/n2n/tasks` | GET | List recent delegated tasks (both directions) — for health/HUD |
| `/n2n/tasks/<task_id>` | GET | Task status/progress/result |
| `/n2n/tasks/<task_id>/cancel` | POST | Cancel an in-flight task |
| `/n2n/health` | GET | Per-peer `{channel_state, last_seen, endpoint_fresh, in_flight_tasks}` (US2/US6) |
| `/n2n/connect` | POST | `{peer, host, port}` — add_peer + consent + dial in one (US6) |
| `/n2n/trust` | POST | `{peer, tools?, chat?}` — consent + default read-only grants + chat-enable (US6) |

All follow 052's body-read + typed-error hardening (FR-019).

## New n2n-mcp tools

| Tool | Purpose |
|---|---|
| `n2n_delegate(peer, target_type, target_name, input_text)` | Async submit; returns task_id + state (US1) |
| `n2n_task_status(task_id)` / `n2n_task_result(task_id)` / `n2n_task_cancel(task_id)` | Task lifecycle (US1) |
| `n2n_health()` | Federation health overview: per-peer channel/endpoint/task state (US6) |
| `n2n_connect(peer, host, port)` | One-step connect (US6) |
| `n2n_trust(peer, tools?, chat?)` | One-step trust (US6) |

- `_post` client timeout stays 610 s (052) — outlasts daemon op timeouts (FR-017).
- Task-status/health calls are short; only the (rare) inline-wait in
  `n2n_delegate` could be long, and it too is bounded then hands back a task_id.

## New `.env` tunables (extend `.env.example`)

| Var | Default | Purpose |
|---|---|---|
| `N2N_TASK_RETENTION_S` | `3600` | Completed-task result retention |
| `N2N_RECONNECT_BACKOFF_MIN_S` | `5` | Reconnect backoff floor |
| `N2N_RECONNECT_BACKOFF_MAX_S` | `60` | Reconnect backoff cap |
| `N2N_RECONNECT_UNREACHABLE_AFTER` | `5` | Consecutive failures before "unreachable" display (keeps retrying) |
| `N2N_TASK_POLL_S` | `15` | Requester-side status poll cadence |

## HUD (ui/netclaw-visual)

- `/api/n2n` gains `health` + `tasks` aggregation from `/n2n/health` + `/n2n/tasks`.
- Claw node: channel-state ring (up/reconnecting/unreachable), last-seen,
  endpoint-freshness badge, and live in-flight task progress.
