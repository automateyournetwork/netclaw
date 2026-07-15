---
name: cloudflare-analytics
description: "Access Cloudflare traffic analytics, logs, and Radar global Internet insights."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Cloudflare Analytics Skill

Access Cloudflare traffic analytics, logs, and Radar global Internet insights.

## Tools

| Tool | Description |
|------|-------------|
| `get_zone_analytics` | Get traffic analytics for a zone |
| `search_logs` | Search HTTP request and firewall logs |
| `get_traffic_insights` | Get global traffic insights from Radar |
| `scan_url` | Scan a URL for security analysis |
| `get_threat_intel` | Get threat intelligence for an indicator |
| `get_internet_trends` | Get Internet traffic trends from Radar |

## Example Queries

```
Show traffic analytics for example.com today

Search Cloudflare logs for 403 errors in the last hour

What are the global Internet traffic trends from Radar?

Scan https://suspicious-site.com for threats
```

## Prerequisites

- `CLOUDFLARE_API_TOKEN` with Analytics:Read scope
- `CLOUDFLARE_ACCOUNT_ID` from dashboard

## Servers

This skill uses:
- `cloudflare-observability` at `observability.mcp.cloudflare.com`
- `cloudflare-radar` at `radar.mcp.cloudflare.com`
