---
name: paloalto-panorama
description: "Palo Alto Panorama operations — device groups, templates, security policy search, NAT review, commit status, and audit workflows. Use when searching Palo Alto firewall rules, checking if traffic is allowed through Panorama, reviewing NAT policies, or auditing device groups."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PANOS_MCP_CMD", "PANOS_HOSTNAME", "PANOS_API_KEY"] } } }
---

# Palo Alto Panorama

## MCP Server

- **Source**: `iflow-mcp-cdot65-palo-alto-mcp` / `palo-alto-mcp`
- **Command**: `$PANOS_MCP_CMD`
- **Transport**: stdio
- **Requires**: `PANOS_HOSTNAME`, `PANOS_API_KEY`
- **Preferred use**: read-only audit and validation; gate policy writes behind ServiceNow CRs

## How to Call the MCP Tools

```bash
python3 $MCP_CALL "$PANOS_MCP_CMD" TOOL_NAME '{"param":"value"}'
```

## Typical Tool Coverage

- Device groups and managed firewalls
- Templates and template stacks
- Security policy rule search
- NAT policy review
- Address objects, services, tags, and zones
- Commit queues and recent job status

## When to Use

- “Can host A reach host B through Palo Alto?”
- Policy hygiene reviews and duplicate-rule cleanup
- Pre-change dependency analysis on Panorama-managed estates
- Commit validation after approved firewall changes

## Workflow: Rule Impact Analysis

1. Resolve the relevant device group and target firewalls.
2. Search security and NAT policies using source, destination, application, and service.
3. Review address objects, dynamic tags, and zones tied to the traffic path.
4. If a policy change is required, create and approve a ServiceNow CR before any write action.
5. Verify commit status and post-change traffic behavior.

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| `servicenow-change-workflow` | Required for Panorama policy writes and commits |
| `slack-network-alerts` | Deliver firewall findings and blocked-path summaries |
| `te-path-analysis` | Correlate blocked or impaired paths with external reachability |
| `netbox-reconcile` | Map firewall objects to source-of-truth IP ownership |

## Important Rules

- **Never push firewall policy without approved change control**
- **Always check Panorama commit status after a write**
- **Policy hit counts and logs should validate the outcome**

## Failure Behavior

- If a tool call fails with an authentication or connection error, check that `PANOS_API_KEY`, `PANOS_HOSTNAME`, `PANOS_MCP_CMD` are set and valid before assuming a data or device problem.
- On a tool error (timeout, unreachable host, malformed response), report the failure and its error message directly to the user rather than fabricating or guessing at results.
- All tools here are read-only, so a failed call has no side effects — it's safe to retry once after confirming connectivity, but don't loop indefinitely on repeated failures.
