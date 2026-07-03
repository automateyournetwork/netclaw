# Data Model: DefenseClaw Security Integration

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Created**: 2026-04-11
**Updated**: 2026-04-16

## Overview

DefenseClaw manages its own data model internally. NetClaw's integration is minimal - we only configure the security mode in `openclaw.json`. DefenseClaw handles:
- Policy storage in `~/.defenseclaw/`
- Audit logs in `~/.defenseclaw/audit.db` (SQLite)
- Tool rules via its CLI

This document defines the NetClaw-side configuration only.

## Entity Definitions

### SecurityConfig (openclaw.json)

The security configuration section in NetClaw's main config file.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| security | SecuritySection | no | Security layer configuration |

### SecuritySection

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| mode | string | yes | "defenseclaw" or "hobby" |
| defenseclaw_home | string | no | Override DefenseClaw home directory |

**Example:**
```json
{
  "security": {
    "mode": "defenseclaw"
  }
}
```

**Hobby mode (default):**
```json
{
  "security": {
    "mode": "hobby"
  }
}
```

---

## DefenseClaw-Managed Entities

These entities are managed by DefenseClaw, documented here for reference only.

### Scan Result

Output from DefenseClaw component scanning.

| Field | Type | Description |
|-------|------|-------------|
| component | string | Skill, MCP, or plugin name |
| severity | string | LOW, MEDIUM, HIGH, CRITICAL |
| findings | Finding[] | List of security issues found |
| blocked | boolean | Whether component was auto-blocked |
| timestamp | datetime | When scan occurred |

### Finding

Individual security finding from CodeGuard.

| Field | Type | Description |
|-------|------|-------------|
| type | string | credential, eval, shell, sqli, path_traversal, weak_crypto, unsafe_deser |
| severity | string | LOW, MEDIUM, HIGH, CRITICAL |
| location | string | File path and line number |
| description | string | Human-readable explanation |

### Tool Rule

DefenseClaw tool block/allow rule.

| Field | Type | Description |
|-------|------|-------------|
| tool | string | Tool name |
| action | string | block or allow |
| reason | string | Why blocked/allowed |
| created | datetime | When rule was created |

### Guardrail Event

Runtime inspection event.

| Field | Type | Description |
|-------|------|-------------|
| category | string | secret, command, sensitive-path, c2, cognitive-file, trust-exploit |
| action | string | observe or block |
| details | object | Event-specific data |
| timestamp | datetime | When event occurred |

---

## Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                         NetClaw                                  │
│                                                                  │
│   ┌─────────────────┐                                           │
│   │  openclaw.json  │─────────────┐                             │
│   │                 │             │                             │
│   │  security.mode  │             │                             │
│   └─────────────────┘             │                             │
│                                   │                             │
└───────────────────────────────────│─────────────────────────────┘
                                    │
                                    │ reads mode
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DefenseClaw                                │
│                                                                  │
│   ┌─────────────────┐    ┌─────────────────┐                   │
│   │   Scan Results  │    │   Tool Rules    │                   │
│   │   (SQLite)      │    │   (SQLite)      │                   │
│   └────────┬────────┘    └────────┬────────┘                   │
│            │                      │                             │
│            └──────────┬───────────┘                             │
│                       │                                         │
│                       ▼                                         │
│            ┌─────────────────┐                                  │
│            │  Guardrail      │                                  │
│            │  Events         │                                  │
│            │  (SQLite/SIEM)  │                                  │
│            └─────────────────┘                                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Storage Details

| Data | Location | Format | Owner |
|------|----------|--------|-------|
| Security Mode | `~/.openclaw/config/openclaw.json` | JSON | NetClaw |
| Scan Results | `~/.defenseclaw/audit.db` | SQLite | DefenseClaw |
| Tool Rules | `~/.defenseclaw/audit.db` | SQLite | DefenseClaw |
| Guardrail Events | `~/.defenseclaw/audit.db` or SIEM | SQLite/Export | DefenseClaw |
| Gateway Binary | `~/.local/bin/defenseclaw-gateway` | Binary | DefenseClaw |
| Python CLI | `~/.local/bin/defenseclaw` | Symlink | DefenseClaw |
| Extensions | `~/.defenseclaw/extensions/` | TypeScript | DefenseClaw |

## Migration Notes

The following NetShell data models are **deprecated and removed**:

- Base Policy (base.yaml) → DefenseClaw handles sandbox automatically
- MCP Policies (mcp/*.yaml) → DefenseClaw tool rules
- Skill Permissions (SKILL.md netshell:) → DefenseClaw tool block/allow
- Audit Records (OCSF) → DefenseClaw SQLite + SIEM export

No data migration required - DefenseClaw starts fresh.
