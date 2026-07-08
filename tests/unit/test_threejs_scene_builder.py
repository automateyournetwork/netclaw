"""
Unit tests for scene_builder.py's embedded topology JSON payload — full
per-object transforms, interface-as-child nesting, and link endpoint
references (spec.md FR-003, FR-005, FR-006, FR-009).
"""

import sys
from pathlib import Path

skill_path = Path(__file__).parent.parent.parent / "workspace" / "skills" / "threejs-network-viz"
sys.path.insert(0, str(skill_path))

from scene_builder import build_scene_payload  # noqa: E402
from sources import from_cml  # noqa: E402


def _sample_snapshot():
    raw = {
        "source": "unit-test-lab",
        "devices": [
            {
                "hostname": "r1",
                "device_type": "router",
                "interfaces": [{"name": "Gi0/0", "ip_address": "10.0.0.1", "status": "healthy"}],
            },
            {
                "hostname": "sw1",
                "device_type": "switch",
                "interfaces": [{"name": "Gi0/1"}],
            },
        ],
        "links": [
            {
                "source_device": "r1",
                "target_device": "sw1",
                "source_interface": "Gi0/0",
                "target_interface": "Gi0/1",
                "status": "healthy",
            }
        ],
    }
    return from_cml(raw)


def test_every_device_has_a_complete_transform():
    payload = build_scene_payload(_sample_snapshot())
    for device in payload["devices"]:
        assert len(device["position"]) == 3
        assert len(device["rotation"]) == 3
        assert len(device["scale"]) == 3
        assert all(isinstance(v, float) for v in device["position"])


def test_interfaces_are_nested_under_their_parent_device_not_top_level():
    payload = build_scene_payload(_sample_snapshot())
    device_by_host = {d["hostname"]: d for d in payload["devices"]}

    assert len(device_by_host["r1"]["interfaces"]) == 1
    assert device_by_host["r1"]["interfaces"][0]["name"] == "Gi0/0"
    # Local offset, not a world-space coordinate — the runtime JS adds this
    # object as a child, so it must NOT carry the parent's world position.
    offset = device_by_host["r1"]["interfaces"][0]["local_offset"]
    assert len(offset) == 3
    assert offset != device_by_host["r1"]["position"]


def test_link_references_both_endpoints_by_hostname_and_interface():
    payload = build_scene_payload(_sample_snapshot())
    assert len(payload["links"]) == 1
    link = payload["links"][0]
    assert link["endpoint_a"]["hostname"] == "r1"
    assert link["endpoint_a"]["interface_name"] == "Gi0/0"
    assert link["endpoint_b"]["hostname"] == "sw1"
    assert link["endpoint_b"]["interface_name"] == "Gi0/1"


def test_legend_is_generated_from_the_live_color_table_not_hardcoded():
    payload = build_scene_payload(_sample_snapshot())
    role_labels = {entry["role"] for entry in payload["legend"]["roles"]}
    assert "router" in role_labels
    assert "switch" in role_labels
    assert "firewall" in role_labels
    assert "load_balancer" in role_labels
    assert "client" in role_labels
    assert "unclassified" in role_labels


def test_state_color_overrides_role_color_when_state_is_known():
    raw = {
        "devices": [{"hostname": "fw1", "device_type": "firewall", "status": "down"}],
        "links": [],
    }
    payload = build_scene_payload(from_cml(raw))
    device = payload["devices"][0]
    assert device["color"] != device["base_role_color"]
    assert device["state"] == "down"


def test_device_with_no_state_renders_base_role_color_not_a_state_color():
    raw = {"devices": [{"hostname": "fw1", "device_type": "firewall"}], "links": []}
    payload = build_scene_payload(from_cml(raw))
    device = payload["devices"][0]
    assert device["color"] == device["base_role_color"]
    assert device["state"] is None


def test_device_with_no_interfaces_still_renders_with_empty_interface_list():
    raw = {"devices": [{"hostname": "fw1", "device_type": "firewall"}], "links": []}
    payload = build_scene_payload(from_cml(raw))
    assert payload["devices"][0]["interfaces"] == []


def test_link_falls_back_to_device_level_when_no_interface_data():
    raw = {
        "devices": [{"hostname": "a"}, {"hostname": "b"}],
        "links": [{"source_device": "a", "target_device": "b", "status": "down"}],
    }
    payload = build_scene_payload(from_cml(raw))
    link = payload["links"][0]
    assert link["endpoint_a"]["interface_name"] is None
    assert link["endpoint_b"]["interface_name"] is None
