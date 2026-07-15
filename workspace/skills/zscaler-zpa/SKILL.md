---
name: zscaler-zpa
description: "Manage Zscaler Private Access applications, segments, policies, and connectors."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Zscaler Private Access (ZPA) Skill

Manage Zscaler Private Access applications, segments, policies, and connectors.

## Tools

| Tool | Description |
|------|-------------|
| `list_application_segments` | List all application segments |
| `get_application_segment` | Get details for an application segment |
| `list_segment_groups` | List segment groups |
| `get_segment_group` | Get segment group details |
| `list_access_policies` | List access policies |
| `get_access_policy` | Get access policy details |
| `list_app_connectors` | List application connectors |
| `get_app_connector` | Get connector details and health |
| `list_connector_groups` | List connector groups |
| `list_server_groups` | List server groups |
| `list_provisioning_keys` | List provisioning keys |
| `create_application_segment` | Create new application segment (write mode) |
| `update_application_segment` | Update application segment (write mode) |
| `delete_application_segment` | Delete application segment (write mode) |

## Example Queries

```
List all ZPA application segments

Show access policies for the finance application

What connectors are unhealthy?

List segment groups in production

Show server groups for data center applications
```

## Prerequisites

- `ZSCALER_CLIENT_ID` OneAPI client ID
- `ZSCALER_CLIENT_SECRET` OneAPI client secret
- `ZSCALER_CUSTOMER_ID` Customer/tenant ID
- `ZSCALER_VANITY_DOMAIN` Vanity domain
- `ZSCALER_MCP_SERVICES` must include `zpa`

## Server

This skill uses the `zscaler-mcp` server which connects to ZPA via OneAPI.
