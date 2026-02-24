---
name: cml-admin
description: CML administration — user/group management, system info, licensing, resource monitoring
version: 1.0.0
tags: [cml, admin, users, groups, system, licensing]
---

# CML Administration

Manage CML server administration — users, groups, system information, licensing status, and resource monitoring. This skill covers the operational management of the CML platform itself.

## MCP Server

- **Command**: `cml-mcp` (pip-installed, stdio transport)
- **Requires**: `CML_URL`, `CML_USERNAME`, `CML_PASSWORD` environment variables

## Available Tools

### User Management

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `get_users` | none | List all CML users |
| `create_user` | `username`, `password`, `fullname?`, `email?`, `admin?` | Create a new CML user |
| `get_user` | `user_id`/`username` | Get user details (labs, resource usage) |
| `update_user` | `user_id`/`username`, fields to update | Update user properties |
| `delete_user` | `user_id`/`username` | Delete a CML user |

### Group Management

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `get_groups` | none | List all CML groups |
| `create_group` | `name`, `description?`, `members?` | Create a new group |
| `update_group` | `group_id`/`name`, fields to update | Update group properties |
| `delete_group` | `group_id`/`name` | Delete a group |

### System Information

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `get_system_info` | none | CML version, uptime, resource usage (CPU, RAM, disk) |
| `get_node_defs` | none | List all available node definitions and their resource requirements |
| `get_licensing` | none | License status, node count, expiration |
| `get_resource_usage` | none | Current resource utilization across all labs |

## Workflow: Onboard a New Lab User

When an admin wants to add a new team member:

1. **Check existing users**: `get_users` to see current user list
2. **Create the user**: `create_user` with their credentials
3. **Add to group** (optional): `update_group` to add user to a team group
4. **Verify**: `get_user` to confirm creation
5. **Share credentials**: Report the username and CML URL to the admin (never share the password in Slack)

## Workflow: Resource Capacity Check

Before building a large lab:

1. **Check system resources**: `get_system_info` for CPU, RAM, disk
2. **Check licensing**: `get_licensing` for available node count
3. **Check node definitions**: `get_node_defs` for per-node resource requirements
4. **Calculate**: Does the planned lab fit within available resources?
5. **Report**: "You have X GB RAM free, Y CPU cores available, Z node licenses remaining. Your planned lab needs A GB RAM and B nodes."

## Workflow: System Health Report

For CML server health monitoring:

1. **System info**: `get_system_info` — version, uptime, resource usage
2. **Licensing**: `get_licensing` — license status and node count
3. **Resource usage**: `get_resource_usage` — breakdown by lab/user
4. **Active labs**: `get_labs` (from cml-lab-lifecycle) — list running labs
5. **Generate report**: Summary of CML platform health

## Resource Planning Guide

Typical per-node resource requirements:

| Node Type | vCPUs | RAM | Disk |
|-----------|-------|-----|------|
| IOSv | 1 | 512 MB | 2 GB |
| IOSv L2 | 1 | 768 MB | 2 GB |
| CSR1000v / Cat8000v | 1 | 3 GB | 8 GB |
| NX-OS 9000v | 2 | 6 GB | 8 GB |
| IOS-XR 9000v | 2 | 8 GB | 16 GB |
| ASAv | 1 | 2 GB | 8 GB |
| Ubuntu Server | 1 | 512 MB | 8 GB |
| Unmanaged Switch | 0 | 0 | 0 |
| External Connector | 0 | 0 | 0 |

**Rule of thumb**: Plan for the CML host to have at least 2x the total RAM needed by all concurrent labs, plus 8 GB for the CML OS itself.

## User Roles

| Role | Capabilities |
|------|-------------|
| **Admin** | Full access: create/delete users, manage all labs, system settings |
| **User** | Create/manage own labs, view shared labs |

## Workflow: Audit CML Usage

For tracking who's using what:

1. **List all users**: `get_users`
2. **For each user**: `get_user` to see their labs and resource usage
3. **List all labs**: `get_labs` with ownership info
4. **Check resource usage**: `get_resource_usage` for allocation breakdown
5. **Report**: Table of users, their labs, running state, and resource consumption
6. **Identify stale labs**: Labs that have been stopped for days — candidates for cleanup

## Important Rules

- **Admin operations require admin credentials** — user management needs admin-level CML access
- **Never share passwords in Slack** — report usernames only, instruct admin to share credentials securely
- **Check resources before big labs** — don't let users build labs that exceed server capacity
- **Monitor licensing** — CML has node count limits; stay within license boundaries
- **Record in GAIT** — log all admin operations for audit trail

## Environment Variables

- `CML_URL` — CML server URL
- `CML_USERNAME` — CML username (admin for full access)
- `CML_PASSWORD` — CML password
- `CML_VERIFY_SSL` — Verify SSL certificate (true/false)
