# Requirements & Coherence Checklist — Feature 070

**Status**: Phase 0 (specification) **COMPLETE**. All implementation items are **BLOCKED**
pending maintainer ratification of the Constitution amendment (1.2.0 → 1.3.0) and answers to
the 9 Open Questions in `spec.md`.

Legend: `[x]` done · `[ ]` not started · `[—]` deliberately out of v1 scope

---

## A. Specification artifacts (this round)

- [x] `spec.md` — template-conformant: 4 prioritized user stories with Given/When/Then, edge
      cases, 17 FRs, key entities + current-state inventory, 7 success criteria, assumptions,
      9 open questions, discovered defects
- [x] `plan.md` — technical context, Constitution Check gate (5 rows marked AMENDED),
      project structure, complexity tracking
- [x] `research.md` — R1–R8 with Decision / Rationale / Alternatives, incl. R6 amendment scope
      modeled on spec 049's R6
- [x] `data-model.md` — `ItsmProvider`, `ProviderAdapter`, `ChangeRef`, `GateDecision`,
      `GateConfig`, decision flow
- [x] `contracts/itsm-gate-contract.md` — public API, envelope with back-compat vs additive
      markings, provider table, shim contract, behavior table
- [x] `contracts/constitution-amendment.md` — literal before/after for all 5 locations
      (byte-verified against the live file) + proposed Sync Impact Report
- [x] `quickstart.md` — maintainer review path + operator usage
- [x] `tasks.md` — phased, characterization-tests-first, amendment as exactly 2 tasks,
      nautobot fenced as follow-on
- [x] `checklists/requirements.md` — this file
- [x] `gait-session-log.md` — Principle IV audit trail of decisions and scope corrections

## B. Ratification gate (blocks everything below)

- [ ] Maintainers ratify the Constitution amendment across all 5 locations
- [ ] **OQ2** answered — default provider when unset (`none` vs `servicenow`) — *changes API*
- [ ] **OQ3** answered — fail-open vs opt-in strict mode — *changes API*
- [ ] **OQ4** answered — adopt `attested_state`? — *changes API*
- [ ] OQ1 answered — config mechanism and precedence
- [ ] OQ5 answered — v1 adapter set
- [ ] OQ6 answered — canonical vs provider-native state vocabulary
- [ ] OQ7 answered — nautobot migration disposition
- [ ] OQ8 answered — register `servicenow-mcp` in `config/openclaw.json`?
- [ ] OQ9 answered — generalize Principle III's "Assess → Authorize → Implement → Review"?
      (`contracts/constitution-amendment.md` offers a conservative and a generalized variant —
      pick one)

## C. Safety net before any refactor (FR-011)

- [ ] Characterization tests written for the **current** gate behavior and passing against the
      **unrefactored** code — coverage is **0** today, so this is the only way "no regression"
      is verifiable rather than asserted
- [ ] Characterization coverage includes the envelope Claroty publishes in tool output
- [ ] Characterization coverage pins the two divergent operation-label message strings
      (`"…for gNMI Set operations"` vs `"…for Claroty write operations"`) byte-for-byte

## D. Implementation (v1 — 7 gated tools, 2 servers)

- [ ] `src/netclaw_itsm/` shared module created, mirroring `src/netclaw_tokens/`
- [ ] Provider adapters: `servicenow`, `halo`, `atlassian`, `none` (declarative only — no
      transport, no credentials)
- [ ] Thin shim at `mcp-servers/gnmi-mcp/itsm_gate.py` re-exporting from the shared module
      (`sys.path` depth: `"..","..","src"`)
- [ ] Thin shim at `mcp-servers/claroty-mcp/utils/itsm_gate.py` (`sys.path` depth:
      `"..","..","..","src"`)
- [ ] `gnmi_set` and the 6 Claroty write tools behave identically under the status-quo provider
- [ ] No MCP tool parameter renamed or made newly required (SC-007)
- [ ] Dead `GnmiSetRequest` validator removed (`mcp-servers/gnmi-mcp/models.py:186-207`)
- [ ] GAIT emission for every gate decision (FR-013) — **note: net-new for the 6 Claroty tools**,
      which emit no GAIT record today; only `gnmi-mcp` does

## E. Constitution XI coherence (implementation round)

- [ ] `.specify/memory/constitution.md` — 5 locations amended + Sync Impact Report + version
      bump + `Last Amended` date
- [ ] `config/openclaw.json` — `NETCLAW_ITSM_PROVIDER` added to **every** gated server's env
      block, including `gnmi-mcp` (`:81-90`), which currently receives no ITSM variable
- [ ] `.env.example` — new variable documented; the two existing ServiceNow-framed comments
      (`:119`, `:397-398`) generalized
- [ ] `SOUL.md` — the three ServiceNow-as-required lines (`:351`, `:408`, `:419`) generalized
- [ ] `SOUL-SKILLS.md` — the ~20 "requires ServiceNow CR" skill lines generalized
- [ ] `README.md` — ServiceNow-as-required lines generalized (`:265`, `:811`, `:812`, `:1589`,
      `:2249`, and the per-skill descriptions); integration-listing mentions left as-is
- [ ] `TOOLS.md` — ITSM provider selection documented alongside the ServiceNow credentials line
- [ ] `AGENTS.md` — `:40`, `:64-65` generalized
- [ ] Affected `workspace/skills/**/SKILL.md` — the hard-gated set updated to reference the
      configured ITSM and its verification responsibility (see `spec.md` FR-007)
- [ ] `ui/netclaw-visual/server.js` — ENV_MAP entries for gated servers include the new variable
- [ ] `scripts/verify-catalog-coverage.py` passes with no new gaps
- [ ] Milestone blog drafted (Principle XVII) — *only if* this ships as a merged feature

## F. Follow-on phase (specified, NOT in v1)

- [—] nautobot family migration: 3 servers, **35** gated tools, `_check_itsm() -> Optional[str]`
      → shared gate, incl. reconciling `ITSM_ENABLED`/`ITSM_LAB_MODE` with
      `NETCLAW_ITSM_PROVIDER`/`NETCLAW_LAB_MODE` while preserving today's gating-off default
      and the **optional** `cr_number` parameter
- [—] Memory MCP change-reference provenance (`validate_cr_number`, `^CHG\d+$`) generalized —
      deferred with rationale (FR-016): provenance metadata, not a gate

## G. Discovered defects (reported for maintainer triage, not fixed here)

- [—] `config/openclaw.json:291-304` registers `aruba-cx-mcp` with ITSM variables, but
      `mcp-servers/aruba-cx-mcp/` does not exist; its skills and contract spec document it as live
- [—] `mcp-servers/gnmi-mcp` receives no ITSM env var, so its lab bypass depends on
      parent-environment leakage
- [—] `servicenow-mcp` is an install-time clone of a community repo, invoked by skills via
      `$MCP_CALL`, and is not registered in `config/openclaw.json` (OQ8)

---

## Verification of this round

- [x] Every artifact conforms to its `.specify/templates/` counterpart
- [x] Canonical counts identical across all artifacts: **5 gate implementations · 5 servers ·
      42 gated tools (7 v1 + 35 follow-on) · 4 `^CHG\d+$` regexes · 0 existing tests ·
      5 Constitution locations · 1.2.0 → 1.3.0**
- [x] Constitution current-text quotes byte-verified against `.specify/memory/constitution.md`
- [x] No artifact treats feature 069 (`halo-mcp`, `halo-change-request`) as existing on this
      branch — it is cited as an unmerged dependency (PR #167)
- [x] `git status` shows changes only under `specs/070-itsm-provider-abstraction/`
