---
name: blender-3d-viz
description: "Create 3D network topology visualizations in Blender from CDP/LLDP neighbor data"
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3", "uvx"]
      env: ["BLENDER_HOST"]
---

# Blender 3D Network Visualization

Create stunning 3D network topology visualizations in Blender from CDP/LLDP neighbor data. Network engineers can request topology drawings via natural language, and NetClaw translates neighbor discovery data into 3D rendering commands.

## When to Use

- Visualizing network topology in 3D for presentations
- Creating topology diagrams from CDP/LLDP neighbor data
- Exporting network diagrams as PNG images
- Customizing device colors and adding labels
- Demonstrating network architecture to stakeholders

## MCP Server

- **Server**: `blender-mcp` (community MCP via uvx)
- **Command**: `uvx blender-mcp` (stdio transport)
- **Host**: Windows running Blender with BlenderMCP addon (port 9876)
- **Requirements**: Blender 3.0+, BlenderMCP addon installed and connected

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `get_scene_info` | None | Returns current Blender scene objects |
| `create_object` | type, name, location, scale | Creates primitives (cube, sphere, cylinder) |
| `modify_object` | name, position?, rotation?, scale? | Transform position/rotation/scale |
| `set_material` | object_name, color, metallic?, roughness? | Apply colors and materials |
| `execute_blender_code` | code | Run arbitrary Python in Blender |

## Workflow Examples

### Draw Network Topology

```bash
# Draw topology from CDP/LLDP data
"Draw the network topology in Blender using CDP data"

# Visualize neighbors for a specific device
"Visualize the CDP neighbors for core-rtr-01 in 3D"

# Create diagram from LLDP data
"Create a 3D network diagram from the LLDP data"

# Quick topology request
"Show me the network topology in Blender"
```

### Export Visualization

```bash
# Export as PNG
"Export the Blender scene as topology.png"

# Save the diagram
"Save the network diagram as a PNG file"

# Render to image
"Render the topology to an image"
```

### Customize Visualization

```bash
# Color customization
"Color router-1 red"
"Make all switches purple"
"Change the color of the firewalls to orange"

# Add labels
"Add labels to all devices"
"Label each device with its hostname"

# Highlighting
"Highlight router-1"
"Make core-rtr-01 stand out"
```

### Scene Management

```bash
# Clear scene
"Clear the Blender scene"
"Reset the 3D view"

# Query scene
"What objects are in the Blender scene?"
"List the devices in Blender"
```

## Device Color Mapping

| Device Type | Color | RGB |
|-------------|-------|-----|
| Router | Blue | (0.2, 0.4, 0.8) |
| Switch | Green | (0.2, 0.7, 0.3) |
| Firewall | Red | (0.8, 0.2, 0.2) |
| Access Point | Yellow | (0.9, 0.8, 0.2) |
| Unknown | Gray | (0.5, 0.5, 0.5) |

Device types are inferred from hostnames:
- Contains "rtr" or "router" → Router
- Contains "sw" or "switch" → Switch
- Contains "fw" or "firewall" or "asa" → Firewall
- Contains "ap" or "wap" or "wireless" → Access Point

## Integration with Other Skills

- **pyats-run**: Query CDP/LLDP neighbor data from live devices
- **suzieq-show**: Query network state from SuzieQ observability platform
- **canvas-a2ui**: Alternative 2D visualization in chat

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| CONNECTION_FAILED | Blender not running or addon not connected | Start Blender, click 'Connect to Claude' in BlenderMCP panel |
| ADDON_NOT_READY | Addon not connected | Press 'N' in Blender, find BlenderMCP tab, click 'Connect' |
| NO_CDP_DATA | No neighbor data available | Query network devices first via pyats-run or suzieq-show |
| TIMEOUT | First command may timeout | This is normal - retry the same command |
| EXPORT_FAILED | Export failed (window minimized) | Ensure Blender window is visible |

## Notes

- Read-only operations - no ServiceNow CR gating required
- Maximum 25 devices rendered per topology (performance limit)
- First command may timeout - subsequent commands are faster
- Requires Windows running Blender (WSL connectivity to Windows host)
- All operations logged to GAIT audit trail
