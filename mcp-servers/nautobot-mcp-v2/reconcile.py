"""Reconciliation engine — compare live device state against Nautobot SoT."""

from datetime import datetime, timezone
from typing import Any


def reconcile_interfaces(
    nautobot_interfaces: list[dict[str, Any]],
    live_interfaces: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare Nautobot interface records against live device interface data.

    Returns a structured diff report with matches, mismatches, device_only, nautobot_only.
    """
    # Index by normalized name
    nb_map = {_norm(i["name"]): i for i in nautobot_interfaces}
    live_map = {_norm(i["name"]): i for i in live_interfaces}

    nb_names = set(nb_map)
    live_names = set(live_map)

    both = nb_names & live_names
    nb_only = nb_names - live_names
    live_only = live_names - nb_names

    matches = []
    mismatches = []

    for name in sorted(both):
        nb = nb_map[name]
        live = live_map[name]
        diffs = _compare(nb, live)
        if diffs:
            mismatches.append({"name": nb["name"], "differences": diffs})
        else:
            matches.append({"name": nb["name"]})

    nautobot_only = [{"name": nb_map[n]["name"]} for n in sorted(nb_only)]
    device_only = [{"name": live_map[n]["name"]} for n in sorted(live_only)]

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_nautobot": len(nautobot_interfaces),
            "total_live": len(live_interfaces),
            "matches": len(matches),
            "mismatches": len(mismatches),
            "nautobot_only": len(nautobot_only),
            "device_only": len(device_only),
        },
        "matches": matches,
        "mismatches": mismatches,
        "nautobot_only": nautobot_only,
        "device_only": device_only,
    }


def _compare(nb: dict, live: dict) -> list[dict]:
    """Compare fields between a Nautobot interface and a live interface."""
    diffs = []

    # enabled
    nb_enabled = nb.get("enabled")
    live_enabled = live.get("enabled")
    if nb_enabled is not None and live_enabled is not None and nb_enabled != live_enabled:
        diffs.append({"field": "enabled", "nautobot": nb_enabled, "live": live_enabled})

    # description
    nb_desc = (nb.get("description") or "").strip()
    live_desc = (live.get("description") or "").strip()
    if nb_desc != live_desc:
        diffs.append({"field": "description", "nautobot": nb_desc, "live": live_desc})

    # mtu
    nb_mtu = nb.get("mtu")
    live_mtu = live.get("mtu")
    if nb_mtu is not None and live_mtu is not None and nb_mtu != live_mtu:
        diffs.append({"field": "mtu", "nautobot": nb_mtu, "live": live_mtu})

    # ip_addresses
    nb_ips = _extract_ips(nb)
    live_ips = set(live.get("ip_addresses") or [])
    if nb_ips != live_ips:
        diffs.append({
            "field": "ip_addresses",
            "nautobot": sorted(nb_ips),
            "live": sorted(live_ips),
        })

    return diffs


def _extract_ips(nb: dict) -> set[str]:
    """Extract IP address strings from a Nautobot interface record."""
    ips = nb.get("ip_addresses", [])
    if not ips:
        return set()
    return {ip["address"] if isinstance(ip, dict) else ip for ip in ips}


def _norm(name: str) -> str:
    """Normalize interface name for comparison."""
    return name.strip().lower()
