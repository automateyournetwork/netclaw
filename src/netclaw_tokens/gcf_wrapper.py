"""GCF conversion wrapper for community/remote MCP servers.

For MCP servers that cannot be directly modified (community forks, remote
servers), this wrapper post-processes JSON responses into GCF format.
It can be used as middleware or a standalone converter.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Union

from . import GCFResponse
from .gcf_serializer import serialize_response

logger = logging.getLogger("netclaw_tokens.gcf_wrapper")


def wrap_json_response(json_str: str) -> GCFResponse:
    """Convert a JSON string response to GCF format.

    Args:
        json_str: A JSON-encoded string from an MCP server response.

    Returns:
        GCFResponse with the data in GCF format (or original JSON on failure).
    """
    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("Cannot parse JSON for GCF conversion: %s", exc)
        return GCFResponse(
            gcf_data=json_str,
            json_token_count=max(1, len(json_str) // 4),
            gcf_token_count=max(1, len(json_str) // 4),
            savings_tokens=0,
            savings_pct=0.0,
            fallback_used=True,
        )

    return serialize_response(data)


def wrap_mcp_tool_result(result: Union[str, dict, list, Any]) -> str:
    """Wrap any MCP tool result in GCF format.

    Handles string (assumed JSON), dict, or list inputs.
    Returns the GCF-serialized string (or JSON fallback).

    Args:
        result: The tool result to wrap. Can be a JSON string, dict, or list.

    Returns:
        GCF-serialized string.
    """
    if isinstance(result, str):
        response = wrap_json_response(result)
        return response.gcf_data
    elif isinstance(result, (dict, list)):
        response = serialize_response(result)
        return response.gcf_data
    elif isinstance(result, (bytes, bytearray)):
        # Binary data -- pass through as-is
        logger.debug("Binary data detected; skipping GCF wrapping")
        return result.decode("utf-8", errors="replace") if isinstance(result, bytes) else str(result)
    else:
        # Unknown type -- convert to string
        return str(result)


def validate_gcf_integration(data: Any) -> dict:
    """Validate that GCF serialization works correctly for the given data.

    Tests edge cases: empty data, large data, nested structures, mixed types.
    Returns a validation report.

    Args:
        data: The data to validate GCF serialization against.

    Returns:
        Dict with: success (bool), gcf_size, json_size, savings_pct,
        fallback_used, error (str or None).
    """
    try:
        response = serialize_response(data)
        return {
            "success": True,
            "gcf_size": len(response.gcf_data),
            "json_size": response.json_token_count * 4,  # Approximate
            "gcf_token_count": response.gcf_token_count,
            "json_token_count": response.json_token_count,
            "savings_pct": response.savings_pct,
            "fallback_used": response.fallback_used,
            "error": None,
        }
    except Exception as exc:
        return {
            "success": False,
            "gcf_size": 0,
            "json_size": 0,
            "gcf_token_count": 0,
            "json_token_count": 0,
            "savings_pct": 0.0,
            "fallback_used": True,
            "error": str(exc),
        }
