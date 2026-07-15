---
name: ipfix-receiver
description: "Receive and query IPFIX and NetFlow flow records from network devices via UDP."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# IPFIX/NetFlow Receiver Skill

Receive and query IPFIX and NetFlow flow records from network devices via UDP.

## Skill ID

`ipfix-receiver`

## Description

This skill enables NetClaw to receive IPFIX (RFC 7011) and NetFlow (v5/v9) flow records from network devices and query the collected data. It provides visibility into network traffic patterns, bandwidth usage, and communication flows.

## When to Use

- Monitoring network traffic volumes and patterns
- Identifying top bandwidth consumers (top talkers)
- Investigating network communication between hosts
- Analyzing protocol distribution across the network
- Troubleshooting connectivity by examining flow data
- Capacity planning based on traffic trends

## Required MCP Server

`ipfix-mcp`

## Available Tools

| Tool | Purpose |
|------|---------|
| `ipfix_start_receiver` | Start listening for flow exports |
| `ipfix_stop_receiver` | Stop the receiver |
| `ipfix_get_status` | Check receiver status and statistics |
| `ipfix_query_flows` | Search flows with filters |
| `ipfix_get_flow` | Get full details of a specific flow |
| `ipfix_top_talkers` | Identify highest bandwidth consumers |
| `ipfix_get_templates` | List cached flow templates |

## Example Workflows

### Start Monitoring

```
1. Use ipfix_start_receiver with port 2055
2. Configure network devices to export flows to this port
3. Use ipfix_get_status to verify flows are being received
```

### Identify Bandwidth Hogs

```
1. Use ipfix_top_talkers to see highest traffic sources/destinations
2. Filter by time range if investigating specific period
3. Use ipfix_query_flows with src_ip to drill into specific host
```

### Investigate Host Communication

```
1. Use ipfix_query_flows with src_ip or dst_ip filter
2. Add protocol filter (6=TCP, 17=UDP) for specific traffic
3. Use min_bytes filter to focus on significant flows
```

### Protocol Analysis

```
1. Use ipfix_top_talkers to see protocol breakdown
2. Query specific protocols with ipfix_query_flows
3. Analyze port usage patterns
```

## Sample Prompts

- "Start the flow receiver on port 2055"
- "Show me the top 10 bandwidth consumers"
- "Find all TCP flows from 192.168.1.100"
- "What's the total traffic volume in the last hour?"
- "Show me flows to port 443 with more than 1MB"
- "What templates have been received from exporters?"

## Configuration

The ipfix-mcp server is configured via environment variables:

- `IPFIX_PORT`: UDP listening port (default: 2055)
- `IPFIX_BIND_ADDRESS`: Bind address (default: 0.0.0.0)
- `IPFIX_RETENTION_HOURS`: Flow retention (default: 24)
- `IPFIX_RATE_LIMIT`: Max flows/second (default: 10000)
- `IPFIX_DEDUP_WINDOW`: Dedup window in seconds (default: 5)

## Limitations

- In-memory storage only (data lost on restart)
- Template caching expires after 30 minutes
- Single instance per port
- No flow aggregation or rollup
- UDP only (no SCTP support)
- GAIT logging sampled at 1% to reduce overhead

## Related Skills

- `syslog-receiver` - Syslog message collection
- `snmptrap-receiver` - SNMP trap collection
- `gnmi-telemetry` - Streaming telemetry
