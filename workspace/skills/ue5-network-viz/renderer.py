"""
Topology Renderer for UE5 Network Visualization.

This module orchestrates the complete rendering of network topology
in Unreal Engine 5, coordinating layout calculation, actor spawning,
material application, and scene setup.
"""

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

try:
    from .ue5_mcp_client import UE5MCPClient, UE5MCPError, check_connectivity
    from .layout import calculate_topology_layout, LayoutConfig, Vector3
    from .materials import infer_device_type, create_device_material_config
except ImportError:  # pragma: no cover - fallback for sys.path-style loading
    from ue5_mcp_client import UE5MCPClient, UE5MCPError, check_connectivity
    from layout import calculate_topology_layout, LayoutConfig, Vector3
    from materials import infer_device_type, create_device_material_config
try:
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
    )
except ImportError:  # pragma: no cover - fallback for sys.path-style loading
    from actors import (
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
    )
try:
    from .scene import (
        get_scene_state,
        reset_scene_state,
        register_device_actor,
        register_link_actor,
        unregister_device_actor,
        unregister_link_actor,
        get_tracked_devices,
        get_tracked_links,
        get_device_position,
        setup_default_lighting,
        sync_scene_state_from_ue5,
    )
except ImportError:  # pragma: no cover - fallback for sys.path-style loading
    from scene import (
        get_scene_state,
        reset_scene_state,
        register_device_actor,
        register_link_actor,
        unregister_device_actor,
        unregister_link_actor,
        get_tracked_devices,
        get_tracked_links,
        get_device_position,
        setup_default_lighting,
        sync_scene_state_from_ue5,
    )


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NetworkDevice:
    """Network device for visualization."""
    hostname: str
    device_type: str = "unknown"
    ip_addresses: list[str] = field(default_factory=list)
    model: str = ""
    vendor: str = ""
    status: str = "healthy"
    utilization: Optional[float] = None


@dataclass
class NetworkLink:
    """Network link for visualization."""
    source_device: str
    target_device: str
    source_interface: str = ""
    target_interface: str = ""
    status: str = "healthy"
    bandwidth: Optional[int] = None
    utilization: Optional[float] = None

    @property
    def id(self) -> str:
        """Generate unique link identifier."""
        return f"{self.source_device}_{self.target_device}"


@dataclass
class TopologyGraph:
    """Complete network topology."""
    devices: list[NetworkDevice] = field(default_factory=list)
    links: list[NetworkLink] = field(default_factory=list)
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)

    def to_hash(self) -> str:
        """Generate hash for change detection."""
        data = {
            "devices": [d.hostname for d in self.devices],
            "links": [f"{l.source_device}-{l.target_device}" for l in self.links],
        }
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()


@dataclass
class RenderResult:
    """Result of a render operation."""
    success: bool
    devices_rendered: int = 0
    links_rendered: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


# =============================================================================
# Topology Parsing
# =============================================================================

def parse_topology_dict(data: dict) -> TopologyGraph:
    """
    Parse topology data from dict format (from MCP queries).

    Args:
        data: Dict with 'devices' and 'links' lists

    Returns:
        TopologyGraph object
    """
    devices = []
    for d in data.get("devices", []):
        hostname = d.get("hostname", d.get("name", ""))
        device_type = d.get("device_type", "")
        if not device_type:
            device_type = infer_device_type(hostname, d.get("model", ""))

        devices.append(NetworkDevice(
            hostname=hostname,
            device_type=device_type,
            ip_addresses=d.get("ip_addresses", []),
            model=d.get("model", ""),
            vendor=d.get("vendor", ""),
            status=d.get("status", "healthy"),
            utilization=d.get("utilization"),
        ))

    links = []
    for l in data.get("links", []):
        links.append(NetworkLink(
            source_device=l.get("source_device", l.get("source", "")),
            target_device=l.get("target_device", l.get("target", "")),
            source_interface=l.get("source_interface", ""),
            target_interface=l.get("target_interface", ""),
            status=l.get("status", "healthy"),
            bandwidth=l.get("bandwidth"),
            utilization=l.get("utilization"),
        ))

    return TopologyGraph(
        devices=devices,
        links=links,
        source=data.get("source", "unknown"),
    )


# =============================================================================
# Main Render Functions
# =============================================================================

async def render_topology(
    client: UE5MCPClient,
    topology: TopologyGraph,
    clear_existing: bool = True,
    setup_lighting: bool = True,
    apply_materials: bool = True,
    layout_config: Optional[LayoutConfig] = None,
) -> RenderResult:
    """
    Render a complete network topology in UE5.

    This is the main orchestration function that:
    1. Clears existing actors (optional)
    2. Calculates layout positions
    3. Spawns device actors
    4. Spawns link actors
    5. Applies materials
    6. Sets up lighting

    Args:
        client: UE5 MCP client
        topology: Network topology to render
        clear_existing: Whether to clear existing NetClaw actors
        setup_lighting: Whether to configure scene lighting
        apply_materials: Whether to apply colored materials
        layout_config: Optional custom layout configuration

    Returns:
        RenderResult with success status and counts
    """
    import time
    start_time = time.time()

    result = RenderResult(success=True)

    try:
        # Step 1: Clear existing actors if requested
        if clear_existing:
            await clear_all_netclaw_actors(client)
            reset_scene_state()

        # Step 2: Calculate layout positions
        device_dicts = [
            {"hostname": d.hostname, "device_type": d.device_type}
            for d in topology.devices
        ]
        link_dicts = [
            {"source_device": l.source_device, "target_device": l.target_device}
            for l in topology.links
        ]

        positions = calculate_topology_layout(device_dicts, link_dicts, layout_config)

        # Step 3: Spawn device actors
        for device in topology.devices:
            if device.hostname not in positions:
                result.errors.append(f"No position for device: {device.hostname}")
                continue

            pos = positions[device.hostname]

            success, actor = await spawn_device_actor(
                client,
                hostname=device.hostname,
                device_type=device.device_type,
                location=pos,
                status=device.status,
            )

            if success:
                register_device_actor(device.hostname, actor.name, pos)
                result.devices_rendered += 1
            else:
                result.errors.append(f"Failed to spawn device: {device.hostname}")

        # Step 4: Spawn link actors
        for link in topology.links:
            source_pos = positions.get(link.source_device)
            target_pos = positions.get(link.target_device)

            if not source_pos or not target_pos:
                result.errors.append(f"Missing position for link: {link.id}")
                continue

            success, actor = await spawn_link_actor(
                client,
                source_hostname=link.source_device,
                target_hostname=link.target_device,
                source_pos=source_pos,
                target_pos=target_pos,
                status=link.status,
            )

            if success:
                register_link_actor(link.id, actor.name)
                result.links_rendered += 1
            else:
                result.errors.append(f"Failed to spawn link: {link.id}")

        # Step 5: Apply materials (optional)
        if apply_materials:
            for device in topology.devices:
                await apply_device_material(
                    client,
                    hostname=device.hostname,
                    device_type=device.device_type,
                    status=device.status,
                )

            for link in topology.links:
                await apply_link_material(
                    client,
                    source_hostname=link.source_device,
                    target_hostname=link.target_device,
                    status=link.status,
                )

        # Step 6: Setup lighting (optional)
        if setup_lighting:
            await setup_default_lighting(client)

        # Update scene state
        state = get_scene_state()
        state.last_topology_hash = topology.to_hash()

    except UE5MCPError as e:
        result.success = False
        result.errors.append(f"UE5 MCP error: {str(e)}")
    except Exception as e:
        result.success = False
        result.errors.append(f"Unexpected error: {str(e)}")

    result.duration_seconds = time.time() - start_time

    # Mark as failed if no devices rendered
    if result.devices_rendered == 0 and len(topology.devices) > 0:
        result.success = False

    return result


async def render_topology_from_dict(
    client: UE5MCPClient,
    data: dict,
    **kwargs,
) -> RenderResult:
    """
    Render topology from dict format.

    Args:
        client: UE5 MCP client
        data: Topology dict with 'devices' and 'links'
        **kwargs: Additional render options

    Returns:
        RenderResult
    """
    topology = parse_topology_dict(data)
    return await render_topology(client, topology, **kwargs)


async def render_topology_fast(
    client: UE5MCPClient,
    topology: TopologyGraph,
    clear_existing: bool = True,
    include_labels: bool = True,
    layout_config: Optional[LayoutConfig] = None,
) -> RenderResult:
    """
    Render a full topology using the single-round-trip batch build
    (actors.render_topology_batch) instead of one MCP call per actor.

    Preferred entry point for INITIAL/FULL builds — it's both much faster and
    far more resistant to a mid-build crash than render_topology(), per the
    2026-07-01 live incident where a per-actor build took 20+ minutes and was
    repeatedly interrupted by host crashes. Falls back to the proven
    per-actor render_topology() if the batch path either raises OR reports
    failure, so this can never be worse than the old behavior — only faster
    when it works.

    NOTE (found live 2026-07-02): not every UE5 MCP build allows
    execute_tool_script to `import unreal` — one UE5 8.0 build's script
    sandbox only permits stdlib modules (math/json/re/time/etc). On such a
    build, render_topology_batch's script fails immediately and comes back
    as a normal `success=False` RenderResult, NOT a raised exception — so
    this function must check `result.success`, not only catch exceptions,
    or the fallback never triggers and the caller gets a failed render
    instead of one via the proven per-actor path.

    render_topology_incremental() (health-state updates on an already-built
    scene) intentionally still uses the per-actor path — incremental updates
    touch one or two actors at a time, where the batch build's overhead
    (recomputing the whole scene) isn't worth it.
    """
    try:
        from .actors import render_topology_batch
    except ImportError:  # pragma: no cover - fallback for sys.path-style loading
        from actors import render_topology_batch

    batch_error: Optional[str] = None
    try:
        batch_result = await render_topology_batch(
            client,
            topology,
            layout_config=layout_config,
            clear_existing=clear_existing,
            include_labels=include_labels,
        )
        if batch_result.success:
            return batch_result
        batch_error = "; ".join(batch_result.errors) or "batch build reported failure"
    except Exception as e:
        batch_error = str(e)

    result = await render_topology(
        client,
        topology,
        clear_existing=clear_existing,
        layout_config=layout_config,
    )
    result.errors.insert(0, f"Batch build failed ({batch_error}); fell back to per-actor render.")
    return result


# =============================================================================
# Incremental Updates
# =============================================================================

@dataclass
class TopologyDiff:
    """Differences between two topology states."""
    devices_to_add: list[NetworkDevice] = field(default_factory=list)
    devices_to_remove: list[str] = field(default_factory=list)
    devices_to_update: list[NetworkDevice] = field(default_factory=list)
    links_to_add: list[NetworkLink] = field(default_factory=list)
    links_to_remove: list[str] = field(default_factory=list)
    links_to_update: list[NetworkLink] = field(default_factory=list)


def calculate_topology_diff(
    new_topology: TopologyGraph,
    current_devices: dict[str, str],
    current_links: dict[str, str],
) -> TopologyDiff:
    """
    Calculate differences between new topology and current scene state.

    Args:
        new_topology: New topology to render
        current_devices: Currently tracked devices (hostname -> actor_name)
        current_links: Currently tracked links (link_id -> actor_name)

    Returns:
        TopologyDiff with changes
    """
    diff = TopologyDiff()

    # Find device changes
    new_hostnames = {d.hostname for d in new_topology.devices}
    current_hostnames = set(current_devices.keys())

    diff.devices_to_add = [d for d in new_topology.devices if d.hostname not in current_hostnames]
    diff.devices_to_remove = list(current_hostnames - new_hostnames)
    diff.devices_to_update = [d for d in new_topology.devices if d.hostname in current_hostnames]

    # Find link changes
    new_link_ids = {l.id for l in new_topology.links}
    current_link_ids = set(current_links.keys())

    diff.links_to_add = [l for l in new_topology.links if l.id not in current_link_ids]
    diff.links_to_remove = list(current_link_ids - new_link_ids)
    diff.links_to_update = [l for l in new_topology.links if l.id in current_link_ids]

    return diff


async def render_topology_incremental(
    client: UE5MCPClient,
    topology: TopologyGraph,
    apply_materials: bool = True,
    layout_config: Optional[LayoutConfig] = None,
) -> RenderResult:
    """
    Render topology incrementally, only updating changed elements.

    Preserves camera position and existing actors that haven't changed.

    Args:
        client: UE5 MCP client
        topology: New topology to render
        apply_materials: Whether to apply/update materials
        layout_config: Optional custom layout configuration

    Returns:
        RenderResult
    """
    import time
    start_time = time.time()

    result = RenderResult(success=True)

    try:
        # Get current scene state
        current_devices = get_tracked_devices()
        current_links = get_tracked_links()

        # Calculate diff
        diff = calculate_topology_diff(topology, current_devices, current_links)

        # Calculate layout for all devices (needed for link positioning)
        device_dicts = [
            {"hostname": d.hostname, "device_type": d.device_type}
            for d in topology.devices
        ]
        link_dicts = [
            {"source_device": l.source_device, "target_device": l.target_device}
            for l in topology.links
        ]
        positions = calculate_topology_layout(device_dicts, link_dicts, layout_config)

        # Remove old links first (before removing devices)
        for link_id in diff.links_to_remove:
            parts = link_id.split("_")
            if len(parts) >= 2:
                await destroy_link_actor(client, parts[0], parts[1])
                unregister_link_actor(link_id)

        # Remove old devices
        for hostname in diff.devices_to_remove:
            await destroy_device_actor(client, hostname)
            unregister_device_actor(hostname)

        # Add new devices
        for device in diff.devices_to_add:
            pos = positions.get(device.hostname, [0, 0, 100])

            success, actor = await spawn_device_actor(
                client,
                hostname=device.hostname,
                device_type=device.device_type,
                location=pos,
                status=device.status,
            )

            if success:
                register_device_actor(device.hostname, actor.name, pos)
                result.devices_rendered += 1

                if apply_materials:
                    await apply_device_material(
                        client,
                        hostname=device.hostname,
                        device_type=device.device_type,
                        status=device.status,
                    )

        # Add new links
        for link in diff.links_to_add:
            source_pos = positions.get(link.source_device)
            target_pos = positions.get(link.target_device)

            if source_pos and target_pos:
                success, actor = await spawn_link_actor(
                    client,
                    source_hostname=link.source_device,
                    target_hostname=link.target_device,
                    source_pos=source_pos,
                    target_pos=target_pos,
                    status=link.status,
                )

                if success:
                    register_link_actor(link.id, actor.name)
                    result.links_rendered += 1

                    if apply_materials:
                        await apply_link_material(
                            client,
                            source_hostname=link.source_device,
                            target_hostname=link.target_device,
                            status=link.status,
                        )

        # Update existing devices (status changes)
        if apply_materials:
            for device in diff.devices_to_update:
                await apply_device_material(
                    client,
                    hostname=device.hostname,
                    device_type=device.device_type,
                    status=device.status,
                )

            for link in diff.links_to_update:
                await apply_link_material(
                    client,
                    source_hostname=link.source_device,
                    target_hostname=link.target_device,
                    status=link.status,
                )

        # Update scene state
        state = get_scene_state()
        state.last_topology_hash = topology.to_hash()

    except UE5MCPError as e:
        result.success = False
        result.errors.append(f"UE5 MCP error: {str(e)}")
    except Exception as e:
        result.success = False
        result.errors.append(f"Unexpected error: {str(e)}")

    result.duration_seconds = time.time() - start_time
    return result


# =============================================================================
# Device Details
# =============================================================================

async def get_device_details(
    client: UE5MCPClient,
    hostname: str,
) -> Optional[dict[str, Any]]:
    """
    Get details for a rendered device.

    Args:
        client: UE5 MCP client
        hostname: Device hostname

    Returns:
        Device metadata dict or None if not found
    """
    state = get_scene_state()

    if hostname not in state.device_actors:
        return None

    return {
        "hostname": hostname,
        "actor_name": state.device_actors[hostname],
        "position": state.device_positions.get(hostname),
    }


async def list_rendered_devices(client: UE5MCPClient) -> list[str]:
    """
    List all rendered device hostnames.

    Args:
        client: UE5 MCP client

    Returns:
        List of hostnames
    """
    return list(get_tracked_devices().keys())


# =============================================================================
# Error Handling
# =============================================================================

async def safe_render_topology(
    topology_data: dict,
    url: Optional[str] = None,
) -> RenderResult:
    """
    Safely render topology with connection error handling.

    This is the recommended entry point for external callers.

    Args:
        topology_data: Topology dict with 'devices' and 'links'
        url: Optional UE5 MCP URL override

    Returns:
        RenderResult
    """
    # Check connectivity first
    is_connected, message = await check_connectivity(url)

    if not is_connected:
        return RenderResult(
            success=False,
            errors=[message],
        )

    # Render topology using the fast batch-build path (falls back internally
    # to the per-actor path on failure — see render_topology_fast)
    topology = parse_topology_dict(topology_data)
    async with UE5MCPClient(url=url) as client:
        return await render_topology_fast(client, topology)
