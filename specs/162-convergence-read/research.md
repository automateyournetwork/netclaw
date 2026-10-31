# Research

Proposal161 (merged upstream PR309) specifies scope and existing service contracts.
The independently maintained Convergence fork at f54bafca qualifies local demo and
host export with native Linux Docker/K3s CI; those tests do not qualify this new
connector. Existing upstream HUD server uses session/trusted-origin gates and MCP
invocation seams; reuse these instead of importing fork module infrastructure.

Use upstream isolated FastMCP/httpx pins and catalogue generators. Preserve existing
runtime/provider settings. Implement new connector against documented HTTP response
fields; refer to external source for contract compatibility, not copied case code.
