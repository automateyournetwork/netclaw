# MCP Tool Contracts: Unreal Engine 5.8 Network Visualization

**Feature**: 044-ue5-mcp-network-viz
**Date**: 2026-06-28

## Overview

This document defines the MCP tool interfaces used by the ue5-network-viz skill. These are contracts with the upstream Unreal Engine 5.8 MCP server.

## Transport

| Property | Value |
|----------|-------|
| Protocol | HTTP + Server-Sent Events |
| URL | `http://127.0.0.1:8000/mcp` |
| Content-Type | `application/json` |

## Tool Search Mode

UE5 MCP uses tool search mode by default. All tool calls go through meta-tools:

### list_toolsets

**Purpose**: Discover available toolsets.

**Request**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "list_toolsets",
    "arguments": {}
  }
}
```

**Response**:
```json
{
  "toolsets": [
    {"name": "ActorTools", "description": "Tools for managing actors"},
    {"name": "MaterialInstanceTools", "description": "Tools for materials"},
    {"name": "SceneTools", "description": "Tools for scene management"},
    {"name": "CameraTools", "description": "Tools for camera control"}
  ]
}
```

---

### describe_toolset

**Purpose**: Get tool schemas for a specific toolset.

**Request**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "describe_toolset",
    "arguments": {
      "name": "ActorTools"
    }
  }
}
```

**Response**:
```json
{
  "toolset": "ActorTools",
  "tools": [
    {
      "name": "spawn_actor",
      "description": "Spawn an actor in the level",
      "parameters": {
        "type": "object",
        "properties": {
          "class": {"type": "string", "description": "Actor class path"},
          "name": {"type": "string", "description": "Actor label"},
          "location": {"type": "array", "items": {"type": "number"}},
          "rotation": {"type": "array", "items": {"type": "number"}},
          "scale": {"type": "array", "items": {"type": "number"}}
        },
        "required": ["class"]
      }
    }
  ]
}
```

---

### call_tool

**Purpose**: Execute a tool within a toolset.

**Request**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "call_tool",
    "arguments": {
      "toolset": "ActorTools",
      "tool": "spawn_actor",
      "args": {
        "class": "/Engine/BasicShapes/Cube.Cube",
        "name": "netclaw_device_router-1",
        "location": [0, 0, 100],
        "scale": [50, 50, 50]
      }
    }
  }
}
```

**Response**:
```json
{
  "success": true,
  "actor_name": "netclaw_device_router-1"
}
```

---

## ActorTools

### spawn_actor

**Purpose**: Create an actor in the scene.

**Parameters**:
```json
{
  "class": "string (required) - UE5 class path",
  "name": "string (optional) - Actor label",
  "location": "[x, y, z] (optional) - World position, default [0,0,0]",
  "rotation": "[pitch, yaw, roll] (optional) - Euler rotation in degrees",
  "scale": "[x, y, z] (optional) - Scale factors, default [1,1,1]",
  "tags": "[string] (optional) - Actor tags"
}
```

**Common Classes for Network Visualization**:
- `/Engine/BasicShapes/Cube.Cube` - Network devices
- `/Engine/BasicShapes/Sphere.Sphere` - Endpoints
- `/Engine/BasicShapes/Cylinder.Cylinder` - Simple links

**Example - Device**:
```json
{
  "class": "/Engine/BasicShapes/Cube.Cube",
  "name": "netclaw_device_core-rtr-01",
  "location": [0, 0, 100],
  "scale": [50, 50, 50],
  "tags": ["netclaw", "device", "router"]
}
```

---

### destroy_actor

**Purpose**: Remove an actor from the scene.

**Parameters**:
```json
{
  "name": "string (required) - Actor label to destroy"
}
```

**Response**:
```json
{
  "success": true
}
```

**Usage**: Remove deleted network devices.

---

### set_actor_transform

**Purpose**: Update an actor's position, rotation, or scale.

**Parameters**:
```json
{
  "name": "string (required) - Actor label",
  "location": "[x, y, z] (optional)",
  "rotation": "[pitch, yaw, roll] (optional)",
  "scale": "[x, y, z] (optional)"
}
```

**Usage**: Reposition devices after layout recalculation.

---

### get_all_actors_with_tag

**Purpose**: Find all actors with a specific tag.

**Parameters**:
```json
{
  "tag": "string (required) - Tag to search for"
}
```

**Response**:
```json
{
  "actors": [
    {
      "name": "netclaw_device_router-1",
      "class": "/Engine/BasicShapes/Cube.Cube",
      "location": [0, 0, 100],
      "tags": ["netclaw", "device", "router"]
    }
  ]
}
```

**Usage**: Query existing NetClaw actors for incremental updates.

---

## MaterialInstanceTools

### create_material_instance

**Purpose**: Create a dynamic material instance.

**Parameters**:
```json
{
  "parent": "string (required) - Parent material path",
  "name": "string (required) - Instance name"
}
```

**Response**:
```json
{
  "success": true,
  "material_name": "MI_Router_Blue"
}
```

**Usage**: Create materials for each device type.

---

### set_material_parameter

**Purpose**: Set a parameter on a material instance.

**Parameters**:
```json
{
  "material": "string (required) - Material instance name",
  "parameter": "string (required) - Parameter name",
  "value": "any (required) - Parameter value"
}
```

**Common Parameters**:
- `BaseColor`: `[r, g, b]` - RGB color (0-1 range)
- `Metallic`: `float` - 0-1
- `Roughness`: `float` - 0-1
- `EmissiveColor`: `[r, g, b]` - For glowing effects
- `EmissiveIntensity`: `float` - Glow brightness

**Example - Set Router Color**:
```json
{
  "material": "MI_Router",
  "parameter": "BaseColor",
  "value": [0.2, 0.4, 0.8]
}
```

**Example - Critical Alert Glow**:
```json
{
  "material": "MI_Router",
  "parameter": "EmissiveColor",
  "value": [1.0, 0.0, 0.0]
},
{
  "material": "MI_Router",
  "parameter": "EmissiveIntensity",
  "value": 5.0
}
```

---

### apply_material_to_actor

**Purpose**: Apply a material to an actor.

**Parameters**:
```json
{
  "actor_name": "string (required)",
  "material": "string (required) - Material instance name",
  "slot": "int (optional) - Material slot index, default 0"
}
```

---

## SceneTools

### clear_actors_with_tag

**Purpose**: Remove all actors with a specific tag.

**Parameters**:
```json
{
  "tag": "string (required)"
}
```

**Usage**: Clear all NetClaw actors before full re-render.

```json
{
  "tag": "netclaw"
}
```

---

### get_scene_info

**Purpose**: Get current scene state.

**Parameters**: None

**Response**:
```json
{
  "level_name": "string",
  "actor_count": 42,
  "selected_actors": ["actor_name"]
}
```

---

## CameraTools

### set_camera_location

**Purpose**: Move the editor viewport camera.

**Parameters**:
```json
{
  "location": "[x, y, z] (required)",
  "rotation": "[pitch, yaw, roll] (optional)"
}
```

---

### focus_on_actor

**Purpose**: Frame an actor in the viewport.

**Parameters**:
```json
{
  "actor_name": "string (required)"
}
```

**Usage**: "Focus on router-1" command.

---

### get_camera_state

**Purpose**: Get current camera position (for preservation).

**Parameters**: None

**Response**:
```json
{
  "location": [x, y, z],
  "rotation": [pitch, yaw, roll],
  "fov": 90.0
}
```

---

## LightingTools

### set_directional_light

**Purpose**: Configure scene lighting.

**Parameters**:
```json
{
  "intensity": "float (optional)",
  "color": "[r, g, b] (optional)",
  "direction": "[x, y, z] (optional)"
}
```

**Usage**: Set up default lighting for topology scene.

---

## Error Handling Contract

All tools may return errors:

```json
{
  "error": true,
  "code": "string",
  "message": "string"
}
```

**Common Error Codes**:
- `ACTOR_NOT_FOUND`: Actor name doesn't exist
- `INVALID_CLASS`: Class path not valid
- `MATERIAL_NOT_FOUND`: Material instance doesn't exist
- `INVALID_PARAMETERS`: Parameter validation failed

## Skill-Level Command Mapping

| Natural Language | MCP Tool Sequence |
|------------------|-------------------|
| "Render my network in UE5" | `get_all_actors_with_tag` → (diff) → `spawn_actor` × N → `apply_material_to_actor` × N → `set_directional_light` |
| "Clear the scene" | `clear_actors_with_tag(netclaw)` |
| "Focus on router-1" | `focus_on_actor(netclaw_device_router-1)` |
| "Show device health" | `set_material_parameter` × N (update colors based on status) |
| "Fly through the network" | Scripted `set_camera_location` sequence |
| "What devices are rendered?" | `get_all_actors_with_tag(netclaw)` → filter devices |
| "Update link status" | `set_material_parameter` on link materials |

## Connection Health Check

Before any operation, verify UE5 MCP connectivity:

```json
{
  "method": "tools/list"
}
```

Expected: JSON-RPC response with tools or meta-tools.

**Timeout**: 5 seconds
**On failure**: Report "UE5 MCP server not reachable at {url}. Please ensure Unreal Editor is running with MCP plugin enabled."
