---
name: cisco-iq
description: Cisco IQ (official remote MCP, read-only) for support investigations — asset and product information, lifecycle and coverage, Cisco bug information, and correlating Cisco IQ findings with an existing investigation. Use when a second- or third-line engineer needs Cisco IQ data next to router diagnostics. Discovers tools at runtime; field availability depends on Cisco IQ schemas, account data and key-owner permissions.
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      - cisco-iq-mcp
---

# Cisco IQ

## Status and limits (read first)

- Cisco IQ is Cisco's official remote MCP server (Streamable HTTP, `Authorization: Bearer` API key). Registered by an administrator with `scripts/cisco-iq-enable.sh enable --region <emea|us|apjc>`; the region is chosen by the administrator and never inferred.
- The key must be owned by a **user principal**. A service-account-owned key receives **no tools**. Keys expire and inherit the key owner's current permissions.
- **Not validated**: NetClaw has no live Cisco IQ validation of any workflow below. They describe how to *attempt* these tasks. What each tool returns depends on Cisco IQ's published schemas, the account's data and the key owner's permissions. Treat missing fields as "not available", never as "not covered" or "no bugs".
- Do not invent tool names or arguments. Cisco IQ tool names are not published to this project.

## Policy (read-only)

1. Use only tools on the allowlist in `config/cisco-iq-policy.json` (deny by default). Run `scripts/cisco-iq-enable.sh policy-check --live` (administrator) to see which advertised tools are allowed, denied or unlisted.
2. Never call a tool that creates, updates, deletes, executes, submits or otherwise changes state, even if it is advertised. Refuse and tell the user.
3. Never print, request or store an API key or Authorization header. If a key problem is suspected, direct the user to `scripts/cisco-iq-enable.sh diagnose` and `rotate`.
4. Without DefenseClaw this policy is enforced by these instructions, not by a technical gate.

## Discovery first

At the start of a task, list the server's tools (MCP `tools/list`) and read each tool's description and input schema. Pick tools by what they declare, ask the user for any identifier the schema requires, and do not guess identifiers. If no tools are listed, say so: the likely causes are a service-account-owned key, insufficient owner permissions, or the wrong region. Suggest `scripts/cisco-iq-enable.sh diagnose --live`.

## Workflows

Each workflow maps a goal to a capability category. Select the matching advertised tool, if any.

### 1. Identify assets and product information
Given a serial number, product ID, hostname or device record from an investigation, look it up with the asset/inventory-class tool. Report product family, software/hardware identifiers and anything the tool returns, with the tool name as the source. If nothing is returned, say the asset was not found in the account's Cisco IQ data (it may simply not be onboarded).

### 2. Lifecycle and coverage
Use the lifecycle/contract/coverage-class tool for the same asset. Report end-of-life milestones and coverage status exactly as stated, with dates. Do not infer entitlement, renewal need or support eligibility beyond the returned fields.

### 3. Bug information
Use the bug/advisory-class tool with the product and software version from the device (for example from `show version` collected with the router diagnostic skills). Report bug IDs, severity and fixed-in versions as returned. A lack of results is not proof that no bug applies.

### 4. Correlate with an existing investigation
1. Gather what is already known (symptoms, device, version, timeline) from the investigation.
2. Collect the relevant Cisco IQ facts using workflows 1-3.
3. Present a short table: finding, source tool, evidence, and relation to the symptoms (supports, contradicts, unrelated, unknown).
4. State confidence honestly, list fields that were unavailable, and recommend next read-only checks. Any remediation goes through the normal change process (ITSM gate), not through Cisco IQ.

## Output rules

- Cite the Cisco IQ tool for every claim.
- Distinguish "returned by Cisco IQ" from "inferred by NetClaw".
- Redact identifiers the user marked sensitive when sharing externally.

## References

- Administrator guide: `docs/CISCO-IQ.md`
- Official guide: https://iq.cisco.com/apidocs/mcp-server (could not be retrieved by automation during implementation; the contract was taken from issue #346)
- Endpoints: EMEA https://eu-central-1.iq.cisco.com/mcp, US https://us-west-2.iq.cisco.com/mcp, APJC https://ap-southeast-2.iq.cisco.com/mcp
