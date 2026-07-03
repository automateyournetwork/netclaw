#!/usr/bin/env python3
"""
EVE-NG MCP Server — entry point.

38 tools across 6 domains:
  System        (3)  — status, auth, list images          [tools_lab.py]
  Lab Lifecycle (6)  — list, get, create, delete, export, import [tools_lab.py]
  Node Ops      (9)  — list, get, create, delete, start, stop, start-lab, stop-lab, wipe [tools_node.py]
  Network/Topo  (8)  — topology, networks, node-types, interfaces, connect [tools_network.py]
  Console Exec  (6)  — discover, exec-ios, exec-junos, exec-vpcs, exec-eos, exec-nxos [tools_console_exec.py]
  Config Mgmt   (7)  — get/set/export/wipe config, startup-mode, list-summaries, get-all [tools_config.py]

Module layout:
  mcp_init.py          — shared FastMCP instance
  eve_client.py        — EVEClient, helpers, get_client() singleton
  eve_console.py       — TelnetSession + IOS/Junos/EOS/NX-OS drivers
  tools_*.py           — MCP tool registrations (import triggers @mcp.tool() decoration)
"""

import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    stream=sys.stderr,
)

# Importing tool modules registers all 38 tools onto the shared mcp instance.
from mcp_init import mcp          # noqa: E402
import tools_lab                  # noqa: F401, E402 — System (3) + Lab Lifecycle (6)
import tools_node                 # noqa: F401, E402 — Node Ops (9)
import tools_network              # noqa: F401, E402 — Network/Topo (8)
import tools_console_exec         # noqa: F401, E402 — Console Exec (6)
import tools_config               # noqa: F401, E402 — Config Mgmt (7)

if __name__ == "__main__":
    log = logging.getLogger("eve-ng-mcp")
    log.info("EVE-NG MCP Server starting")
    log.info("EVE URL:          %s", os.getenv("EVE_URL", "http://127.0.0.1"))
    log.info("EVE User:         %s", os.getenv("EVE_USER", ""))
    log.info("Console host:     %s", os.getenv("EVE_CONSOLE_HOST", "127.0.0.1"))
    log.info("Session TTL:      %ss", os.getenv("EVE_SESSION_TTL", "1800"))
    log.info("SSL verification: %s", os.getenv("EVE_VERIFY_SSL", "true"))
    mcp.run(transport="stdio")
