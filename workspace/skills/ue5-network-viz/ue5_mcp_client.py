"""
UE5 MCP Client - HTTP transport client for Unreal Engine 5.8 MCP server.

This module provides a Python client wrapper for communicating with the
built-in Unreal Engine 5.8 MCP server using HTTP + JSON-RPC 2.0 transport.

Key features:
- Automatic session initialization (Mcp-Session-Id handling)
- Tool search mode support (list_toolsets, describe_toolset, call_tool)
- Connectivity health check with retry logic
- Async/await support via httpx
- First-command timeout handling (UE5 MCP warmup)

IMPORTANT: UE5 MCP requires a session handshake before tool calls.
This client handles that automatically via initialize_session().
"""

import os
import asyncio
import json
from typing import Any, Optional
from dataclasses import dataclass, field

import httpx


# Default configuration
DEFAULT_UE5_MCP_URL = "http://127.0.0.1:8000/mcp"
DEFAULT_TIMEOUT = 30.0  # seconds
FIRST_COMMAND_TIMEOUT = 60.0  # UE5 MCP first command can be slow


@dataclass
class UE5MCPError(Exception):
    """Exception raised for UE5 MCP communication errors."""
    message: str
    code: Optional[str] = None
    details: Optional[dict] = None

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


@dataclass
class ToolsetInfo:
    """Information about an available UE5 MCP toolset."""
    name: str
    description: str


@dataclass
class ToolInfo:
    """Information about a tool within a toolset."""
    name: str
    description: str
    parameters: dict = field(default_factory=dict)


@dataclass
class ToolResult:
    """Result from calling a UE5 MCP tool."""
    success: bool
    data: Any = None
    error: Optional[str] = None


class UE5MCPClient:
    """
    Async HTTP client for Unreal Engine 5.8 MCP server.

    CRITICAL: UE5 MCP requires session initialization before tool calls.
    This client automatically handles session management.

    Uses the tool search mode pattern with meta-tools:
    - list_toolsets: Discover available toolsets
    - describe_toolset: Get tool schemas for a toolset
    - call_tool: Execute a tool within a toolset

    Available toolsets (with AllToolsets plugin enabled):
    - editor_toolset.toolsets.actor.ActorTools - spawn, transform, labels
    - editor_toolset.toolsets.scene.SceneTools - level management, camera
    - editor_toolset.toolsets.material_instance.MaterialInstanceTools
    - editor_toolset.toolsets.primitive.PrimitiveTools - geometry
    - editor_toolset.toolsets.object.ObjectTools - property manipulation

    Example:
        async with UE5MCPClient() as client:
            # Session is auto-initialized on first request
            toolsets = await client.list_toolsets()

            # Call a tool from ActorTools
            result = await client.call_tool(
                toolset_name="editor_toolset.toolsets.actor.ActorTools",
                tool_name="get_all_actors",
                arguments={}
            )
    """

    def __init__(
        self,
        url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize UE5 MCP client.

        Args:
            url: UE5 MCP server URL (default: from UE5_MCP_URL env or localhost:8000)
            timeout: Request timeout in seconds (default: 30s)
        """
        self.url = url or os.environ.get("UE5_MCP_URL", DEFAULT_UE5_MCP_URL)
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._request_id = 0
        self._session_id: Optional[str] = None
        self._is_initialized = False
        self._toolset_cache: dict[str, list[ToolInfo]] = {}
        self._available_toolsets: Optional[list[ToolsetInfo]] = None

    async def __aenter__(self) -> "UE5MCPClient":
        """Async context manager entry - initializes HTTP client and session."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        # Auto-initialize session on entry
        await self.initialize_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._session_id = None
        self._is_initialized = False

    def _next_request_id(self) -> int:
        """Generate next JSON-RPC request ID."""
        self._request_id += 1
        return self._request_id

    async def initialize_session(self) -> str:
        """
        Initialize MCP session and get session ID.

        UE5 MCP REQUIRES this before any tool calls. The session ID
        is returned in the 'Mcp-Session-Id' response header.

        Returns:
            Session ID string

        Raises:
            UE5MCPError: If initialization fails
        """
        if self._is_initialized and self._session_id:
            return self._session_id

        if not self._client:
            self._client = httpx.AsyncClient(timeout=self.timeout)

        request_id = self._next_request_id()
        payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"capabilities": {}},
            "id": request_id,
        }

        try:
            # LESSON (found live 2026-07-03, via NetClaw's own from-scratch
            # http.client-based UE5 client, which never had this bug): some
            # UE5 MCP builds respond to `initialize` as a keep-alive
            # text/event-stream that stays open even after the headers (and
            # the Mcp-Session-Id we actually need) have arrived. httpx's
            # plain `.post()` waits for the full response body — i.e. for
            # the connection to close — before returning, which can hang
            # indefinitely on those builds even though the session ID we
            # need was available immediately. Use a streaming request and
            # only read the headers; don't wait for the body.
            async with self._client.stream(
                "POST",
                self.url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=FIRST_COMMAND_TIMEOUT,
            ) as response:
                response.raise_for_status()

                # Extract session ID from response headers
                self._session_id = response.headers.get("Mcp-Session-Id")
                if not self._session_id:
                    # Try case-insensitive search
                    for key, value in response.headers.items():
                        if key.lower() == "mcp-session-id":
                            self._session_id = value
                            break

            if not self._session_id:
                raise UE5MCPError(
                    "No Mcp-Session-Id in response headers. "
                    "UE5 MCP may be misconfigured.",
                    code="NO_SESSION_ID",
                )

            self._is_initialized = True
            return self._session_id

        except httpx.ConnectError as e:
            raise UE5MCPError(
                f"Cannot connect to UE5 MCP server at {self.url}. "
                "Please ensure Unreal Editor is running with MCP plugin enabled. "
                "Run 'ModelContextProtocol.StartServer' in UE5 console.",
                code="CONNECTION_ERROR",
            ) from e
        except httpx.TimeoutException as e:
            raise UE5MCPError(
                f"Session initialization timed out after {FIRST_COMMAND_TIMEOUT}s. "
                "UE5 MCP may be initializing - try again.",
                code="TIMEOUT",
            ) from e

    async def _send_request(
        self,
        method: str,
        params: Optional[dict] = None,
        timeout_override: Optional[float] = None,
    ) -> dict:
        """
        Send a JSON-RPC 2.0 request to UE5 MCP server.

        Automatically ensures session is initialized and includes
        Mcp-Session-Id header in all requests.

        Args:
            method: JSON-RPC method name
            params: Method parameters
            timeout_override: Override default timeout

        Returns:
            Response result data

        Raises:
            UE5MCPError: On communication or protocol errors
        """
        # Ensure session is initialized
        if not self._is_initialized:
            await self.initialize_session()

        if not self._client:
            raise UE5MCPError("Client not initialized. Use async context manager.")

        request_id = self._next_request_id()
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id,
        }
        if params:
            payload["params"] = params

        headers = {
            "Content-Type": "application/json",
            "Mcp-Session-Id": self._session_id,
        }

        effective_timeout = timeout_override or self.timeout

        try:
            # LESSON (found live 2026-07-03): some UE5 MCP builds keep the
            # text/event-stream connection open as a keep-alive stream even
            # after the actual JSON-RPC answer has been sent. The old code
            # used `self._client.post(...)` + `response.text`, which makes
            # httpx wait for the full response body — i.e. for the
            # connection to close — before returning. On a keep-alive build
            # that hangs until the timeout fires, even though the real
            # answer arrived instantly. NetClaw's own from-scratch
            # http.client-based UE5 client never hit this because it reads
            # the SSE stream line-by-line and stops as soon as it sees a
            # complete JSON-RPC object. Do the same here via httpx's
            # streaming API instead of waiting for the body to finish.
            async with self._client.stream(
                "POST",
                self.url,
                json=payload,
                headers=headers,
                timeout=effective_timeout,
            ) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")

                if "text/event-stream" in content_type:
                    result = None
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line.startswith("data:"):
                            continue
                        data = line[len("data:"):].strip()
                        try:
                            obj = json.loads(data)
                        except (json.JSONDecodeError, ValueError):
                            continue
                        if "result" in obj or "error" in obj or obj.get("id") == request_id:
                            result = obj
                            break
                    if result is None:
                        raise UE5MCPError(
                            "SSE stream ended without a JSON-RPC response",
                            code="EMPTY_STREAM",
                        )
                else:
                    text = (await response.aread()).decode(errors="replace").strip()
                    try:
                        result = json.loads(text)
                    except Exception as e:
                        raise UE5MCPError(
                            f"Invalid JSON response from UE5 MCP: {text[:200]}",
                            code="PARSE_ERROR",
                        ) from e

        except httpx.ConnectError as e:
            # Session might have expired - try reinitializing
            self._is_initialized = False
            raise UE5MCPError(
                f"Lost connection to UE5 MCP server at {self.url}. "
                "UE5 may have restarted - will reinitialize session on next call.",
                code="CONNECTION_ERROR",
            ) from e
        except httpx.TimeoutException as e:
            raise UE5MCPError(
                f"Request timed out after {effective_timeout}s.",
                code="TIMEOUT",
            ) from e
        except httpx.HTTPStatusError as e:
            raise UE5MCPError(
                f"HTTP error: {e.response.status_code}",
                code="HTTP_ERROR",
            ) from e

        # Check for JSON-RPC error
        if "error" in result:
            error = result["error"]
            raise UE5MCPError(
                error.get("message", "Unknown error"),
                code=str(error.get("code", "UNKNOWN")),
                details=error.get("data"),
            )

        return result.get("result", {})

    async def ping(self, timeout: float = 5.0) -> bool:
        """
        Check if UE5 MCP server is reachable and session can be established.

        Args:
            timeout: Ping timeout in seconds

        Returns:
            True if server is reachable and session established
        """
        try:
            await self.initialize_session()
            return self._is_initialized and self._session_id is not None
        except UE5MCPError:
            return False

    async def list_toolsets(self) -> list[ToolsetInfo]:
        """
        List available toolsets from UE5 MCP server.

        Returns:
            List of available toolsets with names and descriptions
        """
        if self._available_toolsets is not None:
            return self._available_toolsets

        result = await self._send_request(
            "tools/call",
            params={
                "name": "list_toolsets",
                "arguments": {},
            },
        )

        # Parse the text content which is a markdown-style list
        toolsets = []
        content = result.get("content", [])
        if content and isinstance(content, list):
            text = content[0].get("text", "") if content else ""
            # Parse lines like "- ToolsetRegistry.Name: Description"
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    line = line[2:]
                    if ": " in line:
                        name, desc = line.split(": ", 1)
                        toolsets.append(ToolsetInfo(name=name.strip(), description=desc.strip()))

        self._available_toolsets = toolsets
        return toolsets

    async def describe_toolset(self, toolset_name: str, use_cache: bool = True) -> list[ToolInfo]:
        """
        Get tool schemas for a specific toolset.

        Args:
            toolset_name: Full toolset name (e.g., "editor_toolset.toolsets.actor.ActorTools")
            use_cache: Use cached toolset info if available

        Returns:
            List of tools with names, descriptions, and parameter schemas
        """
        if use_cache and toolset_name in self._toolset_cache:
            return self._toolset_cache[toolset_name]

        result = await self._send_request(
            "tools/call",
            params={
                "name": "describe_toolset",
                "arguments": {"toolset_name": toolset_name},
            },
        )

        tools = []
        content = result.get("content", [])
        if content and isinstance(content, list):
            text = content[0].get("text", "") if content else ""
            try:
                # Parse as JSON
                toolset_data = json.loads(text)
                for tool in toolset_data.get("tools", []):
                    tools.append(ToolInfo(
                        name=tool.get("name", ""),
                        description=tool.get("description", ""),
                        parameters=tool.get("inputSchema", {}),
                    ))
            except json.JSONDecodeError:
                pass  # Not JSON format

        self._toolset_cache[toolset_name] = tools
        return tools

    # Response markers that indicate UE5 rejected the call even though the
    # outer JSON-RPC request itself succeeded. Found live on 2026-07-02: a
    # UE5 8.0 build silently returned "Unknown tool" text for every call
    # because tool_name was passed fully-qualified (see note below), and the
    # old code treated that as success=True — a "false positive" that
    # reported actors as spawned when nothing had actually happened. Detect
    # these markers so a soft failure is never mistaken for success again.
    _SOFT_FAILURE_MARKERS = ("unknown tool", "unknown toolset", "tool not found")

    async def call_tool(
        self,
        toolset_name: str,
        tool_name: str,
        arguments: Optional[dict] = None,
    ) -> ToolResult:
        """
        Execute a tool within a toolset.

        Args:
            toolset_name: Full toolset name (e.g., "editor_toolset.toolsets.actor.ActorTools")
            tool_name: Tool name — either the short method name (e.g.
                "get_all_actors") or the fully-qualified
                "<toolset_name>.method" form used elsewhere in this codebase
                for readability. The fully-qualified prefix is stripped
                before sending, since some UE5 MCP builds (confirmed live
                2026-07-02 against a UE5 8.0 build) expect ONLY the short
                method name here and silently return "Unknown tool" for the
                fully-qualified form even though toolset_name is passed
                separately.
            arguments: Tool arguments

        Returns:
            ToolResult with success status and data
        """
        short_tool_name = tool_name
        if toolset_name and tool_name.startswith(f"{toolset_name}."):
            short_tool_name = tool_name[len(toolset_name) + 1:]

        try:
            result = await self._send_request(
                "tools/call",
                params={
                    "name": "call_tool",
                    "arguments": {
                        "toolset_name": toolset_name,
                        "tool_name": short_tool_name,
                        "arguments": arguments or {},
                    },
                },
            )

            # Parse result content
            content = result.get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text", "") if content else ""
                if any(marker in text.lower() for marker in self._SOFT_FAILURE_MARKERS):
                    return ToolResult(success=False, error=text, data=None)
                try:
                    data = json.loads(text)
                    return ToolResult(success=True, data=data)
                except json.JSONDecodeError:
                    return ToolResult(success=True, data=text)

            return ToolResult(success=True, data=result)

        except UE5MCPError as e:
            return ToolResult(
                success=False,
                error=str(e),
            )

    def clear_cache(self) -> None:
        """Clear the toolset schema cache."""
        self._toolset_cache.clear()
        self._available_toolsets = None

    @property
    def session_id(self) -> Optional[str]:
        """Get current session ID."""
        return self._session_id

    @property
    def is_connected(self) -> bool:
        """Check if client has an active session."""
        return self._is_initialized and self._session_id is not None


# Convenience functions for common operations

async def check_connectivity(url: Optional[str] = None) -> tuple[bool, str]:
    """
    Check if UE5 MCP server is reachable and can establish session.

    Args:
        url: Optional UE5 MCP URL override

    Returns:
        Tuple of (is_connected, status_message)
    """
    try:
        async with UE5MCPClient(url=url) as client:
            if client.is_connected:
                return True, f"Connected to UE5 MCP at {client.url} (session: {client.session_id[:8]}...)"
            else:
                return False, f"Failed to establish session with UE5 MCP at {client.url}"
    except UE5MCPError as e:
        return False, str(e)


async def discover_toolsets(url: Optional[str] = None) -> list[ToolsetInfo]:
    """
    Discover all available toolsets.

    Args:
        url: Optional UE5 MCP URL override

    Returns:
        List of available toolsets
    """
    async with UE5MCPClient(url=url) as client:
        return await client.list_toolsets()


async def discover_tools(url: Optional[str] = None) -> dict[str, list[ToolInfo]]:
    """
    Discover all available toolsets and their tools.

    Args:
        url: Optional UE5 MCP URL override

    Returns:
        Dictionary mapping toolset names to their tools
    """
    async with UE5MCPClient(url=url) as client:
        toolsets = await client.list_toolsets()

        all_tools = {}
        for ts in toolsets:
            try:
                tools = await client.describe_toolset(ts.name)
                all_tools[ts.name] = tools
            except UE5MCPError:
                all_tools[ts.name] = []

        return all_tools


# Key toolset names for network visualization
TOOLSETS = {
    "actor": "editor_toolset.toolsets.actor.ActorTools",
    "scene": "editor_toolset.toolsets.scene.SceneTools",
    "material": "editor_toolset.toolsets.material_instance.MaterialInstanceTools",
    "primitive": "editor_toolset.toolsets.primitive.PrimitiveTools",
    "object": "editor_toolset.toolsets.object.ObjectTools",
    "static_mesh": "editor_toolset.toolsets.static_mesh.StaticMeshTools",
    "blueprint": "editor_toolset.toolsets.blueprint.BlueprintTools",
    "editor_app": "EditorToolset.EditorAppToolset",
}
