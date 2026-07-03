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

    # Mapping of link_id to actor name for links
    link_actors: dict[str, str] = field(default_factory=dict)

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

def register_device_actor(hostname: str, actor_name: str, position: list[float]) -> None:
    """
    Register a spawned device actor for tracking.

    Args:
        hostname: Device hostname
        actor_name: UE5 actor name
        position: Device position [x, y, z]
    """
    state = get_scene_state()
    state.device_actors[hostname] = actor_name
    state.device_positions[hostname] = position
    update_scene_timestamp()


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


def register_link_actor(link_id: str, actor_name: str) -> None:
    """
    Register a spawned link actor for tracking.

    Args:
        link_id: Link identifier (source_target)
        actor_name: UE5 actor name
    """
    state = get_scene_state()
    state.link_actors[link_id] = actor_name
    update_scene_timestamp()


def unregister_link_actor(link_id: str) -> None:
    """
    Remove a link actor from tracking.

    Args:
        link_id: Link identifier
    """
    state = get_scene_state()
    state.link_actors.pop(link_id, None)
    update_scene_timestamp()


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
    from actors import NETCLAW_TAG

    result = await client.call_tool(
        toolset="ActorTools",
        tool="get_all_actors_with_tag",
        args={"tag": NETCLAW_TAG},
    )

    state = get_scene_state()

    if result.success:
        actors = result.data.get("actors", [])

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
        toolset="LightingTools",
        tool="set_directional_light",
        args=args,
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
        toolset="LightingTools",
        tool="set_sky_light",
        args={
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
    result = await client.call_tool(
        toolset="SceneTools",
        tool="get_scene_info",
        args={},
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
    from actors import NETCLAW_TAG

    result = await client.call_tool(
        toolset="ActorTools",
        tool="get_all_actors_with_tag",
        args={"tag": NETCLAW_TAG},
    )

    if result.success:
        return len(result.data.get("actors", []))
    return 0
