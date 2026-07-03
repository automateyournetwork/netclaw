"""Node operation (9) MCP tools."""

import re
import time
from typing import Optional

from mcp_init import mcp
from eve_client import (
    get_client, EVEError, handle_eve_response, success_response, error_response,
    with_gait_logging, paginate_sequence,
    normalize_lab_path, resolve_node_id, node_is_running,
    poll_node_status, build_verification, correct_local_nodes_status, correct_local_node_status,
)
from tools_config import _set_config_in_unl, _reset_node_runtime_dir


IOS_ZERO_CONFIG_TYPES = {"iol", "dynamips"}
IOS_ZERO_CONFIG_TEMPLATES = (
    "iol", "vios", "csr", "csr1000v", "ios", "iosv", "xrv", "xrv9k", "c7200", "c3725", "c3640", "c2691"
)


def _is_ios_like_node(node_info: dict) -> bool:
    node_type = str(node_info.get("type", "")).lower()
    template = str(node_info.get("template", "")).lower()
    image = str(node_info.get("image", "")).lower()
    return (
        node_type in IOS_ZERO_CONFIG_TYPES
        or any(token in template for token in IOS_ZERO_CONFIG_TEMPLATES)
        or any(token in image for token in IOS_ZERO_CONFIG_TEMPLATES)
    )


def _has_zero_startup_config(node_info: dict) -> bool:
    mode = str(node_info.get("config", "0")).strip().lower()
    return mode in {"", "0", "false", "none", "null"}


def _minimal_ios_startup_config(name: str) -> str:
    hostname = re.sub(r"[^A-Za-z0-9_-]", "-", str(name or "Router")).strip("-") or "Router"
    return "\n".join([
        "!",
        f"hostname {hostname}",
        "no service config",
        "no ip domain lookup",
        "service timestamps debug datetime msec",
        "service timestamps log datetime msec",
        "line con 0",
        " logging synchronous",
        " exec-timeout 0 0",
        "line vty 0 4",
        " login",
        "end",
        "",
    ])


def _seed_zero_config_if_needed(c, lab_path: str, node_id: str, node_info: dict) -> dict | None:
    if not isinstance(node_info, dict):
        return None
    if node_is_running(node_info):
        return None
    if not _has_zero_startup_config(node_info):
        return None
    if not _is_ios_like_node(node_info):
        return None
    name = node_info.get("name", node_id)
    result = _set_config_in_unl(lab_path, node_id, _minimal_ios_startup_config(name))
    runtime = _reset_node_runtime_dir(lab_path, node_id)
    c.invalidate_cache()
    return {
        "node_id": str(node_id),
        "node_name": name,
        "reason": "startup-config mode was zero; seeded minimal IOS config to bypass setup dialog",
        "startup_config_mode": result.get("startup_config_mode"),
        "write_path": result.get("fallback", "local_unl"),
        "runtime": runtime,
    }


@mcp.tool()
@with_gait_logging("eve_list_nodes")
def eve_list_nodes(lab_path: str, page: int = 1, page_size: int = 50) -> str:
    """
    List all nodes in a lab with runtime status, type, image, and console port.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        page: 1-based page number for pagination.
        page_size: Number of records per page (max capped by server setting).
    """
    try:
        c = get_client()
        data = handle_eve_response(c.get(f"/api/labs{normalize_lab_path(lab_path)}/nodes", no_cache=True))
        if isinstance(data, dict):
            data = correct_local_nodes_status(c, lab_path, data)
        if not isinstance(data, dict):
            return success_response([], "No nodes found", 0, total_count=0,
                                    pagination={"page": 1, "page_size": page_size, "returned": 0,
                                                "total_count": 0, "total_pages": 1, "has_next": False})
        nodes = [
            {
                "id": nid,
                "name": n.get("name"),
                "type": n.get("type"),
                "template": n.get("template"),
                "image": n.get("image"),
                "status": n.get("status"),
                "running": node_is_running(n),
                "console_port": n.get("console"),
                "cpu": n.get("cpu"),
                "ram": n.get("ram"),
            }
            for nid, n in data.items() if isinstance(n, dict)
        ]
        nodes = sorted(nodes, key=lambda node: (str(node.get("name") or ""), str(node.get("id") or "")))
        paged, meta = paginate_sequence(nodes, page, page_size)
        return success_response(
            paged,
            f"Found {meta['total_count']} nodes",
            len(paged),
            total_count=meta["total_count"],
            pagination=meta,
        )
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_get_node")
def eve_get_node(lab_path: str, node: str) -> str:
    """
    Get full details for a single node (config, status, interfaces, console).

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name (e.g. 'R1') or numeric ID
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        data = handle_eve_response(c.get(f"/api/labs{normalize_lab_path(lab_path)}/nodes/{node_id}", no_cache=True))
        if isinstance(data, dict):
            data = correct_local_node_status(c, lab_path, node_id, data)
        return success_response(data)
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_create_node")
def eve_create_node(
    lab_path: str,
    name: str,
    node_type: str,
    template: str,
    image: str = "",
    left: int = 100,
    top: int = 100,
    ram: int = 256,
    ethernet: int = 4,
    serial: int = 0,
    console: str = "telnet",
    cpu: int = 1,
    icon: str = "Router.png",
    node_id: int | None = None,
) -> str:
    """
    Add a new node to a lab from a template.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        name: Node name (e.g. 'R1')
        node_type: Node type — 'iol', 'qemu', 'dynamips', 'docker', 'vpcs'
        template: Template name (e.g. 'vios', 'csr1000v', 'iol')
        image: Image filename — uses template default when blank
        left: Canvas X position (pixels)
        top: Canvas Y position (pixels)
        ram: RAM in MB
        ethernet: Number of Ethernet interfaces
        serial: Number of serial interfaces
        console: Console type — 'telnet' or 'vnc'
        cpu: Number of vCPUs
        icon: Canvas icon filename (e.g. 'Router.png', 'Switch.png', 'Server.png')
        node_id: Optional explicit node ID. Use lab-number block IDs on this host, e.g. 801, 802.
    """
    try:
        c = get_client()
        payload: dict = {
            "name": name, "type": node_type, "template": template,
            "left": left, "top": top, "ram": ram,
            "ethernet": ethernet, "serial": serial,
            "console": console, "cpu": cpu, "icon": icon,
        }
        if image:
            payload["image"] = image
        if node_id is not None:
            existing = handle_eve_response(c.get(f"/api/labs{normalize_lab_path(lab_path)}/nodes"))
            if isinstance(existing, dict) and str(node_id) in existing:
                raise EVEError(
                    "EVE_CONFLICT",
                    f"Node ID '{node_id}' already exists in lab '{lab_path}'",
                    409,
                )
            payload["id"] = int(node_id)
        data = handle_eve_response(
            c.post(f"/api/labs{normalize_lab_path(lab_path)}/nodes", json=payload),
            success_codes=[200, 201],
        )
        verify = handle_eve_response(c.get(f"/api/labs{normalize_lab_path(lab_path)}/nodes"))
        resolved_id = None
        if node_id is not None and isinstance(verify, dict) and str(node_id) in verify:
            resolved_id = str(node_id)
        elif isinstance(verify, dict):
            for nid, node in verify.items():
                if isinstance(node, dict) and node.get("name", "").lower() == name.lower():
                    resolved_id = str(nid)
                    break
        if node_id is not None and resolved_id != str(node_id):
            raise EVEError(
                "EVE_SERVER_ERROR",
                f"Node '{name}' was created but did not persist with requested ID '{node_id}'",
                500,
            )
        return success_response({
            "requested_id": node_id,
            "resolved_id": resolved_id,
            "api_result": data,
        }, f"Node '{name}' created")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_delete_node")
def eve_delete_node(lab_path: str, node: str) -> str:
    """
    Remove a node from a lab. Node must be stopped first.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name or numeric ID
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        handle_eve_response(c.delete(f"/api/labs{normalize_lab_path(lab_path)}/nodes/{node_id}"),
                            success_codes=[200, 204])
        return success_response({"node_id": node_id}, f"Node '{node}' deleted")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_start_node")
def eve_start_node(lab_path: str, node: str) -> str:
    """
    Start a node and poll to verify it reaches running state.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name (e.g. 'R1') or numeric ID
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        path = normalize_lab_path(lab_path)
        before = handle_eve_response(c.get(f"/api/labs{path}/nodes")) or {}
        node_info = before.get(str(node_id), {}) if isinstance(before, dict) else {}
        zero_config_seed = _seed_zero_config_if_needed(c, lab_path, str(node_id), node_info)
        if zero_config_seed:
            before = handle_eve_response(c.get(f"/api/labs{path}/nodes", no_cache=True)) or before
            node_info = before.get(str(node_id), node_info) if isinstance(before, dict) else node_info
        handle_eve_response(c.get(f"/api/labs{path}/nodes/{node_id}/start"))
        after = poll_node_status(c, lab_path, node_id, expect_running=True)
        return success_response({
            "node_id": node_id,
            "node_name": node_info.get("name", node) if isinstance(node_info, dict) else node,
            "zero_config_seed": zero_config_seed,
            "verification": build_verification("start", node_id, before, after),
        }, "Node started")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_stop_node")
def eve_stop_node(lab_path: str, node: str) -> str:
    """
    Stop a node and poll to verify it reaches stopped state.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name (e.g. 'R1') or numeric ID
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        path = normalize_lab_path(lab_path)
        before = handle_eve_response(c.get(f"/api/labs{path}/nodes")) or {}
        handle_eve_response(c.get(f"/api/labs{path}/nodes/{node_id}/stop"))
        after = poll_node_status(c, lab_path, node_id, expect_running=False)
        node_info = before.get(str(node_id), {})
        return success_response({
            "node_id": node_id,
            "node_name": node_info.get("name", node) if isinstance(node_info, dict) else node,
            "verification": build_verification("stop", node_id, before, after),
        }, "Node stopped")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_start_lab")
def eve_start_lab(lab_path: str) -> str:
    """
    Start all nodes in a lab. Returns per-node results and running/stopped summary.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
    """
    try:
        c = get_client()
        path = normalize_lab_path(lab_path)
        before = handle_eve_response(c.get(f"/api/labs{path}/nodes")) or {}
        steps = []
        for nid, node in (before.items() if isinstance(before, dict) else {}.items()):
            name = node.get("name", nid) if isinstance(node, dict) else nid
            try:
                zero_config_seed = _seed_zero_config_if_needed(c, lab_path, str(nid), node if isinstance(node, dict) else {})
                handle_eve_response(c.get(f"/api/labs{path}/nodes/{nid}/start"))
                step = {"node_id": nid, "node_name": name, "ok": True}
                if zero_config_seed:
                    step["zero_config_seed"] = zero_config_seed
                steps.append(step)
            except Exception as exc:
                steps.append({"node_id": nid, "node_name": name, "ok": False, "error": str(exc)})
        time.sleep(3)
        after = handle_eve_response(c.get(f"/api/labs{path}/nodes")) or {}
        running = [n.get("name", nid) for nid, n in after.items()
                   if isinstance(n, dict) and node_is_running(n)]
        stopped  = [n.get("name", nid) for nid, n in after.items()
                   if isinstance(n, dict) and not node_is_running(n)]
        failures = [s["node_name"] for s in steps if not s["ok"]]
        return success_response(
            {"steps": steps, "summary": {"running": running, "stopped": stopped, "failures": failures}},
            f"Start complete: {len(running)} running, {len(stopped)} stopped",
        )
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_stop_lab")
def eve_stop_lab(lab_path: str) -> str:
    """
    Stop all nodes in a lab. Returns per-node results and final summary.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
    """
    try:
        c = get_client()
        path = normalize_lab_path(lab_path)
        before = handle_eve_response(c.get(f"/api/labs{path}/nodes")) or {}
        steps = []
        for nid, node in (before.items() if isinstance(before, dict) else {}.items()):
            name = node.get("name", nid) if isinstance(node, dict) else nid
            try:
                handle_eve_response(c.get(f"/api/labs{path}/nodes/{nid}/stop"))
                steps.append({"node_id": nid, "node_name": name, "ok": True})
            except Exception as exc:
                steps.append({"node_id": nid, "node_name": name, "ok": False, "error": str(exc)})
        time.sleep(2)
        after = handle_eve_response(c.get(f"/api/labs{path}/nodes")) or {}
        running = [n.get("name", nid) for nid, n in after.items()
                   if isinstance(n, dict) and node_is_running(n)]
        stopped  = [n.get("name", nid) for nid, n in after.items()
                   if isinstance(n, dict) and not node_is_running(n)]
        failures = [s["node_name"] for s in steps if not s["ok"]]
        return success_response(
            {"steps": steps, "summary": {"running": running, "stopped": stopped, "failures": failures}},
            f"Stop complete: {len(stopped)} stopped, {len(running)} still running",
        )
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_wipe_node")
def eve_wipe_node(lab_path: str, node: str) -> str:
    """
    Wipe a node to factory defaults — clears NVRAM and startup config.
    Node must be stopped before wiping.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name or numeric ID
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        handle_eve_response(c.get(f"/api/labs{normalize_lab_path(lab_path)}/nodes/{node_id}/wipe"))
        return success_response({"node_id": node_id}, f"Node '{node}' wiped to factory defaults")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)
