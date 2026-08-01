#!/usr/bin/env python3
"""
SuzieQ MCP Server — Network Observability for NetClaw

Exposes 5 read-only tools via FastMCP/stdio for SuzieQ network observability:
  suzieq_show       — Query current or historical network state from any table
  suzieq_summarize  — Get aggregated statistics and summary views
  suzieq_assert     — Run validation assertions (bgp, ospf, interface, evpnVni)
  suzieq_unique     — Get distinct values and counts for a column
  suzieq_path       — Trace forwarding path between two endpoints

All operations are read-only. Credentials are read from environment variables.

Payload controls (T158, FR-046/FR-047):
  - max_rows: Server-enforced row cap (default 200, env SUZIEQ_MAX_ROWS)
  - Per-table default columns: avoids returning all columns when caller omits
  - Explicit truncation metadata in every response (truncated/rows_returned/rows_available)
  - Data freshness (newest timestamp) in every response
  - Hard byte ceiling on serialized output (env SUZIEQ_MAX_RESPONSE_BYTES, default 128KB)
"""

import json
import logging
import os
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Add netclaw_tokens to path for GCF serialization
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))

from suzieq_client import ASSERT_TABLES, KNOWN_TABLES, SuzieQClient

# ---------------------------------------------------------------------------
# GCF serialization helper
# ---------------------------------------------------------------------------
def _gcf_dumps(data: dict, **kwargs) -> str:
    """Serialize data using GCF with graph auto-detection and session dedup."""
    try:
        from netclaw_tokens.gcf_serializer import serialize_response
        result = serialize_response(data, use_session=True, use_delta=True)
        return result["encoded_data"]
    except Exception:
        return json.dumps(data, indent=2, **kwargs)

# ---------------------------------------------------------------------------
# Logging — stderr only (stdout is reserved for MCP JSON-RPC)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("suzieq-mcp")

# ---------------------------------------------------------------------------
# SuzieQ client (singleton)
# ---------------------------------------------------------------------------
client = SuzieQClient()

# Validate config at import time so failures are loud and immediate
try:
    client.validate_config()
    logger.info(
        "SuzieQ MCP server starting — api_url=%s verify_ssl=%s timeout=%ds max_rows=%d",
        client.api_url,
        client.verify_ssl,
        client.timeout,
        client.max_rows,
    )
except ValueError as exc:
    logger.error("Configuration error: %s", exc)
    print(f"ERROR: {exc}", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------
mcp = FastMCP("suzieq-mcp")


# ---------------------------------------------------------------------------
# Response envelope builder (T158 — FR-046 truncation + FR-047 freshness)
# ---------------------------------------------------------------------------
def _enforce_byte_ceiling(payload: str) -> str:
    """Hard ceiling: if the serialized response exceeds max bytes, re-truncate.

    This is a safety net — normal truncation at the row level should keep
    payloads well under the ceiling, but a table with very wide rows could
    still exceed it. In that case, truncate the data array to fit.
    """
    max_bytes = client.max_response_bytes
    if len(payload.encode("utf-8", errors="replace")) <= max_bytes:
        return payload

    # Parse, halve data, re-serialize until it fits
    try:
        obj = json.loads(payload)
        data = obj.get("data", [])
        while len(json.dumps(obj, indent=2).encode("utf-8")) > max_bytes and len(data) > 1:
            data = data[: len(data) // 2]
            obj["data"] = data
            obj["truncation"] = {
                "truncated": True,
                "rows_returned": len(data),
                "rows_available": obj.get("truncation", {}).get("rows_available", len(data)),
                "byte_ceiling_applied": True,
            }
        return json.dumps(obj, indent=2)
    except (json.JSONDecodeError, TypeError):
        return payload


def build_response_envelope(
    body: dict,
    result: dict,
) -> str:
    """Build the final response string with truncation + freshness metadata.

    Every response carries these fields regardless of success/failure, so the
    consumer can always determine:
    - whether the data is a subset (truncation)
    - how fresh the data is (freshness)
    """
    # Merge truncation and freshness into the body
    truncation = result.get("truncation")
    freshness = result.get("freshness")

    if truncation is not None:
        body["truncation"] = truncation
    if freshness is not None:
        body["data_freshness"] = freshness

    payload = _gcf_dumps(body)
    return _enforce_byte_ceiling(payload)


# ---------------------------------------------------------------------------
# Response formatters
# ---------------------------------------------------------------------------
def format_query_response(
    table: str,
    verb: str,
    result: dict,
    filters_applied: dict,
) -> str:
    """Format a SuzieQ query result into a standardized JSON response."""
    if not result["success"]:
        return json.dumps(
            {"error": result["error"], "table": table, "verb": verb},
            indent=2,
        )

    data = result["data"]
    row_count = len(data) if isinstance(data, list) else 0

    if row_count == 0:
        body = {
            "table": table,
            "verb": verb,
            "row_count": 0,
            "filters_applied": filters_applied,
            "message": f"No data found for {table} with the specified filters.",
            "data": [],
        }
        return build_response_envelope(body, result)

    body = {
        "table": table,
        "verb": verb,
        "row_count": row_count,
        "filters_applied": filters_applied,
        "data": data,
    }
    return build_response_envelope(body, result)


def format_assert_response(table: str, result: dict) -> str:
    """Format assertion results with pass/fail counts and per-device details."""
    if not result["success"]:
        return json.dumps(
            {"error": result["error"], "table": table, "verb": "assert"},
            indent=2,
        )

    data = result["data"]
    if not data or (isinstance(data, list) and len(data) == 0):
        body = {
            "table": table,
            "verb": "assert",
            "message": f"Assertion cannot be evaluated: no data found for table '{table}'. "
            "Ensure devices are being polled and the table has data.",
            "pass_count": 0,
            "fail_count": 0,
            "data": [],
        }
        return build_response_envelope(body, result)

    # Count pass/fail from assertion results
    pass_count = 0
    fail_count = 0
    failures = []

    if isinstance(data, list):
        for record in data:
            if isinstance(record, dict):
                assert_result = record.get("assert", record.get("assertReason", ""))
                if assert_result == "pass":
                    pass_count += 1
                else:
                    fail_count += 1
                    failures.append(record)
            else:
                pass_count += 1

    body = {
        "table": table,
        "verb": "assert",
        "pass_count": pass_count,
        "fail_count": fail_count,
        "total": pass_count + fail_count,
        "status": "PASS" if fail_count == 0 else "FAIL",
        "failures": failures if failures else [],
        "data": data,
    }
    return build_response_envelope(body, result)


def format_path_response(
    namespace: str,
    source: str,
    destination: str,
    vrf: str,
    result: dict,
) -> str:
    """Format a path trace result with hop-by-hop details."""
    if not result["success"]:
        return json.dumps(
            {
                "error": result["error"],
                "query": {
                    "namespace": namespace,
                    "source": source,
                    "destination": destination,
                    "vrf": vrf,
                },
            },
            indent=2,
        )

    data = result["data"]
    hop_count = len(data) if isinstance(data, list) else 0

    if hop_count == 0:
        body = {
            "namespace": namespace,
            "source": source,
            "destination": destination,
            "vrf": vrf,
            "hop_count": 0,
            "message": f"No path found from {source} to {destination} in namespace '{namespace}'. "
            "The endpoints may be unreachable or not monitored by SuzieQ.",
            "hops": [],
        }
        return build_response_envelope(body, result)

    body = {
        "namespace": namespace,
        "source": source,
        "destination": destination,
        "vrf": vrf,
        "hop_count": hop_count,
        "hops": data,
    }
    return build_response_envelope(body, result)


# ---------------------------------------------------------------------------
# Tool: suzieq_show (US1 + US2)
# ---------------------------------------------------------------------------
@mcp.tool()
async def suzieq_show(
    table: str,
    namespace: Optional[str] = None,
    hostname: Optional[str] = None,
    columns: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    view: Optional[str] = None,
    filters: Optional[str] = None,
    max_rows: Optional[int] = None,
) -> str:
    """Query detailed network state data from any SuzieQ table. Supports filtering
    by device, namespace, time range, and columns. Use for current or historical
    (time-travel) network state queries.

    Responses are bounded: the server enforces a row cap (default 200) and
    applies per-table default columns when none are specified. Every response
    includes truncation metadata (truncated, rows_returned, rows_available) and
    data_freshness (newest record timestamp). Use hostname, namespace, and
    start_time filters to narrow before increasing max_rows.

    Args:
        table: SuzieQ table name (e.g., "bgp", "route", "interface", "ospf",
               "arpnd", "mac", "lldp", "vlan", "mlag", "device", "evpnVni",
               "ifCounters", "address", "inventory", "sqPoller")
        namespace: Filter by SuzieQ namespace
        hostname: Filter by device hostname
        columns: Comma-separated column names to return. If omitted, per-table
                 defaults are applied (not all columns) to limit payload size.
        start_time: Start time for time-travel query (ISO 8601 or relative e.g. "1h", "2d")
        end_time: End time for time-travel query (ISO 8601 or relative)
        view: Data view: "latest" (default), "all", or "changes"
        filters: Additional filters as key=value pairs separated by ampersand
                 (e.g. "state=Established&vrf=default")
        max_rows: Override the default row cap (default: 200). Use sparingly —
                  prefer narrowing filters over raising the cap.
    """
    logger.info(
        "suzieq_show: table=%s namespace=%s hostname=%s columns=%s "
        "start_time=%s end_time=%s view=%s filters=%s max_rows=%s",
        table, namespace, hostname, columns,
        start_time, end_time, view, filters, max_rows,
    )

    if table not in KNOWN_TABLES:
        logger.warning(
            "Table '%s' not in known tables list. Forwarding to SuzieQ anyway.", table
        )

    # Apply per-table default columns when caller does not specify (FR-046)
    effective_columns = columns
    if not columns:
        default_cols = SuzieQClient.get_default_columns(table)
        if default_cols:
            effective_columns = default_cols
            logger.info("suzieq_show: using default columns for table=%s", table)

    # When start_time is provided without an explicit view, default to "all"
    # so historical data is actually returned (US2)
    effective_view = view
    if start_time and not view:
        effective_view = "all"

    params = SuzieQClient.build_query_params(
        namespace=namespace,
        hostname=hostname,
        columns=effective_columns,
        start_time=start_time,
        end_time=end_time,
        view=effective_view,
        filters=filters,
    )

    result = await client.query(table, "show", params, max_rows=max_rows)

    if not result["success"]:
        logger.error("suzieq_show error: %s", result["error"])
    else:
        trunc = result.get("truncation", {})
        logger.info(
            "suzieq_show: table=%s returned %d/%d rows (truncated=%s)",
            table,
            trunc.get("rows_returned", 0),
            trunc.get("rows_available", 0),
            trunc.get("truncated", False),
        )

    filters_applied = {
        k: v
        for k, v in {
            "namespace": namespace,
            "hostname": hostname,
            "columns": effective_columns,
            "columns_source": "caller" if columns else "default",
            "start_time": start_time,
            "end_time": end_time,
            "view": effective_view,
            "filters": filters,
            "max_rows": max_rows or client.max_rows,
        }.items()
        if v is not None
    }

    return format_query_response(table, "show", result, filters_applied)


# ---------------------------------------------------------------------------
# Tool: suzieq_summarize (US4)
# ---------------------------------------------------------------------------
@mcp.tool()
async def suzieq_summarize(
    table: str,
    namespace: Optional[str] = None,
    hostname: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> str:
    """Get aggregated statistics and summary views of any SuzieQ network table.
    Returns counts, distributions, and per-device breakdowns rather than
    individual records. Summaries are inherently compact — no row cap needed.

    Prefer this over suzieq_show when sizing a problem: use summarize first to
    understand the scope, then show with targeted filters to inspect specifics.

    Args:
        table: SuzieQ table name
        namespace: Filter by SuzieQ namespace
        hostname: Filter by device hostname
        start_time: Start time for historical summary
        end_time: End time for historical summary
    """
    logger.info(
        "suzieq_summarize: table=%s namespace=%s hostname=%s "
        "start_time=%s end_time=%s",
        table, namespace, hostname, start_time, end_time,
    )

    params = SuzieQClient.build_query_params(
        namespace=namespace,
        hostname=hostname,
        start_time=start_time,
        end_time=end_time,
    )

    # Summarize returns compact aggregations — no row cap
    result = await client.query(table, "summarize", params, max_rows=0)

    if not result["success"]:
        logger.error("suzieq_summarize error: %s", result["error"])
    else:
        logger.info("suzieq_summarize: table=%s completed", table)

    filters_applied = {
        k: v
        for k, v in {
            "namespace": namespace,
            "hostname": hostname,
            "start_time": start_time,
            "end_time": end_time,
        }.items()
        if v is not None
    }

    return format_query_response(table, "summarize", result, filters_applied)


# ---------------------------------------------------------------------------
# Tool: suzieq_assert (US3)
# ---------------------------------------------------------------------------
@mcp.tool()
async def suzieq_assert(
    table: str,
    namespace: Optional[str] = None,
    hostname: Optional[str] = None,
) -> str:
    """Run validation assertions against network state. Checks conditions like
    "all BGP peers should be established" or "no interface should have errors".
    Only supported for tables: bgp, ospf, interface, evpnVni.

    Assert results are inherently bounded (one record per entity) and carry
    pass/fail counts, so no row cap is applied.

    Args:
        table: Table to assert against. Must be one of: bgp, ospf, interface, evpnVni
        namespace: Filter by SuzieQ namespace
        hostname: Filter by device hostname
    """
    logger.info(
        "suzieq_assert: table=%s namespace=%s hostname=%s",
        table, namespace, hostname,
    )

    # Validate table is in ASSERT_TABLES
    if table not in ASSERT_TABLES:
        error_msg = (
            f"Table '{table}' does not support assertions. "
            f"Supported: {', '.join(ASSERT_TABLES)}."
        )
        logger.error("suzieq_assert: %s", error_msg)
        return json.dumps({"error": error_msg, "table": table, "verb": "assert"}, indent=2)

    params = SuzieQClient.build_query_params(
        namespace=namespace,
        hostname=hostname,
    )

    # Assertions are bounded per-entity — no row cap
    result = await client.query(table, "assert", params, max_rows=0)

    if not result["success"]:
        logger.error("suzieq_assert error: %s", result["error"])
    else:
        logger.info("suzieq_assert: table=%s completed", table)

    return format_assert_response(table, result)


# ---------------------------------------------------------------------------
# Tool: suzieq_unique (US4)
# ---------------------------------------------------------------------------
@mcp.tool()
async def suzieq_unique(
    table: str,
    column: str,
    namespace: Optional[str] = None,
    hostname: Optional[str] = None,
    max_rows: Optional[int] = None,
) -> str:
    """Get distinct values and their counts for a specific column in a SuzieQ
    table. Useful for understanding the distribution of values (e.g., unique
    VRFs, unique interface states, unique BGP peer ASNs).

    Responses are bounded with truncation metadata. On high-cardinality columns
    (e.g., macaddr, ipAddress), narrow with namespace/hostname first.

    Args:
        table: SuzieQ table name
        column: Column name to get unique values for
        namespace: Filter by SuzieQ namespace
        hostname: Filter by device hostname
        max_rows: Override the default row cap (default: 200)
    """
    logger.info(
        "suzieq_unique: table=%s column=%s namespace=%s hostname=%s max_rows=%s",
        table, column, namespace, hostname, max_rows,
    )

    params = SuzieQClient.build_query_params(
        namespace=namespace,
        hostname=hostname,
        columns=column,
    )

    result = await client.query(table, "unique", params, max_rows=max_rows)

    if not result["success"]:
        logger.error("suzieq_unique error: %s", result["error"])
    else:
        trunc = result.get("truncation", {})
        logger.info(
            "suzieq_unique: table=%s column=%s returned %d/%d unique values",
            table, column,
            trunc.get("rows_returned", 0),
            trunc.get("rows_available", 0),
        )

    filters_applied = {
        k: v
        for k, v in {
            "namespace": namespace,
            "hostname": hostname,
            "column": column,
            "max_rows": max_rows or client.max_rows,
        }.items()
        if v is not None
    }

    return format_query_response(table, "unique", result, filters_applied)


# ---------------------------------------------------------------------------
# Tool: suzieq_path (US5)
# ---------------------------------------------------------------------------
@mcp.tool()
async def suzieq_path(
    namespace: str,
    source: str,
    destination: str,
    vrf: Optional[str] = None,
) -> str:
    """Trace the forwarding path between two endpoints through the network.
    Returns hop-by-hop path with ingress/egress interfaces and forwarding
    decisions at each node.

    Path traces are inherently bounded (one path). Responses include
    data_freshness so the consumer can detect stale lake state.

    Args:
        namespace: SuzieQ namespace (required for path resolution)
        source: Source IP address
        destination: Destination IP address
        vrf: VRF name (default: "default")
    """
    effective_vrf = vrf or "default"

    logger.info(
        "suzieq_path: namespace=%s source=%s destination=%s vrf=%s",
        namespace, source, destination, effective_vrf,
    )

    result = await client.query_path(
        namespace=namespace,
        source=source,
        destination=destination,
        vrf=effective_vrf,
    )

    if not result["success"]:
        logger.error("suzieq_path error: %s", result["error"])
    else:
        hop_count = len(result["data"]) if isinstance(result["data"], list) else 0
        logger.info(
            "suzieq_path: %s -> %s returned %d hops",
            source, destination, hop_count,
        )

    return format_path_response(
        namespace=namespace,
        source=source,
        destination=destination,
        vrf=effective_vrf,
        result=result,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")
