# Tasks: N2N Federation Ergonomics & Reliability

**Input**: Design documents from `/specs/053-n2n-ergonomics/`
**Prerequisites**: plan.md, spec.md (6 user stories), research.md (R1–R7), data-model.md, contracts/ (3), quickstart.md

**Tests**: Included — spec US5 + SC-008 require regression tests that fail against pre-053 behavior; plan mandates pytest units + the two-service loopback harness from 052.

**Organization**: By user story. US1 (async delegation) and US2 (auto-reconnect) are both P1; US1 is the MVP. All work is additive over the frozen 052 core (FR-022).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different files, no dependency on an incomplete task)
- **[Story]**: US1 async tasks · US2 reconnect · US3 endpoint · US4 negotiate · US5 robustness · US6 ergonomics

---

## Phase 1: Setup

- [X] T001 Add 053 `N2N_*` tunables (no values) to `.env.example` per contracts/n2n-daemon-api-delta.md: `N2N_TASK_RETENTION_S`, `N2N_RECONNECT_BACKOFF_MIN_S`, `N2N_RECONNECT_BACKOFF_MAX_S`, `N2N_RECONNECT_UNREACHABLE_AFTER`, `N2N_TASK_POLL_S`
- [X] T002 [P] Extend `tests/n2n/conftest.py` loopback harness with helpers to: simulate a peer daemon restart (drop + relaunch a service), and inject a slow/long-running stub executor for async-task tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema + channel-lifecycle plumbing every story builds on

**⚠️ No user story work begins until this phase is complete**

- [X] T003 Add `delegated_task` table + `federation_peer.endpoint_updated_at` column (additive, `CREATE TABLE/ALTER IF NOT EXISTS`) to the schema in `mcp-servers/protocol-mcp/bgp/federation/manager.py` per data-model.md; leave all 052 tables untouched (FR-022)
- [X] T004 Add an `on_close` hook to `FederationChannel` in `mcp-servers/protocol-mcp/bgp/federation/channel.py` (invoked from `close()`), and make the heartbeat loop increment `consecutive_misses` and call `close()` after `N2N_HEARTBEAT_MISS_LIMIT` misses or a failed send (US2 foundation, FR-006)
- [X] T005 Wire `FederationChannel.on_close` in `mcp-servers/protocol-mcp/bgp/federation/service.py` so a closing channel deregisters itself from `self.channels` (kills the zombie-channel class permanently)
- [X] T006 [P] Unit test channel death→deregister + heartbeat-miss→close in `tests/n2n/test_reconnect.py` (foundation slice)

**Checkpoint**: dead channels self-deregister; task table exists.

---

## Phase 3: User Story 1 — Async task delegation (P1) 🎯 MVP

**Goal**: Long remote operations complete via submit → background run → poll → result, no single call long enough to drop

**Independent Test**: quickstart.md §1 — delegate a multi-minute stub op on the loopback pair; submit returns a task_id in seconds, status polls short, result delivered intact even across a mid-task channel drop

- [X] T007 [US1] Create `mcp-servers/protocol-mcp/bgp/federation/tasks.py`: `DelegatedTask` dataclass + `TaskManager` — create/persist tasks (manager.py table), spawn asyncio background workers running the existing `_exec_skill_gateway`/`_exec_tool_stdio`, track state/progress, store result via the 052 audit result store, retention sweep on `N2N_TASK_RETENTION_S`
- [X] T008 [US1] Rewrite `handle_task_submit` in `mcp-servers/protocol-mcp/bgp/federation/invocation.py` to be async: authorize (unchanged 052 default-deny), create task via TaskManager, spawn worker, return `{task_id, state:"submitted"}` immediately; add `handle_task_status`, `handle_task_result`, `handle_task_cancel` handlers
- [X] T009 [US1] Register `n2n/tasks/status`, `n2n/tasks/result`, `n2n/tasks/cancel` on the channel dispatcher in `mcp-servers/protocol-mcp/bgp/federation/service.py` (submit already registered); keep budget debit + audit on completion (052 semantics)
- [X] T010 [US1] Implement outbound delegation + requester-side poll in `invocation.py`: `submit_task(peer, ...)` returns task_id; a background poller (cadence `N2N_TASK_POLL_S`) fetches status→result and caches it keyed by task_id for retrieval after a drop (FR-004)
- [X] T011 [US1] Add daemon routes `/n2n/tasks` (POST submit, GET list), `/n2n/tasks/<id>` (GET), `/n2n/tasks/<id>/cancel` (POST) in `mcp-servers/protocol-mcp/bgp-daemon-v2.py` per contracts/n2n-task-lifecycle.md (full-body-read + typed errors)
- [X] T012 [P] [US1] Add n2n-mcp tools `n2n_delegate`, `n2n_task_status`, `n2n_task_result`, `n2n_task_cancel` in `mcp-servers/n2n-mcp/server.py` (proxy the new routes; `n2n_delegate` may inline-wait briefly then return task_id)
- [X] T013 [P] [US1] Unit tests for the task lifecycle in `tests/n2n/test_tasks.py`: submit→working→completed, cancel, unknown task_id → terminal status, retention sweep
- [X] T014 [US1] Loopback integration test in `tests/n2n/test_tasks.py`: delegate a slow stub op → task_id in seconds → poll → result. MUST also assert: (a) **each** lifecycle call (submit/status/result) returns in well under the ngrok idle window regardless of total op duration (FR-005 invariant); (b) result survives a mid-task **channel** drop+reconnect (FR-004); (c) result survives a responder **daemon restart** mid-task — restart the responder service, then retrieve the result from the persisted `delegated_task` row (FR-004, US1 scenario 5). Covers US1 scenarios 1–5.

**Checkpoint**: MVP — the CML-clone-style long delegation completes reliably on the loopback pair.

---

## Phase 4: User Story 2 — Channel auto-reconnect (P1)

**Goal**: Federation self-heals after a peer restart with no manual re-dial

**Independent Test**: quickstart.md §2 — restart one loopback service; the other detects the dead channel and re-establishes automatically within bounded time; queries succeed after

- [X] T015 [US2] Implement a reconnect supervisor in `mcp-servers/protocol-mcp/bgp/federation/service.py`: periodic task that, for each `federated` peer with no live channel, re-dials via existing `open_channel` with bounded backoff (`N2N_RECONNECT_BACKOFF_MIN_S`→`MAX_S`); track `ChannelHealth` (state up/reconnecting/unreachable, attempts) in-memory per data-model.md
- [X] T016 [US2] On a request to a peer with no live channel, trigger an on-demand reconnect (or fail fast with `peer_unreachable`) in `service.py`/`invocation.py` rather than hanging on a dead channel (FR-009)
- [X] T017 [US2] Mark peer `unreachable` for display after `N2N_RECONNECT_UNREACHABLE_AFTER` consecutive failures while continuing background retry; surface via ChannelHealth (FR-008)
- [X] T018 [US2] Extend `tests/n2n/test_reconnect.py`: simulate peer restart on the loopback pair → supervisor auto-re-establishes from persisted consent (no re-consent) → query succeeds; verify bounded backoff and unreachable-state transition (covers US2 scenarios 1–4, SC-002)

**Checkpoint**: a restarted peer re-federates automatically.

---

## Phase 5: User Story 3 — Endpoint auto-re-announce (P2)

**Goal**: Endpoint changes propagate automatically; no manual host:port exchange

**Independent Test**: quickstart.md §3 — change one service's endpoint; peer learns it and re-dials with no human step

- [X] T019 [US3] Add `n2n/endpoint_update` handler in `service.py`: accept only for an already-federated identity over its authenticated session (FR-012), update `federation_peer.endpoint_host/port/endpoint_updated_at`, trigger the reconnect supervisor to re-dial preserving lower-AS-initiates role (FR-011)
- [X] T020 [US3] Detect local endpoint change in `bgp-daemon-v2.py` (it already auto-detects the ngrok endpoint at startup — compare against the last-announced value and detect changes there; `agent.py` stays responsible for mesh-directory only) and call `service.reannounce_endpoint()` to send `n2n/endpoint_update` to all federated peers over their live channels (FR-010)
- [X] T021 [P] [US3] Test in `tests/n2n/test_endpoint_reannounce.py`: endpoint_update from a federated identity updates the record + triggers re-dial; an update for a non-federated / wrong-session identity is rejected + logged (FR-012); higher-AS change still results in lower-AS re-dial

**Checkpoint**: endpoint churn no longer needs a human.

---

## Phase 6: User Story 4 — Capability & version negotiation (P2)

**Goal**: Claws on different builds interoperate; pre-053 peers degrade gracefully

**Independent Test**: quickstart.md §4 — two services with different simulated agent flags/reply shapes complete delegated calls; a descriptor-less peer falls back to 052 behavior

- [X] T022 [US4] Create `mcp-servers/protocol-mcp/bgp/federation/negotiate.py`: build local `CapabilityDescriptor` (probe `openclaw agent --help` for supported flags, list reply shapes, proto_version="053", features) and a compare/adapt helper. Probe ONCE and cache the result (module-level/service-held); do NOT shell out to `--help` per invocation — re-probe only on daemon restart.
- [X] T023 [US4] Extend `n2n/hello` in `service.py` to send + store the peer's `capabilities` descriptor; treat a missing descriptor as proto_version "052" (graceful degrade, FR-016); gate async-task use on the peer advertising `async_tasks`
- [X] T024 [US4] Update `gateway.py` to use the locally-probed **cached** agent invoke flag (from negotiate.py, per T022) instead of a hardcoded flag, and confirm tolerant reply extraction covers both `finalAssistantVisibleText` and `payloads` shapes (consolidate the 052 parser fix); return a clear "unsupported by peer" error when a needed feature is absent (FR-016)
- [X] T025 [P] [US4] Test in `tests/n2n/test_negotiate.py`: descriptor exchange + adaptation; missing-descriptor peer → 052 fallback path chosen; unsupported-feature → clear error (covers US4 scenarios 1–4)

**Checkpoint**: build drift no longer breaks federation silently.

---

## Phase 7: User Story 5 — Robustness hardening (P3)

**Goal**: Consolidate the 052 hot-patches as tested, non-regressing requirements

**Independent Test**: quickstart.md §6 — each hardened path has a regression test that fails against pre-053 behavior and passes after (SC-008)

- [X] T026 [P] [US5] Regression test in `tests/n2n/test_robustness.py`: assert the n2n-mcp `_post` client timeout (610s) strictly exceeds the daemon chat/skill timeouts (300/600s) so a completed op is never dropped (FR-017)
- [X] T027 [US5] Harden reply parsing in `gateway.py` `_extract_reply` to tolerate trailing non-JSON (e.g. a `[agent] run … stopReason=stop` line after the envelope) via raw-decode of the first JSON object; add a test with a trailing-log fixture (FR-018) — credit Nick's prototype
- [X] T028 [P] [US5] Regression tests in `tests/n2n/test_robustness.py` for the 052 daemon HTTP hardening: segmented/chunked request body read in full (FR-019), and missing-field requests return a typed error naming the field (not a bare KeyError)

**Checkpoint**: the whack-a-mole fixes can't silently regress.

---

## Phase 8: User Story 6 — Operator ergonomics & health (P3)

**Goal**: One-step connect/trust + live federation health in HUD and via MCP

**Independent Test**: quickstart.md §5 — federate a fresh peer via connect/trust in < 2 min; health surface shows accurate channel/endpoint/task state

- [X] T029 [US6] Add daemon routes `/n2n/health` (per-peer channel_state/last_seen/endpoint_fresh/in_flight_tasks) and `/n2n/connect`, `/n2n/trust` composites in `bgp-daemon-v2.py` per contracts/n2n-daemon-api-delta.md
- [X] T030 [P] [US6] Add n2n-mcp tools `n2n_health`, `n2n_connect`, `n2n_trust` in `mcp-servers/n2n-mcp/server.py`
- [X] T031 [US6] Extend HUD `/api/n2n` in `ui/netclaw-visual/server.js` to aggregate `/n2n/health` + `/n2n/tasks`; extend the claw node in `ui/netclaw-visual/src/main.js` to show channel-state ring, last-seen, endpoint-freshness badge, and live in-flight task progress (FR-021)

**Checkpoint**: federation is observable and one-step to set up.

---

## Phase 9: Polish & Cross-Cutting (Constitution XI Artifact Coherence)

- [X] T032 [P] Update `workspace/skills/n2n-federation/SKILL.md`: async delegation (delegate/status/result/cancel), self-heal behavior, connect/trust flow, health tool
- [X] T033 [P] Update `mcp-servers/n2n-mcp/README.md` (new tools) and `N2N-PEERING-NETCLAWS.md` (async tasks, auto-reconnect, endpoint re-announce, negotiation)
- [X] T034 [P] Update `README.md` (N2N capability description reflects reliability features) and `docs/` reference as needed
- [X] T035 Run `python3 scripts/verify-catalog-coverage.py` (n2n catalog id still covered) and full `pytest tests/n2n/ -v`; regression-check daemon with `N2N_ENABLED=false` behaves identically (FR-022, Constitution XV)
- [ ] T036 Live 3-claw validation per quickstart.md with Nick (65007) + Byrn (65099): async CML-lab clone completes (SC-001), peer restart self-heals (SC-002), endpoint change auto-propagates (SC-003); schedule the 24h soak (SC-007)
- [X] T037 Draft WordPress milestone blog post (the reliability chapter — async delegation, self-healing mesh, the debugging saga that motivated it) for review before publishing (Constitution XVII)

---

## Dependencies

```
Phase 1 (T001–T002)
  └─► Phase 2 (T003–T006)  — schema + channel on_close/heartbeat; T003→T007; T004→T005→T015
        ├─► Phase 3 US1 (T007–T014)  🎯 MVP — async tasks
        ├─► Phase 4 US2 (T015–T018)  — reconnect supervisor (needs T004/T005 channel lifecycle)
        │     └─► Phase 5 US3 (T019–T021) — endpoint update triggers the supervisor (needs US2)
        ├─► Phase 6 US4 (T022–T025)  — negotiation in hello (independent; touches gateway.py alongside US5)
        ├─► Phase 7 US5 (T026–T028)  — robustness (largely independent)
        └─► Phase 8 US6 (T029–T031)  — health surfaces (needs US1 tasks + US2 health for full data)
              └─► Phase 9 (T032–T037) — coherence + live validation
```

- US1 and US2 are both P1 and mostly independent (US1 = tasks.py/invocation; US2 = service supervisor) — can proceed in parallel after Phase 2, though US2 depends on the T004/T005 channel-lifecycle foundation.
- US3 depends on US2 (reuses the reconnect supervisor).
- US4 and US5 both touch `gateway.py` — sequence T024 and T027 to avoid a collision (US4's flag-probe adaptation + US5's parser hardening land together).
- US6 health is richest after US1+US2 exist but degrades gracefully if built earlier.

## Parallel Execution Examples

- **Phase 2**: T004 ∥ T003; T006 after T004/T005.
- **US1**: T012 ∥ T013 (different files) after T008/T011; T014 last.
- **US2/US4/US5** can run as parallel tracks after Phase 2 (different modules), coordinating only on `gateway.py` between T024/T027.
- **Phase 9**: T032–T034 all parallel; T035→T036→T037 sequential.

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + Phase 3 (US1)** — async task delegation, the CML-clone blocker. Ship/demo that (a long remote op completes over the loopback pair and then the live mesh), then add US2 (self-heal) — together these two P1 stories remove the bulk of the operational pain. US3/US4 (P2) eliminate the endpoint/version churn; US5/US6 (P3) harden and polish. Each phase is independently testable on the two-service loopback harness before touching the live mesh.
