import logging
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import ipaddress as ipaddr
from mcp.server.fastmcp import FastMCP

# === 1. Logging Setup ===

# Configure global logging format and level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Create a logger specifically for this MCP server
logger = logging.getLogger("SubnetFastMCPServer")

# === 2. Environment Loading ===

# Load environment variables from .env (useful for dev/test environments)
load_dotenv()

# === 3. Input Validation Schema ===

# Define the expected input to the tool using Pydantic
class SubnetInput(BaseModel):
    cidr: str = Field(..., description="Network in CIDR notation, e.g. 192.168.1.0/24")

# === 4. Initialize MCP Server ===

# Create a FastMCP instance with a display name for this server
mcp = FastMCP("Subnet Calculator MCP")

# === 5. Define the Tool ===

# This registers the tool `subnet_calculator` with the MCP runtime
@mcp.tool(
    name="subnet_calculator",
    description="Calculate network details plus previous and next subnets"
)
async def subnet_calculator(cidr: str) -> dict:
    """
    The actual function invoked when the tool is called via MCP.

    Args:
        cidr: A string CIDR input like '192.168.0.0/24'

    Returns:
        A dictionary of subnet details (which MCP serializes to JSON)
    """
    logger.info("🚀 Tool triggered with CIDR: %s", cidr)

    try:
        # Parse the input CIDR using ipaddress with non-strict mode (allows host bits)
        network = ipaddr.IPv4Network(cidr, strict=False)
        size = network.num_addresses
        base = int(network.network_address)

        # Calculate previous and next subnets (same size) based on address math
        prev_sub = ipaddr.IPv4Network(f"{ipaddr.IPv4Address(base - size)}/{network.prefixlen}")
        next_sub = ipaddr.IPv4Network(f"{ipaddr.IPv4Address(base + size)}/{network.prefixlen}")

        # Cap the number of hosts previewed to avoid flooding results for /8 or similar
        MAX_HOST_PREVIEW = 10

        usable_hosts = [
            str(ip)
            for i, ip in enumerate(network)
            if ip not in (network.network_address, network.broadcast_address) and i < MAX_HOST_PREVIEW + 1
        ]

        # Construct a dictionary of results to be returned to the MCP client
        result = {
            # Core subnet parameters
            "network_address": str(network.network_address),
            "broadcast_address": str(network.broadcast_address),
            "netmask": str(network.netmask),
            "wildcard_mask": str(network.hostmask),
            "prefix_length": network.prefixlen,
            "with_netmask": str(network.with_netmask),
            "with_hostmask": str(network.with_hostmask),

            # Host range details
            "num_addresses": network.num_addresses,
            "usable_hosts_count": max(0, network.num_addresses - 2),
            "usable_hosts_preview": usable_hosts,
            "first_usable": (str(list(network)[1]) if network.num_addresses >= 2 else None),
            "last_usable": (str(list(network)[-2]) if network.num_addresses >= 2 else None),
            "address_range": (
                f"{list(network)[1]} - {list(network)[-2]}"
                if network.num_addresses >= 2 else "N/A"
            ),

            # Neighboring subnets (previous/next)
            "previous_subnet": str(prev_sub),
            "next_subnet": str(next_sub),

            # Bit-level subnetting information
            "host_bits": 32 - network.prefixlen,
            "total_bits": 32,

            # Address classification flags
            "is_private": network.is_private,
            "is_global": network.is_global,
            "is_link_local": network.is_link_local,
            "is_multicast": network.is_multicast,
            "is_loopback": network.is_loopback,
            "is_reserved": network.is_reserved,
            "is_unspecified": network.is_unspecified,

            # Human-friendly summary and notes
            "summary": f"CIDR {cidr} has {network.num_addresses} total addresses "
                       f"with {max(0, network.num_addresses - 2)} usable hosts "
                       f"({network.prefixlen} prefix, {32 - network.prefixlen} host bits).",
            "note": f"Showing first {MAX_HOST_PREVIEW} usable hosts only (capped for large subnets)."
        }

        logger.info(f"Calculated result: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in subnet_calculator tool: {e}", exc_info=True)
        return {"error": str(e)}

# === 6. MCP Server Entrypoint ===

if __name__ == "__main__":
    logger.info("Starting Subnet Calculator MCP in stdio mode")
    
    # Start the server in stdio mode (stdin/stdout communication with agent)
    mcp.run(transport="stdio")
