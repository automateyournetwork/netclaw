# Research: Unreal Engine 5.8 MCP Integration

**Feature**: 044-ue5-mcp-network-viz
**Date**: 2026-06-28

## Overview

This document captures research findings for integrating the Unreal Engine 5.8 MCP server with NetClaw for 3D network topology visualization.

## Unreal Engine 5.8 MCP Server Analysis

### Source
- **Built-in Plugin**: Unreal MCP (ModelContextProtocol) - ships with UE5.8
- **Documentation**: https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor
- **License**: Unreal Engine EULA (free for non-commercial/internal tools)
- **Status**: Experimental (APIs may change)

### Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   NetClaw/WSL   │────▶│ Unreal MCP      │────▶│ UE5 Editor      │
│   (MCP Client)  │     │ (HTTP Server)   │     │ (Game Thread)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                      │                       │
    Natural language      JSON-RPC/HTTP           Direct API calls
    topology request      localhost:8000/mcp       to UE subsystems
```

**Components**:
1. **MCP Server Plugin** (`ModelContextProtocol`): HTTP server running inside UE Editor process on port 8000
2. **Toolset Registry** (`AllToolsets`): Plugin that defines available tools (ActorTools, MaterialTools, etc.)
3. **Tool Search Mode**: Default mode uses meta-tools for discovery instead of eager tool listing

### Transport Protocol

| Property | Value |
|----------|-------|
| Type | HTTP + Server-Sent Events (SSE) |
| Default URL | `http://127.0.0.1:8000/mcp` |
| Binding | Loopback only (localhost) |
| Authentication | None (local-only) |

**Key Difference from Blender MCP**: UE5 uses HTTP transport, not stdio. This requires URL-based registration in openclaw.json rather than command-based.

### Tool Search Mode (Default)

UE5 MCP uses "tool search" mode by default, exposing three meta-tools:

| Meta-Tool | Purpose |
|-----------|---------|
| `list_toolsets` | Returns available toolset names and descriptions |
| `describe_toolset` | Returns tool schemas for a named toolset |
| `call_tool` | Dispatches a tool call within a toolset |

This keeps the initial `tools/list` response small even with hundreds of available tools.

### Available Toolsets

Based on AllToolsets plugin documentation:

| Toolset | Description | Our Use Cases |
|---------|-------------|---------------|
| `ActorTools` | Spawn, transform, delete actors | Create device meshes |
| `SceneTools` | Scene management, level loading | Clear scene, setup |
| `MaterialInstanceTools` | Create and modify materials | Device colors by type/health |
| `ObjectTools` | General object manipulation | Transform devices |
| `LightingTools` | Lighting setup | Scene illumination |
| `CameraTools` | Camera control | Fly-throughs, focus |
| `BlueprintTools` | Blueprint interaction | (Future: custom network assets) |

### Key Tools for Network Visualization

| Tool | Toolset | Parameters | Use Case |
|------|---------|------------|----------|
| `spawn_actor` | ActorTools | class, location, rotation, scale | Create device meshes |
| `set_actor_transform` | ActorTools | actor_name, location, rotation, scale | Position devices |
| `destroy_actor` | ActorTools | actor_name | Remove deleted devices |
| `create_material_instance` | MaterialInstanceTools | parent, name, parameters | Device type colors |
| `set_material_parameter` | MaterialInstanceTools | material, parameter, value | Health state colors |
| `set_directional_light` | LightingTools | direction, intensity, color | Scene lighting |
| `set_camera_location` | CameraTools | location, rotation | Navigation |
| `focus_on_actor` | CameraTools | actor_name | Device inspection |

## Integration Decisions

### Decision: HTTP Registration in openclaw.json

**Decision**: Register UE5 MCP as a URL-based MCP server (like Jenkins, Datadog).

**Rationale**:
- UE5 MCP is an HTTP server, not a command-line tool
- Follows existing pattern for remote/HTTP MCP servers in NetClaw
- No process management needed (user starts UE Editor)

**Implementation**:
```json
{
  "unreal-mcp": {
    "url": "http://127.0.0.1:8000/mcp",
    "env": {
      "UE5_MCP_URL": "${UE5_MCP_URL:-http://127.0.0.1:8000/mcp}"
    }
  }
}
```

**Alternatives Considered**:
- Command-based with UE5 CLI: Rejected (UE5 requires GUI for rendering)
- Remote HTTP proxy: Out of scope per spec (local-only)

### Decision: Device Representation with Static Meshes

**Decision**: Use basic UE5 static meshes (cubes, spheres, cylinders) for devices, distinguished by material colors.

| Device Type | Mesh | Material Color | Rationale |
|-------------|------|----------------|-----------|
| Router | Cube | Blue (#3366CC) | Convention |
| Switch | Cube (smaller) | Green (#33B34D) | Convention |
| Firewall | Cube | Red (#CC3333) | Security = red |
| Endpoint | Sphere | Gray (#808080) | Distinct from network devices |
| Unknown | Cube | White (#FFFFFF) | Neutral default |

**Rationale**:
- Simple meshes are performant for 100+ devices
- Color-based differentiation is intuitive
- Matches Blender integration pattern for consistency
- Future: Custom UE assets for device models (out of scope v1)

**Alternatives Considered**:
- Custom 3D models per device type: Deferred (requires asset creation)
- Blueprint-based actors: Over-engineered for v1

### Decision: Connection Rendering with Spline Actors

**Decision**: Use UE5 spline components or procedural cables for link visualization.

**Rationale**:
- UE5 has built-in spline/cable actors unlike Blender's cylinder approach
- Splines can curve naturally around obstacles
- Can be colored/animated for utilization visualization
- Better visual quality than simple cylinders

**Implementation Approach**:
1. For each link, spawn a spline actor
2. Set start point at source device position
3. Set end point at target device position
4. Apply material based on link status (green=healthy, red=down, yellow=degraded)

### Decision: Layout Algorithm (Force-Directed)

**Decision**: Use force-directed spring layout, consistent with Blender integration.

**Rationale**:
- Proven approach from Feature 024
- Works well for network topologies (shows logical relationships)
- Computable in Python before sending to UE5
- Scales to 100+ devices

**Layout Parameters**:
- Spring constant: 0.1 (link attraction)
- Repulsion constant: 100 (node separation)
- Damping: 0.9 (convergence)
- Max iterations: 500
- Convergence threshold: 0.01

### Decision: Incremental Updates via Actor Tracking

**Decision**: Maintain actor name → device hostname mapping for incremental scene updates.

**Rationale**:
- Per clarification: incremental updates preserve camera position and context
- Need to track which actors represent which devices
- Enables: add new devices, remove deleted devices, update existing actors

**Implementation**:
- Actor naming convention: `netclaw_device_{hostname}` and `netclaw_link_{source}_{target}`
- Scene query via `get_all_actors_with_tag("netclaw")` to find existing topology actors
- Diff current topology against scene actors to determine adds/removes/updates

### Decision: Hybrid Real-Time Updates

**Decision**: Event-driven for alerts, polling for metrics (per clarification).

**Implementation**:
- **Event-driven** (via Telemetry Receivers MCP, Feature 010):
  - Syslog alerts → immediate device color change
  - Link state changes → immediate link color change
- **Polling** (configurable interval, default 30 seconds):
  - SNMP interface utilization → link thickness/particle effects
  - NetFlow aggregates → traffic visualization

**Update Mechanism**:
1. Telemetry Receivers MCP pushes events to a queue
2. UE5 integration skill polls queue for events
3. On event: call appropriate UE5 MCP tool to update actor
4. On polling interval: fetch metrics, batch-update visuals

### Decision: Scene Lighting with Lumen

**Decision**: Use UE5's Lumen global illumination for professional-quality lighting.

**Rationale**:
- Lumen is automatic and high-quality
- No manual light placement needed
- Supports dynamic lighting for health state changes

**Implementation**:
- Set up default directional light (sun)
- Enable Lumen in post-process volume
- Use emissive materials for "glowing" critical alerts

### Decision: Camera Navigation via Tool Calls

**Decision**: Implement fly-through and focus via UE5 camera tools.

**Natural Language Mapping**:
| User Request | UE5 Tool Sequence |
|--------------|-------------------|
| "Fly through the network" | Scripted camera animation through key points |
| "Focus on router-1" | `focus_on_actor(netclaw_device_router-1)` |
| "Show the core" | Move camera to center of high-degree nodes |
| "Zoom out" | Adjust camera distance |

## Testing Strategy

### Live UE5 MCP Integration Testing

**Prerequisites**:
- UE5.8 with MCP plugin enabled and running
- MCP server started (auto-start or console command)
- Test project with basic level loaded

**Test Phases**:

#### Phase 1: Connectivity Tests
```python
# Test 1: Verify MCP server reachable
def test_mcp_ping():
    response = mcp_client.call("list_toolsets", {})
    assert "ActorTools" in response["toolsets"]

# Test 2: Verify tool discovery
def test_describe_toolset():
    response = mcp_client.call("describe_toolset", {"name": "ActorTools"})
    assert "spawn_actor" in [t["name"] for t in response["tools"]]
```

#### Phase 2: Actor Spawning Tests
```python
# Test 3: Spawn single device actor
def test_spawn_device():
    response = mcp_client.call("call_tool", {
        "toolset": "ActorTools",
        "tool": "spawn_actor",
        "args": {
            "class": "/Engine/BasicShapes/Cube.Cube",
            "name": "netclaw_device_test-router",
            "location": [0, 0, 100],
            "scale": [0.5, 0.5, 0.5]
        }
    })
    assert response["success"]

    # Verify actor exists in scene
    scene = mcp_client.call("call_tool", {
        "toolset": "SceneTools",
        "tool": "get_all_actors_with_tag",
        "args": {"tag": "netclaw"}
    })
    assert "netclaw_device_test-router" in scene["actors"]

# Test 4: Spawn multiple devices
def test_spawn_topology():
    devices = ["router-1", "switch-1", "switch-2", "firewall-1"]
    for device in devices:
        spawn_device(device, get_position_for_device(device))

    scene = get_scene_actors()
    assert len([a for a in scene if a.startswith("netclaw_device_")]) == 4

# Test 5: Remove device
def test_remove_device():
    response = mcp_client.call("call_tool", {
        "toolset": "ActorTools",
        "tool": "destroy_actor",
        "args": {"name": "netclaw_device_test-router"}
    })
    assert response["success"]
```

#### Phase 3: Material Tests
```python
# Test 6: Apply device type colors
def test_device_colors():
    spawn_device("router-1", [0, 0, 100])
    apply_router_material("netclaw_device_router-1")

    material = get_actor_material("netclaw_device_router-1")
    assert material["base_color"] == [0.2, 0.4, 0.8]  # Blue

# Test 7: Health state color change
def test_health_color_update():
    spawn_device("router-1", [0, 0, 100])
    set_device_health("netclaw_device_router-1", "critical")

    material = get_actor_material("netclaw_device_router-1")
    assert material["base_color"] == [0.8, 0.2, 0.2]  # Red
```

#### Phase 4: Link Tests
```python
# Test 8: Create link between devices
def test_spawn_link():
    spawn_device("router-1", [0, 0, 100])
    spawn_device("switch-1", [500, 0, 100])

    spawn_link("router-1", "switch-1")

    scene = get_scene_actors()
    assert "netclaw_link_router-1_switch-1" in scene

# Test 9: Update link status
def test_link_status_update():
    spawn_link("router-1", "switch-1")
    set_link_status("router-1", "switch-1", "down")

    material = get_actor_material("netclaw_link_router-1_switch-1")
    assert material["base_color"] == [0.8, 0.2, 0.2]  # Red
```

#### Phase 5: Incremental Update Tests
```python
# Test 10: Add device to existing scene
def test_incremental_add():
    render_topology(["router-1", "switch-1"])
    assert count_devices() == 2

    update_topology(["router-1", "switch-1", "switch-2"])
    assert count_devices() == 3

# Test 11: Remove device from existing scene
def test_incremental_remove():
    render_topology(["router-1", "switch-1", "switch-2"])
    assert count_devices() == 3

    update_topology(["router-1", "switch-1"])
    assert count_devices() == 2
    assert "netclaw_device_switch-2" not in get_scene_actors()

# Test 12: Camera preserved after update
def test_camera_preserved():
    render_topology(["router-1", "switch-1"])
    camera_pos_before = get_camera_position()

    update_topology(["router-1", "switch-1", "switch-2"])
    camera_pos_after = get_camera_position()

    assert camera_pos_before == camera_pos_after
```

#### Phase 6: Performance Tests
```python
# Test 13: Render 100 devices within timeout
def test_render_100_devices():
    devices = generate_test_topology(100)
    start = time.time()

    render_topology(devices)

    elapsed = time.time() - start
    assert elapsed < 60  # SC-001: under 60 seconds

# Test 14: Update latency
def test_update_latency():
    render_topology(["router-1"])

    start = time.time()
    set_device_health("netclaw_device_router-1", "critical")
    elapsed = time.time() - start

    assert elapsed < 30  # SC-002: within 30 seconds
```

#### Phase 7: Camera Tests
```python
# Test 15: Focus on device
def test_focus_on_device():
    render_topology(["router-1", "switch-1"])

    focus_on_device("router-1")

    camera = get_camera()
    device_pos = get_actor_position("netclaw_device_router-1")
    assert camera["look_at"] == device_pos

# Test 16: Fly-through
def test_flythrough():
    render_topology(generate_test_topology(10))

    result = execute_flythrough()
    assert result["success"]
    assert result["frames_rendered"] > 0
```

### Manual Verification Checklist

After automated tests pass, manually verify in UE5 Editor:

- [ ] Devices visually distinguishable by color
- [ ] Links connect device centers properly
- [ ] Scene lighting is adequate (no dark areas)
- [ ] Camera fly-through is smooth (no stuttering)
- [ ] Health color changes are visible
- [ ] Labels (if implemented) are readable
- [ ] Scene looks professional/presentation-ready

## Best Practices Applied

1. **MCP Standard Compliance**: Uses official MCP protocol via HTTP transport
2. **Existing Patterns**: Follows NetClaw's URL-based MCP server registration (like Jenkins, Datadog)
3. **Environment Variables**: UE5_MCP_URL follows .env.example conventions
4. **Skill Modularity**: Single-purpose skill with clear boundaries
5. **Error Transparency**: Clear error messages for connection failures, scene issues
6. **Incremental Updates**: Scene state tracked for efficient updates
7. **Testability**: Comprehensive test plan with live UE5 integration

## Summary of Decisions

| Topic | Decision |
|-------|----------|
| MCP Registration | URL-based (`http://127.0.0.1:8000/mcp`) |
| Tool Access | Via tool search mode (list_toolsets → describe_toolset → call_tool) |
| Device Meshes | Static mesh cubes/spheres with material colors |
| Link Rendering | Spline actors or procedural cables |
| Layout Algorithm | Force-directed spring layout |
| Scene Updates | Incremental with actor tracking |
| Real-Time Updates | Hybrid: event-driven (alerts) + polling (metrics) |
| Lighting | Lumen global illumination (default) |
| Testing | Live integration tests against running UE5 MCP |
