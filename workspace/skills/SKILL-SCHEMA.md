# SKILL.md Schema Reference

This document defines the YAML frontmatter schema for NetClaw skill definitions.

## Full Schema

```yaml
---
# Required fields
name: string                    # Skill identifier (lowercase, hyphens)
description: string             # Human-readable description
version: string                 # Semantic version (e.g., "1.0.0")
license: string                 # SPDX license identifier (e.g., "Apache-2.0", "MIT")

# Optional metadata
author: string                  # Skill author
tags: [string]                  # Categorization tags
priority: integer               # Execution priority (lower = higher priority)

# MCP dependencies
mcp_servers: [string]           # List of MCP servers this skill uses
---
```

## Field Descriptions

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique skill identifier. Use lowercase with hyphens (e.g., `pyats-health-check`). |
| `description` | string | Brief explanation of what the skill does. |
| `version` | string | Semantic version for tracking changes. |
| `license` | string | SPDX license identifier (e.g., `Apache-2.0`, `MIT`, `BSD-3-Clause`). |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `author` | string | Skill author name. |
| `tags` | array | Categorization tags for filtering. |
| `priority` | integer | Execution priority (lower = higher priority). |
| `mcp_servers` | array | List of MCP servers this skill uses. |

## Examples

### Read-Only Skill

```yaml
---
name: network-inventory
description: Discover and inventory network devices
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: [inventory, discovery]
mcp_servers: [suzieq-mcp, batfish-mcp]
---
```

### Read/Write Skill

```yaml
---
name: vlan-provisioner
description: Provision VLANs across network devices
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: [provisioning, vlan]
mcp_servers: [aruba-cx-mcp, meraki-magic-mcp]
---
```

### Documentation Skill

```yaml
---
name: api-docs-lookup
description: Search API documentation
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: [documentation, api]
mcp_servers: [devnet-content-search]
---
```

---

## Security with DefenseClaw

When DefenseClaw is enabled, all skills are automatically scanned before execution. No changes to SKILL.md are required.

### Automatic Scanning

DefenseClaw's CodeGuard scans all skill code for:
- Hardcoded credentials (API keys, passwords)
- Dynamic code execution (eval, exec)
- Shell command injection
- SQL injection
- Path traversal
- Weak cryptography

### Tool Management

Instead of declaring permissions in SKILL.md, DefenseClaw manages tool access centrally:

```bash
# Block a tool for all skills
defenseclaw tool block delete_file --reason "destructive operation"

# Allow a tool
defenseclaw tool allow read_file

# List tool rules
defenseclaw tool list
```

### Scan a Skill

```bash
# Scan skill code before deployment
defenseclaw skill scan pyats-health-check

# Expected output:
# Scanning skill: pyats-health-check
# ✓ No HIGH/CRITICAL findings
# Status: ALLOWED
```

### Security Notes for Skill Authors

1. **Never hardcode credentials** - Use environment variables
2. **Avoid eval/exec** - Use safe alternatives
3. **Sanitize inputs** - Validate all user-provided data
4. **Use approved libraries** - Stick to well-known packages

### Documentation

- [DefenseClaw Guide](../docs/DEFENSECLAW.md) - Full security documentation
- [Security Principles](../docs/SOUL-DEFENSE.md) - Security posture guidance
