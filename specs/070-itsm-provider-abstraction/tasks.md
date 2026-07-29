# Tasks: ITSM Provider Abstraction for Change Gating

**Input**: Design documents from `/specs/070-itsm-provider-abstraction/`
**Prerequisites**: `spec.md` (required — source of truth), `plan.md` (required), `research.md`, `data-model.md`, `contracts/itsm-gate-contract.md`, `contracts/constitution-amendment.md`, `quickstart.md`, `checklists/requirements.md`

---

## ⛔ IMPLEMENTATION IS BLOCKED PENDING MAINTAINER RATIFICATION

**This round's deliverable is documentation only — the spec set.** Phase 0 below is complete. **Every task from Phase 1 onward is BLOCKED** and must not be started until **T010** records the maintainer's ratification of the Constitution amendment (**1.2.0 → 1.3.0**) plus written answers to `spec.md`'s nine Open Questions.

Why the block is real and not ceremonial:

- Constitution **Principle XVI**: "No implementation work begins without a ratified spec." This spec's own completion criterion (**FR-017**) is a constitutional amendment, so the spec is not ratified until the amendment is.
- Constitution **Governance**: amendments require a documented rationale, an impact review, and a semantic version bump — and the maintainer performs the ratification, not this plan.
- The amendment touches **Principle III**, a safety principle, and **Forbidden Operations**, which makes bypassing it a forbidden operation. `plan.md`'s Constitution Check marks Principle III **AMENDED**, not PASS, precisely so nothing here can proceed on the assumption that ratification will happen.
- Three Open Questions change the module's **API shape**, not just its defaults: Q2 (default provider when unset), Q3 (fail-open vs. an opt-in strict mode), Q4 (whether an `attested_state` is adopted). Writing `src/netclaw_itsm/` before those are answered means writing it twice.

**Legend**

- `[X]` — **documentation-only, already done this round** (Phase 0)
- `[ ]` — **implementation, BLOCKED** (Phase 1 onward)
- **NOT IN v1** — Phase 7 only; specified deliberately, implemented deliberately later

---

**Tests**: Explicitly requested by the spec. **FR-011** makes characterization tests a *blocking prerequisite*, not an optional extra: coverage across all five gate implementations is **zero** today, so the current behavior must be pinned **before** any refactor touches it (`SC-003`, `SC-004`, US2 acceptance 1).

**Organization**: Grouped by user story per `spec.md`'s priorities, with one deliberate inversion — **Phase 3 implements US2 (consolidation) and Phase 4 implements US1 (provider selection)**, even though US1 has the lower story number. This follows `spec.md` US2 verbatim: *"Provider selection (US1) is unbuildable on five divergent copies — it would mean five parallel implementations of the same abstraction. Consolidation is the prerequisite."* Both are P1; the phases are ordered by dependency, not by number.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, or FOLLOW-ON)
- Include exact file paths in descriptions

## Path Conventions

- **Shared library**: `src/netclaw_itsm/` at repository root (mirroring the existing `src/netclaw_tokens/`, reached by a `sys.path` insert anchored on `__file__` — see `mcp-servers/gnmi-mcp/gnmi_mcp_server.py:31`)
- **Gated servers**: `mcp-servers/gnmi-mcp/`, `mcp-servers/claroty-mcp/` (v1); `mcp-servers/nautobot-mcp-v2/`, `mcp-servers/nautobot-routing-mcp/`, `mcp-servers/nautobot-golden-config-mcp/` (follow-on)
- **Tests**: `tests/itsm-gate/` — its own per-component directory with `pytest.ini` + `conftest.py`, following `tests/halo-mcp/` (feature 069)
- **Governance**: `.specify/memory/constitution.md`
- **Config**: `config/openclaw.json`, `.env.example`
- **Docs**: `SOUL.md`, `SOUL-SKILLS.md`, `README.md`, `TOOLS.md`, `workspace/skills/<name>/SKILL.md`

---

## Phase 0: Specification (THIS ROUND — documentation only, COMPLETE)

**Purpose**: Produce the nine-artifact spec set so the maintainer has something concrete to ratify or reject. **No code, config, or constitution file is modified by this phase.**

- [X] T001 Write `specs/070-itsm-provider-abstraction/spec.md` — problem, goals/non-goals, 4 user stories, edge cases, FR-001…FR-017, key entities, the current-state inventory table (5 implementations · 42 gated tools · 4 `^CHG\d+$` regexes · 0 tests), SC-001…SC-007, assumptions, 9 Open Questions, 3 discovered defects
- [X] T002 [P] Write `research.md` — Phase 0 evidence: the five-implementation survey with file:line citations, why the gate must be sync and network-free, the `src/netclaw_tokens/` vs. installable-package decision, the mixed-interpreter constraint, the GAIT emit/commit seam, and a landing place for the maintainer's Open Question answers
- [X] T003 [P] Write `data-model.md` — `ItsmProvider`, `ProviderAdapter`, `ChangeRef`, `GateDecision`, `GateConfig`
- [X] T004 [P] Write `contracts/itsm-gate-contract.md` — `validate_change_request(cr_number) -> dict{valid, message, cr_number, state}` plus the additive `provider`/verification keys, and the nautobot `_check_itsm() -> Optional[str]` contract documented as the follow-on target
- [X] T005 [P] Write `contracts/constitution-amendment.md` — the exact before/after text for all five ServiceNow-naming locations, so US4 is a reviewable diff the maintainer can ratify rather than an intention they must trust
- [X] T006 [P] Write `quickstart.md` — operator walkthrough: select a provider, run a gated write, read the GAIT record, switch providers, trip the unknown-provider error
- [X] T007 [P] Write `checklists/requirements.md` — requirements-quality checklist for `spec.md`
- [X] T008 Write `plan.md` — technical context, the Constitution Check gate table with the honest Principle III self-reference note, project structure, and Complexity Tracking
- [X] T009 Write `tasks.md` (this file)
- [X] T009a Write `gait-session-log.md` — Principle IV append-only audit trail: the four scoping decisions, the exploration findings that corrected the scope, and the corrections surfaced during authoring (Claroty emits no GAIT today; the two divergent operation-label strings; per-shim `sys.path` depth; two adapter fields that cannot be settled on this branch)

**Checkpoint**: Ten artifacts exist in `specs/070-itsm-provider-abstraction/`. The proposal is reviewable. **Nothing is implemented, and nothing may be.** (Principle IV's session record is `gait-session-log.md`, written at T009a. Principle XVII's milestone post is deferred to T062, once there is a shipped milestone to record — a specification round is not one.)

---

## Phase 1: Setup (Shared Infrastructure) — ⛔ BLOCKED

**Purpose**: Unblock the feature, then stand up the two containers (test directory, package skeleton) that everything else fills in.

- [ ] T010 **🔓 UNBLOCKING GATE — nothing below may start until this task is recorded.** Obtain the maintainer's ratification of the Constitution amendment (1.2.0 → 1.3.0, MINOR) **and** written answers to all nine Open Questions in `spec.md`, recording them verbatim in `research.md`. The three that change the module's API: **Q2** default provider when unset (`none` + startup warning is the recommendation), **Q3** fail-open vs. an opt-in `NETCLAW_ITSM_STRICT` mode, **Q4** whether an `attested_state` is adopted. Also required before Phase 6: **Q9** (whether Principle III's "Assess → Authorize → Implement → Review" lifecycle wording, which is ServiceNow's vocabulary, is also generalized). If ratification is declined, this feature stops here and the spec set stands as a rejected proposal — which is a valid outcome, not a failure.
- [ ] T011 [P] Create `tests/itsm-gate/pytest.ini` and `tests/itsm-gate/conftest.py` with fixtures that isolate **all four** relevant environment variables per test — `NETCLAW_ITSM_PROVIDER`, `NETCLAW_LAB_MODE`, `ITSM_ENABLED`, `ITSM_LAB_MODE` — so no test inherits operator environment leakage (the same leakage that currently makes `gnmi-mcp`'s lab bypass work by accident)
- [ ] T012 [P] Create the `src/netclaw_itsm/` package skeleton (`__init__.py` only, **no logic yet**) and prove the `sys.path` insert pattern from `mcp-servers/gnmi-mcp/gnmi_mcp_server.py:31` resolves it under **both** interpreters the repo actually uses — bare `python3` (gnmi, claroty) and the nautobot venv python — since a package invisible to one of them is the exact failure the follow-on phase would hit

---

## Phase 2: Foundational (Blocking Prerequisites) — ⛔ BLOCKED

**Purpose**: Pin the current behavior of the gate **before** anything refactors it. This is **FR-011** and it is blocking because coverage is currently **zero** — there is no existing suite to fall back on, so the safety net has to be built first.

**⚠️ CRITICAL**: No user story work may begin until **T015** passes. Characterization tests must be written against, and pass against, the **UNREFACTORED** code. A suite that only ever ran after the refactor proves nothing.

- [ ] T013 [P] Write `tests/itsm-gate/test_characterization_gnmi.py` against the **unrefactored** `mcp-servers/gnmi-mcp/itsm_gate.py`, pinning every branch of today's `validate_change_request()`: empty/`None` reference → `valid: False` with the exact "Change request number is required for gNMI Set operations" message; malformed reference → `valid: False` with the exact "Invalid CR format… Expected format: CHG followed by digits (e.g. CHG0012345)" message; well-formed reference with lab mode off → `valid: True, state: "unverified"` (because `_check_servicenow_cr_state()` returns `None` unconditionally); lab mode on → `valid: True, state: "lab_mode"`; and in every case assert **exactly** the four envelope keys `valid`, `message`, `cr_number`, `state`
- [ ] T014 [P] Write `tests/itsm-gate/test_characterization_claroty.py` against the **unrefactored** `mcp-servers/claroty-mcp/utils/itsm_gate.py`: the same branch matrix, plus its Claroty-specific wording ("Change request number is required for Claroty write operations"), plus the **published envelope shape** `{"itsm_gate": …, "applied": bool, …}` as emitted at `mcp-servers/claroty-mcp/tools/alerts.py:182` (deny), `:219` (allow), `:223` (error) and `tools/devices.py:228`/`:284` — this is the public contract FR-009 protects
- [ ] T015 **🚧 BLOCKING GATE** — Run `tests/itsm-gate/` against the **unrefactored** code and confirm **100% pass** (FR-011, US2 acceptance 1, baseline for SC-003). If an assertion fails, the **test** is wrong and gets corrected; the code must not be touched to make a characterization test pass, because the whole point is that it characterizes what exists
- [ ] T016 [P] Snapshot the SC-007 baseline into `contracts/itsm-gate-contract.md`: all **7 v1 gated call sites** with file:line — `mcp-servers/gnmi-mcp/gnmi_mcp_server.py:196` (`gnmi_set`, plain `def`, param `change_request_number`, **required**) and Claroty's six (`tools/alerts.py:180`, `tools/devices.py:226`, `tools/devices.py:282`, `tools/user_actions.py:47`, `tools/user_actions.py:109`, `tools/vulnerabilities.py:209` — param `cr_number`, **required**) — plus the nautobot contrast (`cr_number`, **optional**) so no later task can rename anything without a visible diff against this list
- [ ] T017 [P] Snapshot the SC-001 baseline: the **four** independent `^CHG\d+$` regex locations — `mcp-servers/gnmi-mcp/itsm_gate.py`, `mcp-servers/claroty-mcp/utils/itsm_gate.py`, `mcp-servers/gnmi-mcp/models.py:198` (dead), `mcp-servers/memory-mcp/storage/sqlite_store.py:109` (deferred provenance, FR-016) — so the 4 → 1 reduction is measurable rather than asserted

**Checkpoint**: A passing characterization suite exists against code nobody has touched yet. **Only now** can consolidation begin, and any regression it causes will be visible immediately.

---

## Phase 3: User Story 2 — One Gate Implementation Instead of Five (Priority: P1) 🎯 MVP FOUNDATION — ⛔ BLOCKED

**Goal**: Collapse the two `validate_change_request()` copies onto one shared module behind thin shims, with **zero** behavior change and **zero** call-site churn. Nautobot stays untouched.

**Independent Test**: With provider `servicenow` (status-quo config), the Phase 2 characterization suite passes **unchanged** against the refactored gate — including Claroty's published envelope — and `git diff` shows no change to any MCP tool signature.

*Sequenced before US1 per `spec.md` US2: consolidation is the prerequisite for provider selection.*

### Implementation for User Story 2

- [ ] T018 [US2] Implement `src/netclaw_itsm/gate.py` — port today's `validate_change_request()` logic as the `servicenow` provider's behavior, **verbatim in effect**: a plain synchronous `def` (never a coroutine — `gnmi_set` cannot await), stdlib only, **no network calls**, all four envelope keys preserved with unchanged meaning, and today's exact message strings preserved for the status-quo provider (FR-001, FR-006, FR-009)
- [ ] T019 [US2] Implement `src/netclaw_itsm/config.py` — resolve `NETCLAW_ITSM_PROVIDER` and the lab/bypass state, with the default and precedence exactly as answered in T010 (Q2, Q3). `NETCLAW_LAB_MODE` keeps its current truthiness parsing (`true`/`1`/`yes`, case-insensitive) so lab behavior does not shift under operators who never touch the new variable
- [ ] T020 [US2] Replace the body of `mcp-servers/gnmi-mcp/itsm_gate.py` with a **thin shim** that re-exports `validate_change_request` from `netclaw_itsm` via a `sys.path` insert anchored on `__file__`. The module path and the symbol name are unchanged, so `gnmi_mcp_server.py`'s import and its `gnmi_set` call site are not edited at all (FR-010, SC-007)
- [ ] T021 [US2] Replace `mcp-servers/claroty-mcp/utils/itsm_gate.py` with the same thin shim. Preserve Claroty's distinct "required for Claroty write operations" wording by passing a **caller context** into the shared gate — **not** by keeping a second copy of the logic, which would defeat FR-001
- [ ] T022 [US2] Re-run the Phase 2 characterization suite **unchanged** against the refactored code; 100% pass required (**SC-003**). Editing an assertion at this step is a regression being covered up, not a fix — if an assertion fails, the refactor is wrong
- [ ] T023 [US2] Verify against T016's snapshot that all 7 v1 call sites and both parameter names (`change_request_number`, `cr_number`) are byte-identical, and that neither requiredness changed (**SC-007**, US2 acceptance 4)
- [ ] T024 [US2] Verify Claroty's published envelope is still consumable: `{"itsm_gate": …}` continues to carry `valid`, `message`, `cr_number`, `state` at `tools/alerts.py:182`/`:219`/`:223` and `tools/devices.py:228`/`:284` (FR-009, US2 acceptance 3)
- [ ] T025 [US2] Delete the dead validator `GnmiSetRequest` at `mcp-servers/gnmi-mcp/models.py:186-207` (its `^CHG\d+$` regex is at `:198`), first proving it is unreferenced (`grep -rn GnmiSetRequest`). Regex count: 4 → 3
- [ ] T026 [US2] Confirm the nautobot trio is entirely untouched — `git diff --stat` empty for `mcp-servers/nautobot-mcp-v2/server.py`, `mcp-servers/nautobot-routing-mcp/server.py`, `mcp-servers/nautobot-golden-config-mcp/server.py` — and that their `_check_itsm()` definitions still sit at `:39`, `:57`, `:61` respectively (US2 acceptance 5, FR-014)

**Checkpoint**: 5 implementations → 1 shared module + 2 thin shims. Regex count 4 → 2 (shared gate + the deferred Memory MCP provenance check). Zero regression **proven**, not assumed. This state is independently valuable and mergeable even if US1 never lands: it removes the five-way duplication that made the real bug unfixable.

---

## Phase 4: User Story 1 — An Operator Gates Changes With Their Own ITSM (Priority: P1) 🎯 MVP — ⛔ BLOCKED

**Goal**: Make the gating ITSM selectable, so a Halo or Jira shop is never told to produce a ServiceNow CR that will never exist in their environment.

**Independent Test**: Set `NETCLAW_ITSM_PROVIDER=halo`, call a gated tool with a Halo change-ticket id → accepted, and **no** output string contains "ServiceNow". Repeat with `CHG0012345` → rejected, with a message naming Halo's expected format.

### Implementation for User Story 1

- [ ] T027 [US1] Implement `src/netclaw_itsm/providers.py` — four declarative `ProviderAdapter` entries (`servicenow`, `halo`, `atlassian`, `none`), each declaring **only data**: change-reference format, human-readable ITSM name, "approved for implementation" state vocabulary, and the responsible verification skill. **No transport, no credentials, no HTTP** (FR-004). The `halo` adapter's verification-skill reference points at feature 069's `halo-change-request` skill, which **does not exist on this branch** (PR #167 unmerged) — so the adapter must be able to declare that skill **unavailable** rather than dangle a broken reference
- [ ] T028 [US1] Wire provider resolution into `src/netclaw_itsm/gate.py`: validate the supplied reference against the **configured** provider's format, and on failure return a message naming **that** provider and **its** expected format (FR-005, US1 acceptance 1 & 2)
- [ ] T029 [US1] Implement the unknown-provider hard failure: an explicit configuration error naming the supported providers, with **no** fallback to any vendor default (FR-003, US1 acceptance 5). A silent fallback to ServiceNow would recreate the exact bug this feature exists to fix, so this path must be tested, not just written
- [ ] T030 [US1] Add the **additive** `provider` key to the returned envelope while leaving `valid`, `message`, `cr_number`, `state` untouched in name and meaning (FR-009, US2 acceptance 3). `cr_number` keeps its ServiceNow-flavored name on purpose — renaming it is a breaking change to Claroty's published output
- [ ] T031 [US1] Implement the `none` provider and its precedence relative to `NETCLAW_LAB_MODE` per the Q3/Q2 answers recorded in T010 — the two overlap and the spec requires defined precedence. Every bypass is GAIT-logged (FR-012, US1 acceptance 4)
- [ ] T032 [US1] Add `NETCLAW_ITSM_PROVIDER` to **every** gated server's env block in `config/openclaw.json` (FR-015): `gnmi-mcp` at `:81-90`, which today passes **no ITSM variable at all** (its lab bypass currently works only by parent-environment leakage), and `claroty-mcp` at `:551-558`, which today passes only `NETCLAW_LAB_MODE` (`:557`). Miss either and the feature silently misconfigures
- [ ] T033 [P] [US1] Write `tests/itsm-gate/test_providers.py` — per-provider accept/reject format matrix; `provider=halo` + `CHG0012345` → rejected with a **Halo-named** message (US1 acceptance 2); unknown provider → configuration error, never a fallback (FR-003)
- [ ] T034 [P] [US1] Write `tests/itsm-gate/test_gate_policy.py` — `none`/lab bypass precedence (US1 acceptance 4); `provider=servicenow` produces behavior identical to the Phase 2 baseline (US1 acceptance 3); the verified/unverified distinction placeholder that T036 fills in
- [ ] T035 [US1] **SC-002 check**: with a non-ServiceNow provider configured, assert that no gate output, error message, or prompt emitted on a gated-write path contains the string "ServiceNow" — as an automated test, not a manual read

**Checkpoint**: US1 + US2 both hold. An operator can pick their ITSM; a maintainer changing gate behavior edits one module. Regex count 4 → 1 for gating (**SC-001**), plus the one deferred provenance check.

---

## Phase 5: User Story 3 — Skill-Layer Verification Is Documented and Auditable (Priority: P2) — ⛔ BLOCKED

**Goal**: Make the safety posture honest. The server-side gate enforces **format + policy**; the **skill layer** verifies a change record's **state**; the GAIT trail shows which of the two actually happened.

**Independent Test**: Run a gated write through the provider's change skill and confirm the GAIT record shows the reference, the provider, and that state was **verified**. Then call the gated tool directly with no attestation and confirm the decision is recorded as **unverified** — never reported as verified.

### Implementation for User Story 3

- [ ] T036 [US3] Implement the verified/unverified distinction in the `GateDecision` (FR-008): the envelope must be able to say "state verified by the skill layer" versus "state not verified", and must **never** report verification that did not occur (US3 acceptance 1 & 3). Today's code implies verification it does not perform — this task is what stops that
- [ ] T037 [US3] Implement the attestation input per the Q4 answer — the value a verifying skill passes into the gate — defaulting to **unattested** for any direct tool call. Attestation is a precondition for any future strict mode (Q3)
- [ ] T038 [US3] Implement `src/netclaw_itsm/audit.py` — emit a structured gate-decision record carrying provider, change reference, verification status, and allow/deny outcome (FR-013), using the emit/commit seam recorded in `research.md`. The gate **emits**; the session/skill layer **commits** to GAIT — the gate itself must do no git, subprocess, or filesystem work on a synchronous write path
- [ ] T039 [P] [US3] Document, per provider, **which skill verifies state** before a gated write (FR-007, US3 acceptance 4): `servicenow` → `workspace/skills/servicenow-change-workflow/SKILL.md`; `halo` → feature 069's `halo-change-request` skill, marked **unavailable on this branch** (PR #167 unmerged); `atlassian` → the `atlassian-mcp`-backed change skill; `none` → no verification by definition. Also note (per Open Question 8) that ServiceNow is reachable only as an **unregistered install-time clone** (`$SERVICENOW_MCP_SCRIPT` via `$MCP_CALL`), which constrains how its verification skill can honestly be described
- [ ] T040 [P] [US3] Document the advisory boundary explicitly, without softening it: MCP servers cannot call other MCP servers, so the server-side gate is advisory **by construction** — a direct tool call can assert any reference, and an attested state is only as trustworthy as the caller. State plainly that this is **not a regression** (today's `_check_servicenow_cr_state()` returns `None`, so nothing is enforced now either); the change is that the boundary becomes honest and auditable instead of implied
- [ ] T041 [P] [US3] Document FR-016 as a **known deferred inconsistency**: `memory_record_decision(cr_number=…)` validates `^CHG\d+$` at `mcp-servers/memory-mcp/storage/sqlite_store.py:109` for audit provenance, so a Halo or Jira shop's change reference will fail that validation. It is provenance metadata, not a gate — deferred on purpose, but user-visible and therefore documented rather than discovered
- [ ] T042 [US3] **SC-006 check**: confirm an auditor reading a single GAIT record for a gated write can determine the provider, the change reference, and whether the change record's state was actually verified

**Checkpoint**: "Advisory" has become "advisory **and** auditable". The gate no longer claims verification it cannot perform.

---

## Phase 6: User Story 4 — The Constitution Describes Provider-Agnostic Gating (Priority: P3) — ⛔ BLOCKED

**Goal**: Amend all five ServiceNow-naming locations together, so no contributor can read the Constitution and conclude ServiceNow is the only supported ITSM.

**Independent Test**: A contributor who has read **only** the amended Constitution can correctly state (a) the gating ITSM is configurable, (b) lab mode remains the sole bypass and is still GAIT-logged, and (c) no specific vendor is mandated (**SC-005**).

**Exactly two tasks**, mirroring feature 049's T022/T023 — the text edit, then the Sync Impact Report and version bump. Amending Principle III alone would leave **four contradicting references** in the same document, so this is **all-or-nothing across the five locations**.

### Implementation for User Story 4

- [ ] T043 [US4] In `.specify/memory/constitution.md`, edit all **five** ServiceNow-naming locations so each describes **the configured ITSM**: **Principle III — ITSM-Gated Changes** (`:55-64`, "an approved ServiceNow Change Request (CR)"); **Principle VIII — Verify After Every Change** (`:114`, "mark the ServiceNow CR as failed"); **Principle XIV — Human-in-the-Loop** (`:200`, "Creating, updating, or closing ServiceNow tickets"); **Operational Constraints → Technology Stack** (`:260`, "**ITSM**: ServiceNow (change management, incidents, CMDB)"); **Operational Constraints → Forbidden Operations** (`:269`, "Bypassing ServiceNow CR approval for production changes"). Preserve each principle's substance exactly — an approved change record is still required, lab mode is still the **sole** exception, bypasses are still GAIT-logged, and bypassing approval is still forbidden. Apply the T010/Q9 decision on whether Principle III's "Assess → Authorize → Implement → Review" lifecycle wording (ServiceNow's own vocabulary) is also generalized
- [ ] T044 [US4] Rewrite the top-of-file **Sync Impact Report** comment block in the established format (matching the existing 1.1.0 → 1.2.0 block): version-change line stating **1.2.0 → 1.3.0 (MINOR — principle generalization)** with the reasoning that this generalizes existing principle text and neither removes nor redefines a principle; the five modified locations listed; added/removed sections (**None**/**None**); the templates-requiring-updates checklist; follow-up TODOs (carry FR-016's deferred Memory MCP inconsistency and the nautobot follow-on phase); and prior versions compressed into **"Previous version history"** including 1.2.0. Then bump the footer to `**Version**: 1.3.0 | **Ratified**: 2026-03-26 | **Last Amended**: <amendment date>` (US4 acceptance 1, 3 & 4)

**Checkpoint**: Governance and code agree. Principle III's Constitution Check row in `plan.md` can now honestly move from **AMENDED** to **PASS**.

---

## Phase 7: Follow-On — Nautobot Migration (35 Gated Tools) — **NOT IN v1** 🚫

**Purpose**: Fold the three nautobot servers onto the shared gate. **This phase is specified, not implemented** (FR-014, `spec.md` Non-Goals, US2 acceptance 5). It is a **separate feature branch and a separate PR**, and none of it may be pulled forward into v1 — doing so is what makes SC-003 unfalsifiable, because a 42-tool blast radius with two incompatible contracts and defaults that flip in opposite directions cannot be characterization-tested as one unit.

Scope: `mcp-servers/nautobot-mcp-v2/server.py` (`_check_itsm()` at `:39`), `mcp-servers/nautobot-routing-mcp/server.py` (`:57`), `mcp-servers/nautobot-golden-config-mcp/server.py` (`:61`) — **35 gated tools**, contract `_check_itsm() -> Optional[str]`, env `ITSM_ENABLED` + `ITSM_LAB_MODE`, gating currently defaults **OFF**, `cr_number` **optional**, venv interpreter.

- [ ] T045 [FOLLOW-ON] **Compatibility analysis (gates the whole phase)** — document the complete delta between `_check_itsm() -> Optional[str]` and `validate_change_request() -> dict`, item by item, and decide for each one: *preserve*, *migrate*, or *break with a documented migration path* per Constitution **Principle XV**. The items: return type (`Optional[str]` vs. dict envelope); **absence of any format check** in `_check_itsm()`; env scheme (`ITSM_ENABLED` + `ITSM_LAB_MODE` vs. `NETCLAW_ITSM_PROVIDER` + `NETCLAW_LAB_MODE`); default posture (gating **OFF** vs. **ON**); `cr_number` **optional** vs. **required**; and the venv interpreter vs. bare `python3` (the reason `src/netclaw_itsm/` is a `sys.path` insert and not an installed package). Resolve Open Question 7 here
- [ ] T046 [FOLLOW-ON] Write characterization tests for all three `_check_itsm()` implementations **before** touching them — same discipline as Phase 2, and equally non-negotiable given the 35-tool surface
- [ ] T047 [FOLLOW-ON] Add an `_check_itsm()`-shaped adapter over the shared gate that keeps the `Optional[str]` return and the **optional** `cr_number`, so no nautobot tool signature changes (FR-010 applies to this phase too)
- [ ] T048 [FOLLOW-ON] Re-point the three servers at the adapter; all 35 call sites unchanged; re-run T046's suite with zero assertion edits
- [ ] T049 [FOLLOW-ON] Env compatibility: honor `ITSM_ENABLED`/`ITSM_LAB_MODE` with **defaults preserved** — gating stays **OFF** unless T045 explicitly decides otherwise and documents the migration. Silently flipping 35 tools from ungated to gated is a breaking change dressed as a refactor
- [ ] T050 [FOLLOW-ON] Add `NETCLAW_ITSM_PROVIDER` to all three nautobot env blocks in `config/openclaw.json` (FR-015), and reconcile it with the `ITSM_*` variables they already receive

---

## Phase 8: Polish & Cross-Cutting Concerns — ⛔ BLOCKED

**Purpose**: Constitution **Principle XI** artifact coherence (**NON-NEGOTIABLE** — a PR missing these must not merge) plus triage of the three defects this feature discovered but did not cause.

### Constitution XI coherence updates

- [ ] T051 [P] `.env.example` — add `NETCLAW_ITSM_PROVIDER` with a description and **no value** (Principle XIII), noting the supported values and that it coexists with `NETCLAW_LAB_MODE` (`:119`) and the nautobot pair `ITSM_ENABLED`/`ITSM_LAB_MODE` (`:397-398`) until Phase 7 lands
- [ ] T052 [P] `SOUL.md` — replace ServiceNow-as-the-ITSM framing in the capability summary and identity references with the configurable-provider model; name the per-provider verification skills
- [ ] T053 [P] `SOUL-SKILLS.md` — same reframing for the skill index, including which skill verifies change state per provider
- [ ] T054 [P] `README.md` — describe ITSM gating as provider-selectable; document `NETCLAW_ITSM_PROVIDER`; state the v1 boundary honestly (7 tools now, 35 in a follow-on phase)
- [ ] T055 [P] `TOOLS.md` — update the infrastructure reference so ITSM is listed as configurable rather than as ServiceNow
- [ ] T056 `config/openclaw.json` — full env-block sweep confirming **every** gated server receives `NETCLAW_ITSM_PROVIDER` (FR-015); this is the task that catches the `gnmi-mcp` `:81-90` omission if T032 missed it
- [ ] T057 [P] `SKILL.md` sweep — **66** `SKILL.md` files under `workspace/skills/` currently mention ServiceNow. Update the ones on a v1 gated-write path first (`workspace/skills/servicenow-change-workflow/`, the Claroty skills, `gnmi-telemetry`), and leave an explicit, enumerated list of the remainder as a documented follow-up rather than silently touching or silently skipping all 66

### Discovered-defect triage (found by this feature, out of its scope)

- [ ] T058 [P] **Dangling config entry** — `config/openclaw.json:291-304` registers `aruba-cx-mcp` with `ITSM_ENABLED`/`ITSM_LAB_MODE`, but `mcp-servers/aruba-cx-mcp/` **does not exist**, while its skills and contract spec document it as live. File for triage as its own fix (it is a coverage/registration defect, not a gating defect) — do not quietly delete a registration whose docs claim it works
- [ ] T059 [P] **`gnmi-mcp` receives no ITSM env var** — `config/openclaw.json:81-90`; its lab bypass depends on parent-environment leakage. Closed by T032; confirm and record the closure here so the defect is not double-reported
- [ ] T060 [P] **Dead `GnmiSetRequest` validator** — `mcp-servers/gnmi-mcp/models.py:186-207`, carrying a second `^CHG\d+$` regex at `:198`. Closed by T025; confirm and record

### Final validation

- [ ] T061 Run `quickstart.md` end to end against a real deployment: select each provider in turn, run a gated write, read the GAIT record, and trip the unknown-provider error deliberately
- [ ] T062 Verify all seven success criteria are met — **SC-001** (4 format validators → 1), **SC-002** (no "ServiceNow" leakage under another provider), **SC-003** (100% of pre-refactor assertions pass), **SC-004** (0 tests → a suite covering per-provider formats, unknown-provider error, lab/none bypass, verified/unverified), **SC-005** (Constitution reads provider-agnostic), **SC-006** (auditable GAIT record), **SC-007** (zero parameter changes) — then record the GAIT session log and draft the Principle XVII milestone blog post

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 0 (Specification)**: Complete. No dependencies. Documentation only.
- **Phase 1 (Setup)**: **Blocked by T010** (maintainer ratification + Open Question answers). T011 and T012 may then run in parallel.
- **Phase 2 (Foundational)**: Depends on Phase 1. **BLOCKS every user story** — T015 is the hard gate, because there is no pre-existing test coverage to fall back on.
- **Phase 3 (US2 — consolidation)**: Depends on Phase 2. **BLOCKS Phase 4** — provider selection cannot be built on five divergent copies (`spec.md` US2).
- **Phase 4 (US1 — provider selection)**: Depends on Phase 3.
- **Phase 5 (US3 — verification honesty)**: Depends on Phase 4 (T036's verified/unverified distinction extends the envelope T030 established). T039–T041 are pure documentation and can start as soon as T027 fixes the adapter set.
- **Phase 6 (US4 — the amendment)**: Depends only on **T010**, not on any code. It can be done in parallel with Phases 3–5 by a different contributor — the constitution file is touched by nothing else. Sequenced last because governance should follow the implementation, but it is **required for completion** (FR-017).
- **Phase 7 (Follow-on nautobot)**: **NOT IN v1.** Depends on all of v1 having shipped and settled. Separate branch, separate PR.
- **Phase 8 (Polish)**: Depends on Phases 3–6 being complete. **Principle XI is NON-NEGOTIABLE** — T051–T057 are merge blockers, not nice-to-haves.

### User Story Dependencies

- **US2 (P1)** — no dependencies beyond Phase 2. Independently mergeable and independently valuable: it removes the five-way duplication even if nothing else lands.
- **US1 (P1)** — depends on US2. This is the one real cross-story dependency and it is stated in `spec.md` rather than inferred here.
- **US3 (P2)** — depends on US1's envelope work; its documentation tasks are independent.
- **US4 (P3)** — fully independent of US1/US2/US3 at the file level.

### Within Each User Story

- Characterization tests before **any** refactor (Phase 2 before Phase 3) — non-negotiable
- Data (`providers.py`) before logic that reads it (`gate.py` provider wiring)
- Shared module before shims before call-site verification
- Envelope shape (T030) before the verification indicator that extends it (T036)
- Every phase's own verification task runs before its checkpoint is claimed

### Parallel Opportunities

- Phase 0: T002–T007 were parallel (different artifacts)
- Phase 1: T011 and T012 (different trees)
- Phase 2: T013, T014, T016, T017 all parallel (different files); **T015 is a serialization point**
- Phase 4: T033 and T034 (different test files)
- Phase 5: T039, T040, T041 (documentation, different targets)
- **Phase 6 in parallel with Phases 3–5** — `.specify/memory/constitution.md` is touched by nothing else in this feature
- Phase 8: T051–T055 and T057–T060 all parallel (different files); T056 and T061–T062 serialize at the end

Caution: T018–T021 all converge on the same two shim files and the same shared module. They are logically ordered, not parallel — implement them in one working session to avoid edit conflicts.

---

## Parallel Example: Phase 2 (Foundational)

```bash
# Launch the characterization tests together — different files, no shared state:
Task: "Write tests/itsm-gate/test_characterization_gnmi.py against the unrefactored mcp-servers/gnmi-mcp/itsm_gate.py"
Task: "Write tests/itsm-gate/test_characterization_claroty.py against the unrefactored mcp-servers/claroty-mcp/utils/itsm_gate.py"

# And the two baseline snapshots, also in parallel:
Task: "Snapshot the 7 v1 call sites + parameter names/requiredness into contracts/itsm-gate-contract.md (SC-007 baseline)"
Task: "Snapshot the 4 ^CHG\\d+$ regex locations (SC-001 baseline)"

# Then SERIALIZE on the gate — nothing in Phase 3 starts until this passes:
Task: "Run tests/itsm-gate/ against the UNREFACTORED code; require 100% pass (T015)"
```

---

## Implementation Strategy

### Step 0: Decide whether to implement at all

`plan.md`'s Constitution Check marks Principle III **AMENDED, not PASS** — this feature *is* the proposed change to a safety principle, so compliance cannot be self-asserted. **T010 is the only task that may be started.** If the maintainer declines ratification, the nine spec artifacts stand as a documented, rejected proposal with a full current-state inventory — a legitimate outcome that still leaves the repo better understood than it was.

### MVP First (US2 → US1)

1. Phase 1: Setup (T010–T012)
2. Phase 2: Foundational (T013–T017) — **the characterization suite must pass against unrefactored code**
3. Phase 3: US2 — consolidation (T018–T026)
4. **STOP and VALIDATE**: the characterization suite passes unchanged; `git diff` shows zero tool-signature changes; Claroty's published envelope still carries all four keys
5. Phase 4: US1 — provider selection (T027–T035)
6. **STOP and VALIDATE**: SC-002 (no "ServiceNow" leakage) and US1's five acceptance scenarios

### Incremental Delivery

1. Phases 1–2 → a safety net exists where there was none (0 → a real suite). Valuable on its own: the gate becomes changeable.
2. + US2 → 5 implementations become 1; zero regression proven. Mergeable alone.
3. + US1 → the actual feature; a Halo shop stops being asked for a ServiceNow CR.
4. + US3 → the posture becomes honest and auditable.
5. + US4 → governance matches the code; Principle III's row moves to PASS.
6. + Phase 8 → Principle XI satisfied; merge becomes permissible.
7. **Later, separately**: Phase 7 brings the remaining 35 tools across.

### Suggested MVP Scope

**US2 is the true MVP**, even though US1 is the headline. US2 is what converts "a bug that must be fixed in five places with no tests" into "a bug that can be fixed in one place with a safety net". US1 is the visible payoff, but shipping US1 without US2 would mean four more copies of the same abstraction — the failure mode this feature exists to end.

### Parallel Team Strategy

With multiple contributors, after **T010**:

- Contributor A: Phases 1–2 (setup + characterization), then Phase 3 (US2)
- Contributor B: Phase 6 (US4, the amendment) — no file overlap with anyone, can start immediately after T010
- Contributor C: Phase 5's documentation tasks (T039–T041) and Phase 8's doc sweep (T051–T055, T057), drafted against `spec.md` and reconciled once T027 fixes the adapter set
- Then A + C converge on Phase 4 (US1)

---

## Notes

- **`[P]`** = different files, no dependencies. **`[Story]`** maps a task to a user story for traceability.
- **Do not adjust a characterization assertion to make a refactor pass.** That inverts the entire purpose of Phase 2. If T022 fails, the refactor is wrong.
- **`cr_number` keeps its ServiceNow-flavored name forever.** It is a published envelope key (Claroty emits the dict verbatim) and an MCP tool parameter on six tools. Renaming it is breaking; living with the name is not (FR-009, FR-010, SC-007).
- **No new third-party dependency, in any phase.** The shared gate is stdlib-only by design, because the gate must be synchronous (`gnmi_set` is a plain `def`) and must make no network calls. Introducing `httpx` here would force an async surface `gnmi_set` cannot await and would place per-ITSM credentials inside every gated server.
- **MCP servers cannot call other MCP servers** — no MCP client exists anywhere under `mcp-servers/`. Any task that seems to require one is misspecified; the answer is skill-layer verification plus attestation.
- **Feature 069 (Halo MCP) is an unmerged dependency** (PR #167). `halo-mcp` and the `halo-change-request` skill **do not exist on this branch**. The `halo` adapter must ship with its verification skill marked *unavailable* if 069 does not land — a dangling reference to a nonexistent skill would be worse than the ServiceNow hardcoding this feature removes.
- **Phase 7 is a fence, not a suggestion.** 35 tools, a different contract, a different env scheme, a different default, a different requiredness, and a different interpreter. Pulling any of it into v1 destroys SC-003's falsifiability.
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.
