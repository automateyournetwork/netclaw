---
name: zscaler-identity
description: "Manage users, groups, departments, and identity provider configurations."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Zscaler Identity Skill

Manage users, groups, departments, and identity provider configurations.

## Tools

| Tool | Description |
|------|-------------|
| `list_users` | List all users |
| `get_user` | Get user details |
| `list_groups` | List all groups |
| `get_group` | Get group details |
| `list_departments` | List all departments |
| `get_department` | Get department details |
| `list_idp_configs` | List identity provider configurations |
| `get_idp_config` | Get IdP configuration details |
| `list_scim_groups` | List SCIM-provisioned groups |
| `list_saml_attributes` | List SAML attribute mappings |
| `list_admin_users` | List admin users |
| `get_admin_user` | Get admin user details |
| `list_admin_roles` | List admin roles |

## Example Queries

```
List all users in the engineering department

Show groups synced from Azure AD

What IdP configurations are active?

List admin users with super admin role

Show department hierarchy
```

## Prerequisites

- `ZSCALER_CLIENT_ID` OneAPI client ID
- `ZSCALER_CLIENT_SECRET` OneAPI client secret
- `ZSCALER_CUSTOMER_ID` Customer/tenant ID
- `ZSCALER_VANITY_DOMAIN` Vanity domain
- `ZSCALER_MCP_SERVICES` must include `zidentity`

## Server

This skill uses the `zscaler-mcp` server which connects to ZIdentity via OneAPI.
