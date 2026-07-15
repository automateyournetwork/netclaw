---
name: zscaler-zdx
description: "Monitor digital experience scores, user performance, and application health."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Zscaler Digital Experience (ZDX) Skill

Monitor digital experience scores, user performance, and application health.

## Tools

| Tool | Description |
|------|-------------|
| `list_zdx_applications` | List monitored applications |
| `get_zdx_application` | Get application health and metrics |
| `list_zdx_users` | List users with experience data |
| `get_zdx_user` | Get user experience details |
| `list_zdx_devices` | List devices with metrics |
| `get_zdx_device` | Get device health details |
| `get_zdx_score_trends` | Get experience score trends over time |
| `list_zdx_events` | List experience events |
| `get_zdx_event` | Get event details |
| `list_zdx_alerts` | List active alerts |
| `get_zdx_alert` | Get alert details |
| `list_zdx_web_probes` | List web probe configurations |
| `get_zdx_cloudpath` | Get cloudpath analysis |

## Example Queries

```
Show ZDX score trends for the last 24 hours

What users have poor experience scores?

List applications with degraded performance

Show alerts for the sales team

Get cloudpath analysis for Office 365
```

## Prerequisites

- `ZSCALER_CLIENT_ID` OneAPI client ID
- `ZSCALER_CLIENT_SECRET` OneAPI client secret
- `ZSCALER_CUSTOMER_ID` Customer/tenant ID
- `ZSCALER_VANITY_DOMAIN` Vanity domain
- `ZSCALER_MCP_SERVICES` must include `zdx`

## Server

This skill uses the `zscaler-mcp` server which connects to ZDX via OneAPI.
