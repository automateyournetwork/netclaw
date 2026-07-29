# GAIT Session Log — Feature 070: ITSM Provider Abstraction

**Principle IV — Immutable Audit Trail.** This log records the decisions and findings of the
specification session. Entries are append-only; corrections are recorded as new turns that
reference the original, never by rewriting history.

**Branch**: `070-itsm-provider-abstraction` (from clean `origin/main` @ `12325d0`)
**Date**: 2026-07-24
**Deliverable**: specification artifacts only — **no code**
**Outcome**: 10 SDD artifacts authored; implementation deliberately blocked pending maintainer
ratification of a Constitution amendment.

---

## Turn 0 — Origin of the feature

**Asked** (operator, during feature 069 review): *"Is there any way in the current ITSM gating to
allow for the user to choose which ITSM tool should be used vs NetClaw always talking about
ServiceNow?"*

**Answered** No. Verified by grep: no `ITSM_PROVIDER` / `CHANGE_PROVIDER` / equivalent
configuration knob exists anywhere in the repo. ServiceNow is hardwired at three layers — the
Constitution (Principle III), the code (`itsm_gate.py`), and the skill layer
(`servicenow-change-workflow`).

**Decided** This warrants its own feature rather than being bolted onto 069, because it touches
the Constitution. Operator direction: *"That's going to take some discussion with the netclaw
maintainers, but I think it's good."* → the deliverable is a **proposal**, not an
implementation.

---

## Turn 1 — Four scoping decisions

**Q1 — What does this round deliver?**
> **Decided: specification artifacts only.** Nothing is built on an unratified Constitution
> amendment. The artifacts are a proposal to take to the @automateyournetwork maintainers.

**Q2 — How much of the gate surface does v1 unify?**
> **Decided: phase it.** v1 covers the two servers on the `validate_change_request()` contract
> (`gnmi-mcp`, `claroty-mcp` — 7 gated tools). The nautobot family (3 servers, 35 gated tools,
> a different contract and different env vars) is **specified** as a follow-on phase but not
> implemented. Rationale: with zero existing test coverage, a 42-tool blast radius is
> irresponsible; 7 tools is a complete, verifiable story.

**Q3 — How wide is the Constitution amendment?**
> **Decided: all five ServiceNow-naming locations** — Principle III (`:55-64`), Principle VIII
> (`:114`), Principle XIV (`:200`), Technology Stack (`:260`), Forbidden Operations (`:269`).
> Amending Principle III alone would leave four references contradicting it, which would fail
> the comprehension test that spec 049's own amendment criterion established.

**Q4 — How is a change record's state verified?**
> **Decided: skill-layer verification.** The agent/skill verifies via the ITSM's own MCP tools;
> the server-side shared gate enforces reference format + provider policy + envelope + GAIT and
> makes **no** network calls.
>
> This overruled the initial recommendation of server-side HTTP adapters. The operator's choice
> is the better fit, and the reasons are recorded in `research.md` R2: NetClaw MCP servers
> cannot call other MCP servers (no MCP client exists under `mcp-servers/`), the gate must be
> **synchronously** callable (`gnmi_set` is a plain `def`), and server-side verification would
> require per-ITSM credentials and HTTP clients inside every gated server.
>
> **Consequence accepted and documented rather than hidden:** the server-side gate is
> **advisory** — a direct tool call can assert any reference. This is not a regression;
> `_check_servicenow_cr_state()` already returns `None`, so today every well-formed `CHG\d+`
> passes as `unverified`. The feature makes the boundary honest and adds an optional
> `attested_state` so skill verification becomes auditable.

---

## Turn 2 — Exploration corrected the scope (three material findings)

The initial draft spec was written before codebase exploration and **understated the problem**.
Superseded by these verified findings:

1. **The gate surface is 4× larger than drafted.** Beyond the two `itsm_gate.py` copies there
   are three more copies of a *different* gate — `_check_itsm()` in `nautobot-mcp-v2`,
   `nautobot-routing-mcp`, `nautobot-golden-config-mcp` — with a different return type
   (`Optional[str]`), a different env scheme (`ITSM_ENABLED`/`ITSM_LAB_MODE`), **no** reference
   format validation, and an **optional** `cr_number`. Plus a ServiceNow-shaped provenance
   validator in Memory MCP and a dead validator in `gnmi-mcp/models.py`.
   → Canonical totals: **5 implementations · 5 servers · 42 gated tools · 4 independent
   `^CHG\d+$` regexes.**
2. **Zero test coverage on any gate.** `grep tests/` for itsm / `validate_change_request` /
   `NETCLAW_LAB_MODE` returns nothing. → FR-011: characterization tests must exist and pass
   against the *unrefactored* code before consolidation, or "no regression" is unfalsifiable.
3. **The Constitution names ServiceNow in five places, not one.** → drove the Q3 decision above.

**Also corrected:** the draft implied a server could verify a Halo ticket's status. It cannot
(finding in Q4). The draft did not follow `.specify/templates/spec-template.md` (missing the
mandatory User Scenarios, Given/When/Then, Edge Cases, Key Entities, Assumptions) and was
therefore **rewritten**, not extended.

---

## Turn 3 — Artifacts authored

Ten artifacts under `specs/070-itsm-provider-abstraction/`: `spec.md`, `plan.md`, `research.md`,
`data-model.md`, `contracts/itsm-gate-contract.md`, `contracts/constitution-amendment.md`,
`quickstart.md`, `tasks.md`, `checklists/requirements.md`, and this log.

**Design recorded:**
- Shared module at `src/netclaw_itsm/`, mirroring `src/netclaw_tokens/` — the only working
  cross-server Python precedent (a `sys.path` insert anchored on `__file__`, used by 8 servers).
  A root installable package was rejected for v1: no root packaging exists and the repo runs
  mixed interpreters (nautobot servers use a venv python, others bare `python3`), so a package
  installed into one would be invisible to the other.
- Thin shims retained at both existing gate paths so no import site or call site churns.
- Backwards compatibility as a hard requirement: the envelope keys `valid`/`message`/
  `cr_number`/`state` are a **public contract** because Claroty returns the whole dict in its
  tool output; changes are additive only, and no MCP tool parameter is renamed.
- The amendment is structured on the **spec 049 precedent**: its own P3 user story, a dedicated
  research item justifying the MINOR bump, exactly two tasks, a quickstart step, and a
  comprehension-test success criterion. Constitution current text was **byte-verified** against
  the live file before being quoted.

**Verification performed:** template conformance; canonical counts cross-checked across all
artifacts; Constitution quotes byte-verified; confirmed no artifact treats feature 069
(`halo-mcp`, `halo-change-request`) as existing on this branch — it is cited as an unmerged
dependency (PR #167); `git status` limited to the spec directory.

**Line-number corrections found during verification** (recorded rather than silently fixed):
`nautobot-golden-config-mcp/server.py:60` (not `:61`); Principle III's lifecycle line sits at
constitution `:59-60`; Principle XIV's ServiceNow line is `:200` (an earlier note said `:201`,
which is the GitHub line).

---

## Turn 4 — Findings surfaced during authoring that change requirements

Recorded because they were discovered *after* the spec's first pass and alter its meaning:

1. **`claroty-mcp` emits no GAIT record at all** (`grep -rn gait mcp-servers/claroty-mcp/` is
   empty), whereas `gnmi-mcp` does. Therefore **FR-013 is net-new behavior for 6 of the 7 v1
   tools**, not preservation of existing behavior — which strengthens the case for emitting GAIT
   from inside the shared gate rather than leaving it to each caller.
2. **The two gate copies differ in two user-visible message strings** (`"…for gNMI Set
   operations"` vs `"…for Claroty write operations"`). To preserve them byte-for-byte, the
   shared gate needs an operation label supplied by the **shim**, not by a tool parameter.
   Otherwise the characterization tests would have to be authored already-failing.
3. **The `sys.path` insert depth differs per shim** — `gnmi-mcp` needs two levels
   (`"..","..","src"`), `claroty-mcp/utils/` needs three. A silent-fallback trap if copied.
4. **Two adapter fields cannot be settled from this branch** and are marked open rather than
   invented: Halo's reference format (feature 069 is unmerged) and Atlassian's approved-state
   vocabulary (Jira statuses are per-project configurable, so any shipped constant would be
   wrong — must be operator-supplied).

---

## Open at end of session

Nine questions await maintainer decisions (`spec.md` → *Open Questions for Maintainer Review*).
**Three change the module's public API** and therefore block implementation: OQ2 (default
provider), OQ3 (fail-open vs strict mode), OQ4 (adopt `attested_state`).

Three defects were discovered and reported for triage rather than fixed: the dangling
`aruba-cx-mcp` entry in `config/openclaw.json:291-304` pointing at a server that does not exist;
`gnmi-mcp` receiving no ITSM environment variable; and the dead `GnmiSetRequest` validator.

**End of session log.**
