"""Tests for tools/knowledge.py — halo_list_kb_articles, halo_get_kb_article."""

import json

import httpx
import pytest

from clients.halo_client import HaloClient
from tools.knowledge import halo_get_kb_article, halo_list_kb_articles

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
# halo_list_kb_articles
# ---------------------------------------------------------------------------


class TestListKBArticles:
    async def test_happy_path(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(
                200,
                json={"articles": [{"id": 11, "name": "Reset VPN", "summary": "How to reset"}]},
            )

        client = _client_for(handler)
        out = await halo_list_kb_articles(client)
        await client.close()

        assert captured["path"] == "/api/KBArticle"
        data = json.loads(out)
        assert data["items"][0]["id"] == 11
        assert data["items"][0]["name"] == "Reset VPN"
        # List shaping does not include the article body.
        assert "article_body" not in data["items"][0]

    async def test_search_forwarded(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"articles": []})

        client = _client_for(handler)
        await halo_list_kb_articles(client, search="vpn")
        await client.close()

        assert captured["params"].get("search") == "vpn"


# ---------------------------------------------------------------------------
# halo_get_kb_article
# ---------------------------------------------------------------------------


class TestGetKBArticle:
    async def test_non_numeric_is_validation_error(self):
        called = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            called["n"] += 1
            return httpx.Response(200, json={})

        client = _client_for(handler)
        out = await halo_get_kb_article(client, article="reset-vpn")
        await client.close()

        assert called["n"] == 0
        assert json.loads(out)["error"]["code"] == "ValidationError"

    async def test_happy_path_includes_body(self):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(
                200,
                json={"id": 11, "name": "Reset VPN", "article": "<p>Step 1...</p>"},
            )

        client = _client_for(handler)
        out = await halo_get_kb_article(client, article="11")
        await client.close()

        assert captured["path"] == "/api/KBArticle/11"
        data = json.loads(out)
        assert data["id"] == 11
        assert data["article_body"] == "<p>Step 1...</p>"
