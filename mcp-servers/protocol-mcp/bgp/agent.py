"""
BGP Agent - Main Orchestrator

The BGPAgent is the top-level orchestrator that manages:
- Multiple BGP sessions (peers)
- Shared Loc-RIB (routing table)
- Best path selection across all peers
- Route advertisement to peers
- Policy engine integration
- Route reflection (if configured)

The agent runs the BGP decision process and coordinates route exchange
between all peers.
"""

import asyncio
import logging
import struct
from typing import Dict, List, Optional, Set, Tuple
from ipaddress import ip_address

from .constants import *
from .session import BGPSession, BGPSessionConfig
from .rib import LocRIB, BGPRoute
from .path_selection import BestPathSelector
from .policy import PolicyEngine, Policy
from .route_reflection import RouteReflector
from .graceful_restart import GracefulRestartManager
from .rpki import RPKIValidator
from .flowspec import FlowspecManager
from .messages import BGPUpdate, BGPNotification, BGPMessage, BGPOpen
from .attributes import *


class BGPAgent:
    """
    BGP Agent - Main orchestrator for BGP speaker

    Manages multiple BGP sessions, maintains Loc-RIB,
    runs decision process, and coordinates route advertisement.
    """

    def __init__(self, local_as: int, router_id: str, listen_ip: str = "0.0.0.0",
                 listen_port: int = BGP_PORT, kernel_route_manager=None):
        """
        Initialize BGP agent

        Args:
            local_as: Local AS number
            router_id: Local router ID (IPv4 address format)
            listen_ip: IP address to listen on for passive connections
            listen_port: TCP port to listen on
            kernel_route_manager: Optional kernel route manager for installing routes
        """
        self.local_as = local_as
        self.router_id = router_id
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.kernel_route_manager = kernel_route_manager

        self.logger = logging.getLogger(f"BGPAgent[AS{local_as}]")

        # Sessions
        self.sessions: Dict[str, BGPSession] = {}  # Key: peer_ip (or synthetic "mesh-as{N}" for mesh peers)
        self.mesh_sessions: Dict[int, BGPSession] = {}  # Key: peer_as (for accept_any_source peers)

        # Shared Loc-RIB (best routes)
        self.loc_rib = LocRIB()

        # Best path selector
        self.best_path_selector = BestPathSelector(local_as, router_id)

        # Policy engine
        self.policy_engine = PolicyEngine()

        # Route reflector (optional)
        self.route_reflector: Optional[RouteReflector] = None

        # Graceful restart manager
        self.graceful_restart = GracefulRestartManager(router_id)

        # RPKI validator
        self.rpki_validator = RPKIValidator()

        # FlowSpec manager
        self.flowspec_manager = FlowspecManager()

        # TCP listener
        self.server: Optional[asyncio.Server] = None

        # Decision process task
        self.decision_process_task: Optional[asyncio.Task] = None
        self.decision_process_interval: float = 5.0  # Run every 5 seconds

        # Running state
        self.running = False

    async def start(self) -> None:
        """Start BGP agent"""
        self.logger.info(f"Starting BGP agent AS{self.local_as} Router-ID {self.router_id}")
        self.running = True

        # Start TCP listener for passive connections
        await self._start_listener()

        # Start decision process
        self.decision_process_task = asyncio.create_task(self._decision_process_loop())

        self.logger.info("BGP agent started")

    async def stop(self) -> None:
        """Stop BGP agent"""
        self.logger.info("Stopping BGP agent")
        self.running = False

        # Stop all sessions
        for session in self.sessions.values():
            await session.stop()

        # Stop listener
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        # Stop decision process
        if self.decision_process_task and not self.decision_process_task.done():
            self.decision_process_task.cancel()

        self.logger.info("BGP agent stopped")

    async def _start_listener(self) -> None:
        """Start TCP listener for incoming BGP connections"""
        try:
            self.server = await asyncio.start_server(
                self._handle_incoming_connection,
                self.listen_ip,
                self.listen_port
            )

            addr = self.server.sockets[0].getsockname()
            self.logger.info(f"Listening for BGP connections on {addr[0]}:{addr[1]}")

        except Exception as e:
            self.logger.warning(f"Failed to start TCP listener on port {self.listen_port}: {e}")
            self.logger.warning("Continuing in active-only mode (will initiate connections to peers)")
            # Don't raise — allow the speaker to run in active-only mode

    async def _read_open_message(self, reader: asyncio.StreamReader,
                                timeout: float = 30.0) -> Optional[BGPOpen]:
        """
        Read and parse a BGP OPEN message from a raw TCP stream.

        Used for mesh peer identification: when an inbound connection doesn't
        match any configured peer IP, we read the OPEN to extract the AS number
        and router-ID, then match against mesh_sessions.

        Args:
            reader: Stream reader
            timeout: Read timeout in seconds

        Returns:
            BGPOpen message or None if invalid/timeout
        """
        try:
            # Read 19-byte BGP header
            header = await asyncio.wait_for(reader.readexactly(BGP_HEADER_SIZE), timeout=timeout)
            marker = header[0:16]
            length = struct.unpack('!H', header[16:18])[0]
            msg_type = header[18]

            # Validate: must be OPEN (type 1) with valid marker
            if marker != b'\xff' * 16:
                self.logger.warning("Mesh OPEN read: invalid marker")
                return None
            if msg_type != MSG_OPEN:
                self.logger.warning(f"Mesh OPEN read: expected OPEN (1), got type {msg_type}")
                return None

            # Read body
            body_length = length - BGP_HEADER_SIZE
            if body_length > 0:
                body = await asyncio.wait_for(reader.readexactly(body_length), timeout=timeout)
            else:
                body = b''

            # Decode full message
            full_message = header + body
            open_msg = BGPOpen.decode(full_message)
            if open_msg:
                self.logger.info(f"Mesh OPEN read: AS={open_msg.my_as}, ID={open_msg.bgp_identifier}")
            return open_msg

        except asyncio.TimeoutError:
            self.logger.warning("Mesh OPEN read: timeout waiting for OPEN message")
            return None
        except asyncio.IncompleteReadError:
            self.logger.warning("Mesh OPEN read: connection closed before OPEN received")
            return None
        except Exception as e:
            self.logger.error(f"Mesh OPEN read error: {type(e).__name__}: {e}")
            return None

    async def _handle_incoming_connection(self, reader: asyncio.StreamReader,
                                         writer: asyncio.StreamWriter) -> None:
        """
        Handle incoming TCP connection

        Per RFC 4271 Section 6.8, when a BGP speaker receives an incoming connection
        for a peer it's actively connecting to, it should handle the collision.
        The connection with the higher BGP Identifier (router ID) wins.

        Args:
            reader: Stream reader
            writer: Stream writer
        """
        try:
            self.logger.debug("_handle_incoming_connection called")

            peer_addr = writer.get_extra_info('peername')
            self.logger.debug(f"Peer address: {peer_addr}")

            peer_ip = peer_addr[0]
            self.logger.info(f"Incoming connection from {peer_ip}")

            # Find session for this peer — first try exact IP match (local FRR peers)
            self.logger.debug(f"Looking for session for {peer_ip} in {list(self.sessions.keys())}")
            session = self.sessions.get(peer_ip)
            mesh_identified = False

            if not session and self.mesh_sessions:
                # No IP match — try OPEN-based identification for mesh peers
                # Read the BGP OPEN to extract AS number and router-ID
                self.logger.info(f"No IP match for {peer_ip}, attempting mesh OPEN-based identification "
                                f"({len(self.mesh_sessions)} mesh peer(s) configured)")
                open_msg = await self._read_open_message(reader)

                if not open_msg:
                    self.logger.warning(f"Failed to read OPEN from {peer_ip} for mesh identification, rejecting")
                    writer.close()
                    await writer.wait_closed()
                    return

                # Match by AS number against mesh_sessions
                peer_as = open_msg.my_as
                session = self.mesh_sessions.get(peer_as)

                if not session:
                    self.logger.warning(f"No mesh peer configured for AS{peer_as} from {peer_ip}, rejecting")
                    writer.close()
                    await writer.wait_closed()
                    return

                self.logger.info(f"Mesh peer matched: AS{peer_as} router-id {open_msg.bgp_identifier} from {peer_ip}")
                # Store the pre-read OPEN so the session can process it after accept
                session._pending_open = open_msg
                mesh_identified = True

            if not session:
                self.logger.warning(f"No configured session for {peer_ip}, rejecting")
                writer.close()
                await writer.wait_closed()
                return

            # RFC 4271 Section 6.8: Connection Collision Detection
            # If we're in passive mode (or mesh-identified), always accept
            # If we're in active mode BUT:
            #   - Session is in Idle/Connect/Active state: Accept (we haven't established yet)
            #   - Session is in OpenSent/OpenConfirm: Handle collision based on router ID
            #   - Session is Established: Reject (we already have a working connection)
            self.logger.debug(f"Session passive mode: {session.config.passive}, FSM state: {session.fsm.get_state_name()}")

            if not session.config.passive and not mesh_identified:
                # Active mode - check current state for collision handling
                current_state = session.fsm.state

                if current_state == STATE_ESTABLISHED:
                    # Already established, reject new connection
                    self.logger.warning(f"Session {peer_ip} already established, rejecting new connection")
                    writer.close()
                    await writer.wait_closed()
                    return

                elif current_state in (STATE_OPENSENT, STATE_OPENCONFIRM):
                    # Connection collision - per RFC 4271, compare BGP identifiers (router IDs)
                    # The connection initiated by the higher router ID is kept
                    import socket
                    our_id = struct.unpack("!I", socket.inet_aton(self.router_id))[0]
                    peer_id = struct.unpack("!I", socket.inet_aton(session.config.peer_router_id or peer_ip))[0]

                    if our_id > peer_id:
                        # We have higher ID - keep our outgoing connection, reject incoming
                        self.logger.info(f"Connection collision with {peer_ip}: our ID higher, rejecting incoming")
                        writer.close()
                        await writer.wait_closed()
                        return
                    else:
                        # Peer has higher ID - accept incoming, close our outgoing attempt
                        self.logger.info(f"Connection collision with {peer_ip}: peer ID higher, accepting incoming, dropping outgoing")
                        # CRITICAL: Cancel message reader task FIRST to prevent race condition
                        if session.message_reader_task and not session.message_reader_task.done():
                            self.logger.debug("Canceling existing message reader task before collision resolution")
                            session.message_reader_task.cancel()
                            try:
                                await session.message_reader_task
                            except asyncio.CancelledError:
                                pass
                        # Close existing connection attempt
                        if session.writer:
                            try:
                                session.writer.close()
                                await session.writer.wait_closed()
                            except (ConnectionError, OSError, asyncio.CancelledError) as e:
                                self.logger.debug(f"Error closing writer during collision: {e}")
                        session.reader = None
                        session.writer = None

                else:
                    # In Idle/Connect/Active state - accept the incoming connection
                    # This handles the case where both sides are trying to connect
                    self.logger.info(f"Accepting incoming connection from {peer_ip} (collision resolution)")
            elif mesh_identified:
                # Mesh peer: check if already established
                if session.fsm.state == STATE_ESTABLISHED:
                    self.logger.warning(f"Mesh session AS{session.config.peer_as} already established, rejecting")
                    session._pending_open = None
                    writer.close()
                    await writer.wait_closed()
                    return

            # Accept connection - pass is_collision=True if we're not in passive mode
            # and this is not a mesh-identified connection
            is_collision = not session.config.passive and not mesh_identified
            self.logger.debug(f"Calling session.accept_connection for {peer_ip} (collision={is_collision}, mesh={mesh_identified})")
            await session.accept_connection(reader, writer, is_collision=is_collision)
            self.logger.debug(f"session.accept_connection completed for {peer_ip}")

        except Exception as e:
            self.logger.error(f"Error in _handle_incoming_connection: {type(e).__name__}: {e}", exc_info=True)
            try:
                writer.close()
                await writer.wait_closed()
            except (ConnectionError, OSError, asyncio.CancelledError) as close_err:
                self.logger.debug(f"Error closing writer after connection error: {close_err}")

    def add_peer(self, config: BGPSessionConfig) -> BGPSession:
        """
        Add BGP peer

        Args:
            config: Session configuration

        Returns:
            BGPSession object
        """
        peer_ip = config.peer_ip

        if peer_ip in self.sessions:
            self.logger.warning(f"Peer {peer_ip} already exists")
            return self.sessions[peer_ip]

        # Create session
        session = BGPSession(config)
        session.loc_rib = self.loc_rib  # Share Loc-RIB
        session.graceful_restart_manager = self.graceful_restart  # Share graceful restart manager
        session.rpki_validator = self.rpki_validator  # Share RPKI validator
        session.flowspec_manager = self.flowspec_manager  # Share FlowSpec manager

        # Mesh peers (accept_any_source): index by AS number for OPEN-based matching
        if config.accept_any_source:
            self.mesh_sessions[config.peer_as] = session
            self.logger.info(f"Added mesh peer AS{config.peer_as} (accept_any_source, passive)")

        self.sessions[peer_ip] = session

        # Register callback for when session becomes established
        session.on_established = lambda: asyncio.create_task(self._on_session_established(peer_ip))

        # Configure route reflection if enabled
        if self.route_reflector and config.route_reflector_client:
            self.route_reflector.add_client(peer_ip)
            self.logger.info(f"Added {peer_ip} as route reflector client")

        self.logger.info(f"Added peer {peer_ip} (AS{config.peer_as})")

        return session

    def remove_peer(self, peer_ip: str) -> None:
        """
        Remove BGP peer

        Args:
            peer_ip: Peer IP address (or synthetic key like "mesh-as65002")
        """
        if peer_ip not in self.sessions:
            self.logger.warning(f"Peer {peer_ip} not found")
            return

        session = self.sessions[peer_ip]

        # Stop session (if event loop is running)
        try:
            asyncio.create_task(session.stop())
        except RuntimeError:
            # No event loop running (e.g., in unit tests)
            pass

        # Remove from route reflector
        if self.route_reflector:
            self.route_reflector.remove_peer(peer_ip)

        # Remove from mesh_sessions if present
        for as_num, mesh_session in list(self.mesh_sessions.items()):
            if mesh_session is session:
                del self.mesh_sessions[as_num]
                self.logger.debug(f"Removed mesh session for AS{as_num}")

        # Remove from sessions
        del self.sessions[peer_ip]

        self.logger.info(f"Removed peer {peer_ip}")

    async def start_peer(self, peer_ip: str) -> bool:
        """
        Start BGP peer session

        Args:
            peer_ip: Peer IP address

        Returns:
            True if started successfully
        """
        if peer_ip not in self.sessions:
            self.logger.error(f"Peer {peer_ip} not found")
            return False

        session = self.sessions[peer_ip]

        try:
            await session.start()
            # Note: FSM handles TCP connection initiation via on_tcp_connect callback
            # No need to call session.connect() explicitly - it's already triggered
            # by the ManualStart event processing in the FSM

            return True

        except Exception as e:
            self.logger.error(f"Failed to start peer {peer_ip}: {e}")
            return False

    async def stop_peer(self, peer_ip: str) -> None:
        """
        Stop BGP peer session

        Args:
            peer_ip: Peer IP address
        """
        if peer_ip not in self.sessions:
            self.logger.warning(f"Peer {peer_ip} not found")
            return

        session = self.sessions[peer_ip]
        await session.stop()

    async def _on_session_established(self, peer_ip: str) -> None:
        """
        Callback when a session becomes established

        Advertises all existing Loc-RIB routes to the newly established peer

        Args:
            peer_ip: Peer IP address
        """
        self.logger.info(f"Session with {peer_ip} established - advertising existing routes")

        # Get all prefixes from Loc-RIB
        all_routes = self.loc_rib.get_all_routes()
        all_prefixes = [route.prefix for route in all_routes]

        if all_prefixes:
            self.logger.debug(f"Advertising {len(all_prefixes)} existing routes to {peer_ip}")
            await self._advertise_routes(all_prefixes)
        else:
            self.logger.debug(f"No existing routes to advertise to {peer_ip}")

    def enable_route_reflection(self, cluster_id: Optional[str] = None) -> None:
        """
        Enable route reflection

        Args:
            cluster_id: Cluster ID (defaults to router ID)
        """
        if not cluster_id:
            cluster_id = self.router_id

        self.route_reflector = RouteReflector(cluster_id, self.router_id)
        self.logger.info(f"Route reflection enabled with cluster ID {cluster_id}")

    def originate_route(self, prefix: str, next_hop: Optional[str] = None,
                       local_pref: int = 100, origin: int = ORIGIN_IGP) -> bool:
        """
        Originate a local route (network statement equivalent)

        Args:
            prefix: Prefix to originate (e.g., "10.2.2.2/32")
            next_hop: Next hop IP (defaults to router_id)
            local_pref: Local preference value
            origin: Origin type (IGP, EGP, INCOMPLETE)

        Returns:
            True if route was originated successfully
        """
        from .attributes import OriginAttribute, ASPathAttribute, NextHopAttribute, LocalPrefAttribute

        try:
            # Parse prefix
            if '/' in prefix:
                prefix_ip, prefix_len_str = prefix.split('/')
                prefix_len = int(prefix_len_str)
            else:
                prefix_ip = prefix
                prefix_len = 32

            # Use router_id as next_hop if not specified
            if not next_hop:
                next_hop = self.router_id

            # Build path attributes for local route
            path_attributes = {
                ATTR_ORIGIN: OriginAttribute(origin),
                ATTR_AS_PATH: ASPathAttribute([]),  # Empty AS_PATH for local routes
                ATTR_NEXT_HOP: NextHopAttribute(next_hop),
                ATTR_LOCAL_PREF: LocalPrefAttribute(local_pref)
            }

            # Create BGP route
            route = BGPRoute(
                prefix=prefix,
                prefix_len=prefix_len,
                path_attributes=path_attributes,
                peer_id=self.router_id,  # Local router is the "peer"
                peer_ip=self.router_id,
                source="local",  # Mark as locally originated
                afi=AFI_IPV4,
                safi=SAFI_UNICAST
            )

            # Install in Loc-RIB
            self.loc_rib.install_route(route)

            self.logger.info(f"Originated local route: {prefix} via {next_hop}")

            # Trigger advertisement to all peers
            asyncio.create_task(self._advertise_routes([prefix]))

            return True

        except Exception as e:
            self.logger.error(f"Failed to originate route {prefix}: {e}")
            return False

    async def _decision_process_loop(self) -> None:
        """Run BGP decision process periodically"""
        self.logger.info("Decision process loop started")

        while self.running:
            try:
                await asyncio.sleep(self.decision_process_interval)
                await self._run_decision_process()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in decision process: {e}")

        self.logger.info("Decision process loop stopped")

    async def _run_decision_process(self) -> None:
        """
        Run BGP decision process

        This runs the best path selection algorithm across all received routes
        and updates Loc-RIB with best paths.
        """
        # Collect all prefixes from all Adj-RIB-In
        all_prefixes: Set[str] = set()

        for session in self.sessions.values():
            if session.is_established():
                prefixes = session.adj_rib_in.get_prefixes()
                all_prefixes.update(prefixes)

        if not all_prefixes:
            return

        # Run decision process for each prefix
        changed_prefixes = []

        for prefix in all_prefixes:
            # Collect all candidate routes for this prefix
            candidates: List[BGPRoute] = []

            for session in self.sessions.values():
                if not session.is_established():
                    continue

                routes = session.adj_rib_in.get_routes(prefix)

                # Apply import policy
                for route in routes:
                    filtered_route = self.policy_engine.apply_import_policy(
                        route, session.peer_id
                    )
                    if filtered_route:
                        candidates.append(filtered_route)

            if not candidates:
                # No routes for this prefix, remove from Loc-RIB if present
                if self.loc_rib.lookup(prefix):
                    self.loc_rib.remove_route(prefix)
                    changed_prefixes.append(prefix)
                continue

            # Select best path
            best_route = self.best_path_selector.select_best(candidates)

            if not best_route:
                continue

            # Check if best path changed
            current_best = self.loc_rib.lookup(prefix)

            if current_best is None:
                # New best path
                self.loc_rib.install_route(best_route)
                changed_prefixes.append(prefix)
                self.logger.debug(f"Installed new best path for {prefix} via {best_route.peer_id}")

                # Install route into kernel
                if self.kernel_route_manager and best_route.next_hop:
                    self.kernel_route_manager.install_route(
                        prefix, best_route.next_hop, protocol="bgp"
                    )

            elif current_best.peer_id != best_route.peer_id:
                # Best path changed
                self.loc_rib.install_route(best_route)
                changed_prefixes.append(prefix)
                self.logger.info(f"Best path changed for {prefix}: {current_best.peer_id} → {best_route.peer_id}")

                # Install route into kernel
                if self.kernel_route_manager and best_route.next_hop:
                    self.kernel_route_manager.install_route(
                        prefix, best_route.next_hop, protocol="bgp"
                    )

        # If best paths changed, trigger route advertisement
        if changed_prefixes:
            self.logger.debug(f"Decision process: {len(changed_prefixes)} prefixes changed")
            await self._advertise_routes(changed_prefixes)

    async def _advertise_routes(self, changed_prefixes: List[str]) -> None:
        """
        Advertise routes to peers

        Args:
            changed_prefixes: List of prefixes that changed
        """
        for session in self.sessions.values():
            if not session.is_established():
                continue

            # Build UPDATE messages for changed prefixes
            nlri = []
            withdrawn = []

            for prefix in changed_prefixes:
                best_route = self.loc_rib.lookup(prefix)

                if best_route:
                    # CRITICAL: Only advertise IPv4 routes in standard UPDATE messages
                    # IPv6 routes require MP_BGP extensions which we don't fully support yet
                    if ':' in prefix:
                        self.logger.debug(f"Skipping IPv6 route {prefix} - MP_BGP not implemented")
                        continue

                    # Check if we should advertise this route to this peer
                    if self._should_advertise_to_peer(best_route, session):
                        # Apply export policy
                        exported_route = self.policy_engine.apply_export_policy(
                            best_route, session.peer_id
                        )

                        if exported_route:
                            nlri.append(prefix)
                else:
                    # Route withdrawn
                    # Only withdraw IPv4 routes
                    if ':' not in prefix:
                        withdrawn.append(prefix)

            # Send UPDATE if there are changes
            if nlri or withdrawn:
                # Get path attributes from best route
                path_attrs_dict = {}
                if nlri and changed_prefixes:
                    best_route = self.loc_rib.lookup(nlri[0])
                    if best_route:
                        path_attrs_list = list(best_route.path_attributes.values())

                        # Modify attributes for advertisement
                        path_attrs_list = self._prepare_attributes_for_advertisement(
                            path_attrs_list, session
                        )

                        # Convert list back to dict
                        path_attrs_dict = {attr.type_code: attr for attr in path_attrs_list}

                # Create and send UPDATE
                update = BGPUpdate(
                    withdrawn_routes=withdrawn,
                    path_attributes=path_attrs_dict,
                    nlri=nlri
                )

                await session._send_message(update)

                session.stats['routes_advertised'] += len(nlri)
                self.logger.debug(f"Advertised {len(nlri)} routes, withdrew {len(withdrawn)} to {session.peer_id}")

    def _should_advertise_to_peer(self, route: BGPRoute, session: BGPSession) -> bool:
        """
        Determine if route should be advertised to peer

        Args:
            route: BGP route
            session: BGP session

        Returns:
            True if route should be advertised
        """
        # Always advertise local routes (originated by this router)
        if route.source == "local":
            return True

        # Don't advertise back to source
        if route.peer_id == session.peer_id:
            return False

        # Check route reflection rules
        if self.route_reflector:
            # Determine if route is from eBGP
            is_ebgp_source = route.peer_ip != self.router_id  # Simplified check

            return self.route_reflector.should_reflect(
                route, route.peer_id, session.peer_id, is_ebgp_source
            )

        # Standard BGP rules (no route reflection)
        # iBGP: Don't advertise iBGP routes to other iBGP peers
        # eBGP: Advertise all routes

        route_peer_as = self._get_route_peer_as(route)
        is_route_ibgp = route_peer_as == self.local_as

        session_peer_as = session.config.peer_as
        is_session_ibgp = session_peer_as == self.local_as

        if is_route_ibgp and is_session_ibgp:
            # iBGP to iBGP - don't advertise (requires full mesh or RR)
            return False

        return True

    def _get_route_peer_as(self, route: BGPRoute) -> Optional[int]:
        """
        Get peer AS from route

        Args:
            route: BGP route

        Returns:
            Peer AS number or None
        """
        if not route.has_attribute(ATTR_AS_PATH):
            return None

        as_path_attr = route.get_attribute(ATTR_AS_PATH)

        # Get first AS from AS_PATH (neighbor AS)
        if as_path_attr.segments:
            seg_type, as_list = as_path_attr.segments[0]
            if as_list:
                return as_list[0]

        return None

    def _prepare_attributes_for_advertisement(self, attributes: List[PathAttribute],
                                              session: BGPSession) -> List[PathAttribute]:
        """
        Prepare path attributes for advertisement to peer

        Modifies attributes as needed:
        - Ensure ORIGIN, AS_PATH, NEXT_HOP are present (required)
        - Update NEXT_HOP to self
        - Prepend AS_PATH with local AS (for eBGP)
        - Set LOCAL_PREF (for iBGP)

        Args:
            attributes: Original attributes
            session: Target session

        Returns:
            Modified attributes
        """
        # Track which required attributes we've seen
        has_origin = False
        has_as_path = False
        has_next_hop = False

        # Create copies to avoid modifying originals
        modified = []

        for attr in attributes:
            # Create a copy
            if attr.type_code == ATTR_ORIGIN:
                # Keep ORIGIN as-is
                modified.append(attr)
                has_origin = True

            elif attr.type_code == ATTR_NEXT_HOP:
                # Update NEXT_HOP to self
                modified.append(NextHopAttribute(session.config.local_ip))
                has_next_hop = True

            elif attr.type_code == ATTR_AS_PATH:
                # Create a copy of AS_PATH attribute
                import copy
                segments_copy = copy.deepcopy(attr.segments)
                as_path_copy = ASPathAttribute(segments_copy)

                # Prepend local AS for eBGP
                if session.config.peer_as != self.local_as:  # eBGP
                    as_path_copy.prepend(self.local_as)
                modified.append(as_path_copy)
                has_as_path = True

            elif attr.type_code == ATTR_LOCAL_PREF:
                # LOCAL_PREF: Only include for iBGP, strip for eBGP
                if session.config.peer_as == self.local_as:  # iBGP
                    modified.append(attr)
                # else: skip for eBGP

            else:
                # Keep other attributes as-is
                modified.append(attr)

        # Ensure all required well-known mandatory attributes are present
        # Add them at the beginning of the list in order: ORIGIN, AS_PATH, NEXT_HOP
        if not has_origin:
            modified.insert(0, OriginAttribute(ORIGIN_IGP))

        if not has_as_path:
            as_path = ASPathAttribute([])
            if session.config.peer_as != self.local_as:  # eBGP
                as_path.prepend(self.local_as)
            # Insert after ORIGIN if present
            insert_pos = 1 if has_origin else 0
            modified.insert(insert_pos, as_path)

        if not has_next_hop:
            # Insert after ORIGIN and AS_PATH if present
            insert_pos = 0
            if has_origin:
                insert_pos += 1
            if has_as_path:
                insert_pos += 1
            modified.insert(insert_pos, NextHopAttribute(session.config.local_ip))

        # Add LOCAL_PREF for iBGP if not present
        if session.config.peer_as == self.local_as:  # iBGP
            has_local_pref = any(attr.type_code == ATTR_LOCAL_PREF for attr in modified)
            if not has_local_pref:
                modified.append(LocalPrefAttribute(100))  # Default LOCAL_PREF

        return modified

    def set_import_policy(self, peer_ip: str, policy: Policy) -> None:
        """
        Set import policy for peer

        Args:
            peer_ip: Peer IP address
            policy: Import policy
        """
        self.policy_engine.set_import_policy(peer_ip, policy)

    def set_export_policy(self, peer_ip: str, policy: Policy) -> None:
        """
        Set export policy for peer

        Args:
            peer_ip: Peer IP address
            policy: Export policy
        """
        self.policy_engine.set_export_policy(peer_ip, policy)

    def get_statistics(self) -> Dict:
        """
        Get BGP agent statistics

        Returns:
            Dictionary with statistics
        """
        stats = {
            'local_as': self.local_as,
            'router_id': self.router_id,
            'total_peers': len(self.sessions),
            'established_peers': sum(1 for s in self.sessions.values() if s.is_established()),
            'loc_rib_routes': self.loc_rib.size(),
            'peers': {}
        }

        # Per-peer statistics
        for peer_ip, session in self.sessions.items():
            stats['peers'][peer_ip] = session.get_statistics()

        # Route reflector statistics
        if self.route_reflector:
            stats['route_reflector'] = self.route_reflector.get_statistics()

        return stats

    @property
    def stats(self) -> Dict:
        """
        Get aggregated message statistics from all BGP sessions.
        Used by Prometheus metrics collector.

        Returns:
            Dictionary with aggregated message counters
        """
        aggregated = {
            'open_sent': 0,
            'open_recv': 0,
            'update_sent': 0,
            'update_recv': 0,
            'keepalive_sent': 0,
            'keepalive_recv': 0,
            'notification_sent': 0,
            'notification_recv': 0,
            'messages_sent': 0,
            'messages_received': 0
        }

        for session in self.sessions.values():
            session_stats = session.stats
            aggregated['open_sent'] += session_stats.get('open_sent', 0)
            aggregated['open_recv'] += session_stats.get('open_recv', 0)
            aggregated['update_sent'] += session_stats.get('update_sent', 0)
            aggregated['update_recv'] += session_stats.get('update_recv', 0)
            aggregated['keepalive_sent'] += session_stats.get('keepalive_sent', 0)
            aggregated['keepalive_recv'] += session_stats.get('keepalive_recv', 0)
            aggregated['notification_sent'] += session_stats.get('notification_sent', 0)
            aggregated['notification_recv'] += session_stats.get('notification_recv', 0)
            aggregated['messages_sent'] += session_stats.get('messages_sent', 0)
            aggregated['messages_received'] += session_stats.get('messages_received', 0)

        return aggregated

    def get_peer_status(self, peer_ip: str) -> Optional[Dict]:
        """
        Get status of specific peer

        Args:
            peer_ip: Peer IP address

        Returns:
            Peer status dictionary or None
        """
        session = self.sessions.get(peer_ip)
        if not session:
            return None

        return session.get_statistics()

    def get_routes(self, prefix: Optional[str] = None) -> List[BGPRoute]:
        """
        Get routes from Loc-RIB

        Args:
            prefix: Optional prefix filter

        Returns:
            List of BGP routes
        """
        if prefix:
            route = self.loc_rib.lookup(prefix)
            return [route] if route else []
        else:
            return self.loc_rib.get_all_routes()
