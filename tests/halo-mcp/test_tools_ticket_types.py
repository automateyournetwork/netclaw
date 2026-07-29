"""Tests for tools/ticket_types.py — halo_list_ticket_types, halo_get_ticket_type.

Each test uses a real HaloClient backed by httpx.MockTransport; ``_client_for``
auto-serves the OAuth token endpoint so the per-test handler only has to answer
the ``/api/*`` resource request(s). Assertions cover path/params, shaping, and
name-resolution edge cases (ambiguous / not-found / validation).
"""

import json

import httpx
import pytest

from clients.halo_client import HaloClient
from tools.ticket_types import halo_get_ticket_type, halo_list_ticket_types

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
# halo_list_ticket_types
# ---------------------------------------------------------------------------


class TestListTicketTypes:
    async def test_happy_path(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(
                200, json={"record_count": 1, "tickettypes": [{"id": 9, "name": "Change"}]}
            )

        client = _client_for(handler)
        out = await halo_list_ticket_types(client)
        await client.close()

        assert captured["path"] == "/api/TicketType"
        data = json.loads(out)
        assert data["items"][0]["id"] == 9
        assert data["items"][0]["name"] == "Change"

    async def test_filters_forwarded(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"tickettypes": []})

        client = _client_for(handler)
        # customer as numeric id → resolver passthrough (no extra /Client call).
        await halo_list_ticket_types(
            client, can_create_only=True, customer="501", showcounts=True
        )
        await client.close()

        assert captured["params"].get("can_create_only") == "true"
        assert captured["params"].get("client_id") == "501"
        assert captured["params"].get("showcounts") == "true"

    async def test_customer_name_resolved(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/Client":
                return httpx.Response(200, json={"clients": [{"id": 501, "name": "Acme"}]})
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"tickettypes": []})

        client = _client_for(handler)
        await halo_list_ticket_types(client, customer="Acme")
        await client.close()

        assert captured["params"].get("client_id") == "501"

    async def test_customer_not_found(self):
        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/Client":
                return httpx.Response(200, json={"clients": []})
            return httpx.Response(200, json={"tickettypes": []})

        client = _client_for(handler)
        out = await halo_list_ticket_types(client, customer="Ghost")
        await client.close()

        assert json.loads(out)["error"]["code"] == "NotFound"

    async def test_raw_returns_untouched_items(self):
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"tickettypes": [{"id": 9, "name": "Change", "extra": "kept"}]},
            )

        client = _client_for(handler)
        out = await halo_list_ticket_types(client, raw=True)
        await client.close()

        data = json.loads(out)
        assert data["items"][0]["extra"] == "kept"


# ---------------------------------------------------------------------------
# halo_get_ticket_type
# ---------------------------------------------------------------------------


class TestGetTicketType:
    async def test_missing_ticket_type_is_validation_error(self):
        called = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            called["n"] += 1
            return httpx.Response(200, json={})

        client = _client_for(handler)
        out = await halo_get_ticket_type(client, ticket_type="   ")
        await client.close()

        assert called["n"] == 0
        assert json.loads(out)["error"]["code"] == "ValidationError"

    async def test_by_numeric_id_includes_field_schema(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(
                200,
                json={
                    "id": 9,
                    "name": "Change",
                    "fields": [
                        {
                            "fieldid": 142,
                            "fieldname": "Impact",
                            "agentcheckboxmandatory": True,
                            "fieldinfo": {"id": 142, "name": "Impact", "values": [{"id": 1, "name": "High"}]},
                        }
                    ],
                },
            )

        client = _client_for(handler)
        out = await halo_get_ticket_type(client, ticket_type="9")
        await client.close()

        assert captured["path"] == "/api/TicketType/9"
        assert captured["params"].get("includedetails") == "true"
        data = json.loads(out)
        assert data["id"] == 9
        assert data["fields"][0]["fieldid"] == 142
        assert data["fields"][0]["required_agent"] is True
        assert data["fields"][0]["fieldinfo"]["values"][0]["name"] == "High"

    async def test_by_name_resolves_then_reads_detail(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/TicketType":
                return httpx.Response(200, json={"tickettypes": [{"id": 9, "name": "Change Request"}]})
            captured["path"] = req.url.path
            return httpx.Response(200, json={"id": 9, "name": "Change Request"})

        client = _client_for(handler)
        out = await halo_get_ticket_type(client, ticket_type="Change Request")
        await client.close()

        assert captured["path"] == "/api/TicketType/9"
        assert json.loads(out)["id"] == 9

    async def test_ambiguous_name(self):
        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/TicketType":
                return httpx.Response(
                    200,
                    json={"tickettypes": [{"id": 9, "name": "Change A"}, {"id": 10, "name": "Change B"}]},
                )
            return httpx.Response(200, json={})

        client = _client_for(handler)
        out = await halo_get_ticket_type(client, ticket_type="Change")
        await client.close()

        assert json.loads(out)["error"]["code"] == "Ambiguous"
