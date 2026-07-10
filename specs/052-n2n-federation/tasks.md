# Tasks: NetClaw-to-NetClaw (N2N) Federation

**Input**: Design documents from `/specs/052-n2n-federation/`
**Prerequisites**: plan.md, spec.md (4 user stories), research.md (R1–R8), data-model.md (9 entities), contracts/ (3), quickstart.md

**Tests**: Included — the plan's Testing context mandates pytest units plus a two-daemon loopback integration suite, and SC-003/SC-004 are only verifiable by test.

**Organization**: Grouped by user story; each story phase is an independently testable increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different files, no dependency on an incomplete task)
- **[Story]**: US1 capability exchange · US2 remote invocation · US3 chat · US4 HUD

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package skeletons, constants, config surface — no behavior yet

- [X] T001 Create `mcp-servers/protocol-mcp/bgp/federation/` package with empty modules `__init__.py`, `channel.py`, `manager.py`, `inventory.py`, `authorization.py`, `invocation.py`, `chat.py`, `audit.py` per plan.md source tree
- [X] T002 [P] Add `NCFED_MAGIC = b"NCFED"`, frame constants (4-byte length + 1-byte flags header, 64 KB max payload, heartbeat interval 30 s) to `mcp-servers/protocol-mcp/bgp/constants.py`
- [X] T003 [P] Add all `N2N_*` environment variables with descriptions (no values) to `.env.example` per contracts/n2n-daemon-api.md table (`N2N_ENABLED`, `N2N_DISPLAY_NAME`, `N2N_DAILY_REQUESTS`, `N2N_DAILY_TOKENS`, `N2N_RATE_PER_MIN`, `N2N_APPROVAL_WINDOW_S`, `N2N_INVENTORY_REFRESH_S`, `N2N_TOOL_TIMEOUT_S`, `N2N_SKILL_TIMEOUT_S`, `N2N_CHAT_IDLE_TIMEOUT_S`)
- [X] T004 [P] Create `mcp-servers/n2n-mcp/` skeleton: `server.py` (FastMCP app + `_daemon_get`/`_daemon_post` helpers copied from the protocol-mcp pattern, commit d6e2cb2), `requirements.txt` (fastmcp, httpx)
- [X] T005 [P] Create `tests/n2n/` package with `conftest.py` providing a `tmp_path`-scoped federation.db fixture and a two-daemon loopback harness fixture (spawns two `bgp-daemon-v2.py` instances on distinct localhost ports with `N2N_ENABLED=true`, distinct AS/router-id env)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Channel, discrimination, persistence, consent state machine, audit — every story depends on these

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Implement SQLite schema + data-access layer in `mcp-servers/protocol-mcp/bgp/federation/manager.py`: tables `federation_peer`, `consent_record`, `visibility_setting`, `invocation_grant`, `budget_counter`, `remote_invocation_record`, `approval_request`, `n2n_chat_session` per data-model.md; DB at `~/.openclaw/n2n/federation.db` with idempotent `CREATE TABLE IF NOT EXISTS` init
- [X] T007 Implement consent state machine in `mcp-servers/protocol-mcp/bgp/federation/manager.py`: transitions `not_federated → consent_pending_* → federated → severed → consent_pending_remote` (data-model.md); `consent(peer)`, `sever(peer)` (revoke consent, purge cached inventory, mark severed), identity keying `as<AS>-<router-id>` (FR-002, FR-004, FR-028)
- [X] T008 Implement NCFED framing + handshake in `mcp-servers/protocol-mcp/bgp/federation/channel.py`: frame encode/decode (length + flags + UTF-8 JSON-RPC 2.0), chunking/reassembly for >64 KB messages, heartbeat frames, `NCFED` + AS + router-id handshake with identity validation against an Established BGP session (FR-003), lower-AS-initiates rule, reconnect backoff 5→60 s per contracts/n2n-wire-protocol.md
- [X] T009 Add `NCFED` branch to protocol discrimination in `mcp-servers/protocol-mcp/bgp/agent.py` (~line 271): after first byte `N`, read 4 more; `CTUN` → existing tunnel path unchanged, `CFED` → hand socket to federation channel acceptor; any other → close (FR-027 backwards compat: pre-federation peers unaffected)
- [X] T010 Implement JSON-RPC dispatcher in `mcp-servers/protocol-mcp/bgp/federation/channel.py`: request/response correlation with sender-prefixed ids, notification support, reserved error codes −32001…−32007, method registry the other modules register into; reject every method except `n2n/hello` unless peer state is `federated` (wire-protocol invariant)
- [X] T011 Implement lifecycle methods `n2n/hello`, `n2n/consent_state`, `n2n/sever` in `mcp-servers/protocol-mcp/bgp/federation/manager.py`, wired to the state machine; channel opens automatically when both consents present (FR-001)
- [X] T012 Implement dual-side audit in `mcp-servers/protocol-mcp/bgp/federation/audit.py`: write `remote_invocation_record` rows, store result payloads under `~/.openclaw/n2n/results/`, emit GAIT reference per Constitution IV; helper used by US2/US3
- [X] T013 Wire FederationManager into `mcp-servers/protocol-mcp/bgp-daemon-v2.py`: instantiate when `N2N_ENABLED=true`, register channel acceptor with the agent, add base HTTP routes `/n2n/status`, `/n2n/consent` (POST), `/n2n/kill` (POST) per contracts/n2n-daemon-api.md; daemon starts identically when disabled (FR-027)
- [X] T014 [P] Unit tests for framing/chunking/heartbeat/handshake-rejection in `tests/n2n/test_framing.py` (bad magic, identity mismatch vs BGP session, oversized frame, chunk reassembly)
- [X] T015 [P] Unit tests for consent state machine + kill switch in `tests/n2n/test_consent.py` (mutual-consent gating, sever purges inventory + keeps BGP-facing rows, re-federation requires fresh consent — FR-001/FR-004)

**Checkpoint**: Two loopback daemons can consent, open an NCFED channel, exchange hello, and sever — no capabilities yet

---

## Phase 3: User Story 1 — Capability Exchange & Remote Capability Queries (Priority: P1) 🎯 MVP

**Goal**: Federated peers exchange visibility-filtered inventories; operator asks their own claw about a peer's capabilities with staleness shown

**Independent Test**: quickstart.md §1–2 on the loopback harness — consent both sides, verify inventory arrives, query capabilities, hide an item and verify absence from the next advertisement, stop one daemon and verify stale flag

- [X] T016 [P] [US1] Implement local inventory builder in `mcp-servers/protocol-mcp/bgp/federation/inventory.py`: skills from `workspace/skills/*/SKILL.md` (name + first-paragraph description), MCP servers + tool names from `config/openclaw.json`, capability badge mapping table (`cml-*`→CML, pyATS testbed→pyATS, `meraki-*`→Meraki, …) per research.md R7; document version counter
- [X] T017 [US1] Implement visibility filtering in `mcp-servers/protocol-mcp/bgp/federation/inventory.py`: apply `visibility_setting` rows (all_federated / selected_peers / hidden) at build time so hidden items are absent from the payload (FR-006); defaults per data-model.md
- [X] T018 [US1] Implement no-secrets guard in `mcp-servers/protocol-mcp/bgp/federation/inventory.py`: scan built inventory against values loaded from `~/.openclaw/.env` and refuse to advertise on any match (FR-007, SC-004)
- [X] T019 [US1] Implement `n2n/inventory` push + `n2n/inventory_get` pull in `mcp-servers/protocol-mcp/bgp/federation/inventory.py` registered on the channel dispatcher: send on federate, on local change (watch config/openclaw.json + workspace/skills mtimes), and every `N2N_INVENTORY_REFRESH_S`; receiver caches to `~/.openclaw/n2n/inventories/<identity>.json` with `received_at` (FR-008)
- [X] T020 [US1] Add daemon routes `/n2n/peers/<identity>`, `/n2n/peers/<identity>/inventory` (with `stale` computed as received_at older than 2× refresh interval), `/n2n/visibility` (POST → rebuild + re-advertise) in `mcp-servers/protocol-mcp/bgp-daemon-v2.py` (FR-009)
- [X] T021 [P] [US1] Implement n2n-mcp tools `n2n_status`, `n2n_consent`, `n2n_kill` (with confirmation guidance in docstring), `n2n_peer_capabilities`, `n2n_compare_capabilities`, `n2n_set_visibility` in `mcp-servers/n2n-mcp/server.py` per contracts/n2n-mcp-tools.md, all proxying `/n2n/*`, GCF-serialized responses
- [X] T022 [P] [US1] Unit tests for inventory build, visibility filter, and no-secrets invariant in `tests/n2n/test_inventory.py` (hidden item absent from payload; planted fake secret in a skill description blocks advertisement)
- [X] T023 [US1] Loopback integration test in `tests/n2n/test_two_daemon_loopback.py`: consent → federated → inventory exchanged → capability query via `/n2n/peers/<id>/inventory` → visibility change re-advertises → one side stops → stale flag set → **restart the stopped daemon on a DIFFERENT localhost port and assert `federated` state, grants, and cached inventory survive with NO re-consent and the channel re-establishes by identity (FR-028, endpoint-churn edge case)** → sever (covers US1 acceptance scenarios 1–5)

**Checkpoint**: MVP — "does the peer have CML?" answerable end-to-end on the loopback pair and on the live mesh (John ↔ Nicholas)

---

## Phase 4: User Story 2 — Authorized Remote Tool/Skill Invocation (Priority: P2)

**Goal**: Default-deny allowlisted invocation with approvals, budgets, rate limits, dual-side audit

**Independent Test**: quickstart.md §3 on the loopback harness — grant one tool, invoke it (succeeds), invoke a non-granted tool (explicit refusal), approval-gated grant blocks then approves, budget exhaustion refuses; audit rows on both sides

- [X] T024 [P] [US2] Implement authorization engine in `mcp-servers/protocol-mcp/bgp/federation/authorization.py`: grant lookup (default-deny, FR-012), per-peer rate limiter (`N2N_RATE_PER_MIN`), `budget_counter` day-keyed debit with request+token caps (FR-017), approval workflow rows with `expires_at` enforcement (FR-013); returns typed decisions matching wire error codes
- [X] T025 [P] [US2] Implement MCP stdio tool executor in `mcp-servers/protocol-mcp/bgp/federation/invocation.py`: spawn target server per its `config/openclaw.json` command, JSON-RPC `initialize` → `tools/call` → collect result, timeout `N2N_TOOL_TIMEOUT_S`, kill on expiry; when `security.mode == "defenseclaw"`, run DefenseClaw tool inspection on tool name + arguments before spawn and refuse with `-32008 guardrail_blocked` on rejection (research.md R3, FR-014)
- [X] T026 [US2] Implement gateway task executor for delegated skills in `mcp-servers/protocol-mcp/bgp/federation/invocation.py`: POST to local gateway OpenAI-compatible API with skill-execution system context, stream progress, count tokens against budget, timeout `N2N_SKILL_TIMEOUT_S` (research.md R3; FR-014 — remote policies/DefenseClaw apply)
- [X] T027 [US2] Register wire methods `n2n/tools/call`, `n2n/tasks/submit`, `n2n/tasks/status`, `n2n/tasks/result`, `n2n/tasks/cancel` on the channel dispatcher in `mcp-servers/protocol-mcp/bgp/federation/invocation.py`: inbound path = authorize (T024) → approval hold if required → execute (T025/T026) → audit (T012) → respond; outbound path = request + await/stream, mark results remote-untrusted (FR-016)
- [X] T028 [US2] Add daemon routes `/n2n/grants` (GET/POST), `/n2n/grants/<id>` (DELETE), `/n2n/invoke` (POST + status poll route), `/n2n/approvals` (GET), `/n2n/approvals/<id>` (POST approve/deny), `/n2n/audit` (GET), `/n2n/config` (POST budgets) in `mcp-servers/protocol-mcp/bgp-daemon-v2.py` per contracts/n2n-daemon-api.md
- [X] T029 [P] [US2] Implement n2n-mcp tools `n2n_grant`, `n2n_revoke_grant`, `n2n_list_grants`, `n2n_invoke`, `n2n_approvals`, `n2n_approve`, `n2n_deny`, `n2n_audit`, `n2n_config` in `mcp-servers/n2n-mcp/server.py` per contracts/n2n-mcp-tools.md, refusal codes surfaced verbatim, remote results wrapped `{"trust": "remote-untrusted"}`
- [X] T030 [US2] Approval delivery (proactive push, FR-013): on new `approval_request`, the daemon POSTs a notification to the local gateway (existing message-injection surface, humanrail-escalation pattern) so the prompt reaches the operator's connected channels (Slack/Webex/CLI) without polling; fall back to daemon log + `/n2n/approvals` when the gateway is down; implement in `mcp-servers/protocol-mcp/bgp/federation/authorization.py` and document the respond-via-`n2n_approve`/`n2n_deny` flow in `workspace/skills/n2n-federation/SKILL.md` (research.md R6)
- [X] T031 [P] [US2] Unit tests for authorization in `tests/n2n/test_authorization.py`: default-deny, grant match, rate-limit window, budget request+token exhaustion and midnight-UTC reset, approval expiry (FR-012/013/017)
- [X] T032 [US2] Extend loopback integration test in `tests/n2n/test_two_daemon_loopback.py`: grant → `n2n/tools/call` against a stub MCP server → success + dual audit rows; non-granted call → `-32001`; approval-gated → `-32002` then approve → success; budget cap 1 → second call `-32004` (covers US2 acceptance scenarios 1–6)

**Checkpoint**: "List the labs on Nicholas's CML server" works under grant + approval + budget on the live mesh

---

## Phase 5: User Story 3 — Claw-to-Claw Chat (Priority: P3)

**Goal**: Attributed, rate-limited operator↔remote-agent conversation with streamed replies and reviewable transcripts

**Independent Test**: quickstart.md §4 on the loopback harness — chat enabled both sides: question → streamed attributed reply; disabled side refuses; flood hits rate limit; transcripts on both sides

- [X] T033 [US3] Implement chat session manager + wire methods `n2n/chat/open|message|stream|close` in `mcp-servers/protocol-mcp/bgp/federation/chat.py`: per-peer enable check (FR-018), rate limit + shared budget debit (FR-020), relay inbound messages to local gateway API and stream reply chunks back (FR-019), idle close after `N2N_CHAT_IDLE_TIMEOUT_S`, append-only transcript under `~/.openclaw/n2n/chats/` + `n2n_chat_session` rows + audit (FR-022)
- [X] T034 [US3] Add daemon routes `/n2n/chat/open`, `/n2n/chat/send` (long-poll chunks), `/n2n/chat/close`, `/n2n/chats` and `chat_enabled` handling in `/n2n/config` in `mcp-servers/protocol-mcp/bgp-daemon-v2.py`
- [X] T035 [P] [US3] Implement n2n-mcp `n2n_chat` tool (send + collect streamed reply, return `session_id` for continuation, response attributed to peer identity) in `mcp-servers/n2n-mcp/server.py`
- [X] T036 [US3] Extend loopback integration test in `tests/n2n/test_two_daemon_loopback.py` with a stub gateway (canned completion response): chat round-trip attributed both sides; `chat_enabled=false` refusal; rate-limit rejection; transcript files exist (covers US3 acceptance scenarios 1–4)

**Checkpoint**: "Ask Byrn's claw why OSPF area 0 is flapping" flows end-to-end

---

## Phase 6: User Story 4 — HUD Federation View (Priority: P4)

**Goal**: Expandable claw nodes with inventory, badges, freshness, pending approvals, chat affordance

**Independent Test**: quickstart.md §5 — one federated + one non-federated peer: federated node expands with inventory/badges/freshness and working chat panel; non-federated shows state only; sever updates the node without restart

- [X] T037 [US4] Add `/api/n2n` aggregation endpoint to `ui/netclaw-visual/server.js` (mirror of `/api/bgp` pattern): merges daemon `/n2n/status`, per-peer inventories, pending approvals; graceful `{available:false}` when daemon lacks N2N (FR-027)
- [X] T038 [US4] Extend claw nodes in `ui/netclaw-visual/src/` scene code: federation state ring/badge (not_federated / pending / federated / severed), click-to-expand panel listing skills, MCP tools, capability badges, inventory freshness, pending approvals — remote inventory styled distinct from local (FR-023/FR-024/FR-026, polling like existing BGP refresh)
- [X] T039 [US4] Add chat panel to the expanded claw node in `ui/netclaw-visual/src/`: drives `/api/n2n` → daemon `/n2n/chat/*`, streams reply chunks, attributes messages to peer identity; disabled state when `chat_enabled=false` (FR-025)

**Checkpoint**: All four stories demonstrable on the live three-claw mesh from the HUD

---

## Phase 7: Polish & Cross-Cutting (Constitution XI Artifact Coherence)

- [X] T040 [P] Write `workspace/skills/n2n-federation/SKILL.md`: purpose, all n2n-mcp tools, federate/browse/grant/invoke/chat/sever workflows, required env vars, examples (Constitution VII/XII; completes T030 doc)
- [X] T041 [P] Write `mcp-servers/n2n-mcp/README.md`: tool inventory, env vars, stdio transport, install steps (MCP Server Standards)
- [X] T042 [P] Register `n2n-mcp` in `config/openclaw.json` (stdio, command + args, `N2N_*` env passthrough)
- [X] T043 [P] Add catalog entry `"n2n|Federation|N2N Federation|Peer NetClaws: capability exchange, remote invocation, claw-to-claw chat"` to `scripts/lib/catalog.sh` and `component_install_n2n()` (pip deps, env prompts for `N2N_ENABLED`/`N2N_DISPLAY_NAME`, consent quickstart pointer) to `scripts/lib/install-steps.sh`
- [X] T044 Run `python3 scripts/verify-catalog-coverage.py` and fix any gap so `n2n-mcp` is reachable from the `n2n` catalog id
- [X] T045 [P] Update `README.md` (capability description + MCP/tool counts), `TOOLS.md` reference, and `SOUL.md` capability summary for N2N federation
- [X] T046 Run full test suite `pytest tests/n2n/ -v` plus regression check that daemon with `N2N_ENABLED=false` behaves byte-identically on BGP paths (FR-027, Constitution XV)
- [ ] T047 Live-mesh validation per quickstart.md verification checklist with Nicholas (AS 65007) and Byrn (AS 65099): SC-001…SC-008 spot checks + schedule the 24 h SC-009 soak
- [X] T048 Draft WordPress milestone blog post (what was built, why, key decisions — NCFED mux, MCP/A2A hybrid, budgets; lessons learned) and present for review before publishing (Constitution XVII)

---

## Dependencies

```
Phase 1 (T001–T005)
  └─► Phase 2 (T006–T015)  — T006→T007→(T011,T013); T008→(T009,T010); T012 after T006
        └─► Phase 3 US1 (T016–T023)  — MVP; T016→T017→T018→T019→T020; T021 after T013; T023 last
              ├─► Phase 4 US2 (T024–T032) — needs channel+consent+inventory (grants reference advertised names)
              │     └─► Phase 5 US3 (T033–T036) — reuses budget/rate/audit from US2 (FR-020)
              └─► Phase 6 US4 (T037–T039) — needs US1 data; approval list/chat panel richer after US2/US3 but degrade gracefully
                          └─► Phase 7 (T040–T048) — after all implemented stories
```

- US2 depends on US1 (inventory names what is grantable).
- US3 depends on US2 (shared budget/rate/audit engine).
- US4 depends only on US1 for its core view; T037/T038 can start once T020 exists.

## Parallel Execution Examples

- **Phase 1**: T002, T003, T004, T005 all parallel after T001.
- **Phase 2**: T008 ∥ T006; then T009+T010 ∥ T007; T014 ∥ T015 once their subjects exist.
- **US1**: T016 ∥ T021 (different files); T022 ∥ T023 after implementation tasks.
- **US2**: T024 ∥ T025 ∥ T029; T031 ∥ T032 after wiring (T027/T028).
- **US4**: T038 ∥ T039 after T037.
- **Phase 7**: T040–T043 and T045 all parallel; T044 after T042/T043; T046→T047→T048 sequential.

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + Phase 3 (US1)** — 23 tasks: two claws federate and browse each other's capabilities. Ship/demo that on the live John↔Nicholas mesh, then add US2 (invocation), US3 (chat), US4 (HUD) as independent increments, closing with the coherence phase. Each checkpoint is demoable on the loopback harness without live peers.
