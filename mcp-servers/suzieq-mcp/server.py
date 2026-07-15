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
        "SuzieQ MCP server starting — api_url=%s verify_ssl=%s timeout=%ds",
        client.api_url,
        client.verify_ssl,
        client.timeout,
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
# Response formatters
# ---------------------------------------------------------------------------
def format_query_response(
    table: str,
    verb: str,
    result: dict,
    filters_applied: dict,
) -> str:
    """Format a SuzieQ query result into a standardized JSON response.

    Returns a JSON string with table, verb, row_count, filters_applied, and data.
    Empty results return a descriptive message rather than an error.
    """
    if not result["success"]:
        return json.dumps(
            {"error": result["error"], "table": table, "verb": verb},
            indent=2,
        )

    data = result["data"]
    row_count = len(data) if isinstance(data, list) else 0

    if row_count == 0:
        return json.dumps(
            {
                "table": table,
                "verb": verb,
                "row_count": 0,
                "filters_applied": filters_applied,
                "message": f"No data found for {table} with the specified filters.",
                "data": [],
            },
            indent=2,
        )

    return _gcf_dumps(
        {
            "table": table,
            "verb": verb,
            "row_count": row_count,
            "filters_applied": filters_applied,
            "data": data,
        },
    )


def format_assert_response(table: str, result: dict) -> str:
    """Format assertion results with pass/fail counts and per-device details.

    Handles the case where no data exists for the asserted table.
    """
    if not result["success"]:
        return json.dumps(
            {"error": result["error"], "table": table, "verb": "assert"},
            indent=2,
        )

    data = result["data"]
    if not data or (isinstance(data, list) and len(data) == 0):
        return json.dumps(
            {
                "table": table,
                "verb": "assert",
                "message": f"Assertion cannot be evaluated: no data found for table '{table}'. "
                "Ensure devices are being polled and the table has data.",
                "pass_count": 0,
                "fail_count": 0,
                "data": [],
            },
            indent=2,
        )

    # Count pass/fail from assertion results
    pass_count = 0
    fail_count = 0
    failures = []

    if isinstance(data, list):
        for record in data:
            if isinstance(record, dict):
                # SuzieQ assert returns records with an 'assert' field
                assert_result = record.get("assert", record.get("assertReason", ""))
                if assert_result == "pass":
                    pass_count += 1
                else:
                    fail_count += 1
                    failures.append(record)
            else:
                pass_count += 1

    return _gcf_dumps(
        {
            "table": table,
            "verb": "assert",
            "pass_count": pass_count,
            "fail_count": fail_count,
            "total": pass_count + fail_count,
            "status": "PASS" if fail_count == 0 else "FAIL",
            "failures": failures if failures else [],
            "data": data,
        },
    )


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
        return json.dumps(
            {
                "namespace": namespace,
                "source": source,
                "destination": destination,
                "vrf": vrf,
                "hop_count": 0,
                "message": f"No path found from {source} to {destination} in namespace '{namespace}'. "
                "The endpoints may be unreachable or not monitored by SuzieQ.",
                "hops": [],
            },
            indent=2,
        )

    return _gcf_dumps(
        {
            "namespace": namespace,
            "source": source,
            "destination": destination,
            "vrf": vrf,
            "hop_count": hop_count,
            "hops": data,
        },
    )


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
) -> str:
    """Query detailed network state data from any SuzieQ table. Supports filtering
    by device, namespace, time range, and columns. Use for current or historical
    (time-travel) network state queries.

    Args:
        table: SuzieQ table name (e.g., "bgp", "route", "interface", "ospf",
               "arpnd", "mac", "lldp", "vlan", "mlag", "device", "evpnVni",
               "ifCounters", "address", "inventory")
        namespace: Filter by SuzieQ namespace
        hostname: Filter by device hostname
        columns: Comma-separated column names to return (default: all columns)
        start_time: Start time for time-travel query (ISO 8601 or relative e.g. "1h", "2d")
        end_time: End time for time-travel query (ISO 8601 or relative)
        view: Data view: "latest" (default), "all", or "changes"
        filters: Additional filters as key=value pairs separated by ampersand
                 (e.g. "state=Established&vrf=default")
    """
    logger.info(
        "suzieq_show: table=%s namespace=%s hostname=%s columns=%s "
        "start_time=%s end_time=%s view=%s filters=%s",
        table, namespace, hostname, columns,
        start_time, end_time, view, filters,
    )

    if table not in KNOWN_TABLES:
        logger.warning(
            "Table '%s' not in known tables list. Forwarding to SuzieQ anyway.", table
        )

    # When start_time is provided without an explicit view, default to "all"
    # so historical data is actually returned (US2)
    effective_view = view
    if start_time and not view:
        effective_view = "all"

    params = SuzieQClient.build_query_params(
        namespace=namespace,
        hostname=hostname,
        columns=columns,
        start_time=start_time,
        end_time=end_time,
        view=effective_view,
        filters=filters,
    )

    result = await client.query(table, "show", params)

    if not result["success"]:
        logger.error("suzieq_show error: %s", result["error"])
    else:
        row_count = len(result["data"]) if isinstance(result["data"], list) else 0
        logger.info("suzieq_show: table=%s returned %d rows", table, row_count)

    filters_applied = {
        k: v
        for k, v in {
            "namespace": namespace,
            "hostname": hostname,
            "columns": columns,
            "start_time": start_time,
            "end_time": end_time,
            "view": effective_view,
            "filters": filters,
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
    individual records.

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

    result = await client.query(table, "summarize", params)

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

    result = await client.query(table, "assert", params)

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
) -> str:
    """Get distinct values and their counts for a specific column in a SuzieQ
    table. Useful for understanding the distribution of values (e.g., unique
    VRFs, unique interface states, unique BGP peer ASNs).

    Args:
        table: SuzieQ table name
        column: Column name to get unique values for
        namespace: Filter by SuzieQ namespace
        hostname: Filter by device hostname
    """
    logger.info(
        "suzieq_unique: table=%s column=%s namespace=%s hostname=%s",
        table, column, namespace, hostname,
    )

    params = SuzieQClient.build_query_params(
        namespace=namespace,
        hostname=hostname,
        columns=column,
    )

    result = await client.query(table, "unique", params)

    if not result["success"]:
        logger.error("suzieq_unique error: %s", result["error"])
    else:
        row_count = len(result["data"]) if isinstance(result["data"], list) else 0
        logger.info(
            "suzieq_unique: table=%s column=%s returned %d unique values",
            table, column, row_count,
        )

    filters_applied = {
        k: v
        for k, v in {
            "namespace": namespace,
            "hostname": hostname,
            "column": column,
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
