"""
UE5 Network Visualization Skill.

This skill enables 3D network topology visualization in Unreal Engine 5.8
using the built-in MCP server. Network engineers can visualize their
infrastructure with color-coded devices, animated links, and real-time
health updates.

Quick Start:
    from workspace.skills.ue5_network_viz import render_topology, UE5MCPClient

    topology = {
        "devices": [
            {"hostname": "core-rtr-01", "device_type": "router"},
            {"hostname": "dist-sw-01", "device_type": "switch"},
        ],
        "links": [
            {"source_device": "core-rtr-01", "target_device": "dist-sw-01"},
        ],
    }

    async with UE5MCPClient() as client:
        result = await render_topology(client, topology)
        print(f"Rendered {result.devices_rendered} devices")
"""

# Version info
__version__ = "0.1.0"
__author__ = "NetClaw Team"

# Core client
from .ue5_mcp_client import (
    UE5MCPClient,
    UE5MCPError,
    ToolsetInfo,
    ToolInfo,
    ToolResult,
    check_connectivity,
    discover_tools,
)

# Layout algorithm
from .layout import (
    ForceDirectedLayout,
    LayoutConfig,
    Vector3,
    calculate_topology_layout,
)

# Materials and colors
from .materials import (
    Color,
    DeviceType,
    DeviceStatus,
    LinkStatus,
    get_device_type_color,
    get_link_status_color,
    create_device_material_config,
    create_link_material_config,
    infer_device_type,
)

# Actor management
from .actors import (
    spawn_device_actor,
    spawn_link_actor,
    destroy_device_actor,
    destroy_link_actor,
    apply_device_material,
    apply_link_material,
    clear_all_netclaw_actors,
    find_netclaw_actors,
    generate_device_actor_name,
    generate_link_actor_name,
    render_topology_batch,
    save_level_as,
    capture_scene_screenshot,
)

# Scene management
from .scene import (
    get_scene_state,
    reset_scene_state,
    setup_default_lighting,
    sync_scene_state_from_ue5,
)

# Rendering
from .renderer import (
    NetworkDevice,
    NetworkLink,
    TopologyGraph,
    RenderResult,
    render_topology,
    render_topology_fast,
    render_topology_from_dict,
    render_topology_incremental,
    safe_render_topology,
    get_device_details,
    list_rendered_devices,
)

# Telemetry
from .telemetry import (
    TelemetryEvent,
    TelemetryEventType,
    TelemetryPoller,
    TelemetryReceiver,
    update_device_status,
    update_link_status,
    set_device_critical,
    set_device_healthy,
    set_link_down,
    set_link_healthy,
)

# Camera controls
from .camera import (
    CameraState,
    get_camera_state,
    set_camera_location,
    focus_on_device,
    set_overview_camera,
    set_top_down_camera,
    flythrough_orbit,
    flythrough_devices,
    save_camera_position,
    restore_camera_position,
)

__all__ = [
    # Client
    "UE5MCPClient",
    "UE5MCPError",
    "check_connectivity",
    "discover_tools",
    # Layout
    "ForceDirectedLayout",
    "LayoutConfig",
    "Vector3",
    "calculate_topology_layout",
    # Materials
    "Color",
    "DeviceType",
    "DeviceStatus",
    "LinkStatus",
    "get_device_type_color",
    "infer_device_type",
    # Actors
    "spawn_device_actor",
    "spawn_link_actor",
    "clear_all_netclaw_actors",
    "find_netclaw_actors",
    "render_topology_batch",
    "save_level_as",
    "capture_scene_screenshot",
    # Scene
    "get_scene_state",
    "setup_default_lighting",
    # Rendering
    "NetworkDevice",
    "NetworkLink",
    "TopologyGraph",
    "RenderResult",
    "render_topology",
    "render_topology_fast",
    "render_topology_from_dict",
    "safe_render_topology",
    # Telemetry
    "TelemetryEvent",
    "update_device_status",
    "set_device_critical",
    "set_link_down",
    # Camera
    "CameraState",
    "focus_on_device",
    "flythrough_orbit",
]
