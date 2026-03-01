"""
OSPFv3 Speaker - Main OSPFv3 Protocol Handler
RFC 5340 - OSPF for IPv6
"""

import asyncio
import logging
import time
import ipaddress
from typing import Dict, List, Optional
from dataclasses import dataclass
from .constants import *
from .interface import OSPFv3Interface, OSPFv3InterfaceConfig
from .lsdb import OSPFv3LSDB
from .lsa import *
from .packets import LSAHeader


@dataclass
class OSPFv3Config:
    """OSPFv3 global configuration"""
    router_id: str
    areas: List[str] = None  # Area IDs, default [0.0.0.0]
    log_level: str = "INFO"

    def __post_init__(self):
        if self.areas is None:
            self.areas = ["0.0.0.0"]


class OSPFv3Speaker:
    """
    OSPFv3 Speaker

    Main OSPFv3 protocol engine that manages:
    - Multiple areas and interfaces
    - Link State Database per area
    - SPF calculation
    - LSA generation and flooding
    """

    def __init__(self, config: OSPFv3Config):
        self.config = config
        self.router_id = config.router_id
        self.logger = logging.getLogger(f"OSPFv3[{self.router_id}]")
        self.logger.setLevel(getattr(logging, config.log_level.upper()))

        # Interfaces
        self.interfaces: Dict[str, OSPFv3Interface] = {}  # interface_name -> interface

        # Link State Databases (per area)
        self.lsdbs: Dict[str, OSPFv3LSDB] = {}  # area_id -> LSDB

        # Initialize LSDBs for configured areas
        for area_id in self.config.areas:
            self.lsdbs[area_id] = OSPFv3LSDB(area_id)

        # Running state
        self.running = False

        # Tasks
        self.lsa_refresh_task = None
        self.spf_task = None

        # Statistics
        self.stats = {
            'uptime': 0,
            'start_time': 0,
            'interfaces': 0,
            'neighbors': 0,
            'neighbors_full': 0,
            'lsas_total': 0,
            'spf_runs': 0,
            'last_spf_time': 0
        }

    async def start(self):
        """Start OSPFv3 speaker"""
        if self.running:
            self.logger.warning("OSPFv3 speaker already running")
            return

        self.logger.info(f"Starting OSPFv3 speaker - Router ID {self.router_id}")

        self.running = True
        self.stats['start_time'] = time.time()

        # Start all interfaces
        for interface in self.interfaces.values():
            try:
                await interface.start()
            except Exception as e:
                self.logger.error(f"Failed to start interface {interface.config.interface_name}: {e}")

        # Start background tasks
        self.lsa_refresh_task = asyncio.create_task(self._lsa_refresh_loop())
        self.spf_task = asyncio.create_task(self._spf_calculation_loop())

        self.logger.info(f"OSPFv3 speaker started with {len(self.interfaces)} interfaces")

    async def stop(self):
        """Stop OSPFv3 speaker"""
        if not self.running:
            return

        self.logger.info("Stopping OSPFv3 speaker")

        self.running = False

        # Cancel tasks
        if self.lsa_refresh_task:
            self.lsa_refresh_task.cancel()
        if self.spf_task:
            self.spf_task.cancel()

        # Stop all interfaces
        for interface in self.interfaces.values():
            await interface.stop()

        self.logger.info("OSPFv3 speaker stopped")

    def add_interface(self, interface_name: str, interface_id: int,
                     link_local_address: str, area_id: str = "0.0.0.0",
                     global_addresses: List[str] = None,
                     network_type: str = NETWORK_TYPE_BROADCAST,
                     hello_interval: int = DEFAULT_HELLO_INTERVAL,
                     dead_interval: int = DEFAULT_DEAD_INTERVAL,
                     router_priority: int = 1) -> OSPFv3Interface:
        """
        Add OSPFv3 interface

        Args:
            interface_name: Interface name (e.g., 'eth0')
            interface_id: Numeric interface ID
            link_local_address: IPv6 link-local address (fe80::)
            area_id: OSPF area ID
            global_addresses: List of IPv6 global unicast addresses
            network_type: Network type (broadcast, point-to-point, etc.)
            hello_interval: Hello interval in seconds
            dead_interval: Dead interval in seconds
            router_priority: Router priority for DR election

        Returns:
            OSPFv3Interface instance
        """
        if interface_name in self.interfaces:
            self.logger.warning(f"Interface {interface_name} already exists")
            return self.interfaces[interface_name]

        if global_addresses is None:
            global_addresses = []

        # Create interface configuration
        config = OSPFv3InterfaceConfig(
            interface_name=interface_name,
            interface_id=interface_id,
            area_id=area_id,
            link_local_address=link_local_address,
            global_addresses=global_addresses,
            network_type=network_type,
            hello_interval=hello_interval,
            dead_interval=dead_interval,
            router_priority=router_priority
        )

        # Create interface
        interface = OSPFv3Interface(config, self.router_id)
        self.interfaces[interface_name] = interface

        # Ensure LSDB exists for this area
        if area_id not in self.lsdbs:
            self.lsdbs[area_id] = OSPFv3LSDB(area_id)

        self.logger.info(f"Added interface {interface_name} (ID={interface_id}) to area {area_id}")

        return interface

    def remove_interface(self, interface_name: str):
        """Remove OSPFv3 interface"""
        if interface_name not in self.interfaces:
            self.logger.warning(f"Interface {interface_name} not found")
            return

        interface = self.interfaces[interface_name]

        # Stop interface if running
        if self.running:
            asyncio.create_task(interface.stop())

        del self.interfaces[interface_name]

        self.logger.info(f"Removed interface {interface_name}")

    async def _lsa_refresh_loop(self):
        """
        Periodic LSA refresh and aging

        Refreshes self-originated LSAs every 30 minutes
        Ages all LSAs every second
        """
        self.logger.info("LSA refresh loop started")

        try:
            while self.running:
                await asyncio.sleep(60)  # Run every minute

                # Age all LSAs
                for lsdb in self.lsdbs.values():
                    maxage_lsas = lsdb.age_lsas()

                    # Flush MaxAge LSAs
                    if maxage_lsas:
                        self.logger.info(f"Flushing {len(maxage_lsas)} MaxAge LSAs from area {lsdb.area_id}")
                        lsdb.flush_maxage_lsas()

                # TODO: Refresh self-originated LSAs

        except asyncio.CancelledError:
            self.logger.info("LSA refresh loop stopped")
        except Exception as e:
            self.logger.error(f"Error in LSA refresh loop: {e}")

    async def _spf_calculation_loop(self):
        """
        Periodic SPF calculation

        Runs SPF when LSDB changes
        """
        self.logger.info("SPF calculation loop started")

        try:
            while self.running:
                await asyncio.sleep(10)  # Check every 10 seconds

                # TODO: Implement SPF calculation trigger
                # For now, just a placeholder

        except asyncio.CancelledError:
            self.logger.info("SPF calculation loop stopped")
        except Exception as e:
            self.logger.error(f"Error in SPF calculation loop: {e}")

    def run_spf(self, area_id: str):
        """
        Run SPF calculation for area

        Dijkstra's algorithm to compute shortest path tree
        """
        if area_id not in self.lsdbs:
            self.logger.error(f"No LSDB for area {area_id}")
            return

        self.logger.info(f"Running SPF for area {area_id}")

        lsdb = self.lsdbs[area_id]

        # TODO: Implement Dijkstra SPF calculation
        # This is a placeholder for the actual SPF implementation

        self.stats['spf_runs'] += 1
        self.stats['last_spf_time'] = time.time()

    def originate_router_lsa(self, area_id: str):
        """
        Originate Router-LSA for area

        Router-LSA describes router's links in the area
        """
        if area_id not in self.lsdbs:
            self.logger.error(f"No LSDB for area {area_id}")
            return

        self.logger.info(f"Originating Router-LSA for area {area_id}")

        # Build list of links from interfaces in this area
        links = []

        for interface in self.interfaces.values():
            if interface.config.area_id != area_id:
                continue

            # Add links based on interface state and neighbors
            if interface.config.network_type == NETWORK_TYPE_PTP:
                # Point-to-point link
                for neighbor in interface.neighbors.values():
                    if neighbor.is_full():
                        link = RouterLink(
                            link_type=LINK_TYPE_PTP,
                            metric=1,  # TODO: Get from interface cost
                            interface_id=interface.config.interface_id,
                            neighbor_interface_id=neighbor.neighbor_interface_id,
                            neighbor_router_id=neighbor.neighbor_id
                        )
                        links.append(link)

            elif interface.state in ["DR", "Backup", "DROther"]:
                # Broadcast network
                if interface.designated_router != "0.0.0.0":
                    # Link to transit network (DR)
                    link = RouterLink(
                        link_type=LINK_TYPE_TRANSIT,
                        metric=1,
                        interface_id=interface.config.interface_id,
                        neighbor_interface_id=interface.config.interface_id,
                        neighbor_router_id=interface.designated_router
                    )
                    links.append(link)

        # Create Router-LSA
        router_lsa = RouterLSA(
            header=LSAHeader(
                ls_type=ROUTER_LSA,
                link_state_id=0,  # Always 0 for Router-LSA
                advertising_router=self.router_id,
                ls_sequence_number=INITIAL_SEQ_NUM,  # TODO: Increment properly
                ls_age=0
            ),
            flags=0,  # TODO: Set V, E, B bits appropriately
            options=OPTION_V6 | OPTION_E | OPTION_R,
            links=links
        )

        # Encode and install in LSDB
        body = router_lsa.encode()
        router_lsa.header.length = LSA_HEADER_SIZE + len(body)

        lsdb = self.lsdbs[area_id]
        lsdb.install_lsa(router_lsa.header, body, from_self=True)

        self.logger.info(f"Originated Router-LSA with {len(links)} links")

    def get_statistics(self) -> Dict:
        """Get OSPFv3 statistics"""
        # Update uptime
        if self.stats['start_time'] > 0:
            self.stats['uptime'] = int(time.time() - self.stats['start_time'])

        # Update interface and neighbor counts
        self.stats['interfaces'] = len(self.interfaces)
        self.stats['neighbors'] = sum(len(iface.neighbors) for iface in self.interfaces.values())
        self.stats['neighbors_full'] = sum(
            sum(1 for n in iface.neighbors.values() if n.is_full())
            for iface in self.interfaces.values()
        )

        # Update LSDB statistics
        self.stats['lsas_total'] = sum(len(lsdb) for lsdb in self.lsdbs.values())

        # Per-area statistics
        area_stats = {}
        for area_id, lsdb in self.lsdbs.items():
            area_stats[area_id] = lsdb.get_statistics()

        return {
            'router_id': self.router_id,
            'uptime': self.stats['uptime'],
            'interfaces': self.stats['interfaces'],
            'neighbors': self.stats['neighbors'],
            'neighbors_full': self.stats['neighbors_full'],
            'lsas_total': self.stats['lsas_total'],
            'spf_runs': self.stats['spf_runs'],
            'last_spf_time': self.stats['last_spf_time'],
            'areas': area_stats
        }

    def get_interface_status(self) -> List[Dict]:
        """Get status of all interfaces"""
        return [iface.get_statistics() for iface in self.interfaces.values()]

    def get_neighbor_status(self) -> List[Dict]:
        """Get status of all neighbors across all interfaces"""
        neighbors = []
        for interface in self.interfaces.values():
            neighbors.extend(interface.get_neighbor_list())
        return neighbors

    def get_lsdb_summary(self, area_id: str = None) -> Dict:
        """
        Get LSDB summary

        Args:
            area_id: Specific area, or None for all areas

        Returns:
            LSDB statistics
        """
        if area_id:
            if area_id in self.lsdbs:
                return {area_id: self.lsdbs[area_id].get_statistics()}
            else:
                return {}
        else:
            return {area_id: lsdb.get_statistics()
                   for area_id, lsdb in self.lsdbs.items()}
