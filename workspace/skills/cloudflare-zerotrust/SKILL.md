---
name: cloudflare-zerotrust
description: "Inspect Cloudflare Zero Trust access applications, policies, tunnels, and CASB findings."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Cloudflare Zero Trust Skill

Inspect Cloudflare Zero Trust access applications, policies, tunnels, and CASB findings.

## Tools

| Tool | Description |
|------|-------------|
| `list_access_applications` | List Zero Trust Access applications |
| `get_access_application` | Get details for an access application |
| `list_access_policies` | List access policies for an application |
| `get_access_policy` | Get details for an access policy |
| `list_tunnels` | List Cloudflare Tunnels |
| `get_tunnel` | Get tunnel details and connection status |
| `list_casb_findings` | List CASB security findings |
| `get_casb_finding` | Get details for a CASB finding |

## Example Queries

```
List all Cloudflare Access applications

Show access policies for the internal-dashboard app

What Cloudflare Tunnels are configured and their status?

List CASB security findings for SaaS misconfigurations
```

## Prerequisites

- `CLOUDFLARE_API_TOKEN` with Access:Read, Account:Read scopes
- `CLOUDFLARE_ACCOUNT_ID` from dashboard

## Servers

This skill uses:
- `cloudflare-casb` remote MCP server at `casb.mcp.cloudflare.com`
- `cloudflare-audit-logs` for access audit trails
