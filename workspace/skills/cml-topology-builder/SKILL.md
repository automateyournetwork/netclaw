---
name: cml-topology-builder
description: Build CML topologies — add nodes, create interfaces, wire links, set link conditioning, add annotations
version: 1.0.0
tags: [cml, topology, nodes, links, interfaces]
---

# CML Topology Builder

Build network topologies in Cisco Modeling Labs from natural language. Add nodes, create interfaces, wire links, set bandwidth/delay/loss conditions, and annotate the topology with visual documentation.

## MCP Server

- **Command**: `cml-mcp` (pip-installed, stdio transport)
- **Requires**: `CML_URL`, `CML_USERNAME`, `CML_PASSWORD` environment variables

## Available Tools

### Node Management

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `get_node_defs` | none | List all available node definitions (IOSv, NX-OS, IOS-XR, etc.) |
| `create_node` | `lab_id`/`lab_title`, `node_def`, `label`, `x`, `y` | Add a node to a lab |
| `get_nodes` | `lab_id`/`lab_title` | List all nodes in a lab |
| `get_node` | `lab_id`/`lab_title`, `node_id`/`node_label` | Get details of a specific node |

### Interface Management

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `create_interface` | `lab_id`/`lab_title`, `node_id`/`node_label`, `slot?` | Create a new interface on a node |
| `get_interfaces` | `lab_id`/`lab_title`, `node_id`/`node_label` | List all interfaces on a node |
| `get_interface` | `lab_id`/`lab_title`, `node_id`/`node_label`, `interface_id`/`interface_label` | Get interface details |

### Link Management

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `create_link` | `lab_id`/`lab_title`, `src_node`/`src_label`, `src_intf`, `dst_node`/`dst_label`, `dst_intf` | Create a link between two interfaces |
| `get_links` | `lab_id`/`lab_title` | List all links in a lab |
| `get_link` | `lab_id`/`lab_title`, `link_id` | Get link details |
| `set_link_condition` | `lab_id`/`lab_title`, `link_id`, `bandwidth?`, `latency?`, `jitter?`, `loss?` | Set link conditioning (WAN simulation) |
| `set_link_state` | `lab_id`/`lab_title`, `link_id`, `state` | Set link state (up/down) — simulate link failures |

### Annotations

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `create_annotation` | `lab_id`/`lab_title`, `annotation_type`, `content`, `x`, `y`, `width?`, `height?` | Add a text/shape annotation |
| `get_annotations` | `lab_id`/`lab_title` | List all annotations |
| `delete_annotation` | `lab_id`/`lab_title`, `annotation_id` | Remove an annotation |

## Available Node Definitions

Common node types available in CML (use `get_node_defs` to get the full list):

| Node Definition ID | Description | Typical Use |
|--------------------|-------------|-------------|
| `iosv` | Cisco IOSv (IOS 15.x) | Routing, switching labs |
| `iosvl2` | Cisco IOSv L2 | Layer 2 switching labs |
| `iosxrv9000` | Cisco IOS XR 9000v | SP, MPLS, Segment Routing |
| `nxosv9000` | Cisco NX-OS 9000v | Data center, VXLAN |
| `csr1000v` | Cisco CSR 1000v (IOS-XE) | SD-WAN, routing |
| `cat8000v` | Cisco Catalyst 8000v | Enterprise routing |
| `asav` | Cisco ASAv | Firewall labs |
| `server` | Ubuntu/Alpine server | Traffic gen, testing |
| `external_connector` | External bridge | Connect lab to host/internet |
| `unmanaged_switch` | Unmanaged L2 switch | Simple L2 connectivity |
| `wan_emulator` | WAN emulator | Add latency/loss between nodes |

## Workflow: Build Topology from Description

When the user describes a topology:

1. **Create the lab** (or get an existing one via `get_lab`)
2. **Get node definitions**: `get_node_defs` to know what's available
3. **Plan the layout**: Calculate x,y coordinates for visual placement
   - Use a grid layout: 200px spacing horizontally, 200px vertically
   - Group by role: core in center, edge on sides, servers at bottom
4. **Create nodes**: `create_node` for each device with meaningful labels
5. **Create interfaces**: `create_interface` for each connection point
6. **Wire links**: `create_link` to connect interface pairs
7. **Set conditions** (if requested): `set_link_condition` for WAN links
8. **Add annotations**: `create_annotation` for labels, IP addressing plans
9. **Report the topology**: List all nodes, interfaces, and links

## Layout Guidelines

When placing nodes, use this visual grid approach:

```
Topology Layout (x, y coordinates):

Layer 0 (Top):     Core routers         y=100
Layer 1:           Distribution          y=300
Layer 2:           Access / Leaf         y=500
Layer 3 (Bottom):  Servers / Endpoints   y=700

x spacing: 200px between nodes in the same layer
Center the topology: start x at 100, distribute evenly
```

Example for a 2-spine, 4-leaf topology:
```
Spine1: (300, 100)    Spine2: (500, 100)
Leaf1:  (100, 300)    Leaf2:  (300, 300)    Leaf3:  (500, 300)    Leaf4:  (700, 300)
Srv1:   (100, 500)    Srv2:   (300, 500)    Srv3:   (500, 500)    Srv4:   (700, 500)
```

## Link Conditioning

Use `set_link_condition` to simulate real-world WAN characteristics:

| Scenario | Bandwidth | Latency | Jitter | Loss |
|----------|-----------|---------|--------|------|
| LAN | (none) | (none) | (none) | (none) |
| Metro Ethernet | 100 Mbps | 5 ms | 1 ms | 0% |
| WAN (good) | 50 Mbps | 20 ms | 5 ms | 0.1% |
| WAN (poor) | 10 Mbps | 100 ms | 20 ms | 1% |
| Satellite | 5 Mbps | 300 ms | 50 ms | 2% |
| Congested link | 1 Mbps | 200 ms | 100 ms | 5% |

## Workflow: Annotate Topology

After building a topology, add visual documentation:

1. **Title annotation**: Lab name and purpose at the top
2. **IP addressing**: Annotation blocks showing subnet assignments per link
3. **AS numbers**: Label BGP AS boundaries
4. **Area labels**: Mark OSPF areas, VRF names, VLAN IDs
5. **Notes**: Any special instructions or test scenarios

## Workflow: Simulate Link Failure

When testing network resilience:

1. **Get the link**: `get_links` to find the link ID between the two nodes
2. **Capture baseline**: Use `execute_command` to check routing tables before failure
3. **Bring link down**: `set_link_state` with state "down"
4. **Observe convergence**: Execute show commands on affected nodes (OSPF neighbors, BGP summary, routing table)
5. **Optionally capture traffic**: Use cml-packet-capture to capture reconvergence traffic
6. **Restore link**: `set_link_state` with state "up"
7. **Verify recovery**: Confirm routing adjacencies re-establish
8. **Report**: Document failover/failback time and behavior

## Important Rules

- **Always use `get_node_defs` first** to verify available node types before creating nodes
- **Create interfaces before links** — you need interface IDs to wire links
- **Use descriptive labels** — "R1-Core" not "Node1"
- **Plan before building** — figure out the full topology before starting to create nodes
- **Lab must be STOPPED to add nodes** — cannot modify topology of a running lab
- **Position nodes logically** — hierarchical layout makes the topology readable in CML UI
- **Record in GAIT** — log topology creation for audit trail
