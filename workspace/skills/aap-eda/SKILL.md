---
name: aap-eda
description: "Event-Driven Ansible (EDA) — activation lifecycle, rulebook management, decision environments, event stream monitoring. Use when managing event-driven automation triggers, enabling/disabling activations, or reviewing EDA rulebooks."
version: 1.0.0
license: Apache-2.0
tags: [ansible, eda, event-driven, redhat, automation, rulebook]
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["EDA_URL", "EDA_TOKEN"] } } }
---

# Event-Driven Ansible (EDA) Operations

## MCP Server

- **Repository**: [sibilleb/AAP-Enterprise-MCP-Server](https://github.com/sibilleb/AAP-Enterprise-MCP-Server)
- **Transport**: stdio (Python via `uv run eda.py`)
- **Install**: `git clone` + `uv sync` (or `pip install -e .`)
- **Requires**: `EDA_URL`, `EDA_TOKEN`

## Available Tools (12)

### Activation Management (7)

| Tool | What It Does |
|------|-------------|
| `list_activations` | List all activations in EDA |
| `get_activation` | Retrieve details for a specific activation by ID |
| `create_activation` | Create a new activation |
| `enable_activation` | Enable a disabled activation |
| `disable_activation` | Disable an active activation |
| `restart_activation` | Restart an activation |
| `delete_activation` | Delete an activation |

### Rulebooks & Environments (3)

| Tool | What It Does |
|------|-------------|
| `list_rulebooks` | List all rulebooks in EDA |
| `get_rulebook` | Retrieve details of a specific rulebook |
| `list_decision_environments` | List all decision environments |

### Event Streams & Environments (2)

| Tool | What It Does |
|------|-------------|
| `create_decision_environment` | Add a new decision environment |
| `list_event_streams` | List all event streams |

## Key Concepts

| Concept | What It Means |
|---------|---------------|
| **EDA** | Event-Driven Ansible — reactive automation triggered by events |
| **Activation** | A running instance of a rulebook processing events |
| **Rulebook** | YAML-defined rules mapping events to Ansible actions |
| **Decision Environment** | Container image with collections and dependencies for EDA |
| **Event Stream** | Source of events fed into EDA for processing |

## Workflow: Activation Management

1. **List activations**: `list_activations` — see all current activations and their state
2. **Inspect**: `get_activation` — review activation details (rulebook, decision env, status)
3. **Lifecycle**: `enable_activation`, `disable_activation`, `restart_activation` as needed
4. **Report**: Activation health summary

## Workflow: Event-Driven Automation Audit

1. **List activations**: `list_activations` — enumerate all EDA activations
2. **List rulebooks**: `list_rulebooks` — review available automation rules
3. **Check environments**: `list_decision_environments` — verify container images
4. **Monitor streams**: `list_event_streams` — confirm event sources are active
5. **Report**: EDA health, dormant activations, orphaned rulebooks

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `aap-automation` | EDA triggers → AAP job template execution |
| `aap-lint` | Validate rulebook playbook actions before activation |
| `servicenow-change-workflow` | ServiceNow CR before enabling EDA activations in production |
| `gait-session-tracking` | Audit trail for EDA lifecycle changes |
| `slack-network-alerts` | EDA event notifications via Slack |

## Environment Variables

- `EDA_URL` — EDA API endpoint (e.g., `https://aap.example.com/api/eda/v1`)
- `EDA_TOKEN` — EDA API token (can match AAP_TOKEN)

## Important Rules

- **Activations process events in real-time** — disabling/enabling affects live automation
- **ServiceNow CR** — gate activation changes behind change requests in production
- **Record in GAIT** — log all EDA operations for audit trail
