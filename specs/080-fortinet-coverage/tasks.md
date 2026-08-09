# Tasks: Fortinet Coverage (FortiOS / FortiManager / FortiAnalyzer)

**Input**: Design documents from `/specs/080-fortinet-coverage/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-tools.md, quickstart.md
**Roadmap**: R3 — largest single-vendor absence

**Tests**: Contract tests ARE included. The spec makes them mandatory — SC-002a requires plane/scope
attribution be asserted *mechanically across all tools, not spot-checked*, and SC-009's two-gate refusals
cannot be demonstrated by inspection. They are also the only tasks provably runnable **without an
appliance**, which matters given the licence dependency below.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 (manager) · US2 (device) · US3 (gated writes) · US4 (analyzer)

## Path Conventions

New vendored server at `mcp-servers/fortinet-mcp/`, skills under `workspace/skills/`, lab under
`labs/fortinet-r3/`, tests under `tests/fortinet/`. Per plan.md "Source Code".

---

## ⚠️ Two external dependencies that shape this order

**1. The FortiGate is unlicensed.** Measured 2026-08-01: `License Status: No License`, `Model: INVAL (0)`,
`0 CPU allowed`. It began the day as `Invalid` / `EVAL (1)`; an `execute vm-license` fetch authenticated
successfully but returned an **empty** licence — the account held no VM-eval entitlement — and applying it
overwrote the built-in eval. Recovery is uploading the `.lic` obtained from FortiCare (T025). Two
consequences worth carrying forward:

- An unlicensed unit issues **no API session** (`/logincheck` returns no `Set-Cookie`), so REST work is
  fully blocked until the licence lands, not merely degraded.
- `execute restore vmlicense` accepts **only `tftp` and `ftp`** — not `scp` — so the practical upload path
  is the GUI unless a TFTP server is available.

This blocks **T027 onward**. T001–T020 are entirely device-free — a design property, not luck, and the
reason the envelope, credentials and transports are built first.

**2. FortiManager and FortiAnalyzer are 15-day clocks from first boot.** They must NOT be powered on until
**T035** (FortiManager) and **T043** (FortiAnalyzer) respectively. Importing them into Hyper-V now is free
— the clock starts at power-on, not import. Booting them during Phase 1 would spend the verification
window on implementation.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Server skeleton and dependency discipline. No appliance required.

- [ ] T001 Create `mcp-servers/fortinet-mcp/` with `transport/`, `planes/` subpackages and `__init__.py` files per plan.md "Source Code"
- [ ] T002 Add `.gitignore` negation for `mcp-servers/fortinet-mcp/` — the repo ignores broadly and new server dirs are silently untracked (docs/ADDING-AN-MCP.md step 1)
- [ ] T003 Write `mcp-servers/fortinet-mcp/requirements.txt` with `mcp>=1.2.0,<2` and `httpx>=0.27.0,<1`, including the comment explaining the upper bound is load-bearing (spec 077; `mcp` 2.0.0 removed `mcp.server.fastmcp`)
- [ ] T004 Create `mcp-servers/fortinet-mcp/server.py` FastMCP skeleton with stdio transport and JSON-RPC lifecycle (Principle V), no tools yet
- [ ] T005 [P] Create `tests/fortinet/run-tests.sh` harness following `tests/reconcile/run-tests.sh` — bash + stdlib, no new test framework in the shared environment

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The envelope and credential layer. **Every user story depends on this.** Built before any
tool exists so that no tool can be written without attribution.

**⚠️ MUST complete before Phases 3–7.**

- [ ] T006 Implement `mcp-servers/fortinet-mcp/envelope.py` — `plane` + `scope` + `source` + `retrieved_at` + `outcome` stamping per data-model.md §1
- [ ] T007 Make `envelope.py` a **chokepoint**: a wrapper/decorator every tool response passes through, so omission is structurally impossible rather than a review item (FR-005, plan "Key design decisions")
- [ ] T008 Enforce in `envelope.py` that `plane` is set by the calling module and can never be supplied by a caller parameter (FR-006)
- [ ] T009 Enforce per-plane scope validation in `envelope.py`: `adom` for manager, `device`+`vdom` for device, `window_start`+`window_end` for analyzer; indeterminate scope returns `scope_indeterminate` as an **error**, never an unqualified result (FR-009)
- [ ] T010 Implement the `outcome` enum in `envelope.py` with all ten values from data-model.md §2, keeping `refused_no_approval` and `refused_no_change_record` **distinct** (FR-020a)
- [ ] T011 [P] Implement `mcp-servers/fortinet-mcp/credentials.py` — six per-plane env vars plus `FORTINET_VERIFY_SSL` (default true) and `FORTINET_ALLOW_WRITES` (default false) per data-model.md §8
- [ ] T012 [P] In `credentials.py`, report a missing variable **by name and never by value**, including inside exception text — the usual leak path (FR-029)
- [ ] T012a Implement GAIT audit emission **inside the `envelope.py` chokepoint** so every operation — read or write, permitted or refused — produces an audit record by construction (FR-023, **Principle IV, NON-NEGOTIABLE**). Placing it anywhere else makes silent operations possible, which the principle forbids outright
- [ ] T012b Ensure the GAIT record captures tool name, `plane`, `scope`, `outcome` and timestamp, and **never** a credential value — the audit trail is a disclosure surface too (FR-023 with FR-029)
- [ ] T012c Ensure a GAIT write failure does not silently swallow the operation: surface it, because an unaudited operation violates Principle IV whether or not the tool call itself succeeded
- [ ] T013 [P] Contract test in `tests/fortinet/test_envelope.py`: every envelope carries `plane` and valid scope; a missing-scope response is an error (SC-002a) — runs with **no appliance**
- [ ] T013a [P] Contract test in `tests/fortinet/test_audit.py`: every tool invocation, **including refusals**, emits exactly one GAIT record, and no record contains a credential (FR-023, SC-011) — runs with **no appliance**
- [ ] T014 [P] Contract test in `tests/fortinet/test_credentials.py`: no token, key, session id or password appears in any output or exception string (SC-012) — runs with **no appliance**

**Checkpoint**: envelope, audit and credentials proven without a device.

> **Why the audit tasks are here and not in Phase 12.** `/speckit.analyze` found FR-023 had a
> *verification* task (T093) and no *implementation* task — the same defect it caught in spec 076, where
> Principle III was recorded as "inherited" with nothing behind it. Verification of an unimplemented
> guarantee passes only by accident. GAIT emission belongs in the chokepoint, before any tool exists.

---

## Phase 3: Transports (Blocking for all plane work)

**Purpose**: Two protocols, three planes. Research R2 found FortiManager and FortiAnalyzer share one.

- [ ] T015 Implement `transport/jsonrpc.py` — a single client for **both** FortiManager and FortiAnalyzer; both use `/jsonrpc` with the same envelope and `exec /sys/login/user` login (research R2)
- [ ] T016 Implement token authentication in `transport/jsonrpc.py`; token-only in v1, no username/password session flow (research R9)
- [ ] T017 Map expired sessions to `auth_expired` in `transport/jsonrpc.py` — **never** to an empty result. "No policies exist" from an expired session is a silent, plausible, wrong answer (data-model.md §2)
- [ ] T018 [P] Implement `transport/rest.py` — `httpx.AsyncClient` against the FortiOS REST API with bearer-token auth (research R3)
- [ ] T019 [P] Implement TLS posture in both transports: verification **on** by default, opt-out only via `FORTINET_VERIFY_SSL`, never a silent default (FR-030, research R8)
- [ ] T020 [P] Contract test in `tests/fortinet/test_transport.py`: TLS verification defaults on; disabling requires the explicit variable — **no appliance**

---

## Phase 4: Lab (Unblocks device verification)

**Purpose**: Make the lab reproducible by someone who is not the author (FR-036a).

- [ ] T021 Create `labs/fortinet-r3/README.md` — three Hyper-V VMs, image acquisition as an operator action, explicit statement that **no image, licence or credential is committed** (FR-036a)
- [ ] T022 Create `labs/fortinet-r3/topology.md` recording the addressing and the **Default Switch trap**: internal NAT unreachable from WSL2, *and* its subnet re-randomises on host reboot — use an External vSwitch with a static address (research R6)
- [ ] T023 Document required `allowaccess` on `port1` in `topology.md` — FortiGate drops everything not listed, so a failed ping proves nothing about reachability
- [ ] T024 Create `labs/fortinet-r3/verify-lab.sh` — reachability, version and licence-state preflight, with **no credentials embedded**
- [ ] T025 **[OPERATOR]** Activate the FortiGate evaluation licence: `execute vm-license-options account-id <FortiCloud Account ID>` then `execute vm-license`. Currently `Invalid`. Note the free permanent eval is **one per FortiCloud account**
- [ ] T026 **[OPERATOR]** Create a least-privilege read-only REST API admin on the FortiGate with a trusthost restricted to the NetClaw host; record the token in `.env`, never in the repo
- [ ] T027 Verify with `labs/fortinet-r3/verify-lab.sh` that licence reads `Valid` and the REST API answers — **gate for Phase 5**

---

## Phase 5: US2 — Device-plane state, including VPN tunnels (P2)

**Goal**: Answer "is the tunnel up?" from the FortiGate itself. Sequenced before the manager plane
because the FortiGate licence is **permanent** while FortiManager's is a 15-day clock.

**Independent test**: query IPsec tunnel state and confirm phase 1 and phase 2 are reported separately,
with the answering device named.

- [ ] T028 [P] [US2] Implement `planes/device.py` `fgt_system_status` — hostname, serial, version, HA mode, and **which HA member answered** (FR-015, FR-017)
- [ ] T029 [P] [US2] Implement `fgt_list_interfaces` and `fgt_get_routes` in `planes/device.py`, reported **per VDOM** (FR-015, FR-018)
- [ ] T030 [US2] Implement `fgt_vpn_tunnels` in `planes/device.py` with `phase1_status` and `phase2_status` as **separate fields** — a tunnel with phase 1 up and phase 2 down is neither up nor down (FR-016)
- [ ] T031 [US2] Implement `fgt_get_policies` in `planes/device.py` — rules as running on the device, the input to divergence detection (FR-008)
- [ ] T032 [US2] Ensure an unreachable device returns `plane_unreachable` and **never** substitutes manager-plane configuration as observed state (US2 AS3, FR-007)
- [ ] T033 [P] [US2] Contract test in `tests/fortinet/test_device_plane.py`: phase 1 and phase 2 never collapse into one status field (SC-006)
- [ ] T034 [US2] Live-verify all device tools against the FortiGate at FortiOS v8.0.0; record which endpoint paths differ from the community repos' 7.6.6 assumptions (research R6, open item 6)

**Checkpoint**: US2 independently deliverable — a working device plane with no manager or analyzer.

---

## Phase 6: US1 — The unbacked skill answers a real question (P1) 🎯 MVP

**Goal**: Convert `fortimanager-ops` from a false claim into a true one.

**⚠️ T035 starts the FortiManager 15-day clock. Do not run it before Phase 5 is complete.**

**Independent test**: run the skill's declared workflow end to end against a reachable FortiManager and
confirm every step returns real data.

- [ ] T035 **[OPERATOR]** Boot FortiManager-VM on Hyper-V (**starts the 15-day trial**), register the FortiGate to it (1 of 3 device slots), create a read-only API token
- [ ] T036 [P] [US1] Implement `planes/manager.py` `fmg_list_adoms` and `fmg_list_devices` (FR-010)
- [ ] T037 [P] [US1] Implement `fmg_list_policy_packages` and `fmg_get_policy_package` in `planes/manager.py` — ordered rules with position, action and enabled/disabled state (FR-011)
- [ ] T038 [US1] Implement `fmg_search_rules` in `planes/manager.py` — by source, destination, service or object reference (FR-012)
- [ ] T039 [US1] Implement `fmg_resolve_object` in `planes/manager.py` resolving groups **recursively**; a nested group resolved one level deep is still unresolved, and a rule reported only by object name is not an audit (FR-013)
- [ ] T040 [P] [US1] Implement `fmg_get_revisions` in `planes/manager.py` — rollback context for the write path (FR-014)
- [ ] T041 [US1] Implement `fmg_preview_install` in `planes/manager.py` — read-only, **requires neither gate**, named `preview` and never `install` (FR-022)
- [ ] T042 [US1] Live-verify manager tools against FortiManager with the ADOM named on every result (SC-003, SC-004, SC-005)

**Checkpoint**: US1 delivers the roadmap's headline value — the unbacked skill is backed.

---

## Phase 7: US4 — FortiAnalyzer: what actually hit the policy (P3)

**Goal**: Answer "is this rule dead?" — the only plane that can.

**⚠️ T043 starts the FortiAnalyzer 15-day clock.**

**Independent test**: query logs for a known policy over a bounded window; confirm the window is stated.

- [ ] T043 **[OPERATOR]** Boot FortiAnalyzer-VM on Hyper-V (**starts the 15-day trial**), point the FortiGate's logging at it, create a read-only API token. First confirm a Hyper-V image exists (research open item 3)
- [ ] T044 [US4] Implement `planes/analyzer.py` `faz_query_logs` over the shared JSON-RPC client, filtered by policy/address/service within a bounded window (FR-018a)
- [ ] T045 [US4] Implement offset-based pagination in `planes/analyzer.py` — `faz_fetch_more` re-runs at a new offset rather than reusing FortiAnalyzer's single-use `tid` (research R1)
- [ ] T046 [US4] Apply and **state** a 24-hour default window when bounds are absent; never issue an unbounded query (FR-018c)
- [ ] T046a [P] [US4] Implement `faz_list_devices` in `planes/analyzer.py` — devices logging to this analyzer (FR-018a; present in contracts/mcp-tools.md but was missing a task)
- [ ] T047 [US4] Implement `faz_policy_activity`; an empty result returns `no_logs_in_window` with the explicit statement that this is **not** evidence the rule is unused (FR-018b)
- [ ] T048 [P] [US4] Contract test in `tests/fortinet/test_analyzer_plane.py`: an empty log result never renders as "unused" (SC-007a) — **no appliance**
- [ ] T049 [US4] Live-verify analyzer tools; record that verification is thin by design — the 3-policy device cap limits log volume and diversity

---

## Phase 8: Cross-plane divergence and manifest budget

**Purpose**: The finding only NetClaw can produce, plus the ceiling that governs registration.

- [ ] T050 Implement `fgt_compare_with_manager` in `planes/device.py` — reports `only_in_manager` / `only_in_device` / `differs` as a **finding**, never silently resolved (FR-008, data-model.md §7)
- [ ] T051 Ensure `fgt_compare_with_manager` returns `plane_unreachable` naming the missing plane rather than comparing against a plane it could not read (FR-007)
- [ ] T052 Measure the serialised `tools/list` response with `count_tokens` and **record the number** (FR-025) — **no appliance**
- [ ] T053 Assert the measured manifest is **≤ 5,000 tokens**; if it exceeds, merge tools or fold parameters — the ceiling wins over the surface (FR-026, FR-026a)
- [ ] T054 [P] Document the measured figure, the ceiling, and any filtering rule including **which tools were excluded and why**, in `mcp-servers/fortinet-mcp/README.md` (FR-027)
- [ ] T055 [P] Contract test in `tests/fortinet/test_manifest_size.py` failing the build if the manifest exceeds 5,000 tokens — **no appliance**

---

## Phase 9: US3 — Writes gated by two distinct gates (P2)

**Goal**: Refuse a policy install for the right reason, naming the gate that is missing.

**Independently deferrable.** If this slips, Phases 1–8 still deliver three planes of read-only reach.

**Independent test**: attempt a write with each gate independently absent; confirm refusal both times with
the specific missing gate named.

- [ ] T056 [US3] Port the two-gate logic from `mcp-servers/multivendor-cli-mcp/tools/change.py` into `mcp-servers/fortinet-mcp/gates.py` **with explicit attribution in the header** — copy, do not import; separate processes, separate deps (research R7)
- [ ] T057 [US3] Implement the read-only default in `gates.py`: every write returns `refused_read_only` unless `FORTINET_ALLOW_WRITES=true` (FR-019)
- [ ] T058 [US3] Implement gate 1 in `gates.py` — missing human approval returns `refused_no_approval` (FR-020, FR-020a)
- [ ] T059 [US3] Implement gate 2 in `gates.py` — missing or unapproved ServiceNow CR returns `refused_no_change_record`, querying `/api/now/table/change_request`; an unconfigured ServiceNow reports **unconfigured**, never approval (FR-020)
- [ ] T060 [US3] Enforce that neither gate can satisfy the other, and that `is_lab` exempts **only** the change-record gate, never the approval gate (FR-020, FR-024)
- [ ] T061 [US3] Treat an unclassifiable device as **production** — misclassifying production as lab permits an unauthorised change; the reverse costs one CR (research R7, inherited from spec 076)
- [ ] T062 [US3] Implement `fmg_install_package` in `planes/manager.py`: identify the rollback revision **before** apply, capture baseline, apply, verify against expected state, roll back on failed verification (FR-021, Principles II and VIII)
- [ ] T063 [US3] Implement `fmg_check_change_record` as a standalone tool (contracts/mcp-tools.md)
- [ ] T064 [P] [US3] Contract test in `tests/fortinet/test_gates.py`: each gate refused independently produces its own distinct outcome value; neither substitutes for the other (SC-009) — **no appliance**
- [ ] T065 [US3] Live-verify the gate matrix against FortiManager, confirming an install succeeds only with both gates satisfied (SC-009, SC-010)
- [ ] T066 [US3] Confirm whether the FortiGate 3-policy cap blocks installing a package of >3 rules — a finding about the **lab**, not the server (research open item 4)

---

## Phase 10: Skills (US1, US2, US4 surfaces)

- [ ] T067 [US1] Back-fill `workspace/skills/fortimanager-ops/SKILL.md` so every declared MCP command, env var and tool name matches what ships; **keep the skill name** — six documents reference it — but replace `FORTIMANAGER_MCP_CMD` with `FORTINET_MCP_CMD`, since one server now backs three skills (FR-002, data-model.md §8)
- [ ] T068 [P] [US2] Create `workspace/skills/fortigate-ops/SKILL.md` for the device plane (FR-002a)
- [ ] T069 [P] [US4] Create `workspace/skills/fortianalyzer-ops/SKILL.md` for the analyzer plane (FR-002a)
- [ ] T070 Make each skill state which plane it owns and name the other two as the route for planes it does not own (FR-034)
- [ ] T071 [P] State in each skill the boundary against spec 076's multivendor CLI driver: that driver is FortiOS **CLI**, this feature is the structured API and manager planes; neither replaces the other (FR-031)
- [ ] T072 [US1] Document the `fwrule-analyzer` composition in `fortimanager-ops/SKILL.md` and verify policy retrieved here is accepted by its FortiOS parser — completing a pairing that skill already documents but cannot currently execute (FR-032, SC-014)
- [ ] T073 State the ServiceNow boundary in `fortimanager-ops/SKILL.md` as the CR gate of FR-020 specifically, not as a general integration note (FR-033)
- [ ] T074 Regenerate `migration-staging/members/fortimanager/` so its command variable — now `FORTINET_MCP_CMD` — resolves; use the **member generator, not a hand-edit** — 27 members share a generated shape (FR-003, FR-003a)
- [ ] T075 Confirm the regenerated member starts successfully (SC-002b). Do **not** touch the generated absolute home path — it is generator convention, not a spec-075 defect (FR-003b)

---

## Phase 11: Artifact Coherence (Principle XI — NON-NEGOTIABLE)

**Purpose**: docs/ADDING-AN-MCP.md end to end. Three of these fail no automated gate and must be checked
by hand.

- [ ] T076 Register `fortinet-mcp` in `config/openclaw.json` with **repo-relative** paths, `command` and `args` separate — never an absolute path under `/home/` (docs/ADDING-AN-MCP.md step 2)
- [ ] T077 Add a catalog entry to `scripts/lib/catalog.sh` as `"fortinet|Security|Fortinet|..."`
- [ ] T078 Add `fortinet` to **`PROFILE_SECURITY` and `PROFILE_MULTIVENDOR`** in `scripts/lib/catalog.sh` — a component in no profile appears only in the fine-tune checklist, and R1 shipped missing from the one profile named after it
- [ ] T079 Add `component_install_fortinet()` to `scripts/lib/install-steps.sh` using `netclaw_pip_install`, **never** a bare `pip`/`pip3` (spec 077, FR-041)
- [ ] T080 Add the HUD **node list** entry in `ui/netclaw-visual/server.js` — `{ id, name, prefixes }`
- [ ] T081 Add the HUD **annotation map** entry in `ui/netclaw-visual/server.js` — `{ env, files, notes }`. **Both are required**; the annotation alone renders no node
- [ ] T082 [P] Update `README.md` — description, architecture, **and the counts** (204→206 skills)
- [ ] T083 Update `SOUL.md` counts **and** add a capability section describing what NetClaw can now do with Fortinet and its routing boundaries — a bumped count does not tell the agent what it can do
- [ ] T084 [P] Update `.env.example` with the **nine** new variables per data-model.md §8, **names and descriptions only, never values**
- [ ] T085 [P] Update `TOOLS.md` with the Fortinet infrastructure reference
- [ ] T086 [P] Write `mcp-servers/fortinet-mcp/README.md` — tools, env vars, transport, install, and the measured manifest token count
- [ ] T086a Record in `mcp-servers/fortinet-mcp/README.md` the **entry-point decision and its reasoning** — all three planes in scope, why, and that manager/device/analyzer are distinct rather than interchangeable — so a later roadmap item does not re-litigate it (FR-004)
- [ ] T087 Run `python3 scripts/reconcile-mcp.py`; must exit 0 across all four surfaces (FR-038). Check the exit code directly — **never through a pipe**, which reports the pipe's status
- [ ] T088 Run `python3 scripts/verify-inventory-counts.py`; must exit 0 with 206 skills (FR-039)
- [ ] T089 Run `python3 scripts/trace-skill.py` for all three skills — the check that would have caught this feature's premise long ago (FR-040, SC-001)

---

## Phase 12: Honest verification reporting

- [ ] T090 Build the per-capability verification table distinguishing **live-exercised** from **static-only** (FR-035, SC-016)
- [ ] T091 Mark unverified, or cut, anything that could not be exercised — spec 078's precedent, where four of five API families were dropped rather than shipped as claims (FR-036)
- [ ] T092 [P] Record the FortiOS v8.0.0 findings: which community-documented endpoints changed since 7.6.6, so the next maintainer inherits the correction (research open item 6)
- [ ] T093 Confirm every operation performed during verification produced a GAIT record (FR-023, SC-011)
- [ ] T094 Update `docs/COVERAGE-ROADMAP.md` R3 status to `DONE` with the outcome summary, following the R1/R2/R8 format
- [ ] T095 Draft the milestone blog post for review before publishing (Principle XVII)

---

## Dependencies

```
Phase 1 (Setup)
   └─> Phase 2 (Envelope + credentials)      ← BLOCKS EVERYTHING
          └─> Phase 3 (Transports)
                 ├─> Phase 4 (Lab) ──> T027 gate
                 │      └─> Phase 5 (US2 device)      [permanent licence]
                 │             └─> Phase 6 (US1 manager)   [starts 15-day clock]
                 │                    └─> Phase 7 (US4 analyzer) [starts 15-day clock]
                 │                           └─> Phase 8 (divergence + manifest)
                 │                                  └─> Phase 9 (US3 gated writes)
                 └─> Phase 10 (Skills) ─> Phase 11 (Artifacts) ─> Phase 12 (Reporting)
```

**Story independence**: US2 stands alone once Phase 4 completes. US1 needs only FortiManager. US4 needs
only FortiAnalyzer. US3 depends on US1 (it installs packages). Phase 8's divergence tool is the sole
cross-story dependency (US1 + US2).

**Critical-path externals**: T025 (licence activation) gates T027 onward. T035 and T043 start irreversible
15-day clocks.

## Parallel opportunities

- **Phase 2**: T011–T014 in parallel with T006–T010 (different files)
- **Phase 3**: T018, T019, T020 parallel with T015–T017
- **Phase 5**: T028, T029, T033 parallel
- **Phase 6**: T036, T037, T040 parallel
- **Phase 10**: T068, T069, T071 parallel
- **Phase 11**: T082, T084, T085, T086 parallel

## Implementation strategy

**MVP = Phase 1 → 2 → 3 → 4 → 5 → 6.** That delivers the roadmap's headline: a backed
`fortimanager-ops` plus a working device plane. Phases 7–9 are additive.

**Two deliberate departures from strict priority order**, flagged by `/speckit.analyze` and confirmed:

1. **US2 (P2) is built before US1 (P1).** US1 is the headline story, but its appliance runs a 15-day
   clock while US2's FortiGate licence is permanent. Building the device plane first means the transport,
   envelope and audit layers are proven before any clock starts.
2. **US4 (P3) is built before US3 (P2).** US4 shares the trial window that US1 opens, so deferring it
   past US3 would waste that window. US3 is writes — the one story that is genuinely deferrable without
   reducing read coverage, which is why it is last regardless of priority.

Priority still governs *what matters most*; licence clocks govern *what must happen while a clock runs*.

**Everything before T027 is device-free.** Phases 1–3 (T001–T020) can be completed today regardless of the
licence state. That is deliberate: the envelope, credentials, transports and their contract tests are all
pure functions or mockable, so an external blocker cannot stall the build.

**Do not boot FortiManager or FortiAnalyzer early.** T035 and T043 are the only tasks that start a clock,
and neither is needed before its phase.

**Total: 101 tasks** — 95 from the initial pass plus six added by `/speckit.analyze` remediation
(T012a–c and T013a for the GAIT gap, T046a for the missing `faz_list_devices`, T086a for FR-004's
entry-point rationale).

**T001–T020 plus T012a–c and T013a — 24 tasks — require no appliance** and can proceed immediately,
regardless of the licence state.
