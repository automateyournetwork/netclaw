---
name: vault-pki
description: "Manage HashiCorp Vault PKI certificate infrastructure."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Vault PKI Skill

Manage HashiCorp Vault PKI certificate infrastructure.

## Tools

| Tool | Description |
|------|-------------|
| `enable_pki` | Enable PKI secrets engine at a path |
| `create_pki_issuer` | Create a CA certificate issuer |
| `list_pki_issuers` | List configured issuers |
| `get_pki_issuer` | Get issuer details |
| `create_pki_role` | Create certificate issuing role |
| `list_pki_roles` | List PKI roles |
| `get_pki_role` | Get role configuration |
| `issue_certificate` | Issue certificate from role |
| `list_certificates` | List issued certificates |
| `revoke_certificate` | Revoke a certificate |

## Example Queries

```
List PKI roles in the network-pki engine

Issue a certificate for router-mgmt.example.com

Create a PKI role for network device certificates

Show issuers in the pki/network path
```

## Prerequisites

- `VAULT_ADDR` Vault server address
- `VAULT_TOKEN` Token with PKI management policy
- Optional: `VAULT_NAMESPACE` for Vault Enterprise

## Server

This skill uses the `vault-mcp` server which connects to Vault PKI API.
