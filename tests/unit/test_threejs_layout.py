"""
Unit tests for the threejs-network-viz skill's force-directed layout —
specifically centering/scale correctness across varied coordinate ranges
(spec.md FR-008; the exact class of bug fixed once already in
ue5-network-viz, see research.md §4).
"""

import sys
from pathlib import Path

skill_path = Path(__file__).parent.parent.parent / "workspace" / "skills" / "threejs-network-viz"
sys.path.insert(0, str(skill_path))

from layout import LayoutConfig, calculate_topology_layout  # noqa: E402
from topology_model import Device, DeviceRole, Link, LinkEndpoint  # noqa: E402


def _linear_topology(n: int) -> tuple[list[Device], list[Link]]:
    devices = [Device(hostname=f"d{i}", role=DeviceRole.ROUTER) for i in range(n)]
    links = [
        Link(link_id=f"l{i}", endpoint_a=LinkEndpoint(f"d{i}"), endpoint_b=LinkEndpoint(f"d{i+1}"))
        for i in range(n - 1)
    ]
    return devices, links


def test_single_device_centers_on_bounds_midpoint():
    devices = [Device(hostname="only", role=DeviceRole.ROUTER)]
    calculate_topology_layout(devices, [])
    config = LayoutConfig()
    expected_x = (config.bounds_min.x + config.bounds_max.x) / 2
    expected_y = (config.bounds_min.y + config.bounds_max.y) / 2
    assert devices[0].position.x == expected_x
    assert devices[0].position.y == expected_y


def test_topology_centroid_sits_near_bounds_center():
    devices, links = _linear_topology(8)
    calculate_topology_layout(devices, links)

    config = LayoutConfig()
    target_x = (config.bounds_min.x + config.bounds_max.x) / 2
    target_y = (config.bounds_min.y + config.bounds_max.y) / 2

    centroid_x = sum(d.position.x for d in devices) / len(devices)
    centroid_y = sum(d.position.y for d in devices) / len(devices)

    # The centroid-recentering fix (research.md §4) guarantees the whole
    # topology's centroid lands at the bounds' center, not just that every
    # individual node stays in-bounds.
    assert abs(centroid_x - target_x) < 1.0
    assert abs(centroid_y - target_y) < 1.0


def test_all_devices_stay_within_configured_bounds():
    devices, links = _linear_topology(12)
    config = LayoutConfig()
    calculate_topology_layout(devices, links, config)

    for d in devices:
        assert config.bounds_min.x - 1e-6 <= d.position.x <= config.bounds_max.x + 1e-6
        assert config.bounds_min.y - 1e-6 <= d.position.y <= config.bounds_max.y + 1e-6
        assert config.bounds_min.z - 1e-6 <= d.position.z <= config.bounds_max.z + 1e-6


def test_scale_is_consistent_across_topology_sizes():
    """A larger topology should not produce degenerate (all-overlapping or
    wildly-oversized) positions relative to a smaller one — regression guard
    against the exact class of scale bug fixed in ue5-network-viz (commit
    5281cac, research.md §4)."""
    small_devices, small_links = _linear_topology(3)
    large_devices, large_links = _linear_topology(15)

    calculate_topology_layout(small_devices, small_links)
    calculate_topology_layout(large_devices, large_links)

    def spread(devices):
        xs = [d.position.x for d in devices]
        return max(xs) - min(xs)

    # Both must actually spread out (not collapse to ~0 = overlap), and
    # neither may blow past the configured bounds width.
    config = LayoutConfig()
    bounds_width = config.bounds_max.x - config.bounds_min.x
    assert spread(small_devices) > 0.01
    assert spread(large_devices) > 0.01
    assert spread(small_devices) <= bounds_width + 1e-6
    assert spread(large_devices) <= bounds_width + 1e-6


def test_empty_topology_returns_no_positions():
    assert calculate_topology_layout([], []) == {}
