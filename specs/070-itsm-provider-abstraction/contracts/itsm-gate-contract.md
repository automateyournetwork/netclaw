# Contract — Shared ITSM Change Gate (`src/netclaw_itsm/`)

**Feature**: 070-itsm-provider-abstraction
**Status**: PROPOSED — contract for maintainer review. Not implemented. Blocked on the Constitution amendment (1.2.0 → 1.3.0, see `contracts/constitution-amendment.md`).

This document is the interface contract for the single shared change gate that replaces the duplicated per-server gate logic (FR-001). It defines the public function signature, the returned `GateDecision` envelope and its back-compat guarantees, the per-provider adapter data, the shim contract that keeps existing import sites unchanged, and the full input → decision behavior table.

**Scope of v1**: the two servers using the `validate_change_request()` contract — **7 gated tools** (`gnmi_set` plus the six Claroty write tools `acknowledge_alert`, `set_device_purdue_level`, `set_device_custom_attribute`, `set_vulnerability_relevance`, `label_alerts`, `assign_alerts`). The three nautobot servers (**35 gated tools**, `_check_itsm() -> Optional[str]`, `ITSM_ENABLED` + `ITSM_LAB_MODE`) are a specified follow-on and are **not** covered by this contract (FR-014). Current-state totals being consolidated: **5 gate implementations, 42 gated tools, 4 independent `^CHG\d+$` regexes, 0 existing tests.**

---

## 1. Public API

The shared module lives at `src/netclaw_itsm/`, following the one working precedent for cross-server Python in this repo (`src/netclaw_tokens/`, imported via a `sys.path` insert anchored on `__file__`).

### 1.1 Entry point

```python
def validate_change_request(
    cr_number: str,
    *,
    operation_label: str = "write operations",
    attested_state: str | None = None,
) -> dict[str, Any]
```

**THE ENTRY POINT IS SYNCHRONOUS.** It is a plain `def`, not `async def`, and MUST remain so. This is not a style preference — it is a hard constraint from the call sites:

- `gnmi_set` (`mcp-servers/gnmi-mcp/gnmi_mcp_server.py:196`) is a plain `def` tool and calls the gate at line 219 with no `await` available.
- The six Claroty write tools are `async def` but call the gate **unawaited** (e.g. `mcp-servers/claroty-mcp/tools/alerts.py:180`, `gate = validate_change_request(cr_number)`).

Making the gate `async` would be a breaking change at all seven call sites. This constraint is also why server-side ITSM HTTP verification was rejected in favor of skill-layer verification (see §7).

**Parameters**

| Parameter | Type | Required | Meaning |
|---|---|---|---|
| `cr_number` | `str` | yes, positional | The operator-supplied change reference (`ChangeRef`). Name retained from the pre-refactor signature — see §4. Format is provider-specific (§3). |
| `operation_label` | `str` | keyword-only, defaulted | Human-readable label for the gated operation class, interpolated into the "reference is required" message. Bound by each shim (§4) so today's exact message strings are preserved byte-for-byte. **New in 070; additive.** |
| `attested_state` | `str \| None` | keyword-only, defaulted `None` | **New in 070; additive (Open Question 4).** The change record's state as *actually observed* by the verifying skill immediately before the write, in the provider's native vocabulary (e.g. `"Implement"`, `"Approved"`). `None` means no skill verified the state — the gate MUST then report `verified: false` and MUST NOT claim verification (FR-008). |

`attested_state` is the only mechanism by which a `GateDecision` may report `verified: true`. Absent it, every decision is honestly `unverified`.

### 1.2 Supporting public surface

```python
SUPPORTED_PROVIDERS: tuple[str, ...]          # ("servicenow", "halo", "atlassian", "none")

def resolve_config() -> GateConfig            # reads env; never raises
def get_adapter(provider_id: str) -> ProviderAdapter | None
```

`GateConfig` carries the resolved active provider, the lab/bypass state, and (proposed, Open Question 3) the strict flag. `ProviderAdapter` is **pure declarative data** — reference pattern, display name, approved-state vocabulary, responsible verification skill — and contains no transport, credential, or HTTP logic whatsoever (FR-004, FR-006).

### 1.3 Error discipline

`validate_change_request()` **MUST NOT raise** for any input, including an unrecognized provider value. Neither `gnmi_set` nor any Claroty write tool wraps the gate call in `try`/`except`, so a raised exception would surface as an unhandled traceback rather than a gate denial. Configuration errors are therefore returned as a **deny decision** with `state: "config_error"` and a message naming the supported providers (FR-003 — explicit, loud, and never a silent vendor fallback). Exceptions remain reserved for genuine programming errors (e.g. a non-`str` `cr_number`).

### 1.4 Configuration inputs

| Variable | Values | Default | Notes |
|---|---|---|---|
| `NETCLAW_ITSM_PROVIDER` | `servicenow` \| `halo` \| `atlassian` \| `none` | **Open Question 2** — spec recommends `none` with a startup warning | Case-insensitive, whitespace-trimmed. Any other value → `config_error` deny. MUST be added to **every** gated server's `env` block in `config/openclaw.json` (FR-015), including `gnmi-mcp`, whose block (`config/openclaw.json:81-90`) currently passes **no** ITSM variable at all — its lab bypass works today only by parent-environment leakage. |
| `NETCLAW_LAB_MODE` | `true` \| `1` \| `yes` (case-insensitive) enable; anything else disables | `false` | Existing variable, semantics unchanged. Present in `claroty-mcp`'s env block; absent from `gnmi-mcp`'s. |
| `NETCLAW_ITSM_STRICT` | `true` \| `1` \| `yes` | `false` | **Proposed, opt-in (Open Question 3).** When enabled, a format-valid but unverified reference denies instead of permitting. Default `false` preserves today's fail-open behavior and SC-003. |

---

## 2. The `GateDecision` envelope

The return value is a plain `dict`. It is a **public contract**, not an internal detail: Claroty publishes the whole dict inside its tool output as `{"itsm_gate": <GateDecision>, "applied": bool, "response": ...}` (see `tools/alerts.py:182,219,223` and the equivalent lines in `devices.py`, `user_actions.py`, `vulnerabilities.py`). Any consumer parsing Claroty tool output sees these keys.

| Key | Type | Meaning | Compatibility |
|---|---|---|---|
| `valid` | `bool` | Whether the gated write may proceed. `False` = deny; the caller MUST NOT perform the write. | **BACK-COMPAT — unchanged.** Present pre-070, same type, same meaning. |
| `message` | `str` | Human-readable explanation. Always present, never `None`, never empty. Surfaced verbatim to operators and into GAIT. | **BACK-COMPAT — key unchanged.** The *key* is contractual; the *text* is not (it necessarily changes per provider — that is the point of the feature, SC-002). The one exception: under provider `servicenow` the text MUST remain byte-identical to pre-070 (§4, SC-003). |
| `cr_number` | `str` | The change reference that was evaluated, echoed back exactly as supplied (including invalid values, so the operator can see what was rejected). | **BACK-COMPAT — MUST NOT BE RENAMED.** Renaming this to `change_ref` or similar is a **breaking change** to Claroty's published tool output. It keeps the ServiceNow-flavored name deliberately; the name is frozen even for non-ServiceNow providers. |
| `state` | `str \| None` | Canonical state of the decision/change record. `None` when no state could be determined (missing or malformed reference). Vocabulary in §2.1. | **BACK-COMPAT — key and existing values unchanged.** The vocabulary is **extended additively**; no pre-070 value changes meaning. |
| `provider` | `str` | The active provider id that evaluated this decision (`servicenow` \| `halo` \| `atlassian` \| `none`), or the raw offending value on a `config_error`. | **ADDITIVE — new in 070.** Explicitly sanctioned by spec US2 acceptance scenario 3. |
| `verified` | `bool` | Whether the change record's state was **actually verified by the skill layer** for this decision. `true` only when a non-`None` `attested_state` was supplied. Never `true` on the strength of format validation alone. | **ADDITIVE — new in 070.** This is the FR-008 "verification indicator" and the key an auditor reads for SC-006. |

These six keys are the complete envelope. Implementations MUST populate all six on every return path.

### 2.1 `state` vocabulary

Canonical internally, provider-native in `message` (Open Question 6 recommendation).

| Value | Meaning | Status |
|---|---|---|
| `None` | No state determined — reference missing or malformed. | Pre-070, unchanged. |
| `"unverified"` | Reference format-valid; state not verified by anyone. **This is the status-quo happy path** — today every well-formed `CHG\d+` lands here. | Pre-070, unchanged. |
| `"lab_mode"` | Lab bypass taken; format was still checked first. | Pre-070, unchanged. |
| `"error"` | Verification attempt raised. **Retained in the vocabulary for envelope compatibility but unreachable in v1**, because the shared gate makes no network calls (§7). No characterization test can reach it; today it is equally unreachable, since `_check_servicenow_cr_state()` returns `None` unconditionally. | Pre-070, unchanged, dead. |
| `"approved"` | Skill layer attested a state that is in the active provider's approved-for-implementation vocabulary. Paired with `verified: true`. | **Additive.** |
| `"not_approved"` | Skill layer attested a state that is **not** in the approved vocabulary → deny. Paired with `verified: true`. | **Additive.** |
| `"no_itsm"` | Provider `none`: no external change record is required. | **Additive.** |
| `"config_error"` | `NETCLAW_ITSM_PROVIDER` holds an unrecognized value. | **Additive.** |

Provider-native state strings (e.g. `"Implement"`) MUST NOT be placed in `state`; they belong in `message`. Pre-070 code would have returned raw provider states in `state` on a code path that has never executed, so nothing depends on it.

---

## 3. Provider adapters

Declarative data only (FR-004). One active provider per deployment; multi-provider-simultaneous gating is a non-goal.

| Provider id | Display name | Change-reference format | Valid example | Invalid example | Approved-state vocabulary | Verifying skill (FR-007) |
|---|---|---|---|---|---|---|
| `servicenow` | ServiceNow | `^CHG\d+$` — literal `CHG` + one or more digits | `CHG0012345` | `1084` (bare integer — a valid **Halo** ref, rejected here) | `Implement` → canonical `approved` | `servicenow-change-request`, calling the install-time ServiceNow clone via `$SERVICENOW_MCP_SCRIPT` / `$MCP_CALL`. **Caveat**: there is no `servicenow-mcp` registered in `config/openclaw.json`, so this path is reachable only as an unregistered clone — see Open Question 8. |
| `halo` | HaloPSA / HaloITSM | **PROVISIONAL** `^\d+$` — a Halo change-ticket id (Halo ticket ids are integers; change tickets are a distinct ticket type) | `1084` | `CHG0012345` (ServiceNow-shaped — MUST be rejected with a Halo-specific message, US1 acceptance scenario 2) | Halo change-ticket status naming its post-approval/implementation state → canonical `approved`. **Requires confirmation against feature 069's ticket-type and status data.** | `halo-change-request` (feature 069, PR #167). **Feature 069 is an unmerged dependency: `halo-mcp` and this skill do not exist on this branch.** If 069 does not land, this adapter ships with its verification skill marked unavailable, per the spec's Assumptions. |
| `atlassian` | Atlassian Jira / Jira Service Management | Jira issue key `^[A-Z][A-Z0-9]+-\d+$` | `CHG-482`, `NETOPS-1204` | `CHG0012345` (no hyphen — not a Jira key) | Workflow-dependent; the adapter declares the operator-configurable set (e.g. `Approved`, `Implementing`) → canonical `approved` | `atlassian-change-request`, via the registered `atlassian-mcp` |
| `none` | *(no ITSM gating)* | Not validated. A reference MAY be supplied and is echoed in `cr_number`, but is neither required nor pattern-checked. | any value, including `""` | — (nothing is invalid) | n/a | none — the bypass itself is the audit record and MUST be GAIT-logged (FR-012) |

**Format notes for maintainer review**

- The bare-integer Halo pattern is flagged PROVISIONAL because it accepts any typo'd digit string and cannot be told apart from a mistyped ticket number. A prefixed operator-facing form (e.g. `HALO-1084`, normalized to the integer before use) would be unambiguous at the cost of not matching what Halo's own UI displays. This is a decision for the maintainers, related to Open Question 5.
- Cross-provider references MUST NEVER be silently accepted. Under `halo`, `CHG0012345` is a denial, not a fallback (spec Edge Cases; a silent fallback would recreate the original bug).
- Reference-format matching is the **only** validation the gate performs on the reference. It does not check existence, ownership, scheduling window, or CAB status — no gate code can, without network access.

---

## 4. Shim contract

Thin per-server shims are retained at the two existing gate paths so that no import site or call site churns (FR-010, SC-007). Each shim MUST behave as an alias of the shared gate with its `operation_label` pre-bound.

### 4.1 `mcp-servers/gnmi-mcp/itsm_gate.py`

MUST continue to export:

```python
def validate_change_request(cr_number: str) -> dict[str, Any]
```

- Callable with **exactly one positional argument**. The sole importer is `mcp-servers/gnmi-mcp/gnmi_mcp_server.py:50` — `from itsm_gate import validate_change_request` — and the sole call site is line 219, `itsm_result = validate_change_request(change_request_number)`. Both MUST remain unchanged.
- MUST bind `operation_label` such that the empty-reference message is byte-identical to today's: `"Change request number is required for gNMI Set operations"`.
- MAY accept and forward `attested_state` as a keyword-only parameter (that is how a future gnmi skill would attest), but MUST NOT make it required.
- MUST resolve `netclaw_itsm` itself via its own `sys.path` insert anchored on `__file__` (`os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")`), matching the `netclaw_tokens` precedent. It MUST NOT rely on the insert that `gnmi_mcp_server.py:31` happens to perform first, so that the module is importable standalone (which the characterization tests require).

### 4.2 `mcp-servers/claroty-mcp/utils/itsm_gate.py`

MUST continue to export the same one-positional-argument `validate_change_request(cr_number)`.

- Four importers, all `from utils.itsm_gate import validate_change_request`: `tools/alerts.py:17`, `tools/devices.py:27`, `tools/user_actions.py:22`, `tools/vulnerabilities.py:17`. Six call sites: `alerts.py:180`, `devices.py:226`, `devices.py:282`, `user_actions.py:47`, `user_actions.py:109`, `vulnerabilities.py:209`. All MUST remain unchanged.
- MUST bind `operation_label` such that the empty-reference message is byte-identical to today's: `"Change request number is required for Claroty write operations"`.
- MUST resolve `netclaw_itsm` via its own `sys.path` insert of `os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src")` — three levels up from `utils/`, exactly as `mcp-servers/claroty-mcp/utils/gcf_helper.py:8` already does. Claroty's server module (`claroty_mcp_server.py:25`) inserts only its own directory, so the shim cannot inherit a `src` path.

### 4.3 Private names

`_CR_PATTERN` and `_check_servicenow_cr_state()` are private and have **no importers anywhere in the repo**. The shared gate MUST NOT call `_check_servicenow_cr_state()` (it is a stub returning `None`, and the shared gate makes no network calls). Recommendation: the characterization suite (FR-011) MUST NOT monkeypatch either name, so both can be deleted with the shim rewrite. If any characterization test does depend on them, the shims MUST retain them as deprecated no-ops for exactly as long as that test does.

### 4.4 Parameter names at the MCP boundary

Untouched by this contract, and MUST stay untouched (FR-010, SC-007):

| Server | MCP tool parameter | Requiredness |
|---|---|---|
| `gnmi-mcp` | `change_request_number` | required |
| `claroty-mcp` | `cr_number` | required |
| nautobot family (follow-on, not v1) | `cr_number` | **optional** |

The shared gate's own first parameter is `cr_number`; the gnmi shim receives whatever `gnmi_set` passes positionally, so the tool-level name `change_request_number` needs no rename.

---

## 5. Behavior table

Evaluation order is normative — it is what preserves status-quo behavior:

1. resolve provider → unknown value denies immediately (a misconfiguration MUST NOT be maskable by lab mode);
2. provider `none` → permit;
3. reference presence;
4. reference format;
5. lab bypass;
6. attestation;
7. strict mode.

Steps 3 → 4 → 5 reproduce today's ordering exactly: **format is checked before the lab bypass**, so a malformed reference is rejected even in lab mode.

| # | Input condition | `valid` | `state` | `verified` | `provider` | Message names |
|---|---|---|---|---|---|---|
| 1 | Provider `servicenow`; `CHG0012345`; no attestation | `true` | `unverified` | `false` | `servicenow` | ServiceNow; verification unavailable |
| 2 | Provider `halo`; valid Halo ref; no attestation | `true` | `unverified` | `false` | `halo` | Halo; verification unavailable |
| 3 | Any provider; format-valid ref; `attested_state` in approved vocabulary | `true` | `approved` | `true` | as configured | provider + provider-native state |
| 4 | Any provider; format-valid ref; `attested_state` **not** in approved vocabulary | `false` | `not_approved` | `true` | as configured | provider + observed state + required state(s) |
| 5 | Provider `halo`; `CHG0012345` (**wrong-provider format**) | `false` | `None` | `false` | `halo` | Halo + Halo's expected format. Never accepted, never a fallback. |
| 6 | Any real provider; malformed ref (e.g. `chg123`, `NET 482`) | `false` | `None` | `false` | as configured | provider + expected format |
| 7 | Any real provider; `cr_number` empty / falsy | `false` | `None` | `false` | as configured | shim-bound `operation_label`; byte-identical to pre-070 under `servicenow` |
| 8 | Lab mode on; provider `servicenow`; format-valid ref | `true` | `lab_mode` | `false` | `servicenow` | lab mode; state check skipped. **GAIT-logged bypass** (FR-012). |
| 9 | Lab mode on; **malformed** ref | `false` | `None` | `false` | as configured | expected format. Lab mode does **not** waive format validation (preserves today's ordering). |
| 10 | Provider `none` (with or without lab mode; `none` wins and reports `no_itsm`) | `true` | `no_itsm` | `false` | `none` | no ITSM configured; no change record required. **GAIT-logged bypass** (FR-012). |
| 11 | Provider `none`; no ref supplied at all | `true` | `no_itsm` | `false` | `none` | as row 10 — no reference is required |
| 12 | `NETCLAW_ITSM_PROVIDER` unrecognized (e.g. `jira`, `Servicenow!`, `remedy`) | `false` | `config_error` | `false` | the raw offending value | configuration error + the four supported ids. **Never falls back to ServiceNow** (FR-003). Not bypassable by lab mode. |
| 13 | Strict mode on; format-valid ref; **no** attestation | `false` | `unverified` | `false` | as configured | strict mode requires verified state. **Opt-in only** (Open Question 3); default off preserves row 1. |
| 14 | Strict mode on; format-valid ref; attested approved | `true` | `approved` | `true` | as configured | as row 3 |

**Precedence resolutions this table settles** (both called out as undefined in the spec's Edge Cases):

- **Unknown provider vs lab mode**: unknown provider wins (row 12). A misconfiguration must be loud even in a lab.
- **Provider `none` vs lab mode**: `none` wins and reports `no_itsm` (row 10), because provider selection is explicit operator configuration while lab mode is ambient environment. The permit/deny outcome is identical either way; only `state` differs.

**GAIT (FR-013)**: every decision — allow and deny — is recorded with the provider, the change reference, the verification status, and the outcome. The gate module itself does not write GAIT; the calling server does, as `gnmi_set` already does at `gnmi_mcp_server.py:221-227`. Servers MUST extend their existing GAIT calls with `provider` and `verified`.

---

## 6. Compatibility guarantees and breaking-change rules

### Guaranteed (a conforming implementation MUST NOT break these)

1. `validate_change_request()` stays **synchronous** and callable with one positional `str`.
2. The two shim module paths stay importable at their current paths with their current export names.
3. All six envelope keys are present on every return path; the four pre-070 keys keep their names, types, and meanings.
4. `cr_number` keeps its name.
5. Under provider `servicenow` with lab mode off and strict mode off, every decision — including `message` text, byte-for-byte — is identical to the pre-070 gate. This is what the characterization suite (FR-011) locks down and what SC-003 measures.
6. No MCP tool parameter is renamed and none changes requiredness (SC-007).
7. The four pre-070 `state` values keep their exact spellings.

### A future change MAY

- add new keys to the envelope (additive only);
- add new `state` values;
- add new providers to `SUPPORTED_PROVIDERS` and new adapters;
- change `message` **text** for non-`servicenow` providers freely, and for `servicenow` only alongside an updated characterization baseline;
- add new keyword-only parameters with defaults that preserve current behavior.

### A future change MUST NOT (each is breaking; requires a new contract version and a coordinated consumer update)

- rename or remove `valid`, `message`, `cr_number`, or `state`;
- rename `cr_number` to a provider-neutral name — the ServiceNow-flavored name is deliberately frozen;
- change the type of any existing key (e.g. `state` to a dict, `valid` to a tri-state);
- repurpose an existing `state` value;
- make the entry point `async`, or add a required positional/keyword parameter;
- make `verified: true` reachable without a real skill-layer attestation (that would resurrect exactly the dishonesty this feature removes);
- default `NETCLAW_ITSM_PROVIDER` to a vendor when it is unset or invalid;
- move the shim module paths, or drop their one-positional-argument form, while the current call sites exist.

---

## 7. Explicit non-responsibilities

This contract deliberately does **not** cover, and a conforming gate MUST NOT do, the following:

| Not done here | Why | Who owns it |
|---|---|---|
| **Any network call to any ITSM** (FR-006) | NetClaw MCP servers cannot call other MCP servers — no MCP client exists anywhere under `mcp-servers/`; `scripts/mcp-call.py` is used only by skills, bash, and the UI. Server-side HTTP would also require per-ITSM credentials inside every gated server and an `async` gate, which §1.1 forbids. | The agent/skill layer, which can reach any ITSM's MCP tools |
| **Credential handling** — no tokens, no API keys, no instance URLs | Nothing in the gate authenticates to anything. Adapters are data. | The provider's MCP server + its `config/openclaw.json` env block |
| **Change-record state verification** | The gate can only *receive* an attested state; it cannot observe one. | The per-provider verifying skill named in §3 (FR-007) |
| **Deciding *which* tools are gated / what counts as a write** | Unchanged by this feature (explicit non-goal). | Each server's own tool definitions |
| **Writing GAIT records** | The gate returns a decision; the caller already owns its audit call. | The calling MCP server (FR-013) |
| **nautobot's `_check_itsm()` contract** (35 tools, `Optional[str]`, `ITSM_ENABLED` + `ITSM_LAB_MODE`) | Different contract, different env scheme, gating currently defaults **off** — migrating it is a breaking env change needing its own compatibility analysis. | Follow-on phase (FR-014, Open Question 7) |
| **Memory MCP change-reference provenance** (`memory-mcp/storage/sqlite_store.py:109`, `validate_cr_number()`, `^CHG\d+$`) | Provenance metadata for audit records, not a gate. | Deferred, documented as a known user-visible inconsistency: a Halo or Jira reference will fail it (FR-016) |

**The honest consequence, stated plainly**: with skill-layer verification the server-side gate is **advisory**. A direct tool call can assert any reference. The real controls are the skill layer and the GAIT audit trail. This is not a regression — today's gate enforces nothing either (`_check_servicenow_cr_state()` returns `None`, so every well-formed reference passes as `unverified`). What this contract changes is that the boundary is now *stated and auditable* rather than implied by a docstring that promises a ServiceNow check the code never performs.

---

## 8. Test obligations

Referenced here because they are part of the contract's acceptance, not merely of the plan:

- **FR-011 / US2-1**: characterization tests capturing the **current** behavior MUST exist and pass against the **unrefactored** code before the shared module replaces it. There are **0 existing tests** across all five gate implementations, so this baseline is written from the code in `mcp-servers/gnmi-mcp/itsm_gate.py` and `mcp-servers/claroty-mcp/utils/itsm_gate.py`.
- The suite MUST cover, at minimum: each provider's format validation (valid and invalid), wrong-provider references, the unknown-provider error, the lab and `none` bypasses, the verified/unverified distinction, and the exact Claroty `{"itsm_gate": ..., "applied": ...}` envelope shape (SC-004).
- Rows 1, 7, 8, and 9 of §5 are the status-quo rows; their assertions MUST be identical before and after the refactor (SC-003).
