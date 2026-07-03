"""
PagerDuty Incident Correlation for UE5 Network Digital Twin (045-ue5-digital-twin, US9).

Like telemetry.py's traffic/health functions, this module never calls
PagerDuty itself — the calling agent retrieves open incidents via PagerDuty's
existing MCP integration in conversation, and hands the results here as a
plain list of dicts. This module's job is only the hostname-substring
correlation and the resulting alarm visual state (FR-026/FR-027).
"""

try:
    from .ue5_mcp_client import UE5MCPClient
    from .actors import (
        apply_actor_color,
        generate_device_actor_name,
        generate_link_actor_name,
        is_device_in_topology,
        is_link_in_topology,
    )
    from .materials import get_alarm_color
    from .telemetry import record_history
except ImportError:  # pragma: no cover - fallback for sys.path-style loading
    from ue5_mcp_client import UE5MCPClient
    from actors import (
        apply_actor_color,
        generate_device_actor_name,
        generate_link_actor_name,
        is_device_in_topology,
        is_link_in_topology,
    )
    from materials import get_alarm_color
    from telemetry import record_history


async def correlate_incident(
    client: UE5MCPClient,
    hostname_or_link: str,
    open_incidents: list[dict],
) -> dict:
    """
    Correlate `hostname_or_link` against `open_incidents` (already retrieved
    by the calling agent via PagerDuty's MCP integration) by hostname
    substring match against each incident's title/description/service_name
    (FR-026). For a link, either endpoint's hostname counts as a match. On a
    match, applies the alarm visual state to the corresponding actor.
    Explicitly reports "no correlated incident" rather than a silent no-op
    (FR-027), and refuses rather than attempts for a subject not in the
    current topology (FR-040).
    """
    if is_device_in_topology(hostname_or_link):
        candidate_hostnames = [hostname_or_link]
        subject_kind = "device"
    elif is_link_in_topology(hostname_or_link):
        parts = hostname_or_link.split("_", 1)
        candidate_hostnames = parts if len(parts) == 2 else [hostname_or_link]
        subject_kind = "link"
    else:
        return {"correlated": False, "reason": f"{hostname_or_link} not in current topology"}

    for incident in open_incidents:
        haystack = " ".join([
            str(incident.get("title", "")),
            str(incident.get("description", "")),
            str(incident.get("service_name", "")),
        ]).lower()

        if not any(hostname.lower() in haystack for hostname in candidate_hostnames):
            continue

        color = get_alarm_color().to_list()
        if subject_kind == "device":
            applied = await apply_actor_color(
                client, generate_device_actor_name(hostname_or_link), color, emissive_intensity=3.0
            )
        else:
            applied = await apply_actor_color(
                client, generate_link_actor_name(*candidate_hostnames), color, emissive_intensity=3.0
            )

        record_history(hostname_or_link, "trap", None, f"incident:{incident.get('incident_id')}")
        return {
            "correlated": True,
            "incident_id": incident.get("incident_id"),
            "alarm_state_applied": applied,
        }

    return {"correlated": False, "reason": f"no open incident references {hostname_or_link}"}
