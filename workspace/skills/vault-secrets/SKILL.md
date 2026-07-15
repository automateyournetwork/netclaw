---
name: vault-secrets
description: "Manage HashiCorp Vault KV secrets with strict value protection."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Vault Secrets Skill

Manage HashiCorp Vault KV secrets with strict value protection.

## Tools

| Tool | Description |
|------|-------------|
| `read_secret` | Read secret metadata (values NEVER displayed) |
| `write_secret` | Write secret to KV engine |
| `list_secrets` | List secrets in a path |
| `delete_secret` | Delete a secret |
| `get_secret_metadata` | Get secret version metadata |
| `inject_secret` | Inject secret value to integration |

## CRITICAL: Secret Value Protection

**Secret values are NEVER displayed in responses.** When reading secrets:
- Only metadata is shown (version, created time, etc.)
- Actual secret values are never logged or returned
- Use `inject_to` parameter to send secrets directly to integrations

## Example Queries

```
List secrets in the network-devices path

Read metadata for secret network-devices/router-creds

Inject router credentials to pyATS testbed

Write a new secret to network-devices/switch-01
```

## Prerequisites

- `VAULT_ADDR` Vault server address
- `VAULT_TOKEN` Authentication token with appropriate policy
- Optional: `VAULT_NAMESPACE` for Vault Enterprise

## Server

This skill uses the `vault-mcp` server which connects to Vault API.
