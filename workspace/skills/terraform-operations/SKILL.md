---
name: terraform-operations
description: "Execute local Terraform operations with ServiceNow change control."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Terraform Operations Skill

Execute local Terraform operations with ServiceNow change control.

## Tools

| Tool | Description |
|------|-------------|
| `terraform_init` | Initialize Terraform working directory |
| `terraform_validate` | Validate configuration syntax |
| `terraform_fmt` | Format configuration files |
| `terraform_plan` | Generate execution plan |
| `terraform_apply` | Apply changes (REQUIRES CR) |
| `terraform_destroy` | Destroy infrastructure (REQUIRES CR) |
| `terraform_output` | Show output values |
| `terraform_state_list` | List resources in state |
| `terraform_import` | Import existing infrastructure |

## CRITICAL: Change Control

**`terraform_apply` and `terraform_destroy` require an approved ServiceNow Change Request.** The CR must be in `Implement` state before these operations execute.

## Example Queries

```
Run terraform init in the vpc directory

Validate the staging configuration

Generate a plan for the production network

Show terraform outputs for the current workspace
```

## Prerequisites

- Terraform CLI installed locally
- ServiceNow CR for apply/destroy operations
- Provider credentials in environment

## Server

This skill uses the `terraform-mcp` server with Operations toolset enabled.
