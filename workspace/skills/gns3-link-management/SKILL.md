---
name: gns3-link-management
description: "Manage GNS3 links - connect/disconnect node interfaces, isolate nodes"
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["GNS3_URL", "GNS3_USER", "GNS3_PASSWORD"]
---

# GNS3 Link Management

Create and manage links between node interfaces in GNS3 projects. Build network topologies by connecting devices and isolate nodes for testing.

## When to Use

- Connecting two network devices together
- Building out a network topology
- Viewing existing connections in a lab
- Removing links between devices
- Isolating a node without deleting its links
- Re-enabling links after isolation testing

## MCP Server

- **Command**: `python3 -u mcp-servers/gns3-mcp-server/gns3_mcp_server.py` (stdio transport)
- **Requires**: `GNS3_URL`, `GNS3_USER`, `GNS3_PASSWORD` environment variables

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `gns3_list_links` | project_id | List all links with connected nodes and interfaces |
| `gns3_create_link` | project_id, node1, port1, node2, port2 | Create a link between two interfaces |
| `gns3_delete_link` | project_id, link_id | Delete a link |
| `gns3_isolate_node` | project_id, node_id, isolate | Disable/enable all links to a node |

## Interface Name Formats

The tools support multiple interface naming conventions:

| Format | Example | Adapter | Port |
|--------|---------|---------|------|
| eth# | eth0, eth1 | 0 | 0, 1 |
| Ethernet# | Ethernet0 | 0 | 0 |
| Gi#/# | Gi0/0, Gi0/1 | 0 | 0, 1 |
| GigabitEthernet#/# | GigabitEthernet0/0 | 0 | 0 |
| Fa#/# | Fa0/0, Fa0/1 | 0 | 0, 1 |
| e# | e0, e1 | 0 | 0, 1 |
| port# | port0, port1 | 0 | 0, 1 |
| #/# | 0/0, 0/1 | 0 | 0, 1 |

## Workflow Examples

### Build a Topology

```bash
# Connect router to switch
"Connect router1 Gi0/0 to switch1 eth0 in routing-test"

# Connect switch to another router
"Connect switch1 eth1 to router2 Gi0/0 in routing-test"

# Connect hosts to switch
"Connect host1 eth0 to switch1 eth2 in routing-test"
```

### View Topology

```bash
# List all connections
"List all links in routing-test"
```

### Isolate for Testing

```bash
# Isolate a node (disable all its links)
"Isolate router1 in routing-test"

# Test behavior with router1 disconnected...

# Re-enable links
"Unisolate router1 in routing-test"
```

### Clean Up

```bash
# Remove a specific link
"Delete the link between router1 and switch1 in routing-test"
```

## Integration with Other Skills

- **gns3-project-lifecycle**: Create project first
- **gns3-node-operations**: Add nodes before connecting them
- **gns3-packet-capture**: Capture traffic on links

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| GNS3_NOT_FOUND | Node or link doesn't exist | Check names/IDs |
| GNS3_CONFLICT | Interface already connected | Check existing links first |
| GNS3_VALIDATION | Invalid interface format | Use supported naming conventions |

## Notes

- Links can only be created between existing nodes
- Each interface can only have one link
- Isolating a node disables links without deleting them
- Link IDs are UUIDs - use `gns3_list_links` to find them
- All operations logged to GAIT audit trail
