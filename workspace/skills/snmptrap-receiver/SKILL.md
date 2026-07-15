---
name: snmptrap-receiver
description: "Receive and query SNMP traps from network devices via UDP."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# SNMP Trap Receiver Skill

Receive and query SNMP traps from network devices via UDP.

## Skill ID

`snmptrap-receiver`

## Description

This skill enables NetClaw to receive SNMP traps from network devices (routers, switches, firewalls) and query the collected data. It supports SNMPv1, SNMPv2c, and SNMPv3 trap formats.

## When to Use

- Monitoring network device events (link up/down, authentication failures)
- Investigating incidents by querying historical trap data
- Aggregating traps from multiple network devices
- Filtering traps by type, source, or SNMP version
- Analyzing trap patterns across the network

## Required MCP Server

`snmptrap-mcp`

## Available Tools

| Tool | Purpose |
|------|---------|
| `snmptrap_start_receiver` | Start listening for SNMP traps |
| `snmptrap_stop_receiver` | Stop the receiver |
| `snmptrap_get_status` | Check receiver status and statistics |
| `snmptrap_query` | Search traps with filters |
| `snmptrap_get_trap` | Get full details of a specific trap |
| `snmptrap_get_counts` | Get trap counts by type and source |

## Example Workflows

### Start Monitoring

```
1. Use snmptrap_start_receiver with port 10162
2. Configure network devices to send traps to this port
3. Use snmptrap_get_status to verify traps are being received
```

### Investigate Link Issues

```
1. Use snmptrap_query with trap_oid_prefix "1.3.6.1.6.3.1.1.5" for standard traps
2. Filter by source_ip to focus on specific device
3. Use snmptrap_get_trap for full variable binding details
```

### Daily Summary

```
1. Use snmptrap_get_counts to see trap distribution
2. Focus on linkDown, authenticationFailure counts
3. Query high-frequency trap sources for details
```

## Sample Prompts

- "Start the SNMP trap receiver on port 10162"
- "Show me all linkDown traps from the last hour"
- "How many traps have we received by type?"
- "Find all SNMP traps from 192.168.1.1"
- "What's the trap receiver status?"
- "Query SNMPv3 traps received today"

## Configuration

The snmptrap-mcp server is configured via environment variables:

- `SNMPTRAP_PORT`: UDP listening port (default: 162)
- `SNMPTRAP_BIND_ADDRESS`: Bind address (default: 0.0.0.0)
- `SNMPTRAP_RETENTION_HOURS`: Trap retention (default: 24)
- `SNMPTRAP_RATE_LIMIT`: Max traps/second (default: 1000)
- `SNMPTRAP_DEDUP_WINDOW`: Dedup window in seconds (default: 5)

## Limitations

- In-memory storage only (data lost on restart)
- SNMPv3 requires USM user configuration for full parsing
- Single instance per port
- No MIB compilation (OIDs shown numerically)
- UDP only (no TCP/TLS support)

## Related Skills

- `syslog-receiver` - Syslog message collection
- `ipfix-receiver` - Flow data collection
- `gnmi-telemetry` - Streaming telemetry
