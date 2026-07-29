"""Tests for tools/assets.py — halo_get_asset, halo_list_assets,
halo_get_asset_relationships."""

import json

import httpx
import pytest

from clients.halo_client import HaloClient
from tools.assets import (
    halo_get_asset,
    halo_get_asset_relationships,
    halo_list_assets,
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
# halo_get_asset
# ---------------------------------------------------------------------------


class TestGetAsset:
    async def test_blank_is_validation_error(self):
        called = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            called["n"] += 1
            return httpx.Response(200, json={})

        client = _client_for(handler)
        out = await halo_get_asset(client, asset="   ")
        await client.close()

        assert called["n"] == 0
        assert json.loads(out)["error"]["code"] == "ValidationError"

    async def test_happy_path_numeric(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(
                200, json={"id": 701, "inventory_number": "SW-CORE-01", "assettype_id": 3}
            )

        client = _client_for(handler)
        out = await halo_get_asset(client, asset="701")
        await client.close()

        assert captured["path"] == "/api/Asset/701"
        assert captured["params"].get("includedetails") == "true"
        data = json.loads(out)
        assert data["id"] == 701
        assert data["inventory_number"] == "SW-CORE-01"

    async def test_name_resolved_then_detail(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/Asset":
                return httpx.Response(
                    200, json={"assets": [{"id": 701, "inventory_number": "SW-CORE-01"}]}
                )
            captured["path"] = req.url.path
            return httpx.Response(200, json={"id": 701, "inventory_number": "SW-CORE-01"})

        client = _client_for(handler)
        out = await halo_get_asset(client, asset="SW-CORE-01")
        await client.close()

        assert captured["path"] == "/api/Asset/701"
        assert json.loads(out)["id"] == 701

    async def test_not_found(self):
        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/Asset":
                return httpx.Response(200, json={"assets": []})
            return httpx.Response(200, json={})

        client = _client_for(handler)
        out = await halo_get_asset(client, asset="ghost")
        await client.close()

        assert json.loads(out)["error"]["code"] == "NotFound"


# ---------------------------------------------------------------------------
# halo_list_assets
# ---------------------------------------------------------------------------


class TestListAssets:
    async def test_happy_path(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(
                200, json={"record_count": 1, "assets": [{"id": 701, "inventory_number": "SW-CORE-01"}]}
            )

        client = _client_for(handler)
        out = await halo_list_assets(client)
        await client.close()

        assert captured["path"] == "/api/Asset"
        assert json.loads(out)["items"][0]["id"] == 701

    async def test_filters_forwarded(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"assets": []})

        client = _client_for(handler)
        await halo_list_assets(client, customer="501", assettype_id=3, search="switch")
        await client.close()

        p = captured["params"]
        assert p.get("client_id") == "501"
        assert p.get("assettype_id") == "3"
        assert p.get("search") == "switch"

    async def test_customer_name_resolved(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/Client":
                return httpx.Response(200, json={"clients": [{"id": 501, "name": "Acme"}]})
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"assets": []})

        client = _client_for(handler)
        await halo_list_assets(client, customer="Acme")
        await client.close()

        assert captured["params"].get("client_id") == "501"


# ---------------------------------------------------------------------------
# halo_get_asset_relationships
# ---------------------------------------------------------------------------


class TestGetAssetRelationships:
    async def test_blank_is_validation_error(self):
        called = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            called["n"] += 1
            return httpx.Response(200, json={})

        client = _client_for(handler)
        out = await halo_get_asset_relationships(client, asset="")
        await client.close()

        assert called["n"] == 0
        assert json.loads(out)["error"]["code"] == "ValidationError"

    async def test_happy_path(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(
                200,
                json={
                    "id": 701,
                    "hierarchy": [{"id": 800, "name": "child"}],
                    "related_ticket_id": 123,
                    "child_count": 1,
                },
            )

        client = _client_for(handler)
        out = await halo_get_asset_relationships(client, asset="701")
        await client.close()

        assert captured["path"] == "/api/Asset/701"
        assert captured["params"].get("includedetails") == "true"
        assert captured["params"].get("includehierarchy") == "true"
        data = json.loads(out)
        assert data["asset_id"] == "701"
        assert data["hierarchy"] == [{"id": 800, "name": "child"}]
        assert data["related_ticket_id"] == 123
        assert data["child_count"] == 1
