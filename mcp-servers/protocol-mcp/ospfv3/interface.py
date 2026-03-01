"""
OSPFv3 Interface Management
RFC 5340 Section 4.1 and 4.3
"""

import asyncio
import socket
import struct
import time
import logging
import ipaddress
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from .constants import *
from .packets import *
from .neighbor import OSPFv3Neighbor
from .lsa import *


@dataclass
class OSPFv3InterfaceConfig:
    """OSPFv3 Interface Configuration"""
    # Interface identification
    interface_name: str
    interface_id: int
    area_id: str = "0.0.0.0"
    instance_id: int = DEFAULT_INSTANCE_ID

    # IPv6 addresses
    link_local_address: str = ""  # Link-local address (fe80::)
    global_addresses: List[str] = field(default_factory=list)  # Global unicast addresses

    # Network type
    network_type: str = NETWORK_TYPE_BROADCAST

    # Timers
    hello_interval: int = DEFAULT_HELLO_INTERVAL
    dead_interval: int = DEFAULT_DEAD_INTERVAL
    rxmt_interval: int = DEFAULT_RXMT_INTERVAL
    inftra_delay: int = DEFAULT_INFTRA_DELAY

    # Router priority for DR election
    router_priority: int = 1

    # Options
    options: int = OPTION_V6 | OPTION_E | OPTION_R


class OSPFv3Interface:
    """
    OSPFv3 Interface

    Handles:
    - Hello protocol on interface
    - Neighbor discovery and management
    - DR/BDR election
    - LSA flooding on interface
    """

    def __init__(self, config: OSPFv3InterfaceConfig, router_id: str):
        self.config = config
        self.router_id = router_id
        self.logger = logging.getLogger(f"OSPFv3Interface[{config.interface_name}]")

        # Interface state
        self.state = "Down"
        self.designated_router = "0.0.0.0"
        self.backup_designated_router = "0.0.0.0"

        # Neighbors on this interface
        self.neighbors: Dict[str, OSPFv3Neighbor] = {}  # key = neighbor router ID

        # Sockets
        self.socket = None
        self.socket_fd = None

        # Tasks
        self.hello_task = None
        self.receive_task = None
        self.neighbor_timer_task = None

        # Statistics
        self.stats = {
            'hello_sent': 0,
            'hello_received': 0,
            'neighbors_up': 0,
            'neighbors_full': 0,
            'dr_elections': 0,
            'last_hello_sent': 0.0,
            'last_hello_received': 0.0
        }

        # Link-LSA for this interface (link-local scope)
        self.link_lsa: Optional[LinkLSA] = None

    async def start(self):
        """Start interface operation"""
        try:
            self.logger.info(f"Starting OSPFv3 on interface {self.config.interface_name}")

            # Verify we have link-local address
            if not self.config.link_local_address:
                raise ValueError(f"No link-local address on {self.config.interface_name}")

            # Create and bind socket
            await self._setup_socket()

            # Generate Link-LSA for this interface
            self._generate_link_lsa()

            # Start tasks
            self.hello_task = asyncio.create_task(self._hello_sender())
            self.receive_task = asyncio.create_task(self._packet_receiver())
            self.neighbor_timer_task = asyncio.create_task(self._neighbor_timer())

            # Set interface state
            if self.config.network_type == NETWORK_TYPE_PTP:
                self.state = "Point-to-Point"
            else:
                self.state = "Waiting"  # Will transition after Wait Timer

            self.logger.info(f"Interface {self.config.interface_name} state: {self.state}")

        except Exception as e:
            self.logger.error(f"Failed to start interface: {e}")
            raise

    async def stop(self):
        """Stop interface operation"""
        self.logger.info(f"Stopping OSPFv3 on interface {self.config.interface_name}")

        # Cancel tasks
        if self.hello_task:
            self.hello_task.cancel()
        if self.receive_task:
            self.receive_task.cancel()
        if self.neighbor_timer_task:
            self.neighbor_timer_task.cancel()

        # Close socket
        if self.socket:
            self.socket.close()

        self.state = "Down"

    async def _setup_socket(self):
        """Setup raw IPv6 socket for OSPFv3"""
        try:
            # Create raw IPv6 socket
            self.socket = socket.socket(socket.AF_INET6, socket.SOCK_RAW, OSPF_PROTOCOL_NUMBER)

            # Bind to interface
            # Note: This is simplified - actual interface binding varies by OS
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE,
                                  self.config.interface_name.encode())

            # Join multicast group
            # AllSPFRouters (ff02::5)
            mreq = socket.inet_pton(socket.AF_INET6, ALLSPFROUTERS_V6)
            mreq += struct.pack('@I', socket.if_nametoindex(self.config.interface_name))
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

            # Set multicast hop limit
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 1)

            # Get file descriptor for async operations
            self.socket.setblocking(False)
            self.socket_fd = self.socket.fileno()

            self.logger.info(f"Socket created and bound to {self.config.interface_name}")

        except Exception as e:
            self.logger.error(f"Failed to setup socket: {e}")
            raise

    async def _hello_sender(self):
        """Periodically send Hello packets"""
        self.logger.info(f"Hello sender started (interval: {self.config.hello_interval}s)")

        try:
            while True:
                await asyncio.sleep(self.config.hello_interval)
                await self.send_hello()

        except asyncio.CancelledError:
            self.logger.info("Hello sender stopped")
        except Exception as e:
            self.logger.error(f"Error in hello sender: {e}")

    async def send_hello(self):
        """Send Hello packet on interface"""
        try:
            # Build Hello packet
            hello = OSPFv3HelloPacket(
                header=OSPFv3Header(
                    packet_type=HELLO_PACKET,
                    router_id=self.router_id,
                    area_id=self.config.area_id,
                    instance_id=self.config.instance_id
                ),
                interface_id=self.config.interface_id,
                router_priority=self.config.router_priority,
                options=self.config.options,
                hello_interval=self.config.hello_interval,
                dead_interval=self.config.dead_interval,
                designated_router=self.designated_router,
                backup_designated_router=self.backup_designated_router,
                neighbors=list(self.neighbors.keys())  # List of neighbor router IDs
            )

            # Encode packet
            packet_bytes = hello.encode(
                src_addr=self.config.link_local_address,
                dst_addr=ALLSPFROUTERS_V6
            )

            # Send packet
            self.socket.sendto(packet_bytes, (ALLSPFROUTERS_V6, 0))

            self.stats['hello_sent'] += 1
            self.stats['last_hello_sent'] = time.time()

            self.logger.debug(f"Sent Hello: DR={self.designated_router}, "
                            f"BDR={self.backup_designated_router}, "
                            f"Neighbors={len(self.neighbors)}")

        except Exception as e:
            self.logger.error(f"Error sending Hello: {e}")

    async def _packet_receiver(self):
        """Receive and process OSPFv3 packets"""
        self.logger.info("Packet receiver started")

        try:
            loop = asyncio.get_event_loop()

            while True:
                # Wait for data with source address
                data, addr_info = await loop.sock_recvfrom(self.socket, 65535)

                if data:
                    # Extract source address (IPv6 address is first element of tuple)
                    src_addr = addr_info[0]
                    await self._process_packet(data, src_addr)

        except asyncio.CancelledError:
            self.logger.info("Packet receiver stopped")
        except Exception as e:
            self.logger.error(f"Error in packet receiver: {e}")

    async def _process_packet(self, data: bytes, src_addr: str):
        """Process received OSPFv3 packet"""
        try:
            # Decode packet
            result = decode_packet(data)
            if not result:
                return

            header, packet = result

            # Verify instance ID
            if header.instance_id != self.config.instance_id:
                self.logger.debug(f"Ignoring packet with wrong instance ID: {header.instance_id}")
                return

            # Verify area ID
            if header.area_id != self.config.area_id:
                self.logger.debug(f"Ignoring packet from different area: {header.area_id}")
                return

            # Process based on packet type
            if header.packet_type == HELLO_PACKET:
                await self._process_hello(packet, src_addr)
            elif header.packet_type == DATABASE_DESCRIPTION:
                await self._process_database_description(packet)
            # TODO: Add other packet types

        except Exception as e:
            self.logger.error(f"Error processing packet: {e}")

    async def _process_hello(self, hello: OSPFv3HelloPacket, src_addr: str):
        """Process received Hello packet"""
        self.stats['hello_received'] += 1
        self.stats['last_hello_received'] = time.time()

        neighbor_id = hello.header.router_id

        self.logger.debug(f"Received Hello from {neighbor_id}")

        # Check if neighbor exists
        if neighbor_id not in self.neighbors:
            # New neighbor
            self.logger.info(f"Discovered new neighbor: {neighbor_id}")

            neighbor = OSPFv3Neighbor(
                neighbor_id=neighbor_id,
                neighbor_interface_id=hello.interface_id,
                neighbor_address=src_addr,  # Use source address from packet
                priority=hello.router_priority,
                designated_router=hello.designated_router,
                backup_designated_router=hello.backup_designated_router,
                options=hello.options,
                dead_interval=hello.dead_interval
            )

            self.neighbors[neighbor_id] = neighbor

            # Process Hello event
            neighbor.process_event(EVENT_HELLO_RECEIVED)

        else:
            neighbor = self.neighbors[neighbor_id]

            # Update neighbor address if it changed
            if neighbor.neighbor_address != src_addr:
                neighbor.neighbor_address = src_addr

            # Update neighbor from Hello
            neighbor.update_from_hello(hello)

        # Check if we're in the neighbor list (2-Way check)
        if self.router_id in hello.neighbors:
            if neighbor.state == STATE_INIT:
                # Bidirectional communication established
                self.logger.info(f"2-Way communication with {neighbor_id}")

                # Determine if we should form adjacency
                should_form_adjacency = self._should_form_adjacency(neighbor)

                neighbor.process_event(EVENT_2WAY_RECEIVED,
                                     should_form_adjacency=should_form_adjacency)

                # If adjacency formed, initiate DD exchange
                if neighbor.state == STATE_EXSTART:
                    await self._send_dd_packet(neighbor)

                # Run DR/BDR election if needed
                if self.config.network_type == NETWORK_TYPE_BROADCAST:
                    await self._run_dr_election()
        else:
            # We're not in neighbor list
            if neighbor.state >= STATE_2WAY:
                neighbor.process_event(EVENT_1WAY)

        # Update statistics
        self._update_stats()

    def _should_form_adjacency(self, neighbor: OSPFv3Neighbor) -> bool:
        """
        Determine if adjacency should be formed with neighbor

        On point-to-point networks: always form adjacency
        On broadcast networks: form adjacency only with DR/BDR
        """
        if self.config.network_type == NETWORK_TYPE_PTP:
            return True

        # On broadcast networks, form adjacency only with DR/BDR
        if neighbor.neighbor_id == self.designated_router:
            return True
        if neighbor.neighbor_id == self.backup_designated_router:
            return True

        # Also form adjacency if we're the DR or BDR
        if self.router_id == self.designated_router:
            return True
        if self.router_id == self.backup_designated_router:
            return True

        return False

    async def _run_dr_election(self):
        """
        Run Designated Router election (RFC 5340 Section 4.3)

        Same algorithm as OSPFv2
        """
        self.logger.debug("Running DR/BDR election")

        # Build list of eligible routers (priority > 0)
        eligible_routers = []

        # Add ourselves
        if self.config.router_priority > 0:
            eligible_routers.append({
                'router_id': self.router_id,
                'priority': self.config.router_priority,
                'declared_dr': self.designated_router,
                'declared_bdr': self.backup_designated_router
            })

        # Add neighbors
        for neighbor in self.neighbors.values():
            if neighbor.is_two_way_or_better() and neighbor.priority > 0:
                eligible_routers.append({
                    'router_id': neighbor.neighbor_id,
                    'priority': neighbor.priority,
                    'declared_dr': neighbor.designated_router,
                    'declared_bdr': neighbor.backup_designated_router
                })

        if not eligible_routers:
            return

        # Election Algorithm (simplified)
        # 1. Calculate BDR
        bdr_candidates = [r for r in eligible_routers
                         if r['declared_dr'] != r['router_id'] and r['priority'] > 0]

        if bdr_candidates:
            # Sort by: 1) declared BDR (self), 2) priority, 3) router ID
            bdr_candidates.sort(key=lambda r: (
                r['declared_bdr'] == r['router_id'],
                r['priority'],
                int(ipaddress.IPv4Address(r['router_id']))
            ), reverse=True)

            new_bdr = bdr_candidates[0]['router_id']
        else:
            new_bdr = "0.0.0.0"

        # 2. Calculate DR
        dr_candidates = [r for r in eligible_routers
                        if r['declared_dr'] == r['router_id']]

        if dr_candidates:
            # Sort by: priority, router ID
            dr_candidates.sort(key=lambda r: (
                r['priority'],
                int(ipaddress.IPv4Address(r['router_id']))
            ), reverse=True)

            new_dr = dr_candidates[0]['router_id']
        else:
            new_dr = new_bdr
            new_bdr = "0.0.0.0"

        # Check if DR/BDR changed
        if new_dr != self.designated_router or new_bdr != self.backup_designated_router:
            old_dr = self.designated_router
            old_bdr = self.backup_designated_router

            self.designated_router = new_dr
            self.backup_designated_router = new_bdr

            self.stats['dr_elections'] += 1

            self.logger.info(f"DR election: DR={new_dr}, BDR={new_bdr} "
                           f"(was DR={old_dr}, BDR={old_bdr})")

            # Transition interface state
            if self.router_id == new_dr:
                self.state = "DR"
            elif self.router_id == new_bdr:
                self.state = "Backup"
            else:
                self.state = "DROther"

            # Re-evaluate adjacencies
            for neighbor in self.neighbors.values():
                if neighbor.state >= STATE_2WAY:
                    should_form_adjacency = self._should_form_adjacency(neighbor)
                    neighbor.process_event(EVENT_ADJ_OK,
                                         should_form_adjacency=should_form_adjacency)

    async def _process_database_description(self, dd_packet: DatabaseDescriptionPacket):
        """Process Database Description packet"""
        neighbor_id = dd_packet.header.router_id

        if neighbor_id not in self.neighbors:
            self.logger.warning(f"DD packet from unknown neighbor: {neighbor_id}")
            return

        neighbor = self.neighbors[neighbor_id]

        if neighbor.state < STATE_EXSTART:
            self.logger.warning(f"DD packet from neighbor {neighbor_id} in state {neighbor.state}")
            return

        neighbor.dd_received += 1

        self.logger.debug(f"Received DD from {neighbor_id}: "
                        f"Seq={dd_packet.dd_sequence_number}, "
                        f"Flags=0x{dd_packet.flags:02x}, "
                        f"LSAs={len(dd_packet.lsa_headers)}")

        # Process based on neighbor state
        if neighbor.state == STATE_EXSTART:
            await self._process_dd_exstart(neighbor, dd_packet)
        elif neighbor.state == STATE_EXCHANGE:
            await self._process_dd_exchange(neighbor, dd_packet)
        elif neighbor.state == STATE_LOADING or neighbor.state == STATE_FULL:
            await self._process_dd_stable(neighbor, dd_packet)

    async def _process_dd_exstart(self, neighbor, dd_packet):
        """Process DD packet in ExStart state - master/slave negotiation"""
        # Determine master/slave based on Router ID
        # Higher Router ID becomes master
        my_router_id_int = int(ipaddress.IPv4Address(self.router_id))
        neighbor_router_id_int = int(ipaddress.IPv4Address(neighbor.neighbor_id))

        if my_router_id_int > neighbor_router_id_int:
            # We are master
            neighbor.is_master = False  # We are master, neighbor is slave

            # Accept neighbor's DD if it acknowledges us as master
            if not (dd_packet.flags & DD_FLAG_MS):
                # Neighbor accepts us as master
                neighbor.dd_sequence_number = dd_packet.dd_sequence_number
                neighbor.last_received_dd_sequence = dd_packet.dd_sequence_number

                # Move to Exchange state
                neighbor.process_event(EVENT_NEGOTIATION_DONE)
                self.logger.info(f"Negotiation done with {neighbor.neighbor_id}, we are MASTER")

                # Send first DD in Exchange state
                await self._send_dd_packet(neighbor)
        else:
            # Neighbor is master
            neighbor.is_master = True  # Neighbor is master, we are slave

            # Use neighbor's sequence number
            neighbor.dd_sequence_number = dd_packet.dd_sequence_number
            neighbor.last_received_dd_sequence = dd_packet.dd_sequence_number

            # Move to Exchange state
            neighbor.process_event(EVENT_NEGOTIATION_DONE)
            self.logger.info(f"Negotiation done with {neighbor.neighbor_id}, we are SLAVE")

            # Send response DD in Exchange state
            await self._send_dd_packet(neighbor)

    async def _process_dd_exchange(self, neighbor, dd_packet):
        """Process DD packet in Exchange state - database exchange"""
        # Verify sequence number
        if neighbor.is_master:
            # We are slave, neighbor is master - accept neighbor's sequence
            if dd_packet.dd_sequence_number != neighbor.last_received_dd_sequence + 1:
                self.logger.warning(f"DD sequence mismatch from master {neighbor.neighbor_id}")
                return
            neighbor.last_received_dd_sequence = dd_packet.dd_sequence_number
            neighbor.dd_sequence_number = dd_packet.dd_sequence_number
        else:
            # We are master, neighbor is slave - sequence should match ours
            if dd_packet.dd_sequence_number != neighbor.dd_sequence_number:
                self.logger.warning(f"DD sequence mismatch from slave {neighbor.neighbor_id}")
                return

        # Process LSA headers from DD packet
        # (In a full implementation, we would check against our LSDB and add missing LSAs to request list)
        for lsa_header in dd_packet.lsa_headers:
            # Simplified: just log for now
            self.logger.debug(f"Received LSA header: type=0x{lsa_header.ls_type:04x}, "
                            f"adv={lsa_header.advertising_router}")

        # Check if exchange is complete (More bit not set)
        if not (dd_packet.flags & DD_FLAG_M):
            # Neighbor has sent all its LSAs
            if len(neighbor.db_summary_list) == 0:
                # We have also sent all our LSAs
                self.logger.info(f"DD Exchange complete with {neighbor.neighbor_id}")

                # Check if we need to load LSAs
                if len(neighbor.link_state_request_list) > 0:
                    neighbor.process_event(EVENT_EXCHANGE_DONE, need_loading=True)
                else:
                    neighbor.process_event(EVENT_EXCHANGE_DONE, need_loading=False)
            else:
                # Send next DD packet with our remaining LSAs
                await self._send_dd_packet(neighbor)
        else:
            # Send response DD packet
            await self._send_dd_packet(neighbor)

    async def _process_dd_stable(self, neighbor, dd_packet):
        """Process DD packet in Loading or Full state - duplicate/retransmission"""
        # This is likely a retransmission, just acknowledge
        self.logger.debug(f"Received duplicate DD from {neighbor.neighbor_id}")
        # In a full implementation, we would resend our last DD packet
        pass

    async def _send_dd_packet(self, neighbor):
        """Send Database Description packet to neighbor"""
        try:
            # Determine flags
            flags = 0

            if neighbor.state == STATE_EXSTART:
                # Initial DD packet in ExStart
                flags = DD_FLAG_I | DD_FLAG_M
                if not neighbor.is_master:
                    flags |= DD_FLAG_MS
                # Use our own sequence number for initial packet
                if neighbor.dd_sequence_number == 0:
                    import random
                    neighbor.dd_sequence_number = random.randint(1, 0xFFFFFFFF)
            elif neighbor.state == STATE_EXCHANGE:
                # Exchange state
                if len(neighbor.db_summary_list) > 0:
                    flags |= DD_FLAG_M
                if not neighbor.is_master:
                    flags |= DD_FLAG_MS
                    # Increment sequence as master
                    neighbor.dd_sequence_number += 1

            # Build DD packet
            dd = DatabaseDescriptionPacket(
                header=OSPFv3Header(
                    packet_type=DATABASE_DESCRIPTION,
                    router_id=self.router_id,
                    area_id=self.config.area_id,
                    instance_id=self.config.instance_id
                ),
                options=self.config.options,
                interface_mtu=1500,
                flags=flags,
                dd_sequence_number=neighbor.dd_sequence_number,
                lsa_headers=[]  # Simplified: empty for now
            )

            # Encode and send
            packet_bytes = dd.encode(
                src_addr=self.config.link_local_address,
                dst_addr=neighbor.neighbor_address
            )

            self.socket.sendto(packet_bytes, (neighbor.neighbor_address, 0))

            self.logger.debug(f"Sent DD to {neighbor.neighbor_id}: "
                            f"Seq={neighbor.dd_sequence_number}, Flags=0x{flags:02x}")

        except Exception as e:
            self.logger.error(f"Error sending DD packet: {e}")

    async def _neighbor_timer(self):
        """Check neighbor inactivity timers"""
        self.logger.info("Neighbor timer started")

        try:
            while True:
                await asyncio.sleep(1)

                # Check each neighbor
                for neighbor_id, neighbor in list(self.neighbors.items()):
                    if neighbor.is_inactive():
                        self.logger.warning(f"Neighbor {neighbor_id} timed out")
                        neighbor.process_event(EVENT_INACTIVITY_TIMER)

                        # Remove if down
                        if neighbor.state == STATE_DOWN:
                            del self.neighbors[neighbor_id]
                            self.logger.info(f"Removed neighbor {neighbor_id}")

                # Update statistics
                self._update_stats()

        except asyncio.CancelledError:
            self.logger.info("Neighbor timer stopped")

    def _generate_link_lsa(self):
        """Generate Link-LSA for this interface"""
        # Create prefixes from global addresses
        prefixes = []
        for addr in self.config.global_addresses:
            # Assuming /64 prefix
            prefix = PrefixOption(
                prefix_length=64,
                prefix_options=PREFIX_OPTION_LA,  # Local address
                metric=0,
                address_prefix=addr
            )
            prefixes.append(prefix)

        self.link_lsa = LinkLSA(
            header=LSAHeader(
                ls_type=LINK_LSA,
                link_state_id=self.config.interface_id,
                advertising_router=self.router_id,
                ls_age=0,
                ls_sequence_number=INITIAL_SEQ_NUM
            ),
            router_priority=self.config.router_priority,
            options=self.config.options,
            link_local_address=self.config.link_local_address,
            prefixes=prefixes
        )

        self.logger.info(f"Generated Link-LSA with {len(prefixes)} prefixes")

    def _update_stats(self):
        """Update interface statistics"""
        self.stats['neighbors_up'] = len(self.neighbors)
        self.stats['neighbors_full'] = sum(1 for n in self.neighbors.values() if n.is_full())

    def get_statistics(self) -> dict:
        """Get interface statistics"""
        self._update_stats()

        return {
            'interface': self.config.interface_name,
            'state': self.state,
            'area_id': self.config.area_id,
            'router_id': self.router_id,
            'dr': self.designated_router,
            'bdr': self.backup_designated_router,
            'neighbors': len(self.neighbors),
            'neighbors_full': self.stats['neighbors_full'],
            'hello_sent': self.stats['hello_sent'],
            'hello_received': self.stats['hello_received'],
            'dr_elections': self.stats['dr_elections']
        }

    def get_neighbor_list(self) -> List[Dict]:
        """Get list of neighbors with details"""
        return [neighbor.get_statistics() for neighbor in self.neighbors.values()]
