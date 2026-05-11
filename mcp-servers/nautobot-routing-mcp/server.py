"""Nautobot Routing MCP Server — BGP and OSPF model management.

One-call tools for BGP peering lifecycle, peer group management, OSPF
interface configuration, and routing model reconciliation against live state.

Environment Variables:
    NAUTOBOT_URL          — Nautobot instance URL (required)
    NAUTOBOT_TOKEN        — Nautobot API token (required)
    NAUTOBOT_TIMEOUT      — API request timeout in seconds (default: 60)
    NAUTOBOT_VERIFY_SSL   — Verify SSL certificates (default: false)
    ITSM_ENABLED          — Require ServiceNow CR for write ops (default: false)
    ITSM_LAB_MODE         — Bypass ITSM in lab mode (default: true)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

from nautobot_client import NautobotClient, NautobotError
from bgp_helpers import (
    find_routing_instance,
    find_or_create_asn,
    find_ip_id,
    find_peer_group,
    find_peering_by_ips,
    find_endpoint_by_peer_ip,
    _esc,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("nautobot-routing-mcp")

for var in ("NAUTOBOT_URL", "NAUTOBOT_TOKEN"):
    if not os.environ.get(var):
        logger.error(f"Required environment variable {var} is not set.")
        sys.exit(1)

mcp = FastMCP("nautobot-routing-mcp")
client = NautobotClient()

ITSM_ENABLED = os.environ.get("ITSM_ENABLED", "false").lower() == "true"
ITSM_LAB_MODE = os.environ.get("ITSM_LAB_MODE", "true").lower() == "true"


def _check_itsm(cr_number: Optional[str]) -> Optional[str]:
    if ITSM_ENABLED and not ITSM_LAB_MODE:
        if not cr_number:
            return "Write operation blocked: ITSM is enabled. Provide a cr_number parameter."
    return None


# ═══════════════════════════════════════════════════════════════════════
# PHASE 2: BGP READ TOOLS
# ═══════════════════════════════════════════════════════════════════════


@mcp.tool()
async def routing_get_bgp_summary(device: Optional[str] = None) -> str:
    """Get the full BGP topology for a device: routing instance, ASN, peers, groups, address families.

    Returns a structured summary equivalent to 'show bgp summary' but from the
    Nautobot source of truth. If device is omitted, returns all routing instances.

    Args:
        device: Device name (e.g. 'RR1'). If omitted, returns all BGP instances.
    """
    logger.info(f"routing_get_bgp_summary device={device}")
    try:
        filt = f'(device: "{_esc(device)}")' if device else ""
        query = f"""{{
  bgp_routing_instances{filt} {{
    device {{ name }}
    autonomous_system {{ asn description }}
    router_id {{ address }}
    status {{ name }}
    peer_groups {{
      name
      autonomous_system {{ asn }}
      source_ip {{ address }}
      source_interface {{ name }}
    }}
    endpoints {{
      enabled
      source_ip {{ address }}
      autonomous_system {{ asn }}
      peer_group {{ name }}
      peer {{ source_ip {{ address }} autonomous_system {{ asn }} }}
    }}
  }}
}}"""
        data = await client.graphql(query)
        instances = data.get("bgp_routing_instances", [])

        results = []
        for inst in instances:
            dev_name = inst.get("device", {}).get("name")
            local_asn = inst.get("autonomous_system", {}).get("asn")
            peers = []
            for ep in inst.get("endpoints", []):
                remote = ep.get("peer") or {}
                remote_ip = remote.get("source_ip", {}).get("address", "")
                remote_asn = (ep.get("autonomous_system") or remote.get("autonomous_system") or {}).get("asn")
                peers.append({
                    "local_ip": ep.get("source_ip", {}).get("address", ""),
                    "remote_ip": remote_ip,
                    "remote_asn": remote_asn,
                    "peer_group": (ep.get("peer_group") or {}).get("name"),
                    "enabled": ep.get("enabled"),
                })
            results.append({
                "device": dev_name,
                "local_asn": local_asn,
                "router_id": inst.get("router_id", {}).get("address"),
                "peer_count": len(peers),
                "peer_groups": [pg["name"] for pg in inst.get("peer_groups", [])],
                "peers": peers,
            })

        return json.dumps({"count": len(results), "bgp_instances": results}, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def routing_get_bgp_peers(device: str) -> str:
    """List all BGP peers for a device with remote AS, local/remote IP, peer group, and enabled state.

    Args:
        device: Device name (e.g. 'RR1')
    """
    logger.info(f"routing_get_bgp_peers device={device}")
    try:
        query = f"""{{
  bgp_routing_instances(device: "{_esc(device)}") {{
    autonomous_system {{ asn }}
    endpoints {{
      id enabled description
      source_ip {{ address }}
      autonomous_system {{ asn }}
      peer_group {{ name }}
      peer {{
        source_ip {{ address }}
        autonomous_system {{ asn }}
        routing_instance {{ device {{ name }} }}
      }}
    }}
  }}
}}"""
        data = await client.graphql(query)
        instances = data.get("bgp_routing_instances", [])
        if not instances:
            return json.dumps({"device": device, "error": "No BGP routing instance found for this device."})

        local_asn = instances[0].get("autonomous_system", {}).get("asn")
        peers = []
        for ep in instances[0].get("endpoints", []):
            remote = ep.get("peer") or {}
            remote_asn = (ep.get("autonomous_system") or remote.get("autonomous_system") or {}).get("asn")
            peers.append({
                "local_ip": ep.get("source_ip", {}).get("address", ""),
                "remote_ip": (remote.get("source_ip") or {}).get("address", ""),
                "remote_asn": remote_asn,
                "remote_device": (remote.get("routing_instance") or {}).get("device", {}).get("name"),
                "peer_group": (ep.get("peer_group") or {}).get("name"),
                "enabled": ep.get("enabled"),
                "description": ep.get("description"),
                "type": "iBGP" if remote_asn == local_asn else "eBGP",
            })

        return json.dumps({
            "device": device,
            "local_asn": local_asn,
            "peer_count": len(peers),
            "peers": peers,
        }, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def routing_get_bgp_peer_detail(device: str, peer_ip: str) -> str:
    """Get full detail of a specific BGP peering: both endpoints, address families, peer group.

    Args:
        device: Local device name (e.g. 'RR1')
        peer_ip: Remote peer IP address (e.g. '100.0.254.1')
    """
    logger.info(f"routing_get_bgp_peer_detail device={device} peer_ip={peer_ip}")
    try:
        ep_info = await find_endpoint_by_peer_ip(client, device, peer_ip)
        if not ep_info:
            return json.dumps({"error": f"No peering found for {device} with peer {peer_ip}"})

        # Get full peering detail
        peering_id = ep_info["peering_id"]
        peering = await client.rest_get(f"plugins/bgp/peerings/{peering_id}")

        # Get both endpoints via GraphQL (REST doesn't support peering filter)
        ep_query = f"""{{ bgp_peer_endpoints {{
            id enabled description
            routing_instance {{ device {{ name }} autonomous_system {{ asn }} }}
            source_ip {{ address }}
            autonomous_system {{ asn }}
            peer_group {{ name }}
            peering {{ id }}
        }} }}"""
        ep_data = await client.graphql(ep_query)
        endpoints = [
            ep for ep in ep_data.get("bgp_peer_endpoints", [])
            if ep.get("peering", {}).get("id") == peering_id
        ]

        result = {
            "peering_id": peering_id,
            "status": peering.get("status", {}).get("value") if isinstance(peering.get("status"), dict) else peering.get("status"),
            "endpoints": endpoints,
        }

        return json.dumps(result, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def routing_get_peer_groups(device: Optional[str] = None) -> str:
    """List BGP peer groups with member count and address families.

    Args:
        device: Device name to filter by (optional). If omitted, returns all peer groups.
    """
    logger.info(f"routing_get_peer_groups device={device}")
    try:
        filt = f'(device: "{_esc(device)}")' if device else ""
        query = f"""{{
  bgp_routing_instances{filt} {{
    device {{ name }}
    peer_groups {{
      id name description enabled
      autonomous_system {{ asn }}
      source_ip {{ address }}
      source_interface {{ name }}
    }}
    endpoints {{
      peer_group {{ id }}
    }}
  }}
}}"""
        data = await client.graphql(query)
        instances = data.get("bgp_routing_instances", [])

        groups = []
        for inst in instances:
            # Count members per group
            member_counts: dict[str, int] = {}
            for ep in inst.get("endpoints", []):
                pg = ep.get("peer_group")
                if pg:
                    member_counts[pg["id"]] = member_counts.get(pg["id"], 0) + 1

            for pg in inst.get("peer_groups", []):
                groups.append({
                    "device": inst.get("device", {}).get("name"),
                    "name": pg["name"],
                    "remote_asn": (pg.get("autonomous_system") or {}).get("asn"),
                    "source_ip": (pg.get("source_ip") or {}).get("address"),
                    "source_interface": (pg.get("source_interface") or {}).get("name"),
                    "enabled": pg.get("enabled"),
                    "member_count": member_counts.get(pg["id"], 0),
                })

        return json.dumps({"count": len(groups), "peer_groups": groups}, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def routing_get_autonomous_systems() -> str:
    """List all autonomous systems registered in the Nautobot BGP model."""
    logger.info("routing_get_autonomous_systems")
    try:
        query = """{ autonomous_systems { asn description status { name } provider { name } } }"""
        data = await client.graphql(query)
        systems = data.get("autonomous_systems", [])
        return json.dumps({"count": len(systems), "autonomous_systems": systems}, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: BGP WRITE TOOLS
# ═══════════════════════════════════════════════════════════════════════


@mcp.tool()
async def routing_create_autonomous_system(
    asn: int,
    description: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create or return an existing autonomous system. Idempotent. ITSM-gated.

    Args:
        asn: AS number (e.g. 65099)
        description: Optional description (e.g. 'NetClaw Protocol Agent')
        cr_number: ServiceNow change request number (required if ITSM enabled)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"routing_create_autonomous_system asn={asn}")
    try:
        resp = await client.rest_get("plugins/bgp/autonomous-systems", {"asn": asn})
        results = resp.get("results", [])
        if results:
            return json.dumps({"status": "already_exists", "asn": asn, "id": results[0]["id"]})

        payload: dict = {"asn": asn, "status": {"name": "Active"}}
        if description:
            payload["description"] = description
        result = await client.rest_post("plugins/bgp/autonomous-systems", payload)
        return json.dumps({"status": "created", "asn": asn, "id": result["id"]}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def routing_create_routing_instance(
    device: str,
    asn: int,
    router_id: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create a BGP routing instance for a device. Idempotent. ITSM-gated.

    Args:
        device: Device name (e.g. 'RR1')
        asn: Local autonomous system number
        router_id: Router ID IP address (optional, e.g. '100.0.254.5/32')
        cr_number: ServiceNow change request number (required if ITSM enabled)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"routing_create_routing_instance device={device} asn={asn}")
    try:
        existing = await find_routing_instance(client, device)
        if existing:
            return json.dumps({"status": "already_exists", "device": device, "id": existing})

        # Resolve device ID
        dev_data = await client.graphql(f'{{ devices(name: "{_esc(device)}") {{ id }} }}')
        devices = dev_data.get("devices", [])
        if not devices:
            return json.dumps({"error": f"Device '{device}' not found"})
        device_id = devices[0]["id"]

        # Find or create ASN
        asn_id = await find_or_create_asn(client, asn)

        payload: dict = {
            "device": device_id,
            "autonomous_system": asn_id,
            "status": {"name": "Active"},
        }
        if router_id:
            rid_id = await find_ip_id(client, router_id)
            if rid_id:
                payload["router_id"] = rid_id

        result = await client.rest_post("plugins/bgp/routing-instances", payload)
        return json.dumps({"status": "created", "device": device, "id": result["id"]}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def routing_create_peering(
    device: str,
    local_ip: str,
    peer_ip: str,
    peer_asn: int,
    peer_group: Optional[str] = None,
    afi: str = "ipv4_unicast",
    description: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create a complete BGP peering in one call. Idempotent. ITSM-gated.

    Handles the full object chain: ASN (if new) + Peering + 2 Endpoints + address family.
    If the peering already exists, returns the existing one.

    Args:
        device: Local device name (e.g. 'RR1')
        local_ip: Local source IP with mask (e.g. '10.255.255.2/30')
        peer_ip: Remote peer IP with mask (e.g. '10.255.255.1/30')
        peer_asn: Remote autonomous system number
        peer_group: Optional peer group name to associate the local endpoint with
        afi: Address family (default: 'ipv4_unicast'). Options: ipv4_unicast, ipv6_unicast, l2_evpn
        description: Optional peering description
        cr_number: ServiceNow change request number (required if ITSM enabled)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"routing_create_peering device={device} local={local_ip} peer={peer_ip} as={peer_asn}")
    try:
        # Idempotency check
        existing = await find_peering_by_ips(client, device, local_ip, peer_ip)
        if existing:
            return json.dumps({
                "status": "already_exists",
                "peering_id": existing["peering_id"],
                "endpoint_id": existing["endpoint_id"],
            })

        # 1. Find routing instance
        instance_id = await find_routing_instance(client, device)
        if not instance_id:
            return json.dumps({"error": f"No BGP routing instance for device '{device}'. Create one first with routing_create_routing_instance."})

        # 2. Find or create remote ASN
        asn_id = await find_or_create_asn(client, peer_asn, description=f"AS {peer_asn}")

        # 3. Resolve IPs
        local_ip_id = await find_ip_id(client, local_ip)
        if not local_ip_id:
            return json.dumps({"error": f"Local IP '{local_ip}' not found in Nautobot. Create the interface and IP first."})
        peer_ip_id = await find_ip_id(client, peer_ip)

        # 4. Find peer group if specified
        pg_id = None
        if peer_group:
            pg_id = await find_peer_group(client, device, peer_group)
            if not pg_id:
                return json.dumps({"error": f"Peer group '{peer_group}' not found on device '{device}'."})

        # 5. Create Peering container
        peering_payload: dict = {"status": {"name": "Active"}}
        peering = await client.rest_post("plugins/bgp/peerings", peering_payload)
        peering_id = peering["id"]

        # 6. Create Endpoint A (local)
        ep_a_payload: dict = {
            "peering": peering_id,
            "routing_instance": instance_id,
            "source_ip": local_ip_id,
            "enabled": True,
        }
        if pg_id:
            ep_a_payload["peer_group"] = pg_id
        if description:
            ep_a_payload["description"] = description
        ep_a = await client.rest_post("plugins/bgp/peer-endpoints", ep_a_payload)

        # 7. Create Endpoint B (remote)
        ep_b_payload: dict = {
            "peering": peering_id,
            "autonomous_system": asn_id,
            "enabled": True,
        }
        if peer_ip_id:
            ep_b_payload["source_ip"] = peer_ip_id
        ep_b = await client.rest_post("plugins/bgp/peer-endpoints", ep_b_payload)

        # 8. Add address family to local endpoint
        try:
            await client.rest_post("plugins/bgp/peer-endpoint-address-families", {
                "peer_endpoint": ep_a["id"],
                "afi_safi": afi,
            })
        except NautobotError:
            pass  # AFI may already exist or not be supported

        return json.dumps({
            "status": "created",
            "peering_id": peering_id,
            "endpoint_a": ep_a["id"],
            "endpoint_b": ep_b["id"],
            "device": device,
            "local_ip": local_ip,
            "peer_ip": peer_ip,
            "peer_asn": peer_asn,
            "peer_group": peer_group,
            "afi": afi,
        }, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def routing_delete_peering(
    device: str,
    peer_ip: str,
    cr_number: Optional[str] = None,
) -> str:
    """Delete a BGP peering and both endpoints. ITSM-gated.

    Args:
        device: Local device name (e.g. 'RR1')
        peer_ip: Remote peer IP address (e.g. '10.255.255.1')
        cr_number: ServiceNow change request number (required if ITSM enabled)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"routing_delete_peering device={device} peer_ip={peer_ip}")
    try:
        ep_info = await find_endpoint_by_peer_ip(client, device, peer_ip)
        if not ep_info:
            return json.dumps({"error": f"No peering found for {device} with peer {peer_ip}"})

        peering_id = ep_info["peering_id"]
        # Deleting the peering cascades to endpoints
        await client.rest_delete(f"plugins/bgp/peerings/{peering_id}")

        return json.dumps({
            "status": "deleted",
            "peering_id": peering_id,
            "device": device,
            "peer_ip": peer_ip,
        })
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def routing_create_peer_group(
    device: str,
    name: str,
    remote_asn: Optional[int] = None,
    source_interface: Optional[str] = None,
    afi: str = "ipv4_unicast",
    description: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create a BGP peer group on a device. Idempotent. ITSM-gated.

    Args:
        device: Device name (e.g. 'RR1')
        name: Peer group name (e.g. 'NETCLAW-PEERS')
        remote_asn: Optional remote AS for the group
        source_interface: Optional update-source interface name (e.g. 'Loopback0')
        afi: Address family (default: 'ipv4_unicast')
        description: Optional description
        cr_number: ServiceNow change request number (required if ITSM enabled)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"routing_create_peer_group device={device} name={name}")
    try:
        # Idempotency check
        existing = await find_peer_group(client, device, name)
        if existing:
            return json.dumps({"status": "already_exists", "name": name, "id": existing})

        # Find routing instance
        instance_id = await find_routing_instance(client, device)
        if not instance_id:
            return json.dumps({"error": f"No BGP routing instance for device '{device}'."})

        payload: dict = {
            "name": name,
            "routing_instance": instance_id,
            "enabled": True,
        }
        if description:
            payload["description"] = description
        if remote_asn:
            asn_id = await find_or_create_asn(client, remote_asn)
            payload["autonomous_system"] = asn_id
        if source_interface:
            # Resolve interface ID
            iface_data = await client.graphql(
                f'{{ interfaces(device: "{_esc(device)}", name: "{_esc(source_interface)}") {{ id }} }}'
            )
            ifaces = iface_data.get("interfaces", [])
            if ifaces:
                payload["source_interface"] = ifaces[0]["id"]

        result = await client.rest_post("plugins/bgp/peer-groups", payload)
        pg_id = result["id"]

        # Add address family
        try:
            await client.rest_post("plugins/bgp/peer-group-address-families", {
                "peer_group": pg_id,
                "afi_safi": afi,
            })
        except NautobotError:
            pass  # May not be supported or already exists

        return json.dumps({"status": "created", "name": name, "id": pg_id, "afi": afi}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def routing_delete_peer_group(
    device: str,
    name: str,
    cr_number: Optional[str] = None,
) -> str:
    """Delete a BGP peer group. Fails if the group still has members. ITSM-gated.

    Args:
        device: Device name (e.g. 'RR1')
        name: Peer group name to delete
        cr_number: ServiceNow change request number (required if ITSM enabled)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"routing_delete_peer_group device={device} name={name}")
    try:
        pg_id = await find_peer_group(client, device, name)
        if not pg_id:
            return json.dumps({"error": f"Peer group '{name}' not found on device '{device}'."})

        await client.rest_delete(f"plugins/bgp/peer-groups/{pg_id}")
        return json.dumps({"status": "deleted", "name": name, "device": device})
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def routing_add_peer_to_group(
    device: str,
    peer_ip: str,
    group: str,
    cr_number: Optional[str] = None,
) -> str:
    """Move an existing BGP peer into a peer group. ITSM-gated.

    Args:
        device: Local device name (e.g. 'RR1')
        peer_ip: Remote peer IP address
        group: Peer group name to add the peer to
        cr_number: ServiceNow change request number (required if ITSM enabled)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"routing_add_peer_to_group device={device} peer_ip={peer_ip} group={group}")
    try:
        ep_info = await find_endpoint_by_peer_ip(client, device, peer_ip)
        if not ep_info:
            return json.dumps({"error": f"No peering found for {device} with peer {peer_ip}"})

        pg_id = await find_peer_group(client, device, group)
        if not pg_id:
            return json.dumps({"error": f"Peer group '{group}' not found on device '{device}'."})

        await client.rest_patch(
            f"plugins/bgp/peer-endpoints/{ep_info['endpoint_id']}",
            {"peer_group": pg_id},
        )
        return json.dumps({"status": "updated", "peer_ip": peer_ip, "group": group, "device": device})
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def routing_remove_peer_from_group(
    device: str,
    peer_ip: str,
    cr_number: Optional[str] = None,
) -> str:
    """Remove a BGP peer from its peer group. ITSM-gated.

    Args:
        device: Local device name (e.g. 'RR1')
        peer_ip: Remote peer IP address
        cr_number: ServiceNow change request number (required if ITSM enabled)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"routing_remove_peer_from_group device={device} peer_ip={peer_ip}")
    try:
        ep_info = await find_endpoint_by_peer_ip(client, device, peer_ip)
        if not ep_info:
            return json.dumps({"error": f"No peering found for {device} with peer {peer_ip}"})

        current_group = (ep_info.get("peer_group") or {}).get("name")
        if not current_group:
            return json.dumps({"status": "no_change", "message": "Peer is not in any group."})

        await client.rest_patch(
            f"plugins/bgp/peer-endpoints/{ep_info['endpoint_id']}",
            {"peer_group": None},
        )
        return json.dumps({"status": "updated", "peer_ip": peer_ip, "removed_from": current_group, "device": device})
    except NautobotError as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════
# PHASE 5: RECONCILIATION TOOLS
# ═══════════════════════════════════════════════════════════════════════


@mcp.tool()
async def routing_reconcile_bgp(device: str, live_peers: str) -> str:
    """Compare Nautobot BGP model vs live peer data from pyATS. Returns drift report.

    Identifies: peers in Nautobot but not live (documented but not established),
    peers live but not in Nautobot (undocumented), and ASN mismatches.

    Args:
        device: Device name (e.g. 'RR1')
        live_peers: JSON array of live peers from 'show bgp summary'. Each entry:
                    {"ip": "10.0.0.1", "asn": 65001, "state": "Established"}
    """
    logger.info(f"routing_reconcile_bgp device={device}")
    try:
        live = json.loads(live_peers)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid live_peers JSON: {e}"})

    try:
        # Get Nautobot BGP peers for this device
        result = await routing_get_bgp_peers(device)
        nb_data = json.loads(result)
        if nb_data.get("error"):
            return json.dumps({"error": nb_data["error"]})

        nb_peers = nb_data.get("peers", [])

        # Build lookup maps (by IP without mask)
        nb_map: dict[str, dict] = {}
        for p in nb_peers:
            ip = p.get("remote_ip", "").split("/")[0]
            if ip:
                nb_map[ip] = p

        live_map: dict[str, dict] = {}
        for p in live:
            ip = p.get("ip", "").split("/")[0]
            if ip:
                live_map[ip] = p

        # Compare
        in_nautobot_not_live = []
        for ip, p in nb_map.items():
            if ip not in live_map:
                in_nautobot_not_live.append({
                    "peer_ip": ip,
                    "asn": p.get("remote_asn"),
                    "peer_group": p.get("peer_group"),
                    "status": "documented but not established",
                })

        in_live_not_nautobot = []
        for ip, p in live_map.items():
            if ip not in nb_map:
                in_live_not_nautobot.append({
                    "peer_ip": ip,
                    "asn": p.get("asn"),
                    "state": p.get("state"),
                    "status": "undocumented peer",
                })

        asn_mismatch = []
        for ip in set(nb_map) & set(live_map):
            nb_asn = nb_map[ip].get("remote_asn")
            live_asn = live_map[ip].get("asn")
            if nb_asn and live_asn and int(nb_asn) != int(live_asn):
                asn_mismatch.append({
                    "peer_ip": ip,
                    "nautobot_asn": nb_asn,
                    "live_asn": live_asn,
                })

        return json.dumps({
            "device": device,
            "nautobot_peers": len(nb_map),
            "live_peers": len(live_map),
            "in_sync": len(in_nautobot_not_live) == 0 and len(in_live_not_nautobot) == 0 and len(asn_mismatch) == 0,
            "drift": {
                "in_nautobot_not_live": in_nautobot_not_live,
                "in_live_not_nautobot": in_live_not_nautobot,
                "asn_mismatch": asn_mismatch,
            },
        }, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run(transport="stdio")
