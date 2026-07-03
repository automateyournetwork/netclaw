# Contract: Skill Permission Schema

**Feature**: [../spec.md](../spec.md) | **Data Model**: [../data-model.md](../data-model.md)

## Purpose

Defines the schema for the `netshell:` section in `workspace/skills/*/SKILL.md` frontmatter - per-skill tool allowlists that enforce the principle of least privilege.

## Schema (YAML Frontmatter)

```yaml
---
name: string                        # Skill name (existing field)
description: string                 # Skill description (existing field)
version: string                     # Skill version (existing field)
# ... other existing fields ...

# NetShell permissions (new section)
netshell:
  mcp_tools:                        # Required: tools this skill can invoke
    - mcp: string                   # MCP server name
      tools: [string]               # Allowed tool names
  approval_required: boolean        # Optional: override ITSM default
---
```

## Validation Rules

1. **netshell** section is optional (backward compatible)
2. If **netshell** is present, **mcp_tools** is required
3. **mcp_tools[].mcp** must match an existing MCP server name
4. **mcp_tools[].tools** must list tools that exist in the MCP
5. **mcp_tools[].tools** must be allowed by the MCP policy (not denied)
6. Skills without **netshell** section cannot invoke any MCP tools when NetShell is enabled
7. **approval_required** defaults to MCP policy setting if not specified

## Example (Read-Only Skill)

```yaml
---
name: network-inventory
description: Discover and inventory network devices
version: 1.0.0
author: netclaw
tags: [inventory, discovery]

netshell:
  mcp_tools:
    - mcp: suzieq-mcp
      tools:
        - get_devices
        - get_interfaces
        - get_routes
    - mcp: batfish-mcp
      tools:
        - analyze_config
        - get_reachability
---
```

## Example (Read/Write Skill)

```yaml
---
name: vlan-provisioner
description: Provision VLANs across network devices
version: 1.0.0
author: netclaw
tags: [provisioning, vlan]

netshell:
  mcp_tools:
    - mcp: aruba-cx-mcp
      tools:
        - aruba_get_vlans         # Read
        - aruba_create_vlan       # Write (will trigger ITSM)
        - aruba_delete_vlan       # Write (will trigger ITSM)
    - mcp: meraki-mcp
      tools:
        - get_network_vlans       # Read
        - create_network_vlan     # Write (will trigger ITSM)
  approval_required: true           # Force ITSM for all writes
---
```

## Example (Documentation Skill - No Network Access)

```yaml
---
name: api-docs-lookup
description: Search API documentation
version: 1.0.0
author: netclaw
tags: [documentation, api]

netshell:
  mcp_tools:
    - mcp: devnet-content-search
      tools:
        - Meraki-API-Doc-Search
        - CatalystCenter-API-Doc-Search
        - Meraki-API-OperationId-Search
---
```

## Permission Resolution Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                     Skill invokes MCP tool                        │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  1. Check: Does SKILL.md have netshell: section?                 │
│     NO  → BLOCK (skill not declared for NetShell)                │
│     YES → Continue                                               │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  2. Check: Is MCP listed in netshell.mcp_tools?                  │
│     NO  → BLOCK (MCP not allowed for this skill)                 │
│     YES → Continue                                               │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  3. Check: Is tool listed in that MCP's tools array?            │
│     NO  → BLOCK (tool not allowed for this skill)                │
│     YES → Continue                                               │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  4. Check: MCP policy allows this tool?                          │
│     NO  → BLOCK (MCP policy denies)                              │
│     YES → Continue                                               │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  5. Check: requires_approval AND tool.requires_approval?         │
│     YES → Route to ITSM for change request                       │
│     NO  → Continue                                               │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  6. Check: Arguments match dangerous_patterns?                   │
│     YES → BLOCK (dangerous pattern detected)                     │
│     NO  → ALLOW (invoke tool)                                    │
└──────────────────────────────────────────────────────────────────┘
```

## Backward Compatibility

When NetShell is **disabled**:
- SKILL.md `netshell:` section is ignored
- Skills can invoke any MCP tool (existing behavior)
- No ITSM gates enforced by NetShell

When NetShell is **enabled** but skill lacks `netshell:` section:
- Skill can still run for non-MCP operations
- Any MCP tool invocation is blocked
- Warning logged: "Skill 'X' has no netshell permissions declared"

## Migration Path

Existing skills need to add `netshell:` section to work with NetShell enabled:

1. Identify all MCP tools the skill uses (grep for tool calls)
2. Add `netshell:` section with required tools
3. Test with NetShell enabled in development
4. Commit updated SKILL.md
