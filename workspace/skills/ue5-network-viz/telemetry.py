"""
Telemetry Integration for UE5 Network Visualization.

This module handles real-time updates to the visualization based on
network telemetry data. Supports both event-driven updates (alerts)
and polling-based updates (metrics).

Integration points:
- Telemetry Receivers MCP (Feature 010) for syslog/SNMP/NetFlow
- Direct polling of device status via pyATS/SNMP
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional, Any
from enum import Enum

try:
    from .ue5_mcp_client import UE5MCPClient
    from .materials import (
        create_device_material_config,
        create_link_material_config,
        DeviceStatus,
        LinkStatus,
    )
    from .actors import apply_device_material, apply_link_material
    from .scene import get_scene_state, get_device_position
except ImportError:  # pragma: no cover - fallback for sys.path-style loading
    from ue5_mcp_client import UE5MCPClient
    from materials import (
        create_device_material_config,
        create_link_material_config,
        DeviceStatus,
        LinkStatus,
    )
    from actors import apply_device_material, apply_link_material
    from scene import get_scene_state, get_device_position


# =============================================================================
# Telemetry Events
# =============================================================================

class TelemetryEventType(Enum):
    """Types of telemetry events."""
    DEVICE_STATUS_CHANGE = "device_status_change"
    LINK_STATUS_CHANGE = "link_status_change"
    UTILIZATION_UPDATE = "utilization_update"
    ALERT = "alert"


@dataclass
class TelemetryEvent:
    """A telemetry event that triggers visualization update."""
    event_type: TelemetryEventType
    hostname: Optional[str] = None
    link_id: Optional[str] = None
    new_status: Optional[str] = None
    utilization: Optional[float] = None
    severity: str = "info"
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: dict = field(default_factory=dict)


# =============================================================================
# Event Handlers
# =============================================================================

async def handle_device_status_change(
    client: UE5MCPClient,
    hostname: str,
    new_status: str,
    device_type: str = "unknown",
) -> bool:
    """
    Handle a device status change event.

    Updates the device actor's material to reflect the new status.

    Args:
        client: UE5 MCP client
        hostname: Device hostname
        new_status: New status (healthy, warning, critical, unreachable)
        device_type: Device type for base color

    Returns:
        True if update successful
    """
    state = get_scene_state()

    if hostname not in state.device_actors:
        # Device not rendered - ignore
        return False

    return await apply_device_material(
        client,
        hostname=hostname,
        device_type=device_type,
        status=new_status,
    )


async def handle_link_status_change(
    client: UE5MCPClient,
    source_hostname: str,
    target_hostname: str,
    new_status: str,
) -> bool:
    """
    Handle a link status change event.

    Updates the link actor's material to reflect the new status.

    Args:
        client: UE5 MCP client
        source_hostname: Source device hostname
        target_hostname: Target device hostname
        new_status: New status (healthy, degraded, down)

    Returns:
        True if update successful
    """
    link_id = f"{source_hostname}_{target_hostname}"
    state = get_scene_state()

    if link_id not in state.link_actors:
        # Link not rendered - ignore
        return False

    return await apply_link_material(
        client,
        source_hostname=source_hostname,
        target_hostname=target_hostname,
        status=new_status,
    )


async def handle_telemetry_event(
    client: UE5MCPClient,
    event: TelemetryEvent,
) -> bool:
    """
    Handle any telemetry event and update visualization.

    Args:
        client: UE5 MCP client
        event: Telemetry event to process

    Returns:
        True if update successful
    """
    if event.event_type == TelemetryEventType.DEVICE_STATUS_CHANGE:
        if event.hostname and event.new_status:
            return await handle_device_status_change(
                client,
                event.hostname,
                event.new_status,
            )

    elif event.event_type == TelemetryEventType.LINK_STATUS_CHANGE:
        if event.link_id and event.new_status:
            parts = event.link_id.split("_")
            if len(parts) >= 2:
                return await handle_link_status_change(
                    client,
                    parts[0],
                    parts[1],
                    event.new_status,
                )

    elif event.event_type == TelemetryEventType.ALERT:
        # Map alert severity to device status
        if event.hostname:
            status_map = {
                "critical": "critical",
                "error": "critical",
                "warning": "warning",
                "info": "healthy",
            }
            new_status = status_map.get(event.severity.lower(), "unknown")
            return await handle_device_status_change(
                client,
                event.hostname,
                new_status,
            )

    return False


# =============================================================================
# Polling Loop
# =============================================================================

@dataclass
class PollingConfig:
    """Configuration for telemetry polling."""
    interval_seconds: float = 30.0  # Poll every 30 seconds
    enabled: bool = True
    device_status_callback: Optional[Callable] = None
    link_status_callback: Optional[Callable] = None


class TelemetryPoller:
    """
    Polling loop for telemetry-based visualization updates.

    Periodically queries device/link status and updates visualization.
    """

    def __init__(
        self,
        client: UE5MCPClient,
        config: Optional[PollingConfig] = None,
    ):
        """
        Initialize telemetry poller.

        Args:
            client: UE5 MCP client
            config: Polling configuration
        """
        self.client = client
        self.config = config or PollingConfig()
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Device status cache (hostname -> last_status)
        self._device_status_cache: dict[str, str] = {}
        self._link_status_cache: dict[str, str] = {}

    async def start(self) -> None:
        """Start the polling loop."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await self._poll_once()
            except Exception as e:
                # Log error but continue polling
                print(f"Telemetry poll error: {e}")

            await asyncio.sleep(self.config.interval_seconds)

    async def _poll_once(self) -> None:
        """Perform a single poll iteration."""
        state = get_scene_state()

        # Poll device status
        if self.config.device_status_callback:
            for hostname in state.device_actors.keys():
                try:
                    new_status = await self.config.device_status_callback(hostname)

                    if new_status and new_status != self._device_status_cache.get(hostname):
                        await handle_device_status_change(
                            self.client,
                            hostname,
                            new_status,
                        )
                        self._device_status_cache[hostname] = new_status

                except Exception as e:
                    print(f"Error polling device {hostname}: {e}")

        # Poll link status
        if self.config.link_status_callback:
            for link_id in state.link_actors.keys():
                try:
                    new_status = await self.config.link_status_callback(link_id)

                    if new_status and new_status != self._link_status_cache.get(link_id):
                        parts = link_id.split("_")
                        if len(parts) >= 2:
                            await handle_link_status_change(
                                self.client,
                                parts[0],
                                parts[1],
                                new_status,
                            )
                            self._link_status_cache[link_id] = new_status

                except Exception as e:
                    print(f"Error polling link {link_id}: {e}")


# =============================================================================
# Event-Driven Updates (Telemetry Receivers Integration)
# =============================================================================

class TelemetryReceiver:
    """
    Event-driven telemetry receiver for real-time updates.

    Integrates with Telemetry Receivers MCP (Feature 010) for
    syslog, SNMP traps, and NetFlow events.
    """

    def __init__(self, client: UE5MCPClient):
        """
        Initialize telemetry receiver.

        Args:
            client: UE5 MCP client for visualization updates
        """
        self.client = client
        self._handlers: dict[str, list[Callable]] = {}

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[TelemetryEvent], None],
    ) -> None:
        """
        Register an event handler.

        Args:
            event_type: Type of event to handle
            handler: Callback function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def process_syslog_event(self, event_data: dict) -> None:
        """
        Process a syslog event from Telemetry Receivers MCP.

        Args:
            event_data: Raw syslog event data
        """
        # Parse syslog severity
        severity = event_data.get("severity", 6)  # Default: INFO
        severity_map = {
            0: "critical",   # Emergency
            1: "critical",   # Alert
            2: "critical",   # Critical
            3: "critical",   # Error
            4: "warning",    # Warning
            5: "info",       # Notice
            6: "info",       # Informational
            7: "info",       # Debug
        }

        hostname = event_data.get("hostname")
        if not hostname:
            return

        event = TelemetryEvent(
            event_type=TelemetryEventType.ALERT,
            hostname=hostname,
            severity=severity_map.get(severity, "info"),
            message=event_data.get("message", ""),
            raw_data=event_data,
        )

        await handle_telemetry_event(self.client, event)

    async def process_snmp_trap(self, trap_data: dict) -> None:
        """
        Process an SNMP trap from Telemetry Receivers MCP.

        Args:
            trap_data: Raw SNMP trap data
        """
        # Common trap types that affect link status
        hostname = trap_data.get("source_ip")
        oid = trap_data.get("trap_oid", "")

        # Link down trap: 1.3.6.1.6.3.1.1.5.3
        if "1.3.6.1.6.3.1.1.5.3" in oid:
            interface = trap_data.get("interface", "")
            event = TelemetryEvent(
                event_type=TelemetryEventType.LINK_STATUS_CHANGE,
                hostname=hostname,
                new_status="down",
                message=f"Link down: {interface}",
                raw_data=trap_data,
            )
            await handle_telemetry_event(self.client, event)

        # Link up trap: 1.3.6.1.6.3.1.1.5.4
        elif "1.3.6.1.6.3.1.1.5.4" in oid:
            interface = trap_data.get("interface", "")
            event = TelemetryEvent(
                event_type=TelemetryEventType.LINK_STATUS_CHANGE,
                hostname=hostname,
                new_status="healthy",
                message=f"Link up: {interface}",
                raw_data=trap_data,
            )
            await handle_telemetry_event(self.client, event)


# =============================================================================
# Convenience Functions
# =============================================================================

async def update_device_status(
    client: UE5MCPClient,
    hostname: str,
    status: str,
    device_type: str = "unknown",
) -> bool:
    """
    Update a device's visual status.

    Args:
        client: UE5 MCP client
        hostname: Device hostname
        status: New status
        device_type: Device type

    Returns:
        True if successful
    """
    return await handle_device_status_change(client, hostname, status, device_type)


async def update_link_status(
    client: UE5MCPClient,
    source: str,
    target: str,
    status: str,
) -> bool:
    """
    Update a link's visual status.

    Args:
        client: UE5 MCP client
        source: Source device hostname
        target: Target device hostname
        status: New status

    Returns:
        True if successful
    """
    return await handle_link_status_change(client, source, target, status)


async def set_device_critical(
    client: UE5MCPClient,
    hostname: str,
) -> bool:
    """Mark a device as critical (red glow)."""
    return await update_device_status(client, hostname, "critical")


async def set_device_warning(
    client: UE5MCPClient,
    hostname: str,
) -> bool:
    """Mark a device as warning (orange glow)."""
    return await update_device_status(client, hostname, "warning")


async def set_device_healthy(
    client: UE5MCPClient,
    hostname: str,
) -> bool:
    """Mark a device as healthy (normal color)."""
    return await update_device_status(client, hostname, "healthy")


async def set_link_down(
    client: UE5MCPClient,
    source: str,
    target: str,
) -> bool:
    """Mark a link as down (red)."""
    return await update_link_status(client, source, target, "down")


async def set_link_degraded(
    client: UE5MCPClient,
    source: str,
    target: str,
) -> bool:
    """Mark a link as degraded (yellow)."""
    return await update_link_status(client, source, target, "degraded")


async def set_link_healthy(
    client: UE5MCPClient,
    source: str,
    target: str,
) -> bool:
    """Mark a link as healthy (green)."""
    return await update_link_status(client, source, target, "healthy")
