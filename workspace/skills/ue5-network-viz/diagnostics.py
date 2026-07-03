"""
Diagnostics Visualization for UE5 Network Digital Twin (045-ue5-digital-twin, US7).

Animates real ping/traceroute results in the 3D scene. Like telemetry.py's
traffic/health functions, this module does not invoke gnmi-mcp/pyATS itself —
the calling agent executes the real ping/traceroute via those MCP tools in
conversation and hands the already-retrieved outcome to these functions,
which are responsible only for the visual animation (FR-020/FR-021).
"""

import asyncio
from typing import Optional

try:
    from .ue5_mcp_client import UE5MCPClient
    from .actors import (
        apply_actor_color,
        generate_device_actor_name,
        generate_link_actor_name,
        is_device_in_topology,
    )
    from .telemetry import record_history
except ImportError:  # pragma: no cover - fallback for sys.path-style loading
    from ue5_mcp_client import UE5MCPClient
    from actors import (
        apply_actor_color,
        generate_device_actor_name,
        generate_link_actor_name,
        is_device_in_topology,
    )
    from telemetry import record_history

# Deliberately distinct from health-status colors (materials.py's
# DeviceStatus/LinkStatus palette) since a diagnostic animation is a
# transient overlay, not a persistent status change.
PING_SUCCESS_COLOR = [0.0, 1.0, 0.4]
PING_FAILURE_COLOR = [1.0, 0.0, 0.0]
HOP_ILLUMINATE_DELAY_SECONDS = 0.6


async def animate_ping(
    client: UE5MCPClient,
    source_hostname: str,
    target_hostname: str,
    success: bool,
    latency_ms: Optional[float] = None,
) -> dict:
    """
    Animate a real ping result (FR-020/FR-023) between two topology devices:
    pulses the source actor, the direct link actor if one exists, then the
    target actor — green on success, red on failure. Refuses rather than
    attempts when either device isn't in the current topology (FR-022/FR-040).
    """
    if not is_device_in_topology(source_hostname):
        return {"animated": False, "reason": f"{source_hostname} not in current topology"}
    if not is_device_in_topology(target_hostname):
        return {"animated": False, "reason": f"{target_hostname} not in current topology"}

    color = PING_SUCCESS_COLOR if success else PING_FAILURE_COLOR

    await apply_actor_color(client, generate_device_actor_name(source_hostname), color, emissive_intensity=2.0)
    await asyncio.sleep(HOP_ILLUMINATE_DELAY_SECONDS)
    # Best-effort: only lights up if a direct link actor exists between these
    # two devices. A multi-hop ping with no direct link simply skips this
    # step (apply_actor_color no-ops when it can't find the named actor).
    await apply_actor_color(client, generate_link_actor_name(source_hostname, target_hostname), color, emissive_intensity=2.0)
    await asyncio.sleep(HOP_ILLUMINATE_DELAY_SECONDS)
    await apply_actor_color(client, generate_device_actor_name(target_hostname), color, emissive_intensity=2.0)

    record_history(
        f"{source_hostname}->{target_hostname}", "health", None,
        "ping_success" if success else "ping_failure",
    )
    return {"animated": True, "success": success, "latency_ms": latency_ms}


async def animate_traceroute(client: UE5MCPClient, hops: list[dict]) -> dict:
    """
    Animate a real traceroute's hop list as sequential illumination
    (FR-021), in order. `hops` is `[{"hostname": str, "reached": bool}, ...]`
    already retrieved by the calling agent. A hop that timed out
    (`reached=False`) lights up red instead of green, so failures are
    visually distinguishable (FR-023), but the animation still proceeds
    through the remaining hops. A hop naming a device not in the current
    topology is reported and skipped rather than attempted (FR-022/FR-040),
    without aborting the rest of the sequence.
    """
    animated: list[str] = []
    skipped: list[str] = []

    for hop in hops:
        hostname = hop.get("hostname")
        reached = hop.get("reached", True)
        if not hostname or not is_device_in_topology(hostname):
            skipped.append(hostname or "?")
            continue

        color = PING_SUCCESS_COLOR if reached else PING_FAILURE_COLOR
        await apply_actor_color(client, generate_device_actor_name(hostname), color, emissive_intensity=2.0)
        animated.append(hostname)
        await asyncio.sleep(HOP_ILLUMINATE_DELAY_SECONDS)

    path = "->".join(h.get("hostname") or "?" for h in hops)
    record_history(f"traceroute:{path}", "health", None, {"animated": animated, "skipped": skipped})
    return {"animated": animated, "skipped": skipped}
