"""Nautobot API client — GraphQL for reads, REST for writes."""

import json
import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# Cache for resolved UUIDs (type:name -> uuid)
_id_cache: dict[str, str] = {}


class NautobotError(Exception):
    pass


class NautobotAuthError(NautobotError):
    pass


class NautobotConnectionError(NautobotError):
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

    async def close(self):
        await self.http.aclose()

    # ── GraphQL ──────────────────────────────────────────────────────

    async def graphql(
        self, query: str, variables: Optional[dict] = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"query": query}
        if variables:
            body["variables"] = variables

        try:
            resp = await self.http.post(f"{self.url}/api/graphql/", json=body)
        except httpx.ConnectError as e:
            raise NautobotConnectionError(
                f"Nautobot API unreachable at {self.url}: {e}"
            )
        except httpx.TimeoutException:
            raise NautobotConnectionError(
                f"Nautobot query timed out after {self.http.timeout.read}s."
            )

        self._check_http(resp)
        data = resp.json()

        if "errors" in data:
            msgs = "; ".join(e.get("message", str(e)) for e in data["errors"])
            raise NautobotError(f"Nautobot GraphQL error: {msgs}")

        return data.get("data", {})

    # ── REST ─────────────────────────────────────────────────────────

    async def rest_get(
        self, endpoint: str, params: Optional[dict] = None
    ) -> dict[str, Any]:
        return await self._rest("GET", endpoint, params=params)

    async def rest_post(self, endpoint: str, data: dict) -> dict[str, Any]:
        return await self._rest("POST", endpoint, json_body=data)

    async def rest_patch(self, endpoint: str, data: dict) -> dict[str, Any]:
        return await self._rest("PATCH", endpoint, json_body=data)

    async def rest_delete(self, endpoint: str) -> dict[str, Any]:
        return await self._rest("DELETE", endpoint)

    async def rest_list(
        self, endpoint: str, params: Optional[dict] = None, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        """GET a list endpoint with pagination."""
        p = dict(params or {})
        p["limit"] = limit
        p["offset"] = offset
        return await self._rest("GET", endpoint, params=p)

    async def _rest(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
    ) -> dict[str, Any]:
        url = f"{self.url}/api/{endpoint.strip('/')}/"
        try:
            resp = await self.http.request(method, url, params=params, json=json_body)
        except httpx.ConnectError as e:
            raise NautobotConnectionError(
                f"Nautobot API unreachable at {self.url}: {e}"
            )
        except httpx.TimeoutException:
            raise NautobotConnectionError(
                f"Nautobot request timed out after {self.http.timeout.read}s."
            )

        self._check_http(resp)
        if resp.status_code == 204:
            return {}
        return resp.json()

    # ── ID Resolution ────────────────────────────────────────────────

    async def resolve_id(self, object_type: str, name: str) -> str:
        """Resolve a human-readable name to a Nautobot UUID.

        Supported object_type values:
          status, role, location, device, platform, namespace,
          vlan_group, tenant, interface (use "device_name:iface_name")
        """
        cache_key = f"{object_type}:{name}"
        if cache_key in _id_cache:
            return _id_cache[cache_key]

        query_map: dict[str, str] = {
            "status": '{{ statuses(name: "{}") {{ id }} }}'.format(_esc(name)),
            "role": '{{ roles(name: "{}") {{ id }} }}'.format(_esc(name)),
            "location": '{{ locations(name: "{}") {{ id }} }}'.format(_esc(name)),
            "location_type": '{{ location_types(name: "{}") {{ id }} }}'.format(_esc(name)),
            "device": '{{ devices(name: "{}") {{ id }} }}'.format(_esc(name)),
            "device_type": '{{ device_types(model: "{}") {{ id }} }}'.format(_esc(name)),
            "manufacturer": '{{ manufacturers(name: "{}") {{ id }} }}'.format(_esc(name)),
            "platform": '{{ platforms(name: "{}") {{ id }} }}'.format(_esc(name)),
            "tenant": '{{ tenants(name: "{}") {{ id }} }}'.format(_esc(name)),
            "tenant_group": '{{ tenant_groups(name: "{}") {{ id }} }}'.format(_esc(name)),
            "vlan_group": '{{ vlan_groups(name: "{}") {{ id }} }}'.format(_esc(name)),
            "vrf": '{{ vrfs(name: "{}") {{ id }} }}'.format(_esc(name)),
            "cluster": '{{ clusters(name: "{}") {{ id }} }}'.format(_esc(name)),
            "cluster_type": '{{ cluster_types(name: "{}") {{ id }} }}'.format(_esc(name)),
            "cluster_group": '{{ cluster_groups(name: "{}") {{ id }} }}'.format(_esc(name)),
            "virtual_machine": '{{ virtual_machines(name: "{}") {{ id }} }}'.format(_esc(name)),
            "provider": '{{ providers(name: "{}") {{ id }} }}'.format(_esc(name)),
            "circuit_type": '{{ circuit_types(name: "{}") {{ id }} }}'.format(_esc(name)),
            "tag": '{{ tags(name: "{}") {{ id }} }}'.format(_esc(name)),
        }

        if object_type == "namespace":
            # Namespaces use REST — not always in GraphQL
            resp = await self.rest_get("ipam/namespaces", {"name": name})
            results = resp.get("results", [])
            if not results:
                raise NautobotError(f"Namespace '{name}' not found in Nautobot.")
            uid = results[0]["id"]
            _id_cache[cache_key] = uid
            return uid

        if object_type == "interface":
            # Expect "DeviceName:InterfaceName"
            if ":" not in name:
                raise NautobotError(
                    "Interface identifier must be 'device_name:interface_name'"
                )
            dev, iface = name.split(":", 1)
            q = '{{ interfaces(device: "{}", name: "{}") {{ id }} }}'.format(
                _esc(dev), _esc(iface)
            )
            data = await self.graphql(q)
            items = _first_list(data)
            if not items:
                raise NautobotError(
                    f"Interface '{iface}' on device '{dev}' not found in Nautobot."
                )
            uid = items[0]["id"]
            _id_cache[cache_key] = uid
            return uid

        if object_type not in query_map:
            raise NautobotError(f"Cannot resolve object type '{object_type}'")

        data = await self.graphql(query_map[object_type])
        items = _first_list(data)
        if not items:
            raise NautobotError(
                f"{object_type.replace('_', ' ').title()} '{name}' not found in Nautobot."
            )
        uid = items[0]["id"]
        _id_cache[cache_key] = uid
        return uid

    # ── Helpers ───────────────────────────────────────────────────────

    def _check_http(self, resp: httpx.Response) -> None:
        if resp.status_code in (401, 403):
            raise NautobotAuthError(
                "Nautobot authentication failed. Verify NAUTOBOT_TOKEN is correct."
            )
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text[:500]
            raise NautobotError(
                f"Nautobot REST API error ({resp.status_code}): {detail}"
            )


def _esc(s: str) -> str:
    """Escape a string for embedding in a GraphQL query."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _first_list(data: dict) -> list:
    """Return the first list value from a GraphQL response dict."""
    for v in data.values():
        if isinstance(v, list):
            return v
    return []
