"""Tests for the halo_mcp_server entrypoint (Feature 069).

Covers:
  * the module imports cleanly with the dummy credentials conftest sets;
  * REGISTERED_TOOL_NAMES / TOOL_FUNCS both have exactly 18 entries;
  * FastMCP introspection (mcp.list_tools) reports the same 18 names;
  * all core tool functions are async;
  * get_client() fails fast when required Halo credentials are absent.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Generator

import pytest

_EXPECTED_TOOL_NAMES = frozenset(
    [
        "halo_list_ticket_types",
        "halo_get_ticket_type",
        "halo_list_fields",
        "halo_get_field",
        "halo_get_ticket",
        "halo_list_tickets",
        "halo_get_ticket_actions",
        "halo_get_asset_tickets",
        "halo_create_change_request",
        "halo_get_asset",
        "halo_list_assets",
        "halo_get_asset_relationships",
        "halo_list_clients",
        "halo_list_sites",
        "halo_list_users",
        "halo_list_contracts",
        "halo_list_kb_articles",
        "halo_get_kb_article",
    ]
)


def _import_server():
    if "halo_mcp_server" not in sys.modules:
        import halo_mcp_server  # noqa: F401
    return sys.modules["halo_mcp_server"]


# ---------------------------------------------------------------------------
# Import + counts
# ---------------------------------------------------------------------------


def test_server_imports_cleanly():
    assert _import_server() is not None


def test_registered_tool_names_count_is_18():
    server = _import_server()
    assert len(server.REGISTERED_TOOL_NAMES) == 18, (
        f"Expected 18 tools, got {len(server.REGISTERED_TOOL_NAMES)}: "
        f"{server.REGISTERED_TOOL_NAMES}"
    )


def test_tool_funcs_count_is_18():
    server = _import_server()
    assert len(server.TOOL_FUNCS) == 18


def test_registered_tool_names_exact_set():
    server = _import_server()
    actual = frozenset(server.REGISTERED_TOOL_NAMES)
    assert actual == _EXPECTED_TOOL_NAMES, (
        f"Missing: {_EXPECTED_TOOL_NAMES - actual}; Extra: {actual - _EXPECTED_TOOL_NAMES}"
    )


def test_registered_tool_names_no_duplicates():
    server = _import_server()
    names = server.REGISTERED_TOOL_NAMES
    assert len(names) == len(set(names))


def test_tool_funcs_are_coroutines():
    server = _import_server()
    for fn in server.TOOL_FUNCS:
        assert asyncio.iscoroutinefunction(fn), f"{fn.__name__!r} is not async"


def test_tool_func_names_match_registered():
    server = _import_server()
    assert frozenset(fn.__name__ for fn in server.TOOL_FUNCS) == _EXPECTED_TOOL_NAMES


# ---------------------------------------------------------------------------
# FastMCP introspection
# ---------------------------------------------------------------------------


def test_fastmcp_list_tools_returns_18():
    server = _import_server()
    tools = asyncio.run(server.mcp.list_tools())
    assert len(tools) == 18, f"FastMCP reports {len(tools)} tools: {[t.name for t in tools]}"


def test_fastmcp_tool_names_match_registered():
    server = _import_server()
    tools = asyncio.run(server.mcp.list_tools())
    assert frozenset(t.name for t in tools) == _EXPECTED_TOOL_NAMES


# ---------------------------------------------------------------------------
# get_client() credential guards
# ---------------------------------------------------------------------------


@pytest.fixture
def _reset_singleton() -> Generator:
    server = _import_server()
    original = server._client
    server._client = None
    yield
    server._client = original


def test_get_client_raises_without_base_url(monkeypatch, _reset_singleton):
    server = _import_server()
    monkeypatch.setattr(server, "HALO_BASE_URL", "")
    monkeypatch.setattr(server, "HALO_CLIENT_ID", "id")
    monkeypatch.setattr(server, "HALO_CLIENT_SECRET", "secret")
    server._client = None

    with pytest.raises(ValueError, match="HALO_BASE_URL"):
        server.get_client()


def test_get_client_raises_without_client_id(monkeypatch, _reset_singleton):
    server = _import_server()
    monkeypatch.setattr(server, "HALO_BASE_URL", "https://test.halopsa.com")
    monkeypatch.setattr(server, "HALO_CLIENT_ID", "")
    monkeypatch.setattr(server, "HALO_CLIENT_SECRET", "secret")
    server._client = None

    with pytest.raises(ValueError, match="HALO_CLIENT_ID"):
        server.get_client()


def test_get_client_raises_without_client_secret(monkeypatch, _reset_singleton):
    server = _import_server()
    monkeypatch.setattr(server, "HALO_BASE_URL", "https://test.halopsa.com")
    monkeypatch.setattr(server, "HALO_CLIENT_ID", "id")
    monkeypatch.setattr(server, "HALO_CLIENT_SECRET", "")
    server._client = None

    with pytest.raises(ValueError, match="HALO_CLIENT_SECRET|HALO_CLIENT_ID"):
        server.get_client()


def test_get_client_returns_singleton(monkeypatch, _reset_singleton):
    from clients.halo_client import HaloClient

    server = _import_server()
    monkeypatch.setattr(server, "HALO_BASE_URL", "https://test.halopsa.com")
    monkeypatch.setattr(server, "HALO_CLIENT_ID", "id")
    monkeypatch.setattr(server, "HALO_CLIENT_SECRET", "secret")
    server._client = None

    c1 = server.get_client()
    c2 = server.get_client()
    assert isinstance(c1, HaloClient)
    assert c1 is c2
