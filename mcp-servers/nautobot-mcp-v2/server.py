"""Nautobot MCP Server v2 — GraphQL reads, REST writes, ITSM-gated changes, reconciliation.

Targets Nautobot 3.1.0 (graphene_django 3.2.3, no GraphQL mutations).
"""

import json
import logging
import os
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

from nautobot_client import NautobotClient, NautobotError, _esc
from reconcile import reconcile_interfaces
from cisco_design_reference import DESIGN_REFERENCE, get_reference, get_all_features, get_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("nautobot-mcp-v2")

# ── Startup validation ───────────────────────────────────────────────

for var in ("NAUTOBOT_URL", "NAUTOBOT_TOKEN"):
    if not os.environ.get(var):
        logger.error(f"Required environment variable {var} is not set.")
        sys.exit(1)

mcp = FastMCP("nautobot-mcp-v2")
client = NautobotClient()

ITSM_ENABLED = os.environ.get("ITSM_ENABLED", "false").lower() == "true"
ITSM_LAB_MODE = os.environ.get("ITSM_LAB_MODE", "true").lower() == "true"


def _check_itsm(cr_number: Optional[str]) -> Optional[str]:
    """Return error message if ITSM blocks the operation, else None."""
    if ITSM_ENABLED and not ITSM_LAB_MODE:
        if not cr_number:
            return (
                "Write operation blocked: ITSM is enabled. "
                "Provide a cr_number parameter with a valid ServiceNow Change Request number."
            )
    return None


def _gql_filters(**kwargs: Optional[str | int | bool]) -> str:
    """Build a GraphQL filter argument string from keyword args."""
    parts = []
    for k, v in kwargs.items():
        if v is None:
            continue
        if isinstance(v, bool):
            parts.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, int):
            parts.append(f"{k}: {v}")
        else:
            parts.append(f'{k}: "{_esc(str(v))}"')
    return f"({', '.join(parts)})" if parts else ""


# ═══════════════════════════════════════════════════════════════════════
# READ TOOLS — GraphQL
# ═══════════════════════════════════════════════════════════════════════


@mcp.tool()
async def nautobot_test_connection() -> str:
    """Test connectivity to the Nautobot API. Verifies GraphQL and REST endpoints."""
    results = {"url": client.url, "graphql": False, "rest": False, "version": None}
    try:
        await client.graphql("{ __typename }")
        results["graphql"] = True
    except Exception as e:
        results["graphql_error"] = str(e)
    try:
        status = await client.rest_get("status")
        results["rest"] = True
        results["nautobot_version"] = status.get("python-version")
        results["plugins"] = list(status.get("plugins", {}).keys())
    except Exception as e:
        results["rest_error"] = str(e)
    return json.dumps(results, indent=2)


@mcp.tool()
async def nautobot_get_devices(
    name: Optional[str] = None,
    location: Optional[str] = None,
    role: Optional[str] = None,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query devices from Nautobot. Returns name, role, platform, location, status, primary IP, serial."""
    logger.info(f"nautobot_get_devices name={name} location={location} role={role}")
    filt = _gql_filters(
        name=name, location=location, role=role, platform=platform,
        status=status, q=q, limit=limit, offset=offset,
    )
    query = f"""{{
  devices{filt} {{
    name serial status {{ name }} role {{ name }} platform {{ name }}
    location {{ name }} device_type {{ model manufacturer {{ name }} }}
    primary_ip4 {{ address }} primary_ip6 {{ address }} comments
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    devices = data.get("devices", [])
    return json.dumps({"count": len(devices), "devices": devices}, indent=2)


@mcp.tool()
async def nautobot_get_interfaces(
    device: Optional[str] = None,
    name: Optional[str] = None,
    type: Optional[str] = None,
    enabled: Optional[bool] = None,
    status: Optional[str] = None,
    has_ip_addresses: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query interfaces from Nautobot with VLAN assignments, IPs, and cable peer."""
    logger.info(f"nautobot_get_interfaces device={device} name={name}")
    filt = _gql_filters(
        device=device, name=name, type=type, enabled=enabled,
        status=status, has_ip_addresses=has_ip_addresses, limit=limit, offset=offset,
    )
    query = f"""{{
  interfaces{filt} {{
    name type enabled status {{ name }} description mac_address mtu mode label
    device {{ name }}
    untagged_vlan {{ vid name }}
    tagged_vlans {{ vid name }}
    ip_addresses {{ address }}
    lag {{ name }}
    connected_interface {{ name device {{ name }} }}
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    ifaces = data.get("interfaces", [])
    return json.dumps({"count": len(ifaces), "interfaces": ifaces}, indent=2)


@mcp.tool()
async def nautobot_get_vlans(
    vid: Optional[int] = None,
    name: Optional[str] = None,
    location: Optional[str] = None,
    vlan_group: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> str:
    """Query VLANs from Nautobot. Returns VID, name, status, locations, group."""
    logger.info(f"nautobot_get_vlans vid={vid} name={name}")
    filt = _gql_filters(
        vid=vid, name=name, location=location, vlan_group=vlan_group,
        status=status, limit=limit, offset=offset,
    )
    query = f"""{{
  vlans{filt} {{
    vid name status {{ name }} locations {{ name }}
    vlan_group {{ name }} tenant {{ name }} role {{ name }} description
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    vlans = data.get("vlans", [])
    return json.dumps({"count": len(vlans), "vlans": vlans}, indent=2)


@mcp.tool()
async def nautobot_get_prefixes(
    prefix: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    tenant: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query IP prefixes from Nautobot IPAM."""
    logger.info(f"nautobot_get_prefixes prefix={prefix}")
    filt = _gql_filters(
        prefix=prefix, status=status, location=location,
        tenant=tenant, limit=limit, offset=offset,
    )
    query = f"""{{
  prefixes{filt} {{
    prefix status {{ name }} locations {{ name }}
    role {{ name }} tenant {{ name }} description
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    prefixes = data.get("prefixes", [])
    return json.dumps({"count": len(prefixes), "prefixes": prefixes}, indent=2)


@mcp.tool()
async def nautobot_get_ip_addresses(
    address: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query IP addresses from Nautobot IPAM with interface/device assignments."""
    logger.info(f"nautobot_get_ip_addresses address={address} q={q}")
    filt = _gql_filters(
        address=address, status=status, q=q, limit=limit, offset=offset,
    )
    query = f"""{{
  ip_addresses{filt} {{
    address status {{ name }} dns_name description tenant {{ name }}
    interface_assignments {{ interface {{ name device {{ name }} }} }}
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    ips = data.get("ip_addresses", [])
    return json.dumps({"count": len(ips), "ip_addresses": ips}, indent=2)


@mcp.tool()
async def nautobot_get_cables(
    device: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query cables from Nautobot. Resolves termination endpoints to device+interface names."""
    logger.info(f"nautobot_get_cables device={device}")
    filt = _gql_filters(status=status, limit=limit, offset=offset)
    query = f"""{{
  cables{filt} {{
    id type status {{ name }} label color length length_unit
    termination_a_type termination_a_id termination_b_type termination_b_id
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})

    cables = data.get("cables", [])

    # Resolve termination UUIDs to names
    iface_ids: set[str] = set()
    for c in cables:
        if c.get("termination_a_type") == "dcim.interface":
            iface_ids.add(c["termination_a_id"])
        if c.get("termination_b_type") == "dcim.interface":
            iface_ids.add(c["termination_b_id"])

    iface_map: dict[str, dict] = {}
    if iface_ids:
        # Batch resolve — query interfaces by id
        for iid in iface_ids:
            try:
                q = f'{{ interfaces(id: "{_esc(iid)}") {{ name device {{ name }} }} }}'
                r = await client.graphql(q)
                ifaces = r.get("interfaces", [])
                if ifaces:
                    iface_map[iid] = ifaces[0]
            except Exception:
                pass

    enriched = []
    for c in cables:
        entry = {
            "id": c["id"],
            "type": c.get("type"),
            "status": c.get("status"),
            "label": c.get("label"),
            "color": c.get("color"),
        }
        for side in ("a", "b"):
            tid = c.get(f"termination_{side}_id")
            ttype = c.get(f"termination_{side}_type")
            if ttype == "dcim.interface" and tid in iface_map:
                info = iface_map[tid]
                entry[f"termination_{side}"] = {
                    "device": info.get("device", {}).get("name"),
                    "interface": info.get("name"),
                }
            else:
                entry[f"termination_{side}"] = {"type": ttype, "id": tid}
        enriched.append(entry)

    # Filter by device if requested
    if device:
        enriched = [
            c for c in enriched
            if (c.get("termination_a", {}).get("device") == device
                or c.get("termination_b", {}).get("device") == device)
        ]

    return json.dumps({"count": len(enriched), "cables": enriched}, indent=2)


@mcp.tool()
async def nautobot_graphql(query: str, variables: Optional[str] = None) -> str:
    """Execute an arbitrary GraphQL query against Nautobot. Read-only — Nautobot 3.1.0 has no GraphQL mutations."""
    logger.info(f"nautobot_graphql query_len={len(query)}")
    vars_dict = None
    if variables:
        try:
            vars_dict = json.loads(variables)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid variables JSON: {e}"})
    try:
        data = await client.graphql(query, vars_dict)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    return json.dumps(data, indent=2)


# ═══════════════════════════════════════════════════════════════════════
# WRITE TOOLS — REST API (ITSM-gated)
# ═══════════════════════════════════════════════════════════════════════


@mcp.tool()
async def nautobot_create_ip_address(
    address: str,
    status: str = "Active",
    device: Optional[str] = None,
    interface: Optional[str] = None,
    dns_name: Optional[str] = None,
    description: Optional[str] = None,
    tenant: Optional[str] = None,
    namespace: str = "Global",
    cr_number: Optional[str] = None,
) -> str:
    """Create an IP address in Nautobot IPAM. Optionally assign to a device interface. ITSM-gated."""
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"nautobot_create_ip_address {address} cr={cr_number}")
    try:
        status_id = await client.resolve_id("status", status)
        ns_id = await client.resolve_id("namespace", namespace)

        payload: dict = {
            "address": address,
            "status": status_id,
            "namespace": ns_id,
        }
        if dns_name:
            payload["dns_name"] = dns_name
        if description:
            payload["description"] = description
        if tenant:
            payload["tenant"] = await client.resolve_id("tenant", tenant)

        result = await client.rest_post("ipam/ip-addresses", payload)

        # Assign to interface if specified
        if device and interface:
            iface_id = await client.resolve_id("interface", f"{device}:{interface}")
            await client.rest_post(
                "ipam/ip-address-to-interface",
                {"ip_address": result["id"], "interface": iface_id},
            )
            result["assigned_to"] = f"{device}:{interface}"

        return json.dumps({"created": True, "ip_address": result}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_create_vlan(
    vid: int,
    name: str,
    status: str = "Active",
    location: Optional[str] = None,
    vlan_group: Optional[str] = None,
    tenant: Optional[str] = None,
    description: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create a VLAN in Nautobot. ITSM-gated."""
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"nautobot_create_vlan vid={vid} name={name} cr={cr_number}")
    try:
        status_id = await client.resolve_id("status", status)
        payload: dict = {"vid": vid, "name": name, "status": status_id}
        if vlan_group:
            payload["vlan_group"] = await client.resolve_id("vlan_group", vlan_group)
        if tenant:
            payload["tenant"] = await client.resolve_id("tenant", tenant)
        if description:
            payload["description"] = description

        result = await client.rest_post("ipam/vlans", payload)

        # Associate with location if specified
        if location:
            loc_id = await client.resolve_id("location", location)
            try:
                await client.rest_post(
                    "ipam/vlan-location-assignments",
                    {"vlan": result["id"], "location": loc_id},
                )
                result["location_assigned"] = location
            except NautobotError as e:
                result["location_warning"] = str(e)

        return json.dumps({"created": True, "vlan": result}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_create_prefix(
    prefix: str,
    status: str = "Active",
    location: Optional[str] = None,
    tenant: Optional[str] = None,
    namespace: str = "Global",
    description: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create a prefix in Nautobot IPAM. ITSM-gated."""
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"nautobot_create_prefix {prefix} cr={cr_number}")
    try:
        status_id = await client.resolve_id("status", status)
        ns_id = await client.resolve_id("namespace", namespace)
        payload: dict = {
            "prefix": prefix,
            "status": status_id,
            "namespace": ns_id,
        }
        if tenant:
            payload["tenant"] = await client.resolve_id("tenant", tenant)
        if description:
            payload["description"] = description

        result = await client.rest_post("ipam/prefixes", payload)

        if location:
            loc_id = await client.resolve_id("location", location)
            try:
                await client.rest_post(
                    "ipam/prefix-location-assignments",
                    {"prefix": result["id"], "location": loc_id},
                )
                result["location_assigned"] = location
            except NautobotError as e:
                result["location_warning"] = str(e)

        return json.dumps({"created": True, "prefix": result}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


# ── Object type → REST endpoint + GraphQL lookup mapping ─────────────

_OBJ_MAP = {
    "device": {
        "endpoint": "dcim/devices",
        "lookup": '{{ devices(name: "{}") {{ id }} }}',
    },
    "interface": {
        "endpoint": "dcim/interfaces",
        # identifier = "DeviceName:InterfaceName"
        "lookup": None,  # uses resolve_id("interface", ...)
    },
    "ip_address": {
        "endpoint": "ipam/ip-addresses",
        "lookup": '{{ ip_addresses(address: "{}") {{ id }} }}',
    },
    "vlan": {
        "endpoint": "ipam/vlans",
        "lookup": '{{ vlans(vid: {}) {{ id }} }}',
    },
    "prefix": {
        "endpoint": "ipam/prefixes",
        "lookup": '{{ prefixes(prefix: "{}") {{ id }} }}',
    },
    "cable": {
        "endpoint": "dcim/cables",
        "lookup": None,  # identifier IS the UUID
    },
}


@mcp.tool()
async def nautobot_update_object(
    object_type: str,
    identifier: str,
    updates: str,
    cr_number: Optional[str] = None,
) -> str:
    """Update any Nautobot object via REST PATCH. Resolves by type+name. ITSM-gated.

    object_type: device, interface, ip_address, vlan, prefix, cable
    identifier: device name, "device:interface", IP address, VLAN vid, prefix, or cable UUID
    updates: JSON string of fields to update
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    if object_type not in _OBJ_MAP:
        return json.dumps(
            {"error": f"Unknown object_type '{object_type}'. Valid: {list(_OBJ_MAP)}"}
        )

    logger.info(
        f"nautobot_update_object type={object_type} id={identifier} cr={cr_number}"
    )

    try:
        update_dict = json.loads(updates)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid updates JSON: {e}"})

    try:
        info = _OBJ_MAP[object_type]
        endpoint = info["endpoint"]

        # Resolve identifier to UUID
        if object_type == "interface":
            obj_id = await client.resolve_id("interface", identifier)
        elif object_type == "cable":
            obj_id = identifier  # already a UUID
        elif object_type == "vlan":
            q = info["lookup"].format(int(identifier))
            data = await client.graphql(q)
            items = _first_list_from(data)
            if not items:
                return json.dumps(
                    {"error": f"VLAN vid={identifier} not found in Nautobot."}
                )
            obj_id = items[0]["id"]
        else:
            q = info["lookup"].format(_esc(identifier))
            data = await client.graphql(q)
            items = _first_list_from(data)
            if not items:
                return json.dumps(
                    {"error": f"{object_type} '{identifier}' not found in Nautobot."}
                )
            obj_id = items[0]["id"]

        # Get current state for old values
        old = await client.rest_get(f"{endpoint}/{obj_id}")

        # Resolve any related object names in updates to UUIDs
        for field in ("status", "role", "location", "platform", "tenant"):
            if field in update_dict and isinstance(update_dict[field], str):
                try:
                    update_dict[field] = await client.resolve_id(
                        field, update_dict[field]
                    )
                except NautobotError:
                    pass  # leave as-is, let REST API validate

        result = await client.rest_patch(f"{endpoint}/{obj_id}", update_dict)

        # Build change summary
        changes = {}
        for k in update_dict:
            old_val = old.get(k)
            new_val = result.get(k)
            if old_val != new_val:
                changes[k] = {"old": old_val, "new": new_val}

        return json.dumps(
            {"updated": True, "object_type": object_type, "id": obj_id, "changes": changes},
            indent=2,
        )
    except NautobotError as e:
        return json.dumps({"error": str(e)})


def _first_list_from(data: dict) -> list:
    for v in data.values():
        if isinstance(v, list):
            return v
    return []


# ═══════════════════════════════════════════════════════════════════════
# RECONCILIATION TOOL
# ═══════════════════════════════════════════════════════════════════════


@mcp.tool()
async def nautobot_reconcile(device_name: str, live_interfaces: str) -> str:
    """Compare live device interfaces (from pyATS) against Nautobot source of truth.

    device_name: Device name in Nautobot
    live_interfaces: JSON array of live interface objects with keys: name, enabled, description, ip_addresses, mtu
    """
    logger.info(f"nautobot_reconcile device={device_name}")

    try:
        live = json.loads(live_interfaces)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid live_interfaces JSON: {e}"})

    if not isinstance(live, list):
        return json.dumps({"error": "live_interfaces must be a JSON array"})

    # Query Nautobot interfaces for this device
    query = f"""{{
  interfaces(device: "{_esc(device_name)}") {{
    name enabled description mtu
    ip_addresses {{ address }}
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})

    nautobot_ifaces = data.get("interfaces", [])
    if not nautobot_ifaces:
        return json.dumps(
            {"error": f"No interfaces found for device '{device_name}' in Nautobot."}
        )

    report = reconcile_interfaces(nautobot_ifaces, live)
    report["device_name"] = device_name
    return json.dumps(report, indent=2)


# ═══════════════════════════════════════════════════════════════════════
# DESIGN REFERENCE TOOLS — Cisco best practices knowledge base
# ═══════════════════════════════════════════════════════════════════════


@mcp.tool()
async def cisco_design_reference(
    feature: Optional[str] = None,
) -> str:
    """Query Cisco design best practices for network configuration features.

    Returns best practices, config examples, rationale, and relevant RFCs.
    Use when building golden config templates, compliance rules, or hardening recommendations.

    feature: Specific feature to look up. If omitted, returns summary of all features.
    Available features: aaa, ntp, logging, snmp, ssh, vty_lines, spanning_tree, vtp,
    interfaces_l2_access, interfaces_l2_trunk, management_plane, dhcp_snooping, control_plane_policing
    """
    if feature:
        ref = get_reference(feature)
        if not ref:
            available = get_all_features()
            return json.dumps(
                {"error": f"Feature '{feature}' not found. Available: {available}"}
            )
        return json.dumps(ref, indent=2)
    else:
        return json.dumps({"features": get_summary()}, indent=2)


@mcp.tool()
async def golden_config_get_template(
    template_path: Optional[str] = None,
) -> str:
    """Get a golden config Jinja template scaffolding file for review or customization.

    These are starting-point templates based on Cisco IOS-XE best practices.
    Use during golden config bootstrap to present templates to the user for review and modification.

    template_path: Relative path within the cisco_xe template tree (e.g., 'management/ntp.j2').
    If omitted, returns the directory listing of all available templates.
    """
    import pathlib
    base = pathlib.Path(__file__).parent / "references" / "templates" / "cisco_xe"

    if not template_path:
        # Return directory listing
        templates = []
        for f in sorted(base.rglob("*.j2")):
            templates.append(str(f.relative_to(base)))
        return json.dumps({"templates": templates}, indent=2)

    target = base / template_path
    if not target.exists():
        return json.dumps({"error": f"Template '{template_path}' not found.", "available": [str(f.relative_to(base)) for f in sorted(base.rglob('*.j2'))]})
    return json.dumps({"path": template_path, "content": target.read_text()}, indent=2)


# ═══════════════════════════════════════════════════════════════════════
# PLUGIN TOOLS — Golden Config, Firewall Models, BGP/IGP Models
# ═══════════════════════════════════════════════════════════════════════


# ── Golden Config Plugin ─────────────────────────────────────────────


@mcp.tool()
async def nautobot_get_golden_configs(
    device: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query golden config records — backup, intended, and compliance configs per device."""
    logger.info(f"nautobot_get_golden_configs device={device}")
    filt = _gql_filters(device=device, limit=limit, offset=offset)
    query = f"""{{
  golden_configs{filt} {{
    device {{ name }}
    backup_config
    backup_last_success_date
    intended_config
    intended_last_success_date
    compliance_config
    compliance_last_success_date
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    configs = data.get("golden_configs", [])
    return json.dumps({"count": len(configs), "golden_configs": configs}, indent=2)


@mcp.tool()
async def nautobot_get_config_compliance(
    device: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query config compliance status per device and feature. Shows compliant/non-compliant with actual vs intended diffs."""
    logger.info(f"nautobot_get_config_compliance device={device}")
    filt = _gql_filters(device=device, limit=limit, offset=offset)
    query = f"""{{
  config_compliances{filt} {{
    device {{ name }}
    rule {{ feature {{ name }} platform {{ name }} config_type match_config }}
    compliance
    actual
    intended
    missing
    extra
    remediation
    ordered
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    records = data.get("config_compliances", [])
    return json.dumps({"count": len(records), "config_compliances": records}, indent=2)


@mcp.tool()
async def nautobot_get_compliance_rules(
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query compliance features and rules. Shows what config sections are being checked and the match patterns."""
    logger.info("nautobot_get_compliance_rules")
    try:
        feat_data = await client.graphql(
            f'{{ compliance_features(limit: {limit}, offset: {offset}) {{ id name slug description }} }}'
        )
        rule_data = await client.graphql(
            f'{{ compliance_rules(limit: {limit}, offset: {offset}) {{ feature {{ name }} platform {{ name }} config_ordered config_remediation match_config config_type custom_compliance description }} }}'
        )
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    features = feat_data.get("compliance_features", [])
    rules = rule_data.get("compliance_rules", [])
    return json.dumps(
        {"features_count": len(features), "features": features,
         "rules_count": len(rules), "rules": rules},
        indent=2,
    )


@mcp.tool()
async def nautobot_get_golden_config_settings() -> str:
    """Query golden config settings — repos, path templates, SoT query, and dynamic group scope."""
    logger.info("nautobot_get_golden_config_settings")
    try:
        data = await client.rest_get("plugins/golden-config/golden-config-settings")
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    results = data.get("results", [])
    return json.dumps({"count": len(results), "settings": results}, indent=2)


@mcp.tool()
async def nautobot_get_git_repositories() -> str:
    """Query Nautobot git repositories — used for golden config templates, backups, and intended configs."""
    logger.info("nautobot_get_git_repositories")
    try:
        data = await client.rest_get("extras/git-repositories")
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    results = data.get("results", [])
    return json.dumps({"count": len(results), "repositories": results}, indent=2)


@mcp.tool()
async def nautobot_get_graphql_queries() -> str:
    """Query saved GraphQL queries in Nautobot — used as SoT aggregation queries for golden config."""
    logger.info("nautobot_get_graphql_queries")
    try:
        data = await client.rest_get("extras/graphql-queries")
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    results = data.get("results", [])
    return json.dumps({"count": len(results), "queries": results}, indent=2)


@mcp.tool()
async def nautobot_create_compliance_feature(
    name: str,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create a compliance feature (e.g., 'aaa', 'ntp', 'logging', 'snmp', 'acl'). ITSM-gated."""
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})
    logger.info(f"nautobot_create_compliance_feature name={name} cr={cr_number}")
    try:
        payload: dict = {"name": name, "slug": slug or name.lower().replace(" ", "_")}
        if description:
            payload["description"] = description
        result = await client.rest_post("plugins/golden-config/compliance-feature", payload)
        return json.dumps({"created": True, "compliance_feature": result}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_create_compliance_rule(
    feature: str,
    platform: str,
    match_config: str,
    config_type: str = "cli",
    config_ordered: bool = False,
    config_remediation: bool = False,
    description: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create a compliance rule linking a feature to a platform with a config match pattern. ITSM-gated.

    feature: Compliance feature name (e.g., 'aaa')
    platform: Platform name (e.g., 'cisco_ios')
    match_config: Config line(s) to match for this feature (regex or literal)
    config_type: 'cli' (default) or 'json'
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})
    logger.info(f"nautobot_create_compliance_rule feature={feature} platform={platform} cr={cr_number}")
    try:
        # Resolve feature and platform to UUIDs
        feat_data = await client.graphql(
            f'{{ compliance_features(name: "{_esc(feature)}") {{ id }} }}'
        )
        feats = feat_data.get("compliance_features", [])
        if not feats:
            return json.dumps({"error": f"Compliance feature '{feature}' not found. Create it first."})
        feat_id = feats[0]["id"]

        plat_id = await client.resolve_id("platform", platform)

        payload: dict = {
            "feature": feat_id,
            "platform": plat_id,
            "match_config": match_config,
            "config_type": config_type,
            "config_ordered": config_ordered,
            "config_remediation": config_remediation,
        }
        if description:
            payload["description"] = description
        result = await client.rest_post("plugins/golden-config/compliance-rule", payload)
        return json.dumps({"created": True, "compliance_rule": result}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_create_git_repository(
    name: str,
    remote_url: str,
    provided_contents: str,
    branch: str = "main",
    cr_number: Optional[str] = None,
) -> str:
    """Register a git repository in Nautobot for golden config templates, backups, or intended configs. ITSM-gated.

    provided_contents: comma-separated content types. Valid values:
      nautobot_golden_config.jinjatemplate — Jinja templates for intended config generation
      nautobot_golden_config.intendedconfigs — Intended config storage
      nautobot_golden_config.backupconfigs — Backup config storage
      extras.configcontext — Config contexts
      extras.job — Jobs
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})
    logger.info(f"nautobot_create_git_repository name={name} url={remote_url} cr={cr_number}")
    try:
        contents = [c.strip() for c in provided_contents.split(",")]
        payload: dict = {
            "name": name,
            "remote_url": remote_url,
            "branch": branch,
            "provided_contents": contents,
        }
        result = await client.rest_post("extras/git-repositories", payload)
        return json.dumps({"created": True, "repository": result}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_create_graphql_query(
    name: str,
    query: str,
    cr_number: Optional[str] = None,
) -> str:
    """Create a saved GraphQL query in Nautobot — used as SoT aggregation query for golden config. ITSM-gated.

    The query should return device data needed by Jinja templates (hostname, interfaces, VLANs, IPs, etc.).
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})
    logger.info(f"nautobot_create_graphql_query name={name} cr={cr_number}")
    try:
        payload: dict = {"name": name, "query": query}
        result = await client.rest_post("extras/graphql-queries", payload)
        return json.dumps({"created": True, "graphql_query": result}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_update_golden_config_setting(
    setting_id: str,
    updates: str,
    cr_number: Optional[str] = None,
) -> str:
    """Update a golden config setting — link repos, set path templates, assign SoT query. ITSM-gated.

    setting_id: UUID of the golden config setting (get from nautobot_get_golden_config_settings)
    updates: JSON string of fields to update. Common fields:
      backup_repository: UUID of git repo for backups
      intended_repository: UUID of git repo for intended configs
      jinja_repository: UUID of git repo for Jinja templates
      backup_path_template: Jinja path template (e.g., '{{obj.location.name}}/{{obj.name}}.cfg')
      intended_path_template: Jinja path template for intended configs
      jinja_path_template: Jinja path template for templates (e.g., '{{obj.platform.network_driver}}/main.j2')
      sot_agg_query: UUID of saved GraphQL query for SoT aggregation
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})
    logger.info(f"nautobot_update_golden_config_setting id={setting_id} cr={cr_number}")
    try:
        update_dict = json.loads(updates)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid updates JSON: {e}"})
    try:
        old = await client.rest_get(f"plugins/golden-config/golden-config-settings/{setting_id}")
        result = await client.rest_patch(
            f"plugins/golden-config/golden-config-settings/{setting_id}", update_dict
        )
        changes = {}
        for k in update_dict:
            if old.get(k) != result.get(k):
                changes[k] = {"old": old.get(k), "new": result.get(k)}
        return json.dumps({"updated": True, "changes": changes}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


# ── Job Management (trigger and monitor Nautobot jobs) ─────────────


@mcp.tool()
async def nautobot_run_job(
    job_id: str,
    data: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Trigger a Nautobot job by its UUID. ITSM-gated.

    job_id: UUID of the job (get from nautobot_list_jobs)
    data: Optional JSON string of job input data (e.g., '{"device": ["uuid1"]}')
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})
    logger.info(f"nautobot_run_job job_id={job_id} cr={cr_number}")
    try:
        payload: dict = {"data": json.loads(data) if data else {}}
        result = await client.rest_post(f"extras/jobs/{job_id}/run", payload)
        return json.dumps({"triggered": True, "job_result": result}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_get_job_result(job_result_id: str) -> str:
    """Check the status and result of a Nautobot job run.

    job_result_id: UUID of the job result (returned by nautobot_run_job)
    """
    logger.info(f"nautobot_get_job_result id={job_result_id}")
    try:
        result = await client.rest_get(f"extras/job-results/{job_result_id}")
        summary = {
            "id": result.get("id"),
            "status": result.get("status", {}).get("value") if isinstance(result.get("status"), dict) else result.get("status"),
            "name": result.get("name"),
            "completed": result.get("date_done"),
            "result": result.get("result"),
        }
        return json.dumps(summary, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_list_jobs(
    q: Optional[str] = None,
    limit: int = 50,
) -> str:
    """List available Nautobot jobs. Use q to search by name (e.g., 'intended', 'backup', 'compliance')."""
    logger.info(f"nautobot_list_jobs q={q}")
    try:
        params = {"limit": limit}
        if q:
            params["q"] = q
        data = await client.rest_get("extras/jobs", params)
        results = data.get("results", [])
        jobs = [{"id": j["id"], "name": j.get("name"), "enabled": j.get("enabled")} for j in results]
        return json.dumps({"count": len(jobs), "jobs": jobs}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_enable_job(
    job_id: Optional[str] = None,
    enable_all: bool = False,
    enabled: bool = True,
) -> str:
    """Enable or disable Nautobot jobs.

    job_id: UUID of a single job to enable/disable (get from nautobot_list_jobs)
    enable_all: If True, enables ALL disabled jobs in one call. Ignores job_id.
    enabled: True to enable, False to disable (default: True)
    """
    logger.info(f"nautobot_enable_job id={job_id} enable_all={enable_all} enabled={enabled}")
    try:
        if enable_all:
            data = await client.rest_get("extras/jobs", {"limit": 200})
            results = data.get("results", [])
            disabled = [j for j in results if not j.get("enabled")]
            if not disabled:
                return json.dumps({"message": "All jobs already enabled", "count": 0})
            updated = []
            errors = []
            for job in disabled:
                try:
                    r = await client.rest_patch(f"extras/jobs/{job['id']}", {"enabled": enabled})
                    updated.append({"id": r.get("id"), "name": r.get("name")})
                except NautobotError as e:
                    errors.append({"id": job["id"], "name": job.get("name"), "error": str(e)})
            return json.dumps({
                "updated": True,
                "enabled_count": len(updated),
                "jobs": updated,
                "errors": errors if errors else None,
            }, indent=2)
        elif job_id:
            result = await client.rest_patch(f"extras/jobs/{job_id}", {"enabled": enabled})
            return json.dumps({
                "updated": True,
                "job": {"id": result.get("id"), "name": result.get("name"), "enabled": result.get("enabled")},
            }, indent=2)
        else:
            return json.dumps({"error": "Provide job_id or set enable_all=True"})
    except NautobotError as e:
        return json.dumps({"error": str(e)})


# ── Git Repository Sync ───────────────────────────────────────


@mcp.tool()
async def nautobot_sync_git_repository(
    repository_id: str,
    cr_number: Optional[str] = None,
) -> str:
    """Trigger a git repository sync in Nautobot. ITSM-gated.

    repository_id: UUID of the git repository (get from nautobot_get_git_repositories)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})
    logger.info(f"nautobot_sync_git_repository id={repository_id} cr={cr_number}")
    try:
        result = await client.rest_post(f"extras/git-repositories/{repository_id}/sync", {})
        return json.dumps({"synced": True, "result": result}, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_update_git_repository(
    repository_id: str,
    updates: str,
    cr_number: Optional[str] = None,
) -> str:
    """Update a git repository in Nautobot. ITSM-gated.

    repository_id: UUID of the git repository (get from nautobot_get_git_repositories)
    updates: JSON string of fields to update. Common fields:
      secrets_group: UUID of secrets group for authentication
      remote_url: Git remote URL
      branch: Branch name
      provided_contents: List of content types
      name: Display name
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})
    logger.info(f"nautobot_update_git_repository id={repository_id} cr={cr_number}")
    try:
        update_dict = json.loads(updates)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid updates JSON: {e}"})
    try:
        old = await client.rest_get(f"extras/git-repositories/{repository_id}")
        result = await client.rest_patch(f"extras/git-repositories/{repository_id}", update_dict)
        changes = {}
        for k in update_dict:
            if old.get(k) != result.get(k):
                changes[k] = {"old": old.get(k), "new": result.get(k)}
        return json.dumps({"updated": True, "changes": changes}, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


# ── Config Contexts ──────────────────────────────────────────


@mcp.tool()
async def nautobot_get_config_contexts(
    name: Optional[str] = None,
    limit: int = 50,
) -> str:
    """Query config contexts from Nautobot. Returns name, data, and role/location/platform assignments."""
    logger.info(f"nautobot_get_config_contexts name={name}")
    try:
        params: dict = {"limit": limit}
        if name:
            params["name"] = name
        data = await client.rest_get("extras/config-contexts", params)
        results = data.get("results", [])
        contexts = []
        for ctx in results:
            contexts.append({
                "id": ctx["id"],
                "name": ctx.get("name"),
                "roles": [r.get("name") or r.get("display") for r in ctx.get("roles", [])],
                "locations": [l.get("name") or l.get("display") for l in ctx.get("locations", [])],
                "platforms": [p.get("name") or p.get("display") for p in ctx.get("platforms", [])],
                "data_keys": list(ctx.get("data", {}).keys()) if ctx.get("data") else [],
            })
        return json.dumps({"count": len(contexts), "config_contexts": contexts}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_get_config_context_detail(config_context_id: str) -> str:
    """Get full detail of a config context including its data payload."""
    logger.info(f"nautobot_get_config_context_detail id={config_context_id}")
    try:
        result = await client.rest_get(f"extras/config-contexts/{config_context_id}")
        return json.dumps(result, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_create_config_context(
    name: str,
    data: str,
    roles: Optional[str] = None,
    locations: Optional[str] = None,
    platforms: Optional[str] = None,
    description: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create a config context in Nautobot. ITSM-gated.

    name: Display name
    data: JSON string of the config context data payload
    roles: Optional comma-separated role names to scope the context to
    locations: Optional comma-separated location names
    platforms: Optional comma-separated platform names
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})
    logger.info(f"nautobot_create_config_context name={name} cr={cr_number}")
    try:
        ctx_data = json.loads(data)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid data JSON: {e}"})
    try:
        payload: dict = {"name": name, "data": ctx_data}
        if description:
            payload["description"] = description
        if roles:
            role_ids = []
            for r in roles.split(","):
                role_ids.append(await client.resolve_id("role", r.strip()))
            payload["roles"] = role_ids
        if locations:
            loc_ids = []
            for l in locations.split(","):
                loc_ids.append(await client.resolve_id("location", l.strip()))
            payload["locations"] = loc_ids
        if platforms:
            plat_ids = []
            for p in platforms.split(","):
                plat_ids.append(await client.resolve_id("platform", p.strip()))
            payload["platforms"] = plat_ids
        result = await client.rest_post("extras/config-contexts", payload)
        return json.dumps({"created": True, "config_context": result}, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_update_config_context(
    config_context_id: str,
    updates: str,
    cr_number: Optional[str] = None,
) -> str:
    """Update a config context in Nautobot. ITSM-gated.

    config_context_id: UUID of the config context
    updates: JSON string of fields to update. Common fields: data, roles, locations, platforms, name, description
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})
    logger.info(f"nautobot_update_config_context id={config_context_id} cr={cr_number}")
    try:
        update_dict = json.loads(updates)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid updates JSON: {e}"})
    try:
        result = await client.rest_patch(f"extras/config-contexts/{config_context_id}", update_dict)
        return json.dumps({"updated": True, "config_context": result}, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


# ── Dynamic Groups ───────────────────────────────────────────


@mcp.tool()
async def nautobot_get_dynamic_group_members(
    dynamic_group_id: str,
) -> str:
    """Get the members of a Nautobot dynamic group. Returns the list of devices that match the group's filter."""
    logger.info(f"nautobot_get_dynamic_group_members id={dynamic_group_id}")
    try:
        data = await client.rest_get(f"extras/dynamic-groups/{dynamic_group_id}/members")
        results = data.get("results", []) if isinstance(data, dict) else data
        members = [{"name": m.get("name"), "id": m.get("id")} for m in results if isinstance(m, dict)]
        return json.dumps({"count": len(members), "members": members}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


# ── Secrets Management (for Git Repository auth) ────────────────────


@mcp.tool()
async def nautobot_create_secret(
    name: str,
    provider: str,
    parameters: str,
    description: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create a secret in Nautobot. Used to store credentials for git repo access. ITSM-gated.

    name: Display name (e.g., 'GitHub Token')
    provider: Secret provider type. Common values:
      environment-variable — reads from a Nautobot server env var
      text-file — reads from a file on the Nautobot server
    parameters: JSON string of provider-specific parameters.
      For environment-variable: {"variable": "NAUTOBOT_GIT_TOKEN"}
      For text-file: {"path": "/opt/nautobot/secrets/github-token"}
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})
    logger.info(f"nautobot_create_secret name={name} provider={provider} cr={cr_number}")
    try:
        params = json.loads(parameters)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid parameters JSON: {e}"})
    try:
        payload: dict = {"name": name, "provider": provider, "parameters": params}
        if description:
            payload["description"] = description
        result = await client.rest_post("extras/secrets", payload)
        return json.dumps({"created": True, "secret": result}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_create_secrets_group(
    name: str,
    description: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create a secrets group in Nautobot. Secrets groups bundle secrets for use with git repos. ITSM-gated."""
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})
    logger.info(f"nautobot_create_secrets_group name={name} cr={cr_number}")
    try:
        payload: dict = {"name": name}
        if description:
            payload["description"] = description
        result = await client.rest_post("extras/secrets-groups", payload)
        return json.dumps({"created": True, "secrets_group": result}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_add_secret_to_group(
    secrets_group_id: str,
    secret_id: str,
    access_type: str,
    secret_type: str,
    cr_number: Optional[str] = None,
) -> str:
    """Associate a secret with a secrets group. ITSM-gated.

    secrets_group_id: UUID of the secrets group
    secret_id: UUID of the secret
    access_type: How the secret is accessed. Values: 'HTTP(S)', 'SSH', 'SNMP', 'REST', 'Generic'
    secret_type: What the secret represents. Values: 'token', 'username', 'password', 'key', 'secret'
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})
    logger.info(f"nautobot_add_secret_to_group group={secrets_group_id} secret={secret_id} cr={cr_number}")
    try:
        payload: dict = {
            "secrets_group": secrets_group_id,
            "secret": secret_id,
            "access_type": access_type,
            "secret_type": secret_type,
        }
        result = await client.rest_post("extras/secrets-groups-associations", payload)
        return json.dumps({"created": True, "association": result}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


# ── Firewall Models Plugin ───────────────────────────────────────────


@mcp.tool()
async def nautobot_get_firewall_policies(
    device: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query firewall policies with rules, zones, address objects, and device assignments."""
    logger.info(f"nautobot_get_firewall_policies device={device}")
    filt = _gql_filters(limit=limit, offset=offset)
    query = f"""{{
  policies{filt} {{
    name status {{ name }} description tenant {{ name }}
    assigned_devices {{ name }}
    policy_rules {{
      name index action log description
      source_zone {{ name }}
      destination_zone {{ name }}
      source_addresses {{ name ip_address {{ address }} prefix {{ prefix }} fqdn {{ name }} }}
      source_address_groups {{ name }}
      destination_addresses {{ name ip_address {{ address }} prefix {{ prefix }} fqdn {{ name }} }}
      destination_address_groups {{ name }}
      source_services {{ name port ip_protocol }}
      destination_services {{ name port ip_protocol }}
    }}
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    policies = data.get("policies", [])
    # Filter by device if requested
    if device:
        policies = [
            p for p in policies
            if any(d.get("name") == device for d in p.get("assigned_devices", []))
        ]
    return json.dumps({"count": len(policies), "policies": policies}, indent=2)


@mcp.tool()
async def nautobot_get_firewall_zones(
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query firewall zones with associated VRFs and interfaces."""
    logger.info("nautobot_get_firewall_zones")
    filt = _gql_filters(limit=limit, offset=offset)
    query = f"""{{
  zones{filt} {{
    name status {{ name }} description
    vrfs {{ name }}
    interfaces {{ name device {{ name }} }}
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    zones = data.get("zones", [])
    return json.dumps({"count": len(zones), "zones": zones}, indent=2)


@mcp.tool()
async def nautobot_get_nat_policies(
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query NAT policies with rules, original/translated addresses, and device assignments."""
    logger.info("nautobot_get_nat_policies")
    filt = _gql_filters(limit=limit, offset=offset)
    query = f"""{{
  nat_policies{filt} {{
    name status {{ name }} description tenant {{ name }}
    nat_policy_rules {{
      name index log
      original_source_addresses {{ name }}
      original_destination_addresses {{ name }}
      translated_source_addresses {{ name }}
      translated_destination_addresses {{ name }}
      source_zone {{ name }}
      destination_zone {{ name }}
    }}
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    policies = data.get("nat_policies", [])
    return json.dumps({"count": len(policies), "nat_policies": policies}, indent=2)


# ── BGP Models Plugin ────────────────────────────────────────────────


@mcp.tool()
async def nautobot_get_bgp_routing(
    device: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query BGP routing instances, peer groups, peer endpoints, and autonomous systems."""
    logger.info(f"nautobot_get_bgp_routing device={device}")
    filt = _gql_filters(limit=limit, offset=offset)
    query = f"""{{
  bgp_routing_instances{filt} {{
    device {{ name }}
    router_id {{ address }}
    autonomous_system {{ asn description }}
    status {{ name }}
    description
    peer_groups {{
      name enabled description
      autonomous_system {{ asn }}
      source_ip {{ address }}
      source_interface {{ name }}
    }}
    endpoints {{
      enabled description
      autonomous_system {{ asn }}
      source_ip {{ address }}
      source_interface {{ name }}
      peer {{ source_ip {{ address }} }}
      peer_group {{ name }}
      role {{ name }}
    }}
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    instances = data.get("bgp_routing_instances", [])
    if device:
        instances = [i for i in instances if i.get("device", {}).get("name") == device]
    return json.dumps({"count": len(instances), "bgp_routing_instances": instances}, indent=2)


@mcp.tool()
async def nautobot_get_autonomous_systems(
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query autonomous systems registered in Nautobot BGP models."""
    logger.info("nautobot_get_autonomous_systems")
    filt = _gql_filters(limit=limit, offset=offset)
    query = f"""{{
  autonomous_systems{filt} {{
    asn description status {{ name }}
    provider {{ name }}
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    systems = data.get("autonomous_systems", [])
    return json.dumps({"count": len(systems), "autonomous_systems": systems}, indent=2)


# ── IGP Models Plugin ────────────────────────────────────────────────


@mcp.tool()
async def nautobot_get_ospf_routing(
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query OSPF configurations and interface configurations from the IGP models plugin."""
    logger.info("nautobot_get_ospf_routing")
    filt = _gql_filters(limit=limit, offset=offset)
    query = f"""{{
  ospf_configurations{filt} {{
    name instance {{ device {{ name }} }} process_id status {{ name }}
    default_cost default_hello_interval default_dead_interval
  }}
  ospf_interface_configurations{filt} {{
    name
    interface {{ name device {{ name }} }}
    ospf_config {{ name }}
    area cost status {{ name }}
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    return json.dumps({
        "ospf_configs": data.get("ospf_configurations", []),
        "ospf_interface_configs": data.get("ospf_interface_configurations", []),
    }, indent=2)


# ── Virtualization ────────────────────────────────────────────────────


@mcp.tool()
async def nautobot_get_virtual_machines(
    name: Optional[str] = None,
    cluster: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query virtual machines from Nautobot. Returns name, cluster, role, status, primary IP, vCPUs, memory, disk."""
    logger.info(f"nautobot_get_virtual_machines name={name} cluster={cluster}")
    filt = _gql_filters(
        name=name, cluster=cluster, role=role, status=status,
        limit=limit, offset=offset,
    )
    query = f"""{{
  virtual_machines{filt} {{
    id name status {{ name }} role {{ name }} cluster {{ name }}
    vcpus memory disk comments
    primary_ip4 {{ address }}
    interfaces {{ name enabled mac_address ip_addresses {{ address }} }}
  }}
}}"""
    try:
        data = await client.graphql(query)
    except NautobotError as e:
        return json.dumps({"error": str(e)})
    vms = data.get("virtual_machines", [])
    return json.dumps({"count": len(vms), "virtual_machines": vms}, indent=2)


@mcp.tool()
async def nautobot_create_virtual_machine(
    name: str,
    cluster: str,
    role: Optional[str] = None,
    status: str = "Active",
    vcpus: Optional[int] = None,
    memory: Optional[int] = None,
    disk: Optional[int] = None,
    comments: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create a virtual machine in Nautobot. ITSM-gated.

    Args:
        name: VM name (e.g., "otel-collector")
        cluster: Cluster name the VM belongs to (e.g., "Observability")
        role: Device role (e.g., "Monitoring")
        status: Status name (default: Active)
        vcpus: Number of virtual CPUs
        memory: Memory in MB
        disk: Disk in GB
        comments: Free-text description
        cr_number: ServiceNow change request number (required if ITSM enabled)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"nautobot_create_virtual_machine {name} cluster={cluster} cr={cr_number}")
    try:
        status_id = await client.resolve_id("status", status)
        cluster_id = await client.resolve_id("cluster", cluster)

        payload: dict = {
            "name": name,
            "status": status_id,
            "cluster": cluster_id,
        }
        if role:
            payload["role"] = await client.resolve_id("role", role)
        if vcpus:
            payload["vcpus"] = vcpus
        if memory:
            payload["memory"] = memory
        if disk:
            payload["disk"] = disk
        if comments:
            payload["comments"] = comments

        result = await client.rest_post("virtualization/virtual-machines", payload)
        return json.dumps({"created": True, "virtual_machine": result}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_create_vm_interface(
    virtual_machine: str,
    name: str,
    enabled: bool = True,
    description: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create a network interface on a virtual machine. ITSM-gated.

    Args:
        virtual_machine: VM name (e.g., "otel-collector")
        name: Interface name (e.g., "eth0")
        enabled: Whether the interface is enabled
        description: Interface description
        cr_number: ServiceNow change request number
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"nautobot_create_vm_interface {virtual_machine}:{name} cr={cr_number}")
    try:
        vm_id = await client.resolve_id("virtual_machine", virtual_machine)

        payload: dict = {
            "virtual_machine": vm_id,
            "name": name,
            "enabled": enabled,
        }
        if description:
            payload["description"] = description

        result = await client.rest_post("virtualization/interfaces", payload)
        return json.dumps({"created": True, "vm_interface": result}, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def nautobot_assign_ip_to_vm(
    virtual_machine: str,
    interface: str,
    address: str,
    status: str = "Active",
    namespace: str = "Global",
    set_primary: bool = True,
    cr_number: Optional[str] = None,
) -> str:
    """Create an IP address and assign it to a VM interface. Optionally set as primary. ITSM-gated.

    Args:
        virtual_machine: VM name
        interface: VM interface name (e.g., "eth0")
        address: IP address in CIDR notation (e.g., "192.168.220.200/24")
        status: IP status (default: Active)
        namespace: IPAM namespace (default: Global)
        set_primary: Set as the VM's primary IPv4 address
        cr_number: ServiceNow change request number
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"nautobot_assign_ip_to_vm {virtual_machine}:{interface} {address} cr={cr_number}")
    try:
        status_id = await client.resolve_id("status", status)
        ns_id = await client.resolve_id("namespace", namespace)

        # Create the IP address
        ip_payload: dict = {
            "address": address,
            "status": status_id,
            "namespace": ns_id,
        }
        ip_result = await client.rest_post("ipam/ip-addresses", ip_payload)
        ip_id = ip_result["id"]

        # Resolve VM interface
        # Query for the VM interface by VM name + interface name
        query = f"""{{ vm_interfaces(virtual_machine: "{_esc(virtual_machine)}", name: "{_esc(interface)}") {{ id }} }}"""
        data = await client.graphql(query)
        ifaces = data.get("vm_interfaces", [])
        if not ifaces:
            return json.dumps({"error": f"VM interface {virtual_machine}:{interface} not found"})
        iface_id = ifaces[0]["id"]

        # Assign IP to VM interface
        await client.rest_post(
            "ipam/ip-address-to-interface",
            {"ip_address": ip_id, "vm_interface": iface_id},
        )

        # Set as primary IP if requested
        if set_primary:
            vm_query = f"""{{ virtual_machines(name: "{_esc(virtual_machine)}") {{ id }} }}"""
            vm_data = await client.graphql(vm_query)
            vms = vm_data.get("virtual_machines", [])
            if vms:
                await client.rest_patch(
                    f"virtualization/virtual-machines/{vms[0]['id']}",
                    {"primary_ip4": ip_id},
                )

        return json.dumps({
            "created": True,
            "ip_address": address,
            "assigned_to": f"{virtual_machine}:{interface}",
            "primary": set_primary,
        }, indent=2)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    mcp.run(transport="stdio")
