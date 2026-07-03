"""
Historical Playback for UE5 Network Digital Twin (045-ue5-digital-twin, US10).

Replays telemetry.py's session history buffer (populated by US4 traffic, US5
health polling, and US6 trap alerts) against the live scene, in original
order, at a compressed default speed (FR-029/FR-030). Reports explicitly
when a requested window has no recorded changes (FR-031) rather than a
silent no-op.
"""

import asyncio
from datetime import datetime

try:
    from .ue5_mcp_client import UE5MCPClient
    from .actors import (
        apply_actor_color,
        apply_device_material,
        apply_link_material,
        apply_interface_material,
        generate_link_actor_name,
        is_device_in_topology,
        is_link_in_topology,
    )
    from .materials import get_traffic_color, get_alarm_color, get_link_status_color
    from .telemetry import get_history_window, HistoryRecord
except ImportError:  # pragma: no cover - fallback for sys.path-style loading
    from ue5_mcp_client import UE5MCPClient
    from actors import (
        apply_actor_color,
        apply_device_material,
        apply_link_material,
        apply_interface_material,
        generate_link_actor_name,
        is_device_in_topology,
        is_link_in_topology,
    )
    from materials import get_traffic_color, get_alarm_color, get_link_status_color
    from telemetry import get_history_window, HistoryRecord

# "Compressed... at double speed" per spec.md's clarification example — the
# gap between two recorded changes is divided by this factor, not replayed
# at real elapsed pace.
DEFAULT_SPEED = 2.0
_MIN_STEP_SECONDS = 0.05
_MAX_STEP_SECONDS = 3.0  # cap so a multi-hour-old gap doesn't stall playback


async def _apply_replayed_state(client: UE5MCPClient, record: HistoryRecord) -> None:
    """Best-effort visual re-application of one recorded change against the live scene."""
    key = record.subject_key
    new_state = record.new_state

    if record.change_type == "traffic" and isinstance(new_state, (int, float)):
        color = get_traffic_color(new_state).to_list()
        if ":" in key:
            hostname, interface_name = key.split(":", 1)
            await apply_interface_material(client, hostname, interface_name, color)
        else:
            source, target = key.split("_", 1) if "_" in key else (key, key)
            await apply_actor_color(client, generate_link_actor_name(source, target), color)

    elif record.change_type == "health" and isinstance(new_state, str):
        if ":" in key:
            hostname, interface_name = key.split(":", 1)
            await apply_interface_material(client, hostname, interface_name, get_link_status_color(new_state).to_list())
        elif is_device_in_topology(key):
            await apply_device_material(client, key, "unknown", new_state)
        elif is_link_in_topology(key):
            source, target = key.split("_", 1) if "_" in key else (key, key)
            await apply_link_material(client, source, target, new_state)

    elif record.change_type == "trap":
        color = get_link_status_color("healthy").to_list() if new_state == "linkUp" else get_alarm_color().to_list()
        if ":" in key:
            hostname, interface_name = key.split(":", 1)
            await apply_interface_material(client, hostname, interface_name, color)


async def replay_window(
    client: UE5MCPClient,
    start: datetime,
    end: datetime,
    speed: float = DEFAULT_SPEED,
) -> dict:
    """
    Replay every recorded state change in [start, end], in original order,
    at `speed`x the recorded pacing (FR-029/FR-030). Reports explicitly
    when the window has no recorded changes (FR-031).
    """
    records = get_history_window(start, end)
    if not records:
        return {"replayed": 0, "reason": "no recorded changes in this window"}

    for i, record in enumerate(records):
        await _apply_replayed_state(client, record)
        if i < len(records) - 1:
            gap_seconds = (records[i + 1].timestamp - record.timestamp).total_seconds()
            step = max(_MIN_STEP_SECONDS, min(gap_seconds / max(speed, 0.01), _MAX_STEP_SECONDS))
            await asyncio.sleep(step)

    return {"replayed": len(records), "speed": speed, "start": start, "end": end}
