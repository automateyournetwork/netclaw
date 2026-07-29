# Phase 1 Data Model: ITSM Provider Abstraction for Change Gating

**Feature**: 070-itsm-provider-abstraction
**Date**: 2026-07-24

No persistent store, no schema migration, no new database. Every entity here is
in-process and resolved per gated call inside the new shared module
`src/netclaw_itsm/` (home rationale: research R3), reached from two thin
re-export shims at the existing gate paths:

- `mcp-servers/gnmi-mcp/itsm_gate.py` — shim for `gnmi_set`
- `mcp-servers/claroty-mcp/utils/itsm_gate.py` — shim for Claroty's six writes

Two of the five entities cross a **public** boundary and are therefore
compatibility-constrained: `GateDecision` (published verbatim in Claroty tool
output at `mcp-servers/claroty-mcp/tools/alerts.py:178,182,219,223`) and
`ChangeRef` (its parameter name is part of each MCP tool's schema).

---

## Entity: `ItsmProvider` (enum)

The selected ITSM for change gating. Exactly one is active per deployment
(spec Non-Goals: no multi-provider-simultaneous gating).

| Value | Meaning | v1 status |
|---|---|---|
| `servicenow` | ServiceNow change management. Reproduces today's behavior exactly. | supported |
| `halo` | HaloPSA / HaloITSM change tickets. | supported; verification skill depends on unmerged PR #167 |
| `atlassian` | Atlassian Jira issues used as change records. | supported |
| `none` | No external ITSM. Writes proceed ungated, every call GAIT-logged as a bypass. | supported |

**Validation rules**

- Resolved from `NETCLAW_ITSM_PROVIDER` (research R5), **trimmed** and
  **lower-cased** before comparison.
- An unrecognized non-empty value is a **loud configuration error** — the gate
  MUST fail with a message naming the four supported values and MUST NOT fall
  back to any vendor (FR-003). A silent fallback to `servicenow` would recreate
  the original defect.
- Unset → the documented default. **Recommended**: `none` plus a startup warning
  (spec Open Question 2 — maintainer decision, not settled here).
- The set is closed: it is a frozen table in code, so no adapter can be
  constructed at runtime for a value not listed above.

---

## Entity: `ProviderAdapter`

Declarative metadata for one provider. **Pure data plus a compiled regex.**

| Field | Type | Notes |
|---|---|---|
| `provider` | `ItsmProvider` | Primary key of the adapter table. |
| `display_name` | `str` | Human-readable ITSM name used in every message (FR-005). Never a hard-coded vendor string elsewhere. |
| `ref_pattern` | `re.Pattern \| None` | Compiled at import. `None` only for `none`, which accepts any/no reference. |
| `ref_example` | `str \| None` | Concrete example embedded in the rejection message. |
| `ref_description` | `str \| None` | Human phrasing of the expected format ("CHG followed by digits"), so messages read naturally instead of printing a regex. |
| `approved_states` | `frozenset[str]` | Provider-native state strings that mean "approved for implementation". Compared case-insensitively, matching today's `cr_state.lower() == "implement"` (`mcp-servers/gnmi-mcp/itsm_gate.py:95`). |
| `canonical_approved_state` | `str` | Internal normalization (`approved_for_implementation`). Envelope/messages carry the **native** name (spec Open Question 6 recommendation: canonical internally, provider-native in messages). |
| `verification_skill` | `str \| None` | Name of the skill responsible for verifying a change record's state before a gated write (FR-004, FR-007). |
| `verification_available` | `bool` | `False` when the named skill or its dependency is not present in the deployment; drives documentation and the startup warning, never a silent pass. |

**Invariants**

- **No transport, no credentials, no HTTP client, no network call, no ITSM SDK
  import.** An adapter cannot perform I/O; this is the mechanical guarantee
  behind FR-006 (research R2).
- The only environment variable the module reads is the gate configuration
  itself (`GateConfig`); adapters read none.
- Adapters are immutable after import and are not operator-editable data files
  in v1 (a plugin/registry mechanism is out of scope).
- Every message rendered from an adapter MUST derive its ITSM name from
  `display_name`, which is what makes SC-002 ("no gate output contains
  'ServiceNow' under a non-ServiceNow provider") checkable by grep.

### Per-provider adapter table

| Provider | `display_name` | Reference format (`ref_pattern`) | Example | `approved_states` | `verification_skill` |
|---|---|---|---|---|---|
| `servicenow` | ServiceNow | `^CHG\d+$` — verified as today's behavior at `mcp-servers/gnmi-mcp/itsm_gate.py:21` and `mcp-servers/claroty-mcp/utils/itsm_gate.py:27` | `CHG0012345` | `{"Implement"}` (case-insensitive) | `servicenow-change-workflow` — exists at `workspace/skills/servicenow-change-workflow/`, but reaches ServiceNow only via `$SERVICENOW_MCP_SCRIPT`, an unregistered install-time clone (spec Open Question 8), so `verification_available` is deployment-dependent |
| `halo` | HaloPSA / HaloITSM | **Proposed, must be confirmed against feature 069 when it merges** — Halo change tickets are addressed by ticket id, so a numeric-id pattern (optionally accepting an operator-visible prefix). Recorded as *open* deliberately: FR-004 exists so this is data, not code | pending 069 | pending 069 (Halo change-ticket status vocabulary) | `halo-change-request` — **does NOT exist on this branch**; it and `halo-mcp` arrive with PR #167. Ships with `verification_available = False` if 069 does not land (spec Assumptions) |
| `atlassian` | Atlassian Jira | Jira issue key, `^[A-Z][A-Z0-9]*-\d+$` — key shape confirmed from `workspace/skills/atlassian-itsm/SKILL.md:108` ("NET-1234") | `NET-1234` | **Operator-supplied.** Jira workflow statuses are per-project configurable, so a fixed default would be wrong for most tenants; the adapter needs an operator-configurable status list rather than a shipped constant | `atlassian-itsm` — exists at `workspace/skills/atlassian-itsm/`, uses `jira_get_issue` / `jira_get_transitions` / `jira_transition_issue`; `atlassian-mcp` is registered in `config/openclaw.json` |
| `none` | no ITSM (ungated) | `None` — no reference required or validated | — | n/a | n/a — no verification occurs; every call is a GAIT-logged bypass (FR-012) |

**Note on `halo`**: feature 069 is an unmerged dependency. Neither `halo-mcp`
nor a Halo change skill exists in this worktree, so this row records what the
adapter needs rather than asserting what it is. The `atlassian` row's
operator-supplied state vocabulary and the `halo` row's pending reference format
are the two adapter fields that cannot be finalized from this branch alone.

---

## Entity: `ChangeRef`

The operator-supplied reference to a change record. Not a stored object — a
validated view over the string a tool received.

| Field | Type | Notes |
|---|---|---|
| `raw` | `str \| None` | Exactly what the tool passed in, echoed unmodified into the envelope's `cr_number`. |
| `provider` | `ItsmProvider` | The provider the reference was evaluated against. |
| `matches_format` | `bool` | Result of `adapter.ref_pattern` (always `True` for `none`). |
| `param_name` | `str` | Which tool parameter carried it — informational, for the GAIT record only. |

**Validation rules**

- Presence is checked first: empty or `None` → invalid, with the calling
  subsystem named in the message ("gNMI Set operations" / "Claroty write
  operations"). These two strings are supplied by the **shim**, not by a tool
  parameter (research R4), and are preserved byte-for-byte.
- Format is checked against the **configured provider's** pattern only. A
  `CHG0012345` reference under provider `halo` MUST be rejected with a message
  naming Halo's expected format — never silently accepted (spec Edge Cases).
- `raw` is echoed **verbatim** in the envelope, including when it is `""` or
  malformed. This preserves observed behavior at
  `mcp-servers/gnmi-mcp/itsm_gate.py:38-54`, where `cr_number` mirrors the input
  on every rejection path.
- **Requiredness is a property of the tool signature, not of `ChangeRef`**, and
  FR-010/SC-007 freeze it:

  | Server | Parameter | Requiredness |
  |---|---|---|
  | `gnmi-mcp` (`gnmi_set`) | `change_request_number` | required |
  | `claroty-mcp` (6 write tools) | `cr_number` | required |
  | nautobot family (35 tools, follow-on) | `cr_number` | **optional** |

  No rename, no requiredness change, in v1 or in the follow-on phase.

---

## Entity: `GateDecision` (the envelope — public contract)

The dict returned by `validate_change_request()`. Claroty publishes it whole to
the model as `{"itsm_gate": <GateDecision>, "applied": <bool>, …}`, so its keys
are a public contract: **additive changes only** (FR-009).

| Key | Type | Status | Meaning |
|---|---|---|---|
| `valid` | `bool` | **pre-existing / back-compat** | Whether the write may proceed. Load-bearing: branched on at `mcp-servers/gnmi-mcp/gnmi_mcp_server.py:220` and at all six Claroty sites (`tools/alerts.py:181`, `tools/devices.py:227,283`, `tools/user_actions.py:48,110`, `tools/vulnerabilities.py:210`). |
| `message` | `str` | **pre-existing / back-compat** | Always present. Operator-facing explanation; carries the provider's `display_name` and, on the two subsystem-specific paths, the shim's operation label. |
| `cr_number` | `str \| None` | **pre-existing / back-compat — name retained** | The reference that was checked, echoed verbatim. The name is now provider-neutral in meaning but MUST NOT be renamed (renaming is breaking; `provider` supplies the missing context). |
| `state` | `str \| None` | **pre-existing / back-compat** | Observed value domain today: `None` (format failure), `"lab_mode"`, `"unverified"`, `"error"`, or a provider-native state string. New values are additive members of this domain, e.g. `"none"` for the ungated provider. |
| `provider` | `str` | **additive (new)** | The active `ItsmProvider` value (FR-002). Present on every decision, including bypasses. |
| `verified` | `bool` | **additive (new)** | `True` only when a skill attested a state that the adapter counts as approved. MUST be `False` on every other path, including `state: "unverified"`, `"lab_mode"`, `"error"`, and `"none"` (FR-008). |
| `attested_state` | `str \| None` | **additive (new, proposed)** | The provider-native state the verifying skill claims (spec Open Question 4). `None` when the caller supplied none. |

**Invariants**

- Additive only: no pre-existing key is ever removed, renamed, or retyped, and
  the four back-compat keys keep their exact meanings.
- `valid == False` ⇒ the calling tool MUST NOT perform the write. Both existing
  servers already honor this; the shared gate does not change the contract.
- `verified == True` requires an `attested_state` present **and** in
  `adapter.approved_states`. The gate MUST NEVER report verification that did not
  occur (FR-008) — this is the single most important invariant in the model,
  because the pre-refactor code's docstrings implied verification it never
  performed.
- JSON/GCF-serializable: Claroty passes the envelope through `gcf_dumps()`
  (`mcp-servers/claroty-mcp/utils/gcf_helper.py`) and `json.dumps(..., indent=2)`.
  So: primitives only — no sets, no `datetime`, no dataclass instances, no
  regex objects.
- Under a non-ServiceNow provider, no rendered `message` may contain the string
  "ServiceNow" (SC-002).

---

## Entity: `GateConfig`

Resolved policy, computed once at module import and reused for every decision
(no per-call environment reads).

| Field | Type | Source | Default |
|---|---|---|---|
| `provider` | `ItsmProvider` | `NETCLAW_ITSM_PROVIDER` | recommended `none` + startup warning (Open Question 2) |
| `lab_mode` | `bool` | `NETCLAW_LAB_MODE` | `false` — truthy set `("true", "1", "yes")`, case-insensitive, preserving `mcp-servers/gnmi-mcp/itsm_gate.py:57` exactly |
| `strict` | `bool` | `NETCLAW_ITSM_STRICT` (**proposed**, Open Question 3) | `false` — v1 stays fail-open for compatibility |
| `source` | `str` | which variable/default supplied `provider` | — |
| `warnings` | `list[str]` | emitted at import (unset provider, unavailable verification skill) | `[]` |

**Validation and precedence rules**

- **Unknown provider is an error even in lab mode.** Lab mode must not mask a
  misconfiguration — an operator who typo'd `serviccenow` needs to hear about it
  in the lab, not in production.
- **Bypass precedence**: `lab_mode == True` **or** `provider == none` ⇒ a single
  bypass decision (`valid: True`, `verified: False`, `state: "lab_mode"` or
  `"none"`), GAIT-logged as a bypass (FR-012). When both hold, one decision is
  produced and the GAIT record names both reasons; there is no double bypass and
  no ambiguity about which fired.
- `strict` has no effect on a bypass path — bypass is a deliberate operator
  choice, not an unverified accident.
- Delivery (FR-015): `NETCLAW_ITSM_PROVIDER` must appear in the `env` block of
  every gated server in `config/openclaw.json`. `gnmi-mcp`'s block
  (`config/openclaw.json:81-90`) currently carries **no** ITSM variable at all,
  so it must gain both `NETCLAW_ITSM_PROVIDER` and `NETCLAW_LAB_MODE`, or
  provider selection silently no-ops there the same way lab mode does today.
  `claroty-mcp` already receives `NETCLAW_LAB_MODE` at
  `config/openclaw.json:557`.
- **Not touched in v1**: the nautobot family's `ITSM_ENABLED` / `ITSM_LAB_MODE`
  pair. When the follow-on phase migrates them, they map onto `GateConfig` with
  defaults preserved — `ITSM_ENABLED=false` (default) behaves as
  `provider = none`, and `ITSM_LAB_MODE=true` (default) behaves as
  `lab_mode = True` — so that migration flips no deployment's posture.

---

## Decision flow (how a `GateDecision` is reached)

Evaluation is a single synchronous pass with no I/O (research R2). Order matters:
it is chosen so that every currently-reachable path produces byte-identical
output under provider `servicenow` with no attestation (SC-003).

1. **Resolve config** — `GateConfig` from import-time state. Unknown provider ⇒
   configuration error, terminal.
2. **Bypass check** — `lab_mode` or `provider == none` ⇒ `valid: True`,
   `verified: False`, `state: "lab_mode"` / `"none"`; GAIT bypass record;
   terminal. (Preserves today's lab-mode message and `state: "lab_mode"`.)
3. **Presence check** — empty/missing `ChangeRef.raw` ⇒ `valid: False`,
   `state: None`, message = shim's operation label ("Change request number is
   required for … operations"); terminal.
4. **Format check** — `adapter.ref_pattern` fails ⇒ `valid: False`,
   `state: None`, message names `display_name` + `ref_description` +
   `ref_example`; terminal (FR-005).
5. **Verification classification** —
   - `attested_state` present **and** in `adapter.approved_states` ⇒
     `verified: True`, `state` = the native attested string, `valid: True`.
   - `attested_state` present **and not** approved ⇒ `valid: False`, message in
     the form "…is in '<state>' state, not '<approved>'…" plus the subsystem
     clause — mirroring the pre-existing, currently unreachable branch at
     `mcp-servers/gnmi-mcp/itsm_gate.py:102-111`.
   - `attested_state` absent ⇒ `verified: False`, `state: "unverified"`.
6. **Policy** — for the `unverified` outcome: `strict == False` (v1 default) ⇒
   `valid: True` (status quo preserved); `strict == True` ⇒ `valid: False` with a
   message stating that no skill verified the record.
7. **GAIT record** — one entry per decision carrying provider, reference,
   verification status, allow/deny outcome, and the operation label (FR-013).
   Emitted from the shared gate so all 7 v1 tools are uniform: `gnmi-mcp`
   already logs decisions (`gnmi_mcp_server.py:97-110`), `claroty-mcp` logs
   nothing today.

### Terminal outcomes

| Condition | `valid` | `state` | `verified` |
|---|---|---|---|
| Unknown provider value | *error raised* | — | — |
| Lab mode on | `True` | `"lab_mode"` | `False` |
| Provider `none` | `True` | `"none"` | `False` |
| Reference missing/empty | `False` | `None` | `False` |
| Reference fails provider format | `False` | `None` | `False` |
| Valid reference, no attestation, non-strict | `True` | `"unverified"` | `False` |
| Valid reference, no attestation, strict | `False` | `"unverified"` | `False` |
| Attested, state approved | `True` | native state | `True` |
| Attested, state not approved | `False` | native state | `False` |
| Internal error during evaluation | `True` | `"error"` | `False` |

The last row preserves the existing fail-open exception path
(`mcp-servers/gnmi-mcp/itsm_gate.py:113-123`).

---

## Not modeled here (explicitly out of this data model)

- **`_check_itsm(cr_number: Optional[str]) -> Optional[str]`** — the nautobot
  family's separate contract (`nautobot-mcp-v2/server.py:39`,
  `nautobot-routing-mcp/server.py:57`,
  `nautobot-golden-config-mcp/server.py:60`). Returns an error message or `None`,
  performs **no** format validation, and gates 35 tools with gating **off** by
  default. Follow-on phase (FR-014); its mapping onto `GateConfig` is sketched
  above but not implemented in v1.
- **`validate_cr_number(cr_number) -> Tuple[bool, str|None]`** —
  `mcp-servers/memory-mcp/storage/sqlite_store.py:109`. Audit *provenance* for
  `memory_record_decision`, not a gate. Stays `^CHG\d+$`, so a Halo or Jira
  reference will be rejected there; documented as a known deferred
  inconsistency (FR-016). It is also the only change-reference validator in the
  repo that currently has tests (`tests/unit/test_sqlite_store.py:98-107`).
- **`GnmiSetRequest`** — `mcp-servers/gnmi-mcp/models.py:186-207`, unreferenced
  dead code carrying a second `^CHG\d+$` validator at `:198`. Deleted, not
  modeled; its removal is what takes SC-001's validator count from 4 to 1.
