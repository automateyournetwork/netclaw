"""Install GCF serialization on FastMCP servers (token-efficient tool results).

Wraps every registered tool so dict/list return values are encoded with Dayna's
GCF serializer before FastMCP JSON-ifies them into TextContent. Strings and
binary/content blocks pass through unchanged. Fail-open to JSON on any error.

Usage (after all @mcp.tool registrations)::

    from netclaw_tokens.mcp_gcf import install_gcf_on_fastmcp
    install_gcf_on_fastmcp(mcp)

Environment:
  NETCLAW_GCF_MODE = full|graph|generic|off  (default full; off disables wrapping)
"""

from __future__ import annotations

import functools
import inspect
import json
import logging
import os
from typing import Any, Callable

logger = logging.getLogger("netclaw_tokens.mcp_gcf")


def gcf_dumps(data: Any) -> str:
    """Serialize data with GCF; JSON fallback. Always returns str."""
    if isinstance(data, str):
        return data
    mode = os.environ.get("NETCLAW_GCF_MODE", "full").lower()
    if mode == "off":
        return json.dumps(data, indent=2, default=str)
    try:
        from netclaw_tokens.gcf_serializer import serialize_response

        result = serialize_response(data, use_session=True, use_delta=True)
        if isinstance(result, dict):
            encoded = result.get("encoded_data")
            if encoded:
                if result.get("fallback_used"):
                    logger.debug(
                        "GCF fallback_used profile=%s", result.get("profile_used")
                    )
                else:
                    logger.debug(
                        "GCF %s save=%.1f%% (%s→%s tokens)",
                        result.get("profile_used"),
                        result.get("savings_pct") or 0,
                        result.get("json_token_count"),
                        result.get("gcf_token_count"),
                    )
                return encoded
        return str(result)
    except Exception as exc:
        logger.debug("GCF encode failed (%s); JSON fallback", exc)
        return json.dumps(data, indent=2, default=str)


def _wrap_tool_fn(fn: Callable[..., Any], tool_name: str) -> Callable[..., Any]:
    """Wrap a tool callable to GCF-encode dict/list results."""

    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await fn(*args, **kwargs)
            return _maybe_gcf(result, tool_name)

        return async_wrapper

    @functools.wraps(fn)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        result = fn(*args, **kwargs)
        return _maybe_gcf(result, tool_name)

    return sync_wrapper


def _maybe_gcf(result: Any, tool_name: str) -> Any:
    if result is None:
        return result
    # Already text / content blocks / binary — leave alone
    if isinstance(result, (str, bytes, bytearray)):
        return result
    type_name = type(result).__name__
    if type_name in ("TextContent", "ImageContent", "CallToolResult", "Image", "Audio"):
        return result
    if isinstance(result, (dict, list, tuple)):
        return gcf_dumps(result)
    # Pydantic models etc. — try dump then GCF
    if hasattr(result, "model_dump"):
        try:
            return gcf_dumps(result.model_dump(mode="json"))
        except Exception:
            pass
    return result


def _install_via_tool_manager(mcp: Any, label: str | None) -> int | None:
    """Legacy mcp.server.fastmcp path (``_tool_manager._tools``)."""
    tm = getattr(mcp, "_tool_manager", None)
    tools = getattr(tm, "_tools", None) if tm is not None else None
    if not isinstance(tools, dict) or not tools:
        tools = getattr(mcp, "_tools", None)
    if not isinstance(tools, dict):
        return None

    wrapped = 0
    for name, tool in list(tools.items()):
        fn = getattr(tool, "fn", None)
        if fn is None:
            continue
        if getattr(fn, "_gcf_wrapped", False):
            continue
        new_fn = _wrap_tool_fn(fn, name)
        new_fn._gcf_wrapped = True  # type: ignore[attr-defined]
        try:
            tool.fn = new_fn
        except Exception:
            object.__setattr__(tool, "fn", new_fn)
        if hasattr(tool, "is_async"):
            try:
                tool.is_async = inspect.iscoroutinefunction(fn)
            except Exception:
                object.__setattr__(tool, "is_async", inspect.iscoroutinefunction(fn))
        wrapped += 1
    return wrapped


def _install_via_middleware(mcp: Any, label: str | None) -> int | None:
    """Standalone ``fastmcp`` package path (add_middleware / on_call_tool)."""
    if not hasattr(mcp, "add_middleware"):
        return None
    try:
        from fastmcp.server.middleware import Middleware
        from mcp.types import TextContent
    except Exception as exc:
        logger.debug("middleware imports failed: %s", exc)
        return None

    # Avoid double-install
    existing = getattr(mcp, "middleware", None) or []
    for mw in existing:
        if type(mw).__name__ == "GCFResultMiddleware":
            return 0

    class GCFResultMiddleware(Middleware):
        async def on_call_tool(self, context, call_next):  # type: ignore[no-untyped-def]
            result = await call_next(context)
            try:
                content = getattr(result, "content", None)
                if not content:
                    return result
                new_blocks = []
                changed = False
                for block in content:
                    text = getattr(block, "text", None)
                    if not isinstance(text, str) or not text.strip():
                        new_blocks.append(block)
                        continue
                    # Only re-encode JSON payloads (FastMCP default serialization)
                    s = text.lstrip()
                    if not (s.startswith("{") or s.startswith("[")):
                        new_blocks.append(block)
                        continue
                    try:
                        data = json.loads(text)
                    except Exception:
                        new_blocks.append(block)
                        continue
                    encoded = gcf_dumps(data)
                    if encoded != text:
                        changed = True
                        new_blocks.append(TextContent(type="text", text=encoded))
                    else:
                        new_blocks.append(block)
                if not changed:
                    return result
                # Rebuild ToolResult preserving structured_content/meta when present
                try:
                    from fastmcp.tools.base import ToolResult

                    return ToolResult(
                        content=new_blocks,
                        structured_content=None,  # GCF is text; drop JSON structured twin
                        meta=getattr(result, "meta", None),
                    )
                except Exception:
                    try:
                        result.content = new_blocks
                    except Exception:
                        object.__setattr__(result, "content", new_blocks)
                    return result
            except Exception as e:
                logger.debug("GCF middleware skip: %s", e)
                return result

    mcp.add_middleware(GCFResultMiddleware())
    logger.info(
        "GCF middleware installed on %s (mode=%s)",
        label or getattr(mcp, "name", type(mcp).__name__),
        os.environ.get("NETCLAW_GCF_MODE", "full"),
    )
    return 1  # one middleware installed


def install_gcf_on_fastmcp(mcp: Any, *, label: str | None = None) -> int:
    """Install GCF on a FastMCP instance (legacy tool wrap or new middleware).

    Returns a positive count on success (tools wrapped or middleware installed).
    """
    if os.environ.get("NETCLAW_GCF_MODE", "full").lower() == "off":
        logger.info("NETCLAW_GCF_MODE=off — skipping GCF install on %s", label or mcp)
        return 0

    # Prefer tool-fn wrap when available (mcp.server.fastmcp / greynoise / memory)
    n = _install_via_tool_manager(mcp, label)
    if n is not None:
        logger.info(
            "GCF installed on %s — wrapped %d tool(s) (mode=%s)",
            label or getattr(mcp, "name", type(mcp).__name__),
            n,
            os.environ.get("NETCLAW_GCF_MODE", "full"),
        )
        return n

    n = _install_via_middleware(mcp, label)
    if n is not None:
        return n

    logger.warning("Cannot install GCF on %s — unknown FastMCP layout", label or type(mcp))
    return 0
