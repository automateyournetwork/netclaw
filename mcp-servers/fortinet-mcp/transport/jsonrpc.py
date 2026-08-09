"""JSON-RPC client for FortiManager **and** FortiAnalyzer. Spec 080, research R2.

Both appliances expose `/jsonrpc` with the same request envelope and the same
`exec /sys/login/user` authentication. They differ only in the methods invoked,
so one client serves two of the three planes. The roadmap listed FortiManager and
FortiAnalyzer as separate line items, which made them look like separate
integrations; they are not.

Auth is token-only (research R9). Username/password adds session lifecycle for no
capability gain, and both vendors' own documentation recommends tokens.
"""

from __future__ import annotations

from typing import Any

import httpx

from credentials import PlaneCredentials
from envelope import Outcome

#: FortiManager/FortiAnalyzer report application errors inside a 200 response,
#: in result[].status.code. -11 is "no permission", -5 "login failure".
_AUTH_ERROR_CODES = {-11, -5, -22}


class JsonRpcError(RuntimeError):
    """A JSON-RPC call returned a non-zero status.

    `outcome` maps the appliance's error onto our vocabulary so callers do not
    have to interpret Fortinet status codes. In particular an expired session
    becomes AUTH_EXPIRED and never an empty result — "no policies exist" from an
    expired session is a silent, plausible, wrong answer.
    """

    def __init__(self, message: str, *, code: int | None = None, outcome: Outcome | None = None):
        super().__init__(message)
        self.code = code
        self.outcome = outcome or Outcome.EMPTY_RESULT


class JsonRpcClient:
    """Minimal FortiManager/FortiAnalyzer JSON-RPC client.

    Deliberately not pyFMG (research R4): the protocol is a POST with
    method/params/session, and an SDK would add a dependency and a spec-077
    pinning hazard over an abstraction simpler than the thing abstracted.
    """

    def __init__(self, creds: PlaneCredentials, *, timeout: float = 30.0) -> None:
        self._creds = creds
        self._timeout = timeout
        self._endpoint = f"{creds.host}/jsonrpc"

    @property
    def source(self) -> str:
        """Host identity for the response envelope. Never includes the token."""
        return self._creds.host

    async def call(self, method: str, url: str, **params: Any) -> Any:
        """Invoke one JSON-RPC method against one object path.

        `method` is the JSON-RPC verb (`get`, `exec`, `add`, `set`, `delete`);
        `url` is the appliance object path (`/dvmdb/adom`, `/logview/...`).
        """
        payload: dict[str, Any] = {
            "id": 1,
            "method": method,
            "params": [{"url": url, **params}],
            "session": self._creds.token,
            "verbose": 1,
        }

        try:
            async with httpx.AsyncClient(
                verify=self._creds.verify_ssl, timeout=self._timeout
            ) as client:
                response = await client.post(self._endpoint, json=payload)
        except httpx.HTTPError as exc:
            # Connection-level failure. The caller turns this into
            # PLANE_UNREACHABLE — it must not be reported as "no data".
            raise JsonRpcError(
                f"{self._creds.plane.value} plane unreachable: {type(exc).__name__}",
                outcome=Outcome.PLANE_UNREACHABLE,
            ) from None  # `from None`: an httpx repr can carry the URL and token

        if response.status_code == 401:
            raise JsonRpcError(
                f"{self._creds.plane.value} plane rejected the API token",
                outcome=Outcome.AUTH_EXPIRED,
            )
        response.raise_for_status()
        body = response.json()

        results = body.get("result") or []
        first = results[0] if results else {}
        status = first.get("status") or {}
        code = status.get("code", 0)

        if code != 0:
            message = status.get("message", "unspecified error")
            outcome = (
                Outcome.AUTH_EXPIRED if code in _AUTH_ERROR_CODES else Outcome.EMPTY_RESULT
            )
            raise JsonRpcError(
                f"{self._creds.plane.value} plane returned {code}: {message}",
                code=code,
                outcome=outcome,
            )

        return first.get("data")
