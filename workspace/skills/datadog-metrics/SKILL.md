---
name: datadog-metrics
description: "Query metrics and explore dashboards in Datadog."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Datadog Metrics Skill

Query metrics and explore dashboards in Datadog.

## Tools

| Tool | Description |
|------|-------------|
| `query_metrics` | Execute metric queries with aggregations |
| `list_metrics` | List available metrics matching a pattern |
| `get_metric_metadata` | Get metadata for a specific metric |
| `list_dashboards` | List all available dashboards |
| `get_dashboard` | Get dashboard definition and widgets |

## Example Queries

```
Query CPU utilization for network devices
→ query_metrics(query="avg:system.cpu.user{role:network_device} by {host}", time_range="1h")

Get interface traffic metrics
→ query_metrics(query="sum:network.bytes_rcvd{*} by {interface}", time_range="4h")

List all network-related metrics
→ list_metrics(pattern="network.*")

Get a specific dashboard
→ get_dashboard(dashboard_id="abc-def-123")
```

## Workflows

### Network Performance Monitoring
1. Query interface utilization: `query_metrics(query="avg:network.bytes_sent{*} by {host,interface}")`
2. Check error rates: `query_metrics(query="sum:network.errors{*} by {host}")`
3. Monitor latency percentiles: `query_metrics(query="p99:network.latency{*}")`
4. Compare against SLA thresholds

### Infrastructure Health Assessment
1. List all infrastructure metrics: `list_metrics(pattern="system.*")`
2. Query CPU/memory across fleet: `query_metrics(query="avg:system.cpu.user{*} by {availability_zone}")`
3. Identify outliers and degradation
4. Check dashboard for historical trends

### Capacity Planning
1. Query peak utilization: `query_metrics(query="max:system.disk.used{*} by {host}", time_range="30d")`
2. Calculate growth rate
3. Forecast exhaustion dates
4. Generate capacity report

## Prerequisites

- `DD_API_KEY` Datadog API key
- `DD_APP_KEY` Datadog application key
- `DD_SITE` Datadog site (optional, defaults to datadoghq.com)

## Server

This skill uses the `datadog-mcp` server via remote MCP transport.
