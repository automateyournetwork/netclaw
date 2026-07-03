"""System status (3) + Lab lifecycle (6) MCP tools."""

import os
from typing import Optional

from mcp_init import mcp
from eve_client import (
    get_client, EVEError, handle_eve_response, success_response, error_response,
    with_gait_logging, paginate_sequence,
    normalize_lab_path, split_lab_path, normalize_folder_path, collect_labs,
)

import zipfile
import io


# =============================================================================
# System Tools
# =============================================================================

@mcp.tool()
@with_gait_logging("eve_status")
def eve_status() -> str:
    """Get EVE-NG system status including version, CPU, memory, and disk."""
    try:
        data = handle_eve_response(get_client().get("/api/status"))
        return success_response(data, "EVE-NG system status retrieved")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_auth")
def eve_auth() -> str:
    """Verify EVE-NG authentication and return current user details."""
    try:
        data = handle_eve_response(get_client().get("/api/auth"))
        return success_response(data, "Authentication verified")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_list_images")
def eve_list_images(node_type: Optional[str] = None, page: int = 1, page_size: int = 50) -> str:
    """
    List available node images on the EVE-NG server.

    Args:
        node_type: Optional filter — 'iol', 'qemu', 'dynamips', 'docker', etc.
                   Omit to list all template types.
        page: 1-based page number for pagination.
        page_size: Number of records per page (max capped by server setting).
    """
    try:
        c = get_client()
        # EVE-NG 6.x exposes templates at one aggregate endpoint; node_type-specific
        # paths such as /api/list/qemus/templates/ return 404. Fetch once and filter
        # locally by template key/name instead of inventing plural API paths.
        data = handle_eve_response(c.get("/api/list/templates/"))
        if isinstance(data, dict):
            items = [{"type": k, **(v if isinstance(v, dict) else {"name": v})} for k, v in data.items()]
        elif isinstance(data, list):
            items = data
        else:
            items = [data] if data else []
        if node_type:
            wanted = str(node_type).lower().rstrip("s")
            aliases = {
                "qemu": {"qemu", "vios", "viosl2", "csr", "csr1000v", "xrv", "xrv9k", "nxos", "nxosv", "vmx", "vsrx", "veos", "linux"},
                "iol": {"iol", "i86bi", "iourc"},
                "vpcs": {"vpcs"},
                "docker": {"docker"},
                "dynamips": {"dynamips", "c7200", "c3725", "c3640", "c2691"},
            }.get(wanted, {wanted})
            def matches(item):
                hay = f"{item.get('type','')} {item.get('name','')}".lower()
                return any(alias in hay for alias in aliases)
            items = [item for item in items if matches(item)]
        items = sorted(items, key=lambda item: str(item.get("name") or item.get("type") or item))
        paged, meta = paginate_sequence(items, page, page_size)
        return success_response(
            paged,
            f"Found {meta['total_count']} images",
            len(paged),
            total_count=meta["total_count"],
            pagination=meta,
        )
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


# =============================================================================
# Lab Lifecycle Tools
# =============================================================================

@mcp.tool()
@with_gait_logging("eve_list_labs")
def eve_list_labs(folder: str = "/", page: int = 1, page_size: int = 50) -> str:
    """
    List all labs recursively from a folder.

    Args:
        folder: Root folder to search (default '/')
        page: 1-based page number for pagination.
        page_size: Number of records per page (max capped by server setting).
    """
    try:
        labs = sorted(collect_labs(get_client(), folder))
        paged, meta = paginate_sequence(labs, page, page_size)
        return success_response(
            paged,
            f"Found {meta['total_count']} labs",
            len(paged),
            total_count=meta["total_count"],
            pagination=meta,
        )
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_get_lab")
def eve_get_lab(lab_path: str) -> str:
    """
    Get lab metadata: description, version, author, and body.

    Args:
        lab_path: Lab path like '/Labs/demo.unl' — folder prefix required when outside root
    """
    try:
        data = handle_eve_response(get_client().get(f"/api/labs{normalize_lab_path(lab_path)}"))
        return success_response(data)
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_create_lab")
def eve_create_lab(
    name: str,
    folder: str = "/",
    description: str = "",
    version: str = "1",
    author: str = "",
) -> str:
    """
    Create a new empty lab file.

    Args:
        name: Lab name without .unl extension (e.g. 'BGP-Test')
        folder: Target folder (default '/')
        description: Lab description
        version: Version string
        author: Author name
    """
    try:
        payload: dict = {
            "name": name,
            "path": normalize_folder_path(folder),
            "version": version,
        }
        if description:
            payload["description"] = description
        if author:
            payload["author"] = author
        data = handle_eve_response(get_client().post("/api/labs", json=payload),
                                   success_codes=[200, 201])
        return success_response(data, f"Lab '{name}' created in {folder}")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_delete_lab")
def eve_delete_lab(lab_path: str) -> str:
    """
    Delete a lab and all its runtime objects. Stop all nodes first.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
    """
    try:
        handle_eve_response(get_client().delete(f"/api/labs{normalize_lab_path(lab_path)}"),
                            success_codes=[200, 204])
        return success_response(message=f"Lab '{lab_path}' deleted")
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_export_lab")
def eve_export_lab(lab_path: str) -> str:
    """
    Export a lab using EVE's ZIP export, then return the raw .unl XML plus package metadata.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
    """
    try:
        c = get_client()
        folder, normalized = split_lab_path(lab_path)
        export_meta = handle_eve_response(c.post("/api/export", json={"path": folder, "lab": normalized}))
        if not isinstance(export_meta, str) or not export_meta:
            raise EVEError("EVE_SERVER_ERROR", f"Unexpected export response: {export_meta}", 500)
        zip_resp = c.get(export_meta)
        if zip_resp.status_code not in (200, 201):
            handle_eve_response(zip_resp)
        zip_bytes = zip_resp.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            members = zf.namelist()
            unl_members = [name for name in members if name.endswith(".unl")]
            if not unl_members:
                raise EVEError("EVE_SERVER_ERROR", "Export ZIP did not contain a .unl file", 500)
            content = zf.read(unl_members[0]).decode("utf-8", errors="replace")
        return success_response(
            {
                "content": content,
                "size_bytes": len(content),
                "export_url": export_meta,
                "package_size_bytes": len(zip_bytes),
                "package_members": members,
            },
            f"Lab exported ({len(content)} XML bytes, {len(zip_bytes)} ZIP bytes)",
        )
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_import_lab")
def eve_import_lab(archive_path: str, folder: str = "/") -> str:
    """
    Import an EVE-NG lab export ZIP into a destination folder.

    Args:
        archive_path: Local filesystem path to the ZIP archive to upload
        folder: Destination lab folder on the EVE-NG server (default '/')
    """
    try:
        c = get_client()
        folder = normalize_folder_path(folder)
        if not os.path.isfile(archive_path):
            raise EVEError("EVE_NOT_FOUND", f"Archive not found: {archive_path}", 404)
        filename = os.path.basename(archive_path)
        with open(archive_path, "rb") as fh:
            files = {"file": (filename, fh, "application/zip")}
            resp = c.post("/api/import", data={"path": folder}, files=files)
        data = handle_eve_response(resp)
        return success_response(
            {"archive_path": archive_path, "folder": folder, "response": data},
            f"Lab archive '{filename}' imported into {folder}",
        )
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)
