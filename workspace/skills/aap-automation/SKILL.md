---
name: aap-automation
description: "Red Hat Ansible Automation Platform — inventory management, job template execution, project SCM sync, ad-hoc commands, host management, Galaxy content discovery. Use when automating infrastructure with Ansible, running playbooks, managing inventories, or searching for Ansible collections and roles."
version: 1.0.0
license: Apache-2.0
tags: [ansible, aap, automation, redhat, inventory, playbook, job-template]
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["AAP_URL", "AAP_TOKEN"] } } }
---

# Ansible Automation Platform Operations

## MCP Server

- **Repository**: [sibilleb/AAP-Enterprise-MCP-Server](https://github.com/sibilleb/AAP-Enterprise-MCP-Server)
- **Transport**: stdio (Python via `uv run ansible.py`)
- **Install**: `git clone` + `uv sync` (or `pip install -e .`)
- **Requires**: `AAP_URL`, `AAP_TOKEN`

## Available Tools (45)

### Inventory & Host Management (11)

| Tool | What It Does |
|------|-------------|
| `list_inventories` | Retrieve all inventories from AAP |
| `get_inventory` | Fetch details for a specific inventory by ID |
| `create_inventory` | Create a new inventory with organization and configuration |
| `delete_inventory` | Remove an inventory from the platform |
| `list_hosts` | List all hosts within a specific inventory |
| `get_host_details` | Get comprehensive information about a host |
| `get_host_facts` | Obtain gathered facts for a host |
| `add_host_to_inventory` | Add a new host with optional variables |
| `update_host` | Modify host properties including variables and status |
| `delete_host` | Remove a host from inventory |
| `get_failed_hosts` | List hosts with active failures |

### Group Management (6)

| Tool | What It Does |
|------|-------------|
| `list_groups` | Show all groups in an inventory |
| `get_group_details` | Retrieve group information |
| `create_group` | Create a new group within an inventory |
| `add_host_to_group` | Associate a host with a group |
| `remove_host_from_group` | Disassociate a host from a group |
| `get_host_groups` | List all groups containing a host |

### Job & Template Management (8)

| Tool | What It Does |
|------|-------------|
| `list_job_templates` | List all available job templates |
| `get_job_template` | Get details for a specific job template |
| `create_job_template` | Create a new job template with playbook configuration |
| `run_job` | Execute a job template with optional extra variables |
| `list_jobs` | Show all jobs in the platform |
| `list_recent_jobs` | Filter jobs by timeframe |
| `job_status` | Check current status of a job |
| `job_logs` | Retrieve execution logs for a job |

### Project Management (7)

| Tool | What It Does |
|------|-------------|
| `list_projects` | List all projects |
| `get_project` | Get project details |
| `create_project` | Create a project with SCM configuration |
| `update_project` | Trigger an SCM sync |
| `list_project_updates` | Show all project update jobs |
| `get_project_update` | Get status of an update job |
| `get_project_update_logs` | Retrieve logs from an SCM sync |

### Inventory Sources (6)

| Tool | What It Does |
|------|-------------|
| `list_inventory_sources` | Show all dynamic inventory sources |
| `get_inventory_source` | Get details for a specific source |
| `create_inventory_source` | Create a dynamic inventory source |
| `update_inventory_source` | Modify an existing source |
| `delete_inventory_source` | Remove an inventory source |
| `sync_inventory_source` | Trigger a manual sync |

### Ad-Hoc Commands (3)

| Tool | What It Does |
|------|-------------|
| `run_adhoc_command` | Execute Ansible commands directly against hosts |
| `get_adhoc_command_status` | Check execution status |
| `get_adhoc_command_output` | Retrieve command output |

### Galaxy Search (4)

| Tool | What It Does |
|------|-------------|
| `search_galaxy_collections` | Search Ansible Galaxy for collections |
| `search_galaxy_roles` | Search Galaxy for roles |
| `get_collection_details` | Get comprehensive collection info |
| `get_role_details` | Get detailed role info |

## Key Concepts

| Concept | What It Means |
|---------|---------------|
| **AAP** | Ansible Automation Platform — Red Hat's enterprise automation controller |
| **Inventory** | Collection of managed hosts organized by groups |
| **Job Template** | Reusable playbook execution definition with parameters |
| **Project** | SCM-backed collection of Ansible playbooks |
| **Ad-Hoc Command** | One-off Ansible module execution against hosts |
| **Inventory Source** | Dynamic inventory pulled from cloud/CMDB/external systems |

## Workflow: Run a Playbook Against Inventory

1. **List inventories**: `list_inventories` — find the target inventory
2. **List hosts**: `list_hosts` — verify target hosts are present
3. **Find template**: `list_job_templates` — locate the playbook to run
4. **Execute**: `run_job` — launch the job template with extra vars if needed
5. **Monitor**: `job_status` — poll until completion
6. **Review**: `job_logs` — check execution output
7. **Report**: Summarize success/failure per host

## Workflow: Inventory Audit

1. **List inventories**: `list_inventories` — enumerate all inventories
2. **For each inventory**: `list_hosts` — count and list hosts
3. **Check failures**: `get_failed_hosts` — identify hosts with active failures
4. **Get facts**: `get_host_facts` — verify host data is current
5. **Cross-reference**: Compare with NetBox or Nautobot source of truth
6. **Report**: Inventory coverage, stale hosts, failed hosts

## Workflow: Project SCM Sync

1. **List projects**: `list_projects` — find the project
2. **Sync**: `update_project` — trigger SCM pull
3. **Monitor**: `get_project_update` — check sync status
4. **Review logs**: `get_project_update_logs` — verify no errors
5. **Report**: Sync success/failure, last commit pulled

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `aap-eda` | AAP job execution + EDA event-driven triggers |
| `aap-lint` | Validate playbooks before running them through AAP |
| `netbox-reconcile` | Cross-reference AAP inventories with NetBox DCIM |
| `nautobot-sot` | AAP inventory validation against Nautobot IPAM |
| `servicenow-change-workflow` | ServiceNow CR gating before AAP job execution |
| `github-ops` | Commit playbooks and inventory changes to Git |
| `pyats-health-check` | Device health verification before/after AAP automation |
| `gait-session-tracking` | Audit trail for all AAP operations |

## Environment Variables

- `AAP_URL` — AAP Controller API endpoint (e.g., `https://aap.example.com/api/controller/v2`)
- `AAP_TOKEN` — AAP API token (Write scope)

## Important Rules

- **Job execution changes infrastructure** — always verify the target inventory and template before running
- **ServiceNow CR** — gate job execution behind change requests in production
- **Record in GAIT** — log all AAP operations for audit trail
- **SSL handling** — self-signed certificates are automatically handled for lab environments
