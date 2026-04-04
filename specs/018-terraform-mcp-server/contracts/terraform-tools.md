# Terraform MCP Tools Contract

**Feature**: 018-terraform-mcp-server | **Date**: 2026-04-04

## Overview

This document defines the tool interface contract for the official HashiCorp Terraform MCP server integration.

## MCP Server Configuration

```json
{
  "terraform-mcp": {
    "command": "terraform-mcp-server",
    "args": ["--enable-all-toolsets"],
    "env": {
      "TFE_TOKEN": "${TFE_TOKEN}",
      "TFE_ADDRESS": "${TFE_ADDRESS}"
    }
  }
}
```

## Tool Catalog by Skill

### terraform-registry (4 tools)

| Tool | Type | Parameters | Returns |
|------|------|------------|---------|
| `search_providers` | read | query, tier?, namespace? | Array of providers |
| `get_provider_details` | read | namespace, name, version? | Provider documentation |
| `search_modules` | read | query, provider?, namespace? | Array of modules |
| `get_module_details` | read | namespace, name, provider, version? | Module inputs/outputs |

### terraform-workspaces (5 tools)

| Tool | Type | Parameters | Returns |
|------|------|------------|---------|
| `list_workspaces` | read | organization, search?, page? | Array of workspaces |
| `get_workspace` | read | organization, workspace | Workspace details |
| `create_workspace` | write | organization, name, execution_mode? | Created workspace |
| `trigger_run` | write | workspace_id, message?, auto_apply? | Run details |
| `get_run_status` | read | run_id | Run status and logs |

### terraform-operations (6 tools)

| Tool | Type | Parameters | Returns |
|------|------|------------|---------|
| `terraform_init` | write | working_dir, backend_config? | Init output |
| `terraform_validate` | read | working_dir | Validation result |
| `terraform_fmt` | write | working_dir, check? | Format changes |
| `terraform_plan` | read | working_dir, var_file?, target? | Plan output |
| `terraform_apply` | write | working_dir, auto_approve?, target? | Apply output |
| `terraform_destroy` | write | working_dir, auto_approve?, target? | Destroy output |

## Parameter Details

### search_providers

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| query | string | Yes | - | Search query |
| tier | enum | No | all | official, partner, community |
| namespace | string | No | - | Filter by namespace |

### terraform_plan

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| working_dir | string | Yes | - | Terraform working directory |
| var_file | string | No | - | Variables file path |
| target | array | No | - | Target resources |
| out | string | No | - | Plan file output path |

## Security Gating

### ServiceNow CR Required

These operations require ServiceNow Change Request approval:
- `terraform_apply` (creates/modifies infrastructure)
- `terraform_destroy` (destroys infrastructure)
- `trigger_run` with `auto_apply=true`

### Confirmation Required

These operations require explicit user confirmation:
- `terraform_destroy` (double confirmation)
- `create_workspace` (new workspace creation)

## Error Responses

| Code | Meaning | Example |
|------|---------|---------|
| 400 | Bad Request | Invalid configuration |
| 401 | Unauthorized | Invalid TFE_TOKEN |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Workspace/provider not found |
| 409 | Conflict | Run already in progress |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TFE_TOKEN` | Yes* | HCP Terraform API token |
| `TFE_ADDRESS` | No | API address (default: app.terraform.io) |
| `TF_LOG` | No | Terraform log level |

*Required only for HCP Terraform toolset
