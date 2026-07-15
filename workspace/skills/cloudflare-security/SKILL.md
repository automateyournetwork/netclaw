---
name: cloudflare-security
description: "Monitor Cloudflare WAF, firewall events, audit logs, and threat intelligence."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Cloudflare Security Skill

Monitor Cloudflare WAF, firewall events, audit logs, and threat intelligence.

## Tools

| Tool | Description |
|------|-------------|
| `list_firewall_rules` | List WAF and firewall rules |
| `get_firewall_events` | Get firewall event logs |
| `list_audit_logs` | List account audit log entries |
| `get_audit_log` | Get details for an audit log entry |
| `list_security_events` | List security events and threats |
| `get_threat_score` | Get threat score for an IP address |

## Example Queries

```
List all firewall rules for example.com

Show firewall events from the last 24 hours

Show Cloudflare audit logs for today

What is the threat score for IP 1.2.3.4?
```

## Prerequisites

- `CLOUDFLARE_API_TOKEN` with Firewall:Read, Audit Logs:Read scopes
- `CLOUDFLARE_ACCOUNT_ID` from dashboard

## Servers

This skill uses:
- `cloudflare-observability` at `observability.mcp.cloudflare.com`
- `cloudflare-audit-logs` at `audit-logs.mcp.cloudflare.com`
- `cloudflare-radar` at `radar.mcp.cloudflare.com` (for threat intel)
