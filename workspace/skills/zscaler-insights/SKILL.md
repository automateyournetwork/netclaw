---
name: zscaler-insights
description: "Access analytics, threat intelligence, and security event data."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Zscaler Insights Skill

Access analytics, threat intelligence, and security event data.

## Tools

| Tool | Description |
|------|-------------|
| `get_threat_intelligence` | Get threat intelligence data |
| `list_security_events` | List security events |
| `get_security_event` | Get security event details |
| `list_blocked_threats` | List blocked threats |
| `get_blocked_threat` | Get blocked threat details |
| `get_traffic_analytics` | Get traffic analytics |
| `list_anomalies` | List detected anomalies |
| `get_anomaly` | Get anomaly details |
| `list_sandbox_reports` | List sandbox analysis reports |
| `get_sandbox_report` | Get sandbox report details |
| `get_risk_score` | Get organizational risk score |
| `list_top_threats` | List top threats by category |
| `get_compliance_status` | Get compliance posture |

## Example Queries

```
Show security events from the last hour

What threats were blocked today?

Get threat intelligence for IP 1.2.3.4

Show traffic anomalies detected this week

List sandbox reports for suspicious files
```

## Prerequisites

- `ZSCALER_CLIENT_ID` OneAPI client ID
- `ZSCALER_CLIENT_SECRET` OneAPI client secret
- `ZSCALER_CUSTOMER_ID` Customer/tenant ID
- `ZSCALER_VANITY_DOMAIN` Vanity domain
- `ZSCALER_MCP_SERVICES` must include `zinsights`

## Server

This skill uses the `zscaler-mcp` server which connects to Z-Insights via OneAPI.
