# Tasks: Federation Inbound-Call Observability

**Feature**: `100-federation-log-observability` | **Date**: 2026-08-06
**Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/interfaces.md](./contracts/interfaces.md)

## Format: `[ID] [P?] [Story] Description`

- **[P]** — parallelizable (different file, no incomplete dependency)
- **[US1..US5]** — user story this task serves

## Path Conventions

All paths relative to repo root. Daemon package is `mcp-servers/protocol-mcp/`;
tests live in `tests/n2n/` (62 existing files, `test_*.py`).

## Interpreter

**All test invocations use `/usr/bin/python3` (3.14.4) explicitly** — the interpreter
`netclaw-mesh.service` actually runs. The repo `.venv/` is Python 3.13.0b1 with a
different `asyncio`, and FR-017/FR-030 are asyncio-behavior-dependent (research R1).
`pytest 9.1.1` is available under `/usr/bin/python3` — verified.

## Tests

Test tasks **are** included. Not a default: FR-019 ("unexpected internal faults MUST
continue to be reported at error severity with a stack trace") is a *preservation*
requirement whose violation is silent — a too-broad `except` would satisfy every other
requirement here while quietly swallowing real bugs. That regression is only catchable
by test. Likewise FR-031 (flapping must not defeat dampening) and FR-012 (transients
must not be penalized) are opposing behaviors that a single implementation must satisfy
simultaneously; they are asserted, not eyeballed.

## Ordering rationale

Phases follow plan.md "Phase Sequencing and Risk" — highest-noise/lowest-risk first, so
the log becomes readable *before* the risky dial-scheduling change is verified against it:

1. **US3 + FR-030/038** — severity/classification only, no behavioral change.
2. **US1** — additive, single choke point.
3. **US5** — outbound outcome resolution, adjacent to US1's choke point.
4. **US2** — dampening; touches dial scheduling. Highest risk.
5. **US4** — endpoint retirement; independent.

---

## Phase 1: Setup

- [x] T001 Capture the live baseline per [quickstart.md](./quickstart.md) §0 — dead-peer failure count per 10 min, benign-traceback count, `eof_received` count, and the `federation_peer` endpoint table. **SC-003 requires a ≥90% reduction and is unmeasurable without this.** Record the numbers in the PR description.
- [x] T002 Back up the database: `cp ~/.openclaw/n2n/federation.db ~/.openclaw/n2n/federation.db.bak-$(date +%Y%m%d-%H%M%S)`
- [x] T003 [P] Confirm `/usr/bin/python3 -m pytest tests/n2n/ -q` passes **before** any change, so later failures are attributable to this work and not inherited.

**Checkpoint**: baseline recorded, DB backed up, suite green.

---

## Phase 2: Foundational — configuration surface

**⚠️ Blocks US2 and FR-038.** Both read these settings.

- [x] T004 Add the six env vars from [contracts/interfaces.md](./contracts/interfaces.md) §1 to `FederationService.__init__` in `mcp-servers/protocol-mcp/bgp/federation/service.py`, beside the existing `N2N_RECONNECT_*` reads at `:83-85`: `N2N_RECONNECT_DAMPEN` (default `1`), `_DEAD_CEILING_S` (`900`), `_DEAD_AFTER` (`20`), `_ENDPOINT_STALE_S` (`86400`), `_SUMMARY_INTERVAL_S` (`300`), `_STABLE_AFTER_S` (`120`).
- [x] T005 Parse each with a fallback-on-malformed helper — a typo in an env file MUST NOT prevent daemon startup (contracts §1.1). Do **not** let `int()` raise out of `__init__`.
- [x] T006 [P] Document all six in `.env.example` with names and comments but **no values** (Constitution XI/XIII).
- [x] T007 [P] Test `tests/n2n/test_log_dampening_config_100.py`: defaults match contracts §1 exactly; malformed values fall back rather than raise; `N2N_RECONNECT_DAMPEN=0` is readable as a bypass flag.

**Checkpoint**: settings load with today's behavior preserved; daemon starts with a garbage env value.

---

## Phase 3: US3 + FR-030/038 — benign disconnects (Priority: P2)

**Goal**: a probe produces one quiet line, not a ten-line traceback — making the log readable for every later verification.

- [x] T008 [US3] In `mcp-servers/protocol-mcp/bgp/agent.py`, wrap **only** the pre-handshake reads (`:278` `readexactly(1)`, `:282` `readexactly(4)`) in a narrow `except (asyncio.IncompleteReadError, ConnectionResetError, asyncio.TimeoutError)` that logs one `debug` line naming source and reason, then returns. Format per contracts §5.4.
- [x] T009 [US3] Verify the narrow handler sits **before** the catch-all at `:498-499` and does not widen it. The catch-all keeps `exc_info=True` (FR-019). Leave the `Invalid N-magic` `warning` at `:307` exactly as-is (FR-018).
- [x] T010 [US3] Test `tests/n2n/test_benign_disconnect_100.py`: zero-byte connect → exactly one line, no traceback (SC-004); truncated preamble → one low-severity line; complete-but-invalid magic → still `WARNING` (FR-018); **an unexpected internal fault still reaches the catch-all with a traceback (FR-019)** — the regression guard that justifies this phase's tests.
- [x] T011 Create `mcp-servers/protocol-mcp/bgp/federation/logfilter.py` — a `logging.Filter` dropping **only** the message `returning true from eof_received() has no effect when using ssl` on the `asyncio` logger (research R5, FR-030). One module so its narrowness is reviewable in one place.
- [x] T012 Install the filter during daemon startup in `mcp-servers/protocol-mcp/bgp-daemon-v2.py`.
- [x] T013 [P] Test `tests/n2n/test_logfilter_eof_100.py`: the target message is dropped; **other `asyncio` warnings pass through unchanged** (FR-030 explicitly forbids silencing the logger wholesale). Run under `/usr/bin/python3` — this asserts stdlib behavior (research R1).
- [x] T014 [FR-038] Add `_probe_health` per-source-IP collapsing to `bgp/agent.py` per [data-model.md](./data-model.md) §5: summarize non-protocol connections at `INFO` on the `SUMMARY_INTERVAL_S` cadence, cap the dict at 512 entries evicting oldest `summary_at`.
- [x] T015 [FR-038] Test repeated probes collapse to a periodic summary; the dict never exceeds 512 entries under rotating source IPs; **a genuine enrolled-device failure remains visible and distinguishable** (FR-038). *Implemented in `tests/n2n/test_benign_disconnect_100.py` rather than a separate `test_probe_dampening_100.py` — probe collapsing is reached through the same `_note_benign_disconnect` path the FR-017 tests exercise, so splitting the file would have separated assertions about one function.*

**Checkpoint**: `python3 -c "import socket; socket.create_connection(('127.0.0.1',1179)).close()"` yields one line, no traceback. Zero `eof_received` lines after a channel close.

---

## Phase 4: US1 — inbound call unmistakable (Priority: P1)

**Goal**: enrich the one existing audit line; add the arrival event. **No second line per call** (FR-032).

> **Scope correction (research R2)**: inbound calls are *already* logged at info with peer, target, decision and outcome. FR-001/002/004/006 are **regression guards, not new work**. Only FR-003, FR-005, FR-032, FR-033 need code.

- [x] T016 [US1] In `mcp-servers/protocol-mcp/bgp/federation/audit.py`, interpolate `request_id` into the existing `logger.info` at `:77-79` as ` req=<first 10 chars>`, omitted entirely when `None` — mirroring how `gait=` is already handled (FR-005, contracts §5.2).
- [x] T017 [US1] Key the level off `outcome`, not `decision`: `warning` for `denied`/`timeout`/`error`, `info` otherwise (FR-003, [data-model.md](./data-model.md) §3.1). Keep field order and the `AUDIT[` prefix byte-identical so existing greps survive.
- [x] T018 [US1] Confirm exactly one line is emitted per `record()` call — enrich in place, add no parallel logger (FR-032).
- [x] T019 [US1] Add the arrival event (FR-033) at inbound handler entry in `mcp-servers/protocol-mcp/bgp/federation/invocation.py`, at `info`, carrying method and `req=` per contracts §5.1. Emit it **once at the shared entry**, not per branch, so a hung call is visible without inflating volume.
- [x] T020 [US1] Audit the new lines for FR-007: no secrets, credentials, key material, or full payloads. Log target *names*, never argument values.
- [x] T021 [US1] Test `tests/n2n/test_inbound_log_enrichment_100.py`: `req=` present and prefix-matches the persisted `request_id` (FR-005); `outcome="denied"` emits at `WARNING` and `success` at `INFO` (FR-003); exactly one audit line per `record()` (FR-032); arrival line precedes the decision line (FR-033); **existing fields all still present (FR-001/002/004 regression guard)**; no secret-shaped content (FR-007).
- [x] T022 [US1] Test that `Auditor.record()` ignores dampening settings entirely — denials can never be suppressed (FR-003 second clause).

**Checkpoint**: `journalctl -p warning | grep 'AUDIT\['` shows refusals and no successes. Every audit line carries `req=`.

---

## Phase 5: US5 — outbound outcome resolution (Priority: P1)

**Goal**: an outbound call reaches a terminal recorded state instead of staying `pending` forever.

- [x] T023 [US5] Locate every outbound `audit.record(..., outcome="pending")` call site (7 `pending` uses exist across `bgp/federation/*.py`) and identify which lack a terminal follow-up write.
- [x] T024 [US5] Add terminal-outcome resolution keyed to the **same `request_id`** used at initiation (FR-034/035), so both parties reconcile one call by one identifier.
- [x] T025 [US5] Map a remote refusal to `denied` rather than discarding it (FR-036), and a timeout or dropped channel to a terminal state rather than leaving `pending` (FR-037).
- [x] T026 [US5] Test `tests/n2n/test_outbound_outcome_100.py`: a successful outbound resolves to `success`; a remote refusal records `denied` (FR-036); a timeout resolves to `timeout` (FR-037); a dropped channel before response still reaches terminal state; the terminal row joins the initiating row by `request_id` (FR-035); **no outbound call remains `pending` after its channel closes**.

**Checkpoint**: no `pending` rows survive their call's completion.

---

## Phase 6: US2 — dead-peer dampening (Priority: P2) ⚠️ HIGHEST RISK

**Goal**: bound dead-peer log volume without delaying any healthy peer.

> **plan.md primary risk**: FR-010 (back long-dead peers off to 15 min) versus FR-012 (never penalize a transient blip). Resolved by the **two-signal test** — consecutive failures **and** endpoint staleness — with FR-013 guaranteeing an endpoint change resets immediately.

- [x] T027 [US2] Extend the health dict in `service.py` with `connected_since`, `cause_sig`, `suppressed`, `summary_at`, `dampened` per [data-model.md](./data-model.md) §1. **Keep `state`/`attempts`/`next_retry_at`/`last_seen` names and types** — the HUD and `/n2n/health` read them (FR-014, FR-027).
- [x] T028 [US2] Add the normalized cause signature helper — `f"{type(exc).__name__}:{errno}"`, no addresses or message text (FR-015, data-model §1.3). Verbatim comparison would defeat collapsing, since live cause strings carry variably-ordered IP lists.
- [x] T029 [US2] **Change the reset semantics** (FR-031): in `open_channel` success at `service.py:709-710`, set `state`/`last_seen`/`connected_since` but **stop clearing `attempts`/`suppressed`/`dampened`**. This is the single riskiest edit in the feature — the current wholesale reset is exactly what lets flapping bypass dampening (research R3).
- [x] T030 [US2] In the supervisor loop, clear dampening only once a live channel has been up ≥ `STABLE_AFTER_S` (FR-031).
- [x] T031 [US2] Implement the two-signal escalation (FR-010/011): ceiling becomes `DEAD_CEILING_S` only when `attempts >= DEAD_AFTER` **and** endpoint older than `ENDPOINT_STALE_S`; otherwise today's `_backoff_max`. Treat `endpoint_updated_at IS NULL` as stale (data-model §2).
- [x] T032 [US2] Detect an endpoint change between iterations and reset `attempts`/`dampened`/`next_retry_at` immediately (FR-013), so a re-registering peer reconnects in seconds regardless of dampening history.
- [x] T033 [US2] Replace the per-attempt `WARNING` at `service.py:711` with collapse-and-summarize: log immediately on a changed `cause_sig` (FR-015), otherwise increment `suppressed` and emit the summary every `SUMMARY_INTERVAL_S` with attempt count and covered period (FR-008/009), format per contracts §5.3.
- [x] T034 [US2] Honor `N2N_RECONNECT_DAMPEN=0` as a complete bypass — no suppression, no summaries, no escalated ceiling (FR-028, SC-010).
- [x] T035 [US2] Expose `dampened` on `/n2n/health` additively; rename and retype nothing (FR-014).
- [x] T036 [US2] Test `tests/n2n/test_dead_peer_dampening_100.py`, asserting the opposing requirements together: a single transient failure reconnects no later than today and never dampens (FR-012, SC-005); a flapping peer does **not** reset `attempts` on brief connects and stays dampened (FR-031, SC-012); escalation requires **both** signals; an endpoint change resets immediately (FR-013, SC-006); differing causes are not collapsed (FR-015); N dead peers produce ≤ N lines per interval (FR-016); a dampened peer stays `FEDERATED` with health observable (FR-013/014); `DAMPEN=0` restores per-attempt logging (FR-028).

**Checkpoint**: dead-peer volume ≥90% below the T001 baseline over ≥30 min (SC-003), with no healthy peer's reconnect delayed.

---

## Phase 7: US4 — endpoint retirement (Priority: P3)

**Goal**: retire a stale endpoint conversationally, zero SQL (FR-026).

- [x] T037 [US4] Add `forget_peer_endpoint(identity)` to `FederationManager` in `manager.py`, beside `upsert_peer` at `:289-317`. Clear `endpoint_host`, `endpoint_port`, `endpoint_updated_at` **together**; return the prior endpoint per contracts §2. Idempotent when already absent; `KeyError` for unknown identity. Do **not** overload `upsert_peer` with sentinels (research R7).
- [x] T038 [US4] Record the retirement through the existing `Auditor.record()` GAIT path with `event="endpoint-forgotten"` and `actor` (FR-025, Constitution IV). No new trail.
- [x] T039 [US4] Leave a live channel to that peer running (research R7 resolution) — the endpoint is consulted only for dialling; tearing it down would convert a cleanup into an outage.
- [x] T040 [US4] Add `POST /n2n/peers/forget-endpoint` to `bgp-daemon-v2.py` per contracts §3, matching the existing dispatch style at `:464`. `400` on missing `peer`, `404` on unknown identity.
- [x] T041 [US4] Add the `n2n_forget_endpoint` tool to `mcp-servers/n2n-mcp/server.py` per contracts §4, using the existing `_gcf_dumps` serializer. **Tool count 38 → 39.**
- [x] T042 [US4] Test `tests/n2n/test_forget_endpoint_100.py`: all three columns cleared together; `state`/`chat_enabled`/`trust_model`/`pinned_fp`/audit history unchanged (FR-022); idempotent second call (contracts §2); unknown identity → `KeyError`/`404`; supervisor stops dialling without restart (FR-023); re-registration restores dialling with no operator action (FR-024); retirement is attributable (FR-025).

**Checkpoint**: a stale endpoint is retirable via the MCP tool with zero database writes (SC-007).

---

## Phase 8: Documentation & Polish (Constitution XI/XII)

- [x] T043 [P] Add `n2n_forget_endpoint` to `TOOLS.md`; update the `n2n-mcp` count to 39.
- [x] T044 [P] Update `README.md` if it states an `n2n-mcp` tool count (Constitution XII — counts must be accurate; nine drifted unnoticed before spec 075).
- [x] T045 Run `python3 scripts/reconcile-mcp.py >/dev/null 2>&1; echo $?` — must be `0`. **CI runs the same command and fails the merge on non-zero.** Never read this exit code through a pipe (CLAUDE.md).
- [x] T046 Run the full suite: `/usr/bin/python3 -m pytest tests/n2n/ -q`. All 62 pre-existing files plus the 8 added here must pass.
- [x] T047 Answer the deferred Out-of-Scope question explicitly: **should the dampening principle also govern BGP session retry reporting?** The `fd00:ee::0` flap is config, not code, but exhibits the identical defect shape (spec.md Out of Scope). Record the answer — a follow-on spec, or a documented decision not to.
- [ ] T048 Walk [quickstart.md](./quickstart.md) §2–§7 against the running daemon and tick every box, including the §6 regression guards.
- [ ] T049 Draft the Principle XVII milestone blog post. **Offer it — never publish unprompted** (Principle XIV).
- [ ] T050 Verify the branch is still `100-federation-log-observability` before committing — other agents switch branches in this shared checkout. Then commit and open the PR, including the T001 baseline and post-change numbers so SC-003 is evidenced, not claimed.

---

## Dependencies

```
Phase 1 (setup) ──► Phase 2 (config) ──┬──► Phase 3 (US3)  [independent]
                                       ├──► Phase 6 (US2)  [needs config]
                                       └──► FR-038 in T014 [needs config]

Phase 3 ──► Phase 4 (US1) ──► Phase 5 (US5)   [US5 shares US1's choke point]

Phase 7 (US4) ── independent of 3/4/5/6; needs only Phase 1

Phase 8 ──► requires all above
```

- **T004/T005 block** T014, T031, T033, T034 — all read the settings.
- **T029 blocks** T030, T036 — the reset change is the precondition for dampening working at all.
- **T037 blocks** T040 → T041 — manager, then route, then tool.
- **T016/T017 block** T021; **T019 blocks** T021.
- Phases 3, 4+5, 6, 7 are each independently shippable and independently verifiable.

## Parallel opportunities

- T006, T007 alongside T004/T005 (different files).
- T011–T013 (logfilter) alongside T008–T010 (agent) — different modules.
- T043, T044 alongside any implementation phase.
- Phase 7 (US4) entirely parallel to Phases 3–6 — different files, no shared state.

## Independent test criteria per story

| Story | Independently verifiable by |
|---|---|
| US1 (P1) | One inbound call: arrival + one enriched line, `req=` joins to the audit row, denial at `WARNING`. |
| US2 (P2) | 30 min with a dead peer: ≥90% volume reduction, healthy peer unaffected, flapping stays dampened. |
| US3 (P2) | One zero-byte connect: one line, no traceback. One channel close: no `eof_received`. |
| US4 (P3) | One MCP tool call: endpoint cleared, peer otherwise untouched, dialling stops, zero SQL. |
| US5 (P1) | One outbound call per outcome class: none left `pending`. |
