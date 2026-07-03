"""Async HTTP client for the Claroty xDome REST API.

xDome is unusual in three ways that this client hides from tool authors:

  1. Every operation is a POST that takes a JSON body (no GETs).
  2. Pagination is offset/limit-in-body, not page tokens or Link headers.
  3. Rate limiting is 2000 calls/min/endpoint with HTTP 429 + Retry-After
     on exhaustion.

Environment variables:
    CLAROTY_API_URL          Base URL (default: https://api.medigate.io)
    CLAROTY_API_TOKEN        Bearer token (required)
    CLAROTY_VERIFY_SSL       Verify TLS (default: true)
    CLAROTY_TIMEOUT          Per-request timeout in seconds (default: 30)
    CLAROTY_RATE_LIMIT_PER_MIN  Sliding-window cap (default: 2000)
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, AsyncIterator, Optional

import httpx

from utils.rate_limiter import SlidingWindowRateLimiter

logger = logging.getLogger("claroty-mcp.client")

_DEFAULT_BASE_URL = "https://api.medigate.io"
_DEFAULT_TIMEOUT = 30
_DEFAULT_RATE_LIMIT = 2000
_DEFAULT_PAGE_SIZE = 100
_MAX_429_RETRIES = 5


class ClarotyAPIError(Exception):
    """Structured error raised when xDome returns a 4xx/5xx response.

    Carries the status code, the path that failed, and xDome's response
    body (parsed as JSON if possible). The string form gives operators
    enough context to diagnose without re-reading raw HTTP. Tool error
    envelopes JSON-serialise ``to_dict()`` so the agent sees the
    structured form too.

    Common status hints (these come up in real operation):

    - **401 Unauthorized**: ``CLAROTY_API_TOKEN`` is missing, malformed,
      or expired. Re-issue from xDome Admin Settings > User Management.
    - **403 Forbidden**: token is valid but lacks the required scope
      for this endpoint. Write endpoints
      (``acknowledge_alert``, ``set_device_purdue_level``,
      ``set_device_custom_attribute``, ``set_vulnerability_relevance``,
      ``label_alerts``, ``assign_alerts``) all need write scope on the
      relevant resource. Read-only tokens trip 403 here.
    - **422 Unprocessable**: the request body failed schema validation.
      The body should include xDome's diagnostic — surface it verbatim.
    - **429 Too Many Requests**: rate-limited; the client retries up to
      5× honoring Retry-After before raising.
    """

    def __init__(
        self,
        path: str,
        status_code: int,
        message: str,
        body: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.path = path
        self.status_code = status_code
        self.message = message
        self.body = body

    @classmethod
    def from_response(cls, path: str, resp) -> "ClarotyAPIError":
        body: Any = None
        if resp.content:
            try:
                body = resp.json()
            except Exception:
                body = resp.text[:2000]
        message = cls._summarise(resp.status_code, body)
        return cls(path, resp.status_code, message, body)

    @staticmethod
    def _summarise(status_code: int, body: Any) -> str:
        hint = {
            401: "Unauthorized — check CLAROTY_API_TOKEN is present and not expired.",
            403: (
                "Forbidden — the token is valid but lacks the scope needed for "
                "this endpoint. Write endpoints require write scope on the "
                "relevant resource (alerts, devices, vulnerabilities, etc.)."
            ),
            422: "Unprocessable Entity — request body failed xDome validation.",
            429: "Too Many Requests — rate limit exceeded after retries.",
        }.get(status_code)
        detail = ""
        if isinstance(body, dict):
            # xDome typically uses "detail" / "message" / "error" keys
            for k in ("detail", "message", "error", "errors"):
                if k in body:
                    detail = f" xDome said: {body[k]!r}"
                    break
            if not detail:
                detail = f" xDome body: {body}"
        elif isinstance(body, str) and body:
            detail = f" body: {body[:300]}"
        suffix = f" — {hint}" if hint else ""
        return f"xDome HTTP {status_code}{suffix}{detail}"

    def to_dict(self) -> dict:
        return {
            "status_code": self.status_code,
            "path": self.path,
            "message": self.message,
            "body": self.body,
        }


class ClarotyClient:
    """Async HTTP client for the Claroty xDome REST API."""

    def __init__(self) -> None:
        self.api_url = os.environ.get("CLAROTY_API_URL", _DEFAULT_BASE_URL).rstrip("/")
        self.api_token = os.environ.get("CLAROTY_API_TOKEN", "")
        self.verify_ssl = os.environ.get("CLAROTY_VERIFY_SSL", "true").lower() in (
            "true",
            "1",
            "yes",
        )
        self.timeout = int(os.environ.get("CLAROTY_TIMEOUT", str(_DEFAULT_TIMEOUT)))
        self.rate_limit_per_min = int(
            os.environ.get("CLAROTY_RATE_LIMIT_PER_MIN", str(_DEFAULT_RATE_LIMIT))
        )
        self._client: Optional[httpx.AsyncClient] = None
        self._limiter = SlidingWindowRateLimiter(self.rate_limit_per_min)

    def validate_config(self) -> None:
        """Raise ValueError if required environment variables are missing."""
        missing = []
        if not self.api_url:
            missing.append("CLAROTY_API_URL")
        if not self.api_token:
            missing.append("CLAROTY_API_TOKEN")
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                verify=self.verify_ssl,
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def post(self, endpoint: str, body: Optional[dict] = None) -> Any:
        """POST a JSON body to ``endpoint`` and return the parsed response.

        Honours the sliding-window rate limit, retries 429 responses
        respecting Retry-After (up to ``_MAX_429_RETRIES``), and raises
        ``ClarotyAPIError`` on other 4xx/5xx errors. ``ClarotyAPIError``
        carries the status code, the request path, and xDome's parsed
        error body (when present) so tool authors don't have to dig
        through an opaque ``HTTPStatusError`` string.
        """
        client = await self._get_client()
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        attempt = 0
        while True:
            await self._limiter.acquire()
            resp = await client.post(path, json=body or {})
            if resp.status_code == 429 and attempt < _MAX_429_RETRIES:
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else 2 ** attempt
                logger.warning(
                    "xDome returned 429 on %s; backing off %.1fs (attempt %d)",
                    path,
                    wait,
                    attempt + 1,
                )
                await asyncio.sleep(wait)
                attempt += 1
                continue
            if resp.status_code >= 400:
                raise ClarotyAPIError.from_response(path, resp)
            if resp.content:
                return resp.json()
            return {}

    @staticmethod
    def _extract_items(data, endpoint: str, items_key: Optional[str]) -> list:
        """Pull the items list out of an xDome response.

        xDome wraps each list response in a property named after the
        resource (``devices``, ``sites``, ``alerts``, ``server_interfaces``,
        ``ot_activity_events``, ``audit_log``, ``organization_zones``,
        ``records`` for edge locations). Passing ``items_key`` explicitly
        is the only reliable approach — when ``items_key`` is omitted we
        try a handful of common keys and log a warning if none match, so
        the "0 items but it actually had 200" silent failure stops being
        invisible.
        """
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []

        # Preferred path: caller told us the key.
        if items_key:
            value = data.get(items_key)
            if isinstance(value, list):
                return value
            if value is None:
                logger.warning(
                    "%s response missing expected items key %r; response keys=%s",
                    endpoint,
                    items_key,
                    list(data.keys()),
                )

        # Fallback heuristics (kept narrow on purpose — last-resort only).
        for candidate in ("items", "results", "data", "records"):
            value = data.get(candidate)
            if isinstance(value, list):
                if items_key and candidate != items_key:
                    logger.warning(
                        "%s: items_key %r missing but found list under %r — using that",
                        endpoint,
                        items_key,
                        candidate,
                    )
                return value

        # Nothing matched — log loudly so this never silently looks empty.
        logger.warning(
            "%s: no recognised items list in response; keys=%s, items_key=%r",
            endpoint,
            list(data.keys()),
            items_key,
        )
        return []

    async def paginate(
        self,
        endpoint: str,
        body: Optional[dict] = None,
        *,
        items_key: Optional[str] = None,
        page_size: int = _DEFAULT_PAGE_SIZE,
        max_pages: Optional[int] = None,
    ) -> AsyncIterator[dict]:
        """Yield items across all pages of an xDome list endpoint.

        Injects ``offset``/``limit`` into the POST body. Stops when the
        page returns fewer than ``page_size`` items. ``items_key`` should
        be the response wrapper property name (e.g. ``"devices"`` for
        ``/api/v1/devices/``) — without it the parser falls back to
        ``items``/``results``/``data``/``records`` and logs a warning.
        """
        offset = 0
        page = 0
        while True:
            page_body = dict(body or {})
            page_body["offset"] = offset
            page_body["limit"] = page_size
            data = await self.post(endpoint, page_body)
            items = self._extract_items(data, endpoint, items_key)

            for item in items:
                yield item

            if len(items) < page_size:
                return

            offset += page_size
            page += 1
            if max_pages is not None and page >= max_pages:
                return

    async def collect(
        self,
        endpoint: str,
        body: Optional[dict] = None,
        *,
        items_key: Optional[str] = None,
        page_size: int = _DEFAULT_PAGE_SIZE,
        max_items: Optional[int] = None,
    ) -> list[dict]:
        """Collect all paginated results into a single list.

        Convenience wrapper around ``paginate``. ``items_key`` must be
        the response wrapper property name for the endpoint (see
        ``utils.xdome_constants.RESPONSE_ITEMS_KEY``).
        """
        out: list[dict] = []
        async for item in self.paginate(
            endpoint, body, items_key=items_key, page_size=page_size
        ):
            out.append(item)
            if max_items is not None and len(out) >= max_items:
                break
        return out


# Module-level singleton — tool modules import this directly.
client = ClarotyClient()


def format_exception(exc: Exception) -> Any:
    """Render an exception in the form tool error envelopes expect.

    ``ClarotyAPIError`` -> structured dict with status_code / path / body
    so the agent can reason about whether to retry, fix scope, etc.
    Anything else -> string (most often a config or connectivity issue).
    """
    if isinstance(exc, ClarotyAPIError):
        return exc.to_dict()
    return str(exc)
