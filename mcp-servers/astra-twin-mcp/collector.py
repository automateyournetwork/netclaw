#!/usr/bin/env python3
"""
Collector — spec 122-astra-live-digital-twin, mcp-servers/astra-twin-mcp/.

Frozen (see specs/122-astra-live-digital-twin/plan.md, research.md R4, loop.md).

Never talks to a lab device directly. Every read goes through the *existing* pyATS MCP server
(mcp-servers/pyATS_MCP/pyats_mcp_server.py), reached here purely as an MCP client over stdio —
this file holds no device credential, session, or write-capable tool call anywhere, so the
read-only guarantee (FR-003/FR-005) is structural, not merely a promise never to call a write
tool that happens to be reachable.

Only two of that server's tools are ever called:
  pyats_list_devices()                      -> device inventory
  pyats_run_show_command(device_name, cmd)  -> read-only 'show' output

pyats_configure_device / pyats_run_linux_command / pyats_run_dynamic_test are never referenced.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
from collections import deque
from typing import Optional

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from models.twin_schema import (  # noqa: E402
    DeltaKind,
    LinkState,
    NodeStatus,
    TwinDelta,
    TwinLink,
    TwinNode,
    TwinSnapshot,
    next_link_state,
    next_node_status,
)

logger = logging.getLogger("astra-twin-collector")

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PYATS_MCP_SERVER = os.path.join(HERE, "..", "pyATS_MCP", "pyats_mcp_server.py")
DEFAULT_PYATS_VENV_PYTHON = os.path.expanduser("~/.openclaw/pyats-venv/bin/python3")

DELTA_BUFFER_SIZE = 500
DEFAULT_POLL_INTERVAL_SECONDS = 10

# Read-only observation commands used to build the topology. Multivendor neutrality
# (Constitution VI) is respected: this file has no vendor branching — it always sends the
# same show commands, and it is the underlying pyATS/Genie parser (owned by pyATS_MCP, not by
# this file) that already normalizes vendor differences into structured output.
CDP_NEIGHBOR_COMMAND = "show cdp neighbors detail"
INTERFACE_STATUS_COMMAND = "show interfaces description"


def _pyats_python() -> str:
    override = os.environ.get("PYATS_MCP_PYTHON")
    if override:
        return override
    if os.path.isfile(DEFAULT_PYATS_VENV_PYTHON):
        return DEFAULT_PYATS_VENV_PYTHON
    return sys.executable


def _pyats_server_path() -> str:
    return os.environ.get("PYATS_MCP_SERVER_PATH", DEFAULT_PYATS_MCP_SERVER)


def _pyats_subprocess_env(pyats_testbed: str) -> dict[str, str]:
    """Translate the loop-level PYATS_TESTBED into the variable name the existing pyATS_MCP
    server actually reads (PYATS_TESTBED_PATH) — see contracts/astra-twin-mcp.md's note. This
    translation happens only in the environment handed to the subprocess; nothing else changes.
    """
    env = dict(os.environ)
    env["PYATS_TESTBED_PATH"] = pyats_testbed
    return env


class Collector:
    """Polls the existing pyATS MCP server on a fixed interval and maintains the twin's
    current-state snapshot plus a bounded ring buffer of deltas since startup."""

    def __init__(self, pyats_testbed: str, poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS):
        self.pyats_testbed = pyats_testbed
        self.poll_interval_seconds = poll_interval_seconds
        self._nodes: dict[str, TwinNode] = {}
        self._links: dict[str, TwinLink] = {}
        self._deltas: deque[TwinDelta] = deque(maxlen=DELTA_BUFFER_SIZE)
        self._seq = 0
        self._testbed_identity = os.path.basename(pyats_testbed)
        self.last_successful_poll: Optional[str] = None
        self.consecutive_failures = 0
        self._lock = asyncio.Lock()

    # -- public read surface, called by server.py's MCP tools -----------------------------

    async def snapshot(self) -> TwinSnapshot:
        async with self._lock:
            return TwinSnapshot(
                nodes=list(self._nodes.values()),
                links=list(self._links.values()),
                seq=self._seq,
                testbed_identity=self._testbed_identity,
            )

    async def deltas_since(self, since_seq: int) -> Optional[list[TwinDelta]]:
        """Returns None if since_seq is older than the oldest buffered delta (caller must
        fall back to snapshot()) per contracts/astra-twin-mcp.md's documented failure mode."""
        async with self._lock:
            if self._deltas and since_seq < self._deltas[0].seq - 1:
                return None
            return [d for d in self._deltas if d.seq > since_seq]

    async def all_buffered_deltas(self) -> list[TwinDelta]:
        """Everything currently in the ring buffer, regardless of how far it's rolled over —
        for internal use (e.g. the cache writer) that wants the buffer's actual contents, not
        deltas_since()'s "since a client-tracked sequence number" semantics."""
        async with self._lock:
            return list(self._deltas)

    def status(self) -> dict:
        return {
            "last_successful_poll": self.last_successful_poll,
            "testbed_identity": self._testbed_identity,
            "poll_interval_seconds": self.poll_interval_seconds,
            "consecutive_failures": self.consecutive_failures,
        }

    # -- polling loop -----------------------------------------------------------------------

    async def run_forever(self) -> None:
        while True:
            try:
                await self._poll_once()
                self.consecutive_failures = 0
            except Exception:
                self.consecutive_failures += 1
                logger.exception("poll cycle failed (consecutive_failures=%d)", self.consecutive_failures)
            await asyncio.sleep(self.poll_interval_seconds)

    async def _poll_once(self) -> None:
        params = StdioServerParameters(
            command=_pyats_python(),
            args=[_pyats_server_path()],
            env=_pyats_subprocess_env(self.pyats_testbed),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                device_names = await self._list_devices(session)
                observed_nodes: dict[str, TwinNode] = {}
                observed_links: dict[str, TwinLink] = {}
                for name in device_names:
                    reachable, admin_down_ifaces = await self._probe_device(session, name)
                    observed_nodes[name] = TwinNode(
                        id=name,
                        label=name,
                        vendor_platform="unknown",
                        status=next_node_status(poll_succeeded=reachable, reported_admin_down=False),
                    )
                    if reachable:
                        neighbors = await self._probe_neighbors(session, name)
                        for local_iface, (peer_name, peer_iface) in neighbors.items():
                            state = LinkState.DOWN if local_iface in admin_down_ifaces else LinkState.UP
                            link_id = TwinLink.make_id(name, local_iface, peer_name, peer_iface)
                            observed_links[link_id] = TwinLink(
                                id=link_id,
                                source_node_id=name,
                                target_node_id=peer_name,
                                source_interface=local_iface,
                                target_interface=peer_iface,
                                state=state,
                            )

        self._reconcile(observed_nodes, observed_links)
        self.last_successful_poll = observed_nodes and next(iter(observed_nodes.values())).last_seen or self.last_successful_poll

    async def _list_devices(self, session: ClientSession) -> list[str]:
        result = await session.call_tool("pyats_list_devices", {})
        text = _first_text(result)
        data = json.loads(text)
        devices = data.get("devices", data) if isinstance(data, dict) else data
        return list(devices.keys()) if isinstance(devices, dict) else []

    async def _probe_device(self, session: ClientSession, device_name: str) -> tuple[bool, set[str]]:
        try:
            result = await session.call_tool(
                "pyats_run_show_command",
                {"device_name": device_name, "command": INTERFACE_STATUS_COMMAND},
            )
            text = _first_text(result)
            admin_down = set(re.findall(r"^(\S+)\s+.*admin\s*down", text, re.IGNORECASE | re.MULTILINE))
            return True, admin_down
        except Exception:
            logger.warning("device %s unreachable this poll", device_name)
            return False, set()

    async def _probe_neighbors(self, session: ClientSession, device_name: str) -> dict[str, tuple[str, str]]:
        """Returns {local_interface: (peer_device_name, peer_interface)} parsed from CDP
        neighbor detail output. Best-effort text parsing — pyATS_MCP's underlying Genie parser
        is the source of structured truth when a parsed table is available; this regex path is
        the fallback so the collector still functions against raw CLI text."""
        try:
            result = await session.call_tool(
                "pyats_run_show_command",
                {"device_name": device_name, "command": CDP_NEIGHBOR_COMMAND},
            )
            text = _first_text(result)
        except Exception:
            return {}

        neighbors: dict[str, tuple[str, str]] = {}
        device_id = None
        local_iface = None
        peer_iface = None
        for line in text.splitlines():
            m_dev = re.match(r"Device ID:\s*(\S+)", line)
            if m_dev:
                device_id = m_dev.group(1).split(".")[0]
                continue
            m_iface = re.search(r"Interface:\s*(\S+),\s*Port ID \(outgoing port\):\s*(\S+)", line)
            if m_iface:
                local_iface, peer_iface = m_iface.group(1), m_iface.group(2)
                if device_id and local_iface and peer_iface:
                    neighbors[local_iface] = (device_id, peer_iface)
                device_id = local_iface = peer_iface = None
        return neighbors

    def _reconcile(self, observed_nodes: dict[str, TwinNode], observed_links: dict[str, TwinLink]) -> None:
        for name, node in observed_nodes.items():
            existing = self._nodes.get(name)
            if existing is None:
                self._emit(DeltaKind.NODE_ADDED, node=node)
            elif existing.status != node.status:
                self._emit(DeltaKind.NODE_STATUS_CHANGED, node=node)
            self._nodes[name] = node
        for removed_name in set(self._nodes) - set(observed_nodes):
            self._emit(DeltaKind.NODE_REMOVED, node=self._nodes.pop(removed_name))

        for link_id, link in observed_links.items():
            existing = self._links.get(link_id)
            if existing is None:
                self._emit(DeltaKind.LINK_ADDED, link=link)
            else:
                resolved = next_link_state(
                    current=existing.state,
                    endpoint_a_reachable=observed_nodes.get(link.source_node_id, TwinNode(
                        id="", label="", vendor_platform="", status=NodeStatus.UNREACHABLE
                    )).status != NodeStatus.UNREACHABLE,
                    endpoint_b_reachable=observed_nodes.get(link.target_node_id, TwinNode(
                        id="", label="", vendor_platform="", status=NodeStatus.UNREACHABLE
                    )).status != NodeStatus.UNREACHABLE,
                    observed_state=link.state,
                )
                if resolved is not None and resolved != existing.state:
                    link.state = resolved
                    self._emit(DeltaKind.LINK_STATE_CHANGED, link=link)
            self._links[link_id] = link
        for removed_id in set(self._links) - set(observed_links):
            stale_link = self._links[removed_id]
            both_endpoints_reachable = (
                observed_nodes.get(stale_link.source_node_id, TwinNode(
                    id="", label="", vendor_platform="", status=NodeStatus.UNREACHABLE
                )).status != NodeStatus.UNREACHABLE
                and observed_nodes.get(stale_link.target_node_id, TwinNode(
                    id="", label="", vendor_platform="", status=NodeStatus.UNREACHABLE
                )).status != NodeStatus.UNREACHABLE
            )
            if both_endpoints_reachable:
                # Both ends were reachable this poll and neither reported the link — a
                # genuine removal, not a gap in observation.
                self._emit(DeltaKind.LINK_REMOVED, link=self._links.pop(removed_id))
            # else: at least one endpoint was unreachable this poll, so absence from
            # observed_links is inconclusive — leave the link at its last-known state
            # rather than guess (Constitution I; data-model.md's transition rules).

    def _emit(self, kind: DeltaKind, node: Optional[TwinNode] = None, link: Optional[TwinLink] = None) -> None:
        self._seq += 1
        self._deltas.append(TwinDelta(seq=self._seq, kind=kind, node=node, link=link))


def _first_text(call_tool_result) -> str:
    for item in call_tool_result.content:
        if getattr(item, "type", None) == "text":
            return item.text
    return "{}"
