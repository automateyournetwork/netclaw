"""Nautobot API client for routing protocol operations."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class NautobotError(Exception):
    pass


class NautobotClient:
    def __init__(self):
        self.url = os.environ["NAUTOBOT_URL"].rstrip("/")
        self.token = os.environ["NAUTOBOT_TOKEN"]
        verify = os.environ.get("NAUTOBOT_VERIFY_SSL", "false").lower() == "true"
        timeout = int(os.environ.get("NAUTOBOT_TIMEOUT", "60"))

        self.http = httpx.AsyncClient(
            headers={
                "Authorization": f"Token {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            verify=verify,
            timeout=timeout,
        )

    async def graphql(self, query: str, variables: Optional[dict] = None) -> dict[str, Any]:
        body: dict[str, Any] = {"query": query}
        if variables:
            body["variables"] = variables
        try:
            resp = await self.http.post(f"{self.url}/api/graphql/", json=body)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise NautobotError(f"Nautobot unreachable: {e}")
        self._check(resp)
        data = resp.json()
        if "errors" in data:
            msgs = "; ".join(e.get("message", str(e)) for e in data["errors"])
            raise NautobotError(f"GraphQL error: {msgs}")
        return data.get("data", {})

    async def rest_get(self, endpoint: str, params: Optional[dict] = None) -> dict[str, Any]:
        return await self._rest("GET", endpoint, params=params)

    async def rest_post(self, endpoint: str, data: dict) -> dict[str, Any]:
        return await self._rest("POST", endpoint, json_body=data)

    async def rest_patch(self, endpoint: str, data: dict) -> dict[str, Any]:
        return await self._rest("PATCH", endpoint, json_body=data)

    async def rest_delete(self, endpoint: str) -> None:
        await self._rest("DELETE", endpoint)

    async def _rest(
        self, method: str, endpoint: str,
        params: Optional[dict] = None, json_body: Optional[dict] = None,
    ) -> dict[str, Any]:
        url = f"{self.url}/api/{endpoint.strip('/')}/"
        try:
            resp = await self.http.request(method, url, params=params, json=json_body)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise NautobotError(f"Nautobot unreachable: {e}")
        self._check(resp)
        if resp.status_code == 204:
            return {}
        return resp.json()

    def _check(self, resp: httpx.Response) -> None:
        if resp.status_code in (401, 403):
            raise NautobotError("Authentication failed. Verify NAUTOBOT_TOKEN.")
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text[:500]
            raise NautobotError(f"API error ({resp.status_code}): {detail}")
