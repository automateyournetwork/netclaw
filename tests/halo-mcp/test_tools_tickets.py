"""Tests for the ticket READ tools in tools/tickets.py.

Covers halo_get_ticket, halo_list_tickets, halo_get_ticket_actions and
halo_get_asset_tickets. The gated write (halo_create_change_request) has its
own module (test_tools_create_change_request.py).
"""

import json

import httpx
import pytest

from clients.halo_client import HaloClient
from tools.tickets import (
    halo_get_asset_tickets,
    halo_get_ticket,
    halo_get_ticket_actions,
    halo_list_tickets,
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
# halo_get_ticket
# ---------------------------------------------------------------------------


class TestGetTicket:
    async def test_non_numeric_is_validation_error(self):
        called = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            called["n"] += 1
            return httpx.Response(200, json={})

        client = _client_for(handler)
        out = await halo_get_ticket(client, ticket="not-a-number")
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
                json={"id": 123, "summary": "VPN down", "details": "full detail", "tickettype_id": 9},
            )

        client = _client_for(handler)
        out = await halo_get_ticket(client, ticket="123")
        await client.close()

        assert captured["path"] == "/api/Tickets/123"
        assert captured["params"].get("includedetails") == "true"
        assert captured["params"].get("includelinkedobjects") == "true"
        data = json.loads(out)
        assert data["id"] == 123
        assert data["summary"] == "VPN down"
        assert data["details"] == "full detail"


# ---------------------------------------------------------------------------
# halo_list_tickets
# ---------------------------------------------------------------------------


class TestListTickets:
    async def test_happy_path_drops_details(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(
                200,
                json={"record_count": 1, "tickets": [{"id": 1, "summary": "S", "details": "should be dropped"}]},
            )

        client = _client_for(handler)
        out = await halo_list_tickets(client)
        await client.close()

        assert captured["path"] == "/api/Tickets"
        data = json.loads(out)
        assert data["items"][0]["id"] == 1
        # List shaping uses include_details=False.
        assert "details" not in data["items"][0]

    async def test_filters_forwarded(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"tickets": []})

        client = _client_for(handler)
        # ticket_type + customer as numeric ids → resolver passthrough.
        await halo_list_tickets(
            client,
            ticket_type="9",
            customer="501",
            asset_id=42,
            status="open",
            open_only=True,
            search="vpn",
        )
        await client.close()

        p = captured["params"]
        assert p.get("requesttype_id") == "9"
        assert p.get("client_id") == "501"
        assert p.get("asset_id") == "42"
        assert p.get("status") == "open"
        assert p.get("open_only") == "true"
        assert p.get("search") == "vpn"

    async def test_ticket_type_name_resolved(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/TicketType":
                return httpx.Response(200, json={"tickettypes": [{"id": 9, "name": "Change"}]})
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"tickets": []})

        client = _client_for(handler)
        await halo_list_tickets(client, ticket_type="Change")
        await client.close()

        assert captured["params"].get("requesttype_id") == "9"

    async def test_customer_ambiguous(self):
        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/Client":
                # Both are substring (not exact) matches for "Acme" → ambiguous.
                return httpx.Response(
                    200,
                    json={"clients": [{"id": 1, "name": "Acme Corp"}, {"id": 2, "name": "Acme Staging"}]},
                )
            return httpx.Response(200, json={"tickets": []})

        client = _client_for(handler)
        out = await halo_list_tickets(client, customer="Acme")
        await client.close()

        assert json.loads(out)["error"]["code"] == "Ambiguous"


# ---------------------------------------------------------------------------
# halo_get_ticket_actions
# ---------------------------------------------------------------------------


class TestGetTicketActions:
    async def test_non_numeric_is_validation_error(self):
        called = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            called["n"] += 1
            return httpx.Response(200, json={})

        client = _client_for(handler)
        out = await halo_get_ticket_actions(client, ticket="bad")
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
                json={"actions": [{"id": 55, "note": "did a thing", "who": "agent"}]},
            )

        client = _client_for(handler)
        out = await halo_get_ticket_actions(client, ticket="123")
        await client.close()

        assert captured["path"] == "/api/Actions"
        assert captured["params"].get("ticket_id") == "123"
        data = json.loads(out)
        assert data["items"][0]["id"] == 55
        assert data["items"][0]["note"] == "did a thing"


# ---------------------------------------------------------------------------
# halo_get_asset_tickets
# ---------------------------------------------------------------------------


class TestGetAssetTickets:
    async def test_blank_asset_is_validation_error(self):
        called = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            called["n"] += 1
            return httpx.Response(200, json={})

        client = _client_for(handler)
        out = await halo_get_asset_tickets(client, asset="")
        await client.close()

        assert called["n"] == 0
        assert json.loads(out)["error"]["code"] == "ValidationError"

    async def test_happy_path_numeric_asset(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"tickets": [{"id": 1, "summary": "S"}]})

        client = _client_for(handler)
        out = await halo_get_asset_tickets(client, asset="701", open_only=True)
        await client.close()

        assert captured["path"] == "/api/Tickets"
        assert captured["params"].get("asset_id") == "701"
        assert captured["params"].get("open_only") == "true"
        assert json.loads(out)["items"][0]["id"] == 1

    async def test_asset_name_resolved(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/Asset":
                return httpx.Response(
                    200, json={"assets": [{"id": 701, "inventory_number": "SW-CORE-01"}]}
                )
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"tickets": []})

        client = _client_for(handler)
        await halo_get_asset_tickets(client, asset="SW-CORE-01")
        await client.close()

        assert captured["params"].get("asset_id") == "701"

    async def test_asset_not_found(self):
        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/Asset":
                return httpx.Response(200, json={"assets": []})
            return httpx.Response(200, json={"tickets": []})

        client = _client_for(handler)
        out = await halo_get_asset_tickets(client, asset="ghost")
        await client.close()

        assert json.loads(out)["error"]["code"] == "NotFound"
