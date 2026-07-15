---
name: datadog-apm
description: "Analyze distributed traces and service performance in Datadog APM."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Datadog APM Skill

Analyze distributed traces and service performance in Datadog APM.

## Tools

| Tool | Description |
|------|-------------|
| `search_traces` | Search traces with query syntax and filters |
| `get_trace_details` | Get detailed span information for a trace |
| `list_services` | List all instrumented services |
| `get_service_summary` | Get service health and performance summary |

## Example Queries

```
Search for slow traces in the network service
→ search_traces(query="service:network-api @duration:>1s", time_range="1h")

Find error traces
→ search_traces(query="status:error", time_range="30m")

Get details of a specific trace
→ get_trace_details(trace_id="abc123def456")

List all services
→ list_services()

Get service performance summary
→ get_service_summary(service_name="network-api")
```

## Workflows

### Latency Analysis
1. Search slow traces: `search_traces(query="@duration:>500ms")`
2. Identify common patterns (resource, operation)
3. Drill into trace waterfall: `get_trace_details(trace_id="...")`
4. Find bottleneck spans
5. Compare with baseline performance

### Error Investigation
1. Search error traces: `search_traces(query="status:error service:network")`
2. Group by error type and root cause
3. Review span-level errors in trace details
4. Correlate with recent deployments or changes

### Service Health Review
1. List all services: `list_services()`
2. Get summary for critical services: `get_service_summary(service_name="...")`
3. Check error rate, latency percentiles, throughput
4. Identify degraded or unhealthy services
5. Review service dependencies map

### Root Cause Analysis
1. Start from incident or alert
2. Find related traces: `search_traces(query="trace_id:abc123")`
3. Walk span tree to identify failure point
4. Check upstream/downstream service health
5. Correlate with infrastructure metrics

## Prerequisites

- `DD_API_KEY` Datadog API key
- `DD_APP_KEY` Datadog application key
- `DD_SITE` Datadog site (optional, defaults to datadoghq.com)

## Server

This skill uses the `datadog-mcp` server via remote MCP transport.

## Notes

- APM requires instrumented services sending traces to Datadog
- Trace retention depends on your Datadog plan
- Large trace searches may be paginated
