# Implementation Plan: ITSM Provider Abstraction for Change Gating

**Branch**: `070-itsm-provider-abstraction` | **Date**: 2026-07-24 | **Spec**: `specs/070-itsm-provider-abstraction/spec.md`
**Input**: Feature specification from `/specs/070-itsm-provider-abstraction/spec.md`

> **Status of this plan**: This round's deliverable is **documentation only** — the nine-artifact spec set (spec, plan, research, data-model, quickstart, two contracts, requirements checklist, tasks). **No code, config, or constitution file is modified by this feature branch yet.** Implementation requires a Constitution amendment (1.2.0 → 1.3.0) and **MUST NOT begin before that amendment is ratified by the maintainer** (spec.md Status; Constitution Governance). Every implementation task in `tasks.md` is marked BLOCKED accordingly.

## Summary

NetClaw's change gate is hardwired to ServiceNow in three layers — the Constitution, `itsm_gate.py`, and the skill layer — and the same gate logic exists **five times across five servers** behind **two incompatible contracts**, guarding **42 gated tools** with **four independent `^CHG\d+$` regexes** and **zero tests**. The gate also enforces nothing today: `_check_servicenow_cr_state()` unconditionally returns `None`, so every well-formed `CHG…` reference passes as `{valid: True, state: "unverified"}`, and no `servicenow-mcp` is registered in `config/openclaw.json`.

This plan consolidates the two servers using the `validate_change_request()` dict-envelope contract onto **one shared, provider-agnostic module** at `src/netclaw_itsm/` — mirroring the `src/netclaw_tokens/` precedent (a `sys.path` insert anchored on `__file__`, already used by 8 servers) — and makes the active ITSM selectable via `NETCLAW_ITSM_PROVIDER` across `servicenow`, `halo`, `atlassian`, and `none`. **v1 covers 7 gated tools** (`gnmi_set` plus Claroty's 6 writes). The **three nautobot servers (35 gated tools, `_check_itsm() -> Optional[str]`, `ITSM_ENABLED`/`ITSM_LAB_MODE`, gating defaults OFF, `cr_number` optional) are specified but explicitly NOT implemented in v1** — they are a distinct follow-on phase with its own compatibility analysis. Memory MCP's `validate_cr_number()` is deferred (it is CR provenance metadata, not a gate); the dead `GnmiSetRequest` validator at `mcp-servers/gnmi-mcp/models.py:198` is removed.

Two architectural facts shape everything below. First, **NetClaw MCP servers cannot call other MCP servers** — no MCP client exists anywhere under `mcp-servers/` — so verification of a change record's *state* can only happen at the agent/skill layer, and the shared gate makes **no network calls** and must be **synchronously** callable (`gnmi_set` at `mcp-servers/gnmi-mcp/gnmi_mcp_server.py:196` is a plain `def`). Second, **back-compat is a hard requirement**: the envelope keys `valid`, `message`, `cr_number`, `state` are a public contract because Claroty publishes the whole dict as `{"itsm_gate": …}` in tool output, and no MCP tool parameter may be renamed (gnmi's `change_request_number` and Claroty's `cr_number` both stay, both required). Thin shims are retained at both existing gate paths so no import or call site churns. Finally, the Constitution's **five ServiceNow-naming locations** are amended together as a MINOR bump — Principle III (`:55-64`), Principle VIII (`:114`), Principle XIV (`:200`), Technology Stack (`:260`), and Forbidden Operations (`:269`).

## Technical Context

**Language/Version**: Python 3.10+ (matches every gated server and the `src/netclaw_tokens/` precedent; `from __future__ import annotations` + `X | None` unions already in use in both existing gate files)
**Primary Dependencies**: **None new — Python standard library only (`os`, `re`, `logging`, `typing`), deliberately.** The gate makes no HTTP calls by design (FR-006), so it needs no client library, no credentials, and no async runtime. This is not minimalism for its own sake: adding `httpx` would force an async surface that `gnmi_set`'s plain `def` cannot await, and would put per-ITSM credentials inside every gated server.
**Storage**: N/A — the gate is stateless. Provider selection is resolved from the process environment on each call; no database, no cache, no file state. (Memory MCP's SQLite is read/written by Memory MCP alone and is explicitly out of scope, FR-016.)
**Testing**: `pytest` — a **characterization suite where none exists today**. Coverage is currently 0 tests across all 5 gate implementations, so the suite is written **first**, against the **unrefactored** code, and must pass before the shared module replaces anything (FR-011, US2 acceptance 1, SC-003/SC-004). New suite lives at `tests/itsm-gate/` following the per-component convention (`tests/halo-mcp/` from feature 069, with its own `conftest.py` + `pytest.ini`).
**Target Platform**: Linux, macOS, WSL2 — same as every NetClaw MCP server. Note the repo runs **mixed interpreters** (the nautobot servers use a venv python; gnmi/claroty use bare `python3`), which is a first-class constraint on how the shared module is delivered.
**Project Type**: Shared in-process Python library plus a governance amendment. No new MCP server, no new transport, no new catalog component, no UI.
**Performance Goals**: N/A in throughput terms. The relevant budget is that the gate must add negligible latency to a write path and must not block: **no network I/O, no git I/O, no disk I/O on the hot path** — a regex match plus an environment lookup.
**Constraints** (all hard):
- **Synchronously callable** — `gnmi_set` is a plain `def`; the gate cannot be a coroutine and cannot require an event loop.
- **No network calls from the gate** — state verification belongs to the skill layer (FR-006/FR-007). MCP servers cannot call other MCP servers.
- **No MCP tool parameter renames or requiredness changes** — `change_request_number` (gnmi, required), `cr_number` (claroty, required), `cr_number` (nautobot, optional) all survive verbatim (FR-010, SC-007).
- **Envelope keys are a public contract** — `valid`, `message`, `cr_number`, `state` keep their names and meanings; `provider` and the verification indicator are **additive only** (FR-009), because Claroty emits the dict verbatim (`mcp-servers/claroty-mcp/tools/alerts.py:182`, `devices.py:228`/`:284`, plus the success paths).
- **No silent vendor fallback** — an unrecognized provider is a loud configuration error, never a quiet default to ServiceNow (FR-003); that silent-default behavior is the bug being fixed.
- **Zero behavior regression under the status-quo provider** — 100% of pre-refactor characterization assertions must pass after (SC-003).
- **`NETCLAW_ITSM_PROVIDER` must reach every gated server through its `config/openclaw.json` env block** (FR-015) — `gnmi-mcp` at `config/openclaw.json:81-90` currently passes **no ITSM variable at all**, so its lab bypass works only by parent-environment leakage; miss this and the feature silently misconfigures.
- **Implementation is gated on maintainer ratification** of the Constitution amendment (Principle XVI + Governance).

**Scale/Scope**: **v1 = 7 gated tools** across 2 servers (`gnmi_set`; Claroty's 6 writes at `tools/alerts.py:180`, `tools/devices.py:226` and `:282`, `tools/user_actions.py:47` and `:109`, `tools/vulnerabilities.py:209`). **35 further gated tools across 3 nautobot servers are specified but not implemented** (follow-on phase). Consolidation: **5 gate implementations → 1** shared module plus 2 thin shims; **4 independent `^CHG\d+$` regexes → 1** (excluding the deferred Memory MCP provenance check). **4 provider adapters** (`servicenow`, `halo`, `atlassian`, `none`). **1 Constitution amendment across 5 locations**, 1.2.0 → 1.3.0 MINOR. **9 spec artifacts** in this directory. **0 → a full gate test suite.**

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` **v1.2.0** (the version in force as this plan is written). Five rows are marked **AMENDED** because this feature's own deliverable is the change to that text — see the self-reference note below the table.

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First Operations (NON-NEGOTIABLE) | PASS | The gate sits in front of writes and this feature only strengthens it. No new bypass is introduced: the lab/no-ITSM path already exists and is preserved with its GAIT logging intact (FR-012). Device interaction itself is untouched. |
| II. Read-Before-Write | N/A | No device configuration path changes. `observe → baseline → modify → verify` is unaffected. |
| III. ITSM-Gated Changes | **AMENDED — this feature *is* the change to Principle III** | `:55-64` currently mandates "an approved **ServiceNow** Change Request". FR-017 generalizes that to "the configured ITSM". The *substance* of the principle is preserved exactly — changes still require an approved change record, lab mode remains the **sole** exception, and it remains GAIT-logged. Open Question 9 asks the maintainer whether the "Assess → Authorize → Implement → Review" lifecycle wording (which is ServiceNow's vocabulary) should also be generalized. This row cannot honestly be marked PASS against v1.2.0, because compliance with the amended text is what is being proposed, not asserted. |
| IV. Immutable Audit Trail | PASS (strengthened) | FR-013 requires **every** gate decision to be GAIT-recorded with provider, change reference, verification status, and allow/deny outcome — strictly more audit than today, and the basis for SC-006. FR-012 keeps every lab bypass logged. **Design constraint to honor**: the gate cannot perform git I/O itself (sync + no-I/O-on-hot-path), so it emits a structured decision record that the session/skill layer commits to the GAIT trail; that split is a Phase 0 research item, not an assumption. |
| V. MCP-Native Integration | PASS | No new MCP server, no new transport, no protocol change. A shared in-process Python library imported by existing FastMCP servers, exactly as `src/netclaw_tokens/` already is by 8 of them. Notably this feature *declines* to introduce server-to-server MCP calls — none exist in the repo, and inventing a bespoke one would violate this principle rather than satisfy it. |
| VI. Multi-Vendor Neutrality | PASS (this feature's core subject) | This is Principle VI applied to ITSM. Vendor-specific facts (reference format, display name, approved-state vocabulary, responsible skill) move into declarative `ProviderAdapter` data (FR-004); the shared gate holds no vendor logic and no vendor default (FR-003). |
| VII. Skill Modularity | PASS | US3 documents **one** verification skill per provider rather than growing any skill's charter. `workspace/skills/servicenow-change-workflow/SKILL.md` remains the ServiceNow verifier; Halo's counterpart is feature 069's `halo-change-request` skill, which **does not exist on this branch** (PR #167 unmerged) — so the `halo` adapter ships with its verification skill marked unavailable if 069 does not land. |
| VIII. Verify After Every Change | PASS + **AMENDED (location 2 of 5)** | The verify workflow is unchanged. The amendment touches only `:114`'s "mark the **ServiceNow** CR as failed", which becomes provider-agnostic. Separately, US2's characterization-first sequencing is this principle applied to a refactor: capture the baseline, apply, verify against the baseline. |
| IX. Security by Default | PASS | The gate holds **no credentials** and opens **no network path** by design (FR-006), so this adds zero credential surface and zero new privilege. It also improves honesty: today's code *implies* it verifies CR state and does not. Documenting the advisory boundary (spec Assumptions, FR-007/FR-008) is a security-posture improvement, not a weakening — nothing is being turned off that was ever on. |
| X. Observability as a First-Class Citizen | PASS (adapted) | No new monitored system, so no new HUD node is required by this feature. Gate decisions do become observable with provider and verification status attached (SC-006). If a HUD posture line for the active ITSM provider is wanted, it is a Polish nicety, not a completion criterion. |
| XI. Full-Stack Artifact Coherence (NON-NEGOTIABLE) | PASS **conditional on the Polish phase completing** | No new MCP server and no new installable component ⇒ `scripts/lib/catalog.sh`, `scripts/lib/install-steps.sh`, and `scripts/verify-catalog-coverage.py` are **not** touched. The touchpoints that **do** apply are blocking Polish tasks: `.env.example` (`NETCLAW_ITSM_PROVIDER`, no value), `config/openclaw.json` env blocks (FR-015 — `gnmi-mcp` `:81-90` and `claroty-mcp` `:551-558`), `SOUL.md`, `SOUL-SKILLS.md`, `README.md`, `TOOLS.md`, and the affected `SKILL.md` files. Pre-existing, **not** caused here: `config/openclaw.json:291-304` registers `aruba-cx-mcp` with ITSM variables while `mcp-servers/aruba-cx-mcp/` does not exist — reported for triage, not fixed by this feature. |
| XII. Documentation-as-Code | PASS | FR-007 (per-provider verification skill) and FR-016 (Memory MCP's deferred ServiceNow-shaped provenance check) are **requirements**, not follow-ups, so docs land in the same PR as the code by construction. |
| XIII. Credential Safety | PASS | Nothing secret is introduced. `NETCLAW_ITSM_PROVIDER` is non-secret configuration, documented in `.env.example` with a description and **no value**. The gate reads it from the environment at runtime, never from a config file baked with a value. |
| XIV. Human-in-the-Loop for External Communications | PASS + **AMENDED (location 3 of 5)** | Substance holds — nothing here sends messages or writes tickets; the gate never mutates an ITSM record. The amendment touches only `:200`'s "Creating, updating, or closing **ServiceNow** tickets", which becomes provider-agnostic. This principle also governs the amendment itself: the maintainer, not this plan, ratifies it. |
| XV. Backwards Compatibility | PASS (hard requirement, this feature's second core subject) | FR-009 (additive envelope keys only), FR-010 (no parameter renames), FR-011 (characterization tests before the refactor), SC-003 (100% of prior assertions pass), SC-007 (zero parameter changes), retained thin shims at both existing gate paths, nautobot left entirely alone in v1, and dual env schemes allowed to coexist. New dependency conflicts are impossible — there are no new dependencies. |
| XVI. Spec-Driven Development | PASS | Full specify → plan → tasks before any code, which is precisely why this round ships documentation only. The sharper reading is deliberate: "no implementation work begins without a ratified spec" — and a spec whose completion **requires** a constitutional amendment is not ratified until that amendment is. |
| XVII. Milestone Documentation via WordPress | DEFERRED | Applies post-implementation. Nothing shipped this round — a rejected-or-pending proposal is not a milestone. Recorded as a session-log note per the principle's own fallback clause, and carried as `tasks.md` T062. |
| Operational Constraints → Technology Stack | **AMENDED (location 4 of 5)** | `:260` reads `**ITSM**: ServiceNow (change management, incidents, CMDB)`. Becomes provider-agnostic, naming ServiceNow, HaloPSA/HaloITSM, and Atlassian/Jira as supported options rather than mandating one. |
| Operational Constraints → Forbidden Operations | **AMENDED (location 5 of 5)** | `:269` reads `Bypassing **ServiceNow** CR approval for production changes`. Becomes provider-agnostic; lab mode remains the sole sanctioned bypass and remains GAIT-logged. |
| Operational Constraints → MCP Server Standards | PASS | "Write operations MUST be explicitly flagged and gated" — this feature is that gating, consolidated. No new MCP server, so the per-server `README.md` requirement is not triggered; the shared module gets its own docs instead. |
| Governance → amendment process | PASS | All three required elements are produced: (1) documented rationale, (2) review of impact on existing principles (this table), (3) a semantic version bump. **MINOR, 1.2.0 → 1.3.0** — the amendment generalizes existing principle text and removes no principle and redefines none, the same reasoning the 1.1.0 → 1.2.0 amendment used for Principle XI. The Sync Impact Report is rewritten in the established format with prior versions compressed into "Previous version history" (US4 acceptance 4). |

### Self-reference note (Principle III) — read this before treating the gate as passed

Feature 049 hit this same shape with Principle XI and marked it `PASS (this feature's core subject)` because the artifact-coherence work *was* the amendment. Principle III is a harder case and is marked differently on purpose.

Principle XI is a process rule about which files to touch; 049's amendment changed the file list and complied with the rule in the act of changing it. Principle III is a **safety** rule (and Forbidden Operations makes bypassing it a forbidden operation). A plan cannot mark a safety principle "PASS" by pointing at text it proposes to rewrite — that is circular, and circular reasoning is exactly how a gating feature ends up weakening the gate it claims to strengthen. So:

- Against the **current** text (v1.2.0), this feature does **not** claim compliance for III. It claims that the proposal preserves the principle's substance — approved change record required, lab mode the sole exception, still GAIT-logged — while removing the vendor name.
- Against the **amended** text (v1.3.0), the feature complies. That is why implementation is **BLOCKED pending ratification**: the maintainer's ratification is what converts this row from AMENDED to PASS, and nothing in `tasks.md` may proceed on the assumption that it will.
- Because Principle VIII, Principle XIV, Technology Stack, and Forbidden Operations all restate the same ServiceNow assumption, amending III alone would leave **four contradicting references** in the same document. The amendment is therefore **all-or-nothing across all five locations** (US4, FR-017).

**Gate verdict**: **PASS with one gate held open.** No principle is violated, no complexity requires waiving a rule, and every applicable coherence touchpoint is tracked. The single open gate is ratification of the 1.3.0 amendment; until it closes, this feature ships specification artifacts only.

## Project Structure

### Documentation (this feature)

Ten artifacts: the set features 065/068 shipped, plus a second contract for the amendment itself and a GAIT session log (Principle IV):

```text
specs/070-itsm-provider-abstraction/
├── spec.md                          # Feature specification — SOURCE OF TRUTH (DRAFT, awaiting ratification)
├── plan.md                          # This file
├── research.md                      # Phase 0 — the 5-implementation survey with file:line evidence,
│                                    #   sync/no-network rationale, the src/netclaw_tokens/ precedent
│                                    #   decision, GAIT emit/commit seam, the 9 open questions
├── data-model.md                    # Phase 1 — ItsmProvider, ProviderAdapter, ChangeRef, GateDecision,
│                                    #   GateConfig
├── quickstart.md                    # Phase 1 — operator walkthrough: select a provider, run a gated write,
│                                    #   read the GAIT record, switch providers, trip the unknown-provider error
├── contracts/
│   ├── itsm-gate-contract.md        # Phase 1 — validate_change_request(cr_number) ->
│   │                                #   dict{valid,message,cr_number,state} plus the additive
│   │                                #   provider/verification keys; the nautobot _check_itsm() ->
│   │                                #   Optional[str] contract documented as the follow-on target
│   └── constitution-amendment.md    # Phase 1 — the exact before/after text for all five ServiceNow-naming
│                                    #   locations, so US4 is a reviewable diff rather than an intention
├── checklists/
│   └── requirements.md              # Requirements + Constitution XI coherence checklist
├── gait-session-log.md              # Principle IV — append-only audit trail of the four scoping
│                                    #   decisions, the exploration findings that corrected scope,
│                                    #   and the line-number/GAIT-emission corrections
└── tasks.md                         # Phase 2 output — every implementation task marked BLOCKED
```

### Source Code (repository root)

Paths below are what implementation **will** touch once ratified. Nothing in this tree is modified by this documentation round.

```text
src/
├── netclaw_tokens/                     # EXISTING precedent this feature copies (imported by 8 servers via
│                                       #   sys.path insert anchored on __file__ — e.g. gnmi_mcp_server.py:31)
└── netclaw_itsm/                       # NEW — the single shared, provider-agnostic gate (stdlib only)
    ├── __init__.py                     #   public surface: validate_change_request(), provider registry
    ├── config.py                       #   NETCLAW_ITSM_PROVIDER + lab/bypass resolution  (FR-002, FR-003, FR-015)
    ├── providers.py                    #   declarative ProviderAdapter data: servicenow|halo|atlassian|none (FR-004)
    ├── gate.py                         #   format + policy evaluation; NO network, sync-callable
    │                                   #     (FR-005, FR-006, FR-008, FR-009)
    └── audit.py                        #   structured gate-decision record for the GAIT trail (FR-012, FR-013)
                                        #   NOTE: no requirements.txt — stdlib only, deliberately

mcp-servers/gnmi-mcp/
├── itsm_gate.py                        # RETAINED as a thin shim re-exporting src/netclaw_itsm  (FR-010, SC-007)
├── gnmi_mcp_server.py                  # gnmi_set() at :196 — plain `def`, param `change_request_number`;
│                                       #   import path and call site UNCHANGED
└── models.py                           # DELETE dead GnmiSetRequest ^CHG\d+$ validator (:186-207, regex at :198)

mcp-servers/claroty-mcp/
├── utils/itsm_gate.py                  # RETAINED as a thin shim re-exporting src/netclaw_itsm
└── tools/                              # 6 gated write call sites UNCHANGED; still publish {"itsm_gate": …}
    ├── alerts.py                       #   :180 gate, :182/:219/:223 envelope publication
    ├── devices.py                      #   :226 and :282 gates
    ├── user_actions.py                 #   :47 and :109 gates
    └── vulnerabilities.py              #   :209 gate

mcp-servers/nautobot-mcp-v2/server.py            # UNTOUCHED in v1 — _check_itsm() at :39, 35-tool follow-on phase
mcp-servers/nautobot-routing-mcp/server.py       # UNTOUCHED in v1 — _check_itsm() at :57
mcp-servers/nautobot-golden-config-mcp/server.py # UNTOUCHED in v1 — _check_itsm() at :61
mcp-servers/memory-mcp/storage/sqlite_store.py   # UNTOUCHED — validate_cr_number() at :109 deferred (FR-016)

tests/itsm-gate/                        # NEW — the coverage that does not exist today (FR-011, SC-004)
├── conftest.py                         #   env isolation for NETCLAW_ITSM_PROVIDER / NETCLAW_LAB_MODE
├── pytest.ini                          #   per-component config, matching tests/halo-mcp/ (feature 069)
├── test_characterization_gnmi.py       #   pins PRE-refactor gnmi validate_change_request() behavior
├── test_characterization_claroty.py    #   pins PRE-refactor claroty behavior + the published envelope
├── test_providers.py                   #   per-provider format validation; unknown-provider error (FR-003)
└── test_gate_policy.py                 #   lab/none bypass precedence; verified-vs-unverified (FR-008)

config/openclaw.json                    # + NETCLAW_ITSM_PROVIDER into every gated server's env block (FR-015):
                                        #   gnmi-mcp   :81-90   — currently passes NO ITSM variable at all
                                        #   claroty-mcp :551-558 — currently NETCLAW_LAB_MODE only (:557)
.env.example                            # + NETCLAW_ITSM_PROVIDER documented, no value (Principle XIII)
.specify/memory/constitution.md         # AMENDED 1.2.0 → 1.3.0 (MINOR) at five locations —
                                        #   III :55-64 · VIII :114 · XIV :200 · Tech Stack :260 · Forbidden :269
                                        #   plus a rewritten Sync Impact Report and footer version/date
SOUL.md, SOUL-SKILLS.md, README.md, TOOLS.md     # Principle XI coherence updates (Polish phase)
workspace/skills/servicenow-change-workflow/SKILL.md  # named as the `servicenow` provider's verification skill,
                                        #   reframed as one provider among several (US3, FR-007)
```

**Structure Decision**: The shared module goes at `src/netclaw_itsm/`, deliberately copying the **one cross-server Python pattern that already works in this repo** — `src/netclaw_tokens/`, imported through a `sys.path` insert anchored on `__file__` (see `mcp-servers/gnmi-mcp/gnmi_mcp_server.py:31`), currently consumed by 8 servers. A root-level installable package was considered and rejected for v1: no root packaging exists, and the repo runs **mixed interpreters** (the nautobot servers use a venv python while gnmi/claroty use bare `python3`), so a package installed into one interpreter would be invisible to the other — the exact failure the follow-on nautobot phase would trip over. The two existing gate files are **kept as thin shims** rather than deleted, so `from itsm_gate import validate_change_request` and `from utils.itsm_gate import validate_change_request` keep working verbatim across all 7 v1 call sites; that is what makes FR-010 and SC-007 achievable without touching a single tool signature. `src/netclaw_itsm/` carries **no `requirements.txt`** because it has no dependencies, and that is a design property to protect, not an omission. Tests go in their own per-component directory (`tests/itsm-gate/`) following feature 069's `tests/halo-mcp/` layout rather than being scattered into `tests/unit/`, because the characterization suite must be runnable as a single pre/post-refactor gate. The nautobot trio and Memory MCP appear in the tree only as **explicitly untouched** paths, so a reader can see the v1 boundary rather than infer it.

## Complexity Tracking

No constitution violation requires a waiver. Four deliberate complexities are nonetheless worth justifying up front, because each one *is* a place where a simpler design was available and rejected.

| Violation / Added Complexity | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **Two thin shims retained** (`mcp-servers/gnmi-mcp/itsm_gate.py`, `mcp-servers/claroty-mcp/utils/itsm_gate.py`) instead of deleting them and importing `netclaw_itsm` directly | They are what make "one implementation, zero call-site churn" simultaneously true. All 7 v1 call sites keep their existing import statements, so the characterization suite exercises unchanged code paths and SC-003 is a real test rather than a rewritten one. The shims also localize the `sys.path` insert per server, matching how `netclaw_tokens` is reached today. | Deleting them means editing 7 call sites in 6 files across 2 servers **in the same change** that swaps the gate implementation — mixing a behavioral refactor with an import refactor and destroying the ability to attribute any regression to one or the other. It would also put a `sys.path`-dependent import into tool modules that currently know nothing about `src/`. The residual cost is 2 files of ~5 lines each; the residual risk of the alternative is a silent gate regression on a write path. |
| **Phasing the nautobot family out of v1** (35 of 42 gated tools deferred), leaving **two** gate contracts and **two** env schemes alive simultaneously | The nautobot servers use a different contract (`_check_itsm() -> Optional[str]`, no format check), a different env scheme (`ITSM_ENABLED` + `ITSM_LAB_MODE`), a different default (**gating OFF**), a different parameter requiredness (`cr_number` **optional**), and a different interpreter. Folding them in during v1 would make the change a breaking env-var migration across 35 tools whose gate is currently off — landing in the same PR that must prove zero regression on 7 tools whose gate is currently on. | "Migrate all five servers at once" was rejected because it makes SC-003 unfalsifiable: a 42-tool blast radius with two incompatible contracts and defaults that flip in opposite directions cannot be characterization-tested as one unit. The interim cost is real and named honestly — two contracts and two env schemes coexist until the follow-on phase, and the coexistence is documented rather than hidden. The follow-on phase carries its own compatibility analysis task specifically so the default-off → default-? decision is made deliberately (Open Question 7). |
| **`ProviderAdapter` indirection for what is, in v1, four rows of static data** | FR-003 forbids a silent vendor default and FR-005 requires provider-named error messages, so provider facts (reference format, display name, approved-state vocabulary, responsible verification skill) must be addressable as data by the shared gate. Declaring them as data — with **no** transport or credential logic — is what keeps the gate vendor-neutral (Principle VI) and lets a fifth provider be one table entry rather than a fifth `if`. | Inline `if provider == "halo": …` branching in `gate.py` was rejected because it reproduces, at a smaller scale, the exact defect this feature exists to remove: vendor identity smeared across shared logic. The `halo` adapter's dangling verification-skill reference (feature 069 is unmerged, PR #167) is precisely the kind of fact that must live in data so it can be marked *unavailable* rather than crash a code path. |
| **Gate decisions emitted as structured records rather than written to GAIT by the gate itself** | FR-013 demands every decision reach the GAIT trail, while the gate must stay synchronous and do no I/O on a write path. Splitting *emit* from *commit* satisfies both: the gate produces the record (provider, reference, verification status, outcome) and the session/skill layer commits it. | Having `gate.py` invoke git directly was rejected — it would put filesystem and subprocess work inside a synchronous pre-write check on every gated call, in a module whose entire architectural value is that it does nothing but match a regex and read the environment. Dropping the requirement instead was also rejected: SC-006 (an auditor can determine provider, reference, and whether state was actually verified) is the payoff for admitting the gate is advisory, and without it US3 is just a comment in a file. The exact emit/commit seam is a Phase 0 research item, flagged rather than assumed. |
