"""Pytest configuration and shared fixtures for the halo-mcp test suite.

Mirrors the auvik-mcp test conventions:
  * insert the ``mcp-servers/halo-mcp`` server package directory on ``sys.path``
    so ``from clients.halo_client import ...`` / ``from tools... import ...``
    resolve;
  * set dummy Halo credentials so any module reading env at import time is happy;
  * expose a couple of ``_FakeClient`` fixtures for the pure-resolver tests
    (those only need ``get_all``, no HTTP transport).

The HTTP-level tests build a *real* ``HaloClient`` backed by ``httpx.MockTransport``
via a per-module ``_client_for(handler)`` helper (see the ``test_tools_*`` and
``test_client*`` modules), so the same transport intercepts both the OAuth token
POST (``.../auth/token``) and every ``/api/*`` resource request.
"""

import os
import sys

import pytest

# Add the halo-mcp server package directory to sys.path so imports like
# `from utils.constants import ...` resolve correctly.
_SERVER_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..",
    "mcp-servers",
    "halo-mcp",
)
sys.path.insert(0, os.path.abspath(_SERVER_DIR))

# Dummy credentials so modules that read env vars at import time don't fail.
os.environ.setdefault("HALO_BASE_URL", "https://test.halopsa.com")
os.environ.setdefault("HALO_CLIENT_ID", "test_client_id")
os.environ.setdefault("HALO_CLIENT_SECRET", "test_client_secret")


# ---------------------------------------------------------------------------
# Fake client (get_all only) for the pure-resolver tests
# ---------------------------------------------------------------------------


class _FakeClient:
    """Minimal fake HaloClient exposing only ``get_all`` for resolver tests.

    ``get_all`` returns the list registered for a given path, matching the
    ``{"items": [...], "truncated": False}`` page shape the real client returns.
    Every call is recorded in ``self.calls`` so tests can assert a numeric id
    short-circuits without any HTTP round-trip.
    """

    def __init__(self, items_by_path: dict):
        self._items_by_path = items_by_path
        self.calls: list = []

    async def get_all(self, path: str, params=None, max_pages=None) -> dict:
        self.calls.append((path, dict(params or {})))
        return {
            "items": list(self._items_by_path.get(path, [])),
            "truncated": False,
            "next_page": None,
            "record_count": None,
        }


# Sample rows keyed by the resolver's list path.
_CLIENT_ONE = {"id": 501, "name": "Acme Corp"}
_CLIENT_TWO = {"id": 502, "name": "Acme Staging"}
_SITE_ONE = {"id": 601, "name": "Acme HQ", "client_id": 501}
_ASSET_ONE = {"id": 701, "inventory_number": "SW-CORE-01", "name": "Core Switch"}
_ASSET_TWO = {"id": 702, "inventory_number": "SW-CORE-02", "name": "Core Switch B"}
_TICKET_TYPE_ONE = {"id": 9, "name": "Change Request"}
_TICKET_TYPE_TWO = {"id": 10, "name": "Change Advisory"}


@pytest.fixture
def fake_client_one_match():
    return _FakeClient(
        {
            "/Client": [_CLIENT_ONE],
            "/Site": [_SITE_ONE],
            "/Asset": [_ASSET_ONE],
            "/TicketType": [_TICKET_TYPE_ONE],
        }
    )


@pytest.fixture
def fake_client_two_matches():
    return _FakeClient(
        {
            "/Client": [_CLIENT_ONE, _CLIENT_TWO],
            "/Asset": [_ASSET_ONE, _ASSET_TWO],
            "/TicketType": [_TICKET_TYPE_ONE, _TICKET_TYPE_TWO],
        }
    )


@pytest.fixture
def fake_client_no_match():
    return _FakeClient(
        {
            "/Client": [],
            "/Site": [],
            "/Asset": [],
            "/TicketType": [],
        }
    )
