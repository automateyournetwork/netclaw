# Phase 0 Research: N2N Ergonomics & Reliability

**Feature**: 053-n2n-ergonomics | **Date**: 2026-07-11

All decisions extend proven 052 primitives; none touch the frozen NCFED
framing, consent, authorization, or no-secrets guard (FR-022).

## R1. Async task delegation (US1)

**Decision**: Replace the synchronous `handle_task_submit` with a background
worker model in a new `tasks.py`:
- `n2n/tasks/submit {skill|tool, input, request_id}` → responder creates a
  `delegated_task` row (state=submitted), spawns an asyncio background task that
  runs the existing executor (`_exec_skill_gateway` / `_exec_tool_stdio`),
  and returns `{task_id}` immediately (< ~3 s).
- `n2n/tasks/status {task_id}` → `{state, progress, detail}` (short call).
- `n2n/tasks/result {task_id}` → `{state, output, tokens}` once completed.
- `n2n/tasks/cancel {task_id}` → cancels the background task.
- Requester side (`n2n_delegate`) submits, then the daemon polls status on the
  operator's behalf and returns the result when done (or returns the task_id so
  the operator/agent can poll via `n2n_task_status`).

**Rationale**: Decouples operation duration from any single call, so ngrok's
idle/reset never kills an in-flight build (the CML-clone blocker). Reuses the
existing executors unchanged. Matches the A2A task lifecycle already named in
the 052 contracts — we are finishing it, not inventing it.

**Alternatives considered**: Streaming progress frames over one long call —
still one long-lived call, still ngrok-resettable; rejected. Bumping timeouts
only (done as a stopgap in 052) — doesn't survive a channel reset; insufficient.

**Persistence/retention**: `delegated_task` rows persist in federation.db so a
completed result survives a channel drop/reconnect (FR-004) and a daemon
restart; retention window `N2N_TASK_RETENTION_S` (default 3600 s), swept
periodically.

## R2. Channel health + auto-reconnect (US2)

**Decision**: (a) Give `FederationChannel` an `on_close` hook that deregisters
it from `service.channels` so a closed channel is never a lingering zombie.
(b) Make the heartbeat loop actually detect death: on 3 missed heartbeats or a
failed send, close the channel (which now deregisters it). (c) Add a service-
level reconnect supervisor: for each `federated` peer whose channel is absent,
re-dial with bounded exponential backoff (5 s → 60 s cap), using the peer's
current endpoint from the mesh directory / `federation_peer` record. (d) A
request for a peer with no live channel triggers an on-demand reconnect first,
else fails fast with `peer_unreachable`.

**Rationale**: 052 already fixed "re-dial replaces stale channel" but re-dial
had to be manually triggered; the supervisor makes it automatic and bounded.
Consent persists, so re-federation needs no operator action (FR-007).

**Alternatives considered**: TCP keepalive only — doesn't cover ngrok half-open
resets; the app-level heartbeat is already in NCFED, just wire it to action.

## R3. Endpoint auto-re-announce (US3)

**Decision**: The mesh already carries per-AS endpoints (`agent.mesh_directory`,
`_send_mesh_directory`/`_process_mesh_directory`). On local ngrok endpoint change
(daemon detects its own `mesh_endpoint` changed, or on startup), the daemon
sends an `n2n/endpoint_update {identity, endpoint}` over the live NCFED channel
to each federated peer AND relies on the existing BGP mesh-directory exchange as
the backup path. The receiver validates the update is for an already-federated
identity arriving over that identity's authenticated session (FR-012), updates
`federation_peer.endpoint_host/port`, and triggers the reconnect supervisor to
re-dial the new endpoint (preserving lower-AS-initiates role, FR-011).

**Rationale**: Uses the authenticated session already in place; no new trust
path. Kills the manual host:port swap that recurred ~5×/session.

**Alternatives considered**: A rendezvous/discovery service — new infra, new
exposure, overkill for a small trusted mesh; rejected. Static endpoints (paid
ngrok/reserved addresses) — out of NetClaw's control, doesn't fix the general
case; noted as an operator option but not the fix.

## R4. Capability & version negotiation (US4)

**Decision**: Extend the `n2n/hello` handshake (already exchanged at federate
and — after R2 — on every reconnect) with a `capabilities` descriptor:
`{proto_version, features: [...], agent_invoke: "session-id"|"session-key",
reply_shapes: [...]}`. New `negotiate.py` builds the local descriptor (probing
the local `openclaw agent --help` for supported flags) and compares against the
peer's. `gateway.py` uses the negotiated `agent_invoke` flag and tolerant reply
extraction (already improved in 052: prefer `finalAssistantVisibleText`, search
recursively). A peer that sends no descriptor (pre-053) is treated as 052
baseline — graceful degrade (FR-016).

**Rationale**: Turns the silent `--session-key`/output-shape breakage into
explicit, self-adapting behavior. `hello` is the natural, already-present place;
no new round trip.

**Alternatives considered**: Pin a single OpenClaw version across the mesh —
unenforceable across independent operators; rejected. Try-flags-until-one-works
per call — wasteful and slow; probe once at negotiation instead.

## R5. Robustness hardening (US5)

**Decision**: Consolidate the 052 live hot-patches as first-class, tested
requirements: (a) client timeouts outlast server timeouts (n2n-mcp `_post`
610s > daemon 300/600 s — landed in 052, add a test asserting the invariant);
(b) reply parser tolerates trailing non-JSON (adopt the raw-decode-of-first-
object approach — the fix Nick prototyped — so a trailing `[agent] run … stop`
line can't break parsing); (c) full HTTP body read per Content-Length (landed in
052, add a segmented-body test); (d) typed errors naming the missing field
(landed in 052 for /n2n routes, extend + test). Each gets a regression test that
fails against pre-053 behavior (SC-008).

**Rationale**: These bugs each cost live debugging; codifying + testing them
prevents silent regression and is the cheapest high-value durability work.

## R6. Operator ergonomics & health visibility (US6)

**Decision**: (a) `n2n_connect(peer, host, port)` = add_peer + consent (+ dial)
in one; `n2n_trust(peer, [tools], chat=true)` = consent + default read-only
grants + chat-enable in one — thin composites over existing daemon routes, no
new protocol. (b) `/n2n/health` daemon route + `n2n_health` tool returning
per-peer `{channel_state, last_seen, endpoint_fresh, in_flight_tasks:[{id,
state, progress}]}`. (c) HUD claw node shows channel state ring, last-seen,
endpoint freshness, and live task progress from `/api/n2n`.

**Rationale**: Collapses the multi-step dance and makes federation observable —
directly serves Constitution X. All composites reuse existing endpoints.

## R7. Defaults (operator-configurable via `.env` `N2N_*`)

- `N2N_TASK_RETENTION_S=3600` — completed task result retention.
- `N2N_HEARTBEAT_MISS_LIMIT=3` (already), reconnect backoff `5s→60s`.
- `N2N_RECONNECT_MAX_ATTEMPTS` before surfacing `peer_unreachable` (default: keep
  retrying at the 60 s cap, mark unreachable after 5 consecutive failures for
  display, keep trying in background).
- Task status poll cadence (requester side): 15 s.
- Existing timeouts unchanged (chat 300 s, skill 600 s, client 610 s).
