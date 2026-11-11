# Feature Specification: Cisco IQ Remote MCP Integration

**Feature Branch**: `191-cisco-iq-mcp`
**Created**: 2026-11-11
**Status**: Draft
**Input**: GitHub issue #346 - "Add the Official Cisco IQ Remote MCP as a Maintained NetClaw Integration". Provide a supported setup, credential-management, agent-policy and validation workflow for Cisco's official Cisco IQ remote MCP server, using NetClaw's existing native remote MCP support (no custom adapter, no locally hosted Cisco IQ server, no extra credential service).

## Contract Provenance *(read first)*

The connection contract below is taken from the text of issue #346, which cites the official Cisco IQ MCP guide (`https://iq.cisco.com/apidocs/mcp-server`). That guide returned HTTP 403 to automated fetching on 2026-11-11 and so **could not be independently read or verified** during this work. What was verified: the three regional endpoint hostnames resolve and answer an unauthenticated request with HTTP 401 and `www-authenticate: Session realm="Cisco IQ"` (reachability and existence only; not a tool list, schema, or auth behaviour with a real key). Cisco IQ tool names and input/output schemas are **not published to us and are not invented** by this feature; they are discovered at runtime from the server or left configurable.

| Item | Value (per issue #346) |
|---|---|
| Transport | Streamable HTTP |
| EMEA endpoint | `https://eu-central-1.iq.cisco.com/mcp` |
| US endpoint | `https://us-west-2.iq.cisco.com/mcp` |
| APJC endpoint | `https://ap-southeast-2.iq.cisco.com/mcp` |
| Authentication | single `Authorization: Bearer <API_KEY>` header; key used directly, no OAuth/token exchange |
| Key ownership | must be owned by a user principal; service-account-owned keys receive no MCP tools |
| Key lifecycle | keys expire; they inherit the owner's current permissions |

## Clarifications

### Session 2026-11-11 (autonomous defaults; no human available)

- Q: Is the registration pre-seeded in `config/openclaw.json`? -> A: No. Region is mandatory and must be explicit, so a fixed URL cannot be pre-seeded. The enable script writes a `cisco-iq-mcp` url+headers entry into the runtime `openclaw.json`; the catalog records it as an external/remote integration.
- Q: Which variables hold state? -> A: `CISCO_IQ_API_KEY` (secret, runtime `.env`, mode 0600) and `CISCO_IQ_REGION` (non-secret, `emea|us|apjc`); the registration header is the template `Bearer ${CISCO_IQ_API_KEY}`, never the resolved value.
- Q: What does disable do with the credential? -> A: Removes the registration only; the key is kept unless `--purge-credential` is passed (non-interactive safe default, avoids losing a key the admin cannot re-display). This replaces the earlier "removed after confirmation" wording.
- Q: How is "read-only allowlisted" enforced? -> A: NetClaw's native remote client has no per-tool gate, so enforcement is layered and described honestly: a maintained policy file (`config/cisco-iq-policy.json`, deny by default, empty/unverified allowlist, deny patterns for mutating verbs) consumed by an offline `policy check` command and by DefenseClaw `tool allow/block` guidance when DefenseClaw is enabled, plus SOUL/skill instructions. Documentation states it is not a hard sandbox without DefenseClaw.
- Q: How does diagnose test connectivity without a Cisco IQ client library? -> A: A stdlib HTTP client sends MCP `initialize` then `tools/list` over Streamable HTTP with the Bearer header, redacting everything printed; it is opt-in (`--live`) and never run by CI. Offline checks run by default against a local mock endpoint in tests.
- Q: Rotation input channel? -> A: Standard input or a no-echo prompt only; never arguments. Backup is a private 0600 copy of the prior `.env` plus a state journal holding digests, not values.
- Q: Which tool names appear in the skill? -> A: None are asserted. The skill instructs `tools/list` discovery and maps workflows to capability categories; any admin-supplied tool names live in the policy allowlist.
- Q: Update semantics? -> A: `update` re-applies the registration for the current or a newly supplied region and refreshes policy defaults from the repo; it does not change the key.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Connect NetClaw to Cisco IQ in my region (Priority: P1)

An administrator selects their Cisco IQ account region (EMEA, US or APJC) explicitly, supplies a Cisco IQ API key without it appearing in any command line, prompt, committed file or output, and NetClaw registers the Cisco IQ remote MCP server through its existing native remote MCP support.

**Why this priority**: Nothing else is possible until the connection exists, and an unsafe or mis-regioned connection is the main risk.

**Independent Test**: Run the enable procedure offline with a dummy key and a chosen region; confirm the registration carries the selected region's endpoint and a reference to (not the value of) the key, and that no output contains the key.

**Acceptance Scenarios**:

1. **Given** no Cisco IQ integration, **When** the administrator runs enable and chooses `us`, **Then** the registration targets exactly the US endpoint over Streamable HTTP with an `Authorization: Bearer` header resolved from a protected environment reference.
2. **Given** no region is supplied, **When** enable runs, **Then** it refuses and lists the three valid regions; it never infers a region from host location, locale, timezone or DNS.
3. **Given** an unknown region value, **When** enable runs, **Then** it refuses with the valid list and changes nothing.
4. **Given** the key is provided, **When** enable previews, applies, or reports status, **Then** the key and the resolved `Authorization` header never appear in any output, log or diagnostic.
5. **Given** the key is absent, **When** enable runs, **Then** it prompts without echo (or reads standard input), never accepts the key as an argument, and stores it only in the private (mode 0600) environment file.

---

### User Story 2 - Administrator operates the integration without an AI (Priority: P1)

An administrator can diagnose, rotate the credential, update (change region or re-sync), and disable the integration using maintained scripts alone.

**Why this priority**: The issue requires operability without depending on an AI operator.

**Independent Test**: Run each of diagnose, rotate, update and disable against a fixture home directory and a local mock endpoint; verify state changes and redaction.

**Acceptance Scenarios**:

1. **Given** an enabled integration, **When** diagnose runs, **Then** it reports region, endpoint, whether the key variable is set (never its value), env-file permissions, registration consistency, and a connectivity result, with every header redacted.
2. **Given** a 401/403 from the endpoint, **When** diagnose runs, **Then** it explains the likely causes (expired key, wrong region, service-account-owned key receiving no tools) without claiming a certain cause.
3. **Given** an enabled integration, **When** rotate runs with a new key on standard input, **Then** only the env variable changes, the registration is untouched, a private backup is kept, and the old key is never printed.
4. **Given** an enabled integration, **When** update runs with a different region, **Then** the endpoint changes atomically and the previous region is recorded in the output.
5. **Given** an enabled integration, **When** disable runs, **Then** the registration is removed, the credential is retained unless `--purge-credential` is given, and a re-run is a safe no-op.

---

### User Story 3 - Agent uses Cisco IQ safely alongside router diagnostics (Priority: P2)

A second- or third-line support engineer asks NetClaw about assets and product information, lifecycle and coverage, Cisco bug information, and to correlate findings with an existing support investigation. The agent follows a read-only, allowlisted policy and a skill describing these workflows.

**Why this priority**: This is the user value, but depends on US1 and must not overclaim.

**Independent Test**: Inspect the shipped policy and skill; verify the policy denies by default, lists only configurable read-class tools, and the skill states that field availability depends on Cisco IQ schemas, account data and key-owner permissions and that no use case is claimed validated.

**Acceptance Scenarios**:

1. **Given** the policy, **When** a tool not on the allowlist (or whose name or description indicates write/mutate behaviour) is requested, **Then** the policy denies it.
2. **Given** the skill, **When** a workflow needs a tool, **Then** it instructs discovery of the tool list at runtime rather than assuming a name.
3. **Given** a Cisco IQ result and an open investigation, **When** correlating, **Then** the skill instructs the agent to cite the source, flag missing fields, and not infer entitlement or coverage beyond what the data states.

---

### User Story 4 - Validate the integration without credentials (Priority: P2)

A maintainer or CI job validates the integration offline: configuration shape, region table, redaction, policy, scripts and catalog/documentation surfaces, with live checks strictly opt-in.

**Why this priority**: No live Cisco IQ key is available to CI; honest offline validation prevents silent regressions.

**Independent Test**: Run the offline suite with no network and no key; it passes and reports live checks as "needs live credentials", not as failures or passes.

**Acceptance Scenarios**:

1. **Given** no credentials, **When** the suite runs, **Then** all offline contracts pass and live checks are reported as not run.
2. **Given** a mutation that logs the header or hardcodes a key or region, **When** the suite runs, **Then** it fails.

### Edge Cases

- Key expired or revoked after enable: diagnose reports authentication failure; rotate restores service.
- Service-account-owned key: connection authenticates but exposes no tools; diagnose reports "zero tools" as a distinct finding.
- Key owner's permissions change: results change; documented, not detected.
- Region mismatch (account in another region): 401/403 or empty results; diagnose lists the other regions to try but never auto-switches.
- Environment file missing, world-readable, a symlink, or key containing newline/NUL: refused or repaired per `docs/ENVIRONMENT-FILES.md`.
- Key supplied in an environment variable at invocation: accepted only by variable name, never echoed.
- Re-running enable/disable repeatedly: idempotent.
- Cisco IQ publishes new tools: they stay denied until an administrator allowlists them.
- Network unreachable or TLS failure: diagnose reports transport failure separately from authentication failure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The integration MUST register Cisco IQ as a remote Streamable HTTP MCP server using NetClaw's existing native remote MCP configuration (URL plus headers), with no custom adapter, no local Cisco IQ server process and no credential service.
- **FR-002**: The administrator MUST select the region explicitly from `emea`, `us`, `apjc`; the system MUST NOT infer it, and MUST refuse missing or unknown values.
- **FR-003**: The endpoint table MUST be a single maintained source of truth used by the scripts, catalog, docs and tests.
- **FR-004**: Authentication MUST be exactly one `Authorization: Bearer <API_KEY>` header, with the key used directly; no OAuth or token exchange is implemented.
- **FR-005**: The key MUST be referenced from configuration by environment-variable name only; the value MUST live only in the private (0600) environment file and MUST NOT appear in committed files, examples, prompts, command-line arguments, previews, status, logs or diagnostics.
- **FR-006**: All output paths (previews, status, diagnose, errors, support bundles) MUST redact resolved `Authorization` values and any string equal to the key.
- **FR-007**: Provide administrator scripts, runnable without an AI, for enable, disable, diagnose, rotate and update, each idempotent, with a non-mutating preview mode.
- **FR-008**: Rotation MUST change only the credential value, keep a private backup, and preserve unrelated environment content.
- **FR-009**: Documentation MUST state that the key must be owned by a user principal, that service-account keys receive no tools, that keys expire, and that they inherit the owner's current permissions.
- **FR-010**: Provide an agent policy that is read-only, deny-by-default, and driven by a configurable allowlist; tool names are not hardcoded from guesswork and default allowlist entries, if any, MUST be marked unverified.
- **FR-011**: Provide a skill documenting workflows for assets/product information, lifecycle and coverage, bug information, and correlation with investigations, stating that field availability depends on Cisco IQ schemas, account data and key-owner permissions and that no use case is claimed validated.
- **FR-012**: Provide an offline validation suite that needs no network or credentials, declared in the contract-suite manifest, plus an opt-in live check that never prints secrets.
- **FR-013**: Provide a catalog entry, installer coverage, `.env.example` names, and README/SOUL/TOOLS documentation updates with correct counts per `docs/ADDING-AN-MCP.md`, and the integration MUST pass `scripts/reconcile-mcp.py` surfaces without new failures.
- **FR-014**: Diagnose MUST distinguish: not enabled, key unset, env-file permission problem, transport failure, authentication failure, zero tools, and success.
- **FR-015**: Verification notes MUST record what was tested offline and explicitly list what was not verified (live key, tool names/schemas, official guide contents).

### Key Entities

- **Region**: name (`emea`/`us`/`apjc`), endpoint URL; single source of truth.
- **Cisco IQ Registration**: the native remote MCP entry (URL, header template referencing an env variable name).
- **Credential**: API key value in the private env file; owner type (user principal) and expiry are external facts.
- **Tool Allowlist / Policy**: configurable set of permitted read-class tools plus deny rules.
- **Diagnostic Report**: redacted findings with one status from FR-014.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator can go from nothing to a registered integration for a chosen region in a single script invocation and under 2 minutes of hands-on time.
- **SC-002**: Across the full offline suite and all script outputs, zero occurrences of the test key or a resolved Authorization value.
- **SC-003**: 100% of the three regions are covered by offline tests; missing/unknown region always refuses with no state change.
- **SC-004**: Administrators can complete diagnose, rotate, update and disable without any AI assistance, verified by script-only tests.
- **SC-005**: The offline suite passes with no network and no credentials; live checks are reported separately and never counted as passing when not run.
- **SC-006**: The reconciliation tool shows no new failures attributable to this integration.

## Assumptions

- The contract in the Provenance section is accurate per the issue; deviations discovered later require a spec update, not silent script changes.
- Region names `emea`, `us`, `apjc` are administrator-facing aliases for the three listed endpoints.
- "Private env file" is the NetClaw runtime `.env` under `~/.openclaw/` (mode 0600), written via the existing safe writer; the key variable is `CISCO_IQ_API_KEY`, region variable `CISCO_IQ_REGION`.
- Cisco IQ is Cisco-hosted and read-oriented, but this feature does not assume that; the policy is read-only by NetClaw's own enforcement and allowlist.
- Tool names and schemas are discovered live or configured by the administrator; none are invented here.
- No live Cisco IQ key is available during implementation; live behaviour is unverified.
- Out of scope: OAuth flows, service-account key support, caching Cisco IQ data, write operations, hosting a Cisco IQ server.
