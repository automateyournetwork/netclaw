"""Safety-critical tests for halo_create_change_request (the ONE gated write).

Contract under test:
  * ``submit=False`` (the default) performs NO write — the handler must record
    ZERO POST requests to ``/api/Tickets`` and the return must be a preview whose
    ``body`` is a one-element array carrying tickettype_id / summary / details
    (+ normalized customfields).
  * ``submit=True`` fires EXACTLY ONE ``POST /api/Tickets`` with that same array
    body.
  * Missing/blank required params fail validation with NO HTTP call at all.
"""

import json

import httpx
import pytest

from clients.halo_client import HaloClient
from tools.tickets import halo_create_change_request

TOKEN = {"access_token": "tok", "token_type": "Bearer", "expires_in": 3600}


class _Recorder:
    """Handler wrapper that records POSTs to /api/Tickets and all resource hits."""

    def __init__(self, resource_handler=None):
        self.ticket_posts: list = []  # bodies POSTed to /api/Tickets
        self.resource_calls = 0
        self._resource_handler = resource_handler

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json=TOKEN)
        self.resource_calls += 1
        if request.method == "POST" and request.url.path == "/api/Tickets":
            self.ticket_posts.append(json.loads(request.content))
        if self._resource_handler is not None:
            return self._resource_handler(request)
        return httpx.Response(200, json=[{"id": 555}])


def _client_for(recorder: _Recorder) -> HaloClient:
    return HaloClient(
        base_url="https://test.halopsa.com",
        client_id="cid",
        client_secret="secret",
        transport=httpx.MockTransport(recorder),
    )


# ---------------------------------------------------------------------------
# Validation — no HTTP call at all
# ---------------------------------------------------------------------------


class TestValidation:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"summary": "", "details": "D", "ticket_type": "9"},
            {"summary": "S", "details": "  ", "ticket_type": "9"},
            {"summary": "S", "details": "D", "ticket_type": ""},
            {"summary": None, "details": None, "ticket_type": None},
        ],
    )
    async def test_missing_required_fields_no_http(self, kwargs):
        rec = _Recorder()
        client = _client_for(rec)
        out = await halo_create_change_request(client, **kwargs)
        await client.close()

        assert rec.resource_calls == 0, "validation must not touch the API"
        assert rec.ticket_posts == []
        assert json.loads(out)["error"]["code"] == "ValidationError"

    async def test_validation_lists_missing_fields(self):
        rec = _Recorder()
        client = _client_for(rec)
        out = await halo_create_change_request(client, summary="", details="", ticket_type="9")
        await client.close()

        details = json.loads(out)["error"]["details"]
        assert "summary" in details
        assert "details" in details

    async def test_non_numeric_user_is_validation_error(self):
        rec = _Recorder()
        client = _client_for(rec)
        out = await halo_create_change_request(
            client, summary="S", details="D", ticket_type="9", user="alice"
        )
        await client.close()

        assert rec.ticket_posts == []
        assert json.loads(out)["error"]["code"] == "ValidationError"


# ---------------------------------------------------------------------------
# Preview (submit=False, the default) — ZERO POSTs
# ---------------------------------------------------------------------------


class TestPreview:
    async def test_preview_records_zero_posts_and_returns_body(self):
        rec = _Recorder()
        client = _client_for(rec)
        out = await halo_create_change_request(
            client,
            summary="Upgrade core switch",
            details="Firmware bump on SW-CORE-01",
            ticket_type="9",
            custom_fields={"142": "High", "Reason": "maintenance"},
        )
        await client.close()

        # No write of any kind — numeric ticket_type also means no resolver call.
        assert rec.ticket_posts == [], "preview must POST nothing"
        assert rec.resource_calls == 0

        data = json.loads(out)
        assert data["preview"] is True
        assert data["would_post"] == "/api/Tickets"

        body = data["body"]
        assert isinstance(body, list) and len(body) == 1
        obj = body[0]
        assert obj["tickettype_id"] == 9
        assert obj["summary"] == "Upgrade core switch"
        assert obj["details"] == "Firmware bump on SW-CORE-01"
        # Normalized customfields: numeric key -> id, non-numeric -> name.
        assert {"id": 142, "value": "High"} in obj["customfields"]
        assert {"name": "Reason", "value": "maintenance"} in obj["customfields"]

    async def test_preview_default_is_submit_false(self):
        """Calling with no submit kwarg behaves as a preview (no POST)."""
        rec = _Recorder()
        client = _client_for(rec)
        out = await halo_create_change_request(
            client, summary="S", details="D", ticket_type="9"
        )
        await client.close()

        assert rec.ticket_posts == []
        assert json.loads(out)["preview"] is True

    async def test_preview_omits_empty_optional_fields(self):
        rec = _Recorder()
        client = _client_for(rec)
        out = await halo_create_change_request(
            client, summary="S", details="D", ticket_type="9"
        )
        await client.close()

        obj = json.loads(out)["body"][0]
        assert "client_id" not in obj
        assert "site_id" not in obj
        assert "assets" not in obj
        assert "customfields" not in obj


# ---------------------------------------------------------------------------
# Submit (submit=True) — EXACTLY ONE POST
# ---------------------------------------------------------------------------


class TestSubmit:
    async def test_submit_fires_exactly_one_post_with_array_body(self):
        rec = _Recorder()
        client = _client_for(rec)
        out = await halo_create_change_request(
            client,
            summary="Upgrade core switch",
            details="Firmware bump",
            ticket_type="9",
            custom_fields={"142": "High"},
            submit=True,
        )
        await client.close()

        assert len(rec.ticket_posts) == 1, "exactly one POST /api/Tickets"
        posted = rec.ticket_posts[0]
        assert isinstance(posted, list) and len(posted) == 1
        assert posted[0]["tickettype_id"] == 9
        assert posted[0]["summary"] == "Upgrade core switch"
        assert posted[0]["details"] == "Firmware bump"
        assert posted[0]["customfields"] == [{"id": 142, "value": "High"}]

        assert json.loads(out)["created"] is True

    async def test_preview_body_matches_submitted_body(self):
        """The previewed body is exactly what a subsequent submit POSTs."""
        rec_preview = _Recorder()
        client_p = _client_for(rec_preview)
        preview_out = await halo_create_change_request(
            client_p,
            summary="S",
            details="D",
            ticket_type="9",
            custom_fields={"142": "High"},
        )
        await client_p.close()
        preview_body = json.loads(preview_out)["body"]

        rec_submit = _Recorder()
        client_s = _client_for(rec_submit)
        await halo_create_change_request(
            client_s,
            summary="S",
            details="D",
            ticket_type="9",
            custom_fields={"142": "High"},
            submit=True,
        )
        await client_s.close()

        assert rec_submit.ticket_posts[0] == preview_body

    async def test_submit_includes_resolved_customer_and_asset(self):
        def resource(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/Client":
                return httpx.Response(200, json={"clients": [{"id": 501, "name": "Acme"}]})
            if req.url.path == "/api/Asset":
                return httpx.Response(
                    200, json={"assets": [{"id": 701, "inventory_number": "SW-CORE-01"}]}
                )
            return httpx.Response(200, json=[{"id": 555}])

        rec = _Recorder(resource)
        client = _client_for(rec)
        await halo_create_change_request(
            client,
            summary="S",
            details="D",
            ticket_type="9",
            customer="Acme",
            asset="SW-CORE-01",
            user=42,
            submit=True,
        )
        await client.close()

        posted = rec.ticket_posts[0][0]
        assert posted["client_id"] == 501
        assert posted["user_id"] == 42
        assert posted["assets"] == [{"id": 701}]

    async def test_ambiguous_ticket_type_no_post(self):
        def resource(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/TicketType":
                return httpx.Response(
                    200,
                    json={"tickettypes": [{"id": 9, "name": "Change A"}, {"id": 10, "name": "Change B"}]},
                )
            return httpx.Response(200, json=[{"id": 555}])

        rec = _Recorder(resource)
        client = _client_for(rec)
        out = await halo_create_change_request(
            client, summary="S", details="D", ticket_type="Change", submit=True
        )
        await client.close()

        assert rec.ticket_posts == [], "must not POST when ticket type is ambiguous"
        assert json.loads(out)["error"]["code"] == "Ambiguous"
