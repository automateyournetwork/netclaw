---
name: datadog-incidents
description: "Manage incidents in Datadog Incident Management."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Datadog Incidents Skill

Manage incidents in Datadog Incident Management.

## Tools

| Tool | Description |
|------|-------------|
| `list_incidents` | List incidents with optional filters |
| `get_incident` | Get detailed incident information |
| `create_incident` | Create a new incident (read-only by default) |
| `update_incident` | Update incident status or fields (read-only by default) |

## Example Queries

```
List all active incidents
→ list_incidents(status="active")

Get details of a specific incident
→ get_incident(incident_id="INC-12345")

List recent network-related incidents
→ list_incidents(tags=["service:network"], time_range="7d")

List SEV1 incidents from the past month
→ list_incidents(severity="SEV-1", time_range="30d")
```

## Workflows

### Incident Investigation
1. List active incidents: `list_incidents(status="active")`
2. Get incident details: `get_incident(incident_id="INC-12345")`
3. Review timeline and related monitors
4. Check correlated metrics and logs
5. Document findings in incident

### Network Outage Tracking
1. Search network incidents: `list_incidents(tags=["service:network"])`
2. Filter by impact: `list_incidents(severity="SEV-1,SEV-2")`
3. Review affected services and dependencies
4. Track MTTR and resolution patterns

### Post-Incident Review
1. Get incident timeline: `get_incident(incident_id="INC-12345")`
2. Extract key events and decisions
3. Identify detection and response gaps
4. Document lessons learned

## Prerequisites

- `DD_API_KEY` Datadog API key
- `DD_APP_KEY` Datadog application key
- `DD_SITE` Datadog site (optional, defaults to datadoghq.com)

## Server

This skill uses the `datadog-mcp` server via remote MCP transport.

## Notes

- Create and update operations may require additional permissions
- NetClaw operates in read-only mode by default for safety
- Incident creation should follow your organization's incident process
