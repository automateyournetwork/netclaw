"""TOON / GCF serialization shim for the Halo MCP server.

Mirrors auvik-mcp/utils/toon_helper.py: attempts to use the netclaw_tokens
GCF serializer for token-efficient output; falls back to standard json.dumps
if the optional package is unavailable.
"""

import json
import os
import sys

# Allow the optional netclaw_tokens package (in src/) to be found.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src"),
)


def gcf_dumps(data, **kwargs) -> str:
    """Serialize data using GCF format, falling back to JSON if unavailable."""
    try:
        from netclaw_tokens.gcf_serializer import serialize_response  # type: ignore

        return serialize_response(data).gcf_data
    except Exception:
        return json.dumps(data, indent=2, default=str)
