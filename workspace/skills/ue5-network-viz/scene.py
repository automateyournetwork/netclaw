"""
Scene Management for UE5 Network Visualization.

This module handles scene-level operations including lighting setup,
actor tracking for incremental updates, and scene state management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

try:
    from .ue5_mcp_client import UE5MCPClient, ToolResult
except ImportError:  # pragma: no cover - fallback for sys.path-style loading
    from ue5_mcp_client import UE5MCPClient, ToolResult


# =============================================================================
# Scene State
# =============================================================================

@dataclass
class SceneState:
    """
    Tracks the current state of the UE5 visualization scene.

    Used for incremental updates to avoid re-rendering unchanged elements.
    """
    # Mapping of hostname to actor name for devices
    device_actors: dict[str, str] = field(default_factory=dict)

    # Mapping of hostname to the REAL actor reference ({"refPath": ...})
    # captured at spawn time (045-ue5-digital-twin, live-discovered
    # 2026-07-03). The requested spawn "name" (generate_device_actor_name's
    # "NC_..." string) is NOT what UE5 actually names or labels the actor —
    # the label ends up being the bare hostname, and the internal object
    # name is UE5's own auto-generated one (e.g. "StaticMeshActor_34").
    # Reconstructing a refPath from the generated name therefore never
    # resolves to the real actor; this is the only reliable handle for any
    # post-spawn operation (recoloring, removal) on a specific actor.
    device_refs: dict[str, dict] = field(default_factory=dict)

    # Mapping of link_id to actor name for links
    link_actors: dict[str, str] = field(default_factory=dict)

    # Mapping of link_id to its real actor reference — see device_refs.
    link_refs: dict[str, dict] = field(default_factory=dict)

    # Mapping of "{hostname}:{interface_name}" to actor name for up/up
    # interface actors (045-ue5-digital-twin). Only up/up interfaces get an
    # entry here — down interfaces are tracked separately (see below) and
    # never get an individual actor, to bound total actor count.
    interface_actors: dict[str, str] = field(default_factory=dict)

    # Mapping of "{hostname}:{interface_name}" to its real actor reference — see device_refs.
    interface_refs: dict[str, dict] = field(default_factory=dict)

    # Mapping of hostname to a list of that device's down interface names,
    # for the compact down-interface summary (spec FR-002) rather than one
    # actor per down port.
    down_interfaces: dict[str, list[str]] = field(default_factory=dict)

    # Device positions for link calculation
    device_positions: dict[str, list[float]] = field(default_factory=dict)

    # Last known topology data
    last_topology_hash: str = ""

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


# Global scene state (per session)
_scene_state: Optional[SceneState] = None


def get_scene_state() -> SceneState:
    """Get or create the global scene state."""
    global _scene_state
    if _scene_state is None:
        _scene_state = SceneState()
    return _scene_state


def reset_scene_state() -> None:
    """Reset the scene state (after clear_all)."""
    global _scene_state
    _scene_state = SceneState()


def update_scene_timestamp() -> None:
    """Update the last_updated timestamp."""
    state = get_scene_state()
    state.last_updated = datetime.now()


# =============================================================================
# Actor Tracking
# =============================================================================

def register_device_actor(
    hostname: str,
    actor_name: str,
    position: list[float],
    ref_path: Optional[str] = None,
) -> None:
    """
    Register a spawned device actor for tracking.

    Args:
        hostname: Device hostname
        actor_name: UE5 actor name (requested at spawn time — see device_refs'
            docstring for why this is NOT reliable for later lookups)
        position: Device position [x, y, z]
        ref_path: The REAL actor reference captured from the spawn call's own
            response, if available — the only reliable handle for recoloring
            or removing this specific actor later.
    """
    state = get_scene_state()
    state.device_actors[hostname] = actor_name
    state.device_positions[hostname] = position
    if ref_path:
        state.device_refs[hostname] = {"refPath": ref_path}
    update_scene_timestamp()


def get_device_ref(hostname: str) -> Optional[dict]:
    """Get the real actor reference for a tracked device, if captured at spawn time."""
    return get_scene_state().device_refs.get(hostname)


def unregister_device_actor(hostname: str) -> None:
    """
    Remove a device actor from tracking.

    Args:
        hostname: Device hostname
    """
    state = get_scene_state()
    state.device_actors.pop(hostname, None)
    state.device_positions.pop(hostname, None)
    update_scene_timestamp()


def register_link_actor(link_id: str, actor_name: str, ref_path: Optional[str] = None) -> None:
    """
    Register a spawned link actor for tracking.

    Args:
        link_id: Link identifier (source_target)
        actor_name: UE5 actor name (requested at spawn time)
        ref_path: The REAL actor reference captured from the spawn call's own response, if available.
    """
    state = get_scene_state()
    state.link_actors[link_id] = actor_name
    if ref_path:
        state.link_refs[link_id] = {"refPath": ref_path}
    update_scene_timestamp()


def get_link_ref(link_id: str) -> Optional[dict]:
    """Get the real actor reference for a tracked link, if captured at spawn time."""
    return get_scene_state().link_refs.get(link_id)


def unregister_link_actor(link_id: str) -> None:
    """
    Remove a link actor from tracking.

    Args:
        link_id: Link identifier
    """
    state = get_scene_state()
    state.link_actors.pop(link_id, None)
    update_scene_timestamp()


def register_interface_actor(
    hostname: str,
    interface_name: str,
    actor_name: str,
    ref_path: Optional[str] = None,
) -> None:
    """Register a spawned up/up interface actor for tracking (045-ue5-digital-twin)."""
    state = get_scene_state()
    key = f"{hostname}:{interface_name}"
    state.interface_actors[key] = actor_name
    if ref_path:
        state.interface_refs[key] = {"refPath": ref_path}
    update_scene_timestamp()


def get_interface_ref(hostname: str, interface_name: str) -> Optional[dict]:
    """Get the real actor reference for a tracked interface, if captured at spawn time."""
    return get_scene_state().interface_refs.get(f"{hostname}:{interface_name}")


def unregister_interface_actor(hostname: str, interface_name: str) -> None:
    """Remove an interface actor from tracking."""
    state = get_scene_state()
    state.interface_actors.pop(f"{hostname}:{interface_name}", None)
    update_scene_timestamp()


def get_tracked_interfaces() -> dict[str, str]:
    """Get all tracked interface actors ("hostname:interface" -> actor_name)."""
    return get_scene_state().interface_actors.copy()


def is_interface_tracked(hostname: str, interface_name: str) -> bool:
    """Check if a specific up/up interface is currently tracked."""
    return f"{hostname}:{interface_name}" in get_scene_state().interface_actors


def set_down_interfaces(hostname: str, interface_names: list[str]) -> None:
    """Record a device's down interfaces for the compact summary (FR-002)."""
    state = get_scene_state()
    state.down_interfaces[hostname] = list(interface_names)
    update_scene_timestamp()


def get_down_interfaces(hostname: str) -> list[str]:
    """Get a device's recorded down interfaces."""
    return get_scene_state().down_interfaces.get(hostname, [])


def get_tracked_devices() -> dict[str, str]:
    """Get all tracked device actors (hostname -> actor_name)."""
    return get_scene_state().device_actors.copy()


def get_tracked_links() -> dict[str, str]:
    """Get all tracked link actors (link_id -> actor_name)."""
    return get_scene_state().link_actors.copy()


def get_device_position(hostname: str) -> Optional[list[float]]:
    """Get the position of a tracked device."""
    return get_scene_state().device_positions.get(hostname)


def is_device_tracked(hostname: str) -> bool:
    """Check if a device is currently tracked."""
    return hostname in get_scene_state().device_actors


def is_link_tracked(link_id: str) -> bool:
    """Check if a link is currently tracked."""
    return link_id in get_scene_state().link_actors


# =============================================================================
# Scene Synchronization
# =============================================================================

async def sync_scene_state_from_ue5(client: UE5MCPClient) -> SceneState:
    """
    Synchronize scene state with actual UE5 scene.

    Queries UE5 for all NetClaw actors and updates tracking.

    Args:
        client: UE5 MCP client

    Returns:
        Updated scene state
    """
    from actors import find_netclaw_actors

    actors = await find_netclaw_actors(client)

    state = get_scene_state()

    # Clear current tracking
    state.device_actors.clear()
    state.link_actors.clear()
    state.device_positions.clear()

    # Rebuild from UE5 state
    for actor in actors:
        name = actor.get("name", "")
        tags = actor.get("tags", [])
        location = actor.get("location", [0, 0, 0])

        if "device" in tags:
            # Extract hostname from actor name
            # Format: netclaw_device_{hostname}
            if name.startswith("netclaw_device_"):
                hostname = name[15:].replace("_", "-")
                state.device_actors[hostname] = name
                state.device_positions[hostname] = location

        elif "link" in tags:
            # Extract link_id from actor name
            # Format: netclaw_link_{source}__{target}
            if name.startswith("netclaw_link_"):
                link_id = name[13:].replace("__", "_")
                state.link_actors[link_id] = name

    update_scene_timestamp()

    return state


# =============================================================================
# Lighting Setup
# =============================================================================

async def setup_scene_lighting(
    client: UE5MCPClient,
    intensity: float = 5.0,
    color: Optional[list[float]] = None,
    direction: Optional[list[float]] = None,
) -> bool:
    """
    Configure scene lighting for network visualization.

    Args:
        client: UE5 MCP client
        intensity: Light intensity
        color: RGB color [r, g, b] (default: white)
        direction: Light direction [x, y, z] (default: top-down)

    Returns:
        True if successful
    """
    args = {"intensity": intensity}

    if color:
        args["color"] = color
    else:
        args["color"] = [1.0, 1.0, 1.0]  # White light

    if direction:
        args["direction"] = direction
    else:
        args["direction"] = [0, 0, -1]  # Top-down

    result = await client.call_tool(
        toolset_name="LightingTools",
        tool_name="set_directional_light",
        arguments=args,
    )

    return result.success


async def setup_ambient_lighting(
    client: UE5MCPClient,
    intensity: float = 0.3,
    color: Optional[list[float]] = None,
) -> bool:
    """
    Configure ambient/sky lighting for the scene.

    Args:
        client: UE5 MCP client
        intensity: Ambient intensity
        color: RGB color [r, g, b]

    Returns:
        True if successful
    """
    # Try to set sky light if available
    result = await client.call_tool(
        toolset_name="LightingTools",
        tool_name="set_sky_light",
        arguments={
            "intensity": intensity,
            "color": color or [0.5, 0.6, 0.8],  # Slight blue tint
        },
    )

    return result.success


async def setup_default_lighting(client: UE5MCPClient) -> bool:
    """
    Set up default lighting configuration for network visualization.

    Creates a well-lit scene suitable for viewing network topology.

    Args:
        client: UE5 MCP client

    Returns:
        True if successful
    """
    # Primary directional light (sun-like)
    await setup_scene_lighting(
        client,
        intensity=5.0,
        color=[1.0, 0.98, 0.95],  # Warm white
        direction=[0.5, 0.3, -1],  # Angled from above-right
    )

    # Ambient fill
    await setup_ambient_lighting(
        client,
        intensity=0.4,
        color=[0.6, 0.7, 0.9],  # Cool fill
    )

    return True


# =============================================================================
# Scene Info
# =============================================================================

async def get_scene_info(client: UE5MCPClient) -> dict[str, Any]:
    """
    Get information about the current UE5 scene.

    Args:
        client: UE5 MCP client

    Returns:
        Scene information dict
    """
    try:
        from .actors import SCENE_TOOLSET, TOOL_GET_CURRENT_LEVEL
    except ImportError:  # pragma: no cover - fallback for sys.path-style loading
        from actors import SCENE_TOOLSET, TOOL_GET_CURRENT_LEVEL

    result = await client.call_tool(
        toolset_name=SCENE_TOOLSET,
        tool_name=TOOL_GET_CURRENT_LEVEL,
        arguments={},
    )

    if result.success:
        return result.data
    return {}


async def get_netclaw_actor_count(client: UE5MCPClient) -> int:
    """
    Count NetClaw actors in the current scene.

    Args:
        client: UE5 MCP client

    Returns:
        Number of NetClaw actors
    """
    from actors import find_netclaw_actors

    return len(await find_netclaw_actors(client))
