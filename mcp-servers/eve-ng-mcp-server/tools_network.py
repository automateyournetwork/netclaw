"""Network / topology (7) + node-types (1) = 8 MCP tools."""

from mcp_init import mcp
from eve_client import (
    get_client, EVEError, handle_eve_response, success_response, error_response,
    with_gait_logging, paginate_sequence,
    normalize_lab_path, resolve_node_id, resolve_network_id,
    ensure_nodes_stopped_for_link_edit,
)


@mcp.tool()
@with_gait_logging("eve_get_topology")
def eve_get_topology(lab_path: str) -> str:
    """
    Get full lab topology: nodes, networks, and all interconnection links.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
    """
    try:
        data = handle_eve_response(get_client().get(f"/api/labs{normalize_lab_path(lab_path)}/topology"))
        return success_response(data)
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_list_networks")
def eve_list_networks(lab_path: str, page: int = 1, page_size: int = 50) -> str:
    """
    List all virtual networks (bridges, clouds, physical interfaces) in a lab.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        page: 1-based page number for pagination.
        page_size: Number of records per page (max capped by server setting).
    """
    try:
        data = handle_eve_response(get_client().get(f"/api/labs{normalize_lab_path(lab_path)}/networks"))
        if not isinstance(data, dict):
            return success_response([], "No networks found", 0, total_count=0,
                                    pagination={"page": 1, "page_size": page_size, "returned": 0,
                                                "total_count": 0, "total_pages": 1, "has_next": False})
        networks = [{"id": nid, **net} for nid, net in data.items() if isinstance(net, dict)]
        networks = sorted(networks, key=lambda net: (str(net.get("name") or ""), str(net.get("id") or "")))
        paged, meta = paginate_sequence(networks, page, page_size)
        return success_response(
            paged,
            f"Found {meta['total_count']} networks",
            len(paged),
            total_count=meta["total_count"],
            pagination=meta,
        )
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_create_network")
def eve_create_network(
    lab_path: str,
    name: str,
    network_type: str = "bridge",
    visibility: int = 1,
    left: int = 200,
    top: int = 200,
) -> str:
    """
    Create a virtual network in a lab.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        name: Network name (e.g. 'Net1', 'Management', 'WAN')
        network_type: 'bridge' (internal L2), 'ovs', 'pnet0'-'pnet9' (physical uplink),
                      'cloud0'-'cloud9' (cloud/internet bridge)
        visibility: 1 = visible on canvas, 0 = hidden
        left: Canvas X position
        top: Canvas Y position
    """
    try:
        c = get_client()
        payload = {"name": name, "type": network_type, "visibility": visibility,
                   "left": left, "top": top}
        data = handle_eve_response(
            c.post(f"/api/labs{normalize_lab_path(lab_path)}/networks", json=payload),
            success_codes=[200, 201],
        )
        networks = handle_eve_response(c.get(f"/api/labs{normalize_lab_path(lab_path)}/networks"))
        created_id = None
        if isinstance(networks, dict):
            for nid, net in networks.items():
                if isinstance(net, dict) and net.get("name", "").lower() == name.lower():
                    created_id = str(nid)
                    break
        if not created_id:
            raise EVEError(
                "EVE_SERVER_ERROR",
                f"Network '{name}' creation was acknowledged but did not persist in lab topology",
                500,
            )
        return success_response({
            "network_id": created_id,
            "name": name,
            "network_type": network_type,
            "visibility": visibility,
            "left": left,
            "top": top,
            "api_result": data,
        }, f"Network '{name}' created")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_delete_network")
def eve_delete_network(lab_path: str, network: str) -> str:
    """
    Delete a network from a lab. Disconnect all nodes before deleting.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        network: Network name or numeric ID
    """
    try:
        c = get_client()
        net_id = resolve_network_id(c, lab_path, network)
        handle_eve_response(c.delete(f"/api/labs{normalize_lab_path(lab_path)}/networks/{net_id}"),
                            success_codes=[200, 204])
        return success_response(message=f"Network '{network}' deleted")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_list_node_interfaces")
def eve_list_node_interfaces(lab_path: str, node: str) -> str:
    """
    List all interfaces of a node and their current network connections.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name or numeric ID
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        data = handle_eve_response(
            c.get(f"/api/labs{normalize_lab_path(lab_path)}/nodes/{node_id}/interfaces"))
        return success_response(data)
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_connect_interface")
def eve_connect_interface(
    lab_path: str,
    node: str,
    interface_id: int,
    network: str,
) -> str:
    """
    Connect a node interface to a network.
    Stop the node before rewiring to avoid runtime bridge conflicts.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name or numeric ID
        interface_id: Interface index — 0 = first (Ethernet0/0), 1 = second, etc.
        network: Target network name or numeric ID
    """
    try:
        c = get_client()
        ensure_nodes_stopped_for_link_edit(c, lab_path, [node])
        node_id = resolve_node_id(c, lab_path, node)
        net_id = resolve_network_id(c, lab_path, network)
        handle_eve_response(
            c.put(f"/api/labs{normalize_lab_path(lab_path)}/nodes/{node_id}/interfaces",
                  json={str(interface_id): int(net_id)}))
        interfaces = handle_eve_response(
            c.get(f"/api/labs{normalize_lab_path(lab_path)}/nodes/{node_id}/interfaces"))
        attached = None
        if isinstance(interfaces, dict):
            iface = interfaces.get(str(interface_id)) or interfaces.get(interface_id)
            if isinstance(iface, dict):
                attached = str(iface.get("network_id") or iface.get("network") or "")
            elif isinstance(interfaces.get("ethernet"), list) and 0 <= int(interface_id) < len(interfaces.get("ethernet")):
                eth = interfaces.get("ethernet")[int(interface_id)]
                if isinstance(eth, dict):
                    attached = str(eth.get("network_id") or eth.get("network") or "")
        if attached != str(net_id):
            raise EVEError(
                "EVE_SERVER_ERROR",
                f"Interface {interface_id} of '{node}' did not persist on network '{network}' after API success",
                500,
            )
        return success_response({
            "node": node, "node_id": node_id,
            "interface_id": interface_id,
            "network": network, "network_id": net_id,
        }, f"Interface {interface_id} of '{node}' connected to '{network}'")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_list_node_types")
def eve_list_node_types(page: int = 1, page_size: int = 50) -> str:
    """List available node types (templates) installed on the EVE-NG server."""
    try:
        data = handle_eve_response(get_client().get("/api/list/templates/"))
        if isinstance(data, dict):
            types = [{"type": k, **(v if isinstance(v, dict) else {"name": str(v)})}
                     for k, v in data.items()]
        else:
            types = data if isinstance(data, list) else []
        types = sorted(types, key=lambda item: str(item.get("name") or item.get("type") or item))
        paged, meta = paginate_sequence(types, page, page_size)
        return success_response(
            paged,
            f"Found {meta['total_count']} node types",
            len(paged),
            total_count=meta["total_count"],
            pagination=meta,
        )
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)
