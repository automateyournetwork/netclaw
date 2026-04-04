# Feature Specification: Terraform MCP Server Integration

**Feature ID**: 018-terraform-mcp-server
**Status**: Draft
**Created**: 2026-04-04

## Overview

Integrate the official HashiCorp Terraform MCP server to provide Infrastructure as Code (IaC) capabilities within NetClaw. This enables GitOps workflows for network infrastructure provisioning and management.

## Source

- **Repository**: https://github.com/hashicorp/terraform-mcp-server
- **Type**: Official (HashiCorp-maintained)
- **License**: MPL-2.0
- **Transport**: stdio or StreamableHTTP

## Tools Available (15+ across toolsets)

### Registry Toolset (Default)

| Tool | Description |
|------|-------------|
| `search_providers` | Search Terraform Registry for providers |
| `get_provider_details` | Get provider documentation and versions |
| `search_modules` | Search for Terraform modules |
| `get_module_details` | Get module documentation and inputs/outputs |

### Terraform Operations Toolset

| Tool | Description |
|------|-------------|
| `terraform_init` | Initialize Terraform working directory |
| `terraform_plan` | Generate execution plan |
| `terraform_apply` | Apply infrastructure changes |
| `terraform_destroy` | Destroy infrastructure |
| `terraform_validate` | Validate configuration syntax |
| `terraform_fmt` | Format configuration files |

### HCP Terraform / TFE Toolset

| Tool | Description |
|------|-------------|
| `list_workspaces` | List HCP Terraform workspaces |
| `get_workspace` | Get workspace details |
| `create_workspace` | Create new workspace |
| `trigger_run` | Trigger a Terraform run |
| `get_run_status` | Check run status |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TFE_TOKEN` | Yes | HCP Terraform / TFE API token |
| `TFE_ADDRESS` | No | API address (default: https://app.terraform.io) |
| `TRANSPORT_MODE` | No | stdio or streamable-http |
| `ENABLE_TF_OPERATIONS` | No | Enable terraform operations (plan/apply) |

## User Stories

### US1: Provider Discovery (Priority: P1) MVP
**As a** network engineer
**I want to** search for Terraform providers for network devices
**So that** I can find the right provider for my infrastructure

**Acceptance Criteria:**
- Can search providers by keyword (e.g., "cisco", "juniper", "palo alto")
- Returns provider name, version, and documentation link
- Shows provider capabilities and resources

### US2: Module Discovery (Priority: P1) MVP
**As a** network engineer
**I want to** find Terraform modules for common network patterns
**So that** I can reuse proven infrastructure code

**Acceptance Criteria:**
- Can search modules by keyword or provider
- Returns module inputs, outputs, and examples
- Shows module popularity and verification status

### US3: Workspace Management (Priority: P2)
**As a** network engineer using HCP Terraform
**I want to** manage workspaces from NetClaw
**So that** I can orchestrate infrastructure changes

**Acceptance Criteria:**
- Can list workspaces by organization
- Can view workspace state and variables
- Can trigger runs with ServiceNow CR approval

### US4: Plan Review (Priority: P2)
**As a** network engineer
**I want to** review Terraform plans before applying
**So that** I understand infrastructure changes

**Acceptance Criteria:**
- Can view plan output with resource changes
- Can identify adds, changes, and destroys
- Apply requires explicit approval

## Proposed Skills

| Skill | Tools | Description |
|-------|-------|-------------|
| `terraform-registry` | 4 | Provider and module discovery |
| `terraform-workspaces` | 4 | HCP Terraform workspace management |
| `terraform-operations` | 4 | Plan, apply, and state operations |

## Integration Points

- **ServiceNow**: CR approval for terraform apply
- **GitHub/GitLab**: GitOps workflow triggers
- **Vault**: Secrets injection for provider credentials
- **Azure/AWS**: Cloud provider configurations

## Clarifications

### Session 2026-04-04
- Q: Terraform operations enablement? → A: Enable ALL toolsets (Registry + Operations + HCP Terraform)

## Security Considerations

- All toolsets enabled (Registry, Operations, HCP Terraform)
- Apply and destroy operations require ServiceNow CR approval
- Credentials managed via Vault integration
- State files not exposed through MCP
- Destroy operations require explicit confirmation plus CR

## Success Criteria

1. Can query "search Terraform providers for Cisco ACI" and get results
2. Can query "list my HCP Terraform workspaces" and see network workspaces
3. Integration appears in NetClaw UI with correct tool count
4. All 3 skills documented with SKILL.md files
