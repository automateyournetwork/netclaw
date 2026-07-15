---
name: datadog-logs
description: "Search and analyze logs in Datadog Log Management."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Datadog Logs Skill

Search and analyze logs in Datadog Log Management.

## Tools

| Tool | Description |
|------|-------------|
| `search_logs` | Search logs with query syntax, time range, and filters |
| `get_log_details` | Get detailed information about a specific log entry |
| `list_log_indexes` | List all available log indexes |
| `get_log_pipeline` | Get log pipeline configuration for processing |

## Example Queries

```
Search for error logs in the network service
→ search_logs(query="service:network status:error", time_range="1h")

Find all logs from a specific host
→ search_logs(query="host:router-core-01", time_range="15m")

Get logs with a specific trace ID
→ search_logs(query="trace_id:abc123", time_range="1d")

List all log indexes
→ list_log_indexes()
```

## Workflows

### Security Event Hunting
1. Search for authentication failures: `search_logs(query="@auth.status:failed")`
2. Correlate by source IP: `search_logs(query="@network.client.ip:10.0.0.1")`
3. Check for privilege escalation: `search_logs(query="@action:sudo OR @action:su")`
4. Review timeline and patterns

### Network Log Correlation
1. Search interface events: `search_logs(query="service:network @interface.status:down")`
2. Correlate with routing changes: `search_logs(query="@event.type:bgp_state_change")`
3. Check for cascading failures across regions
4. Build incident timeline

### Syslog Analysis
1. Search by facility: `search_logs(query="@syslog.facility:local0")`
2. Filter by severity: `search_logs(query="@syslog.severity:<4")` (warning and above)
3. Aggregate by host and time window
4. Identify anomalous patterns

## Prerequisites

- `DD_API_KEY` Datadog API key
- `DD_APP_KEY` Datadog application key
- `DD_SITE` Datadog site (optional, defaults to datadoghq.com)

## Server

This skill uses the `datadog-mcp` server via remote MCP transport.
