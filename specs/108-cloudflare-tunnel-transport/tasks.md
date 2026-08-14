# Tasks: Cloudflare Tunnel as a Hardened eN2N Transport

**Input**: Design documents from `/specs/108-cloudflare-tunnel-transport/`
**Prerequisites**: plan.md, spec.md (clarified 2026-08-14, 4 Qs), research.md (R0 confirmed live gap + R1–R5), data-model.md, contracts/interfaces.md, quickstart.md

**Tests**: Included — spec defines an Independent Test per story + measurable SCs; mirrors 063's own testing bar (integration reuses the existing `tests/n2n/` loopback pattern).

**Phase order = implementation order** (not strictly spec priority order): US1 (P1, pure ops + small persistence-field addition, zero risk to existing peers) first, then US3 (P3, posture display — small, depends only on US1's new field existing) next since it's low-risk and immediately useful once US1 lands, then **US2 (P2) last** because it's the one story with an external dependency (Cloudflare Access configuration) and a security-relevant default (off) that deserves to be validated against a real US1 deployment first, not built in parallel with it.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [ ] T001 [P] Add `N2N_TRANSPORT_HEALTH_CHECK` (bool, default enabled) to `.env.example`, documented per data-model.md §4 — controls whether the local tunnel/DNS health probe runs at all (allows a full no-op for operators who never touch this feature)
- [ ] T002 [P] Document the TCP/private-network-mode-only decision (never HTTP(S) ingress) in `mcp-servers/protocol-mcp/README.md` or equivalent ops doc, with the confidentiality rationale from research.md R1 — this is a fixed decision, not operator-configurable, and needs to be findable before anyone stands up a `cloudflared` config

---

## Phase 2: Foundational (blocking prerequisites)

- [ ] T003 In `mcp-servers/protocol-mcp/bgp/federation/manager.py`, add `transport` (text, default `'ngrok'`) and `edge_gate` (text, default `'none'`) columns to the `federation_peer` schema (migration-safe: `ALTER TABLE ... ADD COLUMN ... DEFAULT ...`, matching how 063 relied on already-existing columns — here the columns are new but the pattern of additive, defaulted columns is identical) (data-model.md §1)
- [ ] T004 [P] In `mcp-servers/protocol-mcp/bgp/federation/manager.py`, extend `upsert_peer()` to accept optional `transport` and `edge_gate` kwargs, writing them only when explicitly supplied (never overwritten to a default on an unrelated call, mirroring how `endpoint_host`/`endpoint_port` are only touched when supplied) (FR-001, FR-005)
- [ ] T005 [P] In `mcp-servers/protocol-mcp/bgp/federation/manager.py`, extend `get_peer()`/`list_peers()` to include `transport` and `edge_gate` in returned peer dicts (needed by every downstream US)
- [ ] T006 Unit test in `tests/n2n/test_transport_field_108.py`: `upsert_peer` with no `transport`/`edge_gate` args leaves existing values unchanged; a peer inserted with no explicit values defaults to `('ngrok', 'none')`; explicit values round-trip through `get_peer`/`list_peers` (SC-005 — zero regression for existing rows)

**Checkpoint**: schema + manager primitives ready; no external behavior has changed yet (all new fields default to today's implicit reality).

---

## Phase 3: User Story 1 — Endpoint never goes stale (P1) 🎯 MVP

**Goal**: A claw's advertised eN2N endpoint survives `cloudflared`/host restarts with zero manual `n2n_forget_endpoint` + re-dial cycles, closing the confirmed live gap between spec 063's endpoint-persistence fix and reality (research.md R0).

**Independent Test**: bind a Cloudflare Tunnel to a fixed hostname; restart `cloudflared` and the host repeatedly over an extended period; confirm a federated peer's stored endpoint for this claw never needs manual correction and every reconnect succeeds against the same hostname (spec.md US1 Independent Test, SC-001).

- [ ] T007 [US1] In `mcp-servers/protocol-mcp/bgp-daemon-v2.py` `/n2n/connect` handler, accept an optional `transport` field (`ngrok`\|`cloudflare_tunnel`\|`other`, default `ngrok` when omitted — existing callers/scripts unaffected) and pass it through to `open_channel`/`upsert_peer` (contracts/interfaces.md, FR-001, FR-008)
- [ ] T008 [US1] In `mcp-servers/protocol-mcp/bgp/federation/service.py` `open_channel`, extend the existing "successful, authenticated channel" persistence call (the same call site 063/T004 added) to also pass through `transport` when supplied, using T004's extended `upsert_peer` signature — no change to the success/failure-path logic itself, only the additional field (FR-001, reuses 063's precondition exactly)
- [ ] T009 [P] [US1] Author the ops-layer deployment doc/script mirroring spec 057's `in2n-services.py` pattern: `scripts/cloudflared-transport.sh` (or extend `in2n-services.py`) to generate a durable systemd unit for `cloudflared tunnel run <name>`, so a Cloudflare Tunnel is provisioned repeatably rather than hand-run (spec.md US1 durability requirement, FR-002, mirrors 057 US5's "not hand-authored" bar)
- [ ] T010 [US1] Confirm (read + smoke-test, no code change expected) that the reconnect supervisor in `service.py` — already reading `endpoint_host`/`endpoint_port` from the peer row per 063 — requires no change to correctly re-dial a Cloudflare-Tunnel-hosted `host:port`, since from the daemon's perspective it is just another stable address (FR-002; if a change IS needed, it indicates a hidden ngrok-specific assumption and must be fixed here)
- [ ] T011 [P] [US1] Integration test in `tests/n2n/test_endpoint_stability_108.py`: configure a peer with `transport=cloudflare_tunnel` and a fixed host:port; simulate a "restart" (fresh `FederationManager` instance over the same DB, per 063's own test pattern in `test_endpoint_persistence_063.py`); assert the stored `endpoint_host`/`endpoint_port`/`transport` are unchanged and the supervisor's next-dial target is identical to before the simulated restart (SC-001)
- [ ] T012 [P] [US1] Regression test in `tests/n2n/test_endpoint_stability_108.py`: a peer with `transport` unset/`ngrok` behaves byte-for-byte as it did before this feature (no field, no behavior change) — explicit SC-005 guard

**Checkpoint**: US1 independently shippable — a Cloudflare-Tunnel-configured peer's address is durable across restarts, verified by test; zero change for peers who haven't adopted it.

---

## Phase 4: User Story 3 — Transport and edge-gate status are operator-visible (P3)

**Goal**: An operator can see, per peer, which transport carries the channel and whether an edge gate is active, in the existing 060/063 posture surface — no second tool or view.

**Independent Test**: federate with a mix of ngrok- and Cloudflare-Tunnel-transported peers, one with Access enabled and one without; confirm the posture/HUD view shows transport type and edge-gate status per peer without a second tool (spec.md US3 Independent Test).

- [ ] T013 [US3] In `mcp-servers/protocol-mcp/bgp/federation/posture.py`, extend the existing per-peer posture record (already carrying trust model/fingerprint/expiry per 060, kex_group/pq per 063) with `transport` and `edge_gate`, sourced from `manager.get_peer()`/`list_peers()` (T005) (data-model.md §3, FR-006)
- [ ] T014 [P] [US3] In `mcp-servers/protocol-mcp/bgp-daemon-v2.py`, extend the `/n2n/health` route's per-peer entries with `transport`/`edge_gate` (mirrors `/n2n/posture`'s addition — one write via T005, two read surfaces, matching the existing 060/063 dual-exposure pattern) (contracts/interfaces.md)
- [ ] T015 [US3] Add the local tunnel/DNS health probe (data-model.md §2): a small function in `bgp-daemon-v2.py` (or a new tiny helper module alongside `service.py`) that, when `N2N_TRANSPORT_HEALTH_CHECK` is enabled and at least one peer/self-record uses `transport=cloudflare_tunnel`, checks DNS resolution of the configured hostname and the local `cloudflared` systemd unit's active state; returns `true`/`false`/`"n/a"` — surfaced as `local_transport_healthy` on `/n2n/health` (FR-007)
- [ ] T016 [US3] In the `n2n-mcp` server (wherever `n2n_health`/`n2n_status` map to the daemon HTTP routes), confirm the new fields pass through unmodified to the MCP tool response shape — likely no code change needed if the mapping is a direct passthrough, but verify and add a test if any field allowlist/schema needs updating
- [ ] T017 [P] [US3] Test in `tests/n2n/test_transport_posture_108.py`: posture/health output for a peer with `transport=cloudflare_tunnel, edge_gate=cloudflare_access` shows both fields distinctly from a peer with `transport=ngrok, edge_gate=none`; `local_transport_healthy` reflects a forced-down local check (mock/stub the systemd-unit-state read) as `false`, and `"n/a"` when no peer uses `cloudflare_tunnel` at all

**Checkpoint**: US1 + US3 both independently functional — transport reality is durable (US1) and visible (US3) with no separate tooling required.

---

## Phase 5: User Story 2 — Unauthenticated probes never reach the NCFED listener (P2, opt-in, default off)

**Goal**: An optional, per-peer, default-off Cloudflare Access gate rejects unauthenticated connections at Cloudflare's edge, before any bytes reach the NCFED listener — additive to, never a replacement for, spec 060's peer-identity TLS.

**Independent Test**: with an Access policy configured in front of a claw's tunnel, confirm a credential-less or wrong-credential connection is rejected at the edge with zero NCFED traffic reaching the listener; confirm a correctly-credentialed connection proceeds to normal spec-060 negotiation unaffected (spec.md US2 Independent Test).

**Note on scope**: Cloudflare Access itself is configured entirely on the Cloudflare side (dashboard/API) — this phase's tasks are the local-side plumbing (the toggle, the visibility, the verification that nothing in the federation code path needs to change), not an implementation of Access itself.

- [ ] T018 [US2] In `mcp-servers/protocol-mcp/bgp-daemon-v2.py`, add `POST /n2n/peer/edge_gate` accepting `{"peer": "<identity>", "edge_gate": "cloudflare_access"|"none"}`, validating the peer exists, and calling `manager.upsert_peer(..., edge_gate=...)` (T004) — this is the ONLY way `edge_gate` changes from its `none` default; never implied by setting `transport=cloudflare_tunnel` (contracts/interfaces.md, FR-005, Clarifications default-off resolution)
- [ ] T019 [P] [US2] Add `n2n_set_edge_gate(peer, edge_gate)` to the `n2n-mcp` server, proxying T018's route, following the existing small-single-purpose-tool pattern (`n2n_forget_endpoint` from spec 100 is the closest precedent) — deliberately no bulk/"all peers" variant (contracts/interfaces.md)
- [ ] T020 [US2] Verify (read + targeted test, expect no code change) that nothing in `bgp/federation/channel.py`/`tls.py`/`service.py`'s connection-acceptance or TLS-upgrade path is aware of or gated by Access — per research.md R2, this must be true by construction (Access operates strictly before `asyncio.start_server`'s `on_conn` fires), so this task is a verification, not an implementation, of FR-004
- [ ] T021 [P] [US2] Integration test in `tests/n2n/test_edge_gate_108.py`: setting `edge_gate=cloudflare_access` for peer A and leaving peer B at `none` does not change either peer's `PeerState`/consent/trust-model computation — confirms FR-004/FR-005's "additive only, never bypasses or replaces 060" claim at the code level (the live Cloudflare-side Access enforcement itself is validated via quickstart.md's manual procedure, not unit-testable without a real Cloudflare account)
- [ ] T022 [US2] Add the GAIT-audit scope decision from plan.md's Complexity Tracking open question: record `edge_gate` toggles (via T018) to the GAIT immutable trail if the operator decides they are security-relevant per spec 057 US4's event model — **decision required before this task can be marked done**; if the operator declines, close this task as "decided: not GAIT-audited, posture-visible only" rather than leaving it silently unaddressed

**Checkpoint**: All three user stories independently functional. US1 fixes the confirmed live bug; US3 makes the new reality visible; US2 adds an optional, clearly-scoped, non-default hardening layer on top, none of which touches or weakens 060's existing identity guarantees.

---

## Phase 6: Polish & Cross-Cutting

- [ ] T023 [P] Extend `n2n-federation` skill (`~/.openclaw/workspace/skills/n2n-federation/SKILL.md`) with a short section documenting `transport`/`edge_gate` fields and when to reach for `n2n_set_edge_gate`, mirroring how the skill already documents `n2n_forget_endpoint` (spec 100) — keeps the skill in sync with the new tool surface
- [ ] T024 Run `quickstart.md` end-to-end against this claw's own reference deployment (`as65099-10.255.255.1`, `byrnbaker.me`) for US1 and US3 unilaterally (US2 additionally requires a Cloudflare Access policy to be configured, which is an operator action outside the codebase)
- [ ] T025 [P] Full `tests/n2n/` suite green, confirming zero regression to existing 052/053/056/057/060/063/100 test coverage (SC-005 — the cross-feature regression bar every prior spec in this lineage has held itself to)
- [ ] T026 Update `.env.example` and any deployment README with the final `N2N_TRANSPORT_HEALTH_CHECK` default and the TCP/private-network-mode-only note (T001/T002 follow-through once implementation confirms no surprises)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup. BLOCKS all three user stories (every story reads/writes the `transport`/`edge_gate` fields Phase 2 introduces).
- **User Story 1 (Phase 3)**: Depends on Foundational only. No dependency on US2/US3.
- **User Story 3 (Phase 4)**: Depends on Foundational (needs `transport`/`edge_gate` to exist) and benefits from US1 having landed (something real to display), but is not code-blocked by US1 — could technically run in parallel if staffed, since it only reads the fields US1 also reads/writes.
- **User Story 2 (Phase 5)**: Depends on Foundational only, code-wise. Sequenced last per plan.md's stated rationale (validate against a real US1 deployment first; it's the one story with an external Cloudflare-side dependency and a security-relevant default).
- **Polish (Phase 6)**: Depends on all three user stories being complete (or explicitly deferred, mirroring how 063 deferred its own US2 with a documented status note).

### Within Each User Story

- Schema/manager changes (Phase 2) before any route/tool changes.
- Route changes before MCP tool passthrough verification.
- Implementation before its integration test (tests may be written first per the repo's stated pattern of "write to fail first," but are listed after implementation tasks here for readability, consistent with 063's own tasks.md ordering).

### Parallel Opportunities

- T001/T002 (Setup) in parallel.
- T004/T005 (Foundational, different methods on the same file but non-overlapping) in parallel.
- T009/T011/T012 (US1 ops-doc + tests) in parallel with each other once T007/T008 land.
- T014/T017 (US3) in parallel once T013 lands.
- T019/T021 (US2) in parallel once T018 lands.
- US1 and US3 could be staffed in parallel by different people once Foundational completes, since US3 only reads what US1 writes and doesn't block on US1's ops-deployment task (T009).

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) + Phase 2 (Foundational).
2. Complete Phase 3 (US1) — this alone closes the confirmed live bug (stale ngrok endpoints for John/Nick-style peers) for any peer that adopts Cloudflare Tunnel, with zero visibility polish and zero Access hardening yet.
3. **STOP and VALIDATE** via quickstart.md's US1 section against this claw's own reference deployment.
4. Ship/demo if ready — US1 alone is a complete, independently valuable increment (mirrors how 063 shipped US1 alone and explicitly deferred its own US2).

### Incremental Delivery

1. Setup + Foundational → foundation ready, zero externally visible change.
2. US1 → the address-rot bug is fixed for adopters → validate → ship (MVP).
3. US3 → the fix (and any ngrok peers still in the mix) become visible in the existing posture view → validate → ship.
4. US2 → optional edge hardening becomes available, off by default → validate against a real Cloudflare Access policy → ship.
5. Polish → skill docs, full regression pass, config docs finalized.

---

## Notes

- [P] tasks = different files or non-overlapping methods, no dependencies.
- [Story] label maps each task to spec.md's US1/US2/US3 for traceability, matching 063's tasks.md convention exactly.
- No task in this file requires changing NCFED wire format, `channel.py`, or `tls.py`'s core negotiation logic — verified explicitly by T020, consistent with FR-004/FR-008.
- T022 is deliberately left as an explicit decision point rather than a default, per plan.md's Complexity Tracking note — do not silently skip it.
