---
name: telemetry-ops
description: "Comprehensive network telemetry and event collection across multiple protocols."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Unified Telemetry Operations Skill

Comprehensive network telemetry and event collection across multiple protocols.

## Skill ID

`telemetry-ops`

## Description

This meta-skill provides a unified interface to all NetClaw telemetry receivers: syslog, SNMP traps, IPFIX/NetFlow, and gNMI streaming telemetry. It enables holistic network monitoring by aggregating events from multiple sources.

## When to Use

- Setting up comprehensive network monitoring across multiple telemetry types
- Correlating events across syslog, SNMP traps, and flow data
- Investigating network issues using multiple data sources
- Understanding the full picture of network health and behavior
- Onboarding a new device to NetClaw monitoring

## Component Skills

| Skill | MCP Server | Protocol | Default Port |
|-------|------------|----------|--------------|
| `syslog-receiver` | syslog-mcp | RFC 5424/3164 UDP | 514 |
| `snmptrap-receiver` | snmptrap-mcp | SNMPv1/v2c/v3 UDP | 162 |
| `ipfix-receiver` | ipfix-mcp | IPFIX/NetFlow UDP | 2055 |
| `gnmi-telemetry` | gnmi-mcp | gNMI gRPC | 57400 |

## Example Workflows

### Full Device Onboarding

```
1. Configure device to send syslog to NetClaw (UDP 514)
2. Configure SNMP traps to NetClaw (UDP 162)
3. Configure NetFlow/IPFIX export to NetClaw (UDP 2055)
4. Add device to gNMI targets for streaming telemetry
5. Start all receivers
6. Verify data is being received from each source
```

### Multi-Source Incident Investigation

```
1. Query syslog for error messages around incident time
2. Check SNMP traps for linkDown events
3. Analyze flows for traffic anomalies
4. Subscribe to gNMI telemetry for real-time interface state
```

### Network Health Dashboard

```
1. Use syslog_get_severity_counts for error distribution
2. Use snmptrap_get_counts for trap type breakdown
3. Use ipfix_top_talkers for bandwidth consumers
4. Use gnmi_get for current device state
```

## Sample Prompts

- "Start all telemetry receivers on their default ports"
- "What events have we received from 192.168.1.1 across all sources?"
- "Show me a summary of network health from all telemetry"
- "Configure the Catalyst 9300 for full telemetry to NetClaw"
- "Investigate the network issue at 3pm - check all telemetry sources"

## Cisco Catalyst 9300 Configuration

### Syslog

```
logging host 10.0.0.1 transport udp port 514
logging trap informational
logging source-interface Loopback0
```

### SNMP Traps

```
snmp-server enable traps
snmp-server host 10.0.0.1 version 2c public
```

### NetFlow/IPFIX

```
flow exporter NETCLAW
 destination 10.0.0.1
 transport udp 2055
 export-protocol ipfix
```

### gNMI

```
netconf-yang
gnmi-yang
gnmi-yang secure-server
```

## Remote Access (UDP Tunneling)

Since ngrok doesn't support UDP, use these alternatives:

| Service | UDP Support | Best For |
|---------|-------------|----------|
| Pinggy | Yes | Quick tunnel setup |
| Tailscale | Yes | Persistent mesh VPN |
| LocalXpose | Yes | Full protocol support |

## Architecture

```
                    ┌─────────────────┐
                    │ Cisco Cat 9300  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │         │          │          │         │
        ▼         ▼          ▼          ▼         │
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ Syslog  │ │  SNMP   │ │  IPFIX  │ │  gNMI   │
   │ UDP 514 │ │ UDP 162 │ │UDP 2055 │ │TCP 57400│
   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
        │           │           │           │
        ▼           ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │syslog-  │ │snmptrap-│ │ ipfix-  │ │ gnmi-   │
   │  mcp    │ │   mcp   │ │   mcp   │ │   mcp   │
   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
        │           │           │           │
        └───────────┴─────┬─────┴───────────┘
                          │
                    ┌─────┴─────┐
                    │  NetClaw  │
                    │   Agent   │
                    └───────────┘
```

## Limitations

- All receivers use in-memory storage (data lost on restart)
- No cross-source correlation built-in (done by agent)
- Each receiver runs independently
- UDP tunneling required for remote testing

## Related Documentation

- `/mcp-servers/syslog-mcp/README.md`
- `/mcp-servers/snmptrap-mcp/README.md`
- `/mcp-servers/ipfix-mcp/README.md`
- `/mcp-servers/gnmi-mcp/README.md`

## Failure Behavior

- On a tool error (timeout, unreachable host, malformed response), report the failure and its error message directly to the user rather than fabricating or guessing at results.
- All tools here are read-only, so a failed call has no side effects — it's safe to retry once after confirming connectivity, but don't loop indefinitely on repeated failures.
