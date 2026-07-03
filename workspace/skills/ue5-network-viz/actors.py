"""
Actor Management for UE5 Network Visualization.

This module handles spawning, updating, and destroying UE5 actors
that represent network devices and links in the 3D visualization.

KEY LEARNINGS FROM TESTING:
1. Must load mesh asset FIRST, then assign the loaded object (not path string)
2. Use 'staticMesh' (lowercase 's') for the property name
3. Create a new empty level BEFORE populating actors
4. _StrictDict requires direct key access ["key"] not .get("key")
5. execute_tool() arguments must be JSON strings
6. Hierarchical layout: routers (top) > switches (middle) > endpoints (bottom)
"""

from dataclasses import dataclass, field
from typing import Optional, Any
import json

try:
    from .ue5_mcp_client import UE5MCPClient, ToolResult
except ImportError:  # pragma: no cover - fallback for sys.path-style loading
    from ue5_mcp_client import UE5MCPClient, ToolResult


# =============================================================================
# UE5 MCP Toolset and Tool Names
# =============================================================================

# Full toolset paths
SCENE_TOOLSET = "editor_toolset.toolsets.scene.SceneTools"
ACTOR_TOOLSET = "editor_toolset.toolsets.actor.ActorTools"
MATERIAL_TOOLSET = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"
PRIMITIVE_TOOLSET = "editor_toolset.toolsets.primitive.PrimitiveTools"
PROGRAMMATIC_TOOLSET = "editor_toolset.toolsets.programmatic.ProgrammaticToolset"
ASSET_TOOLSET = "editor_toolset.toolsets.asset.AssetTools"
OBJECT_TOOLSET = "editor_toolset.toolsets.object.ObjectTools"

# Full tool names - Scene
TOOL_ADD_FROM_ASSET = f"{SCENE_TOOLSET}.add_to_scene_from_asset"
TOOL_ADD_FROM_CLASS = f"{SCENE_TOOLSET}.add_to_scene_from_class"
TOOL_REMOVE_FROM_SCENE = f"{SCENE_TOOLSET}.remove_from_scene"
TOOL_FIND_ACTORS = f"{SCENE_TOOLSET}.find_actors"
TOOL_LOAD_LEVEL = f"{SCENE_TOOLSET}.load_level"
TOOL_GET_CURRENT_LEVEL = f"{SCENE_TOOLSET}.get_current_level"

# Full tool names - Actor
TOOL_SET_TRANSFORM = f"{ACTOR_TOOLSET}.set_actor_transform"
TOOL_ADD_TAG = f"{ACTOR_TOOLSET}.add_tag"
TOOL_SET_LABEL = f"{ACTOR_TOOLSET}.set_label"
TOOL_GET_COMPONENTS = f"{ACTOR_TOOLSET}.get_components"

# Full tool names - Object (for setting properties)
TOOL_SET_PROPERTIES = f"{OBJECT_TOOLSET}.set_properties"
TOOL_GET_PROPERTY = f"{OBJECT_TOOLSET}.get_property"

# Full tool names - Asset (for loading meshes)
TOOL_LOAD_ASSET = f"{ASSET_TOOLSET}.load_asset"
TOOL_FIND_ASSETS = f"{ASSET_TOOLSET}.find_assets"
TOOL_SAVE_ASSETS = f"{ASSET_TOOLSET}.save_assets"
TOOL_CREATE_FOLDER = f"{ASSET_TOOLSET}.create_folder"

# Full tool names - Programmatic (for batch operations)
TOOL_EXECUTE_SCRIPT = f"{PROGRAMMATIC_TOOLSET}.execute_tool_script"


# =============================================================================
# Asset Paths for Basic Shapes
# =============================================================================

# StaticMesh asset paths - these are the mesh assets to LOAD first
STATIC_MESH_PATHS = {
    "cube": "/Engine/BasicShapes/Cube.Cube",
    "sphere": "/Engine/BasicShapes/Sphere.Sphere",
    "cylinder": "/Engine/BasicShapes/Cylinder.Cylinder",
    "cone": "/Engine/BasicShapes/Cone.Cone",
}

# StaticMeshActor class path (for spawning empty actors)
STATIC_MESH_ACTOR_CLASS = "/Script/Engine.StaticMeshActor"

# Default device shapes by type
DEVICE_SHAPES = {
    "router": "cube",
    "switch": "cube",
    "firewall": "cube",
    "access_point": "sphere",
    "load_balancer": "cube",
    "endpoint": "sphere",
    "unknown": "cube",
}

# =============================================================================
# Hierarchical 3D Layout Heights (in UE5 centimeters)
# =============================================================================

# Z-heights for hierarchical topology (routers at top, endpoints at bottom)
LAYER_HEIGHTS = {
    "router": 400,       # Top tier - core/edge routers
    "firewall": 350,     # Security layer
    "load_balancer": 300,# Load balancing layer
    "switch": 200,       # Distribution/access switches
    "access_point": 150, # Wireless APs
    "endpoint": 50,      # Servers, hosts, endpoints
    "unknown": 100,      # Default middle
}

# Base scale for device actors (larger for visibility)
DEFAULT_DEVICE_SCALE = {"x": 100, "y": 100, "z": 100}  # 1 meter cubes
DEFAULT_LINK_SCALE = {"x": 10, "y": 10, "z": 100}      # Thin cylinders

# Spacing between devices
DEVICE_SPACING_X = 400  # 4 meters between devices horizontally
DEVICE_SPACING_Y = 400  # 4 meters between devices depth-wise

# Tag used to identify all NetClaw actors
NETCLAW_TAG = "netclaw"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ActorInfo:
    """Information about a spawned UE5 actor."""
    name: str
    ref_path: str  # Full actor reference path
    location: dict  # {"x": float, "y": float, "z": float}
    rotation: dict = field(default_factory=lambda: {"pitch": 0, "yaw": 0, "roll": 0})
    scale: dict = field(default_factory=lambda: {"x": 100, "y": 100, "z": 100})
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceActor(ActorInfo):
    """Actor representing a network device."""
    hostname: str = ""
    device_type: str = "unknown"
    status: str = "healthy"
    label: str = ""


@dataclass
class LinkActor(ActorInfo):
    """Actor representing a network link."""
    source_device: str = ""
    target_device: str = ""
    source_interface: str = ""
    target_interface: str = ""
    status: str = "healthy"


# =============================================================================
# Actor Name Generation
# =============================================================================

def generate_device_actor_name(hostname: str) -> str:
    """Generate UE5 actor name for a device."""
    safe_name = hostname.replace("-", "_").replace(".", "_").replace(" ", "_")
    return f"NC_{safe_name}"


def generate_link_actor_name(source: str, target: str) -> str:
    """Generate UE5 actor name for a link."""
    safe_source = source.replace("-", "_").replace(".", "_")[:10]
    safe_target = target.replace("-", "_").replace(".", "_")[:10]
    return f"NC_Link_{safe_source}_{safe_target}"


def generate_label_actor_name(hostname: str) -> str:
    """Generate UE5 actor name for a device label."""
    safe_name = hostname.replace("-", "_").replace(".", "_")
    return f"NC_Label_{safe_name}"


def _safe(text: str) -> str:
    """Sanitize a string for use in a UE5 actor name."""
    return text.replace("-", "_").replace(".", "_").replace(" ", "_").replace("/", "_")


def generate_interface_actor_name(hostname: str, interface_name: str) -> str:
    """Generate UE5 actor name for an up/up interface actor (045-ue5-digital-twin, FR-001)."""
    return f"NC_If_{_safe(hostname)}_{_safe(interface_name)}"


def generate_interface_label_actor_name(hostname: str, interface_name: str) -> str:
    """Generate UE5 actor name for an interface's label (045-ue5-digital-twin, FR-006)."""
    return f"NC_Label_If_{_safe(hostname)}_{_safe(interface_name)}"


def generate_link_label_actor_name(link_id: str) -> str:
    """Generate UE5 actor name for a link's label (045-ue5-digital-twin, FR-007)."""
    return f"NC_Label_Link_{_safe(link_id)}"


def generate_down_interface_summary_actor_name(hostname: str) -> str:
    """Generate UE5 actor name for a device's down-interface summary (045-ue5-digital-twin, FR-002)."""
    return f"NC_DownIf_{_safe(hostname)}"


LEGEND_ACTOR_NAME = "NC_Legend"


# =============================================================================
# Transform Helpers
# =============================================================================

def make_transform(
    location: list[float],
    rotation: Optional[list[float]] = None,
    scale: Optional[list[float]] = None,
) -> dict:
    """
    Create a UE5 ToolsetTransform object.

    Args:
        location: [x, y, z] position in centimeters
        rotation: [pitch, yaw, roll] in degrees (optional)
        scale: [x, y, z] scale factors (optional)

    Returns:
        Transform dict for UE5 MCP API
    """
    xform = {
        "location": {"x": location[0], "y": location[1], "z": location[2]}
    }
    if rotation:
        xform["rotation"] = {"pitch": rotation[0], "yaw": rotation[1], "roll": rotation[2]}
    if scale:
        xform["scale"] = {"x": scale[0], "y": scale[1], "z": scale[2]}
    return xform


def make_actor_ref(actor_name: str, level_path: str = "/Game/NetClaw/NetClawTopo") -> dict:
    """
    Create an actor reference object.

    Args:
        actor_name: The actor's label/name
        level_path: The level path (defaults to NetClaw topology level)

    Returns:
        Actor reference dict with refPath
    """
    return {"refPath": f"{level_path}.{level_path.split('/')[-1]}:PersistentLevel.{actor_name}"}


# =============================================================================
# Scene Setup - Create Empty Level First
# =============================================================================

async def setup_netclaw_level(client: UE5MCPClient) -> bool:
    """
    Set up a clean level for NetClaw topology.

    Creates /Game/NetClaw/ folder and prepares an empty level.
    This MUST be called before spawning any actors.

    Args:
        client: UE5 MCP client

    Returns:
        True if successful
    """
    # Create the NetClaw folder
    await client.call_tool(
        toolset_name=ASSET_TOOLSET,
        tool_name=TOOL_CREATE_FOLDER,
        arguments={"folder_path": "/Game/NetClaw"}
    )

    return True


async def load_mesh_asset(client: UE5MCPClient, mesh_path: str) -> Optional[dict]:
    """
    Load a mesh asset and return the loaded object reference.

    CRITICAL: Must load the mesh first before assigning to actors.

    Args:
        client: UE5 MCP client
        mesh_path: Path to the mesh asset (e.g., "/Engine/BasicShapes/Cube.Cube")

    Returns:
        Loaded asset reference dict or None if failed
    """
    result = await client.call_tool(
        toolset_name=ASSET_TOOLSET,
        tool_name=TOOL_LOAD_ASSET,
        arguments={"asset_path": mesh_path}
    )

    if result.success and result.data:
        # Return the loaded asset reference
        return result.data.get("returnValue") if isinstance(result.data, dict) else result.data
    return None


# =============================================================================
# Device Actor Operations
# =============================================================================

async def spawn_device_actor(
    client: UE5MCPClient,
    hostname: str,
    device_type: str,
    location: list[float],
    status: str = "healthy",
    scale: Optional[list[float]] = None,
) -> tuple[bool, Optional[DeviceActor]]:
    """
    Spawn a device actor in UE5.

    Process:
    1. Load the mesh asset first
    2. Spawn StaticMeshActor using add_to_scene_from_class
    3. Assign the loaded mesh using set_properties with 'staticMesh' (lowercase s)
    4. Set label for the device

    Args:
        client: UE5 MCP client
        hostname: Device hostname
        device_type: Device type (router, switch, etc.)
        location: [x, y, z] position
        status: Device health status
        scale: Optional custom scale [x, y, z]

    Returns:
        Tuple of (success, DeviceActor info or None)
    """
    # Determine shape and mesh path
    shape = DEVICE_SHAPES.get(device_type, "cube")
    mesh_path = STATIC_MESH_PATHS[shape]

    # Generate actor name
    actor_name = generate_device_actor_name(hostname)

    # Use hierarchical Z-height based on device type
    if location[2] == 0:  # If Z not specified, use default height for device type
        location[2] = LAYER_HEIGHTS.get(device_type, LAYER_HEIGHTS["unknown"])

    # Build transform with larger scale for visibility
    scale_list = scale or [100, 100, 100]
    xform = make_transform(location, scale=scale_list)

    # Step 1: Spawn empty StaticMeshActor using add_to_scene_from_class
    spawn_result = await client.call_tool(
        toolset_name=SCENE_TOOLSET,
        tool_name=TOOL_ADD_FROM_CLASS,
        arguments={
            "actor_type": {"refPath": STATIC_MESH_ACTOR_CLASS},
            "name": actor_name,
            "xform": xform,
            "snap_to_ground": False,
        },
    )

    if not spawn_result.success:
        return False, None

    # Extract the actor reference from result
    actor_ref = None
    if spawn_result.data:
        if isinstance(spawn_result.data, dict):
            actor_ref = spawn_result.data.get("returnValue")

    if not actor_ref:
        return False, None

    # Step 2: Load the mesh asset
    loaded_mesh = await load_mesh_asset(client, mesh_path)

    # Step 3: Assign mesh to actor using set_properties
    # CRITICAL: Use 'staticMesh' (lowercase 's') and pass the loaded asset object
    if loaded_mesh:
        await client.call_tool(
            toolset_name=OBJECT_TOOLSET,
            tool_name=TOOL_SET_PROPERTIES,
            arguments={
                "instance": actor_ref,
                "values": json.dumps({"staticMesh": loaded_mesh})
            },
        )

    # Step 4: Set label/tag for the actor
    await client.call_tool(
        toolset_name=ACTOR_TOOLSET,
        tool_name=TOOL_SET_LABEL,
        arguments={
            "actor": actor_ref,
            "label": hostname,
        },
    )

    # Add netclaw tag
    await client.call_tool(
        toolset_name=ACTOR_TOOLSET,
        tool_name=TOOL_ADD_TAG,
        arguments={
            "actor": actor_ref,
            "tag": NETCLAW_TAG,
        },
    )

    actor = DeviceActor(
        name=actor_name,
        ref_path=actor_ref.get("refPath", "") if isinstance(actor_ref, dict) else "",
        location=xform["location"],
        scale=xform.get("scale", DEFAULT_DEVICE_SCALE),
        tags=[NETCLAW_TAG, "device", device_type],
        hostname=hostname,
        device_type=device_type,
        status=status,
        label=hostname,
        metadata={
            "hostname": hostname,
            "device_type": device_type,
            "status": status,
        },
    )

    return True, actor


async def destroy_device_actor(
    client: UE5MCPClient,
    hostname: str,
) -> bool:
    """Remove a device actor from the scene."""
    actor_name = generate_device_actor_name(hostname)
    actor_ref = make_actor_ref(actor_name)

    result = await client.call_tool(
        toolset_name=SCENE_TOOLSET,
        tool_name=TOOL_REMOVE_FROM_SCENE,
        arguments={"actor": actor_ref},
    )

    return result.success


# =============================================================================
# Link Actor Operations
# =============================================================================

def calculate_link_transform(
    source_pos: list[float],
    target_pos: list[float],
) -> tuple[list[float], list[float], list[float]]:
    """
    Calculate position, rotation, and scale for a link cylinder.

    Args:
        source_pos: [x, y, z] of source device
        target_pos: [x, y, z] of target device

    Returns:
        Tuple of (location, rotation, scale) as lists
    """
    import math

    # Midpoint for position
    mid_x = (source_pos[0] + target_pos[0]) / 2
    mid_y = (source_pos[1] + target_pos[1]) / 2
    mid_z = (source_pos[2] + target_pos[2]) / 2

    # Distance for length
    dx = target_pos[0] - source_pos[0]
    dy = target_pos[1] - source_pos[1]
    dz = target_pos[2] - source_pos[2]
    distance = math.sqrt(dx * dx + dy * dy + dz * dz)

    # Calculate rotation angles (Pitch, Yaw, Roll in degrees)
    horizontal_dist = math.sqrt(dx * dx + dy * dy)

    if horizontal_dist > 0.001:
        yaw = math.degrees(math.atan2(dy, dx))
        pitch = math.degrees(math.atan2(-dz, horizontal_dist))
    else:
        yaw = 0
        pitch = 90 if dz < 0 else -90

    # Scale: thin cylinder with length matching distance
    # Default cylinder is 100 units, scale Z proportionally
    scale_z = max(distance / 100, 0.1)
    scale = [10, 10, scale_z]  # Thin visible cylinder

    return [mid_x, mid_y, mid_z], [pitch, yaw, 0], scale


async def spawn_link_actor(
    client: UE5MCPClient,
    source_hostname: str,
    target_hostname: str,
    source_pos: list[float],
    target_pos: list[float],
    status: str = "healthy",
) -> tuple[bool, Optional[LinkActor]]:
    """
    Spawn a link actor (cylinder) connecting two devices.

    Args:
        client: UE5 MCP client
        source_hostname: Source device hostname
        target_hostname: Target device hostname
        source_pos: Source device [x, y, z] position
        target_pos: Target device [x, y, z] position
        status: Link status

    Returns:
        Tuple of (success, LinkActor info or None)
    """
    actor_name = generate_link_actor_name(source_hostname, target_hostname)
    mesh_path = STATIC_MESH_PATHS["cylinder"]

    # Calculate transform
    location, rotation, scale = calculate_link_transform(source_pos, target_pos)
    xform = make_transform(location, rotation, scale)

    # Step 1: Spawn empty StaticMeshActor
    spawn_result = await client.call_tool(
        toolset_name=SCENE_TOOLSET,
        tool_name=TOOL_ADD_FROM_CLASS,
        arguments={
            "actor_type": {"refPath": STATIC_MESH_ACTOR_CLASS},
            "name": actor_name,
            "xform": xform,
            "snap_to_ground": False,
        },
    )

    if not spawn_result.success:
        return False, None

    actor_ref = None
    if spawn_result.data:
        if isinstance(spawn_result.data, dict):
            actor_ref = spawn_result.data.get("returnValue")

    if not actor_ref:
        return False, None

    # Step 2: Load and assign cylinder mesh
    loaded_mesh = await load_mesh_asset(client, mesh_path)

    if loaded_mesh:
        await client.call_tool(
            toolset_name=OBJECT_TOOLSET,
            tool_name=TOOL_SET_PROPERTIES,
            arguments={
                "instance": actor_ref,
                "values": json.dumps({"staticMesh": loaded_mesh})
            },
        )

    # Step 3: Add tag
    await client.call_tool(
        toolset_name=ACTOR_TOOLSET,
        tool_name=TOOL_ADD_TAG,
        arguments={
            "actor": actor_ref,
            "tag": NETCLAW_TAG,
        },
    )

    actor = LinkActor(
        name=actor_name,
        ref_path=actor_ref.get("refPath", "") if isinstance(actor_ref, dict) else "",
        location=xform["location"],
        rotation=xform["rotation"],
        scale=xform["scale"],
        tags=[NETCLAW_TAG, "link", status],
        source_device=source_hostname,
        target_device=target_hostname,
        status=status,
        metadata={
            "source_device": source_hostname,
            "target_device": target_hostname,
            "status": status,
        },
    )

    return True, actor


async def destroy_link_actor(
    client: UE5MCPClient,
    source_hostname: str,
    target_hostname: str,
) -> bool:
    """Remove a link actor from the scene."""
    actor_name = generate_link_actor_name(source_hostname, target_hostname)
    actor_ref = make_actor_ref(actor_name)

    result = await client.call_tool(
        toolset_name=SCENE_TOOLSET,
        tool_name=TOOL_REMOVE_FROM_SCENE,
        arguments={"actor": actor_ref},
    )

    return result.success


# =============================================================================
# Batch Operations
# =============================================================================

async def find_netclaw_actors(client: UE5MCPClient) -> list[dict]:
    """Find all NetClaw actors in the scene."""
    result = await client.call_tool(
        toolset_name=SCENE_TOOLSET,
        tool_name=TOOL_FIND_ACTORS,
        arguments={
            "name": "NC_",  # All NetClaw actors start with NC_
            "tag": NETCLAW_TAG,
            "collision_channels": [],
        },
    )

    if not result.success or result.data is None:
        return []

    data = result.data

    # LIVE INCIDENT 2026-07-02: UE5 8.0 was observed returning find_actors'
    # result as a raw JSON string instead of an already-parsed dict/list,
    # which crashed the old `result.data.get(...)` with
    # "'str' object has no attribute 'get'" during clear_all_netclaw_actors.
    # Tolerate str (re-parse), dict (expected shape), and list (defensive,
    # in case returnValue is ever returned unwrapped) uniformly.
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, ValueError):
            return []

    if isinstance(data, dict):
        actors = data.get("returnValue", [])
    elif isinstance(data, list):
        actors = data
    else:
        actors = []

    return actors if isinstance(actors, list) else []


async def clear_all_netclaw_actors(client: UE5MCPClient) -> int:
    """Remove all NetClaw actors from the scene."""
    actors = await find_netclaw_actors(client)
    removed = 0

    for actor in actors:
        ref_path = actor.get("refPath", "") if isinstance(actor, dict) else ""
        if ref_path:
            result = await client.call_tool(
                toolset_name=SCENE_TOOLSET,
                tool_name=TOOL_REMOVE_FROM_SCENE,
                arguments={"actor": {"refPath": ref_path}},
            )
            if result.success:
                removed += 1

    return removed


async def save_level(client: UE5MCPClient) -> bool:
    """
    Save the current level.

    Note: Level should be saved to /Game/NetClaw/NetClawTopo via
    File > Save Current Level As... first to avoid /Temp/ path issues.
    """
    result = await client.call_tool(
        toolset_name=ASSET_TOOLSET,
        tool_name=TOOL_SAVE_ASSETS,
        arguments={"all": True}
    )

    return result.success


# =============================================================================
# Material Application
# =============================================================================
#
# 044 left this as a TODO stub returning True unconditionally, because the
# generic MaterialInstanceTools API's exact parameter schema was never
# confirmed live. That silently no-op'd every device/link status-color update
# ever since (handle_device_status_change/handle_link_status_change always
# reported success without actually recoloring anything in the scene).
#
# Fixed here (045-ue5-digital-twin) by reusing the SAME find-actor-by-label +
# dynamic-material-instance approach the batch-build script already uses
# successfully for the initial color pass (see _apply_color inside
# build_batch_scene_script) — routed through execute_tool_script, the one
# UE5 interaction path this codebase has actually verified live.

async def apply_actor_color(
    client: UE5MCPClient,
    actor_label: str,
    rgb: list[float],
    emissive_intensity: float = 0.0,
) -> bool:
    """
    Recolor an already-spawned actor (found by its outliner label) by
    applying a new dynamic material instance. Used for every post-build
    status/traffic/alert color change in US4-US6 and US9 — the actor must
    already exist (spawned by render_topology_batch/render_topology); this
    never spawns anything itself.
    """
    script = f'''
import json
import unreal

_editor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
_ok = False
try:
    target = None
    for a in _editor.get_all_level_actors():
        if a.get_actor_label() == "{actor_label}":
            target = a
            break
    if target:
        mesh_component = target.get_component_by_class(unreal.StaticMeshComponent)
        if mesh_component:
            base_material = unreal.load_asset("/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial")
            if base_material:
                dyn_material = unreal.KismetMaterialLibrary.create_dynamic_material_instance(
                    unreal.EditorLevelLibrary.get_editor_world(), base_material
                )
                if dyn_material:
                    dyn_material.set_vector_parameter_value(
                        "BaseColor", unreal.LinearColor({rgb[0]}, {rgb[1]}, {rgb[2]}, 1.0)
                    )
                    if {emissive_intensity} > 0:
                        dyn_material.set_scalar_parameter_value("EmissiveIntensity", {emissive_intensity})
                        dyn_material.set_vector_parameter_value(
                            "EmissiveColor", unreal.LinearColor({rgb[0]}, {rgb[1]}, {rgb[2]}, 1.0)
                        )
                    mesh_component.set_material(0, dyn_material)
                    _ok = True
except Exception as exc:
    unreal.log_error("apply_actor_color failed: " + str(exc))
    _ok = False

result = json.dumps({{"applied": _ok}})
print(result)
'''
    exec_result = await client.call_tool(
        toolset_name=PROGRAMMATIC_TOOLSET,
        tool_name=TOOL_EXECUTE_SCRIPT,
        arguments={"script": script},
    )
    if not exec_result.success:
        return False
    if isinstance(exec_result.data, dict):
        return bool(exec_result.data.get("applied", False))
    # execute_tool_script's own return-value convention was never confirmed
    # live (see module docstring) — treat a bare success as best-effort True
    # rather than failing a color change we likely did apply.
    return True


async def apply_device_material(
    client: UE5MCPClient,
    hostname: str,
    device_type: str,
    status: str = "healthy",
) -> bool:
    """Apply material to a device actor based on type and status."""
    try:
        from .materials import get_device_status_color, get_device_type_color
    except ImportError:  # pragma: no cover - fallback for sys.path-style loading
        from materials import get_device_status_color, get_device_type_color

    color = get_device_status_color(status) or get_device_type_color(device_type)
    emissive = 2.0 if status in ("critical", "unreachable") else (1.0 if status == "warning" else 0.0)
    return await apply_actor_color(client, generate_device_actor_name(hostname), color.to_list(), emissive)


async def apply_link_material(
    client: UE5MCPClient,
    source_hostname: str,
    target_hostname: str,
    status: str = "healthy",
) -> bool:
    """Apply material to a link actor based on status."""
    try:
        from .materials import get_link_status_color
    except ImportError:  # pragma: no cover - fallback for sys.path-style loading
        from materials import get_link_status_color

    color = get_link_status_color(status)
    emissive = 2.0 if status == "down" else (1.0 if status == "degraded" else 0.0)
    actor_name = generate_link_actor_name(source_hostname, target_hostname)
    return await apply_actor_color(client, actor_name, color.to_list(), emissive)


async def apply_interface_material(
    client: UE5MCPClient,
    hostname: str,
    interface_name: str,
    rgb: list[float],
    emissive_intensity: float = 0.0,
) -> bool:
    """
    Recolor an interface actor (045-ue5-digital-twin). Used by traffic
    visualization (US4), health polling (US5), and sticky trap alerts (US6).
    Callers MUST check is_interface_in_topology() first (FR-040) — this
    function does not verify the interface actor exists before trying.
    """
    actor_name = generate_interface_actor_name(hostname, interface_name)
    return await apply_actor_color(client, actor_name, rgb, emissive_intensity)


# =============================================================================
# Batch Build (execute_tool_script) — devices + links + labels in ONE round trip
# =============================================================================
#
# LESSONS FROM 2026-07-01 LIVE INCIDENT (John's PC crashed repeatedly mid-build):
#
# 1. Spawning one actor at a time (spawn_device_actor / spawn_link_actor above)
#    costs ~4 MCP round trips per actor (spawn, load mesh, set_properties,
#    set_label/add_tag). For a 10-device/12-link topology that is ~90 round
#    trips at 15-20s each — several minutes, and every one of those round
#    trips is a chance for a host crash to leave the build half-finished.
# 2. `execute_tool_script` (PROGRAMMATIC_TOOLSET) runs an arbitrary Python
#    script INSIDE UE5's embedded interpreter in a single MCP call. Schema
#    confirmed live against a running UE5 8.0 MCP server on 2026-07-02:
#        {"script": "<python source as a string>"}  (script is required)
#    The exact shape of the *return* value was not confirmed live (the UE5
#    session hung before a round trip completed — the same host instability
#    this whole incident was about). This code defensively parses whatever
#    comes back and, more importantly, does NOT trust it: after running the
#    script it re-queries the scene via find_netclaw_actors() to confirm
#    what actually got spawned, exactly like the live agent did by hand
#    ("Verification confirms the scene: 10 devices, 12 links in their
#    folders"). Treat the return-value parsing as a nice-to-have, and the
#    re-query as the source of truth.
# 3. `_StrictDict` (UE5's wrapper around dicts/objects returned by its own
#    APIs) does NOT support `.get(key, default)` — only `.get(key)` (no
#    default) or direct `["key"]` access. This ONLY applies to objects that
#    come from calling INTO UE5 from a running script (e.g. the return value
#    of get_component_by_class(), get_all_level_actors(), etc.) — it does
#    NOT apply to plain dicts we build ourselves. To sidestep this class of
#    bug entirely, the generated script below does all positioning/coloring
#    math on the CLIENT side (in Python, before the script is even built)
#    and only *plays back* pre-computed literals inside UE5 — the UE5-side
#    script never needs to read a key out of a UE5-returned dict at all.
# 4. TextRenderActor spawns with a small editor-only billboard/sprite child
#    component (the "Tt" icon) that renders as a black box in editor
#    viewport screenshots, distinct from the actual 3D text. It must be
#    hidden explicitly (see _hide_billboard() in the generated script) or
#    every label doubles as an eyesore in any CaptureViewport screenshot.
# 5. Default TextRenderComponent world_size (previously 24-95 in earlier
#    experiments) is unreadable at real topology scale (~4-5k unit scene
#    span). Auto-scale it from the scene's bounding-box diagonal instead of
#    hardcoding a constant.
# 6. Temp levels (`/Temp/Untitled_*`) cannot be persisted with
#    AssetTools.save_assets — that only flushes dirty *content* assets, not
#    the level itself. Saving the level requires a real `/Game/` path (see
#    save_level_as() below).
# 7. Anything written to `/tmp` is lost if WSL restarts (which happens on
#    every host crash). Persist working artifacts under WORKSPACE_UE5_DIR
#    instead — see persist_build_artifacts().

from pathlib import Path

# Persist topology + generated scripts here, NOT /tmp — WSL restarts on every
# host crash and wipes /tmp, which is exactly what cost an hour of rework
# during the 2026-07-01 incident ("Everything in /tmp is gone").
WORKSPACE_UE5_DIR = Path.home() / ".openclaw" / "workspace" / "ue5-topo"


def persist_build_artifacts(topology_json: dict, script: str, tag: str = "last_build") -> None:
    """Write the topology payload and generated UE5 script to disk so a mid-build
    crash doesn't lose them. Best-effort only — never raises."""
    try:
        WORKSPACE_UE5_DIR.mkdir(parents=True, exist_ok=True)
        (WORKSPACE_UE5_DIR / f"{tag}.json").write_text(json.dumps(topology_json, indent=2))
        (WORKSPACE_UE5_DIR / f"{tag}.py").write_text(script)
    except OSError:
        pass


INTERFACE_OFFSET_RADIUS = 60.0   # cm - small ring around the parent device
INTERFACE_SCALE = [20.0, 20.0, 20.0]  # small sphere, distinct from the device itself


def resolve_device_interfaces(
    device: "NetworkDevice",
    links: list["NetworkLink"],
) -> tuple[list[str], list[str]]:
    """
    Determine a device's up and down interface names (045-ue5-digital-twin, FR-001/FR-002).

    If the device carries an explicit `interfaces` inventory (from pyATS/gNMI,
    e.g. real "show interfaces" data), that is authoritative: entries with
    status "up" become up-interface actors, entries with any other status
    (e.g. "down", "admin-down") go into the down-interface summary.

    If no explicit inventory is present, up interfaces are inferred purely
    from this device's link endpoints (a link can only exist between
    interfaces that are up) and NO down-interface list is produced — there is
    no reliable way to enumerate ports we have zero data about at all. This
    keeps the existing 044 CML+pyATS topology-only workflow (link-derived
    interface names, no full "show interfaces" inventory) working unchanged.

    Returns (up_interface_names, down_interface_names), each de-duplicated
    and order-preserving.
    """
    up: list[str] = []
    down: list[str] = []
    seen_up: set[str] = set()
    seen_down: set[str] = set()

    if device.interfaces:
        for iface in device.interfaces:
            name = iface.get("name", "")
            if not name:
                continue
            status = str(iface.get("status", "down")).lower()
            if status == "up":
                if name not in seen_up:
                    up.append(name)
                    seen_up.add(name)
            else:
                if name not in seen_down:
                    down.append(name)
                    seen_down.add(name)
        return up, down

    # Fallback: infer up interfaces from this device's link endpoints only.
    for link in links:
        if link.source_device == device.hostname and link.source_interface:
            if link.source_interface not in seen_up:
                up.append(link.source_interface)
                seen_up.add(link.source_interface)
        if link.target_device == device.hostname and link.target_interface:
            if link.target_interface not in seen_up:
                up.append(link.target_interface)
                seen_up.add(link.target_interface)
    return up, down


def _compute_batch_specs(
    topology: "TopologyGraph",
    positions: dict[str, list[float]],
) -> tuple[list[dict], list[dict], list[dict], list[dict], Optional[dict], float]:
    """Precompute every device/interface/link/down-summary/legend spec (mesh,
    transform, color, label) on the client side, so the UE5-side script is
    pure playback with no branching logic that could touch a _StrictDict.

    Returns (device_specs, interface_specs, link_specs, down_summary_specs,
    legend_spec, label_world_size).
    """
    import math

    try:
        from .materials import (
            get_device_type_color,
            get_device_status_color,
            get_link_status_color,
            generate_legend_swatches,
        )
    except ImportError:  # pragma: no cover - fallback for sys.path-style loading
        from materials import (
            get_device_type_color,
            get_device_status_color,
            get_link_status_color,
            generate_legend_swatches,
        )

    device_specs = []
    interface_specs = []
    down_summary_specs = []
    # interface position lookup for link attachment: "hostname:interface" -> [x,y,z]
    interface_positions: dict[str, list[float]] = {}
    min_pt = [float("inf")] * 3
    max_pt = [float("-inf")] * 3

    for device in topology.devices:
        pos = positions.get(device.hostname)
        if not pos:
            continue
        shape = DEVICE_SHAPES.get(device.device_type, "cube")
        color = get_device_status_color(device.status) or get_device_type_color(device.device_type)
        device_specs.append({
            "name": generate_device_actor_name(device.hostname),
            "label": device.hostname,
            "mesh_path": STATIC_MESH_PATHS[shape],
            "location": pos,
            "scale": [100, 100, 100],
            "color": color.to_list(),
            "device_type": device.device_type,
        })
        for i in range(3):
            min_pt[i] = min(min_pt[i], pos[i])
            max_pt[i] = max(max_pt[i], pos[i])

        # US1 (FR-001/FR-002): spawn an actor only for up/up interfaces;
        # down interfaces get one compact summary actor per device, never
        # one actor each.
        up_ifaces, down_ifaces = resolve_device_interfaces(device, topology.links)
        for idx, iface_name in enumerate(up_ifaces):
            angle = (2 * math.pi * idx) / max(len(up_ifaces), 1)
            offset = [
                INTERFACE_OFFSET_RADIUS * math.cos(angle),
                INTERFACE_OFFSET_RADIUS * math.sin(angle),
                INTERFACE_OFFSET_RADIUS * 0.5,
            ]
            iface_pos = [pos[i] + offset[i] for i in range(3)]
            interface_positions[f"{device.hostname}:{iface_name}"] = iface_pos
            interface_specs.append({
                "name": generate_interface_actor_name(device.hostname, iface_name),
                "label": iface_name,
                "parent_hostname": device.hostname,
                "interface_name": iface_name,
                "location": iface_pos,
                "scale": INTERFACE_SCALE,
                "color": color.to_list(),
            })

        if down_ifaces:
            down_summary_specs.append({
                "name": generate_down_interface_summary_actor_name(device.hostname),
                "parent_hostname": device.hostname,
                "location": [pos[0], pos[1], pos[2] + 140.0],
                "text": f"{len(down_ifaces)} down: " + ", ".join(down_ifaces[:8]) + (
                    ", ..." if len(down_ifaces) > 8 else ""
                ),
                "color": [0.8, 0.2, 0.2],
            })

    link_specs = []
    for link in topology.links:
        source_pos = positions.get(link.source_device)
        target_pos = positions.get(link.target_device)
        if not source_pos or not target_pos:
            continue

        # FR-003: attach to interface actors when both ends resolve to a
        # known up/up interface position; fall back to device-level
        # attachment otherwise (e.g. no interface data, or the named
        # interface was reported down and has no actor).
        src_key = f"{link.source_device}:{link.source_interface}" if link.source_interface else None
        dst_key = f"{link.target_device}:{link.target_interface}" if link.target_interface else None
        attach_source = interface_positions.get(src_key) if src_key else None
        attach_target = interface_positions.get(dst_key) if dst_key else None
        endpoint_source = attach_source or source_pos
        endpoint_target = attach_target or target_pos

        location, rotation, scale = calculate_link_transform(endpoint_source, endpoint_target)
        link_specs.append({
            "name": generate_link_actor_name(link.source_device, link.target_device),
            "link_id": link.id,
            "mesh_path": STATIC_MESH_PATHS["cylinder"],
            "location": location,
            "rotation": rotation,
            "scale": scale,
            "color": get_link_status_color(link.status).to_list(),
            "attached_to_interfaces": bool(attach_source and attach_target),
        })

    # US3 (FR-008/FR-009): one legend actor, generated directly from the live
    # color mapping so it can never drift out of sync with reality.
    legend_spec = None
    if device_specs:
        legend_lines = [f"{e['label']}: RGB{tuple(round(c, 2) for c in e['color'])}" for e in generate_legend_swatches()]
        legend_spec = {
            "name": LEGEND_ACTOR_NAME,
            "text": "LEGEND\n" + "\n".join(legend_lines),
            "location": [min_pt[0] - 300.0, min_pt[1] - 300.0, max_pt[2] + 300.0],
            "color": [1.0, 1.0, 1.0],
        }

    # Auto-scale label size from the scene's bounding-box diagonal.
    # Fixed sizes (24, then 95 during live testing) were unreadable once the
    # scene grew past a handful of devices; ~1/20th of the diagonal reads
    # cleanly at the overview camera distance camera.py uses.
    if all(v not in (float("inf"), float("-inf")) for v in min_pt + max_pt):
        span = sum((max_pt[i] - min_pt[i]) ** 2 for i in range(3)) ** 0.5
    else:
        span = 2000.0
    label_world_size = max(span / 20.0, 100.0)

    return device_specs, interface_specs, link_specs, down_summary_specs, legend_spec, label_world_size


def _spawn_text_render_snippet() -> str:
    """Shared UE5-side helper (embedded once) for spawning a labeled
    TextRenderActor — used by device/interface/link labels, down-interface
    summaries, and the legend. Kept as one function inside the generated
    script instead of four near-duplicates."""
    return '''
def _spawn_text(location, text, world_size, rgb, actor_label, extra_tag):
    loc = unreal.Vector(location[0], location[1], location[2])
    text_actor = _editor.spawn_actor_from_class(unreal.TextRenderActor, loc, unreal.Rotator(0, 0, 0))
    if not text_actor:
        return None
    text_component = text_actor.get_component_by_class(unreal.TextRenderComponent)
    if text_component:
        text_component.set_text(text)
        text_component.set_world_size(world_size)
        text_component.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
        text_component.set_text_render_color(
            unreal.Color(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255), 255)
        )
    text_actor.set_actor_label(actor_label)
    text_actor.tags.append("{tag}")
    if extra_tag:
        text_actor.tags.append(extra_tag)
    _hide_billboard(text_actor)
    return text_actor
'''.format(tag=NETCLAW_TAG)


def build_batch_scene_script(
    device_specs: list[dict],
    interface_specs: list[dict],
    link_specs: list[dict],
    down_summary_specs: list[dict],
    legend_spec: Optional[dict],
    label_world_size: float,
    include_labels: bool = True,
) -> str:
    """Generate a single self-contained Python script to run inside UE5 via
    execute_tool_script. Spawns every device, interface, link, down-interface
    summary, legend, and (optionally) label in one MCP round trip instead of
    one call per actor (045-ue5-digital-twin: US1 interface actors, US2
    labels, US3 legend, all folded into the same proven batch-build path).

    All positioning/color data is embedded as JSON literals — the script does
    no lookups against UE5-returned dicts, so it can't trip the _StrictDict
    .get(key, default) bug.
    """
    payload = {
        "devices": device_specs,
        "interfaces": interface_specs,
        "links": link_specs,
        "down_summaries": down_summary_specs,
        "legend": legend_spec,
        "label_world_size": label_world_size,
        "include_labels": include_labels,
    }
    return f'''
import json
import unreal

_data = json.loads({json.dumps(json.dumps(payload))})
_editor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
_mesh_cache = {{}}
_errors = []
_devices_ok = 0
_interfaces_ok = 0
_links_ok = 0
_labels_ok = 0
_down_summaries_ok = 0
_legend_ok = 0


def _load_mesh(path):
    if path not in _mesh_cache:
        _mesh_cache[path] = unreal.load_asset(path)
    return _mesh_cache[path]


def _apply_color(actor, rgb):
    mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
    if not mesh_component:
        return
    base_material = unreal.load_asset("/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial")
    if not base_material:
        return
    dyn_material = unreal.KismetMaterialLibrary.create_dynamic_material_instance(
        unreal.EditorLevelLibrary.get_editor_world(), base_material
    )
    if dyn_material:
        dyn_material.set_vector_parameter_value(
            "BaseColor", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0)
        )
        mesh_component.set_material(0, dyn_material)


def _hide_billboard(actor):
    # TextRenderActor spawns an editor-only billboard/sprite child (the "Tt"
    # icon) that shows up as a black box in CaptureViewport screenshots.
    # Hide every billboard component so only the real text renders.
    for comp in actor.get_components_by_class(unreal.BillboardComponent):
        comp.set_visibility(False)
        comp.set_hidden_in_game(True)

{_spawn_text_render_snippet()}

for spec in _data["devices"]:
    try:
        mesh = _load_mesh(spec["mesh_path"])
        loc = spec["location"]
        actor = _editor.spawn_actor_from_class(
            unreal.StaticMeshActor, unreal.Vector(loc[0], loc[1], loc[2]), unreal.Rotator(0, 0, 0)
        )
        if not actor:
            _errors.append("spawn failed: " + spec["name"])
            continue
        mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if mesh_component and mesh:
            mesh_component.set_static_mesh(mesh)
        scale = spec["scale"]
        actor.set_actor_scale3d(unreal.Vector(scale[0], scale[1], scale[2]))
        # Actor label carries the NC_-prefixed name (not the bare hostname) so
        # the post-build find_actors re-query (the source of truth for
        # devices_rendered) can actually tell devices apart from every other
        # NC_-tagged actor kind by name prefix alone.
        actor.set_actor_label(spec["name"])
        actor.tags.append("{NETCLAW_TAG}")
        actor.tags.append("device")
        _apply_color(actor, spec["color"])
        _devices_ok += 1

        if _data["include_labels"]:
            label_loc = [loc[0], loc[1], loc[2] + scale[2] * 0.75 + 50]
            if _spawn_text(label_loc, spec["label"], _data["label_world_size"], spec["color"], spec["label"] + "_Label", "label"):
                _labels_ok += 1
    except Exception as exc:
        _errors.append(spec.get("name", "?") + ": " + str(exc))

for spec in _data["interfaces"]:
    try:
        loc = spec["location"]
        actor = _editor.spawn_actor_from_class(
            unreal.StaticMeshActor, unreal.Vector(loc[0], loc[1], loc[2]), unreal.Rotator(0, 0, 0)
        )
        if not actor:
            _errors.append("interface spawn failed: " + spec["name"])
            continue
        mesh = _load_mesh("{STATIC_MESH_PATHS['sphere']}")
        mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if mesh_component and mesh:
            mesh_component.set_static_mesh(mesh)
        scale = spec["scale"]
        actor.set_actor_scale3d(unreal.Vector(scale[0], scale[1], scale[2]))
        actor.set_actor_label(spec["name"])
        actor.tags.append("{NETCLAW_TAG}")
        actor.tags.append("interface")
        _apply_color(actor, spec["color"])
        _interfaces_ok += 1

        if _data["include_labels"]:
            label_loc = [loc[0], loc[1], loc[2] + scale[2] * 1.5 + 20]
            label_size = max(_data["label_world_size"] * 0.5, 60.0)
            if _spawn_text(label_loc, spec["label"], label_size, spec["color"], spec["label"] + "_IfLabel", "label"):
                _labels_ok += 1
    except Exception as exc:
        _errors.append(spec.get("name", "?") + ": " + str(exc))

for spec in _data["links"]:
    try:
        mesh = _load_mesh(spec["mesh_path"])
        loc = spec["location"]
        rot = spec["rotation"]
        actor = _editor.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(loc[0], loc[1], loc[2]),
            unreal.Rotator(rot[0], rot[1], rot[2]),
        )
        if not actor:
            _errors.append("link spawn failed: " + spec["name"])
            continue
        mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if mesh_component and mesh:
            mesh_component.set_static_mesh(mesh)
        scale = spec["scale"]
        actor.set_actor_scale3d(unreal.Vector(scale[0], scale[1], scale[2]))
        actor.set_actor_label(spec["name"])
        actor.tags.append("{NETCLAW_TAG}")
        actor.tags.append("link")
        _apply_color(actor, spec["color"])
        _links_ok += 1

        if _data["include_labels"]:
            label_loc = [loc[0], loc[1], loc[2] + 40]
            label_size = max(_data["label_world_size"] * 0.5, 60.0)
            if _spawn_text(label_loc, spec.get("link_id", spec["name"]), label_size, spec["color"], spec["name"] + "_LinkLabel", "label"):
                _labels_ok += 1
    except Exception as exc:
        _errors.append(spec.get("name", "?") + ": " + str(exc))

for spec in _data["down_summaries"]:
    try:
        if _spawn_text(spec["location"], spec["text"], _data["label_world_size"] * 0.6, spec["color"], spec["name"], "down_summary"):
            _down_summaries_ok += 1
    except Exception as exc:
        _errors.append(spec.get("name", "?") + ": " + str(exc))

if _data["legend"]:
    try:
        spec = _data["legend"]
        if _spawn_text(spec["location"], spec["text"], _data["label_world_size"] * 0.7, spec["color"], spec["name"], "legend"):
            _legend_ok = 1
    except Exception as exc:
        _errors.append("legend: " + str(exc))

result = json.dumps({{
    "devices_spawned": _devices_ok,
    "interfaces_spawned": _interfaces_ok,
    "links_spawned": _links_ok,
    "labels_spawned": _labels_ok,
    "down_summaries_spawned": _down_summaries_ok,
    "legend_spawned": _legend_ok,
    "errors": _errors,
}})
print(result)
'''


async def render_topology_batch(
    client: UE5MCPClient,
    topology: "TopologyGraph",
    layout_config: Optional[Any] = None,
    clear_existing: bool = True,
    include_labels: bool = True,
) -> "RenderResult":
    """
    Render a full topology in ONE execute_tool_script round trip instead of
    one call per actor. This is the preferred path for initial/full builds —
    it is both much faster (1 round trip vs. ~4 per actor) and far more
    resistant to a mid-build host crash, since the whole scene is built
    atomically inside UE5 rather than across dozens of separate MCP calls
    that a crash can interrupt halfway through.

    Falls back is the caller's responsibility (see renderer.render_topology_fast).
    """
    import time
    try:
        from .layout import calculate_topology_layout
        from .renderer import RenderResult  # local import to avoid a circular import at module load
        from .scene import (
            get_scene_state,
            reset_scene_state,
            register_device_actor,
            register_link_actor,
            register_interface_actor,
            set_down_interfaces,
        )
    except ImportError:  # pragma: no cover - fallback for sys.path-style loading
        from layout import calculate_topology_layout
        from renderer import RenderResult  # local import to avoid a circular import at module load
        from scene import (
            get_scene_state,
            reset_scene_state,
            register_device_actor,
            register_link_actor,
            register_interface_actor,
            set_down_interfaces,
        )

    start_time = time.time()
    result = RenderResult(success=True)

    if clear_existing:
        await clear_all_netclaw_actors(client)
        reset_scene_state()

    device_dicts = [{"hostname": d.hostname, "device_type": d.device_type} for d in topology.devices]
    link_dicts = [{"source_device": l.source_device, "target_device": l.target_device} for l in topology.links]
    positions = calculate_topology_layout(device_dicts, link_dicts, layout_config)

    device_specs, interface_specs, link_specs, down_summary_specs, legend_spec, label_world_size = (
        _compute_batch_specs(topology, positions)
    )
    script = build_batch_scene_script(
        device_specs, interface_specs, link_specs, down_summary_specs, legend_spec, label_world_size, include_labels
    )

    persist_build_artifacts(
        {
            "devices": device_specs,
            "interfaces": interface_specs,
            "links": link_specs,
            "down_summaries": down_summary_specs,
            "legend": legend_spec,
            "label_world_size": label_world_size,
        },
        script,
    )

    exec_result = await client.call_tool(
        toolset_name=PROGRAMMATIC_TOOLSET,
        tool_name=TOOL_EXECUTE_SCRIPT,
        arguments={"script": script},
    )

    if not exec_result.success:
        result.success = False
        result.errors.append(f"execute_tool_script failed: {exec_result.error}")

    # Best-effort parse of the script's own summary (return-value convention
    # for execute_tool_script was not confirmed live — see module docstring
    # above). Never trust this alone; always re-verify against the scene.
    if isinstance(exec_result.data, dict):
        result.errors.extend(exec_result.data.get("errors") or [])

    # Source of truth: re-query the scene for what actually got spawned,
    # exactly like the live agent did by hand during the incident.
    #
    # BUG FIXED 2026-07-02 (found live, on a UE5 8.0 build): this used to be
    # `sum(...) or len(device_specs)`. When the real re-queried count was 0
    # (e.g. because execute_tool_script silently no-op'd — see the
    # `import unreal` sandbox-restriction note in the module docstring),
    # Python's `or` treated that legitimate 0 as falsy and silently
    # substituted the *intended* device count instead, reporting a false
    # "10 devices rendered" for a scene that had nothing in it. The whole
    # point of re-querying was to not trust the script's own claims — never
    # let a fallback quietly override a real (even if zero) count.
    actual_actors = await find_netclaw_actors(client)

    def _name(a: Any) -> str:
        return str(a.get("name", "")) if isinstance(a, dict) else ""

    # 045-ue5-digital-twin added interface/down-summary/legend/link-label
    # actors that also carry the NC_ prefix (previously only devices and
    # links did), so classification must key off each generator's exact
    # prefix rather than a loose "Link"/"_Label" substring check — that
    # looser check would double-count link labels (named "..._LinkLabel") as
    # extra links, and count interfaces/down-summaries/the legend as devices,
    # since none of those existed when this filter was first written.
    result.devices_rendered = sum(
        1 for a in actual_actors
        if _name(a).startswith("NC_")
        and not _name(a).startswith("NC_Link_")
        and not _name(a).startswith("NC_If_")
        and not _name(a).startswith("NC_DownIf_")
        and _name(a) != "NC_Legend"
        and "_Label" not in _name(a)
    )
    result.links_rendered = sum(
        1 for a in actual_actors
        if _name(a).startswith("NC_Link_") and "_LinkLabel" not in _name(a)
    )

    for device in topology.devices:
        pos = positions.get(device.hostname)
        if pos:
            register_device_actor(device.hostname, generate_device_actor_name(device.hostname), pos)
    for link in topology.links:
        register_link_actor(link.id, generate_link_actor_name(link.source_device, link.target_device))

    # US1 (FR-001/FR-002): mirror what the batch script actually spawned into
    # scene state, so is_interface_in_topology()/resolve_actor_ref() and the
    # down-interface HUD (US8/US12) can answer without re-querying UE5.
    for spec in interface_specs:
        register_interface_actor(spec["parent_hostname"], spec["interface_name"], spec["name"])
    for device in topology.devices:
        _, down_ifaces = resolve_device_interfaces(device, topology.links)
        if down_ifaces:
            set_down_interfaces(device.hostname, down_ifaces)

    state = get_scene_state()
    state.last_topology_hash = topology.to_hash()

    result.duration_seconds = time.time() - start_time
    if result.devices_rendered == 0 and len(topology.devices) > 0:
        result.success = False

    return result


async def save_level_as(client: UE5MCPClient, package_path: str = "/Game/NetClaw/NetClawTopo") -> bool:
    """
    Save the current level to a real /Game/ path via execute_tool_script.

    AssetTools.save_assets (save_level() above) only flushes dirty *content*
    assets — it cannot persist a /Temp/Untitled_* level, which has no file on
    disk to save to. This calls UE5's native save_map API directly, removing
    the need for the user to do File > Save Current Level As... by hand.
    """
    script = f'''
import json
import unreal

_ok = False
try:
    world = unreal.EditorLevelLibrary.get_editor_world()
    _ok = bool(unreal.EditorLoadingAndSavingUtils.save_map(world, "{package_path}"))
except Exception as exc:
    unreal.log_error("save_level_as failed: " + str(exc))
    _ok = False

result = json.dumps({{"saved": _ok}})
print(result)
'''
    exec_result = await client.call_tool(
        toolset_name=PROGRAMMATIC_TOOLSET,
        tool_name=TOOL_EXECUTE_SCRIPT,
        arguments={"script": script},
    )
    if not exec_result.success:
        return False
    if isinstance(exec_result.data, dict):
        return bool(exec_result.data.get("saved"))
    # Return-value convention unconfirmed (see module docstring) — treat a
    # successful call with no parseable summary as "probably worked" but
    # tell the caller to verify manually rather than silently assuming.
    return True


# =============================================================================
# Foundational: Topology Name Resolution (045-ue5-digital-twin)
# =============================================================================
#
# Shared by diagnostics.py, panels.py, incidents.py, playback.py, and
# hierarchy.py to satisfy FR-040: any request naming a device, interface, or
# link not present in the CURRENTLY BUILT topology must be reported to the
# user rather than silently attempted or ignored. This is the single place
# that answers "is this actually in the scene right now?" so every new
# capability in this feature reports the same way instead of each
# reinventing (and potentially getting wrong) its own check.

def is_device_in_topology(hostname: str) -> bool:
    """True if `hostname` currently has a tracked device actor."""
    try:
        from .scene import get_scene_state
    except ImportError:  # pragma: no cover - fallback for sys.path-style loading
        from scene import get_scene_state
    return hostname in get_scene_state().device_actors


def is_interface_in_topology(hostname: str, interface_name: str) -> bool:
    """True if this device/interface pair currently has a tracked up/up interface actor."""
    try:
        from .scene import is_interface_tracked
    except ImportError:  # pragma: no cover - fallback for sys.path-style loading
        from scene import is_interface_tracked
    return is_interface_tracked(hostname, interface_name)


def is_link_in_topology(link_id: str) -> bool:
    """True if `link_id` currently has a tracked link actor."""
    try:
        from .scene import get_scene_state
    except ImportError:  # pragma: no cover - fallback for sys.path-style loading
        from scene import get_scene_state
    return link_id in get_scene_state().link_actors


def resolve_actor_ref(name: str) -> Optional[dict]:
    """
    Resolve a device hostname, "hostname:interface" pair, or link id against
    the currently built topology and return a UE5 actor reference dict, or
    None if it isn't present. Callers MUST report a None result to the user
    (FR-040) rather than proceeding as if the actor existed.
    """
    try:
        from .scene import get_scene_state
    except ImportError:  # pragma: no cover - fallback for sys.path-style loading
        from scene import get_scene_state
    state = get_scene_state()

    if name in state.device_actors:
        return make_actor_ref(state.device_actors[name])
    if name in state.interface_actors:
        return make_actor_ref(state.interface_actors[name])
    if name in state.link_actors:
        return make_actor_ref(state.link_actors[name])
    return None


async def capture_scene_screenshot(
    client: UE5MCPClient,
    filename: str,
    width: int = 1920,
    height: int = 1080,
) -> bool:
    """
    Capture a screenshot of the editor viewport via execute_tool_script.

    Avoids the built-in CaptureViewport MCP tool, whose schema requires every
    field (including a full nested `annotations` struct) with no defaults
    honored despite being marked optional — discovered the hard way during
    the 2026-07-01 incident. UE5's own AutomationLibrary screenshot API takes
    a plain filename and needs no such struct.
    """
    script = f'''
import json
import unreal

_ok = False
try:
    unreal.AutomationLibrary.take_high_res_screenshot({width}, {height}, "{filename}")
    _ok = True
except Exception as exc:
    unreal.log_error("capture_scene_screenshot failed: " + str(exc))
    _ok = False

result = json.dumps({{"captured": _ok}})
print(result)
'''
    exec_result = await client.call_tool(
        toolset_name=PROGRAMMATIC_TOOLSET,
        tool_name=TOOL_EXECUTE_SCRIPT,
        arguments={"script": script},
    )
    return exec_result.success
