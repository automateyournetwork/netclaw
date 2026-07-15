---
description: "Task list for iN2N Production-Mode Enforcement & Durable Runtime (057)"
---

# Tasks: iN2N Production-Mode Enforcement & Durable Runtime

**Input**: Design documents from `/specs/057-in2n-production-enforcement/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: INCLUDED — the spec's success criteria (SC-001…008) are test-shaped, the plan enumerates `tests/n2n/`, and SC-007 mandates the 056/eN2N regression suite stay green. Tests are written per story before/with implementation.

**Organization**: By user story (priority order). eN2N core (052/053) and the iN2N wire (056) are FROZEN — no task touches `internal_channel.py`, NCFED framing, or eN2N. Repo root: `/home/johncapobianco/netclaw`.

## Path Conventions

- Federation package: `mcp-servers/protocol-mcp/bgp/federation/`
- Daemon: `mcp-servers/protocol-mcp/bgp-daemon-v2.py`
- MCP tool: `mcp-servers/n2n-mcp/server.py`
- Tooling: `scripts/`, installer: `scripts/lib/`
- HUD: `ui/netclaw-visual/src/main.js`
- Tests: `tests/n2n/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module skeletons and test scaffolding so story work can proceed without import churn.

- [ ] T001 [P] Create module skeleton `mcp-servers/protocol-mcp/bgp/federation/controls.py` with stubbed async `openshell_available()`, `defenseclaw_available()`, `gait_recording()` returning `(False, "not implemented")` and a shared `~3s` probe cache helper.
- [ ] T002 [P] Create module skeleton `mcp-servers/protocol-mcp/bgp/federation/posture.py` with stubbed `compute_posture(service)` and `posture_ok_for_delegation(posture, *, strict_all)` matching `contracts/posture.md`.
- [ ] T003 [P] Create module skeleton `mcp-servers/protocol-mcp/bgp/federation/gait.py` with stubbed `ensure_repo()`, `emit(...)`, `recent(limit)` matching `contracts/gait-events.md`.
- [ ] T004 [P] Register the three new modules in `mcp-servers/protocol-mcp/bgp/federation/__init__.py` exports (keep alphabetical with existing).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema + control probes that BOTH posture (US1) and enforcement (US2/US3) depend on.

**⚠️ CRITICAL**: No user story work begins until this phase completes.

- [ ] T005 Add idempotent additive columns to the `member` table in `mcp-servers/protocol-mcp/bgp/federation/risk.py` — `managed_by TEXT DEFAULT 'cold'`, `service_unit TEXT`, `component_scan TEXT` — guarded by a `PRAGMA table_info(member)` check (same pattern as 056 migrations); add `managed_by(member_id)` and `set_managed_by(member_id, kind, service_unit)` accessors.
- [ ] T006 Implement the real control probes in `mcp-servers/protocol-mcp/bgp/federation/controls.py`: `openshell_available()` (shutil.which + cheap `openshell` health/version exec), `defenseclaw_available()` (which + guard/proxy health, reuse the `invocation.py` fail-closed discipline), `gait_recording()` (delegates to `gait.ensure_repo()` + writability). All results cached ~3s with `probed_at`; each returns `(bool, detail)`.

**Checkpoint**: probes + schema ready — user stories can begin.

---

## Phase 3: User Story 1 — Honest production posture (Priority: P1) 🎯 MVP

**Goal**: The Border reports `testing` / `production — enforced` / `production — degraded (<controls>)`, never a false production claim, and gates each delegation via a synchronous preflight (FR-001/002/003/003a, FR-019/020).

**Independent Test**: With one control forced unavailable in production, the status tool/heartbeat/HUD report `production — degraded (<control>)` and never `enforced`; with all controls up, `production — enforced`; testing mode reports `testing`.

- [ ] T007 [P] [US1] Write `tests/n2n/test_posture.py`: the posture matrix (each control missing → `degraded` naming it; all up → `enforced`; testing mode → `testing`) and `posture_ok_for_delegation` decisions (containment gap → refused; audit gap → audit-degraded; strict_all → refused on any gap). Stub `controls.py` probes.
- [ ] T008 [US1] Implement `compute_posture(service)` and `posture_ok_for_delegation(...)` in `mcp-servers/protocol-mcp/bgp/federation/posture.py` per `contracts/posture.md` (reads `N2N_RISK_MODE`, `N2N_STRICT_ALL`, and the three `controls.py` probes; builds the posture object incl. `summary`).
- [ ] T009 [US1] Add the synchronous preflight gate to `mcp-servers/protocol-mcp/bgp/federation/service.py` `route_and_delegate` and `delegate_to_member`: call `posture_ok_for_delegation`; on refuse return an error envelope with `enforcement="refused:<control>"`; on allow attach `enforcement` (`enforced`|`audit-degraded`) to the delegation result (FR-003a/019/020).
- [ ] T010 [US1] Start a background posture poller (~10s asyncio task) in `mcp-servers/protocol-mcp/bgp-daemon-v2.py` caching the latest `RiskPosture` on the service; expose it on the daemon status route.
- [ ] T011 [US1] Extend the status tool in `mcp-servers/n2n-mcp/server.py` to return the posture object (add `n2n_posture` or fold into `n2n_status`) per `contracts/posture.md`.
- [ ] T012 [P] [US1] Surface `posture.summary` in the operator heartbeat skill `workspace/skills/n2n-federation/SKILL.md` (report posture line each heartbeat).
- [ ] T013 [P] [US1] Add a posture panel to the HUD in `ui/netclaw-visual/src/main.js` (enforced=green / degraded=amber naming missing controls / testing=grey), fed by the status tool.

**Checkpoint**: US1 independently testable — the risk tells the truth about itself and gates delegations, even before every control is wired (a missing control simply reads unavailable).

---

## Phase 4: User Story 2 — Members run sandboxed under OpenShell (Priority: P1)

**Goal**: In production every member executes inside the OpenShell sandbox; a member that cannot be sandboxed does not run (fail-closed), driving `degraded(sandbox)` (FR-004/005/006).

**Independent Test**: Launch a member in production → its process runs under `openshell`; force `openshell` unavailable → the delegation is refused and posture goes `degraded(sandbox)`; testing mode → member runs unsandboxed.

- [ ] T014 [P] [US2] Write the sandbox portion of `tests/n2n/test_controls_failclosed.py`: production + `openshell_available()` false → delegation refused (`refused:sandbox`), posture degraded; testing → unwrapped. Stub `openshell`.
- [ ] T015 [US2] In `mcp-servers/protocol-mcp/bgp/federation/gateway.py`, wrap `run_agent_turn(local=True)` under `openshell run -- …` when `N2N_RISK_MODE=production` (confirm the exact `openshell` invocation against `openshell --help`); if `openshell_available()` is false in production, raise a sandbox-refusal instead of running (FR-005).
- [ ] T016 [US2] In `mcp-servers/protocol-mcp/bgp/federation/service.py` `_cold_start`, apply the same production sandbox wrap to the cold-start launch and widen the cold-start wait to absorb sandbox spin-up (edge case); a sandbox-refusal surfaces as `degraded(sandbox)` not a member flap.

**Checkpoint**: US2 independently testable — members are contained in production, fail-closed when they can't be.

---

## Phase 5: User Story 3 — Model I/O guarded by DefenseClaw, fail-closed (Priority: P1)

**Goal**: In production, member/Border model I/O is guarded by DefenseClaw and the member's skill/MCP set is scanned before it runs; if DefenseClaw is unavailable, production fails closed (FR-007/008/009).

**Independent Test**: In production a delegated task's model call traverses DefenseClaw and the member was component-scanned; force DefenseClaw unavailable → the task fails closed (`refused:model-guard`), never runs through a direct provider; a flagged component blocks that member.

- [ ] T017 [P] [US3] Extend `tests/n2n/test_controls_failclosed.py` with the guard portion: production + `defenseclaw_available()` false → `refused:model-guard`, posture degraded, 0% unguarded (SC-003); a flagged component-scan blocks the member (FR-008). Stub `defenseclaw`.
- [ ] T018 [US3] Add the pre-run component scan at the member (cold-)start path in `mcp-servers/protocol-mcp/bgp/federation/service.py` (where the member's scope is known — read the scoped skill/MCP list from the `member` row / `service.member_scope`, NOT the full catalog): run `defenseclaw skill scan` across those components once per start, cache result in `member.component_scan`; a flag blocks the member and is reported (FR-008, resolves U1).
- [ ] T019 [US3] Route the member model turn through the DefenseClaw guard path in `mcp-servers/protocol-mcp/bgp/federation/gateway.py`. In production this guarding is **unconditional** — it MUST NOT consult OpenClaw's `security.mode` (reusing only the fail-closed *discipline* of `invocation.py::_defenseclaw_inspect`, not its `security.mode` early-return, which would bypass guarding under the default `hobby`). If `defenseclaw_available()` is false in production, fail closed (no unguarded provider fallback) — FR-009 (resolves I1).
- [ ] T019a [US3] Assert `security.mode=defenseclaw` when a risk enters production, so the **Border's own** model turns (run via the OpenClaw gateway, not the member local path) are guarded. Implement in the production-mode entry path (daemon startup / risk mode set) in `mcp-servers/protocol-mcp/bgp/federation/controls.py` (`defenseclaw_available()` treats `security.mode != defenseclaw` as unavailable) and surface a clear posture message if it cannot be set (FR-007, resolves C1).

**Checkpoint**: US3 independently testable — the "silent fallback to direct Anthropic" bug is corrected; production guards or refuses.

---

## Phase 6: User Story 5 — Durable runtime: daemon + always-on members survive churn (Priority: P1)

**Goal**: Mesh daemon + each always-on member run as durable systemd `--user` services (auto-start/restart, survive churn/reboot), generated repeatably; single-owner vs cold-start reconciled (FR-013/014/015/016).

**Independent Test**: Generate + enable services; kill the daemon and an always-on member → both auto-restart within a bounded window with no operator action; session/terminal exit and reboot leave them running; a service-managed member is never double-launched by the cold-start path.

- [ ] T020 [P] [US5] Write `tests/n2n/test_durable_services.py`: `in2n-services.py generate` emits valid unit text for the mesh daemon and per-member units from `managed_by=service` rows; single-owner reconciliation skips `create_subprocess_shell` for a service-managed member (no double-launch). Stub `systemctl`.
- [ ] T021 [P] [US5] Check the mesh daemon unit template into the repo at `scripts/systemd/netclaw-mesh.service` (parameterized `<repo>`/`<home>`), matching the live hotfix + `contracts/durable-services.md`.
- [ ] T022 [US5] Implement `scripts/in2n-services.py` with `generate` / `enable` / `status` / `disable <member>`: emits `netclaw-mesh.service` + `netclaw-member-<id>.service` (Restart=always, WantedBy=default.target, EnvironmentFile per member) for members where `managed_by=service`; idempotent; detects missing `systemctl --user` and degrades gracefully with the documented fallback (FR-015).
- [ ] T023 [US5] Add single-owner reconciliation to `mcp-servers/protocol-mcp/bgp/federation/service.py` `_cold_start` per `contracts/durable-services.md`: if `managed_by(member)=="service"`, ensure the unit is active (`systemctl --user start` if inactive) and wait for dial-in instead of shell-spawning (no double-launch, FR-014).
- [ ] T024 [P] [US5] Update `scripts/in2n-profiles.py` to mark always-on members as `managed_by=service` (record `service_unit`) and cold members as `managed_by=cold` when a risk is provisioned.
- [ ] T025 [US5] Constitution XI installer: add the durable-runtime/enforcement component to `scripts/lib/catalog.sh` (one `id|Category|Name|Description` entry) and a `component_install_<id>()` in `scripts/lib/install-steps.sh` that runs `in2n-services.py generate && enable` and verifies the `openshell`/`defenseclaw` CLIs are present.

**Checkpoint**: US5 independently testable — the recurring 056 outage cannot recur; the runtime is durable and self-healing.

---

## Phase 7: User Story 4 — GAIT git audit trail for federation events (Priority: P2)

**Goal**: In production every delegation/enrollment/removal/quarantine is committed to the immutable GAIT git trail (plus the existing SQLite row); GAIT unavailable → `degraded(audit)` (FR-010/011/012/012a).

**Independent Test**: In production perform a delegation + enrollment + quarantine → each is a git commit in `~/.openclaw/n2n/gait/` AND a SQLite row whose `gait_ref` matches the SHA; the trail is append-only/unbounded; GAIT unavailable → posture degraded naming GAIT.

- [ ] T026 [P] [US4] Write `tests/n2n/test_gait_emit.py`: `emit()` creates one commit per event with attributable message + `sqlite_row_id`; the SHA is stored in `remote_invocation_record.gait_ref`; trail is append-only (no amend/rebase); `gait_recording()` false → posture `degraded(audit)` and delegation runs `audit-degraded` (FR-019). Use a tmp GAIT dir.
- [ ] T027 [US4] Implement `mcp-servers/protocol-mcp/bgp/federation/gait.py` `ensure_repo()` (git init at `~/.openclaw/n2n/gait/`), `emit(event, actor, subject, target, channel_kind, sqlite_row_id) -> sha`, `recent(limit)` per `contracts/gait-events.md`; append-only, unbounded, separate repo.
- [ ] T028 [US4] Wire `mcp-servers/protocol-mcp/bgp/federation/audit.py` `_gait_ref` to call `gait.emit(...)` and store the returned SHA in the `gait_ref` column; keep SQLite authoritative (GAIT failure never breaks the audit row, only drives posture in production). **Also thread the event type + actor** from the `audit.record(...)` call sites (in `service.py`, `invocation.py`, `risk.py` enroll/remove/quarantine) so each row maps to the correct GAIT event (`delegation`/`enrollment`/`removal`/`quarantine`) with an attributable actor (resolves C2).
- [ ] T029 [US4] Surface the GAIT trail (via `gait.recent`) in the HUD audit view `ui/netclaw-visual/src/main.js` and note `audit-degraded` results. *(Not `[P]`: shares `ui/netclaw-visual/src/main.js` with T013 — sequence after T013.)*

**Checkpoint**: US4 independently testable — Constitution IV's immutable trail is real; SQLite + git cross-reference.

---

## Phase 8: User Story 6 — Truthful health & fault isolation (Priority: P2)

**Goal**: Health/status distinguishes daemon-down vs member-down vs backend-unreachable, so the heartbeat's diagnosis matches the real cause (FR-017/018).

**Independent Test**: Induce each fault class → the heartbeat reports the correct distinct cause (daemon fault / that member down + will_cold_start / backend unreachable), never conflating them.

- [ ] T030 [P] [US6] Write `tests/n2n/test_fault_isolation.py`: daemon-down, member-down (daemon up), backend-unreachable (daemon+member up, task reports backend failure) each yield the correct `fault_class` with precedence `daemon > member > backend > none`.
- [ ] T031 [US6] Implement `health_report()` in `mcp-servers/protocol-mcp/bgp/federation/service.py` per `contracts/durable-services.md` (data-model §6): daemon self-probe, per-member `state`+`will_cold_start` from `health`/`_spawning`/`managed_by`, backend reachability from the member's last task result; compute `fault_class` by precedence.
- [ ] T032 [US6] Consume `health_report()` in the operator heartbeat skill `workspace/skills/n2n-federation/SKILL.md` so its diagnosis matches the actual cause (fixes the 056 poll-bug-as-member-flap misdiagnosis, FR-018).

**Checkpoint**: US6 independently testable — the heartbeat is trustworthy.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Constitution XI artifact coherence, regression, and docs. All after the stories they document.

- [ ] T033 [P] Update `.env.example` with new vars (`N2N_STRICT_ALL`, any GAIT/service paths) — names + descriptions, no values (Constitution XIII).
- [ ] T034 [P] Update `README.md` (posture/enforcement + durable services + tool counts), `TOOLS.md` (infrastructure reference), and `SOUL.md` (capability summary) for 057.
- [ ] T035 Create/update `workspace/skills/n2n-federation/SKILL.md` posture + fault-isolation documentation and add a SKILL section for the durable-services tooling. *(Not `[P]`: shares `workspace/skills/n2n-federation/SKILL.md` with T012 and T032 — sequence after them.)*
- [ ] T036 Run `python3 scripts/verify-catalog-coverage.py` and confirm the new component id is reachable with zero unexplained gaps (Constitution XI).
- [ ] T037 Run the full regression + new suite: `cd /home/johncapobianco/netclaw && pytest tests/n2n/` — 44 eN2N regression + 45 iN2N (056) + the new 057 tests all green (SC-007).
- [ ] T038 Execute `quickstart.md` end-to-end against the live risk (durable services, flip to production, force each control degraded, verify GAIT commits + fault isolation) and capture the run in the GAIT session log.

---

## Dependencies & Execution Order

- **Setup (T001–T004)** → **Foundational (T005–T006)** block everything.
- **US1 (T007–T013)** is the MVP and defines the preflight/`enforcement` envelope other stories plug into — do first among the P1s.
- **US2 (T014–T016)** and **US3 (T017–T019)** both edit `gateway.py`; sequence T015→T018→T019 (same file) — do NOT run those `[P]`-free gateway edits in parallel with each other. Their tests (T014, T017) are `[P]`.
- **US5 (T020–T025)** is independent of US2/US3 except it shares `service.py::_cold_start` with T016 — sequence T016 before T023 (same method), or coordinate the edit.
- **US4 (T026–T029)** depends only on Foundational (the `gait_recording` probe) + `audit.py`; independent of US2/US3/US5.
- **US6 (T030–T032)** depends on `managed_by` (T005) and edits `service.py` (`health_report` is a new method, safe alongside T009/T016/T023 but land after them to avoid churn).
- **Polish (T033–T038)** last; T037/T038 gate completion.

**Story completion order (priority)**: US1 → US2 → US3 → US5 → US4 → US6. All P1 (US1/US2/US3/US5) constitute the enforcement+durability core; P2 (US4/US6) complete the audit/observability story.

## Parallel Execution Examples

- Setup: T001, T002, T003, T004 all `[P]` (different new files).
- Test-first per story: T007, T014, T017, T020, T026, T030 are `[P]` (separate test files) — write them before their implementation tasks.
- HUD/docs: T013, T033, T034 are `[P]` (independent files) once their story logic exists. NOTE: T012/T032/T035 all edit `SKILL.md` and T013/T029 both edit `main.js` — within each of those groups run sequentially, not in parallel.

## Implementation Strategy

**MVP = US1 alone** (T001–T013): the risk honestly reports `testing`/`enforced`/`degraded` and gates delegations. Immediately valuable and shippable even before a single control is fully wired — a not-yet-implemented control simply reads unavailable and the posture says so (never a false claim).

**Increment 2 (containment)**: add US2 + US3 → production actually sandboxes and guards, fail-closed.

**Increment 3 (durability)**: add US5 → the runtime survives churn/reboot (closes the 056 outage).

**Increment 4 (audit + truthful health)**: add US4 + US6 → immutable trail + trustworthy heartbeat.

Each increment is independently testable and leaves the eN2N/iN2N regression suite green (SC-007).
