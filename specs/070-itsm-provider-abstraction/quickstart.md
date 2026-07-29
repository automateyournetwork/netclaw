# Quickstart — ITSM Provider Abstraction (Feature 070)

**Status**: this feature is a **proposal**. Nothing below is implemented yet; implementation is
blocked pending maintainer ratification of the Constitution amendment (1.2.0 → 1.3.0). This
document serves two audiences: a **maintainer reviewing the proposal**, and an **operator** who
will use the feature once it ships.

---

## Part 1 — For the maintainer reviewing this proposal

### What to read, in order

| # | File | Why |
|---|------|-----|
| 1 | `spec.md` | The problem, four user stories, 17 functional requirements, and the **9 Open Questions** that need your decisions |
| 2 | `contracts/constitution-amendment.md` | The **literal before/after text** for all five ServiceNow-naming locations, plus the proposed Sync Impact Report. Review this as a diff |
| 3 | `research.md` → R2, R3, R6 | Why the gate can't verify state itself (R2), where the shared module lives (R3), and the amendment's scope + bump justification (R6) |
| 4 | `contracts/itsm-gate-contract.md` | The interface and its backwards-compatibility guarantees |
| 5 | `plan.md` → Constitution Check | How this feature reconciles with the Constitution it proposes to amend |
| 6 | `tasks.md` | The phased execution, with T010 as the single ratification gate |

### The decisions we need from you

All nine are listed in `spec.md` → *Open Questions for Maintainer Review*, each with a
recommendation. **Three of them change the module's public API**, so they must be settled
before implementation starts, not during:

- **OQ2 — default provider when unset** (`none` vs `servicenow`)
- **OQ3 — fail-open vs an opt-in strict mode**
- **OQ4 — adopt the `attested_state` parameter?**

The remaining six (config mechanism, adapter set, state vocabulary, nautobot migration,
`servicenow-mcp` registration, amendment scope) can be settled in review comments.

### The one thing to push back on hardest

With skill-layer verification, **the server-side gate is advisory** — a direct tool call can
assert any change reference. We chose this because NetClaw's MCP servers cannot call other MCP
servers (`research.md` R2), and we documented it plainly rather than implying enforcement.

If you want the gate to *actually* enforce, that is a different and larger feature: it means
per-ITSM HTTP clients and credentials inside every gated server, plus resolving the
sync-callability constraint. Worth deciding now, because it changes the architecture.

Note the honest baseline: **today's gate enforces nothing either.**
`_check_servicenow_cr_state()` returns `None`, so every well-formed `CHG\d+` already passes as
`unverified`. This feature does not weaken the current posture; it makes it visible.

### Verifying this proposal

```bash
# Nothing outside the spec directory should have changed
git status --short          # expect only specs/070-itsm-provider-abstraction/

# The current-state claims are checkable
grep -rn "return None" mcp-servers/gnmi-mcp/itsm_gate.py          # the fail-open stub
grep -rn "servicenow" config/openclaw.json                        # expect: no matches
grep -rniE "itsm|validate_change_request" tests/                  # expect: no matches (0 tests)
diff mcp-servers/gnmi-mcp/itsm_gate.py mcp-servers/claroty-mcp/utils/itsm_gate.py
```

---

## Part 2 — For the operator, once this ships

### Prerequisites

- An ITSM that NetClaw can reach for change records: ServiceNow, HaloPSA/HaloITSM, or Jira —
  or none, if you gate changes another way.
- The corresponding integration configured (e.g. the Halo MCP server for `halo`, which
  requires feature 069 / PR #167 to be merged).

### Select your ITSM

Set one variable in `~/.openclaw/.env`:

```bash
NETCLAW_ITSM_PROVIDER=halo        # servicenow | halo | atlassian | none
```

That's the whole configuration. Restart NetClaw so the gated MCP servers pick it up.

### What changes for you

| Before | After |
|--------|-------|
| Every gated write demanded a `CHG…` ServiceNow number | The gate expects **your** ITSM's change reference format |
| Error messages named ServiceNow regardless of your stack | Messages name your configured ITSM |
| `CHG\d+` format check, then fail open | Provider-appropriate format check, plus an explicit record of whether the change's state was verified |

### A gated write, end to end

Using Halo as the example:

1. **Open the change** in your ITSM — via the provider's change skill
   (`halo-change-request`, `servicenow-change-workflow`, or `atlassian-itsm`).
2. **The skill verifies the change is approved** before proceeding. This is the real
   verification step: the skill can reach your ITSM's MCP tools; the server-side gate cannot.
3. **Call the gated tool**, passing the change reference in its existing parameter
   (`cr_number`, or `change_request_number` for `gnmi_set` — these names do not change).
4. **The gate checks** the reference against your provider's format and applies policy, then
   returns its decision including which provider was used and whether the state was verified.
5. **GAIT records** the provider, the reference, the verification status, and allow/deny.

### Lab and no-ITSM operation

Both remain supported and are unchanged in spirit:

```bash
NETCLAW_ITSM_PROVIDER=none        # no external change record required
# or
NETCLAW_LAB_MODE=true             # existing lab bypass
```

Every bypass is still GAIT-logged — that requirement does not relax.

### Troubleshooting

| Symptom | Cause |
|---------|-------|
| Gate rejects a reference that is valid in your ITSM | `NETCLAW_ITSM_PROVIDER` is set to a different provider than you think — check the `provider` field in the gate's response |
| Configuration error naming the supported providers | Unrecognized `NETCLAW_ITSM_PROVIDER` value. This is deliberate: there is **no** silent fallback to ServiceNow |
| Lab bypass not taking effect on gNMI writes | `gnmi-mcp`'s `config/openclaw.json` env block historically passed no ITSM variable (`config/openclaw.json:81-90`); confirm the variable reaches the server |
| A Halo/Jira reference rejected by `memory_record_decision` | Known deferred inconsistency (FR-016): Memory MCP's change-reference provenance check is still ServiceNow-shaped |
