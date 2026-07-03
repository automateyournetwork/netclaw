# Data Model: Check Point MCP Integration

**Feature**: 031-checkpoint-mcp-integration
**Date**: 2026-06-14

## Entities

### 1. MCP Server Configuration

Represents a single Check Point MCP server registration in openclaw.json.

```
MCPServerConfig
├── name: string                    # Unique identifier (e.g., "chkp-management")
├── command: "npx"                  # Always npx for Check Point MCPs
├── args: string[]                  # Package name (e.g., ["@chkp/quantum-management-mcp"])
├── env: Record<string, string>     # Environment variable mappings
└── enabled: boolean                # Whether this MCP is active
```

**Validation Rules**:
- `name` must be unique across all MCP configurations
- `args[0]` must be a valid @chkp/* package name
- `env` values reference environment variables with `${VAR_NAME}` syntax

### 2. Credential Set

Logical grouping of related environment variables for a Check Point product family.

```
CredentialSet
├── id: string                      # Group identifier (mgmt, sase, reputation, etc.)
├── name: string                    # Human-readable name
├── variables: CredentialVariable[]
├── mcpServers: string[]            # MCP servers that use this credential set
└── required: boolean               # Whether at least one auth method is required
```

**Credential Sets Defined**:

| ID | Name | Variables | MCPs |
|----|------|-----------|------|
| `mgmt` | Management Server | CHKP_MGMT_HOST, CHKP_MGMT_PORT, CHKP_MGMT_API_KEY, CHKP_MGMT_USERNAME, CHKP_MGMT_PASSWORD, CHKP_MGMT_DOMAIN | quantum-management, management-logs, threat-prevention, https-inspection, policy-insights, quantum-gw-cli, quantum-gw-connection-analysis, quantum-gaia |
| `s1c` | Smart-1 Cloud | CHKP_S1C_API_KEY, CHKP_S1C_URL | quantum-management (alternate) |
| `sase` | Harmony SASE | CHKP_SASE_API_KEY, CHKP_SASE_MGMT_HOST, CHKP_SASE_ORIGIN | harmony-sase |
| `reputation` | Reputation Service | CHKP_REPUTATION_API_KEY | reputation-service |
| `te` | Threat Emulation | CHKP_TE_API_KEY | threat-emulation |
| `spark` | Spark Management | CHKP_SPARK_API_KEY | spark-management |
| `argos` | Argos ERM | CHKP_ARGOS_API_KEY | argos-erm |
| `none` | No Credentials | (none) | documentation, cpinfo-analysis |

### 3. Credential Variable

Individual environment variable definition.

```
CredentialVariable
├── name: string                    # Variable name (e.g., "CHKP_MGMT_HOST")
├── description: string             # Human-readable description
├── required: boolean               # Whether variable is required
├── default: string?                # Optional default value
├── sensitive: boolean              # Whether value should be masked in logs
└── checkPointVar: string           # Native Check Point variable name to map to
```

### 4. Query Route

Mapping from natural language patterns to MCP server(s).

```
QueryRoute
├── keywords: string[]              # Trigger keywords (lowercase)
├── primaryMcp: string              # Primary MCP to invoke
├── secondaryMcps: string[]?        # Additional MCPs for composite queries
├── category: string                # Functional category
└── examples: string[]              # Example queries
```

**Query Route Categories**:
- `policy` → quantum-management, policy-insights
- `logs` → management-logs
- `threat-prevention` → threat-prevention
- `threat-intel` → reputation-service
- `gateway-diagnostics` → quantum-gw-cli
- `connection-debug` → quantum-gw-connection-analysis
- `malware-analysis` → threat-emulation
- `sase` → harmony-sase
- `https-inspection` → https-inspection
- `gaia` → quantum-gaia
- `documentation` → documentation
- `spark` → spark-management
- `cpinfo` → cpinfo-analysis
- `exposure` → argos-erm

## Configuration Schema

### openclaw.json MCP Entry Format

```json
{
  "mcpServers": {
    "chkp-management": {
      "command": "npx",
      "args": ["@chkp/quantum-management-mcp"],
      "env": {
        "MANAGEMENT_HOST": "${CHKP_MGMT_HOST}",
        "PORT": "${CHKP_MGMT_PORT:-443}",
        "API_KEY": "${CHKP_MGMT_API_KEY}",
        "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
      }
    }
  }
}
```

### .env Variable Format

```bash
# Check Point Management Server
CHKP_MGMT_HOST=192.168.1.100
CHKP_MGMT_PORT=443
CHKP_MGMT_API_KEY=your-api-key-here
# Alternative: username/password
# CHKP_MGMT_USERNAME=admin
# CHKP_MGMT_PASSWORD=your-password

# Logging (per clarification)
CHKP_LOG_LEVEL=standard  # minimal|standard|verbose

# Telemetry
CHKP_TELEMETRY_DISABLED=true
```

## State Transitions

### MCP Server Availability States

```
┌─────────────┐
│ Unconfigured│ ← No credentials in .env
└──────┬──────┘
       │ User adds credentials
       ▼
┌─────────────┐
│ Configured  │ ← Credentials present but not validated
└──────┬──────┘
       │ First query / startup validation
       ▼
┌─────────────┐     ┌─────────────┐
│  Available  │ ←──►│ Unavailable │
└─────────────┘     └─────────────┘
  ↑                   │ Connection error
  │                   │ Auth failure
  └───────────────────┘ Retry on next query
```

## Relationships

```
CredentialSet 1──────* CredentialVariable
       │
       │ uses
       ▼
MCPServerConfig *────1 CredentialSet
       │
       │ routes to
       ▼
QueryRoute *─────────* MCPServerConfig
```

## Data Volume Assumptions

- 15 MCP server configurations (fixed set)
- 7 credential sets (fixed groupings)
- ~25 environment variables total
- ~50 query route patterns
- No persistent storage (stateless proxy)
