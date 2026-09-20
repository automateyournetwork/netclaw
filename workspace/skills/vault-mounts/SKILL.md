---
name: vault-mounts
description: "Discover and manage HashiCorp Vault secret engine mounts."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Vault Mounts Skill

Discover and manage HashiCorp Vault secret engine mounts.

## Tools

| Tool | Description |
|------|-------------|
| `list_mounts` | List all secret engine mounts |
| `get_mount` | Get mount configuration details |
| `create_mount` | Enable a new secret engine |
| `delete_mount` | Disable a secret engine |
| `tune_mount` | Tune mount configuration |
| `list_auth_methods` | List authentication methods |

## Example Queries

```
List all secret engine mounts

What KV engines are enabled?

Enable a new KV-v2 engine at network-secrets

Show configuration for the pki mount
```

## Prerequisites

- `VAULT_ADDR` Vault server address
- `VAULT_TOKEN` Token with sys/mounts policy
- Optional: `VAULT_NAMESPACE` for Vault Enterprise

## Server

This skill uses the `vault-mcp` server which connects to Vault sys API.

## Failure Behavior

- On a tool error (timeout, unreachable host, malformed response), report the failure and its error message directly to the user rather than fabricating or guessing at results.
- Do not automatically retry a write/mutating operation after a failure — surface the error and get explicit confirmation before retrying, since a blind retry on a partially-applied change can leave state inconsistent.
