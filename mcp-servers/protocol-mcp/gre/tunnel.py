"""
GRE Tunnel Implementation

This module provides the GRETunnel class for managing individual GRE tunnels,
including raw socket handling, packet send/receive, and tunnel state management.

Supports both:
- Active mode: Agent initiates tunnel to external network (CML, CLAB)
- Passive mode: Agent accepts incoming GRE from external network
"""

import asyncio
import socket
import struct
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any, List, Tuple
from datetime import datetime
from enum import Enum

from .constants import (
    IPPROTO_GRE,
    PROTO_IPV4,
    PROTO_IPV6,
    PROTOCOL_NAMES,
    GRE_TUNNEL_MTU,
    GRE_SAFE_MTU,
    GRE_OVERHEAD_MIN,
    DEFAULT_TTL,
    DEFAULT_TOS,
    DEFAULT_KEEPALIVE_INTERVAL,
    DEFAULT_KEEPALIVE_RETRIES,
    TUNNEL_STATE_DOWN,
    TUNNEL_STATE_UP,
    TUNNEL_STATE_ADMIN_DOWN,
    TUNNEL_STATE_ESTABLISHING,
    TUNNEL_STATE_FAILED,
    GREError,
)
from .header import (
    GREHeader,
    encode_gre_header,
    decode_gre_header,
    encapsulate_packet,
    decapsulate_packet,
)

logger = logging.getLogger("GRE.Tunnel")


class TunnelMode(Enum):
    """GRE tunnel operational mode"""
    POINT_TO_POINT = "p2p"      # Standard P2P tunnel
    MULTIPOINT = "multipoint"   # mGRE (future)


class TunnelDirection(Enum):
    """Tunnel initiation direction"""
    ACTIVE = "active"           # We initiate the tunnel
    PASSIVE = "passive"         # We accept incoming tunnels
    BIDIRECTIONAL = "bidir"     # Both directions supported


@dataclass
class GRETunnelConfig:
    """
    Configuration for a GRE tunnel

    Attributes:
        name: Tunnel interface name (e.g., "gre0", "gre-to-cml")
        local_ip: Local endpoint IP address (physical interface)
        remote_ip: Remote endpoint IP address
        tunnel_ip: IP address assigned to tunnel interface (with prefix, e.g., "10.0.0.1/30")
        key: Optional GRE key for traffic identification
        use_checksum: Whether to calculate checksums
        use_sequence: Whether to use sequence numbers
        mtu: Tunnel MTU (default calculated from overhead)
        ttl: TTL for outer IP packets
        tos: TOS/DSCP byte for outer IP packets
        keepalive_interval: Keepalive probe interval (0 to disable)
        keepalive_retries: Max keepalive failures before marking down
        mode: Tunnel mode (P2P or multipoint)
        direction: Active (initiate) or Passive (accept)
        description: Optional description
    """
    name: str
    local_ip: str
    remote_ip: str
    tunnel_ip: str = ""

    # GRE options
    key: Optional[int] = None
    use_checksum: bool = False
    use_sequence: bool = False

    # Transport options
    mtu: int = GRE_SAFE_MTU
    ttl: int = DEFAULT_TTL
    tos: int = DEFAULT_TOS

    # Keepalive
    keepalive_interval: int = DEFAULT_KEEPALIVE_INTERVAL
    keepalive_retries: int = DEFAULT_KEEPALIVE_RETRIES

    # Mode
    mode: TunnelMode = TunnelMode.POINT_TO_POINT
    direction: TunnelDirection = TunnelDirection.BIDIRECTIONAL

    # Metadata
    description: str = ""
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "local_ip": self.local_ip,
            "remote_ip": self.remote_ip,
            "tunnel_ip": self.tunnel_ip,
            "key": self.key,
            "use_checksum": self.use_checksum,
            "use_sequence": self.use_sequence,
            "mtu": self.mtu,
            "ttl": self.ttl,
            "tos": self.tos,
            "keepalive_interval": self.keepalive_interval,
            "keepalive_retries": self.keepalive_retries,
            "mode": self.mode.value,
            "direction": self.direction.value,
            "description": self.description,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GRETunnelConfig":
        """Create from dictionary"""
        # Handle enum conversions
        mode = data.get("mode", "p2p")
        if isinstance(mode, str):
            mode = TunnelMode(mode)
        direction = data.get("direction", "bidir")
        if isinstance(direction, str):
            direction = TunnelDirection(direction)

        return cls(
            name=data["name"],
            local_ip=data["local_ip"],
            remote_ip=data["remote_ip"],
            tunnel_ip=data.get("tunnel_ip", ""),
            key=data.get("key"),
            use_checksum=data.get("use_checksum", False),
            use_sequence=data.get("use_sequence", False),
            mtu=data.get("mtu", GRE_SAFE_MTU),
            ttl=data.get("ttl", DEFAULT_TTL),
            tos=data.get("tos", DEFAULT_TOS),
            keepalive_interval=data.get("keepalive_interval", DEFAULT_KEEPALIVE_INTERVAL),
            keepalive_retries=data.get("keepalive_retries", DEFAULT_KEEPALIVE_RETRIES),
            mode=mode,
            direction=direction,
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
        )


@dataclass
class GRETunnelStatistics:
    """Statistics for a GRE tunnel"""
    packets_tx: int = 0
    packets_rx: int = 0
    bytes_tx: int = 0
    bytes_rx: int = 0
    packets_dropped: int = 0
    checksum_errors: int = 0
    key_mismatches: int = 0
    sequence_errors: int = 0
    keepalive_tx: int = 0
    keepalive_rx: int = 0
    keepalive_failures: int = 0
    last_packet_rx: Optional[datetime] = None
    last_packet_tx: Optional[datetime] = None
    uptime_start: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "packets_tx": self.packets_tx,
            "packets_rx": self.packets_rx,
            "bytes_tx": self.bytes_tx,
            "bytes_rx": self.bytes_rx,
            "packets_dropped": self.packets_dropped,
            "checksum_errors": self.checksum_errors,
            "key_mismatches": self.key_mismatches,
            "sequence_errors": self.sequence_errors,
            "keepalive_tx": self.keepalive_tx,
            "keepalive_rx": self.keepalive_rx,
            "keepalive_failures": self.keepalive_failures,
            "last_packet_rx": self.last_packet_rx.isoformat() if self.last_packet_rx else None,
            "last_packet_tx": self.last_packet_tx.isoformat() if self.last_packet_tx else None,
            "uptime_seconds": (datetime.now() - self.uptime_start).total_seconds() if self.uptime_start else 0,
        }

    def reset(self):
        """Reset all statistics"""
        self.packets_tx = 0
        self.packets_rx = 0
        self.bytes_tx = 0
        self.bytes_rx = 0
        self.packets_dropped = 0
        self.checksum_errors = 0
        self.key_mismatches = 0
        self.sequence_errors = 0
        self.keepalive_tx = 0
        self.keepalive_rx = 0
        self.keepalive_failures = 0


class GRETunnel:
    """
    GRE Tunnel Manager

    Manages a single GRE tunnel including:
    - Raw socket for GRE protocol (IP protocol 47)
    - Packet encapsulation/decapsulation
    - Keepalive management
    - State tracking and statistics
    """

    def __init__(self, config: GRETunnelConfig):
        """
        Initialize GRE tunnel

        Args:
            config: Tunnel configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"GRE.Tunnel[{config.name}]")

        # Socket
        self._socket: Optional[socket.socket] = None
        self._socket_lock = asyncio.Lock()

        # State
        self._state = TUNNEL_STATE_DOWN
        self._state_reason = ""
        self._sequence_tx = 0
        self._sequence_rx = 0

        # Statistics
        self.stats = GRETunnelStatistics()

        # Callbacks
        self._packet_callback: Optional[Callable[[bytes, GREHeader, str], None]] = None

        # Tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._keepalive_task: Optional[asyncio.Task] = None

        # Keepalive tracking
        self._keepalive_failures = 0
        self._last_keepalive_rx: Optional[float] = None

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_up(self) -> bool:
        return self._state == TUNNEL_STATE_UP

    @property
    def tunnel_id(self) -> str:
        """Unique tunnel identifier"""
        return f"{self.config.local_ip}-{self.config.remote_ip}"

    async def start(self) -> bool:
        """
        Start the tunnel

        Returns:
            True if tunnel started successfully
        """
        if not self.config.enabled:
            self._state = TUNNEL_STATE_ADMIN_DOWN
            self._state_reason = "Administratively disabled"
            return False

        self._state = TUNNEL_STATE_ESTABLISHING
        self.logger.info(f"Starting GRE tunnel {self.name}: {self.config.local_ip} -> {self.config.remote_ip}")

        try:
            # Create raw socket for GRE
            await self._create_socket()

            # Start receive task
            self._receive_task = asyncio.create_task(self._receive_loop())

            # Start keepalive task if enabled
            if self.config.keepalive_interval > 0:
                self._keepalive_task = asyncio.create_task(self._keepalive_loop())

            # Mark tunnel as up
            self._state = TUNNEL_STATE_UP
            self._state_reason = ""
            self.stats.uptime_start = datetime.now()

            self.logger.info(f"GRE tunnel {self.name} is UP")
            return True

        except PermissionError:
            self._state = TUNNEL_STATE_FAILED
            self._state_reason = "Permission denied - root/admin required"
            self.logger.error(f"Permission denied creating GRE socket (need root)")
            return False

        except Exception as e:
            self._state = TUNNEL_STATE_FAILED
            self._state_reason = str(e)
            self.logger.error(f"Failed to start tunnel: {e}")
            return False

    async def stop(self):
        """Stop the tunnel"""
        self.logger.info(f"Stopping GRE tunnel {self.name}")

        # Cancel tasks
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None

        # Close socket
        await self._close_socket()

        self._state = TUNNEL_STATE_DOWN
        self._state_reason = "Stopped"
        self.logger.info(f"GRE tunnel {self.name} is DOWN")

    async def _create_socket(self):
        """Create raw socket for GRE"""
        async with self._socket_lock:
            if self._socket:
                return

            # Create raw socket for GRE protocol
            self._socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_RAW,
                IPPROTO_GRE
            )

            # Set socket options
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind to local IP to receive only traffic destined for us
            self._socket.bind((self.config.local_ip, 0))

            # Set non-blocking for asyncio
            self._socket.setblocking(False)

            # Set TOS for QoS
            try:
                self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, self.config.tos)
            except Exception as e:
                self.logger.warning(f"Could not set TOS: {e}")

            # Set TTL
            try:
                self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, self.config.ttl)
            except Exception as e:
                self.logger.warning(f"Could not set TTL: {e}")

            self.logger.debug(f"Created GRE socket bound to {self.config.local_ip}")

    async def _close_socket(self):
        """Close the raw socket"""
        async with self._socket_lock:
            if self._socket:
                try:
                    self._socket.close()
                except Exception as e:
                    self.logger.warning(f"Error closing socket: {e}")
                self._socket = None

    async def send(self, payload: bytes, protocol_type: int = PROTO_IPV4) -> bool:
        """
        Send a packet through the tunnel

        Args:
            payload: Packet payload to encapsulate and send
            protocol_type: Ethertype of payload (default IPv4)

        Returns:
            True if sent successfully
        """
        if not self.is_up or not self._socket:
            self.logger.warning(f"Cannot send - tunnel {self.name} is not up")
            return False

        # Check MTU
        if len(payload) > self.config.mtu:
            self.logger.warning(f"Packet size {len(payload)} exceeds MTU {self.config.mtu}")
            self.stats.packets_dropped += 1
            return False

        try:
            # Get sequence number if using
            seq = None
            if self.config.use_sequence:
                seq = self._sequence_tx
                self._sequence_tx = (self._sequence_tx + 1) % (2**32)

            # Encode GRE header
            header_bytes, _ = encode_gre_header(
                protocol_type=protocol_type,
                checksum=self.config.use_checksum,
                key=self.config.key,
                sequence_number=seq,
                payload=payload
            )

            # Build full GRE packet
            gre_packet = header_bytes + payload

            # Send to remote endpoint
            loop = asyncio.get_event_loop()
            await loop.sock_sendto(self._socket, gre_packet, (self.config.remote_ip, 0))

            # Update stats
            self.stats.packets_tx += 1
            self.stats.bytes_tx += len(gre_packet)
            self.stats.last_packet_tx = datetime.now()

            self.logger.debug(f"Sent {len(gre_packet)} bytes to {self.config.remote_ip}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send packet: {e}")
            self.stats.packets_dropped += 1
            return False

    async def _receive_loop(self):
        """Background task to receive GRE packets"""
        self.logger.debug(f"Starting receive loop for tunnel {self.name}")
        loop = asyncio.get_event_loop()

        while self._state in [TUNNEL_STATE_UP, TUNNEL_STATE_ESTABLISHING]:
            try:
                # Receive packet (includes IP header)
                data, addr = await loop.sock_recvfrom(self._socket, 65535)
                source_ip = addr[0]

                # Filter by remote IP (only accept from our peer)
                if source_ip != self.config.remote_ip:
                    self.logger.debug(f"Ignoring packet from unexpected source: {source_ip}")
                    continue

                # Strip IP header (variable length)
                ip_header_len = (data[0] & 0x0F) * 4
                gre_data = data[ip_header_len:]

                # Decode GRE header
                header, offset, error = decode_gre_header(gre_data)

                if error:
                    self._handle_decode_error(error)
                    continue

                # Verify key if configured
                if self.config.key is not None and header.key != self.config.key:
                    self.logger.warning(f"Key mismatch: expected {self.config.key}, got {header.key}")
                    self.stats.key_mismatches += 1
                    continue

                # Extract payload
                payload = gre_data[offset:]

                # Update stats
                self.stats.packets_rx += 1
                self.stats.bytes_rx += len(data)
                self.stats.last_packet_rx = datetime.now()
                self._last_keepalive_rx = time.time()
                self._keepalive_failures = 0  # Reset on any received packet

                # Handle keepalive probe (empty payload with our protocol marker)
                if len(payload) == 0 or self._is_keepalive(payload, header):
                    self.stats.keepalive_rx += 1
                    self.logger.debug(f"Received keepalive from {source_ip}")
                    continue

                # Deliver payload to callback
                if self._packet_callback:
                    try:
                        await self._packet_callback(payload, header, source_ip)
                    except Exception as e:
                        self.logger.error(f"Packet callback error: {e}")

                self.logger.debug(f"Received {len(payload)} byte {header.protocol_name} packet from {source_ip}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._state != TUNNEL_STATE_DOWN:
                    self.logger.error(f"Receive error: {e}")
                await asyncio.sleep(0.1)

        self.logger.debug(f"Receive loop ended for tunnel {self.name}")

    def _handle_decode_error(self, error: int):
        """Handle GRE decode errors"""
        if error == GREError.CHECKSUM_MISMATCH:
            self.stats.checksum_errors += 1
            self.logger.warning("GRE checksum mismatch")
        elif error == GREError.INVALID_HEADER:
            self.stats.packets_dropped += 1
            self.logger.warning("Invalid GRE header")
        else:
            self.stats.packets_dropped += 1
            self.logger.warning(f"GRE decode error: {error}")

    def _is_keepalive(self, payload: bytes, header: GREHeader) -> bool:
        """Check if packet is a keepalive probe"""
        # Keepalive: small payload or specific marker
        if len(payload) < 20:
            return True
        return False

    async def _keepalive_loop(self):
        """Background task to send keepalive probes"""
        self.logger.debug(f"Starting keepalive loop (interval={self.config.keepalive_interval}s)")

        while self._state in [TUNNEL_STATE_UP, TUNNEL_STATE_ESTABLISHING]:
            try:
                await asyncio.sleep(self.config.keepalive_interval)

                if not self.is_up:
                    continue

                # Send keepalive probe (empty GRE packet)
                await self._send_keepalive()

                # Check for keepalive timeout
                if self._last_keepalive_rx:
                    elapsed = time.time() - self._last_keepalive_rx
                    timeout = self.config.keepalive_interval * self.config.keepalive_retries

                    if elapsed > timeout:
                        self._keepalive_failures += 1
                        self.stats.keepalive_failures += 1
                        self.logger.warning(f"Keepalive timeout ({elapsed:.1f}s > {timeout}s)")

                        if self._keepalive_failures >= self.config.keepalive_retries:
                            self.logger.error(f"Tunnel {self.name} marked DOWN due to keepalive failures")
                            self._state = TUNNEL_STATE_DOWN
                            self._state_reason = "Keepalive timeout"

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Keepalive error: {e}")

    async def _send_keepalive(self):
        """Send a keepalive probe"""
        if not self._socket:
            return

        try:
            # Send minimal GRE packet (just header, no payload)
            header_bytes, _ = encode_gre_header(
                protocol_type=PROTO_IPV4,
                key=self.config.key,
                checksum=False
            )

            loop = asyncio.get_event_loop()
            await loop.sock_sendto(self._socket, header_bytes, (self.config.remote_ip, 0))
            self.stats.keepalive_tx += 1
            self.logger.debug(f"Sent keepalive to {self.config.remote_ip}")

        except Exception as e:
            self.logger.error(f"Failed to send keepalive: {e}")

    def set_packet_callback(self, callback: Callable[[bytes, GREHeader, str], None]):
        """
        Set callback for received packets

        Args:
            callback: Async function(payload, header, source_ip) called for each packet
        """
        self._packet_callback = callback

    def get_status(self) -> Dict[str, Any]:
        """Get tunnel status"""
        return {
            "name": self.config.name,
            "state": self._state,
            "state_reason": self._state_reason,
            "local_ip": self.config.local_ip,
            "remote_ip": self.config.remote_ip,
            "tunnel_ip": self.config.tunnel_ip,
            "key": self.config.key,
            "mtu": self.config.mtu,
            "mode": self.config.mode.value,
            "direction": self.config.direction.value,
            "keepalive_interval": self.config.keepalive_interval,
            "statistics": self.stats.to_dict(),
        }

    def __str__(self) -> str:
        return f"GRETunnel({self.name}: {self.config.local_ip} -> {self.config.remote_ip}, state={self._state})"

    def __repr__(self) -> str:
        return self.__str__()
