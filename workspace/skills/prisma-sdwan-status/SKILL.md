---
name: prisma-sdwan-status
description: "Monitor Prisma SD-WAN element health, software versions, events, and alarms"
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["PAN_CLIENT_ID", "PAN_CLIENT_SECRET", "PAN_TSG_ID"]
---

# Prisma SD-WAN Health and Status Monitoring

Monitor the health and operational status of your Palo Alto Networks Prisma SD-WAN fabric. Check element CPU/memory, software versions, operational events, and active alarms.

## When to Use

- Checking if ION devices are online and healthy
- Reviewing CPU and memory utilization across elements
- Identifying devices with pending software upgrades
- Viewing recent operational events (state changes, warnings)
- Investigating active alarms (critical, major, minor)
- Troubleshooting connectivity issues

## MCP Server

- **Server**: `prisma-sdwan-mcp` (community MCP from iamdheerajdubey)
- **Command**: `python3 -u mcp-servers/prisma-sdwan-mcp/src/prisma_sdwan_mcp/server.py` (stdio transport)
- **Auth**: OAuth2 via `PAN_CLIENT_ID`, `PAN_CLIENT_SECRET`, `PAN_TSG_ID`
- **Region**: `PAN_REGION` (americas or europe, default: americas)

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `get_element_status` | element_id? | Get health metrics (CPU, memory, uptime, state) |
| `get_software_status` | element_id? | Check software versions and upgrade availability |
| `get_events` | limit? | List recent operational events (default: 20) |
| `get_alarms` | limit? | List active alarms with severity (default: 20) |

## Workflow Examples

### Health Check

```bash
# Check all element health
"What's the health status of all SD-WAN elements?"

# Check specific element
"Is hq-router-1 healthy?"

# Find high CPU elements
"Which ION devices have high CPU usage?"

# Check memory utilization
"Show me memory usage across all elements"
```

### Software Management

```bash
# Check software versions
"What software versions are running on my ION devices?"

# Find upgrade candidates
"Which elements have software upgrades available?"

# Check for version consistency
"Are all elements running the same software version?"
```

### Event Monitoring

```bash
# View recent events
"Show me the last 20 SD-WAN events"

# Check for state changes
"Have any elements gone offline recently?"

# Filter by severity
"Show me all warning and error events"
```

### Alarm Investigation

```bash
# List active alarms
"Are there any active SD-WAN alarms?"

# Check critical alarms
"Show me all critical alarms"

# Check specific element alarms
"What alarms are active on the Headquarters site?"
```

## Integration with Other Skills

- **prisma-sdwan-topology**: Identify element IDs before checking status
- **prisma-sdwan-config**: Investigate interface issues flagged by alarms
- **servicenow-change-workflow**: Create incident tickets for critical alarms

## Response Examples

### Element Status Response

```json
{
  "element_status": [
    {
      "element_id": "def456",
      "element_name": "hq-router-1",
      "state": "online",
      "cpu_usage": 15.2,
      "memory_usage": 42.8,
      "uptime_seconds": 864000,
      "last_seen": "2026-04-03T12:00:00Z"
    }
  ]
}
```

### Alarms Response

```json
{
  "alarms": [
    {
      "id": "alm456",
      "severity": "critical",
      "type": "interface_down",
      "message": "WAN interface 1 is down on hq-router-1",
      "timestamp": "2026-04-03T10:30:00Z",
      "acknowledged": false
    }
  ],
  "total_count": 3
}
```

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| AUTH_FAILED | OAuth2 authentication failed | Verify PAN_CLIENT_ID, PAN_CLIENT_SECRET, PAN_TSG_ID |
| NOT_FOUND | Element not found | Check element_id via prisma-sdwan-topology |
| RATE_LIMITED | API rate limit exceeded | Wait and retry; reduce request frequency |

## Notes

- Read-only operations - no ServiceNow CR gating required
- Events are returned in reverse chronological order
- Alarms include severity: critical, major, minor, warning
- All operations logged to GAIT audit trail
