#!/usr/bin/env python3
"""Wrapper to run GAIT MCP server in stdio mode (default is SSE)."""
import sys
import os
import asyncio

# Add the gait_mcp directory to path
gait_dir = os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "gait_mcp")
sys.path.insert(0, gait_dir)

# Import the FastMCP instance from the GAIT server
from gait_mcp import mcp  # noqa: E402

if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())
