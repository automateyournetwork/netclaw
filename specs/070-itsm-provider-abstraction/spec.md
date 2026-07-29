# Feature Specification: ITSM Provider Abstraction for Change Gating

**Feature Branch**: `070-itsm-provider-abstraction`
**Created**: 2026-07-24
**Status**: DRAFT — proposal for maintainer review. **Requires a Constitution amendment (1.2.0 → 1.3.0) and MUST NOT be implemented before that amendment is ratified.**
**Input**: Let the operator choose which ITSM system provides the change record that gates NetClaw's write operations, instead of NetClaw hard-assuming ServiceNow everywhere.

---

## Problem

NetClaw's change gating is hardwired to **ServiceNow** at three layers — the governance layer (Constitution), the code layer (`itsm_gate.py`), and the skill layer — so NetClaw "always talks about ServiceNow" even for organizations that run a different ITSM.

This is now a concrete friction point, because two NetClaw integrations **are themselves ITSMs** with native change management: **HaloPSA/HaloITSM** (feature 069, PR #167) and **Atlassian/Jira** (`atlassian-mcp`). For a Halo shop, the change record *is* the Halo change ticket; requiring a separate ServiceNow CR is redundant and wrong.

Two further facts make this more than cosmetic:

1. **The gate currently enforces nothing.** `_check_servicenow_cr_state()` unconditionally returns `None`, so every well-formed `CHG\d+` yields `{valid: True, state: "unverified"}`. There is no `servicenow-mcp` registered in `config/openclaw.json`. The gate is format-only and fails open.
2. **The gate logic is duplicated five times with two incompatible contracts** (see Key Entities → *Current-state inventory*), so any change to gating behavior today must be made in five places, and **no test anywhere exercises any of them**.

## Goals / Non-Goals

**Goals**
- An operator can select the ITSM that gates writes (`servicenow`, `halo`, `atlassian`, `none`), and NetClaw's gate messages, ref formats, and skill routing follow that selection.
- One shared, provider-agnostic gate module replaces the duplicated copies, with **no behavior regression** for currently-gated tools.
- The trust boundary is stated honestly: verification of a change record's *state* happens at the skill/agent layer; the server-side gate enforces ref format + provider policy and records the decision.
- The Constitution describes provider-agnostic ITSM gating consistently.

**Non-Goals (this feature)**
- Building a `servicenow-mcp` server, or fixing the fact that ServiceNow is only reachable as an unregistered install-time clone.
- Making the server-side gate call any ITSM API (explicitly rejected — see Assumptions).
- Changing *which* tools are gated, or what counts as a write.
- Multi-provider-simultaneous gating. One active provider per deployment.
- Migrating the nautobot family in v1 (specified as a follow-on phase — see US2 and FR-014).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — An operator gates changes with their own ITSM (Priority: P1)

An operator runs HaloPSA, not ServiceNow. They set the ITSM provider to `halo`. When they attempt a gated write, NetClaw expects a **Halo** change-ticket reference, validates it against Halo's ref format, and every message, prompt, and error names **Halo** — never ServiceNow. The same deployment switched to `servicenow` behaves exactly as NetClaw does today.

**Why this priority**: This is the entire point of the feature. Without it a Halo or Jira shop is told to produce a ServiceNow CR that does not and will never exist in their environment.

**Independent Test**: Configure `NETCLAW_ITSM_PROVIDER=halo`, call a gated tool with a Halo change-ticket id, and confirm it is accepted and that no output string contains "ServiceNow". Repeat with a `CHG0012345` ref and confirm it is rejected with a message naming Halo's expected format.

**Acceptance Scenarios**:

1. **Given** provider `halo`, **When** a gated tool is called with a valid Halo change-ticket reference, **Then** the gate returns `valid: true` with `provider: "halo"` and no ServiceNow terminology.
2. **Given** provider `halo`, **When** a gated tool is called with `CHG0012345`, **Then** the gate returns `valid: false` with a message stating the expected Halo reference format.
3. **Given** provider `servicenow`, **When** a gated tool is called with `CHG0012345`, **Then** behavior is identical to the pre-refactor gate (format accepted; `state` reported honestly).
4. **Given** provider `none` (or `NETCLAW_LAB_MODE=true`), **When** a gated tool is called, **Then** the write proceeds without an external change record and the bypass is GAIT-logged.
5. **Given** an unrecognized provider value, **When** any gated tool is called, **Then** the gate fails with a clear configuration error naming the supported providers, and does **not** silently fall back to ServiceNow.

---

### User Story 2 — One gate implementation instead of five (Priority: P1)

A maintainer changing gating behavior edits **one** module and every gated server picks it up. Today the same logic exists in five places with two different contracts and two different environment-variable schemes, and a sixth ServiceNow-shaped CR regex lives in Memory MCP.

**Why this priority**: Provider selection (US1) is unbuildable on five divergent copies — it would mean five parallel implementations of the same abstraction. Consolidation is the prerequisite, and it must be provably regression-free.

**Independent Test**: With provider `servicenow` (status-quo config), run the characterization test suite captured before the refactor against the refactored gate; every assertion passes unchanged. Confirm `gnmi_set` and the six Claroty write tools behave identically, including the envelope Claroty publishes in its tool output.

**Acceptance Scenarios**:

1. **Given** zero existing test coverage of the gate, **When** the refactor begins, **Then** characterization tests capturing the *current* behavior already exist and pass against the *unrefactored* code.
2. **Given** the shared module, **When** `gnmi-mcp` and `claroty-mcp` are re-pointed at it, **Then** their existing import paths and call sites are unchanged (thin shims re-export), and the characterization suite still passes.
3. **Given** Claroty publishes the gate envelope as `{"itsm_gate": {...}}` in tool output, **When** the envelope gains a `provider` key, **Then** all previously-present keys (`valid`, `message`, `cr_number`, `state`) remain with unchanged meaning.
4. **Given** the two servers use different parameter names (`change_request_number` vs `cr_number`), **When** the shared gate is adopted, **Then** both continue to work without renaming any MCP tool parameter.
5. **Given** the nautobot family's separate `_check_itsm()` contract, **When** v1 ships, **Then** the nautobot servers are untouched and their migration is specified as a distinct later phase with its own compatibility analysis.

---

### User Story 3 — Skill-layer verification is documented and auditable (Priority: P2)

Because NetClaw's MCP servers cannot call other MCP servers, the *state* of a change record ("is this CR approved?") can only be verified by the agent/skill layer, which can reach any ITSM's MCP tools. An operator and an auditor can both see exactly who verified what: the responsible skill per provider is documented, and the skill records its verification result so the gate decision and the GAIT trail show whether the state was actually checked or merely asserted.

**Why this priority**: This makes the safety posture honest. Today the code *implies* it verifies CR state and does not — the worst of both worlds. Documenting the real boundary, plus an attestation the skill can pass, is what turns "advisory" into "advisory and auditable".

**Independent Test**: Run a gated write through the provider's change skill and confirm the GAIT record shows the change reference, the provider, and whether the state was verified (attested) or unverified. Then call the gated tool directly without attestation and confirm the decision is recorded as unverified rather than reported as verified.

**Acceptance Scenarios**:

1. **Given** any provider, **When** the gate returns a decision, **Then** the decision distinguishes "state verified by the skill" from "state not verified" and never reports verification that did not occur.
2. **Given** provider `halo`, **When** the change skill verifies the ticket's status before the write, **Then** the verified state is carried into the gate decision and the GAIT record.
3. **Given** a gated tool called with no attestation, **When** the gate evaluates it, **Then** the write is permitted or denied per the configured policy, and the decision records that the state was unverified.
4. **Given** documentation, **When** an operator asks "who checks that my change is approved?", **Then** the answer is stated explicitly per provider, naming the responsible skill.

---

### User Story 4 — The Constitution describes provider-agnostic gating (Priority: P3)

A contributor reading the Constitution learns that changes require an approved change record in **the configured ITSM**, and cannot come away believing ServiceNow is the only supported system. All five ServiceNow-naming locations are consistent with each other and with the code.

**Why this priority**: Governance should follow the implementation, not block it, so this is sequenced last — but it is **required for completion**, and it is the part that needs maintainer ratification. Amending Principle III alone would leave four contradicting references, so the amendment is all-or-nothing across the five locations.

**Independent Test**: A contributor who has read only the amended Constitution can correctly state (a) that the gating ITSM is configurable, (b) that lab mode remains the sole bypass and is still GAIT-logged, and (c) that no specific vendor is mandated.

**Acceptance Scenarios**:

1. **Given** the Constitution's own amendment process (documented rationale, impact review, semantic version bump), **When** this amendment is made, **Then** that process is followed and recorded exactly as prior amendments were.
2. **Given** the five ServiceNow-naming locations, **When** the amendment lands, **Then** all five are provider-agnostic and mutually consistent.
3. **Given** the amendment generalizes existing principle text rather than removing or redefining a principle, **When** the version is bumped, **Then** it is a MINOR bump (1.2.0 → 1.3.0) with that reasoning stated.
4. **Given** the top-of-file Sync Impact Report, **When** the amendment lands, **Then** the report is rewritten in the established format and prior versions are compressed into "Previous version history".

---

### Edge Cases

- **Provider/ref mismatch**: a `CHG\d+` ref supplied while provider is `halo` — must be rejected with a provider-specific message, never silently accepted.
- **Unknown provider value**: must be a loud configuration error, never a silent fallback to ServiceNow (a silent fallback would recreate the bug).
- **Provider configured but its ITSM is unreachable**: the skill cannot verify state. The gate must report the decision honestly per the configured policy — see Open Question 3 (fail-open today).
- **Missing provider configuration entirely**: needs a documented default — see Open Question 2.
- **`gnmi-mcp` receives no ITSM environment variable** from `config/openclaw.json:81-90` today, so its lab bypass works only by parent-environment leakage. Any new variable must be added to every gated server's env block or the feature silently misconfigures.
- **Claroty's published envelope**: it returns the whole gate dict inside tool output, so envelope keys are a public contract. Additive changes only; renaming `cr_number` is breaking.
- **Parameter-name divergence**: `gnmi_set` uses `change_request_number` (required); Claroty uses `cr_number` (required); nautobot uses `cr_number` (**optional**). A shared gate must not force a rename.
- **Divergent operation-label messages**: the two gate copies emit different user-visible strings (`"…for gNMI Set operations"` vs `"…for Claroty write operations"`). Preserving them byte-for-byte requires the label to come from the **shim**, not from a tool parameter — otherwise the characterization tests of FR-011 would have to be authored already-failing.
- **Provider-adapter fields that cannot be fixed on this branch**: Halo's change-reference format depends on unmerged feature 069, and Jira statuses are configurable per project, so Atlassian's approved-state vocabulary cannot ship as a constant — it must be operator-supplied. Both must be marked provisional rather than invented.
- **Lab mode interaction**: `NETCLAW_LAB_MODE` (gnmi/claroty) and `ITSM_ENABLED`/`ITSM_LAB_MODE` (nautobot) coexist with different defaults. Provider `none` and lab mode overlap and must have defined precedence.
- **Attestation spoofing**: an attested state is only as trustworthy as the caller. With skill-layer verification the server boundary is advisory by construction; this must be documented, not papered over.
- **Memory MCP CR provenance**: `memory_record_decision(cr_number=...)` validates `^CHG\d+$` for audit metadata. A Halo shop's change reference will fail that validation — deferred, but it is a user-visible inconsistency (FR-016).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a single shared, provider-agnostic change-gate module that all gated MCP servers use, replacing per-server copies of the gate logic.
- **FR-002**: The gate MUST resolve an active ITSM provider from configuration, supporting at minimum `servicenow`, `halo`, `atlassian`, and `none`.
- **FR-003**: The gate MUST reject an unrecognized provider value with an explicit configuration error and MUST NOT fall back to any vendor default.
- **FR-004**: Each provider MUST declare, as data: its change-reference format, its human-readable ITSM name, its "approved for implementation" state vocabulary, and the skill responsible for verifying a change record's state.
- **FR-005**: The gate MUST validate a supplied change reference against the **configured provider's** format and, on failure, return a message naming that provider and its expected format.
- **FR-006**: The gate MUST NOT make network calls to any ITSM. State verification is the responsibility of the agent/skill layer (see FR-007).
- **FR-007**: Documentation MUST state, per provider, which skill verifies the change record's state before a gated write, and MUST describe the server-side gate as enforcing format and policy rather than verifying state.
- **FR-008**: The gate decision MUST distinguish a state that was verified by the skill layer from one that was not, and MUST NOT report verification that did not occur.
- **FR-009**: The gate MUST preserve its existing return-envelope keys (`valid`, `message`, `cr_number`, `state`) with unchanged meaning, adding new keys additively, because at least one server publishes the envelope in its tool output.
- **FR-010**: The refactor MUST NOT rename or change the requiredness of any existing MCP tool parameter, including the divergent `change_request_number` and `cr_number` names.
- **FR-011**: Characterization tests capturing the current gate behavior MUST exist and pass against the pre-refactor code before the shared module replaces it, since no test coverage exists today.
- **FR-012**: The gate MUST preserve a lab/no-ITSM path that permits writes without an external change record, and every such bypass MUST be GAIT-logged.
- **FR-013**: Every gate decision MUST be recorded to the GAIT audit trail with the provider, the change reference, the verification status, and the allow/deny outcome. **Note**: this is *net-new* behavior for 6 of the 7 v1-gated tools — `claroty-mcp` emits no GAIT record today (only `gnmi-mcp` does), so this requirement closes an existing Principle IV gap rather than preserving current behavior, and argues for emitting from inside the shared gate rather than per caller.
- **FR-014**: v1 MUST cover the two servers using the `validate_change_request()` contract (7 gated tools) and MUST specify — without implementing — the migration of the three nautobot servers (35 gated tools) that use the separate `_check_itsm()` contract.
- **FR-015**: The provider configuration variable MUST be delivered to every gated server through its `config/openclaw.json` environment block, including servers that currently receive no ITSM variable.
- **FR-016**: The system MUST document, as a known deferred inconsistency, that Memory MCP's change-reference provenance validation remains ServiceNow-shaped and will reject other providers' reference formats.
- **FR-017**: The Constitution MUST be amended, following its own documented amendment process, so that all five of its ServiceNow-naming locations describe a configurable ITSM.

### Key Entities

- **ItsmProvider** — the selected ITSM for change gating. One of `servicenow`, `halo`, `atlassian`, `none`. Resolved from configuration; invalid values are an error.
- **ProviderAdapter** — declarative metadata for one provider: reference format, display name, approved-state vocabulary, responsible verification skill. Contains **no** transport or credential logic.
- **ChangeRef** — the operator-supplied reference to a change record (a ServiceNow `CHG…` number, a Halo change-ticket id, a Jira issue key). Format is provider-specific.
- **GateDecision** — the returned envelope: `valid`, `message`, `cr_number` (retained name), `state`, plus additively `provider` and a verification indicator. Published in at least one server's tool output, so it is a public contract.
- **GateConfig** — resolved policy: active provider, lab/bypass state, and (proposed) strictness.

**Current-state inventory** *(the surface this feature consolidates — canonical counts used across all artifacts)*:

| Implementation | Where | Contract | Env scheme | Gated tools | v1? |
|---|---|---|---|---|---|
| `validate_change_request()` | `mcp-servers/gnmi-mcp/itsm_gate.py`; `mcp-servers/claroty-mcp/utils/itsm_gate.py` | dict envelope | `NETCLAW_LAB_MODE` | **7** (1 gnmi + 6 claroty) | **yes** |
| `_check_itsm()` | `nautobot-mcp-v2/server.py:39`; `nautobot-routing-mcp/server.py:57`; `nautobot-golden-config-mcp/server.py:61` | `Optional[str]`, no format check | `ITSM_ENABLED` + `ITSM_LAB_MODE` | **35** | follow-on |
| `validate_cr_number()` | `memory-mcp/storage/sqlite_store.py:109` | `Tuple[bool, str\|None]` — provenance, not a gate | — | 1 | deferred (FR-016) |
| dead validator | `mcp-servers/gnmi-mcp/models.py:198` (`GnmiSetRequest` unreferenced) | — | — | 0 | remove |

Totals: **5 gate implementations across 5 servers · 42 gated tools · 4 independent `^CHG\d+$` regexes · 0 existing tests.**

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A single gate implementation serves all v1-gated tools; the number of independent change-reference format validators drops from 4 to 1 (excluding the deferred Memory MCP provenance check).
- **SC-002**: With a non-ServiceNow provider configured, no gate output, error message, or prompt for a gated write contains the word "ServiceNow".
- **SC-003**: With the status-quo provider configured, 100% of the characterization assertions captured before the refactor pass after it — including the envelope Claroty publishes.
- **SC-004**: Gate behavior is covered by tests where it previously had none (from 0 tests to a suite covering: each provider's format validation, unknown-provider error, lab/none bypass, and the verified/unverified distinction).
- **SC-005**: A contributor who has read only the amended Constitution can correctly state that the gating ITSM is configurable, that lab mode is the sole bypass and is still GAIT-logged, and that no vendor is mandated.
- **SC-006**: An auditor reading a GAIT record for a gated write can determine the provider, the change reference, and whether the change record's state was actually verified.
- **SC-007**: Zero currently-gated tools change their parameter names or requiredness.

---

## Assumptions

- **Skill-layer verification is the chosen architecture.** NetClaw MCP servers cannot call other MCP servers (no MCP client exists anywhere under `mcp-servers/`; `scripts/mcp-call.py` is used only by skills, bash, and the UI). Server-side HTTP verification was considered and rejected: it would require per-ITSM credentials and HTTP clients inside every gated server, and the gate must be **synchronously** callable (`gnmi_set` is a plain `def`), which rules out reusing the async client patterns the rest of the repo uses.
- **Consequence, stated plainly**: with skill-layer verification the server-side gate is **advisory** — a direct tool call can assert any reference. The real controls are the skill layer and the GAIT audit trail. This is not a regression; today's gate already enforces nothing (`_check_servicenow_cr_state()` returns `None`, so every well-formed reference passes as `unverified`). This feature makes that boundary honest and auditable instead of implied.
- **The shared module follows the one working precedent for cross-server Python**: `src/netclaw_tokens/`, imported via a `sys.path` insert anchored on `__file__`, used by 8 servers. A root-level installable package was considered and rejected for v1 because no root packaging exists and the repo runs mixed interpreters (the nautobot servers use a venv python; others use bare `python3`), so a package installed into one interpreter would be invisible to the other.
- **Thin per-server shims are retained** at the existing gate paths so that existing import sites and call sites do not churn; this is what makes FR-010 and SC-007 achievable.
- **The amendment is a clarifying/generalizing change to existing principle text** — not the removal or redefinition of a principle — and therefore a MINOR bump (1.2.0 → 1.3.0) under the Constitution's own semantic-versioning rule.
- **Feature 069 (Halo MCP) is a dependency, not a given.** It is unmerged (PR #167); `halo-mcp` and the `halo-change-request` skill do not exist on this branch. The `halo` provider adapter's verification-skill reference assumes 069 lands; if it does not, the adapter ships with its verification skill marked unavailable.
- **ServiceNow remains reachable only as an unregistered install-time clone** (`$SERVICENOW_MCP_SCRIPT`, invoked by skills via `$MCP_CALL`). Fixing that is out of scope but affects how the ServiceNow adapter's verification skill is documented (Open Question 8).

---

## Open Questions for Maintainer Review

This specification exists to frame these decisions, not to presume them. Each carries a recommendation.

1. **Config mechanism and precedence** — environment variable only, a `config/openclaw.json` setting, or a Memory MCP fact? *Recommend*: environment variable (`NETCLAW_ITSM_PROVIDER`) for v1, matching the existing `NETCLAW_LAB_MODE` / `ITSM_ENABLED` precedent; a Memory fact is reachable from a server only by reading its SQLite file directly, which is not worth it.
2. **Default provider when unset** — `none` (safe, opt-in) or `servicenow` (preserves the nominal status quo)? *Recommend*: `none` with a startup warning, because the current default enforces nothing anyway and a silent ServiceNow default is what produced this problem.
3. **Fail-open vs fail-closed** — should a configured provider plus an unverified reference ever fail *closed*? Today everything fails open. *Recommend*: keep fail-open in v1 for compatibility, and add an opt-in strict mode (`NETCLAW_ITSM_STRICT`) so operators who want real enforcement can have it.
4. **Attestation** — adopt an `attested_state` the verifying skill passes into the gate, or leave verification purely honor-system? *Recommend*: adopt it; it is what makes US3/SC-006 auditable and is a precondition for any future strict mode.
5. **v1 adapter set** — `servicenow`, `halo`, `atlassian`, `none`. Any others (Freshservice, Jira Service Management as distinct from Jira)?
6. **State vocabulary** — normalize each ITSM's "ready to implement" state to one canonical value, or keep provider-native names in the envelope? *Recommend*: canonical internally, provider-native in messages.
7. **nautobot migration** — fold the three nautobot servers onto the shared gate (a breaking env-var change affecting 35 tools, currently defaulting to gating *off*), or leave them? *Recommend*: migrate in a follow-on phase, defaults preserved.
8. **`servicenow-mcp` registration** — should the community clone finally be registered in `config/openclaw.json`, given that gating documentation depends on it?
9. **Amendment scope confirmation** — all five locations (recommended), and does Principle III's "Assess → Authorize → Implement → Review" lifecycle wording also need generalizing, since that sequence is ServiceNow's?

### Discovered defects (out of scope, reported for triage)

- `config/openclaw.json:291-304` registers `aruba-cx-mcp` with ITSM variables, but `mcp-servers/aruba-cx-mcp/` **does not exist**; its skills and contract spec document it as live.
- `config/openclaw.json:81-90` (`gnmi-mcp`) passes no ITSM environment variable, so its lab bypass depends on environment leakage.
- `mcp-servers/gnmi-mcp/models.py:186-207` (`GnmiSetRequest`) is dead code carrying a second `^CHG\d+$` validator.
