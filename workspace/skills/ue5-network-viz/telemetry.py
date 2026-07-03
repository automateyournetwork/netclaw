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
        get_traffic_color,
        get_alarm_color,
        get_link_status_color,
        DeviceStatus,
        LinkStatus,
    )
    from .actors import (
        apply_device_material,
        apply_link_material,
        apply_interface_material,
        is_device_in_topology,
        is_interface_in_topology,
        is_link_in_topology,
    )
    from .scene import get_scene_state, get_device_position
except ImportError:  # pragma: no cover - fallback for sys.path-style loading
    from ue5_mcp_client import UE5MCPClient
    from materials import (
        create_device_material_config,
        create_link_material_config,
        get_traffic_color,
        get_alarm_color,
        get_link_status_color,
        DeviceStatus,
        LinkStatus,
    )
    from actors import (
        apply_device_material,
        apply_link_material,
        apply_interface_material,
        is_device_in_topology,
        is_interface_in_topology,
        is_link_in_topology,
    )
    from scene import get_scene_state, get_device_position


# =============================================================================
# History Buffer (Foundational, 045-ue5-digital-twin)
# =============================================================================
#
# Session-scoped, in-memory record of every health/traffic/trap-driven state
# change, per data-model.md's HistoryRecord entity. Populated by US4
# (traffic), US5 (health polling), and US6 (trap alerts); consumed by US10's
# playback.py. Bounded ring buffer — never persisted, never survives a
# NetClaw restart (spec Assumptions).

_HISTORY_MAX_LEN = 5000


@dataclass
class HistoryRecord:
    """One recorded state change, for historical playback (US10)."""
    subject_key: str  # hostname, "hostname:interface", or link id
    change_type: str  # "health" | "traffic" | "trap"
    previous_state: Any
    new_state: Any
    timestamp: datetime = field(default_factory=datetime.now)


_history_buffer: list[HistoryRecord] = []


def record_history(subject_key: str, change_type: str, previous_state: Any, new_state: Any) -> None:
    """Append a state change to the session history buffer, trimming to _HISTORY_MAX_LEN."""
    _history_buffer.append(HistoryRecord(
        subject_key=subject_key,
        change_type=change_type,
        previous_state=previous_state,
        new_state=new_state,
    ))
    if len(_history_buffer) > _HISTORY_MAX_LEN:
        del _history_buffer[: len(_history_buffer) - _HISTORY_MAX_LEN]


def get_history_window(start: datetime, end: datetime) -> list[HistoryRecord]:
    """Return recorded changes with start <= timestamp <= end, in original order."""
    return [r for r in _history_buffer if start <= r.timestamp <= end]


def clear_history() -> None:
    """Clear the session history buffer (used by tests and by a fresh topology build)."""
    _history_buffer.clear()


# =============================================================================
# Traffic Visualization (US4, 045-ue5-digital-twin)
# =============================================================================
#
# FR-010: traffic utilization is a *supplied* value — this module never
# queries gnmi-mcp/pyATS itself. The calling agent retrieves utilization via
# those MCP tools in conversation, then hands the results here as a plain
# {"hostname:interface" or link_id -> utilization 0.0-1.0} mapping. Keys not
# present in the mapping keep their current (non-traffic) appearance rather
# than being reset or errored (FR-012).

_traffic_state_cache: dict[str, float] = {}


async def refresh_traffic_visualization(
    client: UE5MCPClient,
    utilization_by_key: dict[str, float],
) -> dict:
    """
    Apply traffic-utilization color to every interface/link actor named in
    `utilization_by_key` (FR-010/FR-011). Unknown keys (not currently
    tracked in the scene) are skipped rather than erroring (FR-019/FR-040).
    Repeated calls simply replace prior traffic state (FR-011: reflects the
    most recently retrieved data).
    """
    state = get_scene_state()
    applied: list[str] = []
    skipped: list[str] = []

    for key, utilization in utilization_by_key.items():
        color = get_traffic_color(utilization).to_list()

        if ":" in key and key in state.interface_actors:
            hostname, interface_name = key.split(":", 1)
            ok = await apply_interface_material(client, hostname, interface_name, color)
        elif key in state.link_actors:
            source, target = key.split("_", 1) if "_" in key else (key, key)
            ok = await _apply_link_traffic_color(client, source, target, color)
        else:
            skipped.append(key)
            continue

        if ok:
            previous = _traffic_state_cache.get(key)
            if previous != utilization:
                record_history(key, "traffic", previous, utilization)
                _traffic_state_cache[key] = utilization
            applied.append(key)
        else:
            skipped.append(key)

    return {"applied": applied, "skipped": skipped}


async def _apply_link_traffic_color(client: UE5MCPClient, source: str, target: str, rgb: list[float]) -> bool:
    """Recolor a link actor directly with a traffic-gradient color (bypasses the health-status color lookup apply_link_material uses)."""
    try:
        from .actors import apply_actor_color, generate_link_actor_name
    except ImportError:  # pragma: no cover - fallback for sys.path-style loading
        from actors import apply_actor_color, generate_link_actor_name
    return await apply_actor_color(client, generate_link_actor_name(source, target), rgb)


# =============================================================================
# Live Mode Control (US5, 045-ue5-digital-twin)
# =============================================================================

@dataclass
class LiveModeState:
    """Session-scoped live-mode status (FR-014/FR-015). Never persisted."""
    active: bool
    started_at: Optional[datetime]
    poll_interval_seconds: float


async def start_live_mode(client: UE5MCPClient, poller: "TelemetryPoller") -> None:
    """Start continuous background polling (FR-014)."""
    await poller.start()
    poller.live_started_at = datetime.now()


async def stop_live_mode(poller: "TelemetryPoller") -> None:
    """Stop continuous background polling (FR-014)."""
    await poller.stop()
    poller.live_started_at = None


def get_live_mode_status(poller: "TelemetryPoller") -> LiveModeState:
    """Report whether live mode is currently active (FR-015)."""
    return LiveModeState(
        active=poller._running,
        started_at=getattr(poller, "live_started_at", None),
        poll_interval_seconds=poller.config.interval_seconds,
    )


async def refresh_health_visualization(
    client: UE5MCPClient,
    device_status_by_hostname: Optional[dict[str, str]] = None,
    link_status_by_id: Optional[dict[str, str]] = None,
) -> dict:
    """
    On-demand health refresh (FR-013), distinct from continuous live mode:
    apply externally-retrieved health status (already queried from
    gnmi-mcp/pyATS by the calling agent) to device/link actors in one shot.
    Unknown hostnames/link ids are skipped without error (FR-019/FR-040). A
    link status of "healthy" also clears any sticky trap alert latched on
    that link, since a confirmed health-poll recovery is a valid clear
    condition alongside a matching linkUp trap (FR-018).
    """
    state = get_scene_state()
    applied: list[str] = []
    skipped: list[str] = []

    for hostname, status in (device_status_by_hostname or {}).items():
        if not is_device_in_topology(hostname):
            skipped.append(hostname)
            continue
        previous = _device_status_history_cache.get(hostname)
        ok = await apply_device_material(client, hostname, "unknown", status)
        if ok:
            if previous != status:
                record_history(hostname, "health", previous, status)
                _device_status_history_cache[hostname] = status
            applied.append(hostname)
        else:
            skipped.append(hostname)

    for link_id, status in (link_status_by_id or {}).items():
        if not is_link_in_topology(link_id):
            skipped.append(link_id)
            continue
        source, target = link_id.split("_", 1) if "_" in link_id else (link_id, link_id)
        previous = _link_status_history_cache.get(link_id)
        ok = await apply_link_material(client, source, target, status)
        if ok:
            if previous != status:
                record_history(link_id, "health", previous, status)
                _link_status_history_cache[link_id] = status
            if status == "healthy" and is_sticky_alert_active(link_id):
                clear_sticky_alert(link_id, "health_poll_recovery")
                await apply_link_material(client, source, target, "healthy")
            applied.append(link_id)
        else:
            skipped.append(link_id)

    return {"applied": applied, "skipped": skipped}


_device_status_history_cache: dict[str, str] = {}
_link_status_history_cache: dict[str, str] = {}


# =============================================================================
# Sticky Trap Alerts (US6, 045-ue5-digital-twin)
# =============================================================================
#
# Per data-model.md's StickyAlertState: a down-type trap latches a visible
# alert on the affected interface/link that survives unrelated refreshes —
# it is cleared ONLY by a matching up-type trap or a health-poll-confirmed
# recovery (FR-018), never by the mere passage of time.

@dataclass
class StickyAlertState:
    """One latched trap-driven alert (data-model.md)."""
    key: str  # "hostname:interface" or a link id
    latched_since: datetime
    trap_type: str
    cleared_by: Optional[str] = None  # "linkUp_trap" | "health_poll_recovery" | None


_sticky_alerts: dict[str, StickyAlertState] = {}


def latch_sticky_alert(subject_key: str, trap_type: str) -> None:
    """Latch a sticky alert on `subject_key` (FR-018). Re-latching an already-active alert refreshes trap_type but keeps the original latched_since untouched only if still active; a fresh latch after a clear starts a new window."""
    existing = _sticky_alerts.get(subject_key)
    if existing and existing.cleared_by is None:
        existing.trap_type = trap_type
        return
    _sticky_alerts[subject_key] = StickyAlertState(
        key=subject_key, latched_since=datetime.now(), trap_type=trap_type
    )


def clear_sticky_alert(subject_key: str, cleared_by: str) -> None:
    """Clear a latched alert (FR-018) — called on a matching linkUp trap or a confirmed health-poll recovery."""
    existing = _sticky_alerts.get(subject_key)
    if existing:
        existing.cleared_by = cleared_by


def is_sticky_alert_active(subject_key: str) -> bool:
    """True if `subject_key` currently has an un-cleared latched alert."""
    existing = _sticky_alerts.get(subject_key)
    return existing is not None and existing.cleared_by is None


def get_active_sticky_alerts() -> list[StickyAlertState]:
    """All currently-active (uncleared) sticky alerts, for HUD/status reporting."""
    return [a for a in _sticky_alerts.values() if a.cleared_by is None]


def clear_all_sticky_alerts() -> None:
    """Reset the registry (used by tests and by a fresh topology build)."""
    _sticky_alerts.clear()


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
                        previous = self._device_status_cache.get(hostname)
                        await handle_device_status_change(
                            self.client,
                            hostname,
                            new_status,
                        )
                        self._device_status_cache[hostname] = new_status
                        record_history(hostname, "health", previous, new_status)  # T027

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
                            previous = self._link_status_cache.get(link_id)
                            await handle_link_status_change(
                                self.client,
                                parts[0],
                                parts[1],
                                new_status,
                            )
                            self._link_status_cache[link_id] = new_status
                            record_history(link_id, "health", previous, new_status)  # T027

                            # T032: a confirmed-healthy poll result is a valid
                            # sticky-alert clear condition, same as a matching
                            # linkUp trap (FR-018) — continuous polling must
                            # clear stale alerts too, not just the on-demand
                            # refresh_health_visualization path.
                            if new_status == "healthy" and is_sticky_alert_active(link_id):
                                clear_sticky_alert(link_id, "health_poll_recovery")
                                await handle_link_status_change(self.client, parts[0], parts[1], "healthy")

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

    async def process_snmp_trap(self, trap_data: dict) -> dict:
        """
        Process a real SNMP trap from `snmptrap-mcp` (010-telemetry-receivers)
        and latch/clear a sticky visual alert on the affected interface
        (US6, FR-017/FR-018/FR-019).

        REWRITTEN for 045-ue5-digital-twin: the previous implementation built
        a LINK_STATUS_CHANGE TelemetryEvent with only `hostname` set, but
        handle_telemetry_event's LINK_STATUS_CHANGE branch only acts when
        `event.link_id` is set — hostname alone was silently ignored, so
        every trap this receiver ever processed was a complete no-op before
        this fix. Interface-level traps also don't map cleanly onto that
        device-pair-keyed event type anyway (a link needs BOTH endpoints;
        a trap only ever names one device/interface), so this routes
        directly to the interface-actor coloring + sticky-alert registry
        added for this feature instead of through the legacy event path.

        Args:
            trap_data: Parsed trap dict. Expects `hostname` (falls back to
                `source_ip` for backward compatibility with pre-045 senders)
                and `interface`; `trap_oid` selects down (.5.3) vs up (.5.4).

        Returns:
            {"applied": bool, "reason": str} — always returns rather than
            raising, per FR-019 (unknown device/interface must be ignored,
            not error).
        """
        hostname = trap_data.get("hostname") or trap_data.get("source_ip")
        interface = trap_data.get("interface", "")
        oid = trap_data.get("trap_oid", "")

        if not hostname or not interface:
            return {"applied": False, "reason": "trap missing hostname/interface"}

        # FR-019: ignore traps for devices/interfaces not in the current scene.
        if not is_interface_in_topology(hostname, interface):
            return {"applied": False, "reason": f"{hostname}:{interface} not in current topology"}

        subject_key = f"{hostname}:{interface}"

        if "1.3.6.1.6.3.1.1.5.3" in oid:  # linkDown
            previous = is_sticky_alert_active(subject_key)
            latch_sticky_alert(subject_key, "linkDown")
            record_history(subject_key, "trap", previous, "linkDown")
            applied = await apply_interface_material(
                self.client, hostname, interface, get_alarm_color().to_list(), emissive_intensity=2.5
            )
            return {"applied": applied, "reason": "linkDown trap latched sticky alert"}

        if "1.3.6.1.6.3.1.1.5.4" in oid:  # linkUp
            if is_sticky_alert_active(subject_key):
                clear_sticky_alert(subject_key, "linkUp_trap")
                record_history(subject_key, "trap", "linkDown", "linkUp")
            applied = await apply_interface_material(
                self.client, hostname, interface, get_link_status_color("healthy").to_list()
            )
            return {"applied": applied, "reason": "linkUp trap cleared sticky alert"}

        return {"applied": False, "reason": f"unhandled trap OID {oid}"}


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
