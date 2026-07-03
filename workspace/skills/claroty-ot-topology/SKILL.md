---
name: claroty-ot-topology
description: "Render Claroty xDome OT / IoT communication maps and zone segmentation as inline Canvas/A2UI topology, draw.io diagrams, and timeline summaries."
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["CLAROTY_API_URL", "CLAROTY_API_TOKEN"]
---

# Claroty OT Topology

Visualise the OT / IoT communication fabric observed by Claroty xDome — device-to-device edges, organisation zones, and OT activity timelines — using Canvas / A2UI for inline chat rendering and draw.io for exportable diagrams.

## When to Use

- Visualising how OT devices communicate (PLC ↔ HMI, RTU ↔ historian, etc.)
- Reviewing network segmentation zones and verifying Purdue-layer separation
- Producing an OT topology diagram for a CR or QBR deck
- Walking an activity timeline for a specific device during incident review
- Sanity-checking that newly deployed zones are reflected in observed traffic

## MCP Server

- **Server**: `claroty-mcp`
- **Command**: `python3 -u mcp-servers/claroty-mcp/claroty_mcp_server.py` (stdio transport)
- **Auth**: Bearer token via `CLAROTY_API_TOKEN`
- **ITSM**: This is a **read-only** skill — no ITSM gate required.

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `get_device_communication_map` | `device_id?, site_id?, limit?, offset?` | Device-to-device edges (src, dst, protocol, port, byte counts) |
| `list_organization_zones` | `limit?, offset?` | Network segmentation zones (id, name, device count) |
| `list_ot_activity_events` | `device_id?, site_id?, event_type?, start?, end?, limit?, offset?, max_items?` | OT activity / protocol observations |
| `list_devices` | (see `claroty-asset-inventory`) | Resolve device IDs ↔ human-friendly names for diagram labels |

Compose with:

- `canvas-network-viz` skill for inline Canvas / A2UI topology rendering
- `drawio-` skill for exportable `.drawio` / SVG diagrams
- `uml-` skill for nwdiag-style topology

## Workflow Examples

### Inline topology for a device

```
"Show me the communication map for device 7a2c... as an inline topology"
```

1. `get_device_communication_map(device_id="7a2c...")` → edges.
2. `list_devices(...)` to resolve neighbour device IDs to names.
3. Hand-off to `canvas-network-viz` to render the topology in chat with health-coloured nodes.

### Zone segmentation audit

```
"List all xDome zones and show their device counts"
```

Calls `list_organization_zones()`. The agent then optionally calls `list_devices` per zone to surface devices that should be in a stricter zone but aren't.

### Site-wide topology export

```
"Render a draw.io diagram of the OT topology at site warehouse-east"
```

1. `list_devices(site_id="warehouse-east")` → nodes.
2. `get_device_communication_map(site_id="warehouse-east")` → edges.
3. Hand off to the draw.io skill to produce an exportable `.drawio` file.

### OT activity timeline during incident review

```
"Show me OT activity events for device 7a2c between 09:00 and 11:00 today"
```

Calls `list_ot_activity_events(device_id="7a2c...", start="2026-06-08T09:00:00Z", end="2026-06-08T11:00:00Z")`. Optionally renders as a Canvas A2UI timeline.

## Rendering hand-offs

This skill is intentionally a **data + composition** skill — it does not own the rendering layer. For visual output:

- Inline chat: `canvas-network-viz` (topology map A2UI primitive)
- Exportable diagram: `drawio-` skill or `uml-` skill (nwdiag)
- Timeline: `canvas-network-viz` (timeline A2UI primitive)

This keeps Principle VII (Skill Modularity) intact — Claroty-specific knowledge stays here, generic rendering lives in the visualisation skills.
