"""
Builds the embedded topology JSON payload consumed by html_template.py's
runtime JS engine. This is the one payload contract that crosses from Python
into the browser — see contracts/topology-scene-contract.md.

Every device entry carries a COMPLETE transform (position + fixed rotation/
scale) — never partial (FR-009) — and every interface carries a local offset
relative to its parent device's origin, so the runtime JS can add it as a
true child object (FR-003) rather than compute a world-space position itself.
"""

import math

from layout import calculate_topology_layout
from materials import (
    generate_role_legend_entries,
    generate_state_legend_entries,
    get_device_role_color,
    get_device_role_shape,
    get_state_color,
)
from topology_model import AssetKind, Device, TopologySnapshot

INTERFACE_OFFSET_RADIUS = 0.7


def _interface_offsets(device: Device) -> None:
    """Assign each interface a deterministic local_offset around its parent's
    origin (evenly spaced on a circle), mutating the Interface objects in place."""
    count = len(device.interfaces)
    if count == 0:
        return
    for i, iface in enumerate(device.interfaces):
        angle = (2 * math.pi * i) / count
        iface.local_offset.x = INTERFACE_OFFSET_RADIUS * math.cos(angle)
        iface.local_offset.y = INTERFACE_OFFSET_RADIUS * math.sin(angle)
        iface.local_offset.z = 0.0


def _device_asset_payload(device: Device) -> dict:
    asset = device.device_asset
    payload = {"kind": asset.kind.value}
    if asset.kind == AssetKind.PROCEDURAL:
        payload["procedural_shape"] = (
            asset.procedural_shape.value
            if asset.procedural_shape
            else get_device_role_shape(device.role)
        )
    else:
        payload["embedded_glb_base64"] = asset.embedded_glb_base64
        payload["model_source"] = asset.model_source.value if asset.model_source else None
    return payload


def _device_payload(device: Device) -> dict:
    role_color = get_device_role_color(device.role)
    state_color = get_state_color(device.state)
    return {
        "hostname": device.hostname,
        "role": device.role.value,
        "color": state_color or role_color,
        "base_role_color": role_color,
        "state": device.state.value if device.state else None,
        "metadata": device.metadata,
        "device_asset": _device_asset_payload(device),
        # Full transform, always all three axes together (FR-009).
        "position": device.position.to_list(),
        "rotation": [0.0, 0.0, 0.0],
        "scale": [1.0, 1.0, 1.0],
        "interfaces": [
            {
                "name": iface.name,
                "ip_address": iface.ip_address,
                "state": iface.state.value if iface.state else None,
                "color": get_state_color(iface.state),
                "metadata": iface.metadata,
                # Relative to the parent device's local origin — the runtime
                # JS adds this as a true child object (FR-003), never a
                # precomputed world-space position.
                "local_offset": iface.local_offset.to_list(),
            }
            for iface in device.interfaces
        ],
    }


def _link_payload(link) -> dict:
    return {
        "link_id": link.link_id,
        "label": link.label,
        "state": link.state.value if link.state else None,
        "color": get_state_color(link.state) or "#999999",
        "endpoint_a": {
            "hostname": link.endpoint_a.hostname,
            "interface_name": link.endpoint_a.interface_name,
        },
        "endpoint_b": {
            "hostname": link.endpoint_b.hostname,
            "interface_name": link.endpoint_b.interface_name,
        },
    }


def build_scene_payload(snapshot: TopologySnapshot) -> dict:
    """Lay out the topology and produce the full JSON payload for html_template.py."""
    calculate_topology_layout(snapshot.devices, snapshot.links)
    for device in snapshot.devices:
        _interface_offsets(device)

    return {
        "snapshot_id": snapshot.snapshot_id,
        "source_kind": snapshot.source_kind.value,
        "source_label": snapshot.source_label,
        "created_at": snapshot.created_at.isoformat(),
        "devices": [_device_payload(d) for d in snapshot.devices],
        "links": [_link_payload(l) for l in snapshot.links],
        "legend": {
            "roles": generate_role_legend_entries(),
            "states": generate_state_legend_entries(),
        },
        "fallback_report": [
            {"hostname": f.hostname, "role": f.role, "reason": f.reason.value}
            for f in snapshot.fallback_report
        ],
    }
