---
name: cloudflare-dns
description: "Manage Cloudflare DNS zones and records with analytics insights."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Cloudflare DNS Skill

Manage Cloudflare DNS zones and records with analytics insights.

## Tools

| Tool | Description |
|------|-------------|
| `list_zones` | List all DNS zones in the account |
| `get_zone` | Get details for a specific zone |
| `list_dns_records` | List DNS records in a zone |
| `get_dns_analytics` | Get DNS query analytics for a zone |
| `get_dns_performance` | Get DNS performance metrics |
| `get_dns_trends` | Get DNS trend analysis over time |

## Example Queries

```
List all my Cloudflare DNS zones

Show DNS records for example.com

What are the DNS analytics for my zone in the last 24 hours?

Show DNS query performance for example.com
```

## Prerequisites

- `CLOUDFLARE_API_TOKEN` with Zone:Read scope
- `CLOUDFLARE_ACCOUNT_ID` from dashboard
- Optional: `CLOUDFLARE_ZONE_ID` for default zone

## Server

This skill uses the `cloudflare-dns-analytics` remote MCP server at `dns-analytics.mcp.cloudflare.com`.

## Failure Behavior

- On a tool error (timeout, unreachable host, malformed response), report the failure and its error message directly to the user rather than fabricating or guessing at results.
- All tools here are read-only, so a failed call has no side effects — it's safe to retry once after confirming connectivity, but don't loop indefinitely on repeated failures.
