---
name: cloudflare-workers
description: "Monitor Cloudflare Workers deployments, bindings, and build insights."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Cloudflare Workers Skill

Monitor Cloudflare Workers deployments, bindings, and build insights.

## Tools

| Tool | Description |
|------|-------------|
| `list_workers` | List deployed Workers scripts |
| `get_worker` | Get details for a Worker script |
| `get_worker_bindings` | Get bindings configuration for a Worker |
| `list_builds` | List build history for a Worker |
| `get_build` | Get details for a specific build |
| `get_worker_analytics` | Get usage metrics for a Worker |

## Example Queries

```
List all my Cloudflare Workers

Show details for the api-gateway Worker

What bindings does my edge-proxy Worker have?

Show build history for my auth-worker
```

## Prerequisites

- `CLOUDFLARE_API_TOKEN` with Workers:Read scope
- `CLOUDFLARE_ACCOUNT_ID` from dashboard

## Servers

This skill uses:
- `cloudflare-observability` at `observability.mcp.cloudflare.com` (for Workers bindings/details)

Note: Workers builds server at `workers-builds.mcp.cloudflare.com` can be added for additional build insights.

## Failure Behavior

- On a tool error (timeout, unreachable host, malformed response), report the failure and its error message directly to the user rather than fabricating or guessing at results.
- All tools here are read-only, so a failed call has no side effects — it's safe to retry once after confirming connectivity, but don't loop indefinitely on repeated failures.
