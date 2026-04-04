# Terraform Workspaces Skill

Manage HCP Terraform (Terraform Cloud/Enterprise) workspaces.

## Tools

| Tool | Description |
|------|-------------|
| `list_workspaces` | List workspaces in an organization |
| `get_workspace` | Get workspace details and variables |
| `create_workspace` | Create a new workspace |
| `update_workspace` | Update workspace configuration |
| `delete_workspace` | Delete a workspace |
| `trigger_run` | Trigger a Terraform run |
| `get_run_status` | Get current run status |
| `list_runs` | List workspace runs |
| `cancel_run` | Cancel a pending run |

## Example Queries

```
List workspaces in the network-infra organization

Show status of the last run for prod-vpc workspace

Trigger a plan for the dev-network workspace

What variables are set on the staging workspace?
```

## Prerequisites

- `TFE_TOKEN` HCP Terraform API token
- Optional: `TFE_ADDRESS` for self-hosted TFE

## Server

This skill uses the `terraform-mcp` server with Workspaces toolset enabled.
