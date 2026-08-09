"""FortiOS REST client for the device plane. Spec 080, research R3.

Plain bearer-token REST over HTTPS — a different protocol from the JSON-RPC the
manager and analyzer planes share, hence a separate module.

Measured against the lab on 2026-08-01 (FortiOS v8.0.0): an **unregistered**
FortiGate refuses the entire management plane. GUI logins bounce and API tokens
return HTTP 401 identically whether the token is valid, invalid, or absent —
verified with a packet capture confirming the source address matched the
api-user's trusthost, so it is not a trust or routing problem. `AUTH_REJECTED`
below therefore carries that diagnosis, because "401" on its own sent us chasing
credentials for hours when the cause was licensing.
"""

from __future__ import annotations

from typing import Any

import httpx

from credentials import PlaneCredentials
from envelope import Outcome


class RestError(RuntimeError):
    """A FortiOS REST call failed, mapped onto our outcome vocabulary."""

    def __init__(self, message: str, *, status: int | None = None, outcome: Outcome | None = None):
        super().__init__(message)
        self.status = status
        self.outcome = outcome or Outcome.EMPTY_RESULT


class FortiOSClient:
    """Read-oriented FortiOS REST client.

    No FortiOS SDK (research R4): `fortiosapi` and `fortigate-api` target config
    *management*, a far wider surface than a read-first server needs, and both
    would add pinning hazards for no benefit here.
    """

    def __init__(self, creds: PlaneCredentials, *, timeout: float = 30.0) -> None:
        self._creds = creds
        self._timeout = timeout
        self._device_name: str | None = None

    @property
    def source(self) -> str:
        return self._creds.host

    @property
    def device_name(self) -> str:
        """Stable identity for the `device` scope key.

        Every tool must report the *same* device identifier or the scope becomes
        useless for correlation — a caller cannot tell that two results describe
        one box. Resolves to the unit's hostname once and caches it, falling back
        to the host URL until then.
        """
        return self._device_name or self._creds.host

    async def resolve_identity(self) -> str:
        """Fetch and cache the unit hostname. Safe to call repeatedly."""
        if self._device_name is None:
            try:
                status = await self.get("monitor/system/status")
                self._device_name = status.get("hostname") or self._creds.host
            except RestError:
                self._device_name = self._creds.host
        return self._device_name

    async def get_envelope(self, path: str, *, vdom: str | None = None, **params: Any) -> dict:
        """GET a path and return the **whole** response body, not just `results`.

        FortiOS puts some of the most useful fields OUTSIDE `results`. On
        `monitor/system/status`, `results` carries hostname and model, while
        **`serial`, `version` and `build` sit at the top level of the envelope**.
        Callers that only ever see `results` silently report those as null — which
        is exactly what happened here until a live end-to-end run caught it.
        """
        return await self._request(path, vdom=vdom, envelope=True, **params)

    async def get(self, path: str, *, vdom: str | None = None, **params: Any) -> Any:
        """GET one FortiOS REST path, e.g. `monitor/system/status`.

        Returns the `results` payload. Use `get_envelope()` when you need the
        top-level fields too. `vdom` is passed through because a device figure
        without its VDOM is ambiguous on a multi-VDOM unit (FR-018).
        """
        return await self._request(path, vdom=vdom, envelope=False, **params)

    async def _request(
        self, path: str, *, vdom: str | None = None, envelope: bool = False, **params: Any
    ) -> Any:
        url = f"{self._creds.host}/api/v2/{path.lstrip('/')}"
        query = dict(params)
        if vdom:
            query["vdom"] = vdom

        try:
            async with httpx.AsyncClient(
                verify=self._creds.verify_ssl, timeout=self._timeout
            ) as client:
                response = await client.get(
                    url,
                    params=query,
                    headers={"Authorization": f"Bearer {self._creds.token}"},
                )
        except httpx.HTTPError as exc:
            raise RestError(
                f"device plane unreachable: {type(exc).__name__}",
                outcome=Outcome.PLANE_UNREACHABLE,
            ) from None  # `from None`: an httpx repr can carry the URL and token

        if response.status_code in (401, 403):
            raise RestError(
                "device plane rejected the API token. On FortiOS this is also "
                "what an UNREGISTERED evaluation unit returns for every request, "
                "valid token or not — check `get system status` for "
                "'License Status: Valid' before assuming a credential problem.",
                status=response.status_code,
                outcome=Outcome.AUTH_EXPIRED,
            )

        response.raise_for_status()
        body = response.json()
        return body if envelope else body.get("results", body)
