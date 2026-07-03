"""Config management (7) MCP tools."""

import base64
import os
import shutil
import xml.etree.ElementTree as ET

from mcp_init import mcp
from eve_client import (
    get_client, EVEError, handle_eve_response, success_response, error_response,
    with_gait_logging, paginate_sequence,
    normalize_lab_path, resolve_node_id,
)


LAB_ROOT = os.getenv("EVE_LAB_ROOT", "/opt/unetlab/labs")


def _local_lab_file(lab_path: str) -> str:
    path = normalize_lab_path(lab_path).lstrip("/")
    full = os.path.abspath(os.path.join(LAB_ROOT, path))
    root = os.path.abspath(LAB_ROOT)
    if not full.startswith(root + os.sep):
        raise EVEError("EVE_VALIDATION", f"Invalid lab path: {lab_path}", 400)
    if not os.path.isfile(full):
        raise EVEError("EVE_NOT_FOUND", f"Local lab file not found: {full}", 404)
    return full


def _lab_id_from_unl(lab_path: str) -> str | None:
    full = _local_lab_file(lab_path)
    root = ET.parse(full).getroot()
    return root.get("id")


def _reset_node_runtime_dir(lab_path: str, node_id: str) -> dict | None:
    """Remove stale EVE runtime dir so changed startup-config is materialized.

    EVE marks existing runtime dirs as .prepared and skips dumping a newly
    embedded startup-config on later starts. Only call this for stopped nodes.
    """
    lab_id = _lab_id_from_unl(lab_path)
    if not lab_id:
        return None
    runtime_root = os.path.abspath(os.getenv("EVE_RUNTIME_ROOT", "/opt/unetlab/tmp/0"))
    node_dir = os.path.abspath(os.path.join(runtime_root, lab_id, str(node_id)))
    if not node_dir.startswith(runtime_root + os.sep):
        raise EVEError("EVE_VALIDATION", f"Invalid runtime path: {node_dir}", 400)
    if os.path.isdir(node_dir):
        shutil.rmtree(node_dir)
        return {"runtime_reset": True, "runtime_dir": node_dir}
    return {"runtime_reset": False, "runtime_dir": node_dir}


def _set_config_in_unl(lab_path: str, node_id: str, config: str) -> dict:
    """Fallback for EVE versions whose config PUT API rejects writes."""
    full = _local_lab_file(lab_path)
    tree = ET.parse(full)
    root = tree.getroot()
    objects = root.find("objects")
    if objects is None:
        objects = ET.SubElement(root, "objects")
    configs = objects.find("configs")
    if configs is None:
        configs = ET.SubElement(objects, "configs")
    node_elem = None
    for elem in root.findall(".//node"):
        if elem.get("id") == str(node_id):
            node_elem = elem
            break
    if node_elem is None:
        raise EVEError("EVE_NOT_FOUND", f"Node id {node_id} not found in {full}", 404)

    target = None
    for elem in configs.findall("config"):
        if elem.get("id") == str(node_id):
            target = elem
            break
    encoded = base64.b64encode((config or "").encode("utf-8")).decode("ascii")
    if target is None:
        target = ET.SubElement(configs, "config", {"id": str(node_id)})
    target.text = encoded
    # EVE only injects the <config> object when the node's startup-config mode
    # is enabled. Without this, the API GET shows data but the VM still boots
    # into the initial setup dialog.
    node_elem.set("config", "1" if config else "0")
    tree.write(full, encoding="UTF-8", xml_declaration=True)
    return {"fallback": "local_unl", "lab_file": full, "encoded_bytes": len(encoded), "startup_config_mode": node_elem.get("config")}


@mcp.tool()
@with_gait_logging("eve_get_node_config")
def eve_get_node_config(lab_path: str, node: str) -> str:
    """
    Get the stored startup configuration for a node.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name or numeric ID
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        nodes = handle_eve_response(c.get(f"/api/labs{normalize_lab_path(lab_path)}/nodes")) or {}
        meta = nodes.get(str(node_id), {}) if isinstance(nodes, dict) else {}
        data = handle_eve_response(
            c.get(f"/api/labs{normalize_lab_path(lab_path)}/configs/{node_id}"))
        return success_response({
            "node_id": node_id,
            "node": meta.get("name", node),
            "startup_config_mode": meta.get("config"),
            "startup_config_data": data.get("data") if isinstance(data, dict) else data,
        })
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_set_node_startup_mode")
def eve_set_node_startup_mode(lab_path: str, node: str, enabled: bool) -> str:
    """
    Enable or disable use of the node's stored startup config at boot.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name or numeric ID
        enabled: True to use exported/stored startup-config, False to disable it
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        handle_eve_response(
            c.put(f"/api/labs{normalize_lab_path(lab_path)}/nodes/{node_id}",
                  json={"id": int(node_id), "config": "1" if enabled else "0"}),
            success_codes=[200, 201])
        return success_response({"node_id": node_id, "node": node, "enabled": enabled},
                                f"Startup-config mode {'enabled' if enabled else 'disabled'} for node '{node}'")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_set_node_config")
def eve_set_node_config(lab_path: str, node: str, config: str) -> str:
    """
    Push a startup configuration to a node. Node should be stopped.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name or numeric ID
        config: Full configuration text to store as startup config
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        fallback = None
        try:
            handle_eve_response(
                c.put(f"/api/labs{normalize_lab_path(lab_path)}/nodes/{node_id}/configs",
                      json={"id": int(node_id), "data": config}))
        except EVEError as api_error:
            if api_error.status_code != 400:
                raise
            fallback = _set_config_in_unl(lab_path, node_id, config)
            c.invalidate_cache()
        return success_response({"node_id": node_id, "node": node, "write_path": fallback or "api"},
                                f"Config applied to node '{node}'")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_export_node_config")
def eve_export_node_config(lab_path: str, node: str) -> str:
    """
    Export a running node's configuration into the lab file as startup config.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name or numeric ID
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        handle_eve_response(
            c.put(f"/api/labs{normalize_lab_path(lab_path)}/nodes/{node_id}/export", json={}))
        return success_response({"node_id": node_id, "node": node},
                                f"Running config exported for node '{node}'")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_export_all_node_configs")
def eve_export_all_node_configs(lab_path: str) -> str:
    """
    Export running configurations for all supported nodes in a lab into the lab file.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
    """
    try:
        c = get_client()
        handle_eve_response(c.put(f"/api/labs{normalize_lab_path(lab_path)}/nodes/export", json={}))
        return success_response({"lab_path": normalize_lab_path(lab_path)},
                                f"Running configs exported for lab '{lab_path}'")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_list_config_summaries")
def eve_list_config_summaries(lab_path: str, page: int = 1, page_size: int = 50) -> str:
    """
    Retrieve cheap startup configuration summaries for all supported nodes in a lab.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        page: 1-based page number for pagination.
        page_size: Number of records per page (max capped by server setting).
    """
    try:
        c = get_client()
        path = normalize_lab_path(lab_path)
        nodes = handle_eve_response(c.get(f"/api/labs{path}/nodes")) or {}
        configs = handle_eve_response(c.get(f"/api/labs{path}/configs")) or {}
        result = []
        for nid, node in nodes.items():
            if not isinstance(node, dict):
                continue
            summary = configs.get(str(nid), {}) if isinstance(configs, dict) else {}
            result.append({
                "node_id": str(nid),
                "name": node.get("name", nid),
                "startup_config_mode": node.get("config"),
                "has_startup_config": bool(isinstance(summary, dict) and summary.get("len", 0)),
                "startup_config_size": summary.get("len", 0) if isinstance(summary, dict) else 0,
                "startup_config_summary": summary,
            })
        result = sorted(result, key=lambda item: (str(item.get("name") or ""), str(item.get("node_id") or "")))
        paged, meta = paginate_sequence(result, page, page_size)
        return success_response(
            paged,
            f"Config summaries retrieved for {meta['total_count']} nodes",
            len(paged),
            total_count=meta["total_count"],
            pagination=meta,
        )
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_get_all_configs")
def eve_get_all_configs(lab_path: str, page: int = 1, page_size: int = 50) -> str:
    """
    Retrieve startup configuration status and stored config text for all supported nodes in a lab.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        page: 1-based page number for pagination.
        page_size: Number of records per page (max capped by server setting).
    """
    try:
        c = get_client()
        path = normalize_lab_path(lab_path)
        nodes = handle_eve_response(c.get(f"/api/labs{path}/nodes")) or {}
        configs = handle_eve_response(c.get(f"/api/labs{path}/configs")) or {}
        node_rows = []
        for nid, node in nodes.items():
            if not isinstance(node, dict):
                continue
            node_rows.append({
                "node_id": str(nid),
                "name": node.get("name", nid),
                "startup_config_mode": node.get("config"),
                "startup_config_summary": configs.get(str(nid), {}) if isinstance(configs, dict) else {},
            })
        node_rows = sorted(node_rows, key=lambda item: (str(item.get("name") or ""), str(item.get("node_id") or "")))
        paged_rows, meta = paginate_sequence(node_rows, page, page_size)
        result = []
        for row in paged_rows:
            nid = row["node_id"]
            summary = row.get("startup_config_summary") or {}
            config_data = None
            if isinstance(summary, dict) and summary.get("len", 0):
                try:
                    detail = handle_eve_response(c.get(f"/api/labs{path}/configs/{nid}")) or {}
                    config_data = detail.get("data") if isinstance(detail, dict) else detail
                except Exception:
                    config_data = None
            result.append({**row, "startup_config_data": config_data})
        return success_response(
            result,
            f"Configs retrieved for {meta['total_count']} nodes",
            len(result),
            total_count=meta["total_count"],
            pagination=meta,
        )
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_wipe_node_config")
def eve_wipe_node_config(lab_path: str, node: str) -> str:
    """
    Clear the startup configuration of a node (writes empty string).
    Lighter than eve_wipe_node — config only, no NVRAM wipe. Node must be stopped.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name or numeric ID
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        fallback = None
        try:
            handle_eve_response(
                c.put(f"/api/labs{normalize_lab_path(lab_path)}/nodes/{node_id}/configs",
                      json={"id": int(node_id), "data": ""}))
        except EVEError as api_error:
            if api_error.status_code != 400:
                raise
            fallback = _set_config_in_unl(lab_path, node_id, "")
            c.invalidate_cache()
        return success_response({"node_id": node_id, "node": node, "write_path": fallback or "api"},
                                f"Startup config cleared for node '{node}'")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)
