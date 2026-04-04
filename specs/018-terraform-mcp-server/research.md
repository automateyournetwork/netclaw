# Research: Terraform MCP Server Integration

**Feature**: 018-terraform-mcp-server | **Date**: 2026-04-04

## Research Tasks

### RT1: Official Terraform MCP Server Evaluation

**Decision**: Use official HashiCorp Terraform MCP server

**Rationale**:
- Maintained by HashiCorp (official repository)
- MPL-2.0 licensed (standard HashiCorp license)
- Three focused toolsets: Registry, Operations, HCP Terraform
- Active development with enterprise features
- Supports both local and HCP Terraform workflows

**Alternatives Considered**:
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Official terraform-mcp-server | Full feature set, official | Requires Go runtime | Selected |
| Custom FastMCP server | Full control | No Registry integration | Rejected |
| Terraform CLI wrapper | Simple | No MCP integration | Rejected |

### RT2: Installation Method

**Decision**: Go binary (go install or pre-built binary)

**Rationale**:
- Official distribution method from HashiCorp
- Single binary, no dependencies
- Easy updates via go install
- Cross-platform support

**Installation Options**:
```bash
# Go install
go install github.com/hashicorp/terraform-mcp-server@latest

# Pre-built binary
curl -LO https://releases.hashicorp.com/terraform-mcp-server/latest/terraform-mcp-server_linux_amd64.zip
```

### RT3: Toolset Configuration

**Decision**: Enable ALL toolsets (Registry + Operations + HCP Terraform)

**Rationale**:
- User preference from clarification session
- Maximum functionality for IaC workflows
- Operations gated by ServiceNow CR for apply/destroy
- Registry tools are read-only and safe

**Enabled Toolsets**:
| Toolset | Tools | Risk Level |
|---------|-------|------------|
| Registry | 4 | Low (read-only) |
| Operations | 6 | High (apply/destroy) |
| HCP Terraform | 5 | Medium (triggers runs) |

### RT4: Authentication Method

**Decision**: TFE_TOKEN via environment variable

**Rationale**:
- HCP Terraform uses API tokens
- Token stored in TFE_TOKEN environment variable
- Optional for Registry-only usage
- Required for workspace management

**Token Scopes Required**:
- `read:workspaces` - List and view workspaces
- `write:workspaces` - Create workspaces
- `read:runs` - View run status
- `write:runs` - Trigger runs

### RT5: Skill Organization

**Decision**: 3 focused skills aligned with Terraform domains

**Rationale**:
- Registry: Provider and module discovery (4 tools)
- Workspaces: HCP Terraform management (5 tools)
- Operations: Local Terraform commands (6 tools)

**Tool Distribution**:
| Skill | Tools | Description |
|-------|-------|-------------|
| terraform-registry | 4 | search_providers, get_provider_details, search_modules, get_module_details |
| terraform-workspaces | 5 | list_workspaces, get_workspace, create_workspace, trigger_run, get_run_status |
| terraform-operations | 6 | init, plan, apply, destroy, validate, fmt |

## Security Considerations

### Apply/Destroy Gating
- Apply operations require ServiceNow CR approval
- Destroy operations require explicit confirmation + CR
- Plan output review before any changes

### Credential Protection
- TFE_TOKEN never logged
- Provider credentials via Vault integration
- State files not exposed through MCP

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| terraform-mcp-server | latest | Official MCP server |
| Terraform CLI | 1.x+ | Local operations |
| HCP Terraform | - | Cloud workspace management |

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Accidental apply | Medium | High | ServiceNow CR gating |
| State corruption | Low | High | Remote state in HCP Terraform |
| Credential exposure | Low | High | Vault integration |
| Long-running operations | Medium | Low | Async execution support |

## Open Questions Resolved

All research tasks completed. No blocking unknowns remain.
