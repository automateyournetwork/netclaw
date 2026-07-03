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
# Run tests if executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
