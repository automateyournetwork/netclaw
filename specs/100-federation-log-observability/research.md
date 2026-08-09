# Phase 0 Research: Federation Inbound-Call Observability

**Feature**: 100-federation-log-observability
**Date**: 2026-08-06

All findings below were verified against the running system and the source on this branch, not inferred.

---

## R1 — The daemon runs on Python 3.14, not the repo virtualenv

**Decision**: Target and test against **Python 3.14.4** (`/usr/bin/python3`).

**Evidence**:
- `netclaw-mesh.service` → `ExecStart=/usr/bin/python3 .../bgp-daemon-v2.py`
- `/proc/538/exe → /usr/bin/python3.14`
- `/usr/bin/python3 --version` → `Python 3.14.4`
- The live traceback referenced `/usr/lib/python3.14/asyncio/tasks.py`

**Rationale**: The repo virtualenv at `.venv/` is **Python 3.13.0b1** — a different interpreter with a different `asyncio`. Two of the four defects are asyncio-behavior-dependent (`IncompleteReadError` classification, the TLS `eof_received` warning), so tests run under the venv would exercise code the daemon never executes. This is a real trap: the venv is what a developer's shell activates by default.

**Consequence**: Any test asserting asyncio behavior must be invoked with `/usr/bin/python3` explicitly.

**Alternatives rejected**: Testing under the venv (would validate the wrong runtime); pinning the daemon to the venv (out of scope, changes deployment).

---

## R2 — Inbound calls are ALREADY logged at info level

**Decision**: Do **not** add new inbound-call logging. Enrich the one existing line.

**Evidence**: `bgp/federation/audit.py:78-80`, inside `Auditor.record()`:

```python
logger.info("AUDIT[%s] %s %s %s/%s → %s/%s%s", channel_kind, direction, peer_identity,
            target_type, target_name, decision, outcome,
            f" gait={gait_ref[:10]}" if gait_ref else "")
```

Confirmed live — 14 such lines in the preceding 6 hours:

```
[n2n.audit] INFO AUDIT[in2n] outbound johns-risk/cml skill/cml-lab-lifecycle → requested/submitted
```

**Rationale**: Every inbound handler in `invocation.py` routes **every** decision branch through `self.audit.record(direction="inbound", ...)`. Peer identity, target type/name, decision, and outcome are therefore already on one info line per audit write. This **invalidates the original premise of User Story 1**, which has been corrected in the spec.

**Why the original draft got it wrong**: `invocation.py` contains only two `logger.warning` calls of its own, so a grep for logging calls in that module returns almost nothing. The logging is delegated to `Auditor.record()`. The observation session compounded the error — its journal filter matched `n2n.invocation` but not `n2n.audit`, so the existing lines were invisible to the very watch set up to find them.

**Remaining genuine gaps** (the only new work for US1):
1. `decision`/`outcome` are all emitted at `info`, so a denial is severity-indistinguishable from a success (FR-003).
2. `request_id` is a parameter of `record()` and is persisted to the DB, but is **not** interpolated into the log line (FR-005).
3. The line is written at decision time, so a call that never reaches a decision leaves no trace (FR-033).

**Alternatives rejected**: Adding per-handler logging (would duplicate the audit line, violating FR-032, and would drift as handlers are added — there are 8+ inbound handlers).

---

## R3 — Where dampening belongs

**Decision**: Extend the existing `self.health[ident]` dict and the reconnect supervisor in `bgp/federation/service.py`. No new component.

**Evidence**:
- Supervisor loop: `service.py:725-757`. Reads `self.manager.list_peers()` fresh every 2s iteration, so DB changes take effect without restart (verified live — clearing four endpoints stopped the storm within seconds, no restart).
- Skip conditions already present: not federated (`:731`), channel live (`:733`), higher local AS (`:736`), **no endpoint** (`:738-739`).
- Backoff: `min(_backoff_min * 2**min(attempts,6), _backoff_max)` at `:749-750`, with `_backoff_min=5`, `_backoff_max=60`, `_unreachable_after=5` from env at `:83-85`.
- Failure WARNING emitted from `open_channel` at `:711`.
- Success resets health wholesale at `:98-99`: `{"state":"up","attempts":0,"next_retry_at":0,"last_seen":time.time()}`.

**Rationale**: The skip-on-no-endpoint branch is what made the manual endpoint clear work, and it is the same mechanism FR-023 depends on. The health dict is already the peer-liveness view FR-014 must keep observable.

**Key finding for FR-031 (flapping)**: the wholesale reset at `:98-99` sets `attempts=0` on **any** successful connection. A peer that connects and immediately drops therefore never accumulates enough attempts to be dampened — flapping defeats dampening completely. This is not hypothetical: the peer observed at 14:39 exhibited exactly a close-then-reopen cycle. Satisfying FR-031 requires the reset to become conditional on sustained uptime rather than on connection success, which means tracking a "connected since" timestamp separately from `last_seen`.

**Alternatives rejected**: A separate supervisor (duplicates peer iteration); dampening at the logging layer only (leaves the 60s dial storm intact, wasting connect attempts).

---

## R4 — Log dampening technique

**Decision**: Suppress at the **call site** using the per-peer health state, emitting a periodic summary. Do not use a `logging.Filter`.

**Rationale**: The suppression decision is per-peer and depends on state the supervisor already owns (consecutive failures, endpoint staleness, last-summary time). A `logging.Filter` would have to re-derive that state from message text — fragile and inverted. Call-site suppression also satisfies FR-009 naturally: the summary can state attempt count and covered period because the counters are right there.

**FR-015 (distinct causes must not collapse)** requires retaining a normalized signature of the last failure cause per peer and treating a change in signature as a reason to log immediately rather than summarize. The raw cause strings are long multi-IP lists (`Multiple exceptions: [Errno 111] Connect call failed ('3.12.245.36', 15091), ...`) whose IP ordering varies between attempts, so the signature must be normalized (e.g. exception type plus error number) rather than compared verbatim — otherwise ordering churn alone would defeat collapsing.

**Alternatives rejected**: `logging.Filter` (state re-derivation); external log-rate limiting (no new dependencies, and would suppress unrelated messages).

---

## R5 — The TLS `eof_received` warning originates in the standard library

**Decision**: Install a narrowly targeted `logging.Filter` on the `asyncio` logger that drops only this one message. Here a filter **is** correct — unlike R4, the emitter is not ours to modify.

**Evidence**: `grep -rn "eof_received" bgp/` returns **nothing**. The message text `returning true from eof_received() has no effect when using ssl` is emitted by CPython's `asyncio/sslproto.py` when the application protocol's `eof_received()` returns a true value over TLS. `asyncio.streams.StreamReaderProtocol.eof_received()` returns `True` unconditionally, and NetClaw obtains its streams via the high-level `asyncio` stream API with an SSL context — so the pairing is structural and fires on every encrypted channel close.

**Rationale**: Because the return value is the stdlib's own and NetClaw never implements `eof_received`, no change to NetClaw's connection handling can prevent it. The only options are reclassification/filtering or replacing the stream API with a custom protocol.

**Constraint from FR-030**: the filter must match this specific message only and must not suppress other `asyncio` warnings, which are frequently genuine.

**Alternatives rejected**: Implementing a custom `asyncio.Protocol` to control `eof_received` (a large, risky rewrite of the channel transport to silence one cosmetic line — grossly disproportionate); raising the `asyncio` logger's level (would hide real asyncio warnings); leaving it (fails FR-030/SC-011).

---

## R6 — Benign-disconnect classification

**Decision**: Catch `asyncio.IncompleteReadError` and `(ConnectionResetError, asyncio.TimeoutError)` around the pre-handshake reads specifically, log one `debug`/`info` line, and return — before the catch-all.

**Evidence**:
- Pre-handshake read: `agent.py:278` (`readexactly(1)`, 30s timeout) and `:282` (`readexactly(4)`, 10s timeout).
- Catch-all: `agent.py:498-499` — `self.logger.error(f"Error in _handle_incoming_connection: ...", exc_info=True)`, which logs **every** exception at ERROR with a traceback.
- Observed live at 14:11:41 from `127.0.0.1`: a ~10-line ERROR traceback for a zero-byte connect.

**Rationale**: FR-020 requires severity to follow operator relevance. A zero-byte or truncated pre-handshake read is a probe, scan, or aborted dial — never actionable. `agent.py:307` already demonstrates the intended contrast: a *complete but invalid* magic value is logged as a one-line `warning`, no traceback. That is the existing convention to match.

**Constraint from FR-019**: the narrow catch must sit *before* the catch-all and must not widen it. Unexpected faults must still reach `:498` and produce a traceback. Catching broadly here would swallow real bugs — the specific failure mode FR-019 exists to prevent.

**Alternatives rejected**: Downgrading the catch-all itself (would hide genuine faults, violating FR-019); suppressing by peer IP (loopback is not the only prober).

---

## R7 — Endpoint retirement: registry method + MCP tool

**Decision**: Add a dedicated `forget_peer_endpoint(identity)` method to `FederationManager`, and expose it as a tool on the existing `n2n-mcp` server.

**Evidence**:
- `manager.py:289-317` `upsert_peer()` applies a column only `if val is not None` (`:298-299`), so `None` means "leave unchanged". `endpoint_port` is an INTEGER column with no sentinel — **clearing it through this API is impossible**. Confirmed: resolving the live incident required `UPDATE federation_peer SET endpoint_host='', endpoint_port=NULL, endpoint_updated_at=NULL WHERE identity IN (...)` against the running database.
- `endpoint_updated_at` is bumped by `upsert_peer` whenever host or port is written (`:303-304`), so the three fields are already treated as one unit on write — clearing them together is symmetric.
- Re-registration paths that will restore the endpoint: `service.py:327` and `service.py:706`.
- `n2n-mcp` is registered in `config/openclaw.json` as `python3 -u mcp-servers/n2n-mcp/server.py` with `BGP_DAEMON_API`, i.e. it reaches the daemon over HTTP rather than touching the DB directly — so the tool needs a corresponding daemon API route, not direct DB access.

**Rationale**: A distinct method rather than overloading `upsert_peer` with sentinels; sentinel values would make every existing caller's semantics ambiguous and risk accidental clears.

**FR-025 (attributable)**: `Auditor.record()` already writes to GAIT via `_gait_ref()` and accepts `event` and `actor` parameters, so recording the retirement reuses existing machinery rather than adding a new trail. Constitution IV ("no operation may execute silently") makes this mandatory, not optional.

**Open item for Phase 1**: whether forgetting the endpoint of a peer with a currently-live channel should tear the channel down. Recommendation: **leave the channel running** — the endpoint is only consulted for *dialling*, so a live channel is unaffected and tearing it down would convert a cleanup action into an outage.

**Alternatives rejected**: Sentinel value in `upsert_peer` (ambiguous for all callers); operator-facing SQL helper script (still hand-surgery, fails FR-026); direct DB write from the MCP server (bypasses the daemon that owns the connection).

---

## R8 — Configuration surface

**Decision**: Add new env vars following the existing `N2N_RECONNECT_*` naming, all with defaults preserving today's behavior where behavior is unchanged, and all documented in `.env.example`.

**Evidence**: existing pattern at `service.py:83-85` — `N2N_RECONNECT_BACKOFF_MIN_S`, `N2N_RECONNECT_BACKOFF_MAX_S`, `N2N_RECONNECT_UNREACHABLE_AFTER`.

**Rationale**: FR-028 requires dampening be tunable and disableable so an operator can restore verbose reporting when diagnosing; Constitution XI and XIII require `.env.example` documentation for every new variable. Reusing the prefix keeps the tuning surface discoverable.

**Planned variables** (names finalized in Phase 1 contracts):
- dead-peer escalated ceiling (default 900s = 15 min, per clarification)
- consecutive failures before escalation
- endpoint staleness horizon qualifying a peer as durably dead
- failure-summary interval
- sustained-uptime threshold before dampening clears (FR-031)
- a master disable restoring per-attempt WARNING logging (FR-028)

---

## R9 — Constitution XI applicability

**Decision**: This is a defect fix in an existing MCP server, **not** a new capability, so the full Principle XI artifact set does not apply. The subset that does:

| Artifact | Applies? | Why |
|---|---|---|
| `.env.example` | **Yes** | New env vars (R8) — also Principle XIII |
| `TOOLS.md` | **Yes** | New `n2n-mcp` tool (R7) changes the tool reference |
| `README.md` | **Yes, if tool counts are stated** | Principle XII requires accurate counts |
| `scripts/reconcile-mcp.py` | **Yes — must run** | CLAUDE.md mandates it before push; CI fails on non-zero |
| `catalog.sh` / `install-steps.sh` | No | No new installable component |
| `ui/netclaw-visual/` | No | No new integration; peer health already rendered |
| `SOUL.md` / `SKILL.md` | No | No new skill |
| `config/openclaw.json` | No | `n2n-mcp` already registered |

**Principle X tension, resolved**: Principle X states the HUD "MUST be updated to reflect new integrations and their operational status." No new integration is added here, and the HUD already renders peer posture — FR-014 only requires that dampened peers *remain* observable, which is satisfied by keeping the health fields the HUD already reads. The clarification session explicitly declined a HUD control. Recorded as a considered decision, not an oversight.

**Principle XVII**: a milestone blog post is required at feature completion. Principle XIV requires human approval before anything externally visible, so the post will be **drafted and offered, never published unprompted**.
