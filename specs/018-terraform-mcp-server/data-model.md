# Data Model: Terraform MCP Server Integration

**Feature**: 018-terraform-mcp-server | **Date**: 2026-04-04

## Overview

This is a stateless MCP server integration. The Terraform MCP server acts as a proxy to the Terraform Registry API, HCP Terraform API, and local Terraform CLI. No local data storage beyond standard Terraform state is used.

## External Entities

### Provider (Registry)

| Field | Type | Description |
|-------|------|-------------|
| id | string | Provider ID (namespace/name) |
| namespace | string | Provider namespace |
| name | string | Provider name |
| version | string | Latest version |
| description | string | Provider description |
| source | string | Source repository |
| tier | enum | official, partner, community |
| docs_url | string | Documentation URL |

### Module (Registry)

| Field | Type | Description |
|-------|------|-------------|
| id | string | Module ID (namespace/name/provider) |
| namespace | string | Module namespace |
| name | string | Module name |
| provider | string | Target provider |
| version | string | Latest version |
| description | string | Module description |
| inputs | array | Input variables |
| outputs | array | Output values |
| verified | boolean | Verified module flag |

### Workspace (HCP Terraform)

| Field | Type | Description |
|-------|------|-------------|
| id | string | Workspace ID |
| name | string | Workspace name |
| organization | string | Organization name |
| terraform_version | string | Terraform version |
| execution_mode | enum | remote, local, agent |
| auto_apply | boolean | Auto-apply flag |
| working_directory | string | Working directory |
| vcs_repo | object | VCS configuration |
| current_run | object | Current run status |

### Run (HCP Terraform)

| Field | Type | Description |
|-------|------|-------------|
| id | string | Run ID |
| status | enum | pending, plan_queued, planning, planned, cost_estimating, policy_checking, policy_override, apply_queued, applying, applied, discarded, errored, canceled |
| message | string | Run message |
| created_at | datetime | Creation timestamp |
| plan | object | Plan details |
| apply | object | Apply details |
| cost_estimate | object | Cost estimate |
| policy_checks | array | Policy check results |

### Plan (Local)

| Field | Type | Description |
|-------|------|-------------|
| format_version | string | Plan format version |
| terraform_version | string | Terraform version |
| planned_values | object | Planned resource values |
| resource_changes | array | Resources to change |
| output_changes | object | Output changes |
| prior_state | object | State before changes |

### Resource Change

| Field | Type | Description |
|-------|------|-------------|
| address | string | Resource address |
| mode | enum | managed, data |
| type | string | Resource type |
| name | string | Resource name |
| provider_name | string | Provider |
| change | object | Change details |
| action_reason | string | Reason for change |

### Change Action

| Field | Type | Description |
|-------|------|-------------|
| actions | array | [no-op, create, read, update, delete, replace] |
| before | object | State before |
| after | object | State after |
| after_unknown | object | Unknown after values |

## Relationships

```
┌──────────────────┐       ┌─────────────────────┐
│    Provider      │───────│      Resource       │
└──────────────────┘       └─────────────────────┘
                                    │
                                    │
                                    ▼
┌──────────────────┐       ┌─────────────────────┐
│     Module       │       │       State         │
└──────────────────┘       └─────────────────────┘
                                    │
                                    │
                                    ▼
┌──────────────────┐       ┌─────────────────────┐
│    Workspace     │───────│        Run          │
└──────────────────┘       └─────────────────────┘
         │                          │
         │                          │
         ▼                          ▼
┌──────────────────┐       ┌─────────────────────┐
│   Organization   │       │        Plan         │
└──────────────────┘       └─────────────────────┘
```

## Run Lifecycle

```
[pending] → [plan_queued] → [planning] → [planned] →
[cost_estimating] → [policy_checking] → [apply_queued] →
[applying] → [applied]
                    │
                    ├──→ [errored]
                    ├──→ [canceled]
                    └──→ [discarded]
```

## No Local Storage

This integration does not persist additional data locally beyond standard Terraform working directory files (.terraform, terraform.tfstate).
