# Phase 0 Research: ITSM Provider Abstraction for Change Gating

**Feature**: 070-itsm-provider-abstraction
**Date**: 2026-07-24
**Status**: Research for a **DRAFT** spec. R6 (Constitution amendment) is a
precondition for implementation, not a side effect of it.

Every claim below was verified against the tree on this branch. Where a fact
comes from an unmerged branch (feature 069 / PR #167) it is labelled as such.

---

## R1: Current-State Inventory — What Actually Exists to Consolidate

**Finding**: Five change-gate implementations across five servers, **42 gated
tools**, **4 independent `^CHG\d+$` regexes**, and **0 tests** exercising any
gate.

| Implementation | Where | Contract | Env scheme | Gated tools | v1? |
|---|---|---|---|---|---|
| `validate_change_request()` | `mcp-servers/gnmi-mcp/itsm_gate.py:24`; `mcp-servers/claroty-mcp/utils/itsm_gate.py:30` | dict envelope | `NETCLAW_LAB_MODE` | **7** (1 gnmi + 6 claroty) | **yes** |
| `_check_itsm()` | `nautobot-mcp-v2/server.py:39`; `nautobot-routing-mcp/server.py:57`; `nautobot-golden-config-mcp/server.py:60` | `Optional[str]`, no format check | `ITSM_ENABLED` + `ITSM_LAB_MODE` | **35** | follow-on |
| `validate_cr_number()` | `memory-mcp/storage/sqlite_store.py:109` | `Tuple[bool, str\|None]` — provenance, not a gate | — | 1 | deferred (FR-016) |
| dead validator | `mcp-servers/gnmi-mcp/models.py:198` (`GnmiSetRequest`, unreferenced) | — | — | 0 | remove |

Supporting measurements taken directly from the tree:

- **The two v1 copies are effectively byte-identical.** `diff -u` between them
  yields only: the module docstring, the logger name (`gnmi-mcp.itsm` vs
  `claroty-mcp.itsm`), one whitespace-only comment difference, and **two**
  message strings — `"Change request number is required for {gNMI Set|Claroty
  write} operations"` and `"{gNMI Set|Claroty write} operations require the CR
  to be in 'Implement' state."` Nothing else differs. Consolidation of these
  two is mechanical, which is exactly why they are v1.
- **The nautobot copies are a different function, not a divergent copy.**
  `_check_itsm(cr_number: Optional[str]) -> Optional[str]` performs **no format
  validation at all** — it only refuses a *missing* `cr_number`, and only when
  `ITSM_ENABLED and not ITSM_LAB_MODE`. Both defaults ship gating **off**
  (`ITSM_ENABLED` default `false`, `ITSM_LAB_MODE` default `true`), verified at
  `nautobot-mcp-v2/server.py:35-36` and the identical pair in the other two.
  Call-site count: 22 + 8 + 5 = **35**, matching the canonical total.
- **GAIT coverage of gate decisions is already uneven.** `gnmi-mcp` records the
  decision (`_gait_log()` at `gnmi_mcp_server.py:97-110`, called on rejection at
  `gnmi_mcp_server.py:219-231`). `claroty-mcp` emits **no GAIT record anywhere** —
  `grep -rn gait mcp-servers/claroty-mcp/` returns nothing. FR-013 is therefore
  a *net-new* requirement for 6 of the 7 v1 tools, not preservation of existing
  behavior.
- **The only change-reference validator in the repo that has tests is the one
  being deferred.** `tests/unit/test_sqlite_store.py:98-107` covers memory-mcp's
  `validate_cr_number()`. No test anywhere imports `validate_change_request` or
  `_check_itsm`.

**Decision**: v1 consolidates only the two `validate_change_request()` copies
(7 gated tools) behind one shared module; the three nautobot servers are left
untouched and specified as a follow-on phase; the dead `GnmiSetRequest`
validator is deleted outright.

**Rationale**: The v1 pair shares one contract, one env var, and (per the diff)
one implementation, so the refactor is provably behavior-preserving. The
nautobot family shares neither contract, env scheme, requiredness (`cr_number`
is `Optional` there), nor default posture — folding it in would turn a
regression-free refactor into a semantic change across 35 tools whose gating is
currently *off by default*. Splitting the phases keeps the blast radius of v1
at 7 tools.

**Alternatives considered**:
- *All five in one pass* — rejected. It combines a mechanical dedup (7 tools)
  with a behavior migration (35 tools, breaking env-var change, defaults flip),
  making SC-003 ("100% of characterization assertions pass") impossible to
  interpret: any failure could be either a bug or the intended migration.
- *Leave the duplication and add provider support to both copies* — rejected.
  That is two parallel implementations of the same abstraction, which is the
  problem US2 exists to remove, and it leaves SC-001 (4 validators → 1) unmet.
- *Keep the dead `GnmiSetRequest` validator "in case it gets wired up"* —
  rejected. It is a fourth `^CHG\d+$` regex that no code path reaches, so it can
  only ever drift from the real gate; leaving it defeats SC-001's count.

---

## R2: Why the Servers Cannot Verify ITSM State — Skill-Layer Verification

**Finding**: A NetClaw MCP server has no route to another MCP server, and the
gate's call sites forbid a coroutine.

1. **No MCP client exists under `mcp-servers/`.** A grep for `ClientSession`,
   `mcp.client`, and `stdio_client` across every `.py` under `mcp-servers/`
   returns exactly one hit, and it is a false positive: the string
   `"claroty-mcp.client"` in a `logging.getLogger()` call at
   `mcp-servers/claroty-mcp/clients/claroty_client.py:29`. There is no MCP
   client library usage anywhere in any server.
2. **`scripts/mcp-call.py` is the only MCP client in the repo, and it is a
   skill-side tool.** Its callers are skills (`$MCP_CALL` in
   `workspace/skills/servicenow-change-workflow/SKILL.md:21,58,71,…`), bash, and
   the UI — never a server.
3. **The gate must be synchronously callable.** `gnmi_set` is a plain `def`
   (`mcp-servers/gnmi-mcp/gnmi_mcp_server.py:196`) and calls the gate inline at
   `:219`. Claroty's six write tools are `async def` but likewise call the gate
   **synchronously** (e.g. `tools/alerts.py:180`, `tools/devices.py:226,282`,
   `tools/user_actions.py:47,109`, `tools/vulnerabilities.py:209`) — no `await`.
   A shared gate that needed to await anything would break `gnmi_set`, and
   `asyncio.run()` inside claroty's already-running loop would raise.
4. **The gate already performs no I/O.** `_check_servicenow_cr_state()`
   (`itsm_gate.py:126-138`) is documented as the integration point and
   unconditionally `return None` at `:138`, so every well-formed reference lands
   in the `valid: True, state: "unverified"` branch.

**Decision**: The shared gate makes **no network calls of any kind** (FR-006).
It enforces reference format + provider policy, returns the envelope, and
records the decision. Verification of a change record's *state* is the
responsibility of the agent/skill layer, and each provider adapter names the
skill that owns it (FR-004, FR-007).

**Rationale**: This is the only architecture the call sites permit, and — given
point 4 — it is not a capability regression. It is a correction of a false
implication: the code currently *reads* as though it verifies ServiceNow state
(docstring: "Be in 'Implement' state in ServiceNow") while verifying nothing.
Moving the claim to where the capability actually lives makes the posture
honest and auditable rather than implied.

**Alternatives considered**:
- *Server-side HTTP verification per ITSM* — rejected on four concrete counts:
  (a) it needs ITSM credentials in the env block of **every** gated server, so a
  Halo token would sit in `gnmi-mcp`'s environment purely to check a ticket;
  (b) it needs an HTTP client and an auth flow per provider (ServiceNow basic/
  OAuth, Halo OAuth client-credentials, Jira token) inside a function that must
  stay synchronous, ruling out reuse of the repo's `httpx.AsyncClient` patterns;
  (c) it converts a gate bug from "advisory decision is wrong" into "every write
  tool is down when the ITSM is slow or unreachable"; (d) it duplicates logic
  that `atlassian-mcp` and (per PR #167) `halo-mcp` already implement correctly.
- *Read Memory MCP's SQLite file directly* — rejected. `memory-mcp` is
  stdio-only, so a server could only reach it by opening
  `~/.openclaw/memory/memory.db` behind its owner's back; that couples two
  servers' storage, adds a file read to every gated write, and the database
  holds change-reference *provenance*, not live ITSM state, so it could not
  answer the question anyway.
- *Have the gate subprocess out to `scripts/mcp-call.py`* — rejected. It pays a
  full stdio server startup per gated write, still requires the ITSM
  credentials in the gated server's environment, and gives the gate a way to
  hang — strictly worse than an advisory decision made in microseconds.

---

## R3: Where the Shared Module Lives

**Decision**: `src/netclaw_itsm/`, imported by each gated server through a
`sys.path.insert` anchored on `__file__`, mirroring `src/netclaw_tokens/`.

**Rationale**: `src/netclaw_tokens/` is the **only** working cross-server Python
sharing precedent in the repo. It contains `__init__.py`, `counter.py`,
`cost_calculator.py`, `footer.py`, `gcf_serializer.py`, `gcf_wrapper.py`,
`session_ledger.py`, `requirements.txt`, and is consumed by **8 servers**
(`azure-network-mcp`, `batfish-mcp`, `claroty-mcp`, `eve-ng-mcp-server`,
`gnmi-mcp`, `n2n-mcp`, `protocol-mcp`, `suzieq-mcp`). The canonical consumer
shim is 9 lines — `mcp-servers/claroty-mcp/utils/gcf_helper.py:8` does the path
insert, imports, and falls back on exception. Reusing that shape means the new
module needs no packaging work, no interpreter assumptions, and no new
convention for a reviewer to learn.

**Implementation trap to record**: the insert depth is per-file, not per-server.
`gnmi-mcp/gnmi_mcp_server.py:31` uses `"..", "..", "src"` (module at server
root); `claroty-mcp/utils/gcf_helper.py:8` uses `"..", "..", "..", "src"`
(module one directory deeper). The gnmi shim lives at
`mcp-servers/gnmi-mcp/itsm_gate.py` and the claroty shim at
`mcp-servers/claroty-mcp/utils/itsm_gate.py`, so the two shims need **different**
depths. Getting this wrong fails silently into the fallback path.

**Alternatives considered**:
- *A root-level installable package* (`pyproject.toml` + `pip install -e .`) —
  rejected for v1 on two verified grounds. First, no root packaging exists to
  extend. Second, the repo runs **mixed interpreters**: `gnmi-mcp` and
  `claroty-mcp` are launched with bare `python3` and *relative* script paths
  (`config/openclaw.json:76-79`, `:546-550`), while all three nautobot servers
  are launched with `/home/ubuntu/netclaw/.venv/bin/python3` and *absolute*
  script paths (`config/openclaw.json:308+`). A package installed into one
  interpreter is invisible to the other, so the follow-on nautobot phase would
  hit an import error that v1 could not have caught. Spec 035's research made
  the same call for GCF ("we **do not** refactor GCF into a proper Python
  package import in this PR"), and this feature is not the place to reverse it.
- *`mcp-servers/_shared/`* — rejected. It invents a second sharing convention
  with zero precedent, and `src/` is already the answer to "where does
  cross-server Python live". Two conventions is worse than one imperfect one.
- *Vendoring a third copy into a `common/` dir per server* — rejected outright;
  that is the status quo with extra steps.

---

## R4: Backwards-Compatibility Constraints

**Finding**: Three hard constraints, all verified in code.

1. **The envelope is published in tool output.** `claroty-mcp` returns the whole
   gate dict to the model: `{"itsm_gate": gate, "applied": False}` on rejection
   (`tools/alerts.py:182`), `{"itsm_gate": gate, "applied": True, "response":
   raw}` on success (`:219`), and again in the error path (`:223`) — and the
   tool docstring advertises that shape at `:178`. So `valid`, `message`,
   `cr_number`, and `state` are a **public contract**, not internals.
2. **Parameter names diverge and cannot be reconciled.** `gnmi_set` takes
   `change_request_number` (required, `gnmi_mcp_server.py:196+`); claroty's six
   tools take `cr_number` (required); nautobot's 35 take `cr_number`
   (**`Optional`**). FR-010/SC-007 forbid touching any of them.
3. **Two message strings are server-specific.** Per R1's diff, the
   missing-reference message and the not-approved message each name the calling
   subsystem ("gNMI Set operations" / "Claroty write operations").

**Decision**: Retain thin shims at the existing paths —
`mcp-servers/gnmi-mcp/itsm_gate.py` and
`mcp-servers/claroty-mcp/utils/itsm_gate.py` — each re-exporting
`validate_change_request` from `src/netclaw_itsm/`. All 7 call sites and both
import statements (`from itsm_gate import validate_change_request`,
`from utils.itsm_gate import validate_change_request`) stay exactly as they are.
The two divergent strings are preserved by having each **shim** supply an
operation label to the shared function; the label is never a tool parameter.
Envelope changes are strictly additive: `provider` and a verification indicator
are added, no existing key is renamed, removed, or retyped.

**Rationale**: The shim is what makes FR-010 and SC-007 achievable without
touching a single tool signature, and it keeps the diff of v1 confined to
`src/netclaw_itsm/` plus two small files. Passing the operation label from the
shim rather than the caller means the label cannot be forgotten at a call site
and cannot leak into an MCP tool schema.

**Alternatives considered**:
- *Re-point the 7 call sites directly at the shared module* — rejected for v1.
  It churns 5 files across 2 servers for zero behavioral gain and widens the
  surface that SC-003 must prove unchanged. The shims can be removed later as
  pure cleanup once the suite exists.
- *Normalize the two divergent messages to one generic string* — rejected. It
  is a user-visible message change that would force the characterization tests
  (FR-011) to be authored already-failing, destroying their value as a
  regression net. Provider-neutral wording is fine; *subsystem*-neutral wording
  is a behavior change.
- *Rename `cr_number` to `change_ref` in the envelope* — rejected. Claroty
  publishes it; renaming is breaking (FR-009 states this explicitly). The name
  is now slightly wrong for a Halo or Jira reference; that is a cheaper cost
  than a broken contract, and the `provider` key supplies the missing context.

---

## R5: Provider Selection and Configuration Mechanism

**Finding**: Existing gating configuration is 100% environment variables, and
the delivery of those variables is already broken for one v1 server.

- `NETCLAW_LAB_MODE` — read by both v1 gates (`itsm_gate.py:57` / `:63`),
  truthy set `("true", "1", "yes")`, case-insensitive, default `false`.
  Delivered to `claroty-mcp` at `config/openclaw.json:557`
  (`"NETCLAW_LAB_MODE": "${NETCLAW_LAB_MODE:-false}"`) and documented at
  `.env.example:119`.
- `ITSM_ENABLED` / `ITSM_LAB_MODE` — nautobot family only, delivered in all
  three env blocks, documented at `.env.example:397-398`.
- **`gnmi-mcp` receives no ITSM variable at all.** Its env block
  (`config/openclaw.json:81-90`) contains eight `GNMI_*` variables and nothing
  else, so its lab-mode bypass works **only** if `NETCLAW_LAB_MODE` happens to
  be exported in the parent process that launches OpenClaw.

**Decision**: Provider selection is a single environment variable,
`NETCLAW_ITSM_PROVIDER`, resolved once at module import, case-insensitive and
trimmed, with an unrecognized value raising a loud configuration error and no
vendor fallback (FR-003). It MUST be added to the `env` block of **every** gated
server in `config/openclaw.json` (FR-015) — and `gnmi-mcp`'s block must gain
both `NETCLAW_ITSM_PROVIDER` **and** `NETCLAW_LAB_MODE`, otherwise provider
selection silently no-ops there exactly the way lab mode does today.
Recommended default when unset: `none` with a startup warning (spec Open
Question 2).

**Rationale**: Env vars are how every server in this repo receives every piece
of configuration, the two existing gate schemes are both env vars, and an env
var is the only mechanism that is unambiguous at gate-evaluation time (no file
resolution, no I/O, no failure mode). Defaulting to `none` rather than
`servicenow` is deliberate: the current default enforces nothing anyway (R2
point 4), and a silent ServiceNow default is precisely the mechanism that
produced this bug.

**Alternatives considered**:
- *A setting in `config/openclaw.json`* — rejected for v1. Servers do not
  receive this file; they receive its `env` block. The only runtime readers of
  an `openclaw.json` under `mcp-servers/` are `protocol-mcp`'s federation
  modules, and they demonstrate the problem rather than a precedent: across
  `federation/controls.py:45`, `inventory.py:58`, `inventory.py:253`,
  `invocation.py:46-57`, and `posture.py:135` they probe **three different
  paths** (`<repo>/config/openclaw.json`,
  `~/.openclaw/config/openclaw.json`, `~/.openclaw/openclaw.json`). A gate
  would have to pick a winner among those on every write. Env vars have no such
  ambiguity.
- *A Memory MCP fact* — rejected. `memory-mcp` is stdio-only; a server could
  only read `~/.openclaw/memory/memory.db` directly (see R2). Operator
  ergonomics do not justify a cross-server storage dependency on the write path.
- *Per-server variables (`GNMI_ITSM_PROVIDER`, `CLAROTY_ITSM_PROVIDER`)* —
  rejected. The spec's Non-Goals fix one active provider per deployment, so
  per-server names would only create drift; spec 035's research made the same
  call when it declined to add a `CLAROTY_LAB_MODE`.
- *Reusing `ITSM_ENABLED` as the on/off switch* — rejected for v1. It belongs
  to the nautobot contract, its default (`false`) means "gating off", and
  overloading it would couple the two phases the whole plan separates.

---

## R6: Constitution Amendment Scope

**Decision**: Amend all **five** ServiceNow-naming locations in
`.specify/memory/constitution.md` in a single, all-or-nothing amendment, and
bump the version **1.2.0 → 1.3.0 (MINOR)**:

| # | Location | Current text (verified) | Amendment |
|---|---|---|---|
| 1 | Principle III "ITSM-Gated Changes", `:55-64` (specifically `:57`) | "All production changes MUST have an approved **ServiceNow** Change Request (CR) before execution." | "…an approved change record in **the configured ITSM** before execution", with the configurable-provider set named once. |
| 2 | Principle VIII "Verify After Every Change", `:114` | "…mark the **ServiceNow** CR as failed." | "…mark the change record as failed in the configured ITSM." |
| 3 | Principle XIV "Human-in-the-Loop…", `:200` | "Creating, updating, or closing **ServiceNow** tickets" | "Creating, updating, or closing tickets in the configured ITSM" |
| 4 | Technology Stack, `:260` | "**ITSM**: ServiceNow (change management, incidents, CMDB)" | "**ITSM**: operator-selected — ServiceNow, HaloPSA/HaloITSM, Atlassian/Jira, or none (change management, incidents, CMDB)" |
| 5 | Forbidden Operations, `:269` | "Bypassing **ServiceNow** CR approval for production changes" | "Bypassing change-record approval in the configured ITSM for production changes" |

Lab mode must remain, verbatim in substance, the **sole** exception and must
remain GAIT-logged (`:61-62`); the amendment generalizes the vendor, never the
control.

**Rationale for MINOR**: This clarifies and generalizes existing principle text.
No principle is removed, no principle is redefined, and no requirement is
relaxed — gating stays mandatory and lab mode stays the only bypass; only the
*vendor* becomes configurable. That is precisely the class of change the
Constitution's own Governance versioning rule reserves for MINOR, and it is the
same class as the 1.1.0 → 1.2.0 bump, whose Sync Impact Report describes
updating "which concrete files satisfy the principle, not a redefinition of what
artifact coherence means."

**Rationale for all-or-nothing**: Amending Principle III alone would leave four
locations still naming ServiceNow, i.e. the exact internal contradiction this
feature exists to remove, and would fail SC-005 (a contributor reading only the
Constitution must be able to state that the ITSM is configurable).

**Sync Impact Report commitment**: The amendment MUST reproduce the established
format — the HTML comment block at `.specify/memory/constitution.md:1-30` — with
the same section order and headings:

```
  Sync Impact Report
  ==================
  Version change: 1.2.0 → 1.3.0 (MINOR — principle clarification)

  Modified principles: <III, VIII, XIV + Technology Stack + Forbidden Operations>
  Added sections: …
  Removed sections: …
  Templates requiring updates:
    - .specify/templates/plan-template.md — ✅ Compatible / <change>
    - .specify/templates/spec-template.md — …
    - .specify/templates/tasks-template.md — …
  Follow-up TODOs: …
  Previous version history:
    - 1.0.0 (2026-03-26): Initial ratification with 16 core principles
    - 1.1.0 (2026-03-28): Added Principle XVII (Milestone Documentation via WordPress)
    - 1.2.0 (2026-07-08): Principle XI — modular installer catalog (spec 049)
```

Prior versions compress into "Previous version history" (1.2.0's own entry gets
added there), and the footer at `:355` — `**Version**: 1.2.0 | **Ratified**:
2026-03-26 | **Last Amended**: 2026-07-08` — is updated to `1.3.0` with the new
amendment date, leaving the ratification date untouched.

**Open item surfaced for the maintainer (spec Open Question 9)**: two fragments
encode ServiceNow's *state machine*, not just its name — Principle III's
lifecycle "(Assess → Authorize → Implement → Review)" at `:59-60`, and
Principle VIII's pairing with the `"Implement"` state that the code checks
literally (`itsm_gate.py:95`, `cr_state.lower() == "implement"`). Recommend
generalizing the lifecycle to provider-neutral phases and letting each
provider's native state vocabulary live in its adapter (FR-004), so the
Constitution stops hard-coding one vendor's workflow. Flagged rather than
assumed, because it widens the amendment beyond a name substitution.

**Alternatives considered**:
- *MAJOR bump (2.0.0)* — rejected. Nothing is removed or redefined; gating
  remains mandatory and lab mode remains the only exception. Reserving MAJOR for
  actual redefinition is what keeps the version signal meaningful.
- *PATCH bump* — rejected. This is not wording/typo cleanup: after the
  amendment, a deployment gated by Halo is *compliant* where before it was not,
  which is a change in normative meaning.
- *Amend Principle III only, leave the rest as "obviously implied"* — rejected;
  see all-or-nothing above.
- *Implement first, amend later* — rejected. Principle III as written makes a
  Halo-gated deployment non-compliant, so shipping the code first would put the
  implementation in violation of the governing document. Hence the spec's DRAFT
  status and the ratification precondition.

---

## R7: Zero Test Coverage — Characterization Tests First

**Finding**: No test in the repo exercises any gate. The change-reference tests
that exist (`tests/unit/test_sqlite_store.py:98-107`) cover memory-mcp's
**deferred** provenance validator — the one implementation this feature does not
touch. Test layout available to copy: `tests/unit/`, `tests/contract/`,
`tests/integration/`, plain pytest classes, stdlib-only assertions.

**Decision**: Author the characterization suite **against the unrefactored
gate** and land it before `src/netclaw_itsm/` exists (FR-011), in `tests/unit/`
alongside the existing unit tests. Behaviors to pin, taken from reading the
current code rather than from intent:

| # | Input / state | Expected today |
|---|---|---|
| 1 | `""` / `None` reference | `valid: False`, `state: None`, message names the calling subsystem ("gNMI Set operations" / "Claroty write operations") |
| 2 | `"INC0012345"`, `"chg123"`, `"CHG"`, `"CHG12 "` | `valid: False`, `state: None`, message `Invalid CR format: '<x>'. Expected format: CHG followed by digits (e.g. CHG0012345)` |
| 3 | `NETCLAW_LAB_MODE` ∈ {`true`,`1`,`yes`} any case | `valid: True`, `state: "lab_mode"`, message ends `(lab mode — ServiceNow check skipped)` |
| 4 | `NETCLAW_LAB_MODE` unset / `"false"` / `"0"` / garbage | lab bypass **not** taken |
| 5 | valid ref, default path | `valid: True`, `state: "unverified"`, "ServiceNow verification unavailable" message (the `_check_servicenow_cr_state() -> None` branch) |
| 6 | `_check_servicenow_cr_state` patched to raise | `valid: True`, `state: "error"` |
| 7 | patched to `"Implement"` / `"implement"` | `valid: True`, `state` echoes the native string |
| 8 | patched to `"New"` | `valid: False`, message `…is in 'New' state, not 'Implement'…` + subsystem clause |
| 9 | every return path | envelope has **exactly** the keys `{valid, message, cr_number, state}`, and `cr_number` echoes the raw input verbatim (including for `""`) |
| 10 | claroty rejection wrapper | output JSON is `{"itsm_gate": <envelope>, "applied": false}` |

**Rationale**: With zero coverage there is no way to distinguish an intended
change from a regression, and SC-003 ("100% of the characterization assertions
captured before the refactor pass after it") is literally unverifiable without
this step. Rows 7 and 8 matter even though they are unreachable in production —
they are the behavior the provider abstraction must reproduce once attestation
(R8) makes them reachable again. Rows 1 and 8 are what prove the shim-supplied
operation label (R4) preserves the divergent strings.

**Alternatives considered**:
- *Refactor first, add tests after* — rejected; that is the failure mode this
  item exists to prevent, and it makes SC-003 meaningless.
- *Live/manual verification only*, as used for feature-specific MCP work
  elsewhere in the repo — rejected. There is no external system to verify
  against (the gate makes no calls), and lab mode makes manual verification
  tautological: everything well-formed passes.
- *Golden-file snapshots of the envelope* — rejected as the primary form.
  Explicit per-branch assertions document *why* each value is what it is; a
  snapshot would freeze the message strings without recording that two of them
  are deliberately subsystem-specific.

---

## R8: The Trust Boundary, Stated Honestly, and Attestation

**Finding**: The current gate does not merely fail open — it *reads* as if it
verifies. `itsm_gate.py:1-9` states the CR must "Be in 'Implement' state in
ServiceNow"; `:67-78` documents a four-step verification flow; `:126-138`
declares the integration point and then `return None`. Consequently every
well-formed `CHG\d+` reference produces `{valid: True, state: "unverified"}`,
and no `servicenow-mcp` is registered in `config/openclaw.json` for it to have
called (verified: zero keys matching `servicenow`).

**Decision**: State the boundary plainly and make it auditable rather than
pretend to close it.

1. The server-side gate is **advisory**: with skill-layer verification (R2), a
   direct MCP tool call can assert any well-formed reference. Documentation MUST
   say so (FR-007), per provider, naming the responsible skill.
2. Add an `attested_state` that the verifying skill passes into the gate, plus a
   verification indicator in the envelope — both **additive** (FR-008, FR-009).
   The gate classifies: attested and in the adapter's approved-state vocabulary
   → verified; absent → `unverified`; attested but **not** approved → deny,
   mirroring the pre-existing (currently unreachable) not-approved branch at
   `itsm_gate.py:102-111`.
3. Every decision emits one GAIT record carrying provider, reference,
   verification status, and allow/deny outcome (FR-013). Emitting it from the
   shared gate is the cheapest way to get all 7 tools uniform, and it closes the
   gap R1 found: claroty currently GAIT-logs nothing.

**Why attestation is a precondition for strict mode**: without it, a strict mode
could only fail closed on *reference format*, which adds no safety — a
well-formed but entirely fictional reference still passes. With attestation,
`NETCLAW_ITSM_STRICT` has a meaning worth having ("deny unless a skill attested
an approved state"), and it can be introduced opt-in without breaking any
currently-working call (spec Open Question 3).

**Rationale**: An attested state is a *claim by the caller*, not a proof. That
is a real limitation and must be documented, not papered over. What it buys is
the difference between unknowable and recorded: the GAIT trail moves from "a
reference was supplied" to "a reference was supplied, and here is whether
anything checked it" — which is exactly what SC-006 asks an auditor to be able
to determine.

**Alternatives considered**:
- *Cryptographic attestation / signed change tokens* — rejected. No ITSM in
  scope issues an offline-verifiable claim about a change record's state, and
  inventing a signing authority for CRs is a far larger feature than this one.
- *Honor system with no attestation field* — rejected. It leaves US3 and SC-006
  unmet and keeps the gate's audit record indistinguishable between "verified"
  and "nobody looked".
- *Fail closed by default whenever a state is unverified* — rejected for v1. It
  would deny **every** currently-working gated call (all of which are
  `unverified`), the precise regression FR-010/SC-003 forbid. Offered instead as
  opt-in strict mode.
- *Trust the skill layer implicitly and drop the server gate entirely* —
  rejected. The format check and the GAIT record are cheap, are the only
  server-side evidence that a change reference was ever demanded, and removing
  the gate would mean removing Principle III's only mechanical enforcement point.

---

## What this feature does NOT change

- The `_check_itsm()` contract or any of the 35 nautobot gated tools (follow-on
  phase; env-var defaults preserved when it happens).
- `memory-mcp`'s `validate_cr_number()` — stays `^CHG\d+$`, so
  `memory_record_decision(cr_number=…)` will still reject a Halo or Jira
  reference. Documented as a known deferred inconsistency (FR-016).
- Which tools are gated, or what counts as a write.
- Any MCP tool parameter name, type, or requiredness.
- `src/netclaw_tokens/` (the module it is modelled on is not touched).
- The absent `servicenow-mcp` registration, or the fact that ServiceNow is
  reachable only as an unregistered install-time clone via
  `$SERVICENOW_MCP_SCRIPT` (spec Open Question 8).
- The discovered defect that `config/openclaw.json` registers `aruba-cx-mcp`
  with ITSM variables for a server directory that does not exist — reported for
  triage, out of scope.
