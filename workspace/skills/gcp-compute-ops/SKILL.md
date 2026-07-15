---
name: gcp-compute-ops
description: "Google Cloud Compute Engine — VM instances, disks, templates, instance groups, reservations, project discovery. Use when listing GCP VMs, troubleshooting a Compute Engine instance, checking disk attachments, planning capacity with reservations and commitments, or managing instance groups."
version: 1.0.0
license: Apache-2.0
tags: [gcp, compute-engine, vm, instances, disks, resource-manager]

netshell:
  mcp_tools:
    - mcp: gcp-compute-mcp
      tools:
        - search_projects
        - list_instances
        - get_instance
        - list_disks
        - get_disk
        - list_instance_templates
        - list_instance_groups
        - list_machine_types
        - list_zones
---

# GCP Compute Operations

## MCP Servers

- **Compute Engine**: `https://compute.googleapis.com/mcp` (Streamable HTTP)
- **Resource Manager**: `https://cloudresourcemanager.googleapis.com/mcp` (Streamable HTTP)
- **Auth**: OAuth 2.0 via Google IAM — service account key (`GOOGLE_APPLICATION_CREDENTIALS`) or `gcloud auth application-default login`
- **Requires**: `GCP_PROJECT_ID` environment variable

## Key Difference from On-Prem MCP Servers

Google Cloud MCP servers are **remote HTTP endpoints** hosted by Google — nothing to install locally. Authentication uses OAuth 2.0 / Google IAM, not API keys. The transport is Streamable HTTP, not stdio.

## Available Tools (29)

### Resource Manager (1 tool)

| Tool | What It Does |
|------|-------------|
| `search_projects` | Search for GCP projects by parent, ID, or filter. Use this first to discover available projects. |

### Instance Management (8 tools)

| Tool | What It Does |
|------|-------------|
| `list_instances` | List VM instances in a project (filter by zone) |
| `get_instance_basic_info` | Get core instance details — name, status, machine type, network interfaces, IPs |
| `create_instance` | Provision a new VM instance |
| `delete_instance` | Remove a VM instance |
| `start_instance` | Boot a stopped instance |
| `stop_instance` | Halt a running instance |
| `reset_instance` | Restart an instance (hard reset) |
| `set_instance_machine_type` | Resize an instance (change machine type) |

### Instance Groups (3 tools)

| Tool | What It Does |
|------|-------------|
| `list_instance_group_managers` | List managed instance groups (MIGs) |
| `get_instance_group_manager_basic_info` | Get MIG details — template, target size, autoscaling |
| `list_managed_instances` | List instances within a MIG |

### Instance Templates (3 tools)

| Tool | What It Does |
|------|-------------|
| `list_instance_templates` | List available instance templates |
| `get_instance_template_basic_info` | Get template basics — name, description |
| `get_instance_template_properties` | Get template specs — machine type, disks, network interfaces |

### Disks & Storage (5 tools)

| Tool | What It Does |
|------|-------------|
| `list_disks` | List persistent disks in a project |
| `get_disk_basic_info` | Get disk metadata — size, type, attached instances |
| `get_disk_performance_config` | Get disk performance settings — IOPS, throughput |
| `list_snapshots` | List disk snapshots |
| `list_instance_attached_disks` | List disks attached to a specific instance |

### Resource Discovery (3 tools)

| Tool | What It Does |
|------|-------------|
| `list_machine_types` | List available machine types in a zone (e2, n2, c3, etc.) |
| `list_accelerator_types` | List available GPU/TPU types in a zone |
| `list_images` | List available boot images (Debian, Ubuntu, CentOS, etc.) |

### Reservations & Commitments (6 tools)

| Tool | What It Does |
|------|-------------|
| `list_reservations` | List capacity reservations |
| `get_reservation_basic_info` | Get reservation details |
| `get_reservation_details` | Get comprehensive reservation info |
| `list_commitments` | List committed use discounts (CUDs) |
| `get_commitment_basic_info` | Get commitment details — term, status |
| `list_commitment_reservations` | List reservations tied to a commitment |

### Operations (1 tool)

| Tool | What It Does |
|------|-------------|
| `get_zone_operation` | Check status of an async operation (create, delete, resize) |

## Workflow: GCP Infrastructure Audit

When a user asks "show me our GCP compute resources":

1. **Discover projects**: `search_projects` to list all accessible GCP projects
2. **List instances**: `list_instances` per project — name, status, zone, machine type
3. **Network interfaces**: `get_instance_basic_info` to see IPs, VPC, subnet per VM
4. **Instance groups**: `list_instance_group_managers` for autoscaled workloads
5. **Disk inventory**: `list_disks` — size, type, attached instances
6. **Report**: GCP compute inventory with status and network details

## Workflow: VM Troubleshooting

When investigating a GCP VM issue:

1. **Find the VM**: `list_instances` filtered by name or zone
2. **Get details**: `get_instance_basic_info` — status, machine type, network interfaces, external IP
3. **Check disks**: `list_instance_attached_disks` — any missing or detached?
4. **Check operation**: `get_zone_operation` — any pending/failed operations?
5. **Cross-reference**: Use `gcp-cloud-logging` for instance logs, `gcp-cloud-monitoring` for metrics
6. **Report**: VM health assessment with findings

## Workflow: Capacity Planning

When planning GCP compute capacity:

1. **Current usage**: `list_instances` — count by machine type and zone
2. **Reservations**: `list_reservations` — reserved capacity vs actual usage
3. **Commitments**: `list_commitments` — CUD utilization and expiration
4. **Available types**: `list_machine_types` — what's available in target zones
5. **GPU availability**: `list_accelerator_types` — GPU/TPU options per zone
6. **Report**: Capacity utilization with recommendations

## Important Rules

- **Google Cloud MCP servers are remote** — no local install, runs on Google's infrastructure
- **OAuth 2.0 authentication** — uses service account or user credentials via IAM
- **Project-scoped** — all operations are scoped to the configured GCP project
- **Write operations available** — unlike AWS Network MCP, Compute Engine MCP can create/modify/delete VMs. Use ServiceNow CR gating for changes.
- **Record in GAIT** — log all GCP operations for audit trail

## Environment Variables

- `GCP_PROJECT_ID` — Google Cloud project ID
- `GOOGLE_APPLICATION_CREDENTIALS` — Path to service account key JSON file (or use `gcloud auth application-default login`)
