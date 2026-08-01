"""OAuth2 client-credentials authentication for the Cisco API.

Spec 078 FR-006, FR-007. Research R4.

Two rules define this module:

1. **Refresh proactively, not on failure.** The token lives 3600 seconds and a
   fleet sweep can outlive it. Discovering expiry via a mid-sweep 401 turns a
   completely predictable event into a partial failure, so the token is renewed
   once its remaining lifetime drops below a margin.

2. **The token never touches disk.** It is a credential. The *advisory* cache is
   on disk (FR-012); this is not. Nor does the token or the client secret appear
   in any error message — errors name the environment variable, never its value
   (FR-007, SC-009).
"""

from __future__ import annotations

import os
import threading
import time

import httpx

TOKEN_URL = "https://id.cisco.com/oauth2/default/v1/token"

# Renew when this much lifetime remains. 60s comfortably covers a slow request
# plus clock skew, without renewing so often that it wastes rate budget.
REFRESH_MARGIN_S = 60


class AuthError(RuntimeError):
    """Authentication failed. Message names the missing/rejected variable, never
    its value."""


class TokenProvider:
    """Holds a Bearer token in memory and renews it before it expires.

    Thread-safe: fleet fan-out calls this concurrently, and two threads racing to
    refresh would burn two of a very scarce 30 calls per minute.
    """

    def __init__(self, client_id: str | None = None, client_secret: str | None = None):
        self._client_id = client_id or os.environ.get("CISCO_CLIENT_ID")
        self._client_secret = client_secret or os.environ.get("CISCO_CLIENT_SECRET")
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def _missing(self) -> str:
        absent = [n for n, v in (("CISCO_CLIENT_ID", self._client_id),
                                 ("CISCO_CLIENT_SECRET", self._client_secret)) if not v]
        return ", ".join(absent)

    def remaining_seconds(self) -> int:
        """Seconds of token life left. Zero when absent or expired."""
        if not self._token:
            return 0
        return max(0, int(self._expires_at - time.time()))

    def _fetch(self) -> None:
        """Exchange client credentials for a Bearer token. Caller holds the lock."""
        try:
            resp = httpx.post(
                TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "client_credentials",
                      "client_id": self._client_id,
                      "client_secret": self._client_secret},
                timeout=30,
            )
        except httpx.HTTPError as exc:
            raise AuthError(f"could not reach the Cisco token endpoint: "
                            f"{type(exc).__name__}") from exc

        if resp.status_code != 200:
            # Deliberately does NOT echo the response body: a rejected credential
            # response can contain the submitted client_id.
            raise AuthError(
                f"Cisco rejected the client credentials (HTTP {resp.status_code}). "
                f"Check CISCO_CLIENT_ID and CISCO_CLIENT_SECRET, and that the "
                f"application is active in the Cisco API Console."
            )

        payload = resp.json()
        token = payload.get("access_token")
        if not token:
            raise AuthError("Cisco returned no access_token")
        self._token = token
        self._expires_at = time.time() + int(payload.get("expires_in", 3600))

    def bearer(self) -> str:
        """Return a valid token, refreshing proactively if it is close to expiry."""
        if not self.configured:
            raise AuthError(
                f"Cisco API credentials are not configured: {self._missing()} unset. "
                f"Register a Service application with the Client Credentials grant at "
                f"apiconsole.cisco.com, select the PSIRT openVuln API, and put the id "
                f"and secret in a gitignored .env."
            )
        with self._lock:
            if self.remaining_seconds() <= REFRESH_MARGIN_S:
                self._fetch()
            assert self._token is not None
            return self._token

    def status(self) -> dict:
        """Non-secret posture, for the psirt_status tool. Never the token itself."""
        return {
            "configured": self.configured,
            "authenticated": bool(self._token),
            "token_expires_in_seconds": self.remaining_seconds(),
            "missing_variables": self._missing() or None,
        }
