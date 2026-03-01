"""
BGP Speaker - Convenience Wrapper

Provides a high-level interface for running a BGP speaker.
Simplifies configuration and management of BGP agent and peers.

Example usage:
    speaker = BGPSpeaker(local_as=65001, router_id="192.0.2.1")

    # Add eBGP peer
    speaker.add_peer(peer_ip="192.0.2.2", peer_as=65002)

    # Add iBGP peer as route reflector client
    speaker.enable_route_reflection()
    speaker.add_peer(peer_ip="192.0.2.3", peer_as=65001,
                    route_reflector_client=True)

    # Start speaker
    await speaker.start()

    # Get routes
    routes = speaker.get_routes()
"""

import asyncio
import logging
from typing import Optional, Dict, List

from .agent import BGPAgent
from .session import BGPSessionConfig
from .rib import BGPRoute
from .policy import Policy, PolicyEngine
from .constants import BGP_PORT


class BGPSpeaker:
    """
    BGP Speaker - High-level BGP interface

    Provides simplified API for running a BGP speaker with multiple peers.
    """

    def __init__(self, local_as: int, router_id: str,
                 listen_ip: str = "0.0.0.0", listen_port: int = BGP_PORT,
                 log_level: str = "INFO", kernel_route_manager=None):
        """
        Initialize BGP speaker

        Args:
            local_as: Local AS number
            router_id: Router ID (IPv4 address format)
            listen_ip: IP to listen on (default: all interfaces)
            listen_port: Port to listen on (default: 179)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            kernel_route_manager: Optional kernel route manager for installing routes
        """
        self.local_as = local_as
        self.router_id = router_id
        self.listen_ip = listen_ip
        self.listen_port = listen_port

        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        self.logger = logging.getLogger(f"BGPSpeaker[AS{local_as}]")

        # Create BGP agent
        self.agent = BGPAgent(local_as, router_id, listen_ip, listen_port, kernel_route_manager)

        # Peer configurations
        self.peer_configs: Dict[str, BGPSessionConfig] = {}

    def add_peer(self, peer_ip: str, peer_as: int,
                 peer_port: int = BGP_PORT,
                 local_ip: Optional[str] = None,
                 local_port: int = 0,
                 passive: bool = False,
                 hold_time: int = 180,
                 connect_retry_time: int = 120,
                 route_reflector_client: bool = False,
                 import_policy: Optional[Policy] = None,
                 export_policy: Optional[Policy] = None,
                 enable_flap_damping: bool = False,
                 flap_damping_config: Optional[object] = None,
                 enable_graceful_restart: bool = False,
                 graceful_restart_time: int = 120,
                 enable_rpki_validation: bool = False,
                 rpki_reject_invalid: bool = False,
                 enable_flowspec: bool = False,
                 accept_any_source: bool = False,
                 hostname: bool = False) -> None:
        """
        Add BGP peer

        Args:
            peer_ip: Peer IP address (or hostname for ngrok, or synthetic key for mesh)
            peer_as: Peer AS number
            peer_port: Peer TCP port (default: 179)
            local_ip: Local IP for this session (default: router_id)
            local_port: Local TCP port (default: ephemeral)
            passive: Wait for peer to connect (default: False)
            hold_time: Hold time in seconds (default: 180)
            connect_retry_time: Connect retry time in seconds (default: 120)
            route_reflector_client: Is this peer a route reflector client (default: False)
            import_policy: Import policy for this peer
            export_policy: Export policy for this peer
            enable_flap_damping: Enable route flap damping (default: False)
            flap_damping_config: Flap damping configuration (default: None, uses RFC defaults)
            enable_graceful_restart: Enable graceful restart (default: False)
            graceful_restart_time: Restart time in seconds (default: 120)
            enable_rpki_validation: Enable RPKI route origin validation (default: False)
            rpki_reject_invalid: Reject RPKI-invalid routes (default: False)
            enable_flowspec: Enable BGP FlowSpec (default: False)
            accept_any_source: Accept connections from any IP, match by AS from OPEN (default: False)
            hostname: True if peer_ip is a hostname like ngrok endpoint (default: False)
        """
        if not local_ip:
            local_ip = self.router_id

        # Create session config
        config = BGPSessionConfig(
            local_as=self.local_as,
            local_router_id=self.router_id,
            local_ip=local_ip,
            local_port=local_port,
            peer_as=peer_as,
            peer_ip=peer_ip,
            peer_port=peer_port,
            hold_time=hold_time,
            connect_retry_time=connect_retry_time,
            passive=passive,
            route_reflector_client=route_reflector_client,
            enable_flap_damping=enable_flap_damping,
            flap_damping_config=flap_damping_config,
            enable_graceful_restart=enable_graceful_restart,
            graceful_restart_time=graceful_restart_time,
            enable_rpki_validation=enable_rpki_validation,
            rpki_reject_invalid=rpki_reject_invalid,
            enable_flowspec=enable_flowspec,
            accept_any_source=accept_any_source,
            hostname=hostname,
        )

        # Add peer to agent
        session = self.agent.add_peer(config)

        # Configure policies
        if import_policy:
            self.agent.set_import_policy(peer_ip, import_policy)
        if export_policy:
            self.agent.set_export_policy(peer_ip, export_policy)

        self.peer_configs[peer_ip] = config

        self.logger.info(f"Added peer {peer_ip} AS{peer_as} "
                        f"({'passive' if passive else 'active'}, "
                        f"{'iBGP' if peer_as == self.local_as else 'eBGP'})")

    def remove_peer(self, peer_ip: str) -> None:
        """
        Remove BGP peer

        Args:
            peer_ip: Peer IP address
        """
        self.agent.remove_peer(peer_ip)

        if peer_ip in self.peer_configs:
            del self.peer_configs[peer_ip]

        self.logger.info(f"Removed peer {peer_ip}")

    def enable_route_reflection(self, cluster_id: Optional[str] = None) -> None:
        """
        Enable route reflection

        Args:
            cluster_id: Cluster ID (default: router_id)
        """
        self.agent.enable_route_reflection(cluster_id)
        self.logger.info("Route reflection enabled")

    async def start(self) -> None:
        """Start BGP speaker"""
        self.logger.info(f"Starting BGP speaker AS{self.local_as} Router-ID {self.router_id}")

        # Start agent
        await self.agent.start()

        # Start all peer sessions
        for peer_ip in self.peer_configs.keys():
            await self.agent.start_peer(peer_ip)

        self.logger.info("BGP speaker started")

    async def stop(self) -> None:
        """Stop BGP speaker"""
        self.logger.info("Stopping BGP speaker")
        await self.agent.stop()
        self.logger.info("BGP speaker stopped")

    async def run(self) -> None:
        """
        Run BGP speaker (blocks until stopped)

        This is a convenience method that starts the speaker
        and keeps it running until interrupted.
        """
        await self.start()

        try:
            # Keep running
            while self.agent.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            await self.stop()

    @property
    def stats(self) -> Dict:
        """
        Get aggregated message statistics from all BGP sessions.
        Used by Prometheus metrics collector.

        Returns:
            Dictionary with aggregated message counters
        """
        return self.agent.stats

    def get_statistics(self) -> Dict:
        """
        Get BGP statistics

        Returns:
            Dictionary with statistics for all peers and routes
        """
        return self.agent.get_statistics()

    def get_peer_status(self, peer_ip: str) -> Optional[Dict]:
        """
        Get status of specific peer

        Args:
            peer_ip: Peer IP address

        Returns:
            Peer status or None if not found
        """
        return self.agent.get_peer_status(peer_ip)

    def get_routes(self, prefix: Optional[str] = None) -> List[BGPRoute]:
        """
        Get routes from Loc-RIB

        Args:
            prefix: Optional prefix to filter (default: all routes)

        Returns:
            List of BGP routes
        """
        return self.agent.get_routes(prefix)

    def get_route(self, prefix: str) -> Optional[BGPRoute]:
        """
        Get specific route from Loc-RIB

        Args:
            prefix: Prefix to lookup

        Returns:
            BGP route or None
        """
        return self.agent.loc_rib.lookup(prefix)

    def get_peer_routes(self, peer_ip: str, prefix: Optional[str] = None) -> List[BGPRoute]:
        """
        Get routes received from specific peer

        Args:
            peer_ip: Peer IP address
            prefix: Optional prefix to filter

        Returns:
            List of BGP routes from this peer
        """
        session = self.agent.sessions.get(peer_ip)
        if not session:
            return []

        if prefix:
            return session.adj_rib_in.get_routes(prefix)
        else:
            all_routes = []
            for pfx in session.adj_rib_in.get_prefixes():
                all_routes.extend(session.adj_rib_in.get_routes(pfx))
            return all_routes

    def set_import_policy(self, peer_ip: str, policy: Policy) -> None:
        """
        Set import policy for peer

        Args:
            peer_ip: Peer IP address
            policy: Import policy
        """
        self.agent.set_import_policy(peer_ip, policy)

    def set_export_policy(self, peer_ip: str, policy: Policy) -> None:
        """
        Set export policy for peer

        Args:
            peer_ip: Peer IP address
            policy: Export policy
        """
        self.agent.set_export_policy(peer_ip, policy)

    def is_established(self, peer_ip: str) -> bool:
        """
        Check if peer session is established

        Args:
            peer_ip: Peer IP address

        Returns:
            True if session is established
        """
        session = self.agent.sessions.get(peer_ip)
        return session.is_established() if session else False

    def get_established_peers(self) -> List[str]:
        """
        Get list of established peer IPs

        Returns:
            List of peer IP addresses with established sessions
        """
        return [
            peer_ip for peer_ip, session in self.agent.sessions.items()
            if session.is_established()
        ]

    def get_all_peers(self) -> List[str]:
        """
        Get list of all configured peer IPs

        Returns:
            List of all peer IP addresses
        """
        return list(self.peer_configs.keys())

    async def shutdown_peer(self, peer_ip: str, error_code: Optional[int] = None,
                           error_subcode: Optional[int] = None) -> None:
        """
        Gracefully shutdown peer session

        Args:
            peer_ip: Peer IP address
            error_code: Optional NOTIFICATION error code
            error_subcode: Optional NOTIFICATION error subcode
        """
        session = self.agent.sessions.get(peer_ip)
        if session:
            await session.stop(error_code, error_subcode)

    async def restart_peer(self, peer_ip: str) -> bool:
        """
        Restart peer session

        Args:
            peer_ip: Peer IP address

        Returns:
            True if restart successful
        """
        # Stop peer
        await self.agent.stop_peer(peer_ip)

        # Wait a moment
        await asyncio.sleep(1)

        # Start peer
        return await self.agent.start_peer(peer_ip)


# Convenience function for simple BGP speaker

async def run_bgp_speaker(local_as: int, router_id: str,
                         peers: List[Dict],
                         route_reflector: bool = False,
                         cluster_id: Optional[str] = None) -> None:
    """
    Run BGP speaker with given configuration

    Args:
        local_as: Local AS number
        router_id: Router ID
        peers: List of peer configurations (dicts with peer_ip, peer_as, etc.)
        route_reflector: Enable route reflection
        cluster_id: Route reflector cluster ID

    Example:
        await run_bgp_speaker(
            local_as=65001,
            router_id="192.0.2.1",
            peers=[
                {"peer_ip": "192.0.2.2", "peer_as": 65002},
                {"peer_ip": "192.0.2.3", "peer_as": 65001, "route_reflector_client": True}
            ],
            route_reflector=True
        )
    """
    speaker = BGPSpeaker(local_as, router_id)

    # Enable route reflection if requested
    if route_reflector:
        speaker.enable_route_reflection(cluster_id)

    # Add peers
    for peer_config in peers:
        speaker.add_peer(**peer_config)

    # Run speaker
    await speaker.run()
