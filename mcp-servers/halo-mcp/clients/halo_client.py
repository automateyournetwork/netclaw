"""Async HTTP client for the Halo (HaloPSA / HaloITSM / HaloCRM) API.

Handles:
- OAuth2 **client-credentials** token acquisition, caching, and refresh
- ``Authorization: Bearer <token>`` on every ``/api/*`` request
- Structured ``{"success", "data", "error"}`` returns (never raises to callers)
- 401 -> one transparent token refresh + retry
- 429 / Retry-After backoff with capped retries
- Page-based pagination (``pageinate``/``page_no``/``page_size``) via ``get_all()``
- A single write path (``post``) for creating tickets

The token endpoint lives on the auth server (``<base>/auth/token``), which is a
different path from the resource API (``<base>/api``). Both are reachable through
the same host, so a single injected ``transport`` (used by tests) intercepts both.

Environment variables (read by the caller, not here):
    HALO_BASE_URL, HALO_TENANT, HALO_CLIENT_ID, HALO_CLIENT_SECRET, HALO_SCOPE
"""

import asyncio
import logging
import time
from typing import Any, Optional

import httpx

from utils.constants import API_PREFIX, AUTH_TOKEN_PATH, DEFAULT_SCOPE
from utils.pagination import extract_list
from utils.rate_limiter import parse_retry_after

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
# Refresh the token this many seconds before its stated expiry.
_EXPIRY_SKEW = 60


class HaloClient:
    """Async client for the Halo REST API (OAuth2 client-credentials, page paging)."""

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        tenant: Optional[str] = None,
        scope: str = DEFAULT_SCOPE,
        auth_url: Optional[str] = None,
        verify_ssl: bool = True,
        timeout: int = 30,
        page_size: int = 50,
        max_pages: int = 20,
        rate_limiter=None,
        transport=None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        # Auth server token endpoint (absolute). Overridable for self-hosted layouts.
        self._auth_url = auth_url or f"{self._base_url}{AUTH_TOKEN_PATH}"
        self._client_id = client_id
        self._client_secret = client_secret
        self._tenant = tenant
        self._scope = scope
        self._verify_ssl = verify_ssl
        self._timeout = timeout
        self._page_size = page_size
        self._max_pages = max_pages
        self._rate_limiter = rate_limiter
        self._transport = transport

        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0  # monotonic deadline
        self._token_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.AsyncClient:
        """Return (and lazily create) the shared resource-API AsyncClient."""
        if self._client is None or self._client.is_closed:
            kwargs: dict[str, Any] = {
                "base_url": self._base_url,  # host; paths carry the /api prefix
                "verify": self._verify_ssl,
                "timeout": httpx.Timeout(self._timeout),
                "headers": {"Accept": "application/json"},
            }
            if self._transport is not None:
                kwargs["transport"] = self._transport
            self._client = httpx.AsyncClient(**kwargs)
        return self._client

    async def _ensure_token(self, force: bool = False) -> Optional[dict]:
        """Ensure a valid bearer token is cached.

        Returns None on success, or a ``{success:False,...}`` error envelope on
        failure (so callers can surface it without a token being available).
        """
        async with self._token_lock:
            if not force and self._token and time.monotonic() < self._token_expiry:
                return None

            data = {
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": self._scope,
            }
            if self._tenant:
                data["tenant"] = self._tenant

            try:
                async with httpx.AsyncClient(
                    verify=self._verify_ssl,
                    timeout=httpx.Timeout(self._timeout),
                    transport=self._transport,
                ) as auth_client:
                    resp = await auth_client.post(self._auth_url, data=data)
            except httpx.HTTPError as exc:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Halo token request failed: {exc}",
                }

            if resp.status_code != 200:
                return {
                    "success": False,
                    "data": None,
                    "error": (
                        f"Halo token endpoint returned HTTP {resp.status_code}: "
                        f"{resp.text[:200]}. Check HALO_CLIENT_ID / HALO_CLIENT_SECRET / "
                        "HALO_TENANT / HALO_SCOPE."
                    ),
                }

            try:
                body = resp.json()
            except ValueError:
                return {
                    "success": False,
                    "data": None,
                    "error": "Halo token endpoint returned a non-JSON body.",
                }

            token = body.get("access_token")
            if not token:
                return {
                    "success": False,
                    "data": None,
                    "error": "Halo token response did not contain an access_token.",
                }

            self._token = token
            expires_in = int(body.get("expires_in", 3600) or 3600)
            self._token_expiry = time.monotonic() + max(30, expires_in - _EXPIRY_SKEW)
            logger.info("Halo token acquired (expires_in=%ss)", expires_in)
            return None

    @staticmethod
    def _auth_error(status_code: int) -> dict[str, Any]:
        return {
            "success": False,
            "data": None,
            "error": (
                f"Halo API authentication failed (HTTP {status_code}). Check the API "
                "application's client id/secret and that its permissions cover this "
                "endpoint (HALO_CLIENT_ID / HALO_CLIENT_SECRET / HALO_SCOPE)."
            ),
        }

    @staticmethod
    def _rate_limited_error() -> dict[str, Any]:
        return {
            "success": False,
            "data": None,
            "error": "Halo API rate limited (HTTP 429): max retries exhausted.",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(
        self,
        path: str,
        params: Optional[dict] = None,
        _retry_auth: bool = True,
    ) -> dict[str, Any]:
        """GET a resource path (relative to ``/api``), returning a result dict.

        Args:
            path: Resource path WITHOUT the ``/api`` prefix, e.g. ``/Tickets/123``.
            params: Optional query parameters.

        Returns:
            ``{"success": True, "data": <parsed json>, "error": None}`` or
            ``{"success": False, "data": None, "error": "<message>"}``.
        """
        if self._rate_limiter is not None:
            await self._rate_limiter.acquire()

        token_err = await self._ensure_token()
        if token_err:
            return token_err

        client = self._get_client()
        full_path = f"{API_PREFIX}{path}"
        attempt = 0
        while True:
            headers = {"Authorization": f"Bearer {self._token}"}
            try:
                resp = await client.get(full_path, params=params, headers=headers)
            except httpx.ConnectError as exc:
                return {"success": False, "data": None, "error": f"Halo API connection error: {exc}"}
            except httpx.TimeoutException as exc:
                return {"success": False, "data": None, "error": f"Halo API request timed out: {exc}"}

            if resp.status_code == 401 and _retry_auth:
                # Token may have been revoked/expired server-side; refresh once.
                token_err = await self._ensure_token(force=True)
                if token_err:
                    return token_err
                _retry_auth = False
                continue

            if resp.status_code in (401, 403):
                return self._auth_error(resp.status_code)

            if resp.status_code == 429:
                attempt += 1
                if attempt > _MAX_RETRIES:
                    return self._rate_limited_error()
                delay = parse_retry_after(resp.headers) or 1
                await asyncio.sleep(delay)
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
                        f"Halo API returned HTTP {exc.response.status_code}: "
                        f"{exc.response.text[:200]}"
                    ),
                }

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
        max_pages: Optional[int] = None,
    ) -> dict[str, Any]:
        """Fetch all pages of a Halo list endpoint (page-based pagination).

        Returns:
            ``{"items": [...], "page_count": int, "truncated": bool,
               "next_page": int|None, "record_count": int|None}``. On a
            mid-pagination error, also includes ``"error"``.
        """
        max_pages = max_pages or self._max_pages
        params = dict(params or {})
        params.setdefault("pageinate", "true")
        params.setdefault("page_size", self._page_size)

        items: list = []
        page_count = 0
        record_count: Optional[int] = None
        page_no = 1

        while True:
            params["page_no"] = page_no
            result = await self.get(path, params=params)
            if not result["success"]:
                return {
                    "items": items,
                    "page_count": page_count,
                    "truncated": True,
                    "next_page": page_no,
                    "error": result["error"],
                }

            page_items, record_count = extract_list(result["data"] or {})
            items.extend(page_items)
            page_count += 1

            # Done when this page under-fills, the endpoint returned nothing, or
            # we've collected the full record_count.
            got_all = record_count is not None and len(items) >= record_count
            short_page = len(page_items) < int(params["page_size"])
            if got_all or short_page or not page_items:
                return {
                    "items": items,
                    "page_count": page_count,
                    "truncated": False,
                    "next_page": None,
                    "record_count": record_count,
                }

            if page_count >= max_pages:
                return {
                    "items": items,
                    "page_count": page_count,
                    "truncated": True,
                    "next_page": page_no + 1,
                    "record_count": record_count,
                }

            page_no += 1

    async def post(self, path: str, body: Any) -> dict[str, Any]:
        """POST a JSON body to a resource path (the one write path).

        Halo's ticket create/update endpoint expects an ARRAY body; callers pass
        the already-wrapped payload. Returns the same result-dict envelope as get().
        """
        if self._rate_limiter is not None:
            await self._rate_limiter.acquire()

        token_err = await self._ensure_token()
        if token_err:
            return token_err

        client = self._get_client()
        full_path = f"{API_PREFIX}{path}"
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            resp = await client.post(full_path, json=body, headers=headers)
        except httpx.ConnectError as exc:
            return {"success": False, "data": None, "error": f"Halo API connection error: {exc}"}
        except httpx.TimeoutException as exc:
            return {"success": False, "data": None, "error": f"Halo API request timed out: {exc}"}

        if resp.status_code in (401, 403):
            return self._auth_error(resp.status_code)

        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return {
                "success": False,
                "data": None,
                "error": (
                    f"Halo API returned HTTP {exc.response.status_code}: "
                    f"{exc.response.text[:300]}"
                ),
            }

        if not resp.content:
            return {"success": True, "data": None, "error": None}
        try:
            return {"success": True, "data": resp.json(), "error": None}
        except ValueError:
            return {"success": True, "data": {"raw": resp.text}, "error": None}

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
