---
name: fortimanager-ops
description: "FortiManager operations — ADOM inventory, policy package review, object search, install preview, and compliance workflows. Use when auditing FortiGate firewall policies, reviewing ADOM policy packages, validating firewall path rules, or planning a FortiManager package install with rollback."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["FORTIMANAGER_MCP_CMD", "FORTIMANAGER_HOST", "FORTIMANAGER_API_TOKEN"] } } }
---

# FortiManager Operations

## MCP Server

- **Source**: `jmpijll/fortimanager-mcp`
- **Command**: `$FORTIMANAGER_MCP_CMD`
- **Transport**: stdio
- **Requires**: `FORTIMANAGER_HOST`, `FORTIMANAGER_API_TOKEN`
- **Mode**: read-only by default; install or policy writes require approved ServiceNow change control

## How to Call the MCP Tools

```bash
python3 $MCP_CALL "$FORTIMANAGER_MCP_CMD" TOOL_NAME '{"param":"value"}'
```

## Typical Tool Coverage

- ADOM and managed-device inventory
- Policy package lookup and rule search
- Address objects, services, and groups
- Install preview and revision history
- Policy package assignment and status

## When to Use

- FortiGate policy audit and path validation
- Multi-site firewall governance through ADOMs
- Change-review support before package install
- Revision comparison and rollback planning

## Workflow: Policy Package Audit

1. Identify the ADOM and target device or policy package.
2. Search relevant firewall and NAT rules.
3. Review objects and groups referenced by the rules.
4. Check revision history and install status.
5. If changes are needed, require an approved ServiceNow CR before install.

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| `servicenow-change-workflow` | Required before package installation or writes |
| `pyats-troubleshoot` | Correlate firewall policy results with device-side path and routing state |
| `slack-report-delivery` | Deliver policy audit summaries |

## Important Rules

- **Treat package install as production change execution**
- **Review ADOM and package scope carefully before acting**
- **Use revision history as rollback context**
