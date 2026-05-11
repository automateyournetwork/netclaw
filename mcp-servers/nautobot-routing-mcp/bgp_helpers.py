"""BGP object chain resolution helpers."""

from __future__ import annotations

from typing import Any, Optional

from nautobot_client import NautobotClient, NautobotError


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


async def find_routing_instance(client: NautobotClient, device: str) -> Optional[str]:
    """Find the BGP routing instance ID for a device."""
    data = await client.graphql(
        f'{{ bgp_routing_instances(device: "{_esc(device)}") {{ id }} }}'
    )
    instances = data.get("bgp_routing_instances", [])
    return instances[0]["id"] if instances else None


async def find_or_create_asn(client: NautobotClient, asn: int, description: Optional[str] = None) -> str:
    """Find an ASN by number or create it. Returns UUID."""
    resp = await client.rest_get("plugins/bgp/autonomous-systems", {"asn": asn})
    results = resp.get("results", [])
    if results:
        return results[0]["id"]
    payload = {"asn": asn, "status": {"name": "Active"}}
    if description:
        payload["description"] = description
    result = await client.rest_post("plugins/bgp/autonomous-systems", payload)
    return result["id"]


async def find_ip_id(client: NautobotClient, address: str) -> Optional[str]:
    """Find an IP address UUID by address string."""
    data = await client.graphql(f'{{ ip_addresses(address: "{_esc(address)}") {{ id }} }}')
    ips = data.get("ip_addresses", [])
    return ips[0]["id"] if ips else None


async def find_peer_group(client: NautobotClient, device: str, name: str) -> Optional[str]:
    """Find a peer group by name within a device's routing instance."""
    data = await client.graphql(f"""{{
        bgp_routing_instances(device: "{_esc(device)}") {{
            peer_groups {{ id name }}
        }}
    }}""")
    instances = data.get("bgp_routing_instances", [])
    if not instances:
        return None
    for pg in instances[0].get("peer_groups", []):
        if pg["name"] == name:
            return pg["id"]
    return None


async def find_peering_by_ips(client: NautobotClient, device: str, local_ip: str, peer_ip: str) -> Optional[dict]:
    """Find an existing peering between local_ip and peer_ip for a device."""
    data = await client.graphql(f"""{{
        bgp_routing_instances(device: "{_esc(device)}") {{
            endpoints {{
                id
                source_ip {{ address }}
                peer {{ source_ip {{ address }} }}
                peering {{ id }}
            }}
        }}
    }}""")
    instances = data.get("bgp_routing_instances", [])
    if not instances:
        return None
    for ep in instances[0].get("endpoints", []):
        ep_ip = ep.get("source_ip", {}).get("address", "")
        peer_ep_ip = (ep.get("peer") or {}).get("source_ip", {}).get("address", "")
        if _ip_match(ep_ip, local_ip) and _ip_match(peer_ep_ip, peer_ip):
            return {"endpoint_id": ep["id"], "peering_id": ep.get("peering", {}).get("id")}
    return None


async def find_endpoint_by_peer_ip(client: NautobotClient, device: str, peer_ip: str) -> Optional[dict]:
    """Find a local endpoint whose remote peer has the given IP."""
    data = await client.graphql(f"""{{
        bgp_routing_instances(device: "{_esc(device)}") {{
            endpoints {{
                id
                peer {{ id source_ip {{ address }} }}
                peering {{ id }}
                peer_group {{ id name }}
            }}
        }}
    }}""")
    instances = data.get("bgp_routing_instances", [])
    if not instances:
        return None
    for ep in instances[0].get("endpoints", []):
        remote_ip = (ep.get("peer") or {}).get("source_ip", {}).get("address", "")
        if _ip_match(remote_ip, peer_ip):
            return {
                "endpoint_id": ep["id"],
                "peer_endpoint_id": ep.get("peer", {}).get("id"),
                "peering_id": ep.get("peering", {}).get("id"),
                "peer_group": ep.get("peer_group"),
            }
    return None


def _ip_match(a: str, b: str) -> bool:
    """Compare IPs ignoring prefix length differences."""
    return a.split("/")[0] == b.split("/")[0]
