#!/usr/bin/env python3
"""Six stdio controls for the installation-owned Genie manager; no provider key."""
from __future__ import annotations

import asyncio
import http.client
import json
import os
from pathlib import Path
import re
import stat
from typing import Annotated
from urllib.parse import urlsplit

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.tools.base import Tool
from mcp.types import ToolAnnotations
from pydantic import Field

UUID = Annotated[str, Field(pattern=r"^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[1-5][a-fA-F0-9]{3}-[89abAB][a-fA-F0-9]{3}-[a-fA-F0-9]{12}$")]
Ref = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{0,95}$")]


def control_binding():
    path = Path(os.environ.get("NETCLAW_GENIE_CONTROL_FILE", ""))
    if not path.is_absolute():
        raise ValueError("control_binding_required")
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError("control_binding_symlink")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077 or st.st_size > 4096:
            raise ValueError("private_control_binding_required")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            config = json.loads(stream.read(4097))
    finally:
        os.close(fd)
    if set(config) != {"schema", "origin", "token"} or config["schema"] != 1:
        raise ValueError("invalid_control_binding")
    origin = urlsplit(config["origin"])
    if (origin.scheme != "http" or origin.hostname != "127.0.0.1" or
            not origin.port or origin.username or origin.password or origin.path or
            origin.query or origin.fragment or config["origin"] != f"http://127.0.0.1:{origin.port}"):
        raise ValueError("loopback_control_required")
    if not isinstance(config["token"], str) or not re.fullmatch(r"[a-f0-9]{64}", config["token"]):
        raise ValueError("invalid_control_binding")
    return origin.port, config["token"]


def call_backend(method, route, payload=None):
    """One bounded send; no redirect, proxy, ambient credentials or retry."""
    connection = None
    sent = False
    try:
        port, token = control_binding()
        data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
        if data and len(data) > 16384:
            raise ValueError("invalid_input")
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        sent = True
        connection.request(method, route, body=data, headers={
            "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        })
        response = connection.getresponse()
        raw = response.read(262145)
        if len(raw) > 262144 or response.getheader("Content-Type") != "application/json":
            raise ValueError("control_contract")
        result = json.loads(raw)
        if response.status != 200:
            code = result.get("error") if isinstance(result, dict) else None
            if not isinstance(code, str) or not re.fullmatch(r"[a-z_]{1,80}", code):
                code = "control_refused"
            return {"schema_version": 1, "status": "refused", "error": {"code": code, "retryable": False}}
        return result
    except Exception:
        # The request may have reached the backend before the response was lost.
        return {"schema_version": 1, "status": "unknown" if sent and method == "POST" else "error",
                "operation_id": (payload or {}).get("request_id") if route == "/v1/sessions" else None,
                "error": {"code": "control_outcome_unknown" if sent and method == "POST" else "control_unavailable", "retryable": False}}
    finally:
        if connection:
            connection.close()


async def backend(method, route, payload=None):
    return await asyncio.to_thread(call_backend, method, route, payload)


async def genie_world_prepare(request_id: UUID, synthetic_fixture_id: Ref | None = None,
                              private_snapshot_ref: Ref | None = None) -> dict:
    """Prepare a registered source. Private export requires an exact backend-owned grant. No generation."""
    data = {"request_id": request_id}
    if synthetic_fixture_id is not None:
        data["synthetic_fixture_id"] = synthetic_fixture_id
    if private_snapshot_ref is not None:
        data["private_snapshot_ref"] = private_snapshot_ref
    return await backend("POST", "/v1/drafts", data)


async def genie_world_start(request_id: UUID, projection_ref: UUID, review_ref: UUID) -> dict:
    """Start once with an existing exact review grant. Save request_id before this spend-capable call."""
    return await backend("POST", "/v1/sessions", dict(request_id=request_id, projection_ref=projection_ref, review_ref=review_ref))


async def genie_world_status(operation_id: UUID) -> dict:
    """Read the original session and retained control outcomes. Never creates or resumes a world."""
    return await backend("GET", f"/v1/sessions/{operation_id}")


async def genie_world_event(request_id: UUID, operation_id: UUID, event_id: Ref) -> dict:
    """Request the fixed fictional event once, only after human target-visible intent in the viewer."""
    return await backend("POST", f"/v1/sessions/{operation_id}/event", dict(request_id=request_id, event_id=event_id))


async def genie_world_stop(request_id: UUID, operation_id: UUID) -> dict:
    """Request backend termination. Accepted is not a terminal receipt or reconciled usage."""
    return await backend("POST", f"/v1/sessions/{operation_id}/stop", dict(request_id=request_id))


async def genie_world_evidence(operation_id: UUID) -> dict:
    """Read bounded artifact hashes and session evidence; no media, raw network facts or acceptance inference."""
    return await backend("GET", f"/v1/sessions/{operation_id}/evidence")


def build_server():
    tools = []
    for fn in (genie_world_prepare, genie_world_start, genie_world_status, genie_world_event, genie_world_stop, genie_world_evidence):
        read = fn in (genie_world_status, genie_world_evidence)
        tool = Tool.from_function(fn, annotations=ToolAnnotations(
            readOnlyHint=read, destructiveHint=not read, idempotentHint=True,
            openWorldHint=fn in (genie_world_start, genie_world_event, genie_world_stop)))
        # SDK validation rejects extra inputs before calling the backend; errors
        # suppress input values so callers cannot accidentally echo a secret.
        tool.fn_metadata.arg_model.model_config.update(extra="forbid", hide_input_in_errors=True, strict=True)
        tool.fn_metadata.arg_model.model_rebuild(force=True)
        tool.parameters = tool.fn_metadata.arg_model.model_json_schema()
        tools.append(tool)
    return MCPServer("netclaw-genie-worlds", version="0.1.0", tools=tools,
                     instructions="Use original request IDs. Private snapshot facts stay local. No approval tool or device access. Human navigation uses the owner viewer.",
                     log_level="ERROR")


if __name__ == "__main__":
    build_server().run(transport="stdio")
