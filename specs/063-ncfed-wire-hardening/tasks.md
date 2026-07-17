# Tasks: NCFED Post-060 Wire-Confidentiality & Metadata Hardening

**Input**: Design documents from `/specs/063-ncfed-wire-hardening/`
**Prerequisites**: plan.md, spec.md (clarified 2026-07-17, 4 Qs), research.md (R0 stack reality + R1–R5), data-model.md, contracts/interfaces.md, quickstart.md

**Tests**: Included — spec defines an Independent Test per story + measurable SCs; Constitution VIII requires verification. Integration reuses the 060 two-node loopback pattern.

**Phase order = implementation order** (not spec priority order): US1 (P1) first as an isolated bug fix, then US4 (P4) + US3 (P3) low-risk scaffolding/docs, then **US2 (P2) last** because in-protocol mesh TLS is the flag-day slice touching the BGP core. Story labels map to spec priorities (US1=P1 … US4=P4).

## Implementation status (2026-07-17)

- **US1 (P1) endpoint persistence — DONE + tested.** The live re-dial bug is closed. `tests/n2n/test_endpoint_persistence_063.py` (3 tests) green; full `tests/n2n/` suite 177 passed.
- **US4 (P4) PQ posture + honest visibility — DONE + tested.** Probe/readout/require-fail-fast wired; `tests/n2n/test_pq_posture_063.py` (7) green.
- **US3 (P3) metadata seam + accepted residuals — DONE + tested.** ECH-ready no-op seam + posture reporting + docs; `tests/n2n/test_metadata_seam_063.py` (3) green.
- **US2 (P2) mesh in-protocol TLS — DEFERRED to a supervised flag-day.** Deliberately NOT landed unsupervised: it modifies the BGP routing core (`agent.py` collision/OPEN-replay path + `session.py`), its value only materializes in a coordinated multi-peer rollout (Nick/Byrn), and it needs two-node validation against the live FRR/mesh FSM. The `tls.upgrade_to_tls` primitive, PQ helpers, and posture wiring it depends on are already in place, so T017–T021 are a well-scoped follow-up to do WITH the operator + peers. See the PR write-up.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [x] T001 [P] Add `N2N_PQ_MODE` (opportunistic|require, default opportunistic) and a mesh-TLS enablement note to `.env.example`, documented as reusing `N2N_CERT_MODE` unless T-mesh finds an independent gate is needed (data-model.md §5)
- [x] T002 [P] Add a `pq_available()` capability probe to `mcp-servers/protocol-mcp/bgp/federation/tls.py` — returns whether this host's `ssl`/OpenSSL can offer the X25519MLKEM768 hybrid AND expose the negotiated group; used by P4 to degrade honestly (research R0/R4)

---

## Phase 2: Foundational (blocking prerequisites)

- [x] T003 Add endpoint-persistence helper usage confirmation in `mcp-servers/protocol-mcp/bgp/federation/manager.py`: verify `upsert_peer(peer_as, router_id, endpoint_host=, endpoint_port=)` writes `endpoint_host/endpoint_port/endpoint_updated_at` (columns already exist) and add a focused unit test in `tests/n2n/test_endpoint_persistence_063.py` asserting the write + `endpoint_updated_at` bump

**Checkpoint**: env + capability probe + persistence primitive ready.

---

## Phase 3: User Story 1 — Endpoint persistence (P1) 🎯 MVP / live bug

**Goal**: A peer's current address is remembered on a successful connect so the supervisor reconnects to it — zero manual re-dials.

**Independent Test**: dial a peer at a fresh address → confirm persisted → restart daemon → supervisor reconnects with no manual action; a bad dial does not overwrite a good address.

- [x] T004 [US1] In `mcp-servers/protocol-mcp/bgp/federation/service.py` `open_channel`, on a **successful, authenticated** channel (after `_secure_dial`/hello, at the "Opened NCFED channel" point) call `self.manager.upsert_peer(peer_as, router_id, endpoint_host=host, endpoint_port=port)` — never on the failure/except path (FR-001, Clarify Q4)
- [x] T005 [US1] In `mcp-servers/protocol-mcp/bgp/federation/service.py` `_on_endpoint_update`, persist the peer-announced endpoint via `upsert_peer(..., endpoint_host, endpoint_port)` bound to the authenticated channel identity (it currently updates then relies on the row; ensure host/port are written) (FR-002)
- [x] T006 [US1] In `mcp-servers/protocol-mcp/bgp-daemon-v2.py` `/n2n/connect`, rely on T004 for persistence (the route already calls `open_channel`); confirm no persist-on-attempt occurs and the response is unchanged (FR-001)
- [x] T007 [US1] Verify the reconnect supervisor in `service.py` reads `endpoint_host/endpoint_port` from the peer row for auto-redial and prefers the persisted (current) address over any stale in-memory value (FR-003)
- [x] T008 [P] [US1] Integration test in `tests/n2n/test_endpoint_persistence_063.py`: successful dial persists endpoint; simulated restart (fresh manager over same DB) → supervisor targets the persisted address; a failed dial leaves the prior good address intact (SC-001, FR-004)

**Checkpoint**: US1 independently shippable — the stale-endpoint re-dial bug is closed.

---

## Phase 4: User Story 4 — PQ posture + honest visibility (P4)

**Goal**: Define the PQ posture and surface, per channel, whether it negotiated PQ or classical — degrading honestly on a stack that can't do PQ.

**Independent Test**: `/n2n/certs` + `/n2n/posture` show `pq_available`, per-channel cipher/tls_version (and group where readable); `N2N_PQ_MODE=require` on a non-PQ stack fails fast at startup.

- [x] T009 [US4] In `mcp-servers/protocol-mcp/bgp/federation/tls.py`, add readout helpers: `channel_kex(sslobj)` returning `{tls_version, cipher, kex_group|None}` using `SSLObject.version()/cipher()` and `group` when present (None on 3.10) (R4)
- [x] T010 [US4] In `mcp-servers/protocol-mcp/bgp/federation/service.py`, read `N2N_PQ_MODE` (default opportunistic); when `require` AND `tls.pq_available()` is False, fail fast at startup with a clear "PQ unavailable on this crypto stack (needs OpenSSL ≥ 3.5 / Python ≥ 3.15 — corrected per research R0-addendum)" error (FR-011, R4)
- [x] T011 [US4] In `mcp-servers/protocol-mcp/bgp/federation/service.py`, when `require` and the stack CAN offer PQ, hard-refuse a channel that negotiated a classical (non-PQ) group, logged + audited (FR-011)
- [x] T012 [US4] Surface `pq_mode`, `pq_available`, and per-channel `kex_group`/`cipher`/`tls_version` in `bgp/federation/posture.py` `channel_security` and in the `GET /n2n/certs` route (`bgp-daemon-v2.py`) (FR-012, contracts)
- [x] T013 [P] [US4] Unit test `tests/n2n/test_pq_posture_063.py`: opportunistic default unchanged; `require` on a non-PQ stack raises the startup error; kex readout returns cipher/tls_version and `kex_group=None` on this stack without crashing

**Checkpoint**: operators see PQ-vs-classical truthfully; posture knob works; nothing faked.

---

## Phase 5: User Story 3 — Metadata minimization (P3, document + ECH seam)

**Goal**: Reduce/observe identity metadata where the stack allows; document accepted residuals honestly.

**Independent Test**: on this stack, SNI still present AND reported as an accepted residual; ECH seam is a no-op that would conceal SNI on an ECH-capable stack; preamble unchanged.

- [x] T014 [US3] Add an ECH-ready seam in `mcp-servers/protocol-mcp/bgp/federation/tls.py` `client_context`: a single guarded point that would set an ECH config if `ssl` exposes it, a documented no-op on the current stack (R3, FR-007)
- [x] T015 [US3] Add an `ech_available()` / SNI-exposure indicator to posture so `/n2n/posture` reports the claw-domain SNI as an accepted residual when ECH is unavailable (FR-007)
- [x] T016 [P] [US3] Document in `docs/N2N-RISK.md` (or a security note) the two accepted residuals — cleartext preamble AS/router-id (structural, FR-008) and SNI claw domain until an ECH-capable stack — with rationale; confirm the preamble is unchanged (Clarify Q2)
- [x] T016a [US3] Add an assertion (in `tests/n2n/test_en2n_auth_baseline_060.py` or the US3 test) that shared-port discrimination is unchanged and a peer that does not implement the metadata seam still federates — closing FR-009's verification gap (analyze C1)

**Checkpoint**: metadata exposure is minimized-where-possible and honestly documented.

---

## Phase 6: User Story 2 — Mesh-layer in-protocol TLS (P2) ⚠️ flag-day, ship last

**Goal**: The BGP mesh/keepalive session runs under NetClaw's own TLS + auth on untrusted paths.

**Independent Test**: two-node loopback mesh session with mesh-TLS enforced → capture shows TLS type-23 records after the OPEN, no readable BGP keepalives; a non-upgraded mesh peer is refused with an actionable reason.

- [ ] T017 [US2] In `mcp-servers/protocol-mcp/bgp/agent.py` connection handler (0xFF BGP branch), after mesh-peer identify (the OPEN read), when mesh-TLS is enabled, upgrade the connection with `tls.upgrade_to_tls(..., server_side=)` using the host credential from 060 before the BGP FSM runs (R2, contracts)
- [ ] T018 [US2] In `mcp-servers/protocol-mcp/bgp/session.py`, ensure the mesh session's outbound connect performs the symmetric client-side TLS upgrade after the OPEN exchange and runs its FSM over the upgraded reader/writer (R2)
- [ ] T019 [US2] Gate P2 behind the enforcement flag (reuse `N2N_CERT_MODE`, or `N2N_MESH_CERT_MODE` if T001 found an independent gate is needed); a non-upgraded mesh peer in enforce mode is refused with an actionable close reason, not silently downgraded (FR-006, Constitution XV)
- [ ] T020 [US2] Route mesh-TLS auth outcomes (established / refused) through the existing audit trail and reflect the mesh trust boundary in posture (FR-006, Constitution IV)
- [ ] T021 [US2] Integration test `tests/n2n/test_mesh_tls_063.py`: two in-process mesh peers over loopback establish a TLS-upgraded BGP session (assert ssl_object present, KEEPALIVEs flow inside TLS); an un-upgraded peer is refused in enforce mode; with the flag off, behavior is byte-identical to today (SC-002, FR-005)

**Checkpoint**: mesh layer confidential on untrusted paths; staged rollout like 060.

---

## Phase 7: Polish & Cross-Cutting

- [x] T022 [P] Update `docs/N2N-RISK.md` + README federation section: endpoint auto-persist behavior, PQ posture (`N2N_PQ_MODE`) + stack requirement for real PQ/ECH, mesh-TLS enablement + trust boundary (FR-006, Constitution XI/XII)
- [x] T023 [P] Update `docs/N2N-FEDERATION-GUIDE.md` / peer guide: peers no longer need repeated re-dials once an endpoint is known; note the mesh-TLS flag day for mesh peers
- [x] T024 Run the Artifact Coherence Checklist (constitution §Checklist): `.env.example`, catalog coverage unaffected, HUD posture shows kex/pq, existing skills verified unbroken; full `tests/n2n/` suite green. Assert FR-013: no new SQLite tables and no new third-party Python dependency were introduced (analyze C2)
- [ ] T025 Record a NCFED-draft `-02` follow-up note in the hardening backlog (mesh TLS + P3/P4 stack notes) — the actual draft revision is out of scope here (spec assumption)
- [ ] T026 Draft the WordPress milestone post (Constitution XVII) — present to John before publishing

---

## Dependencies

```text
Phase 1 (T001–T002) → Phase 2 (T003) → all stories
US1 (T004–T008): needs T003; independent of others — MVP, ship first
US4 (T009–T013): needs T002 (pq_available); independent of US1/US3
US3 (T014–T016): needs T002; independent; mostly docs + seam
US2 (T017–T021): needs 060's tls.upgrade_to_tls; heaviest; ship LAST (flag day)
Polish (T022–T026): after the stories it documents
```

## Parallel Execution Examples

- Phase 1: T001, T002 in parallel
- After Phase 2: US1 (T004+) and US4 (T009+) and US3 (T014+) can proceed in parallel — different files (service/manager vs tls/posture vs docs)
- Docs T022, T023 parallel; T016 parallel within US3

## Implementation Strategy

**MVP = Setup + Foundational + US1**: ship the endpoint-persistence fix alone — it closes the live stale-endpoint re-dial bug and is fully back-compatible, no peer coordination. Then US4 + US3 (low-risk visibility/docs, honest about the stack gate). Then **US2 last** — the flag-day mesh-TLS rollout, gated behind the enforcement flag with two-node loopback tests, coordinated with mesh peers exactly like 060.

**Total**: 26 tasks — Setup 2, Foundational 1, US1 5, US4 5, US3 3, US2 5, Polish 5.
