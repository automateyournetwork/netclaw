#!/usr/bin/env python3
"""Azure Network MCP Server - FastMCP entry point with GAIT audit logging."""

from __future__ import annotations

import json
import logging
import os
import sys
import functools
from datetime import datetime, timezone
from typing import Optional

# Add the server directory to the path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

from clients.azure_client import azure_client_factory
from utils.rate_limiter import format_error_response


def _gcf_dumps(data, **kwargs) -> str:
    """Serialize data using GCF with graph auto-detection and session dedup."""
    try:
        from netclaw_tokens.gcf_serializer import serialize_response
        result = serialize_response(data, use_session=True, use_delta=True)
        return result["encoded_data"]
    except Exception:
        return json.dumps(data, indent=2, default=str)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("azure-network-mcp")

# Initialize FastMCP server
mcp = FastMCP("azure-network-mcp")


# --- GAIT Audit Logging ---

def gait_audit_log(operation: str, target: str, subscription_id: Optional[str] = None,
                   status: str = "success", details: Optional[str] = None) -> None:
    """Log a GAIT audit entry for an MCP tool operation."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "target": target,
        "subscription_id": subscription_id or "default",
        "status": status,
    }
    if details:
        entry["details"] = details
    logger.info(f"GAIT: {json.dumps(entry)}")


def with_gait_logging(tool_name: str):
    """Decorator to wrap MCP tool functions with GAIT audit logging."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            subscription_id = kwargs.get("subscription_id")
            target = kwargs.get("vnet_name") or kwargs.get("nsg_name") or kwargs.get(
                "circuit_name") or kwargs.get("gateway_name") or kwargs.get(
                "policy_name") or kwargs.get("lb_name") or kwargs.get(
                "nic_name") or kwargs.get("zone_name") or kwargs.get(
                "resource_group") or "all"
            gait_audit_log(tool_name, target, subscription_id, "started")
            try:
                result = await func(*args, **kwargs)
                gait_audit_log(tool_name, target, subscription_id, "success")
                return result
            except Exception as e:
                gait_audit_log(tool_name, target, subscription_id, "error", str(e))
                return format_error_response(e)
        return wrapper
    return decorator


# --- Subscription Listing Tool ---

async def azure_list_subscriptions() -> str:
    """List all accessible Azure subscriptions for the authenticated credential."""
    sub_client = azure_client_factory.get_subscription_client()
    subscriptions = []
    for sub in sub_client.subscriptions.list():
        subscriptions.append({
            "subscription_id": sub.subscription_id,
            "display_name": sub.display_name,
            "state": sub.state,
            "tenant_id": getattr(sub, "tenant_id", None),
        })
    return _gcf_dumps(subscriptions)


# --- Import and register all tool modules ---
# Tools are imported here so they register with the FastMCP instance via @mcp.tool()

from tools.vnet import (
    azure_list_vnets,
    azure_get_vnet_details,
    azure_get_vnet_peerings,
)
from tools.nsg import (
    azure_list_nsgs,
    azure_get_nsg_rules,
    azure_get_effective_security_rules,
    azure_audit_nsg_compliance,
)
from tools.expressroute import (
    azure_get_expressroute_status,
    azure_get_expressroute_routes,
)
from tools.vpn_gateway import azure_get_vpn_gateway_status
from tools.firewall import (
    azure_list_firewalls,
    azure_get_firewall_policy,
)
from tools.load_balancer import (
    azure_list_load_balancers,
    azure_get_lb_backend_health,
)
from tools.app_gateway import azure_get_app_gateway_health
from tools.route_table import azure_get_route_tables
from tools.network_watcher import azure_get_network_watcher_status
from tools.private_link import azure_get_private_endpoints
from tools.dns import azure_get_dns_zones

# Register all tools with FastMCP
tools_to_register = [
    azure_list_subscriptions,
    azure_list_vnets,
    azure_get_vnet_details,
    azure_get_vnet_peerings,
    azure_list_nsgs,
    azure_get_nsg_rules,
    azure_get_effective_security_rules,
    azure_audit_nsg_compliance,
    azure_get_expressroute_status,
    azure_get_expressroute_routes,
    azure_get_vpn_gateway_status,
    azure_list_firewalls,
    azure_get_firewall_policy,
    azure_list_load_balancers,
    azure_get_lb_backend_health,
    azure_get_app_gateway_health,
    azure_get_route_tables,
    azure_get_network_watcher_status,
    azure_get_private_endpoints,
    azure_get_dns_zones
]

for tool in tools_to_register:
    mcp.tool()(with_gait_logging(tool.__name__)(tool))


def main():
    """Start the Azure Network MCP server."""
    logger.info("Starting Azure Network MCP Server...")

    # Initialize and validate credentials
    azure_client_factory.initialize()
    if not azure_client_factory.validate_credentials():
        logger.warning(
            "Azure credential validation failed. Tools will return authentication errors. "
            "Verify AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET environment variables."
        )

    default_sub = azure_client_factory.default_subscription_id
    if default_sub:
        logger.info(f"Default subscription: {default_sub}")
    else:
        logger.warning("No default subscription set (AZURE_SUBSCRIPTION_ID not configured).")

    logger.info("Azure Network MCP Server ready - 19 tools registered (18 network + 1 subscription)")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
