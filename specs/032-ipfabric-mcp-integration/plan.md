# Implementation Plan: IP Fabric MCP Integration

**Branch**: `032-ipfabric-mcp-integration` | **Date**: 2026-06-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification for production-grade IP Fabric MCP integration with unified `/ipfabric` skill

## Summary

Integrate the official IP Fabric MCP Server into NetClaw with a unified `/ipfabric` skill that auto-routes natural language queries to appropriate IP Fabric tools. This is a remote MCP server integration (IP Fabric MCP is built into IP Fabric appliances) using the mcp-remote proxy. Includes install.sh integration for new users, ipfabric-enable.sh for existing users, and full documentation updates per constitution requirements. Developed in collaboration with Daren Fulwell (Field CTO, IP Fabric) and John Capobianco (Creator, NetClaw), representing nearly a decade of professional partnership.

## Technical Context

**Language/Version**: Node.js 18+ (mcp-remote proxy), Bash (install scripts)
**Primary Dependencies**: mcp-remote (npx package), IP Fabric appliance with MCP Server enabled
**Storage**: N/A (stateless proxy to IP Fabric APIs)
**Testing**: Manual integration tests with IP Fabric demo instance, connectivity verification
**Target Platform**: Linux (primary), macOS, WSL2
**Project Type**: Integration (MCP server configuration + skill + install scripts)
**Performance Goals**: <30 seconds for typical queries (per SC-001)
**Constraints**: Requires Node.js/NPM, network access to IP Fabric appliance over HTTPS, valid API token
**Scale/Scope**: 1 remote MCP server, 1 skill, 2 install scripts, documentation updates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| V. MCP-Native Integration | ✅ PASS | Using official IP Fabric MCP Server (built into appliance) |
| VI. Multi-Vendor Neutrality | ✅ PASS | IP Fabric-specific logic in IPF MCP, not in shared skills |
| VII. Skill Modularity | ✅ PASS | Single `/ipfabric` skill with clear purpose |
| XI. Full-Stack Artifact Coherence | ⚠️ REQUIRED | Must update README, install.sh, SOUL.md, .env.example, openclaw.json |
| XII. Documentation-as-Code | ⚠️ REQUIRED | Must create SKILL.md for ipfabric skill |
| XIII. Credential Safety | ✅ PASS | All credentials via IPFABRIC_* environment variables |
| XV. Backwards Compatibility | ✅ PASS | Additive integration, no breaking changes |
| XVI. Spec-Driven Development | ✅ PASS | Following SDD workflow |
| XVII. Milestone Documentation | ⚠️ REQUIRED | Blog post at completion |

**Gate Status**: PASS (no violations, required artifacts tracked)

## Project Structure

### Documentation (this feature)

```text
specs/032-ipfabric-mcp-integration/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (MCP tool contracts)
│   └── mcp-tools.md     # IP Fabric MCP tool inventory
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
# Skill definition
workspace/skills/ipfabric/
└── SKILL.md             # /ipfabric skill documentation

# Installation scripts
scripts/
├── install.sh           # Updated with IP Fabric step
└── ipfabric-enable.sh   # New script for existing users

# Configuration
config/
└── openclaw.json        # MCP server registration (1 remote entry via mcp-remote)

# Environment
.env.example             # IPFABRIC_* variable documentation

# Documentation
README.md                # IP Fabric section
SOUL.md                  # IP Fabric expertise
docs/
└── IPFABRIC.md          # Detailed IP Fabric integration guide
```

**Structure Decision**: Integration-only feature. No new MCP server code (using official IP Fabric MCP Server built into appliances). Connection via mcp-remote proxy over HTTPS. Deliverables are configuration, scripts, skill definition, and documentation.

## Complexity Tracking

> No constitution violations requiring justification. IP Fabric MCP is a remote server, not new code.

## Phase 0: Research

### Research Tasks

1. **IP Fabric MCP Environment Variables**: Document exact env var names required for authentication
2. **MCP Tool Inventory**: Catalog all tools exposed by IP Fabric MCP Server
3. **mcp-remote Proxy Configuration**: Document correct npx invocation pattern for remote HTTP MCP
4. **Query Routing Patterns**: Define mapping from natural language patterns to IP Fabric tools
5. **Existing Install.sh Pattern**: Review current install.sh structure for integration point
6. **PNG Diagram Handling**: Verify NetClaw's existing image attachment capabilities for diagrams

### Research Output → research.md

## Phase 1: Design

### Data Model → data-model.md

- MCP Server Configuration Schema (mcp-remote pattern)
- Environment Variable Requirements
- Query Router Mapping Table (natural language → IP Fabric tool)
- Snapshot Handling (default to `$last`)

### Contracts → contracts/mcp-tools.md

- Tool inventory for IP Fabric MCP Server:
  - `ipf_network_health_assess` - Network health assessment
  - `ipf_pathlookup_unicast` - Unicast path lookup
  - `ipf_pathlookup_host-to-gateway` - Host to gateway path
  - `ipf_pathlookup_multicast` - Multicast path lookup
  - `ipf_png_pathlookup_unicast` - Unicast path diagram (PNG)
  - `ipf_png_pathlookup_host-to-gateway` - Host to gateway diagram (PNG)
  - `ipf_png_pathlookup_multicast` - Multicast path diagram (PNG)
  - `ipf_api_endpoint_search` - API endpoint discovery
  - `ipf_api_endpoint_details` - API endpoint details
  - `api_invoke` - Execute API calls
- Environment variable requirements
- Example npx mcp-remote invocation pattern

### Quickstart → quickstart.md

- 5-minute setup for users with IP Fabric credentials
- Prerequisites (IP Fabric appliance with MCP enabled, API token)
- Verification commands to test connectivity

## MCP Configuration Pattern

The IP Fabric MCP uses remote HTTP connection via mcp-remote proxy:

```json
{
  "ipfabric-mcp": {
    "command": "npx",
    "args": [
      "-y",
      "mcp-remote",
      "${IPFABRIC_HOST}/mcp",
      "--header",
      "Authorization:${IPFABRIC_AUTH_HEADER}"
    ],
    "env": {
      "IPFABRIC_AUTH_HEADER": "Bearer ${IPFABRIC_API_TOKEN}"
    }
  }
}
```

**Environment Variables**:
- `IPFABRIC_HOST` - IP Fabric appliance URL (e.g., `https://ipfabric.example.com`)
- `IPFABRIC_API_TOKEN` - API token with appropriate RBAC permissions

## Artifact Coherence Checklist (Constitution XI)

```
[ ] README.md updated (IP Fabric section, tool count)
[ ] scripts/install.sh updated (IP Fabric integration step)
[ ] scripts/ipfabric-enable.sh created (existing user enablement)
[ ] SOUL.md updated (IP Fabric expertise)
[ ] workspace/skills/ipfabric/SKILL.md created
[ ] .env.example updated (IPFABRIC_* variables)
[ ] config/openclaw.json updated (1 MCP server registration via mcp-remote)
[ ] docs/IPFABRIC.md created (detailed guide)
[ ] WordPress blog post drafted (at completion)
```

## Partnership Attribution

This integration was developed in collaboration with:
- **Daren Fulwell** - Field CTO, IP Fabric
- **John Capobianco** - Creator, NetClaw

Their partnership, spanning nearly a decade, continues to bring innovative network automation capabilities to the community.
