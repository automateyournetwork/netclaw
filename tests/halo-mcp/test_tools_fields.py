"""Tests for tools/fields.py — halo_list_fields, halo_get_field."""

import json

import httpx
import pytest

from clients.halo_client import HaloClient
from tools.fields import halo_get_field, halo_list_fields

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
# halo_list_fields
# ---------------------------------------------------------------------------


class TestListFields:
    async def test_happy_path_includes_values(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(
                200,
                json={
                    "fields": [
                        {"id": 142, "name": "Impact", "values": [{"id": 1, "name": "High"}]}
                    ]
                },
            )

        client = _client_for(handler)
        out = await halo_list_fields(client)
        await client.close()

        assert captured["path"] == "/api/FieldInfo"
        assert captured["params"].get("includevalues") == "true"
        assert "iscustomfieldsetup" not in captured["params"]
        data = json.loads(out)
        assert data["items"][0]["id"] == 142
        assert data["items"][0]["values"][0]["name"] == "High"

    async def test_custom_only_adds_filter(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"fields": []})

        client = _client_for(handler)
        await halo_list_fields(client, custom_only=True)
        await client.close()

        assert captured["params"].get("iscustomfieldsetup") == "true"


# ---------------------------------------------------------------------------
# halo_get_field
# ---------------------------------------------------------------------------


class TestGetField:
    async def test_non_numeric_field_is_validation_error(self):
        called = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            called["n"] += 1
            return httpx.Response(200, json={})

        client = _client_for(handler)
        out = await halo_get_field(client, field="Impact")
        await client.close()

        assert called["n"] == 0
        assert json.loads(out)["error"]["code"] == "ValidationError"

    async def test_by_numeric_id(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"id": 142, "name": "Impact"})

        client = _client_for(handler)
        out = await halo_get_field(client, field="142")
        await client.close()

        assert captured["path"] == "/api/FieldInfo/142"
        assert captured["params"].get("getlookupvalues") == "true"
        assert json.loads(out)["id"] == 142
