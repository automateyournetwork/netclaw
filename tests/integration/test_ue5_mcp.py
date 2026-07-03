"""
Integration Tests for UE5 MCP Network Visualization.

These tests run against a live Unreal Engine 5.8 instance with the
MCP plugin enabled. They verify connectivity, tool discovery, and
actor spawning/manipulation operations.

Prerequisites:
- UE5.8 installed and running
- MCP plugin enabled (Edit > Plugins > Unreal MCP)
- MCP server started (auto-start or ModelContextProtocol.StartServer)

Run tests:
    pytest tests/integration/test_ue5_mcp.py -v

Skip if UE5 not running:
    pytest tests/integration/test_ue5_mcp.py -v -m "not ue5_required"

Performance tests (longer timeout):
    pytest tests/integration/test_ue5_mcp.py -k "performance" -v --timeout=120
"""

import os
import sys
import asyncio
import pytest
from pathlib import Path

# Add skill module to path for imports
skill_path = Path(__file__).parent.parent.parent / "workspace" / "skills" / "ue5-network-viz"
sys.path.insert(0, str(skill_path))

from ue5_mcp_client import (
    UE5MCPClient,
    UE5MCPError,
    check_connectivity,
    discover_tools,
)
from materials import (
    get_device_type_color,
    get_link_status_color,
    create_device_material_config,
    infer_device_type,
    DeviceType,
)
from layout import (
    ForceDirectedLayout,
    LayoutConfig,
    Vector3,
    calculate_topology_layout,
)


# =============================================================================
# Test Configuration
# =============================================================================

UE5_MCP_URL = os.environ.get("UE5_MCP_URL", "http://127.0.0.1:8000/mcp")

# Marker for tests requiring UE5 to be running
ue5_required = pytest.mark.skipif(
    os.environ.get("SKIP_UE5_TESTS", "").lower() in ("1", "true", "yes"),
    reason="UE5 tests skipped (SKIP_UE5_TESTS=1)",
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def ue5_client():
    """Create UE5 MCP client for testing."""
    return UE5MCPClient(url=UE5_MCP_URL)


@pytest.fixture
def sample_topology():
    """Sample network topology for testing."""
    return {
        "devices": [
            {"hostname": "core-rtr-01", "device_type": "router"},
            {"hostname": "dist-sw-01", "device_type": "switch"},
            {"hostname": "dist-sw-02", "device_type": "switch"},
            {"hostname": "fw-01", "device_type": "firewall"},
            {"hostname": "srv-01", "device_type": "endpoint"},
        ],
        "links": [
            {"source_device": "core-rtr-01", "target_device": "dist-sw-01"},
            {"source_device": "core-rtr-01", "target_device": "dist-sw-02"},
            {"source_device": "dist-sw-01", "target_device": "fw-01"},
            {"source_device": "dist-sw-02", "target_device": "fw-01"},
            {"source_device": "fw-01", "target_device": "srv-01"},
        ],
    }


# =============================================================================
# Connectivity Tests (T010, T011)
# =============================================================================

@ue5_required
class TestMCPConnectivity:
    """Tests for UE5 MCP server connectivity (T010)."""

    @pytest.mark.asyncio
    async def test_mcp_connectivity(self, ue5_client):
        """T010: Verify MCP server is reachable and responding."""
        async with ue5_client as client:
            is_connected = await client.ping(timeout=10.0)
            assert is_connected, (
                f"UE5 MCP server not reachable at {UE5_MCP_URL}. "
                "Ensure Unreal Editor is running with MCP plugin enabled."
            )

    @pytest.mark.asyncio
    async def test_connectivity_helper(self):
        """Test convenience function for connectivity check."""
        is_connected, message = await check_connectivity(UE5_MCP_URL)
        assert is_connected, message

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test error handling for unreachable server."""
        bad_url = "http://127.0.0.1:9999/mcp"
        async with UE5MCPClient(url=bad_url) as client:
            is_connected = await client.ping(timeout=2.0)
            assert not is_connected


@ue5_required
class TestToolDiscovery:
    """Tests for UE5 MCP tool discovery (T011)."""

    @pytest.mark.asyncio
    async def test_tool_discovery(self, ue5_client):
        """T011: Verify tool discovery via list_toolsets."""
        async with ue5_client as client:
            toolsets = await client.list_toolsets()
            assert len(toolsets) > 0, "No toolsets discovered from UE5 MCP"

            # Verify expected toolsets exist
            toolset_names = [ts.name for ts in toolsets]
            expected_toolsets = ["ActorTools"]  # At minimum

            for expected in expected_toolsets:
                # Check case-insensitively
                found = any(expected.lower() in name.lower() for name in toolset_names)
                assert found, f"Expected toolset '{expected}' not found in {toolset_names}"

    @pytest.mark.asyncio
    async def test_describe_toolset(self, ue5_client):
        """Test describing a toolset to get tool schemas."""
        async with ue5_client as client:
            toolsets = await client.list_toolsets()
            if not toolsets:
                pytest.skip("No toolsets available")

            # Describe first toolset
            tools = await client.describe_toolset(toolsets[0].name)
            assert len(tools) > 0, f"Toolset {toolsets[0].name} has no tools"

            # Verify tool structure
            for tool in tools:
                assert tool.name, "Tool missing name"
                assert isinstance(tool.parameters, dict), "Tool parameters should be dict"

    @pytest.mark.asyncio
    async def test_discover_all_tools(self):
        """Test discovering all available tools."""
        all_tools = await discover_tools(UE5_MCP_URL)
        assert len(all_tools) > 0, "No tools discovered"

        # Log discovered tools for debugging
        for toolset_name, tools in all_tools.items():
            print(f"\nToolset: {toolset_name}")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description[:50]}...")


# =============================================================================
# Actor Spawning Tests (T012-T016)
# =============================================================================

@ue5_required
class TestActorSpawning:
    """Tests for actor spawning operations."""

    @pytest.mark.asyncio
    async def test_spawn_single_device(self, ue5_client):
        """T012: Test spawning a single device actor."""
        async with ue5_client as client:
            result = await client.call_tool(
                toolset="ActorTools",
                tool="spawn_actor",
                args={
                    "class": "/Engine/BasicShapes/Cube.Cube",
                    "name": "netclaw_test_device_single",
                    "location": [0, 0, 100],
                    "scale": [50, 50, 50],
                    "tags": ["netclaw", "test", "device"],
                },
            )

            assert result.success, f"Failed to spawn actor: {result.error}"

            # Cleanup
            await client.call_tool(
                toolset="ActorTools",
                tool="destroy_actor",
                args={"name": "netclaw_test_device_single"},
            )

    @pytest.mark.asyncio
    async def test_spawn_multiple_devices(self, ue5_client):
        """T013: Test spawning multiple device actors."""
        async with ue5_client as client:
            device_names = []
            positions = [
                [0, 0, 100],
                [200, 0, 100],
                [400, 0, 100],
            ]

            # Spawn multiple devices
            for i, pos in enumerate(positions):
                name = f"netclaw_test_device_multi_{i}"
                device_names.append(name)

                result = await client.call_tool(
                    toolset="ActorTools",
                    tool="spawn_actor",
                    args={
                        "class": "/Engine/BasicShapes/Cube.Cube",
                        "name": name,
                        "location": pos,
                        "scale": [50, 50, 50],
                        "tags": ["netclaw", "test"],
                    },
                )
                assert result.success, f"Failed to spawn device {i}: {result.error}"

            # Cleanup
            for name in device_names:
                await client.call_tool(
                    toolset="ActorTools",
                    tool="destroy_actor",
                    args={"name": name},
                )

    @pytest.mark.asyncio
    async def test_remove_device(self, ue5_client):
        """T014: Test removing a device actor."""
        async with ue5_client as client:
            # Create
            actor_name = "netclaw_test_device_remove"
            create_result = await client.call_tool(
                toolset="ActorTools",
                tool="spawn_actor",
                args={
                    "class": "/Engine/BasicShapes/Cube.Cube",
                    "name": actor_name,
                    "location": [0, 0, 100],
                    "scale": [50, 50, 50],
                    "tags": ["netclaw", "test"],
                },
            )
            assert create_result.success, f"Failed to spawn: {create_result.error}"

            # Remove
            remove_result = await client.call_tool(
                toolset="ActorTools",
                tool="destroy_actor",
                args={"name": actor_name},
            )
            assert remove_result.success, f"Failed to remove: {remove_result.error}"

    @pytest.mark.asyncio
    async def test_spawn_link(self, ue5_client):
        """T015: Test spawning a link actor (cylinder)."""
        async with ue5_client as client:
            result = await client.call_tool(
                toolset="ActorTools",
                tool="spawn_actor",
                args={
                    "class": "/Engine/BasicShapes/Cylinder.Cylinder",
                    "name": "netclaw_test_link",
                    "location": [100, 0, 100],
                    "scale": [10, 10, 200],  # Elongated cylinder
                    "rotation": [90, 0, 0],  # Horizontal
                    "tags": ["netclaw", "test", "link"],
                },
            )

            assert result.success, f"Failed to spawn link: {result.error}"

            # Cleanup
            await client.call_tool(
                toolset="ActorTools",
                tool="destroy_actor",
                args={"name": "netclaw_test_link"},
            )

    @pytest.mark.asyncio
    async def test_device_colors(self, ue5_client):
        """T016: Test device type color differentiation."""
        # This test verifies the color mappings are correct
        # Actual material application requires MaterialInstanceTools

        router_color = get_device_type_color("router")
        switch_color = get_device_type_color("switch")
        firewall_color = get_device_type_color("firewall")

        # Colors should be different
        assert router_color.to_list() != switch_color.to_list()
        assert switch_color.to_list() != firewall_color.to_list()
        assert router_color.to_list() != firewall_color.to_list()

        # Verify expected colors
        assert router_color.b > router_color.r  # Blue-ish
        assert switch_color.g > switch_color.r  # Green-ish
        assert firewall_color.r > firewall_color.g  # Red-ish


# =============================================================================
# Material Tests
# =============================================================================

class TestMaterials:
    """Tests for material configuration (no UE5 required)."""

    def test_device_type_colors(self):
        """Test all device types have colors."""
        for device_type in DeviceType:
            color = get_device_type_color(device_type.value)
            assert color is not None
            assert len(color.to_list()) == 3
            assert all(0 <= c <= 1 for c in color.to_list())

    def test_link_status_colors(self):
        """Test all link statuses have colors."""
        for status in ["healthy", "degraded", "down", "unknown"]:
            color = get_link_status_color(status)
            assert color is not None
            assert len(color.to_list()) == 3

    def test_device_material_config(self):
        """Test device material configuration generation."""
        config = create_device_material_config(
            device_type="router",
            status="healthy",
            hostname="core-rtr-01",
        )

        assert config.name == "MI_Device_core_rtr_01"
        assert config.base_color is not None
        assert config.metallic >= 0
        assert config.roughness >= 0

    def test_device_material_critical_emissive(self):
        """Test critical status adds emissive glow."""
        config = create_device_material_config(
            device_type="router",
            status="critical",
            hostname="test",
        )

        assert config.emissive_color is not None
        assert config.emissive_intensity > 0

    def test_infer_device_type(self):
        """Test device type inference from hostname."""
        assert infer_device_type("core-rtr-01") == "router"
        assert infer_device_type("dist-sw-01") == "switch"
        assert infer_device_type("edge-fw-01") == "firewall"
        assert infer_device_type("ap-floor1") == "access_point"
        assert infer_device_type("f5-lb-01") == "load_balancer"
        assert infer_device_type("srv-web-01") == "endpoint"
        assert infer_device_type("unknown-device") == "unknown"


# =============================================================================
# Layout Tests
# =============================================================================

class TestLayout:
    """Tests for force-directed layout algorithm (no UE5 required)."""

    def test_single_node_layout(self):
        """Test layout with single node."""
        layout = ForceDirectedLayout()
        layout.add_node("node1", "router")

        positions = layout.get_positions()
        assert "node1" in positions
        assert len(positions["node1"]) == 3

    def test_two_node_layout(self):
        """Test layout with two connected nodes."""
        layout = ForceDirectedLayout()
        layout.add_node("node1", "router")
        layout.add_node("node2", "switch")
        layout.add_edge("node1", "node2")

        positions = layout.get_positions()
        assert len(positions) == 2

        # Nodes should be separated
        pos1 = Vector3(*positions["node1"])
        pos2 = Vector3(*positions["node2"])
        distance = (pos1 - pos2).magnitude()
        assert distance > 100  # Should be reasonably separated

    def test_topology_layout(self, sample_topology):
        """Test layout with sample topology."""
        positions = calculate_topology_layout(
            sample_topology["devices"],
            sample_topology["links"],
        )

        assert len(positions) == 5

        # All positions should be valid 3D coordinates
        for hostname, pos in positions.items():
            assert len(pos) == 3
            assert all(isinstance(c, float) for c in pos)

    def test_layout_bounds(self):
        """Test that layout respects bounds."""
        config = LayoutConfig(
            bounds_min=Vector3(-100, -100, 0),
            bounds_max=Vector3(100, 100, 200),
        )
        layout = ForceDirectedLayout(config)

        for i in range(10):
            layout.add_node(f"node{i}", "router")

        positions = layout.run()

        for pos in positions.values():
            assert -100 <= pos.x <= 100
            assert -100 <= pos.y <= 100
            assert 0 <= pos.z <= 200

    def test_vector3_operations(self):
        """Test Vector3 math operations."""
        v1 = Vector3(1, 2, 3)
        v2 = Vector3(4, 5, 6)

        # Addition
        v3 = v1 + v2
        assert v3.x == 5 and v3.y == 7 and v3.z == 9

        # Subtraction
        v4 = v2 - v1
        assert v4.x == 3 and v4.y == 3 and v4.z == 3

        # Scalar multiplication
        v5 = v1 * 2
        assert v5.x == 2 and v5.y == 4 and v5.z == 6

        # Magnitude
        v6 = Vector3(3, 4, 0)
        assert v6.magnitude() == 5.0


# =============================================================================
# Performance Tests
# =============================================================================

@ue5_required
class TestPerformance:
    """Performance tests for large topology rendering."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_render_100_devices(self, ue5_client):
        """T025: Test rendering 100 devices in <60 seconds."""
        import time

        async with ue5_client as client:
            start_time = time.time()
            actor_names = []

            # Spawn 100 devices in a grid
            for i in range(100):
                row = i // 10
                col = i % 10
                name = f"netclaw_perf_device_{i}"
                actor_names.append(name)

                result = await client.call_tool(
                    toolset="ActorTools",
                    tool="spawn_actor",
                    args={
                        "class": "/Engine/BasicShapes/Cube.Cube",
                        "name": name,
                        "location": [col * 200, row * 200, 100],
                        "scale": [50, 50, 50],
                        "tags": ["netclaw", "perf_test"],
                    },
                )

                if not result.success:
                    pytest.fail(f"Failed to spawn device {i}: {result.error}")

            spawn_time = time.time() - start_time
            print(f"\nSpawned 100 devices in {spawn_time:.2f} seconds")

            assert spawn_time < 60, f"Spawning took {spawn_time:.2f}s (>60s limit)"

            # Cleanup
            for name in actor_names:
                await client.call_tool(
                    toolset="ActorTools",
                    tool="destroy_actor",
                    args={"name": name},
                )


# =============================================================================
# Health State Tests (US2)
# =============================================================================

@ue5_required
class TestHealthVisualization:
    """Tests for device/link health color updates (T026-T028)."""

    @pytest.mark.asyncio
    async def test_device_health_color(self, ue5_client):
        """T026: Test device health color changes."""
        # Test color mapping logic
        healthy_config = create_device_material_config("router", "healthy")
        critical_config = create_device_material_config("router", "critical")

        # Critical should have emissive, healthy should not
        assert critical_config.emissive_intensity > 0
        assert healthy_config.emissive_intensity == 0

        # Colors should differ
        assert healthy_config.base_color.to_list() != critical_config.base_color.to_list()

    @pytest.mark.asyncio
    async def test_link_status_color(self, ue5_client):
        """T027: Test link status color changes."""
        healthy_color = get_link_status_color("healthy")
        down_color = get_link_status_color("down")

        # Down should be red-ish, healthy should be green-ish
        assert healthy_color.g > healthy_color.r
        assert down_color.r > down_color.g


# =============================================================================
# Camera Tests (US3)
# =============================================================================

@ue5_required
class TestCameraControls:
    """Tests for camera navigation (T036-T037)."""

    @pytest.mark.asyncio
    async def test_focus_on_device(self, ue5_client):
        """T036: Test focusing camera on a device."""
        async with ue5_client as client:
            # Create a device to focus on
            actor_name = "netclaw_test_camera_focus"
            spawn_result = await client.call_tool(
                toolset="ActorTools",
                tool="spawn_actor",
                args={
                    "class": "/Engine/BasicShapes/Cube.Cube",
                    "name": actor_name,
                    "location": [500, 500, 100],
                    "scale": [50, 50, 50],
                    "tags": ["netclaw", "test"],
                },
            )

            if spawn_result.success:
                # Try to focus on it (may fail if CameraTools not available)
                focus_result = await client.call_tool(
                    toolset="CameraTools",
                    tool="focus_on_actor",
                    args={"actor_name": actor_name},
                )

                # Cleanup regardless of focus result
                await client.call_tool(
                    toolset="ActorTools",
                    tool="destroy_actor",
                    args={"name": actor_name},
                )

                # If CameraTools available, verify focus worked
                if not focus_result.error or "not found" not in str(focus_result.error).lower():
                    assert focus_result.success or "CameraTools" in str(focus_result.error)

    @pytest.mark.asyncio
    async def test_flythrough(self, ue5_client):
        """T037: Test camera fly-through animation."""
        async with ue5_client as client:
            # Get current camera state (if available)
            state_result = await client.call_tool(
                toolset="CameraTools",
                tool="get_camera_state",
                args={},
            )

            if state_result.success:
                # Set a new position
                move_result = await client.call_tool(
                    toolset="CameraTools",
                    tool="set_camera_location",
                    args={
                        "location": [0, 0, 500],
                        "rotation": [-45, 0, 0],
                    },
                )

                # Camera tools may not be available in all UE5 MCP versions
                # Just verify no unexpected errors
                assert move_result.success or "CameraTools" in str(move_result.error)


# =============================================================================
# Incremental Update Tests
# =============================================================================

@ue5_required
class TestIncrementalUpdates:
    """Tests for incremental scene updates (T047-T049)."""

    @pytest.mark.asyncio
    async def test_incremental_add(self, ue5_client):
        """T047: Test adding a device to existing scene."""
        async with ue5_client as client:
            # Create initial device
            result1 = await client.call_tool(
                toolset="ActorTools",
                tool="spawn_actor",
                args={
                    "class": "/Engine/BasicShapes/Cube.Cube",
                    "name": "netclaw_incr_device_1",
                    "location": [0, 0, 100],
                    "scale": [50, 50, 50],
                    "tags": ["netclaw", "test"],
                },
            )
            assert result1.success

            # Add second device
            result2 = await client.call_tool(
                toolset="ActorTools",
                tool="spawn_actor",
                args={
                    "class": "/Engine/BasicShapes/Cube.Cube",
                    "name": "netclaw_incr_device_2",
                    "location": [200, 0, 100],
                    "scale": [50, 50, 50],
                    "tags": ["netclaw", "test"],
                },
            )
            assert result2.success

            # Cleanup
            await client.call_tool(
                toolset="ActorTools",
                tool="destroy_actor",
                args={"name": "netclaw_incr_device_1"},
            )
            await client.call_tool(
                toolset="ActorTools",
                tool="destroy_actor",
                args={"name": "netclaw_incr_device_2"},
            )

    @pytest.mark.asyncio
    async def test_incremental_remove(self, ue5_client):
        """T048: Test removing a device from scene."""
        async with ue5_client as client:
            # Create two devices
            for i in range(2):
                await client.call_tool(
                    toolset="ActorTools",
                    tool="spawn_actor",
                    args={
                        "class": "/Engine/BasicShapes/Cube.Cube",
                        "name": f"netclaw_incr_remove_{i}",
                        "location": [i * 200, 0, 100],
                        "scale": [50, 50, 50],
                        "tags": ["netclaw", "test"],
                    },
                )

            # Remove first device
            remove_result = await client.call_tool(
                toolset="ActorTools",
                tool="destroy_actor",
                args={"name": "netclaw_incr_remove_0"},
            )
            assert remove_result.success

            # Cleanup remaining
            await client.call_tool(
                toolset="ActorTools",
                tool="destroy_actor",
                args={"name": "netclaw_incr_remove_1"},
            )


# =============================================================================
# Digital Twin: Interface Actors, Labels, Legend (045-ue5-digital-twin)
#
# US1 (T010/T011), US2 (T015), US3 (T019). These exercise the client-side
# spec computation and script generation directly (no live UE5 required) —
# the same approach TestMaterials/TestLayout use above — since the actual
# spawn logic lives inside a generated execute_tool_script string that only
# runs inside UE5's embedded interpreter and can't be unit tested directly.
# =============================================================================

from actors import (
    resolve_device_interfaces,
    _compute_batch_specs,
    build_batch_scene_script,
    is_device_in_topology,
    is_interface_in_topology,
    is_link_in_topology,
    resolve_actor_ref,
)
from materials import generate_legend_swatches, DEVICE_TYPE_COLORS
from renderer import NetworkDevice, NetworkLink, TopologyGraph
from scene import reset_scene_state, register_device_actor, register_interface_actor, register_link_actor


class TestDigitalTwinInterfaces:
    """US1: up/up interfaces get their own actor; down interfaces are summarized, never spawned individually."""

    def test_resolve_device_interfaces_explicit_inventory(self):
        """T010: explicit interface inventory is authoritative and splits up/down."""
        device = NetworkDevice(
            hostname="r1",
            device_type="router",
            interfaces=[
                {"name": "Gi0/0", "status": "up"},
                {"name": "Gi0/1", "status": "down"},
                {"name": "Gi0/2", "status": "admin-down"},
            ],
        )
        up, down = resolve_device_interfaces(device, links=[])
        assert up == ["Gi0/0"]
        assert down == ["Gi0/1", "Gi0/2"]

    def test_resolve_device_interfaces_link_inferred_fallback(self):
        """T010: with no explicit inventory, up interfaces come only from this device's link endpoints."""
        device = NetworkDevice(hostname="sw1", device_type="switch")
        links = [
            NetworkLink(source_device="sw1", target_device="pc1", source_interface="Gi1/0/1", target_interface="eth0"),
            NetworkLink(source_device="r1", target_device="sw1", source_interface="Gi0/0", target_interface="Gi1/0/2"),
        ]
        up, down = resolve_device_interfaces(device, links)
        assert up == ["Gi1/0/1", "Gi1/0/2"]
        assert down == []  # no inventory data -> never invent a down list

    def test_compute_batch_specs_spawns_one_actor_per_up_interface_and_one_summary_for_down(self):
        """T011: interface_specs has one entry per up interface; down interfaces collapse to one summary actor."""
        device = NetworkDevice(
            hostname="r1",
            device_type="router",
            interfaces=[
                {"name": "Gi0/0", "status": "up"},
                {"name": "Gi0/1", "status": "down"},
                {"name": "Gi0/2", "status": "down"},
            ],
        )
        topology = TopologyGraph(devices=[device], links=[])
        positions = {"r1": [0, 0, 0]}

        _, interface_specs, _, down_summary_specs, _, _ = _compute_batch_specs(topology, positions)

        assert len(interface_specs) == 1
        assert interface_specs[0]["parent_hostname"] == "r1"
        assert interface_specs[0]["interface_name"] == "Gi0/0"

        assert len(down_summary_specs) == 1  # one summary actor, not one per down interface
        assert "Gi0/1" in down_summary_specs[0]["text"]
        assert "Gi0/2" in down_summary_specs[0]["text"]

    def test_links_attach_to_interface_actors_when_available(self):
        """FR-003: a link between two up/up interfaces attaches to those interface actors, not the device centers."""
        r1 = NetworkDevice(hostname="r1", device_type="router")
        sw1 = NetworkDevice(hostname="sw1", device_type="switch")
        link = NetworkLink(source_device="r1", target_device="sw1", source_interface="Gi0/0", target_interface="Gi1/0/1")
        topology = TopologyGraph(devices=[r1, sw1], links=[link])
        positions = {"r1": [0, 0, 300], "sw1": [0, 0, 0]}

        _, _, link_specs, _, _, _ = _compute_batch_specs(topology, positions)

        assert len(link_specs) == 1
        assert link_specs[0]["attached_to_interfaces"] is True


class TestDigitalTwinLabelsAndLegend:
    """US2/US3: every spawned actor type gets a readable label; the legend always matches live colors."""

    def test_generate_legend_swatches_covers_every_device_type(self):
        """T019: legend has exactly one entry per DeviceType, using the live color mapping."""
        swatches = generate_legend_swatches()
        assert len(swatches) == len(DEVICE_TYPE_COLORS)
        by_type = {s["device_type"]: s["color"] for s in swatches}
        for device_type, color in DEVICE_TYPE_COLORS.items():
            assert by_type[device_type.value] == color.to_list()

    def test_endpoint_color_is_orange_not_gray(self):
        """T016: endpoints render orange (previously gray, indistinguishable from 'unknown')."""
        from materials import DeviceType
        endpoint_color = DEVICE_TYPE_COLORS[DeviceType.ENDPOINT].to_list()
        r, g, b = endpoint_color
        assert r > g > b  # orange: red-dominant, green secondary, blue lowest
        assert (r, g, b) != (0.5, 0.5, 0.5)

    def test_compute_batch_specs_generates_one_legend_actor(self):
        """T019: a non-empty topology always gets exactly one legend actor spec."""
        device = NetworkDevice(hostname="r1", device_type="router")
        topology = TopologyGraph(devices=[device], links=[])
        _, _, _, _, legend_spec, _ = _compute_batch_specs(topology, {"r1": [0, 0, 0]})
        assert legend_spec is not None
        assert legend_spec["name"] == "NC_Legend"
        assert "LEGEND" in legend_spec["text"]

    def test_build_batch_scene_script_is_valid_python(self):
        """T015: the generated execute_tool_script payload (devices, interfaces, links, down summaries, legend, labels) parses as valid Python."""
        import ast

        device = NetworkDevice(hostname="r1", device_type="router", interfaces=[{"name": "Gi0/0", "status": "up"}, {"name": "Gi0/1", "status": "down"}])
        sw1 = NetworkDevice(hostname="sw1", device_type="switch")
        link = NetworkLink(source_device="r1", target_device="sw1", source_interface="Gi0/0", target_interface="Gi1/0/1")
        topology = TopologyGraph(devices=[device, sw1], links=[link])
        positions = {"r1": [0, 0, 300], "sw1": [0, 0, 0]}

        specs = _compute_batch_specs(topology, positions)
        script = build_batch_scene_script(*specs, True)

        ast.parse(script)  # raises SyntaxError if malformed
        assert "_spawn_text" in script
        assert "down_summaries" in script


class TestDigitalTwinTopologyResolution:
    """Foundational (T004): every new capability must refuse to act on names that aren't actually in the built scene (FR-040)."""

    def setup_method(self):
        reset_scene_state()

    def test_resolve_actor_ref_finds_registered_device(self):
        register_device_actor("r1", "NC_r1", [0, 0, 0])
        assert is_device_in_topology("r1") is True
        assert resolve_actor_ref("r1") is not None

    def test_resolve_actor_ref_finds_registered_interface(self):
        register_interface_actor("r1", "Gi0/0", "NC_If_r1_Gi0_0")
        assert is_interface_in_topology("r1", "Gi0/0") is True
        assert resolve_actor_ref("Gi0/0") is None  # only resolvable by its actual key, not bare interface name

    def test_resolve_actor_ref_finds_registered_link(self):
        register_link_actor("r1_sw1", "NC_Link_r1_sw1")
        assert is_link_in_topology("r1_sw1") is True
        assert resolve_actor_ref("r1_sw1") is not None

    def test_unknown_name_reports_not_found(self):
        """FR-040: an unbuilt device/interface/link must resolve to None, never be silently ignored."""
        assert is_device_in_topology("does-not-exist") is False
        assert resolve_actor_ref("does-not-exist") is None


# =============================================================================
# Digital Twin: Traffic, Live Health, Sticky Trap Alerts (045-ue5-digital-twin)
#
# US4 (T023), US5 (T028), US6 (T035). These drive the async functions with
# asyncio.run() from plain sync test functions instead of @pytest.mark.asyncio,
# since this environment doesn't have pytest-asyncio installed (the existing
# @pytest.mark.asyncio tests above are already silently skipped for the same
# reason). A minimal AsyncMock-based fake client stands in for a live UE5
# instance so the sticky-alert/traffic/history business logic — the part
# that's actually ours to get right — is verified without requiring UE5.
# =============================================================================

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

from ue5_mcp_client import ToolResult
from telemetry import (
    TelemetryReceiver,
    TelemetryPoller,
    PollingConfig,
    refresh_traffic_visualization,
    refresh_health_visualization,
    start_live_mode,
    stop_live_mode,
    get_live_mode_status,
    latch_sticky_alert,
    clear_sticky_alert,
    is_sticky_alert_active,
    clear_all_sticky_alerts,
    get_history_window,
    clear_history,
    record_history,
)
from materials import get_traffic_color, get_alarm_color, DeviceType


def _fake_client():
    client = AsyncMock()
    client.call_tool = AsyncMock(return_value=ToolResult(success=True, data={"applied": True, "rendered": True}))
    return client


class TestDigitalTwinTrafficVisualization:
    """US4: traffic utilization is a supplied value; unknown keys never error."""

    def test_get_traffic_color_gradient_green_to_red(self):
        assert get_traffic_color(0.0).to_list() == [0.0, 1.0, 0.0]
        red = get_traffic_color(1.0).to_list()
        assert red[0] == 1.0 and red[1] == 0.0

    def test_refresh_traffic_visualization_skips_unregistered_interfaces(self):
        reset_scene_state()
        client = _fake_client()
        result = asyncio.run(refresh_traffic_visualization(client, {"ghost:Gi0/0": 0.9}))
        assert result["applied"] == []
        assert result["skipped"] == ["ghost:Gi0/0"]
        client.call_tool.assert_not_called()

    def test_refresh_traffic_visualization_applies_and_records_history(self):
        reset_scene_state()
        clear_history()
        register_interface_actor("r1", "Gi0/0", "NC_If_r1_Gi0_0")
        client = _fake_client()

        result = asyncio.run(refresh_traffic_visualization(client, {"r1:Gi0/0": 0.8}))
        assert result["applied"] == ["r1:Gi0/0"]
        client.call_tool.assert_awaited()

        records = get_history_window(datetime.min, datetime.max)
        assert any(r.subject_key == "r1:Gi0/0" and r.change_type == "traffic" for r in records)


class TestDigitalTwinLiveHealth:
    """US5: on-demand refresh, live-mode start/stop/status, per-item polling isolation."""

    def test_refresh_health_visualization_ignores_unknown_device(self):
        reset_scene_state()
        client = _fake_client()
        result = asyncio.run(refresh_health_visualization(client, device_status_by_hostname={"ghost": "critical"}))
        assert result["skipped"] == ["ghost"]
        assert result["applied"] == []

    def test_refresh_health_visualization_clears_sticky_alert_on_healthy_link(self):
        reset_scene_state()
        clear_all_sticky_alerts()
        register_link_actor("r1_sw1", "NC_Link_r1_sw1")
        latch_sticky_alert("r1_sw1", "linkDown")
        assert is_sticky_alert_active("r1_sw1") is True

        client = _fake_client()
        asyncio.run(refresh_health_visualization(client, link_status_by_id={"r1_sw1": "healthy"}))
        assert is_sticky_alert_active("r1_sw1") is False

    def test_live_mode_start_stop_status_roundtrip(self):
        client = _fake_client()
        poller = TelemetryPoller(client)

        status = get_live_mode_status(poller)
        assert status.active is False
        assert status.started_at is None

        asyncio.run(start_live_mode(client, poller))
        status = get_live_mode_status(poller)
        assert status.active is True
        assert status.started_at is not None

        asyncio.run(stop_live_mode(poller))
        status = get_live_mode_status(poller)
        assert status.active is False
        assert status.started_at is None

    def test_poll_once_clears_sticky_alert_on_confirmed_healthy_recovery(self):
        """T032: continuous polling, not just the on-demand refresh, must clear a stale sticky alert."""
        reset_scene_state()
        clear_all_sticky_alerts()
        clear_history()
        register_link_actor("r1_sw1", "NC_Link_r1_sw1")
        latch_sticky_alert("r1_sw1", "linkDown")

        async def healthy_link_callback(link_id):
            return "healthy"

        client = _fake_client()
        config = PollingConfig(link_status_callback=healthy_link_callback)
        poller = TelemetryPoller(client, config)

        asyncio.run(poller._poll_once())
        assert is_sticky_alert_active("r1_sw1") is False
        records = get_history_window(datetime.min, datetime.max)
        assert any(r.subject_key == "r1_sw1" and r.change_type == "health" for r in records)

    def test_poll_once_isolates_a_single_device_failure(self):
        """FR-016: one device's polling callback raising must not block polling the rest."""
        reset_scene_state()
        register_device_actor("bad-device", "NC_bad_device", [0, 0, 0])
        register_device_actor("good-device", "NC_good_device", [100, 0, 0])

        async def flaky_status_callback(hostname):
            if hostname == "bad-device":
                raise RuntimeError("simulated device unreachable")
            return "healthy"

        client = _fake_client()
        config = PollingConfig(device_status_callback=flaky_status_callback)
        poller = TelemetryPoller(client, config)

        asyncio.run(poller._poll_once())  # must not raise despite bad-device failing
        assert poller._device_status_cache.get("good-device") == "healthy"
        assert "bad-device" not in poller._device_status_cache


class TestDigitalTwinStickyAlerts:
    """US6: down-type traps latch a sticky alert; only a matching up trap or health-poll recovery clears it."""

    def setup_method(self):
        reset_scene_state()
        clear_all_sticky_alerts()
        clear_history()

    def test_trap_for_unknown_device_is_ignored_without_error(self):
        client = _fake_client()
        receiver = TelemetryReceiver(client)
        result = asyncio.run(receiver.process_snmp_trap({
            "hostname": "ghost-device", "interface": "Gi0/0", "trap_oid": "1.3.6.1.6.3.1.1.5.3",
        }))
        assert result["applied"] is False
        assert is_sticky_alert_active("ghost-device:Gi0/0") is False

    def test_link_down_trap_latches_sticky_alert_and_survives_unrelated_refresh(self):
        register_interface_actor("r1", "Gi0/0", "NC_If_r1_Gi0_0")
        client = _fake_client()
        receiver = TelemetryReceiver(client)

        result = asyncio.run(receiver.process_snmp_trap({
            "hostname": "r1", "interface": "Gi0/0", "trap_oid": "1.3.6.1.6.3.1.1.5.3",
        }))
        assert result["applied"] is True
        assert is_sticky_alert_active("r1:Gi0/0") is True

        # An unrelated refresh (a different interface entirely) must not clear it.
        asyncio.run(refresh_traffic_visualization(client, {"r1:Gi0/0": 0.1}))
        assert is_sticky_alert_active("r1:Gi0/0") is True

    def test_matching_link_up_trap_clears_sticky_alert(self):
        register_interface_actor("r1", "Gi0/0", "NC_If_r1_Gi0_0")
        client = _fake_client()
        receiver = TelemetryReceiver(client)

        asyncio.run(receiver.process_snmp_trap({
            "hostname": "r1", "interface": "Gi0/0", "trap_oid": "1.3.6.1.6.3.1.1.5.3",
        }))
        assert is_sticky_alert_active("r1:Gi0/0") is True

        result = asyncio.run(receiver.process_snmp_trap({
            "hostname": "r1", "interface": "Gi0/0", "trap_oid": "1.3.6.1.6.3.1.1.5.4",
        }))
        assert result["applied"] is True
        assert is_sticky_alert_active("r1:Gi0/0") is False

    def test_alarm_color_distinct_from_critical_status_color(self):
        from materials import DEVICE_STATUS_COLORS, DeviceStatus
        assert get_alarm_color().to_list() != DEVICE_STATUS_COLORS[DeviceStatus.CRITICAL].to_list()


# =============================================================================
# Digital Twin: Ping/Traceroute Animation, Config Panels (045-ue5-digital-twin)
#
# US7 (T039), US8 (T042).
# =============================================================================

import diagnostics
import panels


class TestDigitalTwinDiagnostics:
    """US7: real ping/traceroute results animate along the path; unknown devices are reported, not attempted."""

    def setup_method(self):
        reset_scene_state()

    def test_ping_between_unknown_device_is_reported_not_attempted(self):
        register_device_actor("r1", "NC_r1", [0, 0, 0])
        client = _fake_client()
        result = asyncio.run(diagnostics.animate_ping(client, "r1", "ghost", True))
        assert result["animated"] is False
        assert "ghost" in result["reason"]
        client.call_tool.assert_not_called()

    def test_ping_success_and_failure_are_visually_distinguishable(self):
        register_device_actor("r1", "NC_r1", [0, 0, 0])
        register_device_actor("r2", "NC_r2", [200, 0, 0])
        client = _fake_client()

        success_result = asyncio.run(diagnostics.animate_ping(client, "r1", "r2", True, latency_ms=5.0))
        assert success_result["animated"] is True
        assert success_result["success"] is True

        failure_result = asyncio.run(diagnostics.animate_ping(client, "r1", "r2", False))
        assert failure_result["success"] is False

    def test_traceroute_skips_unknown_hop_but_continues_animating_the_rest(self):
        register_device_actor("r1", "NC_r1", [0, 0, 0])
        register_device_actor("r2", "NC_r2", [200, 0, 0])
        client = _fake_client()

        result = asyncio.run(diagnostics.animate_traceroute(client, [
            {"hostname": "r1", "reached": True},
            {"hostname": "ghost-hop", "reached": True},
            {"hostname": "r2", "reached": False},
        ]))
        assert result["animated"] == ["r1", "r2"]
        assert result["skipped"] == ["ghost-hop"]


class TestDigitalTwinConfigPanels:
    """US8: a device's config appears as a panel; a repeat request replaces rather than duplicates it."""

    def setup_method(self):
        reset_scene_state()

    def test_show_config_panel_for_unknown_device_is_reported(self):
        client = _fake_client()
        result = asyncio.run(panels.show_config_panel(client, "ghost", "hostname ghost"))
        assert result["rendered"] is False
        assert "ghost" in result["reason"]

    def test_show_config_panel_renders_for_known_device(self):
        register_device_actor("r1", "NC_r1", [0, 0, 0])
        client = _fake_client()
        result = asyncio.run(panels.show_config_panel(client, "r1", "hostname r1\ninterface Gi0/0"))
        assert result["rendered"] is True
        assert result["panel_kind"] == "config"
        client.call_tool.assert_awaited()

    def test_repeated_panel_request_uses_the_same_actor_name(self):
        """FR-025/FR-037: same (hostname, panel_kind) always maps to one actor name, so the generated script destroys-then-recreates instead of stacking a duplicate."""
        register_device_actor("r1", "NC_r1", [0, 0, 0])
        first_name = panels.generate_panel_actor_name("r1", "config")
        second_name = panels.generate_panel_actor_name("r1", "config")
        assert first_name == second_name


# =============================================================================
# Digital Twin: Incident Correlation, Historical Playback (045-ue5-digital-twin)
#
# US9 (T046), US10 (T051).
# =============================================================================

from datetime import timedelta

import incidents
import playback


class TestDigitalTwinIncidentCorrelation:
    """US9: a matching open incident applies the alarm state; no match is explicitly reported."""

    def setup_method(self):
        reset_scene_state()

    def test_matching_incident_applies_alarm_state(self):
        register_device_actor("r1", "NC_r1", [0, 0, 0])
        client = _fake_client()
        open_incidents = [{"incident_id": "PD123", "title": "r1 interface flapping", "description": "", "service_name": ""}]

        result = asyncio.run(incidents.correlate_incident(client, "r1", open_incidents))
        assert result["correlated"] is True
        assert result["incident_id"] == "PD123"
        assert result["alarm_state_applied"] is True

    def test_no_matching_incident_is_explicitly_reported(self):
        register_device_actor("r1", "NC_r1", [0, 0, 0])
        client = _fake_client()
        open_incidents = [{"incident_id": "PD999", "title": "unrelated-device down", "description": "", "service_name": ""}]

        result = asyncio.run(incidents.correlate_incident(client, "r1", open_incidents))
        assert result["correlated"] is False
        assert "r1" in result["reason"]

    def test_unknown_subject_is_reported_not_attempted(self):
        client = _fake_client()
        result = asyncio.run(incidents.correlate_incident(client, "ghost", [{"title": "ghost is down"}]))
        assert result["correlated"] is False
        client.call_tool.assert_not_called()

    def test_link_correlates_via_either_endpoint_hostname(self):
        register_link_actor("r1_sw1", "NC_Link_r1_sw1")
        client = _fake_client()
        open_incidents = [{"incident_id": "PD456", "title": "sw1 unreachable", "description": "", "service_name": ""}]

        result = asyncio.run(incidents.correlate_incident(client, "r1_sw1", open_incidents))
        assert result["correlated"] is True


class TestDigitalTwinPlayback:
    """US10: a recorded window replays in order at compressed speed; an empty window is reported, not a silent no-op."""

    def setup_method(self):
        reset_scene_state()
        clear_history()

    def test_empty_window_is_explicitly_reported(self):
        client = _fake_client()
        now = datetime.now()
        result = asyncio.run(playback.replay_window(client, now - timedelta(days=2), now - timedelta(days=1)))
        assert result["replayed"] == 0
        assert "reason" in result

    def test_window_with_changes_replays_all_in_order(self):
        register_device_actor("r1", "NC_r1", [0, 0, 0])
        register_interface_actor("sw1", "Gi0/1", "NC_If_sw1_Gi0_1")
        record_history("r1", "health", "healthy", "critical")
        record_history("sw1:Gi0/1", "traffic", None, 0.9)

        client = _fake_client()
        now = datetime.now()
        result = asyncio.run(playback.replay_window(client, now - timedelta(minutes=5), now + timedelta(minutes=5)))
        assert result["replayed"] == 2
        assert client.call_tool.await_count >= 2

    def test_adjusted_speed_is_reported_back(self):
        register_device_actor("r1", "NC_r1", [0, 0, 0])
        record_history("r1", "health", "healthy", "warning")
        client = _fake_client()
        now = datetime.now()
        result = asyncio.run(playback.replay_window(client, now - timedelta(minutes=1), now + timedelta(minutes=1), speed=4.0))
        assert result["speed"] == 4.0


# =============================================================================
# Digital Twin: Hierarchical Zoom, Metrics HUD, Fixed Camera Controls
# (045-ue5-digital-twin)
#
# US11 (T056), US12 (T059), plus coverage for the camera.py calling-
# convention fix that US11's zoom_to()/zoom_out_to_site() depend on.
# =============================================================================

import camera
import hierarchy


class TestDigitalTwinCameraControls:
    """
    camera.py's get_camera_state/set_camera_location/focus_on_actor
    previously called client.call_tool(toolset=..., tool=..., args=...) —
    not this codebase's real call_tool(toolset_name, tool_name, arguments)
    signature — so every one of them raised TypeError the instant they were
    actually invoked. Fixed by routing through execute_tool_script instead
    of an unconfirmed generic CameraTools toolset.
    """

    def test_set_camera_location_uses_execute_tool_script_convention(self):
        client = _fake_client()
        ok = asyncio.run(camera.set_camera_location(client, [100, 200, 300], [-30, 45, 0]))
        assert ok is True
        _, kwargs = client.call_tool.call_args
        assert kwargs["toolset_name"].endswith("ProgrammaticToolset")
        assert "execute_tool_script" in kwargs["tool_name"]

    def test_get_camera_state_does_not_raise(self):
        client = AsyncMock()
        client.call_tool = AsyncMock(return_value=ToolResult(
            success=True, data={"location": [1.0, 2.0, 3.0], "rotation": [-30.0, 45.0, 0.0]}
        ))
        state = asyncio.run(camera.get_camera_state(client))
        assert state.location == [1.0, 2.0, 3.0]

    def test_focus_on_actor_does_not_raise(self):
        client = _fake_client()
        ok = asyncio.run(camera.focus_on_actor(client, "NC_r1"))
        assert ok is True


class TestDigitalTwinHierarchicalZoom:
    """US11: NetBox/Infrahub-sourced groups first, manual fallback; zoom never loses/duplicates actors."""

    def setup_method(self):
        reset_scene_state()
        hierarchy.clear_zoom_groups()

    def test_resolve_zoom_groups_prefers_netbox_infrahub_data(self):
        register_device_actor("r1", "NC_r1", [0, 0, 0])
        register_device_actor("sw1", "NC_sw1", [100, 0, 0])
        placement = {
            "r1": {"group_name": "rack-1", "zoom_level": "rack", "source": "netbox"},
            "sw1": {"group_name": "rack-1", "zoom_level": "rack", "source": "netbox"},
        }
        groups = asyncio.run(hierarchy.resolve_zoom_groups(["r1", "sw1"], placement))
        assert len(groups) == 1
        assert groups[0].source == "netbox"
        assert set(groups[0].member_hostnames) == {"r1", "sw1"}

    def test_unplaced_device_is_ungrouped_until_manual_assignment(self):
        register_device_actor("pc1", "NC_pc1", [0, 0, 0])
        asyncio.run(hierarchy.resolve_zoom_groups(["pc1"], {}))
        assert hierarchy.get_ungrouped_hostnames(["pc1"]) == ["pc1"]

        hierarchy.assign_manual_group("misc-rack", ["pc1"])
        assert hierarchy.get_ungrouped_hostnames(["pc1"]) == []

    def test_zoom_to_unknown_group_is_reported(self):
        client = _fake_client()
        result = asyncio.run(hierarchy.zoom_to(client, "does-not-exist"))
        assert result["zoomed"] is False
        client.call_tool.assert_not_called()

    def test_zoom_to_and_zoom_out_only_toggle_visibility_never_rebuild(self):
        """FR-034/FR-035: zoom must never call a spawn/destroy tool, only visibility toggles."""
        register_device_actor("r1", "NC_r1", [0, 0, 0])
        register_device_actor("sw1", "NC_sw1", [100, 0, 0])
        hierarchy.assign_manual_group("rack-1", ["r1", "sw1"])

        client = _fake_client()
        zoom_result = asyncio.run(hierarchy.zoom_to(client, "rack-1"))
        assert zoom_result["zoomed"] is True
        assert zoom_result["member_count"] == 2

        zoom_out_result = asyncio.run(hierarchy.zoom_out_to_site(client))
        assert zoom_out_result["zoomed_out"] is True

        for call in client.call_tool.call_args_list:
            script = call.kwargs.get("arguments", {}).get("script", "")
            assert "spawn_actor_from_class" not in script
            assert "destroy_actor" not in script


class TestDigitalTwinMetricsHUD:
    """US12: live CPU/memory/uptime as a floating panel; a repeat request always shows fresh values."""

    def setup_method(self):
        reset_scene_state()

    def test_metrics_hud_for_unknown_device_is_reported(self):
        client = _fake_client()
        result = asyncio.run(panels.show_metrics_hud(client, "ghost", 50.0, 60.0, "3d 2h"))
        assert result["rendered"] is False

    def test_metrics_hud_renders_with_current_values(self):
        register_device_actor("r1", "NC_r1", [0, 0, 0])
        client = _fake_client()
        result = asyncio.run(panels.show_metrics_hud(client, "r1", 42.5, 71.0, "10d 4h"))
        assert result["rendered"] is True
        assert result["panel_kind"] == "metrics"

    def test_repeated_metrics_request_reflects_freshly_supplied_values(self):
        """FR-037: no caching — each call renders exactly what was just passed in."""
        register_device_actor("r1", "NC_r1", [0, 0, 0])
        client = _fake_client()

        asyncio.run(panels.show_metrics_hud(client, "r1", 10.0, 20.0, "1h"))
        first_script = client.call_tool.call_args.kwargs["arguments"]["script"]
        assert "10.0" in first_script

        asyncio.run(panels.show_metrics_hud(client, "r1", 90.0, 95.0, "1h 5m"))
        second_script = client.call_tool.call_args.kwargs["arguments"]["script"]
        assert "90.0" in second_script
        assert "10.0" not in second_script


# =============================================================================
# Run tests if executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
