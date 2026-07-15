---
name: gns3-node-operations
description: "Manage GNS3 nodes - add from templates, start/stop/suspend/reload, console access"
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["GNS3_URL", "GNS3_USER", "GNS3_PASSWORD"]
---

# GNS3 Node Operations

Manage network device nodes in GNS3 projects. Add devices from templates, control power state, and access consoles for configuration and troubleshooting.

## When to Use

- Adding network devices (routers, switches, firewalls) to a lab
- Starting or stopping individual nodes
- Reloading nodes after configuration changes
- Suspending nodes to save state
- Starting or stopping all nodes in a project
- Getting console access information for device configuration
- Isolating nodes for testing without deleting links

## MCP Server

- **Command**: `python3 -u mcp-servers/gns3-mcp-server/gns3_mcp_server.py` (stdio transport)
- **Requires**: `GNS3_URL`, `GNS3_USER`, `GNS3_PASSWORD` environment variables

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `gns3_list_nodes` | project_id | List all nodes in a project with status |
| `gns3_create_node` | project_id, template, name?, x?, y?, compute_id? | Create node from template |
| `gns3_start_node` | project_id, node_id | Start a node (power on) |
| `gns3_stop_node` | project_id, node_id | Stop a node (power off) |
| `gns3_suspend_node` | project_id, node_id | Suspend a node (save state) |
| `gns3_reload_node` | project_id, node_id | Reload a node (restart) |
| `gns3_bulk_node_action` | project_id, action | Apply action to all nodes (start/stop/suspend/reload) |
| `gns3_get_node_console` | project_id, node_id | Get console connection info |

## Utility Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `gns3_list_templates` | None | List available node templates on the server |
| `gns3_list_computes` | None | List available compute servers |

## Workflow Examples

### Build a Lab Topology

```bash
# List available templates
"List GNS3 templates"

# Add devices to the lab
"Add a Cisco IOSv router to routing-test"
"Add an Arista vEOS switch to routing-test"
"Add a VPCS host to routing-test"
```

### Control Node Power State

```bash
# Start individual nodes
"Start router1 in routing-test"

# Start all nodes at once
"Start all nodes in routing-test"

# Stop when done
"Stop all nodes in routing-test"
```

### Console Access

```bash
# Get console connection info
"Show console info for router1 in routing-test"
# Returns: telnet 192.168.1.100 5000
```

### Reload After Config Changes

```bash
# Reload a router after making changes
"Reload router1 in routing-test"
```

## Template Fuzzy Matching

The `gns3_create_node` tool supports fuzzy matching for template names:

- "Cisco IOSv" matches "Cisco IOSv 15.9(3)M2"
- "vEOS" matches "Arista vEOS 4.28.0F"
- "VPCS" matches "VPCS" exactly

## Integration with Other Skills

- **gns3-project-lifecycle**: Create a project first
- **gns3-link-management**: Connect nodes after creation
- **gns3-packet-capture**: Capture traffic on links between nodes

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| GNS3_NOT_FOUND | Node or project doesn't exist | Check name/ID |
| GNS3_CONFLICT | Node already running/stopped | Check current state first |
| GNS3_VALIDATION | Invalid template name | Use gns3_list_templates to find valid names |

## Notes

- Nodes can be referenced by name or UUID
- Template matching is case-insensitive
- Bulk actions affect all nodes in the project
- Console info varies by node type (telnet, VNC, HTTP)
- All operations logged to GAIT audit trail
