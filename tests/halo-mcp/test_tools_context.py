"""Tests for tools/context.py — halo_list_clients, halo_list_sites,
halo_list_users, halo_list_contracts."""

import json

import httpx
import pytest

from clients.halo_client import HaloClient
from tools.context import (
    halo_list_clients,
    halo_list_contracts,
    halo_list_sites,
    halo_list_users,
)

TOKEN = {"access_token": "tok", "token_type": "Bearer", "expires_in": 3600}


def _client_for(resource_handler) -> HaloClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json=TOKEN)
        return resource_handler(request)

    return HaloClient(
        base_url="https://test.halopsa.com",
        client_id="cid",
        client_secret="secret",
        transport=httpx.MockTransport(handler),
    )


# ---------------------------------------------------------------------------
# halo_list_clients
# ---------------------------------------------------------------------------


class TestListClients:
    async def test_happy_path(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(
                200, json={"record_count": 1, "clients": [{"id": 501, "name": "Acme Corp"}]}
            )

        client = _client_for(handler)
        out = await halo_list_clients(client)
        await client.close()

        assert captured["path"] == "/api/Client"
        data = json.loads(out)
        assert data["items"][0]["id"] == 501
        assert data["items"][0]["name"] == "Acme Corp"

    async def test_search_forwarded(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"clients": []})

        client = _client_for(handler)
        await halo_list_clients(client, search="acme")
        await client.close()

        assert captured["params"].get("search") == "acme"


# ---------------------------------------------------------------------------
# halo_list_sites
# ---------------------------------------------------------------------------


class TestListSites:
    async def test_happy_path(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json={"sites": [{"id": 601, "name": "Acme HQ"}]})

        client = _client_for(handler)
        out = await halo_list_sites(client)
        await client.close()

        assert captured["path"] == "/api/Site"
        assert json.loads(out)["items"][0]["id"] == 601

    async def test_customer_and_search_forwarded(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"sites": []})

        client = _client_for(handler)
        await halo_list_sites(client, customer="501", search="HQ")
        await client.close()

        assert captured["params"].get("client_id") == "501"
        assert captured["params"].get("search") == "HQ"

    async def test_customer_name_resolved(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/Client":
                return httpx.Response(200, json={"clients": [{"id": 501, "name": "Acme"}]})
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"sites": []})

        client = _client_for(handler)
        await halo_list_sites(client, customer="Acme")
        await client.close()

        assert captured["params"].get("client_id") == "501"


# ---------------------------------------------------------------------------
# halo_list_users
# ---------------------------------------------------------------------------


class TestListUsers:
    async def test_happy_path(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(
                200, json={"users": [{"id": 801, "name": "Jane Doe", "emailaddress": "jane@acme.test"}]}
            )

        client = _client_for(handler)
        out = await halo_list_users(client)
        await client.close()

        assert captured["path"] == "/api/Users"
        data = json.loads(out)
        assert data["items"][0]["id"] == 801
        assert data["items"][0]["emailaddress"] == "jane@acme.test"

    async def test_filters_forwarded(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"users": []})

        client = _client_for(handler)
        await halo_list_users(client, customer="501", site_id=601, search="jane")
        await client.close()

        p = captured["params"]
        assert p.get("client_id") == "501"
        assert p.get("site_id") == "601"
        assert p.get("search") == "jane"


# ---------------------------------------------------------------------------
# halo_list_contracts
# ---------------------------------------------------------------------------


class TestListContracts:
    async def test_happy_path(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(
                200, json={"contracts": [{"id": 901, "ref": "CONTRACT-1", "client_id": 501}]}
            )

        client = _client_for(handler)
        out = await halo_list_contracts(client)
        await client.close()

        assert captured["path"] == "/api/ClientContract"
        data = json.loads(out)
        assert data["items"][0]["id"] == 901
        assert data["items"][0]["ref"] == "CONTRACT-1"

    async def test_customer_forwarded(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"contracts": []})

        client = _client_for(handler)
        await halo_list_contracts(client, customer="501")
        await client.close()

        assert captured["params"].get("client_id") == "501"
