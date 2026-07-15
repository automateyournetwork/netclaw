"""
Camera Controls for UE5 Network Visualization.

This module provides camera manipulation functions for navigating
and exploring the 3D network visualization, including focus on
specific devices and fly-through animations.
"""

import asyncio
import math
from dataclasses import dataclass, field
from typing import Optional, Any

try:
    from .ue5_mcp_client import UE5MCPClient, ToolResult
    from .scene import get_scene_state, get_device_position
    from .actors import generate_device_actor_name, PROGRAMMATIC_TOOLSET, TOOL_EXECUTE_SCRIPT
except ImportError:  # pragma: no cover - fallback for sys.path-style loading
    from ue5_mcp_client import UE5MCPClient, ToolResult
    from scene import get_scene_state, get_device_position
    from actors import generate_device_actor_name, PROGRAMMATIC_TOOLSET, TOOL_EXECUTE_SCRIPT


# =============================================================================
# Camera State
# =============================================================================

@dataclass
class CameraState:
    """Camera position and orientation."""
    location: list[float] = field(default_factory=lambda: [0, 0, 500])
    rotation: list[float] = field(default_factory=lambda: [-45, 0, 0])
    fov: float = 90.0
    target: Optional[list[float]] = None


# Global camera state cache
_camera_state: Optional[CameraState] = None


def get_cached_camera_state() -> CameraState:
    """Get cached camera state."""
    global _camera_state
    if _camera_state is None:
        _camera_state = CameraState()
    return _camera_state


def update_cached_camera_state(state: CameraState) -> None:
    """Update cached camera state."""
    global _camera_state
    _camera_state = state


# =============================================================================
# Camera Operations
# =============================================================================

async def get_camera_state(client: UE5MCPClient) -> CameraState:
    """
    Get current editor viewport camera position/orientation from UE5, via
    execute_tool_script's native unreal.EditorLevelLibrary API.

    REWRITTEN for 045-ue5-digital-twin: this previously called
    client.call_tool(toolset=..., tool=..., args=...) — not this codebase's
    real call_tool(toolset_name, tool_name, arguments) signature, and never
    against a toolset path confirmed live (unlike SCENE_TOOLSET/ACTOR_TOOLSET/
    etc. in actors.py, which were verified against a running UE5 8.0 server).
    Every camera function in this module raised TypeError on the first line
    the moment it was actually called. Routed through execute_tool_script —
    the one UE5 interaction path this codebase has confirmed live — instead
    of guessing at an unconfirmed "CameraTools" MCP toolset schema.
    """
    script = '''
import json
import unreal

_loc = unreal.Vector(0, 0, 500)
_rot = unreal.Rotator(-45, 0, 0)
try:
    _loc, _rot = unreal.EditorLevelLibrary.get_level_viewport_camera_info()
except Exception as exc:
    unreal.log_error("get_camera_state failed: " + str(exc))

result = json.dumps({
    "location": [_loc.x, _loc.y, _loc.z],
    "rotation": [_rot.pitch, _rot.yaw, _rot.roll],
})
print(result)
'''
    exec_result = await client.call_tool(
        toolset_name=PROGRAMMATIC_TOOLSET,
        tool_name=TOOL_EXECUTE_SCRIPT,
        arguments={"script": script},
    )

    if exec_result.success and isinstance(exec_result.data, dict) and "location" in exec_result.data:
        state = CameraState(
            location=exec_result.data.get("location", [0, 0, 500]),
            rotation=exec_result.data.get("rotation", [-45, 0, 0]),
        )
        update_cached_camera_state(state)
        return state

    return get_cached_camera_state()


async def set_camera_location(
    client: UE5MCPClient,
    location: list[float],
    rotation: Optional[list[float]] = None,
) -> bool:
    """
    Set the editor viewport camera to a specific location/rotation, via
    execute_tool_script (see get_camera_state's docstring for why this isn't
    a generic CameraTools MCP call).

    Args:
        client: UE5 MCP client
        location: [x, y, z] world position
        rotation: Optional [pitch, yaw, roll] rotation
    """
    rot = rotation or get_cached_camera_state().rotation
    script = f'''
import json
import unreal

_ok = False
try:
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(
        unreal.Vector({location[0]}, {location[1]}, {location[2]}),
        unreal.Rotator({rot[0]}, {rot[1]}, {rot[2]}),
    )
    _ok = True
except Exception as exc:
    unreal.log_error("set_camera_location failed: " + str(exc))
    _ok = False

result = json.dumps({{"applied": _ok}})
print(result)
'''
    exec_result = await client.call_tool(
        toolset_name=PROGRAMMATIC_TOOLSET,
        tool_name=TOOL_EXECUTE_SCRIPT,
        arguments={"script": script},
    )

    success = exec_result.success and (not isinstance(exec_result.data, dict) or exec_result.data.get("applied", True))
    if success:
        update_cached_camera_state(CameraState(location=location, rotation=rot))
    return success


async def focus_on_actor(
    client: UE5MCPClient,
    actor_name: str,
) -> bool:
    """
    Move the editor viewport camera to frame a specific actor by its
    outliner label, via execute_tool_script.

    Args:
        client: UE5 MCP client
        actor_name: Outliner label of the actor to focus on
    """
    script = f'''
import json
import unreal

_ok = False
try:
    _editor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    target = None
    for a in _editor.get_all_level_actors():
        if a.get_actor_label() == "{actor_name}":
            target = a
            break
    if target:
        loc = target.get_actor_location()
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(
            unreal.Vector(loc.x - 500, loc.y - 500, loc.z + 300),
            unreal.Rotator(-30, 45, 0),
        )
        _ok = True
except Exception as exc:
    unreal.log_error("focus_on_actor failed: " + str(exc))
    _ok = False

result = json.dumps({{"applied": _ok}})
print(result)
'''
    exec_result = await client.call_tool(
        toolset_name=PROGRAMMATIC_TOOLSET,
        tool_name=TOOL_EXECUTE_SCRIPT,
        arguments={"script": script},
    )
    return exec_result.success and (not isinstance(exec_result.data, dict) or exec_result.data.get("applied", True))


async def focus_on_device(
    client: UE5MCPClient,
    hostname: str,
) -> bool:
    """
    Focus camera on a network device.

    Args:
        client: UE5 MCP client
        hostname: Device hostname

    Returns:
        True if successful
    """
    actor_name = generate_device_actor_name(hostname)
    return await focus_on_actor(client, actor_name)


# =============================================================================
# Camera Positioning Helpers
# =============================================================================

def calculate_overview_position(
    device_positions: dict[str, list[float]],
    offset_height: float = 1000,
    offset_distance: float = 500,
) -> tuple[list[float], list[float]]:
    """
    Calculate camera position for overview of all devices.

    Args:
        device_positions: Dict of hostname -> [x, y, z] positions
        offset_height: Height above scene center
        offset_distance: Distance from scene center

    Returns:
        Tuple of (location, rotation)
    """
    if not device_positions:
        return [0, 0, 500], [-45, 0, 0]

    # Calculate bounding box
    all_pos = list(device_positions.values())
    min_x = min(p[0] for p in all_pos)
    max_x = max(p[0] for p in all_pos)
    min_y = min(p[1] for p in all_pos)
    max_y = max(p[1] for p in all_pos)
    min_z = min(p[2] for p in all_pos)
    max_z = max(p[2] for p in all_pos)

    # Center point
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    center_z = (min_z + max_z) / 2

    # Camera position above and offset from center
    camera_pos = [
        center_x - offset_distance,
        center_y - offset_distance,
        center_z + offset_height,
    ]

    # Look at center (pitch down, yaw toward center)
    pitch = -45
    yaw = 45

    return camera_pos, [pitch, yaw, 0]


async def set_overview_camera(client: UE5MCPClient) -> bool:
    """
    Position camera for overview of entire topology.

    Args:
        client: UE5 MCP client

    Returns:
        True if successful
    """
    state = get_scene_state()
    location, rotation = calculate_overview_position(state.device_positions)

    return await set_camera_location(client, location, rotation)


async def set_top_down_camera(
    client: UE5MCPClient,
    height: float = 2000,
) -> bool:
    """
    Position camera for top-down view of topology.

    Args:
        client: UE5 MCP client
        height: Camera height

    Returns:
        True if successful
    """
    state = get_scene_state()

    if not state.device_positions:
        center = [0, 0]
    else:
        all_pos = list(state.device_positions.values())
        center_x = sum(p[0] for p in all_pos) / len(all_pos)
        center_y = sum(p[1] for p in all_pos) / len(all_pos)
        center = [center_x, center_y]

    location = [center[0], center[1], height]
    rotation = [-90, 0, 0]  # Look straight down

    return await set_camera_location(client, location, rotation)


# =============================================================================
# Fly-Through Animation
# =============================================================================

@dataclass
class FlyThroughKeyframe:
    """A keyframe in a fly-through animation."""
    location: list[float]
    rotation: list[float]
    duration: float = 1.0  # Seconds to reach this keyframe


@dataclass
class FlyThroughPath:
    """A camera fly-through path."""
    keyframes: list[FlyThroughKeyframe] = field(default_factory=list)
    loop: bool = False


def generate_orbit_path(
    center: list[float],
    radius: float = 500,
    height: float = 300,
    num_points: int = 8,
    duration_per_point: float = 2.0,
) -> FlyThroughPath:
    """
    Generate an orbital fly-through path around a center point.

    Args:
        center: [x, y, z] center to orbit around
        radius: Orbit radius
        height: Height above center
        num_points: Number of keyframes
        duration_per_point: Seconds per keyframe

    Returns:
        FlyThroughPath
    """
    keyframes = []

    for i in range(num_points + 1):  # +1 to close the loop
        angle = (2 * math.pi * i) / num_points

        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        z = center[2] + height

        # Rotation: look at center
        yaw = math.degrees(angle) + 180  # Face inward

        keyframes.append(FlyThroughKeyframe(
            location=[x, y, z],
            rotation=[-30, yaw, 0],
            duration=duration_per_point,
        ))

    return FlyThroughPath(keyframes=keyframes, loop=False)


def generate_linear_path(
    points: list[list[float]],
    duration_per_point: float = 2.0,
    look_at_next: bool = True,
) -> FlyThroughPath:
    """
    Generate a linear fly-through path through points.

    Args:
        points: List of [x, y, z] positions
        duration_per_point: Seconds per segment
        look_at_next: Whether to orient camera toward next point

    Returns:
        FlyThroughPath
    """
    keyframes = []

    for i, point in enumerate(points):
        if look_at_next and i < len(points) - 1:
            # Calculate rotation to face next point
            next_point = points[i + 1]
            dx = next_point[0] - point[0]
            dy = next_point[1] - point[1]
            dz = next_point[2] - point[2]

            yaw = math.degrees(math.atan2(dy, dx))
            horizontal_dist = math.sqrt(dx * dx + dy * dy)
            pitch = math.degrees(math.atan2(-dz, horizontal_dist))

            rotation = [pitch, yaw, 0]
        else:
            rotation = [0, 0, 0]

        keyframes.append(FlyThroughKeyframe(
            location=point,
            rotation=rotation,
            duration=duration_per_point,
        ))

    return FlyThroughPath(keyframes=keyframes, loop=False)


def generate_device_tour_path(
    device_positions: dict[str, list[float]],
    duration_per_device: float = 3.0,
    view_height: float = 200,
    view_distance: float = 300,
) -> FlyThroughPath:
    """
    Generate a fly-through that visits each device.

    Args:
        device_positions: Dict of hostname -> [x, y, z]
        duration_per_device: Seconds per device
        view_height: Height above device
        view_distance: Distance from device

    Returns:
        FlyThroughPath
    """
    keyframes = []

    for hostname, pos in device_positions.items():
        # Position camera at an angle above and in front of device
        camera_x = pos[0] - view_distance
        camera_y = pos[1] - view_distance / 2
        camera_z = pos[2] + view_height

        # Look at device
        pitch = -30
        yaw = 30

        keyframes.append(FlyThroughKeyframe(
            location=[camera_x, camera_y, camera_z],
            rotation=[pitch, yaw, 0],
            duration=duration_per_device,
        ))

    return FlyThroughPath(keyframes=keyframes, loop=False)


async def execute_flythrough(
    client: UE5MCPClient,
    path: FlyThroughPath,
    smooth: bool = True,
) -> bool:
    """
    Execute a fly-through animation.

    Args:
        client: UE5 MCP client
        path: Fly-through path to execute
        smooth: Whether to interpolate between keyframes

    Returns:
        True if completed successfully
    """
    if not path.keyframes:
        return False

    # Save initial camera state
    initial_state = await get_camera_state(client)

    try:
        for keyframe in path.keyframes:
            # Move to keyframe
            success = await set_camera_location(
                client,
                keyframe.location,
                keyframe.rotation,
            )

            if not success:
                return False

            # Wait for duration
            if smooth:
                # For smooth animation, we'd need UE5 to interpolate
                # For now, just wait the duration
                await asyncio.sleep(keyframe.duration)
            else:
                await asyncio.sleep(0.1)  # Small delay for instant transitions

        return True

    except asyncio.CancelledError:
        # Restore initial camera on cancellation
        await set_camera_location(
            client,
            initial_state.location,
            initial_state.rotation,
        )
        raise


async def flythrough_orbit(
    client: UE5MCPClient,
    center: Optional[list[float]] = None,
    radius: float = 800,
    duration: float = 20.0,
) -> bool:
    """
    Execute an orbital fly-through around the topology.

    Args:
        client: UE5 MCP client
        center: Optional center point (auto-calculated if None)
        radius: Orbit radius
        duration: Total animation duration

    Returns:
        True if completed
    """
    state = get_scene_state()

    if center is None:
        # Calculate center from device positions
        if state.device_positions:
            all_pos = list(state.device_positions.values())
            center = [
                sum(p[0] for p in all_pos) / len(all_pos),
                sum(p[1] for p in all_pos) / len(all_pos),
                sum(p[2] for p in all_pos) / len(all_pos),
            ]
        else:
            center = [0, 0, 100]

    num_points = max(8, int(duration / 2))
    path = generate_orbit_path(
        center=center,
        radius=radius,
        num_points=num_points,
        duration_per_point=duration / num_points,
    )

    return await execute_flythrough(client, path)


async def flythrough_devices(client: UE5MCPClient) -> bool:
    """
    Execute a fly-through that visits each rendered device.

    Args:
        client: UE5 MCP client

    Returns:
        True if completed
    """
    state = get_scene_state()

    if not state.device_positions:
        return False

    path = generate_device_tour_path(state.device_positions)
    return await execute_flythrough(client, path)


# =============================================================================
# Camera Preservation
# =============================================================================

async def save_camera_position(client: UE5MCPClient) -> CameraState:
    """
    Save current camera position for later restoration.

    Args:
        client: UE5 MCP client

    Returns:
        Saved camera state
    """
    return await get_camera_state(client)


async def restore_camera_position(
    client: UE5MCPClient,
    state: CameraState,
) -> bool:
    """
    Restore camera to a previously saved position.

    Args:
        client: UE5 MCP client
        state: Camera state to restore

    Returns:
        True if successful
    """
    return await set_camera_location(
        client,
        state.location,
        state.rotation,
    )
