"""
GRE Manager - Multi-Tunnel Orchestration

Manages multiple GRE tunnels for an agent, providing:
- Tunnel lifecycle management (create, delete, start, stop)
- Packet routing to appropriate tunnels
- Integration with routing protocols (OSPF, BGP)
- Passive listening for incoming tunnels
"""

import asyncio
import socket
import logging
from typing import Dict, Optional, List, Any, Callable, Set
from dataclasses import dataclass
from datetime import datetime

from .constants import (
    IPPROTO_GRE,
    PROTO_IPV4,
    PROTO_IPV6,
    TUNNEL_STATE_UP,
    TUNNEL_STATE_DOWN,
    GRE_SAFE_MTU,
    GREError,
)
from .header import GREHeader, decode_gre_header
from .tunnel import GRETunnel, GRETunnelConfig, TunnelDirection

logger = logging.getLogger("GRE.Manager")

# Global manager instances per agent
_managers: Dict[str, "GREManager"] = {}


def get_gre_manager(agent_id: str = "local") -> Optional["GREManager"]:
    """Get the GRE manager for an agent"""
    return _managers.get(agent_id)


def configure_gre_manager(agent_id: str, local_ip: str, **kwargs) -> "GREManager":
    """Create and configure a GRE manager for an agent"""
    if agent_id in _managers:
        return _managers[agent_id]

    manager = GREManager(agent_id=agent_id, local_ip=local_ip, **kwargs)
    _managers[agent_id] = manager
    logger.info(f"Created GRE manager for agent {agent_id} (local_ip={local_ip})")
    return manager


@dataclass
class GREManagerConfig:
    """Configuration for GRE Manager"""
    local_ip: str
    enable_passive: bool = True  # Accept incoming tunnels
    accept_any_source: bool = False  # Accept tunnels from any IP
    allowed_sources: List[str] = None  # List of allowed source IPs for passive
    default_key: Optional[int] = None  # Default key for auto-accepted tunnels
    max_tunnels: int = 100  # Maximum concurrent tunnels

    def __post_init__(self):
        if self.allowed_sources is None:
            self.allowed_sources = []


class GREManager:
    """
    GRE Manager

    Orchestrates multiple GRE tunnels for an agent, supporting both
    active (outbound) and passive (inbound) tunnel establishment.

    Usage:
        manager = GREManager(agent_id="agent1", local_ip="192.168.1.1")
        await manager.start()

        # Create outbound tunnel to CML
        config = GRETunnelConfig(
            name="gre-to-cml",
            local_ip="192.168.1.1",
            remote_ip="192.168.2.1",
            tunnel_ip="10.0.0.1/30"
        )
        tunnel = await manager.create_tunnel(config)

        # Tunnel is now up and can be used by OSPF/BGP
    """

    def __init__(
        self,
        agent_id: str,
        local_ip: str,
        enable_passive: bool = True,
        accept_any_source: bool = False,
        allowed_sources: Optional[List[str]] = None,
        default_key: Optional[int] = None,
        max_tunnels: int = 100
    ):
        """
        Initialize GRE Manager

        Args:
            agent_id: Agent identifier
            local_ip: Local IP address for tunnel endpoints
            enable_passive: Whether to accept incoming tunnels
            accept_any_source: Accept tunnels from any source IP
            allowed_sources: List of allowed source IPs for passive mode
            default_key: Default GRE key for auto-accepted tunnels
            max_tunnels: Maximum number of concurrent tunnels
        """
        self.agent_id = agent_id
        self.local_ip = local_ip
        self.enable_passive = enable_passive
        self.accept_any_source = accept_any_source
        self.allowed_sources: Set[str] = set(allowed_sources or [])
        self.default_key = default_key
        self.max_tunnels = max_tunnels

        self.logger = logging.getLogger(f"GRE.Manager[{agent_id}]")

        # Tunnel storage
        self._tunnels: Dict[str, GRETunnel] = {}  # name -> tunnel
        self._tunnels_by_endpoint: Dict[str, GRETunnel] = {}  # "local-remote" -> tunnel

        # Passive listener
        self._passive_socket: Optional[socket.socket] = None
        self._passive_task: Optional[asyncio.Task] = None

        # Callbacks
        self._tunnel_up_callback: Optional[Callable[[GRETunnel], None]] = None
        self._tunnel_down_callback: Optional[Callable[[GRETunnel], None]] = None
        self._packet_callback: Optional[Callable[[bytes, GREHeader, str, str], None]] = None

        # State
        self._running = False
        self._started_at: Optional[datetime] = None

    @property
    def tunnel_count(self) -> int:
        """Number of active tunnels"""
        return len(self._tunnels)

    @property
    def running(self) -> bool:
        """Whether manager is running"""
        return self._running

    async def start(self):
        """Start the GRE manager"""
        if self._running:
            return

        self.logger.info(f"Starting GRE manager for agent {self.agent_id}")
        self._running = True
        self._started_at = datetime.now()

        # Discover existing GRE tunnels from environment variables
        await self._discover_existing_tunnels()

        # Start passive listener if enabled
        if self.enable_passive:
            await self._start_passive_listener()

        self.logger.info(f"GRE manager started (passive={'enabled' if self.enable_passive else 'disabled'}, tunnels={self.tunnel_count})")

    async def _discover_existing_tunnels(self):
        """
        Discover existing GRE tunnels from environment variables

        Reads GRE_TUNNEL_* environment variables set by docker-entrypoint.sh
        and registers them with the manager for dashboard visibility.

        Format: GRE_TUNNEL_<name>=<name>:<local_ip>:<remote_ip>:<tunnel_ip>:<key>:<ttl>:<mtu>
        Example: GRE_TUNNEL_0=gre0:192.168.100.10:192.168.100.20:10.255.0.1/30:100:64:1400
        """
        import os
        import re

        discovered_count = 0

        for env_var, value in os.environ.items():
            if not env_var.startswith("GRE_TUNNEL_"):
                continue

            try:
                # Parse: name:local_ip:remote_ip:tunnel_ip:key:ttl:mtu
                parts = value.split(':')
                if len(parts) < 4:
                    self.logger.warning(f"Invalid GRE tunnel config in {env_var}: {value}")
                    continue

                name = parts[0]
                local_ip = parts[1]
                remote_ip = parts[2]
                tunnel_ip = parts[3]
                key = int(parts[4]) if len(parts) > 4 and parts[4] and parts[4] != "none" else None
                ttl = int(parts[5]) if len(parts) > 5 else 64
                mtu = int(parts[6]) if len(parts) > 6 else 1400

                # Create tunnel config
                from .tunnel import GRETunnelConfig, TunnelDirection, TunnelMode
                config = GRETunnelConfig(
                    name=name,
                    local_ip=local_ip,
                    remote_ip=remote_ip,
                    tunnel_ip=tunnel_ip,
                    key=key,
                    mtu=mtu,
                    ttl=ttl,
                    direction=TunnelDirection.BIDIRECTIONAL,
                    mode=TunnelMode.POINT_TO_POINT  # System tunnels use P2P mode
                )

                # Create tunnel object (it already exists in system, so we just register it)
                from .tunnel import GRETunnel
                tunnel = GRETunnel(config)
                tunnel._state = TUNNEL_STATE_UP  # Assume it's up since it was created by entrypoint.sh
                tunnel._state_reason = "Discovered from environment"

                # Register with manager
                self._tunnels[name] = tunnel
                endpoint_key = f"{local_ip}-{remote_ip}"
                self._tunnels_by_endpoint[endpoint_key] = tunnel

                discovered_count += 1
                self.logger.info(f"Discovered existing GRE tunnel: {name} ({local_ip} -> {remote_ip}, key={key})")

            except Exception as e:
                self.logger.error(f"Error discovering tunnel from {env_var}: {e}")

        if discovered_count > 0:
            self.logger.info(f"Discovered {discovered_count} existing GRE tunnel(s)")

    async def stop(self):
        """Stop the GRE manager and all tunnels"""
        if not self._running:
            return

        self.logger.info(f"Stopping GRE manager for agent {self.agent_id}")

        # Stop passive listener
        await self._stop_passive_listener()

        # Stop all tunnels
        for tunnel in list(self._tunnels.values()):
            await tunnel.stop()

        self._tunnels.clear()
        self._tunnels_by_endpoint.clear()
        self._running = False

        self.logger.info("GRE manager stopped")

    async def create_tunnel(self, config: GRETunnelConfig) -> Optional[GRETunnel]:
        """
        Create and start a new GRE tunnel

        Args:
            config: Tunnel configuration

        Returns:
            GRETunnel instance if successful, None otherwise
        """
        # Check limits
        if len(self._tunnels) >= self.max_tunnels:
            self.logger.error(f"Maximum tunnel limit reached ({self.max_tunnels})")
            return None

        # Check for duplicate name
        if config.name in self._tunnels:
            self.logger.error(f"Tunnel with name '{config.name}' already exists")
            return None

        # Check for duplicate endpoint
        endpoint_key = f"{config.local_ip}-{config.remote_ip}"
        if endpoint_key in self._tunnels_by_endpoint:
            self.logger.error(f"Tunnel to {config.remote_ip} already exists")
            return None

        # Override local_ip if not set
        if not config.local_ip:
            config.local_ip = self.local_ip

        # Create tunnel
        tunnel = GRETunnel(config)

        # Set packet callback
        tunnel.set_packet_callback(self._on_tunnel_packet)

        # Store tunnel before starting (so it shows in dashboard even if start fails)
        self._tunnels[config.name] = tunnel
        self._tunnels_by_endpoint[endpoint_key] = tunnel

        # Start tunnel
        success = await tunnel.start()
        if not success:
            self.logger.error(f"Failed to start tunnel {config.name}")
            return tunnel  # Return the tunnel object (state=FAILED) so caller knows it exists

        # Notify callback
        if self._tunnel_up_callback:
            try:
                await self._tunnel_up_callback(tunnel)
            except Exception as e:
                self.logger.error(f"Tunnel up callback error: {e}")

        self.logger.info(f"Created tunnel {config.name}: {config.local_ip} -> {config.remote_ip}")
        return tunnel

    async def delete_tunnel(self, name: str) -> bool:
        """
        Delete a tunnel by name

        Args:
            name: Tunnel name

        Returns:
            True if deleted successfully
        """
        tunnel = self._tunnels.get(name)
        if not tunnel:
            self.logger.warning(f"Tunnel '{name}' not found")
            return False

        # Stop tunnel
        await tunnel.stop()

        # Remove from storage
        del self._tunnels[name]
        endpoint_key = f"{tunnel.config.local_ip}-{tunnel.config.remote_ip}"
        self._tunnels_by_endpoint.pop(endpoint_key, None)

        # Notify callback
        if self._tunnel_down_callback:
            try:
                await self._tunnel_down_callback(tunnel)
            except Exception as e:
                self.logger.error(f"Tunnel down callback error: {e}")

        self.logger.info(f"Deleted tunnel {name}")
        return True

    def get_tunnel(self, name: str) -> Optional[GRETunnel]:
        """Get a tunnel by name"""
        return self._tunnels.get(name)

    def get_tunnel_by_remote(self, remote_ip: str) -> Optional[GRETunnel]:
        """Get a tunnel by remote IP"""
        for tunnel in self._tunnels.values():
            if tunnel.config.remote_ip == remote_ip:
                return tunnel
        return None

    def get_tunnels(self) -> list:
        """Get all tunnel objects"""
        return list(self._tunnels.values())

    def list_tunnels(self) -> List[Dict[str, Any]]:
        """List all tunnels with status"""
        return [tunnel.get_status() for tunnel in self._tunnels.values()]

    def get_tunnel_names(self) -> List[str]:
        """Get list of tunnel names"""
        return list(self._tunnels.keys())

    async def _start_passive_listener(self):
        """Start passive GRE listener for incoming tunnels"""
        try:
            # Create raw socket to receive all GRE packets
            self._passive_socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_RAW,
                IPPROTO_GRE
            )
            self._passive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._passive_socket.bind((self.local_ip, 0))
            self._passive_socket.setblocking(False)

            # Start receive task
            self._passive_task = asyncio.create_task(self._passive_receive_loop())

            self.logger.info(f"Passive GRE listener started on {self.local_ip}")

        except PermissionError:
            self.logger.warning("Cannot start passive listener - root required")
            self.enable_passive = False
        except Exception as e:
            self.logger.error(f"Failed to start passive listener: {e}")
            self.enable_passive = False

    async def _stop_passive_listener(self):
        """Stop passive listener"""
        if self._passive_task:
            self._passive_task.cancel()
            try:
                await self._passive_task
            except asyncio.CancelledError:
                pass
            self._passive_task = None

        if self._passive_socket:
            try:
                self._passive_socket.close()
            except Exception:
                pass
            self._passive_socket = None

    async def _passive_receive_loop(self):
        """Background task for passive tunnel reception"""
        self.logger.debug("Starting passive receive loop")
        loop = asyncio.get_event_loop()

        while self._running:
            try:
                # Receive packet
                data, addr = await loop.sock_recvfrom(self._passive_socket, 65535)
                source_ip = addr[0]

                # Check if this is from an existing tunnel
                endpoint_key = f"{self.local_ip}-{source_ip}"
                if endpoint_key in self._tunnels_by_endpoint:
                    # Already have a tunnel for this endpoint
                    continue

                # Check if source is allowed
                if not self.accept_any_source and source_ip not in self.allowed_sources:
                    self.logger.debug(f"Ignoring GRE from non-allowed source: {source_ip}")
                    continue

                # Strip IP header
                ip_header_len = (data[0] & 0x0F) * 4
                gre_data = data[ip_header_len:]

                # Decode GRE header
                header, offset, error = decode_gre_header(gre_data)
                if error:
                    continue

                # Check key if we require one
                if self.default_key is not None and header.key != self.default_key:
                    self.logger.debug(f"Ignoring GRE with wrong key from {source_ip}")
                    continue

                # Auto-create tunnel for this source
                await self._auto_create_tunnel(source_ip, header)

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._running:
                    self.logger.error(f"Passive receive error: {e}")
                await asyncio.sleep(0.1)

        self.logger.debug("Passive receive loop ended")

    async def _auto_create_tunnel(self, remote_ip: str, header: GREHeader):
        """Auto-create a tunnel for an incoming connection"""
        self.logger.info(f"Auto-creating tunnel for incoming connection from {remote_ip}")

        # Generate tunnel name
        tunnel_num = len(self._tunnels)
        name = f"gre-auto-{tunnel_num}"

        # Create config
        config = GRETunnelConfig(
            name=name,
            local_ip=self.local_ip,
            remote_ip=remote_ip,
            key=header.key,
            direction=TunnelDirection.PASSIVE,
            description=f"Auto-created tunnel from {remote_ip}"
        )

        # Create tunnel
        tunnel = await self.create_tunnel(config)
        if tunnel:
            self.logger.info(f"Auto-created tunnel {name} for {remote_ip}")

    async def _on_tunnel_packet(self, payload: bytes, header: GREHeader, source_ip: str):
        """Handle packet received from a tunnel"""
        if self._packet_callback:
            # Find tunnel name
            tunnel_name = ""
            for name, tunnel in self._tunnels.items():
                if tunnel.config.remote_ip == source_ip:
                    tunnel_name = name
                    break

            try:
                await self._packet_callback(payload, header, source_ip, tunnel_name)
            except Exception as e:
                self.logger.error(f"Packet callback error: {e}")

    def add_allowed_source(self, ip: str):
        """Add an IP to the allowed sources list"""
        self.allowed_sources.add(ip)
        self.logger.info(f"Added {ip} to allowed GRE sources")

    def remove_allowed_source(self, ip: str):
        """Remove an IP from the allowed sources list"""
        self.allowed_sources.discard(ip)
        self.logger.info(f"Removed {ip} from allowed GRE sources")

    def set_tunnel_up_callback(self, callback: Callable[[GRETunnel], None]):
        """Set callback for tunnel up events"""
        self._tunnel_up_callback = callback

    def set_tunnel_down_callback(self, callback: Callable[[GRETunnel], None]):
        """Set callback for tunnel down events"""
        self._tunnel_down_callback = callback

    def set_packet_callback(self, callback: Callable[[bytes, GREHeader, str, str], None]):
        """Set callback for received packets"""
        self._packet_callback = callback

    def get_status(self) -> Dict[str, Any]:
        """Get manager status"""
        tunnels_up = sum(1 for t in self._tunnels.values() if t.is_up)
        total_rx = sum(t.stats.packets_rx for t in self._tunnels.values())
        total_tx = sum(t.stats.packets_tx for t in self._tunnels.values())

        return {
            "agent_id": self.agent_id,
            "local_ip": self.local_ip,
            "running": self._running,
            "passive_enabled": self.enable_passive,
            "accept_any_source": self.accept_any_source,
            "allowed_sources": list(self.allowed_sources),
            "tunnel_count": self.tunnel_count,
            "tunnels_up": tunnels_up,
            "tunnels_down": self.tunnel_count - tunnels_up,
            "max_tunnels": self.max_tunnels,
            "total_packets_rx": total_rx,
            "total_packets_tx": total_tx,
            "uptime_seconds": (datetime.now() - self._started_at).total_seconds() if self._started_at else 0,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics"""
        stats = {
            "tunnels": {},
            "totals": {
                "packets_rx": 0,
                "packets_tx": 0,
                "bytes_rx": 0,
                "bytes_tx": 0,
                "packets_dropped": 0,
            }
        }

        for name, tunnel in self._tunnels.items():
            tunnel_stats = tunnel.stats.to_dict()
            stats["tunnels"][name] = tunnel_stats
            stats["totals"]["packets_rx"] += tunnel.stats.packets_rx
            stats["totals"]["packets_tx"] += tunnel.stats.packets_tx
            stats["totals"]["bytes_rx"] += tunnel.stats.bytes_rx
            stats["totals"]["bytes_tx"] += tunnel.stats.bytes_tx
            stats["totals"]["packets_dropped"] += tunnel.stats.packets_dropped

        return stats

    def __str__(self) -> str:
        return f"GREManager(agent={self.agent_id}, tunnels={self.tunnel_count}, running={self._running})"
