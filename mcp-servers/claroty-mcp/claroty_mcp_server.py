#!/usr/bin/env python3
"""Claroty xDome MCP Server — FastMCP entry point.

Registers 21 tools (15 read-only + 6 ITSM-gated writes) for OT/IoT/IoMT
visibility, vulnerability triage, alert response, and Purdue-model
classification via the Claroty xDome REST API.

Transport: stdio (JSON-RPC 2.0) via FastMCP.
Configuration: 5 environment variables (see .env.example).

Constitution alignment:
  Principle V   — FastMCP / MCP-Native Integration.
  Principle II  — Read-Before-Write (15 reads, 6 gated writes).
  Principle III — ITSM-Gated Changes (every write calls validate_change_request).
  Principle XIII — Credential Safety (CLAROTY_API_TOKEN read from env, never logged).
"""

from __future__ import annotations

import logging
import os
import sys

# Allow `from clients...`, `from tools...`, etc. when run as a script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

from clients.claroty_client import client
from tools.alerts import (
    acknowledge_alert,
    get_alert_with_devices,
    list_alerts,
)
from tools.audit_governance import (
    get_audit_log,
    list_organization_zones,
)
from tools.devices import (
    get_device_communication_map,
    get_device_details,
    list_devices,
    set_device_custom_attribute,
    set_device_purdue_level,
)
from tools.servers_ot import (
    get_server_interfaces,
    list_ot_activity_events,
    list_servers,
)
from tools.sites_edge import (
    get_site,
    list_edge_locations,
    list_sites,
)
from tools.user_actions import (
    assign_alerts,
    label_alerts,
)
from tools.vulnerabilities import (
    get_vulnerable_devices,
    list_vulnerabilities,
    set_vulnerability_relevance,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("claroty-mcp")

# Validate configuration at import time so failures are loud.
try:
    client.validate_config()
    logger.info(
        "Claroty MCP starting — api_url=%s verify_ssl=%s timeout=%ds rate=%d/min",
        client.api_url,
        client.verify_ssl,
        client.timeout,
        client.rate_limit_per_min,
    )
except ValueError as exc:
    logger.error("Configuration error: %s", exc)
    print(f"ERROR: {exc}", file=sys.stderr)
    sys.exit(1)


mcp = FastMCP("claroty-mcp")

# --- Read-only tools (15) ---
mcp.tool()(list_devices)
mcp.tool()(get_device_details)
mcp.tool()(get_device_communication_map)
mcp.tool()(list_alerts)
mcp.tool()(get_alert_with_devices)
mcp.tool()(list_vulnerabilities)
mcp.tool()(get_vulnerable_devices)
mcp.tool()(list_sites)
mcp.tool()(get_site)
mcp.tool()(list_edge_locations)
mcp.tool()(list_servers)
mcp.tool()(get_server_interfaces)
mcp.tool()(list_ot_activity_events)
mcp.tool()(get_audit_log)
mcp.tool()(list_organization_zones)

# --- ITSM-gated write tools (6) ---
mcp.tool()(acknowledge_alert)
mcp.tool()(set_vulnerability_relevance)
mcp.tool()(set_device_purdue_level)
mcp.tool()(set_device_custom_attribute)
mcp.tool()(label_alerts)
mcp.tool()(assign_alerts)


def main() -> None:
    logger.info("Claroty MCP server ready — 21 tools (15 read + 6 ITSM-gated write)")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
