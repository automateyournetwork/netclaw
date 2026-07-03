# Contract: MCP Policy Schema

**Feature**: [../spec.md](../spec.md) | **Data Model**: [../data-model.md](../data-model.md)

## Purpose

Defines the schema for `netshell/policies/mcp/*.yaml` - per-MCP server policies that extend the base policy with MCP-specific network egress rules, tool permissions, and dangerous pattern detection.

## Schema (YAML)

```yaml
# Required fields
version: 1                          # Schema version (integer, must be 1)
mcp_server: string                  # MCP server identifier (e.g., "suzieq-mcp")
description: string                 # Optional human description

# Network egress rules for this MCP
network_policies:
  egress:                           # Required: allowed endpoints
    - name: string                  # Required: rule identifier
      host: string                  # Required: hostname/IP/CIDR/pattern
      ports: [integer]              # Required: allowed ports
      protocols: [string]           # Required: https|http|tcp|udp|grpc
      methods: [string]             # Optional: HTTP methods

# Tool permissions
tools:                              # Required: map of tool_name -> permission
  tool_name:
    permission: string              # Required: allow|deny
    requires_approval: boolean      # Required: ITSM gate
    audit_level: string             # Required: standard|full|none
    description: string             # Optional: tool purpose

# Dangerous patterns to block
dangerous_patterns:                 # Optional
  - pattern: string                 # Regex pattern
    description: string             # Why dangerous

# Required credentials
credentials: [string]               # Optional: env var names
```

## Validation Rules

1. **version** must equal 1
2. **mcp_server** must match filename (e.g., `suzieq-mcp.yaml` → `mcp_server: suzieq-mcp`)
3. **network_policies.egress** must have at least one rule
4. **network_policies.egress[].host** must not be `*` (too permissive)
5. **tools** must define permission for every tool the MCP exposes
6. **tools[].permission** must be `allow` or `deny`
7. **tools[].requires_approval** must be `true` for write operations
8. **tools[].audit_level** must be `full` for write operations
9. **dangerous_patterns[].pattern** must be valid regex

## Tool Categories

| Category | requires_approval | audit_level | Examples |
|----------|-------------------|-------------|----------|
| Read | false | standard | get_*, show_*, list_* |
| Write | true | full | create_*, update_*, delete_*, configure_* |
| Dangerous | true | full | reload, reboot, erase_*, push_config |

## Example (Read-Only MCP)

```yaml
version: 1
mcp_server: devnet-content-search
description: DevNet Content Search - Meraki and Catalyst Center API docs

network_policies:
  egress:
    - name: devnet-mcp
      host: devnet.cisco.com
      ports: [443]
      protocols: [https]
      methods: [GET, POST]

tools:
  Meraki-API-Doc-Search:
    permission: allow
    requires_approval: false
    audit_level: standard
    description: Search Meraki API documentation

  CatalystCenter-API-Doc-Search:
    permission: allow
    requires_approval: false
    audit_level: standard
    description: Search Catalyst Center API documentation

  Meraki-API-OperationId-Search:
    permission: allow
    requires_approval: false
    audit_level: standard
    description: Lookup specific Meraki operation by ID

dangerous_patterns: []
credentials: []
```

## Example (Read/Write MCP)

```yaml
version: 1
mcp_server: aruba-cx-mcp
description: Aruba CX - switch management

network_policies:
  egress:
    - name: aruba-cx-targets
      host: "${ARUBA_CX_TARGETS}"
      ports: [443, 80]
      protocols: [https, http]
      methods: [GET, POST, PUT, PATCH, DELETE]
    - name: internal-rfc1918-10
      host: "10.0.0.0/8"
      ports: [443, 80]
      protocols: [https, http]

tools:
  # Read tools - no approval
  aruba_get_system_info:
    permission: allow
    requires_approval: false
    audit_level: standard
  aruba_get_interfaces:
    permission: allow
    requires_approval: false
    audit_level: standard

  # Write tools - REQUIRE APPROVAL
  aruba_create_vlan:
    permission: allow
    requires_approval: true
    audit_level: full
    description: Create a VLAN
  aruba_delete_vlan:
    permission: allow
    requires_approval: true
    audit_level: full
    description: Delete a VLAN

dangerous_patterns:
  - pattern: "erase.*startup"
    description: "Erasing startup config"
  - pattern: "reload"
    description: "Reloading switch"

credentials:
  - ARUBA_CX_TARGETS
  - ARUBA_CX_CONFIG
```

## Variable Substitution

MCP policies support environment variable substitution using `${VAR_NAME}` syntax:

| Variable | Source | Example |
|----------|--------|---------|
| `${MERAKI_ORG_ID}` | Environment | Organization-specific endpoints |
| `${ARUBA_CX_TARGETS}` | Environment | Device IP list |
| `${INTERNAL_NETWORK}` | Environment | Private network CIDR |

Variables are resolved at policy load time. Missing variables cause policy load failure.

## Network Pattern Types

| Pattern | Example | Matches |
|---------|---------|---------|
| Exact hostname | `api.meraki.com` | Single host |
| Wildcard | `*.meraki.com` | Any subdomain |
| CIDR | `10.0.0.0/8` | IP range |
| Variable | `${TARGETS}` | From environment |
