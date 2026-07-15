---
description: "Task list for iN2N — Internal NetClaw Federation (spec 054)"
---

# Tasks: iN2N — Internal NetClaw Federation (a "risk" of claws)

**Input**: Design documents from `/specs/056-in2n-internal-federation/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (all present)

**Tests**: INCLUDED — the plan enumerates a `tests/n2n/` suite and Constitution XV mandates integration testing over frozen eN2N.

**Organization**: By user story (US1–US5, priority order), over the existing `bgp/federation/` package + `n2n-mcp` + `scripts/netclaw`/installer + HUD. All additive; frozen eN2N core (052/053) untouched.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different file, no incomplete dependency)
- Absolute-ish repo paths shown; `mcp-servers/protocol-mcp/bgp/federation/` abbreviated `bgp/federation/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffolding the new modules and test harness so all later phases have a home.

- [X] T001 [P] Create empty new modules with module docstrings: `bgp/federation/risk.py`, `bgp/federation/internal_channel.py`, `bgp/federation/router.py` (mirror the header style of `manager.py`/`channel.py`)
- [X] T002 [P] Create `tests/n2n/` iN2N test files as empty stubs with imports + skip markers: `test_risk.py`, `test_enrollment.py`, `test_internal_transport.py`, `test_routing.py`, `test_scope_enforcement.py`, `test_quarantine.py`, `test_member_delegation.py`, `test_en2n_regression.py`
- [X] T003 [P] Create `scripts/in2n-profiles.py` skeleton (stdlib-only, matching `scripts/register-all-mcps.py` style) that will derive profiles from the installed skill catalog
- [X] T004 Add iN2N constants to `mcp-servers/protocol-mcp/bgp/constants.py` (the module `channel.py` imports via `from ..constants import …`): `N2N_ROLE` values, iN2N handshake method names (`in2n/hello`, `in2n/enroll`), new error codes (-32021..-32024, -32030, -32031), default `N2N_QUARANTINE_THRESHOLD=5`, optional `N2N_IN2N_PORT` — reusing existing NCFED framing constants unchanged

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The DB schema, key handling, and role config that every user story needs. **⚠️ No user story can begin until this is done.**

- [X] T005 Extend `bgp/federation/manager.py` SCHEMA with `risk`, `member`, `enrollment_token` tables (per data-model.md) and add idempotent `ALTER TABLE` migrations for `remote_invocation_record.channel_kind` (default `en2n`) and `linked_record_id` — following the existing migration loop pattern
- [X] T006 [P] Implement key handling in `bgp/federation/risk.py`: generate/load this claw's self-signed keypair under `~/.openclaw/n2n/keys/`, compute fingerprints, pin/unpin a member public key to `~/.openclaw/n2n/keys/pinned/<member_id>.pub` (uses `cryptography`, already a repo dep) — gitignored path
- [X] T007 Implement `RiskManager` core in `bgp/federation/risk.py` on top of the shared `FederationManager` connection: `get_risk()`, `set_role(role, risk_name?, description?, enabled_stacks?, border_endpoint?)` with **single-Border enforcement** (FR-003), `is_standalone()`, `self_member_id`
- [X] T008 Add `~/.openclaw/n2n/keys/` to `.gitignore` (Constitution XIII) and add iN2N env vars to `.env.example` (`N2N_ROLE`, `N2N_RISK_NAME`, `N2N_ENABLED_STACKS`, `N2N_IN2N_PORT`, `N2N_BORDER_ENDPOINT`, `N2N_QUARANTINE_THRESHOLD`) with descriptions, no values

**Checkpoint**: DB + keys + role config ready — user stories can begin.

---

## Phase 3: User Story 1 — Stand up a risk and talk only to the Border (Priority: P1) 🎯 MVP

**Goal**: Install one claw as Border and one as Member of a named risk; the Member enrolls (token + self-signed key, pinned) by dialing outbound and appears in the Border's member list as reachable, with no inbound ports. Operator interacts only with the Border.

**Independent Test**: Bring up a Border + one Member over loopback; `n2n_member_list()` shows the member `active`; the member opened zero inbound ports; enrollment rejected without a valid token.

### Tests for User Story 1 ⚠️ (write first, must fail)

- [X] T009 [P] [US1] `tests/n2n/test_risk.py`: role model (`standalone`/`border`/`member`), standalone = risk-of-one behaves as pre-054, single-Border enforcement raises on a second Border, and a **Member role does not expose the operator-facing gateway** while a Border does (FR-005)
- [X] T010 [P] [US1] `tests/n2n/test_enrollment.py`: valid unspent token pins key + flips token to spent; re-presenting spent token → ERR_ENROLL_TOKEN_INVALID; expired token rejected; reconnect with non-pinned key → ERR_MEMBER_NOT_TRUSTED; reconnect with pinned key → active
- [X] T011 [P] [US1] `tests/n2n/test_internal_transport.py`: first **extend the 052/053 two-service loopback harness into an in-memory iN2N Border↔Member channel-pair fixture** (shared by T011/T021), then assert: member-initiated outbound dial establishes an encrypted channel; `in2n/hello` returns risk context; wire frames are byte-identical to eN2N framing; member opens zero inbound listening ports; **a member has no dialable peer other than the Border (hub-and-spoke, no member↔member — FR-007a)**; dropped channel re-dials with bounded backoff

### Implementation for User Story 1

- [X] T012 [P] [US1] Implement enrollment token model + issue/verify/spend in `bgp/federation/risk.py`: `issue_token(label?, ttl?)` (store only the hash), `consume_token(token, member_id, public_key, scope, runtime_kind)` → pin + insert `member` row `state=enrolled`, single-use guard (FR-013a/b)
- [X] T013 [US1] Implement `bgp/federation/internal_channel.py`: member outbound dial to `border_endpoint`, self-signed-key TLS, reuse `encode_frames`/decode + heartbeats from `channel.py`, `in2n/hello`/`in2n/enroll` handshake handlers (member-id + pinned-key proof, NOT AS/router-id) — sibling to eN2N `n2n/hello`, which stays untouched
- [X] T014 [US1] Extend `bgp/federation/service.py`: iN2N supervisor — on a **Border**, accept member dial-ins, authenticate against pinned key, register/track member channels, `on_close` deregister (no zombies); on a **Member**, dial supervisor to the Border reusing the 053 bounded-backoff reconnect
- [X] T015 [US1] Implement member registry reads in `bgp/federation/risk.py`: `list_members()`, `get_member()`, health/last-seen update hooks called by the service
- [X] T016 [US1] Add daemon routes in `mcp-servers/protocol-mcp/bgp-daemon-v2.py`: `GET /n2n/risk`, `POST /n2n/risk` (single-Border guard), `GET /n2n/members`; wire the iN2N supervisor to start when `role in (border, member)`
- [X] T017 [US1] Add MCP tools in `mcp-servers/n2n-mcp/server.py`: `n2n_risk_status` (role/risk/stacks; member summary on Border; `standalone` note otherwise), `n2n_member_list`
- [X] T018 [US1] Installer: add role/risk prompts to `scripts/lib/install-steps.sh` `component_install_n2n` using `scripts/lib/tui.sh` — `tui_menu` for standalone-vs-risk and Border/Member, `read` for name/description, `tui_yesno` confirm; write `N2N_ROLE`/`N2N_RISK_NAME`/`N2N_BORDER_ENDPOINT` to `~/.openclaw/.env`
- [X] T019 [US1] `scripts/netclaw`: add `risk_menu` (Overview · Members) dispatched by `TUI_CHOICE` mirroring `peering_menu`, a **Risk** entry in `main_menu`, and non-interactive `netclaw risk [status|members]` using `api_get` — standalone shows the risk-of-one note

**Checkpoint**: A two-claw risk stands up over loopback; operator drives it via the Border; member enrolled + pinned + reachable, no inbound ports. **MVP.**

---

## Phase 4: User Story 2 — Ask the Border to route work to the right Member (Priority: P1)

**Goal**: Operator asks the Border a task-shaped request; the Border matches it to the owning Member, delegates asynchronously (reusing 053 tasks), and returns the result. No-capable-member is reported plainly; no secrets cross the boundary.

**Independent Test**: With a Border + a CML Member, ask the Border a CML task → it routes to the CML member, runs as a background task, returns the result; a no-match request returns ERR_NO_CAPABLE_MEMBER.

### Tests for User Story 2 ⚠️ (write first, must fail)

- [X] T020 [P] [US2] `tests/n2n/test_routing.py`: single match routes there; two matches → most-specific specialty wins, then lexicographic member_id (deterministic/repeatable); no match → ERR_NO_CAPABLE_MEMBER and Border performs no work itself
- [X] T021 [P] [US2] `tests/n2n/test_member_delegation.py`: long internal task over iN2N returns a `task_id` fast (submit), status polls advance, result fetched on completion, and result survives a simulated member restart mid-task (reused 053 persistence) — driven over the in-memory channel-pair harness

### Implementation for User Story 2

- [X] T022 [US2] Extend `bgp/federation/inventory.py`: a Member advertises its (scoped) capability inventory to its Border over the internal channel, reusing the 052 inventory build + no-secrets guard (names/descriptions only)
- [X] T023 [US2] Implement `bgp/federation/router.py`: capability match against member inventories, deterministic tie-break (most-specific **specialty** count excluding base floor per FR-021b, then lexicographic member_id), `ERR_NO_CAPABLE_MEMBER` path
- [X] T024 [US2] Extend `bgp/federation/invocation.py`: internal delegation path — submit work to the selected member as a 053 `delegated_task` (`peer_identity=member_id`, direction outbound on Border / inbound on Member) over `internal_channel`, reusing submit/status/result/cancel
- [X] T025 [US2] Add daemon route `POST /n2n/route` in `bgp-daemon-v2.py`: run the router, submit to the member, return `{task_id, member_id}` or the no-capable-member error
- [X] T026 [US2] Add MCP tool `n2n_route(request_text, target_hint?)` in `mcp-servers/n2n-mcp/server.py`; confirm `n2n_task_status`/`n2n_task_result`/`n2n_task_cancel` (053) work against iN2N task_ids unchanged
- [X] T027 [US2] `scripts/netclaw`: add `netclaw risk route "<request>"` subcommand → `POST /n2n/route`, and a **Route a request** entry in `risk_menu`

**Checkpoint**: The Border routes real work to the right Member and returns results; US1+US2 = the core "focused fleet" experience.

---

## Phase 5: User Story 3 — Provision a risk with pre-set profiles, no hand-assembly (Priority: P2)

**Goal**: Catalog-derived claw profiles (CML/pyATS/security…) + Custom, each layered on the mandatory base floor; selecting profiles provisions scoped members; a new risk may seed a small default set.

> **What "provision a member" means (FR-028):** a Member is its **own NetClaw install** — a separate OpenClaw process/container — brought up by installing NetClaw with `N2N_ROLE=member`, `N2N_RISK_NAME=<risk>`, `N2N_BORDER_ENDPOINT=<border>`, and the join token. The Border does **not** spawn members. `n2n_member_add`/the installer only compute the member's scope, issue the single-use token, and print the join instructions; the operator (or their orchestration) then stands up that member instance, which dials home and enrolls (US1). The `runtime_kind` (process|container) is recorded on the member row but the actual runtime is created by that separate install.

**Independent Test**: Create a risk, select the CML profile → a member is provisioned carrying only CML skills + the base floor; Custom lets you pick an arbitrary subset; a fresh risk seeds a default member set.

### Tests for User Story 3 ⚠️ (write first, must fail)

- [X] T028 [P] [US3] Extend `tests/n2n/test_risk.py` (provisioning section): a profile provisions a member scoped to that profile's skills + base floor; base-floor items tagged `base`; Custom selects an arbitrary subset; default seed set created on a new risk

### Implementation for User Story 3

- [X] T029 [P] [US3] Implement `scripts/in2n-profiles.py`: parse the installed skill catalog (`workspace/skills/` + `config/openclaw.json`), emit profiles (CML/pyATS/security/…), always layer the **mandatory base floor** (FR-021a) tagged `base` vs specialty, and support a Custom skill set
- [X] T030 [US3] Implement member provisioning in `bgp/federation/risk.py`: `add_member(name, profile|custom_skills)` → compute scope (base + specialty tagged), create enrollment token, return join instructions; seed-default-members helper (FR-022)
- [X] T031 [US3] Add MCP tools `n2n_member_add(profile|custom_skills, name)` and `n2n_enroll_token(label?, ttl?)` in `mcp-servers/n2n-mcp/server.py` — `n2n_member_add` computes scope, issues a single-use token, and returns **join instructions** (install NetClaw with `N2N_ROLE=member` + endpoint + token); it does NOT spawn the member runtime (see US3 note, FR-028)
- [X] T032 [US3] Add daemon route `POST /n2n/enroll/token` in `bgp-daemon-v2.py`
- [X] T033 [US3] Installer: profile/seed selection in `component_install_n2n` — `tui_menu` per profile and `tui_checklist` (category-headed `CL_IDS/CL_LABELS/CL_ON`) for Custom, sourced from `scripts/in2n-profiles.py`; add the `n2n` risk/role/profile metadata to `scripts/lib/catalog.sh`
- [X] T034 [US3] `scripts/netclaw`: add **Add member (profile | custom)** to `risk_menu` and `netclaw risk add <profile|custom> <name>` / `netclaw risk token [label]` subcommands

**Checkpoint**: Members provisioned from profiles/Custom without hand-assembly; each scoped + base floor.

---

## Phase 6: User Story 4 — The Border is the risk's single, auditable face to the outside (Priority: P2)

**Goal**: eN2N/iN2N/both is a Border setting; a peer risk sees one identity (the Border) and no member details; all internal + external activity is centrally audited, with linked records when an external request is fulfilled internally.

**Independent Test**: On a Border with both stacks, a peer risk queries caps + delegates → sees only the Border identity; the Border's audit shows the external request and the internal delegation, linked; a Member cannot federate externally.

### Tests for User Story 4 ⚠️ (write first, must fail)

- [X] T035 [P] [US4] `tests/n2n/test_en2n_regression.py`: eN2N `n2n/hello`, consent, default-deny, framing byte-for-byte unchanged with iN2N present; a peer never receives member ids/endpoints/topology (FR-016); a Member role has no external federation stack
- [X] T036 [P] [US4] Extend `tests/n2n/test_member_delegation.py` (audit section): an eN2N request satisfied by internal delegation writes two `remote_invocation_record` rows (`channel_kind` en2n + in2n) joined by `linked_record_id`; the external result is attributed to the risk, not the member

### Implementation for User Story 4

- [X] T037 [US4] Enforce role gating in `bgp/federation/service.py` + daemon startup (`bgp-daemon-v2.py`): only a Border runs the external (eN2N) stack and exposes the operator-facing gateway; a **Member role does NOT start/expose the gateway** (FR-005) and never opens the mesh/eN2N path (FR-014); Border runs eN2N/iN2N/both per config (FR-015)
- [X] T038 [US4] Extend `bgp/federation/audit.py`: record internal delegations with `channel_kind='in2n'`; when an external request triggers internal delegation, write + link both records (`linked_record_id`, FR-025); record enroll/remove/quarantine events
- [X] T039 [US4] Single-identity guard: ensure the external (eN2N) inventory/response path in `bgp/federation/inventory.py` never exposes member ids/endpoints/internal topology — the risk presents only the Border identity (FR-016)
- [X] T040 [US4] Surface stacks + centralized audit: extend `n2n_risk_status` and add an audit view (reuse `n2n_audit`) so the operator sees all iN2N + eN2N activity in one place; Border-only enablement reflected in `GET /n2n/risk`

**Checkpoint**: The risk has one external face and one audit trail spanning both federation tiers.

---

## Phase 7: User Story 5 — Member scoping enforced + health + quarantine (Priority: P3)

**Goal**: A scoped member refuses out-of-scope work; the operator can remove a member (unpin); the Border auto-quarantines a member that repeatedly fails auth/health and alerts the operator; per-member health is visible (tools + HUD).

**Independent Test**: Ask a CML member (via Border) a non-CML action → ERR_OUT_OF_SCOPE; remove a member → refused on reconnect; force repeated auth failures → auto-quarantine + alert; stop a member → Border reports unreachable.

### Tests for User Story 5 ⚠️ (write first, must fail)

- [X] T041 [P] [US5] `tests/n2n/test_scope_enforcement.py`: out-of-scope target on a scoped member → ERR_OUT_OF_SCOPE (refused, not attempted); advertised == allowed; base floor present + non-removable; base excluded from specificity (FR-021b)
- [X] T042 [P] [US5] `tests/n2n/test_quarantine.py`: `remove` unpins + refuses reconnect on old key (re-enroll with new token works); N consecutive auth/health failures → auto-quarantine (unpin, stop routing, alert); routing skips non-`active` members

### Implementation for User Story 5

- [X] T043 [US5] Scope enforcement in `bgp/federation/invocation.py` (member side): reject a `tasks/submit` whose target is outside the member's advertised scope with `ERR_OUT_OF_SCOPE`, independent of the relaxed internal trust (FR-023/FR-027)
- [X] T044 [US5] Removal + auto-quarantine in `bgp/federation/risk.py`/`service.py`: `remove_member(member_id)` (unpin, drop, refuse reconnect); increment `auth_failures` on failed auth/health-miss; at `N2N_QUARANTINE_THRESHOLD` → `state=quarantined` + unpin + operator alert; router selects only `active` members (FR-013c/d)
- [X] T045 [US5] Daemon routes `POST /n2n/members/remove` and `GET /n2n/members/health` in `bgp-daemon-v2.py`
- [X] T046 [US5] MCP tools `n2n_member_remove(member_id)` (confirm-gated) and `n2n_member_health(member_id?)` in `mcp-servers/n2n-mcp/server.py`; `scripts/netclaw`: **Remove member** in `risk_menu` + `netclaw risk remove <member_id>`
- [X] T047 [P] [US5] HUD: `ui/netclaw-visual/server.js` fold `role` + `members` into `/api/n2n`
- [ ] T048 [US5] HUD: `ui/netclaw-visual/src/main.js` risk view — Border hub + member spokes with scope badge, state (active/unreachable/quarantined), and live in-flight task progress; standalone renders as today

**Checkpoint**: All five stories independently functional; scoping/health/quarantine complete.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Artifact coherence (Constitution XI), docs, and validation.

- [X] T049 [P] Update `workspace/skills/n2n-federation/SKILL.md` with an iN2N section: risk/roles, ask-the-Border-to-route, member management, enrollment (mirror the delegate-vs-chat guidance style)
- [X] T050 [P] Update `mcp-servers/n2n-mcp/README.md` with the new tools; update `README.md` (iN2N capability, tool count) and `TOOLS.md`
- [X] T051 [P] Update `SOUL.md` (iN2N capability summary + risk/roles identity references)
- [X] T052 Run `scripts/verify-catalog-coverage.py` and confirm zero unexplained gaps for the `n2n` component's risk/role/profile additions
- [X] T053 [P] Add `config/openclaw.json` changes if any new server registration is needed (likely none — `n2n-mcp` already registered; confirm)
- [X] T054 Run `tests/n2n/` full suite (all iN2N tests green) + the existing 052/053 suite (eN2N regression green, SC-009)
- [ ] T055 Execute `specs/056-in2n-internal-federation/quickstart.md` end-to-end on the live setup (Border + co-located CML member + distributed pyATS member) and check the SC-001..SC-011 acceptance checklist
- [ ] T056 Draft the milestone WordPress blog post (Constitution XVII) — present to John before publishing; note GAIT session log

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (P1)**: no deps — start immediately.
- **Foundational (P2)**: depends on Setup — **blocks all user stories** (schema, keys, role config).
- **US1 (P3)**: after Foundational. **MVP.**
- **US2 (P4)**: after Foundational; builds on US1's channel/registry (needs a member to route to for a full test).
- **US3 (P5)**: after Foundational; independent of US2 (provisioning), but its provisioned members exercise US1's enrollment.
- **US4 (P6)**: after Foundational; the linked-audit test (T036) needs US2's delegation path; the frozen-core test (T035) is independent.
- **US5 (P7)**: after Foundational; scope-refusal builds on US2's delegation; health/HUD build on US1's registry.
- **Polish (P8)**: after all targeted stories.

### User Story Independence

- US1 is fully independent (MVP).
- US3 is independent of US2/US4/US5 (pure provisioning) — can be built in parallel with US2 by a second dev.
- US2, US4(audit), US5(scope) share the delegation path — sequence US2 → US4/US5 or coordinate on `invocation.py`.

### Within a story

- Tests first (must fail) → new-file modules → shared-file edits → daemon routes → MCP tools → installer/`netclaw`/HUD.

---

## Parallel Opportunities

- **Setup**: T001, T002, T003 all [P] (distinct new files); T004 after.
- **Foundational**: T006 [P] (keys, new file) alongside T005 (schema); T007 depends on T005/T006; T008 [P].
- **US1 tests**: T009, T010, T011 [P] together.
- **US2 tests**: T020, T021 [P] together.
- **US3**: T028 [P] (test) and T029 [P] (`in2n-profiles.py`, new file) in parallel.
- **US4 tests**: T035, T036 [P].
- **US5 tests**: T041, T042 [P]; T047 [P] (HUD server.js) alongside non-HUD work.
- ⚠️ Serialize edits to the same file: `service.py` (T014, T037, T044), `bgp-daemon-v2.py` (T016, T025, T032, T045), `n2n-mcp/server.py` (T017, T026, T031, T046), `scripts/netclaw` (T019, T027, T034, T046), `invocation.py` (T024, T043), `risk.py` (T007, T012, T015, T030, T044).

---

## Implementation Strategy

### MVP First (US1)

1. Phase 1 Setup → 2. Phase 2 Foundational → 3. Phase 3 US1 → **STOP & VALIDATE**: a Border + one Member stand up over loopback, member enrolled/pinned/reachable, operator drives via the Border. Demoable.

### Incremental Delivery

US1 (form + enroll) → US2 (route to specialist) → US3 (profile provisioning) → US4 (single face + audit) → US5 (scope + health + quarantine) → Polish. Each adds value without breaking the prior; run `test_en2n_regression.py` continuously to keep the frozen eN2N core honest.

### Notes

- No new third-party packages; `cryptography` already vendored (spec 003).
- Reuse Nick's `scripts/lib/tui.sh` primitives and the `scripts/netclaw` command tree — no new prompt style (PRs #96/#115/#117).
- Frozen 052/053 core: never edit eN2N framing/consent/default-deny/no-secrets; add iN2N as siblings.
