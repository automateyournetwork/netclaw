"""Async HTTP client for the Auvik API.

Handles:
- HTTP Basic authentication (username + API key)
- Rate limiter integration (optional)
- Structured error returns for 401/403, network errors, timeouts
- 429/Retry-After back-off with capped retries (get)
- Auto-paginating get_all() driven by links.next (never meta.totalPages)

Environment Variables (used by callers; not read here):
    AUVIK_USERNAME: Auvik account username
    AUVIK_API_KEY: Auvik API key (used as HTTP Basic password)
"""

import asyncio
import logging
from typing import Any, Optional

import httpx

from utils.pagination import merge_page, next_cursor_url
from utils.rate_limiter import parse_retry_after

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


class AuvikClient:
    """Async HTTP client for the Auvik REST API (JSON:API, cursor pagination)."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        verify_ssl: bool = True,
        timeout: int = 30,
        rate_limiter=None,
        transport=None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._verify_ssl = verify_ssl
        self._timeout = timeout
        self._rate_limiter = rate_limiter
        self._transport = transport
        self._client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.AsyncClient:
        """Return (and lazily create) the shared AsyncClient."""
        if self._client is None or self._client.is_closed:
            kwargs: dict[str, Any] = {
                "base_url": self._base_url,
                "auth": httpx.BasicAuth(self._username, self._password),
                "verify": self._verify_ssl,
                "timeout": httpx.Timeout(self._timeout),
                "headers": {"Accept": "application/vnd.api+json"},
            }
            if self._transport is not None:
                kwargs["transport"] = self._transport
            self._client = httpx.AsyncClient(**kwargs)
        return self._client

    @staticmethod
    def _auth_error(status_code: int) -> dict[str, Any]:
        return {
            "success": False,
            "data": None,
            "error": (
                f"Auvik API authentication failed (HTTP {status_code}). "
                "Check AUVIK_USERNAME and AUVIK_API_KEY environment variables."
            ),
        }

    @staticmethod
    def _rate_limited_error() -> dict[str, Any]:
        return {
            "success": False,
            "data": None,
            "error": "Auvik API rate limited (429 RateLimited): max retries exhausted.",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(
        self,
        path: str,
        params: Optional[dict] = None,
        _max_retries: int = _MAX_RETRIES,
    ) -> dict[str, Any]:
        """Issue a GET request, returning a structured result dict.

        Args:
            path:   URL path (relative to base_url) or absolute URL for pagination.
            params: Optional query parameters.

        Returns:
            {"success": True, "data": <parsed json>, "error": None}
            or
            {"success": False, "data": None, "error": "<message>"}
        """
        if self._rate_limiter is not None:
            await self._rate_limiter.acquire()

        client = self._get_client()

        attempt = 0
        while True:
            try:
                resp = await client.get(path, params=params)
            except httpx.ConnectError as exc:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Auvik API connection error: {exc}",
                }
            except httpx.TimeoutException as exc:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Auvik API request timed out: {exc}",
                }

            if resp.status_code in (401, 403):
                return self._auth_error(resp.status_code)

            if resp.status_code == 429:
                attempt += 1
                if attempt > _max_retries:
                    return self._rate_limited_error()
                # Pass the httpx Headers object directly: dict(resp.headers)
                # lowercases header names, which loses the "Retry-After" lookup.
                delay = parse_retry_after(resp.headers) or 1
                await asyncio.sleep(delay)
                # Re-acquire rate limiter slot after sleeping
                if self._rate_limiter is not None:
                    await self._rate_limiter.acquire()
                continue

            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                return {
                    "success": False,
                    "data": None,
                    "error": (
                        f"Auvik API returned HTTP {exc.response.status_code}: "
                        f"{exc.response.text[:200]}"
                    ),
                }

            # Some Auvik 2xx responses carry no body (e.g. the credential-verify
            # endpoint returns an empty 200). Don't assume JSON — guard the parse.
            if not resp.content:
                return {"success": True, "data": None, "error": None}
            try:
                return {"success": True, "data": resp.json(), "error": None}
            except ValueError:
                return {"success": True, "data": {"raw": resp.text}, "error": None}

    async def get_all(
        self,
        path: str,
        params: Optional[dict] = None,
        max_pages: int = 50,
    ) -> dict[str, Any]:
        """Fetch all pages for a resource, auto-following links.next.

        Args:
            path:      Initial URL path (relative or absolute).
            params:    Query parameters for the first request.
            max_pages: Stop after this many pages (truncation guard).

        Returns:
            {
                "items":       [<merged data items>],
                "page_count":  <int>,
                "truncated":   <bool>,
                "next_cursor": <str | None>,
            }
            On mid-pagination error, also includes "error": <str>.
        """
        items: list = []
        page_count = 0
        current_path = path
        current_params = params
        next_url: Optional[str] = None

        while True:
            result = await self.get(current_path, params=current_params)
            if not result["success"]:
                return {
                    "items": items,
                    "page_count": page_count,
                    "truncated": True,
                    "next_cursor": current_path if page_count > 0 else None,
                    "error": result["error"],
                }

            payload = result["data"]
            merge_page(items, payload)
            page_count += 1
            next_url = next_cursor_url(payload)

            if not next_url or page_count >= max_pages:
                truncated = bool(next_url and page_count >= max_pages)
                return {
                    "items": items,
                    "page_count": page_count,
                    "truncated": truncated,
                    "next_cursor": next_url if truncated else None,
                }

            # Follow next page using the absolute URL from links.next
            current_path = next_url
            current_params = None  # Params are embedded in the next URL

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

