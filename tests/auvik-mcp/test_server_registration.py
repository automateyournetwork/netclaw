"""Tests for the auvik_mcp_server entrypoint (Feature 036).

Covers:
- Module imports cleanly with dummy credentials (conftest sets them).
- REGISTERED_TOOL_NAMES has exactly 20 entries matching the expected names.
- No registered tool name contains write verbs (read-only guarantee).
- AuvikClient exposes no post/put/delete/patch method (structural read-only).
- get_client() raises ValueError when AUVIK_USERNAME or AUVIK_API_KEY is absent.
- FastMCP tool introspection via mcp.list_tools() returns 20 tools.
"""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
from typing import Generator

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WRITE_VERBS = frozenset(
    ["create", "update", "delete", "dismiss", "set_", "post", "put", "patch", "remove"]
)

_EXPECTED_TOOL_NAMES = frozenset(
    [
        "auvik_list_devices",
        "auvik_list_networks",
        "auvik_list_interfaces",
        "auvik_list_components",
        "auvik_list_tenants",
        "auvik_list_entity_notes",
        "auvik_list_entity_audits",
        "auvik_get_usage",
        "auvik_verify_credentials",
        "auvik_list_alerts",
        "auvik_list_device_lifecycle",
        "auvik_list_device_warranty",
        "auvik_list_configurations",
        "auvik_get_device_statistics",
        "auvik_get_interface_statistics",
        "auvik_get_service_statistics",
        "auvik_get_component_statistics",
        "auvik_get_oid_statistics",
        "auvik_list_snmp_poller_settings",
        "auvik_get_snmp_poller_history",
    ]
)


def _import_server():
    """Import (or return cached) auvik_mcp_server from sys.modules."""
    # The conftest already inserted mcp-servers/auvik-mcp into sys.path and
    # set dummy env vars, so a plain import works.
    if "auvik_mcp_server" not in sys.modules:
        import auvik_mcp_server  # noqa: F401

    return sys.modules["auvik_mcp_server"]


# ---------------------------------------------------------------------------
# Basic import
# ---------------------------------------------------------------------------


def test_server_imports_cleanly():
    """Importing the server module with dummy creds must not raise."""
    server = _import_server()
    assert server is not None


# ---------------------------------------------------------------------------
# REGISTERED_TOOL_NAMES
# ---------------------------------------------------------------------------


def test_registered_tool_names_count():
    server = _import_server()
    assert len(server.REGISTERED_TOOL_NAMES) == 20, (
        f"Expected 20 tools, got {len(server.REGISTERED_TOOL_NAMES)}: "
        f"{server.REGISTERED_TOOL_NAMES}"
    )


def test_registered_tool_names_exact_set():
    server = _import_server()
    actual = frozenset(server.REGISTERED_TOOL_NAMES)
    assert actual == _EXPECTED_TOOL_NAMES, (
        f"Tool name mismatch.\n"
        f"  Missing: {_EXPECTED_TOOL_NAMES - actual}\n"
        f"  Extra:   {actual - _EXPECTED_TOOL_NAMES}"
    )


def test_registered_tool_names_no_duplicates():
    server = _import_server()
    names = server.REGISTERED_TOOL_NAMES
    assert len(names) == len(set(names)), f"Duplicate tool names: {names}"


# ---------------------------------------------------------------------------
# TOOL_FUNCS
# ---------------------------------------------------------------------------


def test_tool_funcs_count():
    server = _import_server()
    assert len(server.TOOL_FUNCS) == 20, (
        f"Expected 20 TOOL_FUNCS, got {len(server.TOOL_FUNCS)}"
    )


def test_tool_funcs_are_coroutines():
    """All core tool functions must be async (awaitable)."""
    import asyncio

    server = _import_server()
    for fn in server.TOOL_FUNCS:
        assert asyncio.iscoroutinefunction(fn), (
            f"{fn.__name__!r} is not an async function"
        )


# ---------------------------------------------------------------------------
# Read-only guarantee: tool names
# ---------------------------------------------------------------------------


def test_no_write_verb_in_tool_names():
    """No registered tool name should contain a write-mutation verb."""
    server = _import_server()
    violations = [
        name
        for name in server.REGISTERED_TOOL_NAMES
        if any(verb in name for verb in _WRITE_VERBS)
    ]
    assert not violations, (
        f"Tool names contain write verbs: {violations}"
    )


# ---------------------------------------------------------------------------
# Read-only guarantee: AuvikClient has no mutating HTTP methods
# ---------------------------------------------------------------------------


def test_auvik_client_has_no_post():
    from clients.auvik_client import AuvikClient
    assert not hasattr(AuvikClient, "post"), (
        "AuvikClient must not expose a 'post' method"
    )


def test_auvik_client_has_no_put():
    from clients.auvik_client import AuvikClient
    assert not hasattr(AuvikClient, "put"), (
        "AuvikClient must not expose a 'put' method"
    )


def test_auvik_client_has_no_delete():
    from clients.auvik_client import AuvikClient
    assert not hasattr(AuvikClient, "delete"), (
        "AuvikClient must not expose a 'delete' method"
    )


def test_auvik_client_has_no_patch():
    from clients.auvik_client import AuvikClient
    assert not hasattr(AuvikClient, "patch"), (
        "AuvikClient must not expose a 'patch' method"
    )


# ---------------------------------------------------------------------------
# get_client() fails fast on missing credentials
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=False)
def _reset_singleton() -> Generator:
    """Clear the _client singleton before and after each credential test."""
    server = _import_server()
    original_client = server._client
    server._client = None
    yield
    # Restore so other tests are not affected
    server._client = original_client


def test_get_client_raises_without_username(monkeypatch, _reset_singleton):
    server = _import_server()
    monkeypatch.setattr(server, "AUVIK_USERNAME", "")
    monkeypatch.setattr(server, "AUVIK_API_KEY", "some_key")
    server._client = None

    with pytest.raises(ValueError, match="AUVIK_USERNAME"):
        server.get_client()


def test_get_client_raises_without_api_key(monkeypatch, _reset_singleton):
    server = _import_server()
    monkeypatch.setattr(server, "AUVIK_USERNAME", "user@example.com")
    monkeypatch.setattr(server, "AUVIK_API_KEY", "")
    server._client = None

    with pytest.raises(ValueError, match="AUVIK_API_KEY"):
        server.get_client()


def test_get_client_returns_auvik_client(monkeypatch, _reset_singleton):
    """get_client() returns an AuvikClient when both creds are set."""
    from clients.auvik_client import AuvikClient

    server = _import_server()
    monkeypatch.setattr(server, "AUVIK_USERNAME", "user@example.com")
    monkeypatch.setattr(server, "AUVIK_API_KEY", "key123")
    server._client = None

    client = server.get_client()
    assert isinstance(client, AuvikClient)


def test_get_client_is_singleton(monkeypatch, _reset_singleton):
    """Calling get_client() twice returns the same object."""
    server = _import_server()
    monkeypatch.setattr(server, "AUVIK_USERNAME", "user@example.com")
    monkeypatch.setattr(server, "AUVIK_API_KEY", "key123")
    server._client = None

    c1 = server.get_client()
    c2 = server.get_client()
    assert c1 is c2


# ---------------------------------------------------------------------------
# FastMCP introspection: list_tools() returns 20
# ---------------------------------------------------------------------------


def test_fastmcp_list_tools_returns_20():
    """mcp.list_tools() must report exactly 20 registered tools."""
    server = _import_server()
    tools = asyncio.run(server.mcp.list_tools())
    assert len(tools) == 20, (
        f"FastMCP reports {len(tools)} tools, expected 20.\n"
        f"Names: {[t.name for t in tools]}"
    )


def test_fastmcp_tool_names_match_registered():
    """Names from mcp.list_tools() must match REGISTERED_TOOL_NAMES exactly."""
    server = _import_server()
    tools = asyncio.run(server.mcp.list_tools())
    fastmcp_names = frozenset(t.name for t in tools)
    registered = frozenset(server.REGISTERED_TOOL_NAMES)
    assert fastmcp_names == registered, (
        f"FastMCP names differ from REGISTERED_TOOL_NAMES.\n"
        f"  In FastMCP only: {fastmcp_names - registered}\n"
        f"  In REGISTERED only: {registered - fastmcp_names}"
    )
