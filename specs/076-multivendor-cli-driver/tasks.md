# Tasks: Generic Multivendor CLI Driver

**Feature**: 076-multivendor-cli-driver | **Date**: 2026-07-30
**Input**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/mcp-tools.md](./contracts/mcp-tools.md) · [quickstart.md](./quickstart.md)
**Tech**: Python (interpreter chosen deliberately — see R7), `nornir`/`napalm`/`netmiko`/`jdiff` in a **dedicated virtualenv**
**Stacked on**: R0 / spec 075 (unmerged). Must pass `scripts/reconcile-mcp.py`

---

## Three things that shape this task list

**1. Execution order inverts priority for US4.** US4 (inventory and credentials) is P2, but you cannot
connect to a device without it — so it executes *before* US1 (P1, reach). Priority describes user value;
this ordering describes dependency. Same shape as spec 075, where enforcement was P1 but had to run last.

**2. The command filter is Foundational, not part of a story.** It blocks every device interaction and
belongs to no single story, so it sits in Phase 2 alongside the venv. Building reach first and adding
safety later would create a window in which arbitrary commands execute — precisely what Principle I
forbids. **Phase 2 must be complete before any task touches a real device.**

**3. Stage 1 is the first task in this whole roadmap that changes system state.** It installs ~21
packages. Everything in spec 075 was repository files; this is not. R7 found the host toolchain split
(`pip3` → Python 3.13 stranded site-packages, `python3` → 3.14.4, two different `cryptography`
versions), so the install must be done with the venv's own pip and verified, not assumed.

**4. Post-analyze corrections applied.** `/speckit.analyze` found one CRITICAL and two HIGH issues,
all fixed here rather than deferred:

- **CRITICAL** — Constitution Principle III (ITSM-gated changes) had **zero** task coverage. The plan
  had marked it "Partially — inherited from the existing approval path", which was an assertion, not an
  implementation. Human approval (FR-025) and a ServiceNow Change Request are **distinct gates**. Now
  T070a–T070d and T076a–T076b.
- **HIGH** — the MCP entry point was sequenced *after* the stories that need it, so no story phase was
  independently testable as an MCP capability. A stub now lands in Foundational as T016a.
- **HIGH** — SC-002's "90+ platform families" was not verifiable; the figure comes from a driver's
  supported-platform list, and only containerlab-hostable platforms can be live-tested. Split into
  documented-versus-verified.

---

## Phase 1: Setup

- [X] T001 Read `specs/076-multivendor-cli-driver/research.md` in full before writing any code, R7 and R8 especially — R7 invalidates an earlier conclusion about dependency safety and R8 corrects the transport decision.
- [X] T002 Create the server skeleton at `mcp-servers/multivendor-cli-mcp/` with the package layout from plan.md (`inventory/`, `policy/`, `tools/`, `server.py`, `routing.py`, `credentials.py`).
- [X] T003 Add a `.gitignore` negation entry for `mcp-servers/multivendor-cli-mcp/` so the new server directory is tracked — the repo ignores broadly and new server dirs are otherwise silently untracked.
- [X] T004 [P] Create the test harness skeleton at `tests/multivendor/run-tests.sh`, following spec 075's `tests/reconcile/run-tests.sh` pattern: bash + stdlib, no new framework in the shared environment. **Capture exit codes without a pipe** (`cmd >/dev/null 2>&1; echo $?`) — a `| tail` pipe reports the pipe's status and caused a misdiagnosis in spec 075.

---

## Phase 2: Foundational

**Blocking prerequisites. No user story work — and specifically no device contact — begins until every
task here is done.**

### Stage 1 — dedicated virtualenv and dependency isolation (FR-030a/b/c, R7)

- [X] T005 Confirm wheel availability for the full dependency tree on `/usr/bin/python3` (3.14.4) using `--dry-run` executed by **that interpreter's own pip**. If any wheel is unavailable, select an older base interpreter and record the choice and reason in research.md — this is the plan's one open item and must be resolved by evidence, not assumption.
- [X] T006 Record the pre-install `cryptography` version as reported by `/usr/bin/python3` (currently 46.0.5) in `specs/076-multivendor-cli-driver/baseline-deps.txt`. This is the FR-030c comparison point and MUST be read from the interpreter NetClaw's servers run under, not from `pip3`.
- [X] T007 Write `mcp-servers/multivendor-cli-mcp/requirements.txt` with every dependency **explicitly pinned**: `nornir`, `napalm`, `netmiko`, `nornir-netmiko`, `nornir_napalm`, `nornir-netbox`, `nornir-nautobot`, `pynautobot`, `jdiff`. Note in a comment that the scrapli family arrives transitively via NAPALM 5.x and is expected, not accidental (R8).
- [X] T008 Create the virtualenv with `/usr/bin/python3 -m venv mcp-servers/multivendor-cli-mcp/.venv` and install using `<venv>/bin/python -m pip install -r requirements.txt`. **Never bare `pip3`** — on this host it targets a stranded Python 3.13 site-packages the server cannot import from (R7).
- [X] T009 Verify the system `cryptography` version reported by `/usr/bin/python3` is unchanged against T006's baseline (FR-030c). If it moved, stop — the NCFED X.509 stack (spec 060) depends on it and a regression here breaks certificate handling, not this server.
- [X] T010 Verify the venv can import `nornir`, `napalm`, `netmiko` and `jdiff`, and that the system interpreter still **cannot** — proving isolation actually holds rather than assuming it.

### Stage 2 — command filter and per-platform denylists (FR-022/023/029, R6)

- [X] T011 Implement `mcp-servers/multivendor-cli-mcp/policy/filter.py` with the four-step evaluation from contracts/mcp-tools.md. **Chaining rejection MUST be step 1** — `show version; write erase` passes an allowlist check on its first token and is catastrophic. Order is contractual, not stylistic.
- [X] T012 Implement chaining detection for `;`, `&&`, `||`, `>`, `<`, backtick and `$(` in `policy/filter.py` (FR-023).
- [X] T013 Implement `mcp-servers/multivendor-cli-mcp/policy/platform_deny.py` with per-platform destructive first tokens (R6): VyOS `delete`, MikroTik `/system reset-configuration`, SR Linux `tools system configuration`, SONiC `config erase`, plus the Constitution's Cisco set. A Cisco-shaped denylist is explicitly insufficient (FR-023).
- [X] T014 Implement read-only mode as the default, with write tools absent from `tools/list` entirely unless `MULTIVENDOR_WRITE_ENABLED` is set (FR-022). Absent, not present-and-refusing.
- [X] T015 [P] Add Pydantic input validation across every tool argument, ported from candidate A's design (research R1).
- [X] T016a Implement `mcp-servers/multivendor-cli-mcp/server.py` as a **FastMCP stdio server stub** now, registering tools as they land in later phases (Principle V). **Moved into Foundational per analyze finding O1**: T029–T055 implement the tools, but without an entry point none of them is reachable over MCP, so no story phase would be independently testable as an MCP capability. The stub need only expose `initialize` / `tools/list` / `tools/call` with an empty tool set.
- [X] T016 [P] Add filter contract tests to `tests/multivendor/run-tests.sh` — these run with **no device**: chaining rejected first, per-platform denylist fires, read-only mode blocks non-allowlisted verbs, and `show version` alone passes. Assert exit codes directly.

**Checkpoint Phase 2**: dependencies isolated and proven, and no command can reach a device without
passing a tested server-side filter.

---

## Phase 3: User Story 4 — Inventory and credentials from what NetClaw already has (P2)

> **Sequenced before US1 despite lower priority**: connecting to a device requires knowing it exists and
> how to authenticate. This is a dependency inversion, not a priority change.

**Goal**: Devices resolve from one of three sources; credentials never touch an inventory file.

**Independent test**: Resolve a device from each of the three sources in turn and confirm each reports
its own source; confirm no credential appears in any file on disk.

- [X] T017 [US4] Implement `inventory/sources.py` with the three-source model and resolution order `live_sot` → `generated` → `operator`, plus `auto` (FR-017, FR-017b). A device absent from **every** source MUST be reported as absent, never guessed at or silently defaulted (FR-021).
- [X] T018 [P] [US4] Implement `inventory/live_sot.py` using `nornir-netbox` / `nornir-nautobot`, plus Infrahub via its existing MCP surface (FR-017 live tier).
- [X] T019 [P] [US4] Implement `inventory/generated.py` to render an inventory file from a source of truth, writing a machine-readable **generated marker** so a refresh can never overwrite an operator file (FR-017a/b).
- [X] T020 [P] [US4] Implement `inventory/operator.py` as a strictly **read-only** consumer of an operator-authored file. The server MUST NOT write to it under any circumstance (FR-017b).
- [X] T021 [US4] Populate `source` on every resolved Device and surface it in every result, with `fallback_reason` when the source is not `live_sot` — a stale-cache answer must never look live (FR-017c).
- [X] T022 [US4] Reject any inventory record carrying credential-shaped fields, from any of the three sources, with a clear error naming the offending device and field (FR-017d, Principle XIII).
- [X] T023 [US4] Explicitly refuse `PYATS_TESTBED_PATH` as an inventory source, with an error explaining that pyATS assumes Cisco and those platforms route to `pyATS` instead (FR-017e).
- [X] T024 [US4] Implement `credentials.py` with Vault preferred and environment variables as a documented fallback. **Vault MUST NOT be a hard prerequisite** — an operator with an operator-authored inventory typically has no Vault either (FR-018). Support per-device, per-site and per-platform credential differences via the Device `credential_ref`; a single global credential is not a realistic assumption for a mixed network (FR-020).
- [X] T025 [US4] Report the credential path (`vault` or `environment`) in results so a deployment's posture is inspectable, while never emitting the secret value itself (FR-018a, FR-019).
- [X] T026 [US4] Implement the `list_devices` tool per contracts/mcp-tools.md, including `source_used` and `owning_server`, and never returning credential values.
- [X] T027 [P] [US4] Add inventory contract tests to `tests/multivendor/`: each source reports itself; a credential-bearing inventory record is rejected; a generated-file refresh leaves an operator file byte-identical; a device in no source is reported absent; two devices with different `credential_ref` values resolve independently (SC-007, FR-020, FR-021).
- [X] T028 [P] [US4] Document all three onboarding paths in `.env.example` with descriptions and no values (Principle XIII).

**Checkpoint US4**: any device is resolvable and authenticable, with attribution, and no secret on disk.

---

## Phase 4: User Story 1 — Reach a platform NetClaw cannot touch today (P1)

**Goal**: Retrieve live state from platforms with no dedicated NetClaw server.

**Independent test**: Against a containerlab-hosted SR Linux, SONiC or VyOS device, run a
platform-specific `show`-class command and get real output. This is the first task set that contacts a
real device.

- [X] T029 [US1] Implement `tools/raw.py` executing a single command via netmiko, returning the typed result shape from contracts/mcp-tools.md (FR-002).
- [X] T030 [US1] Apply the Phase 2 filter **before opening any connection** — a denied command MUST NOT establish a session (FR-029).
- [X] T031 [US1] Implement the five distinct failure statuses — `unreachable`, `auth_failed`, `platform_mismatch`, `denied`, `timeout` — keeping them separate, since each has a different remediation (FR-005).
- [X] T032 [US1] Halt and report on unreachable devices; never return cached or assumed state as if live (FR-004, Principle I).
- [X] T033 [US1] Report an unsupported platform explicitly rather than failing obscurely (FR-003).
- [X] T034 [US1] Implement the `check_reachability` tool, separating TCP reachability from authentication from platform mismatch (FR-005).
- [X] T035 [US1] Add `PlatformId` mappings in `routing.py` for the target families: `mikrotik_routeros`, `vyos`, `sonic`, `nokia_srlinux`, `extreme_exos`, `huawei_vrp`, `dell_os10`, `ubiquiti_edge` (FR-001).
- [X] T036 [US1] Stand up a containerlab topology with SR Linux, SONiC and VyOS for integration testing (research R4). Do **not** gate acceptance on MikroTik/Extreme/Huawei, which need licensed images.
- [X] T037 [US1] Verify SC-001: live state retrieved from at least **five platform families NetClaw cannot reach today**, evidenced against real lab devices.

**Checkpoint US1**: the core gap is closed — NetClaw reaches platforms it previously could not. This
alone is a shippable increment.

---

## Phase 5: User Story 2 — One question, one shape, across vendors (P1)

**Goal**: Normalized facts identical in shape across vendors, with gaps reported rather than hidden.

**Independent test**: Request the same normalized fact across three vendors' devices and confirm one
shape, presentable as a single table with no per-vendor special-casing.

- [X] T038 [US2] Implement `tools/facts.py` wrapping NAPALM getters and returning the `NormalizedFact` shape from data-model.md (FR-006).
- [X] T039 [US2] Enumerate supported getters **per platform at runtime**, since NAPALM driver support is uneven — a driver may implement `get_facts` but not `get_bgp_neighbors` (research R5).
- [X] T040 [US2] Report an unavailable getter explicitly with a `gap_reason`, never omitting it silently from results (FR-007).
- [X] T041 [US2] Set `provenance` to `napalm` or `ttp_template`, and **never present a TTP-parsed result as equivalent to a NAPALM one** — emulating a missing getter by scraping CLI output is the exact failure FR-007 exists to prevent (research R9).
- [X] T042 [US2] Implement the `get_facts` tool per contracts/mcp-tools.md, permitted read-only on Cisco and Junos devices because cross-vendor normalized comparison is the one case where this server is correct for them (FR-008).
- [X] T043 [US2] Implement the platform-first routing rule in `routing.py`: dedicated servers own their platforms; this server covers the rest plus cross-vendor normalized reads (FR-009).
- [X] T044 [US2] Refuse configuration changes on platforms owned by another server, naming that server in `owning_server`, so every platform has exactly one write path (FR-010).
- [X] T045 [US2] Return a refusal as a **successful call with a refusal result**, not a protocol error, so the agent can read why and route elsewhere (contracts/mcp-tools.md).
- [X] T046 [US2] Stamp `server: "multivendor-cli"` on every result so answers are attributable when more than one server could have answered (FR-011).
- [X] T047 [P] [US2] Add routing contract tests: a Cisco write is refused and names `pyats`; a Cisco normalized read succeeds; both behaviours hold for Junos and `junos-mcp`.
- [X] T048 [US2] Verify SC-003: one normalized fact across three or more vendors returns one shape, and SC-010: a Cisco/Junos write through this server is refused with the correct server named.

**Checkpoint US2**: cross-vendor questions answerable in one shape, with the boundary against pyATS and
`junos-mcp` enforced in code rather than documented in prose.

---

## Phase 6: User Story 3 — Ask many devices at once (P2)

**Goal**: One query against a fleet, per-device results, isolated failures.

**Independent test**: Query a mixed group including at least one deliberately unreachable device;
confirm every reachable device returns and the failure is isolated.

- [X] T049 [US3] Implement `tools/fleet.py` executing one query across a device group and returning per-device results (FR-013).
- [X] T050 [US3] Isolate per-device failures so one device cannot abort the operation for others (FR-014).
- [X] T051 [US3] Guarantee `len(results) == requested` — every targeted device appears, including failures, because a silently absent device reads as success (FR-014).
- [X] T052 [US3] Contact devices concurrently with a bound, defaulting to **10 workers** and operator-overridable. Nornir's own default is 20, but devices commonly cap concurrent management sessions at 5–15 (research R11, FR-015).
- [X] T053 [US3] Enforce a per-device timeout defaulting to **30 seconds**, operator-overridable, so one hung device cannot stall the operation indefinitely (research R11, FR-016).
- [X] T054 [US3] Implement the `run_fleet` tool per contracts/mcp-tools.md, including the status `summary` block, accepting exactly one of `command` or `getters`.
- [X] T055 [US3] Verify SC-004 (mixed group with an unreachable device returns all reachable results and isolates the failure) and SC-005 (N devices materially faster than N sequential queries).

**Checkpoint US3**: fleet-scale questions work, which is the common real-world case.

---

## Phase 7: Integration and Artifact Coherence (Principle XI)

> Can proceed in parallel from the US1 checkpoint onward. Unlike spec 075, this feature genuinely adds
> capability, so **every** Principle XI touchpoint applies.

- [X] T056 Finalise `server.py`: confirm every tool built in Phases 3–6 is registered, the read-only surface is complete, and write tools are absent unless `MULTIVENDOR_WRITE_ENABLED` is set. The stub itself was created in T016a (analyze finding O1).
- [X] T057 Add a catalog entry to `scripts/lib/catalog.sh` — no generic-driver catalog id exists today, so this is a genuinely new component (FR-030).
- [X] T058 Add `component_install_multivendor_cli()` to `scripts/lib/install-steps.sh` creating the venv per T008's method, using the venv's own pip and never bare `pip3` (FR-030a, R7).
- [X] T059 Register the server in `config/openclaw.json` with the venv interpreter path **resolved at install time, never hardcoded** — spec 075 found three registrations hardcoded to `/home/ubuntu/netclaw/.venv/bin/python3` and broken for every installer, and `reconcile-mcp.py` now fails on exactly that (FR-030b).
- [X] T060 [P] Write `mcp-servers/multivendor-cli-mcp/README.md` documenting every tool, environment variable, transport, and install step (Principle XII).
- [X] T061 [P] Create `workspace/skills/multivendor-device-query/SKILL.md` for normalized facts, and **state the routing rule explicitly** so operator and agent select consistently (FR-012, FR-031).
- [X] T062 [P] Create `workspace/skills/multivendor-raw-cli/SKILL.md` for safe raw command execution, documenting the filter policy while making clear enforcement is server-side (FR-029, FR-031).
- [X] T063 [P] Create `workspace/skills/multivendor-fleet-ops/SKILL.md` for fleet fan-out (FR-031).
- [X] T064 [P] Note in the skills that netmiko also drives Fortinet, PAN-OS and Check Point, but that **CLI reach is not equivalent to their dedicated API servers** — this must not cause R3/R4 to be skipped (research R3).
- [X] T065 [P] Update `README.md`, `SOUL.md`, `TOOLS.md` and `ui/netclaw-visual/` per Principle XI, **including the skill and MCP counts** — the step most often forgotten, and wrong in nine places before spec 075.
- [X] T066 Publish `docs/ADDING-AN-MCP.md`-compliant onboarding by copying `quickstart.md` guidance into the server README, covering all three inventory sources.
- [X] T067 Verify `python3 scripts/reconcile-mcp.py` exits 0 with the new server registered (SC-012).

---

## Phase 8: User Story 5 — Configuration change is gated, staged and reversible (P3)

> **Independently deferrable.** If this slips, Phases 1–7 still deliver ~90 platforms of read-only
> reach. Ships last because it is the only part that can cause an outage.

**Goal**: Writes only via baseline → approval → apply → verify → rollback.

**Independent test**: Attempt a change and confirm it cannot proceed without approval, that a baseline
was captured first, and that it reverts on verification failure.

- [X] T068 [US5] Implement `tools/change.py` with the `ChangeTransaction` state machine from data-model.md, where each transition is a gate rather than a step.
- [X] T069 [US5] Capture a baseline **before** any modification, written inside a path-sandboxed root with traversal prevented, ported from candidate A's design (FR-024, Principle II).
- [X] T070 [US5] Require explicit human approval via NetClaw's existing approval path; no transition past `awaiting_approval` without it (FR-025, Principle I).
- [X] T070a [US5] Classify each device as **lab or production** from inventory metadata, treating an unclassified device as **production**. Never infer or assume lab status (FR-025c). **Added per analyze finding D1.**
- [X] T070b [US5] Require an approved ServiceNow Change Request before any change to a production device, via the existing `servicenow-mcp` integration and `servicenow-change-workflow` skill. This is a **second gate**, distinct from FR-025's human approval — a person saying yes is not change-management authorisation (FR-025a, Constitution Principle III).
- [X] T070c [US5] Halt immediately and roll back to the captured baseline if a Change Request is rejected or withdrawn mid-execution (FR-025b, Principle III).
- [X] T070d [US5] Permit lab-device changes without a Change Request while still recording them in the audit trail (FR-025c, Principle III).
- [X] T071 [US5] Verify post-change state by structured comparison of actual against expected using `jdiff`, **never** from command exit status (FR-026, Principle VIII, research R9).
- [X] T072 [US5] Attempt rollback to the captured baseline on verification failure, and **halt and alert** if rollback itself fails (FR-027, Principle VIII).
- [X] T073 [US5] Terminate at `refused` for Cisco and Junos devices, naming the owning server (FR-010).
- [X] T074 [US5] Expose `apply_config` only when `MULTIVENDOR_WRITE_ENABLED` is set — absent from `tools/list` otherwise (FR-022).
- [X] T075 [US5] GAIT-log every device interaction and every state transition (FR-028, Principle IV).
- [X] T076 [US5] Verify SC-009: no change applies without both a captured baseline and explicit approval, tested by attempting to bypass each.
- [X] T076a [US5] Verify SC-009a: a production-device change is refused without an approved Change Request, and a lab-classified device may change without one while still being audit-logged.
- [X] T076b [US5] Verify SC-009b: a device with no lab/production metadata is treated as production and requires a Change Request.

---

## Phase 9: Polish and Cross-Cutting

- [X] T077 Verify SC-011 / FR-032: all 18 pyATS skills and the Junos skill still work unchanged. This feature must not regress existing device access.
- [X] T078 Verify SC-007a: an operator with **neither** a source of truth **nor** Vault can onboard a device, using an operator-authored inventory and env-var credentials.
- [X] T079 Verify SC-007b / FR-030c: installing this server leaves the system `cryptography` version unchanged.
- [X] T080 Verify SC-006: no credential appears in any file on disk outside a gitignored `.env`, inspected across all three inventory sources.
- [X] T081 Verify SC-008: every Constitution-forbidden operation is blocked on **every** supported platform, tested per platform rather than inferred from one.
- [X] T082 Verify SC-002 and SC-013: **≥90 platform families documented as driver-supported and ≥5 verified against live devices** — the two are separate claims and only the second is testable without licensed images (analyze finding U1, research R4). Also verify an operator can tell from skill documentation alone which server should answer a given question.
- [X] T083 [P] Raise the repo-wide `pip3` hazard from research R7 as its own roadmap item: `scripts/lib/install-steps.sh` contains 186 `pip install` invocations, and on a split-toolchain host any bare `pip3` lands where servers cannot import from. Out of scope here; must not be lost.
- [X] T084 [P] Update `docs/COVERAGE-ROADMAP.md`: mark R1 `DONE`, record that both candidate servers were rejected and why, and note the CLI-reach-is-not-R3/R4 caveat.
- [X] T085 Run the Constitution Principle XI Artifact Coherence Checklist and record the result.
- [X] T086 [P] Draft the WordPress milestone post per Principle XVII: what R1 added, the split-toolchain finding, and why building beat adopting. Present to John before publishing.
- [X] T087 Record the GAIT session summary commit (Principle IV).

---

## Dependencies

```
Phase 1 Setup (T001–T004)
      ↓
Phase 2 Foundational — venv (T005–T010), filter (T011–T016), server stub (T016a)
      ↓                 ← NOTHING touches a device until this completes
Phase 3 US4 inventory + credentials (T017–T028)
      ↓                 ← dependency prerequisite for US1, despite being P2
Phase 4 US1 reach (T029–T037)     ★ MVP boundary
      ↓
   ┌──┴────────────────┬─────────────────────┐
   ↓                   ↓                     ↓
Phase 5 US2 (T038–T048)   Phase 6 US3 (T049–T055)   Phase 7 Integration (T056–T067)
   ↓                   ↓                     ↓
   └───────────────────┴─────────────────────┘
                       ↓
       Phase 8 US5 gated writes (T068–T076b)  ← deferrable; includes ITSM CR gating
                       ↓
       Phase 9 Polish (T077–T087)
```

**Hard constraints**

- Phase 2 blocks **everything**. The filter must exist and be tested before any device contact.
- Phase 3 (US4) blocks Phase 4 (US1) — no inventory means no connection.
- Phase 8 (US5) depends on Phases 2, 3, 4 and 7.
- Phase 7 may proceed in parallel from the Phase 4 checkpoint onward.
- Phases 5 and 6 are independent of each other.

## Parallel opportunities

| Batch | Tasks | Note |
|---|---|---|
| Setup | T004 alongside T001–T003 | Harness skeleton independent |
| Foundational | T015, T016 after T011–T014 | Validation and tests are separable |
| US4 | T018, T019, T020 | Three inventory sources, three files |
| US4 | T027, T028 | Tests and `.env.example` independent |
| US2 | T047 | Routing tests separable from implementation |
| Integration | T060–T065 | Six documentation artifacts, different files |
| Polish | T083, T084, T086 | Different files |

## Implementation strategy

**MVP = Phases 1 + 2 + 3 + 4** (T001–T037). Delivers the feature's entire reason for existing: NetClaw
reaches ~90 platform families it previously could not, safely, read-only, with credentials off disk.
Shippable and demonstrable on its own.

**Then Phase 5 (US2)** for cross-vendor normalized comparison — the capability no existing server can
provide at all, and the one that justifies this server touching Cisco and Junos at all.

**Then Phase 6 (US3)** for fleet scale, and **Phase 7** for the artifact coherence needed to merge.

**Phase 8 (US5) last, and genuinely optional for a first merge.** Read-only across ninety platforms is
valuable; writes are the only part that can cause an outage.

## Task summary

| Phase | Story | Tasks | Count |
|---|---|---|---|
| 1 Setup | — | T001–T004 | 4 |
| 2 Foundational (venv + filter + server stub) | — | T005–T016a | 13 |
| 3 | US4 (P2) | T017–T028 | 12 |
| 4 | US1 (P1) | T029–T037 | 9 |
| 5 | US2 (P1) | T038–T048 | 11 |
| 6 | US3 (P2) | T049–T055 | 7 |
| 7 Integration (XI) | — | T056–T067 | 12 |
| 8 | US5 (P3) | T068–T076b | 15 |
| 9 Polish | — | T077–T087 | 11 |
| **Total** | | | **94** |
