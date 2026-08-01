"""
SuzieQ REST API Client for NetClaw MCP Server

Async HTTP client that wraps the SuzieQ REST API. Handles connection setup,
authentication (access_token), SSL configuration, query parameter building,
response truncation, freshness stamping, and structured error handling.

Environment Variables:
    SUZIEQ_API_URL: Base URL of the SuzieQ REST API (required)
    SUZIEQ_API_KEY: API access token for authentication (required)
    SUZIEQ_VERIFY_SSL: Whether to verify SSL certificates (default: true)
    SUZIEQ_TIMEOUT: Query timeout in seconds (default: 30)
    SUZIEQ_MAX_ROWS: Default maximum rows returned (default: 200)
    SUZIEQ_MAX_RESPONSE_BYTES: Hard ceiling on serialized response (default: 128KB)
"""

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger("suzieq-mcp")

# ---------------------------------------------------------------------------
# Known tables and assert-capable tables
# ---------------------------------------------------------------------------
KNOWN_TABLES = [
    "address", "arpnd", "bgp", "device", "devconfig",
    "evpnVni", "fs", "ifCounters", "interface", "inventory",
    "lldp", "mac", "mlag", "namespace", "network",
    "ospf", "route", "sqPoller", "topology", "vlan",
]

ASSERT_TABLES = ["bgp", "ospf", "interface", "evpnVni"]

# ---------------------------------------------------------------------------
# Per-table default columns — used when the caller does not specify columns.
# Purpose: avoid returning every column by default (many tables have 20–40
# columns), which produces massive payloads at scale. These are the columns
# most likely to be useful for investigation and triage.
# ---------------------------------------------------------------------------
DEFAULT_COLUMNS: dict[str, str] = {
    "route": "namespace,hostname,vrf,prefix,nexthopIps,oifs,protocol,timestamp",
    "mac": "namespace,hostname,vlan,macaddr,oif,remoteVtepIp,timestamp",
    "arpnd": "namespace,hostname,ipAddress,macaddr,oif,state,timestamp",
    "bgp": "namespace,hostname,vrf,peer,peerHostname,state,peerAsn,asn,pfxRx,pfxTx,estdTime,timestamp",
    "ospf": "namespace,hostname,vrf,ifname,peerHostname,peerIP,area,state,timestamp",
    "interface": "namespace,hostname,ifname,state,adminState,type,mtu,speed,ipAddressList,timestamp",
    "lldp": "namespace,hostname,ifname,peerHostname,peerIfname,peerMacaddr,timestamp",
    "vlan": "namespace,hostname,vlanName,vlan,state,interfaces,timestamp",
    "mlag": "namespace,hostname,systemId,peerAddress,state,peerLink,timestamp",
    "device": "namespace,hostname,model,vendor,version,serialNumber,status,uptime,timestamp",
    "evpnVni": "namespace,hostname,vni,type,state,vrf,remoteVtepList,timestamp",
    "ifCounters": "namespace,hostname,ifname,inBytes,outBytes,inErrors,outErrors,inDiscards,outDiscards,timestamp",
    "address": "namespace,hostname,ifname,ipAddressList,macaddr,timestamp",
    "sqPoller": "namespace,hostname,service,status,pollExcdPeriodCount,timestamp",
}

# ---------------------------------------------------------------------------
# Payload controls — defaults
# ---------------------------------------------------------------------------
DEFAULT_MAX_ROWS = int(os.environ.get("SUZIEQ_MAX_ROWS", "200"))
DEFAULT_MAX_RESPONSE_BYTES = int(os.environ.get("SUZIEQ_MAX_RESPONSE_BYTES", str(128 * 1024)))


class SuzieQClient:
    """Async HTTP client for the SuzieQ REST API."""

    def __init__(self) -> None:
        self.api_url = os.environ.get("SUZIEQ_API_URL", "").rstrip("/")
        self.api_key = os.environ.get("SUZIEQ_API_KEY", "")
        self.verify_ssl = os.environ.get("SUZIEQ_VERIFY_SSL", "true").lower() in (
            "true",
            "1",
            "yes",
        )
        self.timeout = int(os.environ.get("SUZIEQ_TIMEOUT", "30"))
        self.max_rows = DEFAULT_MAX_ROWS
        self.max_response_bytes = DEFAULT_MAX_RESPONSE_BYTES
        self._client: Optional[httpx.AsyncClient] = None

    def validate_config(self) -> None:
        """Validate that required environment variables are set.

        Raises:
            ValueError: If SUZIEQ_API_URL or SUZIEQ_API_KEY is missing.
        """
        missing = []
        if not self.api_url:
            missing.append("SUZIEQ_API_URL")
        if not self.api_key:
            missing.append("SUZIEQ_API_KEY")
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                verify=self.verify_ssl,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @staticmethod
    def build_query_params(
        namespace: Optional[str] = None,
        hostname: Optional[str] = None,
        columns: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        view: Optional[str] = None,
        filters: Optional[str] = None,
    ) -> dict[str, str]:
        """Convert tool parameters into SuzieQ REST API query parameters.

        Args:
            namespace: SuzieQ namespace filter.
            hostname: Device hostname filter.
            columns: Comma-separated column names.
            start_time: ISO 8601 or relative time string (e.g., "1h", "2d").
            end_time: ISO 8601 or relative time string.
            view: Data view: "latest", "all", or "changes".
            filters: Additional key=value pairs separated by ampersand.

        Returns:
            Dict of query parameter names to values.
        """
        params: dict[str, str] = {}

        if namespace:
            params["namespace"] = namespace
        if hostname:
            params["hostname"] = hostname
        if columns:
            params["columns"] = columns
        if start_time:
            params["start-time"] = start_time
        if end_time:
            params["end-time"] = end_time
        if view:
            params["view"] = view

        # Parse additional filters string (key=value&key=value)
        if filters:
            for pair in filters.split("&"):
                pair = pair.strip()
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        params[key] = value

        return params

    @staticmethod
    def get_default_columns(table: str) -> Optional[str]:
        """Return default column set for a table, or None if no default defined.

        Used when the caller does not specify columns, to prevent unbounded
        payloads on high-cardinality tables like route, mac, and arpnd.
        """
        return DEFAULT_COLUMNS.get(table)

    @staticmethod
    def truncate_response(
        data: list,
        max_rows: int,
    ) -> tuple[list, dict]:
        """Apply row cap and return (truncated_data, truncation_metadata).

        The metadata dict is always present in the response envelope so the
        consumer can distinguish "small table" from "truncated table" — a
        subset must never be mistakable for the whole (FR-046).

        Returns:
            (data_slice, {"truncated": bool, "rows_returned": int, "rows_available": int})
        """
        total = len(data)
        if total <= max_rows:
            return data, {
                "truncated": False,
                "rows_returned": total,
                "rows_available": total,
            }
        return data[:max_rows], {
            "truncated": True,
            "rows_returned": max_rows,
            "rows_available": total,
        }

    @staticmethod
    def extract_freshness(data: list) -> Optional[str]:
        """Extract the newest timestamp from a list of SuzieQ records.

        SuzieQ records carry a `timestamp` field (epoch ms). Returns the
        newest as an ISO 8601 string, or None if no timestamps are found.
        This lets the consumer detect stale data — a confident wrong answer
        from old state is worse than no answer (FR-047).
        """
        from datetime import datetime, timezone

        newest: Optional[int] = None
        for record in data:
            if isinstance(record, dict):
                ts = record.get("timestamp")
                if ts is not None:
                    try:
                        ts_int = int(ts)
                        if newest is None or ts_int > newest:
                            newest = ts_int
                    except (ValueError, TypeError):
                        continue

        if newest is None:
            return None

        # SuzieQ timestamps are milliseconds since epoch
        try:
            dt = datetime.fromtimestamp(newest / 1000.0, tz=timezone.utc)
            return dt.isoformat()
        except (OSError, OverflowError, ValueError):
            return None

    async def query(
        self,
        table: str,
        verb: str,
        params: Optional[dict[str, str]] = None,
        max_rows: Optional[int] = None,
    ) -> dict[str, Any]:
        """Execute a query against the SuzieQ REST API.

        Args:
            table: SuzieQ table name (e.g., "bgp", "route").
            verb: Operation verb (e.g., "show", "summarize", "assert", "unique").
            params: Optional query parameters dict.
            max_rows: Override the default row cap for this query.
                      Pass 0 to disable truncation (not recommended for auto paths).

        Returns:
            Dict with keys: success, data, error, truncation, freshness.
        """
        effective_max_rows = max_rows if max_rows is not None else self.max_rows
        url = f"{self.api_url}/api/v2/{table}/{verb}"
        query_params = {"access_token": self.api_key}
        if params:
            query_params.update(params)

        try:
            client = await self._get_client()
            response = await client.get(url, params=query_params)

            if response.status_code in (401, 403):
                return {
                    "success": False,
                    "data": [],
                    "error": "SuzieQ authentication failed. Verify SUZIEQ_API_KEY is correct.",
                    "truncation": None,
                    "freshness": None,
                }

            response.raise_for_status()
            data = response.json()

            # Normalize to list
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                data = [data] if data else []

            # Extract freshness before any truncation
            freshness = self.extract_freshness(data)

            # Apply truncation (FR-046)
            if effective_max_rows > 0 and isinstance(data, list):
                data, truncation = self.truncate_response(data, effective_max_rows)
            else:
                truncation = {
                    "truncated": False,
                    "rows_returned": len(data) if isinstance(data, list) else 0,
                    "rows_available": len(data) if isinstance(data, list) else 0,
                }

            return {
                "success": True,
                "data": data,
                "error": None,
                "truncation": truncation,
                "freshness": freshness,
            }

        except httpx.ConnectError:
            return {
                "success": False,
                "data": [],
                "error": f"SuzieQ API unreachable at {self.api_url}: connection refused or DNS failure",
                "truncation": None,
                "freshness": None,
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "data": [],
                "error": f"SuzieQ query timed out after {self.timeout}s. Try narrowing filters.",
                "truncation": None,
                "freshness": None,
            }
        except httpx.HTTPStatusError as exc:
            return {
                "success": False,
                "data": [],
                "error": f"SuzieQ API returned HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                "truncation": None,
                "freshness": None,
            }
        except Exception as exc:
            return {
                "success": False,
                "data": [],
                "error": f"Unexpected error querying SuzieQ: {type(exc).__name__}: {exc}",
                "truncation": None,
                "freshness": None,
            }

    async def query_path(
        self,
        namespace: str,
        source: str,
        destination: str,
        vrf: str = "default",
    ) -> dict[str, Any]:
        """Execute a path trace query against the SuzieQ REST API.

        Args:
            namespace: SuzieQ namespace (required).
            source: Source IP address.
            destination: Destination IP address.
            vrf: VRF name (default: "default").

        Returns:
            Dict with keys: success, data, error, truncation, freshness.
        """
        url = f"{self.api_url}/api/v2/path/show"
        query_params = {
            "access_token": self.api_key,
            "namespace": namespace,
            "src": source,
            "dest": destination,
            "vrf": vrf,
        }

        try:
            client = await self._get_client()
            response = await client.get(url, params=query_params)

            if response.status_code in (401, 403):
                return {
                    "success": False,
                    "data": [],
                    "error": "SuzieQ authentication failed. Verify SUZIEQ_API_KEY is correct.",
                    "truncation": None,
                    "freshness": None,
                }

            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                data = [data] if data else []

            freshness = self.extract_freshness(data)
            # Path traces are inherently bounded (one path), but still report
            truncation = {
                "truncated": False,
                "rows_returned": len(data),
                "rows_available": len(data),
            }

            return {
                "success": True,
                "data": data,
                "error": None,
                "truncation": truncation,
                "freshness": freshness,
            }

        except httpx.ConnectError:
            return {
                "success": False,
                "data": [],
                "error": f"SuzieQ API unreachable at {self.api_url}: connection refused or DNS failure",
                "truncation": None,
                "freshness": None,
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "data": [],
                "error": f"SuzieQ path query timed out after {self.timeout}s. Try narrowing the scope.",
                "truncation": None,
                "freshness": None,
            }
        except httpx.HTTPStatusError as exc:
            return {
                "success": False,
                "data": [],
                "error": f"SuzieQ API returned HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                "truncation": None,
                "freshness": None,
            }
        except Exception as exc:
            return {
                "success": False,
                "data": [],
                "error": f"Unexpected error querying SuzieQ path: {type(exc).__name__}: {exc}",
                "truncation": None,
                "freshness": None,
            }
