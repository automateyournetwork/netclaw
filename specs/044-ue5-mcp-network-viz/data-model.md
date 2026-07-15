# Data Model: Unreal Engine 5.8 MCP Network Visualization

**Feature**: 044-ue5-mcp-network-viz
**Date**: 2026-06-28

## Overview

This document defines the data structures used for transforming network topology data into UE5 3D visualization commands.

## Entities

### NetworkDevice

Represents a network device to be rendered in 3D.

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `hostname` | string | Device hostname (unique identifier) | Topology data |
| `device_type` | DeviceType | Type of device | Inferred from hostname/model |
| `ip_addresses` | string[] | Management IP addresses | Topology/inventory |
| `model` | string? | Device model | Topology data |
| `vendor` | string? | Vendor name | Topology data |
| `interfaces` | Interface[] | Device interfaces | Topology data |
| `status` | DeviceStatus | Operational status | Telemetry |
| `utilization` | float? | CPU/memory utilization (0-100) | Telemetry |
| `position` | Vector3? | Calculated 3D position | Layout algorithm |

**Device Types**:
```
enum DeviceType {
  ROUTER = "router"
  SWITCH = "switch"
  FIREWALL = "firewall"
  ENDPOINT = "endpoint"
  ACCESS_POINT = "access_point"
  LOAD_BALANCER = "load_balancer"
  UNKNOWN = "unknown"
}
```

**Device Status**:
```
enum DeviceStatus {
  HEALTHY = "healthy"       // Green
  WARNING = "warning"       // Yellow
  CRITICAL = "critical"     // Red
  UNKNOWN = "unknown"       // Gray
  UNREACHABLE = "unreachable" // Pulsing red
}
```

**Type Inference Rules**:
- Contains "rtr", "router", "cr", "er" → ROUTER
- Contains "sw", "switch", "ds", "as" → SWITCH
- Contains "fw", "firewall", "asa", "ftd", "palo" → FIREWALL
- Contains "ap", "wap", "wireless", "wlc" → ACCESS_POINT
- Contains "lb", "f5", "bigip", "netscaler" → LOAD_BALANCER
- Contains "pc", "host", "server", "vm" → ENDPOINT
- Otherwise → UNKNOWN

### Interface

Represents a network interface on a device.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Interface name (e.g., "GigabitEthernet0/1") |
| `status` | InterfaceStatus | Up/down/admin-down |
| `speed` | int? | Speed in Mbps |
| `utilization` | float? | Current utilization (0-100) |
| `ip_address` | string? | IP address if assigned |

**Interface Status**:
```
enum InterfaceStatus {
  UP = "up"
  DOWN = "down"
  ADMIN_DOWN = "admin_down"
}
```

### NetworkLink

Represents a connection between two devices.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique link ID (`{source}_{target}`) |
| `source_device` | string | Source device hostname |
| `target_device` | string | Target device hostname |
| `source_interface` | string? | Interface on source device |
| `target_interface` | string? | Interface on target device |
| `status` | LinkStatus | Link operational status |
| `bandwidth` | int? | Link bandwidth in Mbps |
| `utilization` | float? | Current utilization (0-100) |
| `latency` | float? | Round-trip latency in ms |

**Link Status**:
```
enum LinkStatus {
  HEALTHY = "healthy"       // Green
  DEGRADED = "degraded"     // Yellow (high utilization or errors)
  DOWN = "down"             // Red
  UNKNOWN = "unknown"       // Gray
}
```

### TopologyGraph

Represents the complete network topology as a graph structure.

| Field | Type | Description |
|-------|------|-------------|
| `devices` | NetworkDevice[] | All devices in topology |
| `links` | NetworkLink[] | All connections between devices |
| `source` | string | Data source (e.g., "pyATS", "SuzieQ", "GNS3") |
| `timestamp` | datetime | When topology was collected |
| `total_device_count` | int | Original count before truncation |
| `is_truncated` | bool | True if exceeds device limit |

### UE5Actor

Represents a 3D actor in Unreal Engine (internal representation).

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | UE5 actor name (unique) |
| `actor_class` | string | UE5 class path |
| `position` | Vector3 | World location (X, Y, Z) |
| `rotation` | Rotator | Euler rotation (Pitch, Yaw, Roll) |
| `scale` | Vector3 | Scale factors |
| `material` | string? | Material instance name |
| `tags` | string[] | Actor tags (includes "netclaw") |
| `metadata` | dict | Custom metadata (hostname, device_type, etc.) |

**Actor Naming Convention**:
- Devices: `netclaw_device_{hostname}`
- Links: `netclaw_link_{source}_{target}`
- Labels: `netclaw_label_{hostname}`

### UE5Material

Represents a material instance in Unreal Engine.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Material instance name |
| `parent` | string | Parent material path |
| `base_color` | Color | RGB base color |
| `metallic` | float | Metallic value (0-1) |
| `roughness` | float | Roughness value (0-1) |
| `emissive` | Color? | Emissive color for glowing effects |
| `emissive_intensity` | float? | Emissive brightness |

### Vector3

3D coordinate or scale vector.

| Field | Type | Description |
|-------|------|-------------|
| `x` | float | X component (UE5: forward) |
| `y` | float | Y component (UE5: right) |
| `z` | float | Z component (UE5: up) |

### Rotator

Euler rotation in degrees.

| Field | Type | Description |
|-------|------|-------------|
| `pitch` | float | Rotation around Y axis |
| `yaw` | float | Rotation around Z axis |
| `roll` | float | Rotation around X axis |

### Color

Color representation (linear RGB, 0-1 range).

| Field | Type | Description |
|-------|------|-------------|
| `r` | float | Red (0.0-1.0) |
| `g` | float | Green (0.0-1.0) |
| `b` | float | Blue (0.0-1.0) |
| `a` | float | Alpha (0.0-1.0, default 1.0) |

## Color Mappings

### Device Type Colors

| DeviceType | Color | RGB | Hex |
|------------|-------|-----|-----|
| ROUTER | Blue | (0.2, 0.4, 0.8) | #3366CC |
| SWITCH | Green | (0.2, 0.7, 0.3) | #33B34D |
| FIREWALL | Red | (0.8, 0.2, 0.2) | #CC3333 |
| ACCESS_POINT | Yellow | (0.9, 0.8, 0.2) | #E6CC33 |
| LOAD_BALANCER | Purple | (0.6, 0.2, 0.8) | #9933CC |
| ENDPOINT | Gray | (0.5, 0.5, 0.5) | #808080 |
| UNKNOWN | White | (1.0, 1.0, 1.0) | #FFFFFF |

### Device Status Colors (Override)

When a device has a non-healthy status, these colors override the device type color:

| DeviceStatus | Color | RGB | Effect |
|--------------|-------|-----|--------|
| HEALTHY | (device type color) | - | Normal |
| WARNING | Orange | (1.0, 0.6, 0.0) | Pulsing glow |
| CRITICAL | Red | (1.0, 0.0, 0.0) | Bright emissive |
| UNREACHABLE | Dark Red | (0.5, 0.0, 0.0) | Flashing |
| UNKNOWN | Gray | (0.5, 0.5, 0.5) | Dimmed |

### Link Status Colors

| LinkStatus | Color | RGB | Visual Effect |
|------------|-------|-----|---------------|
| HEALTHY | Green | (0.2, 0.8, 0.2) | Solid |
| DEGRADED | Yellow | (1.0, 0.8, 0.0) | Animated particles |
| DOWN | Red | (0.8, 0.2, 0.2) | Dashed/broken |
| UNKNOWN | Gray | (0.5, 0.5, 0.5) | Thin/faded |

## Scene State

### NetworkScene

Represents the current UE5 scene state for incremental updates.

| Field | Type | Description |
|-------|------|-------------|
| `device_actors` | dict[str, UE5Actor] | hostname → actor mapping |
| `link_actors` | dict[str, UE5Actor] | link_id → actor mapping |
| `label_actors` | dict[str, UE5Actor] | hostname → label actor |
| `camera_state` | CameraState | Current camera position |
| `last_topology` | TopologyGraph | Last rendered topology |
| `last_update` | datetime | Last update timestamp |

### CameraState

Camera position and orientation for preservation during updates.

| Field | Type | Description |
|-------|------|-------------|
| `location` | Vector3 | Camera world position |
| `rotation` | Rotator | Camera rotation |
| `fov` | float | Field of view |
| `target` | Vector3? | Look-at target (if any) |

## Data Flow

```
Network Data Sources → TopologyGraph → Layout Algorithm → UE5Actors → MCP Tool Calls → UE5 Scene
         ↓                                                                                ↑
   Telemetry Stream ────────────────────────────────────────────────────────────────────────
                         (updates device/link status)
```

### Step 1: Collect Topology
```
Input: MCP queries to pyATS, SuzieQ, GNS3, CML, or similar
Output: TopologyGraph with devices and links (no positions yet)
```

### Step 2: Apply Layout
```
Input: TopologyGraph
Output: TopologyGraph with Vector3 positions for each device
Algorithm: Force-directed spring layout
```

### Step 3: Diff Against Scene
```
Input: New TopologyGraph + Current NetworkScene
Output:
  - Devices to add
  - Devices to remove
  - Devices to update
  - Links to add/remove/update
```

### Step 4: Generate UE5 Actors
```
Input: Topology diff
Output: UE5Actor definitions (devices as meshes, links as splines)
```

### Step 5: Execute via MCP
```
Input: UE5Actor definitions
Output: MCP tool calls to UE5 server
  - spawn_actor for new devices
  - destroy_actor for removed devices
  - set_actor_transform for position updates
  - set_material_parameter for status color changes
```

### Step 6: Continuous Updates (Telemetry)
```
Input: Telemetry events (syslog alerts, SNMP traps, link state changes)
Output: Targeted MCP calls to update specific actors
  - Event-driven: immediate color/status changes
  - Polling: periodic utilization visual updates
```

## Validation Rules

### NetworkDevice
- `hostname`: Required, non-empty, unique within topology
- `device_type`: Must be valid DeviceType enum value
- `status`: Must be valid DeviceStatus enum value
- `utilization`: If present, must be 0-100

### NetworkLink
- `source_device`: Must reference valid device in topology
- `target_device`: Must reference valid device in topology
- `source_device` ≠ `target_device` (no self-links)
- `utilization`: If present, must be 0-100

### TopologyGraph
- `devices`: Max 200 elements (soft limit for performance)
- `links`: Max 500 elements (soft limit)
- No duplicate device hostnames

### UE5Actor
- `name`: Unique within scene, follows naming convention
- `position`: All components must be finite numbers
- `scale`: All components must be positive (> 0)
- `tags`: Must include "netclaw" for scene management

## State Management

### Incremental Update Rules

1. **Add Device**: If device in new topology but not in scene → spawn_actor
2. **Remove Device**: If device in scene but not in new topology → destroy_actor
3. **Update Device**: If device in both but properties differ → set_actor_transform / set_material_parameter
4. **Preserve Camera**: Camera position NEVER modified by topology updates
5. **Link follows Device**: If device removed, remove all connected links

### Telemetry Update Rules

1. **Alert Received**: Immediately update device status color (event-driven)
2. **Link Down**: Immediately update link status color (event-driven)
3. **Utilization Change**: Update on next poll interval (polling-based)
4. **No duplicate updates**: Track last-updated timestamp per actor
