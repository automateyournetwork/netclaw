---
name: syslog-receiver
description: "Receive and query syslog messages from network devices via UDP."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Syslog Receiver Skill

Receive and query syslog messages from network devices via UDP.

## Skill ID

`syslog-receiver`

## Description

This skill enables NetClaw to receive syslog messages from network devices (routers, switches, firewalls) and query the collected data. It supports both RFC 5424 (modern) and RFC 3164 (BSD/Cisco) syslog formats.

## When to Use

- Monitoring network device events in real-time
- Investigating incidents by querying historical syslog data
- Aggregating logs from multiple network devices
- Filtering messages by severity, facility, hostname, or content
- Analyzing error patterns across the network

## Required MCP Server

`syslog-mcp`

## Available Tools

| Tool | Purpose |
|------|---------|
| `syslog_start_receiver` | Start listening for syslog messages |
| `syslog_stop_receiver` | Stop the receiver |
| `syslog_get_status` | Check receiver status and statistics |
| `syslog_query` | Search messages with filters |
| `syslog_get_message` | Get full details of a specific message |
| `syslog_get_severity_counts` | Get message counts by severity |

## Example Workflows

### Start Monitoring

```
1. Use syslog_start_receiver with port 10514
2. Configure network devices to send syslog to this port
3. Use syslog_get_status to verify messages are being received
```

### Investigate Errors

```
1. Use syslog_query with severity_max=3 to find ERROR and above
2. Filter by hostname or source_ip if investigating specific device
3. Use message_contains to search for specific keywords
4. Use syslog_get_message for full details of interesting entries
```

### Daily Summary

```
1. Use syslog_get_severity_counts to see distribution
2. Focus on CRITICAL, ERROR, WARNING counts
3. Query high-severity messages for details
```

## Sample Prompts

- "Start the syslog receiver on port 10514"
- "Show me all error messages from the last hour"
- "How many critical alerts have we received today?"
- "Find all syslog messages containing 'interface down'"
- "What's the syslog receiver status?"
- "Query syslog for messages from 192.168.1.1"

## Configuration

The syslog-mcp server is configured via environment variables:

- `SYSLOG_PORT`: UDP listening port (default: 514)
- `SYSLOG_BIND_ADDRESS`: Bind address (default: 0.0.0.0)
- `SYSLOG_RETENTION_HOURS`: Message retention (default: 24)
- `SYSLOG_RATE_LIMIT`: Max messages/second (default: 1000)
- `SYSLOG_DEDUP_WINDOW`: Dedup window in seconds (default: 5)

## Limitations

- In-memory storage only (data lost on restart)
- Single instance per port
- No persistent storage or export
- UDP only (no TCP syslog support)

## Related Skills

- `snmptrap-receiver` - SNMP trap collection
- `ipfix-receiver` - Flow data collection
- `gnmi-telemetry` - Streaming telemetry
