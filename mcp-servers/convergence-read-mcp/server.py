#!/usr/bin/env python3
"""Optional, read-only Convergence flow evidence over MCP stdio."""
from fastmcp import FastMCP
from client import ConvergenceClient, ReadError, Settings, error_result

mcp = FastMCP("convergence-read-mcp", strict_input_validation=True)


def configured_client():
    # Read configuration per invocation: disabling never leaves an enabled cache.
    return ConvergenceClient(Settings.from_env())


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True})
async def convergence_flow_summary(range: str = "1h", exporter: str | None = None) -> dict:
    """Read retained traffic rankings for the fixed configured site and allowed exporters.

    Choose 15m, 1h, 6h or 24h. Preserve the returned start/end for evidence.
    Exported counters and receipt age are not a threat verdict or collector health.
    """
    try:
        return await configured_client().summary(range, exporter)
    except ReadError as error:
        return error_result(error.code)


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True})
async def convergence_flow_evidence(address: str, start: str, end: str, exporter: str | None = None) -> dict:
    """Read at most 100 retained records involving an IP in the exact summary window.

    Records include both source and destination directions; their bounded subset
    need not reconstruct any directional ranking total. No raw query is accepted.
    """
    try:
        return await configured_client().evidence(address, start, end, exporter)
    except ReadError as error:
        return error_result(error.code)


if __name__ == "__main__":
    mcp.run(transport="stdio")
