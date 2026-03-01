"""
BGP Session Management

Manages BGP peer sessions with TCP transport, FSM integration,
and message send/receive over the wire.

Each BGPSession represents a single BGP peering session, managing:
- TCP connection establishment (active or passive)
- Message encoding/decoding from wire format
- FSM event processing
- RIB management and route exchange
- Timers (ConnectRetry, Hold, Keepalive)
"""

import asyncio
import logging
import struct
import time
from typing import Optional, Callable, Dict, List, Any
from dataclasses import dataclass

from .constants import *
from .messages import BGPMessage, BGPOpen, BGPUpdate, BGPKeepalive, BGPNotification, BGPCapability
from .fsm import BGPFSM, BGPEvent
from .rib import AdjRIBIn, LocRIB, AdjRIBOut, BGPRoute
from .capabilities import CapabilityManager, build_capability_list, parse_capabilities_from_open
from .attributes import PathAttribute
from .flap_damping import RouteFlapDamping, FlapDampingConfig


@dataclass
class BGPSessionConfig:
    """Configuration for a BGP session"""
    # Required fields (no defaults)
    local_as: int
    local_router_id: str
    local_ip: str
    peer_as: int
    peer_ip: str

    # Optional fields (with defaults)
    local_port: int = BGP_PORT
    peer_port: int = BGP_PORT
    peer_router_id: Optional[str] = None  # Learned from OPEN

    hold_time: int = 180
    keepalive_time: int = 60
    connect_retry_time: int = 120

    passive: bool = False  # True for passive/listen mode

    # Mesh peering (NetClaw-to-NetClaw via ngrok)
    accept_any_source: bool = False  # Accept connections from any IP (match by AS from OPEN)
    hostname: bool = False  # True if peer_ip is a hostname (e.g. ngrok endpoint)

    # Route Reflection
    route_reflector_client: bool = False
    cluster_id: Optional[str] = None

    # Policy
    import_policy: Optional[str] = None
    export_policy: Optional[str] = None

    # Route Flap Damping
    enable_flap_damping: bool = False
    flap_damping_config: Optional[FlapDampingConfig] = None

    # Graceful Restart
    enable_graceful_restart: bool = False
    graceful_restart_time: int = 120  # Restart time in seconds

    # RPKI Validation
    enable_rpki_validation: bool = False
    rpki_reject_invalid: bool = False  # Reject invalid routes

    # FlowSpec
    enable_flowspec: bool = False


class BGPSession:
    """
    BGP Session Manager

    Manages a single BGP peer session including TCP transport,
    FSM, RIBs, and message processing.
    """

    def __init__(self, config: BGPSessionConfig):
        """
        Initialize BGP session

        Args:
            config: Session configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"BGPSession[{config.peer_ip}]")

        # Session identifiers
        self.session_id = f"{config.local_ip}:{config.local_port}-{config.peer_ip}:{config.peer_port}"
        self.peer_id = config.peer_router_id or config.peer_ip

        # TCP transport
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connection_task: Optional[asyncio.Task] = None

        # FSM
        self.fsm = BGPFSM(
            peer_id=self.peer_id,
            local_as=config.local_as,
            peer_as=config.peer_as,
            hold_time=config.hold_time,
            connect_retry_time=config.connect_retry_time
        )

        # Wire FSM callbacks
        self.fsm.send_message_callback = self._send_message
        self.fsm.on_state_change = self._on_fsm_state_change
        self.fsm.on_send_open = self._on_fsm_send_open
        self.fsm.on_send_keepalive = self._on_fsm_send_keepalive
        self.fsm.on_send_notification = self._on_fsm_send_notification
        self.fsm.on_tcp_connect = self._on_fsm_tcp_connect
        self.fsm.on_tcp_disconnect = self._on_fsm_tcp_disconnect

        # Capabilities
        self.capabilities = CapabilityManager(config.local_as)

        # RIBs
        self.adj_rib_in = AdjRIBIn()
        self.adj_rib_out = AdjRIBOut()
        self.loc_rib: Optional[LocRIB] = None  # Shared Loc-RIB (set by BGPAgent)

        # Route Flap Damping
        self.flap_damping: Optional[RouteFlapDamping] = None
        if config.enable_flap_damping:
            self.flap_damping = RouteFlapDamping(config.flap_damping_config)
            self.logger.info("Route flap damping ENABLED")

        # Graceful Restart (set by BGPAgent)
        self.graceful_restart_manager: Optional['GracefulRestartManager'] = None

        # RPKI Validator (set by BGPAgent)
        self.rpki_validator: Optional['RPKIValidator'] = None

        # FlowSpec Manager (set by BGPAgent)
        self.flowspec_manager: Optional['FlowspecManager'] = None
        if config.enable_flowspec:
            self.logger.info("BGP FlowSpec ENABLED (requires SAFI 133/134 support)")

        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'updates_sent': 0,
            'updates_received': 0,
            'routes_received': 0,
            'routes_advertised': 0,
            'last_error': None,
            'uptime': 0,
            'established_time': None,
            # Individual message type counters for Prometheus
            'open_sent': 0,
            'open_recv': 0,
            'update_sent': 0,
            'update_recv': 0,
            'keepalive_sent': 0,
            'keepalive_recv': 0,
            'notification_sent': 0,
            'notification_recv': 0
        }

        # Pre-read OPEN message for mesh peer identification (set by BGPAgent)
        self._pending_open: Optional[BGPOpen] = None

        # Tasks
        self.message_reader_task: Optional[asyncio.Task] = None
        self.running = False

    async def start(self) -> None:
        """Start BGP session"""
        self.logger.info(f"Starting BGP session to {self.config.peer_ip}")
        self.running = True

        # Initialize capabilities
        self._configure_capabilities()

        # Start FSM with appropriate event
        if self.config.passive:
            self.logger.info("Passive mode - waiting for incoming connection")
            # Start FSM in passive mode
            await self.fsm.process_event(BGPEvent.ManualStart_with_PassiveTcpEstablishment)
        else:
            # Active mode - initiate connection
            self.logger.info("Active mode - initiating connection")
            await self.fsm.process_event(BGPEvent.ManualStart)

    async def stop(self, error_code: Optional[int] = None, error_subcode: Optional[int] = None,
                   error_data: bytes = b'') -> None:
        """
        Stop BGP session

        Args:
            error_code: Optional NOTIFICATION error code
            error_subcode: Optional NOTIFICATION error subcode
            error_data: Optional error data
        """
        self.logger.info(f"Stopping BGP session to {self.config.peer_ip}")
        self.running = False

        # Send NOTIFICATION if error specified
        if error_code is not None:
            try:
                notification = BGPNotification(error_code, error_subcode, error_data)
                await self._send_message(notification)
            except Exception as e:
                self.logger.error(f"Error sending NOTIFICATION: {e}")

        # Stop FSM
        await self.fsm.stop()

        # Close connection
        await self._close_connection()

        # Cancel tasks
        if self.message_reader_task and not self.message_reader_task.done():
            self.message_reader_task.cancel()
        if self.connection_task and not self.connection_task.done():
            self.connection_task.cancel()

    async def connect(self) -> bool:
        """
        Establish TCP connection to peer (active mode)

        Returns:
            True if connection successful
        """
        try:
            self.logger.info(f"Connecting to {self.config.peer_ip}:{self.config.peer_port}")

            # Open TCP connection
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.config.peer_ip, self.config.peer_port),
                timeout=30.0
            )

            self.logger.info(f"TCP connection established to {self.config.peer_ip}")

            # Set DSCP for BGP traffic - RFC 4594 Network Control (CS6)
            # DSCP CS6 = 48, TOS byte = DSCP << 2 = 192 (0xC0)
            try:
                import socket
                sock = self.writer.get_extra_info('socket')
                if sock:
                    tos_byte = 192  # CS6 for Network Control (BGP)
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, tos_byte)
                    self.logger.info(f"[QoS] Set BGP socket TOS=0x{tos_byte:02X} (DSCP CS6 - Network Control)")
            except Exception as tos_err:
                self.logger.warning(f"[QoS] Could not set TOS on BGP socket: {tos_err}")

            # Start message reader
            self.message_reader_task = asyncio.create_task(self._message_reader())

            # Notify FSM
            await self.fsm.process_event(BGPEvent.TcpConnectionConfirmed)

            return True

        except asyncio.TimeoutError:
            self.logger.error(f"Connection timeout to {self.config.peer_ip}")
            await self.fsm.process_event(BGPEvent.TcpConnectionFails)
            return False
        except Exception as e:
            self.logger.error(f"Connection failed to {self.config.peer_ip}: {e}")
            await self.fsm.process_event(BGPEvent.TcpConnectionFails)
            return False

    async def accept_connection(self, reader: asyncio.StreamReader,
                               writer: asyncio.StreamWriter,
                               is_collision: bool = False) -> None:
        """
        Accept incoming TCP connection (passive mode or collision resolution)

        This method handles both passive mode connections and connection collision
        scenarios where an incoming connection replaces an outgoing attempt.

        Args:
            reader: Stream reader
            writer: Stream writer
            is_collision: True if this is a collision resolution (need to re-send OPEN)
        """
        self.logger.info(f"Accepted connection from {self.config.peer_ip}")

        # Track if we were in an advanced state (collision case)
        was_in_open_state = self.fsm.state in (STATE_OPENSENT, STATE_OPENCONFIRM)

        # Clean up any existing connection (collision resolution case)
        if self.message_reader_task and not self.message_reader_task.done():
            self.logger.debug("Canceling existing message reader task (collision resolution)")
            self.message_reader_task.cancel()
            try:
                await self.message_reader_task
            except asyncio.CancelledError:
                pass

        if self.writer:
            self.logger.debug("Closing existing writer (collision resolution)")
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except (ConnectionError, OSError, asyncio.CancelledError) as e:
                self.logger.debug(f"Error closing writer during collision resolution: {e}")

        # Accept the new connection
        self.reader = reader
        self.writer = writer

        # Set DSCP for BGP traffic - RFC 4594 Network Control (CS6)
        try:
            import socket
            sock = self.writer.get_extra_info('socket')
            if sock:
                tos_byte = 192  # CS6 for Network Control (BGP)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, tos_byte)
                self.logger.info(f"[QoS] Set accepted BGP socket TOS=0x{tos_byte:02X} (DSCP CS6)")
        except Exception as tos_err:
            self.logger.warning(f"[QoS] Could not set TOS on accepted BGP socket: {tos_err}")

        # Start message reader
        self.message_reader_task = asyncio.create_task(self._message_reader())

        # Handle collision case: we need to re-send OPEN on the new connection
        # because the peer never received our OPEN (it was on the old connection)
        if is_collision and was_in_open_state:
            self.logger.info(f"Collision resolution: re-sending OPEN on new connection")
            # CRITICAL: Stop all timers from the old connection before resetting state
            # This prevents old keepalive/hold timers from trying to use closed writer
            self.logger.debug("Stopping all FSM timers before collision resolution")
            self.fsm._stop_all_timers()
            # Reset FSM to Connect state so TcpConnectionConfirmed triggers OPEN send
            self.fsm.state = STATE_CONNECT
            await self.fsm.process_event(BGPEvent.TcpConnectionConfirmed)
        else:
            # Normal passive accept
            await self.fsm.process_event(BGPEvent.TcpConnectionConfirmed)

        # Process pre-read OPEN message if set (mesh peer identified by BGPAgent)
        # The agent already consumed the OPEN from the wire during identification,
        # so we replay it directly into _process_open instead of reading from stream.
        if self._pending_open is not None:
            self.logger.info("Processing pre-read OPEN from mesh peer identification")
            pending = self._pending_open
            self._pending_open = None
            # Small delay to let FSM settle into OpenSent after sending our OPEN
            await asyncio.sleep(0.1)
            await self._process_open(pending)

    async def _close_connection(self) -> None:
        """Close TCP connection"""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                self.logger.error(f"Error closing connection: {e}")
            finally:
                self.writer = None
                self.reader = None

    async def _send_message(self, message: BGPMessage) -> None:
        """
        Send BGP message over TCP

        Args:
            message: BGP message to send
        """
        msg_name = MESSAGE_TYPE_NAMES.get(message.msg_type, f"UNKNOWN({message.msg_type})")

        if not self.writer:
            self.logger.error(f"Cannot send {msg_name} - writer is None")
            return

        try:
            # Check if writer is closing
            if self.writer.is_closing():
                self.logger.error(f"Cannot send {msg_name} - writer is closing")
                return

            # Encode message
            data = message.encode()

            # Enhanced debug logging
            self.logger.debug(f"Sending {msg_name} ({len(data)} bytes)")
            self.logger.debug(f"Message hex dump: {data.hex()}")

            # Check connection before write
            try:
                sock = self.writer.get_extra_info('socket')
                if sock:
                    self.logger.debug(f"Socket state: connected={sock.fileno() != -1}")
            except Exception as e:
                self.logger.debug(f"Could not get socket info: {e}")

            # Send over TCP
            self.logger.debug(f"Writing {len(data)} bytes to stream...")
            self.writer.write(data)

            self.logger.debug(f"Draining writer buffer...")
            await self.writer.drain()

            self.logger.debug(f"Successfully sent {msg_name}")

            # Update statistics
            self.stats['messages_sent'] += 1
            if message.msg_type == MSG_UPDATE:
                self.stats['updates_sent'] += 1
                self.stats['update_sent'] += 1
            elif message.msg_type == MSG_OPEN:
                self.stats['open_sent'] += 1
            elif message.msg_type == MSG_KEEPALIVE:
                self.stats['keepalive_sent'] += 1
            elif message.msg_type == MSG_NOTIFICATION:
                self.stats['notification_sent'] += 1

        except ConnectionResetError as e:
            self.logger.error(f"Connection reset while sending {msg_name}: {e}")
            await self.fsm.process_event(BGPEvent.TcpConnectionFails)
        except BrokenPipeError as e:
            self.logger.error(f"Broken pipe while sending {msg_name}: {e}")
            await self.fsm.process_event(BGPEvent.TcpConnectionFails)
        except Exception as e:
            self.logger.error(f"Error sending {msg_name}: {type(e).__name__}: {e}", exc_info=True)
            await self.fsm.process_event(BGPEvent.TcpConnectionFails)

    async def _message_reader(self) -> None:
        """Read and process BGP messages from TCP stream"""
        self.logger.info("Message reader started")

        try:
            while self.running and self.reader:
                # Check EOF before reading
                if self.reader.at_eof():
                    self.logger.warning("Reader at EOF - connection closed by peer")
                    break

                # Log before attempting to read
                self.logger.debug("Waiting for BGP message header (19 bytes)...")

                # Read BGP message header (19 bytes)
                try:
                    header = await self.reader.readexactly(BGP_HEADER_SIZE)
                    self.logger.debug(f"Received header: {header.hex()}")
                except asyncio.IncompleteReadError as e:
                    self.logger.warning(f"Incomplete read for header: expected {BGP_HEADER_SIZE} bytes, got {len(e.partial)} bytes")
                    self.logger.warning("Connection closed by peer while reading header")
                    break

                # Parse header
                marker, length, msg_type = struct.unpack('!16sHB', header)

                msg_name = MESSAGE_TYPE_NAMES.get(msg_type, f"UNKNOWN({msg_type})")
                self.logger.debug(f"Header parsed: type={msg_name}, length={length}")

                # Validate marker
                if marker != BGP_MARKER:
                    self.logger.error(f"Invalid BGP marker: {marker.hex()}")
                    await self.fsm.process_event(BGPEvent.BGPHeaderErr)
                    return

                # Validate length
                if length < BGP_HEADER_SIZE or length > BGP_MAX_MESSAGE_SIZE:
                    self.logger.error(f"Invalid message length: {length} (must be {BGP_HEADER_SIZE}-{BGP_MAX_MESSAGE_SIZE})")
                    await self.fsm.process_event(BGPEvent.BGPHeaderErr)
                    return

                # Read message body
                body_length = length - BGP_HEADER_SIZE
                if body_length > 0:
                    self.logger.debug(f"Reading message body ({body_length} bytes)...")
                    try:
                        body = await self.reader.readexactly(body_length)
                        self.logger.debug(f"Received body: {body.hex()}")
                    except asyncio.IncompleteReadError as e:
                        self.logger.warning(f"Incomplete read for body: expected {body_length} bytes, got {len(e.partial)} bytes")
                        self.logger.warning("Connection closed by peer while reading body")
                        break
                else:
                    body = b''

                # Decode message
                full_message = header + body
                self.logger.debug(f"Decoding {msg_name} message ({len(full_message)} bytes)")

                message = BGPMessage.decode(full_message)

                if message:
                    self.logger.debug(f"Successfully decoded {msg_name}")

                    # Update statistics
                    self.stats['messages_received'] += 1

                    # Process message
                    await self._process_message(message)
                else:
                    self.logger.error(f"Failed to decode {msg_name} message")
                    self.logger.error(f"Message hex: {full_message.hex()}")
                    await self.fsm.process_event(BGPEvent.BGPHeaderErr)
                    return

        except asyncio.IncompleteReadError as e:
            self.logger.info(f"Connection closed by peer (IncompleteReadError): expected={e.expected}, partial={len(e.partial)}")
            await self.fsm.process_event(BGPEvent.TcpConnectionFails)
        except ConnectionResetError as e:
            self.logger.warning(f"Connection reset by peer: {e}")
            await self.fsm.process_event(BGPEvent.TcpConnectionFails)
        except Exception as e:
            self.logger.error(f"Error reading message: {type(e).__name__}: {e}", exc_info=True)
            await self.fsm.process_event(BGPEvent.TcpConnectionFails)
        finally:
            self.logger.info("Message reader stopped")

    async def _process_message(self, message: BGPMessage) -> None:
        """
        Process received BGP message

        Args:
            message: Received BGP message
        """
        msg_type = message.msg_type

        # QoS Ingress Trust - trust BGP traffic from peer (TCP doesn't expose DSCP to app)
        try:
            import os
            from agentic.protocols.qos import get_qos_manager
            qos_agent_id = os.environ.get("ASI_AGENT_ID", "local")
            qos_mgr = get_qos_manager(qos_agent_id)
            if qos_mgr and qos_mgr.enabled:
                qos_mgr.trust_ingress_protocol("bgp", "eth0")
        except ImportError:
            pass  # QoS module not available
        except Exception as qos_err:
            self.logger.debug(f"[QoS] BGP ingress trust error: {qos_err}")

        # Track individual message type counters for Prometheus
        if msg_type == MSG_OPEN:
            self.stats['open_recv'] += 1
            await self._process_open(message)
        elif msg_type == MSG_UPDATE:
            self.stats['update_recv'] += 1
            await self._process_update(message)
        elif msg_type == MSG_KEEPALIVE:
            self.stats['keepalive_recv'] += 1
            await self._process_keepalive(message)
        elif msg_type == MSG_NOTIFICATION:
            self.stats['notification_recv'] += 1
            await self._process_notification(message)
        elif msg_type == MSG_ROUTE_REFRESH:
            await self._process_route_refresh(message)
        else:
            self.logger.warning(f"Unknown message type: {msg_type}")

    async def _process_open(self, message: BGPOpen) -> None:
        """Process OPEN message"""
        self.logger.info(f"Received OPEN: AS={message.my_as}, ID={message.bgp_identifier}, "
                        f"HoldTime={message.hold_time}")

        # Store peer router ID
        self.config.peer_router_id = message.bgp_identifier
        self.peer_id = message.bgp_identifier

        # Negotiate hold time (use minimum of local and peer)
        negotiated_hold_time = self.fsm.negotiate_hold_time(message.hold_time)
        self.logger.info(f"Negotiated hold time: {negotiated_hold_time} seconds "
                        f"(local={self.config.hold_time}, peer={message.hold_time})")

        # Parse peer capabilities
        peer_caps = {}
        for cap in message.capabilities:
            peer_caps[cap.code] = cap.value
        self.capabilities.set_peer_capabilities(peer_caps)

        self.logger.info(f"Peer capabilities: {list(peer_caps.keys())}")

        # Notify FSM (will trigger KEEPALIVE send via callback)
        # The FSM will automatically send KEEPALIVE and transition to OpenConfirm
        await self.fsm.process_event(BGPEvent.BGPOpen)

    async def _process_update(self, message: BGPUpdate) -> None:
        """Process UPDATE message"""
        self.stats['updates_received'] += 1

        # Check for End-of-RIB marker (RFC 4724)
        # IPv4: UPDATE with no withdrawn routes, no NLRI, and empty path attributes
        is_end_of_rib_ipv4 = (
            not message.withdrawn_routes and
            not message.nlri and
            not message.path_attributes
        )

        if is_end_of_rib_ipv4:
            self.logger.info(f"Received End-of-RIB marker for IPv4 unicast from {self.config.peer_ip}")
            if self.graceful_restart_manager and self.config.enable_graceful_restart:
                stale_routes = self.graceful_restart_manager.handle_end_of_rib(
                    self.config.peer_ip, AFI_IPV4, SAFI_UNICAST
                )
                # Remove stale routes that weren't refreshed
                for prefix in stale_routes:
                    self.adj_rib_in.remove_route(prefix, self.peer_id)
                    self.logger.debug(f"Removed stale route {prefix}")
            return

        # Process IPv4 withdrawn routes
        if message.withdrawn_routes:
            self.logger.debug(f"IPv4 withdrawn routes: {len(message.withdrawn_routes)}")
            for prefix in message.withdrawn_routes:
                # Track flap if damping enabled
                if self.flap_damping:
                    self.flap_damping.route_withdrawn(prefix)

                self.adj_rib_in.remove_route(prefix, self.peer_id)
                self.stats['routes_received'] -= 1

        # Process IPv4 advertised routes
        if message.nlri:
            self.logger.debug(f"IPv4 advertised routes: {len(message.nlri)}, "
                            f"attributes: {len(message.path_attributes)}")

            # Build route with path attributes
            for prefix in message.nlri:
                # Check flap damping suppression
                if self.flap_damping:
                    is_suppressed = self.flap_damping.route_announced(prefix, attribute_changed=False)
                    if is_suppressed:
                        self.logger.warning(f"Route {prefix} is SUPPRESSED by flap damping - not installing")
                        continue

                route = self._build_route_from_update(prefix, message.path_attributes, AFI_IPV4)
                if route:
                    # RPKI validation
                    if self.rpki_validator and self.config.enable_rpki_validation:
                        origin_as = self._get_origin_as(route)
                        if origin_as is not None:
                            validation_state = self.rpki_validator.validate_route(
                                route.prefix.split('/')[0],
                                route.prefix_len,
                                origin_as
                            )
                            route.validation_state = validation_state

                            # Reject invalid routes if configured
                            if self.config.rpki_reject_invalid and validation_state == 1:  # INVALID
                                self.logger.warning(f"REJECTING RPKI-invalid route {prefix} from AS{origin_as}")
                                continue

                    self.adj_rib_in.add_route(route)
                    self.stats['routes_received'] += 1

                    # Mark route as refreshed if in graceful restart
                    if self.graceful_restart_manager and self.config.enable_graceful_restart:
                        self.graceful_restart_manager.route_refreshed(self.config.peer_ip, prefix)

        # Process MP_REACH_NLRI for IPv6 (and other address families)
        if ATTR_MP_REACH_NLRI in message.path_attributes:
            mp_reach = message.path_attributes[ATTR_MP_REACH_NLRI]
            if mp_reach.afi == AFI_IPV6 and mp_reach.safi == SAFI_UNICAST:
                self.logger.info(f"IPv6 MP_REACH_NLRI: {len(mp_reach.nlri)} routes, next_hop={mp_reach.next_hop}")

                # Add next hop to attributes for route building
                modified_attrs = message.path_attributes.copy()

                for prefix in mp_reach.nlri:
                    # Check flap damping suppression
                    if self.flap_damping:
                        is_suppressed = self.flap_damping.route_announced(prefix, attribute_changed=False)
                        if is_suppressed:
                            self.logger.warning(f"IPv6 route {prefix} is SUPPRESSED by flap damping - not installing")
                            continue

                    route = self._build_route_from_update(prefix, modified_attrs, AFI_IPV6, mp_reach.next_hop)
                    if route:
                        # RPKI validation
                        if self.rpki_validator and self.config.enable_rpki_validation:
                            origin_as = self._get_origin_as(route)
                            if origin_as is not None:
                                validation_state = self.rpki_validator.validate_route(
                                    route.prefix.split('/')[0],
                                    route.prefix_len,
                                    origin_as
                                )
                                route.validation_state = validation_state

                                # Reject invalid routes if configured
                                if self.config.rpki_reject_invalid and validation_state == 1:  # INVALID
                                    self.logger.warning(f"REJECTING RPKI-invalid IPv6 route {prefix} from AS{origin_as}")
                                    continue

                        self.adj_rib_in.add_route(route)
                        self.stats['routes_received'] += 1
                        self.logger.info(f"Added IPv6 route: {prefix} via {mp_reach.next_hop}")

                        # Mark route as refreshed if in graceful restart
                        if self.graceful_restart_manager and self.config.enable_graceful_restart:
                            self.graceful_restart_manager.route_refreshed(self.config.peer_ip, prefix)

        # Process MP_UNREACH_NLRI for IPv6 withdrawals
        if ATTR_MP_UNREACH_NLRI in message.path_attributes:
            mp_unreach = message.path_attributes[ATTR_MP_UNREACH_NLRI]
            if mp_unreach.afi == AFI_IPV6 and mp_unreach.safi == SAFI_UNICAST:
                self.logger.info(f"IPv6 MP_UNREACH_NLRI: {len(mp_unreach.withdrawn_routes)} withdrawn")

                for prefix in mp_unreach.withdrawn_routes:
                    # Track flap if damping enabled
                    if self.flap_damping:
                        self.flap_damping.route_withdrawn(prefix)

                    self.adj_rib_in.remove_route(prefix, self.peer_id)
                    self.stats['routes_received'] -= 1
                    self.logger.info(f"Withdrew IPv6 route: {prefix}")

    async def _process_keepalive(self, message: BGPKeepalive) -> None:
        """Process KEEPALIVE message"""
        self.logger.debug("Received KEEPALIVE")
        await self.fsm.process_event(BGPEvent.KeepAliveMsg)

    async def _process_notification(self, message: BGPNotification) -> None:
        """Process NOTIFICATION message"""
        error_name = ERROR_CODE_NAMES.get(message.error_code, f"UNKNOWN({message.error_code})")
        self.logger.warning(f"Received NOTIFICATION: {error_name} "
                          f"(code={message.error_code}, subcode={message.error_subcode})")

        self.stats['last_error'] = f"{error_name} ({message.error_code}/{message.error_subcode})"

        await self.fsm.process_event(BGPEvent.NotifMsg)

    async def _process_route_refresh(self, message) -> None:
        """Process ROUTE-REFRESH message"""
        self.logger.info("Received ROUTE-REFRESH - re-advertising routes")
        # Re-send all routes in Adj-RIB-Out
        # This will be implemented when we add the advertisement logic

    def _build_route_from_update(self, prefix: str, attributes: Dict[int, Any],
                                 afi: int = AFI_IPV4, mp_next_hop: Optional[str] = None) -> Optional[BGPRoute]:
        """
        Build BGPRoute from UPDATE message

        Args:
            prefix: Prefix string
            attributes: Path attributes dictionary (type_code -> value)
            afi: Address Family Identifier (AFI_IPV4 or AFI_IPV6)
            mp_next_hop: Multiprotocol next hop (for IPv6)

        Returns:
            BGPRoute or None
        """
        try:
            # Parse prefix
            if '/' in prefix:
                prefix_str, prefix_len_str = prefix.split('/')
                prefix_len = int(prefix_len_str)
            else:
                prefix_str = prefix
                prefix_len = 32 if afi == AFI_IPV4 else 128

            # For IPv6, store the next hop from MP_REACH_NLRI in path attributes
            # so it can be retrieved later for route installation
            route_attributes = attributes.copy()
            if afi == AFI_IPV6 and mp_next_hop:
                # Store IPv6 next hop as a pseudo-attribute for easy access
                route_attributes['_ipv6_next_hop'] = mp_next_hop

            # Create route
            route = BGPRoute(
                prefix=prefix,
                prefix_len=prefix_len,
                path_attributes=route_attributes,
                peer_id=self.peer_id,
                peer_ip=self.config.peer_ip,
                timestamp=time.time(),
                afi=afi,
                safi=SAFI_UNICAST
            )

            return route

        except Exception as e:
            self.logger.error(f"Error building route from UPDATE: {e}", exc_info=True)
            return None

    def _configure_capabilities(self) -> None:
        """Configure local capabilities"""
        # Enable IPv4 unicast capability (required for route exchange with FRR)
        self.capabilities.enable_multiprotocol(AFI_IPV4, SAFI_UNICAST)

        # Enable additional standard capabilities
        self.capabilities.enable_four_octet_as()
        self.capabilities.enable_route_refresh()

        # Enable IPv6 unicast for dual-stack support
        self.capabilities.enable_multiprotocol(AFI_IPV6, SAFI_UNICAST)

        # Enable graceful restart if configured
        if self.config.enable_graceful_restart:
            self.capabilities.enable_graceful_restart(
                restart_time=self.config.graceful_restart_time,
                restart_state=False
            )
            self.logger.info(f"Graceful restart enabled (restart_time={self.config.graceful_restart_time}s)")

        self.logger.info(f"Configured {len(self.capabilities.local_capabilities)} capabilities: {list(self.capabilities.local_capabilities.keys())}")

    async def _on_fsm_state_change(self, old_state: int, new_state: int) -> None:
        """
        Handle FSM state changes

        Args:
            old_state: Previous state
            new_state: New state
        """
        from .fsm import FSM_STATE_NAMES

        self.logger.info(f"FSM state: {FSM_STATE_NAMES[old_state]} → {FSM_STATE_NAMES[new_state]}")

        # Handle Established state
        if new_state == STATE_ESTABLISHED and old_state != STATE_ESTABLISHED:
            self.stats['established_time'] = time.time()
            self.logger.info(f"BGP session ESTABLISHED with {self.config.peer_ip}")

            # Notify graceful restart manager
            if self.graceful_restart_manager and self.config.enable_graceful_restart:
                supports_gr = self.capabilities.supports_graceful_restart()
                self.graceful_restart_manager.peer_session_up(self.config.peer_ip, supports_gr)

            # Call on_established callback if registered
            if hasattr(self, 'on_established') and self.on_established:
                self.on_established()

        # Handle connection loss
        if old_state == STATE_ESTABLISHED and new_state != STATE_ESTABLISHED:
            if self.stats['established_time']:
                uptime = time.time() - self.stats['established_time']
                self.stats['uptime'] += uptime
                self.stats['established_time'] = None
            self.logger.warning(f"BGP session DOWN with {self.config.peer_ip}")

            # Handle graceful restart - mark routes as stale
            if self.graceful_restart_manager and self.config.enable_graceful_restart:
                # Get all routes from this peer's Adj-RIB-In
                routes = {}
                for prefix in self.adj_rib_in.get_prefixes():
                    prefix_routes = self.adj_rib_in.get_routes(prefix)
                    for route in prefix_routes:
                        if route.source == self.peer_id:
                            routes[prefix] = route

                # Notify graceful restart manager
                self.graceful_restart_manager.peer_session_down(
                    self.config.peer_ip,
                    routes,
                    restart_time=self.config.graceful_restart_time
                )

    def _on_fsm_send_open(self) -> None:
        """FSM callback to send OPEN message"""
        asyncio.create_task(self._send_open())

    def _on_fsm_send_keepalive(self) -> None:
        """FSM callback to send KEEPALIVE message"""
        asyncio.create_task(self._send_keepalive())

    def _on_fsm_send_notification(self, error_code: int, error_subcode: int) -> None:
        """FSM callback to send NOTIFICATION message"""
        asyncio.create_task(self._send_notification(error_code, error_subcode))

    def _on_fsm_tcp_connect(self) -> None:
        """FSM callback to initiate TCP connection"""
        asyncio.create_task(self.connect())

    def _on_fsm_tcp_disconnect(self) -> None:
        """FSM callback to close TCP connection"""
        asyncio.create_task(self._disconnect())

    async def _send_open(self) -> None:
        """Send OPEN message"""
        open_msg = BGPOpen(
            version=BGP_VERSION,
            my_as=self.config.local_as,
            hold_time=self.config.hold_time,
            bgp_identifier=self.config.local_router_id,
            capabilities=build_capability_list(self.capabilities)
        )
        await self._send_message(open_msg)

    async def _send_keepalive(self) -> None:
        """Send KEEPALIVE message"""
        keepalive_msg = BGPKeepalive()
        await self._send_message(keepalive_msg)

    async def _send_notification(self, error_code: int, error_subcode: int, data: bytes = b'') -> None:
        """Send NOTIFICATION message"""
        notif_msg = BGPNotification(
            error_code=error_code,
            error_subcode=error_subcode,
            data=data
        )
        await self._send_message(notif_msg)

    async def _disconnect(self) -> None:
        """Close TCP connection"""
        await self._close_connection()

    def _get_origin_as(self, route: 'BGPRoute') -> Optional[int]:
        """
        Extract origin AS from route's AS_PATH attribute

        Args:
            route: BGP route

        Returns:
            Origin AS number or None
        """
        if ATTR_AS_PATH not in route.path_attributes:
            return None

        as_path_attr = route.path_attributes[ATTR_AS_PATH]
        if hasattr(as_path_attr, 'as_path') and as_path_attr.as_path:
            # AS_PATH is a list of AS numbers, origin is the last one
            return as_path_attr.as_path[-1]

        return None

    def is_established(self) -> bool:
        """Check if session is in Established state"""
        return self.fsm.state == STATE_ESTABLISHED

    def get_statistics(self) -> Dict:
        """
        Get session statistics

        Returns:
            Dictionary with statistics
        """
        stats = self.stats.copy()

        # Add current uptime if established
        if self.stats['established_time']:
            stats['current_uptime'] = time.time() - self.stats['established_time']

        # Add FSM state
        from .fsm import FSM_STATE_NAMES
        stats['fsm_state'] = FSM_STATE_NAMES.get(self.fsm.state, f"UNKNOWN({self.fsm.state})")

        # Add RIB statistics
        stats['adj_rib_in_routes'] = self.adj_rib_in.size()
        stats['adj_rib_out_routes'] = self.adj_rib_out.size()

        return stats
