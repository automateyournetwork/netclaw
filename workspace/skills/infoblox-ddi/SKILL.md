---
name: infoblox-ddi
description: "Infoblox DDI operations — DNS zones/records, DHCP scopes and leases, IPAM networks and address utilization. Use when checking DNS records, validating IPAM address allocation, investigating DHCP scope exhaustion, verifying reverse DNS for network devices, or reconciling Infoblox with NetBox or Nautobot."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["INFOBLOX_MCP_CMD", "INFOBLOX_URL", "INFOBLOX_API_KEY"] } } }
---

# Infoblox DDI

## MCP Server

- **Source**: `infoblox-ddi-mcp` (PyPI)
- **Command**: `$INFOBLOX_MCP_CMD`
- **Transport**: stdio
- **Requires**: `INFOBLOX_URL`, `INFOBLOX_API_KEY`
- **Recommended scope**: read-only for audit workflows; gate write operations behind ServiceNow CRs

## How to Call the MCP Tools

```bash
python3 $MCP_CALL "$INFOBLOX_MCP_CMD" TOOL_NAME '{"param":"value"}'
```

## Typical Tool Coverage

- Network and prefix inventory
- Fixed addresses and host records
- A, AAAA, CNAME, PTR, TXT records
- DHCP ranges, reservations, and lease lookup
- IP utilization and next-available-address queries

## When to Use

- IPAM source-of-truth validation before assigning addresses
- DNS cutover and record verification during change windows
- DHCP scope exhaustion checks
- Reverse-DNS validation for network devices and services
- Reconciliation between NetBox/Nautobot intent and Infoblox reality

## Workflow: DNS Change Validation

1. Query the target zone and existing records.
2. Check for conflicting A, AAAA, CNAME, and PTR records.
3. Confirm the target IP is allocated correctly in IPAM.
4. If the change is a write operation, require a ServiceNow CR first.
5. Verify forward and reverse records after implementation.

## Workflow: DHCP Scope Investigation

1. Query the affected network or scope.
2. Review lease utilization and remaining free addresses.
3. Check reservations and exclusions for collisions.
4. Correlate the client or IP with Catalyst Center, ISE, or pyATS data if needed.

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| `netbox-reconcile` | Validate address intent against Infoblox allocations |
| `nautobot-sot` | Cross-check prefixes and IP ownership |
| `servicenow-change-workflow` | Gate DDI write actions behind approved changes |
| `pyats-config-mgmt` | Confirm address plan before device configuration |

## Important Rules

- **Do not modify DNS/DHCP/IPAM without approved change control**
- **Always verify both forward and reverse DNS after writes**
- **Treat DDI as production control-plane infrastructure**

## Failure Behavior

- If a tool call fails with an authentication or connection error, check that `INFOBLOX_API_KEY`, `INFOBLOX_MCP_CMD`, `INFOBLOX_URL` are set and valid before assuming a data or device problem.
- On a tool error (timeout, unreachable host, malformed response), report the failure and its error message directly to the user rather than fabricating or guessing at results.
- All tools here are read-only, so a failed call has no side effects — it's safe to retry once after confirming connectivity, but don't loop indefinitely on repeated failures.
